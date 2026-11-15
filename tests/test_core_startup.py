#!/usr/bin/env python3
"""Tests para orquestación de arranque CLI en core/startup.py."""

import os
import sys
import tempfile
from types import SimpleNamespace

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.startup import run_startup_flow


class _FakeManager:
    def __init__(self, vault_directory: str):
        self.vault_directory = vault_directory
        self.run_called = False

    def run(self):
        self.run_called = True


class TestCoreStartup:
    """Valida flujo parseado -> selección vault -> dispatch -> run."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def _assert(self, condition: bool, message: str):
        if not condition:
            raise AssertionError(message)

    def _args(self, directory=None):
        return SimpleNamespace(directory=directory)

    def _make_vault_dir(self, base_dir: str, name: str = "vault") -> str:
        vault_dir = os.path.join(base_dir, name)
        os.makedirs(os.path.join(vault_dir, "data"), exist_ok=True)
        with open(os.path.join(vault_dir, "data", "config.yaml"), "w", encoding="utf-8") as f:
            f.write("vault_name: test\n")
        return vault_dir

    def test_early_exit_code(self):
        try:
            called = {"manager": False, "dispatch": False}

            def _manager_factory(_vault):
                called["manager"] = True
                return _FakeManager(_vault)

            def _dispatch(_args, _manager, _vault):
                called["dispatch"] = True
                return None

            exit_code = run_startup_flow(
                args=self._args(),
                current_dir=".",
                manager_factory=_manager_factory,
                has_action_flags_fn=lambda _a: False,
                select_vault_directory_fn=lambda **_kwargs: (None, 0),
                dispatch_cli_action_fn=_dispatch,
            )

            self._assert(exit_code == 0, "Debe propagar early_exit_code")
            self._assert(called["manager"] is False, "No debe crear manager en salida temprana")
            self._assert(called["dispatch"] is False, "No debe ejecutar dispatch en salida temprana")

            print("✅ Test: early exit corta el flujo")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test early_exit_code falló: {e}")
            self.failed += 1

    def test_dispatch_exit_code(self):
        try:
            state = {"vault": None, "run": False}

            def _manager_factory(vault):
                state["vault"] = vault
                return _FakeManager(vault)

            def _dispatch(_args, manager, _vault):
                state["run"] = manager.run_called
                return 1

            with tempfile.TemporaryDirectory() as tmp:
                vault_dir = self._make_vault_dir(tmp)
                exit_code = run_startup_flow(
                    args=self._args(),
                    current_dir=tmp,
                    manager_factory=_manager_factory,
                    has_action_flags_fn=lambda _a: True,
                    select_vault_directory_fn=lambda **_kwargs: (vault_dir, None),
                    dispatch_cli_action_fn=_dispatch,
                )

            self._assert(exit_code == 1, "Debe propagar código del dispatcher")
            self._assert(state["vault"] == vault_dir, "Debe crear manager con vault resuelto")
            self._assert(state["run"] is False, "No debe ejecutar modo interactivo si dispatch devuelve código")

            print("✅ Test: dispatch con exit code evita run()")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test dispatch_exit_code falló: {e}")
            self.failed += 1

    def test_interactive_run_when_no_dispatch_code(self):
        try:
            holder = {"manager": None}

            def _manager_factory(vault):
                manager = _FakeManager(vault)
                holder["manager"] = manager
                return manager

            with tempfile.TemporaryDirectory() as tmp:
                vault_dir = self._make_vault_dir(tmp)
                exit_code = run_startup_flow(
                    args=self._args(),
                    current_dir=tmp,
                    manager_factory=_manager_factory,
                    has_action_flags_fn=lambda _a: False,
                    select_vault_directory_fn=lambda **_kwargs: (vault_dir, None),
                    dispatch_cli_action_fn=lambda _args, _manager, _vault: None,
                )

            self._assert(exit_code is None, "Modo interactivo debe devolver None")
            self._assert(holder["manager"] is not None, "Debe crear manager")
            self._assert(holder["manager"].run_called is True, "Debe ejecutar run() en modo interactivo")

            print("✅ Test: sin exit code se ejecuta run()")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test interactive_run_when_no_dispatch_code falló: {e}")
            self.failed += 1

    def test_invalid_vault_directory_stops_before_manager(self):
        try:
            called = {"manager": False}

            with tempfile.TemporaryDirectory() as tmp:
                invalid_dir = os.path.join(tmp, "invalid-vault")
                os.makedirs(invalid_dir, exist_ok=True)

                exit_code = run_startup_flow(
                    args=self._args(),
                    current_dir=tmp,
                    manager_factory=lambda _vault: called.__setitem__("manager", True) or _FakeManager(_vault),
                    has_action_flags_fn=lambda _a: False,
                    select_vault_directory_fn=lambda **_kwargs: (invalid_dir, None),
                    dispatch_cli_action_fn=lambda _args, _manager, _vault: None,
                )

            self._assert(exit_code == 2, "Debe devolver código 2 para vault inválido")
            self._assert(called["manager"] is False, "No debe crear manager para vault inválido")

            print("✅ Test: vault inválido corta flujo antes de manager")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test invalid_vault_directory_stops_before_manager falló: {e}")
            self.failed += 1

    def run_all(self):
        print("\n🧪 TESTS: core/startup.py")
        print("=" * 50)

        self.test_early_exit_code()
        self.test_dispatch_exit_code()
        self.test_interactive_run_when_no_dispatch_code()
        self.test_invalid_vault_directory_stops_before_manager()

        print(f"\n📊 Resultado: ✅ {self.passed} | ❌ {self.failed}")
        return self.failed == 0


if __name__ == "__main__":
    tester = TestCoreStartup()
    success = tester.run_all()
    sys.exit(0 if success else 1)
