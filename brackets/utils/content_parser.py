#!/usr/bin/env python3
"""
Módulo para análisis y extracción de contenido de archivos de bitácora.
"""

import re
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from brackets.config import (
    TOPICS_SECTION_PATTERN,
    NOTES_SECTION_PATTERN,
    SUBSECTION_PATTERN,
    PENDING_TASK_PATTERN,
    COMPLETED_TASK_PATTERN,
    WEIGHT_PATTERN,
    DATE_SECTION_PATTERN,
    WEEKDAYS,
    MAX_WEEKS_PER_YEAR
)

# Actualizar patrones para nueva estructura
TOPICS_SECTION_PATTERN = r'## ✅Topics\s*(.*?)(?=^##|\Z)'
NOTES_SECTION_PATTERN = r'## 📝Notes\s*(.*?)(?=^##|\Z)'


class ContentParser:
    """Clase para analizar y extraer contenido de archivos de bitácora."""

    def __init__(self, content: str):
        self.content = content

    def extract_week_info_from_filename(self, filename: str) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[float]]:
        """Extrae información de la semana del nombre del archivo y contenido."""
        # Extraer semana del nombre del archivo
        file_match = re.search(r'\[(\d{4})\]\[(\d{2})\]Week(\d{2})\.md$', filename)
        if not file_match:
            return None, None, None, None

        year = int(file_match.group(1))
        month = int(file_match.group(2))
        week_num = int(file_match.group(3))

        # Extraer peso del contenido
        weight_match = re.search(WEIGHT_PATTERN, self.content)
        weight = float(weight_match.group(1)) if weight_match else None

        return year, month, week_num, weight

    def extract_pending_tasks(self) -> List[str]:
        """Extrae todas las tareas pendientes del archivo preservando estructura y jerarquía.

        Busca tareas PENDIENTES [ ] en TODO el contenido excepto:
        - Tareas completadas [x]
        - Líneas de metadata (>, ---)

        Preserva:
        - Indentación (para relación padre-hijo)
        - Subsecciones (### nivel)
        - Estructura anidada CON SUS PADRES

        Importante: Si una subtarea está sin su padre, la función intenta reconstruir la relación.
        """
        pending_tasks = []
        seen = set()

        def _process_lines(lines: List[str]) -> None:
            stack = []  # [(indent, is_task, is_completed)]

            for raw_line in lines:
                line = raw_line.rstrip()
                if not line.strip() or line.strip() == '---':
                    continue

                is_pending = bool(re.match(PENDING_TASK_PATTERN, line))
                is_completed = bool(re.match(COMPLETED_TASK_PATTERN, line))
                is_subsection = line.strip().startswith('### ')
                is_cancelled = bool(re.search(r'-\s*\[[ xX]?\]\s*~~.+?~~', line)) or (line.strip().startswith("- ~~") and line.strip().endswith("~~"))

                is_meeting = False
                if is_pending:
                    try:
                        from brackets.models.task_types import TaskTypeRegistry
                        task_text = re.sub(r'^\s*-\s*\[\s*\]\s*', '', line)
                        t_type, _ = TaskTypeRegistry.detect_task_type_and_clean_title(task_text)
                        if t_type == "meeting":
                            is_meeting = True
                    except Exception:
                        pass

                if not (is_pending or is_completed or is_subsection or is_cancelled):
                    continue

                indent = len(line) - len(line.lstrip())
                while stack and indent <= stack[-1][0]:
                    stack.pop()

                # Verificar si algún ancestro en el stack está completado o cancelado
                has_completed_ancestor = any(is_task and completed for _, is_task, completed in stack)

                # Solo procesar si NO tiene un ancestro completado/cancelado Y NO está completada/cancelada ni es reunión
                if (is_pending or is_subsection) and not has_completed_ancestor and not is_completed and not is_cancelled and not is_meeting:
                    key = line.strip()
                    if key not in seen:
                        pending_tasks.append(line)
                        seen.add(key)

                if is_pending and not is_cancelled:
                    stack.append((indent, True, False))
                elif is_completed or is_cancelled:
                    stack.append((indent, True, True))
                else:
                    stack.append((indent, False, False))

        # Buscar en TOPICS primero (sección principal).
        topics_section = re.search(TOPICS_SECTION_PATTERN, self.content, re.MULTILINE | re.DOTALL)
        if topics_section:
            _process_lines(topics_section.group(1).split('\n'))

        # Buscar en secciones de días y mantener jerarquía.
        day_sections = re.findall(
            r'##\s+[🏠🚗🏖️](\d+)(.*?)(?=##\s+|\Z)',
            self.content,
            re.MULTILINE | re.DOTALL
        )
        for _, day_content in day_sections:
            _process_lines(day_content.split('\n'))

        return pending_tasks

    def extract_daily_dates(self) -> List[int]:
        """Extrae los números de días de las secciones diarias."""
        dates_found = re.findall(DATE_SECTION_PATTERN, self.content)
        return [int(d) for d in dates_found[:5]]  # Solo los primeros 5 días

    def get_next_week_dates(self) -> List[datetime]:
        """Calcula las fechas de la próxima semana basándose en las fechas diarias del archivo.

        DEPRECATED: Usar WeeklyGenerator._calculate_next_week_dates_iso() para generación.
        Este método se mantiene únicamente para la herramienta de debug 'calcular fechas'.
        """
        current_days = self.extract_daily_dates()

        if not current_days or len(current_days) < 5:
            # Fallback: próxima semana desde hoy
            today = datetime.now()
            days_until_monday = (7 - today.weekday()) % 7 or 7
            next_monday = today + timedelta(days=days_until_monday)
            return [next_monday + timedelta(days=i) for i in range(5)]

        # Intentar construir fechas usando el mes del primer día encontrado
        today = datetime.now()
        for month_offset in [0, -1, 1]:
            m = today.month + month_offset
            y = today.year
            if m < 1:
                m = 12
                y -= 1
            elif m > 12:
                m = 1
                y += 1
            try:
                dates = [datetime(y, m, d) for d in current_days]
                return [d + timedelta(days=7) for d in dates]
            except ValueError:
                continue

        # Último fallback
        days_until_monday = (7 - today.weekday()) % 7 or 7
        next_monday = today + timedelta(days=days_until_monday)
        return [next_monday + timedelta(days=i) for i in range(5)]

    def clean_completed_tasks(self) -> str:
        """Remueve las tareas completadas [x] y mantiene las pendientes [ ]."""
        lines = self.content.split('\n')
        cleaned_lines = []

        for line in lines:
            # Si es una tarea completada [x], la omitimos
            if re.match(COMPLETED_TASK_PATTERN, line):
                continue
            # Todas las demás líneas se mantienen
            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)


def debug_content_parsing(filepath: str) -> None:
    """Función de debug para analizar el contenido de un archivo."""
    from brackets.utils.legacy_utils import safe_file_read

    content = safe_file_read(filepath)
    if not content:
        return

    parser = ContentParser(content)

    print(f"🔍 DEBUG: Analizando contenido de {filepath}")
    print("=" * 60)

    # Información de semana
    year, month, week, weight = parser.extract_week_info_from_filename(filepath)
    print(f"📅 Semana: {week}, Año: {year}, Mes: {month}")
    if weight:
        print(f"⚖️ Peso: {weight}")

    # Tareas pendientes
    pending_tasks = parser.extract_pending_tasks()
    print(f"📋 Tareas pendientes encontradas: {len(pending_tasks)}")
    for task in pending_tasks[:3]:  # Mostrar solo las primeras 3
        print(f"  {task}")
    if len(pending_tasks) > 3:
        print(f"  ... y {len(pending_tasks) - 3} más")

    # Fechas diarias
    daily_dates = parser.extract_daily_dates()
    print(f"📅 Fechas diarias: {daily_dates}")

    # Próximas fechas
    next_dates = parser.get_next_week_dates()
    print(f"🔮 Próximas fechas calculadas:")
    for i, date in enumerate(next_dates):
        print(f"  {WEEKDAYS[i]}: {date.strftime('%d/%m/%Y')}")

    # Tareas diarias pendientes
    daily_tasks = parser.extract_daily_pending_tasks()
    print(f"📅 Tareas diarias pendientes: {len(daily_tasks)}")
