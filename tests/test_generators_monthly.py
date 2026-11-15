#!/usr/bin/env python3
"""
Tests unitarios para MonthlyGenerator en generators/monthly.py
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generators.monthly as monthly_module
from generators.monthly import MonthlyGenerator


class TestMonthlyGenerator:
    """Tests para la clase MonthlyGenerator."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def test_create_next_monthly_uses_generator_directory(self):
        """Valida que la creación automática mensual escriba dentro del vault."""
        try:
            with tempfile.TemporaryDirectory() as tmp:
                generator = MonthlyGenerator(directory=tmp)
                generator.finder = monthly_module.FileFinder(tmp)

                recent_file = os.path.join(tmp, "[2026][05]MonthTopics.md")
                with open(recent_file, "w", encoding="utf-8") as f:
                    f.write("# May Topics\n\n- [ ] Task\n")

                result = generator.create_next_monthly_topics()

                expected = os.path.join(tmp, "[2026][06]MonthTopics.md")
                assert result is True, "La creación automática mensual debería completar con éxito"
                assert os.path.exists(expected), (
                    f"Debe crear el archivo mensual dentro del vault seleccionado. No existe: {expected}"
                )

            print("✅ Test: creación automática mensual escribe en directorio del vault")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test create_next_monthly_uses_generator_directory falló: {e}")
            self.failed += 1

    def run_all(self):
        """Ejecutar todos los tests."""
        print("\n🧪 TESTS: generators/monthly.py")
        print("=" * 50)

        self.test_create_next_monthly_uses_generator_directory()

        print(f"\n📊 Resultado: ✅ {self.passed} | ❌ {self.failed}")
        return self.failed == 0


if __name__ == "__main__":
    tester = TestMonthlyGenerator()
    success = tester.run_all()
    sys.exit(0 if success else 1)
