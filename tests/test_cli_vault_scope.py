#!/usr/bin/env python3
"""Tests para resolución de contexto de vault en CLI."""

import os
import sys
import tempfile

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.workspace_context import resolve_workspace_context


class TestCliVaultScope:
    """Valida detección de ejecución local vs workspace root."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def _assert(self, condition: bool, message: str):
        if not condition:
            raise AssertionError(message)

    def test_detects_workspace_root(self):
        """Debe detectar root cuando existe brackets/brackets."""
        try:
            with tempfile.TemporaryDirectory() as tmp:
                os.makedirs(os.path.join(tmp, "brackets", "brackets"), exist_ok=True)

                root, local_only = resolve_workspace_context(tmp)

                self._assert(os.path.abspath(root) == os.path.abspath(tmp), "Root incorrecto")
                self._assert(local_only is False, "No debe marcar local_only en workspace root")

            print("✅ Test: detecta workspace root correctamente")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test workspace root falló: {e}")
            self.failed += 1

    def test_detects_local_vault(self):
        """Debe detectar vault local y evitar modo global."""
        try:
            with tempfile.TemporaryDirectory() as tmp:
                os.makedirs(os.path.join(tmp, "brackets", "brackets"), exist_ok=True)
                vault = os.path.join(tmp, "MyVault")
                os.makedirs(os.path.join(vault, "data"), exist_ok=True)
                with open(os.path.join(vault, "data", "config.yaml"), "w", encoding="utf-8") as f:
                    f.write("version: '1.0.0'\n")

                root, local_only = resolve_workspace_context(vault)

                self._assert(os.path.abspath(root) == os.path.abspath(vault), "Vault local incorrecto")
                self._assert(local_only is True, "Debe marcar local_only en vault local")

            print("✅ Test: detecta vault local correctamente")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test vault local falló: {e}")
            self.failed += 1

    def test_detects_nested_path_inside_vault(self):
        """Si se ejecuta desde subcarpeta del vault, debe resolver al vault root."""
        try:
            with tempfile.TemporaryDirectory() as tmp:
                os.makedirs(os.path.join(tmp, "brackets", "brackets"), exist_ok=True)
                vault = os.path.join(tmp, "MyVault")
                nested = os.path.join(vault, "notes", "today")
                os.makedirs(os.path.join(vault, "data"), exist_ok=True)
                os.makedirs(nested, exist_ok=True)
                with open(os.path.join(vault, "data", "config.yaml"), "w", encoding="utf-8") as f:
                    f.write("version: '1.0.0'\n")

                root, local_only = resolve_workspace_context(nested)

                self._assert(os.path.abspath(root) == os.path.abspath(vault), "Debe resolver al vault root")
                self._assert(local_only is True, "Debe mantener local_only desde subcarpeta")

            print("✅ Test: detecta subcarpeta dentro de vault")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test subcarpeta de vault falló: {e}")
            self.failed += 1

    def run_all(self):
        """Ejecuta todos los tests."""
        print("\n🧪 TESTS: cli vault scope")
        print("=" * 50)

        self.test_detects_workspace_root()
        self.test_detects_local_vault()
        self.test_detects_nested_path_inside_vault()

        print(f"\n📊 Resultado: ✅ {self.passed} | ❌ {self.failed}")
        return self.failed == 0


if __name__ == "__main__":
    tester = TestCliVaultScope()
    success = tester.run_all()
    sys.exit(0 if success else 1)
