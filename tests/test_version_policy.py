#!/usr/bin/env python3
"""Tests para política unificada de versionado."""

import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import __init__ as brackets_pkg
import config
from version import VERSION


class TestVersionPolicy:
    """Valida que todos los puntos usen una única versión."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def test_package_and_config_share_same_version(self):
        try:
            assert brackets_pkg.__version__ == VERSION, (
                f"__version__ inconsistente: {brackets_pkg.__version__} != {VERSION}"
            )
            assert config.VERSION == VERSION, (
                f"config.VERSION inconsistente: {config.VERSION} != {VERSION}"
            )

            print("✅ Test: package/config usan la misma versión")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test versionado unificado falló: {e}")
            self.failed += 1

    def run_all(self):
        print("\n🧪 TESTS: version policy")
        print("=" * 50)

        self.test_package_and_config_share_same_version()

        print(f"\n📊 Resultado: ✅ {self.passed} | ❌ {self.failed}")
        return self.failed == 0


if __name__ == "__main__":
    tester = TestVersionPolicy()
    success = tester.run_all()
    sys.exit(0 if success else 1)
