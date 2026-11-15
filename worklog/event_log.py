"""
Event Log: registro append-only de eventos de actividad.

Almacena un archivo YAML por semana ISO en data/log/YYYY-WXX.yaml.
Cada archivo contiene una lista de entries con timestamp y tipo de evento.
"""

import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import yaml


class EventLog:
    """Append-only event log con un archivo YAML por semana ISO."""

    def __init__(self, vault_root: str):
        """
        Args:
            vault_root: Ruta raíz del vault (directorio que contiene data/).
        """
        self.vault_root = os.path.abspath(vault_root)
        self.log_dir = os.path.join(self.vault_root, "data", "log")

    def _ensure_dir(self) -> None:
        """Crea el directorio de logs si no existe."""
        os.makedirs(self.log_dir, exist_ok=True)

    def _week_path(self, day: date) -> str:
        """Ruta al archivo de log para la semana ISO de un día."""
        iso_year, iso_week, _ = day.isocalendar()
        return os.path.join(self.log_dir, f"{iso_year}-W{iso_week:02d}.yaml")

    def append(self, event: str, **kwargs: Any) -> Dict[str, Any]:
        """Agrega un evento al log de la semana actual.

        Args:
            event: Tipo de evento (ej: "task_added", "pomodoro_start", "session_start").
            **kwargs: Datos adicionales del evento (task_id, task_text, detail, etc.).

        Returns:
            El entry completo que fue guardado.
        """
        self._ensure_dir()

        now = datetime.now()
        entry: Dict[str, Any] = {
            "ts": now.isoformat(timespec="seconds"),
            "event": event,
        }
        entry.update(kwargs)

        week_file = self._week_path(now.date())
        entries = self._load_entries(week_file)
        entries.append(entry)
        self._save_entries(week_file, entries)

        return entry

    def read_day(self, day: Optional[date] = None) -> List[Dict[str, Any]]:
        """Lee todos los eventos de un día específico.

        Args:
            day: Fecha a consultar. Si es None, usa hoy.

        Returns:
            Lista de entries del día (filtradas por timestamp).
        """
        if day is None:
            day = date.today()
        week_file = self._week_path(day)
        all_entries = self._load_entries(week_file)
        day_iso = day.isoformat()
        return [e for e in all_entries if e.get("ts", "").startswith(day_iso)]

    def read_week(self, day: Optional[date] = None) -> List[Dict[str, Any]]:
        """Lee todos los eventos de la semana ISO que contiene el día dado.

        Args:
            day: Cualquier día de la semana a consultar. Si es None, usa hoy.

        Returns:
            Lista completa de entries de esa semana.
        """
        if day is None:
            day = date.today()
        week_file = self._week_path(day)
        return self._load_entries(week_file)

    def read_range(self, start: date, end: date) -> List[Dict[str, Any]]:
        """Lee eventos de un rango de fechas (inclusive).

        Args:
            start: Fecha inicial (inclusive).
            end: Fecha final (inclusive).

        Returns:
            Lista combinada de entries dentro del rango, ordenada cronológicamente.
        """
        # Recopilar semanas únicas que cubren el rango
        seen_files: set = set()
        all_entries: List[Dict[str, Any]] = []
        current = start
        while current <= end:
            week_file = self._week_path(current)
            if week_file not in seen_files:
                seen_files.add(week_file)
                all_entries.extend(self._load_entries(week_file))
            current += timedelta(days=1)

        # Filtrar solo entries dentro del rango de fechas
        start_iso = start.isoformat()
        end_iso = end.isoformat()
        return [
            e for e in all_entries
            if start_iso <= e.get("ts", "")[:10] <= end_iso
        ]

    def _load_entries(self, path: str) -> List[Dict[str, Any]]:
        """Carga entries de un archivo YAML."""
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict) and isinstance(data.get("entries"), list):
                return data["entries"]
            return []
        except (yaml.YAMLError, OSError):
            return []

    def _save_entries(self, path: str, entries: List[Dict[str, Any]]) -> None:
        """Guarda entries a un archivo YAML."""
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                {"entries": entries},
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
