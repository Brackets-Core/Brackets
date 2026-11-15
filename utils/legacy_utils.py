#!/usr/bin/env python3
"""
Utilidades y funciones auxiliares para el generador de bitácoras.
"""

import os
import re
import glob
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from config import (
    SEASON_EMOJIS,
    WORK_SCHEDULE,
    DEFAULT_ENCODING,
    MESSAGES,
    WEEKDAYS
)
from managers.settings_manager import get_global_settings_manager

WEEKDAYS_SHORT = ["L", "M", "X", "J", "V"]


def get_season_emoji(month: int) -> str:
    """Devuelve emoji según la estación del año."""
    for months, emoji in SEASON_EMOJIS.items():
        if month in months:
            return emoji
    return "📅"


def get_work_location(day_of_week: int, week_number: Optional[int] = None, current_date: Optional[datetime] = None) -> str:
    """
    Determina el lugar de trabajo según configuración viva.
    Incluye festivos/vacaciones si se proporciona la fecha real.
    """
    try:
        manager = get_global_settings_manager()
        target_date = current_date or _build_date_for_weekday(day_of_week)
        emoji, _ = manager.get_location_for_date(target_date, week_number)
        return emoji
    except Exception:
        # Fallback al comportamiento anterior en caso de error de configuración
        if day_of_week in WORK_SCHEDULE:
            location = WORK_SCHEDULE[day_of_week]
            if location == "alternating":
                if week_number is None:
                    return "🏠"
                return "🏠" if week_number % 2 == 0 else "🚗"
            return location
        return "🚗"


def safe_file_read(filepath: str) -> Optional[str]:
    """Lee un archivo de forma segura, devuelve None si hay error."""
    try:
        with open(filepath, 'r', encoding=DEFAULT_ENCODING) as f:
            return f.read()
    except Exception as e:
        print(MESSAGES['error_reading'].format(error=e))
        return None


def safe_file_write(filepath: str, content: str) -> bool:
    """Escribe un archivo de forma segura, devuelve True si es exitoso."""
    try:
        with open(filepath, 'w', encoding=DEFAULT_ENCODING) as f:
            f.write(content)
        return True
    except Exception as e:
        print(MESSAGES['error_creating'].format(error=e))
        return False


def confirm_overwrite(filename: str) -> bool:
    """Pregunta al usuario si quiere sobrescribir un archivo existente."""
    if os.path.exists(filename):
        response = input(MESSAGES['file_exists'].format(filename=filename))
        return response.lower() == 's'
    return True


def parse_float_input(input_str: str, default: Optional[float] = None) -> Optional[float]:
    """Convierte una cadena a float de forma segura."""
    if not input_str.strip():
        return default
    try:
        return float(input_str)
    except ValueError:
        print(MESSAGES['invalid_weight'])
        return default


def calculate_next_week_info_from_dates(dates: List[datetime], current_week_num: int) -> Tuple[int, int, int]:
    """Calcula la información de la próxima semana basándose en las fechas reales.
    
    Args:
        dates: Lista de fechas de la próxima semana (lunes a viernes)
        current_week_num: Número de semana actual del archivo más reciente
    
    Returns:
        Tuple con (año, mes, número_semana_siguiente)
    """
    if not dates:
        # Fallback al método original si no hay fechas
        today = datetime.now()
        next_monday = today - timedelta(days=today.weekday()) + timedelta(weeks=1)
        return next_monday.year, next_monday.month, current_week_num + 1
    
    # Tomar la primera fecha (lunes) de la próxima semana
    first_date = dates[0]
    
    # Simplemente incrementar el número de semana en 1
    next_week_num = current_week_num + 1
    
    # Si pasamos de la semana 52, reiniciar a 1
    if next_week_num > 52:
        next_week_num = 1
    
    return first_date.year, first_date.month, next_week_num


def generate_filename(
    year: int,
    month: int,
    week: int = None,
    is_monthly: bool = False,
    directory: str = ".",
) -> str:
    """Genera el nombre del archivo según el tipo y devuelve la ruta completa."""
    filename = (
        f"[{year:04d}][{month:02d}]MonthTopics.md"
        if is_monthly
        else f"[{year:04d}][{month:02d}]Week{week:02d}.md"
    )
    return os.path.join(directory, filename)


def print_calculated_dates(week_number: int, dates: List[datetime]) -> None:
    """Imprime las fechas calculadas para la semana."""
    print(f"📅 Fechas calculadas para semana {week_number}:")
    for i, date in enumerate(dates):
        print(f"  {WEEKDAYS[i]}: {date.strftime('%d/%m/%Y')}")


def test_emoji_pattern() -> None:
    """Función para probar el patrón de emojis por varias semanas."""
    print("🧪 Probando patrón de emojis por 8 semanas:")
    print("=" * 50)
    
    today = datetime.now()
    base_monday = today - timedelta(days=today.weekday())

    for week in range(1, 9):
        print(f"Semana {week:2d}: ", end="")
        monday = base_monday + timedelta(weeks=week - 1)
        for day in range(5):  # Lunes a Viernes
            current_date = monday + timedelta(days=day)
            emoji = get_work_location(day, week, current_date)
            print(f"{WEEKDAYS_SHORT[day]}{emoji}", end=" ")
        print()
    
    print("\n🏠 = Casa (Teletrabajo)")
    print("🚗 = Oficina (Presencial)")
    print("Nota: Solo el VIERNES alterna según semana par/impar")


def _build_date_for_weekday(day_of_week: int) -> datetime:
    """Construye una fecha ficticia de la semana actual para un weekday dado."""
    today = datetime.now()
    delta = day_of_week - today.weekday()
    return today + timedelta(days=delta)
