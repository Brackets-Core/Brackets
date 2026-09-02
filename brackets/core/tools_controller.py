#!/usr/bin/env python3
"""Tools/debug menu controller extracted from BitacoraManager."""

import os
from typing import Callable, Optional

from brackets.utils.content_parser import ContentParser, debug_content_parsing
from brackets.utils.legacy_utils import safe_file_read, test_emoji_pattern
from brackets.utils.file_finder import debug_files_in_directory
from brackets.config import WEEKDAYS


class ToolsController:
    """Handle interactive tools submenu behavior."""

    def __init__(
        self,
        directory: str,
        vault_root: str,
        show_tools_menu_fn: Callable[[int], None],
        resolve_menu_command_fn: Callable[[str, str, int], tuple[Optional[str], int, bool]],
        clear_screen_fn: Callable[[], None],
        read_single_key_fn: Callable[[str], str],
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[..., None] = print,
        debug_content_parsing_fn: Callable[[str], None] = debug_content_parsing,
        debug_files_in_directory_fn: Callable[[str], None] = debug_files_in_directory,
        test_emoji_pattern_fn: Callable[[], None] = test_emoji_pattern,
        safe_file_read_fn: Callable[[str], Optional[str]] = safe_file_read,
        content_parser_factory: Callable[[str], ContentParser] = ContentParser,
        run_pomodoro_fn: Optional[Callable[[str], None]] = None,
        entity_manager=None,
    ):
        self.directory = directory
        self.vault_root = vault_root
        self.show_tools_menu = show_tools_menu_fn
        self.resolve_menu_command = resolve_menu_command_fn
        self.clear_screen = clear_screen_fn
        self.read_single_key = read_single_key_fn
        self.input = input_fn
        self.print = print_fn
        self.debug_content_parsing = debug_content_parsing_fn
        self.debug_files_in_directory = debug_files_in_directory_fn
        self.test_emoji_pattern = test_emoji_pattern_fn
        self.safe_file_read = safe_file_read_fn
        self.content_parser_factory = content_parser_factory
        self.run_pomodoro = run_pomodoro_fn
        self.entity_manager = entity_manager

    def run(self) -> None:
        """Run tools submenu loop."""
        selected_index = 0
        while True:
            self.show_tools_menu(selected_index)
            choice = self.read_single_key("Selecciona una opción: ")
            command, selected_index, valid = self.resolve_menu_command("tools", choice, selected_index)
            if not valid:
                self.print("❌ Opción inválida")
                self.input("\nPresiona Enter para continuar...")
                continue
            if command is None:
                continue

            if command == "tool_analyze_content":
                self._handle_analyze_content()
            elif command == "tool_debug_files":
                self._handle_debug_files()
            elif command == "tool_emoji":
                self._handle_emoji_test()
            elif command == "tool_calc_dates":
                self._handle_calc_dates()
            elif command == "tool_pomodoro":
                self._handle_pomodoro()
            elif command == "back":
                break
            else:
                self.print("❌ Opción inválida")
                self.input("\nPresiona Enter para continuar...")

    def _handle_analyze_content(self) -> None:
        self.clear_screen()
        filename = self.input("Nombre del archivo a analizar: ").strip()
        filepath = filename if os.path.exists(filename) else os.path.join(self.directory, filename)
        if os.path.exists(filepath):
            self.debug_content_parsing(filepath)
        else:
            self.print("❌ Archivo no encontrado")
        self.input("\nPresiona Enter para continuar...")

    def _handle_debug_files(self) -> None:
        self.clear_screen()
        self.debug_files_in_directory(self.directory)
        self.input("\nPresiona Enter para continuar...")

    def _handle_emoji_test(self) -> None:
        self.clear_screen()
        self.test_emoji_pattern()
        self.input("\nPresiona Enter para continuar...")

    def _handle_calc_dates(self) -> None:
        self.clear_screen()
        filename = self.input("Nombre del archivo para calcular fechas: ").strip()
        filepath = filename if os.path.exists(filename) else os.path.join(self.directory, filename)
        if os.path.exists(filepath):
            content = self.safe_file_read(filepath)
            if content:
                parser = self.content_parser_factory(content)
                dates = parser.get_next_week_dates()
                self.print("📋 Próximas fechas calculadas:")
                for i, date in enumerate(dates):
                    self.print(f"  {WEEKDAYS[i]}: {date.strftime('%d/%m/%Y')}")
        else:
            self.print("❌ Archivo no encontrado")
        self.input("\nPresiona Enter para continuar...")

    def _handle_pomodoro(self) -> None:
        self.clear_screen()
        if self.run_pomodoro is None:
            from brackets.modules.pomodoro_timer import run_pomodoro_standalone

            event_log = getattr(self, '_event_log', None)
            run_pomodoro_standalone(
                base_dir=self.vault_root,
                event_log=event_log,
                entity_manager=self.entity_manager,
                input_fn=self.input,
                print_fn=self.print,
            )
            return
        self.run_pomodoro(self.vault_root)
