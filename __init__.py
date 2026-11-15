"""
Sistema Brackets - Generador de Bitácoras y Gestión de Proyectos
Version 2.0 - Arquitectura Refactorizada
"""

from version import VERSION

__version__ = VERSION
__author__ = "Usuario"

# Exponer clases principales para importación fácil
from consolidators.month import MonthConsolidator
from consolidators.year import YearConsolidator

__all__ = [
    "MonthConsolidator",
    "YearConsolidator",
]
