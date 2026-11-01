#!/usr/bin/env python3
"""Demo completa del asistente de creación de vault."""

import sys
import os

# Agregar brackets al path
CORE_PATH = os.path.join(os.path.dirname(__file__), "brackets")
sys.path.insert(0, CORE_PATH)

from brackets.utils.vault_creator import create_new_vault

print("\n" + "="*60)
print("🧪 DEMO: Creación de Vault")
print("="*60)

print("\nSimulando creación de vault 'DemoVault'...")
print("  - Nombre: DemoVault")
print("  - Descripción: Vault de demostración")
print("  - Bitácoras: Desactivadas (solo docs)")

# Simular la creación sin interacción
workspace = r"c:\Projects\brackets-workspace"

# Crear directorio de prueba
vault_name = "DemoVault_Test"
vault_path = os.path.join(workspace, vault_name)

print(f"\n📂 Ruta destino: {vault_path}")

# Verificar si existe
if os.path.exists(vault_path):
    print(f"⚠️  El vault ya existe. Saltando creación.")
else:
    print("\n💡 Para crear el vault interactivamente, ejecuta:")
    print("   python run_brackets.py")
    print("   Y selecciona '➕ Crear nuevo vault'")

print("\n" + "="*60)
print("Estructura que se crearía:")
print("="*60)
print(f"""
{vault_name}/
├── data/
│   ├── config.yaml          # Configuración del vault
│   └── categories.yaml      # Categorías de documentos
├── run_brackets.py          # Launcher del sistema
├── README.md                # Documentación
└── .gitignore               # Ignores para git
""")

print("✅ Demo completada")
