#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitarios para la interfaz y lógica de PomodoroRetroApp.
Cubre estética terminal, modo compacto HUD y controles retro.
"""

import unittest
from unittest.mock import MagicMock
import os
import shutil

from brackets.modules.pomodoro_retro_ui import PomodoroRetroApp, tk
from brackets.models.entities import Task
from brackets.managers.entity_manager import EntityManager


class TestPomodoroRetroUI(unittest.TestCase):
    """Pruebas de la aplicación Pomodoro Retro."""

    def setUp(self):
        self.test_dir = os.path.abspath("temp_test_retro_pomodoro")
        os.makedirs(os.path.join(self.test_dir, "data", "tables"), exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_retro_app_headless_components(self):
        """Verifica que la app se inicialice y cargue tareas correctamente si Tkinter está presente."""
        if tk is None:
            self.skipTest("Tkinter no disponible")

        # Crear tareas mock en data/
        mgr = EntityManager(os.path.join(self.test_dir, "data"))
        t1 = Task(id="TSK-0001", title="Preparar reporte", status="pending", project_id="PROJ_TEST")
        mgr.tasks[t1.id] = t1

        try:
            app = PomodoroRetroApp(vault_dir=self.test_dir, entity_manager=mgr)
            # Verificar tareas cargadas
            tasks = app._load_pending_tasks()
            self.assertGreaterEqual(len(tasks), 2)
            self.assertEqual(tasks[1]["id"], "TSK-0001")
            self.assertIn("Preparar reporte", tasks[1]["display"])

            # Probar acciones de timer y pet
            app.action_play_pause()
            self.assertTrue(app.engine.is_running)
            self.assertEqual(app.pet.emotion.value, "focus")

            # Pausar
            app.action_play_pause()
            self.assertTrue(app.engine.is_paused)
            self.assertEqual(app.pet.emotion.value, "sleep")

            # Reset
            app.action_reset()
            self.assertFalse(app.engine.is_running)
            self.assertEqual(app.pet.emotion.value, "idle")

            # Destruir ventana para no bloquear
            app.root.destroy()
        except tk.TclError:
            self.skipTest("TclError: sin entorno gráfico disponible")

    def test_retro_app_compact_mode_toggle(self):
        """Verifica que el modo compacto HUD oculte los controles grandes y muestre solo personaje, dígitos y barra."""
        if tk is None:
            self.skipTest("Tkinter no disponible")

        try:
            app = PomodoroRetroApp(vault_dir=self.test_dir)
            self.assertFalse(app.is_compact)
            self.assertEqual(app.btn_compact.cget("text"), "[-]")

            # Alternar a modo compacto HUD
            app.toggle_compact_mode()
            self.assertTrue(app.is_compact)
            self.assertEqual(app.btn_compact.cget("text"), "[+]")

            # En modo mini, widgets secundarios deben estar ocultos (unmapped)
            self.assertEqual(app.dialogue_frame.winfo_manager(), "")
            self.assertEqual(app.btn_grid.winfo_manager(), "")
            self.assertEqual(app.cmb_tasks.winfo_manager(), "")

            # Elementos esenciales deben permanecer visibles
            self.assertEqual(app.pet_container.winfo_manager(), "pack")
            self.assertEqual(app.canvas.winfo_manager(), "pack")
            self.assertEqual(app.lbl_digits.winfo_manager(), "pack")
            self.assertEqual(app.lbl_progress.winfo_manager(), "pack")

            # Restaurar a modo completo
            app.toggle_compact_mode()
            self.assertFalse(app.is_compact)
            self.assertEqual(app.btn_compact.cget("text"), "[-]")
            self.assertEqual(app.dialogue_frame.winfo_manager(), "pack")
            self.assertEqual(app.btn_grid.winfo_manager(), "pack")
            self.assertEqual(app.cmb_tasks.winfo_manager(), "pack")

            app.root.destroy()
        except tk.TclError:
            self.skipTest("TclError: sin entorno gráfico disponible")

    def test_hud_click_toggles_play_pause(self):
        """Verifica que hacer clic en el display digital o el personaje pause/reanude el temporizador."""
        if tk is None:
            self.skipTest("Tkinter no disponible")

        try:
            app = PomodoroRetroApp(vault_dir=self.test_dir)
            self.assertFalse(app.engine.is_running)

            # Clic HUD -> Inicia focus
            app._on_hud_clicked()
            self.assertTrue(app.engine.is_running)
            self.assertFalse(app.engine.is_paused)

            # Clic HUD -> Pausa
            app._on_hud_clicked()
            self.assertTrue(app.engine.is_paused)

            # Clic HUD -> Reanuda
            app._on_hud_clicked()
            self.assertFalse(app.engine.is_paused)

            app.root.destroy()
        except tk.TclError:
            self.skipTest("TclError: sin entorno gráfico disponible")

    def test_topmost_toggle(self):
        """Verifica la alternancia del estado Always-On-Top."""
        if tk is None:
            self.skipTest("Tkinter no disponible")

        try:
            app = PomodoroRetroApp(vault_dir=self.test_dir)
            self.assertTrue(app.is_topmost)

            app._toggle_topmost()
            self.assertFalse(app.is_topmost)

            app._toggle_topmost()
            self.assertTrue(app.is_topmost)

            app.root.destroy()
        except tk.TclError:
            self.skipTest("TclError: sin entorno gráfico disponible")


if __name__ == "__main__":
    unittest.main()
