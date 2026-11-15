#!/usr/bin/env python3
"""Tests para controlador de sync YAML extraído de main.py."""

import os
import sys
import tempfile

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.sync_yaml_controller import SyncYamlController


class TestCoreSyncYamlController:
    """Valida flujo del controlador de sincronización YAML."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def _assert(self, condition: bool, message: str):
        if not condition:
            raise AssertionError(message)

    def test_cancel_on_nomenclature_prompt(self):
        try:
            called = {"merge": False}
            printed = []

            sync_functions = {
                "from_yaml_file": lambda _path: {"categories": []},
                "get_sync_scan_config": lambda _vault_root: {"output_file": "categories_SYNCED.yaml"},
                "parse_file_structure": lambda **_kwargs: {},
                "build_categories_from_repo": lambda _structure: {"categories": []},
                "check_nomenclature_issues": lambda _repo: [{"issue": "x"}],
                "handle_nomenclature_issues": lambda _issues: None,
                "apply_name_mappings": lambda *_args: None,
                "compare_structures": lambda *_args: None,
                "merge_categories": lambda *_args: called.__setitem__("merge", True),
                "get_empty_descriptions": lambda _merged: [],
                "add_descriptions_to_yaml": lambda *_args: None,
                "to_yaml_string": lambda *_args, **_kwargs: "",
            }

            with tempfile.TemporaryDirectory() as tmp:
                data_dir = os.path.join(tmp, "data")
                os.makedirs(data_dir, exist_ok=True)

                inputs = iter([""])
                controller = SyncYamlController(
                    data_dir=data_dir,
                    vault_root=tmp,
                    notes_root=tmp,
                    input_fn=lambda _prompt="": next(inputs),
                    print_fn=lambda *args, **_kwargs: printed.append(" ".join(str(a) for a in args)),
                    sync_functions=sync_functions,
                )

                controller.run()

            self._assert(not called["merge"], "No debe hacer merge si el usuario cancela nomenclatura")
            self._assert(
                any("Sincronización cancelada" in line for line in printed),
                "Debe informar cancelación por nomenclatura",
            )

            print("✅ Test: sync yaml cancela cuando nomenclatura retorna None")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test cancel_on_nomenclature_prompt falló: {e}")
            self.failed += 1

    def test_no_changes_path_removes_temp_file(self):
        try:
            printed = []

            sync_functions = {
                "from_yaml_file": lambda _path: {"categories": []},
                "get_sync_scan_config": lambda _vault_root: {"output_file": "categories_SYNCED.yaml"},
                "parse_file_structure": lambda **_kwargs: {},
                "build_categories_from_repo": lambda _structure: {"categories": []},
                "check_nomenclature_issues": lambda _repo: [],
                "handle_nomenclature_issues": lambda _issues: {},
                "apply_name_mappings": lambda *_args: None,
                "compare_structures": lambda *_args: None,
                "merge_categories": lambda existing, _repo: existing,
                "get_empty_descriptions": lambda _merged: [],
                "add_descriptions_to_yaml": lambda *_args: None,
                "to_yaml_string": lambda *_args, **_kwargs: "same-content",
            }

            with tempfile.TemporaryDirectory() as tmp:
                data_dir = os.path.join(tmp, "data")
                os.makedirs(data_dir, exist_ok=True)

                yaml_path = os.path.join(data_dir, "categories.yaml")
                with open(yaml_path, "w", encoding="utf-8") as f:
                    f.write("same-content")

                output_path = os.path.join(tmp, "categories_SYNCED.yaml")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write("old-temp")

                inputs = iter([""])
                controller = SyncYamlController(
                    data_dir=data_dir,
                    vault_root=tmp,
                    notes_root=tmp,
                    input_fn=lambda _prompt="": next(inputs),
                    print_fn=lambda *args, **_kwargs: printed.append(" ".join(str(a) for a in args)),
                    sync_functions=sync_functions,
                )

                controller.run()

                self._assert(not os.path.exists(output_path), "Debe borrar archivo temporal si no hay cambios")

            self._assert(
                any("Sin cambios - nada que sincronizar" in line for line in printed),
                "Debe informar que no hay cambios",
            )

            print("✅ Test: sync yaml sin cambios elimina temporal")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test no_changes_path_removes_temp_file falló: {e}")
            self.failed += 1

    def run_all(self):
        print("\n🧪 TESTS: core/sync_yaml_controller.py")
        print("=" * 50)

        self.test_cancel_on_nomenclature_prompt()
        self.test_no_changes_path_removes_temp_file()

        print(f"\n📊 Resultado: ✅ {self.passed} | ❌ {self.failed}")
        return self.failed == 0


if __name__ == "__main__":
    tester = TestCoreSyncYamlController()
    success = tester.run_all()
    sys.exit(0 if success else 1)
