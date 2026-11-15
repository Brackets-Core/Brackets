#!/usr/bin/env python3
"""Tests para controlador de configuración extraído de main.py."""

import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.configuration_controller import ConfigurationController


class _FakeSettings:
    def __init__(self):
        self.day_location_call = None
        self.reset_called = False

    def describe_work_pattern(self):
        return "pattern"

    def list_holidays(self):
        return []

    def list_vacations(self):
        return []

    def set_day_location(self, day_key, location):
        self.day_location_call = (day_key, location)

    def set_alternating(self, day_key, even_loc, odd_loc):
        self.day_location_call = (day_key, even_loc, odd_loc)

    def reset_defaults(self):
        self.reset_called = True

    def add_or_update_holiday(self, _date_str, _name):
        pass

    def delete_holiday(self, _idx):
        pass

    def add_or_update_vacation(self, _start, _end, _name):
        pass

    def delete_vacation(self, _idx):
        pass


class TestCoreConfigurationController:
    """Valida flujo del controlador de configuración."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def _assert(self, condition: bool, message: str):
        if not condition:
            raise AssertionError(message)

    def test_prompt_location_mapping(self):
        try:
            inputs = iter(["2", "9"])
            messages = []
            controller = ConfigurationController(
                settings=_FakeSettings(),
                vault_name="vault",
                show_configured_menu_fn=lambda *_args: None,
                resolve_menu_command_fn=lambda *_args: ("back", 0, True),
                clear_screen_fn=lambda: None,
                read_single_key_fn=lambda _prompt: "0",
                input_fn=lambda _prompt="": next(inputs),
                print_fn=lambda *args, **_kwargs: messages.append(" ".join(str(a) for a in args)),
            )

            valid = controller.prompt_location("Ubicación")
            invalid = controller.prompt_location("Ubicación")

            self._assert(valid == "office", "La opción 2 debe mapear a office")
            self._assert(invalid is None, "Una opción inválida debe devolver None")

            print("✅ Test: prompt_location mapea y valida opciones")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test prompt_location_mapping falló: {e}")
            self.failed += 1

    def test_run_dispatches_commands(self):
        try:
            events = []
            commands = iter(
                [
                    ("config_view", 0, True),
                    ("config_work_pattern", 0, True),
                    ("back", 0, True),
                ]
            )
            settings = _FakeSettings()

            class _TestController(ConfigurationController):
                def show_overview(self_inner):
                    events.append("overview")

                def configure_work_pattern(self_inner):
                    events.append("work_pattern")

            controller = _TestController(
                settings=settings,
                vault_name="vault",
                show_configured_menu_fn=lambda *_args: None,
                resolve_menu_command_fn=lambda *_args: next(commands),
                clear_screen_fn=lambda: None,
                read_single_key_fn=lambda _prompt: "x",
                input_fn=lambda _prompt="": "",
                print_fn=lambda *_args, **_kwargs: None,
            )

            controller.run()

            self._assert(events == ["overview", "work_pattern"], "Debe ejecutar handlers según comando")

            print("✅ Test: run despacha comandos de configuración")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test run_dispatches_commands falló: {e}")
            self.failed += 1

    def run_all(self):
        print("\n🧪 TESTS: core/configuration_controller.py")
        print("=" * 50)

        self.test_prompt_location_mapping()
        self.test_run_dispatches_commands()

        print(f"\n📊 Resultado: ✅ {self.passed} | ❌ {self.failed}")
        return self.failed == 0


if __name__ == "__main__":
    tester = TestCoreConfigurationController()
    success = tester.run_all()
    sys.exit(0 if success else 1)
