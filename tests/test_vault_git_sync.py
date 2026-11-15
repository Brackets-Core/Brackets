#!/usr/bin/env python3
"""Tests unitarios y de integración para `services/vault_git_sync.py`."""

import os
import shutil
import subprocess
import tempfile
import unittest

from services.vault_git_sync import VaultGitSyncService, load_vault_git_sync_config
from web.service import BracketsWebService


def _git(cwd: str, *args: str) -> str:
    res = subprocess.run(
        ["git", "-C", cwd, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return res.stdout.strip()


class TestVaultGitSync(unittest.TestCase):
    """Pruebas del servicio de sincronización Git + Markdown->YAML."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="brackets_git_sync_test_")
        self.remote_dir = os.path.join(self.temp_dir, "remote.git")
        self.workspace_dir = os.path.join(self.temp_dir, "workspace")
        self.vault_dir = os.path.join(self.workspace_dir, "MyTestVault")
        self.mobile_dir = os.path.join(self.temp_dir, "mobile_clone")

        os.makedirs(self.workspace_dir, exist_ok=True)
        subprocess.run(["git", "init", "--bare", self.remote_dir], check=True, capture_output=True)
        subprocess.run(["git", "-C", self.remote_dir, "symbolic-ref", "HEAD", "refs/heads/main"], check=True, capture_output=True)

        # Clonar vault local y configurar identidad Git
        subprocess.run(["git", "clone", self.remote_dir, self.vault_dir], check=True, capture_output=True)
        _git(self.vault_dir, "config", "user.email", "test@brackets.local")
        _git(self.vault_dir, "config", "user.name", "Brackets Test")
        _git(self.vault_dir, "checkout", "-b", "main")

        # Estructura mínima del vault con git_sync habilitado
        os.makedirs(os.path.join(self.vault_dir, "data", "tables"), exist_ok=True)
        os.makedirs(os.path.join(self.vault_dir, "data", "weeks"), exist_ok=True)
        with open(os.path.join(self.vault_dir, "data", "config.yaml"), "w", encoding="utf-8") as f:
            f.write(
                "vault_type: work\n"
                "days_per_week: 5\n"
                "git_sync:\n"
                "  enabled: true\n"
                "  interval_seconds: 60\n"
                "  auto_push: true\n"
                "  remote: origin\n"
            )
        with open(os.path.join(self.vault_dir, "data", "tables", "tasks.yaml"), "w", encoding="utf-8") as f:
            f.write("tasks: []\n")

        _git(self.vault_dir, "add", "-A")
        _git(self.vault_dir, "commit", "-m", "chore: initial vault")
        _git(self.vault_dir, "push", "-u", "origin", "main")

        # Clonar copia "móvil"
        subprocess.run(["git", "clone", self.remote_dir, self.mobile_dir], check=True, capture_output=True)
        _git(self.mobile_dir, "config", "user.email", "mobile@brackets.local")
        _git(self.mobile_dir, "config", "user.name", "Mobile PWA")

        self.web_service = BracketsWebService(workspace_root=self.workspace_dir)
        self.sync_service = VaultGitSyncService(self.web_service)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_vault_git_sync_config_defaults_and_clamp(self):
        """Verifica valores por defecto y límite mínimo de intervalo."""
        empty_dir = os.path.join(self.temp_dir, "no_cfg")
        os.makedirs(empty_dir, exist_ok=True)
        defaults = load_vault_git_sync_config(empty_dir)
        self.assertFalse(defaults["enabled"])
        self.assertEqual(defaults["interval_seconds"], 300)

        cfg = load_vault_git_sync_config(self.vault_dir)
        self.assertTrue(cfg["enabled"])
        self.assertEqual(cfg["interval_seconds"], 60)

    def test_pull_mobile_markdown_reconciles_yaml_and_pushes(self):
        """Si el móvil sube [2026][11]Week46.md, el sync local lo baja, genera YAML y hace push."""
        mobile_md = os.path.join(self.mobile_dir, "[2026][11]Week46.md")
        with open(mobile_md, "w", encoding="utf-8") as f:
            f.write(
                "# 🗓️Week 46\n\n"
                "## 🎯Topics\n"
                "  - \n"
                "  ---\n\n"
                "## 📋Week Tasks\n"
                "  - [ ] Tarea creada desde el móvil\n"
                "  ---\n\n"
                "## 🚗9\n"
                "  - [x] Reunión en móvil\n\n"
                "## Definiciones\n"
                "<!-- Definiciones -->\n"
            )
        _git(self.mobile_dir, "add", "-A")
        _git(self.mobile_dir, "commit", "-m", "feat(task): add from mobile")
        _git(self.mobile_dir, "push", "origin", "main")

        results = self.sync_service.sync_all_enabled_vaults(force=True)
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res["status"], "ok")
        self.assertTrue(res["pulled_changes"])
        self.assertEqual(res["synced_weeks"], ["[2026][11]Week46.md"])
        self.assertTrue(res["pushed"])

        # Verificar que el YAML local se generó e importó las tareas
        self.assertTrue(os.path.exists(os.path.join(self.vault_dir, "data", "weeks", "2026-W46.yaml")))
        mgr = self.web_service.get_entity_manager(self.vault_dir)
        titles = [t.title for t in mgr.tasks.values()]
        self.assertIn("Tarea creada desde el móvil", titles)
        self.assertIn("Reunión en móvil", titles)

    def test_local_changes_are_committed_and_pushed(self):
        """Cambios locales sin commitear se guardan y se suben al remoto automáticamente."""
        local_note = os.path.join(self.vault_dir, "nota_local.md")
        with open(local_note, "w", encoding="utf-8") as f:
            f.write("# Nota local\n")

        res = self.sync_service.sync_vault(self.vault_dir, vault_name="MyTestVault")
        self.assertEqual(res["status"], "ok")
        self.assertTrue(res["committed_local"])
        self.assertTrue(res["pushed"])

        _git(self.mobile_dir, "pull", "origin", "main")
        self.assertTrue(os.path.exists(os.path.join(self.mobile_dir, "nota_local.md")))


if __name__ == "__main__":
    unittest.main()
