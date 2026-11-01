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
        vaults = self.list_vaults()
        if not vaults:
            return self.workspace_root

        if not vault_identifier:
            # Preferir MyJobNotes por defecto o el primer vault disponible
            for v in vaults:
                if v["name"].lower() == "myjobnotes":
                    return v["path"]
            return vaults[0]["path"]

        target = vault_identifier.strip().lower()
        for v in vaults:
            if v["name"].lower() == target or os.path.abspath(v["path"]).lower() == os.path.abspath(vault_identifier).lower():
                return v["path"]

        # Si apunta a un directorio válido con data/config.yaml
        cand = os.path.abspath(vault_identifier)
        if os.path.exists(os.path.join(cand, "data", "config.yaml")):
            return cand

        return vaults[0]["path"]

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

        week = mgr.load_week(target_year, target_week)
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
        week = self._get_or_create_week(vault_path, mgr, year=year, week_number=week_number)

        # Sincronizar cambios manuales desde el .md
        self._sync_week_from_markdown_if_exists(vault_path, week, mgr)

        # Determinar día activo
        active_day = None
        if day_number is not None:
            active_day = next((d for d in week.days if d.day_number == day_number), None)

        if not active_day:
            active_day = next((d for d in week.days if d.day_number == now.day), None)
        if not active_day and week.days:
            active_day = week.days[0]

        # Serializar días de la semana
        days_data = []
        for d in week.days:
            days_data.append({
                "day_number": d.day_number,
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
                "week_tasks": week_tasks
            },
            "active_day": {
                "day_number": active_day.day_number,
                "location_emoji": active_day.location_emoji,
                "location_note": active_day.location_note
            } if active_day else None,
            "days": days_data,
            "today_tasks": today_tasks,
            "week_tasks": week_tasks,
            "notes": notes_data,
            "task_types": task_types
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
            "completed_at": task.completed_at
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

        task = mgr.create_task(
            title=clean_title,
            status=status,
            project_id=final_proj,
            year=week.year,
            week_num=week.week_number,
            day_number=target_day_num if not is_week_task else None,
            is_week_task=is_week_task,
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
            # Reordenar día correspondiente
            for d in week.days:
                if task.id in d.task_ids:
                    mgr.sort_day_tasks_pending_first(d)
                    break
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

    def sync_week(self, vault_identifier: Optional[str] = None) -> Dict[str, Any]:
        """Fuerza la sincronización bidireccional Markdown ↔ YAML de la semana activa."""
        vault_path = self.resolve_vault_path(vault_identifier)
        mgr = self.get_entity_manager(vault_path)

        now = datetime.now()
        iso_year, iso_week, _ = now.isocalendar()
        week = mgr.load_week(iso_year, iso_week)
        if not week and mgr.weeks:
            last_key = sorted(mgr.weeks.keys())[-1]
            week = mgr.weeks[last_key]

        if not week:
            return {"status": "error", "message": "No hay semana activa"}

        md_path = generate_filename(week.year, week.month, week.week_number, directory=vault_path)
        if os.path.exists(md_path):
            service = MarkdownSyncService(mgr, vault_path)
            synced = service.sync_week_from_markdown(md_path, week.year, week.week_number)
            self._render_and_save_week_md(vault_path, week, mgr)
            return {"status": "ok", "synced": synced, "file": os.path.basename(md_path)}

        return {"status": "warning", "message": "Archivo Markdown no encontrado"}
