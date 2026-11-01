#!/usr/bin/env python3
"""
Controlador del Hub Diario Interactivo (CLI Dashboard) para Brackets.
"""

from __future__ import annotations
import os
import re
import sys
from datetime import datetime
from typing import Callable, Optional, List, Tuple

from brackets.models.entities import WeekSchedule, DaySchedule, Task, Note
from brackets.managers.entity_manager import EntityManager
from brackets.generators.bitacora_renderer import BitacoraRenderer
from brackets.utils.legacy_utils import generate_filename
from brackets.core.menu_navigator import MenuNavigator, MenuOption, KEY_ENTER, KEY_ESC
from brackets.core.menu_engine import MenuEngine


class DailyHubController:
    """Gestiona la pantalla interactiva del día actual y las acciones rápidas por teclado."""

    def __init__(
        self,
        vault_root: str,
        entity_manager: Optional[EntityManager] = None,
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[..., None] = print,
        read_single_key_fn: Optional[Callable[[str], str]] = None,
        clear_screen_fn: Optional[Callable[[], None]] = None,
        menu_engine: Optional[MenuEngine] = None,
    ):
        self.vault_root = os.path.abspath(vault_root)
        self.data_dir = os.path.join(self.vault_root, "data")
        self.notes_root = self.vault_root
        self.menu_engine = menu_engine or MenuEngine(self.vault_root)
        self.input = input_fn
        self.print = print_fn
        if read_single_key_fn is not None:
            self.read_single_key = read_single_key_fn
        elif input_fn is not None and input_fn is not input:
            self.read_single_key = lambda prompt="": self.input(prompt)
        else:
            self.read_single_key = None
        self.clear_screen = clear_screen_fn or (lambda: None)

        self.active_day_number: Optional[int] = None

        if entity_manager:
            self.manager = entity_manager
        else:
            # Si no existen las tablas en data/, usar mock o inicializar
            tables_dir = os.path.join(self.data_dir, "tables")
            if not os.path.exists(tables_dir):
                # Fallback al directorio mock si existe para demos
                mock_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mock")
                if os.path.exists(mock_dir):
                    self.manager = EntityManager(mock_dir)
                else:
                    self.manager = EntityManager(self.data_dir)
            else:
                self.manager = EntityManager(self.data_dir)

        from brackets.managers.settings_manager import get_global_settings_manager
        self.settings = get_global_settings_manager(self.vault_root)
        self.vault_type = self._get_vault_type()

    def _get_vault_type(self) -> str:
        """Determina el tipo de vault configurado ('work', 'personal', 'project')."""
        config_path = os.path.join(self.vault_root, "data", "config.yaml")
        if os.path.exists(config_path):
            try:
                import yaml
                with open(config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    return str(data.get("vault_type", "work")).strip().lower()
            except Exception:
                pass
        return "work"

    def _get_active_week_and_day(self) -> Tuple[Optional[WeekSchedule], Optional[DaySchedule]]:
        """Determina la semana y el día activo para la jornada actual."""
        now = datetime.now()
        iso_year, iso_week, _ = now.isocalendar()
        today_day = now.day

        # Intentar cargar la semana actual
        week = self.manager.load_week(iso_year, iso_week)
        if not week:
            # Si no hay semana actual en disco, buscar la más reciente en weeks_dir
            if hasattr(self.manager, "weeks_dir") and os.path.exists(self.manager.weeks_dir):
                week_files = sorted([f for f in os.listdir(self.manager.weeks_dir) if re.match(r'^\d{4}-W\d{2}\.yaml$', f)])
                if week_files:
                    last_fn = week_files[-1]
                    m = re.match(r'^(\d{4})-W(\d{2})\.yaml$', last_fn)
                    if m:
                        week = self.manager.load_week(int(m.group(1)), int(m.group(2)))
            if not week and self.manager.weeks:
                last_key = sorted(self.manager.weeks.keys())[-1]
                week = self.manager.weeks[last_key]
            elif not week:
                return None, None

        if not week or not week.days:
            return None, None

        # Si el usuario ha fijado un día activo, buscarlo
        if self.active_day_number is not None:
            for day in week.days:
                if day.day_number == self.active_day_number:
                    return week, day

        # Buscar el día de hoy dentro de la semana
        for day in week.days:
            if day.day_number == today_day:
                self.active_day_number = day.day_number
                return week, day

        # Si hoy no está en los días de la semana (ej: fin de semana), usar el último día disponible
        active_day = week.days[-1]
        self.active_day_number = active_day.day_number
        return week, active_day

    def _get_target_md_filepath(self, week: WeekSchedule) -> str:
        """Calcula la ruta del archivo Markdown correspondiente a la semana."""
        return generate_filename(
            year=week.year,
            month=week.month,
            week=week.week_number,
            directory=self.notes_root
        )

    def _sync_markdown(self, week: WeekSchedule) -> None:
        """Regenera y guarda el archivo Markdown de la semana."""
        md_path = self._get_target_md_filepath(week)
        BitacoraRenderer.render_and_save_week(week, self.manager, md_path)

    def prompt_project_selection(self) -> Optional[str]:
        """Muestra la lista de proyectos para asociar a una tarea, nota o referencia."""
        projects = self.manager.list_projects()
        self.print("\n📁 VINCULAR A PROYECTO:")
        if projects:
            for idx, p in enumerate(projects, start=1):
                self.print(f"  [{idx}] {p.id} ({p.name})")
        else:
            self.print("  (No hay proyectos registrados)")
        self.print("  [0] Ninguno / Sin vincular")
        self.print("  [+] Crear y vincular nuevo proyecto")

        p_choice = self.input("Selecciona proyecto (0 por defecto): ").strip()
        if not p_choice or p_choice in ("0", "n", "no"):
            return None

        if p_choice == "+":
            new_pid = self.input("Código del nuevo proyecto (ej: PROJ_ALPHA): ").strip()
            if new_pid:
                new_pname = self.input(f"Nombre descriptivo para '{new_pid}': ").strip()
                p_obj = self.manager.ensure_project(new_pid, name=new_pname)
                return p_obj.id
            return None

        try:
            p_idx = int(p_choice)
            if 1 <= p_idx <= len(projects):
                return projects[p_idx - 1].id
        except ValueError:
            # Si el usuario escribe directamente el nombre/código
            for p in projects:
                if p_choice.upper() in (p.id.upper(), p.name.upper()):
                    return p.id

        return None

    def prompt_topic_or_project_selection(self, week: Optional[WeekSchedule] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Permite vincular a un Topic (que hereda su proyecto) o directamente a un Proyecto.
        Devuelve (project_id, topic_id).
        """
        topics = []
        if week and week.topic_ids:
            for tid in week.topic_ids:
                top = self.manager.topics.get(tid)
                if top:
                    topics.append(top)

        projects = self.manager.list_projects()

        self.print("\n🎯 ASIGNACIÓN JERÁRQUICA (Proyecto / Topic):")
        opt_idx = 1
        topic_map = {}
        if topics:
            self.print("  Topics de la semana:")
            for top in topics:
                self.print(f"    [{opt_idx}] 🎯 {top.title} ([{top.project_id}])")
                topic_map[str(opt_idx)] = top
                opt_idx += 1
        else:
            self.print("  (No hay topics definidos para esta semana)")

        proj_map = {}
        if projects:
            self.print("  Proyectos directos:")
            for p in projects:
                self.print(f"    [{opt_idx}] 📁 {p.id} ({p.name})")
                proj_map[str(opt_idx)] = p
                opt_idx += 1

        self.print("    [0] Ninguno / Sin vincular")
        self.print("    [+] Crear nuevo Topic o Proyecto")

        choice = self.input("Selecciona opción (0 por defecto): ").strip()
        if not choice or choice in ("0", "n", "no"):
            return None, None

        if choice == "+":
            sub_choice = self.input("¿Crear [t] Topic o [p] Proyecto?: ").strip().lower()
            if sub_choice.startswith("p"):
                new_pid = self.input("Código del nuevo proyecto (ej: PROJ_ALPHA): ").strip()
                if new_pid:
                    new_pname = self.input(f"Nombre descriptivo para '{new_pid}': ").strip()
                    p_obj = self.manager.ensure_project(new_pid, name=new_pname)
                    return p_obj.id, None
            else:
                top_title = self.input("Título del nuevo Topic: ").strip()
                if top_title:
                    pid = self.prompt_project_selection() or "GENERAL"
                    topic = self.manager.create_topic(
                        title=top_title,
                        project_id=pid,
                        year=week.year if week else None,
                        week_num=week.week_number if week else None
                    )
                    if week and topic.id not in week.topic_ids:
                        week.topic_ids.append(topic.id)
                        self.manager.save_week(week)
                        self._sync_markdown(week)
                    return topic.project_id, topic.id
            return None, None

        if choice in topic_map:
            chosen_topic = topic_map[choice]
            return chosen_topic.project_id, chosen_topic.id
        elif choice in proj_map:
            chosen_proj = proj_map[choice]
            return chosen_proj.id, None

        for p in projects:
            if choice.upper() in (p.id.upper(), p.name.upper()):
                return p.id, None

        return None, None

    def render_dashboard(
        self,
        week: WeekSchedule,
        day: DaySchedule,
        highlighted_task_idx: Optional[int] = None
    ) -> List[str]:
        """Imprime la pantalla del Hub Diario y devuelve los IDs de tareas mostradas en orden."""
        self.clear_screen()
        today_tasks: List[Task] = []
        ordered_task_ids: List[str] = []

        # Asegurar siempre tareas pendientes primero
        self.manager.sort_day_tasks_pending_first(day)

        for tid in day.task_ids:
            task = self.manager.tasks.get(tid)
            if task:
                today_tasks.append(task)
                ordered_task_ids.append(tid)

        md_filename = os.path.basename(self._get_target_md_filepath(week))
        day_label = f"{day.location_emoji} Día {day.day_number}"
        if day.location_note:
            day_label += f" ({day.location_note})"

        self.print("=" * 65)
        self.print(f"🗓️ BITÁCORA: {md_filename} | HOY: {day_label}")
        self.print("=" * 65)

        if week.topic_ids:
            topic_title = "🎯 OBJETIVOS DE LA SEMANA:" if self.vault_type == "personal" else "🎯 TOPICS DE LA SEMANA:"
            self.print(topic_title)
            for tid in week.topic_ids:
                top = self.manager.topics.get(tid)
                if top:
                    proj_tag = f" [{top.project_id}]" if top.project_id else ""
                    self.print(f"  • {top.title}{proj_tag}")
            self.print("-" * 65)

        task_section_title = "🌱 TAREAS Y HÁBITOS DE HOY:" if self.vault_type == "personal" else "📋 TAREAS Y REUNIONES DE HOY:"
        self.print(task_section_title)
        if today_tasks:
            for idx, task in enumerate(today_tasks, start=1):
                status_box = "[x]" if task.is_done else ("[ ] ~~" if task.is_cancelled else "[ ]")
                suffix = "~~" if task.is_cancelled else ""
                proj_tag = f" [{task.project_id}]" if task.project_id else ""
                type_icon = f"{task.premoji} " if task.premoji else ""
                line_str = f"[{idx}] {status_box} {type_icon}{task.title}{proj_tag}{suffix}"

                if highlighted_task_idx == idx:
                    self.print(f"👉 {line_str}")
                else:
                    self.print(f"   {line_str}")
                if task.description:
                    for d_line in task.description.splitlines():
                        if d_line.strip():
                            self.print(f"       💬 {d_line.strip()}")
        else:
            self.print("  (No hay tareas asignadas para este día)")

        week_pending = [
            self.manager.tasks[tid] for tid in week.week_task_ids
            if tid in self.manager.tasks and self.manager.tasks[tid].is_pending and tid not in day.task_ids
        ]
        if week_pending:
            self.print("\n📋 TAREAS DE LA SEMANA (SIN DÍA FIJO):")
            for t in week_pending:
                proj_tag = f" [{t.project_id}]" if t.project_id else ""
                type_icon = f"{t.premoji} " if t.premoji else ""
                self.print(f"  ⏳ {type_icon}{t.title}{proj_tag}")
                if t.description:
                    for d_line in t.description.splitlines():
                        if d_line.strip():
                            self.print(f"       💬 {d_line.strip()}")

        self.print("\n📝 NOTAS DE LA SEMANA:")
        rendered_notes = 0
        for nid in week.note_ids:
            note = self.manager.notes.get(nid)
            if note:
                if note.title:
                    proj_tag = f" [{note.project_id}]" if note.project_id else ""
                    self.print(f"  📌 {note.title}{proj_tag}")
                    for line in note.content[:2]:
                        self.print(f"     • {line[:60]}{'...' if len(line)>60 else ''}")
                else:
                    for line in note.content[:3]:
                        self.print(f"  • {line[:60]}{'...' if len(line)>60 else ''}")
                rendered_notes += 1
        if rendered_notes == 0:
            self.print("  (Sin notas registradas)")

        # 🔗 DEFINICIONES DE LA SEMANA
        week_defs: List[Definition] = []
        if hasattr(week, "definition_ids") and week.definition_ids:
            for did in week.definition_ids:
                d = self.manager.definitions.get(did)
                if d and d not in week_defs:
                    week_defs.append(d)
        for tid in day.task_ids:
            t = self.manager.tasks.get(tid)
            if t:
                for did in BitacoraRenderer._extract_definition_ids(t.title, self.manager):
                    d = self.manager.definitions.get(did)
                    if d and d not in week_defs:
                        week_defs.append(d)
        if week_defs:
            self.print("\n🔗 DEFINICIONES / ENLACES DE LA SEMANA:")
            for d in week_defs[:6]:
                self.print(f"  • {d.id} -> {d.url}")
            if len(week_defs) > 6:
                self.print(f"  • ... ({len(week_defs) - 6} más en bitácora)")

        now = datetime.now()
        is_weekend_missing = now.weekday() in (5, 6) and not any(d.day_number == now.day for d in week.days)
        if is_weekend_missing:
            day_name = "Sábado" if now.weekday() == 5 else "Domingo"
            self.print(f"\n⚡ Fin de semana detectado: pulsa [+] para activar {day_name} {now.day} (Intervención/Guardia)")

        self.print("\n" + "=" * 65)
        if highlighted_task_idx is not None and 1 <= highlighted_task_idx <= len(today_tasks):
            sel_task = today_tasks[highlighted_task_idx - 1]
            title_disp = (sel_task.title[:45] + "...") if len(sel_task.title) > 48 else sel_task.title
            self.print(f"🎯 ACCIONES PARA [{highlighted_task_idx}]: \"{title_disp}\"")
            self.print("=" * 65)
            self.print("  [1/Enter] ✅ Marcar como completada (o desmarcar)")
            self.print("  [2]       ❌ Tachar (Desconvocada / Cancelada)")
            self.print("  [3]       📁 Asignar a Proyecto o Topic")
            self.print("  [4]       🗑️  Eliminar tarea de la bitácora")
            self.print("  [0/Esc]   ↩️  Volver al Hub")
        else:
            self.print("  [1-9] 🎯 Seleccionar tarea   [t] 📋 Tareas   [n] 📝 Notas")
            self.print("  [p] 📁 Proyectos             [d] 📅 Cambiar día   [l] 🔗 Defs")
            self.print("  [k] 🍅 Pomodoro              [y] 🔄 Sync          [0/b] Menú   [q] Salir")
        self.print("=" * 65)

        return ordered_task_ids

    def _sync_from_markdown_if_exists(self, week: WeekSchedule) -> None:
        """Sincroniza cambios hechos a mano en el .md de la semana activa hacia la BD YAML y regenera el Markdown limpio."""
        from brackets.utils.legacy_utils import generate_filename
        from brackets.managers.markdown_sync_service import MarkdownSyncService
        md_path = generate_filename(
            year=week.year,
            month=week.month,
            week=week.week_number,
            directory=self.vault_root
        )
        if os.path.exists(md_path):
            service = MarkdownSyncService(self.manager, self.vault_root)
            synced = service.sync_week_from_markdown(md_path, week.year, week.week_number)
            if self.manager.apply_calendar_to_week(week, getattr(self, "settings", None)):
                self.manager.save_week(week)
                synced = True
            if synced:
                self._sync_markdown(week)

    def _action_sync_markdown_to_yaml(self, week: WeekSchedule) -> None:
        """Sincroniza el archivo Markdown de la semana activa hacia la base de datos relacional YAML."""
        from brackets.utils.legacy_utils import generate_filename
        from brackets.managers.markdown_sync_service import MarkdownSyncService

        self.print(f"\n🔄 Sincronizando Markdown (.md) ➔ Base de datos YAML (Semana {week.week_number:02d})...")
        md_path = generate_filename(
            year=week.year,
            month=week.month,
            week=week.week_number,
            directory=self.vault_root
        )

        if not os.path.exists(md_path):
            self.print(f"⚠️ No se encontró el archivo de la semana: {os.path.basename(md_path)}")
            self.input("\nPresiona Enter para continuar...")
            return

        service = MarkdownSyncService(self.manager, self.vault_root)
        try:
            synced = service.sync_week_from_markdown(md_path, week.year, week.week_number)
            if self.manager.apply_calendar_to_week(week, getattr(self, "settings", None)):
                self.manager.save_week(week)
                synced = True
            reloaded_week = self.manager.load_week(week.year, week.week_number, reload=True)
            if reloaded_week:
                self._sync_markdown(reloaded_week)

            if synced:
                self.print(f"✅ Semana {week.week_number:02d} ({os.path.basename(md_path)}) sincronizada con éxito.")
            else:
                self.print("ℹ️ No se detectaron cambios pendientes en la semana actual.")
        except Exception as ex:
            self.print(f"❌ Error al sincronizar semana: {ex}")

        self.input("\nPresiona Enter para continuar...")

    def _action_run_pomodoro(self, week: WeekSchedule, day: DaySchedule) -> None:
        """Inicia el temporizador Pomodoro (versión Retro con Tomatín por defecto)."""
        ui_mode = "retro"
        try:
            from brackets.managers.settings_manager import SettingsManager
            cfg = SettingsManager(self.vault_root).load_config()
            pomo_cfg = cfg.get("pomodoro", {})
            if isinstance(pomo_cfg, dict):
                ui_mode = pomo_cfg.get("ui_mode", "retro")
            elif cfg.get("feature_flags", {}).get("pomodoro_retro") is False:
                ui_mode = "console"
        except Exception:
            ui_mode = "retro"

        # Si se configuró expresamente 'console' o en tests no interactivos con input mockeado:
        if ui_mode == "console" or (self.input is not input and ui_mode != "force_retro"):
            from brackets.modules.pomodoro_timer import run_pomodoro_standalone
            run_pomodoro_standalone(
                base_dir=self.vault_root,
                event_log=getattr(self, "_event_log", None),
                entity_manager=self.manager,
                current_week=week,
                current_day=day,
                input_fn=self.input,
                print_fn=self.print,
            )
        else:
            try:
                from brackets.modules.pomodoro_retro_ui import launch_retro_pomodoro
                self.print("\n🍅 Abriendo Pomodoro Retro (Tomatín)...")
                launch_retro_pomodoro(
                    vault_dir=self.vault_root,
                    event_log=getattr(self, "_event_log", None),
                    entity_manager=self.manager,
                    current_week=week,
                    current_day=day,
                )
            except Exception as ex:
                self.print(f"⚠️ No se pudo iniciar la interfaz retro ({ex}). Abriendo versión consola...")
                from brackets.modules.pomodoro_timer import run_pomodoro_standalone
                run_pomodoro_standalone(
                    base_dir=self.vault_root,
                    event_log=getattr(self, "_event_log", None),
                    entity_manager=self.manager,
                    current_week=week,
                    current_day=day,
                    input_fn=self.input,
                    print_fn=self.print,
                )

        reloaded_week = self.manager.load_week(week.year, week.week_number, reload=True)
        if reloaded_week:
            self._sync_markdown(reloaded_week)

    def run(self) -> str:
        """Bucle principal de interacción del Hub Diario. Retorna 'menu' o 'exit'."""
        first_iteration = True
        while True:
            week, day = self._get_active_week_and_day()
            if not week or not day:
                self.print("\n⚠️ No se encontró una semana activa para mostrar el Hub Diario.")
                self.print("   Crea una bitácora semanal primero o revisa data/weeks/.")
                self.input("\nPresiona Enter para ir al menú principal...")
                return "menu"

            # Sincronización automática de cambios manuales en Markdown al abrir el hub
            if first_iteration:
                self._sync_from_markdown_if_exists(week)
                if self.manager.apply_calendar_to_week(week, getattr(self, "settings", None)):
                    self.manager.save_week(week)
                    self._sync_markdown(week)
                if self.manager.apply_recurring_tasks(week) > 0:
                    self._sync_markdown(week)
                first_iteration = False

            # Arrastre automático día a día de tareas pendientes previas
            if self.manager.rollover_day_tasks(week, day.day_number) > 0:
                self._sync_markdown(week)

            ordered_task_ids = self.render_dashboard(week, day)

            if self.read_single_key:
                choice = self.read_single_key("Selecciona una opción: ").strip().lower()
            else:
                choice = self.input("Selecciona una opción: ").strip().lower()

            if choice in ("q", "exit"):
                self.clear_screen()
                self.print("\n👋 ¡Hasta luego!")
                return "exit"

            if choice in ("0", "b", "menu", "back", "volver", "__ESC__", "\x1b"):
                return "menu"

            if choice == "t":
                res = self.manage_tasks_menu(week, day, ordered_task_ids)
                if res == "menu":
                    return "menu"
                if res == "exit":
                    return "exit"
                continue

            if choice in ("n", "m"):
                from brackets.core.note_crud_controller import NoteCrudController
                crud = NoteCrudController(
                    entity_manager=self.manager,
                    current_week=week,
                    vault_root=self.vault_root,
                    input_fn=self.input,
                    print_fn=self.print,
                    clear_screen_fn=self.clear_screen,
                    read_single_key_fn=self.read_single_key
                )
                res = crud.run()
                if res == "menu":
                    return "menu"
                if res == "exit":
                    return "exit"
                continue

            if choice == "p":
                from brackets.core.project_backlog_controller import ProjectBacklogController
                ctrl = ProjectBacklogController(
                    entity_manager=self.manager,
                    current_week=week,
                    current_day=day,
                    vault_root=self.vault_root,
                    input_fn=self.input,
                    print_fn=self.print,
                    clear_screen_fn=self.clear_screen,
                    read_single_key_fn=self.read_single_key
                )
                res = ctrl.run()
                if res == "menu":
                    return "menu"
                if res == "exit":
                    return "exit"
                continue

            if choice in ("d", "s"):
                res = self.manage_day_menu(week)
                if res == "menu":
                    return "menu"
                if res == "exit":
                    return "exit"
                continue

            # Atajo directo: Selección contextual de tarea por número (1..N)
            if choice.isdigit() and choice != "0":
                task_num = int(choice)
                if 1 <= task_num <= len(ordered_task_ids):
                    self._handle_selected_task_menu(week, day, ordered_task_ids, task_num)
                    continue

            if choice == "c":
                self._action_toggle_task(week, day, ordered_task_ids)
                continue

            if choice in ("x", "cancel"):
                self._action_cancel_task(week, day, ordered_task_ids)
                continue

            if choice == "j":
                self._action_jira_task(week, day)
                continue

            if choice == "+":
                self._action_add_intervention_day(week)
                continue

            if choice == "a":
                self._action_schedule_topic(week, day)
                continue

            if choice in ("y", "sync", "md2yaml"):
                self._action_sync_markdown_to_yaml(week)
                continue

            if choice in ("l", "f", "def", "link", "links", "definicion", "definiciones"):
                res = self.manage_definitions_menu(week)
                if res in ("menu", "exit"):
                    return res
                continue

            if choice in ("k", "pomo", "pomodoro"):
                self._action_run_pomodoro(week, day)
                continue

    def manage_tasks_menu(self, week: WeekSchedule, day: DaySchedule, ordered_task_ids: List[str]) -> Optional[str]:
        """Subpantalla interactiva de gestión de tareas con MenuNavigator (Opción B)."""
        default_options = [
            MenuOption("1", "➕ Nueva Tarea HOY", "new_task", aliases=["n"]),
            MenuOption("2", "🎫 Tarea Jira HOY", "jira_task", aliases=["j"]),
            MenuOption("3", "✅ Marcar Tarea (completar / reactivar)", "toggle_task", aliases=["c", "m"]),
            MenuOption("4", "🗑️  Borrar Tarea de la Bitácora (eliminar)", "delete_task", aliases=["d", "b"]),
            MenuOption("5", "🎯 Crear nuevo Topic Semanal", "new_topic", aliases=["t"]),
            MenuOption("6", "📋 Nueva Tarea SEMANAL (sin día fijo)", "new_week_task", aliases=["w"]),
            MenuOption("7", "➡️  Agendar Tarea Semanal / Topic a HOY", "schedule_topic", aliases=["a"]),
            MenuOption("8", "✏️  Editar Tarea (texto / proyecto)", "edit_task", aliases=["e"]),
            MenuOption("9", "🔄 Tareas Recurrentes y Reuniones", "recurring_menu", aliases=["r"]),
            MenuOption("10", "🔄 Sincronizar Semana Actual (.md ➔ YAML)", "sync_markdown", aliases=["y", "sync"]),
            MenuOption("11", "🔗 Crear / Gestionar Definiciones", "manage_defs", aliases=["l", "f", "def", "link"]),
            MenuOption("12", "🍅 Iniciar Pomodoro Timer", "run_pomodoro", aliases=["k", "pomo"]),
            MenuOption("13", "❌ Cancelar / Tachar Tarea (conservar en tabla)", "cancel_task", aliases=["x", "cancel"]),
        ]
        options = self.menu_engine.get_menu_options("daily_tasks", default_options=default_options)

        base_title = self.menu_engine.menu_title("daily_tasks", f"📋 G E S T I Ó N  D E  T A R E A S  (Día {day.day_number})")
        if "{day}" in base_title:
            title = base_title.replace("{day}", str(day.day_number))
        elif f"(Día {day.day_number})" not in base_title:
            title = f"{base_title} (Día {day.day_number})"
        else:
            title = base_title

        navigator = MenuNavigator(
            title=title,
            options=options,
            show_back=True,
            show_main_menu=True,
            print_fn=self.print,
            input_fn=self.input,
            read_single_key_fn=self.read_single_key,
            clear_screen_fn=self.clear_screen,
        )

        while True:
            nav_status, opt = navigator.prompt()
            if nav_status == "back":
                return "back"
            if nav_status == "menu":
                return "menu"
            if nav_status == "exit":
                return "exit"

            if opt:
                if opt.action_id == "new_task":
                    self._action_new_task(week, day)
                    return "refresh"
                elif opt.action_id == "new_habit":
                    self._action_new_habit(week, day)
                    return "refresh"
                elif opt.action_id == "jira_task":
                    self._action_jira_task(week, day)
                    return "refresh"
                elif opt.action_id == "toggle_task":
                    self._action_toggle_task(week, day, ordered_task_ids)
                    return "refresh"
                elif opt.action_id == "cancel_task":
                    self._action_cancel_task(week, day, ordered_task_ids)
                    return "refresh"
                elif opt.action_id == "edit_task":
                    self._action_edit_task(week, day, ordered_task_ids)
                    return "refresh"
                elif opt.action_id == "delete_task":
                    self._action_delete_task(week, day, ordered_task_ids)
                    return "refresh"
                elif opt.action_id == "new_topic":
                    self._action_new_topic(week)
                    return "refresh"
                elif opt.action_id == "new_week_task":
                    self._action_new_week_task(week)
                    return "refresh"
                elif opt.action_id == "schedule_topic":
                    self._action_schedule_topic(week, day)
                    return "refresh"
                elif opt.action_id == "recurring_menu":
                    res = self.manage_recurring_menu(week, day)
                    if res in ("menu", "exit"):
                        return res
                    return "refresh"
                elif opt.action_id == "sync_markdown":
                    self._action_sync_markdown_to_yaml(week)
                    return "refresh"
                elif opt.action_id == "manage_defs":
                    res = self.manage_definitions_menu(week)
                    if res in ("menu", "exit"):
                        return res
                    return "refresh"
                elif opt.action_id == "run_pomodoro":
                    self._action_run_pomodoro(week, day)
                    return "refresh"

    def manage_day_menu(self, week: WeekSchedule) -> Optional[str]:
        """Subpantalla interactiva de selección de día y guardias con MenuNavigator (Opción B)."""
        options = []
        for idx, d in enumerate(week.days, start=1):
            is_active = " 👈 (Activo)" if d.day_number == self.active_day_number else ""
            note = f" ({d.location_note})" if d.location_note else ""
            options.append(MenuOption(
                str(idx),
                f"{d.location_emoji} Día {d.day_number}{note}{is_active}",
                f"day_{d.day_number}",
                aliases=[str(d.day_number)]
            ))
        if self.vault_type != "personal" or len(week.days) < 7:
            options.append(MenuOption(
                "+",
                "🛠️ Activar Guardia / Intervención Fin de Semana",
                "add_day",
                aliases=["intervencion", "guardia"]
            ))

        navigator = MenuNavigator(
            title=f"📅 S E L E C C I Ó N  D E  D Í A  (Semana W{week.week_number:02d} / {week.year})",
            options=options,
            show_back=True,
            show_main_menu=True,
            print_fn=self.print,
            input_fn=self.input,
            read_single_key_fn=self.read_single_key,
            clear_screen_fn=self.clear_screen,
        )

        nav_status, opt = navigator.prompt()
        if nav_status == "back":
            return "back"
        if nav_status == "menu":
            return "menu"
        if nav_status == "exit":
            return "exit"

        if opt:
            if opt.action_id == "add_day":
                self._action_add_intervention_day(week)
                return "refresh"
            elif opt.action_id.startswith("day_"):
                day_num = int(opt.action_id.replace("day_", ""))
                self.active_day_number = day_num
                return "refresh"
        return "refresh"

    def _action_new_task(self, week: WeekSchedule, day: DaySchedule) -> None:
        text = self.input("📝 Texto de la nueva tarea: ").strip()
        if text:
            from brackets.models.task_types import TaskTypeRegistry
            from brackets.utils.bitacora_parser import BitacoraMarkdownParser
            task_type, clean_title = TaskTypeRegistry.detect_task_type_and_clean_title(text)
            proj_tag, _ = BitacoraMarkdownParser.parse_project_tag(clean_title)
            if proj_tag:
                self.manager.ensure_project(proj_tag)
                proj_id = proj_tag
                topic_id = None
            else:
                proj_id, topic_id = self.prompt_topic_or_project_selection(week)
            self.manager.create_task(
                title=clean_title,
                task_type=task_type,
                project_id=proj_id,
                topic_id=topic_id,
                year=week.year,
                week_num=week.week_number,
                day_number=day.day_number
            )
            self.manager.sort_day_tasks_pending_first(day)
            self.manager.save_week(week)
            self._sync_markdown(week)

    def _action_new_habit(self, week: WeekSchedule, day: DaySchedule) -> None:
        text = self.input("🌱 Hábito a registrar HOY (ej: Meditar 10m, Leer 20p, Entrenar): ").strip()
        if text:
            if not any(text.lower().startswith(p) for p in ["hábito:", "habito:", "h:"]):
                text = f"hábito: {text}"
            from brackets.models.task_types import TaskTypeRegistry
            task_type, clean_title = TaskTypeRegistry.detect_task_type_and_clean_title(text)
            self.manager.create_task(
                title=clean_title,
                task_type=task_type or "habit",
                year=week.year,
                week_num=week.week_number,
                day_number=day.day_number
            )
            self.manager.sort_day_tasks_pending_first(day)
            self.manager.save_week(week)
            self._sync_markdown(week)
            self.print("✅ Hábito registrado para hoy.")

    def _action_jira_task(self, week: WeekSchedule, day: DaySchedule) -> None:
        ticket_code = self.input("🎫 Código Jira (ej: PROJ-1234): ").strip()
        desc = self.input("📝 Descripción de la tarea: ").strip()
        if ticket_code and desc:
            proj_id, topic_id = self.prompt_topic_or_project_selection(week)
            jira_def = self.manager.ensure_jira_definition(ticket_code)
            full_title = f"{desc} {jira_def.id}"
            self.manager.create_task(
                title=full_title,
                project_id=proj_id,
                topic_id=topic_id,
                year=week.year,
                week_num=week.week_number,
                day_number=day.day_number
            )
            self.manager.sort_day_tasks_pending_first(day)
            self.manager.save_week(week)
            self._sync_markdown(week)

    def _action_new_week_task(self, week: WeekSchedule) -> None:
        text = self.input("📝 Texto de la tarea semanal (sin día fijo): ").strip()
        if text:
            from brackets.models.task_types import TaskTypeRegistry
            task_type, clean_title = TaskTypeRegistry.detect_task_type_and_clean_title(text)
            proj_id, topic_id = self.prompt_topic_or_project_selection(week)
            self.manager.create_task(
                title=clean_title,
                task_type=task_type,
                project_id=proj_id,
                topic_id=topic_id,
                is_week_task=True,
                year=week.year,
                week_num=week.week_number
            )
            self._sync_markdown(week)
            self.print("✅ Tarea añadida a las Tareas de la Semana.")
            self.input("Presiona Enter para continuar...")

    def _print_day_tasks_list(self, day: DaySchedule, ordered_task_ids: List[str]) -> None:
        """Imprime la lista numerada de tareas del día para selección interactiva."""
        self.print(f"\n📋 TAREAS DE HOY (Día {day.day_number}):")
        for idx, tid in enumerate(ordered_task_ids, start=1):
            task = self.manager.tasks.get(tid)
            if task:
                status_box = "[x]" if task.is_done else ("[ ] ~~" if task.is_cancelled else "[ ]")
                suffix = "~~" if task.is_cancelled else ""
                proj_tag = f" [{task.project_id}]" if task.project_id else ""
                self.print(f"  [{idx}] {status_box} {task.title}{proj_tag}{suffix}")
        self.print("")

    def _action_toggle_task(
        self,
        week: WeekSchedule,
        day: DaySchedule,
        ordered_task_ids: List[str],
        target_num: Optional[int] = None
    ) -> None:
        if not ordered_task_ids:
            self.print("❌ No hay tareas para marcar.")
            self.input("Presiona Enter para continuar...")
            return
        if target_num is None:
            self._print_day_tasks_list(day, ordered_task_ids)
            num_str = self.input(f"Número de tarea (1-{len(ordered_task_ids)}) [Enter/0 para cancelar]: ").strip()
            if not num_str or num_str in ("0", "b", "c", "q"):
                return
            try:
                target_num = int(num_str)
            except ValueError:
                self.print("❌ Ingresa un número válido.")
                self.input("Presiona Enter para continuar...")
                return

        if 1 <= target_num <= len(ordered_task_ids):
            target_id = ordered_task_ids[target_num - 1]
            self.manager.toggle_task(target_id)
            self.manager.sort_day_tasks_pending_first(day)
            self.manager.save_week(week)
            self._sync_markdown(week)
        else:
            self.print("❌ Número fuera de rango.")
            self.input("Presiona Enter para continuar...")

    def _action_cancel_task(
        self,
        week: WeekSchedule,
        day: DaySchedule,
        ordered_task_ids: List[str],
        target_num: Optional[int] = None
    ) -> None:
        if not ordered_task_ids:
            self.print("❌ No hay tareas para cancelar.")
            self.input("Presiona Enter para continuar...")
            return
        if target_num is None:
            self._print_day_tasks_list(day, ordered_task_ids)
            num_str = self.input(f"Número de tarea a cancelar/tachar (1-{len(ordered_task_ids)}) [Enter/0 para cancelar]: ").strip()
            if not num_str or num_str in ("0", "b", "c", "q"):
                return
            try:
                target_num = int(num_str)
            except ValueError:
                self.print("❌ Ingresa un número válido.")
                self.input("Presiona Enter para continuar...")
                return

        if 1 <= target_num <= len(ordered_task_ids):
            target_id = ordered_task_ids[target_num - 1]
            self.manager.cancel_task(target_id)
            self.manager.sort_day_tasks_pending_first(day)
            self.manager.save_week(week)
            self._sync_markdown(week)
            self.print("✅ Tarea cancelada (tachada con ~~ en la bitácora y conservada en la base de datos).")
            self.input("Presiona Enter para continuar...")
        else:
            self.print("❌ Número fuera de rango.")
            self.input("Presiona Enter para continuar...")

    def _action_delete_task(
        self,
        week: WeekSchedule,
        day: DaySchedule,
        ordered_task_ids: List[str],
        target_num: Optional[int] = None
    ) -> None:
        if not ordered_task_ids:
            self.print("❌ No hay tareas para borrar.")
            self.input("Presiona Enter para continuar...")
            return
        if target_num is None:
            self._print_day_tasks_list(day, ordered_task_ids)
            num_str = self.input(f"Número de tarea a eliminar de la bitácora (1-{len(ordered_task_ids)}) [Enter/0 para cancelar]: ").strip()
            if not num_str or num_str in ("0", "b", "c", "q"):
                return
            try:
                target_num = int(num_str)
            except ValueError:
                self.print("❌ Ingresa un número válido.")
                self.input("Presiona Enter para continuar...")
                return

        if 1 <= target_num <= len(ordered_task_ids):
            target_id = ordered_task_ids[target_num - 1]
            task = self.manager.tasks.get(target_id)
            title = task.title if task else target_id
            confirm = self.input(f"¿Seguro que deseas eliminar '{title}' de la bitácora? (s/N): ").strip().lower()
            if confirm in ("s", "si", "y", "yes"):
                self.manager.delete_task(
                    task_id=target_id,
                    year=week.year,
                    week_num=week.week_number,
                    day_number=day.day_number
                )
                self._sync_markdown(week)
                self.print("🗑️ Tarea eliminada de la bitácora y de la base de datos.")
                self.input("Presiona Enter para continuar...")
        else:
            self.print("❌ Número fuera de rango.")
            self.input("Presiona Enter para continuar...")

    def _action_assign_task_project(
        self,
        week: WeekSchedule,
        day: DaySchedule,
        ordered_task_ids: List[str],
        target_num: int
    ) -> None:
        """Asigna o cambia el proyecto/topic de la tarea seleccionada."""
        if not (1 <= target_num <= len(ordered_task_ids)):
            return
        target_id = ordered_task_ids[target_num - 1]
        task = self.manager.tasks.get(target_id)
        if not task:
            return

        self.print(f"\n📁 ASIGNAR PROYECTO A: \"{task.title}\"")
        curr_proj = f" (Actual: [{task.project_id}])" if task.project_id else " (Sin proyecto actual)"
        self.print(f"Estado:{curr_proj}")
        proj_id, topic_id = self.prompt_topic_or_project_selection(week)

        task.project_id = proj_id
        if topic_id:
            task.topic_id = topic_id

        self.manager.save_tasks()
        self.manager.save_week(week)
        self._sync_markdown(week)
        p_name = proj_id if proj_id else "General/Ninguno"
        self.print(f"✅ Tarea vinculada al proyecto [{p_name}].")
        self.input("Presiona Enter para continuar...")

    def _handle_selected_task_menu(
        self,
        week: WeekSchedule,
        day: DaySchedule,
        ordered_task_ids: List[str],
        task_num: int
    ) -> None:
        """Muestra la vista con la tarea resaltada y el menú de acciones contextuales."""
        if not (1 <= task_num <= len(ordered_task_ids)):
            return

        self.render_dashboard(week, day, highlighted_task_idx=task_num)
        prompt_msg = "Selecciona acción ([1/Enter] Marcar, [2] Tachar, [3] Asignar, [4] Eliminar, [0] Volver): "
        if self.read_single_key:
            act = self.read_single_key(prompt_msg).strip().lower()
        else:
            act = self.input(prompt_msg).strip().lower()

        if act in ("", "1", "m", "marcar", "c", "check", "\r", "\n", "enter", "__enter__", KEY_ENTER.lower()):
            self._action_toggle_task(week, day, ordered_task_ids, target_num=task_num)
        elif act in ("2", "x", "cancel", "tachar", "cancelar"):
            self._action_cancel_task(week, day, ordered_task_ids, target_num=task_num)
        elif act in ("3", "a", "p", "asignar", "proyecto"):
            self._action_assign_task_project(week, day, ordered_task_ids, target_num=task_num)
        elif act in ("4", "d", "e", "borrar", "eliminar"):
            self._action_delete_task(week, day, ordered_task_ids, target_num=task_num)
        elif act in ("0", "b", "back", "volver", "q", "__esc__", "\x1b", KEY_ESC.lower()):
            return

    def _action_edit_task(
        self,
        week: WeekSchedule,
        day: DaySchedule,
        ordered_task_ids: List[str],
        target_num: Optional[int] = None
    ) -> None:
        if not ordered_task_ids:
            self.print("❌ No hay tareas para editar.")
            self.input("Presiona Enter para continuar...")
            return

        if target_num is None:
            self._print_day_tasks_list(day, ordered_task_ids)
            num_str = self.input(f"Número de tarea a editar (1-{len(ordered_task_ids)}) [Enter/0 para cancelar]: ").strip()
            if not num_str or num_str in ("0", "b", "c", "q"):
                return
            try:
                target_num = int(num_str)
            except ValueError:
                self.print("❌ Ingresa un número válido.")
                self.input("Presiona Enter para continuar...")
                return

        if 1 <= target_num <= len(ordered_task_ids):
            target_id = ordered_task_ids[target_num - 1]
            task = self.manager.tasks.get(target_id)
            if not task:
                self.print("❌ Tarea no encontrada.")
                self.input("Presiona Enter para continuar...")
                return

            self.print(f"\n✏️ Tarea seleccionada: [{task.project_id or 'GENERAL'}] {task.title}")
            new_title = self.input("Nuevo texto (Enter para mantener actual): ").strip()
            if new_title:
                task.title = new_title

            change_proj = self.input(f"¿Cambiar proyecto actual '{task.project_id or 'GENERAL'}'? (s/N): ").strip().lower()
            if change_proj in ("s", "si", "y", "yes"):
                new_proj = self.prompt_project_selection()
                if new_proj:
                    task.project_id = new_proj

            self.manager.save_tasks()
            self._sync_markdown(week)
            self.print(f"✅ Tarea actualizada: [{task.project_id or 'GENERAL'}] {task.title}")
            self.input("Presiona Enter para continuar...")
        else:
            self.print("❌ Número fuera de rango.")
            self.input("Presiona Enter para continuar...")

    def _action_new_topic(self, week: WeekSchedule) -> None:
        text = self.input("📝 Texto del nuevo Topic semanal: ").strip()
        if text:
            proj_id = self.prompt_project_selection() or "GENERAL"
            topic = self.manager.create_topic(
                title=text,
                project_id=proj_id,
                year=week.year,
                week_num=week.week_number
            )
            self._sync_markdown(week)
            self.print(f"✅ Topic añadido a la semana: [{topic.project_id}] {topic.title}")
            self.input("Presiona Enter para continuar...")

    def _action_schedule_topic(self, week: WeekSchedule, day: DaySchedule) -> None:
        available_ids = list(week.week_task_ids) + list(week.topics_task_ids)
        seen = set()
        available_topics = []
        for tid in available_ids:
            if tid not in seen and tid in self.manager.tasks:
                seen.add(tid)
                t = self.manager.tasks[tid]
                if t.is_pending and tid not in day.task_ids:
                    available_topics.append(t)

        if not available_topics:
            self.print("\n⚠️ No hay tareas semanales o topics pendientes disponibles para agendar a hoy.")
            self.input("Presiona Enter para continuar...")
            return

        self.print(f"\n📋 TAREAS Y TOPICS SEMANALES DISPONIBLES PARA AGENDAR AL DÍA {day.day_number}:")
        for idx, t in enumerate(available_topics, start=1):
            top_tag = f" 🎯[{self.manager.topics[t.topic_id].title}]" if (t.topic_id and t.topic_id in self.manager.topics) else ""
            proj_tag = f" [{t.project_id}]" if t.project_id else ""
            self.print(f"  [{idx}] {t.title}{top_tag}{proj_tag}")

        t_choice = self.input(f"Selecciona elemento a agendar a HOY (1-{len(available_topics)}, 0 para cancelar): ").strip()
        try:
            t_idx = int(t_choice)
            if 1 <= t_idx <= len(available_topics):
                chosen_topic = available_topics[t_idx - 1]
                self.manager.assign_topic_to_day(week, chosen_topic.id, day.day_number)
                self._sync_markdown(week)
                self.print(f"✅ '{chosen_topic.title}' agendado para HOY (Día {day.day_number}).")
                self.input("Presiona Enter para continuar...")
        except ValueError:
            pass

    def _action_add_intervention_day(self, week: WeekSchedule) -> None:
        now = datetime.now()
        def_day = now.day if now.weekday() in (5, 6) else (week.days[-1].day_number + 1)
        num_input = self.input(f"Número de día a añadir ({def_day} por defecto): ").strip()
        try:
            add_num = int(num_input) if num_input else def_day
        except ValueError:
            add_num = def_day

        from brackets.managers.settings_manager import SettingsManager
        loc_options = [("🛠️", "Intervención")]
        try:
            sm = SettingsManager(self.vault_root)
            locations_dict = sm.get_locations()
            labels = {
                "home": "Teletrabajo",
                "office": "Oficina",
                "remote": "Remoto",
                "off": "Día libre",
            }
            for loc_key, loc_emoji in locations_dict.items():
                lbl = labels.get(loc_key, loc_key.capitalize())
                item = (loc_emoji, lbl)
                if item not in loc_options:
                    loc_options.append(item)
        except Exception:
            loc_options = [
                ("🛠️", "Intervención"),
                ("🏠", "Teletrabajo"),
                ("🚗", "Oficina"),
            ]

        self.print("\nSelecciona ubicación/tipo:")
        for idx, (em, desc) in enumerate(loc_options, start=1):
            self.print(f"  [{idx}] {em} {desc}")

        loc_opt = self.input("Opción (1 por defecto): ").strip()
        chosen = loc_options[0]
        if loc_opt:
            try:
                opt_idx = int(loc_opt)
                if 1 <= opt_idx <= len(loc_options):
                    chosen = loc_options[opt_idx - 1]
            except ValueError:
                pass

        emoji, note = chosen[0], chosen[1]

        new_day = self.manager.add_day_to_week(
            week=week,
            day_number=add_num,
            location_emoji=emoji,
            location_note=note
        )
        self.active_day_number = new_day.day_number
        self._sync_markdown(week)
        self.print(f"✅ ¡Día {add_num} ({emoji} {note}) añadido con éxito a la semana!")
        self.input("Presiona Enter para continuar...")

    def manage_recurring_menu(self, week: WeekSchedule, day: DaySchedule) -> Optional[str]:
        """Subpantalla interactiva para gestionar Tareas y Reuniones Recurrentes (delegada)."""
        from brackets.core.recurring_controller import RecurringTasksController
        controller = RecurringTasksController(
            manager=self.manager,
            vault_root=self.vault_root,
            input_fn=self.input,
            print_fn=self.print,
            read_single_key_fn=self.read_single_key,
            clear_screen_fn=self.clear_screen,
            sync_markdown_fn=self._sync_markdown,
            prompt_selection_fn=self.prompt_topic_or_project_selection,
            menu_engine=self.menu_engine,
        )
        return controller.manage_recurring_menu(week, day)

    def manage_definitions_menu(self, week: WeekSchedule) -> Optional[str]:
        """Subpantalla interactiva para gestionar y crear definiciones/enlaces (delegada)."""
        from brackets.core.definitions_controller import DefinitionsController
        controller = DefinitionsController(
            manager=self.manager,
            vault_root=self.vault_root,
            input_fn=self.input,
            print_fn=self.print,
            read_single_key_fn=self.read_single_key,
            clear_screen_fn=self.clear_screen,
            sync_markdown_fn=self._sync_markdown,
            menu_engine=self.menu_engine,
        )
        return controller.manage_definitions_menu(week)
