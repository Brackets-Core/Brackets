"""Motor simple de menú basado en configuración YAML."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import yaml

from brackets.core.menu_navigator import MenuOption


DEFAULT_MENU_CONFIG: Dict[str, Any] = {
    "menus": {
        "main": {
            "title": "ERROR: menu_config.yaml no encontrado",
            "items": [
                {
                    "id": "exit",
                    "label": "Salir",
                    "keys": ["0", "q", "x"],
                    "action": "exec",
                    "command": "exit",
                },
            ],
        }
    }
}


class MenuEngine:
    """Carga menús desde YAML y resuelve entradas del usuario."""

    def __init__(self, vault_root: str, fallback_config: Optional[Dict[str, Any]] = None):
        self.vault_root = os.path.abspath(vault_root)
        self.fallback_config = fallback_config or DEFAULT_MENU_CONFIG
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        candidates = [
            os.path.join(self.vault_root, "data", "menu_config.yaml"),
            os.path.normpath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "menu_config.yaml")
            ),
        ]

        for path in candidates:
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as file:
                    data = yaml.safe_load(file) or {}
                if isinstance(data, dict) and isinstance(data.get("menus"), dict):
                    return data
            except Exception:
                continue

        return self.fallback_config

    def visible_items(self, menu_id: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        menus = self.config.get("menus", {})
        menu = menus.get(menu_id, {})
        raw_items = menu.get("items", []) if isinstance(menu, dict) else []
        visible: List[Dict[str, Any]] = []

        for item in raw_items:
            if not isinstance(item, dict):
                continue
            tag = item.get("context_tag")
            if tag and not context.get(tag, False):
                continue
            visible.append(item)

        return visible

    def menu_title(self, menu_id: str, default: str = "") -> str:
        menus = self.config.get("menus", {})
        menu = menus.get(menu_id, {})
        if isinstance(menu, dict):
            title = menu.get("title")
            if isinstance(title, str) and title.strip():
                return title
        return default

    def resolve_choice(
        self, menu_id: str, choice: str, context: Dict[str, Any]
    ) -> Optional[Tuple[str, Optional[str]]]:
        normalized = choice.strip().lower()
        if not normalized:
            return None

        for item in self.visible_items(menu_id, context):
            keys = item.get("keys", [])
            if not isinstance(keys, list):
                continue
            normalized_keys = [str(key).strip().lower() for key in keys if str(key).strip()]
            if normalized in normalized_keys:
                action = str(item.get("action", "noop"))
                command = item.get("command")
                return action, str(command) if command is not None else None

        return None

    def key_conflicts(self, menu_id: str, context: Dict[str, Any]) -> Dict[str, List[str]]:
        """Devuelve teclas duplicadas para los items visibles de un menú."""
        collisions: Dict[str, List[str]] = {}
        seen: Dict[str, List[str]] = {}

        for item in self.visible_items(menu_id, context):
            item_id = str(item.get("id") or item.get("label") or "unknown")
            keys = item.get("keys", [])
            if not isinstance(keys, list):
                continue

            for key in keys:
                normalized_key = str(key).strip().lower()
                if not normalized_key:
                    continue
                seen.setdefault(normalized_key, []).append(item_id)

        for key, owners in seen.items():
            if len(owners) > 1:
                collisions[key] = owners

        return collisions

    def all_key_conflicts(self, context: Dict[str, Any]) -> Dict[str, Dict[str, List[str]]]:
        """Devuelve conflictos de teclas por menú para los items visibles."""
        result: Dict[str, Dict[str, List[str]]] = {}
        menus = self.config.get("menus", {})
        if not isinstance(menus, dict):
            return result

        for menu_id in menus.keys():
            conflicts = self.key_conflicts(str(menu_id), context)
            if conflicts:
                result[str(menu_id)] = conflicts

        return result

    def get_menu_options(
        self,
        menu_id: str,
        context: Optional[Dict[str, Any]] = None,
        default_options: Optional[List[MenuOption]] = None,
    ) -> List[MenuOption]:
        """Obtiene las opciones de menú como objetos MenuOption para MenuNavigator."""
        items = self.visible_items(menu_id, context or {})
        if not items:
            return list(default_options) if default_options else []

        options: List[MenuOption] = []
        for item in items:
            keys = item.get("keys", [])
            if isinstance(keys, list) and keys:
                primary_key = str(keys[0])
                aliases = [str(k) for k in keys[1:]]
            else:
                primary_key = str(item.get("id", ""))
                aliases = []
            label = str(item.get("label", ""))
            action_id = str(item.get("command") or item.get("id", ""))
            group = item.get("group")
            options.append(
                MenuOption(
                    key=primary_key,
                    label=label,
                    action_id=action_id,
                    aliases=aliases,
                    group=group,
                )
            )
        return options
