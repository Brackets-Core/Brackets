#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Asistente interactivo para crear nuevos vaults.
"""

import os
import sys
import json


def create_new_vault(workspace_root: str) -> str:
    """
    Asistente interactivo para crear un nuevo vault.

    Args:
        workspace_root: Raíz del workspace donde crear el vault

    Returns:
        Ruta del vault creado, o None si se cancela
    """
    print("\n" + "=" * 60)
    print("🆕 ASISTENTE DE CREACIÓN DE VAULT")
    print("=" * 60)

    # 1. Nombre del vault
    while True:
        print("\n📝 Paso 1: Nombre del vault")
        vault_name = input("Nombre (ej: PersonalNotes, ProjectX): ").strip()

        if not vault_name:
            print("❌ El nombre no puede estar vacío")
            continue

        # Validar nombre
        if any(c in vault_name for c in r'\/:*?"<>|'):
            print("❌ El nombre contiene caracteres no válidos")
            continue

        vault_path = os.path.join(workspace_root, vault_name)

        if os.path.exists(vault_path):
            print(f"❌ Ya existe un directorio con ese nombre: {vault_path}")
            retry = input("¿Intentar con otro nombre? (S/n): ").strip().lower()
            if retry == 'n':
                return None
            continue

        break

    # 2. Descripción (opcional)
    print("\n📄 Paso 2: Descripción (opcional)")
    description = input("Descripción breve: ").strip()

    # 3. Tipo de vault
    print("\n🏢 Paso 3: Tipo de vault")
    print("  [1] Trabajo (Profesional: Daily Hub, Backlog, Reuniones, Sprints)")
    print("  [2] Personal (Hábitos, Reflexiones, Proyectos personales)")
    print("  [3] Proyecto / Mínimo (Entregables, ADRs, Documentación técnica)")
    vtype_choice = input("Selecciona tipo (1 por defecto): ").strip()
    if vtype_choice == "2":
        vault_type = "personal"
    elif vtype_choice == "3":
        vault_type = "project"
    else:
        vault_type = "work"

    # 4. Activar bitácoras
    print("\n📅 Paso 4: Configuración de bitácoras")
    if vault_type == "project":
        default_bitacoras = "n"
        print("¿Activar generación de bitácoras semanales? (No recomendado para proyectos)")
    else:
        default_bitacoras = "s"
        print("¿Activar generación de bitácoras semanales?")
        print("  Sí: Para notas organizadas por semanas")
        print("  No: Solo gestión de documentos por categorías")

    while True:
        prompt_b = "Activar bitácoras (S/n): " if default_bitacoras == "s" else "Activar bitácoras (s/N): "
        bitacoras = input(prompt_b).strip().lower()
        if not bitacoras:
            bitacoras_enabled = (default_bitacoras == "s")
            break
        if bitacoras in ['s', 'y', 'n']:
            bitacoras_enabled = (bitacoras in ['s', 'y'])
            break
        print("❌ Responde S (sí) o N (no)")

    # 5. Confirmación
    print("\n" + "-" * 60)
    print("📋 RESUMEN DE CONFIGURACIÓN:")
    print(f"  Nombre: {vault_name}")
    print(f"  Tipo: {vault_type.capitalize()}")
    print(f"  Ubicación: {vault_path}")
    if description:
        print(f"  Descripción: {description}")
    print(f"  Bitácoras: {'✅ Activadas' if bitacoras_enabled else '❌ Desactivadas'}")
    print("-" * 60)

    confirm = input("\n¿Crear vault con esta configuración? (S/n): ").strip().lower()
    if confirm == 'n':
        print("❌ Creación cancelada")
        return None

    # 6. Crear estructura
    try:
        print(f"\n🔨 Creando vault '{vault_name}'...")

        # Crear directorios
        os.makedirs(vault_path, exist_ok=True)
        data_dir = os.path.join(vault_path, "data")
        os.makedirs(data_dir, exist_ok=True)

        # Crear config.yaml
        config_content = _generate_config_yaml(description, bitacoras_enabled, vault_type=vault_type, vault_name=vault_name)
        config_path = os.path.join(data_dir, "config.yaml")
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        print(f"  ✅ Creado: data/config.yaml")

        # Crear menu_config.yaml según plantilla de tipo de vault
        menu_content = _generate_menu_config_yaml(vault_type)
        menu_path = os.path.join(data_dir, "menu_config.yaml")
        with open(menu_path, 'w', encoding='utf-8') as f:
            f.write(menu_content)
        print(f"  ✅ Creado: data/menu_config.yaml (plantilla {vault_type})")

        # Crear categories.yaml
        categories_content = _generate_categories_yaml()
        categories_path = os.path.join(data_dir, "categories.yaml")
        with open(categories_path, 'w', encoding='utf-8') as f:
            f.write(categories_content)
        print(f"  ✅ Creado: data/categories.yaml")

        # Crear run_brackets.py
        runner_content = _generate_runner_script()
        runner_path = os.path.join(vault_path, "run_brackets.py")
        with open(runner_path, 'w', encoding='utf-8') as f:
            f.write(runner_content)
        print(f"  ✅ Creado: run_brackets.py")

        # Crear README.md
        readme_content = _generate_readme(vault_name, description, bitacoras_enabled)
        readme_path = os.path.join(vault_path, "README.md")
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        print(f"  ✅ Creado: README.md")

        # Crear .gitignore
        gitignore_content = _generate_gitignore()
        gitignore_path = os.path.join(vault_path, ".gitignore")
        with open(gitignore_path, 'w', encoding='utf-8') as f:
            f.write(gitignore_content)
        print(f"  ✅ Creado: .gitignore")

        # Crear script de bootstrap para publicar en GitHub
        bootstrap_content = _generate_github_bootstrap_script(vault_name)
        bootstrap_path = os.path.join(vault_path, "publish_vault.ps1")
        with open(bootstrap_path, 'w', encoding='utf-8') as f:
            f.write(bootstrap_content)
        print(f"  ✅ Creado: publish_vault.ps1")

        print(f"\n🎉 ¡Vault '{vault_name}' creado exitosamente!")
        print(f"\n📂 Ubicación: {vault_path}")

        # Añadir al workspace de VS Code
        workspace_file = os.path.join(workspace_root, "Brackets.code-workspace")
        if os.path.exists(workspace_file):
            if _add_to_workspace(workspace_file, vault_name, vault_name):
                print(f"✅ Añadido al workspace de VS Code")
            else:
                print(f"⚠️  No se pudo añadir al workspace automáticamente")

        # Añadir al .gitignore del repo de configuración raíz
        root_gitignore = os.path.join(workspace_root, ".gitignore")
        if _add_vault_to_root_gitignore(root_gitignore, vault_name):
            print(f"✅ Añadido a .gitignore raíz: /{vault_name}/")
        else:
            print(f"⚠️  No se pudo actualizar .gitignore raíz")

        print("\n💡 Próximos pasos:")
        print(f"   1. cd {vault_path}")
        print(f"   2. python run_brackets.py")
        print(f"   3. (Opcional) .\\publish_vault.ps1 -RemoteUrl <url-del-repo>")

        input("\nPresiona Enter para continuar...")
        return vault_path

    except Exception as e:
        print(f"\n❌ Error al crear vault: {e}")
        input("\nPresiona Enter para continuar...")
        return None


def _generate_config_yaml(
    description: str,
    bitacoras_enabled: bool,
    vault_type: str = "work",
    vault_name: str = ""
) -> str:
    """Genera el contenido de config.yaml."""
    desc_line = f'description: "{description}"\n' if description else ''
    name_line = f'vault_name: "{vault_name}"\n' if vault_name else ''
    type_line = f'vault_type: "{vault_type}"\n'

    return f"""# Configuración del vault
version: "1.0.0"
system: "Brackets"
{name_line}{type_line}{desc_line}
# Feature flags del sistema
feature_flags:
  bitacoras_enabled: {str(bitacoras_enabled).lower()}

# Rutas del vault
paths:
  notes_root: "."
  data_dir: "data"

# Configuración de sincronización de categorías
sync_yaml:
  include_extensions:
    - ".md"
  excluded_prefixes:
    - "[2025]"
    - "[2026]"
  output_file: "categories_SYNCED.yaml"
"""


def _generate_menu_config_yaml(vault_type: str = "work") -> str:
    """Obtiene el contenido de menu_config.yaml según la plantilla del tipo de vault."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidate_dirs = [
        os.path.normpath(os.path.join(current_dir, "..", "..", "data", "templates")),
        os.path.normpath(os.path.join(current_dir, "..", "data", "templates")),
    ]
    for d in candidate_dirs:
        template_path = os.path.join(d, f"menu_config.{vault_type}.yaml")
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()

    # Fallback al menu_config global
    fallback_dirs = [
        os.path.normpath(os.path.join(current_dir, "..", "..", "data")),
        os.path.normpath(os.path.join(current_dir, "..", "data")),
    ]
    for d in fallback_dirs:
        fallback_path = os.path.join(d, "menu_config.yaml")
        if os.path.exists(fallback_path):
            with open(fallback_path, "r", encoding="utf-8") as f:
                return f.read()

    return "menus: {}\n"


def _generate_categories_yaml() -> str:
    """Genera el contenido de categories.yaml."""
    return """# Categorías de documentos
version: "1.0.0"
categories: []
"""


def _generate_runner_script() -> str:
    """Genera el contenido de run_brackets.py."""
    return """#!/usr/bin/env python3
\"\"\"Script principal de lanzamiento para el Sistema Brackets.
Este archivo actúa como punto de entrada desde el vault.
Usa el core de Brackets de forma dinámica y desacoplada.
\"\"\"

import sys
import os

def find_core_path() -> str:
    if \"BRACKETS_CORE_PATH\" in os.environ and os.path.exists(os.environ[\"BRACKETS_CORE_PATH\"]):
        return os.path.abspath(os.environ[\"BRACKETS_CORE_PATH\"])

    cur = os.path.abspath(os.path.dirname(__file__))
    while cur and os.path.dirname(cur) != cur:
        for cand in [
            os.path.join(cur, \"brackets\"),
            os.path.join(os.path.dirname(cur), \"brackets\")
        ]:
            if os.path.exists(os.path.join(cand, \"brackets\", \"main.py\")):
                return os.path.abspath(cand)
        cur = os.path.dirname(cur)

    return os.path.abspath(os.path.join(os.path.dirname(__file__), \"..\", \"brackets\"))

CORE_PATH = find_core_path()

if CORE_PATH not in sys.path:
    sys.path.insert(0, CORE_PATH)

if not os.path.exists(os.path.join(CORE_PATH, \"brackets\", \"main.py\")):
    print(f\"❌ Error: No se encuentra el core de Brackets en: {CORE_PATH}\")
    print(\"   Define la variable de entorno BRACKETS_CORE_PATH si tu vault está fuera del workspace.\")
    sys.exit(1)

from brackets.main import main

if __name__ == \"__main__\":
    if \"--directory\" not in sys.argv and \"-d\" not in sys.argv:
        vault_dir = os.path.dirname(os.path.abspath(__file__))
        sys.argv.extend([\"--directory\", vault_dir])
    main()
"""


def _generate_readme(vault_name: str, description: str, bitacoras_enabled: bool) -> str:
    """Genera el contenido de README.md."""
    desc_section = f"\n{description}\n" if description else ""
    bitacoras_status = "✅ Activadas" if bitacoras_enabled else "❌ Desactivadas"

    return f"""# {vault_name}
{desc_section}
## 🔗 Integración con Brackets

Este vault es un depósito puro de datos (Markdown + YAML) gestionado desde fuera por el motor **Brackets** (cero código Python en el vault).

- **Bitácoras semanales**: {bitacoras_status}

## 🚀 Uso (desde la raíz del workspace)

```powershell
python run_brackets.py --vault {vault_name}
python run_brackets.py --web
```

## ⚙️ Configuración

La configuración específica de este vault está en:
- `data/config.yaml` - Configuración general, `vault_type` y feature flags
- `data/task_types.yaml` - Tipos de tareas y premojis declarativos
- `data/categories.yaml` - Estructura de categorías de documentos
"""


def _generate_gitignore() -> str:
    """Genera el contenido de .gitignore."""
    return """# Python
__pycache__/
*.py[cod]
*$py.class
*.so

# Virtual environments
venv/
ENV/
env/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Brackets related
brackets/
categories_SYNCED.yaml
"""


def _generate_github_bootstrap_script(vault_name: str) -> str:
    """Genera script para inicializar/publicar el vault en un repo GitHub independiente."""
    return f"""param(
    [Parameter(Mandatory=$true)]
    [string]$RemoteUrl,

    [string]$MainBranch = "main"
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Publicando vault '{vault_name}' en repo independiente..."

if (-not (Test-Path ".git")) {{
    git init
}}

git add .

try {{
    git commit -m "Initial commit - {vault_name} vault"
}} catch {{
    Write-Host "ℹ️ No hay cambios para commit inicial"
}}

git branch -M $MainBranch

$hasOrigin = git remote | Select-String -Pattern "^origin$" -Quiet
if (-not $hasOrigin) {{
    git remote add origin $RemoteUrl
}} else {{
    git remote set-url origin $RemoteUrl
}}

git push -u origin $MainBranch

Write-Host "✅ Vault publicado correctamente en: $RemoteUrl"
"""


def _add_vault_to_root_gitignore(gitignore_path: str, vault_name: str) -> bool:
    """Añade el vault al .gitignore del repo de configuración raíz."""
    try:
        entry = f"/{vault_name}/"

        # Si no existe .gitignore raíz, crearlo con cabecera mínima
        if not os.path.exists(gitignore_path):
            with open(gitignore_path, 'w', encoding='utf-8') as f:
                f.write("# Root workspace ignores\n")

        with open(gitignore_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Ya existe: no hacer nada
        if entry in content:
            return True

        # Añadir al final en nueva línea
        append_prefix = "" if content.endswith("\n") else "\n"
        with open(gitignore_path, 'a', encoding='utf-8') as f:
            f.write(f"{append_prefix}{entry}\n")

        return True
    except Exception as e:
        print(f"Error al actualizar .gitignore raíz: {e}")
        return False


def _add_to_workspace(workspace_file: str, vault_name: str, folder_path: str) -> bool:
    """Añade el vault al archivo .code-workspace.

    Args:
        workspace_file: Ruta al archivo .code-workspace
        vault_name: Nombre del vault
        folder_path: Path relativo del vault desde workspace root

    Returns:
        True si se añadió correctamente, False en caso contrario
    """
    try:
        # Leer workspace actual
        with open(workspace_file, 'r', encoding='utf-8') as f:
            workspace_config = json.load(f)

        # Verificar que no existe ya
        folders = workspace_config.get('folders', [])
        for folder in folders:
            if folder.get('path') == folder_path:
                return True  # Ya existe, no es error

        # Añadir nuevo vault
        emoji_map = {
            'PersonalNotes': '📓',
            'PersonalVault': '📓',
            'ProjectNotes': '📋',
            'WorkNotes': '💼',
        }
        emoji = emoji_map.get(vault_name, '📁')

        new_folder = {
            'name': f"{emoji} {vault_name}",
            'path': folder_path
        }

        # Insertar antes de SharedContext (si existe) o al final
        shared_idx = None
        for idx, folder in enumerate(folders):
            if 'SharedContext' in folder.get('path', ''):
                shared_idx = idx
                break

        if shared_idx is not None:
            folders.insert(shared_idx, new_folder)
        else:
            folders.append(new_folder)

        # Guardar
        with open(workspace_file, 'w', encoding='utf-8') as f:
            json.dump(workspace_config, f, indent='\t', ensure_ascii=False)

        return True

    except Exception as e:
        print(f"Error al actualizar workspace: {e}")
        return False
