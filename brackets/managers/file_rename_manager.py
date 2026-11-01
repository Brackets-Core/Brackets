"""
Gestor de búsqueda y reemplazo global de cadenas de texto.
Permite buscar una cadena y reemplazarla en:
- Nombres de archivos (.md, .py)
- Contenido de archivos (.md, .py, .yaml)
- Actualización automática de todas las referencias
"""

import os
import re
from typing import List, Tuple, Optional, Set, Dict
from pathlib import Path


class FileRenameManager:
    """Gestor de búsqueda y reemplazo global de cadenas de texto."""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = os.path.abspath(base_dir)
        self.data_dir = os.path.join(self.base_dir, "data")
        
    def rename_file_with_references(
        self, 
        old_filename: str, 
        new_filename: str,
        dry_run: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        Renombra un archivo y actualiza todas sus referencias.
        
        Args:
            old_filename: Nombre actual del archivo (con o sin path completo)
            new_filename: Nuevo nombre del archivo (solo nombre, no path)
            dry_run: Si True, solo simula los cambios sin aplicarlos
            
        Returns:
            Tupla (éxito, lista de archivos modificados)
        """
        # Normalizar nombres de archivo
        old_basename = os.path.basename(old_filename)
        old_fullpath = self._find_file(old_filename)
        
        if not old_fullpath:
            print(f"❌ No se encontró el archivo: {old_basename}")
            return False, []
        
        # Obtener el nombre real del archivo encontrado (puede incluir brackets)
        actual_old_basename = os.path.basename(old_fullpath)
        
        # Construir nuevo path preservando prefijo bracket si existe
        old_dir = os.path.dirname(old_fullpath)
        
        # Extraer prefijo bracket del archivo original
        bracket_prefix = ""
        if actual_old_basename.startswith('['):
            # Encontrar todos los brackets al inicio: [XXX][YYY]...
            bracket_end = 0
            in_bracket = False
            bracket_count = 0
            for i, char in enumerate(actual_old_basename):
                if char == '[':
                    in_bracket = True
                    bracket_count += 1
                elif char == ']':
                    in_bracket = False
                    bracket_end = i + 1
                elif not in_bracket and bracket_count > 0:
                    # Ya no hay más brackets consecutivos
                    break
            
            if bracket_end > 0:
                bracket_prefix = actual_old_basename[:bracket_end]
        
        # Nuevo nombre con prefijo bracket si existía
        new_basename = bracket_prefix + new_filename if bracket_prefix else new_filename
        new_fullpath = os.path.join(old_dir, new_basename)
        
        # Verificar que el nuevo archivo no exista
        if os.path.exists(new_fullpath) and old_fullpath != new_fullpath:
            print(f"❌ El archivo destino ya existe: {new_basename}")
            return False, []
        
        print(f"\n{'[SIMULACIÓN] ' if dry_run else ''}🔄 RENOMBRADO DE ARCHIVO")
        print("=" * 60)
        print(f"Archivo original: {actual_old_basename}")
        print(f"Nuevo nombre:     {new_basename}")
        print("-" * 60)
        
        modified_files = []
        
        # 1. Buscar y actualizar referencias en archivos YAML
        print("\n📝 Actualizando archivos YAML...")
        yaml_updates = self._update_yaml_references(old_basename, new_filename, dry_run)
        modified_files.extend(yaml_updates)
        
        # 2. Buscar y actualizar referencias en archivos markdown
        print("\n📄 Actualizando archivos Markdown...")
        md_updates = self._update_markdown_references(old_basename, new_filename, dry_run)
        modified_files.extend(md_updates)
        
        # 3. Renombrar el archivo físico
        if not dry_run:
            try:
                os.rename(old_fullpath, new_fullpath)
                print(f"\n✅ Archivo renombrado: {actual_old_basename} → {new_basename}")
            except Exception as e:
                print(f"\n❌ Error renombrando archivo: {e}")
                return False, modified_files
        else:
            print(f"\n[SIMULACIÓN] Renombrar: {actual_old_basename} → {new_basename}")
        
        # Resumen
        print(f"\n{'[SIMULACIÓN] ' if dry_run else ''}📊 RESUMEN")
        print("=" * 60)
        print(f"Archivos modificados: {len(modified_files)}")
        if modified_files:
            for f in modified_files:
                print(f"  - {os.path.relpath(f, self.base_dir)}")
        
        return True, modified_files
    
    def _find_file(self, filename: str) -> Optional[str]:
        """Busca un archivo en el directorio base."""
        # Si ya es un path completo y existe
        if os.path.isabs(filename) and os.path.exists(filename):
            return filename
        
        # Buscar en el directorio base
        fullpath = os.path.join(self.base_dir, filename)
        if os.path.exists(fullpath):
            return fullpath
        
        # Buscar recursivamente (incluyendo archivos con prefijos bracket)
        for root, dirs, files in os.walk(self.base_dir):
            # Ignorar directorios de sistema
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.git']]
            
            # Buscar coincidencia exacta
            if filename in files:
                return os.path.join(root, filename)
            
            # Buscar por nombre base (sin brackets)
            # Ej: "OldFile.md" podría ser "[TEST]OldFile.md"
            for file in files:
                # Extraer nombre sin brackets
                if file.endswith(filename):
                    return os.path.join(root, file)
        
        return None
    
    def _update_yaml_references(
        self, 
        old_name: str, 
        new_name: str, 
        dry_run: bool
    ) -> List[str]:
        """Actualiza referencias en archivos YAML."""
        modified = []
        
        yaml_files = [
            os.path.join(self.data_dir, "categories.yaml"),
            os.path.join(self.data_dir, "config.yaml"),
        ]
        
        # Buscar todos los YAML en data/
        if os.path.exists(self.data_dir):
            for f in os.listdir(self.data_dir):
                if f.endswith('.yaml') or f.endswith('.yml'):
                    full_path = os.path.join(self.data_dir, f)
                    if full_path not in yaml_files:
                        yaml_files.append(full_path)
        
        for yaml_file in yaml_files:
            if not os.path.exists(yaml_file):
                continue
            
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Buscar el nombre del archivo en el YAML
                if old_name in content:
                    new_content = content.replace(old_name, new_name)
                    
                    if not dry_run:
                        with open(yaml_file, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                    
                    modified.append(yaml_file)
                    count = content.count(old_name)
                    print(f"  ✓ {os.path.basename(yaml_file)}: {count} referencia(s)")
            
            except Exception as e:
                print(f"  ⚠️ Error en {os.path.basename(yaml_file)}: {e}")
        
        return modified
    
    def _update_markdown_references(
        self, 
        old_name: str, 
        new_name: str, 
        dry_run: bool
    ) -> List[str]:
        """Actualiza referencias en archivos markdown."""
        modified = []
        
        # Obtener nombre sin extensión para enlaces WikiStyle
        old_name_no_ext = old_name.rsplit('.', 1)[0] if '.' in old_name else old_name
        new_name_no_ext = new_name.rsplit('.', 1)[0] if '.' in new_name else new_name
        
        # Patrones de búsqueda
        patterns = [
            # Enlaces markdown: [texto](archivo.md)
            (re.compile(r'\[([^\]]+)\]\(' + re.escape(old_name) + r'\)'), 
             r'[\1](' + new_name + r')'),
            
            # Enlaces WikiStyle: [[archivo]]
            (re.compile(r'\[\[' + re.escape(old_name_no_ext) + r'\]\]'), 
             r'[[' + new_name_no_ext + r']]'),
            
            # Enlaces WikiStyle con texto: [[archivo|texto]]
            (re.compile(r'\[\[' + re.escape(old_name_no_ext) + r'\|([^\]]+)\]\]'), 
             r'[[' + new_name_no_ext + r'|\1]]'),
            
            # Referencias directas al nombre del archivo
            (re.compile(r'\b' + re.escape(old_name) + r'\b'), 
             new_name),
        ]
        
        # Buscar archivos markdown
        md_files = self._find_all_markdown_files()
        
        for md_file in md_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                changes_made = False
                
                # Aplicar cada patrón
                for pattern, replacement in patterns:
                    if pattern.search(content):
                        content = pattern.sub(replacement, content)
                        changes_made = True
                
                if changes_made:
                    if not dry_run:
                        with open(md_file, 'w', encoding='utf-8') as f:
                            f.write(content)
                    
                    modified.append(md_file)
                    # Contar cambios
                    changes = sum(1 for p, _ in patterns if p.search(original_content))
                    rel_path = os.path.relpath(md_file, self.base_dir)
                    print(f"  ✓ {rel_path}: {changes} referencia(s)")
            
            except Exception as e:
                print(f"  ⚠️ Error en {os.path.basename(md_file)}: {e}")
        
        return modified
    
    def _find_all_markdown_files(self) -> List[str]:
        """Encuentra todos los archivos markdown en el repositorio."""
        md_files = []
        
        for root, dirs, files in os.walk(self.base_dir):
            # Ignorar directorios de sistema
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv']]
            
            for file in files:
                if file.endswith('.md'):
                    md_files.append(os.path.join(root, file))
        
        return md_files
    
    def list_renameable_files(self) -> List[str]:
        """Lista archivos que pueden ser renombrados (archivos .md en el directorio base)."""
        files = []
        
        if not os.path.exists(self.base_dir):
            return files
        
        for item in os.listdir(self.base_dir):
            full_path = os.path.join(self.base_dir, item)
            if os.path.isfile(full_path) and item.endswith('.md'):
                files.append(item)
        
        return sorted(files)
    
    def search_file_references(self, filename: str) -> List[Tuple[str, int]]:
        """
        Busca todas las referencias a un archivo en el repositorio.
        
        Returns:
            Lista de tuplas (archivo, número de referencias)
        """
        basename = os.path.basename(filename)
        name_no_ext = basename.rsplit('.', 1)[0] if '.' in basename else basename
        
        references = []
        
        # Buscar en archivos YAML
        yaml_files = []
        if os.path.exists(self.data_dir):
            yaml_files = [
                os.path.join(self.data_dir, f) 
                for f in os.listdir(self.data_dir) 
                if f.endswith(('.yaml', '.yml'))
            ]
        
        for yaml_file in yaml_files:
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                count = content.count(basename)
                if count > 0:
                    references.append((yaml_file, count))
            except (OSError, UnicodeDecodeError):
                pass
        
        # Buscar en archivos markdown
        patterns = [
            re.compile(r'\[([^\]]+)\]\(' + re.escape(basename) + r'\)'),
            re.compile(r'\[\[' + re.escape(name_no_ext) + r'\]\]'),
            re.compile(r'\[\[' + re.escape(name_no_ext) + r'\|([^\]]+)\]\]'),
            re.compile(r'\b' + re.escape(basename) + r'\b'),
        ]
        
        md_files = self._find_all_markdown_files()
        for md_file in md_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                count = sum(len(p.findall(content)) for p in patterns)
                if count > 0:
                    references.append((md_file, count))
            except (OSError, UnicodeDecodeError):
                pass
        
        return references
    
    def global_search_replace(
        self,
        search_text: str,
        replace_text: str,
        dry_run: bool = True,
        file_extensions: List[str] = None
    ) -> Tuple[bool, Dict[str, int]]:
        """
        Búsqueda y reemplazo global de texto en archivos y nombres.
        
        Args:
            search_text: Texto a buscar
            replace_text: Texto de reemplazo
            dry_run: Si True, solo simula los cambios
            file_extensions: Lista de extensiones a procesar (default: ['.md', '.py', '.yaml', '.yml'])
            
        Returns:
            Tupla (éxito, dict con estadísticas de cambios)
        """
        if file_extensions is None:
            file_extensions = ['.md', '.py', '.yaml', '.yml']
        
        print(f"\n{'[SIMULACIÓN] ' if dry_run else ''}🔍 BÚSQUEDA Y REEMPLAZO GLOBAL")
        print("=" * 70)
        print(f"Buscar:    '{search_text}'")
        print(f"Reemplazar: '{replace_text}'")
        print(f"Extensiones: {', '.join(file_extensions)}")
        print("-" * 70)
        
        stats = {
            'files_renamed': 0,
            'files_content_modified': 0,
            'total_replacements': 0,
            'files_processed': []
        }
        
        # 1. Buscar y reemplazar en CONTENIDO de archivos
        print("\n📝 Buscando en contenido de archivos...")
        content_results = self._replace_in_file_contents(
            search_text, replace_text, file_extensions, dry_run
        )
        stats['files_content_modified'] = content_results['files_modified']
        stats['total_replacements'] += content_results['replacements']
        stats['files_processed'].extend(content_results['files'])
        
        # 2. Buscar y reemplazar en NOMBRES de archivos
        print("\n📁 Buscando en nombres de archivos...")
        rename_results = self._replace_in_filenames(
            search_text, replace_text, file_extensions, dry_run
        )
        stats['files_renamed'] = rename_results['files_renamed']
        stats['files_processed'].extend(rename_results['files'])
        
        # Resumen
        print(f"\n{'[SIMULACIÓN] ' if dry_run else ''}📊 RESUMEN")
        print("=" * 70)
        print(f"Archivos renombrados:        {stats['files_renamed']}")
        print(f"Archivos con contenido modificado: {stats['files_content_modified']}")
        print(f"Total de reemplazos:         {stats['total_replacements']}")
        print(f"Archivos procesados:         {len(set(stats['files_processed']))}")
        
        if stats['files_processed']:
            print("\nArchivos afectados:")
            for f in sorted(set(stats['files_processed'])):
                rel_path = os.path.relpath(f, self.base_dir)
                print(f"  - {rel_path}")
        
        return True, stats
    
    def _replace_in_file_contents(
        self,
        search_text: str,
        replace_text: str,
        file_extensions: List[str],
        dry_run: bool
    ) -> Dict[str, any]:
        """Reemplaza texto en el contenido de archivos."""
        results = {
            'files_modified': 0,
            'replacements': 0,
            'files': []
        }
        
        # Buscar todos los archivos con las extensiones especificadas
        target_files = []
        for root, dirs, files in os.walk(self.base_dir):
            # Ignorar directorios de sistema
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.git']]
            
            for file in files:
                if any(file.endswith(ext) for ext in file_extensions):
                    target_files.append(os.path.join(root, file))
        
        # Procesar cada archivo
        for filepath in target_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Contar ocurrencias
                count = content.count(search_text)
                
                if count > 0:
                    # Reemplazar texto
                    new_content = content.replace(search_text, replace_text)
                    
                    if not dry_run:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                    
                    results['files_modified'] += 1
                    results['replacements'] += count
                    results['files'].append(filepath)
                    
                    rel_path = os.path.relpath(filepath, self.base_dir)
                    print(f"  ✓ {rel_path}: {count} reemplazo(s)")
            
            except Exception as e:
                rel_path = os.path.relpath(filepath, self.base_dir)
                print(f"  ⚠️ Error en {rel_path}: {e}")
        
        return results
    
    def _replace_in_filenames(
        self,
        search_text: str,
        replace_text: str,
        file_extensions: List[str],
        dry_run: bool
    ) -> Dict[str, any]:
        """Reemplaza texto en nombres de archivos."""
        results = {
            'files_renamed': 0,
            'files': []
        }
        
        # Buscar archivos cuyos nombres contengan el texto
        files_to_rename = []
        for root, dirs, files in os.walk(self.base_dir):
            # Ignorar directorios de sistema
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.git']]
            
            for file in files:
                # Solo procesar archivos con extensiones especificadas
                if any(file.endswith(ext) for ext in file_extensions):
                    if search_text in file:
                        old_path = os.path.join(root, file)
                        new_name = file.replace(search_text, replace_text)
                        new_path = os.path.join(root, new_name)
                        files_to_rename.append((old_path, new_path, file, new_name))
        
        # Renombrar archivos
        for old_path, new_path, old_name, new_name in files_to_rename:
            try:
                # Verificar que el destino no exista
                if os.path.exists(new_path) and old_path != new_path:
                    print(f"  ⚠️ Ya existe: {new_name} (saltando)")
                    continue
                
                if not dry_run:
                    os.rename(old_path, new_path)
                
                results['files_renamed'] += 1
                results['files'].append(new_path if not dry_run else old_path)
                
                rel_old = os.path.relpath(old_path, self.base_dir)
                rel_new = os.path.relpath(new_path, self.base_dir)
                print(f"  ✓ {rel_old}")
                print(f"    → {rel_new}")
            
            except Exception as e:
                print(f"  ❌ Error renombrando {old_name}: {e}")
        
        return results
    
    def interactive_global_replace(self) -> bool:
        """Flujo interactivo para búsqueda y reemplazo global."""
        print("\n🔍 BÚSQUEDA Y REEMPLAZO GLOBAL")
        print("=" * 70)
        print("Busca y reemplaza texto en:")
        print("  • Contenido de archivos (.md, .py, .yaml)")
        print("  • Nombres de archivos")
        print("-" * 70)
        
        # Pedir texto a buscar
        search_text = input("\n📝 Texto a buscar: ").strip()
        if not search_text:
            print("❌ Texto requerido")
            return False
        
        # Pedir texto de reemplazo
        replace_text = input("📝 Texto de reemplazo: ").strip()
        if not replace_text:
            print("❌ Texto de reemplazo requerido")
            return False
        
        # Previsualizar cambios
        print("\n🔍 Buscando ocurrencias...")
        
        # Hacer dry-run primero
        print("\n" + "=" * 70)
        print("VISTA PREVIA DE CAMBIOS")
        print("=" * 70)
        success, stats = self.global_search_replace(
            search_text, replace_text, dry_run=True
        )
        
        if not success:
            print("\n❌ Error durante la búsqueda")
            return False
        
        # Verificar si hay cambios
        total_changes = stats['files_renamed'] + stats['files_content_modified']
        if total_changes == 0:
            print(f"\n⚠️ No se encontraron ocurrencias de '{search_text}'")
            return False
        
        # Confirmar
        print("\n" + "=" * 70)
        print(f"⚠️ Se modificarán {total_changes} archivo(s)")
        print(f"   - {stats['files_renamed']} archivo(s) renombrados")
        print(f"   - {stats['files_content_modified']} archivo(s) con contenido modificado")
        print(f"   - {stats['total_replacements']} reemplazo(s) en total")
        print("=" * 70)
        
        confirm = input("\n¿Ejecutar los cambios? (s/n): ").strip().lower()
        if confirm != 's':
            print("❌ Operación cancelada")
            return False
        
        # Ejecutar cambios reales
        print("\n" + "=" * 70)
        print("EJECUTANDO CAMBIOS")
        print("=" * 70)
        success, stats = self.global_search_replace(
            search_text, replace_text, dry_run=False
        )
        
        if success:
            print("\n✅ ¡Cambios aplicados exitosamente!")
            return True
        else:
            print("\n❌ Error durante la aplicación de cambios")
            return False
    
    def interactive_rename(self) -> bool:
        """Flujo interactivo para renombrar archivos."""
        print("\n🔄 RENOMBRADO INTELIGENTE DE ARCHIVOS")
        print("=" * 60)
        
        # Listar archivos disponibles
        files = self.list_renameable_files()
        
        if not files:
            print("❌ No se encontraron archivos .md en el directorio")
            return False
        
        print("\n📁 Archivos disponibles:")
        for i, f in enumerate(files, 1):
            print(f"{i}. {f}")
        print("0. Cancelar")
        print("-" * 60)
        
        # Seleccionar archivo
        try:
            choice = input("\nSelecciona el archivo a renombrar (número): ").strip()
            if choice == "0":
                return False
            
            idx = int(choice) - 1
            if idx < 0 or idx >= len(files):
                print("❌ Opción inválida")
                return False
            
            old_filename = files[idx]
        except (ValueError, IndexError):
            print("❌ Opción inválida")
            return False
        
        # Mostrar referencias actuales
        print(f"\n🔍 Buscando referencias a '{old_filename}'...")
        refs = self.search_file_references(old_filename)
        
        if refs:
            print(f"\n📊 Se encontraron {len(refs)} archivo(s) con referencias:")
            for ref_file, count in refs:
                rel_path = os.path.relpath(ref_file, self.base_dir)
                print(f"  - {rel_path}: {count} referencia(s)")
        else:
            print("  ℹ️ No se encontraron referencias")
        
        # Pedir nuevo nombre
        print(f"\n✏️ Nombre actual: {old_filename}")
        new_filename = input("Nuevo nombre (con extensión .md): ").strip()
        
        if not new_filename:
            print("❌ Nombre requerido")
            return False
        
        # Asegurar extensión .md
        if not new_filename.endswith('.md'):
            new_filename += '.md'
        
        # Confirmar cambios
        print(f"\n⚠️ CONFIRMACIÓN")
        print("=" * 60)
        print(f"Archivo:          {old_filename}")
        print(f"Nuevo nombre:     {new_filename}")
        print(f"Referencias:      {len(refs)} archivo(s) serán actualizados")
        print("-" * 60)
        
        # Primero hacer dry-run
        confirm = input("¿Ver simulación primero? (s/n): ").strip().lower()
        if confirm == 's':
            print("\n" + "=" * 60)
            print("MODO SIMULACIÓN (no se harán cambios reales)")
            print("=" * 60)
            self.rename_file_with_references(old_filename, new_filename, dry_run=True)
            print("\n" + "=" * 60)
        
        # Confirmar cambios reales
        confirm = input("\n¿Ejecutar el renombrado? (s/n): ").strip().lower()
        if confirm != 's':
            print("❌ Operación cancelada")
            return False
        
        # Ejecutar renombrado
        success, modified = self.rename_file_with_references(
            old_filename, new_filename, dry_run=False
        )
        
        if success:
            print("\n✅ ¡Renombrado completado exitosamente!")
            return True
        else:
            print("\n❌ Error durante el renombrado")
            return False


def main():
    """Función principal para testing."""
    import sys
    
    manager = FileRenameManager()
    
    if len(sys.argv) > 2:
        # Modo búsqueda y reemplazo global
        search_text = sys.argv[1]
        replace_text = sys.argv[2]
        
        print(f"Buscando '{search_text}' para reemplazar por '{replace_text}'...")
        
        # Vista previa
        print("\n" + "=" * 70)
        print("VISTA PREVIA")
        print("=" * 70)
        manager.global_search_replace(search_text, replace_text, dry_run=True)
        
        confirm = input("\n¿Ejecutar cambios? (s/n): ").strip().lower()
        if confirm == 's':
            manager.global_search_replace(search_text, replace_text, dry_run=False)
    else:
        # Modo interactivo - mostrar menú
        while True:
            print("\n🔄 GESTOR DE BÚSQUEDA Y REEMPLAZO")
            print("=" * 70)
            print("1. 🔍 Búsqueda y reemplazo global (nombres + contenido)")
            print("2. 📁 Renombrar archivo específico (con referencias)")
            print("0. ↩️ Salir")
            print("-" * 70)
            
            choice = input("Opción: ").strip()
            
            if choice == "1":
                manager.interactive_global_replace()
            elif choice == "2":
                manager.interactive_rename()
            elif choice == "0":
                break
            else:
                print("❌ Opción inválida")


if __name__ == "__main__":
    main()
