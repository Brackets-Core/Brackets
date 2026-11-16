#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Punto de entrada CLI para el sistema de bitácoras Brackets.
"""

import sys
import os

# Configurar UTF-8 para Windows (seguro también bajo pythonw.exe sin consola)
if sys.platform == 'win32':
    import io
    if sys.stdout is not None:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        elif hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    else:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    if sys.stderr is not None:
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
        elif hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    else:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')

# Asegurar que el directorio raíz del motor brackets esté en sys.path
_pkg_root = os.path.dirname(os.path.abspath(__file__))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from core.bitacora_manager import BitacoraManager, clear_screen
from core.cli_parser import build_cli_parser
from core.startup import run_startup_flow
from core.workspace_context import resolve_workspace_context as _resolve_workspace_context


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
