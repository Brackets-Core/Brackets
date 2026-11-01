#!/usr/bin/env python3
"""Vault selection bootstrap helpers for CLI startup."""

import os
from typing import Callable, Optional, Tuple

from brackets.core.workspace_context import resolve_workspace_context


def _resolve_candidate_directory(directory_arg: str, current_dir: Optional[str]) -> str:
    """Resolve directory arg to absolute path using current_dir as base for relatives."""
    if os.path.isabs(directory_arg):
        return os.path.abspath(directory_arg)
    base = current_dir or os.getcwd()
    return os.path.abspath(os.path.join(base, directory_arg))


def _is_vault_root(path: str) -> bool:
    """Return True when path has a vault config file."""
    return os.path.exists(os.path.join(path, "data", "config.yaml"))


def select_vault_directory(
    directory_arg: Optional[str],
    has_flags: bool,
    current_dir: Optional[str] = None,
    resolve_workspace_context_fn: Callable[[str], Tuple[str, bool]] = resolve_workspace_context,
    vault_manager_factory: Optional[Callable[[str], object]] = None,
    create_new_vault_fn: Optional[Callable[[str], Optional[str]]] = None,
) -> tuple[Optional[str], Optional[int]]:
    """Resolve vault directory before BitacoraManager initialization.

    Returns:
        tuple(vault_directory, early_exit_code)
        - vault_directory: selected/derived vault path (or None if exiting).
        - early_exit_code: exit code when startup should end early.
    """
    scope_root, local_only = resolve_workspace_context_fn(current_dir or os.getcwd())

    vault_indicator = directory_arg or os.environ.get("BRACKETS_VAULT")

    if vault_indicator is not None:
        resolved_dir = _resolve_candidate_directory(vault_indicator, current_dir)
        if _is_vault_root(resolved_dir):
            return resolved_dir, None

        if vault_manager_factory is None:
            from brackets.managers.vault_manager import VaultManager
            vault_manager_factory = VaultManager

        vm = vault_manager_factory(scope_root)
        if hasattr(vm, "resolve_vault_path"):
            found = vm.resolve_vault_path(vault_indicator)
            if found and _is_vault_root(found):
                return found, None

        print(f"❌ No se encontró un vault válido para '{vault_indicator}' (falta data/config.yaml).")
        return None, 2

    if has_flags:
        if local_only:
            return scope_root, None

        print("❌ Para usar flags de acción debes ejecutar dentro de un vault local o indicar --vault / --directory o fijar BRACKETS_VAULT.")
        return None, 2

    if local_only:
        return scope_root, None

    if vault_manager_factory is None:
        from brackets.managers.vault_manager import VaultManager

        vault_manager_factory = VaultManager

    if create_new_vault_fn is None:
        from brackets.utils.vault_creator import create_new_vault

        create_new_vault_fn = create_new_vault

    vault_mgr = vault_manager_factory(scope_root)

    while True:
        selected = vault_mgr.show_vault_menu()
        if selected is None:
            return None, 0

        if selected == "CREATE_NEW":
            created_path = create_new_vault_fn(scope_root)
            if created_path:
                vault_mgr.refresh_vaults()
                return created_path, None
            continue

        resolved_selected = _resolve_candidate_directory(selected, current_dir)
        if _is_vault_root(resolved_selected):
            return resolved_selected, None

        print(f"❌ El directorio seleccionado no es un vault válido: {selected}")
        input("Presiona Enter para continuar...")
