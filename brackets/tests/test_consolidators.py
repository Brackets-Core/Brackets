"""
Tests básicos para validar la refactorización de consolidadores.
"""

import os
import sys

# Agregar el directorio raíz al path para importar módulos
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from brackets.consolidators.month import MonthConsolidator
from brackets.consolidators.year import YearConsolidator
from brackets.config import MONTH_NAMES, SEASON_EMOJIS


def test_imports():
    """Test que las importaciones funcionan correctamente."""
    print("✅ Test 1: Importaciones exitosas")
    print(f"   - MonthConsolidator: {MonthConsolidator.__name__}")
    print(f"   - YearConsolidator: {YearConsolidator.__name__}")
    print(f"   - MONTH_NAMES tiene {len(MONTH_NAMES)} meses")
    print(f"   - SEASON_EMOJIS tiene {len(SEASON_EMOJIS)} estaciones")
    return True


def test_month_consolidator_init():
    """Test que MonthConsolidator se inicializa correctamente."""
    try:
        consolidator = MonthConsolidator(".")
        print("✅ Test 2: MonthConsolidator inicializado correctamente")
        print(f"   - Directorio: {consolidator.directory}")
        print(f"   - Tiene método consolidate: {hasattr(consolidator, 'consolidate')}")
        print(f"   - Hereda de BaseConsolidator: {hasattr(consolidator, 'confirm_deletion')}")
        return True
    except Exception as e:
        print(f"❌ Test 2 falló: {e}")
        return False


def test_year_consolidator_init():
    """Test que YearConsolidator se inicializa correctamente."""
    try:
        consolidator = YearConsolidator(".")
        print("✅ Test 3: YearConsolidator inicializado correctamente")
        print(f"   - Directorio: {consolidator.directory}")
        print(f"   - Tiene método consolidate: {hasattr(consolidator, 'consolidate')}")
        print(f"   - Hereda de BaseConsolidator: {hasattr(consolidator, 'confirm_deletion')}")
        return True
    except Exception as e:
        print(f"❌ Test 3 falló: {e}")
        return False


def test_season_emoji():
    """Test que la función get_season_emoji funciona."""
    try:
        consolidator = MonthConsolidator(".")
        winter = consolidator.get_season_emoji(1)
        spring = consolidator.get_season_emoji(4)
        summer = consolidator.get_season_emoji(7)
        autumn = consolidator.get_season_emoji(10)
        
        print("✅ Test 4: get_season_emoji funciona correctamente")
        print(f"   - Enero (invierno): {winter}")
        print(f"   - Abril (primavera): {spring}")
        print(f"   - Julio (verano): {summer}")
        print(f"   - Octubre (otoño): {autumn}")
        return True
    except Exception as e:
        print(f"❌ Test 4 falló: {e}")
        return False


def test_list_available_months():
    """Test que list_available_months funciona."""
    try:
        consolidator = MonthConsolidator(".")
        months = consolidator.list_available_months()
        print("✅ Test 5: list_available_months funciona")
        print(f"   - Se encontraron {len(months)} meses disponibles")
        if months:
            print(f"   - Primeros 3: {months[:3]}")
        return True
    except Exception as e:
        print(f"❌ Test 5 falló: {e}")
        return False


def test_list_available_years():
    """Test que list_available_years funciona."""
    try:
        consolidator = YearConsolidator(".")
        years = consolidator.list_available_years()
        print("✅ Test 6: list_available_years funciona")
        print(f"   - Se encontraron {len(years)} años disponibles")
        if years:
            print(f"   - Años: {years}")
        return True
    except Exception as e:
        print(f"❌ Test 6 falló: {e}")
        return False


def test_base_consolidator_methods():
    """Test que los métodos heredados de BaseConsolidator están disponibles."""
    try:
        month_cons = MonthConsolidator(".")
        year_cons = YearConsolidator(".")
        
        methods = [
            'confirm_deletion',
            'handle_existing_output',
            'delete_files_confirmed',
            'adjust_markdown_headings',
            'remove_markdown_metadata'
        ]
        
        all_ok = True
        for method in methods:
            if not hasattr(month_cons, method):
                print(f"   ❌ MonthConsolidator no tiene método: {method}")
                all_ok = False
            if not hasattr(year_cons, method):
                print(f"   ❌ YearConsolidator no tiene método: {method}")
                all_ok = False
        
        if all_ok:
            print("✅ Test 7: Métodos de BaseConsolidator disponibles")
            print(f"   - Verificados {len(methods)} métodos")
            return True
        else:
            print("❌ Test 7 falló: Faltan métodos")
            return False
    except Exception as e:
        print(f"❌ Test 7 falló: {e}")
        return False


def test_consolidate_month_deletes_sources_and_unifies_defs():
    """Test que consolidate_month unifica definiciones y elimina los archivos origen."""
    import tempfile
    import shutil

    tmp = tempfile.mkdtemp()
    try:
        w19_content = """# 🗓️Week 19

## 📋Week Tasks
  - [ ] Tarea semana 19 [🎫JIRA-101]

## 🏠04
  - [x] Tarea día 4

<!-- Definiciones -->
[🎫JIRA-101]: https://jira.mango.com/browse/JIRA-101
"""
        w20_content = """# 🗓️Week 20

## 📋Week Tasks
  - [ ] Tarea semana 20 [📂DOC-202]

## 🚗11
  - [ ] Tarea día 11

<!-- Definiciones -->
[📂DOC-202]: https://confluence.mango.com/DOC-202
[🎫JIRA-101]: https://jira.mango.com/browse/JIRA-101
"""
        w19_path = os.path.join(tmp, "[2026][05]Week19.md")
        w20_path = os.path.join(tmp, "[2026][05]Week20.md")
        with open(w19_path, "w", encoding="utf-8") as f:
            f.write(w19_content)
        with open(w20_path, "w", encoding="utf-8") as f:
            f.write(w20_content)

        cons = MonthConsolidator(tmp)
        success = cons.consolidate_month(2026, 5, interactive=False, delete_source=True)
        if not success:
            print("❌ consolidate_month retornó False")
            return False

        out_path = os.path.join(tmp, "[2026][05].md")
        if not os.path.exists(out_path):
            print("❌ Archivo consolidado no fue creado")
            return False

        # Verificar que los archivos semanales origen fueron eliminados
        if os.path.exists(w19_path) or os.path.exists(w20_path):
            print("❌ Los archivos semanales origen no fueron eliminados tras la consolidación")
            return False

        with open(out_path, "r", encoding="utf-8") as f:
            consolidated_text = f.read()

        # Debe contener solo un bloque <!-- Definiciones -->
        def_occurrences = consolidated_text.count("<!-- Definiciones -->")
        if def_occurrences != 1:
            print(f"❌ Esperado 1 bloque <!-- Definiciones -->, encontrado {def_occurrences}")
            return False

        if "[🎫JIRA-101]: https://jira.mango.com/browse/JIRA-101" not in consolidated_text:
            print("❌ Falta [🎫JIRA-101] en definiciones unificadas")
            return False
        if "[📂DOC-202]: https://confluence.mango.com/DOC-202" not in consolidated_text:
            print("❌ Falta [📂DOC-202] en definiciones unificadas")
            return False

        print("✅ Test 8: consolidate_month unifica definiciones y elimina archivos origen correctamente")
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_cleanup_consolidated_sources():
    """Test que cleanup_consolidated_source_files elimina bitácoras de meses ya consolidados."""
    import tempfile
    import shutil

    tmp = tempfile.mkdtemp()
    try:
        # Mes 4 consolidado previamente
        with open(os.path.join(tmp, "[2026][04].md"), "w", encoding="utf-8") as f:
            f.write("# Consolidado Mes 4\n")
        # Bitácora semanal residual
        w15_path = os.path.join(tmp, "[2026][04]Week15.md")
        with open(w15_path, "w", encoding="utf-8") as f:
            f.write("# Semana 15\n")

        cons = MonthConsolidator(tmp)
        pending = cons.get_consolidated_months_with_source_files()
        if len(pending) != 1 or pending[0][0] != 2026 or pending[0][1] != 4:
            print("❌ Fallo en get_consolidated_months_with_source_files")
            return False

        deleted = cons.cleanup_consolidated_source_files(2026, 4, interactive=False)
        if deleted != 1 or os.path.exists(w15_path):
            print("❌ cleanup_consolidated_source_files no eliminó la bitácora residual")
            return False

        print("✅ Test 9: cleanup_consolidated_source_files limpia bitácoras residuales exitosamente")
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_all_tests():
    """Ejecuta todos los tests."""
    print("\n" + "=" * 50)
    print("🧪 EJECUTANDO TESTS DE VALIDACIÓN")
    print("=" * 50 + "\n")
    
    tests = [
        test_imports,
        test_month_consolidator_init,
        test_year_consolidator_init,
        test_season_emoji,
        test_list_available_months,
        test_list_available_years,
        test_base_consolidator_methods,
        test_consolidate_month_deletes_sources_and_unifies_defs,
        test_cleanup_consolidated_sources,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            print()
        except Exception as e:
            print(f"❌ Error ejecutando {test.__name__}: {e}\n")
            results.append(False)
    
    # Resumen
    print("=" * 50)
    print("📊 RESUMEN DE TESTS")
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"\n✅ Pasados: {passed}/{total}")
    print(f"❌ Fallidos: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 TODOS LOS TESTS PASARON")
        print("✅ La refactorización está completa y funcional")
    else:
        print("\n⚠️  ALGUNOS TESTS FALLARON")
        print("⚠️  Revisar los errores antes de continuar")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
