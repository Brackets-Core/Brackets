#!/usr/bin/env python3
"""
Generador especializado para bitácoras semanales.
"""

import os
from datetime import datetime, timedelta
from typing import List, Optional

from brackets.config import MESSAGES
from brackets.utils.file_finder import FileFinder
from brackets.utils.content_parser import ContentParser
from brackets.utils.content_generator import ContentGenerator
from brackets.utils.legacy_utils import (
    safe_file_read, safe_file_write, confirm_overwrite,
    parse_float_input, calculate_next_week_info_from_dates,
    generate_filename, print_calculated_dates
)
from brackets.config import WORKING_DIRECTORY
from brackets.models.entities import WeekSchedule, DaySchedule
from brackets.managers.entity_manager import EntityManager
from brackets.generators.bitacora_renderer import BitacoraRenderer
from brackets.managers.settings_manager import get_global_settings_manager


class WeeklyGenerator:
    """Clase para generar bitácoras semanales."""

    def __init__(self, directory: str = ".", settings=None):
        self.directory = directory
        self.settings = settings or get_global_settings_manager(directory)
        self.finder = FileFinder(directory)
        self.generator = ContentGenerator(self.settings)
        data_dir = os.path.join(self.directory, "data")
        if os.path.exists(data_dir):
            self.entity_manager = EntityManager(data_dir)
        else:
            self.entity_manager = None

    def create_next_weekly_bitacora(self, ask_for_weight: bool = True) -> bool:
        """Crea la siguiente bitácora semanal basada en la más reciente."""

        # Encontrar archivo más reciente
        recent_file = self.finder.get_most_recent_weekly()
        if not recent_file:
            print(MESSAGES['no_files'])
            return False

        print(f"📄 Archivo más reciente encontrado: {os.path.basename(recent_file)}")

        # Leer contenido
        content = safe_file_read(recent_file)
        if not content:
            return False

        # Analizar contenido
        parser = ContentParser(content)
        year, month, current_week, current_weight = parser.extract_week_info_from_filename(recent_file)

        if not current_week:
            print("❌ No se pudo extraer la información de la semana del archivo")
            return False

        # Mostrar información actual
        self._print_current_info(recent_file, year, month, current_week, current_weight)

        # Extraer tareas pendientes (ahora incluye todas las secciones con jerarquía)
        pending_tasks = parser.extract_pending_tasks()

        print(f"📋 Tareas pendientes encontradas: {len(pending_tasks)}")

        # Pedir peso si es necesario
        new_weight = None
        if ask_for_weight:
            weight_input = input(f"⚖️ Ingresa tu peso para la semana siguiente (Enter para omitir): ").strip()
            new_weight = parse_float_input(weight_input)
        # Calcular fechas usando calendario ISO (derivado del nombre del archivo)
        next_week_dates = self._calculate_next_week_dates_iso(year, current_week)
        print_calculated_dates(0, next_week_dates)

        # Calcular próxima semana basándose en las fechas reales
        next_year, next_month, next_week = calculate_next_week_info_from_dates(next_week_dates, current_week)

        print(f"📅 Nueva semana calculada: Semana {next_week}, {next_month:02d}/{next_year}")

        # Generar contenido vía EntityManager y BitacoraRenderer si hay datos relacionales
        if self.entity_manager and os.path.exists(self.entity_manager.tables_dir):
            days = []
            for d in next_week_dates:
                if self.settings and hasattr(self.settings, "get_location_for_date"):
                    loc_emoji, loc_note = self.settings.get_location_for_date(d, next_week)
                else:
                    from brackets.utils.legacy_utils import get_work_location
                    loc_emoji = get_work_location(d.weekday(), next_week, d)
                    loc_note = None
                days.append(DaySchedule(day_number=d.day, location_emoji=loc_emoji, location_note=loc_note, task_ids=[]))

            new_week_schedule = WeekSchedule(
                year=next_year,
                month=next_month,
                week_number=next_week,
                weight=new_weight,
                topics_task_ids=[],
                note_ids=[],
                days=days
            )

            prev_week = self.entity_manager.load_week(year, current_week)
            if prev_week:
                prev_prev_week_num = current_week - 1
                prev_prev_year = year
                if prev_prev_week_num <= 0:
                    prev_prev_year = year - 1
                    prev_prev_week_num = 52
                prev_prev_week = self.entity_manager.load_week(prev_prev_year, prev_prev_week_num)
                self.entity_manager.rollover_week_to_new_week(prev_week, new_week_schedule, prev_prev_week)

            # Inyectar tareas y reuniones recurrentes
            self.entity_manager.apply_recurring_tasks(new_week_schedule)

            self.entity_manager.save_week(new_week_schedule)
            new_content = BitacoraRenderer.render_week(new_week_schedule, self.entity_manager)
        else:
            # Fallback legacy si no hay tablas relacionales
            new_content = self.generator.create_weekly_bitacora(
                pending_tasks=pending_tasks,
                week_num=next_week,
                weight=new_weight,
                dates=next_week_dates
            )

        # Crear archivo
        new_filename = generate_filename(
            year=next_year,
            month=next_month,
            week=next_week,
            directory=self.directory,
        )

        if not confirm_overwrite(new_filename):
            print(MESSAGES['operation_cancelled'])
            return False

        if safe_file_write(new_filename, new_content):
            print(MESSAGES['file_created'].format(filename=new_filename))

            # Mostrar resumen
            summary = self.generator.create_week_summary(
                week_num=next_week,
                dates=next_week_dates,
                pending_count=len(pending_tasks),
                weight=new_weight
            )
            print(summary)
            return True

        return False

    def create_next_or_manual_weekly_bitacora(self, ask_for_weight: bool = True) -> bool:
        """Crea bitácora automática o redirige a flujo manual si no hay base previa."""
        recent_file = self.finder.get_most_recent_weekly()
        if recent_file:
            return self.create_next_weekly_bitacora(ask_for_weight=ask_for_weight)

        print("ℹ️ No hay bitácoras previas. Redirigiendo al flujo manual...")
        return self.create_manual_weekly_bitacora()

    def _print_current_info(self, filepath: str, year: int, month: int, week: int, weight: Optional[float]):
        """Imprime información del archivo actual."""
        print(f"📅 Archivo: {os.path.basename(filepath)}")
        print(f"📅 Semana actual: {week}, Año: {year}, Mes: {month}")
        if weight:
            print(f"⚖️ Peso actual registrado: {weight}")

    def _get_days_per_week(self) -> int:
        """Determina el número de días por semana según configuración o tipo de vault."""
        config_path = os.path.join(self.directory, "data", "config.yaml")
        if os.path.exists(config_path):
            try:
                import yaml
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                    if "days_per_week" in cfg:
                        return int(cfg["days_per_week"])
                    if str(cfg.get("vault_type", "")).strip().lower() == "personal":
                        return 7
            except Exception:
                pass
        return 5

    def _calculate_next_week_dates_iso(self, year: int, week: int) -> List[datetime]:
        """Calcula los días de la siguiente semana usando calendario ISO.

        Esta ruta evita depender de encabezados diarios parseados del archivo,
        que pueden variar por emojis/ediciones manuales y provocar saltos de día.
        """
        if not year or not week:
            raise ValueError("Año/semana ISO inválidos")

        try:
            current_monday = datetime.fromisocalendar(year, week, 1)
            next_monday = current_monday + timedelta(days=7)
        except ValueError:
            # Manejo de semanas fuera de rango (ej: pedir semana 53 en año de 52)
            # Avanzamos al primer día del año siguiente
            next_monday = datetime.fromisocalendar(year + 1, 1, 1)

        days_count = self._get_days_per_week()
        return [next_monday + timedelta(days=i) for i in range(days_count)]

    def create_manual_weekly_bitacora(self) -> bool:
        """Crea una bitácora semanal de forma manual sin necesidad de archivo previo."""
        from datetime import datetime

        print("\n📝 CREAR BITÁCORA SEMANAL MANUAL")
        print("=" * 40)

        # Pedir año
        year_input = input("📅 Año (Enter para actual): ").strip()
        year = int(year_input) if year_input else datetime.now().year

        # Pedir mes
        while True:
            month_input = input("📅 Mes (1-12): ").strip()
            try:
                month = int(month_input)
                if 1 <= month <= 12:
                    break
                print("❌ Mes debe estar entre 1 y 12")
            except ValueError:
                print("❌ Ingresa un número válido")

        # Pedir número de semana
        while True:
            week_input = input("📅 Número de semana (1-53): ").strip()
            try:
                week = int(week_input)
                if 1 <= week <= 53:
                    break
                print("❌ Semana debe estar entre 1 y 53")
            except ValueError:
                print("❌ Ingresa un número válido")

        # Pedir peso (opcional)
        weight_input = input("⚖️ Peso inicial (Enter para omitir): ").strip()
        weight = parse_float_input(weight_input) if weight_input else None

        # Generar nombre de archivo
        filename = generate_filename(
            year=year,
            month=month,
            week=week,
            directory=self.directory
        )

        # Pedir ubicaciones de trabajo para cada día
        print("\n🏠 PATRONES DE TRABAJO")
        print("Ingresa la ubicación para cada día:")
        print("  1 = 🏠 Casa")
        print("  2 = 🚗 Oficina")
        print("  3 = 🏖️ Vacaciones/Festivo")
        print("-" * 40)

        days_count = self._get_days_per_week()
        weekdays_all = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        weekdays = weekdays_all[:days_count]
        try:
            target_monday = datetime.fromisocalendar(year, week, 1)
            day_emoji_map = {i: (target_monday + timedelta(days=i)).day for i in range(days_count)}
        except Exception:
            day_emoji_map = {i: (29 + i) for i in range(days_count)}

        work_locations = {}
        for i, day in enumerate(weekdays):
            while True:
                location = input(f"{day} ({day_emoji_map[i]}): (1/2/3 o emoji): ").strip()
                choice_map = {
                    '1': '🏠',
                    '2': '🚗',
                    '3': '🏖️',
                    '🏠': '🏠',
                    '🚗': '🚗',
                    '🏖️': '🏖️',
                }
                if location in choice_map:
                    work_locations[day_emoji_map[i]] = choice_map[location]
                    break
                print("❌ Ingresa 1/2/3 o 🏠/🚗/🏖️")

        # Generar contenido
        content = self.generator.generate_weekly_content_manual(
            year=year,
            month=month,
            week=week,
            weight=weight,
            work_locations=work_locations,
            days_count=days_count
        )

        if not content:
            print("❌ Error generando contenido")
            return False

        print(f"\n📄 Archivo a crear: {os.path.basename(filename)}")
        print(f"📊 Año: {year}, Mes: {month:02d}, Semana: {week}")

        # Confirmar sobrescritura si existe
        if os.path.exists(filename):
            if not confirm_overwrite(os.path.basename(filename)):
                print(MESSAGES['operation_cancelled'])
                return False

        # Guardar archivo
        if safe_file_write(filename, content):
            print(f"\n✅ {MESSAGES['file_created'].format(filename=os.path.basename(filename))}")
            return True

        return False

    def list_recent_weeks(self, count: int = 5) -> None:
        """Lista las últimas bitácoras semanales."""
        weekly_files = self.finder.list_weekly_files()

        if not weekly_files:
            print("📅 No se encontraron bitácoras semanales")
            return

        print(f"📅 Últimas {min(count, len(weekly_files))} bitácoras semanales:")
        for filepath, year, month, week in weekly_files[-count:]:
            filename = os.path.basename(filepath)
            print(f"  {filename} -> Semana {week}, {month:02d}/{year}")


def create_weekly_interactive() -> bool:
    """Función interactiva para crear bitácora semanal."""
    generator = WeeklyGenerator()

    print("🗓️ Generador de Bitácora Semanal")
    print("=" * 40)

    return generator.create_next_weekly_bitacora()


if __name__ == "__main__":
    create_weekly_interactive()
