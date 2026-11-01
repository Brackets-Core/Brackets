#!/usr/bin/env python3
"""Tests unitarios para la funcionalidad de descripciones de tareas en Brackets."""

import os
import unittest
import tempfile
import shutil

from brackets.models.entities import Task, WeekSchedule, DaySchedule
from brackets.utils.bitacora_parser import BitacoraMarkdownParser
from brackets.generators.bitacora_renderer import BitacoraRenderer
from brackets.managers.entity_manager import EntityManager
from brackets.managers.markdown_sync_service import MarkdownSyncService
from brackets.core.daily_hub_controller import DailyHubController


class TestTaskDescriptions(unittest.TestCase):
    """Verifica que las descripciones de tareas se parseen, sincronicen y rendericen fielmente."""

    def test_task_entity_description_serialization(self):
        """Verifica que la entidad Task guarde y recupere description en dict."""
        t = Task(
            id="TSK-9999",
            title="Tarea de prueba",
            description="Línea 1 de descripción\nLínea 2 de detalle"
        )
        d = t.to_dict()
        self.assertEqual(d["description"], "Línea 1 de descripción\nLínea 2 de detalle")

        loaded = Task.from_dict(d)
        self.assertEqual(loaded.description, "Línea 1 de descripción\nLínea 2 de detalle")

    def test_parser_extracts_task_description(self):
        """Verifica que BitacoraMarkdownParser extrae descripciones indentadas."""
        md_content = """# 🗓️Week 44

## 📋Week Tasks
  - [ ] Tarea Semanal
    - Descripción semanal línea 1
    - Descripción semanal línea 2
  - [ ] Tarea sin descripción

## 🚗28
  - [ ] Tarea diaria
    - Detalle puntual de la tarea
  - [x] Tarea hecha
    - Explicación de cómo se resolvió
"""
        sections = BitacoraMarkdownParser.parse_sections(md_content)

        # Verificar week tasks
        wt = sections["week_tasks"]
        self.assertEqual(len(wt), 2)
        status, title, t_type, desc = wt[0]
        self.assertEqual(title, "Tarea Semanal")
        self.assertEqual(desc, "Descripción semanal línea 1\nDescripción semanal línea 2")

        status2, title2, t_type2, desc2 = wt[1]
        self.assertEqual(title2, "Tarea sin descripción")
        self.assertIsNone(desc2)

        # Verificar day tasks
        day_tasks = sections["days"][28]
        self.assertEqual(len(day_tasks), 2)
        d_status, d_title, d_type, d_desc = day_tasks[0]
        self.assertEqual(d_title, "Tarea diaria")
        self.assertEqual(d_desc, "Detalle puntual de la tarea")

        d_status2, d_title2, d_type2, d_desc2 = day_tasks[1]
        self.assertEqual(d_title2, "Tarea hecha")
        self.assertEqual(d_desc2, "Explicación de cómo se resolvió")

    def test_bitacora_renderer_formats_task_description(self):
        """Verifica que BitacoraRenderer renderiza la descripción como sub-viñetas indentadas."""
        task = Task(
            id="TSK-0001",
            title="Implementar arquitectura Lego",
            description="Modularidad total\nSin acoplamiento duro"
        )
        formatted = BitacoraRenderer._format_task_line(task)
        expected = "  - [ ] Implementar arquitectura Lego\n    - Modularidad total\n    - Sin acoplamiento duro"
        self.assertEqual(formatted, expected)

    def test_bidirectional_sync_preserves_description(self):
        """Verifica ciclo completo: Markdown con descripción -> Sync YAML -> Render Markdown."""
        tmp_dir = tempfile.mkdtemp()
        try:
            data_dir = os.path.join(tmp_dir, "data")
            os.makedirs(os.path.join(data_dir, "tables"), exist_ok=True)
            os.makedirs(os.path.join(data_dir, "weeks"), exist_ok=True)

            mgr = EntityManager(data_dir)
            sync_service = MarkdownSyncService(mgr, tmp_dir)

            # Guardar semana base
            base_week = WeekSchedule(
                year=2026,
                month=10,
                week_number=44,
                days=[DaySchedule(day_number=28, location_emoji="🏠", location_note=None, task_ids=[])],
                topics_task_ids=[],
                note_ids=[]
            )
            mgr.save_week(base_week)

            md_file = os.path.join(tmp_dir, "[2026][10]Week44.md")
            original_md = """# 🗓️Week 44

## 🎯Topics
  - 

## 📋Week Tasks
  - [ ] Migrar esquema DB
    - Crear tabla de auditoría
    - Ejecutar scripts de migración

## 📝Notes
  - 

## 🏠28
  - [ ] Configurar servidor
    - Añadir variables de entorno .env

## Definiciones
<!-- Definiciones -->
"""
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(original_md)

            # Sync Markdown -> YAML
            synced = sync_service.sync_week_from_markdown(md_file, 2026, 44)
            self.assertTrue(synced)

            # Verificar que en el manager las tareas tienen su descripción
            tasks = list(mgr.tasks.values())
            t_migrar = next((t for t in tasks if "Migrar esquema DB" in t.title), None)
            self.assertIsNotNone(t_migrar)
            self.assertEqual(t_migrar.description, "Crear tabla de auditoría\nEjecutar scripts de migración")

            t_server = next((t for t in tasks if "Configurar servidor" in t.title), None)
            self.assertIsNotNone(t_server)
            self.assertEqual(t_server.description, "Añadir variables de entorno .env")

            # Render YAML -> Markdown
            week = mgr.load_week(2026, 44)
            rendered = BitacoraRenderer.render_week(week, mgr)

            self.assertIn("- [ ] Migrar esquema DB\n    - Crear tabla de auditoría\n    - Ejecutar scripts de migración", rendered)
            self.assertIn("- [ ] Configurar servidor\n    - Añadir variables de entorno .env", rendered)

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_daily_hub_renders_description_with_chat_bubble(self):
        """Verifica que el dashboard del Daily Hub muestra la descripción con icono."""
        tmp_dir = tempfile.mkdtemp()
        try:
            data_dir = os.path.join(tmp_dir, "data")
            os.makedirs(os.path.join(data_dir, "tables"), exist_ok=True)
            os.makedirs(os.path.join(data_dir, "weeks"), exist_ok=True)

            mgr = EntityManager(data_dir)
            week = WeekSchedule(year=2026, week_number=44, month=10)
            day = DaySchedule(day_number=28, location_emoji="🏠")
            week.days.append(day)
            mgr.save_week(week)

            task = mgr.create_task(
                title="Refactorizar parser",
                year=2026,
                week_num=44,
                day_number=28,
                description="Soportar sub-bullets de descripción"
            )

            outputs = []
            hub = DailyHubController(
                entity_manager=mgr,
                vault_root=tmp_dir,
                input_fn=lambda prompt="": "",
                print_fn=lambda *args: outputs.append(" ".join(str(a) for a in args)),
            )

            hub.render_dashboard(week, day)
            output_text = "\n".join(outputs)
            self.assertIn("Refactorizar parser", output_text)
            self.assertIn("💬 Soportar sub-bullets de descripción", output_text)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
