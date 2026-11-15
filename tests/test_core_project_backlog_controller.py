#!/usr/bin/env python3
"""
Tests para ProjectBacklogController en brackets/core/project_backlog_controller.py
"""

import sys
import os
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.entities import WeekSchedule, DaySchedule, Idea
from managers.entity_manager import EntityManager
from core.project_backlog_controller import ProjectBacklogController


class TestCoreProjectBacklogController(unittest.TestCase):
    """Pruebas unitarias para el controlador de gestión de proyectos, backlog e ideas."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.mock_source = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "mock"
        )
        self.mock_data_dir = os.path.join(self.tmp_dir, "data")
        shutil.copytree(self.mock_source, self.mock_data_dir)

        self.entity_manager = EntityManager(self.mock_data_dir)
        self.output_lines = []

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _mock_print(self, *args, **kwargs):
        line = " ".join(str(a) for a in args)
        self.output_lines.append(line)

    def test_add_backlog_task(self):
        """Valida que [1] añada una tarea al backlog de un proyecto sin fecha agendada."""
        inputs = [
            "Implementar exportador DuckDB",  # Título
            "1",                              # Proyecto 1: AMR_LOGISTICS
            ""                                # Enter para continuar
        ]
        controller = ProjectBacklogController(
            entity_manager=self.entity_manager,
            vault_root=self.tmp_dir,
            input_fn=lambda _: inputs.pop(0),
            print_fn=self._mock_print
        )

        controller.add_backlog_task()

        # Verificar que la tarea se creó en la base de datos
        matching = [t for t in self.entity_manager.tasks.values() if t.title == "Implementar exportador DuckDB"]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].project_id, "AMR_LOGISTICS")
        self.assertTrue(matching[0].is_pending)

        output_text = "\n".join(self.output_lines)
        self.assertIn("Tarea guardada en el Backlog de [AMR_LOGISTICS]", output_text)

        # Verificar sincronización automática del archivo Markdown de Backlog
        backlog_md = os.path.join(self.tmp_dir, "[📋PROJECTS]✅BackLog.md")
        self.assertTrue(os.path.exists(backlog_md))

    def test_capture_idea(self):
        """Valida que [2] capture una nueva idea con viñetas y estado inicial."""
        inputs = [
            "Probar motor DuckDB en Brackets",  # Título
            "1",                                # Proyecto 1: AMR_LOGISTICS
            "Permitirá consultas SQL analíticas sobre miles de tareas",  # Viñeta 1
            "Sin dependencias pesadas",                                  # Viñeta 2
            "",                                                          # Fin viñetas
            "1",                                                         # Estado: 1 (evaluating)
            ""                                                           # Enter
        ]
        controller = ProjectBacklogController(
            entity_manager=self.entity_manager,
            vault_root=self.tmp_dir,
            input_fn=lambda _: inputs.pop(0),
            print_fn=self._mock_print
        )

        controller.capture_idea()

        matching = [i for i in self.entity_manager.ideas.values() if i.title == "Probar motor DuckDB en Brackets"]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].project_id, "AMR_LOGISTICS")
        self.assertEqual(matching[0].status, "evaluating")
        self.assertEqual(len(matching[0].content), 2)

        output_text = "\n".join(self.output_lines)
        self.assertIn("Idea registrada en [AMR_LOGISTICS]", output_text)
        self.assertIn("🟡 Evaluar", output_text)

        # Verificar sincronización automática del archivo Markdown de Ideas
        ideas_md = os.path.join(self.tmp_dir, "[🧩GENERAL]🧠Ideas.md")
        self.assertTrue(os.path.exists(ideas_md))

    def test_schedule_backlog_task_to_today(self):
        """Valida que [3] asigne una tarea de backlog al día activo de la semana."""
        week = self.entity_manager.load_week(2026, 34)
        day = week.days[0]  # Día 17

        # Crear un proyecto y una tarea única en el backlog
        proj = self.entity_manager.ensure_project("PROJ_SCHED_TEST", name="Project Sched Test")
        task = self.entity_manager.create_task(
            title="Tarea de backlog para agendar",
            project_id=proj.id
        )
        self.assertNotIn(task.id, day.task_ids)

        projects = self.entity_manager.list_projects()
        proj_idx = [p.id for p in projects].index(proj.id) + 1

        inputs = [
            str(proj_idx),  # Filtrar por PROJ_SCHED_TEST
            "1",            # Seleccionar la única tarea disponible
            ""              # Enter
        ]
        controller = ProjectBacklogController(
            entity_manager=self.entity_manager,
            current_week=week,
            current_day=day,
            vault_root=self.tmp_dir,
            input_fn=lambda _: inputs.pop(0),
            print_fn=self._mock_print
        )

        controller.schedule_backlog_task_to_today()

        # Recargar semana y verificar que task.id está en day.task_ids
        reloaded_week = self.entity_manager.load_week(2026, 34, reload=True)
        reloaded_day = reloaded_week.days[0]
        self.assertIn(task.id, reloaded_day.task_ids)

    def test_view_projects_overview(self):
        """Valida que [4] calcule estadísticas al vuelo de proyectos."""
        inputs = [""]  # Enter para volver
        controller = ProjectBacklogController(
            entity_manager=self.entity_manager,
            vault_root=self.tmp_dir,
            input_fn=lambda _: inputs.pop(0),
            print_fn=self._mock_print
        )

        controller.view_projects_overview()
        output_text = "\n".join(self.output_lines)

        self.assertIn("RESUMEN GENERAL DE PROYECTOS", output_text)
        self.assertIn("METRICS_INFLUXDB", output_text)
        self.assertIn("Tareas:", output_text)
        self.assertIn("Ideas:", output_text)

    def test_view_project_ideas_and_update_status(self):
        """Valida que [6] liste ideas y permita actualizar su estado."""
        proj = self.entity_manager.ensure_project("PROJ_IDEA_TEST", name="Project Idea Test")
        idea = self.entity_manager.create_idea(
            title="Idea para actualizar",
            project_id=proj.id,
            status="evaluating"
        )
        projects = self.entity_manager.list_projects()
        proj_idx = [p.id for p in projects].index(proj.id) + 1

        inputs = [
            str(proj_idx),  # Filtrar por PROJ_IDEA_TEST
            "c",            # Cambiar estado
            "1",            # Seleccionar idea 1
            "2",            # Nuevo estado: 2 (accepted)
            "",             # Enter confirmación
            ""              # Enter volver
        ]
        controller = ProjectBacklogController(
            entity_manager=self.entity_manager,
            vault_root=self.tmp_dir,
            input_fn=lambda _: inputs.pop(0),
            print_fn=self._mock_print
        )

        controller.view_project_ideas()

        updated_idea = self.entity_manager.ideas[idea.id]
        self.assertEqual(updated_idea.status, "accepted")

    def test_run_subpanel_loop(self):
        """Valida que el submenú responda a opciones y salga con '0'."""
        inputs = ["0"]  # Salir inmediatamente
        controller = ProjectBacklogController(
            entity_manager=self.entity_manager,
            vault_root=self.tmp_dir,
            input_fn=lambda _: inputs.pop(0),
            print_fn=self._mock_print
        )

        result = controller.run()
        self.assertEqual(result, "back")


if __name__ == "__main__":
    unittest.main()
