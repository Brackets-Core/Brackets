"""
Test del búsqueda y reemplazo global
"""
import os
import sys
import tempfile
import shutil

# Añadir el directorio padre al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from managers.file_rename_manager import FileRenameManager


def test_global_search_replace():
    """Test de búsqueda y reemplazo global."""
    
    # Crear directorio temporal
    test_dir = tempfile.mkdtemp()
    print(f"📁 Directorio de prueba: {test_dir}")
    
    try:
        # Crear estructura de prueba
        data_dir = os.path.join(test_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        
        # 1. Crear archivos .md con texto a buscar
        md_file1 = os.path.join(test_dir, "OldTerm_doc.md")
        with open(md_file1, 'w', encoding='utf-8') as f:
            f.write("# Documento sobre OldTerm\n\nEsto habla de OldTerm y sus usos.\n")
        print(f"✅ Creado: {os.path.basename(md_file1)}")
        
        md_file2 = os.path.join(test_dir, "reference.md")
        with open(md_file2, 'w', encoding='utf-8') as f:
            f.write("# Referencias\n\nVer [[OldTerm_doc]] para más info sobre OldTerm.\n")
        print(f"✅ Creado: {os.path.basename(md_file2)}")
        
        # 2. Crear archivo .py con texto a buscar
        py_file = os.path.join(test_dir, "script_OldTerm.py")
        with open(py_file, 'w', encoding='utf-8') as f:
            f.write('"""Script sobre OldTerm"""\n\nclass OldTerm:\n    pass\n')
        print(f"✅ Creado: {os.path.basename(py_file)}")
        
        # 3. Crear archivo .yaml con texto a buscar
        yaml_file = os.path.join(data_dir, "config.yaml")
        with open(yaml_file, 'w', encoding='utf-8') as f:
            f.write("settings:\n  term: OldTerm\n  files:\n    - OldTerm_doc.md\n")
        print(f"✅ Creado: data/config.yaml")
        
        # 4. Crear FileRenameManager
        manager = FileRenameManager(test_dir)
        
        # 5. Ejecutar búsqueda y reemplazo (dry run)
        print("\n" + "=" * 70)
        print("SIMULACIÓN DE BÚSQUEDA Y REEMPLAZO")
        print("=" * 70)
        success, stats = manager.global_search_replace(
            "OldTerm", "NewTerm", dry_run=True
        )
        
        if not success:
            print("❌ Falló la simulación")
            return False
        
        print(f"\nEstadísticas de simulación:")
        print(f"  - Archivos a renombrar: {stats['files_renamed']}")
        print(f"  - Archivos con contenido a modificar: {stats['files_content_modified']}")
        print(f"  - Total de reemplazos: {stats['total_replacements']}")
        
        # 6. Ejecutar búsqueda y reemplazo real
        print("\n" + "=" * 70)
        print("BÚSQUEDA Y REEMPLAZO REAL")
        print("=" * 70)
        success, stats = manager.global_search_replace(
            "OldTerm", "NewTerm", dry_run=False
        )
        
        if not success:
            print("❌ Falló la búsqueda y reemplazo real")
            return False
        
        # 7. Verificar resultados
        print("\n" + "=" * 70)
        print("VERIFICACIÓN DE RESULTADOS")
        print("=" * 70)
        
        # Verificar archivos renombrados
        new_md_file1 = os.path.join(test_dir, "NewTerm_doc.md")
        new_py_file = os.path.join(test_dir, "script_NewTerm.py")
        
        if not os.path.exists(new_md_file1):
            print(f"❌ Archivo no renombrado: NewTerm_doc.md")
            return False
        print("✅ Archivo renombrado: OldTerm_doc.md → NewTerm_doc.md")
        
        if not os.path.exists(new_py_file):
            print(f"❌ Archivo no renombrado: script_NewTerm.py")
            return False
        print("✅ Archivo renombrado: script_OldTerm.py → script_NewTerm.py")
        
        # Verificar que los viejos no existen
        if os.path.exists(md_file1):
            print("❌ Archivo viejo todavía existe: OldTerm_doc.md")
            return False
        
        if os.path.exists(py_file):
            print("❌ Archivo viejo todavía existe: script_OldTerm.py")
            return False
        
        # Verificar contenido actualizado en .md
        with open(new_md_file1, 'r', encoding='utf-8') as f:
            content_md1 = f.read()
        
        with open(md_file2, 'r', encoding='utf-8') as f:
            content_md2 = f.read()
        
        if "NewTerm" in content_md1 and "OldTerm" not in content_md1:
            print("✅ Contenido actualizado en NewTerm_doc.md")
        else:
            print("❌ Contenido NO actualizado en NewTerm_doc.md")
            print(content_md1)
            return False
        
        if "NewTerm" in content_md2 and "OldTerm" not in content_md2:
            print("✅ Contenido actualizado en reference.md")
        else:
            print("❌ Contenido NO actualizado en reference.md")
            print(content_md2)
            return False
        
        # Verificar contenido en .py
        with open(new_py_file, 'r', encoding='utf-8') as f:
            content_py = f.read()
        
        if "NewTerm" in content_py and "OldTerm" not in content_py:
            print("✅ Contenido actualizado en script_NewTerm.py")
        else:
            print("❌ Contenido NO actualizado en script_NewTerm.py")
            print(content_py)
            return False
        
        # Verificar contenido en .yaml
        with open(yaml_file, 'r', encoding='utf-8') as f:
            content_yaml = f.read()
        
        if "NewTerm" in content_yaml and "OldTerm" not in content_yaml:
            print("✅ Contenido actualizado en config.yaml")
        else:
            print("❌ Contenido NO actualizado en config.yaml")
            print(content_yaml)
            return False
        
        # Verificar estadísticas
        print(f"\n📊 Estadísticas finales:")
        print(f"  - Archivos renombrados: {stats['files_renamed']}")
        print(f"  - Archivos con contenido modificado: {stats['files_content_modified']}")
        print(f"  - Total de reemplazos: {stats['total_replacements']}")
        
        if stats['files_renamed'] != 2:
            print(f"❌ Se esperaban 2 archivos renombrados, se obtuvieron {stats['files_renamed']}")
            return False
        
        if stats['files_content_modified'] != 4:
            print(f"❌ Se esperaban 4 archivos modificados, se obtuvieron {stats['files_content_modified']}")
            return False
        
        print("\n" + "=" * 70)
        print("✅ ¡TODOS LOS TESTS PASARON!")
        print("=" * 70)
        return True
        
    finally:
        # Limpiar directorio temporal
        shutil.rmtree(test_dir)
        print(f"\n🧹 Directorio de prueba eliminado")


if __name__ == "__main__":
    success = test_global_search_replace()
    sys.exit(0 if success else 1)
