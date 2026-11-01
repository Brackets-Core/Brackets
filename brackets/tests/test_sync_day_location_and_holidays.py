"""Tests para verificar que los cambios de ubicación, vacaciones y notas en los días se sincronizan y no se pierden."""

import os
import shutil
import tempfile
import unittest
from datetime import datetime

from brackets.managers.entity_manager import EntityManager
from brackets.managers.settings_manager import SettingsManager
from brackets.managers.markdown_sync_service import MarkdownSyncService
from brackets.models.entities import WeekSchedule, DaySchedule
from brackets.generators.bitacora_renderer import BitacoraRenderer


class TestSyncDayLocationAndHolidays(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.test_dir, "data")
        os.makedirs(os.path.join(self.data_dir, "tables"), exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, "weeks"), exist_ok=True)
        self.em = EntityManager(self.data_dir)
        self.sm = SettingsManager(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_reconcile_preserves_day_emoji_and_note_from_markdown(self):
        # Crear semana inicial con día 25 en casa (🏠)
        day = DaySchedule(day_number=25, location_emoji="🏠", location_note=None, task_ids=[])
        week = WeekSchedule(
            year=2026,
            month=9,
            week_number=39,
            weight=None,
            topics_task_ids=[],
            note_ids=[],
            days=[day]
        )
        self.em.save_week(week)

        # Crear archivo Markdown donde el usuario editó a mano a libre por compensación:
        md_content = """# 🗓️Week 39

## 🎯Topics
  - 
  ---

## 📋Week Tasks
  - 
  ---

## 📝Notes
  ---

## 🏖️25 (Compensación Deploy)
  - 

<!-- Definiciones -->
"""
        md_path = os.path.join(self.test_dir, "[2026][09]Week39.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        sync_service = MarkdownSyncService(self.em, self.test_dir)
        synced = sync_service.sync_week_from_markdown(md_path, 2026, 39)

        # Verificar que el día en week ahora tiene 🏖️ y "Compensación Deploy"
        reloaded = self.em.load_week(2026, 39, reload=True)
        day_25 = next(d for d in reloaded.days if d.day_number == 25)
        self.assertEqual(day_25.location_emoji, "🏖️")
        self.assertEqual(day_25.location_note, "Compensación Deploy")

        # Verificar que al renderizar el markdown limpio, se mantiene el encabezado correcto
        rendered = BitacoraRenderer.render_week(reloaded, self.em)
        self.assertIn("## 🏖️25 (Compensación Deploy)", rendered)

    def test_apply_calendar_to_week_updates_days(self):
        # Configurar en work_calendar.yaml la vacación para 2026-09-25
        self.sm.add_or_update_vacation("2026-09-25", "2026-09-25", "Compensación Deploy")

        # Semana donde el día 25 originalmente estaba como 🏠 sin nota
        day = DaySchedule(day_number=25, location_emoji="🏠", location_note=None, task_ids=[])
        week = WeekSchedule(
            year=2026,
            month=9,
            week_number=39,
            weight=None,
            topics_task_ids=[],
            note_ids=[],
            days=[day]
        )

        changed = self.em.apply_calendar_to_week(week, self.sm)
        self.assertTrue(changed)
        self.assertEqual(day.location_emoji, "🏖️")
        self.assertEqual(day.location_note, "Compensación Deploy")


if __name__ == "__main__":
    unittest.main()
