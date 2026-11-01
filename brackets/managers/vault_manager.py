#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestor de múltiples vaults.
Permite descubrir, listar y seleccionar vaults en el workspace.
"""

import os
import sys
import json
import shutil
from typing import List, Dict, Optional


class VaultManager:
    """Gestiona la detección y selección de vaults en el workspace."""

    def __init__(self, workspace_root: str = None):
        """
        Inicializa el gestor de vaults.

        Args:
            workspace_root: Raíz del workspace. Si es None, busca desde el directorio actual.
        """
        self.workspace_root = workspace_root or os.getcwd()
        self.vaults = self._discover_vaults()

    def _is_valid_vault(self, path: str) -> bool:
        """
        Verifica si un directorio es un vault válido.

        Args:
            path: Ruta del directorio a verificar

        Returns:
            True si es un vault válido (tiene data/config.yaml)
        """
        config_path = os.path.join(path, "data", "config.yaml")
        return os.path.exists(config_path)

    def _load_external_vault_paths(self) -> List[str]:
        """Carga rutas a vaults externos desde vaults.yaml local o global ~/.brackets/vaults.yaml."""
        candidates = [
            os.path.join(self.workspace_root, "vaults.yaml"),
            os.path.join(self.workspace_root, "data", "vaults.yaml"),
            os.path.join(os.path.expanduser("~"), ".brackets", "vaults.yaml"),
        ]
        external_paths = []
        for cand in candidates:
            if os.path.exists(cand):
                try:
                    import yaml
                    with open(cand, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                        base_dir = os.path.dirname(cand)
                        if isinstance(data, list):
                            for item in data:
                                p = item if isinstance(item, str) else (item.get("path") if isinstance(item, dict) else None)
                                if p:
                                    external_paths.append(os.path.abspath(os.path.join(base_dir, p)) if not os.path.isabs(p) else os.path.abspath(p))
                        elif isinstance(data, dict):
                            entries = data.get("vaults") or data.get("external_vaults") or []
                            if isinstance(entries, list):
                                for item in entries:
                                    p = item if isinstance(item, str) else (item.get("path") if isinstance(item, dict) else None)
                                    if p:
                                        external_paths.append(os.path.abspath(os.path.join(base_dir, p)) if not os.path.isabs(p) else os.path.abspath(p))
                except Exception:
                    pass
        return external_paths

    def resolve_vault_path(self, vault_identifier: Optional[str] = None) -> Optional[str]:
        """Resuelve un nombre o ruta de vault al path absoluto correspondiente."""
        if not vault_identifier:
            return self.vaults[0]["path"] if self.vaults else None

        target = vault_identifier.strip().lower()
        for v in self.vaults:
            if v["name"].lower() == target or os.path.abspath(v["path"]).lower() == os.path.abspath(vault_identifier).lower():
                return v["path"]

        # Probar subcarpeta vaults/ o ruta directa
        candidates = [
            os.path.abspath(os.path.join(self.workspace_root, "vaults", vault_identifier)),
            os.path.abspath(os.path.join(self.workspace_root, vault_identifier)),
            os.path.abspath(vault_identifier),
        ]
        for cand in candidates:
            if self._is_valid_vault(cand):
                return cand

        return None

    def _discover_vaults(self) -> List[Dict[str, str]]:
        """
        Descubre todos los vaults en el workspace (en raíz, en carpeta vaults/ o externos).

        Returns:
            Lista de diccionarios con info de cada vault: {name, path, description}
        """
        vaults = []
        seen_paths = set()

        def add_candidate(cand_path: str, cand_name: Optional[str] = None):
            norm = os.path.abspath(cand_path).lower()
            if norm in seen_paths:
                return
            if os.path.isdir(cand_path) and self._is_valid_vault(cand_path):
                name = cand_name or os.path.basename(cand_path)
                vaults.append(self._get_vault_info(cand_path, name))
                seen_paths.add(norm)

        try:
            # 1. Buscar en el workspace raíz (ej: MyJobNotes, PersonalNotes...)
            if os.path.exists(self.workspace_root):
                for item in os.listdir(self.workspace_root):
                    if item.startswith('.') or item in ('SharedContext', 'brackets', 'vaults'):
                        continue
                    item_path = os.path.join(self.workspace_root, item)
                    if os.path.isdir(item_path):
                        add_candidate(item_path, item)

                # 2. Buscar dentro de carpeta contenedora 'vaults/' si existe
                vaults_dir = os.path.join(self.workspace_root, "vaults")
                if os.path.isdir(vaults_dir):
                    for item in os.listdir(vaults_dir):
                        if item.startswith('.'):
                            continue
                        item_path = os.path.join(vaults_dir, item)
                        if os.path.isdir(item_path):
                            add_candidate(item_path, item)

            # 3. Cargar vaults externos registrados en vaults.yaml
            for ext in self._load_external_vault_paths():
                ext_abs = os.path.abspath(ext) if not os.path.isabs(ext) else ext
                if os.path.exists(ext_abs):
                    add_candidate(ext_abs)

        except Exception as e:
            print(f"⚠️  Error al buscar vaults: {e}")

        return sorted(vaults, key=lambda x: x['name'])

    def _get_vault_info(self, path: str, name: str) -> Dict[str, str]:
        """
        Obtiene información de un vault.

        Args:
            path: Ruta del vault
            name: Nombre del vault

        Returns:
            Diccionario con info del vault
        """
        vault_info = {
            'name': name,
            'path': path,
            'description': ''
        }

        # Intentar leer descripción desde config.yaml
        try:
            import yaml
            config_path = os.path.join(path, "data", "config.yaml")
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if config and isinstance(config, dict):
                    vault_info['description'] = config.get('description', '')
        except Exception:
            pass

        return vault_info

    def show_vault_menu(self) -> Optional[str]:
        """
        Muestra el menú de selección de vaults.

        Returns:
            Ruta del vault seleccionado, 'CREATE_NEW' para crear nuevo, o None para salir
        """
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n🗃️  GESTOR DE VAULTS - SISTEMA BRACKETS")
            print("=" * 60)

            if not self.vaults:
                print("\n⚠️  No se encontraron vaults en el workspace")
                print(f"   Buscando en: {self.workspace_root}")
            else:
                print(f"\n📂 Vaults disponibles ({len(self.vaults)}):\n")
                for idx, vault in enumerate(self.vaults, 1):
                    print(f"{idx}. 📁 {vault['name']}")
                    if vault['description']:
                        print(f"   {vault['description']}")

            print(f"\n{len(self.vaults) + 1}. ➕ Crear nuevo vault")
            if self.vaults:
                print(f"{len(self.vaults) + 2}. 🗑️  Borrar vault")
            print("0. 🚪 Salir")
            print("-" * 60)

            choice = input("\nSelecciona una opción: ").strip()

            if choice == "0":
                return None

            # Crear nuevo vault
            if choice == str(len(self.vaults) + 1):
                return 'CREATE_NEW'

            # Borrar vault
            if self.vaults and choice == str(len(self.vaults) + 2):
                self._delete_vault_menu()
                continue

            # Seleccionar vault existente
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(self.vaults):
                    return self.vaults[idx]['path']
                else:
                    print("\n❌ Opción inválida")
                    input("Presiona Enter para continuar...")
            except ValueError:
                print("\n❌ Opción inválida")
                input("Presiona Enter para continuar...")

    def refresh_vaults(self):
        """Refresca la lista de vaults disponibles."""
        self.vaults = self._discover_vaults()

    def _delete_vault_menu(self):
        """Menú para seleccionar y borrar un vault."""
        if not self.vaults:
            return

        print("\n" + "=" * 60)
        print("🗑️  BORRAR VAULT")
        print("=" * 60)
        print("\n⚠️  ADVERTENCIA: Esta acción es PERMANENTE")
        print("\n📂 Selecciona el vault a borrar:\n")

        for idx, vault in enumerate(self.vaults, 1):
            print(f"{idx}. {vault['name']}")
            print(f"   📍 {vault['path']}")

        print("\n0. ← Cancelar")
        print("-" * 60)

        choice = input("\nSelecciona vault a borrar: ").strip()

        if choice == "0" or not choice:
            return

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(self.vaults):
                vault = self.vaults[idx]
                self._delete_vault(vault)
            else:
                print("\n❌ Opción inválida")
                input("Presiona Enter para continuar...")
        except ValueError:
            print("\n❌ Opción inválida")
            input("Presiona Enter para continuar...")

    def _delete_vault(self, vault_info: Dict[str, str]):
        """Borra un vault con doble confirmación.

        Args:
            vault_info: Información del vault a borrar
        """
        vault_name = vault_info['name']
        vault_path = vault_info['path']
        workspace_root = os.path.abspath(self.workspace_root)
        vault_abs_path = os.path.abspath(vault_path)

        if os.path.commonpath([vault_abs_path, workspace_root]) != workspace_root:
            print("\n❌ Seguridad: ruta fuera del workspace")
            input("Presiona Enter para continuar...")
            return

        print("\n" + "=" * 60)
        print("⚠️  CONFIRMACIÓN DE BORRADO")
        print("=" * 60)
        print(f"\n📁 Vault: {vault_name}")
        print(f"📍 Ubicación: {vault_path}")
        print("\n🔥 Se borrará PERMANENTEMENTE:")
        print("   • Todos los archivos y carpetas")
        print("   • Configuración y datos")
        print("   • No se puede recuperar")
        print("\n" + "=" * 60)

        # Primera confirmación
        confirm1 = input(f"\n¿Borrar '{vault_name}'? Escribe 'BORRAR' para confirmar: ").strip()

        if confirm1 != 'BORRAR':
            print("\n❌ Borrado cancelado")
            input("Presiona Enter para continuar...")
            return

        # Segunda confirmación
        print("\n⚠️  ÚLTIMA CONFIRMACIÓN")
        confirm2 = input(f"¿ESTÁS SEGURO de borrar '{vault_name}'? (escribe el nombre completo): ").strip()

        if confirm2 != vault_name:
            print("\n❌ Borrado cancelado - nombre no coincide")
            input("Presiona Enter para continuar...")
            return

        # Proceder con borrado
        try:
            print(f"\n🗑️  Borrando vault...")

            # Borrar directorio si existe
            if os.path.exists(vault_abs_path):
                shutil.rmtree(vault_abs_path)
                print("   ✅ Directorio borrado")
            else:
                print("   ⚠️  Directorio no encontrado, se limpiara el workspace")

            # Quitar del workspace
            workspace_file = os.path.join(self.workspace_root, "Brackets.code-workspace")
            if os.path.exists(workspace_file):
                if self._remove_from_workspace(workspace_file, vault_abs_path, vault_name):
                    print(f"   ✅ Removido del workspace de VS Code")

            print(f"\n✅ Vault '{vault_name}' borrado exitosamente")

            # Refrescar lista
            self.refresh_vaults()

        except Exception as e:
            print(f"\n❌ Error al borrar vault: {e}")

        input("\nPresiona Enter para continuar...")

    def _remove_from_workspace(self, workspace_file: str, vault_path: str, vault_name: str) -> bool:
        """Remueve el vault del archivo .code-workspace.

        Args:
            workspace_file: Ruta al archivo .code-workspace
            vault_path: Ruta absoluta del vault a remover
            vault_name: Nombre del vault a remover

        Returns:
            True si se removió correctamente, False en caso contrario
        """
        try:
            workspace_root = os.path.dirname(workspace_file)
            target_rel = os.path.relpath(vault_path, workspace_root)
            target_rel_norm = os.path.normcase(os.path.normpath(target_rel))
            target_abs_norm = os.path.normcase(os.path.normpath(vault_path))

            # Leer workspace
            with open(workspace_file, 'r', encoding='utf-8') as f:
                workspace_config = json.load(f)

            # Buscar y remover
            folders = workspace_config.get('folders', [])
            new_folders = []
            removed = False

            for folder in folders:
                folder_path = folder.get('path', '')
                folder_norm = os.path.normcase(os.path.normpath(folder_path))

                if folder_norm == target_rel_norm or folder_norm == target_abs_norm:
                    removed = True
                    continue
                if folder.get('name', '').strip().endswith(vault_name):
                    removed = True
                    continue

                new_folders.append(folder)

            if not removed:
                return True  # No estaba, no es error

            workspace_config['folders'] = new_folders

            # Guardar
            with open(workspace_file, 'w', encoding='utf-8') as f:
                json.dump(workspace_config, f, indent='\t', ensure_ascii=False)

            return True

        except Exception as e:
            print(f"Error al actualizar workspace: {e}")
            return False
