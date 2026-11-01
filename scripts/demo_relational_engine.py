#!/usr/bin/env python3
"""
Demostración de la Arquitectura Relacional YAML-First de Brackets con Mock Data.
"""

import os
import sys

# Agregar path
brackets_dir = os.path.dirname(os.path.abspath(__file__))
if brackets_dir not in sys.path:
    sys.path.insert(0, brackets_dir)

from brackets.managers.entity_manager import EntityManager
from brackets.generators.bitacora_renderer import BitacoraRenderer


def run_demo():
    print("=" * 65)
    print("🚀 DEMO: ARQUITECTURA RELACIONAL YAML-FIRST DE BRACKETS")
    print("=" * 65)

    mock_dir = os.path.join(brackets_dir, "data", "mock")
    manager = EntityManager(mock_dir)

    print(f"📦 Tablas cargadas desde: {mock_dir}")
    print(f"  • Tareas en tabla: {len(manager.tasks)}")
    print(f"  • Definiciones en tabla: {len(manager.definitions)}")
    print(f"  • Notas en tabla: {len(manager.notes)}")

    # 1. Cargar semana 34
    week = manager.load_week(2026, 34)
    print(f"\n🗓️ Semana cargada: 2026 - Semana {week.week_number} (Mes {week.month})")

    # 2. Renderizar Markdown inicial
    print("\n" + "-" * 65)
    print("📄 1. VISTA MARKDOWN INICIAL GENERADA DESDE YAML:")
    print("-" * 65)
    initial_md = BitacoraRenderer.render_week(week, manager)
    print(initial_md)

    # 3. Modificación: Completar tarea TSK-0030
    print("\n" + "=" * 65)
    print("⚡ 2. MODIFICANDO DATOS EN TABLA YAML...")
    print("=" * 65)
    print("  👉 Completando tarea 'TSK-0030' (Empezar a preparar propuesta)...")
    manager.toggle_task("TSK-0030")

    # 4. Crear nueva tarea con ticket Jira
    print("  👉 Creando nueva tarea con ticket Jira 'ATLM-99999' para el día 21...")
    jira_def = manager.ensure_jira_definition("ATLM-99999")
    new_task = manager.create_task(
        title=f"Validar flujo E2E con Copilot {jira_def.id}",
        year=2026,
        week_num=34,
        day_number=21,
        definition_ids=[jira_def.id]
    )

    # 5. Re-renderizar Markdown
    print("\n" + "-" * 65)
    print("📄 3. VISTA MARKDOWN REGENERADA TRAS LAS ACTUALIZACIONES:")
    print("-" * 65)
    updated_md = BitacoraRenderer.render_week(week, manager)
    print(updated_md)

    print("=" * 65)
    print("✅ Demostración completada con éxito.")
    print("=" * 65)


if __name__ == "__main__":
    run_demo()
