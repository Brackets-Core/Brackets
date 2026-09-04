#!/usr/bin/env python3
"""
Tests unitarios para el motor de Tareas y Reuniones Recurrentes (RecurringTask).
"""

import os
import shutil
import tempfile
import unittest

from brackets.models.entities import RecurringTask, WeekSchedule, DaySchedule
from brackets.managers.entity_manager import EntityManager


class TestRecurringTasks(unittest.TestCase):
    """Pruebas para definición, persistencia, idempotencia y aplicación de recurrentes."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.mock_source = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data", "mock"
        )
        shutil.copytree(self.mock_source, os.path.join(self.tmp_dir, "mock_data"))
        self.data_dir = os.path.join(self.tmp_dir, "mock_data")
        self.manager = EntityManager(self.data_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_recurring_model_and_persistence(self):
        """Valida que una tarea recurrente se cree, persista y recargue con todos sus atributos."""
        rec = self.manager.create_recurring_task(
            title="Daily S^3",
            recurrence_type="weekly_days",
            days_of_week=[0, 2, 4],
            project_id="DAILY_PROJECT"
        )
        self.assertTrue(rec.id.startswith("REC-"))
        self.assertEqual(rec.title, "Daily S^3")
        self.assertEqual(rec.days_of_week, [0, 2, 4])
        self.assertTrue(rec.active)

        # Recargar desde disco
        new_manager = EntityManager(self.data_dir)
        self.assertIn(rec.id, new_manager.recurring_tasks)
        loaded = new_manager.recurring_tasks[rec.id]
        self.assertEqual(loaded.title, "Daily S^3")
        self.assertEqual(loaded.days_of_week, [0, 2, 4])
        self.assertEqual(loaded.project_id, "DAILY_PROJECT")

    def test_apply_weekly_days_recurring(self):
        """Verifica la inyección de reuniones de días fijos (Lunes, Miércoles, Viernes)."""
        rec = self.manager.create_recurring_task(
            title="Daily S^3",
            recurrence_type="weekly_days",
            days_of_week=[0, 2, 4]  # L, X, V
        )

        week = self.manager.load_week(2026, 34)
        self.assertIsNotNone(week)

        injected = self.manager.apply_recurring_tasks(week)
        self.assertEqual(injected, 3)

        # Verificar que las tareas se hayan creado en los días correspondientes
        # Día 0 (Lunes), Día 2 (Miércoles), Día 4 (Viernes)
        monday = week.days[0]
        wednesday = week.days[2]
        friday = week.days[4]

        # Cada uno debe contener una tarea con el título y recurring_id
        mon_tasks = [self.manager.tasks[tid] for tid in monday.task_ids if tid in self.manager.tasks]
        self.assertTrue(any(t.title == "Daily S^3" and t.recurring_id == rec.id for t in mon_tasks))

        wed_tasks = [self.manager.tasks[tid] for tid in wednesday.task_ids if tid in self.manager.tasks]
        self.assertTrue(any(t.title == "Daily S^3" and t.recurring_id == rec.id for t in wed_tasks))

        fri_tasks = [self.manager.tasks[tid] for tid in friday.task_ids if tid in self.manager.tasks]
        self.assertTrue(any(t.title == "Daily S^3" and t.recurring_id == rec.id for t in fri_tasks))

    def test_apply_interval_weeks_recurring(self):
        """Valida que una tarea de cada 4 semanas solo se inyecte en las semanas que correspondan."""
        rec = self.manager.create_recurring_task(
            title="Renovar Accesos",
            recurrence_type="interval_weeks",
            interval_weeks=4,
            base_week=34,
            day_of_week=4  # Viernes
        )

        week34 = self.manager.load_week(2026, 34)
        injected34 = self.manager.apply_recurring_tasks(week34)
        self.assertEqual(injected34, 1)
        fri_tasks = [self.manager.tasks[tid] for tid in week34.days[4].task_ids if tid in self.manager.tasks]
        self.assertTrue(any(t.title == "Renovar Accesos" and t.recurring_id == rec.id for t in fri_tasks))

        # Crear semana 35 (no le toca por ser 35 - 34 = 1, no múltiplo de 4)
        week35 = WeekSchedule(
            year=2026,
            month=8,
            week_number=35,
            days=[DaySchedule(day_number=24 + i) for i in range(5)]
        )
        self.manager.save_week(week35)

        injected35 = self.manager.apply_recurring_tasks(week35)
        self.assertEqual(injected35, 0)

        # Crear semana 38 (le toca: 38 - 34 = 4, múltiplo de 4)
        week38 = WeekSchedule(
            year=2026,
            month=9,
            week_number=38,
            days=[DaySchedule(day_number=14 + i) for i in range(5)]
        )
        self.manager.save_week(week38)

        injected38 = self.manager.apply_recurring_tasks(week38)
        self.assertEqual(injected38, 1)

    def test_apply_recurring_tasks_idempotence(self):
        """Verifica que ejecutar la inyección múltiples veces NO duplica tareas."""
        self.manager.create_recurring_task(
            title="Daily S^3",
            recurrence_type="weekly_days",
            days_of_week=[0, 2, 4]
        )
        week = self.manager.load_week(2026, 34)
        first_run = self.manager.apply_recurring_tasks(week)
        self.assertEqual(first_run, 3)

        # Segunda ejecución inmediata
        second_run = self.manager.apply_recurring_tasks(week)
        self.assertEqual(second_run, 0)

        # Conteo de tareas en Lunes
        monday = week.days[0]
        daily_count = sum(
            1 for tid in monday.task_ids
            if tid in self.manager.tasks and self.manager.tasks[tid].title == "Daily S^3"
        )
        self.assertEqual(daily_count, 1)

    def test_toggle_and_delete_recurring(self):
        """Verifica pausar, reactivar y borrar tareas recurrentes."""
        rec = self.manager.create_recurring_task(
            title="Reunión 1:1 Semanal",
            recurrence_type="weekly_days",
            days_of_week=[1]
        )
        self.assertTrue(rec.active)

        # Pausar
        toggled = self.manager.toggle_recurring_task(rec.id)
        self.assertFalse(toggled.active)

        # No debe inyectarse al estar pausada
        week = self.manager.load_week(2026, 34)
        injected = self.manager.apply_recurring_tasks(week)
        self.assertEqual(injected, 0)

        # Eliminar
        deleted = self.manager.delete_recurring_task(rec.id)
        self.assertTrue(deleted)
        self.assertNotIn(rec.id, self.manager.recurring_tasks)

    def test_recurring_task_created_at_and_reuse_across_weeks(self):
        """Verifica que las recurrentes tengan fecha de creación del día y se reaprovechen entre semanas."""
        rec = self.manager.create_recurring_task(
            title="Daily S^3",
            recurrence_type="weekly_days",
            days_of_week=[0, 2, 4]  # L, X, V
        )

        week34 = self.manager.load_week(2026, 34)
        self.assertIsNotNone(week34)

        # 1. Primera semana (W34)
        self.manager.apply_recurring_tasks(week34)

        mon_task_w34 = self.manager.tasks[week34.days[0].task_ids[-1]]
        wed_task_w34 = self.manager.tasks[week34.days[2].task_ids[-1]]
        fri_task_w34 = self.manager.tasks[week34.days[4].task_ids[-1]]

        # Deben ser 3 tareas distintas en la misma semana
        self.assertNotEqual(mon_task_w34.id, wed_task_w34.id)
        self.assertNotEqual(wed_task_w34.id, fri_task_w34.id)
        self.assertNotEqual(mon_task_w34.id, fri_task_w34.id)

        # La fecha de creación debe corresponder al día exacto
        self.assertEqual(mon_task_w34.created_at, "2026-08-17")
        self.assertEqual(wed_task_w34.created_at, "2026-08-19")
        self.assertEqual(fri_task_w34.created_at, "2026-08-21")

        # Marcar la del lunes como completada
        mon_task_w34.status = "done"
        mon_task_w34.completed_at = "2026-08-17"

        # Conteo inicial de tareas
        initial_tasks_count = len(self.manager.tasks)

        # 2. Generar nueva semana (W35)
        week35 = WeekSchedule(
            year=2026,
            month=8,
            week_number=35,
            days=[DaySchedule(day_number=d, task_ids=[]) for d in [24, 25, 26, 27, 28]]
        )
        self.manager.save_week(week35)

        # Aplicar recurrentes en W35
        self.manager.apply_recurring_tasks(week35)

        # No debe haber creado tareas nuevas en la base de datos (se reaprovechan las 3)
        self.assertEqual(len(self.manager.tasks), initial_tasks_count)

        mon_task_w35 = self.manager.tasks[week35.days[0].task_ids[-1]]
        wed_task_w35 = self.manager.tasks[week35.days[2].task_ids[-1]]
        fri_task_w35 = self.manager.tasks[week35.days[4].task_ids[-1]]

        # Deben ser las mismas 3 instancias reaprovechadas
        self.assertEqual(mon_task_w35.id, mon_task_w34.id)
        self.assertEqual(wed_task_w35.id, wed_task_w34.id)
        self.assertEqual(fri_task_w35.id, fri_task_w34.id)

        # El estado de la tarea del lunes debe haberse reseteado a pending
        self.assertEqual(mon_task_w35.status, "pending")
        self.assertIsNone(mon_task_w35.completed_at)
        # La fecha de creación debe actualizarse a la del día en que aparece en la bitácora
        self.assertEqual(mon_task_w35.created_at, "2026-08-24")

    def test_deduplicate_tasks(self):
        """Verifica la desduplicación de tareas redundantes y actualización en semanas."""
        # Crear tareas duplicadas artificiales
        t1 = self.manager.create_task(title="Investigar Kaggle ML", status="done", project_id="AI")
        t2 = self.manager.create_task(title="Investigar Kaggle ML", status="pending", project_id="POR_ASIGNAR")
        t3 = self.manager.create_task(title="Investigar Kaggle ML", status="pending")

        week = self.manager.load_week(2026, 34)
        week.days[0].task_ids.append(t2.id)
        week.week_task_ids.append(t3.id)
        self.manager.save_week(week)

        total_mapped, removed_count = self.manager.deduplicate_tasks()
        self.assertGreaterEqual(removed_count, 2)

        # Recargar semana y verificar que t2 y t3 fueron reemplazados por el canónico t1
        reloaded_week = self.manager.load_week(2026, 34, reload=True)
        self.assertIn(t1.id, reloaded_week.week_task_ids)
        self.assertNotIn(t3.id, reloaded_week.week_task_ids)

    def test_recurring_tasks_not_rolled_over_and_not_reinjected_if_moved_or_cancelled(self):
        """Verifica que las tareas recurrentes no se arrastren día a día si no se hacen y no se reinyecten si fueron movidas/canceladas."""
        rec = self.manager.create_recurring_task(
            title="Seguimiento Reporting",
            recurrence_type="weekly_days",
            days_of_week=[2]  # Miércoles
        )

        week = self.manager.load_week(2026, 34)
        self.manager.apply_recurring_tasks(week)

        # En día 2 (miércoles) debe estar la tarea
        wednesday = week.days[2]
        self.assertEqual(len(wednesday.task_ids), 1)
        rec_task_id = wednesday.task_ids[0]
        rec_task = self.manager.tasks[rec_task_id]
        self.assertEqual(rec_task.title, "Seguimiento Reporting")
        self.assertTrue(rec_task.is_recurring)

        # Si el usuario la mueve al jueves (día 3) y la cancela:
        wednesday.task_ids.remove(rec_task_id)
        thursday = week.days[3]
        thursday.task_ids.append(rec_task_id)
        rec_task.status = "cancelled"
        self.manager.save_week(week)
        self.manager.save_tasks()

        # 1. Al llamar de nuevo a apply_recurring_tasks, NO debe reinyectarla en miércoles
        injected = self.manager.apply_recurring_tasks(week)
        self.assertEqual(injected, 0)
        self.assertNotIn(rec_task_id, wednesday.task_ids)

        # 2. Al ejecutar rollover_day_tasks sobre el viernes (día 4), las recurrentes pendientes no se arrastran
        friday = week.days[4]
        # Crear otra tarea recurrente pendiente en el jueves
        daily_rec = self.manager.create_recurring_task(title="Daily S^3", recurrence_type="weekly_days", days_of_week=[0, 2, 4])
        daily_task = self.manager.create_task(title="Daily S^3", recurring_id=daily_rec.id, day_number=thursday.day_number)
        
        # Rollover hacia el viernes
        rolled = self.manager.rollover_day_tasks(week, friday.day_number)
        # No debe haber arrastrado daily_task ni rec_task al viernes
        self.assertNotIn(daily_task.id, friday.task_ids)
        self.assertNotIn(rec_task_id, friday.task_ids)

    def test_meeting_task_type_and_immunity_to_rollover(self):
        """Verifica que las reuniones (task_type='meeting') no salten entre días si no se realizan."""
        rec_meeting = self.manager.create_recurring_task(
            title="Data - BT",
            recurrence_type="weekly_days",
            days_of_week=[3],  # Jueves
            task_type="meeting"
        )
        self.assertTrue(rec_meeting.is_meeting)

        week = self.manager.load_week(2026, 34)
        self.manager.apply_recurring_tasks(week)

        thursday = week.days[3]
        rec_task_id = next(tid for tid in thursday.task_ids if self.manager.tasks[tid].title == "Data - BT")
        task = self.manager.tasks[rec_task_id]
        self.assertTrue(task.is_meeting)
        self.assertEqual(task.task_type, "meeting")
        self.assertEqual(task.status, "pending")

        # El viernes (día 4) se ejecuta rollover
        friday = week.days[4]
        rolled = self.manager.rollover_day_tasks(week, friday.day_number)

        # La reunión no debe haberse arrastrado al viernes
        self.assertNotIn(rec_task_id, friday.task_ids)
        # Debe permanecer en el jueves
        self.assertIn(rec_task_id, thursday.task_ids)


if __name__ == "__main__":
    unittest.main()
