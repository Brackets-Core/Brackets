#!/usr/bin/env python3
"""
Motor de Renderizado: Traduce entidades relacionales (YAML) a Markdown oficial de Bitácoras.
"""

from __future__ import annotations
import re
from typing import Set, List
from brackets.models.entities import WeekSchedule, Task, Note, Definition
from brackets.managers.entity_manager import EntityManager
from brackets.utils.legacy_utils import safe_file_write


class BitacoraRenderer:
    """Renderiza estructuras de semana relacionales en archivos Markdown limpios."""

    @staticmethod
    def render_week(schedule: WeekSchedule, manager: EntityManager) -> str:
        """Genera el contenido Markdown completo para una semana."""
        lines: List[str] = []
        used_def_ids: Set[str] = set()

        # 1. Encabezado principal
        weight_str = f" {schedule.weight}" if schedule.weight else ""
        lines.append(f"# 🗓️Week {schedule.week_number}{weight_str}\n")

        # 2. Sección Topics
        lines.append("## 🎯Topics")
        if schedule.topic_ids:
            for top_id in schedule.topic_ids:
                topic = manager.topics.get(top_id)
                if not topic:
                    continue
                if topic.project_id:
                    lines.append(f"  - [{topic.project_id}] {topic.title}")
                else:
                    lines.append(f"  - {topic.title}")
                used_def_ids.update(BitacoraRenderer._extract_definition_ids(topic.title, manager))
        else:
            lines.append("  - ")
        lines.append("  ---\n")

        # 3. Sección Week Tasks
        lines.append("## 📋Week Tasks")
        if schedule.week_task_ids:
            # Siempre colocar primero las tareas pendientes
            sorted_week_task_ids = sorted(
                schedule.week_task_ids,
                key=lambda tid: (
                    0 if (manager.tasks.get(tid) and manager.tasks[tid].is_pending)
                    else (1 if (manager.tasks.get(tid) and manager.tasks[tid].is_done) else 2)
                )
            )
            for task_id in sorted_week_task_ids:
                task = manager.tasks.get(task_id)
                if not task:
                    continue
                lines.append(BitacoraRenderer._format_task_line(task))
                used_def_ids.update(BitacoraRenderer._extract_definition_ids(task.title, manager))
        else:
            lines.append("  - [ ] ")
        lines.append("  ---\n")

        # 4. Sección Notes
        lines.append("## 📝Notes")
        if schedule.note_ids:
            for note_id in schedule.note_ids:
                note = manager.notes.get(note_id)
                if not note:
                    continue
                if note.title:
                    lines.append(f"- ### {note.title}")
                    used_def_ids.update(BitacoraRenderer._extract_definition_ids(note.title, manager))
                    for content_line in note.content:
                        lines.append(f"  - {content_line}")
                        used_def_ids.update(BitacoraRenderer._extract_definition_ids(content_line, manager))
                else:
                    for content_line in note.content:
                        lines.append(f"- {content_line}")
                        used_def_ids.update(BitacoraRenderer._extract_definition_ids(content_line, manager))
        else:
            lines.append("  - ")
        lines.append("  ---\n")

        # 4. Secciones Diarias
        for day in schedule.days:
            note_suffix = f" ({day.location_note})" if day.location_note else ""
            lines.append(f"## {day.location_emoji}{day.day_number}{note_suffix}")
            if day.task_ids:
                seen_titles = set()
                # Siempre colocar primero las tareas pendientes
                sorted_day_task_ids = sorted(
                    day.task_ids,
                    key=lambda tid: (
                        0 if (manager.tasks.get(tid) and manager.tasks[tid].is_pending)
                        else (1 if (manager.tasks.get(tid) and manager.tasks[tid].is_done) else 2)
                    )
                )
                for task_id in sorted_day_task_ids:
                    task = manager.tasks.get(task_id)
                    if not task or task.title in seen_titles:
                        continue
                    seen_titles.add(task.title)
                    lines.append(BitacoraRenderer._format_task_line(task))
                    used_def_ids.update(BitacoraRenderer._extract_definition_ids(task.title, manager))
            else:
                lines.append("  - ")
            lines.append("")

        # 5. Sección Definiciones (al pie)
        # Siempre colocar por defecto la sección de definiciones al pie de la bitácora
        definitions_to_render: List[Definition] = []
        all_def_ids = set(used_def_ids)
        if hasattr(schedule, "definition_ids") and schedule.definition_ids:
            all_def_ids.update(schedule.definition_ids)

        for def_id in sorted(all_def_ids):
            # Normalizar para buscar en manager
            def_obj = manager.definitions.get(def_id)
            if def_obj:
                definitions_to_render.append(def_obj)

        lines.append("<!-- Definiciones -->")
        for d in definitions_to_render:
            lines.append(f"{d.id}: {d.url}")

        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _format_task_line(task: Task) -> str:
        """Formatea la línea de tarea según su estado e incluye premoji si corresponde."""
        from brackets.models.task_types import TaskTypeRegistry

        formatted_title = TaskTypeRegistry.format_title_with_premoji(task.title, task.task_type)
        if task.is_done:
            return f"  - [x] {formatted_title}"
        elif task.is_cancelled:
            # Si no tiene ya tildes en el título, envolver
            if "~~" not in formatted_title:
                return f"  - [ ] ~~{formatted_title}~~"
            return f"  - [ ] {formatted_title}"
        else:
            return f"  - [ ] {formatted_title}"

    @staticmethod
    def _extract_definition_ids(text: str, manager: Optional[EntityManager] = None) -> Set[str]:
        """Detecta automáticamente IDs de definición tipo [🎫TICKET], [📂LINK], o cualquier definición registrada."""
        found: Set[str] = set()
        candidates = re.findall(r'(\[[^\]\n]+\])', text)
        for cand in candidates:
            if manager and cand in manager.definitions:
                found.add(cand)
            elif re.search(r'[🎫🦒🤖📺📂📁🔗📊🛠️]', cand):
                found.add(cand)

        if manager:
            for def_id in manager.definitions.keys():
                if def_id in text:
                    found.add(def_id)
        return found

    @staticmethod
    def render_and_save_week(
        schedule: WeekSchedule,
        manager: EntityManager,
        target_filepath: str
    ) -> bool:
        """Renderiza y guarda el archivo Markdown en disco."""
        content = BitacoraRenderer.render_week(schedule, manager)
        return safe_file_write(target_filepath, content)

    @staticmethod
    def render_ideas(manager: EntityManager, project_id: Optional[str] = None) -> str:
        """Renderiza las ideas agrupadas por proyecto, sin IDs visibles y con formato limpio."""
        lines: List[str] = ["# 🧠Ideas\n"]
        ideas = manager.list_ideas(project_id=project_id)
        if not ideas:
            lines.append("## 💡Ideas\n  - [ ] \n")
            return "\n".join(lines).strip() + "\n"

        # Agrupar ideas por proyecto
        grouped: dict[str, list] = {}
        for idea in ideas:
            pid = idea.project_id or "GENERAL"
            grouped.setdefault(pid, []).append(idea)

        # Ordenar proyectos (GENERAL primero o alfabético)
        sorted_projects = sorted(grouped.keys(), key=lambda p: ("" if p == "GENERAL" else p))

        for pid in sorted_projects:
            lines.append(f"## 📁 {pid}")
            for idea in grouped[pid]:
                if idea.status == "accepted":
                    lines.append(f"- [x] {idea.title}")
                elif idea.status == "discarded":
                    if "~~" not in idea.title:
                        lines.append(f"- [ ] ~~{idea.title}~~")
                    else:
                        lines.append(f"- [ ] {idea.title}")
                else:
                    lines.append(f"- [ ] {idea.title}")

                for bullet in idea.content:
                    lines.append(f"  - {bullet}")
            lines.append("")

        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def render_and_save_ideas(
        manager: EntityManager,
        target_filepath: str,
        project_id: Optional[str] = None
    ) -> bool:
        """Renderiza y guarda el archivo de Ideas ([🧩GENERAL]🧠Ideas.md) en disco."""
        content = BitacoraRenderer.render_ideas(manager, project_id=project_id)
        return safe_file_write(target_filepath, content)

    @staticmethod
    def render_backlog(
        manager: EntityManager,
        scheduled_task_ids: Optional[Set[str]] = None
    ) -> str:
        """Renderiza las tareas de backlog (no agendadas) agrupadas por proyecto."""
        lines: List[str] = ["# ✅BackLog de Proyectos\n"]
        scheduled = scheduled_task_ids or set()
        
        # Tareas pendientes no asignadas
        backlog_tasks = [
            t for t in manager.tasks.values()
            if t.is_pending and t.id not in scheduled
        ]

        if not backlog_tasks:
            lines.append("## 📁 GENERAL\n- [ ] \n")
            return "\n".join(lines).strip() + "\n"

        # Agrupar por proyecto
        grouped: dict[str, list] = {}
        for task in backlog_tasks:
            pid = task.project_id or "GENERAL"
            grouped.setdefault(pid, []).append(task)

        sorted_projects = sorted(grouped.keys(), key=lambda p: ("" if p == "GENERAL" else p))

        for pid in sorted_projects:
            lines.append(f"## 📁 {pid}")
            for task in grouped[pid]:
                lines.append(f"- [ ] {task.title}")
            lines.append("")

        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def render_and_save_backlog(
        manager: EntityManager,
        target_filepath: str,
        scheduled_task_ids: Optional[Set[str]] = None
    ) -> bool:
        """Renderiza y guarda el archivo de Backlog ([📋PROJECTS]✅BackLog.md) en disco."""
        content = BitacoraRenderer.render_backlog(manager, scheduled_task_ids=scheduled_task_ids)
        return safe_file_write(target_filepath, content)

