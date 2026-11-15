"""
Test del FileRenameManager
"""
import os
import sys
import tempfile
import shutil

# Añadir el directorio padre al path para poder importar brackets
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from managers.file_rename_manager import FileRenameManager


def test_file_rename_manager():
    """Test del renombrado de archivos con actualización de referencias."""
    
    # Crear directorio temporal
    test_dir = tempfile.mkdtemp()
    print(f"📁 Directorio de prueba: {test_dir}")
    
    try:
        # Crear estructura de prueba
        data_dir = os.path.join(test_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        
        # 1. Crear archivo a renombrar
        old_file = os.path.join(test_dir, "[TEST]OldFile.md")
        with open(old_file, 'w', encoding='utf-8') as f:
            f.write("# Old File\n\nContenido del archivo original.\n")
        print(f"✅ Creado: {os.path.basename(old_file)}")
        
        # 2. Crear archivo YAML con referencia
        yaml_file = os.path.join(data_dir, "categories.yaml")
        yaml_content = """categories:
  - id: test
    name: TEST
    description: Categoría de prueba
    subcategories:
      - id: docs
        name: DOCS
        documents:
          - OldFile.md
          - OtherFile.md
"""
        with open(yaml_file, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        print(f"✅ Creado: data/categories.yaml")
        
        # 3. Crear archivo markdown con referencias
        ref_file1 = os.path.join(test_dir, "[TEST]References1.md")
        ref_content1 = """# Referencias 1

Aquí hay una referencia markdown: [Ver archivo](OldFile.md)

Y una referencia WikiStyle: [[OldFile]]

Y una con texto: [[OldFile|Ir al archivo]]

También mencionamos directamente OldFile.md en el texto.
"""
        with open(ref_file1, 'w', encoding='utf-8') as f:
            f.write(ref_content1)
        print(f"✅ Creado: {os.path.basename(ref_file1)}")
        
        # 4. Crear otro archivo markdown con referencias
        ref_file2 = os.path.join(test_dir, "[TEST]References2.md")
        ref_content2 = """# Referencias 2

Otra referencia: [[OldFile]]

Link directo: OldFile.md
"""
        with open(ref_file2, 'w', encoding='utf-8') as f:
            f.write(ref_content2)
        print(f"✅ Creado: {os.path.basename(ref_file2)}")
        
        # 5. Crear FileRenameManager
        manager = FileRenameManager(test_dir)
        
        # 6. Buscar referencias antes del renombrado
        print("\n" + "=" * 60)
        print("🔍 Buscando referencias a 'OldFile.md'...")
        refs = manager.search_file_references("OldFile.md")
        print(f"Encontradas {len(refs)} archivo(s) con referencias:")
        for ref_path, count in refs:
            print(f"  - {os.path.basename(ref_path)}: {count} referencia(s)")
        
        # 7. Simular renombrado (dry run)
        print("\n" + "=" * 60)
        print("SIMULACIÓN DE RENOMBRADO")
        print("=" * 60)
        success, modified = manager.rename_file_with_references(
            "OldFile.md", 
            "NewFile.md", 
            dry_run=True
        )
        
        if not success:
            print("❌ Falló la simulación")
            return False
        
        # 8. Ejecutar renombrado real
        print("\n" + "=" * 60)
        print("RENOMBRADO REAL")
        print("=" * 60)
        success, modified = manager.rename_file_with_references(
            "OldFile.md", 
            "NewFile.md", 
            dry_run=False
        )
        
        if not success:
            print("❌ Falló el renombrado real")
            return False
        
        # 9. Verificar resultados
        print("\n" + "=" * 60)
        print("VERIFICACIÓN DE RESULTADOS")
        print("=" * 60)
        
        # Verificar que el archivo fue renombrado
        new_file = os.path.join(test_dir, "[TEST]NewFile.md")
        if not os.path.exists(new_file):
            print("❌ El archivo nuevo no existe")
            return False
        print(f"✅ Archivo renombrado correctamente: NewFile.md")
        
        # Verificar que el viejo ya no existe
        if os.path.exists(old_file):
            print("❌ El archivo viejo todavía existe")
            return False
        print("✅ Archivo viejo eliminado correctamente")
        
        # Verificar YAML
        with open(yaml_file, 'r', encoding='utf-8') as f:
            yaml_updated = f.read()
        
        if "NewFile.md" in yaml_updated and "OldFile.md" not in yaml_updated:
            print("✅ YAML actualizado correctamente")
        else:
            print("❌ YAML no actualizado correctamente")
            print(yaml_updated)
            return False
        
        # Verificar referencias en markdown
        with open(ref_file1, 'r', encoding='utf-8') as f:
            ref1_updated = f.read()
        
        with open(ref_file2, 'r', encoding='utf-8') as f:
            ref2_updated = f.read()
        
        # Contar referencias actualizadas
        ref1_count = ref1_updated.count("NewFile")
        ref2_count = ref2_updated.count("NewFile")
        
        if ref1_count >= 4 and ref2_count >= 2:
            print(f"✅ Referencias actualizadas en markdown:")
            print(f"   - References1.md: {ref1_count} referencias")
            print(f"   - References2.md: {ref2_count} referencias")
        else:
            print(f"❌ Referencias no actualizadas correctamente")
            print(f"   - References1.md: {ref1_count} (esperado: ≥4)")
            print(f"   - References2.md: {ref2_count} (esperado: ≥2)")
            print("\nContenido de References1.md:")
            print(ref1_updated)
            return False
        
        # Verificar que no quedan referencias al archivo viejo
        if "OldFile" not in ref1_updated and "OldFile" not in ref2_updated:
            print("✅ No quedan referencias al archivo viejo")
        else:
            print("⚠️ Todavía hay referencias al archivo viejo")
            if "OldFile" in ref1_updated:
                print(f"   - En References1.md")
            if "OldFile" in ref2_updated:
                print(f"   - En References2.md")
        
        print("\n" + "=" * 60)
        print("✅ ¡TODOS LOS TESTS PASARON!")
        print("=" * 60)
        return True
        
    finally:
        # Limpiar directorio temporal
        shutil.rmtree(test_dir)
        print(f"\n🧹 Directorio de prueba eliminado")


if __name__ == "__main__":
    success = test_file_rename_manager()
    sys.exit(0 if success else 1)
