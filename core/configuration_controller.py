#!/usr/bin/env python3
"""Configuration menu controller extracted from BitacoraManager."""

from typing import Callable, Optional


class ConfigurationController:
    """Handle configuration menu and related interactive flows."""

    def __init__(
        self,
        settings,
        vault_name: str,
        show_configured_menu_fn: Callable[[str, str, int, int], None],
        resolve_menu_command_fn: Callable[[str, str, int], tuple[Optional[str], int, bool]],
        clear_screen_fn: Callable[[], None],
        read_single_key_fn: Callable[[str], str],
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[..., None] = print,
    ):
        self.settings = settings
        self.vault_name = vault_name
        self.show_configured_menu = show_configured_menu_fn
        self.resolve_menu_command = resolve_menu_command_fn
        self.clear_screen = clear_screen_fn
        self.read_single_key = read_single_key_fn
        self.input = input_fn
        self.print = print_fn

    def run(self) -> None:
        """Entry point for configuration menu flow."""
        selected_index = 0
        while True:
            self.show_configured_menu("configuration", "⚙️ CONFIGURACIÓN", 50, selected_index)
            choice = self.read_single_key("Opción: ")
            command, selected_index, valid = self.resolve_menu_command("configuration", choice, selected_index)
            if not valid:
                self.print("❌ Opción inválida")
                self.input("\nPresiona Enter para continuar...")
                continue
            if command is None:
                continue

            if command == "config_view":
                self.show_overview()
                self.input("\nPresiona Enter para continuar...")
            elif command == "config_work_pattern":
                self.configure_work_pattern()
            elif command == "config_holidays":
                self.configure_holidays()
            elif command == "config_vacations":
                self.configure_vacations()
            elif command == "config_closures":
                self.configure_closures()
            elif command == "config_intensive":
                self.configure_intensive_workdays()
            elif command == "back":
                break
            else:
                self.print("❌ Opción inválida")

    def show_overview(self) -> None:
        self.clear_screen()
        self.print(f"\n👁️ CONFIGURACIÓN ACTUAL - {self.vault_name}")
        self.print("=" * 55)
        self.print(self.settings.describe_work_pattern())

        holidays = self.settings.list_holidays()
        if holidays:
            self.print("\nFestivos configurados:")
            for i, item in enumerate(holidays, 1):
                self.print(f" {i}. {item.get('date')} - {item.get('name', '')}")
        else:
            self.print("\nFestivos configurados: ninguno")

        vacations = self.settings.list_vacations()
        if vacations:
            self.print("\nVacaciones configuradas:")
            for i, item in enumerate(vacations, 1):
                self.print(f" {i}. {item.get('start')} → {item.get('end')} - {item.get('name', '')}")
        else:
            self.print("\nVacaciones configuradas: ninguna")

        closures = getattr(self.settings, "list_closures", lambda: [])()
        if closures:
            self.print("\nCierres de sede central:")
            for i, item in enumerate(closures, 1):
                self.print(f" {i}. {item.get('date')} - {item.get('name', '')}")
        else:
            self.print("\nCierres de sede central: ninguno")

        intensives = getattr(self.settings, "list_intensive_days", lambda: [])()
        if intensives:
            self.print("\nJornada intensiva configurada:")
            for i, item in enumerate(intensives, 1):
                if item.get("date"):
                    self.print(f" {i}. {item.get('date')} - {item.get('name', '')}")
                else:
                    self.print(f" {i}. {item.get('start')} → {item.get('end')} - {item.get('name', '')}")
        else:
            self.print("\nJornada intensiva configurada: ninguna")

    def configure_work_pattern(self) -> None:
        day_map = {
            "1": "monday",
            "2": "tuesday",
            "3": "wednesday",
            "4": "thursday",
            "5": "friday",
        }
        while True:
            self.clear_screen()
            self.print(f"\n🏢 PATRÓN DE TRABAJO - {self.vault_name}")
            self.print("-" * 50)
            self.print(self.settings.describe_work_pattern())
            self.print("\n1. Cambiar día específico")
            self.print("2. Configurar día alterno par/impar")
            self.print("3. Restaurar valores por defecto")
            self.print("0. Volver")
            choice = self.input("Opción: ").strip()

            if choice == "1":
                day_choice = self.input("Selecciona día (1=L, 2=M, 3=X, 4=J, 5=V): ").strip()
                day_key = day_map.get(day_choice)
                if not day_key:
                    self.print("❌ Día inválido")
                    continue
                location = self.prompt_location("Ubicación para el día")
                if not location:
                    continue
                if location == "alternating":
                    even_loc = self.prompt_location("Ubicación semana par")
                    odd_loc = self.prompt_location("Ubicación semana impar")
                    if even_loc and odd_loc:
                        self.settings.set_alternating(day_key, even_loc, odd_loc)
                        self.print("✅ Día alterno actualizado")
                else:
                    try:
                        self.settings.set_day_location(day_key, location)
                        self.print("✅ Día actualizado")
                    except Exception as e:
                        self.print(f"❌ {e}")
            elif choice == "2":
                day_choice = self.input("Día alterno (1=L,2=M,3=X,4=J,5=V): ").strip()
                day_key = day_map.get(day_choice)
                if not day_key:
                    self.print("❌ Día inválido")
                    continue
                even_loc = self.prompt_location("Ubicación semana par")
                odd_loc = self.prompt_location("Ubicación semana impar")
                if even_loc and odd_loc:
                    try:
                        self.settings.set_alternating(day_key, even_loc, odd_loc)
                        self.print("✅ Alternancia actualizada")
                    except Exception as e:
                        self.print(f"❌ {e}")
            elif choice == "3":
                self.settings.reset_defaults()
                self.print("✅ Patrón restaurado a valores por defecto")
            elif choice == "0":
                break
            else:
                self.print("❌ Opción inválida")

    def configure_holidays(self) -> None:
        while True:
            holidays = self.settings.list_holidays()
            self.clear_screen()
            self.print(f"\n🎉 FESTIVOS - {self.vault_name}")
            self.print("-" * 50)
            if holidays:
                for i, item in enumerate(holidays, 1):
                    self.print(f" {i}. {item.get('date')} - {item.get('name', '')}")
            else:
                self.print(" No hay festivos configurados")

            choice = self.input("(A)ñadir/actualizar, (E)ditar nombre, (D)elete, 0 volver: ").strip().lower()
            if choice == "0":
                break
            if choice == "a":
                date_str = self.input("Fecha (YYYY-MM-DD): ").strip()
                name = self.input("Nombre: ").strip() or "Festivo"
                try:
                    self.settings.add_or_update_holiday(date_str, name)
                    self.print("✅ Festivo guardado")
                except Exception as e:
                    self.print(f"❌ {e}")
            elif choice == "e":
                index = self.input("Número a editar: ").strip()
                try:
                    idx = int(index) - 1
                    if 0 <= idx < len(holidays):
                        name = self.input("Nuevo nombre: ").strip() or holidays[idx].get("name", "Festivo")
                        self.settings.add_or_update_holiday(holidays[idx].get("date"), name)
                        self.print("✅ Festivo actualizado")
                    else:
                        self.print("❌ Índice inválido")
                except ValueError:
                    self.print("❌ Índice inválido")
            elif choice == "d":
                index = self.input("Número a eliminar: ").strip()
                try:
                    idx = int(index) - 1
                    self.settings.delete_holiday(idx)
                    self.print("✅ Festivo eliminado")
                except ValueError:
                    self.print("❌ Índice inválido")
            else:
                self.print("❌ Opción inválida")

    def configure_vacations(self) -> None:
        while True:
            vacations = self.settings.list_vacations()
            self.clear_screen()
            self.print(f"\n🏖️ VACACIONES - {self.vault_name}")
            self.print("-" * 50)
            if vacations:
                for i, item in enumerate(vacations, 1):
                    self.print(f" {i}. {item.get('start')} → {item.get('end')} - {item.get('name', '')}")
            else:
                self.print(" No hay vacaciones configuradas")

            choice = self.input("(A)ñadir/actualizar, (E)ditar nombre, (D)elete, 0 volver: ").strip().lower()
            if choice == "0":
                break
            if choice == "a":
                start = self.input("Inicio (YYYY-MM-DD): ").strip()
                end = self.input("Fin (YYYY-MM-DD): ").strip()
                name = self.input("Nombre: ").strip() or "Vacaciones"
                try:
                    self.settings.add_or_update_vacation(start, end, name)
                    self.print("✅ Vacaciones guardadas")
                except Exception as e:
                    self.print(f"❌ {e}")
            elif choice == "e":
                index = self.input("Número a editar: ").strip()
                try:
                    idx = int(index) - 1
                    if 0 <= idx < len(vacations):
                        vac = vacations[idx]
                        name = self.input("Nuevo nombre: ").strip() or vac.get("name", "Vacaciones")
                        self.settings.add_or_update_vacation(vac.get("start"), vac.get("end"), name)
                        self.print("✅ Vacaciones actualizadas")
                    else:
                        self.print("❌ Índice inválido")
                except ValueError:
                    self.print("❌ Índice inválido")
            elif choice == "d":
                index = self.input("Número a eliminar: ").strip()
                try:
                    idx = int(index) - 1
                    self.settings.delete_vacation(idx)
                    self.print("✅ Vacaciones eliminadas")
                except ValueError:
                    self.print("❌ Índice inválido")
            else:
                self.print("❌ Opción inválida")

    def configure_closures(self) -> None:
        while True:
            closures = getattr(self.settings, "list_closures", lambda: [])()
            self.clear_screen()
            self.print(f"\n🏢 CIERRES DE SEDE CENTRAL - {self.vault_name}")
            self.print("-" * 50)
            if closures:
                for i, item in enumerate(closures, 1):
                    self.print(f" {i}. {item.get('date')} - {item.get('name', '')}")
            else:
                self.print(" No hay cierres de sede configurados")

            choice = self.input("(A)ñadir/actualizar, (D)elete, 0 volver: ").strip().lower()
            if choice == "0":
                break
            if choice == "a":
                date_str = self.input("Fecha (YYYY-MM-DD): ").strip()
                name = self.input("Nombre: ").strip() or "Cierre de sede central"
                try:
                    self.settings.add_or_update_closure(date_str, name)
                    self.print("✅ Cierre de sede guardado")
                except Exception as e:
                    self.print(f"❌ {e}")
            elif choice == "d":
                index = self.input("Número a eliminar: ").strip()
                try:
                    idx = int(index) - 1
                    self.settings.delete_closure(idx)
                    self.print("✅ Cierre eliminado")
                except ValueError:
                    self.print("❌ Índice inválido")
            else:
                self.print("❌ Opción inválida")

    def configure_intensive_workdays(self) -> None:
        while True:
            intensives = getattr(self.settings, "list_intensive_days", lambda: [])()
            self.clear_screen()
            self.print(f"\n⚡ JORNADA INTENSIVA - {self.vault_name}")
            self.print("-" * 50)
            if intensives:
                for i, item in enumerate(intensives, 1):
                    if item.get("date"):
                        self.print(f" {i}. {item.get('date')} - {item.get('name', '')}")
                    else:
                        self.print(f" {i}. {item.get('start')} → {item.get('end')} - {item.get('name', '')}")
            else:
                self.print(" No hay jornadas intensivas configuradas")

            choice = self.input("(A)ñadir día o rango, (D)elete, 0 volver: ").strip().lower()
            if choice == "0":
                break
            if choice == "a":
                start_or_date = self.input("Fecha o Inicio (YYYY-MM-DD): ").strip()
                is_range = self.input("¿Es un rango de fechas? [s/N]: ").strip().lower() in ("s", "si", "y", "yes")
                end_str = None
                if is_range:
                    end_str = self.input("Fin (YYYY-MM-DD): ").strip()
                name = self.input("Nombre (Enter para 'Jornada Intensiva'): ").strip() or "Jornada Intensiva"
                try:
                    self.settings.add_or_update_intensive_day(start_or_date, end_str, name)
                    self.print("✅ Jornada intensiva guardada")
                except Exception as e:
                    self.print(f"❌ {e}")
            elif choice == "d":
                index = self.input("Número a eliminar: ").strip()
                try:
                    idx = int(index) - 1
                    self.settings.delete_intensive_day(idx)
                    self.print("✅ Entrada eliminada")
                except ValueError:
                    self.print("❌ Índice inválido")
            else:
                self.print("❌ Opción inválida")

    def prompt_location(self, label: str) -> Optional[str]:
        self.print(f"{label}: 1=🏠 Casa, 2=🚗 Oficina, 3=💻 Remoto, 4=Alterna par/impar")
        value = self.input("Elige opción: ").strip()
        mapping = {
            "1": "home",
            "2": "office",
            "3": "remote",
            "4": "alternating",
        }
        if value not in mapping:
            self.print("❌ Opción inválida")
            return None
        return mapping[value]
