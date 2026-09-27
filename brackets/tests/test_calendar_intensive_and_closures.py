"""Pruebas para cierres de sede central y soporte de jornada intensiva en SettingsManager y ConfigurationController."""

import os
import shutil
import tempfile
from datetime import datetime
import pytest

from brackets.managers.settings_manager import SettingsManager
from brackets.models.entities import DaySchedule, WeekSchedule
from brackets.generators.bitacora_renderer import BitacoraRenderer


class TestCalendarIntensiveAndClosures:
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        self.test_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.test_dir, "data"), exist_ok=True)
        yield
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
        assert emoji == "🏠"
        assert note == "Jornada Intensiva"

        # 2026-12-24 es jueves (cierre de sede central -> 'off' 🏖️)
        dt_closure = datetime(2026, 12, 24)
        emoji, note = sm.get_location_for_date(dt_closure)
        assert emoji == "🏖️"
        assert "Cierre de la sede central" in note

        # Día normal sin intensiva ni cierre
        dt_normal = datetime(2026, 9, 16)  # miércoles -> office o home según patrón
        emoji_norm, note_norm = sm.get_location_for_date(dt_normal)
        assert note_norm is None

    def test_intensive_day_range(self):
        sm = SettingsManager(self.test_dir)
        # Configurar rango de jornada intensiva de verano
        sm.add_or_update_intensive_day("2026-07-01", "2026-07-15", name="Jornada Intensiva de Verano")

        dt_inside = datetime(2026, 7, 7)
        emoji, note = sm.get_location_for_date(dt_inside)
        assert emoji in ("🏠", "🚗")
        assert note == "Jornada Intensiva de Verano"

        dt_outside = datetime(2026, 7, 20)
        _, note_out = sm.get_location_for_date(dt_outside)
        assert note_out is None

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
        assert "## 🏠10 (Jornada Intensiva)" in rendered

    def test_mutations_and_persistence(self):
        sm = SettingsManager(self.test_dir)
        sm.add_or_update_closure("2026-12-31", "Cierre de Fin de año")
        assert len(sm.list_closures()) == 1
        assert sm.list_closures()[0]["name"] == "Cierre de Fin de año"

        sm.delete_closure(0)
        assert len(sm.list_closures()) == 0

        sm.add_or_update_intensive_day("2026-09-10", name="Jornada Intensiva")
        assert len(sm.list_intensive_days()) == 1
        sm.delete_intensive_day(0)
        assert len(sm.list_intensive_days()) == 0
