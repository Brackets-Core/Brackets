#!/usr/bin/env python3
"""Startup orchestration for Brackets CLI."""

import os
from typing import Callable, Optional

from brackets.core.cli_actions import dispatch_cli_action, has_action_flags
from brackets.core.vault_selection import select_vault_directory


def run_startup_flow(
    args,
    current_dir: str,
    manager_factory: Callable[[str], object],
    has_action_flags_fn: Callable[[object], bool] = has_action_flags,
    select_vault_directory_fn: Callable[..., tuple[Optional[str], Optional[int]]] = select_vault_directory,
    dispatch_cli_action_fn: Callable[[object, object, str], Optional[int]] = dispatch_cli_action,
) -> Optional[int]:
    """Run startup orchestration for CLI mode selection and command dispatch.

    Returns:
        Optional exit code. None means interactive flow ended naturally.
    """
    vault_arg = getattr(args, "vault", None) or getattr(args, "directory", None) or os.environ.get("BRACKETS_VAULT")

    if getattr(args, "web", False):
        from brackets.web import run_web_server

        port = getattr(args, "port", 8080)
        open_browser = not getattr(args, "no_browser", False)
        target_root = vault_arg or current_dir
        run_web_server(port=port, workspace_root=target_root, open_browser=open_browser)
        return 0

    has_flags = has_action_flags_fn(args)
    vault_directory, early_exit_code = select_vault_directory_fn(
        directory_arg=vault_arg,
        has_flags=has_flags,
        current_dir=current_dir,
    )

    if early_exit_code is not None:
        if early_exit_code == 0:
            print("\n👋 ¡Hasta luego!")
        return early_exit_code

    if vault_directory is None:
        vault_directory = "."

    resolved_vault_dir = vault_directory if os.path.isabs(vault_directory) else os.path.abspath(
        os.path.join(current_dir, vault_directory)
    )
    if not os.path.exists(os.path.join(resolved_vault_dir, "data", "config.yaml")):
        print("❌ Directorio de vault inválido: falta data/config.yaml")
        return 2

    manager = manager_factory(vault_directory)

    exit_code = dispatch_cli_action_fn(args, manager, vault_directory)
    if exit_code is not None:
        return exit_code

    manager.run()
    return None
