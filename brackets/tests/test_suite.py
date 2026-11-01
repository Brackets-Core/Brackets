#!/usr/bin/env python3
"""
Compatibilidad hacia atrás para el runner interactivo de tests de Brackets.

Uso recomendado:
    python -m unittest discover brackets/tests
O el runner interactivo con formateo de consola:
    python -m brackets.tests.run_all_tests
"""

import sys


def main():
    from brackets.tests.run_all_tests import run_all_tests
    success = run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
