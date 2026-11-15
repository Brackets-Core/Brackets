"""Entry point for running the Brackets app as a module.

Usage:
    python -m brackets
"""

import sys

if sys.platform == 'win32':
    # Prefer reconfigure when available to avoid closing buffers
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    else:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from .main import main as _main

def main():
    _main()

if __name__ == '__main__':
    main()