#!/usr/bin/env python3
"""Category-management menu controller extracted from BitacoraManager."""

from typing import Callable, Optional
from core.menu_navigator import MenuNavigator, MenuOption


class CategoryManagementController:
    """Handle category and document management interactive flow."""

    def __init__(
        self,
        vault_name: str,
        get_category_manager_fn: Callable[[], object],
        clear_screen_fn: Callable[[], None],
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[..., None] = print,
        read_single_key_fn: Optional[Callable[[str], str]] = None,
    ):
        self.vault_name = vault_name
        self.get_category_manager = get_category_manager_fn
        self.clear_screen = clear_screen_fn
        self.input = input_fn
        self.print = print_fn
        self.read_single_key = read_single_key_fn

    def run(self) -> str:
        """Run category-management menu loop."""
        category_manager = self.get_category_manager()

        options = [
            MenuOption("1", "📄 Crear nuevo documento", "create", aliases=["c", "n"]),
            MenuOption("2", "📚 Ver todas las categorías", "list", aliases=["v", "l"]),
            MenuOption("3", "🔍 Explorar categorías", "browse", aliases=["e", "b"]),
        ]

        navigator = MenuNavigator(
            title=f"📂 GESTIONAR CATEGORÍAS Y DOCUMENTOS - {self.vault_name}",
            options=options,
            show_back=True,
            show_main_menu=True,
            print_fn=self.print,
            input_fn=self.input,
            read_single_key_fn=self.read_single_key,
            clear_screen_fn=self.clear_screen,
        )

        while True:
            nav_status, opt = navigator.prompt()
            if nav_status == "back":
                return "back"
            if nav_status == "menu":
                return "menu"
            if nav_status == "exit":
                return "exit"

            if opt:
                if opt.action_id == "create":
                    if category_manager.interactive_create_document():
                        self.print("\n✅ Documento creado exitosamente")
                    else:
                        self.print("\n❌ No se pudo crear el documento")
                    self.input("\nPresiona Enter para continuar...")

                elif opt.action_id == "list":
                    category_manager.list_all_categories()
                    self.input("\nPresiona Enter para continuar...")

                elif opt.action_id == "browse":
                    category = category_manager.select_category()
                    if category:
                        subcategory = category_manager.select_subcategory(category)
                        if subcategory:
                            self.print(f"\n✅ Seleccionado: {category.get('name')} → {subcategory.get('name')}")
                    self.input("\nPresiona Enter para continuar...")
