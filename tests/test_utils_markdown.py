#!/usr/bin/env python3
"""
Tests unitarios para funciones en utils/markdown.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.markdown import adjust_headings, remove_metadata, extract_title, count_headings


class TestMarkdown:
    """Tests para funciones de manipulación Markdown."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
    
    def test_adjust_headings(self):
        """Test que adjust_headings agrega correctamente un nivel."""
        try:
            content = """# Título
## Subtítulo
### Sub-subtítulo
Texto normal"""
            
            # Con skip_first_line=True (default), OMITE la primera línea del resultado
            adjusted = adjust_headings(content, skip_first_line=True)
            # La primera línea (# Título) NO aparece en el resultado
            assert "### Subtítulo" in adjusted, "Nivel 2 no aumentó"
            assert "#### Sub-subtítulo" in adjusted, "Nivel 3 no aumentó"
            assert "Texto normal" in adjusted, "Texto normal debería estar"
            
            print("✅ Test: adjust_headings agrega un nivel correctamente")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test adjust_headings falló: {e}")
            self.failed += 1
    
    def test_remove_metadata(self):
        """Test que remove_metadata elimina líneas de metadata."""
        try:
            content = """# Título
> Metadata 1
> Metadata 2
---
## Sección
Contenido importante"""
            
            cleaned = remove_metadata(content)
            assert "Metadata" not in cleaned, "Metadata no fue removida"
            assert "---" not in cleaned, "Separador no fue removido"
            assert "Contenido importante" in cleaned, "Contenido fue removido"
            
            print("✅ Test: remove_metadata elimina metadata correctamente")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test remove_metadata falló: {e}")
            self.failed += 1
    
    def test_extract_title(self):
        """Test que extract_title obtiene el título correctamente."""
        try:
            content = """# Mi Título Principal
## Subsección
Contenido"""
            
            title = extract_title(content)
            assert title == "Mi Título Principal", f"Título extraído: {title}"
            
            print("✅ Test: extract_title obtiene el título correctamente")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test extract_title falló: {e}")
            self.failed += 1
    
    def test_count_headings(self):
        """Test que count_headings cuenta correctamente."""
        try:
            content = """# Título
## Subsección 1
## Subsección 2
### Sub-subsección
Texto normal"""
            
            result = count_headings(content)
            # count_headings retorna un diccionario con conteos
            if isinstance(result, dict):
                total = sum(result.values())
                assert total >= 4, f"Se esperaban al menos 4 encabezados, se contaron {total}"
            else:
                assert result >= 4, f"Se esperaban al menos 4 encabezados, se contaron {result}"
            
            print("✅ Test: count_headings cuenta correctamente")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test count_headings falló: {e}")
            self.failed += 1
    
    def test_adjust_headings_skip_first(self):
        """Test que adjust_headings omite la primera línea cuando se indica."""
        try:
            content = """# Título Principal
## Subtítulo
### Sub-subtítulo"""
            
            adjusted = adjust_headings(content, skip_first_line=True)
            lines = adjusted.split('\n')
            # Con skip_first_line=True, la primera línea se OMITE completamente
            # Solo aparecen las líneas procesadas (2da en adelante)
            assert "Título Principal" not in adjusted, "Primera línea debería omitirse"
            assert "### Subtítulo" in adjusted, "Segunda línea debería procesarse"
            
            print("✅ Test: adjust_headings respeta skip_first_line")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test adjust_headings skip_first falló: {e}")
            self.failed += 1
    
    def run_all(self):
        """Ejecutar todos los tests."""
        print("\n🧪 TESTS: utils/markdown.py")
        print("=" * 50)
        
        self.test_adjust_headings()
        self.test_remove_metadata()
        self.test_extract_title()
        self.test_count_headings()
        self.test_adjust_headings_skip_first()
        
        print(f"\n📊 Resultado: ✅ {self.passed} | ❌ {self.failed}")
        return self.failed == 0


if __name__ == "__main__":
    tester = TestMarkdown()
    success = tester.run_all()
    sys.exit(0 if success else 1)
