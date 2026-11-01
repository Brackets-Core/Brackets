#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Punto de entrada CLI para el sistema de bitácoras Brackets.
"""

import sys
import os

# Configurar UTF-8 para Windows
if sys.platform == 'win32':
    import io
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Asegurar que el directorio raíz del motor brackets esté en sys.path
_pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from brackets.core.bitacora_manager import BitacoraManager, clear_screen
from brackets.core.cli_parser import build_cli_parser
from brackets.core.startup import run_startup_flow
from brackets.core.workspace_context import resolve_workspace_context as _resolve_workspace_context


def resolve_workspace_context(current_dir: str) -> tuple[str, bool]:
    """Compat wrapper kept for existing imports/tests."""
    return _resolve_workspace_context(current_dir)


def main():
    """Función principal del script."""
    parser = build_cli_parser()
    args = parser.parse_args()

    exit_code = run_startup_flow(
        args=args,
        current_dir=os.getcwd(),
        manager_factory=BitacoraManager,
    )
    if exit_code is not None:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
