"""Pruebas para cierres de sede central y soporte de jornada intensiva en SettingsManager y ConfigurationController."""

import os
import shutil
import tempfile
import unittest
from datetime import datetime

from brackets.managers.settings_manager import SettingsManager
from brackets.models.entities import DaySchedule, WeekSchedule
from brackets.generators.bitacora_renderer import BitacoraRenderer


class TestCalendarIntensiveAndClosures(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.test_dir, "data"), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_intensive_and_closures_resolution(self):
        sm = SettingsManager(self.test_dir)
        # Configurar jornada intensiva para 2026-09-10
        sm.add_or_update_intensive_day("2026-09-10", name="Jornada Intensiva")
        # Configurar cierre de sede para 2026-12-24
        sm.add_or_update_closure("2026-12-24", "Cierre de la sede central (Nochebuena)")

        # 2026-09-10 es jueves (thursday -> por defecto 'home' 🏠)
        dt_intensive = datetime(2026, 9, 10)
        emoji, note = sm.get_location_for_date(dt_intensive)
        self.assertEqual(emoji, "🏠")
        self.assertEqual(note, "Jornada Intensiva")

        # 2026-12-24 es jueves (cierre de sede central -> 'off' 🏖️)
        dt_closure = datetime(2026, 12, 24)
        emoji, note = sm.get_location_for_date(dt_closure)
        self.assertEqual(emoji, "🏖️")
        self.assertIn("Cierre de la sede central", note)

        # Día normal sin intensiva ni cierre
        dt_normal = datetime(2026, 9, 16)  # miércoles -> office o home según patrón
        emoji_norm, note_norm = sm.get_location_for_date(dt_normal)
        self.assertIsNone(note_norm)

    def test_intensive_day_range(self):
        sm = SettingsManager(self.test_dir)
        # Configurar rango de jornada intensiva de verano
        sm.add_or_update_intensive_day("2026-07-01", "2026-07-15", name="Jornada Intensiva de Verano")

        dt_inside = datetime(2026, 7, 7)
        emoji, note = sm.get_location_for_date(dt_inside)
        self.assertIn(emoji, ("🏠", "🚗"))
        self.assertEqual(note, "Jornada Intensiva de Verano")

        dt_outside = datetime(2026, 7, 20)
        _, note_out = sm.get_location_for_date(dt_outside)
        self.assertIsNone(note_out)

    def test_bitacora_rendering_with_intensive(self):
        # Crear día con location_note "Jornada Intensiva"
        day = DaySchedule(day_number=10, location_emoji="🏠", location_note="Jornada Intensiva", task_ids=[])
        week = WeekSchedule(
            year=2026,
            month=9,
            week_number=37,
            weight=None,
            topics_task_ids=[],
            note_ids=[],
            days=[day]
        )
        from brackets.managers.entity_manager import EntityManager
        em = EntityManager(os.path.join(self.test_dir, "data"))
        rendered = BitacoraRenderer.render_week(week, em)
        self.assertIn("## 🏠10 (Jornada Intensiva)", rendered)

    def test_mutations_and_persistence(self):
        sm = SettingsManager(self.test_dir)
        sm.add_or_update_closure("2026-12-31", "Cierre de Fin de año")
        self.assertEqual(len(sm.list_closures()), 1)
        self.assertEqual(sm.list_closures()[0]["name"], "Cierre de Fin de año")

        sm.delete_closure(0)
        self.assertEqual(len(sm.list_closures()), 0)

        sm.add_or_update_intensive_day("2026-09-10", name="Jornada Intensiva")
        self.assertEqual(len(sm.list_intensive_days()), 1)
        sm.delete_intensive_day(0)
        self.assertEqual(len(sm.list_intensive_days()), 0)


if __name__ == "__main__":
    unittest.main()
