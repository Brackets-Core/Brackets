#!/usr/bin/env python3
"""
Controlador de Gestión de Proyectos, Backlog e Ideas para Brackets.
Permite capturar tareas atemporales en cola, registrar ideas y planificar hacia la bitácora activa.
"""

from __future__ import annotations
import os
from typing import Callable, Optional, List, Dict, Any
from datetime import datetime

from brackets.models.entities import WeekSchedule, DaySchedule, Task, Note, Idea, Project
from brackets.managers.entity_manager import EntityManager
from brackets.generators.bitacora_renderer import BitacoraRenderer
from brackets.utils.legacy_utils import generate_filename
from brackets.core.menu_navigator import MenuNavigator, MenuOption


class ProjectBacklogController:
    """Subcontrolador interactivo para la gestión de backlog no agendado, ideas y proyectos."""

    STATUS_EMOJIS = {
        "evaluating": "🟡 Evaluar",
        "accepted": "🟢 Aceptada",
        "discarded": "🔴 Descartada"
    }

    def __init__(
        self,
        entity_manager: EntityManager,
        current_week: Optional[WeekSchedule] = None,
        current_day: Optional[DaySchedule] = None,
        vault_root: Optional[str] = None,
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[..., None] = print,
        clear_screen_fn: Optional[Callable[[], None]] = None,
        read_single_key_fn: Optional[Callable[[str], str]] = None
    ):
        self.manager = entity_manager
        self.current_week = current_week
        self.current_day = current_day
        self.vault_root = vault_root or os.path.dirname(self.manager.base_data_dir)
        self.input = input_fn
        self.print = print_fn
        self.clear_screen = clear_screen_fn or (lambda: None)
        if read_single_key_fn is not None:
            self.read_single_key = read_single_key_fn
        elif input_fn is not input:
            self.read_single_key = lambda prompt="": self.input(prompt)
        else:
            self.read_single_key = None

    def _sync_markdown(self, week: WeekSchedule) -> None:
        """Regenera y guarda el archivo Markdown de la semana si existe vault_root."""
        filename = generate_filename(week.year, week.month, week.week_number)
        md_path = os.path.join(self.vault_root, filename)
        BitacoraRenderer.render_and_save_week(week, self.manager, md_path)

    def prompt_project_selection(self, allow_all: bool = False, prompt_title: str = "VINCULAR A PROYECTO") -> Optional[str]:
        """Muestra la lista de proyectos registrados para seleccionar uno."""
        projects = self.manager.list_projects()
        self.print(f"\n📁 {prompt_title}:")
        if projects:
            for idx, p in enumerate(projects, start=1):
                self.print(f"  [{idx}] {p.id} ({p.name})")
        else:
            self.print("  (No hay proyectos registrados)")

        if allow_all:
            self.print("  [0] Todos los proyectos / General")
        else:
            self.print("  [0] Ninguno / General")
            self.print("  [+] Crear y vincular nuevo proyecto")

        p_choice = self.input("Selecciona proyecto (0 por defecto): ").strip()
        if not p_choice or p_choice in ("0", "n", "no"):
            return None

        if p_choice == "+" and not allow_all:
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
            for p in projects:
                if p_choice.upper() in (p.id.upper(), p.name.upper()):
                    return p.id

        return None

    def _sync_ideas_markdown(self) -> None:
        """Sincroniza y regenera el archivo [🧩GENERAL]🧠Ideas.md en el vault."""
        ideas_path = os.path.join(self.vault_root, "[🧩GENERAL]🧠Ideas.md")
        BitacoraRenderer.render_and_save_ideas(self.manager, ideas_path)

    def _sync_backlog_markdown(self) -> None:
        """Sincroniza y regenera el archivo [📋PROJECTS]✅BackLog.md en el vault."""
        backlog_path = os.path.join(self.vault_root, "[📋PROJECTS]✅BackLog.md")
        BitacoraRenderer.render_and_save_backlog(
            self.manager,
            backlog_path,
            scheduled_task_ids=self.manager.get_scheduled_task_ids()
        )

    # -------------------------------------------------------------------------
    # Acciones del Submenú
    # -------------------------------------------------------------------------
    def add_backlog_task(self) -> None:
        """[1] Añade una tarea atemporal al backlog de un proyecto (sin fecha)."""
        self.print("\n" + "=" * 65)
        self.print("📋 NUEVA TAREA AL BACKLOG (Sin fecha asignada)")
        self.print("=" * 65)
        title = self.input("Título de la tarea: ").strip()
        if not title:
            self.print("❌ El título no puede estar vacío.")
            self.input("Presiona Enter para continuar...")
            return

        from brackets.utils.bitacora_parser import BitacoraMarkdownParser
        proj_tag, _ = BitacoraMarkdownParser.parse_project_tag(title)
        if proj_tag:
            self.manager.ensure_project(proj_tag)
            project_id = proj_tag
        else:
            project_id = self.prompt_project_selection()

        task = self.manager.create_task(title=title, project_id=project_id)
        self._sync_backlog_markdown()

        proj_label = f"[{project_id}]" if project_id else "[GENERAL]"
        self.print(f"\n✅ Tarea guardada en el Backlog de {proj_label} (ID: {task.id}).")
        self.print("   (Queda en cola, lista para cuando decidas agendarla).")
        self.input("\nPresiona Enter para continuar...")

    def capture_idea(self) -> None:
        """[2] Captura una nueva idea o propuesta para evaluar."""
        self.print("\n" + "=" * 65)
        self.print("💡 NUEVA IDEA / PROPUESTA")
        self.print("=" * 65)
        title = self.input("Título o concepto de la idea: ").strip()
        if not title:
            self.print("❌ El título no puede estar vacío.")
            self.input("Presiona Enter para continuar...")
            return

        project_id = self.prompt_project_selection()

        self.print("\n📝 Detalles / Hipótesis de la idea (línea vacía para terminar):")
        content_lines: List[str] = []
        while True:
            line = self.input("  • ").strip()
            if not line:
                break
            content_lines.append(line)

        self.print("\nEstado inicial de la idea:")
        self.print("  [1] 🟡 Evaluar (por defecto)")
        self.print("  [2] 🟢 Aceptada / Aterrizada")
        self.print("  [3] 🔴 Descartada")
        st_choice = self.input("Selecciona estado (1 por defecto): ").strip()

        status = "evaluating"
        if st_choice == "2":
            status = "accepted"
        elif st_choice == "3":
            status = "discarded"

        idea = self.manager.create_idea(
            title=title,
            content=content_lines,
            project_id=project_id,
            status=status
        )
        self._sync_ideas_markdown()

        proj_label = f"[{project_id}]" if project_id else "[GENERAL]"
        st_label = self.STATUS_EMOJIS.get(status, status)
        self.print(f"\n✅ Idea registrada en {proj_label} (ID: {idea.id}) - Estado: {st_label}.")
        self.input("\nPresiona Enter para continuar...")

    def schedule_backlog_task_to_today(self) -> None:
        """[3] Trae una tarea pendiente del backlog al día activo."""
        self.print("\n" + "=" * 65)
        if not self.current_week or not self.current_day:
            self.print("⚠️ No hay una bitácora/día activo configurado para asignar tareas.")
            self.print("   Abre esta opción desde el Daily Hub para asignar a hoy.")
            self.input("\nPresiona Enter para continuar...")
            return

        day_label = f"{self.current_day.location_emoji} Día {self.current_day.day_number}"
        self.print(f"🔄 PLANIFICAR DESDE EL BACKLOG -> AÑADIR A HOY ({day_label})")
        self.print("=" * 65)

        project_id = self.prompt_project_selection(allow_all=True, prompt_title="FILTRAR POR PROYECTO")
        pending_tasks = self.manager.list_backlog_tasks(project_id=project_id, pending_only=True)

        # Filtrar las que ya están en el día de hoy
        available_tasks = [t for t in pending_tasks if t.id not in self.current_day.task_ids]

        if not available_tasks:
            self.print("\nℹ️ No hay tareas pendientes disponibles en el backlog para asignar.")
            self.input("\nPresiona Enter para continuar...")
            return

        self.print(f"\n📋 Tareas disponibles en cola ({len(available_tasks)}):")
        for idx, t in enumerate(available_tasks, start=1):
            proj_tag = f" [{t.project_id}]" if t.project_id else ""
            self.print(f"  [{idx}] {t.id}: {t.title}{proj_tag}")

        t_choice = self.input(f"\nSelecciona tarea para traer a HOY (1-{len(available_tasks)}): ").strip()
        try:
            t_idx = int(t_choice)
            if 1 <= t_idx <= len(available_tasks):
                chosen_task = available_tasks[t_idx - 1]
                self.manager.assign_task_to_day(
                    task_id=chosen_task.id,
                    year=self.current_week.year,
                    week_num=self.current_week.week_number,
                    day_number=self.current_day.day_number
                )
                self._sync_markdown(self.current_week)
                self._sync_backlog_markdown()
                self.print(f"\n✅ {chosen_task.id} ('{chosen_task.title}') asignada a las tareas de HOY ({day_label}).")
            else:
                self.print("❌ Selección fuera de rango.")
        except ValueError:
            self.print("❌ Ingresa un número válido.")

        self.input("\nPresiona Enter para continuar...")

    def view_projects_overview(self) -> None:
        """[4] Muestra resumen de todos los proyectos registrados con estadísticas y métricas de backlog."""
        self.print("\n" + "=" * 65)
        self.print("📂 RESUMEN GENERAL DE PROYECTOS Y MÉTRICAS DE BACKLOG")
        self.print("=" * 65)

        metrics = self.manager.get_all_projects_metrics()
        self.print(
            f"🌐 GLOBAL: {metrics['total_projects']} Proyectos | "
            f"✅ {metrics['total_done']}/{metrics['total_tasks']} Tareas ({metrics['global_completion_rate']}%) | "
            f"📋 Backlog: {metrics['total_backlog']} (Sin asignar: {metrics['unassigned_backlog']})"
        )
        self.print("-" * 65)

        projects = self.manager.list_projects()
        if not projects:
            self.print("  (No hay proyectos registrados en la base de datos)")
        else:
            for p in projects:
                stats = self.manager.get_project_stats(p.id)
                rate = stats["completion_rate"]
                bar_len = 10
                filled = int(rate / 10)
                bar = "█" * filled + "░" * (bar_len - filled)

                self.print(f"\n📁 [{p.id}] {p.name}")
                if p.description:
                    self.print(f"   Descripción: {p.description}")
                self.print(f"   Progreso: [{bar}] {rate}%")
                self.print(
                    f"   📊 Tareas: {stats['total_tasks']} total | "
                    f"✅ {stats['done_tasks']} hechas | "
                    f"⏳ {stats['pending_tasks']} activas (📋 {stats['backlog_tasks']} en cola, 📅 {stats['scheduled_tasks']} agendadas)"
                )
                self.print(
                    f"   💡 Ideas: {stats['total_ideas']} total | "
                    f"🟡 {stats['evaluating_ideas']} evaluar | 🟢 {stats['accepted_ideas']} aceptadas"
                )

        self.print("\n" + "-" * 65)
        self.input("Presiona Enter para volver...")

    def view_project_backlog(self) -> None:
        """[5] Lista y consulta el backlog de tareas de un proyecto."""
        self.print("\n" + "=" * 65)
        self.print("📋 CONSULTAR BACKLOG POR PROYECTO")
        self.print("=" * 65)

        project_id = self.prompt_project_selection(allow_all=True, prompt_title="SELECCIONA PROYECTO")
        tasks = self.manager.list_backlog_tasks(project_id=project_id, pending_only=False)

        proj_label = f"[{project_id}]" if project_id else "[TODOS LOS PROYECTOS]"
        self.print(f"\n📋 Tareas registradas en {proj_label} ({len(tasks)}):")
        if not tasks:
            self.print("  (No hay tareas registradas)")
        else:
            for idx, t in enumerate(tasks, start=1):
                status_icon = "[x]" if t.is_done else ("[ ] ~~" if t.is_cancelled else "[ ]")
                suffix = "~~" if t.is_cancelled else ""
                proj_tag = f" [{t.project_id}]" if t.project_id else ""
                self.print(f"  [{idx}] {status_icon} {t.id}: {t.title}{proj_tag}{suffix}")

        self.print("\n" + "-" * 65)
        self.input("Presiona Enter para volver...")

    def view_project_ideas(self) -> None:
        """[6] Consulta y permite cambiar el estado de las ideas de un proyecto."""
        self.print("\n" + "=" * 65)
        self.print("💡 CONSULTAR Y EVALUAR IDEAS")
        self.print("=" * 65)

        project_id = self.prompt_project_selection(allow_all=True, prompt_title="SELECCIONA PROYECTO")
        ideas = self.manager.list_ideas(project_id=project_id)

        proj_label = f"[{project_id}]" if project_id else "[TODOS LOS PROYECTOS]"
        self.print(f"\n💡 Ideas registradas en {proj_label} ({len(ideas)}):")
        if not ideas:
            self.print("  (No hay ideas registradas)")
            self.input("\nPresiona Enter para volver...")
            return

        for idx, i in enumerate(ideas, start=1):
            st_badge = self.STATUS_EMOJIS.get(i.status, i.status)
            proj_tag = f" [{i.project_id}]" if i.project_id else ""
            self.print(f"\n  [{idx}] {st_badge} - {i.id}: {i.title}{proj_tag}")
            for line in i.content[:2]:
                self.print(f"      • {line[:60]}{'...' if len(line)>60 else ''}")

        self.print("\n" + "-" * 65)
        self.print("[c] Cambiar estado de una idea    [0] Volver")
        sub_choice = self.input("Selecciona opción: ").strip().lower()

        if sub_choice == "c":
            i_choice = self.input(f"Número de idea (1-{len(ideas)}): ").strip()
            try:
                i_idx = int(i_choice)
                if 1 <= i_idx <= len(ideas):
                    target_idea = ideas[i_idx - 1]
                    self.print(f"\nIdea seleccionada: {target_idea.id} - {target_idea.title}")
                    self.print("Nuevo estado:")
                    self.print("  [1] 🟡 Evaluar")
                    self.print("  [2] 🟢 Aceptada / Aterrizada")
                    self.print("  [3] 🔴 Descartada")
                    st_input = self.input("Selecciona estado: ").strip()
                    new_st = None
                    if st_input == "1":
                        new_st = "evaluating"
                    elif st_input == "2":
                        new_st = "accepted"
                    elif st_input == "3":
                        new_st = "discarded"

                    if new_st:
                        self.manager.update_idea_status(target_idea.id, new_st)
                        self._sync_ideas_markdown()
                        self.print(f"\n✅ Estado de {target_idea.id} actualizado a {self.STATUS_EMOJIS.get(new_st, new_st)}.")
                    else:
                        self.print("❌ Opción inválida.")
                else:
                    self.print("❌ Número fuera de rango.")
            except ValueError:
                self.print("❌ Ingresa un número válido.")
            self.input("\nPresiona Enter para continuar...")

    # -------------------------------------------------------------------------
    # Bucle Principal del Submenú
    # -------------------------------------------------------------------------
    def run(self) -> str:
        """Bucle interactivo del submenú. Retorna 'back', 'menu' o 'exit'."""
        day_str = f"Día {self.current_day.day_number}" if self.current_day else "Hoy"
        options = [
            MenuOption("1", "📋 Añadir tarea al Backlog (sin fecha / en cola)", "add_task", aliases=["t"], group="➕ CAPTURA RÁPIDA"),
            MenuOption("2", "💡 Capturar nueva Idea (propuesta / hipótesis)", "capture_idea", aliases=["i"], group="➕ CAPTURA RÁPIDA"),
            MenuOption("3", f"➡️  Traer tarea del Backlog a las tareas de HOY ({day_str})", "schedule_today", aliases=["h", "a"], group="🔄 PLANIFICACIÓN"),
            MenuOption("4", "📂 Ver Proyectos y estado general", "view_projects", aliases=["p"], group="🔍 CONSULTA Y ESTADO"),
            MenuOption("5", "📋 Ver Backlog de un Proyecto (tareas en cola)", "view_backlog", aliases=["b"], group="🔍 CONSULTA Y ESTADO"),
            MenuOption("6", "💡 Ver Ideas de un Proyecto (evaluar / aterrizar / descartar)", "view_ideas", group="🔍 CONSULTA Y ESTADO"),
        ]
        navigator = MenuNavigator(
            title="📁 G E S T I Ó N  D E  B A C K L O G ,  I D E A S  Y  P R O Y E C T O S",
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
                if opt.action_id == "add_task":
                    self.add_backlog_task()
                elif opt.action_id == "capture_idea":
                    self.capture_idea()
                elif opt.action_id == "schedule_today":
                    self.schedule_backlog_task_to_today()
                elif opt.action_id == "view_projects":
                    self.view_projects_overview()
                elif opt.action_id == "view_backlog":
                    self.view_project_backlog()
                elif opt.action_id == "view_ideas":
                    self.view_project_ideas()
