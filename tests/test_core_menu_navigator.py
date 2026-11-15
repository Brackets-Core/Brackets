#!/usr/bin/env python3
"""
Tests unitarios para el componente unificado de navegación y menús (MenuNavigator).
Verifica:
- Navegación con flechas (KEY_UP / KEY_DOWN) y selección con KEY_ENTER.
- Selección directa con teclas rápidas y alias sin Enter.
- Vuelta al nivel superior con 0, v y KEY_ESC.
- Salto directo al Menú Principal con m.
- Salida limpia con q / exit.
"""

import sys
import os

# Asegurar path al core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.menu_navigator import (
    MenuNavigator,
    MenuOption,
    KEY_UP,
    KEY_DOWN,
    KEY_ENTER,
    KEY_ESC,
)


class TestCoreMenuNavigator:
    """Suite de tests para MenuNavigator."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def _assert(self, condition: bool, message: str):
        if not condition:
            raise AssertionError(message)

    def _sample_options(self):
        return [
            MenuOption("1", "Añadir Tarea", "add_task", aliases=["t"], group="ACCIONES"),
            MenuOption("2", "Capturar Idea", "capture_idea", aliases=["i"], group="ACCIONES"),
            MenuOption("3", "Ver Proyectos", "view_projects", aliases=["p"], group="CONSULTA"),
        ]

    def test_menu_option_matching(self):
        """Valida que MenuOption haga matching exacto con key y aliases."""
        try:
            opt = MenuOption("1", "Añadir Tarea", "add_task", aliases=["t", "task"])
            self._assert(opt.matches("1"), "Debe coincidir con la key '1'")
            self._assert(opt.matches("t"), "Debe coincidir con alias 't'")
            self._assert(opt.matches("TASK"), "Debe coincidir insensible a mayúsculas")
            self._assert(not opt.matches("2"), "No debe coincidir con '2'")
            self._assert(not opt.matches(""), "No debe coincidir con vacío")

            print("✅ Test: MenuOption matching con key y aliases")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test menu_option_matching falló: {e}")
            self.failed += 1

    def test_arrow_navigation_and_enter(self):
        """Valida que las flechas muevan el cursor y Enter seleccione la opción resaltada."""
        try:
            options = self._sample_options()
            # Secuencia: abajo (a opción 2), abajo (a opción 3), enter
            inputs = [KEY_DOWN, KEY_DOWN, KEY_ENTER]
            input_iter = iter(inputs)

            nav = MenuNavigator(
                title="TEST MENU",
                options=options,
                read_single_key_fn=lambda prompt="": next(input_iter),
                print_fn=lambda *a, **k: None,
                clear_screen_fn=lambda: None,
            )

            status, selected = nav.prompt()
            self._assert(status == "action", "Debe retornar status 'action'")
            self._assert(selected is not None and selected.action_id == "view_projects", "Debe haber seleccionado la opción 3 (view_projects)")

            print("✅ Test: navegación con flechas (DOWN + DOWN + ENTER)")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test arrow_navigation_and_enter falló: {e}")
            self.failed += 1

    def test_arrow_navigation_cyclic_wrap(self):
        """Valida que la flecha UP desde 0 envuelva hacia el último elemento."""
        try:
            options = self._sample_options()
            # Secuencia: arriba (envuelve a opción 3), enter
            inputs = [KEY_UP, KEY_ENTER]
            input_iter = iter(inputs)

            nav = MenuNavigator(
                title="TEST MENU",
                options=options,
                read_single_key_fn=lambda prompt="": next(input_iter),
                print_fn=lambda *a, **k: None,
                clear_screen_fn=lambda: None,
            )

            status, selected = nav.prompt()
            self._assert(status == "action", "Debe retornar status 'action'")
            self._assert(selected is not None and selected.action_id == "view_projects", "Flecha UP desde el inicio debe ir al último elemento")

            print("✅ Test: navegación cíclica con flecha UP")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test arrow_navigation_cyclic_wrap falló: {e}")
            self.failed += 1

    def test_direct_key_selection(self):
        """Valida que presionar directamente una tecla o alias ejecute sin confirmación por Enter."""
        try:
            options = self._sample_options()
            # Presionar directamente '2'
            nav = MenuNavigator(
                title="TEST MENU",
                options=options,
                read_single_key_fn=lambda prompt="": "2",
                print_fn=lambda *a, **k: None,
                clear_screen_fn=lambda: None,
            )

            status, selected = nav.prompt()
            self._assert(status == "action", "Debe retornar status 'action'")
            self._assert(selected is not None and selected.action_id == "capture_idea", "Debe seleccionar la opción 2 directamente")

            # Presionar alias 't'
            nav_alias = MenuNavigator(
                title="TEST MENU",
                options=options,
                read_single_key_fn=lambda prompt="": "t",
                print_fn=lambda *a, **k: None,
                clear_screen_fn=lambda: None,
            )
            status_alias, selected_alias = nav_alias.prompt()
            self._assert(status_alias == "action" and selected_alias.action_id == "add_task", "Debe seleccionar opción por alias directo")

            print("✅ Test: selección directa por tecla rápida (sin Enter)")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test direct_key_selection falló: {e}")
            self.failed += 1

    def test_return_to_upper_level(self):
        """Valida que '0', 'v' o KEY_ESC retornen 'back'."""
        try:
            for key in ["0", "v", KEY_ESC]:
                nav = MenuNavigator(
                    title="TEST MENU",
                    options=self._sample_options(),
                    read_single_key_fn=lambda prompt="", k=key: k,
                    print_fn=lambda *a, **k: None,
                    clear_screen_fn=lambda: None,
                )
                status, selected = nav.prompt()
                self._assert(status == "back", f"Tecla '{key}' debe retornar status 'back'")
                self._assert(selected is None, "Selected debe ser None en 'back'")

            print("✅ Test: vuelta al nivel superior con 0, v o Esc")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test return_to_upper_level falló: {e}")
            self.failed += 1

    def test_jump_to_main_menu(self):
        """Valida que 'm' o 'menu' retornen 'menu' para salto directo al menú principal."""
        try:
            for key in ["m", "menu"]:
                nav = MenuNavigator(
                    title="TEST MENU",
                    options=self._sample_options(),
                    read_single_key_fn=lambda prompt="", k=key: k,
                    print_fn=lambda *a, **k: None,
                    clear_screen_fn=lambda: None,
                )
                status, selected = nav.prompt()
                self._assert(status == "menu", f"Tecla '{key}' debe retornar status 'menu'")
                self._assert(selected is None, "Selected debe ser None en 'menu'")

            print("✅ Test: salto directo al menú principal con 'm'")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test jump_to_main_menu falló: {e}")
            self.failed += 1

    def test_exit_application(self):
        """Valida que 'q' o 'exit' retornen 'exit'."""
        try:
            nav = MenuNavigator(
                title="TEST MENU",
                options=self._sample_options(),
                read_single_key_fn=lambda prompt="": "q",
                print_fn=lambda *a, **k: None,
                clear_screen_fn=lambda: None,
            )
            status, selected = nav.prompt()
            self._assert(status == "exit", "Tecla 'q' debe retornar status 'exit'")

            print("✅ Test: salida de la aplicación con 'q'")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test exit_application falló: {e}")
            self.failed += 1

    def run_all(self) -> bool:
        print("\n🧪 TESTS: core/menu_navigator.py")
        print("=" * 50)
        self.test_menu_option_matching()
        self.test_arrow_navigation_and_enter()
        self.test_arrow_navigation_cyclic_wrap()
        self.test_direct_key_selection()
        self.test_return_to_upper_level()
        self.test_jump_to_main_menu()
        self.test_exit_application()

        print(f"\n📊 Resultado: ✅ {self.passed} | ❌ {self.failed}")
        return self.failed == 0


if __name__ == "__main__":
    tester = TestCoreMenuNavigator()
    success = tester.run_all()
    sys.exit(0 if success else 1)
