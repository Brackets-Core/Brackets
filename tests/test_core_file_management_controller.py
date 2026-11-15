#!/usr/bin/env python3
"""Tests para controlador de gestión de archivos extraído de main.py."""

import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.file_management_controller import FileManagementController


class _FakeWeeklyGen:
    def __init__(self):
        self.called_with = None

    def list_recent_weeks(self, count):
        self.called_with = count


class _FakeMonthlyGen:
    def __init__(self):
        self.called_with = None

    def list_recent_months(self, count):
        self.called_with = count


class _FakeFinder:
    def __init__(self, weekly=None, monthly=None):
        self._weekly = weekly or []
        self._monthly = monthly or []

    def list_weekly_files(self):
        return self._weekly

    def list_monthly_files(self):
        return self._monthly


class TestCoreFileManagementController:
    """Valida flujo del controlador de gestión de archivos."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def _assert(self, condition: bool, message: str):
        if not condition:
            raise AssertionError(message)

    def test_run_menu_dispatches_manage_categories(self):
        try:
            events = []
            commands = iter(
                [
                    ("manage_categories", 0, True),
                    ("back", 0, True),
                ]
            )

            controller = FileManagementController(
                directory=".",
                show_file_management_menu_fn=lambda _idx: events.append("show_menu"),
                show_list_menu_fn=lambda _idx: None,
                resolve_menu_command_fn=lambda *_args: next(commands),
                clear_screen_fn=lambda: events.append("clear"),
                read_single_key_fn=lambda _prompt: "x",
                weekly_gen=_FakeWeeklyGen(),
                monthly_gen=_FakeMonthlyGen(),
                finder=_FakeFinder(),
                input_fn=lambda _prompt="": "",
                print_fn=lambda *_args, **_kwargs: None,
            )

            controller.run_menu(
                on_manage_categories=lambda: events.append("manage_categories"),
                on_global_replace=lambda: events.append("global_replace"),
                on_sync_yaml=lambda: events.append("sync_yaml"),
                on_add_task=lambda: events.append("add_task"),
            )

            self._assert("manage_categories" in events, "Debe invocar callback de categorías")
            self._assert(events.count("show_menu") == 2, "Debe renderizar menú en cada iteración")

            print("✅ Test: file management dispatch -> manage_categories + back")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test run_menu_dispatches_manage_categories falló: {e}")
            self.failed += 1

    def test_run_menu_dispatches_add_task(self):
        try:
            events = []
            commands = iter(
                [
                    ("add_task", 0, True),
                    ("back", 0, True),
                ]
            )

            controller = FileManagementController(
                directory=".",
                show_file_management_menu_fn=lambda _idx: events.append("show_menu"),
                show_list_menu_fn=lambda _idx: None,
                resolve_menu_command_fn=lambda *_args: next(commands),
                clear_screen_fn=lambda: events.append("clear"),
                read_single_key_fn=lambda _prompt: "x",
                weekly_gen=_FakeWeeklyGen(),
                monthly_gen=_FakeMonthlyGen(),
                finder=_FakeFinder(),
                input_fn=lambda _prompt="": "",
                print_fn=lambda *_args, **_kwargs: None,
            )

            controller.run_menu(
                on_manage_categories=lambda: events.append("manage_categories"),
                on_global_replace=lambda: events.append("global_replace"),
                on_sync_yaml=lambda: events.append("sync_yaml"),
                on_add_task=lambda: events.append("add_task"),
            )

            self._assert("add_task" in events, "Debe invocar callback de añadir tarea")
            self._assert(events.count("show_menu") == 2, "Debe renderizar menú en cada iteración")

            print("✅ Test: file management dispatch -> add_task + back")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test run_menu_dispatches_add_task falló: {e}")
            self.failed += 1

    def test_run_list_menu_dispatches_weekly(self):
        try:
            weekly = _FakeWeeklyGen()
            monthly = _FakeMonthlyGen()
            prompts = []
            commands = iter(
                [
                    ("list_weekly", 0, True),
                    ("back", 0, True),
                ]
            )

            controller = FileManagementController(
                directory=".",
                show_file_management_menu_fn=lambda _idx: None,
                show_list_menu_fn=lambda _idx: None,
                resolve_menu_command_fn=lambda *_args: next(commands),
                clear_screen_fn=lambda: None,
                read_single_key_fn=lambda _prompt: "x",
                weekly_gen=weekly,
                monthly_gen=monthly,
                finder=_FakeFinder(),
                input_fn=lambda prompt="": prompts.append(prompt) or "",
                print_fn=lambda *_args, **_kwargs: None,
            )

            controller.run_list_menu()

            self._assert(weekly.called_with == 10, "Debe listar semanales recientes con límite 10")
            self._assert(any("Presiona Enter" in p for p in prompts), "Debe pedir continuar")

            print("✅ Test: list menu dispatch -> list_weekly + back")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test run_list_menu_dispatches_weekly falló: {e}")
            self.failed += 1

    def run_all(self):
        print("\n🧪 TESTS: core/file_management_controller.py")
        print("=" * 50)

        self.test_run_menu_dispatches_manage_categories()
        self.test_run_menu_dispatches_add_task()
        self.test_run_list_menu_dispatches_weekly()

        print(f"\n📊 Resultado: ✅ {self.passed} | ❌ {self.failed}")
        return self.failed == 0


if __name__ == "__main__":
    tester = TestCoreFileManagementController()
    success = tester.run_all()
    sys.exit(0 if success else 1)
