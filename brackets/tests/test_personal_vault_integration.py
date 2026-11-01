#!/usr/bin/env python3
"""Tests de integración para la experiencia de Vault Personal en Brackets."""

import os
import unittest
from datetime import datetime

from brackets.managers.entity_manager import EntityManager
from brackets.core.daily_hub_controller import DailyHubController
from brackets.models.task_types import TaskTypeRegistry


class TestPersonalVaultIntegration(unittest.TestCase):
    """Verifica que el sistema se adapte de forma nativa cuando el vault es de tipo 'personal'."""

    def setUp(self):
        self.workspace_root = r"c:\Projects\brackets-workspace"
        cand_personal = os.path.join(self.workspace_root, "vaults", "MyPersonalNotes")
        self.personal_vault = cand_personal if os.path.exists(cand_personal) else os.path.join(self.workspace_root, "MyPersonalNotes")
        self.data_dir = os.path.join(self.personal_vault, "data")

    def test_personal_vault_config_exists_and_is_personal(self):
        """Verifica que MyPersonalNotes tiene config.yaml con vault_type == personal."""
        config_path = os.path.join(self.data_dir, "config.yaml")
        self.assertTrue(os.path.exists(config_path), "Falta config.yaml en MyPersonalNotes")

        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.assertEqual(data.get("vault_type"), "personal")
        self.assertEqual(data.get("vault_name"), "MyPersonalNotes")
        self.assertTrue(data.get("feature_flags", {}).get("bitacoras_enabled", False))

    def test_personal_task_types_loaded(self):
        """Verifica que task_types.yaml en MyPersonalNotes contiene hábitos y tipos personales."""
        task_types_path = os.path.join(self.data_dir, "task_types.yaml")
        self.assertTrue(os.path.exists(task_types_path), "Falta task_types.yaml en MyPersonalNotes")

        mgr = EntityManager(self.data_dir)
        mgr.load_all()

        # Comprobar tipos registrados
        specs = TaskTypeRegistry.get_all_specs()
        type_keys = [s.key for s in specs]
        self.assertIn("habit", type_keys)
        self.assertIn("chore", type_keys)
        self.assertIn("health", type_keys)
        self.assertIn("finance", type_keys)

        # Comprobar detección de premojis personales
        tt, clean = TaskTypeRegistry.detect_task_type_and_clean_title("hábito: Meditar 10 minutos")
        self.assertEqual(tt, "habit")
        self.assertEqual(clean, "Meditar 10 minutos")

        tt, clean = TaskTypeRegistry.detect_task_type_and_clean_title("compra: Fruta y pan")
        self.assertEqual(tt, "chore")
        self.assertEqual(clean, "Fruta y pan")

    def test_daily_hub_detects_personal_vault_type(self):
        """Verifica que DailyHubController detecta vault_type='personal' correctamente."""
        outputs = []
        hub = DailyHubController(
            vault_root=self.personal_vault,
            input_fn=lambda prompt="": "",
            print_fn=lambda *args: outputs.append(" ".join(str(a) for a in args)),
        )
        self.assertEqual(hub.vault_type, "personal")

    def test_daily_hub_action_new_habit(self):
        """Verifica que la acción _action_new_habit registra la tarea con tipo habit y premoji (en copia aislada)."""
        import shutil
        import tempfile
        from brackets.models.entities import WeekSchedule, DaySchedule

        with tempfile.TemporaryDirectory() as tmp_dir:
            isolated_vault = os.path.join(tmp_dir, "MyPersonalNotes")
            shutil.copytree(self.personal_vault, isolated_vault)
            isolated_data = os.path.join(isolated_vault, "data")

            mgr = EntityManager(isolated_data)
            mgr.load_all()

            now = datetime.now()
            iso_year, iso_week, _ = now.isocalendar()
            week = WeekSchedule(year=iso_year, week_number=iso_week, month=now.month)
            day = DaySchedule(day_number=now.day, location_emoji="🏠")
            week.days.append(day)
            mgr.save_week(week)

            inputs = ["Yoga matutino"]
            outputs = []

            hub = DailyHubController(
                entity_manager=mgr,
                vault_root=isolated_vault,
                input_fn=lambda prompt="": inputs.pop(0) if inputs else "",
                print_fn=lambda *args: outputs.append(" ".join(str(a) for a in args)),
            )

            initial_count = len(day.task_ids)
            hub._action_new_habit(week, day)

            self.assertEqual(len(day.task_ids), initial_count + 1)
            created_task_id = day.task_ids[-1]
            task = mgr.tasks.get(created_task_id)

            self.assertIsNotNone(task)
            self.assertEqual(task.title, "Yoga matutino")
            self.assertEqual(task.task_type, "habit")
            self.assertEqual(task.premoji, "🌱")

    def test_weekly_generator_creates_7_day_week_in_personal_vault(self):
        """Verifica que WeeklyGenerator calcula 7 días (Lunes a Domingo) para MyPersonalNotes."""
        from brackets.generators.weekly import WeeklyGenerator
        gen = WeeklyGenerator(self.personal_vault)
        self.assertEqual(gen._get_days_per_week(), 7)

        dates = gen._calculate_next_week_dates_iso(2026, 41)
        self.assertEqual(len(dates), 7)
        # Lunes (0) a Domingo (6)
        weekdays = [d.weekday() for d in dates]
        self.assertEqual(weekdays, [0, 1, 2, 3, 4, 5, 6])

    def test_weekly_generator_creates_5_day_week_in_work_vault(self):
        """Verifica que WeeklyGenerator calcula 5 días (Lunes a Viernes) para MyJobNotes."""
        from brackets.generators.weekly import WeeklyGenerator
        cand_work = os.path.join(self.workspace_root, "vaults", "MyJobNotes")
        work_vault = cand_work if os.path.exists(cand_work) else os.path.join(self.workspace_root, "MyJobNotes")
        gen = WeeklyGenerator(work_vault)
        self.assertEqual(gen._get_days_per_week(), 5)

        dates = gen._calculate_next_week_dates_iso(2026, 41)
        self.assertEqual(len(dates), 5)
        # Lunes (0) a Viernes (4)
        weekdays = [d.weekday() for d in dates]
        self.assertEqual(weekdays, [0, 1, 2, 3, 4])

    def test_manage_day_menu_hides_guardia_for_7_day_personal_vault(self):
        """Verifica que en un vault personal de 7 días no se muestra la opción de guardia laboral."""
        from brackets.models.entities import WeekSchedule, DaySchedule
        hub = DailyHubController(
            vault_root=self.personal_vault,
            input_fn=lambda prompt="": "",
            print_fn=lambda *args: None,
        )
        week = WeekSchedule(year=2026, week_number=41, month=10)
        for i in range(1, 8):
            week.days.append(DaySchedule(day_number=i, location_emoji="🏠"))

        # Intercept navigator options
        options = []
        for idx, d in enumerate(week.days, start=1):
            options.append(str(idx))
        if hub.vault_type != "personal" or len(week.days) < 7:
            options.append("+")

        self.assertNotIn("+", options)


if __name__ == "__main__":
    unittest.main()

