#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coordinador principal para la gestión interactiva de bitácoras y vaults en Brackets.
"""

from __future__ import annotations
import os
import sys
import re
from typing import Dict, Callable, Optional, Any, List, Tuple
from datetime import datetime
import yaml

from brackets.generators.weekly import WeeklyGenerator
from brackets.generators.monthly import MonthlyGenerator
from brackets.utils.file_finder import FileFinder
from brackets.managers.settings_manager import SettingsManager, set_global_settings_manager
from brackets.managers.file_rename_manager import FileRenameManager
from brackets.consolidators.month import MonthConsolidator
from brackets.consolidators.year import YearConsolidator
from brackets.core.category_management_controller import CategoryManagementController
from brackets.core.configuration_controller import ConfigurationController
from brackets.core.file_management_controller import FileManagementController
from brackets.core.file_rename_controller import FileRenameController
from brackets.core.menu_engine import MenuEngine
from brackets.core.sync_yaml_controller import SyncYamlController
from brackets.core.tools_controller import ToolsController
from brackets.core.daily_hub_controller import DailyHubController
from brackets.core.cli_actions import add_task_to_latest_file
from brackets.worklog import EventLog
from brackets.core.menu_navigator import (
    KEY_UP,
    KEY_DOWN,
    KEY_ENTER,
    KEY_ESC,
    read_single_key,
)


def clear_screen() -> None:
    """Limpia la pantalla de la consola."""
    os.system('cls' if os.name == 'nt' else 'clear')


class BitacoraManager:
    """Clase principal para gestionar las bitácoras y orquestar subcontroladores."""

    def __init__(self, directory: str = "."):
        self.vault_root = os.path.abspath(directory)
        self.paths = self._load_vault_paths()
        self.notes_root = self.paths["notes_root"]
        self.data_dir = self.paths["data_dir"]
        self.directory = self.notes_root
        self.feature_flags = self._load_feature_flags()
        self.bitacoras_enabled = bool(self.feature_flags.get("bitacoras_enabled", True))
        self.vault_name = self._get_vault_name()
        self.vault_type = self._get_vault_type()
        self.settings = SettingsManager(directory)
        set_global_settings_manager(self.settings)
        self.weekly_gen = WeeklyGenerator(self.notes_root, self.settings)
        self.monthly_gen = MonthlyGenerator(self.notes_root)
        self.month_consolidator = MonthConsolidator(self.notes_root)
        self.year_consolidator = YearConsolidator(self.notes_root)
        self.finder = FileFinder(self.notes_root)
        self.menu_engine = MenuEngine(self.vault_root)
        self.menu_key_conflicts = self.menu_engine.all_key_conflicts(self._menu_context())
        self._menu_conflicts_reported = False
        self.category_manager = None
        self.file_rename_manager = None
        self.configuration_controller = None
        self.tools_controller = None
        self.file_management_controller = None
        self.category_management_controller = None
        self.sync_yaml_controller = None
        self.file_rename_controller = None
        self.daily_hub_controller = None
        self.event_log = EventLog(self.vault_root)

    def _menu_context(self) -> Dict[str, bool]:
        """Expone contexto dinámico consumido por MenuEngine."""
        return {
            "bitacoras_enabled": bool(self.bitacoras_enabled),
            "bitacoras_disabled": not bool(self.bitacoras_enabled),
            "active_vault": bool(self.vault_name),
            "vault_type_work": self.vault_type == "work",
            "vault_type_personal": self.vault_type == "personal",
        }

    def _get_vault_type(self) -> str:
        """Determina tipo de vault para reglas de visibilidad del menú."""
        config_path = os.path.join(self.vault_root, "data", "config.yaml")
        description = ""
        vault_name = ""

        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f) or {}

                vault_type = str(config_data.get("vault_type", "")).strip().lower()
                if vault_type in ("work", "personal"):
                    return vault_type

                description = str(config_data.get("description", "")).strip().lower()
                vault_name = str(config_data.get("vault_name", "")).strip().lower()
            except Exception:
                pass

        if "personal" in description or "personal" in vault_name:
            return "personal"
        if "personal" in os.path.basename(self.vault_root).lower():
            return "personal"

        return "work"

    def _execute_menu_command(self, command: Optional[str]) -> bool:
        """Ejecuta comandos del menú principal. Devuelve False para salir."""
        if command == "open_generation":
            self.handle_generation_menu()
        elif command == "open_consolidation":
            self.handle_consolidation_menu()
        elif command == "open_file_management":
            self.handle_file_management_menu()
        elif command == "open_project_backlog":
            self.handle_project_backlog()
        elif command == "open_notes_crud":
            self.handle_notes_crud()
        elif command == "open_tools":
            self.handle_tools_menu()
        elif command == "open_settings":
            self.handle_configuration()
        elif command == "open_help":
            self.show_help()
        elif command in ("open_sync_markdown", "sync_markdown"):
            self.handle_sync_markdown_menu()
        elif command == "open_daily_hub":
            if self.bitacoras_enabled:
                result = self.handle_daily_hub()
                if result == "exit":
                    return False
            else:
                self._show_bitacoras_disabled_message()
        elif command == "quick_new_weekly":
            if self.bitacoras_enabled:
                clear_screen()
                self.handle_weekly_creation()
            else:
                self._show_bitacoras_disabled_message()
        elif command == "quick_consolidate_month":
            if self.bitacoras_enabled:
                clear_screen()
                self.handle_month_consolidation()
            else:
                self._show_bitacoras_disabled_message()
        elif command == "exit":
            clear_screen()
            print("\n👋 ¡Hasta luego!")
            return False
        else:
            print("❌ Opción inválida. Por favor, selecciona una opción del menú.")
            input("Presiona Enter para continuar...")

        return True

    def _load_vault_paths(self) -> Dict[str, str]:
        """Carga rutas configurables del vault desde data/config.yaml."""
        notes_root = self.vault_root
        data_dir = os.path.join(self.vault_root, "data")

        config_path = os.path.join(self.vault_root, "data", "config.yaml")
        if not os.path.exists(config_path):
            return {
                "notes_root": notes_root,
                "data_dir": data_dir,
            }

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}

            paths = config_data.get("paths", {})
            if isinstance(paths, dict):
                configured_notes = paths.get("notes_root")
                if isinstance(configured_notes, str) and configured_notes.strip():
                    candidate = configured_notes.strip()
                    notes_root = candidate if os.path.isabs(candidate) else os.path.join(self.vault_root, candidate)

                configured_data = paths.get("data_dir")
                if isinstance(configured_data, str) and configured_data.strip():
                    candidate = configured_data.strip()
                    data_dir = candidate if os.path.isabs(candidate) else os.path.join(self.vault_root, candidate)

        except Exception:
            pass

        return {
            "notes_root": os.path.normpath(notes_root),
            "data_dir": os.path.normpath(data_dir),
        }

    def _load_feature_flags(self) -> Dict[str, bool]:
        """Carga feature flags desde data/config.yaml con fallback seguro."""
        config_path = os.path.join(self.vault_root, "data", "config.yaml")
        if not os.path.exists(config_path):
            return {}

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}

            flags = config_data.get("feature_flags", {})
            return flags if isinstance(flags, dict) else {}
        except Exception:
            return {}

    def _get_vault_name(self) -> str:
        """Obtiene el nombre del vault desde config.yaml o del nombre del directorio."""
        config_path = os.path.join(self.vault_root, "data", "config.yaml")

        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f) or {}
                vault_name = config_data.get("vault_name")
                if vault_name and isinstance(vault_name, str):
                    return vault_name.strip()
            except Exception:
                pass

        return os.path.basename(self.vault_root)

    def _show_bitacoras_disabled_message(self) -> None:
        print("\n⚠️ Función no disponible: bitácoras desactivadas en data/config.yaml")
        print("   Activa 'feature_flags.bitacoras_enabled: true' para usar esta opción.")
        input("\nPresiona Enter para continuar...")

    def _render_menu_items(self, menu_id: str, selected_index: int = 0) -> None:
        """Renderiza items del menú con selección visible para navegación por flechas."""
        items = self.menu_engine.visible_items(menu_id, self._menu_context())
        if not items:
            print("(sin opciones disponibles)")
            return

        bounded_index = max(0, min(selected_index, len(items) - 1))
        for i, item in enumerate(items):
            label = str(item.get("label", ""))
            keys = item.get("keys", [])
            primary_key = keys[0] if isinstance(keys, list) and keys else "?"
            aliases = "/".join(str(key) for key in keys[1:]) if isinstance(keys, list) and len(keys) > 1 else ""
            pointer = ">" if i == bounded_index else " "
            if aliases:
                print(f"{pointer} {primary_key}. {label} [{aliases}]")
            else:
                print(f"{pointer} {primary_key}. {label}")

    def _resolve_menu_command(
        self, menu_id: str, choice: str, selected_index: int
    ) -> Tuple[Optional[str], int, bool]:
        """Resuelve comando de menú a partir de tecla rápida o selección con flechas."""
        items = self.menu_engine.visible_items(menu_id, self._menu_context())
        if not items:
            return None, selected_index, False

        if choice == KEY_UP:
            return None, (selected_index - 1) % len(items), True
        if choice == KEY_DOWN:
            return None, (selected_index + 1) % len(items), True
        if choice == KEY_ENTER:
            action = str(items[selected_index].get("action", "exec"))
            if action == "noop":
                return "__NOOP__", selected_index, True
            command = items[selected_index].get("command")
            return str(command) if command is not None else None, selected_index, True

        if choice == KEY_ESC:
            for item in items:
                keys = item.get("keys", [])
                if "0" in keys or "q" in keys or item.get("command") in ("exit", "back"):
                    return str(item.get("command")), selected_index, True
            return None, selected_index, False

        resolved = self.menu_engine.resolve_choice(menu_id, choice, self._menu_context())
        if not resolved:
            return None, selected_index, False

        action, command = resolved
        if action == "noop":
            return "__NOOP__", selected_index, True
        return command, selected_index, True

    def show_main_menu(self, selected_index: int = 0) -> None:
        """Muestra el menú principal."""
        clear_screen()
        print(f"\n🗓️ GENERADOR DE BITÁCORAS - SISTEMA BRACKETS")
        print(f"📁 Vault: {self.vault_name}")

        if self.menu_key_conflicts and not self._menu_conflicts_reported:
            menu_count = len(self.menu_key_conflicts)
            print(f"⚠️ Aviso: se detectaron conflictos de quick-keys en {menu_count} menú(s).")
            self._menu_conflicts_reported = True

        print("=" * 50)
        menu_title = self.menu_engine.menu_title("main", "M E N U  P R I N C I P A L")
        print(f"{menu_title}")
        print("Usa flechas ↑/↓ y Enter, o quick-keys.")
        print("-" * 50)
        self._render_menu_items("main", selected_index)
        print("-" * 50)

    def _show_configured_menu(self, menu_id: str, heading: str, width: int, selected_index: int = 0) -> None:
        """Renderiza un menú con configuración YAML."""
        clear_screen()
        print(f"\n{heading} - {self.vault_name}")
        print("=" * width)
        menu_title = self.menu_engine.menu_title(menu_id, "")
        if menu_title:
            print(menu_title)
            print("Usa flechas ↑/↓ y Enter, o quick-keys.")
            print("-" * width)
        self._render_menu_items(menu_id, selected_index)
        print("-" * width)

    def show_generation_menu(self, selected_index: int = 0) -> None:
        """Muestra el menú de generación."""
        self._show_configured_menu("generation", "📝 GENERACIÓN DE BITÁCORAS", 50, selected_index)

    def show_consolidation_menu(self, selected_index: int = 0) -> None:
        """Muestra el menú de consolidación."""
        self._show_configured_menu("consolidation", "📦 CONSOLIDACIÓN DE ARCHIVOS", 50, selected_index)

    def show_file_management_menu(self, selected_index: int = 0) -> None:
        """Muestra el menú de gestión de archivos."""
        self._show_configured_menu("file_management", "📂 GESTIÓN DE ARCHIVOS Y CATEGORÍAS", 60, selected_index)

    def show_tools_menu(self, selected_index: int = 0) -> None:
        """Muestra el menú de herramientas."""
        self._show_configured_menu("tools", "🔧 HERRAMIENTAS Y UTILIDADES", 50, selected_index)

    def show_list_menu(self, selected_index: int = 0) -> None:
        """Muestra el menú de listado."""
        self._show_configured_menu("list", "📋 LISTAR ARCHIVOS", 40, selected_index)

    def handle_generation_menu(self) -> None:
        """Maneja el submenú de generación."""
        if not self.bitacoras_enabled:
            self._show_bitacoras_disabled_message()
            return

        selected_index = 0
        while True:
            self.show_generation_menu(selected_index)
            choice = read_single_key("Selecciona una opción: ")
            command, selected_index, valid = self._resolve_menu_command("generation", choice, selected_index)
            if not valid:
                print("❌ Opción inválida")
                input("\nPresiona Enter para continuar...")
                continue
            if command is None:
                continue
            if command == "create_weekly":
                clear_screen()
                self.handle_weekly_creation()
            elif command == "create_weekly_manual":
                clear_screen()
                self.handle_manual_weekly_creation()
            elif command == "create_monthly":
                clear_screen()
                self.handle_monthly_creation()
            elif command == "back":
                break
            else:
                print("❌ Opción inválida")
                input("\nPresiona Enter para continuar...")

    def handle_consolidation_menu(self) -> None:
        """Maneja el submenú de consolidación."""
        if not self.bitacoras_enabled:
            self._show_bitacoras_disabled_message()
            return

        selected_index = 0
        while True:
            self.show_consolidation_menu(selected_index)
            choice = read_single_key("Selecciona una opción: ")
            command, selected_index, valid = self._resolve_menu_command("consolidation", choice, selected_index)
            if not valid:
                print("❌ Opción inválida")
                input("\nPresiona Enter para continuar...")
                continue
            if command is None:
                continue
            if command == "consolidate_month":
                clear_screen()
                self.handle_month_consolidation()
            elif command == "consolidate_year":
                clear_screen()
                self.handle_year_consolidation()
            elif command == "back":
                break
            else:
                print("❌ Opción inválida")
                input("\nPresiona Enter para continuar...")

    def _get_file_management_controller(self) -> FileManagementController:
        if self.file_management_controller is None:
            self.file_management_controller = FileManagementController(
                directory=self.directory,
                show_file_management_menu_fn=self.show_file_management_menu,
                show_list_menu_fn=self.show_list_menu,
                resolve_menu_command_fn=self._resolve_menu_command,
                clear_screen_fn=clear_screen,
                read_single_key_fn=read_single_key,
                weekly_gen=self.weekly_gen,
                monthly_gen=self.monthly_gen,
                finder=self.finder,
                input_fn=input,
                print_fn=print,
            )
        return self.file_management_controller

    def _get_category_manager(self):
        from brackets.managers.category_manager import CategoryManager
        if self.category_manager is None:
            self.category_manager = CategoryManager(self.data_dir)
        return self.category_manager

    def _get_category_management_controller(self) -> CategoryManagementController:
        if self.category_management_controller is None:
            self.category_management_controller = CategoryManagementController(
                vault_name=self.vault_name,
                get_category_manager_fn=self._get_category_manager,
                clear_screen_fn=clear_screen,
                input_fn=input,
                print_fn=print,
                read_single_key_fn=read_single_key,
            )
        return self.category_management_controller

    def _get_sync_yaml_controller(self) -> SyncYamlController:
        if self.sync_yaml_controller is None:
            self.sync_yaml_controller = SyncYamlController(
                data_dir=self.data_dir,
                vault_root=self.vault_root,
                notes_root=self.notes_root,
                input_fn=input,
                print_fn=print,
            )
        return self.sync_yaml_controller

    def _get_file_rename_manager(self):
        if self.file_rename_manager is None:
            self.file_rename_manager = FileRenameManager(self.notes_root)
        return self.file_rename_manager

    def _get_file_rename_controller(self) -> FileRenameController:
        if self.file_rename_controller is None:
            self.file_rename_controller = FileRenameController(
                vault_name=self.vault_name,
                get_file_rename_manager_fn=self._get_file_rename_manager,
                clear_screen_fn=clear_screen,
                input_fn=input,
                print_fn=print,
                read_single_key_fn=read_single_key,
            )
        return self.file_rename_controller

    def handle_file_management_menu(self) -> None:
        """Maneja el submenú de gestión de archivos."""
        self._get_file_management_controller().run_menu(
            on_manage_categories=self.handle_category_management,
            on_global_replace=self.handle_file_rename,
            on_sync_yaml=self.handle_sync_yaml,
            on_add_task=self.handle_add_task,
        )

    def handle_add_task(self) -> None:
        """Maneja la creación rápida de tarea desde menú con flujo perfeccionado."""
        selected_target = "weekly"
        status_msg = ""
        
        while True:
            clear_screen()
            print("\n➕ AÑADIR TAREA RÁPIDA")
            print("=" * 30)
            
            if status_msg:
                print(f"{status_msg}\n")
                status_msg = ""
                
            print(f"🎯 Destino actual: {selected_target.upper()}")
            print("-" * 30)
            print("Escribe el texto de la tarea y presiona Enter.")
            print("Comandos rápidos para cambiar destino:")
            print("  w - Modo WEEKLY (Topics)")
            print("  t - Modo HOY (Sección diaria)")
            print("  m - Modo MONTHLY (Topics)")
            print("  0 - Volver al menú principal")
            print("-" * 30)
            
            user_input = input("Tarea o comando: ").strip()
            
            if not user_input or user_input == '0':
                break
                
            cmd = user_input.lower()
            if cmd == 'w':
                selected_target = "weekly"
                status_msg = "🎯 Destino cambiado a: WEEKLY (Topics)"
                continue
            if cmd == 't':
                selected_target = "today"
                status_msg = "🎯 Destino cambiado a: HOY (Sección diaria)"
                continue
            if cmd == 'm':
                selected_target = "monthly"
                status_msg = "🎯 Destino cambiado a: MONTHLY (Topics)"
                continue
            
            if add_task_to_latest_file(self.directory, user_input, selected_target, silent=True):
                self.event_log.append("task_added", task_text=user_input, target=selected_target)
                status_msg = f"✅ Tarea añadida: {user_input[:40]}{'...' if len(user_input)>40 else ''}"
            else:
                status_msg = "❌ Error al añadir la tarea (revisa que el archivo destino exista)"

    def handle_tools_menu(self) -> None:
        """Maneja el submenú de herramientas."""
        if self.tools_controller is None:
            hub = self._get_daily_hub_controller()
            self.tools_controller = ToolsController(
                directory=self.directory,
                vault_root=self.vault_root,
                show_tools_menu_fn=self.show_tools_menu,
                resolve_menu_command_fn=self._resolve_menu_command,
                clear_screen_fn=clear_screen,
                read_single_key_fn=read_single_key,
                input_fn=input,
                print_fn=print,
                entity_manager=hub.manager,
            )
            self.tools_controller._event_log = self.event_log
        self.tools_controller.run()

    def handle_sync_yaml(self) -> None:
        """Maneja la sincronización del YAML con el repositorio."""
        self._get_sync_yaml_controller().run()

    def handle_sync_markdown_menu(self) -> None:
        """Submenú de sincronización Markdown -> YAML desde el Menú Principal."""
        from brackets.core.menu_navigator import MenuNavigator, MenuOption
        from brackets.managers.markdown_sync_service import MarkdownSyncService

        default_options = [
            MenuOption("1", "📅 Sincronizar una semana específica", "sync_specific_week", aliases=["s", "1"]),
            MenuOption("2", "🌐 Sincronizar TODAS las semanas del Vault", "sync_all_weeks", aliases=["t", "all", "2"]),
        ]
        options = self.menu_engine.get_menu_options("sync_markdown", default_options=default_options)
        title = self.menu_engine.menu_title("sync_markdown", "🔄 S I N C R O N I Z A C I Ó N  M A R K D O W N  ➔  Y A M L")

        navigator = MenuNavigator(
            title=title,
            options=options,
            show_back=True,
            show_main_menu=False,
            print_fn=print,
            input_fn=input,
            read_single_key_fn=read_single_key,
            clear_screen_fn=clear_screen,
        )

        while True:
            nav_status, opt = navigator.prompt()
            if nav_status in ("back", "exit"):
                break

            if opt:
                hub = self._get_daily_hub_controller()
                service = MarkdownSyncService(hub.manager, self.vault_root)

                if opt.action_id == "sync_specific_week":
                    self._sync_specific_week_interactive(service, hub)
                elif opt.action_id == "sync_all_weeks":
                    self._sync_all_weeks_interactive(service, hub)

    def _sync_specific_week_interactive(self, service: Any, hub: Any) -> None:
        clear_screen()
        print("=" * 65)
        print("📅 SINCRONIZAR SEMANA ESPECÍFICA (.md ➔ YAML)")
        print("=" * 65)

        available_weeks = []
        if os.path.exists(self.vault_root):
            for fname in sorted(os.listdir(self.vault_root)):
                m = re.match(r'^\[(\d{4})\]\[(\d{2})\]Week(\d{2})\.md$', fname)
                if m:
                    available_weeks.append((int(m.group(1)), int(m.group(2)), int(m.group(3)), fname))

        if not available_weeks:
            print("⚠️ No se encontraron archivos de bitácoras semanales en el vault.")
            input("\nPresiona Enter para continuar...")
            return

        print("Semanas disponibles:")
        recent_subset = available_weeks[-10:]
        for idx, (y, m, w, fname) in enumerate(recent_subset, start=1):
            print(f"  [{idx}] {fname} ({y}-W{w:02d})")

        choice = input(f"\nSelecciona número de la lista (1-{len(recent_subset)}) o escribe el número de semana (ej: 36) [Enter para cancelar]: ").strip()
        if not choice:
            return

        target_file = None
        target_year = datetime.now().year
        target_week_num = None

        try:
            val = int(choice)
            if 1 <= val <= len(recent_subset):
                y, m, w, fname = recent_subset[val - 1]
                target_year = y
                target_week_num = w
                target_file = os.path.join(self.vault_root, fname)
            else:
                target_week_num = val
                match_wk = next(((y, m, w, f) for (y, m, w, f) in available_weeks if w == target_week_num), None)
                if match_wk:
                    target_year, _, _, fname = match_wk
                    target_file = os.path.join(self.vault_root, fname)
        except ValueError:
            print("❌ Entrada inválida.")
            input("\nPresiona Enter para continuar...")
            return

        if not target_file or not os.path.exists(target_file):
            print(f"❌ No se encontró el archivo para la semana {target_week_num}.")
            input("\nPresiona Enter para continuar...")
            return

        print(f"\n🔄 Sincronizando {os.path.basename(target_file)}...")
        try:
            synced = service.sync_week_from_markdown(target_file, target_year, target_week_num)
            reloaded_week = hub.manager.load_week(target_year, target_week_num, reload=True)
            if reloaded_week:
                hub._sync_markdown(reloaded_week)
            if synced:
                print(f"✅ Semana {target_week_num:02d} ({os.path.basename(target_file)}) sincronizada con éxito.")
            else:
                print("ℹ️ No se detectaron cambios pendientes.")
        except Exception as ex:
            print(f"❌ Error al sincronizar semana: {ex}")

        input("\nPresiona Enter para continuar...")

    def _sync_all_weeks_interactive(self, service: Any, hub: Any) -> None:
        clear_screen()
        print("=" * 65)
        print("🌐 SINCRONIZAR TODAS LAS SEMANAS (.md ➔ YAML)")
        print("=" * 65)
        confirm = input("¿Deseas sincronizar todas las bitácoras semanales del Vault? (s/N): ").strip().lower()
        if confirm not in ("s", "si", "y", "yes"):
            print("Operación cancelada.")
            input("\nPresiona Enter para continuar...")
            return

        print("\n🔄 Escaneando y sincronizando todas las semanas...")
        synced_files: List[str] = []
        if os.path.exists(self.vault_root):
            for fname in sorted(os.listdir(self.vault_root)):
                m = re.match(r'^\[(\d{4})\]\[\d{2}\]Week(\d{2})\.md$', fname)
                if m:
                    y = int(m.group(1))
                    w = int(m.group(2))
                    full_path = os.path.join(self.vault_root, fname)
                    try:
                        if service.sync_week_from_markdown(full_path, y, w):
                            synced_files.append(fname)
                            print(f"  ✓ {fname} sincronizado")
                    except Exception as ex:
                        print(f"  ⚠️ Error al sincronizar {fname}: {ex}")

        if synced_files:
            print(f"\n✅ {len(synced_files)} archivo(s) semanal(es) sincronizado(s) con la base de datos YAML.")
        else:
            print("\nℹ️ No se detectaron cambios pendientes en los archivos Markdown.")

        input("\nPresiona Enter para continuar...")

    def handle_weekly_creation(self) -> None:
        """Maneja la creación de bitácora semanal."""
        print("\n📝 CREAR BITÁCORA SEMANAL")
        print("=" * 30)

        success = self.weekly_gen.create_next_or_manual_weekly_bitacora()
        if success:
            self.event_log.append("bitacora_generated", type="weekly")
            print("\n✅ ¡Bitácora semanal creada exitosamente!")
        else:
            print("\n❌ Error al crear la bitácora semanal")

        input("\nPresiona Enter para continuar...")

    def handle_manual_weekly_creation(self) -> None:
        """Maneja la creación manual de bitácora semanal."""
        success = self.weekly_gen.create_manual_weekly_bitacora()
        if success:
            print("\n✅ ¡Bitácora semanal manual creada exitosamente!")
        else:
            print("\n❌ Error al crear la bitácora manual")

        input("\nPresiona Enter para continuar...")

    def handle_monthly_creation(self) -> None:
        """Maneja la creación de archivo mensual."""
        print("\n📋 CREAR ARCHIVO MENSUAL")
        print("=" * 30)

        success = self.monthly_gen.create_next_monthly_topics()
        if success:
            self.event_log.append("bitacora_generated", type="monthly")
            print("\n✅ ¡Archivo mensual creado exitosamente!")
        else:
            print("\n❌ Error al crear el archivo mensual")

    def handle_month_consolidation(self) -> None:
        """Maneja la consolidación de un mes completo."""
        success = self.month_consolidator.interactive_consolidate()
        input("\nPresiona Enter para continuar...")

    def handle_year_consolidation(self) -> None:
        """Maneja la consolidación de un año completo."""
        success = self.year_consolidator.interactive_consolidate()
        input("\nPresiona Enter para continuar...")

    def handle_list_files(self) -> None:
        """Maneja el listado de archivos."""
        self._get_file_management_controller().run_list_menu()

    def handle_analyze_file(self) -> None:
        """Maneja el análisis de archivo específico."""
        self._get_file_management_controller().run_analyze_file()

    def handle_category_management(self) -> None:
        """Maneja la gestión de categorías y documentos."""
        self._get_category_management_controller().run()

    def handle_file_rename(self) -> None:
        """Maneja la búsqueda y reemplazo global de texto."""
        self._get_file_rename_controller().run()

    def handle_configuration(self) -> None:
        """Maneja la configuración viva (horarios y calendario)."""
        if self.configuration_controller is None:
            self.configuration_controller = ConfigurationController(
                settings=self.settings,
                vault_name=self.vault_name,
                show_configured_menu_fn=self._show_configured_menu,
                resolve_menu_command_fn=self._resolve_menu_command,
                clear_screen_fn=clear_screen,
                read_single_key_fn=read_single_key,
                input_fn=input,
                print_fn=print,
            )
        self.configuration_controller.run()

    def show_help(self) -> None:
        """Muestra información de ayuda."""
        clear_screen()
        print(f"\n❓ AYUDA - GENERADOR DE BITÁCORAS")
        print(f"📁 Vault: {self.vault_name}")
        print("=" * 55)
        bitacoras_status = "activadas" if self.bitacoras_enabled else "desactivadas"
        print("""
📝 BITÁCORAS SEMANALES:
• Formato: [YYYY][MM]WeekXX.md
• Contienen sección TOPICS con tareas pendientes
• Incluyen días de trabajo con ubicación (🏠 casa / 🚗 oficina)
• Se transfieren automáticamente las tareas pendientes

📋 ARCHIVOS MENSUALES:
• Formato: [YYYY][MM]MonthTopics.md
• Contienen objetivos y proyectos del mes
• Se limpian automáticamente las tareas completadas [x]
• Incluyen emoji de estación según el mes

🏢 PATRÓN DE TRABAJO:
• Configurable en el menú "⚙️ Configuración"
• Fuente de verdad: data/work_calendar.yaml
• Día alterno (par/impar) editable
• Festivos y vacaciones marcan el día como 🏖️ automáticamente

🔧 FUNCIONES PRINCIPALES:
• Creación automática de siguiente bitácora
• Transferencia de tareas pendientes
• Cálculo automático de fechas
• Limpieza de tareas completadas
• Herramientas de debug y análisis
        """)
        print("\n🧩 MODO DE USO:")
        print(f"• Estado actual de bitácoras: {bitacoras_status}")
        print("• Puedes activar/desactivar bitácoras en data/config.yaml")
        print("• Clave: feature_flags.bitacoras_enabled (true/false)")
        input("\nPresiona Enter para continuar...")

    def _get_daily_hub_controller(self) -> DailyHubController:
        """Obtiene o inicializa el controlador del Hub Diario."""
        if self.daily_hub_controller is None:
            self.daily_hub_controller = DailyHubController(
                vault_root=self.vault_root,
                input_fn=input,
                print_fn=print,
                read_single_key_fn=read_single_key,
                clear_screen_fn=clear_screen,
            )
        return self.daily_hub_controller

    def handle_daily_hub(self) -> str:
        """Ejecuta el Hub Diario interactivo."""
        return self._get_daily_hub_controller().run()

    def handle_project_backlog(self) -> None:
        """Ejecuta el submenú de gestión de proyectos, backlog e ideas."""
        hub = self._get_daily_hub_controller()
        week, day = hub._get_active_week_and_day()
        from brackets.core.project_backlog_controller import ProjectBacklogController
        ctrl = ProjectBacklogController(
            entity_manager=hub.manager,
            current_week=week,
            current_day=day,
            vault_root=self.vault_root,
            input_fn=input,
            print_fn=print,
            clear_screen_fn=clear_screen,
            read_single_key_fn=read_single_key,
        )
        ctrl.run()

    def handle_notes_crud(self) -> None:
        """Ejecuta el módulo CRUD de gestión de notas en modo global."""
        hub = self._get_daily_hub_controller()
        from brackets.core.note_crud_controller import NoteCrudController
        ctrl = NoteCrudController(
            entity_manager=hub.manager,
            current_week=None,
            vault_root=self.vault_root,
            input_fn=input,
            print_fn=print,
            clear_screen_fn=clear_screen,
            read_single_key_fn=read_single_key,
        )
        ctrl.run()

    def run(self) -> None:
        """Ejecuta el menú principal o inicia en el Hub Diario si las bitácoras están activas."""
        self.event_log.append("session_start", vault=self.vault_name)
        try:
            from brackets.worklog.log4brackets import log4brackets
            log4brackets.set_vault_root(self.vault_root)
            log4brackets.log_startup(vault_name=self.vault_name)
        except Exception:
            pass

        if self.bitacoras_enabled:
            hub_result = self.handle_daily_hub()
            if hub_result == "exit":
                return

        selected_index = 0
        while True:
            try:
                self.show_main_menu(selected_index)
                choice = read_single_key("Selecciona una opción: ")
                command, selected_index, valid = self._resolve_menu_command("main", choice, selected_index)

                if not valid:
                    print("❌ Opción inválida. Por favor, selecciona una opción del menú.")
                    input("Presiona Enter para continuar...")
                    continue

                if command is None:
                    continue

                if command == "__NOOP__":
                    self._show_bitacoras_disabled_message()
                    continue

                resolved = self.menu_engine.resolve_choice("main", command, self._menu_context())
                if not resolved:
                    action = "exec"
                else:
                    action, _ = resolved

                if action == "noop":
                    self._show_bitacoras_disabled_message()
                    continue

                if action == "exec" and not self._execute_menu_command(command):
                    break

            except KeyboardInterrupt:
                print("\n\n👋 ¡Hasta luego!")
                break
            except Exception as e:
                print(f"\n❌ Error inesperado: {e}")
                print("Por favor, reporta este error si persiste.")
                input("Presiona Enter para continuar...")
