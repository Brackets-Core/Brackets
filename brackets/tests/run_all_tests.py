#!/usr/bin/env python3
"""
Runner integral para ejecutar todos los tests unitarios y suites del sistema Brackets.
Ejecutar desde la raíz del proyecto: python -m brackets.tests.run_all_tests
"""

import sys
import os

# Agregar el directorio raíz al path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Importar todos los tests
from brackets.tests.test_consolidators import test_imports, test_month_consolidator_init
from brackets.tests.test_consolidators import test_year_consolidator_init, test_season_emoji
from brackets.tests.test_consolidators import test_list_available_months, test_list_available_years
from brackets.tests.test_utils_helpers import TestHelpers
from brackets.tests.test_utils_markdown import TestMarkdown
from brackets.tests.test_utils_legacy import TestLegacyUtils
from brackets.tests.test_utils_content_parser import TestContentParser
from brackets.tests.test_utils_content_generator import TestContentGenerator
from brackets.tests.test_utils_file_finder import TestFileFinder
from brackets.tests.test_generators_monthly import TestMonthlyGenerator
from brackets.tests.test_generators_weekly import TestWeeklyGenerator
from brackets.tests.test_path_scope_smoke import TestPathScopeSmoke
from brackets.tests.test_cli_vault_scope import TestCliVaultScope
from brackets.tests.test_core_cli_actions import TestCoreCliActions
from brackets.tests.test_core_category_management_controller import TestCoreCategoryManagementController
from brackets.tests.test_core_configuration_controller import TestCoreConfigurationController
from brackets.tests.test_core_cli_parser import TestCoreCliParser
from brackets.tests.test_core_file_management_controller import TestCoreFileManagementController
from brackets.tests.test_core_file_rename_controller import TestCoreFileRenameController
from brackets.tests.test_core_sync_yaml_controller import TestCoreSyncYamlController
from brackets.tests.test_core_startup import TestCoreStartup
from brackets.tests.test_core_tools_controller import TestCoreToolsController
from brackets.tests.test_core_vault_type_menu_visibility import TestCoreVaultTypeMenuVisibility
from brackets.tests.test_core_vault_selection import TestCoreVaultSelection
from brackets.tests.test_version_policy import TestVersionPolicy
from brackets.tests.test_event_log import TestEventLog
import unittest
from brackets.tests.test_core_menu_navigator import TestCoreMenuNavigator
from brackets.tests.test_relational_bitacora_renderer import TestRelationalBitacoraRenderer
from brackets.tests.test_core_daily_hub_controller import TestCoreDailyHubController
from brackets.tests.test_core_project_backlog_controller import TestCoreProjectBacklogController
from brackets.tests.test_core_note_crud_controller import TestCoreNoteCrudController
from brackets.tests.test_markdown_sync_service import TestMarkdownSyncService
from brackets.tests.test_main_sync_markdown import TestMainSyncMarkdown
from brackets.tests.test_topics_and_week_tasks import TestTopicsAndWeekTasks
from brackets.tests.test_recurring_tasks import TestRecurringTasks
from brackets.tests.test_file_rename_manager import test_file_rename_manager
from brackets.tests.test_global_search_replace import test_global_search_replace
from brackets.tests.test_manual_creation import test_manual_bitacora_generation, test_manual_weekly_creation
from brackets.tests.test_pomodoro_timer import TestPomodoroTimer
from brackets.tests.test_log4brackets import TestLog4Brackets
from brackets.tests.test_meeting_premoji import TestMeetingPremojiAndTaskTypes
from brackets.tests.test_calendar_intensive_and_closures import TestCalendarIntensiveAndClosures
from brackets.tests.test_sync_day_location_and_holidays import TestSyncDayLocationAndHolidays


def run_all_tests():
    """Ejecutar todos los tests y mostrar resumen."""
    print("\n" + "=" * 60)
    print("🚀 EJECUTANDO SUITE COMPLETA DE TESTS UNITARIOS")
    print("=" * 60)

    total_passed = 0
    total_failed = 0

    # Tests de consolidadores (existentes)
    print("\n" + "=" * 60)
    print("🧪 MÓDULO: Consolidadores")
    print("=" * 60)

    consolidator_tests = [
        ("Importaciones", test_imports),
        ("MonthConsolidator init", test_month_consolidator_init),
        ("YearConsolidator init", test_year_consolidator_init),
        ("Season emoji", test_season_emoji),
        ("List available months", test_list_available_months),
        ("List available years", test_list_available_years),
    ]

    for test_name, test_func in consolidator_tests:
        try:
            result = test_func()
            if result:
                total_passed += 1
            else:
                total_failed += 1
        except Exception as e:
            print(f"❌ {test_name}: {e}")
            total_failed += 1

    # Tests de helpers
    tester = TestHelpers()
    helpers_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de markdown
    tester = TestMarkdown()
    markdown_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de legacy_utils
    tester = TestLegacyUtils()
    legacy_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de content_parser
    tester = TestContentParser()
    parser_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de content_generator
    tester = TestContentGenerator()
    generator_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de file_finder
    tester = TestFileFinder()
    finder_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de weekly generator
    tester = TestWeeklyGenerator()
    weekly_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de monthly generator
    tester = TestMonthlyGenerator()
    monthly_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Smoke tests de scope de rutas (root vs vault local)
    tester = TestPathScopeSmoke()
    path_scope_smoke_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de alcance de vault para CLI
    tester = TestCliVaultScope()
    scope_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de dispatcher de acciones CLI
    tester = TestCoreCliActions()
    cli_actions_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de controlador de categorías
    tester = TestCoreCategoryManagementController()
    category_controller_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de controlador de configuración
    tester = TestCoreConfigurationController()
    config_controller_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de parser CLI
    tester = TestCoreCliParser()
    cli_parser_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de controlador de gestión de archivos
    tester = TestCoreFileManagementController()
    file_management_controller_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de controlador de rename/reemplazo
    tester = TestCoreFileRenameController()
    file_rename_controller_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de controlador de sincronización YAML
    tester = TestCoreSyncYamlController()
    sync_yaml_controller_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de orquestación de arranque
    tester = TestCoreStartup()
    startup_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de controlador de herramientas
    tester = TestCoreToolsController()
    tools_controller_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de selección de vault en arranque
    tester = TestCoreVaultSelection()
    vault_selection_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de contexto de menú por tipo de vault
    tester = TestCoreVaultTypeMenuVisibility()
    vault_type_menu_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de política de versionado
    tester = TestVersionPolicy()
    version_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de Event Log
    tester = TestEventLog()
    event_log_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de Motor Relacional YAML-First
    print("\n" + "=" * 60)
    print("🧪 MÓDULO: Motor Relacional YAML-First (BitacoraRenderer & Entities)")
    print("=" * 60)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestRelationalBitacoraRenderer)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    relational_passed = result.testsRun - len(result.failures) - len(result.errors)
    relational_failed = len(result.failures) + len(result.errors)
    total_passed += relational_passed
    total_failed += relational_failed

    # Tests de MenuNavigator (Navegación Unificada)
    try:
        nav_tester = TestCoreMenuNavigator()
        if nav_tester.run_all():
            total_passed += nav_tester.passed
        else:
            total_passed += nav_tester.passed
            total_failed += nav_tester.failed
    except Exception as e:
        print(f"❌ TestCoreMenuNavigator falló: {e}")
        total_failed += 1

    # Tests de DailyHubController
    print("\n" + "=" * 60)
    print("🧪 MÓDULO: DailyHubController (Hub Diario Interactivo)")
    print("=" * 60)
    hub_suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestCoreDailyHubController)
    hub_result = unittest.TextTestRunner(verbosity=1).run(hub_suite)
    hub_passed = hub_result.testsRun - len(hub_result.failures) - len(hub_result.errors)
    hub_failed = len(hub_result.failures) + len(hub_result.errors)
    total_passed += hub_passed
    total_failed += hub_failed

    # Tests de ProjectBacklogController
    print("\n" + "=" * 60)
    print("🧪 MÓDULO: ProjectBacklogController (Gestión de Proyectos, Backlog e Ideas)")
    print("=" * 60)
    pb_suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestCoreProjectBacklogController)
    pb_result = unittest.TextTestRunner(verbosity=1).run(pb_suite)
    pb_passed = pb_result.testsRun - len(pb_result.failures) - len(pb_result.errors)
    pb_failed = len(pb_result.failures) + len(pb_result.errors)
    total_passed += pb_passed
    total_failed += pb_failed

    # Tests de NoteCrudController
    print("\n" + "=" * 60)
    print("🧪 MÓDULO: NoteCrudController (Gestión CRUD de Notas)")
    print("=" * 60)
    nc_suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestCoreNoteCrudController)
    nc_result = unittest.TextTestRunner(verbosity=1).run(nc_suite)
    nc_passed = nc_result.testsRun - len(nc_result.failures) - len(nc_result.errors)
    nc_failed = len(nc_result.failures) + len(nc_result.errors)
    total_passed += nc_passed
    total_failed += nc_failed

    # Tests de MarkdownSyncService (Sincronización Bidireccional)
    print("\n" + "=" * 60)
    print("🧪 MÓDULO: MarkdownSyncService (Sincronización Bidireccional Markdown ➔ YAML)")
    print("=" * 60)
    sync_suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestMarkdownSyncService)
    sync_result = unittest.TextTestRunner(verbosity=1).run(sync_suite)
    sync_passed = sync_result.testsRun - len(sync_result.failures) - len(sync_result.errors)
    sync_failed = len(sync_result.failures) + len(sync_result.errors)
    total_passed += sync_passed
    total_failed += sync_failed

    # Tests de Sincronización Markdown desde Menú Principal
    print("\n" + "=" * 60)
    print("🧪 MÓDULO: MainSyncMarkdown (Sincronización desde Menú Principal: Específica y Total)")
    print("=" * 60)
    msync_suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestMainSyncMarkdown)
    msync_result = unittest.TextTestRunner(verbosity=1).run(msync_suite)
    msync_passed = msync_result.testsRun - len(msync_result.failures) - len(msync_result.errors)
    msync_failed = len(msync_result.failures) + len(msync_result.errors)
    total_passed += msync_passed
    total_failed += msync_failed

    # Tests de Topics, Week Tasks y Jerarquía Relacional
    print("\n" + "=" * 60)
    print("🧪 MÓDULO: Topics, Week Tasks y Jerarquía Relacional (Proyecto/Topic/Tarea/Nota)")
    print("=" * 60)
    tw_suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestTopicsAndWeekTasks)
    tw_result = unittest.TextTestRunner(verbosity=1).run(tw_suite)
    tw_passed = tw_result.testsRun - len(tw_result.failures) - len(tw_result.errors)
    tw_failed = len(tw_result.failures) + len(tw_result.errors)
    total_passed += tw_passed
    total_failed += tw_failed

    # Tests de Tareas y Reuniones Recurrentes
    print("\n" + "=" * 60)
    print("🧪 MÓDULO: Tareas y Reuniones Recurrentes (RecurringTask)")
    print("=" * 60)
    rec_suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestRecurringTasks)
    rec_result = unittest.TextTestRunner(verbosity=1).run(rec_suite)
    rec_passed = rec_result.testsRun - len(rec_result.failures) - len(rec_result.errors)
    rec_failed = len(rec_result.failures) + len(rec_result.errors)
    total_passed += rec_passed
    total_failed += rec_failed

    # Tests de Tipos de Tarea y Premojis
    print("\n" + "=" * 60)
    print("🧪 MÓDULO: Tipos de Tarea y Premojis (TaskTypeRegistry)")
    print("=" * 60)
    premoji_suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestMeetingPremojiAndTaskTypes)
    premoji_result = unittest.TextTestRunner(verbosity=1).run(premoji_suite)
    premoji_passed = premoji_result.testsRun - len(premoji_result.failures) - len(premoji_result.errors)
    premoji_failed = len(premoji_result.failures) + len(premoji_result.errors)
    total_passed += premoji_passed
    total_failed += premoji_failed

    # Tests de Jornada Intensiva y Cierres
    print("\n" + "=" * 60)
    print("🧪 MÓDULO: Jornadas Intensivas y Cierres de Sede (Calendar)")
    print("=" * 60)
    cal_suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestCalendarIntensiveAndClosures)
    cal_result = unittest.TextTestRunner(verbosity=1).run(cal_suite)
    cal_passed = cal_result.testsRun - len(cal_result.failures) - len(cal_result.errors)
    cal_failed = len(cal_result.failures) + len(cal_result.errors)
    total_passed += cal_passed
    total_failed += cal_failed

    # Tests de Sincronización de Ubicaciones y Vacaciones
    print("\n" + "=" * 60)
    print("🧪 MÓDULO: Sincronización de Ubicación y Días Libres (Preservación)")
    print("=" * 60)
    sync_loc_suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestSyncDayLocationAndHolidays)
    sync_loc_result = unittest.TextTestRunner(verbosity=1).run(sync_loc_suite)
    sync_loc_passed = sync_loc_result.testsRun - len(sync_loc_result.failures) - len(sync_loc_result.errors)
    sync_loc_failed = len(sync_loc_result.failures) + len(sync_loc_result.errors)
    total_passed += sync_loc_passed
    total_failed += sync_loc_failed

    # Tests de FileRenameManager (previamente excluidos)
    print("\n🧪 TESTS: managers/file_rename_manager.py")
    print("=" * 50)
    try:
        result = test_file_rename_manager()
        if result:
            total_passed += 1
        else:
            total_failed += 1
    except Exception as e:
        print(f"❌ test_file_rename_manager: {e}")
        total_failed += 1

    # Tests de Global Search Replace (previamente excluidos)
    print("\n🧪 TESTS: managers/global_search_replace.py")
    print("=" * 50)
    try:
        result = test_global_search_replace()
        if result:
            total_passed += 1
        else:
            total_failed += 1
    except Exception as e:
        print(f"❌ test_global_search_replace: {e}")
        total_failed += 1

    # Tests de Creación Manual (previamente excluidos)
    print("\n🧪 TESTS: generators/manual_creation.py")
    print("=" * 50)
    manual_tests = [
        ("Manual bitacora generation", test_manual_bitacora_generation),
        ("Manual weekly creation", test_manual_weekly_creation),
    ]
    for test_name, test_func in manual_tests:
        try:
            result = test_func()
            if result:
                total_passed += 1
            else:
                total_failed += 1
        except Exception as e:
            print(f"❌ {test_name}: {e}")
            total_failed += 1

    # Tests de Pomodoro Timer (previamente excluidos)
    tester = TestPomodoroTimer()
    pomodoro_passed = tester.run_all()
    total_passed += tester.passed
    total_failed += tester.failed

    # Tests de log4brackets (Event Logging clásico)
    print("\n" + "=" * 60)
    print("🧪 MÓDULO: log4brackets (Logging clásico de una sola línea por mes)")
    print("=" * 60)
    l4b_suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestLog4Brackets)
    l4b_result = unittest.TextTestRunner(verbosity=1).run(l4b_suite)
    l4b_passed = l4b_result.testsRun - len(l4b_result.failures) - len(l4b_result.errors)
    l4b_failed = len(l4b_result.failures) + len(l4b_result.errors)
    total_passed += l4b_passed
    total_failed += l4b_failed

    # Mostrar resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN FINAL DE TESTS")
    print("=" * 60)
    print(f"✅ Tests pasados: {total_passed}")
    print(f"❌ Tests fallidos: {total_failed}")
    print(f"📈 Total: {total_passed + total_failed}")

    if total_failed == 0:
        percentage = 100
        status = "🎉 TODOS LOS TESTS PASARON"
    else:
        percentage = (total_passed / (total_passed + total_failed)) * 100
        status = f"⚠️  {percentage:.1f}% de tests pasaron"

    print(f"📊 Cobertura: {percentage:.1f}%")
    print(status)
    print("=" * 60 + "\n")

    return total_failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
