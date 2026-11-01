#!/usr/bin/env python3
"""
Controlador interactivo para la gestión de Definiciones y Enlaces (Jira, Confluence, etc.) en Brackets.
"""

from __future__ import annotations
from typing import Callable, Optional, TYPE_CHECKING

from brackets.core.menu_navigator import MenuNavigator, MenuOption
from brackets.core.menu_engine import MenuEngine
from brackets.models.entities import WeekSchedule

if TYPE_CHECKING:
    from brackets.managers.entity_manager import EntityManager


class DefinitionsController:
    """Gestiona la subpantalla interactiva de registro y vinculación de definiciones y enlaces externos."""

    def __init__(
        self,
        manager: EntityManager,
        vault_root: str,
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[[str], None] = print,
        read_single_key_fn: Optional[Callable[[str], str]] = None,
        clear_screen_fn: Optional[Callable[[], None]] = None,
        sync_markdown_fn: Optional[Callable[[WeekSchedule], None]] = None,
        menu_engine: Optional[MenuEngine] = None,
    ):
        self.manager = manager
        self.vault_root = vault_root
        self.menu_engine = menu_engine or MenuEngine(self.vault_root)
        self.input = input_fn
        self.print = print_fn
        self.read_single_key = read_single_key_fn
        self.clear_screen = clear_screen_fn or (lambda: None)
        self._sync_markdown = sync_markdown_fn or (lambda w: None)

    def manage_definitions_menu(self, week: WeekSchedule) -> Optional[str]:
        """Subpantalla interactiva para gestionar y crear definiciones/enlaces."""
        default_options = [
            MenuOption("1", "🎫 Nueva Definición Jira (ej: PROJ-1234)", "new_jira_def", aliases=["j"]),
            MenuOption("2", "🔗 Nueva Definición Personalizada (ID + URL)", "new_custom_def", aliases=["c"]),
            MenuOption("3", "📋 Listar Definiciones registradas", "list_defs", aliases=["l"]),
            MenuOption("4", "🗑️  Eliminar Definición", "delete_def", aliases=["d"]),
        ]
        options = self.menu_engine.get_menu_options("definitions", default_options=default_options)
        title = self.menu_engine.menu_title("definitions", "🔗 G E S T I Ó N  D E  D E F I N I C I O N E S  Y  E N L A C E S")
        navigator = MenuNavigator(
            title=title,
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
                if opt.action_id == "new_jira_def":
                    self._action_new_jira_definition(week)
                    return "refresh"
                elif opt.action_id == "new_custom_def":
                    self._action_new_custom_definition(week)
                    return "refresh"
                elif opt.action_id == "list_defs":
                    self._action_list_definitions()
                elif opt.action_id == "delete_def":
                    self._action_delete_definition(week)
                    return "refresh"

    def _action_new_jira_definition(self, week: WeekSchedule) -> None:
        code = self.input("🎫 Código del ticket Jira (ej: PROJ-1234): ").strip()
        if not code:
            return
        clean_code = code.replace("[", "").replace("]", "").replace("🎫", "").strip().upper()
        formatted_id = f"[🎫{clean_code}]"
        base_jira = getattr(self.manager, "jira_base_url", "https://jira.atlassian.net/browse/")
        default_url = f"{base_jira}{clean_code}"
        url_input = self.input(f"URL [{default_url}] (Enter para aceptar): ").strip()
        final_url = url_input if url_input else default_url

        def_obj = self.manager.ensure_definition(def_id=formatted_id, url=final_url, title=clean_code)
        if hasattr(week, "definition_ids") and def_obj.id not in week.definition_ids:
            week.definition_ids.append(def_obj.id)
            self.manager.save_week(week)
        self._sync_markdown(week)
        self.print(f"\n✅ Definición creada: {def_obj.id}: {def_obj.url}")
        self.input("Presiona Enter para continuar...")

    def _action_new_custom_definition(self, week: WeekSchedule) -> None:
        tag = self.input("🏷️  Etiqueta / ID (ej: [🤖Export Validator] o [📊Grafana]): ").strip()
        if not tag:
            return
        if not tag.startswith("[") or not tag.endswith("]"):
            tag = f"[{tag}]"
        url = self.input("🌐 URL de destino: ").strip()
        if not url:
            self.print("❌ La URL es obligatoria.")
            self.input("Presiona Enter para continuar...")
            return
        title = self.input("📝 Título descriptivo (opcional): ").strip() or None

        def_obj = self.manager.ensure_definition(def_id=tag, url=url, title=title)
        if hasattr(week, "definition_ids") and def_obj.id not in week.definition_ids:
            week.definition_ids.append(def_obj.id)
            self.manager.save_week(week)
        self._sync_markdown(week)
        self.print(f"\n✅ Definición creada: {def_obj.id}: {def_obj.url}")
        self.input("Presiona Enter para continuar...")

    def _action_list_definitions(self) -> None:
        self.clear_screen()
        self.print("=" * 65)
        self.print("🔗 DEFINICIONES Y ENLACES REGISTRADOS")
        self.print("=" * 65)
        if not self.manager.definitions:
            self.print("  (No hay definiciones registradas)")
        else:
            for def_id, d in sorted(self.manager.definitions.items()):
                title_suffix = f" ({d.title})" if d.title else ""
                self.print(f"  • {d.id}: {d.url}{title_suffix}")
        self.print("=" * 65)
        self.input("\nPresiona Enter para continuar...")

    def _action_delete_definition(self, week: WeekSchedule) -> None:
        if not self.manager.definitions:
            self.print("❌ No hay definiciones para eliminar.")
            self.input("Presiona Enter para continuar...")
            return
        sorted_keys = sorted(self.manager.definitions.keys())
        self.print("\nDefiniciones registradas:")
        for idx, k in enumerate(sorted_keys, start=1):
            d = self.manager.definitions[k]
            self.print(f"  [{idx}] {d.id}: {d.url}")
        num_str = self.input(f"\nNúmero de definición a eliminar (1-{len(sorted_keys)}) [Enter para cancelar]: ").strip()
        if not num_str:
            return
        try:
            num = int(num_str)
            if 1 <= num <= len(sorted_keys):
                target_key = sorted_keys[num - 1]
                del self.manager.definitions[target_key]
                self.manager.save_definitions()
                self._sync_markdown(week)
                self.print(f"✅ Definición eliminada: {target_key}")
                self.input("Presiona Enter para continuar...")
            else:
                self.print("❌ Número fuera de rango.")
                self.input("Presiona Enter para continuar...")
        except ValueError:
            self.print("❌ Ingresa un número válido.")
            self.input("Presiona Enter para continuar...")
