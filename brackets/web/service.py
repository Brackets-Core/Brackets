#!/usr/bin/env python3
"""
Capa de servicio para la API y la interfaz Web de Brackets.
Desacopla la lógica de negocio de los vaults y las bitácoras
para que puedan ser consumidas por la Web PWA, la API y los agentes de IA.
"""

from __future__ import annotations
import os
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from brackets.managers.entity_manager import EntityManager
from brackets.managers.vault_manager import VaultManager
from brackets.managers.markdown_sync_service import MarkdownSyncService
from brackets.generators.bitacora_renderer import BitacoraRenderer
from brackets.models.task_types import TaskTypeRegistry
from brackets.models.entities import WeekSchedule, DaySchedule, Task
from brackets.utils.bitacora_parser import BitacoraMarkdownParser
from brackets.utils.legacy_utils import generate_filename


class BracketsWebService:
    """Servicio unificado de acceso a datos de vaults para la Web y la API."""

    def __init__(self, workspace_root: Optional[str] = None):
        base = os.path.abspath(workspace_root or os.getcwd())
        # Buscar hacia arriba el contenedor del workspace que tenga vaults o el motor brackets
        cur = base
        found_root = None
        while cur and os.path.dirname(cur) != cur:
            has_subvaults = False
            try:
                has_subvaults = any(
                    os.path.exists(os.path.join(cur, d, "data", "config.yaml"))
                    for d in os.listdir(cur)
                    if os.path.isdir(os.path.join(cur, d))
                )
            except Exception:
                pass

            if (
                os.path.exists(os.path.join(cur, "brackets", "brackets"))
                or os.path.exists(os.path.join(cur, "MyJobNotes"))
                or has_subvaults
            ):
                found_root = cur
                break
            cur = os.path.dirname(cur)

        self.workspace_root = found_root or base
        self.vault_manager = VaultManager(self.workspace_root)
        self._managers: Dict[str, EntityManager] = {}

    def get_entity_manager(self, vault_path: str) -> EntityManager:
        """Obtiene o inicializa una instancia de EntityManager para un vault."""
        resolved = os.path.abspath(vault_path)
        data_dir = os.path.join(resolved, "data")
        if resolved not in self._managers:
            mgr = EntityManager(data_dir)
            mgr.load_all()
            self._managers[resolved] = mgr
        return self._managers[resolved]

    def list_vaults(self) -> List[Dict[str, Any]]:
        """Lista todos los vaults disponibles en el workspace con sus metadatos."""
        self.vault_manager.refresh_vaults() if hasattr(self.vault_manager, "refresh_vaults") else None
        vaults_data = self.vault_manager.vaults

        results = []
        for v in vaults_data:
            path = v["path"]
            config_path = os.path.join(path, "data", "config.yaml")
            vault_type = "work"
            days_per_week = 5
            if os.path.exists(config_path):
                try:
                    import yaml
                    with open(config_path, "r", encoding="utf-8") as f:
                        cfg = yaml.safe_load(f) or {}
                        vault_type = cfg.get("vault_type", "work")
                        days_per_week = cfg.get("days_per_week", 7 if vault_type == "personal" else 5)
                except Exception:
                    pass

            results.append({
                "name": v["name"],
                "path": path,
                "description": v.get("description", ""),
                "vault_type": vault_type,
                "days_per_week": days_per_week
            })

        if not results and os.path.exists(os.path.join(self.workspace_root, "data", "config.yaml")):
            config_path = os.path.join(self.workspace_root, "data", "config.yaml")
            vault_type = "work"
            days_per_week = 5
            try:
                import yaml
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                    vault_type = cfg.get("vault_type", "work")
                    days_per_week = cfg.get("days_per_week", 7 if vault_type == "personal" else 5)
            except Exception:
                pass
            results.append({
                "name": os.path.basename(self.workspace_root),
                "path": self.workspace_root,
                "description": "Vault activo",
                "vault_type": vault_type,
                "days_per_week": days_per_week
            })

        return results

    def resolve_vault_path(self, vault_identifier: Optional[str] = None) -> str:
        """Resuelve un nombre o ruta de vault al path absoluto correspondiente."""
        resolved = self.vault_manager.resolve_vault_path(vault_identifier)
        if resolved:
            return resolved

        vaults = self.list_vaults()
        if vaults:
            # Preferir MyJobNotes por defecto o el primer vault disponible
            for v in vaults:
                if v["name"].lower() == "myjobnotes":
                    return v["path"]
            return vaults[0]["path"]

        # Si apunta a un directorio válido con data/config.yaml
        if vault_identifier:
            cand = os.path.abspath(vault_identifier)
            if os.path.exists(os.path.join(cand, "data", "config.yaml")):
                return cand

        return self.workspace_root

    def _sync_week_from_markdown_if_exists(self, vault_path: str, week: WeekSchedule, mgr: EntityManager) -> None:
        """Absorbe cambios hechos a mano en el .md de la semana activa."""
        md_path = generate_filename(week.year, week.month, week.week_number, directory=vault_path)
        if os.path.exists(md_path):
            sync_service = MarkdownSyncService(mgr, vault_path)
            sync_service.sync_week_from_markdown(md_path, week.year, week.week_number)

    def _render_and_save_week_md(self, vault_path: str, week: WeekSchedule, mgr: EntityManager) -> None:
        """Regenera la bitácora Markdown oficial desde los datos estructurados."""
        md_path = generate_filename(week.year, week.month, week.week_number, directory=vault_path)
        BitacoraRenderer.render_and_save_week(week, mgr, md_path)

    def _auto_register_people_in_text(self, mgr: EntityManager, *texts: Optional[str]) -> None:
        """Detecta menciones @handle al crear/editar y las registra en people.yaml."""
        combined = " ".join(t for t in texts if t)
        if not combined or "@" not in combined:
            return
        mentions = set(re.findall(r'(?:^|[\s(\[])@([A-Za-zÁÉÍÓÚáéíóúñÑ0-9_-]+)', combined))
        if not mentions:
            return
        today_str = datetime.now().strftime("%Y-%m-%d")
        for m in mentions:
            mgr.ensure_person(handle=m, created_at=today_str)

    def _get_or_create_week(
        self,
        vault_path: str,
        mgr: EntityManager,
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> WeekSchedule:
        """Obtiene la semana solicitada o actual, creándola e inicializándola si no existe."""
        now = datetime.now()
        iso_year, iso_week, _ = now.isocalendar()
        target_year = year or iso_year
        target_week = week_number or iso_week

        week = mgr.load_week(target_year, target_week, reload=True)
        if not week and (year is None and week_number is None) and mgr.weeks:
            last_key = sorted(mgr.weeks.keys())[-1]
            week = mgr.weeks[last_key]

        if not week:
            # Crear nueva semana programada
            config_path = os.path.join(vault_path, "data", "config.yaml")
            days_count = 5
            if os.path.exists(config_path):
                try:
                    import yaml
                    with open(config_path, "r", encoding="utf-8") as f:
                        cfg = yaml.safe_load(f) or {}
                        vault_type = cfg.get("vault_type", "work")
                        days_count = cfg.get("days_per_week", 7 if vault_type == "personal" else 5)
                except Exception:
                    pass

            from brackets.managers.settings_manager import SettingsManager
            settings = SettingsManager(vault_path)

            first_day = datetime.fromisocalendar(target_year, target_week, 1)
            days = []
            for d_idx in range(days_count):
                cur_date = first_day + timedelta(days=d_idx)
                loc, note = settings.get_location_for_date(cur_date, target_week)
                days.append(DaySchedule(
                    day_number=cur_date.day,
                    location_emoji=loc or "🏠",
                    location_note=note,
                    task_ids=[]
                ))

            week = WeekSchedule(
                year=target_year,
                week_number=target_week,
                month=first_day.month,
                weight=None,
                days=days,
                week_task_ids=[],
                topic_ids=[],
                note_ids=[]
            )
            mgr.apply_recurring_tasks(week)
            mgr.save_week(week)
            self._render_and_save_week_md(vault_path, week, mgr)

        return week

    def get_hub_data(
        self,
        vault_identifier: Optional[str] = None,
        day_number: Optional[int] = None,
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Obtiene el estado completo del Daily Hub para la UI Web."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)

        now = datetime.now()
        iso_year, iso_week, _ = now.isocalendar()
        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)

        # Sincronizar cambios manuales desde el .md
        self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        # Paridad completa con DailyHubController.run(): calendario, recurrentes y arrastre día a día en la semana actual
        is_current_week = (week.year == iso_year and week.week_number == iso_week) or (year is None and week_number is None)
        today_day = next((d for d in week.days if d.day_number == now.day), None) if is_current_week else None
        if is_current_week:
            changed_week = False
            try:
                from brackets.managers.settings_manager import SettingsManager
                if mgr.apply_calendar_to_week(week, SettingsManager(vault_path)):
                    changed_week = True
            except Exception:
                pass
            if mgr.apply_recurring_tasks(week) > 0:
                changed_week = True
            if today_day:
                rolled = mgr.rollover_day_tasks(week, today_day.day_number)
                if rolled > 0:
                    changed_week = True
                mgr.sort_day_tasks_pending_first(today_day)
            if changed_week:
                mgr.save_week(week)
                self._render_and_save_week_md(vault_path, week, mgr)

        # Determinar día activo
        active_day = None
        if day_number is not None:
            active_day = next((d for d in week.days if d.day_number == day_number), None)

        if not active_day:
            active_day = next((d for d in week.days if d.day_number == now.day), None)
        if not active_day and week.days:
            active_day = week.days[0]

        # Mapa de días de la semana ISO (1=L, 2=M, 3=X, 4=J, 5=V, 6=S, 7=D)
        iso_day_map = {}
        for iso_d in range(1, 8):
            try:
                dt = datetime.fromisocalendar(week.year, week.week_number, iso_d)
                iso_day_map[dt.day] = iso_d
            except Exception:
                pass
        weekday_letters = {1: "L", 2: "M", 3: "X", 4: "J", 5: "V", 6: "S", 7: "D"}
        weekday_names = {1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves", 5: "Viernes", 6: "Sábado", 7: "Domingo"}

        # Serializar días de la semana
        days_data = []
        for idx_d, d in enumerate(week.days):
            iso_idx = iso_day_map.get(d.day_number, (idx_d % 7) + 1)
            letter = weekday_letters.get(iso_idx, "L")
            name = weekday_names.get(iso_idx, "Día")
            days_data.append({
                "day_number": d.day_number,
                "weekday_letter": letter,
                "weekday_name": name,
                "location_emoji": d.location_emoji,
                "location_note": d.location_note,
                "is_active": (active_day is not None and d.day_number == active_day.day_number),
                "is_today": (d.day_number == now.day),
                "task_count": len(d.task_ids),
                "tasks": [self._serialize_task(mgr.tasks[tid]) for tid in d.task_ids if tid in mgr.tasks]
            })

        # Serializar tareas del día activo
        today_tasks = []
        if active_day:
            for tid in active_day.task_ids:
                task = mgr.tasks.get(tid)
                if task:
                    today_tasks.append(self._serialize_task(task))

        # Serializar tareas semanales (sin día asignado)
        week_tasks = []
        for tid in week.week_task_ids:
            task = mgr.tasks.get(tid)
            if task:
                week_tasks.append(self._serialize_task(task))

        # Serializar notas de la semana
        notes_data = []
        for nid in week.note_ids:
            note = mgr.notes.get(nid)
            if note:
                notes_data.append({
                    "id": note.id,
                    "title": note.title or "Sin título",
                    "project_id": note.project_id,
                    "content": note.content
                })

        # Serializar topics de la semana
        topics_data = []
        if hasattr(week, "topic_ids") and week.topic_ids:
            for top_id in week.topic_ids:
                top = mgr.topics.get(top_id)
                if top:
                    topics_data.append({
                        "id": top.id,
                        "title": top.title,
                        "project_id": top.project_id,
                        "status": top.status,
                        "created_at": top.created_at
                    })

        # Serializar definiciones de la semana
        definitions_data = []
        seen_def_ids = set()

        def _add_def(def_id: str, url: str = "", title: Optional[str] = None, dtype: str = "link"):
            if def_id in seen_def_ids:
                return
            seen_def_ids.add(def_id)
            final_url = url
            clean_ticket = def_id.replace("[", "").replace("]", "").replace("🎫", "").strip()
            is_jira = bool(re.search(r'^[A-Za-z]+-\d+$', clean_ticket))
            if not final_url and is_jira and mgr.jira_base_url:
                final_url = f"{mgr.jira_base_url}{clean_ticket}"
            definitions_data.append({
                "id": def_id,
                "url": final_url,
                "title": title or def_id,
                "type": dtype or ("jira" if is_jira else "link")
            })

        # 1. Definiciones explícitas en el objeto de la semana
        if hasattr(week, "definition_ids") and week.definition_ids:
            for def_id in week.definition_ids:
                d = mgr.definitions.get(def_id)
                if not d:
                    clean_id = def_id.replace("[", "").replace("]", "").replace("🎫", "").strip()
                    for k, v in mgr.definitions.items():
                        if k.replace("[", "").replace("]", "").replace("🎫", "").strip() == clean_id:
                            d = v
                            break
                if d:
                    _add_def(d.id, d.url, d.title, d.type)
                else:
                    _add_def(def_id, "", def_id, "link")

        # 2. Text corpus de la semana para encontrar menciones de tickets o URLs
        week_text_corpus = []
        for top in topics_data:
            week_text_corpus.append(top["title"])
        for tid in week.week_task_ids:
            if tid in mgr.tasks:
                week_text_corpus.append(mgr.tasks[tid].title)
                if mgr.tasks[tid].description:
                    week_text_corpus.append(mgr.tasks[tid].description)
        for d in week.days:
            for tid in d.task_ids:
                if tid in mgr.tasks:
                    week_text_corpus.append(mgr.tasks[tid].title)
                    if mgr.tasks[tid].description:
                        week_text_corpus.append(mgr.tasks[tid].description)
        for nid in week.note_ids:
            if nid in mgr.notes:
                week_text_corpus.append(mgr.notes[nid].title or "")
                week_text_corpus.extend(mgr.notes[nid].content)

        full_text = " ".join(week_text_corpus)

        for d_id, d in mgr.definitions.items():
            clean_key = d_id.replace("[", "").replace("]", "").replace("🎫", "").strip()
            if d_id in full_text or (clean_key and clean_key in full_text):
                _add_def(d.id, d.url, d.title, d.type)

        # Buscar URLs de Jira directas en el texto (ej: https://.../browse/SUPPLY-19331)
        jira_matches = re.findall(r'https?://[^\s)]+/browse/([A-Za-z]+-\d+)', full_text)
        for ticket in jira_matches:
            ticket_def_id = f"[🎫{ticket}]"
            ticket_url = f"{mgr.jira_base_url}{ticket}" if mgr.jira_base_url else ""
            _add_def(ticket_def_id, ticket_url, ticket, "jira")

        # Buscar corchetes de tickets en el texto tipo [🎫EXP-119781] o [EXP-119781]
        bracket_tickets = re.findall(r'\[(?:🎫)?([A-Za-z]+-\d+)\]', full_text)
        for ticket in bracket_tickets:
            ticket_def_id = f"[🎫{ticket}]"
            ticket_url = f"{mgr.jira_base_url}{ticket}" if mgr.jira_base_url else ""
            _add_def(ticket_def_id, ticket_url, ticket, "jira")

        # Información del vault
        config_path = os.path.join(vault_path, "data", "config.yaml")
        vault_type = "work"
        if os.path.exists(config_path):
            try:
                import yaml
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                    vault_type = cfg.get("vault_type", "work")
            except Exception:
                pass

        task_types = [
            {"key": t.key, "label": t.label, "premoji": t.premoji}
            for t in TaskTypeRegistry.get_all()
        ]

        available_weeks = self._collect_available_weeks(vault_path, mgr)
        projects_list = [
            {"id": p.id, "name": p.name, "description": p.description, "status": p.status}
            for p in mgr.list_projects()
        ]
        top_menu = self._load_web_top_menu(vault_path)

        people_seen = set()
        people_data = []
        for p in mgr.people.values():
            if getattr(p, "status", "active") != "active" or not p.handle:
                continue
            if p.handle in people_seen:
                continue
            people_seen.add(p.handle)
            people_data.append({
                "id": p.id,
                "handle": p.handle,
                "name": p.name or p.handle.lstrip("@")
            })
        people_data.sort(key=lambda x: x["handle"].lower())

        return {
            "vault": {
                "name": os.path.basename(vault_path),
                "path": vault_path,
                "vault_type": vault_type
            },
            "vault_name": os.path.basename(vault_path),
            "week": {
                "year": week.year,
                "week_number": week.week_number,
                "month": week.month,
                "weight": week.weight,
                "days": days_data,
                "week_tasks": week_tasks,
                "topics": topics_data
            },
            "active_day": {
                "day_number": active_day.day_number,
                "location_emoji": active_day.location_emoji,
                "location_note": active_day.location_note
            } if active_day else None,
            "days": days_data,
            "today_tasks": today_tasks,
            "week_tasks": week_tasks,
            "topics": topics_data,
            "notes": notes_data,
            "definitions": definitions_data,
            "people": people_data,
            "task_types": task_types,
            "available_weeks": available_weeks,
            "projects": projects_list,
            "top_menu": top_menu
        }

    def _serialize_task(self, task: Task) -> Dict[str, Any]:
        """Serializa una entidad Task para la API JSON."""
        return {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "is_done": task.is_done,
            "is_cancelled": task.is_cancelled,
            "is_pending": task.is_pending,
            "task_type": task.task_type,
            "premoji": task.premoji,
            "project_id": task.project_id,
            "description": task.description,
            "created_at": task.created_at,
            "completed_at": task.completed_at,
            "day_number": getattr(task, "day_number", None),
            "is_week_task": getattr(task, "is_week_task", False)
        }

    def create_task(
        self,
        vault_identifier: Optional[str] = None,
        title: str = "",
        target: str = "today",  # "today", "week", "day:N"
        status: str = "pending",  # "pending", "done"
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        day: Optional[int] = None,
        is_done: Optional[bool] = None,
        year: Optional[int] = None,
        week_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Crea una tarea en el vault, sincroniza a YAML y regenera Markdown."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)

        now = datetime.now()
        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)

        # Absorber cambios previos de Markdown
        self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        if is_done is not None:
            status = "done" if is_done else "pending"

        if day is not None:
            target = f"day:{day}"

        # Detectar premojis y tags
        task_type, clean_title = TaskTypeRegistry.detect_task_type_and_clean_title(title)
        proj_tag, clean_title = BitacoraMarkdownParser.parse_project_tag(clean_title)
        final_proj = project_id or proj_tag
        if final_proj:
            mgr.ensure_project(final_proj)

        # Determinar destino
        is_week_task = False
        target_day_num = None

        if target == "week":
            is_week_task = True
        elif target.startswith("day:"):
            try:
                target_day_num = int(target.replace("day:", ""))
            except ValueError:
                target_day_num = now.day
        else:
            # "today" por defecto
            target_day_num = now.day

        # Asegurar que el día existe en la semana si no es tarea semanal
        if not is_week_task and target_day_num is not None:
            day_exists = any(d.day_number == target_day_num for d in week.days)
            if not day_exists:
                # Si hoy no está (ej: fin de semana o primera vez), usar el primer día
                if week.days:
                    target_day_num = week.days[0].day_number

        # Comprobar si coincide con una tarea recurrente activa
        clean_target = clean_title.replace("~~", "").strip()
        rec_info = next(
            (r for r in mgr.list_recurring_tasks(active_only=True)
             if r.title == clean_title or r.title == clean_target),
            None
        )
        recurring_id = rec_info.id if rec_info else None
        if rec_info:
            if not task_type or task_type == "task":
                task_type = rec_info.task_type
            if not final_proj or final_proj == "POR_ASIGNAR":
                final_proj = rec_info.project_id

        task = mgr.create_task(
            title=clean_title,
            status=status,
            project_id=final_proj,
            year=week.year,
            week_num=week.week_number,
            day_number=target_day_num if not is_week_task else None,
            is_week_task=is_week_task,
            recurring_id=recurring_id,
            task_type=task_type or "task",
            description=description.strip() if description else None
        )

        # Ordenar pendientes primero
        if target_day_num is not None:
            for d in week.days:
                if d.day_number == target_day_num:
                    mgr.sort_day_tasks_pending_first(d)
                    break
        mgr.save_week(week)

        self._auto_register_people_in_text(mgr, clean_title, description)

        # Regenerar bitácora Markdown
        self._render_and_save_week_md(vault_path, week, mgr)

        res = self._serialize_task(task)
        res["success"] = True
        res["task"] = self._serialize_task(task)
        return res

    def toggle_task(
        self,
        vault_identifier: Optional[str] = None,
        task_id: str = "",
        year: Optional[int] = None,
        week_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Alterna el estado completado/pendiente de una tarea."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)

        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)

        if week:
            self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        task = mgr.toggle_task(task_id)
        if not task:
            raise ValueError(f"Tarea {task_id} no encontrada.")

        if week:
            # Si era una tarea de la semana (sin día fijo) y se marca como resuelta, trasladarla automáticamente a hoy
            if task.status == "done" and task.id in week.week_task_ids:
                week.week_task_ids.remove(task.id)
                now = datetime.now()
                target_day = next((d for d in week.days if d.day_number == now.day), None)
                if not target_day and week.days:
                    target_day = week.days[0]
                if target_day:
                    if task.id not in target_day.task_ids:
                        target_day.task_ids.append(task.id)
                    mgr.sort_day_tasks_pending_first(target_day)
                mgr.save_tasks()

            # Reordenar día correspondiente
            for d in week.days:
                if task.id in d.task_ids:
                    mgr.sort_day_tasks_pending_first(d)
                    break
            mgr.apply_recurring_tasks(week)
            mgr.save_week(week)
            self._render_and_save_week_md(vault_path, week, mgr)

        res = self._serialize_task(task)
        res["success"] = True
        res["new_status"] = task.status
        return res

    def set_day_location(
        self,
        vault_identifier: Optional[str] = None,
        day_number: Optional[int] = None,
        emoji: Optional[str] = None,
        note: Optional[str] = None,
        day: Optional[int] = None,
        location_emoji: Optional[str] = None,
        location_note: Optional[str] = None,
        year: Optional[int] = None,
        week_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Cambia puntualmente la ubicación de un día (ej: teletrabajo 🏠 vs oficina 🚗)."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)

        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)
        self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        target_day_num = day_number if day_number is not None else day
        if target_day_num is None:
            raise ValueError("El número de día es obligatorio.")

        target_emoji = emoji or location_emoji or "🏠"
        target_note = note if note is not None else location_note

        target_day = next((d for d in week.days if d.day_number == target_day_num), None)
        if not target_day:
            raise ValueError(f"Día {target_day_num} no encontrado en la semana activa.")

        target_day.location_emoji = target_emoji
        if target_note is not None:
            target_day.location_note = target_note.strip() if target_note.strip() else None

        mgr.save_week(week)
        self._render_and_save_week_md(vault_path, week, mgr)

        return {
            "success": True,
            "day_number": target_day.day_number,
            "location_emoji": target_day.location_emoji,
            "location_note": target_day.location_note
        }

    def sync_week(
        self,
        vault_identifier: Optional[str] = None,
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Fuerza la sincronización bidireccional Markdown ↔ YAML de la semana activa o indicada."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)

        now = datetime.now()
        iso_year, iso_week, _ = now.isocalendar()
        target_year = year or iso_year
        target_week = week_number or iso_week
        week = mgr.load_week(target_year, target_week, reload=True)
        if not week and (year is None and week_number is None) and mgr.weeks:
            last_key = sorted(mgr.weeks.keys())[-1]
            week = mgr.weeks[last_key]

        if not week:
            return {"status": "error", "message": "No hay semana activa"}

        md_path = generate_filename(week.year, week.month, week.week_number, directory=vault_path)
        if os.path.exists(md_path):
            service = MarkdownSyncService(mgr, vault_path)
            synced = service.sync_week_from_markdown(md_path, week.year, week.week_number)
            today_day = next((d for d in week.days if d.day_number == now.day), None)
            if today_day:
                rolled = mgr.rollover_day_tasks(week, today_day.day_number)
                if rolled > 0:
                    mgr.sort_day_tasks_pending_first(today_day)
                    mgr.save_week(week)
            self._render_and_save_week_md(vault_path, week, mgr)
            return {"status": "ok", "synced": synced, "file": os.path.basename(md_path)}

        return {"status": "warning", "message": "Archivo Markdown no encontrado"}

    def create_note(
        self,
        vault_identifier: Optional[str] = None,
        title: Optional[str] = None,
        content: Any = "",
        project_id: Optional[str] = None,
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Crea una nota estructurada y la vincula a la semana activa."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)

        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)
        self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        clean_title = title.strip() if title else ""
        proj_tag = None
        if clean_title:
            proj_tag, clean_title = BitacoraMarkdownParser.parse_project_tag(clean_title)

        final_proj = project_id or proj_tag
        if final_proj:
            mgr.ensure_project(final_proj)

        if isinstance(content, str):
            bullets = [line.strip().lstrip("-*•").strip() for line in content.splitlines() if line.strip()]
        elif isinstance(content, list):
            bullets = [str(line).strip().lstrip("-*•").strip() for line in content if str(line).strip()]
        else:
            bullets = []

        if not clean_title and not bullets:
            raise ValueError("La nota debe tener un título o al menos una línea de contenido.")

        note = mgr.add_note(
            content=bullets,
            year=week.year,
            week_num=week.week_number,
            title=clean_title if clean_title else None,
            project_id=final_proj
        )

        self._auto_register_people_in_text(mgr, clean_title, *bullets)
        self._render_and_save_week_md(vault_path, week, mgr)
        return {
            "success": True,
            "note": {
                "id": note.id,
                "title": note.title,
                "content": note.content,
                "project_id": note.project_id
            }
        }

    def create_definition(
        self,
        vault_identifier: Optional[str] = None,
        code_or_id: str = "",
        url: Optional[str] = None,
        title: Optional[str] = None,
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Crea o actualiza una definición/enlace y la asocia a la semana activa."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)

        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)
        self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        clean_code = code_or_id.strip()
        # Si clean_code está vacío pero url tiene un ticket Jira:
        if not clean_code and url:
            m_ticket = re.search(r'(?:browse\/|issues?\/|selectedIssue=|key=|^|[\/?#&])([A-Za-z][A-Za-z0-9_]*-\d+)(?:[/&#? ]|$)', url)
            if m_ticket:
                clean_code = m_ticket.group(1).upper()

        # Si clean_code es una URL completa que contiene ticket Jira:
        if re.search(r'https?://', clean_code):
            m_url_ticket = re.search(r'(?:browse\/|issues?\/|selectedIssue=|key=|^|[\/?#&])([A-Za-z][A-Za-z0-9_]*-\d+)(?:[/&#? ]|$)', clean_code)
            if m_url_ticket:
                if not url:
                    url = clean_code
                clean_code = m_url_ticket.group(1).upper()

        if not clean_code:
            raise ValueError("El código o identificador de definición es obligatorio.")

        # Si parece un ticket Jira (ej: SYSC-12345 o [🎫SYSC-12345])
        is_jira = bool(re.search(r'^[A-Za-z][A-Za-z0-9_]*-\d+$', clean_code.replace("[", "").replace("]", "").replace("🎫", "").strip()))
        if is_jira:
            clean_ticket = clean_code.replace("[", "").replace("]", "").replace("🎫", "").strip().upper()
            def_id = f"[🎫{clean_ticket}]"
            final_url = url.strip() if url and url.strip() else f"{mgr.jira_base_url}{clean_ticket}"
        else:
            def_id = clean_code if clean_code.startswith("[") and clean_code.endswith("]") else f"[{clean_code}]"
            final_url = url.strip() if url and url.strip() else ""

        def_obj = mgr.ensure_definition(def_id=def_id, url=final_url, title=title or clean_code)

        if def_obj.id not in week.definition_ids:
            week.definition_ids.append(def_obj.id)
            mgr.save_week(week)

        self._render_and_save_week_md(vault_path, week, mgr)
        return {
            "success": True,
            "definition": {
                "id": def_obj.id,
                "url": def_obj.url,
                "title": def_obj.title,
                "type": def_obj.type
            }
        }

    def create_topic(
        self,
        vault_identifier: Optional[str] = None,
        title: str = "",
        project_id: Optional[str] = None,
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Crea un nuevo Topic y lo asocia a la semana activa."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)

        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)
        self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        clean_title = title.strip() if title else ""
        if not clean_title:
            raise ValueError("El título del topic es obligatorio.")

        proj_tag, clean_title = BitacoraMarkdownParser.parse_project_tag(clean_title)
        final_proj = project_id or proj_tag or "GENERAL"
        mgr.ensure_project(final_proj)

        topic = mgr.create_topic(
            title=clean_title,
            project_id=final_proj,
            year=week.year,
            week_num=week.week_number
        )

        if topic.id not in week.topic_ids:
            week.topic_ids.append(topic.id)
            mgr.save_week(week)

        self._auto_register_people_in_text(mgr, clean_title)
        self._render_and_save_week_md(vault_path, week, mgr)

        return {
            "success": True,
            "topic": {
                "id": topic.id,
                "title": topic.title,
                "project_id": topic.project_id,
                "status": topic.status,
                "created_at": topic.created_at
            }
        }

    def update_task(
        self,
        vault_identifier: Optional[str] = None,
        task_id: str = "",
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        target: Optional[str] = None,
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Actualiza título, descripción, estado o día/semana de una tarea."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)
        self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        task = mgr.tasks.get(task_id)
        if not task:
            raise ValueError(f"Tarea {task_id} no encontrada.")

        if title is not None and title.strip():
            task_type, clean_title = TaskTypeRegistry.detect_task_type_and_clean_title(title.strip())
            proj_tag, clean_title = BitacoraMarkdownParser.parse_project_tag(clean_title)
            task.title = clean_title
            if task_type:
                task.task_type = task_type
            if proj_tag:
                mgr.ensure_project(proj_tag)
                task.project_id = proj_tag

        if description is not None:
            task.description = description.strip() if description.strip() else None

        if status is not None:
            task.status = status
            if task.is_done and not task.completed_at:
                task.completed_at = datetime.now().strftime("%Y-%m-%d")
            elif not task.is_done:
                task.completed_at = None

        # Cambiar de día o a tarea de la semana si se especifica target
        if target is not None:
            if task.id in week.week_task_ids:
                week.week_task_ids.remove(task.id)
            for d in week.days:
                if task.id in d.task_ids:
                    d.task_ids.remove(task.id)

            if target == "week":
                if task.id not in week.week_task_ids:
                    week.week_task_ids.append(task.id)
                task.is_week_task = True
                task.day_number = None
            elif target == "today":
                now = datetime.now()
                target_day = next((d for d in week.days if d.day_number == now.day), None)
                if not target_day and week.days:
                    target_day = week.days[0]
                if target_day:
                    if task.id not in target_day.task_ids:
                        target_day.task_ids.append(task.id)
                    mgr.sort_day_tasks_pending_first(target_day)
                    task.is_week_task = False
                    task.day_number = target_day.day_number
            elif target.startswith("day:"):
                try:
                    d_num = int(target.replace("day:", ""))
                    target_day = next((d for d in week.days if d.day_number == d_num), None)
                    if target_day and task.id not in target_day.task_ids:
                        target_day.task_ids.append(task.id)
                        mgr.sort_day_tasks_pending_first(target_day)
                    task.is_week_task = False
                    task.day_number = d_num
                except ValueError:
                    pass

        mgr.save_tasks()
        mgr.save_week(week)
        self._auto_register_people_in_text(mgr, task.title, task.description)
        self._render_and_save_week_md(vault_path, week, mgr)
        return {"success": True, "task": self._serialize_task(task)}

    def delete_task(
        self,
        vault_identifier: Optional[str] = None,
        task_id: str = "",
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Elimina una tarea de la semana activa y de la tabla de tareas."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)
        self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        if task_id in week.week_task_ids:
            week.week_task_ids.remove(task_id)
        for d in week.days:
            if task_id in d.task_ids:
                d.task_ids.remove(task_id)

        if task_id in mgr.tasks:
            del mgr.tasks[task_id]
            mgr.save_tasks()

        mgr.save_week(week)
        self._render_and_save_week_md(vault_path, week, mgr)
        return {"success": True, "deleted": task_id}

    def update_topic(
        self,
        vault_identifier: Optional[str] = None,
        topic_id: str = "",
        title: str = "",
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Actualiza el título y proyecto de un topic existente."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)
        self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        topic = mgr.topics.get(topic_id)
        if not topic:
            raise ValueError(f"Topic {topic_id} no encontrado.")

        clean_title = title.strip() if title else ""
        if not clean_title:
            raise ValueError("El título del topic no puede estar vacío.")

        proj_tag, clean_title = BitacoraMarkdownParser.parse_project_tag(clean_title)
        topic.title = clean_title
        if proj_tag:
            mgr.ensure_project(proj_tag)
            topic.project_id = proj_tag

        mgr.save_topics()
        self._auto_register_people_in_text(mgr, clean_title)
        self._render_and_save_week_md(vault_path, week, mgr)
        return {
            "success": True,
            "topic": {
                "id": topic.id,
                "title": topic.title,
                "project_id": topic.project_id,
                "status": topic.status
            }
        }

    def delete_topic(
        self,
        vault_identifier: Optional[str] = None,
        topic_id: str = "",
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Desvincula un topic de la semana activa."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)
        self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        if topic_id in week.topic_ids:
            week.topic_ids.remove(topic_id)
            mgr.save_week(week)

        self._render_and_save_week_md(vault_path, week, mgr)
        return {"success": True, "deleted": topic_id}

    def update_note(
        self,
        vault_identifier: Optional[str] = None,
        note_id: str = "",
        title: Optional[str] = None,
        content: Any = None,
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Actualiza título y/o viñetas de una nota existente."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)
        self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        note = mgr.notes.get(note_id)
        if not note:
            raise ValueError(f"Nota {note_id} no encontrada.")

        if title is not None:
            clean_title = title.strip()
            if clean_title:
                proj_tag, clean_title = BitacoraMarkdownParser.parse_project_tag(clean_title)
                note.title = clean_title
                if proj_tag:
                    mgr.ensure_project(proj_tag)
                    note.project_id = proj_tag
            else:
                note.title = None

        if content is not None:
            if isinstance(content, str):
                bullets = [line.strip().lstrip("-*•").strip() for line in content.splitlines() if line.strip()]
            elif isinstance(content, list):
                bullets = [str(line).strip().lstrip("-*•").strip() for line in content if str(line).strip()]
            else:
                bullets = []
            note.content = bullets

        mgr.save_notes()
        self._auto_register_people_in_text(mgr, note.title, *(note.content or []))
        self._render_and_save_week_md(vault_path, week, mgr)
        return {
            "success": True,
            "note": {
                "id": note.id,
                "title": note.title,
                "content": note.content,
                "project_id": note.project_id
            }
        }

    def delete_note(
        self,
        vault_identifier: Optional[str] = None,
        note_id: str = "",
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Elimina una nota de la semana activa y de la tabla de notas."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)
        self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        if note_id in week.note_ids:
            week.note_ids.remove(note_id)
            mgr.save_week(week)

        if note_id in mgr.notes:
            del mgr.notes[note_id]
            mgr.save_notes()

        self._render_and_save_week_md(vault_path, week, mgr)
        return {"success": True, "deleted": note_id}

    def update_definition(
        self,
        vault_identifier: Optional[str] = None,
        def_id: str = "",
        new_id: Optional[str] = None,
        url: Optional[str] = None,
        title: Optional[str] = None,
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Actualiza código, URL o título de una definición/enlace."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)
        self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        clean_def_id = def_id.strip()
        d_obj = mgr.definitions.get(clean_def_id)
        if not d_obj:
            for k, v in mgr.definitions.items():
                if k.strip("[]") == clean_def_id.strip("[]"):
                    d_obj = v
                    break

        if not d_obj:
            d_obj = mgr.ensure_definition(def_id=clean_def_id, url=url or "", title=title)

        if url is not None:
            d_obj.url = url.strip()
        if title is not None:
            d_obj.title = title.strip() if title.strip() else None

        if new_id and new_id.strip() and new_id.strip() != d_obj.id:
            old_key = d_obj.id
            target_new_id = new_id.strip()
            if not target_new_id.startswith("[") or not target_new_id.endswith("]"):
                target_new_id = f"[{target_new_id}]"

            if old_key in mgr.definitions:
                del mgr.definitions[old_key]
            d_obj.id = target_new_id
            mgr.definitions[target_new_id] = d_obj

            if hasattr(week, "definition_ids"):
                for idx, did in enumerate(week.definition_ids):
                    if did == old_key:
                        week.definition_ids[idx] = target_new_id
                mgr.save_week(week)

        mgr.save_definitions()
        self._render_and_save_week_md(vault_path, week, mgr)
        return {
            "success": True,
            "definition": {
                "id": d_obj.id,
                "url": d_obj.url,
                "title": d_obj.title,
                "type": d_obj.type
            }
        }

    def delete_definition(
        self,
        vault_identifier: Optional[str] = None,
        def_id: str = "",
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Desvincula una definición de la semana activa."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)
        self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        clean_id = def_id.strip()
        if hasattr(week, "definition_ids"):
            week.definition_ids = [d for d in week.definition_ids if d != clean_id and d.strip("[]") != clean_id.strip("[]")]
            mgr.save_week(week)

        self._render_and_save_week_md(vault_path, week, mgr)
        return {"success": True, "deleted": def_id}

    def reorder_elements(
        self,
        vault_identifier: Optional[str] = None,
        reorder_type: str = "",
        ids: Optional[List[str]] = None,
        day_number: Optional[int] = None,
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Reordena los elementos (tareas de hoy, tareas de la semana, notas, topics o definiciones)
        en la semana activa o especificada, guardando en YAML y actualizando el Markdown.
        """
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)
        self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        if ids is None:
            ids = []

        rtype = (reorder_type or "").lower().strip()

        if rtype in ("today_tasks", "today", "day_tasks"):
            target_day_num = day_number
            if target_day_num is None:
                now = datetime.now()
                target_day_num = now.day
            day = next((d for d in week.days if d.day_number == int(target_day_num)), None)
            if not day:
                raise ValueError(f"Día {target_day_num} no encontrado en la semana activa")

            new_task_ids = [tid for tid in ids if tid in day.task_ids]
            for tid in day.task_ids:
                if tid not in new_task_ids:
                    new_task_ids.append(tid)
            day.task_ids = new_task_ids
            mgr.save_week(week)

        elif rtype in ("week_tasks", "week"):
            new_task_ids = [tid for tid in ids if tid in week.week_task_ids]
            for tid in week.week_task_ids:
                if tid not in new_task_ids:
                    new_task_ids.append(tid)
            week.week_task_ids = new_task_ids
            mgr.save_week(week)

        elif rtype in ("notes", "week_notes"):
            new_note_ids = [nid for nid in ids if nid in week.note_ids]
            for nid in week.note_ids:
                if nid not in new_note_ids:
                    new_note_ids.append(nid)
            week.note_ids = new_note_ids
            mgr.save_week(week)

        elif rtype in ("topics", "week_topics"):
            if not hasattr(week, "topic_ids"):
                week.topic_ids = []
            new_topic_ids = [top_id for top_id in ids if top_id in week.topic_ids]
            for top_id in week.topic_ids:
                if top_id not in new_topic_ids:
                    new_topic_ids.append(top_id)
            week.topic_ids = new_topic_ids
            mgr.save_week(week)

        elif rtype in ("definitions", "week_definitions"):
            if not hasattr(week, "definition_ids"):
                week.definition_ids = []
            new_def_ids = [def_id for def_id in ids if def_id in week.definition_ids]
            for def_id in week.definition_ids:
                if def_id not in new_def_ids:
                    new_def_ids.append(def_id)
            week.definition_ids = new_def_ids
            mgr.save_week(week)

        else:
            raise ValueError(f"Tipo de reordenación desconocido: {reorder_type}")

        self._render_and_save_week_md(vault_path, week, mgr)
        return {
            "success": True,
            "reorder_type": rtype,
            "count": len(ids)
        }

    # -------------------------------------------------------------------------
    # Menú Superior Declarativo y Acciones Avanzadas CLI en Web Hub
    # -------------------------------------------------------------------------
    def _load_web_top_menu(self, vault_path: str) -> List[Dict[str, Any]]:
        """Carga la estructura declarativa del menú superior web desde menu_config.yaml."""
        candidates = [
            os.path.join(vault_path, "data", "menu_config.yaml"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "menu_config.yaml"))
        ]
        for cfg_path in candidates:
            if os.path.exists(cfg_path):
                try:
                    import yaml
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                    web_menu = data.get("menus", {}).get("web_top_menu", {})
                    groups = web_menu.get("groups")
                    if isinstance(groups, list) and groups:
                        return groups
                except Exception:
                    pass

        # Fallback declarativo por seguridad
        return [
            {
                "id": "bitacoras",
                "label": "📅 Bitácoras",
                "items": [
                    {"id": "next_weekly", "label": "➕ Nueva Bitácora Semanal (arrastrar pendientes)", "command": "next_weekly"},
                    {"id": "switch_week", "label": "🗓️ Cambiar / Navegar Semana", "command": "switch_week"},
                    {"id": "add_extra_day", "label": "🛠️ Añadir Día Extra / Intervención", "command": "add_extra_day"},
                ]
            },
            {
                "id": "sync_recurring",
                "label": "🔄 Sync y Recurrentes",
                "items": [
                    {"id": "sync_current_week", "label": "🔄 Sincronizar Semana Actual (.md ↔ YAML)", "command": "sync_current_week"},
                    {"id": "sync_all_weeks", "label": "🌐 Sincronizar TODAS las Semanas del Vault", "command": "sync_all_weeks"},
                    {"id": "apply_recurring", "label": "⚡ Inyectar Tareas Recurrentes en esta Semana", "command": "apply_recurring"},
                    {"id": "manage_recurring", "label": "🔁 Gestionar Tareas Recurrentes y Reuniones", "command": "manage_recurring"},
                    {"id": "apply_calendar", "label": "📆 Reaplicar Calendario Laboral a esta Semana", "command": "apply_calendar"},
                ]
            },
            {
                "id": "projects_backlog",
                "label": "📁 Proyectos y Backlog",
                "items": [
                    {"id": "projects_overview", "label": "📊 Estado Global de Proyectos y Métricas", "command": "projects_overview"},
                    {"id": "backlog_manager", "label": "🗂️ Gestionar Backlog (Sin fecha asignada)", "command": "backlog_manager"},
                    {"id": "ideas_manager", "label": "💡 Gestionar Ideas ([🧩GENERAL]🧠Ideas.md)", "command": "ideas_manager"},
                    {"id": "schedule_week_to_today", "label": "➡️ Agendar Tarea Semanal a Día Activo", "command": "schedule_week_to_today"},
                ]
            },
            {
                "id": "consolidation",
                "label": "📦 Consolidación",
                "items": [
                    {"id": "consolidate_month", "label": "📅 Consolidar Mes Completo ([YYYY][MM].md)", "command": "consolidate_month"},
                    {"id": "consolidate_year", "label": "🗓️ Consolidar Año Completo ([YYYY].md)", "command": "consolidate_year"},
                ]
            },
            {
                "id": "tools",
                "label": "🛠️ Herramientas",
                "items": [
                    {"id": "pomodoro_timer", "label": "🍅 Temporizador Pomodoro Flotante", "command": "pomodoro_timer"},
                    {"id": "work_calendar", "label": "🏖️ Calendario Laboral (Festivos / Vacaciones)", "command": "work_calendar"},
                    {"id": "toggle_all_sections", "label": "↕️ Expandir / Colapsar Todas las Secciones", "command": "toggle_all_sections"},
                ]
            }
        ]

    def _collect_available_weeks(self, vault_path: str, mgr: EntityManager) -> List[Dict[str, Any]]:
        """Escanea las semanas disponibles en YAML y Markdown en el vault."""
        weeks_map: Dict[str, Dict[str, Any]] = {}

        # 1. Archivos YAML en data/weeks/
        if os.path.exists(mgr.weeks_dir):
            for fname in os.listdir(mgr.weeks_dir):
                m = re.match(r"^(\d{4})-W(\d{2})\.yaml$", fname)
                if m:
                    y, w = int(m.group(1)), int(m.group(2))
                    key = f"{y}-W{w:02d}"
                    weeks_map[key] = {"year": y, "week_number": w, "key": key}

        # 2. Semanas cargadas en memoria
        for key, w_obj in mgr.weeks.items():
            weeks_map[key] = {"year": w_obj.year, "week_number": w_obj.week_number, "key": key}

        # 3. Archivos Markdown [YYYY][MM]WeekXX.md en la raíz del vault
        if os.path.exists(vault_path):
            for fname in os.listdir(vault_path):
                m = re.match(r"^\[(\d{4})\]\[(\d{2})\]Week(\d{2})\.md$", fname)
                if m:
                    y, mo, w = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    key = f"{y}-W{w:02d}"
                    weeks_map[key] = {"year": y, "week_number": w, "month": mo, "key": key, "file": fname}

        sorted_weeks = sorted(
            weeks_map.values(),
            key=lambda item: (item["year"], item["week_number"]),
            reverse=True
        )
        return sorted_weeks

    def list_available_weeks(self, vault_identifier: Optional[str] = None) -> Dict[str, Any]:
        """Devuelve la lista de semanas disponibles en el vault."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        return {"weeks": self._collect_available_weeks(vault_path, mgr)}

    def create_next_week(
        self,
        vault_identifier: Optional[str] = None,
        weight: Optional[float] = None,
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Crea la siguiente bitácora semanal (o una específica), arrastrando pendientes e inyectando recurrentes."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)

        available = self._collect_available_weeks(vault_path, mgr)
        prev_week: Optional[WeekSchedule] = None
        prev_prev_week: Optional[WeekSchedule] = None

        if year is not None and week_number is not None:
            target_year, target_week = int(year), int(week_number)
            if available:
                latest = available[0]
                prev_week = mgr.load_week(latest["year"], latest["week_number"], reload=True)
                if len(available) > 1:
                    second = available[1]
                    prev_prev_week = mgr.load_week(second["year"], second["week_number"], reload=True)
        elif available:
            latest = available[0]
            prev_week = mgr.load_week(latest["year"], latest["week_number"], reload=True)
            if prev_week:
                self._sync_week_from_markdown_if_exists(vault_path, prev_week, mgr)
            if len(available) > 1:
                second = available[1]
                prev_prev_week = mgr.load_week(second["year"], second["week_number"], reload=True)

            # Calcular lunes de la siguiente semana ISO
            first_day_latest = datetime.fromisocalendar(latest["year"], latest["week_number"], 1)
            next_monday = first_day_latest + timedelta(days=7)
            iso_y, iso_w, _ = next_monday.isocalendar()
            target_year, target_week = iso_y, iso_w
        else:
            now = datetime.now()
            target_year, target_week, _ = now.isocalendar()

        # Verificar configuración de días por semana del vault
        config_path = os.path.join(vault_path, "data", "config.yaml")
        days_count = 5
        if os.path.exists(config_path):
            try:
                import yaml
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                    vault_type = cfg.get("vault_type", "work")
                    days_count = cfg.get("days_per_week", 7 if vault_type == "personal" else 5)
            except Exception:
                pass

        from brackets.managers.settings_manager import SettingsManager
        settings = SettingsManager(vault_path)

        first_day = datetime.fromisocalendar(target_year, target_week, 1)
        days = []
        for d_idx in range(days_count):
            cur_date = first_day + timedelta(days=d_idx)
            loc, note = settings.get_location_for_date(cur_date, target_week)
            days.append(DaySchedule(
                day_number=cur_date.day,
                location_emoji=loc or "🏠",
                location_note=note,
                task_ids=[]
            ))

        existing = mgr.load_week(target_year, target_week, reload=True)
        if existing:
            new_week = existing
            if weight is not None:
                new_week.weight = weight
        else:
            new_week = WeekSchedule(
                year=target_year,
                week_number=target_week,
                month=first_day.month,
                weight=weight,
                days=days,
                week_task_ids=[],
                topic_ids=list(prev_week.topic_ids) if prev_week and prev_week.topic_ids else [],
                note_ids=[]
            )

        rolled_count = 0
        if prev_week and (prev_week.year != new_week.year or prev_week.week_number != new_week.week_number):
            rolled_count = mgr.rollover_week_to_new_week(prev_week, new_week, prev_prev_week=prev_prev_week)

        injected_recurring = mgr.apply_recurring_tasks(new_week)
        mgr.prune_tasks_older_than_two_weeks(new_week)
        mgr.save_week(new_week)
        self._render_and_save_week_md(vault_path, new_week, mgr)

        # Actualizar archivo de Backlog si hubo tareas desagendadas
        backlog_path = os.path.join(vault_path, "[📋PROJECTS]✅BackLog.md")
        BitacoraRenderer.render_and_save_backlog(mgr, backlog_path, scheduled_task_ids=mgr.get_scheduled_task_ids())

        return {
            "success": True,
            "year": new_week.year,
            "week_number": new_week.week_number,
            "month": new_week.month,
            "rolled_tasks": rolled_count,
            "injected_recurring": injected_recurring,
            "file": os.path.basename(generate_filename(new_week.year, new_week.month, new_week.week_number, directory=vault_path))
        }

    def add_extra_day(
        self,
        vault_identifier: Optional[str] = None,
        day_number: Optional[int] = None,
        emoji: str = "🛠️",
        note: Optional[str] = "Intervención",
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Añade un día extra (ej. sábado/domingo de guardia o intervención) a la semana."""
        if day_number is None:
            raise ValueError("El número de día (1-31) es obligatorio.")
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)
        self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        new_day = mgr.add_day_to_week(
            week=week,
            day_number=int(day_number),
            location_emoji=emoji or "🛠️",
            location_note=note.strip() if note and note.strip() else None
        )
        self._render_and_save_week_md(vault_path, week, mgr)
        return {
            "success": True,
            "day": {
                "day_number": new_day.day_number,
                "location_emoji": new_day.location_emoji,
                "location_note": new_day.location_note
            }
        }

    def set_week_weight(
        self,
        vault_identifier: Optional[str] = None,
        weight: Optional[Any] = None,
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Actualiza el peso semanal (⚖️ kg) en la semana activa."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)
        self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        if weight is None or str(weight).strip() == "":
            week.weight = None
        else:
            try:
                week.weight = float(str(weight).replace(",", ".").strip())
            except ValueError:
                raise ValueError("El peso debe ser un valor numérico válido (ej: 81.5).")

        mgr.save_week(week)
        self._render_and_save_week_md(vault_path, week, mgr)
        return {
            "success": True,
            "year": week.year,
            "week_number": week.week_number,
            "weight": week.weight
        }

    def sync_all_weeks(self, vault_identifier: Optional[str] = None) -> Dict[str, Any]:
        """Sincroniza todas las bitácoras semanales Markdown del vault hacia YAML."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        sync_service = MarkdownSyncService(mgr, vault_path)

        synced_files = []
        if os.path.exists(vault_path):
            for fname in sorted(os.listdir(vault_path)):
                m = re.match(r"^\[(\d{4})\]\[(\d{2})\]Week(\d{2})\.md$", fname)
                if m:
                    y, _, w = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    full_path = os.path.join(vault_path, fname)
                    sync_service.sync_week_from_markdown(full_path, y, w)
                    synced_files.append(fname)

        return {
            "success": True,
            "count": len(synced_files),
            "files": synced_files
        }

    def apply_calendar(
        self,
        vault_identifier: Optional[str] = None,
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Reaplica las reglas de work_calendar.yaml (festivos, vacaciones, ubicaciones) a la semana."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)
        self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        from brackets.managers.settings_manager import SettingsManager
        settings = SettingsManager(vault_path)

        changed = mgr.apply_calendar_to_week(week, settings)
        mgr.save_week(week)
        self._render_and_save_week_md(vault_path, week, mgr)
        return {
            "success": True,
            "changed": changed,
            "year": week.year,
            "week_number": week.week_number
        }

    # -------------------------------------------------------------------------
    # Tareas Recurrentes
    # -------------------------------------------------------------------------
    def list_recurring(self, vault_identifier: Optional[str] = None) -> Dict[str, Any]:
        """Lista todas las tareas y reuniones recurrentes del vault."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        items = []
        for r in mgr.list_recurring_tasks(active_only=False):
            items.append({
                "id": r.id,
                "title": r.title,
                "task_type": r.task_type,
                "premoji": TaskTypeRegistry.get_premoji(r.task_type),
                "recurrence_type": r.recurrence_type,
                "days_of_week": r.days_of_week,
                "interval_weeks": r.interval_weeks,
                "base_week": r.base_week,
                "day_of_week": r.day_of_week,
                "project_id": r.project_id,
                "active": r.active,
                "description": r.description
            })
        return {"recurring_tasks": items}

    def create_recurring(
        self,
        vault_identifier: Optional[str] = None,
        title: str = "",
        recurrence_type: str = "weekly_days",
        days_of_week: Optional[List[int]] = None,
        interval_weeks: int = 1,
        day_of_week: int = 4,
        project_id: Optional[str] = None,
        task_type: Optional[str] = None,
        description: Optional[str] = None,
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Crea una nueva tarea o reunión recurrente y la inyecta en la semana actual."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)

        clean_title = title.strip()
        if not clean_title:
            raise ValueError("El título de la tarea recurrente es obligatorio.")

        detected_type, clean_title = TaskTypeRegistry.detect_task_type_and_clean_title(clean_title)
        proj_tag, clean_title = BitacoraMarkdownParser.parse_project_tag(clean_title)
        final_proj = project_id or proj_tag
        if final_proj:
            mgr.ensure_project(final_proj)

        final_task_type = task_type if (task_type and task_type != "task") else (detected_type or "task")
        now = datetime.now()
        _, current_iso_week, _ = now.isocalendar()

        rec = mgr.create_recurring_task(
            title=clean_title,
            recurrence_type=recurrence_type or "weekly_days",
            days_of_week=[int(d) for d in (days_of_week or [])],
            interval_weeks=int(interval_weeks or 1),
            base_week=week_number or current_iso_week,
            day_of_week=int(day_of_week if day_of_week is not None else 4),
            project_id=final_proj,
            task_type=final_task_type,
            description=description
        )

        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)
        injected = mgr.apply_recurring_tasks(week)
        mgr.save_week(week)
        self._render_and_save_week_md(vault_path, week, mgr)

        return {
            "success": True,
            "injected": injected,
            "recurring_task": {
                "id": rec.id,
                "title": rec.title,
                "task_type": rec.task_type,
                "premoji": TaskTypeRegistry.get_premoji(rec.task_type),
                "recurrence_type": rec.recurrence_type,
                "days_of_week": rec.days_of_week,
                "interval_weeks": rec.interval_weeks,
                "day_of_week": rec.day_of_week,
                "project_id": rec.project_id,
                "active": rec.active
            }
        }

    def toggle_recurring(self, vault_identifier: Optional[str] = None, recurring_id: str = "") -> Dict[str, Any]:
        """Pausa o reactiva una tarea recurrente."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        rec = mgr.toggle_recurring_task(recurring_id)
        if not rec:
            raise ValueError(f"Tarea recurrente {recurring_id} no encontrada.")
        return {"success": True, "id": rec.id, "active": rec.active}

    def delete_recurring(self, vault_identifier: Optional[str] = None, recurring_id: str = "") -> Dict[str, Any]:
        """Elimina una definición de tarea recurrente."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        deleted = mgr.delete_recurring_task(recurring_id)
        if not deleted:
            raise ValueError(f"Tarea recurrente {recurring_id} no encontrada.")
        return {"success": True, "deleted": recurring_id}

    def apply_recurring_to_week(
        self,
        vault_identifier: Optional[str] = None,
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Inyecta todas las tareas recurrentes activas que correspondan a la semana."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)
        self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        injected = mgr.apply_recurring_tasks(week)
        mgr.save_week(week)
        self._render_and_save_week_md(vault_path, week, mgr)
        return {"success": True, "injected": injected}

    # -------------------------------------------------------------------------
    # Proyectos, Backlog e Ideas
    # -------------------------------------------------------------------------
    def get_projects_overview(self, vault_identifier: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene las métricas consolidadas de todos los proyectos del vault."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        raw_metrics = mgr.get_all_projects_metrics()

        projects_serialized = []
        for pid, pdata in raw_metrics.get("projects", {}).items():
            proj_obj = pdata["project"]
            stats = pdata["stats"]
            projects_serialized.append({
                "id": proj_obj.id,
                "name": proj_obj.name,
                "description": proj_obj.description,
                "status": proj_obj.status,
                "stats": stats
            })

        return {
            "total_projects": raw_metrics.get("total_projects", 0),
            "total_tasks": raw_metrics.get("total_tasks", 0),
            "total_done": raw_metrics.get("total_done", 0),
            "total_pending": raw_metrics.get("total_pending", 0),
            "total_cancelled": raw_metrics.get("total_cancelled", 0),
            "total_backlog": raw_metrics.get("total_backlog", 0),
            "unassigned_backlog": raw_metrics.get("unassigned_backlog", 0),
            "global_completion_rate": raw_metrics.get("global_completion_rate", 0.0),
            "projects": projects_serialized
        }

    def create_project(
        self,
        vault_identifier: Optional[str] = None,
        project_id: str = "",
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Crea o actualiza un proyecto en el vault."""
        if not project_id or not project_id.strip():
            raise ValueError("El código del proyecto es obligatorio.")
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        proj = mgr.ensure_project(project_id=project_id, name=name, description=description)
        if name and proj.name != name.strip():
            proj.name = name.strip()
        if description is not None:
            proj.description = description.strip() if description.strip() else None
        mgr.save_projects()
        return {
            "success": True,
            "project": {
                "id": proj.id,
                "name": proj.name,
                "description": proj.description,
                "status": proj.status
            }
        }

    def get_backlog(
        self,
        vault_identifier: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Devuelve las tareas pendientes en el Backlog (no asignadas a ninguna semana/día)."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        scheduled = mgr.get_scheduled_task_ids()
        all_pending = mgr.list_backlog_tasks(project_id=project_id, pending_only=True)
        unscheduled = [self._serialize_task(t) for t in all_pending if t.id not in scheduled]
        return {
            "backlog_tasks": unscheduled,
            "count": len(unscheduled)
        }

    def create_backlog_task(
        self,
        vault_identifier: Optional[str] = None,
        title: str = "",
        project_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Crea una tarea directamente en el Backlog (sin semana ni día asignado)."""
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("El título de la tarea de backlog es obligatorio.")

        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)

        task_type, clean_title = TaskTypeRegistry.detect_task_type_and_clean_title(clean_title)
        proj_tag, clean_title = BitacoraMarkdownParser.parse_project_tag(clean_title)
        final_proj = project_id or proj_tag or "GENERAL"
        mgr.ensure_project(final_proj)

        task = mgr.create_task(
            title=clean_title,
            status="pending",
            project_id=final_proj,
            task_type=task_type or "task",
            description=description
        )

        backlog_path = os.path.join(vault_path, "[📋PROJECTS]✅BackLog.md")
        BitacoraRenderer.render_and_save_backlog(mgr, backlog_path, scheduled_task_ids=mgr.get_scheduled_task_ids())

        return {"success": True, "task": self._serialize_task(task)}

    def schedule_task_to_day(
        self,
        vault_identifier: Optional[str] = None,
        task_id: str = "",
        day_number: Optional[int] = None,
        target: str = "day",  # "day" | "week"
        year: Optional[int] = None,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Agenda una tarea del Backlog o de Tareas de la Semana a un día concreto (o a la semana)."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)
        self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        if task_id not in mgr.tasks:
            raise ValueError(f"Tarea {task_id} no encontrada.")

        if target == "week":
            mgr.add_week_task(week, task_id)
        else:
            now = datetime.now()
            target_day_num = int(day_number) if day_number is not None else now.day
            if not any(d.day_number == target_day_num for d in week.days) and week.days:
                target_day_num = week.days[0].day_number

            if task_id in week.week_task_ids:
                mgr.schedule_week_task_to_day(week, task_id, target_day_num)
            else:
                mgr.assign_task_to_day(task_id, week.year, week.week_number, target_day_num)

            for d in week.days:
                if d.day_number == target_day_num:
                    mgr.sort_day_tasks_pending_first(d)
                    break

        mgr.save_week(week)
        self._render_and_save_week_md(vault_path, week, mgr)

        backlog_path = os.path.join(vault_path, "[📋PROJECTS]✅BackLog.md")
        BitacoraRenderer.render_and_save_backlog(mgr, backlog_path, scheduled_task_ids=mgr.get_scheduled_task_ids())

        return {"success": True, "task": self._serialize_task(mgr.tasks[task_id])}

    def list_ideas(
        self,
        vault_identifier: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lista las ideas registradas en el vault."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        ideas = mgr.list_ideas(project_id=project_id)
        return {
            "ideas": [
                {
                    "id": i.id,
                    "title": i.title,
                    "content": i.content,
                    "status": i.status,
                    "project_id": i.project_id,
                    "created_at": i.created_at
                }
                for i in ideas
            ]
        }

    def create_idea(
        self,
        vault_identifier: Optional[str] = None,
        title: str = "",
        content: Any = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Crea una nueva Idea y actualiza [🧩GENERAL]🧠Ideas.md."""
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("El título de la idea es obligatorio.")

        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)

        proj_tag, clean_title = BitacoraMarkdownParser.parse_project_tag(clean_title)
        final_proj = project_id or proj_tag or "GENERAL"
        mgr.ensure_project(final_proj)

        if isinstance(content, str):
            bullets = [line.strip().lstrip("-*•").strip() for line in content.splitlines() if line.strip()]
        elif isinstance(content, list):
            bullets = [str(line).strip().lstrip("-*•").strip() for line in content if str(line).strip()]
        else:
            bullets = []

        idea = mgr.create_idea(title=clean_title, content=bullets, project_id=final_proj)
        ideas_path = os.path.join(vault_path, "[🧩GENERAL]🧠Ideas.md")
        BitacoraRenderer.render_and_save_ideas(mgr, ideas_path)

        return {
            "success": True,
            "idea": {
                "id": idea.id,
                "title": idea.title,
                "content": idea.content,
                "status": idea.status,
                "project_id": idea.project_id
            }
        }

    def update_idea_status(
        self,
        vault_identifier: Optional[str] = None,
        idea_id: str = "",
        status: str = "evaluating"
    ) -> Dict[str, Any]:
        """Cambia el estado de una idea ('evaluating', 'accepted', 'discarded') y sincroniza el Markdown."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)
        idea = mgr.update_idea_status(idea_id, status)
        if not idea:
            raise ValueError(f"Idea {idea_id} no encontrada.")

        ideas_path = os.path.join(vault_path, "[🧩GENERAL]🧠Ideas.md")
        BitacoraRenderer.render_and_save_ideas(mgr, ideas_path)
        return {
            "success": True,
            "idea": {
                "id": idea.id,
                "title": idea.title,
                "status": idea.status,
                "project_id": idea.project_id
            }
        }

    # -------------------------------------------------------------------------
    # Calendario Laboral y Consolidación
    # -------------------------------------------------------------------------
    def get_calendar_config(self, vault_identifier: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene la configuración de calendario laboral (patrón, festivos y vacaciones)."""
        vault_path = self.resolve_vault_path(vault_identifier)
        from brackets.managers.settings_manager import SettingsManager
        settings = SettingsManager(vault_path)
        return {
            "work_pattern": settings.data.get("work_pattern", {}),
            "locations": settings.data.get("locations", {}),
            "holidays": settings.list_holidays(),
            "vacations": settings.list_vacations(),
            "closures": settings.list_closures(),
            "intensive_workdays": settings.list_intensive_days(),
            "summary": settings.describe_work_pattern()
        }

    def add_calendar_holiday(
        self,
        vault_identifier: Optional[str] = None,
        date_str: str = "",
        name: str = ""
    ) -> Dict[str, Any]:
        """Añade o actualiza un día festivo en work_calendar.yaml."""
        vault_path = self.resolve_vault_path(vault_identifier)
        from brackets.managers.settings_manager import SettingsManager
        settings = SettingsManager(vault_path)
        settings.add_or_update_holiday(date_str=date_str.strip(), name=name.strip() or "Festivo")
        return {"success": True, "holidays": settings.list_holidays()}

    def delete_calendar_holiday(
        self,
        vault_identifier: Optional[str] = None,
        index: int = -1
    ) -> Dict[str, Any]:
        """Elimina un festivo por índice."""
        vault_path = self.resolve_vault_path(vault_identifier)
        from brackets.managers.settings_manager import SettingsManager
        settings = SettingsManager(vault_path)
        settings.delete_holiday(int(index))
        return {"success": True, "holidays": settings.list_holidays()}

    def add_calendar_vacation(
        self,
        vault_identifier: Optional[str] = None,
        start_str: str = "",
        end_str: str = "",
        name: str = ""
    ) -> Dict[str, Any]:
        """Añade o actualiza un periodo de vacaciones en work_calendar.yaml."""
        vault_path = self.resolve_vault_path(vault_identifier)
        from brackets.managers.settings_manager import SettingsManager
        settings = SettingsManager(vault_path)
        settings.add_or_update_vacation(
            start_str=start_str.strip(),
            end_str=end_str.strip(),
            name=name.strip() or "Vacaciones"
        )
        return {"success": True, "vacations": settings.list_vacations()}

    def delete_calendar_vacation(
        self,
        vault_identifier: Optional[str] = None,
        index: int = -1
    ) -> Dict[str, Any]:
        """Elimina un periodo de vacaciones por índice."""
        vault_path = self.resolve_vault_path(vault_identifier)
        from brackets.managers.settings_manager import SettingsManager
        settings = SettingsManager(vault_path)
        settings.delete_vacation(int(index))
        return {"success": True, "vacations": settings.list_vacations()}

    def update_work_pattern(
        self,
        vault_identifier: Optional[str] = None,
        defaults: Optional[Dict[str, str]] = None,
        alternating_day: Optional[str] = None,
        even_week: Optional[str] = None,
        odd_week: Optional[str] = None
    ) -> Dict[str, Any]:
        """Actualiza el patrón de trabajo semanal en work_calendar.yaml."""
        vault_path = self.resolve_vault_path(vault_identifier)
        from brackets.managers.settings_manager import SettingsManager
        settings = SettingsManager(vault_path)
        if defaults and isinstance(defaults, dict):
            for d_key, loc in defaults.items():
                if d_key in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                    settings.set_day_location(d_key, loc)
        if alternating_day and even_week and odd_week:
            settings.set_alternating(alternating_day, even_week, odd_week)
        return {
            "success": True,
            "work_pattern": settings.data.get("work_pattern", {}),
            "summary": settings.describe_work_pattern()
        }

    def consolidate_month(
        self,
        vault_identifier: Optional[str] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
        delete_source: bool = False
    ) -> Dict[str, Any]:
        """Consolida todas las bitácoras semanales de un mes en [YYYY][MM].md."""
        vault_path = self.resolve_vault_path(vault_identifier)
        now = datetime.now()
        target_year = int(year) if year else now.year
        target_month = int(month) if month else now.month

        import contextlib
        import io
        from brackets.consolidators.month import MonthConsolidator
        consolidator = MonthConsolidator(vault_path)
        with contextlib.redirect_stdout(io.StringIO()):
            ok = consolidator.consolidate_month(
                year=target_year,
                month=target_month,
                interactive=False,
                delete_source=bool(delete_source)
            )
        if not ok:
            return {
                "success": False,
                "message": f"No se encontraron bitácoras semanales para {target_year}-{target_month:02d}."
            }
        output_file = f"[{target_year}][{target_month:02d}].md"
        return {
            "success": True,
            "file": output_file,
            "year": target_year,
            "month": target_month
        }

    def consolidate_year(
        self,
        vault_identifier: Optional[str] = None,
        year: Optional[int] = None,
        delete_source: bool = False
    ) -> Dict[str, Any]:
        """Consolida todos los archivos mensuales de un año en [YYYY].md."""
        vault_path = self.resolve_vault_path(vault_identifier)
        now = datetime.now()
        target_year = int(year) if year else now.year

        import contextlib
        import io
        from brackets.consolidators.year import YearConsolidator
        consolidator = YearConsolidator(vault_path)
        with contextlib.redirect_stdout(io.StringIO()):
            ok = consolidator.consolidate_year(
                year=target_year,
                interactive=False,
                delete_source=bool(delete_source)
            )
        if not ok:
            return {
                "success": False,
                "message": f"No se encontraron consolidados mensuales ([{target_year}][MM].md) para consolidar el año {target_year}."
            }
        output_file = f"[{target_year}].md"
        return {
            "success": True,
            "file": output_file,
            "year": target_year
        }
