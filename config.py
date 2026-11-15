#!/usr/bin/env python3
"""
Configuración unificada del sistema Brackets.
Constantes, emojis, patrones y mensajes centralizados.
"""

import os
from typing import Dict, Tuple
from version import VERSION, VERSION_NAME

# =============================================================================
# DIRECTORIOS
# =============================================================================

# Directorio de trabajo donde se encuentran los archivos de bitácoras
# Por defecto usa el directorio actual, pero puede configurarse
WORKING_DIRECTORY = os.environ.get('BRACKETS_WORKING_DIR', '.')

# Directorio raíz del sistema Brackets (donde está el código)
BRACKETS_ROOT = os.path.dirname(os.path.abspath(__file__))

# =============================================================================
# NOMBRES DE MESES
# =============================================================================

MONTH_NAMES: Dict[int, str] = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre"
}

# =============================================================================
# EMOJIS DE ESTACIONES
# =============================================================================

SEASON_EMOJIS: Dict[Tuple[int, ...], str] = {
    (12, 1, 2): "❄️",      # Invierno
    (3, 4, 5): "🌱",       # Primavera
    (6, 7, 8): "☀️",       # Verano
    (9, 10, 11): "🍂"      # Otoño
}

# =============================================================================
# DÍAS DE LA SEMANA
# =============================================================================

WEEKDAYS: list = [
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes"
]

# =============================================================================
# PATRÓN DE TRABAJO (CASA/OFICINA)
# =============================================================================

WORK_SCHEDULE: Dict[int, str] = {
    0: "🏠",              # Lunes (casa)
    1: "🚗",              # Martes (oficina)
    2: "🚗",              # Miércoles (oficina)
    3: "🏠",              # Jueves (casa)
    4: "alternating"      # Viernes (alterna según semana par/impar)
}

WORK_LOCATIONS: Dict[str, str] = {
    "home": "🏠 Casa",
    "office": "🚗 Oficina",
    "remote": "💻 Remoto"
}

# =============================================================================
# EMOJIS DEL SISTEMA
# =============================================================================

EMOJIS = {
    # Estado
    'success': "✅",
    'error': "❌",
    'warning': "⚠️",
    'info': "ℹ️",
    'question': "❓",

    # Acciones
    'delete': "🗑️",
    'create': "📝",
    'update': "🔄",
    'search': "🔍",
    'list': "📋",

    # Categorías
    'calendar': "📅",
    'week': "🗓️",
    'month': "📆",
    'year': "📊",
    'project': "📊",
    'learning': "🎓",

    # Lugares
    'home': "🏠",
    'office': "🚗",
    'remote': "💻",

    # Estaciones
    'winter': "❄️",
    'spring': "🌱",
    'summer': "☀️",
    'autumn': "🍂",

    # Varios
    'task': "☐",
    'task_done': "☑",
    'note': "📌",
    'important': "⚡",
    'archive': "📦"
}

# =============================================================================
# MENSAJES DEL SISTEMA
# =============================================================================

MESSAGES = {
    # Confirmaciones
    'confirm_deletion': "⚠️  ¿Confirmar borrado?",
    'confirm_regenerate': "¿Regenerar el consolidado?",

    # Respuestas
    'delete_cancelled': "↩️  Operación de borrado cancelada",
    'operation_cancelled': "↩️  Operación cancelada",
    'delete_success': "🗑️  {count} archivo(s) borrado(s)",

    # Errores
    'error_reading': "❌ Error al leer archivo: {error}",
    'error_creating': "❌ Error al crear archivo: {error}",
    'error_deleting': "❌ Error al borrar archivo: {error}",
    'file_not_found': "❌ Archivo no encontrado: {filename}",
    'no_files_found': "❌ No se encontraron archivos",

    # Éxitos
    'file_created': "✅ Archivo creado: {filename}",
    'file_deleted': "✅ Borrado: {filename}",
    'consolidation_success': "✅ Consolidación completada",

    # Información
    'file_exists': "⚠️  El archivo {filename} ya existe. ¿Sobrescribir? (s/N): ",
    'files_found': "📁 Se encontraron {count} archivo(s)",
    'processing': "🔄 Procesando...",

    # Mensajes legacy (compatibilidad)
    'no_files': "❌ No se encontraron archivos de bitácora en el directorio actual",
    'monthly_created': "✅ Nuevo archivo mensual creado: {filename}",
    'invalid_weight': "⚠️ Peso inválido, se omitirá",
}

# =============================================================================
# CONFIGURACIÓN DE ARCHIVOS
# =============================================================================

# Encoding por defecto para archivos
DEFAULT_ENCODING = 'utf-8'

# Máximo de semanas por año
MAX_WEEKS_PER_YEAR = 52

# Patrones de nombres de archivos (regex simples para buscar)
WEEKLY_PATTERN = r'\[\d{4}\]\[\d{2}\]Week\d{2}\.md'
MONTHLY_PATTERN = r'\[\d{4}\]\[\d{2}\]MonthTopics\.md'

# Patrones de nombres de archivos (con grupos de captura)
FILE_PATTERNS = {
    'weekly': r'\[(\d{4})\]\[(\d{2})\]Week(\d{2})\.md',
    'monthly_topics': r'\[(\d{4})\]\[(\d{2})\]MonthTopics\.md',
    'year_topics': r'\[(\d{4})\]\[00\]YearTopics\.md',
    'month_consolidated': r'\[(\d{4})\]\[(\d{2})\]\.md',
    'year_consolidated': r'\[(\d{4})\]\.md',
}

# Patrones de contenido en bitácoras
DATE_SECTION_PATTERN = r'## [🏠🚗🏖️](\d+)'
TOPICS_SECTION_PATTERN = r'## ✅Topics\s*(.*?)(?=^##|\Z)'
NOTES_SECTION_PATTERN = r'## 📝Notes\s*(.*?)(?=^##|\Z)'
WEIGHT_PATTERN = r'#\s*🗓️Week\s+\d+\s+([\d.]+)'
PENDING_TASK_PATTERN = r'^\s*- \[ \](.+)$'
COMPLETED_TASK_PATTERN = r'^\s*- \[x\]'
SUBSECTION_PATTERN = r'^(\s*)- ### (.+)$'

# Plantillas de nombres de archivos
FILE_TEMPLATES = {
    'weekly': "[{year}][{month:02d}]Week{week:02d}.md",
    'monthly_topics': "[{year}][{month:02d}]MonthTopics.md",
    'year_topics': "[{year}][00]YearTopics.md",
    'month_consolidated': "[{year}][{month:02d}].md",
    'year_consolidated': "[{year}].md",
}

# =============================================================================
# CONFIGURACIÓN DE CONSOLIDACIÓN
# =============================================================================

# Separadores
SEPARATOR_MAJOR = "=" * 40
SEPARATOR_MINOR = "-" * 40
SEPARATOR_SECTION = "---"

# Plantillas de encabezados
HEADER_TEMPLATES = {
    'month_consolidated': "# {emoji} {month_name} - {year}",
    'year_consolidated': "# 📅 Año {year}",
    'weekly': "# 🗓️ {month_name} - Week {week}",
}
