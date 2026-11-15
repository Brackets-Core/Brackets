"""
Modelos de datos para trabajar con categorías y documentos como objetos Python.
Permite cargar, modificar en memoria y serializar a YAML.
"""

from typing import List, Optional, Dict, Any
import re


class Document:
    """Representa un documento individual."""
    
    def __init__(self, filename: str):
        self.filename = filename
    
    def to_dict(self) -> str:
        """Retorna solo el nombre del archivo."""
        return self.filename
    
    def __repr__(self):
        return f"Document({self.filename})"


class Category:
    """Representa una categoría con subcategorías y documentos."""
    
    def __init__(self, id: str, name: str, description: str = ""):
        self.id = id
        self.name = name
        self.description = description
        self.documents: List[Document] = []
        self.subcategories: List['Category'] = []
    
    def add_document(self, filename: str) -> Document:
        """Añade un documento a esta categoría."""
        doc = Document(filename)
        self.documents.append(doc)
        return doc
    
    def add_subcategory(self, id: str, name: str, description: str = "") -> 'Category':
        """Añade una subcategoría."""
        subcat = Category(id, name, description)
        self.subcategories.append(subcat)
        return subcat
    
    def get_subcategory(self, id: str) -> Optional['Category']:
        """Busca una subcategoría por ID."""
        for subcat in self.subcategories:
            if subcat.id == id:
                return subcat
        return None
    
    def find_document(self, filename: str) -> Optional[Document]:
        """Busca un documento (recursivo)."""
        for doc in self.documents:
            if doc.filename == filename:
                return doc
        for subcat in self.subcategories:
            doc = subcat.find_document(filename)
            if doc:
                return doc
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la categoría a diccionario para YAML."""
        result = {
            'id': self.id,
            'name': self.name,
            'description': self.description if self.description else '',
        }
        
        # Documentos
        if self.documents:
            result['documents'] = [doc.filename for doc in self.documents]
        else:
            result['documents'] = []
        
        # Subcategorías
        if self.subcategories:
            result['subcategories'] = [subcat.to_dict() for subcat in self.subcategories]
        else:
            result['subcategories'] = []
        
        return result
    
    def __repr__(self):
        return f"Category({self.id}, name={self.name}, docs={len(self.documents)}, subcats={len(self.subcategories)})"


class CategoriesYAML:
    """Maneja toda la estructura de categorías."""
    
    def __init__(self, version: str = "1.0.0"):
        self.version = version
        self.categories: List[Category] = []
    
    def add_category(self, id: str, name: str, description: str = "") -> Category:
        """Añade una categoría raíz."""
        cat = Category(id, name, description)
        self.categories.append(cat)
        return cat
    
    def get_category(self, id: str) -> Optional[Category]:
        """Busca una categoría por ID."""
        for cat in self.categories:
            if cat.id == id:
                return cat
        return None
    
    def find_category_by_name(self, name: str) -> Optional[Category]:
        """Busca una categoría por nombre (sin emojis)."""
        for cat in self.categories:
            clean_name = self._clean_name(cat.name)
            if clean_name == name:
                return cat
        return None
    
    def find_document(self, filename: str) -> Optional[Document]:
        """Busca un documento en cualquier categoría."""
        for cat in self.categories:
            doc = cat.find_document(filename)
            if doc:
                return doc
        return None
    
    @staticmethod
    def _clean_name(name: str) -> str:
        """Limpia emojis del nombre para comparaciones."""
        # Patrón para emojis y caracteres especiales
        emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]'
        return re.sub(emoji_pattern, '', name).strip()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para YAML."""
        return {
            'version': self.version,
            'categories': [cat.to_dict() for cat in self.categories]
        }
    
    def __repr__(self):
        return f"CategoriesYAML(v{self.version}, {len(self.categories)} categories)"


def custom_representer(dumper, data):
    """Representer personalizado para dumper de YAML."""
    if isinstance(data, str):
        # Para strings, usa el representer por defecto
        return dumper.represent_str(data)
    return dumper.represent_data(data)


def custom_dict_representer(dumper, data):
    """Representer para diccionarios con indentación correcta."""
    return dumper.represent_dict(data.items())


def setup_yaml_representer():
    """Configura el dumper de YAML para indentación adecuada."""
    import yaml
    
    # Configurar representer para diccionarios
    yaml.add_representer(
        dict,
        lambda dumper, data: dumper.represent_dict(data.items())
    )
    
    return yaml


def to_yaml_string(categories_obj: CategoriesYAML, indent: int = 2, include_metadata: bool = False) -> str:
    """Convierte CategoriesYAML a string YAML con indentación correcta."""
    import yaml
    
    data = categories_obj.to_dict()
    
    # Agregar metadata si se solicita
    if include_metadata:
        def count_items(cats):
            total_cats = len(cats)
            total_docs = sum(len(cat.documents) for cat in cats)
            for cat in cats:
                if cat.subcategories:
                    c, d = count_items(cat.subcategories)
                    total_cats += c
                    total_docs += d
            return total_cats, total_docs
        
        total_cats, total_docs = count_items(categories_obj.categories)
        from datetime import datetime
        
        data['metadata'] = {
            'total_categories': total_cats,
            'total_documents': total_docs,
            'last_updated': datetime.now().strftime('%Y-%m-%d'),
            'note': 'Auto-generado desde sincronización de repositorio'
        }
    
    # Dumper con indentación correcta para arrays
    class CustomDumper(yaml.SafeDumper):
        def increase_indent(self, flow=False, indentless=False):
            return super(CustomDumper, self).increase_indent(flow, False)
    
    def represent_none(self, data):
        return self.represent_scalar('tag:yaml.org,2002:null', '')
    
    CustomDumper.add_representer(type(None), represent_none)
    
    # Generar YAML con indentación de 2 espacios
    yaml_str = yaml.dump(
        data,
        Dumper=CustomDumper,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        indent=indent,
        width=float('inf'),
        explicit_start=False,
        explicit_end=False
    )
    
    # Post-proceso: asegurar que los arrays queden indentados dos espacios más
    fixed_lines = []
    prev_indent = None
    prev_ended_colon = False
    for line in yaml_str.split('\n'):
        stripped = line.lstrip(' ')
        current_indent = len(line) - len(stripped)
        if prev_ended_colon and stripped.startswith('- '):
            # Si el guion está al mismo nivel que la clave, añadimos 2 espacios
            if current_indent == prev_indent:
                line = '  ' + line
                current_indent += 2
        fixed_lines.append(line)
        prev_ended_colon = line.rstrip().endswith(':')
        prev_indent = current_indent
    
    return '\n'.join(fixed_lines)


def from_yaml_file(yaml_path: str) -> CategoriesYAML:
    """Carga un archivo YAML y lo convierte a objetos CategoriesYAML."""
    import yaml
    
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    # Crear objeto CategoriesYAML
    categories_yaml = CategoriesYAML(version=data.get('version', '1.0.0'))
    
    # Cargar categorías
    for cat_data in data.get('categories', []):
        category = categories_yaml.add_category(
            id=cat_data.get('id', ''),
            name=cat_data.get('name', ''),
            description=cat_data.get('description', '')
        )
        
        # Cargar documentos
        for doc in cat_data.get('documents', []):
            category.add_document(doc)
        
        # Cargar subcategorías recursivamente
        _load_subcategories(category, cat_data.get('subcategories', []))
    
    return categories_yaml


def _load_subcategories(parent_category: Category, subcats_list: list):
    """Carga subcategorías recursivamente."""
    for subcat_data in subcats_list:
        subcat = parent_category.add_subcategory(
            id=subcat_data.get('id', ''),
            name=subcat_data.get('name', ''),
            description=subcat_data.get('description', '')
        )
        
        # Cargar documentos de subcategoría
        for doc in subcat_data.get('documents', []):
            subcat.add_document(doc)
        
        # Cargar sub-subcategorías
        if subcat_data.get('subcategories'):
            _load_subcategories(subcat, subcat_data['subcategories'])


def merge_categories(existing: CategoriesYAML, new_structure: CategoriesYAML) -> CategoriesYAML:
    """
    Merge de categorías: conserva IDs, descripciones y actualiza estructura del repo.
    
    Estrategia:
    1. Para cada categoría nueva del repo, buscar su equivalente en YAML por nombre
    2. Si existe: preservar ID original, descripción y nombre del YAML
    3. Si no existe: usar el nuevo ID y nombre del repo, sin descripción
    4. Actualizar documentos con los del repo (fuente de verdad)
    5. Permite reorganización de la jerarquía (categorías pueden cambiar de nivel)
    
    Args:
        existing: Categorías actuales del YAML (con descripciones e IDs definidos)
        new_structure: Categorías nuevas del repositorio
    
    Returns:
        CategoriesYAML con IDs y descripciones preservadas, estructura del repo
    """
    result = CategoriesYAML(version=existing.version)
    
    # Obtener lista de TODAS las categorías existentes (para búsqueda recursiva)
    def get_all_categories(cats: list) -> list:
        all_cats = cats.copy()
        for cat in cats:
            if cat.subcategories:
                all_cats.extend(get_all_categories(cat.subcategories))
        return all_cats
    
    all_existing = get_all_categories(existing.categories)
    
    # Por cada categoría nueva del repo
    for new_cat in new_structure.categories:
        # Buscar coincidencia en el YAML existente por nombre
        existing_cat = _find_category_by_name(existing.categories, new_cat.name)
        
        if existing_cat:
            # Preservar ID y descripción del YAML existente
            merged_cat = result.add_category(
                id=existing_cat.id,
                name=existing_cat.name,
                description=existing_cat.description
            )
        else:
            # Nueva categoría: usar del repo
            merged_cat = result.add_category(
                id=new_cat.id,
                name=new_cat.name,
                description=''
            )
        
        # Actualizar documentos (usar los del repo = fuente de verdad)
        for doc in new_cat.documents:
            merged_cat.add_document(doc.filename)
        
        # Merge de subcategorías recursivamente (con acceso a todas las categorías)
        if new_cat.subcategories:
            _merge_subcategories(
                merged_cat, 
                new_cat.subcategories,
                existing_cat.subcategories if existing_cat else [],
                all_existing
            )
    
    return result


def _find_category_by_name(categories: list, target_name: str) -> Optional[Category]:
    """
    Busca una categoría por nombre exacto (búsqueda recursiva en toda la estructura).
    Esto permite encontrar categorías aunque se hayan reorganizado en la jerarquía.
    """
    for cat in categories:
        if cat.name == target_name:
            return cat
        # Búsqueda recursiva en subcategorías
        if cat.subcategories:
            result = _find_category_by_name(cat.subcategories, target_name)
            if result:
                return result
    return None


def _merge_subcategories(parent: Category, new_subcats: list, existing_subcats: list,
                         all_existing_categories: Optional[list] = None):
    """
    Merge recursivo de subcategorías preservando IDs y descripciones.
    Busca en toda la estructura si no encuentra en el nivel actual.
    """
    for new_subcat in new_subcats:
        # 1. Buscar por nombre en las subcategorías existentes del mismo nivel
        existing_subcat = _find_category_by_name(existing_subcats, new_subcat.name)
        
        # 2. Si no encuentra, buscar en TODA la estructura (reorganización permitida)
        if not existing_subcat and all_existing_categories:
            existing_subcat = _find_category_by_name(all_existing_categories, new_subcat.name)
        
        if existing_subcat:
            # Preservar ID y descripción del YAML existente
            merged_subcat = parent.add_subcategory(
                id=existing_subcat.id,
                name=existing_subcat.name,
                description=existing_subcat.description
            )
        else:
            # Nueva subcategoría: usar del repo
            merged_subcat = parent.add_subcategory(
                id=new_subcat.id,
                name=new_subcat.name,
                description=''
            )
        
        # Actualizar documentos
        for doc in new_subcat.documents:
            merged_subcat.add_document(doc.filename)
        
        # Recursión
        if new_subcat.subcategories:
            _merge_subcategories(
                merged_subcat,
                new_subcat.subcategories,
                existing_subcat.subcategories if existing_subcat else [],
                all_existing_categories
            )