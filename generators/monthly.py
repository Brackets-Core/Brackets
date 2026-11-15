#!/usr/bin/env python3
"""
Generador especializado para archivos mensuales de topics.
"""

import os
from typing import Optional

from config import MESSAGES
from utils.file_finder import FileFinder
from utils.content_parser import ContentParser
from utils.content_generator import ContentGenerator
from utils.legacy_utils import (
    safe_file_read, safe_file_write, confirm_overwrite,
    generate_filename
)
from config import WORKING_DIRECTORY


class MonthlyGenerator:
    """Clase para generar archivos mensuales de topics."""

    def __init__(self, directory: str = "."):
        self.directory = directory
        self.finder = FileFinder(directory)
        self.generator = ContentGenerator()

    def create_next_monthly_topics(self) -> bool:
        """Crea el siguiente archivo mensual basado en el más reciente."""

        # Encontrar archivo más reciente
        recent_file = self.finder.get_most_recent_monthly()
        if not recent_file:
            print("❌ No se encontraron archivos mensuales previos")
            return False

        print(f"📄 Archivo mensual más reciente: {os.path.basename(recent_file)}")

        # Leer contenido
        content = safe_file_read(recent_file)
        if not content:
            return False

        # Extraer información del archivo
        current_year, current_month = self._extract_month_info_from_file(recent_file)
        if not current_year or not current_month:
            print("❌ Error al extraer información del archivo mensual")
            return False

        # Calcular próximo mes
        next_month, next_year = self._calculate_next_month(current_month, current_year)

        print(f"📅 Creando archivo para: {next_month:02d}/{next_year}")

        # Generar contenido
        new_content = self.generator.create_monthly_topics(
            month=next_month,
            year=next_year,
            base_content=content
        )

        # Crear archivo
        new_filename = generate_filename(
            year=next_year,
            month=next_month,
            is_monthly=True,
            directory=self.directory,
        )

        if not confirm_overwrite(new_filename):
            print(MESSAGES['operation_cancelled'])
            return False

        if safe_file_write(new_filename, new_content):
            print(MESSAGES['monthly_created'].format(filename=new_filename))

            # Mostrar resumen
            summary = self.generator.create_monthly_summary(
                month=next_month,
                year=next_year,
                filename=new_filename
            )
            print(summary)
            return True

        return False

    def _extract_month_info_from_file(self, filepath: str) -> tuple[Optional[int], Optional[int]]:
        """Extrae información de mes del nombre del archivo."""
        import re

        match = re.search(r'\[(\d{4})\]\[(\d{2})\]MonthTopics\.md$', filepath)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            return year, month
        return None, None

    def _calculate_next_month(self, current_month: int, current_year: int) -> tuple[int, int]:
        """Calcula el próximo mes y año."""
        next_month = current_month + 1
        next_year = current_year

        if next_month > 12:
            next_month = 1
            next_year += 1

        return next_month, next_year

    def list_recent_months(self, count: int = 5) -> None:
        """Lista los últimos archivos mensuales."""
        monthly_files = self.finder.list_monthly_files()

        if not monthly_files:
            print("📋 No se encontraron archivos mensuales")
            return

        print(f"📋 Últimos {min(count, len(monthly_files))} archivos mensuales:")
        for filepath, year, month in monthly_files[-count:]:
            filename = os.path.basename(filepath)
            print(f"  {filename} -> {month:02d}/{year}")



def create_monthly_interactive() -> bool:
    """Función interactiva para crear archivo mensual."""
    generator = MonthlyGenerator()

    print("📅 Generador de Archivo Mensual")
    print("=" * 40)

    return generator.create_next_monthly_topics()


if __name__ == "__main__":
    create_monthly_interactive()
