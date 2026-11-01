#!/usr/bin/env python3
"""
Controlador interactivo para la gestión de Tareas y Reuniones Recurrentes en Brackets.
"""

from __future__ import annotations
from datetime import datetime
from typing import Callable, Optional, List, Tuple, Any, TYPE_CHECKING

from brackets.core.menu_navigator import MenuNavigator, MenuOption
from brackets.core.menu_engine import MenuEngine
from brackets.models.entities import WeekSchedule, DaySchedule
from brackets.models.task_types import TaskTypeRegistry

if TYPE_CHECKING:
    from brackets.managers.entity_manager import EntityManager


class RecurringTasksController:
    """Gestiona la pantalla interactiva de configuración y sincronización de tareas recurrentes."""

    def __init__(
        self,
        manager: EntityManager,
        vault_root: str,
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[[str], None] = print,
        read_single_key_fn: Optional[Callable[[str], str]] = None,
        clear_screen_fn: Optional[Callable[[], None]] = None,
        sync_markdown_fn: Optional[Callable[[WeekSchedule], None]] = None,
        prompt_selection_fn: Optional[Callable[[Optional[WeekSchedule]], Tuple[Optional[str], Optional[str]]]] = None,
        menu_engine: Optional[MenuEngine] = None,
    ):
        self.manager = manager
        self.vault_root = vault_root
        self.menu_engine = menu_engine or MenuEngine(self.vault_root)
        self.input = input_fn
        self.print = print_fn
        self.read_single_key = read_single_key_fn
        self.clear_screen = clear_screen_fn or (lambda: None)
        self._sync_markdown = sync_markdown_fn or (lambda w: None)
        self.prompt_selection_fn = prompt_selection_fn

    def manage_recurring_menu(self, week: WeekSchedule, day: DaySchedule) -> Optional[str]:
        """Subpantalla interactiva para gestionar Tareas y Reuniones Recurrentes."""
        while True:
            recs = self.manager.list_recurring_tasks(active_only=False)
            default_options = [
                MenuOption("1", "➕ Nueva Tarea / Reunión Recurrente", "new_rec", aliases=["n", "+"]),
                MenuOption("2", "⏯️  Pausar / Activar Recurrencia", "toggle_rec", aliases=["p", "t"]),
                MenuOption("3", "🗑️  Eliminar Definición Recurrente", "delete_rec", aliases=["d"]),
                MenuOption("4", "⚡ Inyectar / Sincronizar en esta semana", "sync_rec", aliases=["s"]),
            ]
            options = self.menu_engine.get_menu_options("recurring", default_options=default_options)
            title = self.menu_engine.menu_title("recurring", "🔄 G E S T I Ó N  D E  R E C U R R E N T E S  Y  R E U N I O N E S")

            self.clear_screen()
            self.print("=" * 65)
            self.print("🔄 TAREAS Y REUNIONES RECURRENTES CONFIGURADAS:")
            self.print("=" * 65)
            if recs:
                wday_names = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
                for idx, r in enumerate(recs, start=1):
                    status_lbl = "✅ Activa" if r.active else "⏸️ Pausada"
                    if r.recurrence_type == "weekly_days":
                        days_str = ", ".join(wday_names[d] for d in r.days_of_week if 0 <= d <= 6)
                        pat = f"Días: [{days_str}]"
                    elif r.recurrence_type == "interval_weeks":
                        day_lbl = wday_names[r.day_of_week] if 0 <= r.day_of_week <= 6 else "Día"
                        pat = f"Cada {r.interval_weeks} sem ({day_lbl}, base W{r.base_week})"
                    else:
                        pat = "Semanal sin día fijo"

                    proj_lbl = f" [{r.project_id}]" if r.project_id else ""
                    self.print(f"  [{idx}] {r.title}{proj_lbl} ➔ {pat} | {status_lbl}")
            else:
                self.print("  (No hay tareas recurrentes configuradas todavía)")
            self.print("-" * 65)

            navigator = MenuNavigator(
                title=title,
                options=options,
                show_back=True,
                show_main_menu=True,
                print_fn=self.print,
                input_fn=self.input,
                read_single_key_fn=self.read_single_key,
                clear_screen_fn=lambda: None,
            )

            nav_status, opt = navigator.prompt()
            if nav_status in ("back", "menu", "exit"):
                return nav_status

            if opt:
                if opt.action_id == "new_rec":
                    self._action_create_recurring(week)
                elif opt.action_id == "toggle_rec":
                    self._action_toggle_recurring(recs)
                elif opt.action_id == "delete_rec":
                    self._action_delete_recurring(recs)
                elif opt.action_id == "sync_rec":
                    count = self.manager.apply_recurring_tasks(week)
                    if count > 0:
                        self._sync_markdown(week)
                        self.print(f"\n✅ Se han inyectado {count} tareas recurrentes en la semana.")
                    else:
                        self.print("\nℹ️ Todas las tareas recurrentes ya estaban presentes en la semana.")
                    self.input("Presiona Enter para continuar...")

    def _action_create_recurring(self, week: WeekSchedule) -> None:
        title = self.input("\n📝 Título de la reunión o tarea recurrente (ej: Daily S^3): ").strip()
        if not title:
            return

        proj_id, topic_id = None, None
        if self.prompt_selection_fn:
            proj_id, topic_id = self.prompt_selection_fn(week)

        detected_type, cleaned_title = TaskTypeRegistry.detect_task_type_and_clean_title(title)
        final_title = cleaned_title if cleaned_title else title
        specs = TaskTypeRegistry.get_all_specs()

        # Si no detectó prefijo exacto, buscar si el título contiene alguna palabra clave de los prefijos
        if not detected_type or detected_type == "task":
            title_lower = final_title.lower()
            for spec in specs:
                if any(p.strip().rstrip(":").lower() in title_lower for p in spec.text_prefixes if p.strip()):
                    detected_type = spec.key
                    break

        type_options = [(sp.key, sp) for sp in specs]
        self.print("\n¿Qué tipo de elemento es?")
        default_idx = 1
        for idx, (k, sp) in enumerate(type_options, start=1):
            pre = f"{sp.premoji} " if sp.premoji else ""
            self.print(f"  [{idx}] {pre}{sp.label}")
            if k == detected_type:
                default_idx = idx

        t_type_input = self.input(f"Opción ({default_idx} por defecto): ").strip()
        if not t_type_input:
            task_type = type_options[default_idx - 1][0]
        else:
            try:
                chosen_idx = int(t_type_input)
                if 1 <= chosen_idx <= len(type_options):
                    task_type = type_options[chosen_idx - 1][0]
                else:
                    task_type = detected_type or "task"
            except ValueError:
                task_type = detected_type or "task"

        self.print("\nSelecciona tipo de recurrencia:")
        self.print("  [1] Días fijos cada semana (ej: Lunes, Miércoles, Viernes)")
        self.print("  [2] Cada N semanas en día concreto (ej: Viernes cada 4 semanas)")
        self.print("  [3] Tareas de la Semana (sin día fijo)")
        t_choice = self.input("Opción (1 por defecto): ").strip()

        if t_choice == "2":
            interval_str = self.input("¿Cada cuántas semanas? (ej: 4): ").strip()
            interval = int(interval_str) if interval_str.isdigit() else 4
            self.print("¿En qué día de la semana? [1] Lunes [2] Martes [3] Miércoles [4] Jueves [5] Viernes")
            day_choice = self.input("Día (5 por defecto): ").strip()
            wday_map = {"1": 0, "2": 1, "3": 2, "4": 3, "5": 4}
            wday = wday_map.get(day_choice, 4)
            base_w_str = self.input(f"Semana base de inicio ({week.week_number} por defecto): ").strip()
            base_w = int(base_w_str) if base_w_str.isdigit() else week.week_number

            rec = self.manager.create_recurring_task(
                title=final_title,
                recurrence_type="interval_weeks",
                interval_weeks=interval,
                base_week=base_w,
                day_of_week=wday,
                project_id=proj_id,
                topic_id=topic_id,
                task_type=task_type
            )
        elif t_choice == "3":
            rec = self.manager.create_recurring_task(
                title=final_title,
                recurrence_type="week_tasks",
                project_id=proj_id,
                topic_id=topic_id,
                task_type=task_type
            )
        else:
            self.print("Indica los días separados por comas:")
            self.print("  Ej: '1,3,5' o 'l,x,v' para Lunes, Miércoles y Viernes")
            days_input = self.input("Días (1,3,5 por defecto): ").strip().lower()
            days_list = []
            if not days_input or "1,3,5" in days_input or "l,x,v" in days_input:
                days_list = [0, 2, 4]
            else:
                for token in days_input.replace(" ", "").split(","):
                    if token in ("1", "l", "lun", "lunes"):
                        days_list.append(0)
                    elif token in ("2", "m", "mar", "martes"):
                        days_list.append(1)
                    elif token in ("3", "x", "mie", "miercoles"):
                        days_list.append(2)
                    elif token in ("4", "j", "jue", "jueves"):
                        days_list.append(3)
                    elif token in ("5", "v", "vie", "viernes"):
                        days_list.append(4)
                    elif token in ("6", "s", "sab", "sabado"):
                        days_list.append(5)
                    elif token in ("7", "d", "dom", "domingo"):
                        days_list.append(6)
            if not days_list:
                days_list = [0, 2, 4]

            rec = self.manager.create_recurring_task(
                title=final_title,
                recurrence_type="weekly_days",
                days_of_week=sorted(list(set(days_list))),
                project_id=proj_id,
                topic_id=topic_id,
                task_type=task_type
            )

        # Aplicar de inmediato a la semana en curso
        injected = self.manager.apply_recurring_tasks(week)
        if injected > 0:
            self._sync_markdown(week)
        self.print(f"\n✅ Recurrencia '{rec.title}' creada con éxito.")
        self.input("Presiona Enter para continuar...")

    def _action_toggle_recurring(self, recs: List[Any]) -> None:
        if not recs:
            self.print("\n⚠️ No hay recurrencias para pausar o activar.")
            self.input("Presiona Enter para continuar...")
            return
        choice = self.input(f"\nSelecciona número de recurrencia (1-{len(recs)}, 0 para cancelar): ").strip()
        try:
            idx = int(choice)
            if 1 <= idx <= len(recs):
                target = recs[idx - 1]
                updated = self.manager.toggle_recurring_task(target.id)
                if updated:
                    state_lbl = "activada" if updated.active else "pausada"
                    self.print(f"✅ Recurrencia '{updated.title}' {state_lbl}.")
                    self.input("Presiona Enter para continuar...")
        except ValueError:
            pass

    def _action_delete_recurring(self, recs: List[Any]) -> None:
        if not recs:
            self.print("\n⚠️ No hay recurrencias para eliminar.")
            self.input("Presiona Enter para continuar...")
            return
        choice = self.input(f"\nSelecciona número a eliminar (1-{len(recs)}, 0 para cancelar): ").strip()
        try:
            idx = int(choice)
            if 1 <= idx <= len(recs):
                target = recs[idx - 1]
                confirm = self.input(f"¿Seguro que deseas eliminar '{target.title}'? [s/N]: ").strip().lower()
                if confirm in ("s", "si", "y", "yes"):
                    self.manager.delete_recurring_task(target.id)
                    self.print(f"🗑️ Definición '{target.title}' eliminada.")
                    self.input("Presiona Enter para continuar...")
        except ValueError:
            pass
