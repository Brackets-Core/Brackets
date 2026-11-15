#!/usr/bin/env python3
"""File-rename menu controller extracted from BitacoraManager."""

from typing import Callable, Optional
from core.menu_navigator import MenuNavigator, MenuOption


class FileRenameController:
    """Handle global replace and file rename flow."""

    def __init__(
        self,
        vault_name: str,
        get_file_rename_manager_fn: Callable[[], object],
        clear_screen_fn: Callable[[], None],
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[..., None] = print,
        read_single_key_fn: Optional[Callable[[str], str]] = None,
    ):
        self.vault_name = vault_name
        self.get_file_rename_manager = get_file_rename_manager_fn
        self.clear_screen = clear_screen_fn
        self.input = input_fn
        self.print = print_fn
        self.read_single_key = read_single_key_fn

    def run(self) -> str:
        """Run search/replace menu loop."""
        file_rename_manager = self.get_file_rename_manager()

        options = [
            MenuOption("1", "🔍 Búsqueda y reemplazo global (texto en nombres y contenido)", "global_replace", aliases=["b", "g"]),
            MenuOption("2", "📁 Renombrar archivo específico (actualiza referencias)", "rename", aliases=["r", "f"]),
        ]

        navigator = MenuNavigator(
            title=f"🔍 BÚSQUEDA Y REEMPLAZO - {self.vault_name}",
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
                if opt.action_id == "global_replace":
                    file_rename_manager.interactive_global_replace()
                    self.input("\nPresiona Enter para continuar...")
                    return "back"
                elif opt.action_id == "rename":
                    file_rename_manager.interactive_rename()
                    self.input("\nPresiona Enter para continuar...")
                    return "back"
