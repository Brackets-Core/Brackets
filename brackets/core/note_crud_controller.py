#!/usr/bin/env python3
"""
Controlador CRUD de Notas para Brackets.
Permite Alta, Baja, Modificación y Consulta estructurada de Notas,
con sincronización automática hacia la base de datos relacional y Markdown.
Soporta contexto acotado a la semana activa (Daily Hub) o modo global (Menú Principal).
"""

from __future__ import annotations
import os
from typing import Optional, List, Callable
from brackets.models.entities import Note, WeekSchedule
from brackets.managers.entity_manager import EntityManager
from brackets.generators.bitacora_renderer import BitacoraRenderer
from brackets.core.menu_navigator import MenuNavigator, MenuOption


class NoteCrudController:
    """Controlador para la gestión completa (CRUD) de Notas."""

    def __init__(
        self,
        entity_manager: EntityManager,
        current_week: Optional[WeekSchedule] = None,
        vault_root: str = ".",
        input_fn: Optional[Callable[[str], str]] = None,
        print_fn: Optional[Callable[..., None]] = None,
        clear_screen_fn: Optional[Callable[[], None]] = None,
        read_single_key_fn: Optional[Callable[[str], str]] = None
    ):
        self.manager = entity_manager
        self.current_week = current_week
        self.vault_root = os.path.abspath(vault_root)
        self.input = input_fn or input
        self.print = print_fn or print
        self.clear_screen = clear_screen_fn or (lambda: None)
        if read_single_key_fn is not None:
            self.read_single_key = read_single_key_fn
        elif input_fn is not None and input_fn is not input:
            self.read_single_key = lambda prompt="": self.input(prompt)
        else:
            self.read_single_key = None

    def _sync_current_week_markdown(self) -> None:
        """Regenera la bitácora semanal en Markdown si hay semana cargada."""
        if not self.current_week:
            return
        from brackets.utils.legacy_utils import generate_filename
        md_path = generate_filename(
            year=self.current_week.year,
            month=self.current_week.month,
            week=self.current_week.week_number,
            directory=self.vault_root
        )
        BitacoraRenderer.render_and_save_week(self.current_week, self.manager, md_path)

    def get_current_week_notes(self) -> List[Note]:
        """Obtiene las notas asociadas a la semana activa."""
        if not self.current_week:
            return []
        notes = []
        for nid in self.current_week.note_ids:
            if nid in self.manager.notes:
                notes.append(self.manager.notes[nid])
        return sorted(notes, key=lambda n: n.id)

    def prompt_project_selection(
        self,
        allow_all: bool = False,
        allow_none: bool = True,
        prompt_title: str = "VINCULAR A PROYECTO"
    ) -> Optional[str]:
        """Muestra selector interactivo de proyectos."""
        projects = self.manager.list_projects()
        self.print(f"\n📁 {prompt_title}:")
        for idx, p in enumerate(projects, start=1):
            self.print(f"  [{idx}] {p.id} ({p.name})")

        if allow_all:
            self.print("  [0] Todos los proyectos")
        elif allow_none:
            self.print("  [0] Ninguno / General")
            self.print("  [+] Crear y vincular nuevo proyecto")

        p_choice = self.input("Selecciona proyecto (0 por defecto): ").strip()
        if not p_choice or p_choice in ("0", "n", "no"):
            return None

        if p_choice == "+" and not allow_all and allow_none:
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

    # -------------------------------------------------------------------------
    # 1. Consulta y Búsqueda
    # -------------------------------------------------------------------------
    def query_notes(self) -> List[Note]:
        """[1] Permite consultar y buscar notas por semana, texto, proyecto o mes."""
        self.print("\n" + "=" * 65)
        self.print("🔍 CONSULTAR Y BUSCAR NOTAS")
        self.print("=" * 65)

        if self.current_week:
            self.print(f"  [1] Ver Notas de la Semana Actual (W{self.current_week.week_number:02d}) [Por defecto]")
            self.print("  [2] Ver todas las notas históricas (Global)")
            self.print("  [3] Filtrar por Proyecto")
            self.print("  [4] Filtrar por Mes (ej: 2026-08)")
            self.print("  [5] Búsqueda por palabra clave o texto")
            self.print("  [0] Cancelar")

            choice = self.input("\nSelecciona tipo de consulta (1 por defecto): ").strip()
            if choice == "0":
                return []
            if choice in ("1", ""):
                notes = self.get_current_week_notes()
            elif choice == "2":
                notes = self.manager.list_notes()
            elif choice == "3":
                proj_id = self.prompt_project_selection(allow_all=True)
                notes = self.manager.list_notes(project_id=proj_id)
            elif choice == "4":
                month = self.input("📅 Mes a consultar (YYYY-MM): ").strip()
                notes = self.manager.list_notes(month=month if month else None)
            elif choice == "5":
                query = self.input("🔎 Término de búsqueda: ").strip()
                notes = self.manager.search_notes(query=query)
            else:
                self.print("❌ Opción inválida.")
                return []
        else:
            self.print("  [1] Ver todas las notas registradas")
            self.print("  [2] Filtrar por Proyecto")
            self.print("  [3] Filtrar por Mes (ej: 2026-08)")
            self.print("  [4] Búsqueda por palabra clave o texto")
            self.print("  [0] Cancelar")

            choice = self.input("\nSelecciona tipo de consulta: ").strip()
            if choice in ("0", ""):
                return []

            if choice == "1":
                notes = self.manager.list_notes()
            elif choice == "2":
                proj_id = self.prompt_project_selection(allow_all=True)
                notes = self.manager.list_notes(project_id=proj_id)
            elif choice == "3":
                month = self.input("📅 Mes a consultar (YYYY-MM): ").strip()
                notes = self.manager.list_notes(month=month if month else None)
            elif choice == "4":
                query = self.input("🔎 Término de búsqueda: ").strip()
                notes = self.manager.search_notes(query=query)
            else:
                self.print("❌ Opción inválida.")
                return []

        self.print(f"\n📋 Resultados encontrados ({len(notes)}):")
        if not notes:
            self.print("  (No se encontraron notas con el criterio especificado)")
        else:
            for idx, n in enumerate(notes, start=1):
                proj_tag = f" [{n.project_id}]" if n.project_id else ""
                month_tag = f" ({n.month})" if n.month else ""
                title_str = n.title if n.title else "(Sin título)"
                self.print(f"\n  [{idx}] {n.id}{proj_tag}{month_tag}: {title_str}")
                for line in n.content[:3]:
                    self.print(f"      • {line[:65]}{'...' if len(line)>65 else ''}")

        self.print("\n" + "-" * 65)
        self.input("Presiona Enter para continuar...")
        return notes

    # -------------------------------------------------------------------------
    # 2. Alta (Creación)
    # -------------------------------------------------------------------------
    def create_new_note(self) -> Optional[Note]:
        """[2] Alta: Crea una nueva nota estructurada con título y viñetas."""
        self.print("\n" + "=" * 65)
        if self.current_week:
            self.print(f"➕ ALTA: CREAR NOTA EN SEMANA W{self.current_week.week_number:02d}")
        else:
            self.print("➕ ALTA: CREAR NUEVA NOTA")
        self.print("=" * 65)

        title = self.input("📌 Título de la nota (opcional, Enter para omitir): ").strip()
        self.print("📝 Introduce el contenido en viñetas (línea vacía para terminar):")
        content_lines: List[str] = []
        while True:
            line = self.input("  • ").strip()
            if not line:
                break
            content_lines.append(line)

        if not title and not content_lines:
            self.print("❌ La nota debe tener al menos un título o una viñeta.")
            self.input("Presiona Enter para continuar...")
            return None

        project_id = self.prompt_project_selection()

        year = self.current_week.year if self.current_week else 2026
        week_num = self.current_week.week_number if self.current_week else 35

        note = self.manager.add_note(
            title=title if title else None,
            content=content_lines,
            project_id=project_id,
            year=year,
            week_num=week_num
        )
        self._sync_current_week_markdown()

        proj_label = f"[{project_id}]" if project_id else "[GENERAL]"
        self.print(f"\n✅ Nota creada con éxito (ID: {note.id}) en {proj_label}.")
        self.input("Presiona Enter para continuar...")
        return note

    # -------------------------------------------------------------------------
    # 3. Modificación (Edición)
    # -------------------------------------------------------------------------
    def edit_existing_note(self) -> Optional[Note]:
        """[3] Modificación: Edita título, proyecto, mes y viñetas de una nota existente."""
        self.print("\n" + "=" * 65)
        if self.current_week:
            self.print(f"✏️  MODIFICACIÓN: EDITAR NOTA (Semana W{self.current_week.week_number:02d})")
        else:
            self.print("✏️  MODIFICACIÓN: EDITAR NOTA EXISTENTE")
        self.print("=" * 65)

        notes = []
        if self.current_week:
            notes = self.get_current_week_notes()
            if notes:
                self.print(f"Notas de la Semana Actual W{self.current_week.week_number:02d} ({len(notes)}):")
                for idx, n in enumerate(notes, start=1):
                    proj_tag = f" [{n.project_id}]" if n.project_id else ""
                    title_str = n.title if n.title else "(Sin título)"
                    self.print(f"  [{idx}] {n.id}{proj_tag}: {title_str}")
                self.print("  [s] Buscar en todo el histórico de notas (Global)")
                self.print("  [0] Cancelar")

                choice = self.input("\nSelecciona nota a editar (número o 's'): ").strip()
                if choice in ("0", ""):
                    return None
                if choice.lower() == "s":
                    query = self.input("Buscar en histórico (título, texto o ID): ").strip()
                    notes = self.manager.search_notes(query=query if query else None)
                else:
                    try:
                        n_idx = int(choice)
                        if 1 <= n_idx <= len(notes):
                            notes = [notes[n_idx - 1]]
                        else:
                            return None
                    except ValueError:
                        return None
            else:
                self.print(f"ℹ️ No hay notas registradas en la Semana W{self.current_week.week_number:02d}.")
                search_global = self.input("¿Buscar en el histórico global? (S/n): ").strip().lower()
                if search_global in ("n", "no"):
                    return None
                query = self.input("Buscar en histórico (título, texto o ID): ").strip()
                notes = self.manager.search_notes(query=query if query else None)
        else:
            query = self.input("Buscar nota a editar (título, palabra clave o ID, Enter para listar todas): ").strip()
            notes = self.manager.search_notes(query=query if query else None)

        if not notes:
            self.print("❌ No se encontraron notas.")
            self.input("Presiona Enter para continuar...")
            return None

        if len(notes) > 1:
            self.print(f"\nSelecciona la nota a editar (1-{len(notes)}):")
            for idx, n in enumerate(notes, start=1):
                proj_tag = f" [{n.project_id}]" if n.project_id else ""
                title_str = n.title if n.title else "(Sin título)"
                self.print(f"  [{idx}] {n.id}{proj_tag}: {title_str}")

            n_choice = self.input(f"\nNúmero de nota (1-{len(notes)}, 0 para cancelar): ").strip()
            try:
                n_idx = int(n_choice)
                if not (1 <= n_idx <= len(notes)):
                    return None
            except ValueError:
                return None
            target_note = notes[n_idx - 1]
        else:
            target_note = notes[0]

        self.print("\n" + "-" * 50)
        self.print(f"📝 EDITANDO NOTA: {target_note.id}")
        self.print(f"  • Título:   {target_note.title or '(Sin título)'}")
        self.print(f"  • Proyecto: {target_note.project_id or 'GENERAL'}")
        self.print(f"  • Viñetas ({len(target_note.content)}):")
        for i, c in enumerate(target_note.content, start=1):
            self.print(f"      {i}. {c}")
        self.print("-" * 50)

        # 1. Por defecto: Añadir texto al final directamente
        self.print("\n📝 Introduce las nuevas viñetas para añadir al final (Enter vacío para omitir, 'r' para reemplazar todas):")
        new_content = list(target_note.content)
        first_line = self.input("  • ").strip()

        if first_line.lower() == "r":
            new_content = []
            self.print("Introduce las nuevas viñetas (Enter vacío para terminar):")
            while True:
                line = self.input("  • ").strip()
                if not line:
                    break
                new_content.append(line)
        elif first_line:
            new_content.append(first_line)
            while True:
                line = self.input("  • ").strip()
                if not line:
                    break
                new_content.append(line)

        # 2. Preguntar de forma rápida y no intrusiva si desea modificar título o proyecto
        edit_meta = self.input("\n¿Deseas modificar el título o proyecto? (s/N): ").strip().lower()
        new_title = target_note.title
        new_proj_id = target_note.project_id

        if edit_meta in ("s", "si", "y", "yes"):
            new_title_in = self.input(f"Nuevo título (Enter para mantener '{target_note.title or ''}'): ").strip()
            if new_title_in:
                new_title = new_title_in
            new_proj_id = self.prompt_project_selection()

        # Guardar cambios
        updated = self.manager.update_note(
            note_id=target_note.id,
            title=new_title,
            content=new_content,
            project_id=new_proj_id
        )
        self._sync_current_week_markdown()

        self.print(f"\n✅ Nota {target_note.id} actualizada correctamente.")
        self.input("Presiona Enter para continuar...")
        return updated

    # -------------------------------------------------------------------------
    # 4. Baja (Eliminación)
    # -------------------------------------------------------------------------
    def delete_note(self) -> bool:
        """[4] Baja: Elimina una nota de la base de datos y de las bitácoras."""
        self.print("\n" + "=" * 65)
        if self.current_week:
            self.print(f"🗑️  BAJA: ELIMINAR NOTA (Semana W{self.current_week.week_number:02d})")
        else:
            self.print("🗑️  BAJA: ELIMINAR NOTA")
        self.print("=" * 65)

        notes = []
        if self.current_week:
            notes = self.get_current_week_notes()
            if notes:
                self.print(f"Notas de la Semana Actual W{self.current_week.week_number:02d} ({len(notes)}):")
                for idx, n in enumerate(notes, start=1):
                    proj_tag = f" [{n.project_id}]" if n.project_id else ""
                    title_str = n.title if n.title else "(Sin título)"
                    self.print(f"  [{idx}] {n.id}{proj_tag}: {title_str}")
                self.print("  [s] Buscar en todo el histórico de notas (Global)")
                self.print("  [0] Cancelar")

                choice = self.input("\nSelecciona nota a eliminar (número o 's'): ").strip()
                if choice in ("0", ""):
                    return False
                if choice.lower() == "s":
                    query = self.input("Buscar en histórico (título, texto o ID): ").strip()
                    notes = self.manager.search_notes(query=query if query else None)
                else:
                    try:
                        n_idx = int(choice)
                        if 1 <= n_idx <= len(notes):
                            notes = [notes[n_idx - 1]]
                        else:
                            return False
                    except ValueError:
                        return False
            else:
                self.print(f"ℹ️ No hay notas registradas en la Semana W{self.current_week.week_number:02d}.")
                search_global = self.input("¿Buscar en el histórico global? (S/n): ").strip().lower()
                if search_global in ("n", "no"):
                    return False
                query = self.input("Buscar en histórico (título, texto o ID): ").strip()
                notes = self.manager.search_notes(query=query if query else None)
        else:
            query = self.input("Buscar nota a eliminar (título, texto o ID): ").strip()
            notes = self.manager.search_notes(query=query if query else None)

        if not notes:
            self.print("❌ No se encontraron notas.")
            self.input("Presiona Enter para continuar...")
            return False

        if len(notes) > 1:
            self.print(f"\nSelecciona la nota a eliminar (1-{len(notes)}):")
            for idx, n in enumerate(notes, start=1):
                proj_tag = f" [{n.project_id}]" if n.project_id else ""
                title_str = n.title if n.title else "(Sin título)"
                self.print(f"  [{idx}] {n.id}{proj_tag}: {title_str}")

            n_choice = self.input(f"\nNúmero de nota a eliminar (1-{len(notes)}, 0 para cancelar): ").strip()
            try:
                n_idx = int(n_choice)
                if not (1 <= n_idx <= len(notes)):
                    return False
            except ValueError:
                return False
            target_note = notes[n_idx - 1]
        else:
            target_note = notes[0]

        confirm = self.input(f"⚠️ ¿Estás seguro de eliminar '{target_note.id}: {target_note.title or ''}'? (s/N): ").strip().lower()
        if confirm in ("s", "si", "y", "yes"):
            self.manager.delete_note_complete(target_note.id)
            self._sync_current_week_markdown()
            self.print(f"\n✅ Nota {target_note.id} eliminada correctamente.")
            self.input("Presiona Enter para continuar...")
            return True

        self.print("Operación cancelada.")
        self.input("Presiona Enter para continuar...")
        return False

    # -------------------------------------------------------------------------
    # Bucle Principal del Módulo CRUD
    # -------------------------------------------------------------------------
    # Bucle Principal CRUD
    # -------------------------------------------------------------------------
    def run(self) -> str:
        """Bucle interactivo del menú CRUD de Notas. Retorna 'back', 'menu' o 'exit'."""
        if self.current_week:
            title = f"📝 G E S T I Ó N  D E  N O T A S  (Semana W{self.current_week.week_number:02d} / {self.current_week.year})"
            query_label = "🔍 Consultar Notas (Semana Actual por defecto / Filtros / Búsqueda)"
        else:
            title = "📝 G E S T I Ó N  D E  N O T A S  ( M Ó D U L O  C R U D )"
            query_label = "🔍 Consultar y Buscar Notas (Filtros por Proyecto / Mes / Texto)"

        options = [
            MenuOption("1", query_label, "query", aliases=["c", "s"]),
            MenuOption("2", "➕ Alta: Crear Nueva Nota", "create", aliases=["a", "n"]),
            MenuOption("3", "✏️  Modificación: Editar Nota Existente", "edit", aliases=["e"]),
            MenuOption("4", "🗑️  Baja: Eliminar Nota", "delete", aliases=["d", "b"]),
        ]

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
                if opt.action_id == "query":
                    self.query_notes()
                elif opt.action_id == "create":
                    self.create_new_note()
                elif opt.action_id == "edit":
                    self.edit_existing_note()
                elif opt.action_id == "delete":
                    self.delete_note()
