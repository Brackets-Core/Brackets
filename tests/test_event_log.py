#!/usr/bin/env python3
"""
Tests para brackets/worklog/event_log.py
"""

import os
import sys
import tempfile
import shutil
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worklog.event_log import EventLog


class TestEventLog:
    """Tests para EventLog."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.temp_dir = None

    def setup(self):
        """Crea un directorio temporal como vault."""
        self.temp_dir = tempfile.mkdtemp(prefix="brackets_test_")
        return EventLog(self.temp_dir)

    def teardown(self):
        """Limpia el directorio temporal."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        self.temp_dir = None

    def test_append_creates_file(self):
        """Test que append crea el archivo de log semanal."""
        try:
            log = self.setup()
            entry = log.append("test_event", detail="hello")

            assert entry["event"] == "test_event"
            assert entry["detail"] == "hello"
            assert "ts" in entry

            # Verificar que el archivo existe
            week_file = log._week_path(date.today())
            assert os.path.exists(week_file), "El archivo de log semanal debería existir"

            print("✅ Test: append crea archivo y devuelve entry correcto")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test append_creates_file falló: {e}")
            self.failed += 1
        finally:
            self.teardown()

    def test_append_multiple_entries(self):
        """Test que append acumula entries en el mismo archivo."""
        try:
            log = self.setup()
            log.append("event_1", seq=1)
            log.append("event_2", seq=2)
            log.append("event_3", seq=3)

            entries = log.read_day()
            assert len(entries) == 3, f"Esperaba 3 entries, obtuvo {len(entries)}"
            assert entries[0]["event"] == "event_1"
            assert entries[2]["seq"] == 3

            print("✅ Test: append acumula múltiples entries")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test append_multiple_entries falló: {e}")
            self.failed += 1
        finally:
            self.teardown()

    def test_read_day_empty(self):
        """Test que read_day devuelve lista vacía si no hay archivo."""
        try:
            log = self.setup()
            entries = log.read_day(date(2020, 1, 1))
            assert entries == [], f"Esperaba lista vacía, obtuvo {entries}"

            print("✅ Test: read_day devuelve vacío para día sin log")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test read_day_empty falló: {e}")
            self.failed += 1
        finally:
            self.teardown()

    def test_read_day_filters_by_date(self):
        """Test que read_day filtra entries por fecha dentro de la semana."""
        try:
            log = self.setup()
            log._ensure_dir()

            import yaml
            # Semana del 2026-03-09 (lunes W11)
            week_file = log._week_path(date(2026, 3, 9))
            data = {"entries": [
                {"ts": "2026-03-09T09:00:00", "event": "monday"},
                {"ts": "2026-03-10T10:00:00", "event": "tuesday"},
                {"ts": "2026-03-11T11:00:00", "event": "wednesday"},
            ]}
            with open(week_file, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True)

            entries = log.read_day(date(2026, 3, 10))
            assert len(entries) == 1, f"Esperaba 1 entry, obtuvo {len(entries)}"
            assert entries[0]["event"] == "tuesday"

            print("✅ Test: read_day filtra por fecha dentro de semana")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test read_day_filters falló: {e}")
            self.failed += 1
        finally:
            self.teardown()

    def test_read_week(self):
        """Test que read_week devuelve toda la semana."""
        try:
            log = self.setup()
            log._ensure_dir()

            import yaml
            week_file = log._week_path(date(2026, 3, 9))
            data = {"entries": [
                {"ts": "2026-03-09T09:00:00", "event": "e1"},
                {"ts": "2026-03-13T17:00:00", "event": "e2"},
            ]}
            with open(week_file, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True)

            entries = log.read_week(date(2026, 3, 11))  # miércoles de esa semana
            assert len(entries) == 2, f"Esperaba 2 entries, obtuvo {len(entries)}"

            print("✅ Test: read_week devuelve toda la semana")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test read_week falló: {e}")
            self.failed += 1
        finally:
            self.teardown()

    def test_read_range_cross_weeks(self):
        """Test que read_range funciona cruzando semanas."""
        try:
            log = self.setup()
            log._ensure_dir()

            import yaml
            # Semana W11 (2026-03-09 a 2026-03-15)
            w11 = log._week_path(date(2026, 3, 9))
            data_w11 = {"entries": [
                {"ts": "2026-03-13T09:00:00", "event": "w11_fri"},
            ]}
            with open(w11, "w", encoding="utf-8") as f:
                yaml.dump(data_w11, f, allow_unicode=True)

            # Semana W12 (2026-03-16 a 2026-03-22)
            w12 = log._week_path(date(2026, 3, 16))
            data_w12 = {"entries": [
                {"ts": "2026-03-16T09:00:00", "event": "w12_mon"},
                {"ts": "2026-03-17T09:00:00", "event": "w12_tue"},
            ]}
            with open(w12, "w", encoding="utf-8") as f:
                yaml.dump(data_w12, f, allow_unicode=True)

            entries = log.read_range(date(2026, 3, 13), date(2026, 3, 17))
            assert len(entries) == 3, f"Esperaba 3 entries, obtuvo {len(entries)}"
            assert entries[0]["event"] == "w11_fri"
            assert entries[2]["event"] == "w12_tue"

            print("✅ Test: read_range cruza semanas correctamente")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test read_range falló: {e}")
            self.failed += 1
        finally:
            self.teardown()

    def test_corrupted_file_returns_empty(self):
        """Test que un archivo corrupto no rompe la lectura."""
        try:
            log = self.setup()
            log._ensure_dir()

            path = log._week_path(date(2026, 1, 5))
            with open(path, "w", encoding="utf-8") as f:
                f.write("{{invalid yaml: [[[")

            entries = log.read_week(date(2026, 1, 5))
            assert entries == [], "Archivo corrupto debería devolver lista vacía"

            print("✅ Test: archivo corrupto devuelve lista vacía")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test corrupted_file falló: {e}")
            self.failed += 1
        finally:
            self.teardown()

    def test_entry_preserves_kwargs(self):
        """Test que kwargs arbitrarios se guardan en el entry."""
        try:
            log = self.setup()
            entry = log.append(
                "task_added",
                task_id="T-001",
                task_text="Revisar PRs",
                target="week",
                priority=1,
            )

            assert entry["task_id"] == "T-001"
            assert entry["task_text"] == "Revisar PRs"
            assert entry["target"] == "week"
            assert entry["priority"] == 1

            # Verificar persistencia
            loaded = log.read_day()
            assert loaded[0]["task_id"] == "T-001"

            print("✅ Test: kwargs arbitrarios se preservan en entry")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test entry_preserves_kwargs falló: {e}")
            self.failed += 1
        finally:
            self.teardown()

    def test_log_dir_creation(self):
        """Test que el directorio data/log se crea automáticamente."""
        try:
            log = self.setup()
            expected_dir = os.path.join(self.temp_dir, "data", "log")
            assert not os.path.exists(expected_dir), "Dir no debería existir aún"

            log.append("first_event")
            assert os.path.exists(expected_dir), "Dir debería crearse con append"

            print("✅ Test: directorio data/log se crea automáticamente")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test log_dir_creation falló: {e}")
            self.failed += 1
        finally:
            self.teardown()

    def test_week_file_naming(self):
        """Test que el nombre del archivo sigue formato YYYY-WXX.yaml."""
        try:
            log = self.setup()
            path = log._week_path(date(2026, 5, 31))  # Sábado de W22
            assert path.endswith("2026-W22.yaml"), f"Nombre incorrecto: {path}"

            path2 = log._week_path(date(2026, 1, 5))  # Lunes de W02
            assert path2.endswith("2026-W02.yaml"), f"Nombre incorrecto: {path2}"

            print("✅ Test: nombre de archivo sigue formato YYYY-WXX.yaml")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test week_file_naming falló: {e}")
            self.failed += 1
        finally:
            self.teardown()

    def run_all(self):
        """Ejecutar todos los tests."""
        print("\n🧪 TESTS: worklog/event_log.py")
        print("=" * 50)

        self.test_append_creates_file()
        self.test_append_multiple_entries()
        self.test_read_day_empty()
        self.test_read_day_filters_by_date()
        self.test_read_week()
        self.test_read_range_cross_weeks()
        self.test_corrupted_file_returns_empty()
        self.test_entry_preserves_kwargs()
        self.test_log_dir_creation()
        self.test_week_file_naming()

        print(f"\n📊 Resultado: ✅ {self.passed} | ❌ {self.failed}")
        return self.failed == 0


if __name__ == "__main__":
    tester = TestEventLog()
    success = tester.run_all()
    sys.exit(0 if success else 1)
