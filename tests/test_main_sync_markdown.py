#!/usr/bin/env python3
"""Tests unitarios para la sincronización Markdown -> YAML desde el Menú Principal."""

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from main import BitacoraManager


class TestMainSyncMarkdown(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.mock_source = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "mock"
        )
        self.mock_data_dir = os.path.join(self.tmp_dir, "data")
        shutil.copytree(self.mock_source, self.mock_data_dir)

        # Crear archivos markdown simulados en el vault temporal
        self.w34_md = os.path.join(self.tmp_dir, "[2026][08]Week34.md")
        with open(self.w34_md, "w", encoding="utf-8") as f:
            f.write("# 🗓️Week 34\n\n## 🚗17 (Oficina)\n  - [x] Tarea de prueba semana 34\n\n<!-- Definiciones -->\n")

        self.w35_md = os.path.join(self.tmp_dir, "[2026][08]Week35.md")
        with open(self.w35_md, "w", encoding="utf-8") as f:
            f.write("# 🗓️Week 35\n\n## 🚗24 (Oficina)\n  - [ ] Tarea de prueba semana 35\n\n<!-- Definiciones -->\n")

        self.manager = BitacoraManager(self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_sync_specific_week_interactive(self):
        """Prueba sincronizar una semana específica seleccionándola por número."""
        inputs = [
            "34",  # Escribir semana 34
            ""     # Enter continuar
        ]
        with patch("builtins.input", side_effect=inputs), patch("main.clear_screen"):
            hub = self.manager._get_daily_hub_controller()
            from managers.markdown_sync_service import MarkdownSyncService
            service = MarkdownSyncService(hub.manager, self.tmp_dir)
            self.manager._sync_specific_week_interactive(service, hub)

        # Verificar que la tarea de semana 34 fue importada
        matching = [t for t in hub.manager.tasks.values() if t.title == "Tarea de prueba semana 34"]
        self.assertEqual(len(matching), 1)
        self.assertTrue(matching[0].is_done)

    def test_sync_all_weeks_interactive(self):
        """Prueba sincronizar todas las semanas del vault."""
        inputs = [
            "s",  # Confirmar sincronización de todas
            ""    # Enter continuar
        ]
        with patch("builtins.input", side_effect=inputs), patch("main.clear_screen"):
            hub = self.manager._get_daily_hub_controller()
            from managers.markdown_sync_service import MarkdownSyncService
            service = MarkdownSyncService(hub.manager, self.tmp_dir)
            self.manager._sync_all_weeks_interactive(service, hub)

        # Verificar que ambas tareas se sincronizaron
        t34 = [t for t in hub.manager.tasks.values() if t.title == "Tarea de prueba semana 34"]
        t35 = [t for t in hub.manager.tasks.values() if t.title == "Tarea de prueba semana 35"]
        self.assertEqual(len(t34), 1)
        self.assertEqual(len(t35), 1)


if __name__ == "__main__":
    unittest.main()
