#!/usr/bin/env python3
"""
Pruebas de descubrimiento flexible de vaults:
- Vaults en la raíz del workspace (retrocompatibilidad).
- Vaults agrupados en una subcarpeta 'vaults/'.
- Vaults externos fuera del workspace registrados en 'vaults.yaml'.
- Auto-detección del core desde run_brackets.py en cualquier ubicación.
- Resolución de vault mediante flag --vault y variable de entorno BRACKETS_VAULT.
"""

import os
import shutil
import tempfile
import unittest

from brackets.managers.vault_manager import VaultManager
from brackets.core.vault_selection import select_vault_directory


class TestVaultDiscoveryAndNesting(unittest.TestCase):
    """Pruebas para VaultManager y la ubicación flexible de vaults."""

    def setUp(self):
        self.temp_workspace = tempfile.mkdtemp(prefix="brackets_discovery_test_")

        # 1. Vault en la raíz
        self.root_vault = os.path.join(self.temp_workspace, "RootVault")
        os.makedirs(os.path.join(self.root_vault, "data"), exist_ok=True)
        with open(os.path.join(self.root_vault, "data", "config.yaml"), "w", encoding="utf-8") as f:
            f.write("vault_type: work\ndescription: Vault en raiz\n")

        # 2. Carpeta 'vaults/' con un vault anidado
        self.vaults_dir = os.path.join(self.temp_workspace, "vaults")
        self.nested_vault = os.path.join(self.vaults_dir, "NestedVault")
        os.makedirs(os.path.join(self.nested_vault, "data"), exist_ok=True)
        with open(os.path.join(self.nested_vault, "data", "config.yaml"), "w", encoding="utf-8") as f:
            f.write("vault_type: personal\ndescription: Vault en subcarpeta vaults\n")

        # 3. Vault externo (fuera del workspace)
        self.temp_external_dir = tempfile.mkdtemp(prefix="brackets_external_vault_")
        self.external_vault = os.path.join(self.temp_external_dir, "ExternalVault")
        os.makedirs(os.path.join(self.external_vault, "data"), exist_ok=True)
        with open(os.path.join(self.external_vault, "data", "config.yaml"), "w", encoding="utf-8") as f:
            f.write("vault_type: work\ndescription: Vault externo fuera del workspace\n")

        # Registrar el vault externo en vaults.yaml
        with open(os.path.join(self.temp_workspace, "vaults.yaml"), "w", encoding="utf-8") as f:
            f.write(f"external_vaults:\n  - '{self.external_vault.replace(os.sep, '/')}'\n")

    def tearDown(self):
        shutil.rmtree(self.temp_workspace, ignore_errors=True)
        shutil.rmtree(self.temp_external_dir, ignore_errors=True)

    def test_discover_root_nested_and_external_vaults(self):
        """Verifica que VaultManager descubra vaults en la raíz, en vaults/ y externos."""
        vm = VaultManager(self.temp_workspace)
        vault_names = [v["name"] for v in vm.vaults]

        self.assertIn("RootVault", vault_names)
        self.assertIn("NestedVault", vault_names)
        self.assertIn("ExternalVault", vault_names)

        nested = next(v for v in vm.vaults if v["name"] == "NestedVault")
        self.assertEqual(os.path.abspath(nested["path"]), os.path.abspath(self.nested_vault))

        external = next(v for v in vm.vaults if v["name"] == "ExternalVault")
        self.assertEqual(os.path.abspath(external["path"]), os.path.abspath(self.external_vault))

    def test_resolve_vault_path_by_name_and_env(self):
        """Verifica que resolve_vault_path resuelva vaults por nombre tanto en raíz, subcarpeta o externos."""
        vm = VaultManager(self.temp_workspace)

        self.assertEqual(vm.resolve_vault_path("RootVault"), os.path.abspath(self.root_vault))
        self.assertEqual(vm.resolve_vault_path("NestedVault"), os.path.abspath(self.nested_vault))
        self.assertEqual(vm.resolve_vault_path("ExternalVault"), os.path.abspath(self.external_vault))
        self.assertEqual(vm.resolve_vault_path(self.nested_vault), os.path.abspath(self.nested_vault))

    def test_select_vault_directory_with_vault_flag_or_env(self):
        """Verifica que select_vault_directory soporte nombres y BRACKETS_VAULT."""
        # 1. Pasando nombre en directory_arg
        resolved, code = select_vault_directory(
            directory_arg="NestedVault",
            has_flags=False,
            current_dir=self.temp_workspace,
        )
        self.assertIsNone(code)
        self.assertEqual(os.path.abspath(resolved), os.path.abspath(self.nested_vault))

        # 2. Pasando por variable de entorno BRACKETS_VAULT
        os.environ["BRACKETS_VAULT"] = "ExternalVault"
        try:
            resolved_env, code_env = select_vault_directory(
                directory_arg=None,
                has_flags=False,
                current_dir=self.temp_workspace,
            )
            self.assertIsNone(code_env)
            self.assertEqual(os.path.abspath(resolved_env), os.path.abspath(self.external_vault))
        finally:
            del os.environ["BRACKETS_VAULT"]

    def test_run_brackets_dynamic_resolution(self):
        """Verifica que la lógica de búsqueda dinámica encuentre el core desde un vault anidado."""
        fake_ws = os.path.join(self.temp_workspace, "fake_ws")
        fake_brackets = os.path.join(fake_ws, "brackets", "brackets")
        os.makedirs(fake_brackets, exist_ok=True)
        with open(os.path.join(fake_brackets, "main.py"), "w", encoding="utf-8") as f:
            f.write("# dummy\n")

        fake_vault = os.path.join(fake_ws, "vaults", "TestVault")
        os.makedirs(fake_vault, exist_ok=True)

        cur = os.path.abspath(fake_vault)
        found_core = None
        while cur and os.path.dirname(cur) != cur:
            for cand in [
                os.path.join(cur, "brackets"),
                os.path.join(os.path.dirname(cur), "brackets")
            ]:
                if os.path.exists(os.path.join(cand, "brackets", "main.py")):
                    found_core = os.path.abspath(cand)
                    break
            if found_core:
                break
            cur = os.path.dirname(cur)

        expected_core = os.path.abspath(os.path.join(fake_ws, "brackets"))
        self.assertEqual(found_core, expected_core)


if __name__ == "__main__":
    unittest.main()
