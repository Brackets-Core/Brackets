#!/usr/bin/env python3
"""
Tests para DailyHubController en brackets/core/daily_hub_controller.py
"""

import sys
import os
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from brackets.models.entities import WeekSchedule, DaySchedule
from brackets.managers.entity_manager import EntityManager
from brackets.core.daily_hub_controller import DailyHubController


class TestCoreDailyHubController(unittest.TestCase):
    """Pruebas unitarias para el controlador del Hub Diario interactivo."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.mock_source = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
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

    def test_render_dashboard(self):
        """Verifica que el dashboard imprima la cabecera, tareas de hoy y comandos."""
        controller = DailyHubController(
            vault_root=self.tmp_dir,
            entity_manager=self.entity_manager,
            print_fn=self._mock_print
        )

        week = self.entity_manager.load_week(2026, 34)
        day = week.days[0]  # Día 17

        ordered_ids = controller.render_dashboard(week, day)
        output_text = "\n".join(self.output_lines)

        self.assertEqual(len(ordered_ids), 2)
        self.assertIn("🗓️ BITÁCORA:", output_text)
        self.assertIn("🚗 Día 17 (Oficina)", output_text)
        self.assertIn("Pruebas de AMRs para la vuelta", output_text)
        self.assertIn("[t] 📋 Tareas", output_text)
        self.assertIn("[p] 📁 Proyectos", output_text)

    def test_run_toggle_task(self):
        """Simula pulsar 'c', seleccionar tarea '1' y luego 'q' para salir."""
        inputs = ["c", "1", "q"]

        def mock_input(prompt=""):
            return inputs.pop(0)

        controller = DailyHubController(
            vault_root=self.tmp_dir,
            entity_manager=self.entity_manager,
            input_fn=mock_input,
            print_fn=self._mock_print
        )
        controller.active_day_number = 17

        result = controller.run()
        self.assertEqual(result, "exit")

        # Verificar que la tarea TSK-0010 cambió de estado
        task = self.entity_manager.tasks.get("TSK-0010")
        self.assertFalse(task.is_done)  # Antes estaba done, ahora es pending

    def test_run_toggle_task_by_direct_number(self):
        """Simula pulsar directamente '1' para marcar/desmarcar la primera tarea y luego 'q' para salir."""
        inputs = ["1", "q"]

        def mock_input(prompt=""):
            return inputs.pop(0)

        controller = DailyHubController(
            vault_root=self.tmp_dir,
            entity_manager=self.entity_manager,
            input_fn=mock_input,
            print_fn=self._mock_print
        )
        controller.active_day_number = 17

        result = controller.run()
        self.assertEqual(result, "exit")

        # Verificar que la tarea TSK-0010 cambió de estado
        task = self.entity_manager.tasks.get("TSK-0010")
        self.assertFalse(task.is_done)  # Antes estaba done, ahora es pending

    def test_run_switch_day(self):
        """Simula pulsar 's', elegir día 4 (día 20) y luego 'q'."""
        inputs = ["s", "4", "q"]

        def mock_input(prompt=""):
            return inputs.pop(0)

        controller = DailyHubController(
            vault_root=self.tmp_dir,
            entity_manager=self.entity_manager,
            input_fn=mock_input,
            print_fn=self._mock_print
        )

        result = controller.run()
        self.assertEqual(result, "exit")
        week, _ = controller._get_active_week_and_day()
        self.assertEqual(controller.active_day_number, week.days[3].day_number)

    def test_run_add_new_task(self):
        """Simula pulsar 't' (menú tareas), '1' (nueva tarea), escribir tarea, elegir proyecto 0 y salir."""
        inputs = ["t", "1", "Configurar nuevo endpoint en backend", "0", "q"]

        def mock_input(prompt=""):
            return inputs.pop(0)

        controller = DailyHubController(
            vault_root=self.tmp_dir,
            entity_manager=self.entity_manager,
            input_fn=mock_input,
            print_fn=self._mock_print
        )

        result = controller.run()
        self.assertEqual(result, "exit")

        # Verificar que se creó una tarea con ese título
        created = [t for t in self.entity_manager.tasks.values() if "Configurar nuevo endpoint" in t.title]
        self.assertEqual(len(created), 1)

    def test_run_add_jira_task(self):
        """Simula pulsar 'j', introducir código Jira, descripción, proyecto 0 y luego 'q'."""
        inputs = ["j", "ATLM-88888", "Ajustar timeout de conexión", "0", "q"]

        def mock_input(prompt=""):
            return inputs.pop(0)

        controller = DailyHubController(
            vault_root=self.tmp_dir,
            entity_manager=self.entity_manager,
            input_fn=mock_input,
            print_fn=self._mock_print
        )

        result = controller.run()
        self.assertEqual(result, "exit")

        # Verificar definición y tarea
        jira_def = self.entity_manager.definitions.get("[🎫ATLM-88888]")
        self.assertIsNotNone(jira_def)
        created = [t for t in self.entity_manager.tasks.values() if "[🎫ATLM-88888]" in t.title]
        self.assertEqual(len(created), 1)

    def test_run_add_note(self):
        """Simula pulsar 'm', introducir título, viñeta, fin de viñetas, proyecto 0 y luego 'q'."""
        inputs = [
            "m",
            "2",  # Opción [2] Alta: Crear Nueva Nota en NoteCrudController
            "Revisión de Arquitectura",
            "Revisión con equipo completada sin bloqueos",
            "",
            "0",
            "",   # Enter confirmación
            "0",  # Volver de NoteCrudController
            "q"   # Salir de DailyHubController
        ]

        def mock_input(prompt=""):
            return inputs.pop(0)

        controller = DailyHubController(
            vault_root=self.tmp_dir,
            entity_manager=self.entity_manager,
            input_fn=mock_input,
            print_fn=self._mock_print
        )

        result = controller.run()
        self.assertEqual(result, "exit")

        created = [n for n in self.entity_manager.notes.values() if n.title == "Revisión de Arquitectura"]
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].content, ["Revisión con equipo completada sin bloqueos"])

    def test_run_navigate_to_main_menu(self):
        """Simula pulsar 'b' para ir al menú principal."""
        inputs = ["b"]

        def mock_input(prompt=""):
            return inputs.pop(0)

        controller = DailyHubController(
            vault_root=self.tmp_dir,
            entity_manager=self.entity_manager,
            input_fn=mock_input,
            print_fn=self._mock_print
        )

        result = controller.run()
        self.assertEqual(result, "menu")

    def test_run_add_topic(self):
        """Simula pulsar 't' (menú tareas), '5' (crear topic), definir texto y salir con 'q'."""
        inputs = [
            "t",
            "5",
            "Definir estrategia Q3 para métricas",
            "0",  # Sin proyecto
            "",   # Enter confirmación
            "q"   # Salir
        ]

        def mock_input(prompt=""):
            return inputs.pop(0)

        controller = DailyHubController(
            vault_root=self.tmp_dir,
            entity_manager=self.entity_manager,
            input_fn=mock_input,
            print_fn=self._mock_print
        )
        active_week, _ = controller._get_active_week_and_day()

        result = controller.run()
        self.assertEqual(result, "exit")

        reloaded_week = self.entity_manager.load_week(active_week.year, active_week.week_number, reload=True)
        matching_topics = [top_id for top_id in reloaded_week.topic_ids if self.entity_manager.topics[top_id].title == "Definir estrategia Q3 para métricas"]
        self.assertEqual(len(matching_topics), 1)
        matching_tasks = [t for t in self.entity_manager.tasks.values() if t.title == "Definir estrategia Q3 para métricas"]
        self.assertEqual(len(matching_tasks), 0)

    def test_run_schedule_topic_to_today(self):
        """Simula pulsar 'a', agendar un topic existente a hoy y salir con 'q'."""
        controller = DailyHubController(
            vault_root=self.tmp_dir,
            entity_manager=self.entity_manager,
            input_fn=lambda _: "",
            print_fn=self._mock_print
        )
        active_week, active_day = controller._get_active_week_and_day()
        topic_task = self.entity_manager.create_task(title="Topic para traer a hoy")
        self.entity_manager.add_topic_to_week(active_week, topic_task.id)

        available_topics = [
            self.entity_manager.tasks[tid] for tid in active_week.topics_task_ids
            if tid in self.entity_manager.tasks and self.entity_manager.tasks[tid].is_pending and tid not in active_day.task_ids
        ]
        topic_idx = [t.id for t in available_topics].index(topic_task.id) + 1

        inputs = [
            "a",
            str(topic_idx),  # Seleccionar topic recién creado
            "",              # Enter confirmación
            "q"              # Salir
        ]

        def mock_input(prompt=""):
            return inputs.pop(0)

        controller.input = mock_input
        result = controller.run()
        self.assertEqual(result, "exit")

        reloaded_week = self.entity_manager.load_week(active_week.year, active_week.week_number, reload=True)
        reloaded_day = next(d for d in reloaded_week.days if d.day_number == active_day.day_number)
        self.assertIn(topic_task.id, reloaded_day.task_ids)

    def test_run_add_weekend_intervention_day(self):
        """Simula seleccionar 's' y luego '+' para añadir un día de guardia/intervención a la semana."""
        controller = DailyHubController(
            vault_root=self.tmp_dir,
            entity_manager=self.entity_manager,
            input_fn=lambda _: "",
            print_fn=self._mock_print
        )
        active_week, active_day = controller._get_active_week_and_day()
        initial_day_count = len(active_week.days)

        inputs = [
            "s",             # Cambiar día activo
            "+",             # Añadir día de guardia
            "29",            # Número de día
            "1",             # 🛠️ Guardia / Intervención
            "",              # Enter confirmación
            "q"              # Salir
        ]

        def mock_input(prompt=""):
            return inputs.pop(0)

        controller.input = mock_input
        result = controller.run()
        self.assertEqual(result, "exit")

        reloaded_week = self.entity_manager.load_week(active_week.year, active_week.week_number, reload=True)
        self.assertEqual(len(reloaded_week.days), initial_day_count + 1)
        added_day = next((d for d in reloaded_week.days if d.day_number == 29), None)
        self.assertIsNotNone(added_day)
        self.assertEqual(added_day.location_emoji, "🛠️")
        self.assertEqual(added_day.location_note, "Intervención")

    def test_run_manual_sync_markdown_to_yaml(self):
        """Simula pulsar 'y' para arrancar la sincronización .md -> .yaml y luego 'q' para salir."""
        inputs = [
            "y",  # Sincronizar markdown a YAML
            "",   # Enter confirmación
            "q"   # Salir
        ]

        def mock_input(prompt=""):
            return inputs.pop(0)

        controller = DailyHubController(
            vault_root=self.tmp_dir,
            entity_manager=self.entity_manager,
            input_fn=mock_input,
            print_fn=self._mock_print
        )

        result = controller.run()
        self.assertEqual(result, "exit")
        output_text = "\n".join(self.output_lines)
        self.assertIn("Sincronizando Markdown (.md) ➔ Base de datos YAML", output_text)

    def test_run_edit_task(self):
        """Simula pulsar 't' (menú de tareas), '8' (editar tarea), seleccionar '1', escribir nuevo texto y salir con 'q'."""
        inputs = [
            "t",                          # Menú de tareas
            "8",                          # Opción 8: Editar tarea
            "1",                          # Tarea 1
            "Título editado de la tarea",  # Nuevo texto
            "n",                          # No cambiar proyecto
            "",                           # Enter continuar
            "q"                           # Salir
        ]

        def mock_input(prompt=""):
            return inputs.pop(0)

        controller = DailyHubController(
            vault_root=self.tmp_dir,
            entity_manager=self.entity_manager,
            input_fn=mock_input,
            print_fn=self._mock_print
        )
        controller.active_day_number = 17

        result = controller.run()
        self.assertEqual(result, "exit")

        week, day = controller._get_active_week_and_day()
        first_task_id = day.task_ids[0]
        task = self.entity_manager.tasks.get(first_task_id)
        self.assertEqual(task.title, "Título editado de la tarea")

    def test_run_create_definition(self):
        """Simula pulsar 'l' (definiciones), '1' (nueva Jira), indicar SUPPLY-18495 y luego salir."""
        inputs = [
            "l",             # Menú de definiciones
            "1",             # 1: Nueva Jira
            "SUPPLY-18495",  # Código Jira
            "",              # Enter para aceptar URL por defecto
            "",              # Enter confirmación (vuelve al Hub)
            "q"              # Salir del Hub
        ]

        def mock_input(prompt=""):
            return inputs.pop(0)

        controller = DailyHubController(
            vault_root=self.tmp_dir,
            entity_manager=self.entity_manager,
            input_fn=mock_input,
            print_fn=self._mock_print
        )

        result = controller.run()
        self.assertEqual(result, "exit")

        # Verificar que la definición existe en el EntityManager
        self.assertIn("[🎫SUPPLY-18495]", self.entity_manager.definitions)
        defn = self.entity_manager.definitions["[🎫SUPPLY-18495]"]
        self.assertEqual(defn.url, "https://mangospain.atlassian.net/browse/SUPPLY-18495")

    def test_render_week_default_definitions_section(self):
        """Verifica que la sección <!-- Definiciones --> siempre se incluye por defecto en la bitácora semanal."""
        from brackets.generators.bitacora_renderer import BitacoraRenderer
        week = self.entity_manager.load_week(2026, 34)
        rendered = BitacoraRenderer.render_week(week, self.entity_manager)
        self.assertIn("<!-- Definiciones -->", rendered)

    def test_run_launch_pomodoro_from_tasks_menu(self):
        """Simula pulsar 't' (tareas), '12' (Pomodoro timer), '0' (salir del timer) y 'q' (salir del hub)."""
        inputs = [
            "t",   # Submenú tareas
            "12",  # Opción 12: Pomodoro
            "0",   # Opción 0 del Pomodoro: Salir del timer
            "q"    # Salir del Hub
        ]

        def mock_input(prompt=""):
            return inputs.pop(0)

        controller = DailyHubController(
            vault_root=self.tmp_dir,
            entity_manager=self.entity_manager,
            input_fn=mock_input,
            print_fn=self._mock_print
        )

        result = controller.run()
        self.assertEqual(result, "exit")
        output_text = "\n".join(self.output_lines)
        self.assertIn("POMODORO TIMER", output_text)

    def test_run_cancel_task_from_hub(self):
        """Simula pulsar 'x' (cancelar/tachar tarea), seleccionar la tarea '1' y salir con 'q'."""
        inputs = [
            "x",   # Cancelar/tachar tarea
            "1",   # Tarea número 1
            "",    # Presiona Enter para continuar
            "q"    # Salir del Hub
        ]

        def mock_input(prompt=""):
            return inputs.pop(0)

        controller = DailyHubController(
            vault_root=self.tmp_dir,
            entity_manager=self.entity_manager,
            input_fn=mock_input,
            print_fn=self._mock_print
        )
        controller.active_day_number = 24
        week, active_day = controller._get_active_week_and_day()
        first_tid = active_day.task_ids[0]

        result = controller.run()
        self.assertEqual(result, "exit")

        # La primera tarea del día debe estar en estado 'cancelled'
        task = self.entity_manager.tasks[first_tid]
        self.assertTrue(task.is_cancelled)
        self.assertEqual(task.status, "cancelled")


if __name__ == "__main__":
    unittest.main()
