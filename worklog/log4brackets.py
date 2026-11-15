#!/usr/bin/env python3
"""
Módulo log4brackets: Sistema centralizado de registro de eventos y actividad.
Formato clásico de una sola línea por evento, particionado mensualmente (data/log/YYYY-MM.log).
"""

import os
import threading
from datetime import datetime
from typing import Any, Optional


class Log4Brackets:
    """Registrador centralizado de eventos de actividad para Brackets."""

    def __init__(self, vault_root: Optional[str] = None):
        self.vault_root = os.path.abspath(vault_root) if vault_root else os.getcwd()
        self.log_dir = os.path.join(self.vault_root, "data", "log")
        self._lock = threading.Lock()

    def set_vault_root(self, vault_root: str) -> None:
        """Actualiza la raíz del vault activo."""
        self.vault_root = os.path.abspath(vault_root)
        self.log_dir = os.path.join(self.vault_root, "data", "log")

    def _ensure_log_dir(self) -> None:
        """Asegura que el directorio data/log exista."""
        os.makedirs(self.log_dir, exist_ok=True)

    def _get_log_filepath(self, dt: datetime) -> str:
        """Calcula la ruta del archivo mensual YYYY-MM.log."""
        return os.path.join(self.log_dir, f"{dt.year:04d}-{dt.month:02d}.log")

    def log(
        self,
        category: str,
        action: str,
        message: str = "",
        level: str = "INFO",
        ts: Optional[datetime] = None,
        **kwargs: Any
    ) -> str:
        """Escribe una línea de log estructurada."""
        now = ts or datetime.now()
        ts_str = now.strftime("%Y-%m-%d %H:%M:%S")

        meta_items = []
        for k, v in kwargs.items():
            if v is not None:
                val_str = str(v).replace("\n", " ").strip()
                meta_items.append(f"{k}={val_str}")

        meta_str = " | ".join(meta_items) if meta_items else ""

        parts = [f"[{ts_str}]", f"[{level.upper()}]", f"[{category.upper()}]", action]
        if meta_str:
            parts.append(f"| {meta_str}")
        if message:
            clean_msg = message.replace("\n", " ").strip()
            parts.append(f"| {clean_msg}")

        line = " ".join(parts) + "\n"

        with self._lock:
            self._ensure_log_dir()
            log_path = self._get_log_filepath(now)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line)

        return line.strip()

    def log_startup(self, vault_name: str = "", mode: str = "interactive") -> str:
        return self.log(
            category="STARTUP",
            action="run_brackets",
            message=f"Sesión iniciada en vault '{vault_name or os.path.basename(self.vault_root)}'",
            vault=vault_name or os.path.basename(self.vault_root),
            mode=mode
        )


    def log_task_created(
        self,
        task_id: str,
        project_id: Optional[str],
        title: str,
        ts: Optional[datetime] = None,
        day_number: Optional[int] = None
    ) -> str:
        return self.log(
            category="TASK",
            action="created",
            message=title,
            ts=ts,
            id=task_id,
            project=project_id or "POR_ASIGNAR",
            day=day_number
        )


    def log_task_completed(
        self,
        task_id: str,
        project_id: Optional[str],
        title: str,
        ts: Optional[datetime] = None,
        lead_time_days: Optional[int] = None
    ) -> str:
        return self.log(
            category="TASK",
            action="completed",
            message=title,
            ts=ts,
            id=task_id,
            project=project_id or "POR_ASIGNAR",
            lead_time_days=lead_time_days
        )

    def log_task_reopened(
        self,
        task_id: str,
        project_id: Optional[str],
        title: str,
        ts: Optional[datetime] = None
    ) -> str:
        return self.log(
            category="TASK",
            action="reopened",
            message=title,
            ts=ts,
            id=task_id,
            project=project_id or "POR_ASIGNAR"
        )

    def log_task_cancelled(
        self,
        task_id: str,
        project_id: Optional[str],
        title: str,
        ts: Optional[datetime] = None
    ) -> str:
        return self.log(
            category="TASK",
            action="cancelled",
            message=title,
            ts=ts,
            id=task_id,
            project=project_id or "POR_ASIGNAR"
        )

    def log_task_deleted(
        self,
        task_id: str,
        project_id: Optional[str],
        title: str,
        ts: Optional[datetime] = None
    ) -> str:
        return self.log(
            category="TASK",
            action="deleted",
            message=title,
            ts=ts,
            id=task_id,
            project=project_id or "POR_ASIGNAR"
        )

    def log_task_backlogged(
        self,
        task_id: str,
        project_id: Optional[str],
        title: str,
        reason: str = "rollover_2_weeks",
        ts: Optional[datetime] = None
    ) -> str:
        return self.log(
            category="TASK",
            action="migrated_to_backlog",
            message=title,
            ts=ts,
            id=task_id,
            project=project_id or "POR_ASIGNAR",
            reason=reason
        )


    def log_pomodoro(
        self,
        task_id: Optional[str],
        project_id: Optional[str],
        duration_min: int,
        action: str = "focus_completed",
        ts: Optional[datetime] = None,
        note: str = ""
    ) -> str:
        return self.log(
            category="POMODORO",
            action=action,
            message=note or f"Foco completado ({duration_min} min)",
            ts=ts,
            task=task_id,
            project=project_id,
            duration=f"{duration_min}m"
        )

    def log_note_created(
        self,
        note_id: str,
        project_id: Optional[str],
        title: str,
        topic_id: Optional[str] = None,
        ts: Optional[datetime] = None
    ) -> str:
        return self.log(
            category="NOTE",
            action="created",
            message=title,
            ts=ts,
            id=note_id,
            project=project_id,
            topic=topic_id
        )

    def log_topic_created(
        self,
        topic_id: str,
        project_id: Optional[str],
        title: str,
        ts: Optional[datetime] = None
    ) -> str:
        return self.log(
            category="TOPIC",
            action="created",
            message=title,
            ts=ts,
            id=topic_id,
            project=project_id
        )

    def log_rollover(
        self,
        from_week: int,
        to_week: int,
        rolled_count: int,
        ts: Optional[datetime] = None
    ) -> str:
        return self.log(
            category="ROLLOVER",
            action="week_rollover",
            message=f"Traspasadas {rolled_count} tareas de W{from_week:02d} a W{to_week:02d}",
            ts=ts,
            from_week=f"W{from_week:02d}",
            to_week=f"W{to_week:02d}",
            count=rolled_count
        )

    def log_consolidation(
        self,
        year: int,
        month: int,
        output_file: str,
        ts: Optional[datetime] = None
    ) -> str:
        return self.log(
            category="CONSOLIDATION",
            action="month_consolidated",
            message=f"Consolidado generado: {output_file}",
            ts=ts,
            year=year,
            month=f"{month:02d}",
            file=output_file
        )

    def log_person_created(
        self,
        person_id: str,
        handle: str,
        name: str,
        ts: Optional[datetime] = None
    ) -> str:
        return self.log(
            category="PERSON",
            action="created",
            message=f"{name}",
            ts=ts,
            id=person_id,
            handle=handle
        )


_default_logger: Optional[Log4Brackets] = None


def get_logger(vault_root: Optional[str] = None) -> Log4Brackets:
    global _default_logger
    if _default_logger is None:
        _default_logger = Log4Brackets(vault_root)
    elif vault_root and _default_logger.vault_root != os.path.abspath(vault_root):
        _default_logger.set_vault_root(vault_root)
    return _default_logger


log4brackets = get_logger()

