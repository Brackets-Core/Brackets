#!/usr/bin/env python3
"""
Servicio de Gestión y Aplicación de Tareas Recurrentes.
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from brackets.managers.entity_manager import EntityManager
    from brackets.models.entities import WeekSchedule, DaySchedule


class RecurringTaskService:
    """Gestiona la lógica de inyección e idempotencia de tareas y reuniones recurrentes."""

    def __init__(self, manager: EntityManager):
        self.manager = manager

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
        active_recs = self.manager.list_recurring_tasks(active_only=True)
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
                t for t in self.manager.tasks.values()
                if t.recurring_id == rec.id or (not t.recurring_id and t.title == rec.title)
            ]
            existing_rec_tasks.sort(key=lambda x: x.id)

            # Asegurar que todas tengan el recurring_id seteado y hereden atributos canónicos
            for t in existing_rec_tasks:
                if not t.recurring_id:
                    t.recurring_id = rec.id
                t.task_type = rec.task_type
                if rec.project_id and (not t.project_id or t.project_id == "POR_ASIGNAR"):
                    t.project_id = rec.project_id

            if rec.recurrence_type == "weekly_days":
                # Días específicos (ej: [0, 2, 4] para Lunes, Miércoles, Viernes)
                for idx, target_wday in enumerate(rec.days_of_week):
                    target_day = weekday_to_day_schedule.get(target_wday)
                    if not target_day:
                        continue

                    # No agendar tareas ni reuniones recurrentes en días festivos/vacaciones (🏖️)
                    if target_day.location_emoji == "🏖️":
                        to_remove = [
                            tid for tid in target_day.task_ids
                            if self.manager.tasks.get(tid) and (self.manager.tasks[tid].recurring_id == rec.id or self.manager.tasks[tid].title == rec.title)
                        ]
                        for tid in to_remove:
                            target_day.task_ids.remove(tid)
                        continue

                    try:
                        target_date = datetime.fromisocalendar(week.year, week.week_number, target_wday + 1).strftime("%Y-%m-%d")
                    except Exception:
                        target_date = datetime.now().strftime("%Y-%m-%d")

                    # Comprobar si ya existe en target_day
                    already_in_day = any(
                        (self.manager.tasks.get(tid) and (self.manager.tasks[tid].recurring_id == rec.id or self.manager.tasks[tid].title == rec.title))
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
                        new_task = self.manager.create_task(
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

                    # No agendar tareas ni reuniones recurrentes en días festivos/vacaciones (🏖️)
                    if target_day.location_emoji == "🏖️":
                        to_remove = [
                            tid for tid in target_day.task_ids
                            if self.manager.tasks.get(tid) and (self.manager.tasks[tid].recurring_id == rec.id or self.manager.tasks[tid].title == rec.title)
                        ]
                        for tid in to_remove:
                            target_day.task_ids.remove(tid)
                        continue

                    try:
                        target_date = datetime.fromisocalendar(week.year, week.week_number, rec.day_of_week + 1).strftime("%Y-%m-%d")
                    except Exception:
                        target_date = datetime.now().strftime("%Y-%m-%d")

                    already_in_day = any(
                        (self.manager.tasks.get(tid) and (self.manager.tasks[tid].recurring_id == rec.id or self.manager.tasks[tid].title == rec.title))
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
                        new_task = self.manager.create_task(
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
                        (self.manager.tasks.get(tid) and (self.manager.tasks[tid].recurring_id == rec.id or self.manager.tasks[tid].title == rec.title))
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
                        new_task = self.manager.create_task(
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
            self.manager.save_tasks()
            self.manager.save_week(week)

        return injected_count
