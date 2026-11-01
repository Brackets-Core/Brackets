#!/usr/bin/env python3
"""Tests unitarios para menús declarativos y submenús configurables en YAML."""

import os
import tempfile
import unittest
import yaml

from brackets.core.menu_engine import MenuEngine
from brackets.core.menu_navigator import MenuOption
from brackets.core.daily_hub_controller import DailyHubController
from brackets.core.recurring_controller import RecurringTasksController
from brackets.core.definitions_controller import DefinitionsController
from brackets.managers.entity_manager import EntityManager
from brackets.models.entities import WeekSchedule, DaySchedule


class TestDeclarativeSubmenus(unittest.TestCase):
    """Valida la carga declarativa de submenús desde menu_config.yaml."""

    def test_get_menu_options_from_yaml(self):
        """Verifica que MenuEngine convierta items de YAML en MenuOption."""
        with tempfile.TemporaryDirectory() as tmp_vault:
            data_dir = os.path.join(tmp_vault, "data")
            os.makedirs(data_dir, exist_ok=True)
            custom_menu = {
                "menus": {
                    "custom_sub": {
                        "title": "Submenú Personalizado",
                        "items": [
                            {
                                "id": "action_one",
                                "label": "Primera Acción",
                                "keys": ["1", "a", "one"],
                                "action": "exec",
                                "command": "cmd_one",
                            },
                            {
                                "id": "action_two",
                                "label": "Segunda Acción",
                                "keys": ["2"],
                                "action": "exec",
                                "command": "cmd_two",
                            },
                        ],
                    }
                }
            }
            with open(os.path.join(data_dir, "menu_config.yaml"), "w", encoding="utf-8") as f:
                yaml.safe_dump(custom_menu, f)

            engine = MenuEngine(tmp_vault)
            opts = engine.get_menu_options("custom_sub")

            self.assertEqual(len(opts), 2)
            self.assertEqual(opts[0].key, "1")
            self.assertEqual(opts[0].label, "Primera Acción")
            self.assertEqual(opts[0].action_id, "cmd_one")
            self.assertEqual(opts[0].aliases, ["a", "one"])

            self.assertEqual(opts[1].key, "2")
            self.assertEqual(opts[1].label, "Segunda Acción")
            self.assertEqual(opts[1].action_id, "cmd_two")
            self.assertEqual(opts[1].aliases, [])

    def test_get_menu_options_fallback_when_missing(self):
        """Verifica que se usen default_options si el submenú no existe en YAML."""
        with tempfile.TemporaryDirectory() as tmp_vault:
            data_dir = os.path.join(tmp_vault, "data")
            os.makedirs(data_dir, exist_ok=True)
            empty_menu = {"menus": {}}
            with open(os.path.join(data_dir, "menu_config.yaml"), "w", encoding="utf-8") as f:
                yaml.safe_dump(empty_menu, f)

            engine = MenuEngine(tmp_vault)
            defaults = [
                MenuOption("1", "Default Option", "default_action", aliases=["d"])
            ]
            opts = engine.get_menu_options("non_existent_menu", default_options=defaults)
            self.assertEqual(len(opts), 1)
            self.assertEqual(opts[0].key, "1")
            self.assertEqual(opts[0].action_id, "default_action")

    def test_submenus_in_engine_menu_config(self):
        """Verifica que brackets/data/menu_config.yaml contenga daily_tasks, recurring, definitions, sync_markdown."""
        engine_root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
        engine = MenuEngine(engine_root)
        
        daily_opts = engine.get_menu_options("daily_tasks")
        self.assertGreaterEqual(len(daily_opts), 10)
        action_ids = [opt.action_id for opt in daily_opts]
        self.assertIn("new_task", action_ids)
        self.assertIn("jira_task", action_ids)
        self.assertIn("toggle_task", action_ids)
        self.assertIn("delete_task", action_ids)

        rec_opts = engine.get_menu_options("recurring")
        self.assertEqual(len(rec_opts), 4)
        rec_action_ids = [opt.action_id for opt in rec_opts]
        self.assertIn("new_rec", rec_action_ids)

        def_opts = engine.get_menu_options("definitions")
        self.assertEqual(len(def_opts), 4)
        def_action_ids = [opt.action_id for opt in def_opts]
        self.assertIn("new_jira_def", def_action_ids)

        sync_opts = engine.get_menu_options("sync_markdown")
        self.assertEqual(len(sync_opts), 2)
        sync_action_ids = [opt.action_id for opt in sync_opts]
        self.assertIn("sync_specific_week", sync_action_ids)

    def test_daily_hub_uses_custom_daily_tasks_menu(self):
        """Valida que DailyHubController use las opciones de daily_tasks configuradas en el vault."""
        with tempfile.TemporaryDirectory() as tmp_vault:
            data_dir = os.path.join(tmp_vault, "data")
            os.makedirs(os.path.join(data_dir, "tables"), exist_ok=True)
            os.makedirs(os.path.join(data_dir, "weeks"), exist_ok=True)

            custom_menu = {
                "menus": {
                    "daily_tasks": {
                        "title": "Tareas Personalizadas",
                        "items": [
                            {
                                "id": "custom_action",
                                "label": "Acción Rápida",
                                "keys": ["x"],
                                "action": "exec",
                                "command": "cancel_task",
                            }
                        ]
                    }
                }
            }
            with open(os.path.join(data_dir, "menu_config.yaml"), "w", encoding="utf-8") as f:
                yaml.safe_dump(custom_menu, f)

            mgr = EntityManager(data_dir)
            hub = DailyHubController(
                vault_root=tmp_vault,
                entity_manager=mgr,
                input_fn=lambda prompt="": "x",
                read_single_key_fn=lambda prompt="": "0",  # vuelve con back
                print_fn=lambda *a, **k: None,
            )
            
            week = WeekSchedule(year=2026, month=9, week_number=39)
            day = DaySchedule(day_number=1)
            week.days.append(day)

            # Debe ejecutar manage_tasks_menu y regresar 'back' sin error
            result = hub.manage_tasks_menu(week, day, [])
            self.assertEqual(result, "back")


if __name__ == "__main__":
    unittest.main()
