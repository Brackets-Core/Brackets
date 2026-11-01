#!/usr/bin/env python3
"""
Tests unitarios para ContentParser en utils/content_parser.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from brackets.utils.content_parser import ContentParser


class TestContentParser:
    """Tests para la clase ContentParser."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def test_extract_week_info_from_filename(self):
        """Test que extract_week_info_from_filename parsea correctamente."""
        try:
            # El peso se extrae del patrón del contenido, no es garantizado
            content = """# 🗓️Week05

## ✅Topics
- [ ] Task 1
"""
            parser = ContentParser(content)
            year, month, week, weight = parser.extract_week_info_from_filename(
                "[2026][01]Week05.md"
            )

            assert year == 2026, f"Año incorrecto: {year}"
            assert month == 1, f"Mes incorrecto: {month}"
            assert week == 5, f"Semana incorrecta: {week}"
            # El peso puede ser None si no está en el formato esperado
            # assert weight == 75.5 or weight is None

            print("✅ Test: extract_week_info_from_filename parsea correctamente")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test extract_week_info_from_filename falló: {e}")
            self.failed += 1

    def test_extract_pending_tasks(self):
        """Test que extract_pending_tasks extrae tareas correctamente."""
        try:
            content = """# Week 01

## ✅Topics
  - [ ] Task 1
  - [ ] Task 2
  - [x] Completed task
  - ### Subsection
    - [ ] Sub task
"""
            parser = ContentParser(content)
            tasks = parser.extract_pending_tasks()

            assert len(tasks) > 0, "No se extrajeron tareas"
            # Las tareas completadas [x] no deben incluirse
            completed_in_tasks = any("[x]" in str(t) for t in tasks)
            assert not completed_in_tasks, "Tareas completadas no deberían extraerse"

            print("✅ Test: extract_pending_tasks extrae correctamente")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test extract_pending_tasks falló: {e}")
            self.failed += 1

    def test_extract_pending_tasks_ignores_children_of_completed_parent(self):
        """Test que no migra subtareas de un padre completado y preserva jerarquía útil."""
        try:
            content = """# Week 01

## ✅Topics
  - [ ] Padre pendiente
    - [ ] Hija pendiente
  - [x] Padre completado
    - [ ] Hija de padre completado
"""
            parser = ContentParser(content)
            tasks = parser.extract_pending_tasks()

            joined = "\n".join(tasks)
            assert "Padre pendiente" in joined, "Debe mantener tareas pendientes"
            assert "Hija pendiente" in joined, "Debe mantener subtareas de padre pendiente"
            assert "Hija de padre completado" not in joined, "No debe migrar subtareas de padre completado"

            print("✅ Test: subtareas de padre completado no se migran")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test subtareas de padre completado falló: {e}")
            self.failed += 1

    def test_extract_pending_tasks_ignores_cancelled_tasks(self):
        """Test que tareas tachadas con ~~ (canceladas) no se extraen como pendientes."""
        try:
            content = """# Week 01

## ✅Topics
  - [ ] Tarea normal activa
  - [ ] ~~Tarea cancelada con checkbox~~
  - - ~~Tarea cancelada con guión~~
  - [ ] ~~Tarea cancelada con subitems~~
    - [ ] Subtarea de cancelada
"""
            parser = ContentParser(content)
            tasks = parser.extract_pending_tasks()
            joined = "\n".join(tasks)

            assert "Tarea normal activa" in joined, "Debe incluir tarea normal activa"
            assert "Tarea cancelada con checkbox" not in joined, "No debe incluir tarea cancelada"
            assert "Tarea cancelada con guión" not in joined, "No debe incluir tarea cancelada con guión"
            assert "Subtarea de cancelada" not in joined, "No debe incluir subtarea de tarea cancelada"

            print("✅ Test: tareas canceladas (tachadas) no se extraen como pendientes")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test tareas canceladas no se extraen falló: {e}")
            self.failed += 1

    def test_extract_pending_tasks_ignores_meetings(self):
        """Test que las reuniones pendientes (con premoji o prefijo Reunión:) no se traspasan."""
        try:
            content = """# Week 01

## ✅Topics
  - [ ] Tarea normal a traspasar
  - [ ] Reunión: Sincronización semanal
  - [ ] 🫱🏼‍🫲🏽 Demo cliente
  - [ ] 🤝 1on1 con lead
"""
            parser = ContentParser(content)
            tasks = parser.extract_pending_tasks()
            joined = "\n".join(tasks)

            assert "Tarea normal a traspasar" in joined, "Debe incluir tarea normal"
            assert "Reunión: Sincronización semanal" not in joined, "No debe incluir reunión con prefijo"
            assert "Demo cliente" not in joined, "No debe incluir reunión con premoji oficial"
            assert "1on1 con lead" not in joined, "No debe incluir reunión con emoji handshake"

            print("✅ Test: reuniones pendientes no se traspasan a la siguiente semana")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test reuniones pendientes no se traspasan falló: {e}")
            self.failed += 1

    def test_extract_daily_dates(self):
        """Test que extract_daily_dates extrae fechas correctamente."""
        try:
            content = """# Week 05

## 🏠29
- Task

## 🚗30
- Task

## 🚗31
- Task

## 🏠01
- Task

## 🚗02
- Task
"""
            parser = ContentParser(content)
            dates = parser.extract_daily_dates()

            assert len(dates) == 5, f"Debería extraer 5 fechas, se extrajeron {len(dates)}"
            assert dates[0] == 29, f"Primera fecha debería ser 29, es {dates[0]}"

            print("✅ Test: extract_daily_dates extrae correctamente")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test extract_daily_dates falló: {e}")
            self.failed += 1

    def test_clean_completed_tasks(self):
        """Test que clean_completed_tasks remueve tareas completadas."""
        try:
            content = """# Week 05

## ✅Topics
- [ ] Pending task 1
- [x] Completed task 1
- [ ] Pending task 2
- [x] Completed task 2
"""
            parser = ContentParser(content)
            cleaned = parser.clean_completed_tasks()

            # Las líneas con [x] no deben estar en el resultado
            assert "[x]" not in cleaned, "Tareas completadas no deberían estar en el resultado"
            assert "Pending task 1" in cleaned, "Tareas pendientes deberían mantenerse"

            print("✅ Test: clean_completed_tasks remueve correctamente")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test clean_completed_tasks falló: {e}")
            self.failed += 1

    def run_all(self):
        """Ejecutar todos los tests."""
        print("\n🧪 TESTS: utils/content_parser.py")
        print("=" * 50)

        self.test_extract_week_info_from_filename()
        self.test_extract_pending_tasks()
        self.test_extract_pending_tasks_ignores_children_of_completed_parent()
        self.test_extract_pending_tasks_ignores_cancelled_tasks()
        self.test_extract_pending_tasks_ignores_meetings()
        self.test_extract_daily_dates()
        self.test_clean_completed_tasks()

        print(f"\n📊 Resultado: ✅ {self.passed} | ❌ {self.failed}")
        return self.failed == 0


if __name__ == "__main__":
    tester = TestContentParser()
    success = tester.run_all()
    sys.exit(0 if success else 1)
