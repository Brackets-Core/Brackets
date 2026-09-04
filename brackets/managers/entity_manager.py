#!/usr/bin/env python3
"""
Gestor de Entidades y Almacén de Datos Relacional para Brackets.
"""

from __future__ import annotations
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import yaml

from brackets.models.entities import Task, Note, Definition, Project, Idea, Topic, RecurringTask, WeekSchedule, DaySchedule
from brackets.worklog.log4brackets import log4brackets


class EntityManager:
    """Gestiona la persistencia y operaciones relacionales entre tablas de entidades y semanas."""

    def __init__(self, base_data_dir: str):
        self.base_data_dir = os.path.abspath(base_data_dir)
        vault_root = os.path.dirname(self.base_data_dir)
        log4brackets.set_vault_root(vault_root)
        self.tables_dir = os.path.join(self.base_data_dir, "tables")
        self.notes_dir = os.path.join(self.tables_dir, "notes")
        self.weeks_dir = os.path.join(self.base_data_dir, "weeks")

        os.makedirs(self.tables_dir, exist_ok=True)
        os.makedirs(self.notes_dir, exist_ok=True)
        os.makedirs(self.weeks_dir, exist_ok=True)

        self.projects: Dict[str, Project] = {}
        self.topics: Dict[str, Topic] = {}
        self.recurring_tasks: Dict[str, RecurringTask] = {}
        self.tasks: Dict[str, Task] = {}
        self.notes: Dict[str, Note] = {}
        self.ideas: Dict[str, Idea] = {}
        self.definitions: Dict[str, Definition] = {}
        self.weeks: Dict[str, WeekSchedule] = {}  # key: "YYYY-WXX"

        self.load_all()

    def _get_path(self, table_name: str) -> str:
        return os.path.join(self.tables_dir, f"{table_name}.yaml")

    def _get_week_path(self, year: int, week_num: int) -> str:
        return os.path.join(self.weeks_dir, f"{year}-W{week_num:02d}.yaml")

    def load_all(self) -> None:
        """Carga todas las tablas de entidades desde el disco."""
        self.load_projects()
        self.load_topics()
        self.load_recurring_tasks()
        self.load_definitions()
        self.load_tasks()
        self.load_notes()
        self.load_ideas()

    def load_recurring_tasks(self) -> None:
        path = self._get_path("recurring_tasks")
        self.recurring_tasks.clear()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            items = data.get("recurring_tasks", [])
            for item in items:
                r = RecurringTask.from_dict(item)
                if r.id:
                    self.recurring_tasks[r.id] = r

    def save_recurring_tasks(self) -> None:
        path = self._get_path("recurring_tasks")
        data = {"recurring_tasks": [r.to_dict() for r in self.recurring_tasks.values()]}
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    def load_topics(self) -> None:
        path = self._get_path("topics")
        self.topics.clear()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            items = data.get("topics", [])
            for item in items:
                t = Topic.from_dict(item)
                if t.id:
                    self.topics[t.id] = t

    def save_topics(self) -> None:
        path = self._get_path("topics")
        data = {"topics": [t.to_dict() for t in self.topics.values()]}
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    def load_ideas(self) -> None:
        path = self._get_path("ideas")
        self.ideas.clear()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            items = data.get("ideas", [])
            for item in items:
                i = Idea.from_dict(item)
                if i.id:
                    self.ideas[i.id] = i

    def save_ideas(self) -> None:
        path = self._get_path("ideas")
        data = {"ideas": [i.to_dict() for i in self.ideas.values()]}
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    def load_projects(self) -> None:
        path = self._get_path("projects")
        self.projects.clear()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            items = data.get("projects", [])
            for item in items:
                p = Project.from_dict(item)
                if p.id:
                    self.projects[p.id] = p

    def load_definitions(self) -> None:
        path = self._get_path("definitions")
        self.definitions.clear()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            items = data.get("definitions", [])
            for item in items:
                d = Definition.from_dict(item)
                if d.id:
                    self.definitions[d.id] = d

    def load_tasks(self) -> None:
        path = self._get_path("tasks")
        self.tasks.clear()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            items = data.get("tasks", [])
            for item in items:
                t = Task.from_dict(item)
                if t.id:
                    self.tasks[t.id] = t

    def load_notes(self) -> None:
        """Carga notas desde archivos mensuales en tables/notes/ o fallback a tables/notes.yaml."""
        import glob
        self.notes.clear()
        monthly_files = sorted(glob.glob(os.path.join(self.notes_dir, "*.yaml")))
        if monthly_files:
            for mpath in monthly_files:
                with open(mpath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                items = data.get("notes", [])
                for item in items:
                    n = Note.from_dict(item)
                    if n.id:
                        self.notes[n.id] = n
        else:
            # Fallback legacy si existe notes.yaml
            legacy_path = self._get_path("notes")
            if os.path.exists(legacy_path):
                with open(legacy_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                items = data.get("notes", [])
                for item in items:
                    n = Note.from_dict(item)
                    if n.id:
                        self.notes[n.id] = n

    def save_projects(self) -> None:
        path = self._get_path("projects")
        data = {"projects": [p.to_dict() for p in self.projects.values()]}
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    def save_definitions(self) -> None:
        path = self._get_path("definitions")
        data = {"definitions": [d.to_dict() for d in self.definitions.values()]}
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    def save_tasks(self) -> None:
        path = self._get_path("tasks")
        data = {"tasks": [t.to_dict() for t in self.tasks.values()]}
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    def save_notes(self) -> None:
        """Guarda notas agrupadas por mes en tables/notes/{YYYY}-{MM}.yaml y limpia archivos vacíos."""
        os.makedirs(self.notes_dir, exist_ok=True)
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for note in self.notes.values():
            m = note.month
            if not m and note.created_at and len(note.created_at) >= 7:
                m = note.created_at[:7]
            if not m:
                m = "general"
            grouped.setdefault(m, []).append(note.to_dict())

        # Guardar cada grupo mensual
        saved_files = set()
        for m_key, note_list in grouped.items():
            m_path = os.path.join(self.notes_dir, f"{m_key}.yaml")
            saved_files.add(os.path.normpath(m_path))
            with open(m_path, "w", encoding="utf-8") as f:
                yaml.dump({"notes": note_list}, f, allow_unicode=True, sort_keys=False)

        # Eliminar archivos mensuales antiguos que hayan quedado sin notas
        for fname in os.listdir(self.notes_dir):
            if fname.endswith(".yaml"):
                full_p = os.path.normpath(os.path.join(self.notes_dir, fname))
                if full_p not in saved_files:
                    try:
                        os.remove(full_p)
                    except Exception:
                        pass

    def load_week(self, year: int, week_num: int, reload: bool = False) -> Optional[WeekSchedule]:
        """Carga la estructura de una semana específica."""
        key = f"{year}-W{week_num:02d}"
        if not reload and key in self.weeks:
            return self.weeks[key]

        path = self._get_week_path(year, week_num)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        week = WeekSchedule.from_dict(data)
        self.weeks[key] = week
        return week

    def save_week(self, schedule: WeekSchedule) -> None:
        """Guarda la estructura de una semana en YAML."""
        key = f"{schedule.year}-W{schedule.week_number:02d}"
        path = self._get_week_path(schedule.year, schedule.week_number)
        data = schedule.to_dict()
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        self.weeks[key] = schedule

    def save_all(self) -> None:
        """Persiste todas las tablas en disco."""
        self.save_projects()
        self.save_topics()
        self.save_recurring_tasks()
        self.save_definitions()
        self.save_tasks()
        self.save_notes()
        self.save_ideas()
        for week in self.weeks.values():
            self.save_week(week)

    # -------------------------------------------------------------------------
    # Métodos de Negocio: Proyectos
    # -------------------------------------------------------------------------
    def list_projects(self) -> List[Project]:
        """Devuelve la lista de proyectos registrados ordenados por ID."""
        return sorted(self.projects.values(), key=lambda p: p.id)

    def ensure_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Project:
        """Garantiza que un proyecto exista en la base de datos."""
        pid = project_id.strip().upper().replace(" ", "_")
        if pid in self.projects:
            return self.projects[pid]

        pname = name.strip() if name else pid.replace("_", " ").title()
        project = Project(id=pid, name=pname, description=description)
        self.projects[pid] = project
        self.save_projects()
        return project

    # -------------------------------------------------------------------------
    # Métodos de Negocio: Topics
    # -------------------------------------------------------------------------
    def _generate_next_topic_id(self) -> str:
        """Calcula el siguiente ID de topic disponible evitando colisiones."""
        max_num = 0
        for top_id in self.topics.keys():
            match = re.search(r'\d+', top_id)
            if match:
                max_num = max(max_num, int(match.group()))
        return f"TOP-{max_num + 1:04d}"

    def list_topics(self, project_id: Optional[str] = None) -> List[Topic]:
        """Devuelve la lista de topics, opcionalmente filtrados por proyecto."""
        topics = list(self.topics.values())
        if project_id:
            topics = [t for t in topics if t.project_id == project_id]
        return sorted(topics, key=lambda t: t.id)

    def create_topic(
        self,
        title: str,
        project_id: str,
        topic_id: Optional[str] = None,
        status: str = "active",
        year: Optional[int] = None,
        week_num: Optional[int] = None
    ) -> Topic:
        """Crea un Topic general de trabajo y lo asocia a un proyecto y opcionalmente a una semana."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        if not topic_id:
            topic_id = self._generate_next_topic_id()

        # Asegurar que el proyecto existe
        self.ensure_project(project_id)

        topic = Topic(
            id=topic_id,
            title=title.strip(),
            project_id=project_id,
            status=status,
            created_at=today_str
        )
        self.topics[topic_id] = topic
        self.save_topics()

        if year and week_num:
            week = self.load_week(year, week_num)
            if week and topic_id not in week.topic_ids:
                week.topic_ids.append(topic_id)
                self.save_week(week)

        log4brackets.log_topic_created(topic.id, topic.project_id, topic.title)
        return topic

    def add_topic_to_week(self, week: WeekSchedule, topic_or_task_id: str) -> bool:
        """Añade un topic general (o tarea legacy) a la semana."""
        if topic_or_task_id in self.topics:
            if topic_or_task_id not in week.topic_ids:
                week.topic_ids.append(topic_or_task_id)
                self.save_week(week)
            return True
        elif topic_or_task_id in self.tasks:
            if topic_or_task_id not in week.week_task_ids:
                week.week_task_ids.append(topic_or_task_id)
            if topic_or_task_id not in week.topics_task_ids:
                week.topics_task_ids.append(topic_or_task_id)
            self.save_week(week)
            return True
        return False

    def add_week_task(self, week: WeekSchedule, task_id: str) -> None:
        """Añade una tarea a la lista de tareas de la semana (sin día concreto)."""
        if task_id not in week.week_task_ids:
            week.week_task_ids.append(task_id)
        if task_id not in week.topics_task_ids:
            week.topics_task_ids.append(task_id)
        self.save_week(week)

    def schedule_week_task_to_day(self, week: WeekSchedule, task_id: str, day_number: int) -> bool:
        """Mueve una tarea de la lista semanal a un día concreto de la semana."""
        target_day = next((d for d in week.days if d.day_number == day_number), None)
        if not target_day:
            return False

        if task_id in week.week_task_ids:
            week.week_task_ids.remove(task_id)
        if task_id in week.topics_task_ids:
            week.topics_task_ids.remove(task_id)

        if task_id not in target_day.task_ids:
            target_day.task_ids.append(task_id)

        self.save_week(week)
        return True

    # -------------------------------------------------------------------------
    # Métodos de Negocio: Tareas Recurrentes
    # -------------------------------------------------------------------------
    def _generate_next_recurring_id(self) -> str:
        """Calcula el siguiente ID de recurrencia disponible evitando colisiones."""
        max_num = 0
        for rid in self.recurring_tasks.keys():
            match = re.search(r'\d+', rid)
            if match:
                max_num = max(max_num, int(match.group()))
        return f"REC-{max_num + 1:04d}"

    def list_recurring_tasks(self, active_only: bool = False) -> List[RecurringTask]:
        """Devuelve la lista de tareas recurrentes ordenadas por ID."""
        tasks = list(self.recurring_tasks.values())
        if active_only:
            tasks = [t for t in tasks if t.active]
        return sorted(tasks, key=lambda t: t.id)

    def create_recurring_task(
        self,
        title: str,
        recurrence_type: str = "weekly_days",
        days_of_week: Optional[List[int]] = None,
        interval_weeks: int = 1,
        base_week: int = 1,
        day_of_week: int = 4,
        project_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        recurring_id: Optional[str] = None,
        task_type: str = "task"
    ) -> RecurringTask:
        """Registra una nueva tarea o reunión recurrente."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        if not recurring_id:
            recurring_id = self._generate_next_recurring_id()

        if topic_id and topic_id in self.topics and not project_id:
            project_id = self.topics[topic_id].project_id

        rec = RecurringTask(
            id=recurring_id,
            title=title.strip(),
            recurrence_type=recurrence_type,
            days_of_week=days_of_week or [],
            interval_weeks=interval_weeks,
            base_week=base_week,
            day_of_week=day_of_week,
            project_id=project_id,
            topic_id=topic_id,
            active=True,
            created_at=today_str,
            task_type=task_type
        )
        self.recurring_tasks[recurring_id] = rec
        self.save_recurring_tasks()
        return rec

    def toggle_recurring_task(self, recurring_id: str) -> Optional[RecurringTask]:
        """Alterna el estado activo/pausado de una tarea recurrente."""
        rec = self.recurring_tasks.get(recurring_id)
        if not rec:
            return None
        rec.active = not rec.active
        self.save_recurring_tasks()
        return rec

    def delete_recurring_task(self, recurring_id: str) -> bool:
        """Elimina la definición de una tarea recurrente."""
        if recurring_id in self.recurring_tasks:
            del self.recurring_tasks[recurring_id]
            self.save_recurring_tasks()
            return True
        return False

    def apply_recurring_tasks(self, week: WeekSchedule) -> int:
        """
        Evalúa e inyecta las tareas/reuniones recurrentes activas en la semana indicada.
        Reaprovecha instancias existentes de tareas recurrentes asignándoles la fecha exacta
        del día que aparecen en la bitácora y reseteando su estado a 'pending'.
        Para recurrencias multidía (como Daily S^3 en Lunes, Miércoles, Viernes),
        mantiene instancias distintas e independientes por cada día de la semana.
        Es totalmente idempotente: no duplica tareas si ya existen en ese día o semana.
        Devuelve el número de tareas inyectadas o reaprovechadas en la semana.
        """
        active_recs = self.list_recurring_tasks(active_only=True)
        if not active_recs or not week.days:
            return 0

        # Mapear cada day.day_number a su día de la semana (0=Lunes...6=Domingo)
        day_to_weekday: Dict[int, int] = {}
        for iso_wday in range(1, 8):
            try:
                dt = datetime.fromisocalendar(week.year, week.week_number, iso_wday)
                day_to_weekday[dt.day] = dt.weekday()
            except Exception:
                pass

        weekday_to_day_schedule: Dict[int, DaySchedule] = {}
        for idx, d in enumerate(week.days):
            wday = day_to_weekday.get(d.day_number, idx % 7)
            weekday_to_day_schedule[wday] = d

        injected_count = 0

        for rec in active_recs:
            # Obtener todas las instancias de tareas existentes asociadas a esta recurrencia
            existing_rec_tasks = [
                t for t in self.tasks.values()
                if t.recurring_id == rec.id or (not t.recurring_id and t.title == rec.title)
            ]
            existing_rec_tasks.sort(key=lambda x: x.id)

            # Asegurar que todas tengan el recurring_id seteado
            for t in existing_rec_tasks:
                if not t.recurring_id:
                    t.recurring_id = rec.id

            if rec.recurrence_type == "weekly_days":
                # Días específicos (ej: [0, 2, 4] para Lunes, Miércoles, Viernes)
                for idx, target_wday in enumerate(rec.days_of_week):
                    target_day = weekday_to_day_schedule.get(target_wday)
                    if not target_day:
                        continue

                    try:
                        target_date = datetime.fromisocalendar(week.year, week.week_number, target_wday + 1).strftime("%Y-%m-%d")
                    except Exception:
                        target_date = datetime.now().strftime("%Y-%m-%d")

                    # Comprobar si ya existe en target_day
                    already_in_day = any(
                        (self.tasks.get(tid) and (self.tasks[tid].recurring_id == rec.id or self.tasks[tid].title == rec.title))
                        for tid in target_day.task_ids
                    )
                    if already_in_day:
                        continue

                    # REAPROVECHAR instancia existente correspondiente al slot `idx`
                    if idx < len(existing_rec_tasks):
                        task = existing_rec_tasks[idx]
                        # Si esta instancia ya está en target_day, no hacer nada
                        if task.id in target_day.task_ids:
                            continue
                        # Si esta instancia ya fue asignada a otro día de la semana (por haber sido movida),
                        # no duplicarla ni reinyectarla en target_day
                        if any(task.id in d.task_ids for d in week.days):
                            continue

                        task.status = "pending"
                        task.completed_at = None
                        task.created_at = target_date
                        task.task_type = rec.task_type
                        if rec.project_id and (not task.project_id or task.project_id == "POR_ASIGNAR"):
                            task.project_id = rec.project_id
                        task.topic_id = rec.topic_id
                        task.recurring_id = rec.id
                        target_day.task_ids.append(task.id)
                        injected_count += 1
                    else:
                        new_task = self.create_task(
                            title=rec.title,
                            project_id=rec.project_id,
                            topic_id=rec.topic_id,
                            year=week.year,
                            week_num=week.week_number,
                            day_number=target_day.day_number,
                            recurring_id=rec.id,
                            task_type=rec.task_type
                        )
                        new_task.created_at = target_date
                        existing_rec_tasks.append(new_task)
                        injected_count += 1

            elif rec.recurrence_type == "interval_weeks":
                # Cada N semanas (ej: cada 4 semanas los viernes o cada 2 semanas los martes)
                if (week.week_number - rec.base_week) % rec.interval_weeks == 0:
                    target_day = weekday_to_day_schedule.get(rec.day_of_week)
                    if not target_day:
                        target_day = week.days[-1]

                    try:
                        target_date = datetime.fromisocalendar(week.year, week.week_number, rec.day_of_week + 1).strftime("%Y-%m-%d")
                    except Exception:
                        target_date = datetime.now().strftime("%Y-%m-%d")

                    already_in_day = any(
                        (self.tasks.get(tid) and (self.tasks[tid].recurring_id == rec.id or self.tasks[tid].title == rec.title))
                        for tid in target_day.task_ids
                    )
                    if already_in_day:
                        continue

                    if existing_rec_tasks:
                        task = existing_rec_tasks[0]
                        # Si ya está asignada en cualquier día de la semana, no duplicar
                        if any(task.id in d.task_ids for d in week.days):
                            continue

                        task.status = "pending"
                        task.completed_at = None
                        task.created_at = target_date
                        task.task_type = rec.task_type
                        if rec.project_id and (not task.project_id or task.project_id == "POR_ASIGNAR"):
                            task.project_id = rec.project_id
                        task.topic_id = rec.topic_id
                        task.recurring_id = rec.id
                        target_day.task_ids.append(task.id)
                        injected_count += 1
                    else:
                        new_task = self.create_task(
                            title=rec.title,
                            project_id=rec.project_id,
                            topic_id=rec.topic_id,
                            year=week.year,
                            week_num=week.week_number,
                            day_number=target_day.day_number,
                            recurring_id=rec.id,
                            task_type=rec.task_type
                        )
                        new_task.created_at = target_date
                        existing_rec_tasks.append(new_task)
                        injected_count += 1

            elif rec.recurrence_type == "week_tasks":
                # Cada N semanas en Tareas de la Semana (sin día fijo)
                if (week.week_number - rec.base_week) % rec.interval_weeks == 0:
                    try:
                        target_date = datetime.fromisocalendar(week.year, week.week_number, 1).strftime("%Y-%m-%d")
                    except Exception:
                        target_date = datetime.now().strftime("%Y-%m-%d")

                    already_in_week = any(
                        (self.tasks.get(tid) and (self.tasks[tid].recurring_id == rec.id or self.tasks[tid].title == rec.title))
                        for tid in week.week_task_ids
                    )
                    if already_in_week:
                        continue

                    if existing_rec_tasks:
                        task = existing_rec_tasks[0]
                        if task.id in week.week_task_ids or any(task.id in d.task_ids for d in week.days):
                            continue

                        task.status = "pending"
                        task.completed_at = None
                        task.created_at = target_date
                        task.task_type = rec.task_type
                        if rec.project_id and (not task.project_id or task.project_id == "POR_ASIGNAR"):
                            task.project_id = rec.project_id
                        task.topic_id = rec.topic_id
                        task.recurring_id = rec.id
                        week.week_task_ids.append(task.id)
                        injected_count += 1
                    else:
                        new_task = self.create_task(
                            title=rec.title,
                            project_id=rec.project_id,
                            topic_id=rec.topic_id,
                            is_week_task=True,
                            year=week.year,
                            week_num=week.week_number,
                            recurring_id=rec.id,
                            task_type=rec.task_type
                        )
                        new_task.created_at = target_date
                        existing_rec_tasks.append(new_task)
                        injected_count += 1

        if injected_count > 0:
            self.save_tasks()
            self.save_week(week)

        return injected_count

    def deduplicate_tasks(self) -> Tuple[int, int]:
        """
        Desduplica tareas en tasks.yaml y reasigna los IDs en todos los archivos de semanas.
        - Para tareas recurrentes multidía (como Daily S^3 con N días en la semana):
          mantiene exactamente N instancias canónicas (1 por slot de día) y fusiona las demás.
        - Para tareas recurrentes de 1 día: mantiene 1 instancia canónica.
        - Para tareas no recurrentes repetidas por arrastre: mantiene 1 instancia canónica
          (priorizando la que esté completada, con proyecto asignado o con menor ID).
        - Reemplaza las referencias a tareas redundantes en data/weeks/*.yaml.
        - Elimina las entidades duplicadas de self.tasks y guarda cambios en disco.
        Devuelve (total_reemplazos, total_tareas_eliminadas).
        """
        replacement_map: Dict[str, str] = {}

        # 1. Tareas Recurrentes
        for rec in self.recurring_tasks.values():
            if rec.recurrence_type == "weekly_days":
                k = len(rec.days_of_week) if rec.days_of_week else 1
            else:
                k = 1

            matching = [
                t for t in self.tasks.values()
                if t.recurring_id == rec.id or (not t.recurring_id and t.title == rec.title)
            ]
            matching.sort(key=lambda x: (0 if x.recurring_id == rec.id else 1, x.id))

            canonicals = matching[:k]
            for c in canonicals:
                c.recurring_id = rec.id
                if rec.project_id and (not c.project_id or c.project_id == "POR_ASIGNAR"):
                    c.project_id = rec.project_id

            for idx, extra in enumerate(matching[k:]):
                slot_idx = idx % k
                canonical_slot = canonicals[slot_idx]
                replacement_map[extra.id] = canonical_slot.id
                if canonical_slot.is_pending and (extra.is_done or extra.is_cancelled):
                    canonical_slot.status = extra.status
                    canonical_slot.completed_at = extra.completed_at

        # 2. Tareas No Recurrentes
        from collections import defaultdict
        non_rec_tasks = [
            t for t in self.tasks.values()
            if t.id not in replacement_map and not t.recurring_id
        ]
        groups = defaultdict(list)
        for t in non_rec_tasks:
            key = t.title.strip()
            groups[key].append(t)

        for title, group in groups.items():
            if len(group) > 1:
                group.sort(key=lambda x: (
                    0 if x.is_done else 1,
                    0 if x.project_id and x.project_id != "POR_ASIGNAR" else 1,
                    x.id
                ))
                canonical = group[0]
                if not canonical.project_id or canonical.project_id == "POR_ASIGNAR":
                    for other in group[1:]:
                        if other.project_id and other.project_id != "POR_ASIGNAR":
                            canonical.project_id = other.project_id
                            break

                for extra in group[1:]:
                    replacement_map[extra.id] = canonical.id

        if not replacement_map:
            return (0, 0)

        # 3. Reasignar en todos los archivos de semanas
        import glob
        week_files = sorted(glob.glob(os.path.join(self.weeks_dir, "*.yaml")))
        for wpath in week_files:
            match = re.search(r'(\d{4})-W(\d{2})\.yaml$', os.path.basename(wpath))
            if not match:
                continue
            year = int(match.group(1))
            week_num = int(match.group(2))
            week = self.load_week(year, week_num, reload=True)
            if not week:
                continue

            changed = False
            new_week_task_ids = []
            for tid in week.week_task_ids:
                new_id = replacement_map.get(tid, tid)
                if new_id not in new_week_task_ids:
                    new_week_task_ids.append(new_id)
                if new_id != tid:
                    changed = True
            week.week_task_ids = new_week_task_ids

            new_topics_task_ids = []
            for tid in week.topics_task_ids:
                new_id = replacement_map.get(tid, tid)
                if new_id not in new_topics_task_ids:
                    new_topics_task_ids.append(new_id)
                if new_id != tid:
                    changed = True
            week.topics_task_ids = new_topics_task_ids

            for d in week.days:
                new_day_task_ids = []
                for tid in d.task_ids:
                    new_id = replacement_map.get(tid, tid)
                    if new_id not in new_day_task_ids:
                        new_day_task_ids.append(new_id)
                    if new_id != tid:
                        changed = True
                d.task_ids = new_day_task_ids

            if changed:
                self.save_week(week)

        # 4. Eliminar tareas obsoletas de self.tasks
        removed_count = 0
        for old_id, canonical_id in replacement_map.items():
            if old_id != canonical_id and old_id in self.tasks:
                del self.tasks[old_id]
                removed_count += 1

        self.save_tasks()
        return (len(replacement_map), removed_count)

    # -------------------------------------------------------------------------
    # Métodos de Negocio: Tareas
    # -------------------------------------------------------------------------
    def _generate_next_task_id(self) -> str:
        """Calcula el siguiente ID de tarea disponible evitando colisiones."""
        max_num = 0
        for tid in self.tasks.keys():
            match = re.search(r'\d+', tid)
            if match:
                max_num = max(max_num, int(match.group()))
        return f"TSK-{max_num + 1:04d}"

    def _generate_next_note_id(self) -> str:
        """Calcula el siguiente ID de nota disponible evitando colisiones."""
        max_num = 0
        for nid in self.notes.keys():
            match = re.search(r'\d+', nid)
            if match:
                max_num = max(max_num, int(match.group()))
        return f"NOTE-{max_num + 1:04d}"

    def create_task(
        self,
        title: str,
        status: str = "pending",
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        year: Optional[int] = None,
        week_num: Optional[int] = None,
        day_number: Optional[int] = None,
        is_topic: bool = False,
        topic_id: Optional[str] = None,
        is_week_task: bool = False,
        recurring_id: Optional[str] = None,
        task_type: str = "task"
    ) -> Task:
        """Crea una tarea, la registra en la tabla y opcionalmente la vincula a la semana/día."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        if not task_id:
            task_id = self._generate_next_task_id()

        # Si se especificó topic_id, heredar su project_id si no vino explícito
        if topic_id and topic_id in self.topics:
            if not project_id:
                project_id = self.topics[topic_id].project_id

        task = Task(
            id=task_id,
            title=title.strip(),
            status=status,
            created_at=today_str,
            completed_at=today_str if status == "done" else None,
            project_id=project_id,
            topic_id=topic_id,
            recurring_id=recurring_id,
            task_type=task_type
        )

        self.tasks[task_id] = task
        self.save_tasks()

        # Vincular a la semana si se especifican los parámetros
        if year and week_num:
            week = self.load_week(year, week_num)
            if week:
                if is_week_task or is_topic:
                    if task_id not in week.week_task_ids:
                        week.week_task_ids.append(task_id)
                    if task_id not in week.topics_task_ids:
                        week.topics_task_ids.append(task_id)
                elif day_number:
                    for d in week.days:
                        if d.day_number == day_number:
                            if task_id not in d.task_ids:
                                d.task_ids.append(task_id)
                            break
                self.save_week(week)

        log4brackets.log_task_created(task.id, task.project_id, task.title, day_number=day_number)
        return task

    def toggle_task(self, task_id: str) -> Optional[Task]:
        """Alterna el estado de una tarea entre 'pending' y 'done', o reactiva si estaba 'cancelled'."""
        task = self.tasks.get(task_id)
        if not task:
            return None

        today_str = datetime.now().strftime("%Y-%m-%d")
        if task.is_done:
            task.status = "pending"
            task.completed_at = None
            self.save_tasks()
            log4brackets.log_task_reopened(task.id, task.project_id, task.title)
        elif task.is_cancelled:
            task.status = "pending"
            task.completed_at = None
            self.save_tasks()
            log4brackets.log_task_reopened(task.id, task.project_id, task.title)
        else:
            task.status = "done"
            task.completed_at = today_str
            self.save_tasks()
            log4brackets.log_task_completed(task.id, task.project_id, task.title)

        return task

    def cancel_task(self, task_id: str) -> Optional[Task]:
        """Marca una tarea como 'cancelled' (tachada en la bitácora) sin eliminarla de la tabla de tareas."""
        task = self.tasks.get(task_id)
        if not task:
            return None

        task.status = "cancelled"
        task.completed_at = None
        self.save_tasks()
        log4brackets.log_task_cancelled(task.id, task.project_id, task.title)
        return task

    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Optional[Task]:
        """Actualiza título y/o proyecto de una tarea existente."""
        task = self.tasks.get(task_id)
        if not task:
            return None
        if title is not None and title.strip():
            task.title = title.strip()
        if project_id is not None and project_id.strip():
            self.ensure_project(project_id.strip())
            task.project_id = project_id.strip()
        self.save_tasks()
        return task

    def delete_task(
        self,
        task_id: str,
        year: Optional[int] = None,
        week_num: Optional[int] = None,
        day_number: Optional[int] = None
    ) -> bool:
        """Elimina una tarea de la tabla o desvincula del día de la semana."""
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]

        # Desvincular de la semana si existe
        if year and week_num:
            week = self.load_week(year, week_num)
            if week:
                if task_id in week.topics_task_ids:
                    week.topics_task_ids.remove(task_id)
                if day_number:
                    for d in week.days:
                        if d.day_number == day_number and task_id in d.task_ids:
                            d.task_ids.remove(task_id)
                self.save_week(week)

        log4brackets.log_task_deleted(task.id, task.project_id, task.title)
        del self.tasks[task_id]
        self.save_tasks()
        return True

    # -------------------------------------------------------------------------
    # Métodos de Negocio: Definiciones
    # -------------------------------------------------------------------------
    def ensure_definition(
        self,
        def_id: str,
        url: str,
        title: Optional[str] = None
    ) -> Definition:
        """Garantiza que una definición exista en la tabla."""
        if def_id in self.definitions:
            existing = self.definitions[def_id]
            return existing

        def_obj = Definition(id=def_id, url=url, title=title)
        self.definitions[def_id] = def_obj
        self.save_definitions()
        return def_obj

    def ensure_jira_definition(
        self,
        ticket_code: str,
        base_url: str = "https://mangospain.atlassian.net/browse/"
    ) -> Definition:
        """Normaliza un ticket de Jira (ej: ATLM-12703 -> [🎫ATLM-12703]) y asegura su URL."""
        clean_code = ticket_code.replace("[", "").replace("]", "").replace("🎫", "").strip()
        formatted_id = f"[🎫{clean_code}]"
        full_url = f"{base_url}{clean_code}"
        return self.ensure_definition(def_id=formatted_id, url=full_url, title=clean_code)

    # -------------------------------------------------------------------------
    # Métodos de Negocio: Notas
    # -------------------------------------------------------------------------
    def add_note(
        self,
        content: List[str] | str,
        year: int,
        week_num: int,
        note_id: Optional[str] = None,
        title: Optional[str] = None,
        month: Optional[str] = None,
        project_id: Optional[str] = None,
        topic_id: Optional[str] = None
    ) -> Note:
        """Crea una nota estructurada con título y viñetas, asociada a la semana y mes indicado."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        if not note_id:
            note_id = self._generate_next_note_id()

        if isinstance(content, str):
            content_list = [content] if content else []
        else:
            content_list = list(content)

        if not month:
            week = self.load_week(year, week_num)
            if week and week.month:
                month = f"{year}-{week.month:02d}"
            else:
                month = f"{year}-{datetime.now().month:02d}"

        # Si se especificó topic_id y no viene project_id, heredar del topic
        if topic_id and topic_id in self.topics:
            if not project_id:
                project_id = self.topics[topic_id].project_id

        note = Note(
            id=note_id,
            title=title.strip() if title else None,
            content=content_list,
            created_at=today_str,
            month=month,
            week=week_num,
            project_id=project_id,
            topic_id=topic_id
        )
        self.notes[note_id] = note
        self.save_notes()

        week = self.load_week(year, week_num)
        if week:
            if note_id not in week.note_ids:
                week.note_ids.append(note_id)
            self.save_week(week)

        log4brackets.log_note_created(note.id, note.project_id, note.title or "Nota sin título", topic_id=note.topic_id)
        return note

    def list_notes(
        self,
        month: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> List[Note]:
        """Devuelve la lista de notas filtradas por mes y/o proyecto."""
        notes = list(self.notes.values())
        if month:
            notes = [n for n in notes if n.month == month]
        if project_id:
            notes = [n for n in notes if n.project_id == project_id]
        return sorted(notes, key=lambda n: n.id)

    def search_notes(
        self,
        query: Optional[str] = None,
        month: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> List[Note]:
        """Busca notas por texto (título y viñetas), mes y/o proyecto."""
        notes = self.list_notes(month=month, project_id=project_id)
        if not query:
            return notes

        q = query.strip().lower()
        matched = []
        for n in notes:
            # Buscar en título
            if n.title and q in n.title.lower():
                matched.append(n)
                continue
            # Buscar en viñetas de contenido
            found_in_content = any(q in line.lower() for line in n.content)
            if found_in_content:
                matched.append(n)
                continue
            # Buscar en ID
            if q in n.id.lower():
                matched.append(n)

        return matched

    def update_note(
        self,
        note_id: str,
        title: Optional[str] = None,
        content: Optional[List[str]] = None,
        project_id: Optional[str] = None,
        month: Optional[str] = None
    ) -> Optional[Note]:
        """Actualiza una nota existente y persiste en su archivo mensual correspondiente."""
        note = self.notes.get(note_id)
        if not note:
            return None

        if title is not None:
            note.title = title.strip() if title.strip() else None
        if content is not None:
            note.content = list(content)
        if project_id is not None:
            note.project_id = project_id if project_id != "" else None
        if month is not None and month.strip():
            note.month = month.strip()

        self.save_notes()
        return note

    def delete_note_complete(self, note_id: str) -> bool:
        """Elimina completamente una nota de las tablas y desvincula de las semanas cargadas."""
        if note_id not in self.notes:
            return False

        del self.notes[note_id]
        self.save_notes()

        # Desvincular de semanas si está en memoria o en disco
        for w in self.weeks.values():
            if note_id in w.note_ids:
                w.note_ids.remove(note_id)
                self.save_week(w)

        return True

    # -------------------------------------------------------------------------
    # Métodos de Negocio: Ideas
    # -------------------------------------------------------------------------
    def _generate_next_idea_id(self) -> str:
        """Calcula el siguiente ID de idea disponible evitando colisiones."""
        max_num = 0
        for iid in self.ideas.keys():
            match = re.search(r'\d+', iid)
            if match:
                max_num = max(max_num, int(match.group()))
        return f"IDEA-{max_num + 1:04d}"

    def create_idea(
        self,
        title: str,
        content: Optional[List[str] | str] = None,
        project_id: Optional[str] = None,
        status: str = "evaluating",
        idea_id: Optional[str] = None
    ) -> Idea:
        """Crea y persiste una nueva Idea / Propuesta."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        if not idea_id:
            idea_id = self._generate_next_idea_id()

        if isinstance(content, str):
            content_list = [content] if content else []
        elif content is None:
            content_list = []
        else:
            content_list = list(content)

        idea = Idea(
            id=idea_id,
            title=title.strip(),
            content=content_list,
            status=status,
            created_at=today_str,
            project_id=project_id
        )
        self.ideas[idea_id] = idea
        self.save_ideas()
        return idea

    def update_idea_status(self, idea_id: str, new_status: str) -> Optional[Idea]:
        """Actualiza el estado de una idea ('evaluating', 'accepted', 'discarded')."""
        idea = self.ideas.get(idea_id)
        if not idea:
            return None
        idea.status = new_status
        self.save_ideas()
        return idea

    def list_ideas(self, project_id: Optional[str] = None) -> List[Idea]:
        """Lista ideas opcionalmente filtradas por proyecto."""
        ideas = list(self.ideas.values())
        if project_id is not None:
            ideas = [i for i in ideas if i.project_id == project_id]
        return sorted(ideas, key=lambda i: i.id)

    # -------------------------------------------------------------------------
    # Métodos de Negocio: Backlog y Planificación
    # -------------------------------------------------------------------------
    def list_backlog_tasks(self, project_id: Optional[str] = None, pending_only: bool = True) -> List[Task]:
        """Devuelve las tareas registradas, filtrables por proyecto y estado pendiente."""
        tasks = list(self.tasks.values())
        if project_id is not None:
            tasks = [t for t in tasks if t.project_id == project_id]
        if pending_only:
            tasks = [t for t in tasks if t.is_pending]
        return sorted(tasks, key=lambda t: t.id)

    def assign_task_to_day(
        self,
        task_id: str,
        year: int,
        week_num: int,
        day_number: int
    ) -> bool:
        """Asigna una tarea existente al día especificado de una semana y persiste."""
        if task_id not in self.tasks:
            return False

        week = self.load_week(year, week_num)
        if not week:
            return False

        target_day: Optional[DaySchedule] = None
        for d in week.days:
            if d.day_number == day_number:
                target_day = d
                break

        if not target_day:
            return False

        if task_id not in target_day.task_ids:
            target_day.task_ids.append(task_id)
            self.save_week(week)
            return True

        return True

    def get_project_stats(self, project_id: str) -> Dict[str, int]:
        """Calcula al vuelo estadísticas de tareas e ideas de un proyecto."""
        tasks = [t for t in self.tasks.values() if t.project_id == project_id]
        ideas = [i for i in self.ideas.values() if i.project_id == project_id]
        total = len(tasks)
        done = len([t for t in tasks if t.is_done])
        pending = len([t for t in tasks if t.is_pending])
        evaluating_ideas = len([i for i in ideas if i.status == "evaluating"])
        return {
            "total_tasks": total,
            "done_tasks": done,
            "pending_tasks": pending,
            "total_ideas": len(ideas),
            "evaluating_ideas": evaluating_ideas
        }

    # -------------------------------------------------------------------------
    # Métodos de Ciclo de Vida y Arrastre (Rollover)
    # -------------------------------------------------------------------------
    def assign_topic_to_day(self, week: WeekSchedule, task_id: str, day_number: int) -> bool:
        """Asigna un topic semanal a un día concreto de la semana."""
        target_day = next((d for d in week.days if d.day_number == day_number), None)
        if not target_day:
            return False
        if task_id not in target_day.task_ids:
            target_day.task_ids.append(task_id)
            self.save_week(week)
        return True

    def rollover_day_tasks(self, week: WeekSchedule, current_day_number: int) -> int:
        """
        Arrastra tareas pendientes de días previos de la misma semana al día actual,
        eliminándolas del día anterior para que no queden duplicadas.
        PROTECCIÓN: No arrastra tareas automáticamente hacia días de guardia o intervención,
        ni arrastra tareas propias de una intervención hacia días regulares.
        Devuelve el número de tareas arrastradas.
        """
        current_day = next((d for d in week.days if d.day_number == current_day_number), None)
        if not current_day:
            return 0

        # Si el día actual es de intervención o guardia, NO recibir tareas automáticas
        if current_day.is_intervention:
            return 0

        # Encontrar el índice del día actual en la semana
        day_indices = {d.day_number: idx for idx, d in enumerate(week.days)}
        curr_idx = day_indices.get(current_day_number, -1)
        if curr_idx <= 0:
            return 0

        rolled_count = 0
        for i in range(curr_idx):
            prev_day = week.days[i]
            # Si el día previo fue de intervención/guardia, sus tareas son específicas de esa intervención y no se arrastran
            if prev_day.is_intervention:
                continue

            for tid in list(prev_day.task_ids):
                task = self.tasks.get(tid)
                if task and task.is_pending:
                    # Las reuniones y tareas recurrentes pertenecen a su día y no se arrastran a días posteriores
                    if task.is_meeting or task.is_recurring:
                        continue
                    prev_day.task_ids.remove(tid)
                    if tid not in current_day.task_ids:
                        current_day.task_ids.append(tid)
                    rolled_count += 1

        if rolled_count > 0:
            self.save_week(week)
        return rolled_count

    def add_day_to_week(
        self,
        week: WeekSchedule,
        day_number: int,
        location_emoji: str = "🛠️",
        location_note: Optional[str] = "Intervención"
    ) -> DaySchedule:
        """
        Añade un día adicional (ej: sábado o domingo de guardia/intervención) a la semana.
        Si el día ya existe, devuelve el DaySchedule existente.
        """
        existing = next((d for d in week.days if d.day_number == day_number), None)
        if existing:
            return existing

        new_day = DaySchedule(
            day_number=day_number,
            location_emoji=location_emoji,
            location_note=location_note,
            task_ids=[]
        )
        week.days.append(new_day)
        week.days.sort(key=lambda d: d.day_number)
        self.save_week(week)
        return new_day

    def get_scheduled_task_ids(self) -> Set[str]:
        """Devuelve el conjunto de todos los IDs de tareas asignados a alguna semana/día cargado."""
        scheduled: Set[str] = set()
        # Escanear archivos de semanas si existen
        if os.path.exists(self.weeks_dir):
            for fname in os.listdir(self.weeks_dir):
                if fname.endswith(".yaml"):
                    try:
                        wpath = os.path.join(self.weeks_dir, fname)
                        with open(wpath, "r", encoding="utf-8") as f:
                            data = yaml.safe_load(f)
                        if data:
                            for tid in data.get("week_task_ids", []):
                                scheduled.add(tid)
                            for tid in data.get("topics_task_ids", []):
                                scheduled.add(tid)
                            for d in data.get("days", []):
                                for tid in d.get("task_ids", []):
                                    scheduled.add(tid)
                    except Exception:
                        pass
        # Añadir las que estén en memoria
        for w in self.weeks.values():
            scheduled.update(w.week_task_ids)
            scheduled.update(w.topics_task_ids)
            for d in w.days:
                scheduled.update(d.task_ids)
        return scheduled

    def is_task_scheduled_in_other_weeks(self, task_id: str, exclude_year: int, exclude_week_num: int) -> bool:
        """Comprueba si una tarea está asignada a alguna semana distinta de la indicada."""
        target_filename = f"{exclude_year}-W{exclude_week_num:02d}.yaml"
        if os.path.exists(self.weeks_dir):
            for fname in os.listdir(self.weeks_dir):
                if fname.endswith(".yaml") and fname != target_filename:
                    try:
                        wpath = os.path.join(self.weeks_dir, fname)
                        with open(wpath, "r", encoding="utf-8") as f:
                            data = yaml.safe_load(f)
                        if data:
                            if task_id in data.get("week_task_ids", []):
                                return True
                            if task_id in data.get("topics_task_ids", []):
                                return True
                            for d in data.get("days", []):
                                if task_id in d.get("task_ids", []):
                                    return True
                    except Exception:
                        pass
        target_key = f"{exclude_year}-W{exclude_week_num:02d}"
        for key, w in self.weeks.items():
            if key != target_key:
                if task_id in w.week_task_ids or task_id in w.topics_task_ids:
                    return True
                for d in w.days:
                    if task_id in d.task_ids:
                        return True
        return False

    def rollover_week_to_new_week(
        self,
        prev_week: WeekSchedule,
        new_week: WeekSchedule,
        prev_prev_week: Optional[WeekSchedule] = None
    ) -> int:
        """
        Traspasa tareas pendientes de la semana anterior a Week Tasks de la nueva semana.
        Aplica la regla de 2 semanas: si una tarea ya estuvo en prev_prev_week o semanas
        anteriores, o nació hace >= 2 semanas y sigue pendiente, se desagenda (no pasa a new_week y queda en backlog).
        """
        two_weeks_old_ids: Set[str] = set()
        if prev_prev_week:
            two_weeks_old_ids.update(prev_prev_week.week_task_ids)
            two_weeks_old_ids.update(prev_prev_week.topics_task_ids)
            for d in prev_prev_week.days:
                two_weeks_old_ids.update(d.task_ids)

        # Incluir todas las semanas anteriores registradas en self.weeks (< prev_week)
        for w_key, w in self.weeks.items():
            if w.year < prev_week.year or (w.year == prev_week.year and w.week_number < prev_week.week_number):
                two_weeks_old_ids.update(w.week_task_ids)
                two_weeks_old_ids.update(w.topics_task_ids)
                for d in w.days:
                    two_weeks_old_ids.update(d.task_ids)

        pending_from_prev: List[str] = []
        # Revisar week_task_ids y topics_task_ids de la semana anterior
        for tid in list(prev_week.week_task_ids) + list(prev_week.topics_task_ids):
            task = self.tasks.get(tid)
            if task and task.is_pending and not task.is_meeting and not task.is_recurring and tid not in pending_from_prev:
                pending_from_prev.append(tid)

        # Revisar días
        for d in prev_week.days:
            for tid in d.task_ids:
                task = self.tasks.get(tid)
                if task and task.is_pending and not task.is_meeting and not task.is_recurring and tid not in pending_from_prev:
                    pending_from_prev.append(tid)

        rolled_count = 0
        for tid in pending_from_prev:
            is_two_weeks_old = tid in two_weeks_old_ids
            task = self.tasks.get(tid)
            if not is_two_weeks_old and task and task.created_at:
                try:
                    dt = datetime.strptime(task.created_at, "%Y-%m-%d")
                    iso_y, iso_w, _ = dt.isocalendar()
                    if (new_week.year - iso_y) * 52 + (new_week.week_number - iso_w) >= 2:
                        is_two_weeks_old = True
                except Exception:
                    pass

            # Regla de 2 semanas: si ya estuvo hace 2 semanas o más, se desagenda
            if is_two_weeks_old:
                continue  # Pasa automáticamente a quedar en Backlog no agendado

            if tid not in new_week.week_task_ids:
                new_week.week_task_ids.append(tid)
                if tid not in new_week.topics_task_ids:
                    new_week.topics_task_ids.append(tid)
                rolled_count += 1

        if rolled_count > 0:
            self.save_week(new_week)
            log4brackets.log_rollover(prev_week.week_number, new_week.week_number, rolled_count)
        return rolled_count

    def prune_tasks_older_than_two_weeks(self, week: WeekSchedule) -> int:
        """
        Revisa todas las tareas agendadas en la semana (en week_task_ids y en days).
        Si una tarea pendiente lleva 2 o más semanas de antigüedad (nació o estuvo presente
        en semanas anteriores a (week_number - 1)), se desagenda de la semana para que
        quede limpia y preservada en el Backlog de su proyecto.
        Devuelve el número de tareas migradas al backlog.
        """
        prior_week_task_ids: Set[str] = set()
        for w_key, w in self.weeks.items():
            if w.year < week.year or (w.year == week.year and w.week_number <= week.week_number - 2):
                prior_week_task_ids.update(w.week_task_ids)
                prior_week_task_ids.update(w.topics_task_ids)
                for d in w.days:
                    prior_week_task_ids.update(d.task_ids)

        pruned_count = 0

        # Comprobar week_task_ids
        for tid in list(week.week_task_ids):
            task = self.tasks.get(tid)
            if not task or not task.is_pending:
                continue

            is_old = tid in prior_week_task_ids
            if not is_old and task.created_at:
                try:
                    dt = datetime.strptime(task.created_at, "%Y-%m-%d")
                    iso_y, iso_w, _ = dt.isocalendar()
                    if (week.year - iso_y) * 52 + (week.week_number - iso_w) >= 2:
                        is_old = True
                except Exception:
                    pass

            if is_old:
                week.week_task_ids.remove(tid)
                if tid in week.topics_task_ids:
                    week.topics_task_ids.remove(tid)
                pruned_count += 1
                log4brackets.log_task_backlogged(task.id, task.project_id, task.title)

        # Comprobar días
        for d in week.days:
            for tid in list(d.task_ids):
                task = self.tasks.get(tid)
                if not task or not task.is_pending:
                    continue

                is_old = tid in prior_week_task_ids
                if not is_old and task.created_at:
                    try:
                        dt = datetime.strptime(task.created_at, "%Y-%m-%d")
                        iso_y, iso_w, _ = dt.isocalendar()
                        if (week.year - iso_y) * 52 + (week.week_number - iso_w) >= 2:
                            is_old = True
                    except Exception:
                        pass

                if is_old:
                    d.task_ids.remove(tid)
                    pruned_count += 1
                    log4brackets.log_task_backlogged(task.id, task.project_id, task.title)

        if pruned_count > 0:
            self.save_week(week)

        return pruned_count


