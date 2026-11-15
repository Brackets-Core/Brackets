"""Servicio modular de sincronización Git + Markdown↔YAML en segundo plano para vaults."""

from __future__ import annotations

import os
import re
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional

import yaml

from managers.markdown_sync_service import MarkdownSyncService

WEEK_MD_PATTERN = re.compile(r"^\[(\d{4})\]\[(\d{2})\]Week(\d{2})\.md$")

DEFAULT_GIT_SYNC_CONFIG: Dict[str, Any] = {
    "enabled": False,
    "interval_seconds": 300,
    "auto_push": True,
    "remote": "origin",
}


def load_vault_git_sync_config(vault_path: str) -> Dict[str, Any]:
    """Lee la sección `git_sync` desde `data/config.yaml` del vault con valores por defecto."""
    cfg = dict(DEFAULT_GIT_SYNC_CONFIG)
    config_path = os.path.join(vault_path, "data", "config.yaml")
    if not os.path.exists(config_path):
        return cfg

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        if isinstance(raw, dict) and isinstance(raw.get("git_sync"), dict):
            user_cfg = raw["git_sync"]
            cfg["enabled"] = bool(user_cfg.get("enabled", cfg["enabled"]))
            interval = int(user_cfg.get("interval_seconds", cfg["interval_seconds"]))
            cfg["interval_seconds"] = max(30, interval)
            cfg["auto_push"] = bool(user_cfg.get("auto_push", cfg["auto_push"]))
            remote = str(user_cfg.get("remote", cfg["remote"]) or "origin").strip()
            cfg["remote"] = remote or "origin"
    except Exception:
        pass

    return cfg


class VaultGitSyncService:
    """Sincroniza vaults Git con su remoto y reconcilia cambios remotos de `.md` hacia YAML."""

    def __init__(self, web_service: Any):
        self.web_service = web_service
        self._locks: Dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()
        self._last_sync_at: Dict[str, float] = {}

    def _get_lock(self, vault_path: str) -> threading.Lock:
        norm = os.path.abspath(vault_path)
        with self._locks_guard:
            if norm not in self._locks:
                self._locks[norm] = threading.Lock()
            return self._locks[norm]

    @staticmethod
    def _run_git(vault_path: str, *args: str, timeout: int = 30) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", vault_path, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )

    def _reconcile_changed_markdowns(self, vault_path: str, changed_files: List[str]) -> List[str]:
        """Ejecuta sync `.md -> YAML` para las bitácoras semanales modificadas desde remoto."""
        synced_files: List[str] = []
        mgr = None

        for rel_path in changed_files:
            fname = os.path.basename(rel_path.strip())
            match = WEEK_MD_PATTERN.match(fname)
            if not match:
                continue

            year, week_num = int(match.group(1)), int(match.group(3))
            full_md_path = os.path.join(vault_path, rel_path.strip())
            if not os.path.exists(full_md_path):
                continue

            if mgr is None:
                mgr = self.web_service.get_entity_manager(vault_path)

            week = mgr.load_week(year, week_num, reload=True)
            if not week:
                self.web_service._get_or_create_week(vault_path, mgr, year=year, week_number=week_num)
            else:
                MarkdownSyncService(mgr, vault_path).sync_week_from_markdown(full_md_path, year, week_num)

            synced_files.append(fname)

        return synced_files

    def sync_vault(
        self,
        vault_path: str,
        vault_name: Optional[str] = None,
        auto_push: Optional[bool] = None,
        remote: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ejecuta el ciclo seguro: commit local -> pull --rebase -> sync .md->YAML -> push."""
        label = vault_name or os.path.basename(os.path.abspath(vault_path))
        if not os.path.isdir(os.path.join(vault_path, ".git")):
            return {"vault": label, "status": "skipped", "reason": "not_a_git_repo"}

        cfg = load_vault_git_sync_config(vault_path)
        use_push = cfg["auto_push"] if auto_push is None else auto_push
        use_remote = remote or cfg["remote"]

        lock = self._get_lock(vault_path)
        with lock:
            result: Dict[str, Any] = {
                "vault": label,
                "status": "ok",
                "committed_local": False,
                "pulled_changes": False,
                "synced_weeks": [],
                "pushed": False,
            }

            # 1. Commit de cambios locales pendientes antes de hacer pull
            st = self._run_git(vault_path, "status", "--porcelain")
            if st.returncode == 0 and st.stdout.strip():
                self._run_git(vault_path, "add", "-A")
                cm = self._run_git(vault_path, "commit", "-m", "chore(sync): auto-sync local vault changes")
                if cm.returncode == 0:
                    result["committed_local"] = True

            # 2. Determinar rama actual y HEAD previo
            branch_res = self._run_git(vault_path, "rev-parse", "--abbrev-ref", "HEAD")
            branch = branch_res.stdout.strip() if branch_res.returncode == 0 else "main"
            head_before_res = self._run_git(vault_path, "rev-parse", "HEAD")
            head_before = head_before_res.stdout.strip() if head_before_res.returncode == 0 else ""

            # 3. Pull --rebase desde remoto (si existe remoto configurado)
            remotes_res = self._run_git(vault_path, "remote")
            has_remote = remotes_res.returncode == 0 and use_remote in remotes_res.stdout.split()

            if has_remote:
                pull_res = self._run_git(vault_path, "pull", "--rebase", use_remote, branch, timeout=45)
                if pull_res.returncode != 0:
                    # Abortar rebase para no dejar el repo del usuario bloqueado ante conflictos
                    self._run_git(vault_path, "rebase", "--abort")
                    result["status"] = "warning"
                    result["error"] = (pull_res.stderr or pull_res.stdout).strip()
                    self._last_sync_at[os.path.abspath(vault_path)] = time.monotonic()
                    return result

                head_after_res = self._run_git(vault_path, "rev-parse", "HEAD")
                head_after = head_after_res.stdout.strip() if head_after_res.returncode == 0 else ""

                # 4. Si entraron commits desde remoto, reconciliar .md -> YAML
                if head_before and head_after and head_after != head_before:
                    result["pulled_changes"] = True
                    diff_res = self._run_git(vault_path, "diff", "--name-only", head_before, head_after)
                    if diff_res.returncode == 0 and diff_res.stdout.strip():
                        changed = [line.strip() for line in diff_res.stdout.splitlines() if line.strip()]
                        synced = self._reconcile_changed_markdowns(vault_path, changed)
                        result["synced_weeks"] = synced

                        if synced:
                            st_post = self._run_git(vault_path, "status", "--porcelain")
                            if st_post.returncode == 0 and st_post.stdout.strip():
                                self._run_git(vault_path, "add", "-A")
                                self._run_git(
                                    vault_path,
                                    "commit",
                                    "-m",
                                    "chore(sync): reconcile remote markdown into YAML",
                                )

                # 5. Push si hay commits locales por delante del remoto
                if use_push:
                    ahead_res = self._run_git(vault_path, "rev-list", "--count", f"{use_remote}/{branch}..HEAD")
                    ahead_count = 0
                    if ahead_res.returncode == 0 and ahead_res.stdout.strip().isdigit():
                        ahead_count = int(ahead_res.stdout.strip())
                    if ahead_count > 0:
                        push_res = self._run_git(vault_path, "push", use_remote, branch, timeout=45)
                        if push_res.returncode == 0:
                            result["pushed"] = True
                        else:
                            result["status"] = "warning"
                            result["error"] = (push_res.stderr or push_res.stdout).strip()

            self._last_sync_at[os.path.abspath(vault_path)] = time.monotonic()
            return result

    def sync_all_enabled_vaults(self, force: bool = False) -> List[Dict[str, Any]]:
        """Sincroniza todos los vaults con `git_sync.enabled: true` cuyo intervalo haya vencido."""
        results: List[Dict[str, Any]] = []
        now = time.monotonic()

        for vault in self.web_service.list_vaults():
            v_path = vault["path"]
            v_name = vault["name"]
            cfg = load_vault_git_sync_config(v_path)
            if not cfg["enabled"]:
                continue

            norm = os.path.abspath(v_path)
            last = self._last_sync_at.get(norm, 0.0)
            if not force and last > 0.0 and (now - last) < cfg["interval_seconds"]:
                continue

            res = self.sync_vault(
                v_path,
                vault_name=v_name,
                auto_push=cfg["auto_push"],
                remote=cfg["remote"],
            )
            results.append(res)

        return results


class VaultGitSyncWorker:
    """Hilo demonio que ejecuta `VaultGitSyncService` periódicamente mientras corre el servidor web."""

    def __init__(self, sync_service: VaultGitSyncService, poll_seconds: int = 15):
        self.sync_service = sync_service
        self.poll_seconds = max(5, poll_seconds)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="BracketsGitSyncWorker", daemon=True)
        self._thread.start()

    def stop(self, final_sync: bool = True) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        if final_sync:
            try:
                self.sync_service.sync_all_enabled_vaults(force=True)
            except Exception:
                pass

    def _run_loop(self) -> None:
        # Sincronización inicial al arrancar el servidor para bajar posibles cambios del móvil
        self._run_once_safe(force=True)
        while not self._stop_event.wait(self.poll_seconds):
            self._run_once_safe(force=False)

    def _run_once_safe(self, force: bool = False) -> None:
        try:
            results = self.sync_service.sync_all_enabled_vaults(force=force)
            for res in results:
                if res.get("pulled_changes") or res.get("pushed") or res.get("status") == "warning":
                    print(
                        f"🔄 [GitSync:{res.get('vault')}] "
                        f"status={res.get('status')} "
                        f"pulled={res.get('pulled_changes')} "
                        f"pushed={res.get('pushed')} "
                        f"weeks={res.get('synced_weeks')}"
                        + (f" error={res.get('error')}" if res.get("error") else "")
                    )
        except Exception as exc:
            print(f"⚠️ [GitSync] Error en ciclo periódico: {exc}")
