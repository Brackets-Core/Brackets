#!/usr/bin/env python3
"""Tests para selección de vault extraída de main.py."""

import os
import sys
import tempfile

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.vault_selection import select_vault_directory


class _FakeVaultManager:
    def __init__(self, _workspace_root: str, selections):
        self.selections = list(selections)
        self.refresh_called = False

    def show_vault_menu(self):
        return self.selections.pop(0) if self.selections else None

    def refresh_vaults(self):
        self.refresh_called = True


class TestCoreVaultSelection:
    """Valida orquestación de selección de vault en arranque CLI."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def _assert(self, condition: bool, message: str):
        if not condition:
            raise AssertionError(message)

    def test_directory_arg_passthrough(self):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                os.makedirs(os.path.join(tmp, "data"), exist_ok=True)
                with open(os.path.join(tmp, "data", "config.yaml"), "w", encoding="utf-8") as f:
                    f.write("vault_name: test\n")

                vault, code = select_vault_directory(
                    directory_arg=tmp,
                    has_flags=False,
                )
            self._assert(vault is not None, "Debe aceptar --directory válido")
            self._assert(os.path.abspath(vault) == os.path.abspath(tmp), "Debe respetar --directory")
            self._assert(code is None, "No debe salir temprano")

            print("✅ Test: respeta directory_arg válido")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test directory_arg_passthrough falló: {e}")
            self.failed += 1

    def test_directory_arg_invalid_requires_config(self):
        try:
            vault, code = select_vault_directory(
                directory_arg="/tmp/not-a-vault",
                has_flags=False,
            )
            self._assert(vault is None, "No debe aceptar --directory inválido")
            self._assert(code == 2, "Debe devolver código de error de uso")

            print("✅ Test: --directory inválido requiere data/config.yaml")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test directory_arg_invalid_requires_config falló: {e}")
            self.failed += 1

    def test_flags_in_local_context_use_local_vault(self):
        try:
            vault, code = select_vault_directory(
                directory_arg=None,
                has_flags=True,
                current_dir="/tmp/local-vault",
                resolve_workspace_context_fn=lambda _cwd: ("/tmp/local-vault", True),
            )
            self._assert(vault == "/tmp/local-vault", "Con flags en contexto local debe usar vault local")
            self._assert(code is None, "No debe salir temprano")

            print("✅ Test: con flags usa vault local")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test flags_in_local_context_use_local_vault falló: {e}")
            self.failed += 1

    def test_flags_in_non_local_context_require_directory(self):
        try:
            vault, code = select_vault_directory(
                directory_arg=None,
                has_flags=True,
                current_dir="/ws",
                resolve_workspace_context_fn=lambda _cwd: ("/ws", False),
            )
            self._assert(vault is None, "Sin --directory fuera de vault local no debe continuar")
            self._assert(code == 2, "Debe devolver código de error de uso")

            print("✅ Test: con flags fuera de vault local exige --directory")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test flags_in_non_local_context_require_directory falló: {e}")
            self.failed += 1

    def test_local_context_short_circuit(self):
        try:
            vault, code = select_vault_directory(
                directory_arg=None,
                has_flags=False,
                current_dir="/tmp",
                resolve_workspace_context_fn=lambda _cwd: ("/tmp/local-vault", True),
            )
            self._assert(vault == "/tmp/local-vault", "Debe usar vault local detectado")
            self._assert(code is None, "No debe salir temprano")

            print("✅ Test: contexto local evita selector global")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test local_context_short_circuit falló: {e}")
            self.failed += 1

    def test_global_selector_exit(self):
        try:
            manager = _FakeVaultManager("/ws", [None])
            vault, code = select_vault_directory(
                directory_arg=None,
                has_flags=False,
                current_dir="/ws",
                resolve_workspace_context_fn=lambda _cwd: ("/ws", False),
                vault_manager_factory=lambda _root: manager,
                create_new_vault_fn=lambda _root: None,
            )
            self._assert(vault is None, "Al salir no debe devolver vault")
            self._assert(code == 0, "Salir del selector debe devolver código 0")

            print("✅ Test: salida del selector global")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test global_selector_exit falló: {e}")
            self.failed += 1

    def test_global_selector_create_new_success(self):
        try:
            manager = _FakeVaultManager("/ws", ["CREATE_NEW"])
            vault, code = select_vault_directory(
                directory_arg=None,
                has_flags=False,
                current_dir="/ws",
                resolve_workspace_context_fn=lambda _cwd: ("/ws", False),
                vault_manager_factory=lambda _root: manager,
                create_new_vault_fn=lambda _root: "/ws/NewVault",
            )
            self._assert(vault == "/ws/NewVault", "Debe devolver vault recién creado")
            self._assert(code is None, "No debe salir temprano tras crear vault")
            self._assert(manager.refresh_called is True, "Debe refrescar vaults tras creación")

            print("✅ Test: create_new exitoso refresca y retorna vault")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test global_selector_create_new_success falló: {e}")
            self.failed += 1

    def test_global_selector_create_new_cancel_then_pick_existing(self):
        try:
            manager = _FakeVaultManager("/ws", ["CREATE_NEW", "/ws/ExistingVault"])
            vault, code = select_vault_directory(
                directory_arg=None,
                has_flags=False,
                current_dir="/ws",
                resolve_workspace_context_fn=lambda _cwd: ("/ws", False),
                vault_manager_factory=lambda _root: manager,
                create_new_vault_fn=lambda _root: None,
            )
            self._assert(vault == "/ws/ExistingVault", "Debe permitir volver y seleccionar vault existente")
            self._assert(code is None, "No debe salir temprano")
            self._assert(manager.refresh_called is False, "No debe refrescar si creación se cancela")

            print("✅ Test: create_new cancelado permite seleccionar existente")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test global_selector_create_new_cancel_then_pick_existing falló: {e}")
            self.failed += 1

    def run_all(self):
        print("\n🧪 TESTS: core/vault_selection.py")
        print("=" * 50)

        self.test_directory_arg_passthrough()
        self.test_directory_arg_invalid_requires_config()
        self.test_flags_in_local_context_use_local_vault()
        self.test_flags_in_non_local_context_require_directory()
        self.test_local_context_short_circuit()
        self.test_global_selector_exit()
        self.test_global_selector_create_new_success()
        self.test_global_selector_create_new_cancel_then_pick_existing()

        print(f"\n📊 Resultado: ✅ {self.passed} | ❌ {self.failed}")
        return self.failed == 0


if __name__ == "__main__":
    tester = TestCoreVaultSelection()
    success = tester.run_all()
    sys.exit(0 if success else 1)
