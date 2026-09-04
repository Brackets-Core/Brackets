#!/usr/bin/env python3
"""
Servicio de Sincronización Bidireccional: Markdown ➔ YAML Database.
Analiza archivos Markdown editados externamente (Obsidian, VSCode, etc.)
y reconcilia el estado de tareas, notas e ideas en la base de datos relacional YAML.
Garantiza la no duplicidad de tareas arrastradas entre días.
"""

from __future__ import annotations
import os
import re
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Any

from brackets.models.entities import Task, Note, Idea, WeekSchedule, DaySchedule
from brackets.managers.entity_manager import EntityManager


class MarkdownSyncService:
    """Reconcilia cambios hechos a mano en Markdown hacia la base de datos YAML."""

    def __init__(self, entity_manager: EntityManager, vault_root: str = "."):
        self.manager = entity_manager
        self.vault_root = os.path.abspath(vault_root)

    # -------------------------------------------------------------------------
    # Sincronización de Bitácora Semanal
    # -------------------------------------------------------------------------
    def sync_week_from_markdown(self, md_path: str, year: int, week_num: int) -> bool:
        """Lee un archivo Markdown de bitácora semanal y reconcilia tareas, notas y topics."""
        if not os.path.exists(md_path):
            return False

        week = self.manager.load_week(year, week_num)
        if not week:
            return False

        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        today_str = datetime.now().strftime("%Y-%m-%d")

        # 1. Parsear Secciones Principales
        sections = self._parse_markdown_sections(content)

        # 2. Reconciliar Topics Generales (## 🎯Topics)
        topics_lines = sections.get("topics", [])
        self._reconcile_topics(week, topics_lines, today_str)

        # 3. Reconciliar Tareas de la Semana (## 📋Week Tasks)
        week_tasks = sections.get("week_tasks", [])
        self._reconcile_week_tasks(week, week_tasks, today_str)

        # 4. Reconciliar Notas (## 📝Notes)
        notes_blocks = sections.get("notes_blocks", [])
        self._reconcile_notes(week, notes_blocks, year, week_num)

        # 5. Reconciliar Días de forma holística sin duplicidades
        days_dict = sections.get("days", {})
        days_meta = sections.get("days_meta", {})
        self._reconcile_all_days(week, days_dict, days_meta, year, week_num, today_str)

        # Guardar cambios en YAML
        self.manager.save_topics()
        self.manager.save_tasks()
        self.manager.save_notes()
        self.manager.save_week(week)
        return True

    @staticmethod
    def _parse_task_status_and_title(raw_text: str, is_checkbox_done: bool) -> Tuple[str, str]:
        """
        Determina el estado ('done', 'cancelled', 'pending') y el título limpio de una tarea.
        Si la tarea está tachada con ~~...~~, se considera 'cancelled' y se limpian los delimitadores ~~.
        """
        text = raw_text.strip()

        # Caso 1: Todo el texto está envuelto en ~~...~~ (ej: ~~Seguimiento Reporting~~)
        if text.startswith("~~") and text.endswith("~~") and len(text) >= 4:
            clean = text[2:-2].strip()
            return "cancelled", clean

        # Caso 2: Tachado con etiqueta de proyecto al final (ej: ~~Seguimiento Reporting~~ [GENERAL])
        m_proj_suffix = re.match(r'^~~(.+?)~~\s*(\[[A-Za-z0-9_-]+\])$', text)
        if m_proj_suffix:
            clean = f"{m_proj_suffix.group(1).strip()} {m_proj_suffix.group(2).strip()}"
            return "cancelled", clean

        # Caso 3: Tachado con etiqueta de proyecto al inicio (ej: [GENERAL] ~~Seguimiento Reporting~~)
        m_proj_prefix = re.match(r'^(\[[A-Za-z0-9_-]+\])\s*~~(.+?)~~$', text)
        if m_proj_prefix:
            clean = f"{m_proj_prefix.group(1).strip()} {m_proj_prefix.group(2).strip()}"
            return "cancelled", clean

        # Caso 4: No está tachada en su totalidad
        if is_checkbox_done:
            return "done", text
        return "pending", text

    def _parse_markdown_sections(self, content: str) -> Dict[str, Any]:
        """Trocea el documento Markdown en sus secciones semánticas."""
        lines = content.splitlines()
        current_section = None
        current_day_num = None

        topics_lines: List[str] = []
        week_tasks_lines: List[Tuple[str, str]] = []
        notes_raw_lines: List[str] = []
        days: Dict[int, List[Tuple[str, str]]] = {}
        days_meta: Dict[int, Dict[str, Any]] = {}

        for line in lines:
            stripped = line.strip()

            # Detectar encabezados nivel 2
            if stripped.startswith("## "):
                header = stripped[3:].strip()
                if "Topics" in header or "🎯" in header:
                    current_section = "topics"
                    current_day_num = None
                    continue
                elif "Week Tasks" in header or "Weekly Tasks" in header or "📋" in header or "Tareas" in header:
                    current_section = "week_tasks"
                    current_day_num = None
                    continue
                elif "Notes" in header or "📝" in header:
                    current_section = "notes"
                    current_day_num = None
                    continue
                elif "✅" in header:
                    # Legacy header "## ✅Topics"
                    current_section = "week_tasks"
                    current_day_num = None
                    continue
                else:
                    # Buscar número de día en el encabezado (ej: "🏠24", "🚗 25", "26", "🛠️29 (Intervención)")
                    match = re.search(r'\b(\d{1,2})\b', header)
                    if match:
                        current_section = "day"
                        current_day_num = int(match.group(1))
                        days.setdefault(current_day_num, [])

                        # Extraer emoji si existe antes o junto al número (incluyendo variation selectors como \ufe0f)
                        emoji_match = re.search(r'^([^\w\s\d()]+?)\s*\b\d{1,2}\b', header)
                        emoji = emoji_match.group(1).strip() if emoji_match else "🏠"

                        # Extraer nota entre paréntesis si existe
                        note_match = re.search(r'\(([^)]+)\)', header)
                        note = note_match.group(1).strip() if note_match else None

                        days_meta[current_day_num] = {
                            "emoji": emoji,
                            "note": note
                        }
                        continue
                    else:
                        current_section = None
                        current_day_num = None
                        continue

            if not stripped or stripped.startswith("---"):
                continue

            if current_section == "topics":
                m_chk = re.match(r'^\s*-\s*\[([ xX])\]\s*(.*)$', line)
                if m_chk:
                    t_text = m_chk.group(2).strip()
                    if t_text:
                        status, clean_title = self._parse_task_status_and_title(t_text, m_chk.group(1).lower() == 'x')
                        week_tasks_lines.append((status, clean_title))
                else:
                    m_item = re.match(r'^\s*-\s*(.*)$', line)
                    if m_item:
                        t_text = m_item.group(1).strip()
                        if t_text and not t_text.startswith("---"):
                            topics_lines.append(t_text)
            elif current_section == "week_tasks":
                m = re.match(r'^\s*-\s*\[([ xX])\]\s*(.*)$', line)
                if m:
                    t_text = m.group(2).strip()
                    if t_text:
                        status, clean_title = self._parse_task_status_and_title(t_text, m.group(1).lower() == 'x')
                        week_tasks_lines.append((status, clean_title))
                elif line.strip().startswith("- "):
                    t_text = line.strip()[2:].strip()
                    if t_text:
                        status, clean_title = self._parse_task_status_and_title(t_text, False)
                        week_tasks_lines.append((status, clean_title))
            elif current_section == "notes":
                notes_raw_lines.append(line)
            elif current_section == "day" and current_day_num is not None:
                m = re.match(r'^\s*-\s*\[([ xX])\]\s*(.*)$', line)
                if m:
                    t_text = m.group(2).strip()
                    if t_text:
                        status, clean_title = self._parse_task_status_and_title(t_text, m.group(1).lower() == 'x')
                        days[current_day_num].append((status, clean_title))
                elif line.strip().startswith("- "):
                    t_text = line.strip()[2:].strip()
                    if t_text:
                        status, clean_title = self._parse_task_status_and_title(t_text, False)
                        days[current_day_num].append((status, clean_title))

        # Parsear bloques de notas a partir de notes_raw_lines
        notes_blocks = self._parse_notes_blocks(notes_raw_lines)

        return {
            "topics": topics_lines,
            "week_tasks": week_tasks_lines,
            "notes_blocks": notes_blocks,
            "days": days,
            "days_meta": days_meta
        }

    def _parse_notes_blocks(self, raw_lines: List[str]) -> List[Dict[str, Any]]:
        """Extrae bloques de notas con subencabezados (### Título o - ### Título) y sus viñetas."""
        blocks: List[Dict[str, Any]] = []
        current_title = None
        current_proj = None
        current_bullets: List[str] = []

        for line in raw_lines:
            stripped = line.strip()
            if stripped.startswith("### ") or stripped.startswith("- ### "):
                if current_title or current_bullets:
                    blocks.append({
                        "title": current_title,
                        "project_id": current_proj,
                        "content": current_bullets
                    })
                if stripped.startswith("- ### "):
                    header = stripped[6:].strip()
                else:
                    header = stripped[4:].strip()

                # Extraer proyecto si está presente como [PROJ] Título
                p_match = re.match(r'^\[([A-Za-z0-9_-]+)\]\s*(.*)$', header)
                if p_match:
                    current_proj = p_match.group(1).strip()
                    current_title = p_match.group(2).strip()
                else:
                    current_proj = None
                    current_title = header
                current_bullets = []
            elif stripped.startswith("- "):
                bullet = stripped[2:].strip()
                if bullet:
                    current_bullets.append(bullet)

        if current_title or current_bullets:
            blocks.append({
                "title": current_title,
                "project_id": current_proj,
                "content": current_bullets
            })

        return blocks

    def _reconcile_topics(self, week: WeekSchedule, topic_lines: List[str], today_str: str) -> None:
        """Reconcilia la lista de topics generales en YAML."""
        current_topics = [self.manager.topics[tid] for tid in week.topic_ids if tid in self.manager.topics]

        for raw_line in topic_lines:
            clean = raw_line.strip()
            if not clean:
                continue
            # Puede venir en formato "[PROYECTO] Titulo" o "Titulo"
            proj_match = re.match(r'^\[([A-Za-z0-9_-]+)\]\s*(.*)$', clean)
            if proj_match:
                proj_id = proj_match.group(1).strip()
                title = proj_match.group(2).strip()
            else:
                proj_id = "GENERAL"
                title = clean

            # Evitar crear topics espurios si el texto coincide con una tarea existente y no tenía proyecto
            if not proj_match and any(t.title == title for t in self.manager.tasks.values()):
                continue

            # Buscar topic existente
            matched = next((t for t in current_topics if t.title == title), None)
            if not matched:
                topic = self.manager.create_topic(
                    title=title,
                    project_id=proj_id,
                    year=week.year,
                    week_num=week.week_number
                )
                if topic.id not in week.topic_ids:
                    week.topic_ids.append(topic.id)

    def _reconcile_week_tasks(self, week: WeekSchedule, task_tuples: List[Tuple[str, str]], today_str: str) -> None:
        """Reconcilia la lista de tareas semanales sin día concreto."""
        current_tasks = [self.manager.tasks[tid] for tid in week.week_task_ids if tid in self.manager.tasks]
        new_week_task_ids: List[str] = []

        for status, title in task_tuples:
            matched_task = next((t for t in current_tasks if t.title == title), None)
            if not matched_task:
                matched_task = next((t for t in current_tasks if t.title.replace("~~", "").strip() == title), None)

            if matched_task:
                if "~~" in matched_task.title:
                    matched_task.title = title

                if status == "cancelled":
                    matched_task.status = "cancelled"
                    matched_task.completed_at = None
                elif status == "done":
                    matched_task.status = "done"
                    if not matched_task.completed_at:
                        matched_task.completed_at = today_str
                else:
                    matched_task.status = "pending"
                    matched_task.completed_at = None

                if matched_task.id not in new_week_task_ids:
                    new_week_task_ids.append(matched_task.id)
            else:
                # Extraer proyecto si viene en el texto ej: [PROJ] Tarea
                proj_id = None
                p_match = re.match(r'^\[([A-Za-z0-9_-]+)\]\s*(.*)$', title)
                if p_match:
                    proj_id = p_match.group(1).strip()
                new_task = self.manager.create_task(
                    title=title,
                    project_id=proj_id,
                    is_week_task=True,
                    year=week.year,
                    week_num=week.week_number,
                    status=status
                )
                if status == "done":
                    new_task.completed_at = today_str
                if new_task.id not in new_week_task_ids:
                    new_week_task_ids.append(new_task.id)

        week.week_task_ids = new_week_task_ids
        week.topics_task_ids = new_week_task_ids

    def _reconcile_notes(self, week: WeekSchedule, note_blocks: List[Dict[str, Any]], year: int, week_num: int) -> None:
        """Reconcilia bloques de notas editados a mano."""
        existing_notes = [self.manager.notes[nid] for nid in week.note_ids if nid in self.manager.notes]

        for block in note_blocks:
            title = block.get("title")
            proj = block.get("project_id")
            bullets = block.get("content", [])

            # Buscar nota existente
            matched_note = None
            for n in existing_notes:
                if title and n.title and n.title.strip().lower() == title.strip().lower():
                    matched_note = n
                    break

            if matched_note:
                # Actualizar viñetas y proyecto si cambiaron
                if bullets:
                    matched_note.content = list(bullets)
                if proj:
                    matched_note.project_id = proj
            else:
                # Nota creada a mano en el markdown
                if title or bullets:
                    self.manager.add_note(
                        title=title,
                        content=bullets,
                        project_id=proj,
                        year=year,
                        week_num=week_num
                    )

    def _find_task_for_day(self, day: DaySchedule, week: WeekSchedule, title: str) -> Optional[Task]:
        """
        Busca inteligentemente una tarea con ese título priorizando:
        1. Tareas asignadas a este día concreto.
        2. Tareas en otros días de esta misma semana o en week_task_ids.
        3. Tareas pendientes/canceladas globales no resueltas (sin recurring_id).
        Evita reutilizar tareas recurrentes o completadas de semanas/meses anteriores.
        """
        clean_target = title.replace("~~", "").strip()

        # 1. En este día
        for tid in day.task_ids:
            t = self.manager.tasks.get(tid)
            if t and (t.title == title or t.title.replace("~~", "").strip() == clean_target):
                return t

        # 2. En otros días de esta semana
        for other_day in week.days:
            if other_day.day_number != day.day_number:
                for tid in other_day.task_ids:
                    t = self.manager.tasks.get(tid)
                    if t and (t.title == title or t.title.replace("~~", "").strip() == clean_target):
                        return t

        # 3. En tareas de la semana
        for tid in week.week_task_ids:
            t = self.manager.tasks.get(tid)
            if t and (t.title == title or t.title.replace("~~", "").strip() == clean_target):
                return t

        # 4. Comprobar si coincide con una tarea recurrente activa
        matching_rec = next((r for r in self.manager.list_recurring_tasks() if r.title == title or r.title == clean_target), None)
        if matching_rec:
            # Buscar una tarea existente asociada a esta recurrencia
            rec_task = next((t for t in self.manager.tasks.values() if t.recurring_id == matching_rec.id), None)
            if rec_task:
                return rec_task
            return None

        # 5. Tarea pendiente o cancelada global no asignada a otra semana
        for t in self.manager.tasks.values():
            if (t.title == title or t.title.replace("~~", "").strip() == clean_target) and (t.is_pending or t.is_cancelled):
                return t

        return None

    def _reconcile_all_days(
        self,
        week: WeekSchedule,
        days_dict: Dict[int, List[Tuple[str, str]]],
        days_meta: Dict[int, Dict[str, Optional[str]]],
        year: int,
        week_num: int,
        today_str: str
    ) -> None:
        """
        Reconcilia todos los días de la semana sincronizando tareas [x], [ ] y canceladas ~~...~~,
        evitando duplicidades entre días para una misma tarea arrastrada.
        """
        day_by_number: Dict[int, DaySchedule] = {d.day_number: d for d in week.days}

        # Asegurar días que existan en el markdown pero no en week.days
        for day_num, meta in days_meta.items():
            if day_num not in day_by_number:
                new_day = DaySchedule(
                    day_number=day_num,
                    location_emoji=meta.get("emoji") or "🚗",
                    location_note=meta.get("note")
                )
                week.days.append(new_day)
                day_by_number[day_num] = new_day

        ordered_day_numbers = [d.day_number for d in week.days]

        pending_task_latest_day: Dict[str, int] = {}
        done_tasks_by_day: Dict[int, List[str]] = {d_num: [] for d_num in ordered_day_numbers}
        cancelled_tasks_by_day: Dict[int, List[str]] = {d_num: [] for d_num in ordered_day_numbers}

        for day_num in ordered_day_numbers:
            tuples = days_dict.get(day_num, [])
            for status, title in tuples:
                clean_title = title.strip()
                if not clean_title:
                    continue
                if status == "done":
                    done_tasks_by_day.setdefault(day_num, []).append(clean_title)
                elif status == "cancelled":
                    cancelled_tasks_by_day.setdefault(day_num, []).append(clean_title)
                else:
                    # Guardar el último día donde aparece como pendiente
                    pending_task_latest_day[clean_title] = day_num

        new_day_task_ids: Dict[int, List[str]] = {d_num: [] for d_num in ordered_day_numbers}

        # 1. Reconciliar tareas COMPLETADAS ([x]) por día
        for day_num, done_titles in done_tasks_by_day.items():
            day = day_by_number.get(day_num)
            if not day:
                continue
            for title in done_titles:
                matched_task = self._find_task_for_day(day, week, title)
                if not matched_task:
                    matched_task = self.manager.create_task(
                        title=title,
                        year=year,
                        week_num=week_num,
                        day_number=day_num,
                        status="done"
                    )
                else:
                    if "~~" in matched_task.title:
                        matched_task.title = title
                    matched_task.status = "done"
                    if not matched_task.completed_at:
                        matched_task.completed_at = today_str

                new_day_task_ids[day_num].append(matched_task.id)

        # 2. Reconciliar tareas CANCELADAS ([ ] ~~...~~) por día
        for day_num, cancelled_titles in cancelled_tasks_by_day.items():
            day = day_by_number.get(day_num)
            if not day:
                continue
            for title in cancelled_titles:
                matched_task = self._find_task_for_day(day, week, title)
                if not matched_task:
                    matched_task = self.manager.create_task(
                        title=title,
                        year=year,
                        week_num=week_num,
                        day_number=day_num,
                        status="cancelled"
                    )
                else:
                    if "~~" in matched_task.title:
                        matched_task.title = title
                    matched_task.status = "cancelled"
                    matched_task.completed_at = None

                new_day_task_ids[day_num].append(matched_task.id)

        # 3. Reconciliar tareas PENDIENTES ([ ])
        for title, latest_day_num in pending_task_latest_day.items():
            # Si se marcó como completada o cancelada, no crearla/mantenerla como pendiente
            if any(title in titles for titles in done_tasks_by_day.values()):
                continue
            if any(title in titles for titles in cancelled_tasks_by_day.values()):
                continue

            target_day = day_by_number.get(latest_day_num)
            if not target_day:
                continue

            matched_task = self._find_task_for_day(target_day, week, title)
            if not matched_task:
                matched_task = self.manager.create_task(
                    title=title,
                    year=year,
                    week_num=week_num,
                    day_number=latest_day_num,
                    status="pending"
                )
            else:
                if "~~" in matched_task.title:
                    matched_task.title = title
                if matched_task.is_done or matched_task.is_cancelled:
                    matched_task.status = "pending"
                    matched_task.completed_at = None

            new_day_task_ids[latest_day_num].append(matched_task.id)

        # 4. Asignar los task_ids a cada día, deduplicar preservando orden y remover de tareas semanales
        for day in week.days:
            seen_ids = set()
            seen_titles = set()
            deduped = []
            for tid in new_day_task_ids.get(day.day_number, []):
                t = self.manager.tasks.get(tid)
                if not t:
                    continue
                if tid not in seen_ids and t.title not in seen_titles:
                    seen_ids.add(tid)
                    seen_titles.add(t.title)
                    deduped.append(tid)
                    if tid in week.week_task_ids:
                        week.week_task_ids.remove(tid)
                    if tid in week.topics_task_ids:
                        week.topics_task_ids.remove(tid)
            day.task_ids = deduped

    # -------------------------------------------------------------------------
    # Sincronización de Ideas ([🧩GENERAL]🧠Ideas.md)
    # -------------------------------------------------------------------------
    def sync_ideas_from_markdown(self, md_path: str) -> bool:
        """Lee [🧩GENERAL]🧠Ideas.md y reconcilia estado y viñetas en ideas.yaml."""
        if not os.path.exists(md_path):
            return False

        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.splitlines()
        current_project = None
        current_idea_title = None
        current_idea_status = "evaluating"
        current_idea_bullets: List[str] = []

        parsed_ideas: List[Dict[str, Any]] = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## 📁 "):
                # Guardar idea previa
                if current_idea_title:
                    parsed_ideas.append({
                        "title": current_idea_title,
                        "project_id": current_project,
                        "status": current_idea_status,
                        "content": current_idea_bullets
                    })
                    current_idea_title = None
                    current_idea_bullets = []

                p_str = stripped[5:].strip()
                current_project = None if p_str == "GENERAL" else p_str
                continue

            # Detectar idea (checkbox)
            m = re.match(r'^\s*-\s*\[([ xX])\]\s*(.*)$', line)
            if m and not line.startswith("    ") and not line.startswith("\t"):
                if current_idea_title:
                    parsed_ideas.append({
                        "title": current_idea_title,
                        "project_id": current_project,
                        "status": current_idea_status,
                        "content": current_idea_bullets
                    })

                box = m.group(1).lower()
                raw_text = m.group(2).strip()

                if "~~" in raw_text:
                    current_idea_status = "discarded"
                    current_idea_title = raw_text.replace("~~", "").strip()
                elif box == "x":
                    current_idea_status = "accepted"
                    current_idea_title = raw_text
                else:
                    current_idea_status = "evaluating"
                    current_idea_title = raw_text

                current_idea_bullets = []
                continue

            # Viñeta indentada de hipótesis
            if (line.startswith("  - ") or line.startswith("    - ")) and current_idea_title:
                bullet = stripped[2:].strip()
                if bullet:
                    current_idea_bullets.append(bullet)

        if current_idea_title:
            parsed_ideas.append({
                "title": current_idea_title,
                "project_id": current_project,
                "status": current_idea_status,
                "content": current_idea_bullets
            })

        # Reconciliar ideas en EntityManager
        for item in parsed_ideas:
            t = item["title"]
            proj = item["project_id"]
            stat = item["status"]
            bullets = item["content"]

            matched_idea = next(
                (i for i in self.manager.ideas.values() if i.title == t and i.project_id == proj),
                None
            )
            if matched_idea:
                matched_idea.status = stat
                if bullets:
                    matched_idea.content = list(bullets)
            else:
                self.manager.create_idea(
                    title=t,
                    content=bullets,
                    project_id=proj,
                    status=stat
                )

        self.manager.save_ideas()
        return True
