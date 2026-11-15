#!/usr/bin/env python3
"""Tests para controlador de categorías extraído de main.py."""

import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.category_management_controller import CategoryManagementController


class _FakeCategoryManager:
    def __init__(self):
        self.create_called = False
        self.list_called = False
        self.select_category_called = False
        self.select_subcategory_called = False
        self.create_result = True
        self.category_result = None
        self.subcategory_result = None

    def interactive_create_document(self):
        self.create_called = True
        return self.create_result

    def list_all_categories(self):
        self.list_called = True

    def select_category(self):
        self.select_category_called = True
        return self.category_result

    def select_subcategory(self, _category):
        self.select_subcategory_called = True
        return self.subcategory_result


class TestCoreCategoryManagementController:
    """Valida flujo del controlador de gestión de categorías."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def _assert(self, condition: bool, message: str):
        if not condition:
            raise AssertionError(message)

    def test_dispatch_create_document_and_back(self):
        try:
            fake = _FakeCategoryManager()
            fake.create_result = True
            prompts = []
            inputs = iter(["1", "", "0"])

            controller = CategoryManagementController(
                vault_name="vault",
                get_category_manager_fn=lambda: fake,
                clear_screen_fn=lambda: None,
                input_fn=lambda prompt="": prompts.append(prompt) or next(inputs),
                print_fn=lambda *_args, **_kwargs: None,
            )

            controller.run()

            self._assert(fake.create_called, "Debe ejecutar interactive_create_document")
            self._assert(any("Presiona Enter" in p for p in prompts), "Debe pedir continuar tras crear")

            print("✅ Test: category controller dispatch -> create + back")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test dispatch_create_document_and_back falló: {e}")
            self.failed += 1

    def test_dispatch_explore_category_selection(self):
        try:
            fake = _FakeCategoryManager()
            fake.category_result = {"name": "Work"}
            fake.subcategory_result = {"name": "Python"}
            printed = []
            inputs = iter(["3", "", "0"])

            controller = CategoryManagementController(
                vault_name="vault",
                get_category_manager_fn=lambda: fake,
                clear_screen_fn=lambda: None,
                input_fn=lambda _prompt="": next(inputs),
                print_fn=lambda *args, **_kwargs: printed.append(" ".join(str(a) for a in args)),
            )

            controller.run()

            self._assert(fake.select_category_called, "Debe ejecutar select_category")
            self._assert(fake.select_subcategory_called, "Debe ejecutar select_subcategory")
            self._assert(
                any("Seleccionado:" in line and "Work" in line and "Python" in line for line in printed),
                "Debe mostrar selección final cuando existe categoría/subcategoría",
            )

            print("✅ Test: category controller dispatch -> explore")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test dispatch_explore_category_selection falló: {e}")
            self.failed += 1

    def run_all(self):
        print("\n🧪 TESTS: core/category_management_controller.py")
        print("=" * 50)

        self.test_dispatch_create_document_and_back()
        self.test_dispatch_explore_category_selection()

        print(f"\n📊 Resultado: ✅ {self.passed} | ❌ {self.failed}")
        return self.failed == 0


if __name__ == "__main__":
    tester = TestCoreCategoryManagementController()
    success = tester.run_all()
    sys.exit(0 if success else 1)
