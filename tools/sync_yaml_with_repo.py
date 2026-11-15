"""
Herramienta de sincronización YAML con repositorio.

Funciones para:
1. Cargar YAML existente (conservando descripciones)
2. Escanear repositorio para ver estructura real
3. Comparar ambos objetos
4. Reportar inconsistencias (nomenclatura, descripciones)
5. Generar nuevo YAML conservando metadatos
"""

import os
import re
import shutil
from models.yaml_models import (
    CategoriesYAML, Category, 
    from_yaml_file, to_yaml_string, 
    merge_categories
)


DEFAULT_SCAN_CONFIG = {
    "include_extensions": (".md", ".sql"),
    "excluded_prefixes": ("[2025]", "[2026]", "[🖼️ASSETS]", "[.crossnote]"),
    "output_file": "categories_SYNCED.yaml",
}


def get_sync_scan_config(base_dir: str) -> dict:
    """Obtiene la configuración de escaneo desde data/config.yaml.

    Soporta la sección opcional:
      sync_yaml:
        include_extensions: [".md", ".sql"]
        excluded_prefixes: ["[2025]", "[2026]"]
                output_file: "categories_SYNCED.yaml"

    Si no existe o es inválida, devuelve valores por defecto.
    """
    config = {
        "include_extensions": tuple(DEFAULT_SCAN_CONFIG["include_extensions"]),
        "excluded_prefixes": tuple(DEFAULT_SCAN_CONFIG["excluded_prefixes"]),
        "output_file": DEFAULT_SCAN_CONFIG["output_file"],
    }

    config_path = os.path.join(os.path.abspath(base_dir), "data", "config.yaml")
    if not os.path.exists(config_path):
        return config

    try:
        import yaml

        with open(config_path, "r", encoding="utf-8") as fh:
            payload = yaml.safe_load(fh) or {}

        sync_cfg = payload.get("sync_yaml", {}) if isinstance(payload, dict) else {}

        include_extensions = sync_cfg.get("include_extensions")
        if isinstance(include_extensions, list):
            normalized_ext = []
            for ext in include_extensions:
                if isinstance(ext, str) and ext.strip():
                    normalized_ext.append(ext.strip())
            if normalized_ext:
                config["include_extensions"] = tuple(normalized_ext)

        excluded_prefixes = sync_cfg.get("excluded_prefixes")
        if isinstance(excluded_prefixes, list):
            normalized_prefixes = []
            for prefix in excluded_prefixes:
                if isinstance(prefix, str) and prefix.strip():
                    normalized_prefixes.append(prefix.strip())
            if normalized_prefixes:
                config["excluded_prefixes"] = tuple(normalized_prefixes)

        output_file = sync_cfg.get("output_file")
        if isinstance(output_file, str) and output_file.strip():
            config["output_file"] = output_file.strip()

    except Exception:
        return config

    return config


def extract_emoji(text: str) -> str:
    """Extrae el emoji del texto."""
    emoji_pattern = r'^([\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\u2600-\u26FF\u2700-\u27BF])'
    match = re.match(emoji_pattern, text)
    if match:
        return match.group(1)
    return ""


def clean_id(text: str) -> str:
    """Convierte texto a ID limpio (lowercase, sin espacios, sin emojis)."""
    emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]'
    text = re.sub(emoji_pattern, '', text).strip()
    text = text.lower().replace(' ', '_').replace('&', 'and').replace('/', '_')
    
    if not text:
        text = 'emoji_unnamed'
    return text


def has_only_emojis(text: str) -> bool:
    """Verifica si el texto solo contiene emojis."""
    emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\u2600-\u26FF\u2700-\u27BF\s]'
    clean_text = re.sub(emoji_pattern, '', text).strip()
    return len(clean_text) == 0 and len(text) > 0


def parse_file_structure(
    base_dir: str,
    include_extensions: tuple = ('.md', '.sql'),
    excluded_prefixes: tuple = ('[2025]', '[2026]', '[🖼️ASSETS]', '[.crossnote]')
) -> dict:
    """Parsea la estructura real del repositorio.

    Args:
        base_dir: Directorio raíz del vault a escanear.
        include_extensions: Extensiones de archivo válidas para parsear.
        excluded_prefixes: Prefijos de nombre de archivo a excluir.
    """
    structure = {}
    base_dir = os.path.abspath(base_dir)
    
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        
        if os.path.isfile(item_path):
            if item.startswith('[') and item.endswith(include_extensions):
                if not any(item.startswith(x) for x in excluded_prefixes):
                    parse_file_path(item, structure)
    
    return structure


def parse_file_path(filename: str, structure: dict):
    """Parsea un nombre de archivo como [CAT][SUBCAT]filename.md"""
    bracket_pattern = r'\[([^\]]+)\]'
    brackets = re.findall(bracket_pattern, filename)
    
    if len(brackets) < 1:
        return
    
    last_bracket_end = filename.rfind(']')
    if last_bracket_end == -1:
        return
    
    doc_name = filename[last_bracket_end + 1:]
    if not doc_name:
        return
    
    main_category = brackets[0]
    
    if main_category not in structure:
        structure[main_category] = {
            'docs': [],
            'subcats': {}
        }
    
    if len(brackets) == 1:
        structure[main_category]['docs'].append(doc_name)
    else:
        current = structure[main_category]['subcats']
        
        for i in range(1, len(brackets) - 1):
            subcat = brackets[i]
            if subcat not in current:
                current[subcat] = {
                    'docs': [],
                    'subcats': {}
                }
            current = current[subcat]['subcats']
        
        last_category = brackets[-1]
        if last_category not in current:
            current[last_category] = {
                'docs': [],
                'subcats': {}
            }
        current[last_category]['docs'].append(doc_name)


def build_categories_from_repo(structure: dict) -> CategoriesYAML:
    """Construye objeto CategoriesYAML desde estructura del repo."""
    categories_yaml = CategoriesYAML(version="1.0.0")
    
    for cat_name in sorted(structure.keys()):
        cat_data = structure[cat_name]
        cat_id = clean_id(cat_name)
        
        category = categories_yaml.add_category(
            id=cat_id,
            name=cat_name,
            description=""
        )
        
        for doc in sorted(cat_data['docs']):
            category.add_document(doc)
        
        if cat_data['subcats']:
            build_subcategories(category, cat_data['subcats'])
    
    return categories_yaml


def build_subcategories(parent_category: Category, subcats_dict: dict):
    """Construye recursivamente las subcategorías."""
    for subcat_name in sorted(subcats_dict.keys()):
        subcat_data = subcats_dict[subcat_name]
        subcat_id = clean_id(subcat_name)
        
        subcat = parent_category.add_subcategory(
            id=subcat_id,
            name=subcat_name,
            description=""
        )
        
        for doc in sorted(subcat_data['docs']):
            subcat.add_document(doc)
        
        if subcat_data['subcats']:
            build_subcategories(subcat, subcat_data['subcats'])


def handle_nomenclature_issues(nomenclature_issues: list) -> dict:
    """
    Maneja problemas de nomenclatura encontrados.
    Genera nombres automáticos: "sub-{ParentName}-{Number}"
    Pregunta al usuario si desea usarlos o salir.
    
    Returns:
        Diccionario con mapeo de names-originales a nombres-nuevos
    """
    if not nomenclature_issues:
        return {}
    
    print("\n" + "=" * 80)
    print("⚠️  PROBLEMA DE NOMENCLATURA DETECTADO")
    print("=" * 80 + "\n")
    
    print("Se encontraron categorías/subcategorías que son SOLO EMOJIS:")
    print("(No se puede generar un ID válido sin texto descriptivo)\n")
    
    empty_descriptions = [issue for issue in nomenclature_issues if not issue.get('description', '').strip()]
    
    # MOSTRAR AVISO DESTACADO DE DESCRIPCIONES VACÍAS
    if empty_descriptions:
        print("\n╔" + "=" * 76 + "╗")
        print("║ " + ("⚠️  ADVERTENCIA: DESCRIPCIONES VACÍAS").ljust(75) + " ║")
        print("║ " + (f"{len(empty_descriptions)}/{len(nomenclature_issues)} elementos perderan metadatos al renombrar").ljust(75) + " ║")
        print("╚" + "=" * 76 + "╝\n")
    
    for i, issue in enumerate(nomenclature_issues, 1):
        if issue['level'] == 'category':
            print(f"{i}. Categoria: '{issue['name']}'")
        else:
            print(f"{i}. Subcategoria: '{issue['name']}' en {issue['parent']}")
        
        desc = issue.get('description', '').strip()
        if desc:
            print(f"   Descripcion: '{desc}'")
        else:
            print(f"   Descripcion: ❌ VACIA")
        print()
    
    print("=" * 80)
    print("\n¿Cómo deseas proceder?\n")
    print("1. Generar nombres automáticos: 'sub-{ParentName}-{Number}'")
    print("2. Salir - Debo cambiar los nombres manualmente en los archivos\n")
    
    while True:
        choice = input("Selecciona opción (1 o 2): ").strip()
        if choice in ['1', '2']:
            break
        print("Opción inválida. Por favor, ingresa 1 o 2.\n")
    
    if choice == '2':
        print("\n❌ Operación cancelada.")
        print("\nPara continuar, debes cambiar los nombres de las categorías:")
        for issue in nomenclature_issues:
            if issue['level'] == 'category':
                print(f"  • '{issue['name']}' → asigna un nombre descriptivo (ej: 'AI', 'Intelligence')")
            else:
                print(f"  • '{issue['name']}' en {issue['parent']} → asigna un nombre descriptivo")
        print("\nLuego vuelve a ejecutar este programa.\n")
        return None  # Signal to exit
    
    # Opción 1: Generar nombres automáticos basados en el padre
    print("\n✨ Generando nombres automáticos...\n")
    
    # Agrupar issues por padre
    parent_groups = {}
    for issue in nomenclature_issues:
        parent = issue.get('parent', issue.get('name', 'root'))
        # Extraer el último elemento de la ruta (después del último '>') 
        if '>' in parent:
            parent = parent.split('>')[-1].strip()
        # Extraer nombre del padre sin emojis
        parent_name_clean = clean_id(parent).replace('_', ' ').title()
        
        if parent_name_clean not in parent_groups:
            parent_groups[parent_name_clean] = []
        parent_groups[parent_name_clean].append(issue)
    
    name_mapping = {}
    for parent_name, issues_list in parent_groups.items():
        for idx, issue in enumerate(issues_list, 1):
            original_name = issue['name']
            
            # Generar nombre: "sub-{ParentName}-{Number}"
            if len(issues_list) > 1:
                generic_name = f"sub-{parent_name}-{idx}"
            else:
                generic_name = f"sub-{parent_name}"
            
            name_mapping[original_name] = generic_name
            
            if issue['level'] == 'category':
                print(f"  • Categoría '{original_name}' → '{generic_name}'")
            else:
                print(f"  • Subcategoría '{original_name}' en {issue['parent']} → '{generic_name}'")
    
    print("\n✅ Nombres asignados. Continuando con sincronización...\n")
    return name_mapping


def apply_name_mappings(categories_obj: CategoriesYAML, name_mapping: dict):
    """Aplica los mapeos de nombres a las categorías."""
    def update_names(categories: list):
        for cat in categories:
            if cat.name in name_mapping:
                cat.name = name_mapping[cat.name]
            if cat.subcategories:
                update_names(cat.subcategories)
    
    update_names(categories_obj.categories)


def check_nomenclature_issues(categories_yaml: CategoriesYAML) -> list:
    """Detecta categorías con nomenclatura problemática (solo emojis)."""
    issues = []
    
    for cat in categories_yaml.categories:
        if has_only_emojis(cat.name):
            issues.append({
                'type': 'emoji_only_category',
                'id': cat.id,
                'name': cat.name,
                'level': 'category',
                'description': cat.description or ""
            })
        
        # Revisar subcategorías
        issues.extend(_check_subcat_nomenclature(cat.subcategories, cat.name))
    
    return issues


def _check_subcat_nomenclature(subcats: list, parent_path: str) -> list:
    """Revisa nomenclatura de subcategorías recursivamente."""
    issues = []
    
    for subcat in subcats:
        if has_only_emojis(subcat.name):
            issues.append({
                'type': 'emoji_only_subcategory',
                'id': subcat.id,
                'name': subcat.name,
                'parent': parent_path,
                'level': 'subcategory',
                'description': subcat.description or ""
            })
        
        if subcat.subcategories:
            issues.extend(_check_subcat_nomenclature(
                subcat.subcategories, 
                f"{parent_path} > {subcat.name}"
            ))
    
    return issues


def add_descriptions_to_yaml(categories_yaml: CategoriesYAML, empty_items: list) -> None:
    """Permite al usuario añadir descripciones a categorías vacías."""
    print("\n¿Deseas añadir descripciones a estos elementos? (s/n): ", end="")
    
    while True:
        choice = input().strip().lower()
        if choice in ['s', 'n', 'si', 'no']:
            break
        print("Por favor, ingresa 's' o 'n': ", end="")
    
    if choice in ['n', 'no']:
        return
    
    print("\n" + "=" * 80)
    print("Ingresa descripciones (presiona Enter para omitir):\n")
    
    for i, item in enumerate(empty_items, 1):
        print(f"{i}. {item['path']}")
        try:
            print(f"   > ", end="")
            desc = input().strip()
            
            if desc:
                if _find_and_update_category(categories_yaml, item['path'], desc):
                    print(f"   ✅ Guardado")
                else:
                    print(f"   ⚠️  No encontrado (ruta: {item['path']})")
            else:
                print(f"   ⏭️  Omitido")
        except EOFError:
            print("(entrada agotada)")
            break
        except KeyboardInterrupt:
            print("\n(cancelado)")
            break
    
    print("\n" + "=" * 80)


def _find_and_update_category(categories_obj: CategoriesYAML, target_path: str, description: str) -> bool:
    """Busca recursivamente una categoría por su ruta completa y actualiza su descripción."""
    parts = target_path.split(' > ')
    
    def search_recursive(cats, path_parts, current_depth=0):
        if current_depth >= len(path_parts):
            return False
        
        target_name = path_parts[current_depth]
        
        for cat in cats:
            if cat.name == target_name:
                if current_depth == len(path_parts) - 1:
                    # Hemos llegado al final de la ruta
                    cat.description = description
                    return True
                elif cat.subcategories:
                    # Continuar buscando en subcategorías
                    if search_recursive(cat.subcategories, path_parts, current_depth + 1):
                        return True
        
        return False
    
    return search_recursive(categories_obj.categories, parts, 0)


def get_empty_descriptions(categories_yaml: CategoriesYAML) -> list:
    """Detecta todas las categorías/subcategorías con descripción vacía."""
    empty = []
    
    def check_recursive(cats, parent_path=""):
        for cat in cats:
            if not cat.description or not cat.description.strip():
                path = f"{parent_path} > {cat.name}" if parent_path else cat.name
                empty.append({'name': cat.name, 'path': path})
            
            if cat.subcategories:
                new_path = f"{parent_path} > {cat.name}" if parent_path else cat.name
                check_recursive(cat.subcategories, new_path)
    
    check_recursive(categories_yaml.categories)
    return empty


def compare_structures(existing: CategoriesYAML, repo: CategoriesYAML):
    """Compara ambas estructuras y reporta diferencias."""
    def count_all(cats):
        total_cats = len(cats)
        total_docs = sum(len(cat.documents) for cat in cats)
        for cat in cats:
            if cat.subcategories:
                c, d = count_all(cat.subcategories)
                total_cats += c
                total_docs += d
        return total_cats, total_docs
    
    existing_cats, existing_docs = count_all(existing.categories)
    repo_cats, repo_docs = count_all(repo.categories)
    
    diff_cats = repo_cats - existing_cats
    diff_docs = repo_docs - existing_docs
    
    if diff_cats == 0 and diff_docs == 0:
        print("✅ Sincronizado")
    else:
        print(f"⚠️  Diferencia: {diff_cats:+d} cats, {diff_docs:+d} docs")
