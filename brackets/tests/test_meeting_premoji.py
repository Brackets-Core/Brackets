#!/usr/bin/env python3
"""
Tests para tipos de tarea y premojis (prefijo + emoji), enfocado en 'meeting' (🫱🏼‍🫲🏽 / Reunión:)
y su arquitectura extensible (TaskTypeRegistry).
"""

import os
import shutil
import tempfile
import unittest

from brackets.models.entities import Task, WeekSchedule, DaySchedule
from brackets.models.task_types import TaskTypeRegistry, TaskTypeSpec
from brackets.managers.entity_manager import EntityManager
from brackets.generators.bitacora_renderer import BitacoraRenderer
from brackets.managers.markdown_sync_service import MarkdownSyncService


class TestMeetingPremojiAndTaskTypes(unittest.TestCase):
    """Pruebas de detección, renderizado y sincronización bidireccional de tipos de tarea y premojis."""

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

    def test_task_type_registry_detection(self):
        """Valida que TaskTypeRegistry detecte tipo 'meeting' y limpie el título adecuadamente."""
        # Prefijo textual con tilde y sin tilde
        t_type, clean = TaskTypeRegistry.detect_task_type_and_clean_title("Reunión: Preparar evento de Impulse")
        self.assertEqual(t_type, "meeting")
        self.assertEqual(clean, "Preparar evento de Impulse")

        t_type, clean = TaskTypeRegistry.detect_task_type_and_clean_title("reunion: Sync semanal")
        self.assertEqual(t_type, "meeting")
        self.assertEqual(clean, "Sync semanal")

        # Premoji directo (multicarácter de tono de piel)
        t_type, clean = TaskTypeRegistry.detect_task_type_and_clean_title("🫱🏼‍🫲🏽 Preparar evento de Impulse")
        self.assertEqual(t_type, "meeting")
        self.assertEqual(clean, "Preparar evento de Impulse")

        # Premoji sin espacio
        t_type, clean = TaskTypeRegistry.detect_task_type_and_clean_title("🫱🏼‍🫲🏽Preparar evento de Impulse")
        self.assertEqual(t_type, "meeting")
        self.assertEqual(clean, "Preparar evento de Impulse")

        # Alias emoji simple
        t_type, clean = TaskTypeRegistry.detect_task_type_and_clean_title("🤝 1:1 con Manager")
        self.assertEqual(t_type, "meeting")
        self.assertEqual(clean, "1:1 con Manager")

        # Tarea estándar
        t_type, clean = TaskTypeRegistry.detect_task_type_and_clean_title("Actualizar documentación OpenAPI")
        self.assertEqual(t_type, "task")
        self.assertEqual(clean, "Actualizar documentación OpenAPI")

    def test_task_type_registry_extensibility(self):
        """Valida que el registro sea extensible a futuros tipos de tareas (ej: bug, spike)."""
        # Registrar un tipo custom 'bug'
        TaskTypeRegistry.register_type(TaskTypeSpec(
            name="bug",
            premoji="🐛",
            label="Bug",
            aliases=["🐞"],
            text_prefixes=["bug:", "defecto:"]
        ))

        t_type, clean = TaskTypeRegistry.detect_task_type_and_clean_title("Bug: Error 500 al autenticar")
        self.assertEqual(t_type, "bug")
        self.assertEqual(clean, "Error 500 al autenticar")

        formatted = TaskTypeRegistry.format_title_with_premoji("Error 500 al autenticar", "bug")
        self.assertEqual(formatted, "🐛 Error 500 al autenticar")

    def test_task_types_yaml_loading(self):
        """Valida que los tipos de tareas se puedan definir, cargar y modificar desde un archivo YAML sin tocar código."""
        yaml_path = os.path.join(self.tmp_dir, "custom_task_types.yaml")

        # 1. Si no existe, load_from_yaml genera la plantilla por defecto
        self.assertFalse(os.path.exists(yaml_path))
        ok = TaskTypeRegistry.load_from_yaml(yaml_path)
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(yaml_path))

        # 2. Modificar el YAML agregando tipos personalizados (bug y spike)
        custom_yaml = """task_types:
  - key: meeting
    label: Reunión
    premoji: "🫱🏼‍🫲🏽"
    text_prefixes:
      - "reunión:"
    emoji_aliases:
      - "🤝"

  - key: task
    label: Tarea
    premoji: ""

  - key: bug
    label: Incidencia
    premoji: "🐛"
    text_prefixes:
      - "bug:"
      - "error:"
    emoji_aliases:
      - "🐛"
      - "🐞"

  - key: spike
    label: Investigación
    premoji: "🔬"
    text_prefixes:
      - "spike:"
    emoji_aliases:
      - "🔬"
"""
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(custom_yaml)

        ok_reload = TaskTypeRegistry.load_from_yaml(yaml_path)
        self.assertTrue(ok_reload)

        # 3. Detectar 'bug' por prefijo textual y por premoji
        t_type, clean = TaskTypeRegistry.detect_task_type_and_clean_title("Bug: Fallo en pasarela de pago")
        self.assertEqual(t_type, "bug")
        self.assertEqual(clean, "Fallo en pasarela de pago")

        t_type, clean = TaskTypeRegistry.detect_task_type_and_clean_title("🐛 Fallo en pasarela de pago")
        self.assertEqual(t_type, "bug")
        self.assertEqual(clean, "Fallo en pasarela de pago")

        # 4. Detectar 'spike'
        t_type, clean = TaskTypeRegistry.detect_task_type_and_clean_title("spike: Evaluar PostgreSQL 17")
        self.assertEqual(t_type, "spike")
        self.assertEqual(clean, "Evaluar PostgreSQL 17")

        # 5. Formatear con premoji
        formatted = TaskTypeRegistry.format_title_with_premoji("Fallo en pasarela de pago", "bug")
        self.assertEqual(formatted, "🐛 Fallo en pasarela de pago")

    def test_task_entity_premoji_properties(self):
        """Valida las propiedades computadas premoji y formatted_title en la entidad Task."""
        t_meeting = Task(id="TSK-001", title="Preparar evento", task_type="meeting")
        self.assertEqual(t_meeting.premoji, "🫱🏼‍🫲🏽")
        self.assertEqual(t_meeting.formatted_title, "🫱🏼‍🫲🏽 Preparar evento")

        t_normal = Task(id="TSK-002", title="Revisar PR", task_type="task")
        self.assertEqual(t_normal.premoji, "")
        self.assertEqual(t_normal.formatted_title, "Revisar PR")

    def test_bitacora_renderer_with_meetings(self):
        """Valida que BitacoraRenderer renderice tareas tipo meeting con premojis en todos los estados."""
        task_pending = Task(id="TSK-001", title="Reunión Sprint Planning", task_type="meeting", status="pending")
        task_done = Task(id="TSK-002", title="Daily Sync", task_type="meeting", status="done")
        task_cancelled = Task(id="TSK-003", title="Alineación Cliente", task_type="meeting", status="cancelled")

        line_p = BitacoraRenderer._format_task_line(task_pending)
        self.assertEqual(line_p, "  - [ ] 🫱🏼‍🫲🏽 Reunión Sprint Planning")

        line_d = BitacoraRenderer._format_task_line(task_done)
        self.assertEqual(line_d, "  - [x] 🫱🏼‍🫲🏽 Daily Sync")

        line_c = BitacoraRenderer._format_task_line(task_cancelled)
        self.assertEqual(line_c, "  - [ ] ~~🫱🏼‍🫲🏽 Alineación Cliente~~")

    def test_markdown_sync_creates_clean_task_with_meeting_type(self):
        """
        Valida que al escribir 'Reunión: ...' o '🫱🏼‍🫲🏽 ...' en el Markdown:
        1. Se guarde el título limpio sin 'Reunión:' ni premoji en la BD.
        2. Se guarde task_type='meeting'.
        3. Al renderizar, el archivo Markdown se reemplace con '🫱🏼‍🫲🏽 <Título>'.
        """
        sync_service = MarkdownSyncService(self.manager, self.tmp_dir)
        md_file = os.path.join(self.tmp_dir, "2026-W39.md")

        # Asegurar que la semana existe en el manager
        week_init = WeekSchedule(
            year=2026,
            month=9,
            week_number=39,
            days=[
                DaySchedule(day_number=23, location_emoji="🏠", location_note=None, task_ids=[])
            ],
            week_task_ids=[],
            topics_task_ids=[],
            note_ids=[]
        )
        self.manager.save_week(week_init)

        content = """# 📅 Bitácora: 2026-W39

## 📋Tareas de la Semana
- [ ] Reunión: Preparar evento de Impulse
- [ ] Tarea normal de semana

## 🏠23
- [ ] 🫱🏼‍🫲🏽 Daily S^3
- [ ] Reunión: Sync con Arquitectura
- [x] 🫱🏼‍🫲🏽 Retrospectiva de equipo
- [ ] ~~Reunión: Demo cancelada~~
"""
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(content)

        # Sincronizar hacia BD
        ok = sync_service.sync_week_from_markdown(md_file, year=2026, week_num=39)
        self.assertTrue(ok)

        # Verificar tareas en la BD
        # 1. Preparar evento de Impulse (Week Task)
        t_impulse = next((t for t in self.manager.tasks.values() if t.title == "Preparar evento de Impulse"), None)
        self.assertIsNotNone(t_impulse, "La tarea debe guardarse con título limpio sin 'Reunión:'")
        self.assertEqual(t_impulse.task_type, "meeting")
        self.assertTrue(t_impulse.is_pending)

        # 2. Daily S^3 (Día 23)
        day_23 = next((d for d in week_init.days if d.day_number == 23), None)
        self.assertIsNotNone(day_23)
        t_daily = next((self.manager.tasks[tid] for tid in day_23.task_ids if self.manager.tasks[tid].title == "Daily S^3"), None)
        self.assertIsNotNone(t_daily, "La tarea debe guardarse con título limpio sin '🫱🏼‍🫲🏽'")
        self.assertEqual(t_daily.task_type, "meeting")

        # 3. Sync con Arquitectura (Día 23 con prefijo textual)
        t_sync = next((t for t in self.manager.tasks.values() if t.title == "Sync con Arquitectura"), None)
        self.assertIsNotNone(t_sync, "Debe guardarse con título limpio")
        self.assertEqual(t_sync.task_type, "meeting")

        # 4. Retrospectiva de equipo (Done)
        t_retro = next((t for t in self.manager.tasks.values() if t.title == "Retrospectiva de equipo"), None)
        self.assertIsNotNone(t_retro)
        self.assertEqual(t_retro.task_type, "meeting")
        self.assertTrue(t_retro.is_done)

        # 5. Demo cancelada (Cancelled)
        t_demo = next((t for t in self.manager.tasks.values() if t.title == "Demo cancelada"), None)
        self.assertIsNotNone(t_demo)
        self.assertEqual(t_demo.task_type, "meeting")
        self.assertTrue(t_demo.is_cancelled)

        # Sincronizar de BD hacia Markdown (Renderizar)
        week = self.manager.weeks.get("2026-W39")
        self.assertIsNotNone(week)
        ok_render = BitacoraRenderer.render_and_save_week(week, self.manager, md_file)
        self.assertTrue(ok_render)

        with open(md_file, "r", encoding="utf-8") as f:
            rendered_content = f.read()

        # En el archivo Markdown resultante:
        # Se debe haber reemplazado 'Reunión:' por '🫱🏼‍🫲🏽'
        self.assertIn("- [ ] 🫱🏼‍🫲🏽 Preparar evento de Impulse", rendered_content)
        self.assertIn("- [ ] 🫱🏼‍🫲🏽 Daily S^3", rendered_content)
        self.assertIn("- [ ] 🫱🏼‍🫲🏽 Sync con Arquitectura", rendered_content)
        self.assertIn("- [x] 🫱🏼‍🫲🏽 Retrospectiva de equipo", rendered_content)
        self.assertIn("- [ ] ~~🫱🏼‍🫲🏽 Demo cancelada~~", rendered_content)
        # Y NO debe existir el prefijo textual antiguo 'Reunión:'
        self.assertNotIn("Reunión: Preparar evento", rendered_content)
        self.assertNotIn("Reunión: Sync con Arquitectura", rendered_content)


if __name__ == "__main__":
    unittest.main()
