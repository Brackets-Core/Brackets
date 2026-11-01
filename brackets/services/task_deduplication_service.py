#!/usr/bin/env python3
"""
Servicio de Deduplicación y Consolidación Canónica de Tareas.
"""

from __future__ import annotations
import glob
import os
import re
from collections import defaultdict
from typing import Dict, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from brackets.managers.entity_manager import EntityManager


class TaskDeduplicationService:
    """Gestiona la deduplicación de tareas redundantes y la reasignación de IDs canónicos en semanas."""

    def __init__(self, manager: EntityManager):
        self.manager = manager

    def deduplicate_tasks(self) -> Tuple[int, int]:
        """
        Desduplica tareas en tasks.yaml y reasigna los IDs en todos los archivos de semanas.
        - Para tareas recurrentes multidía (como Daily S^3 con N días en la semana):
          mantiene exactamente N instancias canónicas (1 por slot de día) y fusiona las demás.
        - Para tareas recurrentes de 1 día: mantiene 1 instancia canónica.
        - Para tareas no recurrentes repetidas por arrastre: mantiene 1 instancia canónica
          (priorizando la que esté completada, con proyecto asignado o con menor ID).
        - Reemplaza las referencias a tareas redundantes en data/weeks/*.yaml.
        - Elimina las entidades duplicadas de self.manager.tasks y guarda cambios en disco.
        Devuelve (total_reemplazos, total_tareas_eliminadas).
        """
        replacement_map: Dict[str, str] = {}

        # 1. Tareas Recurrentes
        for rec in self.manager.recurring_tasks.values():
            if rec.recurrence_type == "weekly_days":
                k = len(rec.days_of_week) if rec.days_of_week else 1
            else:
                k = 1

            matching = [
                t for t in self.manager.tasks.values()
                if t.recurring_id == rec.id or (not t.recurring_id and t.title == rec.title)
            ]
            matching.sort(key=lambda x: (0 if x.recurring_id == rec.id else 1, x.id))

            canonicals = matching[:k]
            for c in canonicals:
                c.recurring_id = rec.id
                if rec.project_id and (not c.project_id or c.project_id == "POR_ASIGNAR"):
                    c.project_id = rec.project_id

            for idx, extra in enumerate(matching[k:]):
                slot_idx = idx % k
                canonical_slot = canonicals[slot_idx]
                replacement_map[extra.id] = canonical_slot.id
                if canonical_slot.is_pending and (extra.is_done or extra.is_cancelled):
                    canonical_slot.status = extra.status
                    canonical_slot.completed_at = extra.completed_at

        # 2. Tareas No Recurrentes
        non_rec_tasks = [
            t for t in self.manager.tasks.values()
            if t.id not in replacement_map and not t.recurring_id
        ]
        groups = defaultdict(list)
        for t in non_rec_tasks:
            key = t.title.strip()
            groups[key].append(t)

        for title, group in groups.items():
            if len(group) > 1:
                group.sort(key=lambda x: (
                    0 if x.is_done else 1,
                    0 if x.project_id and x.project_id != "POR_ASIGNAR" else 1,
                    x.id
                ))
                canonical = group[0]
                if not canonical.project_id or canonical.project_id == "POR_ASIGNAR":
                    for other in group[1:]:
                        if other.project_id and other.project_id != "POR_ASIGNAR":
                            canonical.project_id = other.project_id
                            break

                for extra in group[1:]:
                    replacement_map[extra.id] = canonical.id

        if not replacement_map:
            return (0, 0)

        # 3. Reasignar en todos los archivos de semanas
        week_files = sorted(glob.glob(os.path.join(self.manager.weeks_dir, "*.yaml")))
        for wpath in week_files:
            match = re.search(r'(\d{4})-W(\d{2})\.yaml$', os.path.basename(wpath))
            if not match:
                continue
            year = int(match.group(1))
            week_num = int(match.group(2))
            week = self.manager.load_week(year, week_num, reload=True)
            if not week:
                continue

            changed = False
            new_week_task_ids = []
            for tid in week.week_task_ids:
                new_id = replacement_map.get(tid, tid)
                if new_id not in new_week_task_ids:
                    new_week_task_ids.append(new_id)
                if new_id != tid:
                    changed = True
            week.week_task_ids = new_week_task_ids

            new_topics_task_ids = []
            for tid in week.topics_task_ids:
                new_id = replacement_map.get(tid, tid)
                if new_id not in new_topics_task_ids:
                    new_topics_task_ids.append(new_id)
                if new_id != tid:
                    changed = True
            week.topics_task_ids = new_topics_task_ids

            for d in week.days:
                new_day_task_ids = []
                for tid in d.task_ids:
                    new_id = replacement_map.get(tid, tid)
                    if new_id not in new_day_task_ids:
                        new_day_task_ids.append(new_id)
                    if new_id != tid:
                        changed = True
                d.task_ids = new_day_task_ids

            if changed:
                self.manager.save_week(week)

        # 4. Eliminar tareas obsoletas de self.manager.tasks
        removed_count = 0
        for old_id, canonical_id in replacement_map.items():
            if old_id != canonical_id and old_id in self.manager.tasks:
                del self.manager.tasks[old_id]
                removed_count += 1

        self.manager.save_tasks()
        return (len(replacement_map), removed_count)
