#!/usr/bin/env python3
"""Tests unitarios para la Fase 4: Tags de proyectos #[ProjectCode] y Métricas de Backlog."""

import os
import tempfile
import unittest

from brackets.models.entities import WeekSchedule, DaySchedule, Task
from brackets.managers.entity_manager import EntityManager
from brackets.managers.markdown_sync_service import MarkdownSyncService
from brackets.utils.bitacora_parser import BitacoraMarkdownParser
from brackets.core.project_backlog_controller import ProjectBacklogController


class TestPhase4ProjectTagsAndMetrics(unittest.TestCase):
    """Valida la detección de tags #[ProjectCode] y el cálculo de métricas de backlog."""

    def test_parse_project_tag_variations(self):
        """Valida que BitacoraMarkdownParser extraiga tags de proyectos correctamente."""
        # 1. Hashtag explícito con corchetes
        pid, clean = BitacoraMarkdownParser.parse_project_tag("Configurar dashboard #[GRAFANA]")
        self.assertEqual(pid, "GRAFANA")
        self.assertEqual(clean, "Configurar dashboard")

        pid, clean = BitacoraMarkdownParser.parse_project_tag("#[TRUCKS] Revisar telemetría")
        self.assertEqual(pid, "TRUCKS")
        self.assertEqual(clean, "Revisar telemetría")

        pid, clean = BitacoraMarkdownParser.parse_project_tag("Arreglar #[SUPPLY_API] error 500 en endpoint")
        self.assertEqual(pid, "SUPPLY_API")
        self.assertEqual(clean, "Arreglar error 500 en endpoint")

        # 2. Corchete al inicio sin emoji
        pid, clean = BitacoraMarkdownParser.parse_project_tag("[ROVO_AI] Preparar prompt de evaluación")
        self.assertEqual(pid, "ROVO_AI")
        self.assertEqual(clean, "Preparar prompt de evaluación")

        # 3. Hashtag simple al final
        pid, clean = BitacoraMarkdownParser.parse_project_tag("Actualizar librerías de python #CORE")
        self.assertEqual(pid, "CORE")
        self.assertEqual(clean, "Actualizar librerías de python")

        # 4. No debe confundir tickets Jira o checkboxes
        pid, clean = BitacoraMarkdownParser.parse_project_tag("Revisar tarea [🎫SUPPLY-18914]")
        self.assertIsNone(pid)
        self.assertEqual(clean, "Revisar tarea [🎫SUPPLY-18914]")

        pid, clean = BitacoraMarkdownParser.parse_project_tag("[ ] Tarea con checkbox")
        self.assertIsNone(pid)

    def test_sync_markdown_with_project_tag(self):
        """Verifica que al sincronizar una bitácora con #[PROJ], se cree y asigne el proyecto automáticamente."""
        with tempfile.TemporaryDirectory() as tmp_vault:
            data_dir = os.path.join(tmp_vault, "data")
            os.makedirs(os.path.join(data_dir, "tables"), exist_ok=True)
            os.makedirs(os.path.join(data_dir, "weeks"), exist_ok=True)

            manager = EntityManager(data_dir)
            week = WeekSchedule(year=2026, month=9, week_number=39)
            manager.save_week(week)
            service = MarkdownSyncService(manager, tmp_vault)

            md_content = """# 🗓️Week 39

## 🎯Topics
  - 

## 📋Week Tasks
  - [ ] Implementar caché de Redis #[INFRA]

## 📝Notes
  - 

## 🚗21
  - [ ] Revisar logs de ingesta #[DATA_LAKE]
  - [x] Corregir validación de esquema #[DATA_LAKE]

<!-- Definiciones -->
"""
            md_path = os.path.join(tmp_vault, "[2026][09]Week39.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)

            synced = service.sync_week_from_markdown(md_path, 2026, 39)
            self.assertTrue(synced)

            # Verificar que los proyectos fueron creados automáticamente
            self.assertIn("INFRA", manager.projects)
            self.assertIn("DATA_LAKE", manager.projects)

            # Verificar tareas en la base de datos
            infra_tasks = [t for t in manager.tasks.values() if t.project_id == "INFRA"]
            self.assertEqual(len(infra_tasks), 1)
            self.assertEqual(infra_tasks[0].status, "pending")

            data_lake_tasks = [t for t in manager.tasks.values() if t.project_id == "DATA_LAKE"]
            self.assertEqual(len(data_lake_tasks), 2)
            done_tasks = [t for t in data_lake_tasks if t.is_done]
            pending_tasks = [t for t in data_lake_tasks if t.is_pending]
            self.assertEqual(len(done_tasks), 1)
            self.assertEqual(len(pending_tasks), 1)

    def test_project_and_backlog_metrics(self):
        """Valida el cálculo de métricas avanzadas por proyecto y del backlog global."""
        with tempfile.TemporaryDirectory() as tmp_vault:
            data_dir = os.path.join(tmp_vault, "data")
            os.makedirs(os.path.join(data_dir, "tables"), exist_ok=True)
            os.makedirs(os.path.join(data_dir, "weeks"), exist_ok=True)

            mgr = EntityManager(data_dir)
            mgr.ensure_project("ALPHA", name="Proyecto Alpha")
            mgr.ensure_project("BETA", name="Proyecto Beta")

            # 2 tareas hechas, 1 pendiente en ALPHA
            t1 = mgr.create_task(title="Alpha T1", project_id="ALPHA", status="done")
            t2 = mgr.create_task(title="Alpha T2", project_id="ALPHA", status="done")
            t3 = mgr.create_task(title="Alpha T3", project_id="ALPHA", status="pending")

            # Agendar t3 en una semana
            week = WeekSchedule(year=2026, month=9, week_number=39)
            day = DaySchedule(day_number=1, task_ids=[t3.id])
            week.days.append(day)
            mgr.save_week(week)

            # 1 tarea pendiente sin agendar en BETA (Backlog)
            t4 = mgr.create_task(title="Beta T4", project_id="BETA", status="pending")

            # 1 tarea sin proyecto en Backlog
            t5 = mgr.create_task(title="General T5", project_id=None, status="pending")

            # Ideas en ALPHA
            mgr.create_idea(title="Idea 1", project_id="ALPHA", status="evaluating")
            mgr.create_idea(title="Idea 2", project_id="ALPHA", status="accepted")

            # Estadísticas de ALPHA
            alpha_stats = mgr.get_project_stats("ALPHA")
            self.assertEqual(alpha_stats["total_tasks"], 3)
            self.assertEqual(alpha_stats["done_tasks"], 2)
            self.assertEqual(alpha_stats["pending_tasks"], 1)
            self.assertEqual(alpha_stats["backlog_tasks"], 0)  # t3 está agendada en el día 1
            self.assertEqual(alpha_stats["scheduled_tasks"], 1)
            self.assertEqual(alpha_stats["completion_rate"], 66.7)
            self.assertEqual(alpha_stats["evaluating_ideas"], 1)
            self.assertEqual(alpha_stats["accepted_ideas"], 1)

            # Estadísticas de BETA
            beta_stats = mgr.get_project_stats("BETA")
            self.assertEqual(beta_stats["total_tasks"], 1)
            self.assertEqual(beta_stats["backlog_tasks"], 1)
            self.assertEqual(beta_stats["scheduled_tasks"], 0)
            self.assertEqual(beta_stats["completion_rate"], 0.0)

            # Métricas consolidadas
            all_metrics = mgr.get_all_projects_metrics()
            self.assertEqual(all_metrics["total_projects"], 2)
            self.assertEqual(all_metrics["total_tasks"], 5)
            self.assertEqual(all_metrics["total_done"], 2)
            self.assertEqual(all_metrics["total_backlog"], 2)  # t4 y t5
            self.assertEqual(all_metrics["unassigned_backlog"], 1)  # t5

    def test_project_backlog_controller_add_with_hashtag(self):
        """Valida que add_backlog_task reconozca #[PROJ] directamente sin menú interactivo."""
        with tempfile.TemporaryDirectory() as tmp_vault:
            data_dir = os.path.join(tmp_vault, "data")
            os.makedirs(os.path.join(data_dir, "tables"), exist_ok=True)
            os.makedirs(os.path.join(data_dir, "weeks"), exist_ok=True)

            mgr = EntityManager(data_dir)
            ctrl = ProjectBacklogController(
                entity_manager=mgr,
                vault_root=tmp_vault,
                input_fn=lambda prompt="": "Crear microservicio #[NEW_PROJ]",
                print_fn=lambda *a, **k: None,
            )

            ctrl.add_backlog_task()

            self.assertIn("NEW_PROJ", mgr.projects)
            tasks = [t for t in mgr.tasks.values() if t.project_id == "NEW_PROJ"]
            self.assertEqual(len(tasks), 1)
            self.assertIn("Crear microservicio", tasks[0].title)


if __name__ == "__main__":
    unittest.main()
