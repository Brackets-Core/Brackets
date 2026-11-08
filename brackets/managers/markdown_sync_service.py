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
from brackets.worklog.log4brackets import log4brackets
from brackets.utils.bitacora_parser import BitacoraMarkdownParser


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

        # Registrar tareas previas de esta semana para detectar si alguna fue borrada de la bitácora
        prev_week_task_ids: Set[str] = set(week.week_task_ids)
        for d in week.days:
            prev_week_task_ids.update(d.task_ids)

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

        # 6. Reconciliar Definiciones (<!-- Definiciones -->)
        definitions_tuples = sections.get("definitions", [])
        self._reconcile_definitions(week, definitions_tuples)

        # 7. Alta automática de personas mencionadas (@handle)
        self._auto_register_people(content, today_str)

        # 8. Eliminar tareas que han sido completamente borradas de la bitácora
        current_week_task_ids: Set[str] = set(week.week_task_ids)
        for d in week.days:
            current_week_task_ids.update(d.task_ids)

        removed_task_ids = prev_week_task_ids - current_week_task_ids
        for tid in removed_task_ids:
            task = self.manager.tasks.get(tid)
            # Solo eliminar si no es recurrente y no está asignada a otra semana
            if task and not task.is_recurring:
                if not self.manager.is_task_scheduled_in_other_weeks(tid, year, week_num):
                    log4brackets.log_task_deleted(tid, task.project_id, task.title)
                    del self.manager.tasks[tid]

        # Guardar cambios en YAML
        self.manager.save_topics()
        self.manager.save_tasks()
        self.manager.save_notes()
        self.manager.save_definitions()
        self.manager.save_people()
        self.manager.save_week(week)
        return True

    @staticmethod
    def _parse_task_status_and_title(raw_text: str, is_checkbox_done: bool) -> Tuple[str, str, str]:
        """
        Determina el estado ('done', 'cancelled', 'pending'), el título limpio y el tipo de tarea.
        Delega en BitacoraMarkdownParser.
        """
        from brackets.utils.bitacora_parser import BitacoraMarkdownParser
        return BitacoraMarkdownParser.parse_task_status_and_title(raw_text, is_checkbox_done)

    @classmethod
    def _parse_markdown_sections(cls, content: str) -> Dict[str, Any]:
        """Trocea el documento Markdown en sus secciones semánticas delegando en BitacoraMarkdownParser."""
        from brackets.utils.bitacora_parser import BitacoraMarkdownParser
        return BitacoraMarkdownParser.parse_sections(content)

    @staticmethod
    def _parse_notes_blocks(raw_lines: List[str]) -> List[Dict[str, Any]]:
        """Extrae bloques de notas con subencabezados delegando en BitacoraMarkdownParser."""
        from brackets.utils.bitacora_parser import BitacoraMarkdownParser
        return BitacoraMarkdownParser.parse_notes_blocks(raw_lines)

    def _reconcile_definitions(self, week: WeekSchedule, definitions_tuples: List[Tuple[str, str]]) -> None:
        """Reconcilia las definiciones encontradas en el Markdown con manager.definitions."""
        parsed_def_ids = []
        for def_id, url in definitions_tuples:
            def_obj = self.manager.ensure_definition(def_id=def_id, url=url)
            if def_obj and def_obj.id not in parsed_def_ids:
                parsed_def_ids.append(def_obj.id)

        if hasattr(week, "definition_ids"):
            week.definition_ids = parsed_def_ids

    def _auto_register_people(self, content: str, today_str: str) -> None:
        """Detecta automáticamente menciones @handle en la bitácora y asegura su alta en people.yaml."""
        mentions = set(re.findall(r'@([A-Za-zÁÉÍÓÚáéíóúñÑ0-9_-]+)', content))
        for m in sorted(mentions):
            self.manager.ensure_person(handle=m, created_at=today_str)

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

        from brackets.models.task_types import TaskTypeRegistry

        for item in task_tuples:
            if len(item) == 4:
                status, title, task_type, desc = item
            elif len(item) == 3:
                status, title, task_type = item
                desc = None
            else:
                status, title = item
                task_type = "task"
                desc = None

            proj_id, _ = BitacoraMarkdownParser.parse_project_tag(title)
            if proj_id:
                self.manager.ensure_project(proj_id)

            matched_task = None
            for t in current_tasks:
                if t.title == title or t.title.replace("~~", "").strip() == title:
                    matched_task = t
                    break
                _, clean_t = TaskTypeRegistry.detect_task_type_and_clean_title(t.title.replace("~~", "").strip())
                if clean_t == title:
                    matched_task = t
                    break
                _, clean_t_no_proj = BitacoraMarkdownParser.parse_project_tag(clean_t)
                _, clean_title_no_proj = BitacoraMarkdownParser.parse_project_tag(title)
                if clean_t_no_proj == clean_title_no_proj:
                    matched_task = t
                    break

            if matched_task:
                if proj_id and (not matched_task.project_id or matched_task.project_id == "POR_ASIGNAR"):
                    matched_task.project_id = proj_id

                if matched_task.title != title and TaskTypeRegistry.detect_task_type_and_clean_title(matched_task.title)[1] == title:
                    matched_task.title = title

                if task_type != "task":
                    matched_task.task_type = task_type

                if desc is not None:
                    matched_task.description = desc

                if "~~" in matched_task.title:
                    matched_task.title = title

                if status == "cancelled":
                    if matched_task.status != "cancelled":
                        matched_task.status = "cancelled"
                        matched_task.completed_at = None
                        try:
                            from brackets.worklog.log4brackets import log4brackets
                            log4brackets.log_task_cancelled(matched_task.id, matched_task.project_id, matched_task.title)
                        except Exception:
                            pass
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
                new_task = self.manager.create_task(
                    title=title,
                    project_id=proj_id,
                    is_week_task=True,
                    year=week.year,
                    week_num=week.week_number,
                    task_type=task_type,
                    status=status,
                    description=desc
                )
                if status == "done":
                    new_task.completed_at = today_str
                if new_task.id not in new_week_task_ids:
                    new_week_task_ids.append(new_task.id)

        week.week_task_ids = new_week_task_ids
        week.topics_task_ids = new_week_task_ids
        self.manager.sort_week_tasks_pending_first(week)

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

    def _find_task_for_day(
        self,
        day: DaySchedule,
        week: WeekSchedule,
        title: str,
        claimed_ids: Optional[Set[str]] = None
    ) -> Optional[Task]:
        """
        Busca inteligentemente una tarea con ese título priorizando:
        1. Tareas asignadas a este día concreto.
        2. Si coincide con una tarea recurrente activa, busca la instancia específica de este día
           o una instancia no reclamada/no asignada a otro día.
        3. Tareas en otros días de esta misma semana o en week_task_ids (siempre que no sean
           recurrentes y no estén ya reclamadas).
        4. Tareas pendientes/canceladas globales no resueltas (sin recurring_id).
        """
        from brackets.models.task_types import TaskTypeRegistry

        if claimed_ids is None:
            claimed_ids = set()

        clean_target = title.replace("~~", "").strip()
        _, clean_norm_target = TaskTypeRegistry.detect_task_type_and_clean_title(clean_target)
        _, clean_no_proj = BitacoraMarkdownParser.parse_project_tag(clean_norm_target)

        def _is_match(t: Optional[Task]) -> bool:
            if not t:
                return False
            if t.title == title or t.title.replace("~~", "").strip() == clean_target:
                return True
            _, clean_t = TaskTypeRegistry.detect_task_type_and_clean_title(t.title.replace("~~", "").strip())
            if clean_t == clean_norm_target:
                return True
            _, clean_t_no_proj = BitacoraMarkdownParser.parse_project_tag(clean_t)
            return clean_t_no_proj == clean_no_proj

        # 1. En este día
        for tid in day.task_ids:
            if tid in claimed_ids:
                continue
            t = self.manager.tasks.get(tid)
            if _is_match(t):
                return t

        # Comprobar si coincide con una recurrencia activa
        matching_rec = next(
            (r for r in self.manager.list_recurring_tasks(active_only=True)
             if _is_match(Task(id="", title=r.title))),
            None
        )

        if matching_rec:
            # 2a. Para recurrentes: buscar instancia ya existente para este día concreto
            for tid in day.task_ids:
                t = self.manager.tasks.get(tid)
                if t and t.recurring_id == matching_rec.id and tid not in claimed_ids:
                    return t

            # Buscar en manager.tasks una instancia libre que no esté reclamada
            # ni asignada a ningún otro día de la semana actual
            for t in self.manager.tasks.values():
                if t.recurring_id == matching_rec.id and t.id not in claimed_ids:
                    is_in_other_day = any(
                        t.id in od.task_ids for od in week.days if od.day_number != day.day_number
                    )
                    if not is_in_other_day:
                        return t

            # Si no hay instancia libre disponible para este día, retornar None
            # para que el reconciliador cree una instancia limpia exclusiva para este día
            return None

        # 3. En otros días de esta semana (SOLO para tareas no recurrentes movidas/arrastradas)
        for other_day in week.days:
            if other_day.day_number != day.day_number:
                for tid in other_day.task_ids:
                    if tid in claimed_ids:
                        continue
                    t = self.manager.tasks.get(tid)
                    if _is_match(t) and not t.is_recurring:
                        return t

        # 4. En tareas de la semana
        for tid in week.week_task_ids:
            if tid in claimed_ids:
                continue
            t = self.manager.tasks.get(tid)
            if _is_match(t) and not t.is_recurring:
                        return t

        # 5. Tarea pendiente o cancelada global no asignada a otra semana ni recurrente
        for t in self.manager.tasks.values():
            if t.id not in claimed_ids and _is_match(t) and not t.is_recurring and (t.is_pending or t.is_cancelled):
                return t

        return None

    def _reconcile_all_days(
        self,
        week: WeekSchedule,
        days_dict: Dict[int, List[Any]],
        days_meta: Dict[int, Dict[str, Optional[str]]],
        year: int,
        week_num: int,
        today_str: str
    ) -> None:
        """
        Reconcilia todos los días de la semana sincronizando tareas [x], [ ] y canceladas ~~...~~,
        evitando duplicidades entre días para una misma tarea arrastrada sin afectar recurrentes.
        Siempre coloca primero las tareas pendientes, luego completadas y canceladas.
        """
        from brackets.models.task_types import TaskTypeRegistry

        day_by_number: Dict[int, DaySchedule] = {d.day_number: d for d in week.days}

        # Asegurar días y actualizar metadatos (emoji y nota) desde el Markdown
        for day_num, meta in days_meta.items():
            if day_num not in day_by_number:
                new_day = DaySchedule(
                    day_number=day_num,
                    location_emoji=meta.get("emoji") or "🚗",
                    location_note=meta.get("note")
                )
                week.days.append(new_day)
                day_by_number[day_num] = new_day
            else:
                existing_day = day_by_number[day_num]
                if meta.get("emoji"):
                    existing_day.location_emoji = meta["emoji"]
                existing_day.location_note = meta.get("note")

        ordered_day_numbers = [d.day_number for d in week.days]

        pending_by_day: Dict[int, List[str]] = {d_num: [] for d_num in ordered_day_numbers}
        done_by_day: Dict[int, List[str]] = {d_num: [] for d_num in ordered_day_numbers}
        cancelled_by_day: Dict[int, List[str]] = {d_num: [] for d_num in ordered_day_numbers}
        task_types_by_title: Dict[str, str] = {}
        descriptions_by_title: Dict[str, Optional[str]] = {}

        for day_num in ordered_day_numbers:
            tuples = days_dict.get(day_num, [])
            for item in tuples:
                if len(item) == 4:
                    status, title, t_type, desc = item
                elif len(item) == 3:
                    status, title, t_type = item
                    desc = None
                else:
                    status, title = item
                    t_type = "task"
                    desc = None
                clean_title = title.strip()
                if not clean_title:
                    continue
                if desc is not None:
                    descriptions_by_title[clean_title] = desc
                if t_type and t_type != "task":
                    task_types_by_title[clean_title] = t_type

                if status == "done":
                    done_by_day[day_num].append(clean_title)
                elif status == "cancelled":
                    cancelled_by_day[day_num].append(clean_title)
                else:
                    pending_by_day[day_num].append(clean_title)

        # Identificar qué títulos corresponden a tareas recurrentes activas
        active_recs = self.manager.list_recurring_tasks(active_only=True)
        recurring_titles = set()
        for r in active_recs:
            recurring_titles.add(r.title)
            _, clean_r = TaskTypeRegistry.detect_task_type_and_clean_title(r.title)
            recurring_titles.add(clean_r)
            _, clean_r_no_proj = BitacoraMarkdownParser.parse_project_tag(clean_r)
            recurring_titles.add(clean_r_no_proj)

        def _is_recurring(t_title: str) -> bool:
            clean_t = t_title.replace("~~", "").strip()
            _, clean_norm = TaskTypeRegistry.detect_task_type_and_clean_title(clean_t)
            _, clean_no_proj = BitacoraMarkdownParser.parse_project_tag(clean_norm)
            return (
                clean_t in recurring_titles or
                clean_norm in recurring_titles or
                clean_no_proj in recurring_titles
            )

        # Deduplicar solo tareas PENDIENTES NO RECURRENTES si aparecen copiadas en múltiples días
        # (si el usuario arrastró o copió una tarea normal hacia adelante, mantenerla en el último día)
        non_recurring_pending_counts: Dict[str, List[int]] = {}
        for d_num in ordered_day_numbers:
            for t_title in pending_by_day[d_num]:
                if not _is_recurring(t_title):
                    non_recurring_pending_counts.setdefault(t_title, []).append(d_num)

        for t_title, days_with_title in non_recurring_pending_counts.items():
            if len(days_with_title) > 1:
                latest_day = days_with_title[-1]
                for d_num in days_with_title[:-1]:
                    pending_by_day[d_num] = [t for t in pending_by_day[d_num] if t != t_title]

        new_day_task_ids: Dict[int, List[str]] = {d_num: [] for d_num in ordered_day_numbers}
        claimed_ids: Set[str] = set()

        # 1. Reconciliar tareas PENDIENTES ([ ]) día por día
        for day_num in ordered_day_numbers:
            target_day = day_by_number.get(day_num)
            if not target_day:
                continue
            for title in pending_by_day[day_num]:
                if title in done_by_day[day_num] or title in cancelled_by_day[day_num]:
                    continue

                clean_target = title.replace("~~", "").strip()
                proj_tag, _ = BitacoraMarkdownParser.parse_project_tag(clean_target)
                if proj_tag:
                    self.manager.ensure_project(proj_tag)

                detected_type = task_types_by_title.get(title, "task")
                matched_task = self._find_task_for_day(target_day, week, title, claimed_ids=claimed_ids)
                if not matched_task:
                    rec_info = next(
                        (r for r in self.manager.list_recurring_tasks() if r.title == title or r.title == clean_target),
                        None
                    )
                    rec_type = rec_info.task_type if rec_info else None
                    final_task_type = detected_type if detected_type != "task" else (rec_type or "task")
                    desc_val = descriptions_by_title.get(title) or descriptions_by_title.get(clean_target)
                    matched_task = self.manager.create_task(
                        title=title,
                        project_id=proj_tag or (rec_info.project_id if rec_info else None),
                        year=year,
                        week_num=week_num,
                        day_number=day_num,
                        recurring_id=rec_info.id if rec_info else None,
                        task_type=final_task_type,
                        status="pending",
                        description=desc_val
                    )
                else:
                    desc_val = descriptions_by_title.get(title) or descriptions_by_title.get(clean_target)
                    if desc_val is not None:
                        matched_task.description = desc_val
                    if proj_tag and (not matched_task.project_id or matched_task.project_id == "POR_ASIGNAR"):
                        matched_task.project_id = proj_tag
                    if "~~" in matched_task.title:
                        matched_task.title = title
                    if matched_task.title != title and TaskTypeRegistry.detect_task_type_and_clean_title(matched_task.title)[1] == title:
                        matched_task.title = title
                    if detected_type != "task":
                        matched_task.task_type = detected_type
                    if matched_task.is_done or matched_task.is_cancelled:
                        matched_task.status = "pending"
                        matched_task.completed_at = None
                    if matched_task.recurring_id and matched_task.recurring_id in self.manager.recurring_tasks:
                        rec = self.manager.recurring_tasks[matched_task.recurring_id]
                        if rec.task_type != "task" and detected_type == "task":
                            matched_task.task_type = rec.task_type
                        if rec.project_id and (not matched_task.project_id or matched_task.project_id == "POR_ASIGNAR"):
                            matched_task.project_id = rec.project_id

                claimed_ids.add(matched_task.id)
                new_day_task_ids[day_num].append(matched_task.id)

        # 2. Reconciliar tareas COMPLETADAS ([x]) día por día
        for day_num in ordered_day_numbers:
            target_day = day_by_number.get(day_num)
            if not target_day:
                continue
            for title in done_by_day[day_num]:
                clean_target = title.replace("~~", "").strip()
                proj_tag, _ = BitacoraMarkdownParser.parse_project_tag(clean_target)
                if proj_tag:
                    self.manager.ensure_project(proj_tag)

                detected_type = task_types_by_title.get(title, "task")
                matched_task = self._find_task_for_day(target_day, week, title, claimed_ids=claimed_ids)
                if not matched_task:
                    rec_info = next(
                        (r for r in self.manager.list_recurring_tasks() if r.title == title or r.title == clean_target),
                        None
                    )
                    rec_type = rec_info.task_type if rec_info else None
                    final_task_type = detected_type if detected_type != "task" else (rec_type or "task")
                    desc_val = descriptions_by_title.get(title) or descriptions_by_title.get(clean_target)
                    matched_task = self.manager.create_task(
                        title=title,
                        project_id=proj_tag or (rec_info.project_id if rec_info else None),
                        year=year,
                        week_num=week_num,
                        day_number=day_num,
                        recurring_id=rec_info.id if rec_info else None,
                        task_type=final_task_type,
                        status="done",
                        description=desc_val
                    )
                else:
                    desc_val = descriptions_by_title.get(title) or descriptions_by_title.get(clean_target)
                    if desc_val is not None:
                        matched_task.description = desc_val
                    if proj_tag and (not matched_task.project_id or matched_task.project_id == "POR_ASIGNAR"):
                        matched_task.project_id = proj_tag
                    if "~~" in matched_task.title:
                        matched_task.title = title
                    if matched_task.title != title and TaskTypeRegistry.detect_task_type_and_clean_title(matched_task.title)[1] == title:
                        matched_task.title = title
                    if detected_type != "task":
                        matched_task.task_type = detected_type
                    matched_task.status = "done"
                    if not matched_task.completed_at:
                        matched_task.completed_at = today_str
                    if matched_task.recurring_id and matched_task.recurring_id in self.manager.recurring_tasks:
                        rec = self.manager.recurring_tasks[matched_task.recurring_id]
                        if rec.task_type != "task" and detected_type == "task":
                            matched_task.task_type = rec.task_type
                        if rec.project_id and (not matched_task.project_id or matched_task.project_id == "POR_ASIGNAR"):
                            matched_task.project_id = rec.project_id

                claimed_ids.add(matched_task.id)
                new_day_task_ids[day_num].append(matched_task.id)

        # 3. Reconciliar tareas CANCELADAS ([ ] ~~...~~) día por día
        for day_num in ordered_day_numbers:
            target_day = day_by_number.get(day_num)
            if not target_day:
                continue
            for title in cancelled_by_day[day_num]:
                clean_target = title.replace("~~", "").strip()
                proj_tag, _ = BitacoraMarkdownParser.parse_project_tag(clean_target)
                if proj_tag:
                    self.manager.ensure_project(proj_tag)

                detected_type = task_types_by_title.get(title, "task")
                matched_task = self._find_task_for_day(target_day, week, title, claimed_ids=claimed_ids)
                if not matched_task:
                    rec_info = next(
                        (r for r in self.manager.list_recurring_tasks() if r.title == title or r.title == clean_target),
                        None
                    )
                    rec_type = rec_info.task_type if rec_info else None
                    final_task_type = detected_type if detected_type != "task" else (rec_type or "task")
                    desc_val = descriptions_by_title.get(title) or descriptions_by_title.get(clean_target)
                    matched_task = self.manager.create_task(
                        title=title,
                        project_id=proj_tag or (rec_info.project_id if rec_info else None),
                        year=year,
                        week_num=week_num,
                        day_number=day_num,
                        recurring_id=rec_info.id if rec_info else None,
                        task_type=final_task_type,
                        status="cancelled",
                        description=desc_val
                    )
                else:
                    desc_val = descriptions_by_title.get(title) or descriptions_by_title.get(clean_target)
                    if desc_val is not None:
                        matched_task.description = desc_val
                    if proj_tag and (not matched_task.project_id or matched_task.project_id == "POR_ASIGNAR"):
                        matched_task.project_id = proj_tag
                    if "~~" in matched_task.title:
                        matched_task.title = title
                    if matched_task.title != title and TaskTypeRegistry.detect_task_type_and_clean_title(matched_task.title)[1] == title:
                        matched_task.title = title
                    if detected_type != "task":
                        matched_task.task_type = detected_type
                    if matched_task.status != "cancelled":
                        matched_task.status = "cancelled"
                        matched_task.completed_at = None
                        try:
                            from brackets.worklog.log4brackets import log4brackets
                            log4brackets.log_task_cancelled(matched_task.id, matched_task.project_id, matched_task.title)
                        except Exception:
                            pass
                    if matched_task.recurring_id and matched_task.recurring_id in self.manager.recurring_tasks:
                        rec = self.manager.recurring_tasks[matched_task.recurring_id]
                        if rec.task_type != "task" and detected_type == "task":
                            matched_task.task_type = rec.task_type
                        if rec.project_id and (not matched_task.project_id or matched_task.project_id == "POR_ASIGNAR"):
                            matched_task.project_id = rec.project_id

                claimed_ids.add(matched_task.id)
                new_day_task_ids[day_num].append(matched_task.id)

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
            self.manager.sort_day_tasks_pending_first(day)

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
