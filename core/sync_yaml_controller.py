#!/usr/bin/env python3
"""YAML sync controller extracted from BitacoraManager."""

import os
import shutil
from typing import Callable, Optional


class SyncYamlController:
    """Handle synchronization flow between repository structure and categories YAML."""

    def __init__(
        self,
        data_dir: str,
        vault_root: str,
        notes_root: str,
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[..., None] = print,
        sync_functions: Optional[dict] = None,
    ):
        self.data_dir = data_dir
        self.vault_root = vault_root
        self.notes_root = notes_root
        self.input = input_fn
        self.print = print_fn
        self.sync_functions = sync_functions

    def _get_sync_functions(self) -> dict:
        if self.sync_functions is not None:
            return self.sync_functions

        from tools.sync_yaml_with_repo import (
            parse_file_structure,
            build_categories_from_repo,
            from_yaml_file,
            merge_categories,
            to_yaml_string,
            get_sync_scan_config,
            check_nomenclature_issues,
            handle_nomenclature_issues,
            apply_name_mappings,
            get_empty_descriptions,
            add_descriptions_to_yaml,
            compare_structures,
        )

        return {
            "parse_file_structure": parse_file_structure,
            "build_categories_from_repo": build_categories_from_repo,
            "from_yaml_file": from_yaml_file,
            "merge_categories": merge_categories,
            "to_yaml_string": to_yaml_string,
            "get_sync_scan_config": get_sync_scan_config,
            "check_nomenclature_issues": check_nomenclature_issues,
            "handle_nomenclature_issues": handle_nomenclature_issues,
            "apply_name_mappings": apply_name_mappings,
            "get_empty_descriptions": get_empty_descriptions,
            "add_descriptions_to_yaml": add_descriptions_to_yaml,
            "compare_structures": compare_structures,
        }

    def run(self) -> None:
        """Run full sync flow."""
        self.print("\n🔄 SINCRONIZAR YAML CON REPOSITORIO")
        self.print("=" * 50)

        try:
            sync = self._get_sync_functions()

            # 1. Cargar YAML existente
            yaml_path = os.path.join(self.data_dir, "categories.yaml")
            try:
                existing_categories = sync["from_yaml_file"](yaml_path)
                self.print("  ✓ YAML cargado")
            except FileNotFoundError:
                self.print(f"  ⚠ No se encontró {yaml_path}, creando desde cero...")
                from models.yaml_models import CategoriesYAML

                existing_categories = CategoriesYAML(version="1.0.0")

            # 2. Escanear repositorio
            self.print("  ⏳ Escaneando repositorio...")
            scan_config = sync["get_sync_scan_config"](self.vault_root)
            structure = sync["parse_file_structure"](
                base_dir=self.notes_root,
                include_extensions=scan_config.get("include_extensions", (".md", ".sql")),
                excluded_prefixes=scan_config.get(
                    "excluded_prefixes", ("[2025]", "[2026]", "[🖼️ASSETS]", "[.crossnote]")
                ),
            )
            repo_categories = sync["build_categories_from_repo"](structure)
            self.print("  ✓ Repositorio escaneado")

            # 3. Verificar nomenclatura
            self.print("  ⏳ Verificando nomenclatura...")
            nomenclature_issues = sync["check_nomenclature_issues"](repo_categories)

            if nomenclature_issues:
                self.print()
                name_mapping = sync["handle_nomenclature_issues"](nomenclature_issues)

                if name_mapping is None:
                    self.print("\n❌ Sincronización cancelada por el usuario")
                    self.input("\nPresiona Enter para continuar...")
                    return

                if name_mapping:
                    sync["apply_name_mappings"](repo_categories, name_mapping)
                    sync["apply_name_mappings"](existing_categories, name_mapping)
                    self.print("  ✓ Nombres aplicados")
            else:
                self.print("  ✓ Nomenclatura OK")

            # 4. Comparar y fusionar
            self.print("  ⏳ Comparando estructuras...")
            sync["compare_structures"](existing_categories, repo_categories)

            self.print("  ⏳ Haciendo merge...")
            merged_categories = sync["merge_categories"](existing_categories, repo_categories)

            # Detectar descripciones vacías DESPUÉS del merge
            empty_descs = sync["get_empty_descriptions"](merged_categories)
            if empty_descs:
                self.print(f"\n  ⚠ {len(empty_descs)} elementos sin descripción")
                for item in empty_descs[:5]:
                    self.print(f"    • {item['path']}")
                if len(empty_descs) > 5:
                    self.print(f"    ... y {len(empty_descs) - 5} más")

                self.print()
                sync["add_descriptions_to_yaml"](merged_categories, empty_descs)

            # 5. Generar YAML
            self.print("\n  ⏳ Generando YAML...")
            yaml_content = sync["to_yaml_string"](merged_categories, indent=2, include_metadata=True)

            output_file = scan_config.get("output_file", "categories_SYNCED.yaml")
            output_path = output_file if os.path.isabs(output_file) else os.path.join(self.vault_root, output_file)
            output_path = os.path.normpath(output_path)

            # Comparar con el original para detectar cambios
            has_changes = True
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    original_content = f.read()
                has_changes = yaml_content.strip() != original_content.strip()
            except FileNotFoundError:
                has_changes = True

            if not has_changes:
                self.print("  ✓ Sin cambios - nada que sincronizar")
                if os.path.exists(output_path):
                    os.remove(output_path)
            else:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(yaml_content)

                self.print(f"  ✓ Archivo temporal creado: {output_path}")

                self.print("\n¿Reemplazar 'data/categories.yaml' con la versión sincronizada? (s/n): ", end="")
                while True:
                    choice = self.input().strip().lower()
                    if choice in ["s", "n", "si", "no"]:
                        break
                    self.print("Por favor, ingresa 's' o 'n': ", end="")

                if choice in ["s", "si"]:
                    backup_path = yaml_path + ".backup"
                    if os.path.exists(yaml_path):
                        shutil.copy2(yaml_path, backup_path)
                        self.print(f"  ✓ Respaldo creado: {backup_path}")

                    shutil.copy(output_path, yaml_path)
                    self.print("  ✓ 'data/categories.yaml' actualizado")
                    os.remove(output_path)
                else:
                    self.print("  ℹ Sin cambios en 'data/categories.yaml'")
                    self.print(f"  ℹ El archivo temporal está en: {output_path}")

            self.print("\n✅ Sincronización completada")

        except ImportError as e:
            self.print(f"\n❌ Error de importación: {e}")
            self.print("   Asegúrate de que sync_yaml_with_repo.py y yaml_models.py estén disponibles")
        except Exception as e:
            self.print(f"\n❌ Error durante la sincronización: {e}")
            import traceback

            traceback.print_exc()

        self.input("\nPresiona Enter para continuar...")
