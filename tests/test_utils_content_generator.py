#!/usr/bin/env python3
"""
Tests unitarios para ContentGenerator en utils/content_generator.py
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.content_generator import ContentGenerator


class TestContentGenerator:
    """Tests para la clase ContentGenerator."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def test_create_weekly_bitacora(self):
        """Test que create_weekly_bitacora genera contenido válido."""
        try:
            generator = ContentGenerator()

            # Preparar datos
            pending_tasks = ["Task 1", "Task 2"]
            week_num = 5
            weight = 75.5
            dates = [
                datetime(2026, 1, 29),  # Monday
                datetime(2026, 1, 30),  # Tuesday
                datetime(2026, 1, 31),  # Wednesday
                datetime(2026, 2, 1),   # Thursday
                datetime(2026, 2, 2),   # Friday
            ]
            daily_tasks = ["Daily task 1", "Daily task 2"]

            content = generator.create_weekly_bitacora(
                pending_tasks=pending_tasks,
                week_num=week_num,
                weight=weight,
                dates=dates,
                daily_tasks=daily_tasks
            )

            assert "Week 5" in content, "Número de semana no encontrado"
            assert "75.5" in content, "Peso no encontrado"
            assert "## ✅Topics" in content, "Sección Topics no encontrada"
            assert "## 📝Notes" in content, "Sección Notes no encontrada"
            assert "29" in content, "Día 29 no encontrado"

            print("✅ Test: create_weekly_bitacora genera contenido válido")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test create_weekly_bitacora falló: {e}")
            self.failed += 1

    def test_create_weekly_bitacora_no_weight(self):
        """Test que create_weekly_bitacora funciona sin peso."""
        try:
            generator = ContentGenerator()

            dates = [
                datetime(2026, 1, 29),
                datetime(2026, 1, 30),
                datetime(2026, 1, 31),
                datetime(2026, 2, 1),
                datetime(2026, 2, 2),
            ]

            content = generator.create_weekly_bitacora(
                pending_tasks=[],
                week_num=1,
                weight=None,  # Sin peso
                dates=dates,
                daily_tasks=[]
            )

            assert "Week 1" in content, "Semana debería generarse sin peso"
            assert "📝Notes" in content, "Debería tener sección de notas"

            print("✅ Test: create_weekly_bitacora funciona sin peso")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test create_weekly_bitacora_no_weight falló: {e}")
            self.failed += 1

    def test_generate_weekly_content_manual(self):
        """Test que generate_weekly_content_manual genera correctamente."""
        try:
            generator = ContentGenerator()

            work_locations = {
                29: "🏠",
                30: "🚗",
                31: "🚗",
                1: "🏠",
                2: "🚗"
            }

            content = generator.generate_weekly_content_manual(
                year=2026,
                month=1,
                week=5,
                weight=75.0,
                work_locations=work_locations
            )

            assert content is not None, "Debería generar contenido"
            assert "Week 5" in content, "Número de semana no encontrado"
            assert "75" in content, "Peso no encontrado"
            assert "🏠" in content, "Emoji de casa no encontrado"
            assert "🚗" in content, "Emoji de oficina no encontrado"

            print("✅ Test: generate_weekly_content_manual genera correctamente")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test generate_weekly_content_manual falló: {e}")
            self.failed += 1

    def test_create_monthly_topics(self):
        """Test que create_monthly_topics genera correctamente."""
        try:
            generator = ContentGenerator()

            base_content = """# Topics
- [ ] Task 1
- [x] Task 2
- [ ] Task 3
"""

            content = generator.create_monthly_topics(
                month=1,
                year=2026,
                base_content=base_content
            )

            # Verificar que es una cadena y contiene contenido
            assert isinstance(content, str), "Debería retornar string"
            assert len(content) > 0, "El contenido no debería estar vacío"
            assert "# January Topics ❄️" in content, "Formato de título mensual no coincide"
            # Las tareas completadas [x] deberían haber sido removidas
            assert "[x]" not in content, "Tareas completadas deberían removerse"
            assert "[ ]" in content, "Tareas pendientes deberían mantenerse"

            print("✅ Test: create_monthly_topics genera correctamente")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test create_monthly_topics falló: {e}")
            self.failed += 1

    def run_all(self):
        """Ejecutar todos los tests."""
        print("\n🧪 TESTS: utils/content_generator.py")
        print("=" * 50)

        self.test_create_weekly_bitacora()
        self.test_create_weekly_bitacora_no_weight()
        self.test_generate_weekly_content_manual()
        self.test_create_monthly_topics()

        print(f"\n📊 Resultado: ✅ {self.passed} | ❌ {self.failed}")
        return self.failed == 0


if __name__ == "__main__":
    tester = TestContentGenerator()
    success = tester.run_all()
    sys.exit(0 if success else 1)
