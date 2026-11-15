#!/usr/bin/env python3
"""File-management menu controller extracted from BitacoraManager."""

import os
from typing import Callable, Optional


class FileManagementController:
    """Handle file-management submenu and related list/analyze flows."""

    def __init__(
        self,
        directory: str,
        show_file_management_menu_fn: Callable[[int], None],
        show_list_menu_fn: Callable[[int], None],
        resolve_menu_command_fn: Callable[[str, str, int], tuple[Optional[str], int, bool]],
        clear_screen_fn: Callable[[], None],
        read_single_key_fn: Callable[[str], str],
        weekly_gen,
        monthly_gen,
        finder,
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[..., None] = print,
        debug_content_parsing_fn: Optional[Callable[[str], None]] = None,
        debug_files_in_directory_fn: Optional[Callable[[str], None]] = None,
    ):
        self.directory = directory
        self.show_file_management_menu = show_file_management_menu_fn
        self.show_list_menu = show_list_menu_fn
        self.resolve_menu_command = resolve_menu_command_fn
        self.clear_screen = clear_screen_fn
        self.read_single_key = read_single_key_fn
        self.weekly_gen = weekly_gen
        self.monthly_gen = monthly_gen
        self.finder = finder
        self.input = input_fn
        self.print = print_fn

        if debug_content_parsing_fn is None:
            from utils.content_parser import debug_content_parsing

            debug_content_parsing_fn = debug_content_parsing
        if debug_files_in_directory_fn is None:
            from utils.file_finder import debug_files_in_directory

            debug_files_in_directory_fn = debug_files_in_directory

        self.debug_content_parsing = debug_content_parsing_fn
        self.debug_files_in_directory = debug_files_in_directory_fn

    def run_menu(
        self,
        on_manage_categories: Callable[[], None],
        on_global_replace: Callable[[], None],
        on_sync_yaml: Callable[[], None],
        on_add_task: Callable[[], None],
    ) -> None:
        """Run file-management submenu loop."""
        selected_index = 0
        while True:
            self.show_file_management_menu(selected_index)
            choice = self.read_single_key("Selecciona una opción: ")
            command, selected_index, valid = self.resolve_menu_command("file_management", choice, selected_index)
            if not valid:
                self.print("❌ Opción inválida")
                self.input("\nPresiona Enter para continuar...")
                continue
            if command is None:
                continue

            if command == "list_files":
                self.clear_screen()
                self.run_list_menu()
            elif command == "analyze_file":
                self.clear_screen()
                self.run_analyze_file()
            elif command == "manage_categories":
                self.clear_screen()
                on_manage_categories()
            elif command == "global_replace":
                self.clear_screen()
                on_global_replace()
            elif command == "sync_yaml":
                self.clear_screen()
                on_sync_yaml()
            elif command == "add_task":
                self.clear_screen()
                on_add_task()
            elif command == "back":
                break
            else:
                self.print("❌ Opción inválida")
                self.input("\nPresiona Enter para continuar...")

    def run_list_menu(self) -> None:
        """Run listing submenu loop."""
        selected_index = 0
        while True:
            self.show_list_menu(selected_index)
            choice = self.read_single_key("Selecciona una opción: ")
            command, selected_index, valid = self.resolve_menu_command("list", choice, selected_index)
            if not valid:
                self.print("❌ Opción inválida")
                self.input("\nPresiona Enter para continuar...")
                continue
            if command is None:
                continue

            if command == "list_weekly":
                self.clear_screen()
                self.print("\n📝 BITÁCORAS SEMANALES RECIENTES:")
                self.print("=" * 40)
                self.weekly_gen.list_recent_weeks(10)
                self.input("\nPresiona Enter para continuar...")

            elif command == "list_monthly":
                self.clear_screen()
                self.print("\n📋 ARCHIVOS MENSUALES RECIENTES:")
                self.print("=" * 40)
                self.monthly_gen.list_recent_months(10)
                self.input("\nPresiona Enter para continuar...")

            elif command == "list_debug":
                self.clear_screen()
                self.print("\n🔍 DEBUG - TODOS LOS ARCHIVOS:")
                self.print("=" * 40)
                self.debug_files_in_directory(self.directory)
                self.input("\nPresiona Enter para continuar...")

            elif command == "back":
                break

            else:
                self.print("❌ Opción inválida")
                self.input("\nPresiona Enter para continuar...")

    def run_analyze_file(self) -> None:
        """Run analyze-file flow."""
        self.print("\n🔍 ANALIZAR ARCHIVO ESPECÍFICO")
        self.print("=" * 35)

        self.print("Archivos semanales recientes:")
        weekly_files = self.finder.list_weekly_files()
        for i, (filepath, year, month, week) in enumerate(weekly_files[-5:], 1):
            filename = filepath.split("/")[-1] if "/" in filepath else filepath.split("\\")[-1]
            self.print(f"  {i}. {filename}")

        self.print("\nArchivos mensuales recientes:")
        monthly_files = self.finder.list_monthly_files()
        for i, (filepath, year, month) in enumerate(monthly_files[-3:], 6):
            filename = filepath.split("/")[-1] if "/" in filepath else filepath.split("\\")[-1]
            self.print(f"  {i}. {filename}")

        self.print("\nO escribe el nombre completo del archivo:")

        choice = self.input("Selecciona archivo (número o nombre): ").strip()

        filepath = None
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= 5 and choice_num <= len(weekly_files[-5:]):
                filepath = weekly_files[-5:][choice_num - 1][0]
            elif 6 <= choice_num <= 8 and (choice_num - 6) < len(monthly_files[-3:]):
                filepath = monthly_files[-3:][choice_num - 6][0]
        except ValueError:
            if os.path.exists(choice):
                filepath = choice
            elif os.path.exists(os.path.join(self.directory, choice)):
                filepath = os.path.join(self.directory, choice)

        if filepath:
            self.debug_content_parsing(filepath)
        else:
            self.print("❌ Archivo no encontrado")

        self.input("\nPresiona Enter para continuar...")
