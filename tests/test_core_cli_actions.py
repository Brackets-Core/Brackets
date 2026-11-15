#!/usr/bin/env python3
"""Tests para dispatcher de acciones CLI extraído de main.py."""

import os
import sys
import tempfile
from types import SimpleNamespace

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cli_actions import has_action_flags, dispatch_cli_action


class _FakeWeeklyGen:
    def __init__(self):
        self.called = False

    def create_next_or_manual_weekly_bitacora(self):
        self.called = True
        return True


class _FakeMonthlyGen:
    def __init__(self):
        self.called = False

    def create_next_monthly_topics(self):
        self.called = True
        return True

    def list_recent_months(self, _count):
        self.called = True


class _FakeMonthConsolidator:
    def __init__(self):
        self.called_with = None

    def consolidate_month(self, year, month):
        self.called_with = (year, month)
        return True


class _FakeYearConsolidator:
    def consolidate_year(self, _year):
        return True


class _FakeEventLog:
    def append(self, event, **kwargs):
        pass


class _FakeManager:
    def __init__(self, bitacoras_enabled=True):
        self.bitacoras_enabled = bitacoras_enabled
        self.weekly_gen = _FakeWeeklyGen()
        self.monthly_gen = _FakeMonthlyGen()
        self.month_consolidator = _FakeMonthConsolidator()
        self.year_consolidator = _FakeYearConsolidator()
        self.event_log = _FakeEventLog()


class TestCoreCliActions:
    """Valida extracción del dispatcher CLI."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def _assert(self, condition: bool, message: str):
        if not condition:
            raise AssertionError(message)

    def _args(self, **kwargs):
        defaults = {
            "weekly": False,
            "monthly": False,
            "add_task": None,
            "task_target": "weekly",
            "timer": False,
            "consolidate": None,
            "consolidate_year": None,
            "list": False,
            "debug": False,
            "test_emoji": False,
            "analyze": None,
        }
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)

    def test_has_action_flags(self):
        try:
            self._assert(has_action_flags(self._args()) is False, "No debe detectar flags en vacío")
            self._assert(has_action_flags(self._args(weekly=True)) is True, "Debe detectar --weekly")
            self._assert(has_action_flags(self._args(add_task="Nueva tarea")) is True, "Debe detectar --add-task")
            self._assert(has_action_flags(self._args(analyze="file.md")) is True, "Debe detectar --analyze")

            print("✅ Test: has_action_flags detecta acciones")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test has_action_flags falló: {e}")
            self.failed += 1

    def test_dispatch_weekly_disabled(self):
        try:
            manager = _FakeManager(bitacoras_enabled=False)
            exit_code = dispatch_cli_action(self._args(weekly=True), manager, ".")

            self._assert(exit_code == 1, "Debe devolver exit code 1 con bitácoras desactivadas")
            self._assert(manager.weekly_gen.called is False, "No debe ejecutar el generador semanal")

            print("✅ Test: weekly bloqueado si bitácoras desactivadas")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test dispatch_weekly_disabled falló: {e}")
            self.failed += 1

    def test_dispatch_weekly_success(self):
        try:
            manager = _FakeManager(bitacoras_enabled=True)
            exit_code = dispatch_cli_action(self._args(weekly=True), manager, ".")

            self._assert(exit_code == 0, "Debe devolver exit code 0 en weekly exitoso")
            self._assert(manager.weekly_gen.called is True, "Debe ejecutar el generador semanal")

            print("✅ Test: weekly ejecuta y retorna 0")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test dispatch_weekly_success falló: {e}")
            self.failed += 1

    def test_dispatch_consolidate_format_validation(self):
        try:
            manager = _FakeManager(bitacoras_enabled=True)
            bad_exit = dispatch_cli_action(self._args(consolidate="bad-format"), manager, ".")
            ok_exit = dispatch_cli_action(self._args(consolidate="2026-05"), manager, ".")

            self._assert(bad_exit == 1, "Formato inválido debe devolver exit code 1")
            self._assert(ok_exit == 0, "Formato válido debe devolver exit code 0")
            self._assert(manager.month_consolidator.called_with == (2026, 5), "Debe parsear y pasar año/mes")

            print("✅ Test: consolidate valida formato y parsea año/mes")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test dispatch_consolidate_format_validation falló: {e}")
            self.failed += 1

    def test_dispatch_analyze_missing_file(self):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                manager = _FakeManager(bitacoras_enabled=True)
                exit_code = dispatch_cli_action(self._args(analyze="missing.md"), manager, tmp)
                self._assert(exit_code == 1, "Archivo inexistente debe devolver exit code 1")

            print("✅ Test: analyze falla con archivo inexistente")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test dispatch_analyze_missing_file falló: {e}")
            self.failed += 1

    def test_dispatch_add_task_weekly_success(self):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                weekly_file = os.path.join(tmp, "[2026][05]Week22.md")
                with open(weekly_file, "w", encoding="utf-8") as f:
                    f.write("# 🗓️Week 22\n\n## ✅Topics\n  - [ ] Base\n\n## 📝Notes\n")

                manager = _FakeManager(bitacoras_enabled=True)
                exit_code = dispatch_cli_action(
                    self._args(add_task="Nueva tarea semanal", task_target="weekly"),
                    manager,
                    tmp,
                )

                self._assert(exit_code == 0, "--add-task weekly debe devolver 0")
                with open(weekly_file, "r", encoding="utf-8") as f:
                    updated = f.read()
                self._assert("- [ ] Nueva tarea semanal" in updated, "Debe insertar la tarea en Topics")

            print("✅ Test: add-task weekly inserta tarea en último weekly")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test dispatch_add_task_weekly_success falló: {e}")
            self.failed += 1

    def test_dispatch_add_task_monthly_success(self):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                monthly_file = os.path.join(tmp, "[2026][05]MonthTopics.md")
                with open(monthly_file, "w", encoding="utf-8") as f:
                    f.write("# May Topics ☀️\n\n## ✅Topics\n  - [ ] Base mensual\n")

                manager = _FakeManager(bitacoras_enabled=True)
                exit_code = dispatch_cli_action(
                    self._args(add_task="Nueva tarea mensual", task_target="monthly"),
                    manager,
                    tmp,
                )

                self._assert(exit_code == 0, "--add-task monthly debe devolver 0")
                with open(monthly_file, "r", encoding="utf-8") as f:
                    updated = f.read()
                self._assert("- [ ] Nueva tarea mensual" in updated, "Debe insertar la tarea en Topics mensual")

            print("✅ Test: add-task monthly inserta tarea en último monthly")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test dispatch_add_task_monthly_success falló: {e}")
            self.failed += 1

    def test_dispatch_add_task_without_target_file(self):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                manager = _FakeManager(bitacoras_enabled=True)
                exit_code = dispatch_cli_action(
                    self._args(add_task="Nueva tarea semanal", task_target="weekly"),
                    manager,
                    tmp,
                )

                self._assert(exit_code == 1, "Si no hay weekly, add-task debe devolver 1")

            print("✅ Test: add-task falla si no existe archivo destino")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test dispatch_add_task_without_target_file falló: {e}")
            self.failed += 1

    def run_all(self):
        print("\n🧪 TESTS: core/cli_actions.py")
        print("=" * 50)

        self.test_has_action_flags()
        self.test_dispatch_weekly_disabled()
        self.test_dispatch_weekly_success()
        self.test_dispatch_consolidate_format_validation()
        self.test_dispatch_analyze_missing_file()
        self.test_dispatch_add_task_weekly_success()
        self.test_dispatch_add_task_monthly_success()
        self.test_dispatch_add_task_without_target_file()

        print(f"\n📊 Resultado: ✅ {self.passed} | ❌ {self.failed}")
        return self.failed == 0


if __name__ == "__main__":
    tester = TestCoreCliActions()
    success = tester.run_all()
    sys.exit(0 if success else 1)
