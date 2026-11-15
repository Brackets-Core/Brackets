#!/usr/bin/env python3
"""Smoke tests de rutas de escritura (root vs vault local)."""

import os
import sys
import tempfile
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generators.weekly as weekly_module
import generators.monthly as monthly_module
from generators.weekly import WeeklyGenerator
from generators.monthly import MonthlyGenerator


class TestPathScopeSmoke:
    """Valida que la escritura siempre caiga en el vault y no en workspace root."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def _run_in_cwd(self, cwd: str, fn):
        previous = os.getcwd()
        try:
            os.chdir(cwd)
            return fn()
        finally:
            os.chdir(previous)

    def _prepare_weekly_generator(self, vault_dir: str) -> WeeklyGenerator:
        generator = WeeklyGenerator(directory=vault_dir)
        generator.finder = weekly_module.FileFinder(vault_dir)
        generator.generator.create_weekly_bitacora = lambda **_kwargs: "new-content"
        generator.generator.create_week_summary = lambda **_kwargs: ""
        generator._calculate_next_week_dates_iso = lambda _y, _w: [
            datetime(2026, 5, 25),
            datetime(2026, 5, 26),
            datetime(2026, 5, 27),
            datetime(2026, 5, 28),
            datetime(2026, 5, 29),
        ]
        return generator

    def test_weekly_writes_in_vault_from_root_and_local(self):
        """Semanal debe escribir en vault al ejecutar desde root y desde vault local."""
        try:
            with tempfile.TemporaryDirectory() as tmp:
                workspace_root = os.path.join(tmp, "workspace")
                vault = os.path.join(workspace_root, "VaultA")
                os.makedirs(vault, exist_ok=True)

                recent_file = os.path.join(vault, "[2026][05]Week21.md")
                with open(recent_file, "w", encoding="utf-8") as f:
                    f.write("# Semana 21\n")

                expected = os.path.join(vault, "[2026][05]Week22.md")
                root_mirror = os.path.join(workspace_root, "[2026][05]Week22.md")

                def _run_from_root():
                    generator = self._prepare_weekly_generator(vault)
                    return generator.create_next_weekly_bitacora(ask_for_weight=False)

                result = self._run_in_cwd(workspace_root, _run_from_root)
                assert result is True, "Semanal desde root debe completarse con éxito"
                assert os.path.exists(expected), "Semanal desde root debe crear en vault"
                assert not os.path.exists(root_mirror), "Semanal desde root no debe crear espejo en workspace root"

                os.remove(expected)

                def _run_from_local_vault():
                    generator = self._prepare_weekly_generator(vault)
                    return generator.create_next_weekly_bitacora(ask_for_weight=False)

                result = self._run_in_cwd(vault, _run_from_local_vault)
                assert result is True, "Semanal desde vault local debe completarse con éxito"
                assert os.path.exists(expected), "Semanal desde vault local debe crear en vault"
                assert not os.path.exists(root_mirror), "Semanal desde vault local no debe crear espejo en root"

            print("✅ Test smoke: semanal respeta vault desde root y local")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test smoke semanal falló: {e}")
            self.failed += 1

    def test_monthly_writes_in_vault_from_root_and_local(self):
        """Mensual debe escribir en vault al ejecutar desde root y desde vault local."""
        try:
            with tempfile.TemporaryDirectory() as tmp:
                workspace_root = os.path.join(tmp, "workspace")
                vault = os.path.join(workspace_root, "VaultA")
                os.makedirs(vault, exist_ok=True)

                recent_file = os.path.join(vault, "[2026][05]MonthTopics.md")
                with open(recent_file, "w", encoding="utf-8") as f:
                    f.write("# May Topics\n\n- [ ] Task\n")

                expected = os.path.join(vault, "[2026][06]MonthTopics.md")
                root_mirror = os.path.join(workspace_root, "[2026][06]MonthTopics.md")

                def _run_from_root():
                    generator = MonthlyGenerator(directory=vault)
                    generator.finder = monthly_module.FileFinder(vault)
                    return generator.create_next_monthly_topics()

                result = self._run_in_cwd(workspace_root, _run_from_root)
                assert result is True, "Mensual desde root debe completarse con éxito"
                assert os.path.exists(expected), "Mensual desde root debe crear en vault"
                assert not os.path.exists(root_mirror), "Mensual desde root no debe crear espejo en workspace root"

                os.remove(expected)

                def _run_from_local_vault():
                    generator = MonthlyGenerator(directory=vault)
                    generator.finder = monthly_module.FileFinder(vault)
                    return generator.create_next_monthly_topics()

                result = self._run_in_cwd(vault, _run_from_local_vault)
                assert result is True, "Mensual desde vault local debe completarse con éxito"
                assert os.path.exists(expected), "Mensual desde vault local debe crear en vault"
                assert not os.path.exists(root_mirror), "Mensual desde vault local no debe crear espejo en root"

            print("✅ Test smoke: mensual respeta vault desde root y local")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test smoke mensual falló: {e}")
            self.failed += 1

    def run_all(self):
        """Ejecuta todos los tests smoke."""
        print("\n🧪 TESTS: path scope smoke")
        print("=" * 50)

        self.test_weekly_writes_in_vault_from_root_and_local()
        self.test_monthly_writes_in_vault_from_root_and_local()

        print(f"\n📊 Resultado: ✅ {self.passed} | ❌ {self.failed}")
        return self.failed == 0


if __name__ == "__main__":
    tester = TestPathScopeSmoke()
    success = tester.run_all()
    sys.exit(0 if success else 1)
