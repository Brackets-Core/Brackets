#!/usr/bin/env python3
"""
Tests para la entidad Topic, jerarquía Proyecto/Topic/Tarea/Nota,
sección Week Tasks y ciclo de vida (rollover de 2 semanas).
"""

import os
import shutil
import tempfile
import unittest

from models.entities import Topic, Task, Note, WeekSchedule, DaySchedule
from managers.entity_manager import EntityManager
from generators.bitacora_renderer import BitacoraRenderer
from managers.markdown_sync_service import MarkdownSyncService


class TestTopicsAndWeekTasks(unittest.TestCase):
    """Pruebas unitarias para Topics, Week Tasks y jerarquía relacional."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.mock_source = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "mock"
        )
        shutil.copytree(self.mock_source, os.path.join(self.tmp_dir, "mock_data"))
        self.data_dir = os.path.join(self.tmp_dir, "mock_data")
        self.manager = EntityManager(self.data_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_topic_model_and_persistence(self):
        """Verifica la creación y persistencia de Topics en su tabla YAML."""
        top = self.manager.create_topic(
            title="Integración con Flota AMR",
            project_id="AMR_LOGISTICS"
        )
        self.assertTrue(top.id.startswith("TOP-"))
        self.assertEqual(top.title, "Integración con Flota AMR")
        self.assertEqual(top.project_id, "AMR_LOGISTICS")

        # Recargar desde disco
        new_manager = EntityManager(self.data_dir)
        self.assertIn(top.id, new_manager.topics)
        loaded = new_manager.topics[top.id]
        self.assertEqual(loaded.title, "Integración con Flota AMR")
        self.assertEqual(loaded.project_id, "AMR_LOGISTICS")

    def test_task_inherits_project_from_topic(self):
        """Valida que una tarea asociada a un Topic herede el proyecto de dicho Topic."""
        topic = self.manager.create_topic(
            title="Agentes IA en Jira",
            project_id="ROVO_AI"
        )
        task = self.manager.create_task(
            title="Diseñar prompt de clasificación",
            topic_id=topic.id
        )
        self.assertEqual(task.topic_id, topic.id)
        self.assertEqual(task.project_id, "ROVO_AI")

    def test_note_inherits_project_from_topic(self):
        """Valida que una nota asociada a un Topic herede el proyecto del Topic."""
        topic = self.manager.create_topic(
            title="Migración DB",
            project_id="INFRA_CLOUD"
        )
        note = self.manager.add_note(
            year=2026,
            week_num=34,
            title="Decisión de particionado",
            content=["Particionar por año fiscal"],
            topic_id=topic.id
        )
        self.assertEqual(note.topic_id, topic.id)
        self.assertEqual(note.project_id, "INFRA_CLOUD")

    def test_week_tasks_management(self):
        """Verifica agregar tareas semanales sin día y agendarlas a un día concreto."""
        week = self.manager.load_week(2026, 34)
        self.assertIsNotNone(week)

        task = self.manager.create_task(
            title="Revisar documentación de API",
            is_week_task=True,
            year=2026,
            week_num=34
        )
        self.assertIn(task.id, week.week_task_ids)

        # Agendar la tarea semanal al primer día
        first_day_num = week.days[0].day_number
        ok = self.manager.schedule_week_task_to_day(week, task.id, first_day_num)
        self.assertTrue(ok)
        self.assertNotIn(task.id, week.week_task_ids)
        self.assertIn(task.id, week.days[0].task_ids)

    def test_rollover_week_to_new_week_with_two_week_rule(self):
        """
        Valida que el rollover semanal:
        1. Pase tareas pendientes de la semana previa a week_task_ids de la nueva semana.
        2. Si la tarea lleva 2 semanas sin resolverse, la retire de la semana (queda en Backlog).
        """
        # Crear semanas de prueba
        week33 = WeekSchedule(year=2026, month=8, week_number=33, days=[DaySchedule(day_number=10)])
        week34 = WeekSchedule(year=2026, month=8, week_number=34, days=[DaySchedule(day_number=17)])
        week35 = WeekSchedule(year=2026, month=8, week_number=35, days=[DaySchedule(day_number=24)])
        self.manager.save_week(week33)
        self.manager.save_week(week34)
        self.manager.save_week(week35)

        # Tarea 1: creada en W34 (1 semana de antigüedad)
        task_1wk = self.manager.create_task(
            title="Tarea de 1 semana pendiente",
            year=2026,
            week_num=34,
            day_number=17
        )

        # Tarea 2: pendiente desde W33 y aún pendiente en W34 (2 semanas de antigüedad)
        task_2wk = self.manager.create_task(
            title="Tarea vieja de 2 semanas",
            year=2026,
            week_num=33,
            day_number=10
        )
        week34.week_task_ids.append(task_2wk.id)
        self.manager.save_week(week34)

        rolled_count = self.manager.rollover_week_to_new_week(
            prev_week=week34,
            new_week=week35,
            prev_prev_week=week33
        )

        self.assertIn(task_1wk.id, week35.week_task_ids)
        self.assertNotIn(task_2wk.id, week35.week_task_ids)
        self.assertEqual(rolled_count, 1)

    def test_bitacora_renderer_topics_and_week_tasks(self):
        """Verifica que el renderizador genere las secciones ## 🎯Topics y ## 📋Week Tasks."""
        week = self.manager.load_week(2026, 34)
        top = self.manager.create_topic(title="Plan de Despliegue", project_id="DEPLOY_PROJ")
        self.manager.add_topic_to_week(week, top.id)

        task = self.manager.create_task(
            title="Verificar pipelines en GitHub Actions",
            is_week_task=True,
            year=2026,
            week_num=34
        )

        md = BitacoraRenderer.render_week(week, self.manager)
        self.assertIn("## 🎯Topics", md)
        self.assertIn("[DEPLOY_PROJ] Plan de Despliegue", md)
        self.assertIn("## 📋Week Tasks", md)
        self.assertIn("Verificar pipelines en GitHub Actions", md)

    def test_markdown_sync_service_week_tasks(self):
        """Verifica que MarkdownSyncService reconcilie tareas semanales y elimine duplicados al agendar a un día."""
        week = self.manager.load_week(2026, 34)
        day_num = week.days[0].day_number

        md_content = f"""# 🗓️Week 34

## 🎯Topics
  - [PROJECT_X] Arquitectura de Microservicios
  ---

## 📋Week Tasks
  - [ ] Tarea libre para la semana
  ---

## 📝Notes
  - 
  ---

## 🚗{day_num}
  - [x] Tarea libre para la semana
"""
        md_path = os.path.join(self.tmp_dir, "test_week.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        sync_service = MarkdownSyncService(self.manager, self.tmp_dir)
        sync_service.sync_week_from_markdown(md_path, 2026, 34)

        reloaded_week = self.manager.load_week(2026, 34, reload=True)
        topics = [t for t in self.manager.topics.values() if "Arquitectura de Microservicios" in t.title]
        self.assertEqual(len(topics), 1)

        day_obj = next(d for d in reloaded_week.days if d.day_number == day_num)
        completed_task = next(t for t in self.manager.tasks.values() if t.title == "Tarea libre para la semana")
        self.assertTrue(completed_task.is_done)
        self.assertIn(completed_task.id, day_obj.task_ids)
        self.assertNotIn(completed_task.id, reloaded_week.week_task_ids)

    def test_intervention_day_is_immune_to_rollover(self):
        """Verifica que los días de guardia o intervención NO reciban arrastre automático de tareas previas."""
        week = self.manager.load_week(2026, 34)
        friday = week.days[4]  # Viernes
        task_fri = self.manager.create_task(
            title="Tarea pendiente del viernes",
            day_number=friday.day_number,
            year=2026,
            week_num=34
        )

        # Añadir sábado de intervención
        sat = self.manager.add_day_to_week(
            week=week,
            day_number=22,
            location_emoji="🛠️",
            location_note="Intervención"
        )
        task_interv = self.manager.create_task(
            title="Deploy general de producción",
            day_number=22,
            year=2026,
            week_num=34
        )

        # Ejecutar rollover sobre el sábado
        rolled = self.manager.rollover_day_tasks(week, 22)
        self.assertEqual(rolled, 0)

        # La tarea del viernes debe seguir en el viernes y NO en el sábado
        self.assertIn(task_fri.id, friday.task_ids)
        self.assertNotIn(task_fri.id, sat.task_ids)
        self.assertIn(task_interv.id, sat.task_ids)

    def test_prune_tasks_older_than_two_weeks(self):
        """Valida que tareas de >= 2 semanas de antigüedad se desasignen de la semana hacia el backlog."""
        week35 = WeekSchedule(
            year=2026,
            month=8,
            week_number=35,
            days=[DaySchedule(day_number=24)]
        )
        self.manager.save_week(week35)

        # Tarea vieja (creada hace 3 semanas, ej: 2026-08-01 en semana 31)
        old_task = self.manager.create_task(
            title="Tarea vieja arrastrada de julio",
            is_week_task=True,
            year=2026,
            week_num=35
        )
        old_task.created_at = "2026-08-01"
        self.manager.save_tasks()

        # Tarea fresca de la semana actual
        fresh_task = self.manager.create_task(
            title="Tarea creada esta semana",
            is_week_task=True,
            year=2026,
            week_num=35
        )

        pruned = self.manager.prune_tasks_older_than_two_weeks(week35)
        self.assertEqual(pruned, 1)

        # La vieja se fue de la semana, pero sigue viva en la tabla (backlog de proyecto)
        self.assertNotIn(old_task.id, week35.week_task_ids)
        self.assertIn(old_task.id, self.manager.tasks)

        # La fresca se mantiene en la semana
        self.assertIn(fresh_task.id, week35.week_task_ids)

    def test_markdown_sync_topics_with_checkbox_not_treated_as_topics(self):
        """Valida que viñetas con checkbox - [ ] bajo ## Topics no creen entidades Topic con [GENERAL]."""
        md_content = """# 🗓️Week 34

## ✅Topics
  - [ ] Tarea con checkbox legacy en topics
  ---

## 📝Notes
  - 
  ---

## 🚗17 (Oficina)
  - 
"""
        md_path = os.path.join(self.tmp_dir, "legacy_topics_week.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        sync_service = MarkdownSyncService(self.manager, self.tmp_dir)
        sync_service.sync_week_from_markdown(md_path, 2026, 34)

        # No debe haberse creado ningún Topic para la tarea con checkbox
        matching_topics = [t for t in self.manager.topics.values() if "Tarea con checkbox legacy" in t.title]
        self.assertEqual(len(matching_topics), 0)

        # Debe haberse creado como tarea en week_task_ids
        matching_tasks = [t for t in self.manager.tasks.values() if "Tarea con checkbox legacy" in t.title]
        self.assertEqual(len(matching_tasks), 1)


if __name__ == "__main__":
    unittest.main()
