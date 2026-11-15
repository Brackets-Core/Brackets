"""Administrador de configuración viva para horarios y calendario laboral.
Mantiene un YAML como fuente de verdad para el patrón de trabajo,
festivos y vacaciones que afectan la generación automática de bitácoras.
"""

from __future__ import annotations

import os
from copy import deepcopy
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Lazy import para evitar dependencia dura hasta que se use el menú
_yaml = None

WEEKDAY_KEYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
WEEKDAY_LABELS = {
    "monday": "Lunes",
    "tuesday": "Martes",
    "wednesday": "Miércoles",
    "thursday": "Jueves",
    "friday": "Viernes",
    "saturday": "Sábado",
    "sunday": "Domingo",
}

DEFAULT_SETTINGS: Dict[str, object] = {
    "version": 1,
    "locations": {
        "home": "🏠",
        "office": "🚗",
        "remote": "💻",
        "off": "🏖️",
    },
    "work_pattern": {
        "alternating_day": "friday",
        "even_week": "home",
        "odd_week": "office",
        "defaults": {
            "monday": "home",
            "tuesday": "office",
            "wednesday": "office",
            "thursday": "home",
            "friday": "alternating",
        },
    },
    "calendar": {
        "holidays": [],
        "vacations": [],
        "closures": [],
        "intensive_workdays": [],
    },
}

_global_settings_manager: Optional["SettingsManager"] = None


class SettingsManager:
    """Carga y persiste la configuración editable de Brackets."""

    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        self.file_path = os.path.join(base_dir, "data", "work_calendar.yaml")
        self.data = self._load()

    # ------------------------------------------------------------------
    # Carga / persistencia
    # ------------------------------------------------------------------
    def _ensure_yaml(self):
        global _yaml
        if _yaml is None:
            try:
                import yaml as yaml_module
            except ImportError as exc:  # pragma: no cover - dependencia externa
                raise ImportError("PyYAML es requerido. Instala con: python -m pip install pyyaml") from exc
            _yaml = yaml_module

    def _load(self) -> Dict[str, object]:
        """Carga configuración desde disco; si no existe, crea con valores por defecto."""
        if os.path.exists(self.file_path):
            try:
                self._ensure_yaml()
                with open(self.file_path, "r", encoding="utf-8") as fh:
                    loaded = _yaml.safe_load(fh) or {}
                return self._merge_with_defaults(loaded)
            except Exception:
                # Si falla la lectura, no interrumpir el flujo; regenerar con defaults
                pass

        seeded = self._seed_from_main_config() or deepcopy(DEFAULT_SETTINGS)
        self._save(seeded)
        return seeded

    def _save(self, data: Dict[str, object]) -> None:
        self._ensure_yaml()
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as fh:
            _yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False)

    def _merge_with_defaults(self, loaded: Dict[str, object]) -> Dict[str, object]:
        data = deepcopy(DEFAULT_SETTINGS)
        data.update(loaded or {})
        # Asegurar sub-claves
        data.setdefault("locations", {}).update(DEFAULT_SETTINGS["locations"])
        data.setdefault("work_pattern", {})
        data.setdefault("calendar", {})
        data["work_pattern"].setdefault("defaults", {})
        # Completar faltantes de defaults
        for day_key, loc in DEFAULT_SETTINGS["work_pattern"]["defaults"].items():
            data["work_pattern"]["defaults"].setdefault(day_key, loc)
        # Alternancia
        data["work_pattern"].setdefault("alternating_day", DEFAULT_SETTINGS["work_pattern"]["alternating_day"])
        data["work_pattern"].setdefault("even_week", DEFAULT_SETTINGS["work_pattern"]["even_week"])
        data["work_pattern"].setdefault("odd_week", DEFAULT_SETTINGS["work_pattern"]["odd_week"])
        data["calendar"].setdefault("holidays", [])
        data["calendar"].setdefault("vacations", [])
        return data

    def _seed_from_main_config(self) -> Optional[Dict[str, object]]:
        """Si existe data/config.yaml, usarlo como semilla inicial."""
        candidate = os.path.join(self.base_dir, "data", "config.yaml")
        if not os.path.exists(candidate):
            return None

        try:
            self._ensure_yaml()
            with open(candidate, "r", encoding="utf-8") as fh:
                payload = _yaml.safe_load(fh) or {}
        except Exception:
            return None

        seeded = deepcopy(DEFAULT_SETTINGS)

        # Sembrar horarios
        work_schedule = payload.get("work_schedule", {})
        defaults = seeded["work_pattern"]["defaults"]
        for key in WEEKDAY_KEYS:
            node = work_schedule.get(key, {})
            loc = node.get("work_location")
            if loc in ("home", "office", "remote"):
                defaults[key] = loc

        # Sembrar festivos
        holidays = payload.get("holidays", [])
        seeded["calendar"]["holidays"] = self._normalize_holidays(holidays)

        # Sembrar vacaciones
        vacation_periods = payload.get("vacation_periods", [])
        seeded["calendar"]["vacations"] = self._normalize_vacations(vacation_periods)

        return seeded

    # ------------------------------------------------------------------
    # Lectura de estado
    # ------------------------------------------------------------------
    def list_holidays(self) -> List[Dict[str, str]]:
        return list(self.data.get("calendar", {}).get("holidays", []))

    def list_vacations(self) -> List[Dict[str, str]]:
        return list(self.data.get("calendar", {}).get("vacations", []))

    def list_closures(self) -> List[Dict[str, str]]:
        return list(self.data.get("calendar", {}).get("closures", []))

    def list_intensive_days(self) -> List[Dict[str, str]]:
        return list(self.data.get("calendar", {}).get("intensive_workdays", []))

    def describe_work_pattern(self) -> str:
        pattern = self.data["work_pattern"]
        defaults: Dict[str, str] = pattern.get("defaults", {})
        lines: List[str] = []
        lines.append("Patrón de trabajo actual:")
        lines.append("------------------------")
        for key in WEEKDAY_KEYS[:5]:  # Solo lunes-viernes
            loc_key = defaults.get(key, "office")
            emoji = self._location_to_emoji(loc_key)
            alt_flag = " (alterno)" if loc_key == "alternating" else ""
            lines.append(f"{WEEKDAY_LABELS[key]:<10}: {emoji} {self._location_label(loc_key)}{alt_flag}")

        alt_day = pattern.get("alternating_day", "friday")
        if alt_day:
            even_loc = pattern.get("even_week", "home")
            odd_loc = pattern.get("odd_week", "office")
            lines.append("")
            lines.append("Semana par/impar:")
            lines.append(f"- {WEEKDAY_LABELS.get(alt_day, alt_day)} par : {self._location_to_emoji(even_loc)} {self._location_label(even_loc)}")
            lines.append(f"- {WEEKDAY_LABELS.get(alt_day, alt_day)} impar: {self._location_to_emoji(odd_loc)} {self._location_label(odd_loc)}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Mutaciones
    # ------------------------------------------------------------------
    def set_day_location(self, day_key: str, location_key: str) -> None:
        self._validate_day(day_key)
        self._validate_location(location_key, allow_alternating=True)
        self.data["work_pattern"]["defaults"][day_key] = location_key
        self._save(self.data)

    def set_alternating(self, day_key: str, even_location: str, odd_location: str) -> None:
        self._validate_day(day_key)
        self._validate_location(even_location)
        self._validate_location(odd_location)
        self.data["work_pattern"]["alternating_day"] = day_key
        self.data["work_pattern"]["even_week"] = even_location
        self.data["work_pattern"]["odd_week"] = odd_location
        # Marcar el día como alternante
        self.data["work_pattern"]["defaults"][day_key] = "alternating"
        self._save(self.data)

    def reset_defaults(self) -> None:
        self.data = deepcopy(DEFAULT_SETTINGS)
        self._save(self.data)

    def add_or_update_holiday(self, date_str: str, name: str) -> None:
        target = self._parse_date(date_str)
        if not target:
            raise ValueError("Fecha inválida para festivo")
        holidays = self.data["calendar"].setdefault("holidays", [])
        normalized = {"date": target.isoformat(), "name": name}

        for idx, item in enumerate(holidays):
            if item.get("date") == normalized["date"]:
                holidays[idx] = normalized
                break
        else:
            holidays.append(normalized)
            holidays.sort(key=lambda x: x.get("date", ""))

        self._save(self.data)

    def delete_holiday(self, index: int) -> None:
        holidays = self.data["calendar"].get("holidays", [])
        if 0 <= index < len(holidays):
            holidays.pop(index)
            self._save(self.data)

    def add_or_update_vacation(self, start_str: str, end_str: str, name: str) -> None:
        start_date = self._parse_date(start_str)
        end_date = self._parse_date(end_str)
        if not start_date or not end_date or end_date < start_date:
            raise ValueError("Rango de vacaciones inválido")

        vacations = self.data["calendar"].setdefault("vacations", [])
        normalized = {"start": start_date.isoformat(), "end": end_date.isoformat(), "name": name}

        for idx, item in enumerate(vacations):
            if item.get("start") == normalized["start"] and item.get("end") == normalized["end"]:
                vacations[idx] = normalized
                break
        else:
            vacations.append(normalized)
            vacations.sort(key=lambda x: x.get("start", ""))

        self._save(self.data)

    def delete_vacation(self, index: int) -> None:
        vacations = self.data["calendar"].get("vacations", [])
        if 0 <= index < len(vacations):
            vacations.pop(index)
            self._save(self.data)

    def add_or_update_closure(self, date_str: str, name: str) -> None:
        target = self._parse_date(date_str)
        if not target:
            raise ValueError("Fecha inválida para cierre de sede")
        closures = self.data.setdefault("calendar", {}).setdefault("closures", [])
        normalized = {"date": target.isoformat(), "name": name}

        for idx, item in enumerate(closures):
            if item.get("date") == normalized["date"]:
                closures[idx] = normalized
                break
        else:
            closures.append(normalized)
            closures.sort(key=lambda x: x.get("date", ""))

        self._save(self.data)

    def delete_closure(self, index: int) -> None:
        closures = self.data.get("calendar", {}).get("closures", [])
        if 0 <= index < len(closures):
            closures.pop(index)
            self._save(self.data)

    def add_or_update_intensive_day(self, start_or_date: str, end_date_str: Optional[str] = None, name: str = "Jornada Intensiva") -> None:
        start_date = self._parse_date(start_or_date)
        if not start_date:
            raise ValueError("Fecha de inicio o fecha única inválida")

        if end_date_str:
            end_date = self._parse_date(end_date_str)
            if not end_date or end_date < start_date:
                raise ValueError("Rango de jornada intensiva inválido")
            normalized = {"start": start_date.isoformat(), "end": end_date.isoformat(), "name": name}
        else:
            normalized = {"date": start_date.isoformat(), "name": name}

        intensives = self.data.setdefault("calendar", {}).setdefault("intensive_workdays", [])

        for idx, item in enumerate(intensives):
            if normalized.get("date") and item.get("date") == normalized["date"]:
                intensives[idx] = normalized
                break
            elif normalized.get("start") and item.get("start") == normalized["start"] and item.get("end") == normalized["end"]:
                intensives[idx] = normalized
                break
        else:
            intensives.append(normalized)
            intensives.sort(key=lambda x: x.get("date") or x.get("start", ""))

        self._save(self.data)

    def delete_intensive_day(self, index: int) -> None:
        intensives = self.data.get("calendar", {}).get("intensive_workdays", [])
        if 0 <= index < len(intensives):
            intensives.pop(index)
            self._save(self.data)

    # ------------------------------------------------------------------
    # Resolución de ubicación
    # ------------------------------------------------------------------
    def get_location_for_date(self, target_date: datetime, week_number: Optional[int] = None) -> Tuple[str, Optional[str]]:
        """Devuelve (emoji, nota) según calendario y patrón."""
        # Festivo
        holiday_note = self._match_holiday(target_date.date())
        if holiday_note:
            return self._location_to_emoji("off"), holiday_note

        # Cierre de sede central (día libre / no laborable oficial)
        closure_note = self._match_closure(target_date.date())
        if closure_note:
            return self._location_to_emoji("off"), closure_note

        # Vacaciones
        vacation_note = self._match_vacation(target_date.date())
        if vacation_note:
            return self._location_to_emoji("off"), vacation_note

        # Día laboral normal según patrón
        day_key = WEEKDAY_KEYS[target_date.weekday()]
        emoji = self._location_for_day(day_key, week_number)

        # Jornada Intensiva (mantiene la ubicación habitual y añade el sufijo descriptivo)
        intensive_note = self._match_intensive(target_date.date())
        if intensive_note:
            return emoji, intensive_note

        return emoji, None

    def get_day_location(self, target_date: datetime, week_number: Optional[int] = None) -> str:
        """Alias para compatibilidad. Retorna el emoji para la fecha dada."""
        emoji, _ = self.get_location_for_date(target_date, week_number)
        return emoji

    def _location_for_day(self, day_key: str, week_number: Optional[int]) -> str:
        self._validate_day(day_key)
        defaults: Dict[str, str] = self.data["work_pattern"]["defaults"]
        location_key = defaults.get(day_key, "office")

        if location_key == "alternating" and day_key == self.data["work_pattern"].get("alternating_day"):
            even_loc = self.data["work_pattern"].get("even_week", "home")
            odd_loc = self.data["work_pattern"].get("odd_week", "office")
            location_key = even_loc if week_number is not None and week_number % 2 == 0 else odd_loc

        return self._location_to_emoji(location_key)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _validate_day(self, day_key: str) -> None:
        if day_key not in WEEKDAY_KEYS:
            raise ValueError(f"Día inválido: {day_key}")

    def _validate_location(self, location_key: str, allow_alternating: bool = False) -> None:
        valid = set(DEFAULT_SETTINGS["locations"].keys())
        if allow_alternating:
            valid.add("alternating")
        if location_key not in valid:
            raise ValueError(f"Ubicación inválida: {location_key}")

    def _location_to_emoji(self, location_key: str) -> str:
        return self.data.get("locations", {}).get(location_key, location_key)

    def _location_label(self, location_key: str) -> str:
        labels = {
            "home": "Casa",
            "office": "Oficina",
            "remote": "Remoto",
            "off": "Libre",
            "alternating": "Alterna",
        }
        return labels.get(location_key, location_key)

    def _parse_date(self, value: str) -> Optional[date]:
        try:
            return datetime.fromisoformat(value).date()
        except Exception:
            return None

    def _match_holiday(self, target: date) -> Optional[str]:
        for holiday in self.data.get("calendar", {}).get("holidays", []):
            if self._parse_date(holiday.get("date", "")) == target:
                name = holiday.get("name") or holiday.get("title") or "Festivo"
                return name
        return None

    def _match_vacation(self, target: date) -> Optional[str]:
        for period in self.data.get("calendar", {}).get("vacations", []):
            start = self._parse_date(period.get("start", ""))
            end = self._parse_date(period.get("end", ""))
            if start and end and start <= target <= end:
                return period.get("name") or "Vacaciones"
        return None

    def _match_closure(self, target: date) -> Optional[str]:
        for closure in self.data.get("calendar", {}).get("closures", []):
            if self._parse_date(closure.get("date", "")) == target:
                return closure.get("name") or "Cierre de sede central"
        return None

    def _match_intensive(self, target: date) -> Optional[str]:
        for item in self.data.get("calendar", {}).get("intensive_workdays", []):
            if item.get("date") and self._parse_date(item.get("date", "")) == target:
                return item.get("name") or "Jornada Intensiva"
            start = self._parse_date(item.get("start", ""))
            end = self._parse_date(item.get("end", ""))
            if start and end and start <= target <= end:
                return item.get("name") or "Jornada Intensiva"
        return None

    def _normalize_holidays(self, holidays: List[Dict[str, str]]) -> List[Dict[str, str]]:
        normalized: List[Dict[str, str]] = []
        for item in holidays:
            dt = self._parse_date(item.get("date", ""))
            if not dt:
                continue
            normalized.append({"date": dt.isoformat(), "name": item.get("name") or item.get("title") or "Festivo"})
        return sorted(normalized, key=lambda x: x.get("date", ""))

    def _normalize_vacations(self, vacations: List[Dict[str, str]]) -> List[Dict[str, str]]:
        normalized: List[Dict[str, str]] = []
        for item in vacations:
            start = self._parse_date(item.get("start", ""))
            end = self._parse_date(item.get("end", ""))
            if not start or not end:
                continue
            name = item.get("name") or item.get("title") or "Vacaciones"
            normalized.append({"start": start.isoformat(), "end": end.isoformat(), "name": name})
        return sorted(normalized, key=lambda x: x.get("start", ""))


# ----------------------------------------------------------------------
# Gestión global para reutilizar instancia y respetar el mismo base_dir
# ----------------------------------------------------------------------

def set_global_settings_manager(manager: SettingsManager) -> None:
    global _global_settings_manager
    _global_settings_manager = manager


def get_global_settings_manager(base_dir: str = ".") -> SettingsManager:
    global _global_settings_manager
    if _global_settings_manager is None or _global_settings_manager.base_dir != base_dir:
        _global_settings_manager = SettingsManager(base_dir)
    return _global_settings_manager
