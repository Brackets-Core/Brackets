#!/usr/bin/env python3
"""
Runner para ejecutar los tests del sistema Brackets.
Ejecutar desde la raíz del proyecto: python -m brackets.tests.run_tests
"""

import sys
import os

# Asegurar que el directorio raíz del proyecto está en el path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Importar y ejecutar los tests
from tests import test_consolidators

if __name__ == "__main__":
    print("\n🚀 Ejecutando tests desde brackets/tests/")
    # El módulo test_consolidators se ejecuta automáticamente
