#!/usr/bin/env python3
"""Utilities to resolve workspace/vault execution scope."""

import os


def resolve_workspace_context(current_dir: str) -> tuple[str, bool]:
    """Resolve execution context for vault selection.

    Returns:
        tuple(workspace_root, local_only)
        - workspace_root: detected workspace root or local vault root.
        - local_only: True when executed from a local vault context.
    """
    cursor = os.path.abspath(current_dir)
    visited = set()

    while cursor not in visited:
        visited.add(cursor)

        is_workspace_root = (
            (os.path.exists(os.path.join(cursor, "main.py")) and os.path.exists(os.path.join(cursor, "core")))
            or os.path.exists(os.path.join(cursor, "vaults.yaml"))
            or os.path.exists(os.path.join(cursor, "brackets", "brackets"))
        )
        is_vault_root = os.path.exists(os.path.join(cursor, "data", "config.yaml"))

        if is_vault_root:
            return cursor, True

        if is_workspace_root:
            return cursor, False

        parent = os.path.abspath(os.path.join(cursor, ".."))
        if parent == cursor:
            break
        cursor = parent

    return os.path.abspath(current_dir), False
