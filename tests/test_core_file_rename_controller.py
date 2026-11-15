#!/usr/bin/env python3
"""Tests para controlador de file rename extraído de main.py."""

import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.file_rename_controller import FileRenameController


class _FakeFileRenameManager:
    def __init__(self):
        self.global_called = False
        self.rename_called = False

    def interactive_global_replace(self):
        self.global_called = True

    def interactive_rename(self):
        self.rename_called = True


class TestCoreFileRenameController:
    """Valida flujo del controlador de búsqueda y reemplazo."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def _assert(self, condition: bool, message: str):
        if not condition:
            raise AssertionError(message)

    def test_dispatch_global_replace_and_back(self):
        try:
            fake = _FakeFileRenameManager()
            prompts = []
            inputs = iter(["1", ""])

            controller = FileRenameController(
                vault_name="vault",
                get_file_rename_manager_fn=lambda: fake,
                clear_screen_fn=lambda: None,
                input_fn=lambda prompt="": prompts.append(prompt) or next(inputs),
                print_fn=lambda *_args, **_kwargs: None,
            )

            controller.run()

            self._assert(fake.global_called, "Debe ejecutar interactive_global_replace")
            self._assert(any("Presiona Enter" in p for p in prompts), "Debe pedir continuar tras ejecutar")

            print("✅ Test: file rename dispatch -> global replace")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test dispatch_global_replace_and_back falló: {e}")
            self.failed += 1

    def test_invalid_then_rename(self):
        try:
            fake = _FakeFileRenameManager()
            printed = []
            inputs = iter(["9", "2", ""])

            controller = FileRenameController(
                vault_name="vault",
                get_file_rename_manager_fn=lambda: fake,
                clear_screen_fn=lambda: None,
                input_fn=lambda _prompt="": next(inputs),
                print_fn=lambda *args, **_kwargs: printed.append(" ".join(str(a) for a in args)),
            )

            controller.run()

            self._assert(fake.rename_called, "Debe ejecutar interactive_rename")
            self._assert(any("Opción inválida" in line for line in printed), "Debe reportar opción inválida")

            print("✅ Test: file rename opción inválida -> rename")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test invalid_then_rename falló: {e}")
            self.failed += 1

    def run_all(self):
        print("\n🧪 TESTS: core/file_rename_controller.py")
        print("=" * 50)

        self.test_dispatch_global_replace_and_back()
        self.test_invalid_then_rename()

        print(f"\n📊 Resultado: ✅ {self.passed} | ❌ {self.failed}")
        return self.failed == 0


if __name__ == "__main__":
    tester = TestCoreFileRenameController()
    success = tester.run_all()
    sys.exit(0 if success else 1)
