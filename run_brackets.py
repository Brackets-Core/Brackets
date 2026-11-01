#!/usr/bin/env python3
"""Script principal de lanzamiento para el Sistema Brackets.
Este archivo actúa como punto de entrada desde la raíz del proyecto.
"""

import sys
import os

# Agregar el directorio raíz que contiene el paquete brackets al path
core_dir = os.path.dirname(os.path.abspath(__file__))
if core_dir not in sys.path:
    sys.path.insert(0, core_dir)

# Importar y ejecutar el main desde brackets
from brackets.main import main

if __name__ == "__main__":
    main()
