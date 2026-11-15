#!/usr/bin/env python3
"""Tests para controlador de herramientas extraído de main.py."""

import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tools_controller import ToolsController


class TestCoreToolsController:
    """Valida flujo de herramientas y despacho de comandos."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def _assert(self, condition: bool, message: str):
        if not condition:
            raise AssertionError(message)

    def test_dispatch_debug_files_and_back(self):
        try:
            events = []
            commands = iter(
                [
                    ("tool_debug_files", 0, True),
                    ("back", 0, True),
                ]
            )

            controller = ToolsController(
                directory=".",
                vault_root=".",
                show_tools_menu_fn=lambda _idx: events.append("show_menu"),
                resolve_menu_command_fn=lambda *_args: next(commands),
                clear_screen_fn=lambda: events.append("clear"),
                read_single_key_fn=lambda _prompt: "x",
                input_fn=lambda _prompt="": "",
                print_fn=lambda *_args, **_kwargs: None,
                debug_files_in_directory_fn=lambda _directory: events.append("debug_files"),
            )

            controller.run()

            self._assert("debug_files" in events, "Debe invocar debug_files_in_directory")
            self._assert(events.count("show_menu") == 2, "Debe renderizar menú en cada iteración")

            print("✅ Test: tools dispatch -> debug_files + back")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test dispatch_debug_files_and_back falló: {e}")
            self.failed += 1

    def test_invalid_option_prompts_continue(self):
        try:
            prompts = []
            commands = iter(
                [
                    (None, 0, False),
                    ("back", 0, True),
                ]
            )

            controller = ToolsController(
                directory=".",
                vault_root=".",
                show_tools_menu_fn=lambda _idx: None,
                resolve_menu_command_fn=lambda *_args: next(commands),
                clear_screen_fn=lambda: None,
                read_single_key_fn=lambda _prompt: "bad",
                input_fn=lambda prompt="": prompts.append(prompt) or "",
                print_fn=lambda *_args, **_kwargs: None,
            )

            controller.run()

            self._assert(any("Presiona Enter" in p for p in prompts), "Debe pedir continuar tras opción inválida")

            print("✅ Test: opción inválida solicita continuar")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test invalid_option_prompts_continue falló: {e}")
            self.failed += 1

    def run_all(self):
        print("\n🧪 TESTS: core/tools_controller.py")
        print("=" * 50)

        self.test_dispatch_debug_files_and_back()
        self.test_invalid_option_prompts_continue()

        print(f"\n📊 Resultado: ✅ {self.passed} | ❌ {self.failed}")
        return self.failed == 0


if __name__ == "__main__":
    tester = TestCoreToolsController()
    success = tester.run_all()
    sys.exit(0 if success else 1)
