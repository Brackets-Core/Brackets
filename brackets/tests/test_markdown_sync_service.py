#!/usr/bin/env python3
"""
Tests unitarios para MarkdownSyncService (Sincronización Bidireccional Markdown -> YAML).
"""

import os
import shutil
import tempfile
import unittest
from datetime import datetime

from brackets.models.entities import WeekSchedule, DaySchedule
from brackets.managers.entity_manager import EntityManager
from brackets.generators.bitacora_renderer import BitacoraRenderer
from brackets.managers.markdown_sync_service import MarkdownSyncService


class TestMarkdownSyncService(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.tmp_dir, "data")
        self.manager = EntityManager(self.data_dir)
        self.sync_service = MarkdownSyncService(self.manager, self.tmp_dir)

        # Crear semana base y persistir
        self.week = WeekSchedule(
            year=2026,
            month=8,
            week_number=35,
            days=[
                DaySchedule(day_number=24, location_emoji="🏠", location_note=None, task_ids=[]),
                DaySchedule(day_number=25, location_emoji="🚗", location_note=None, task_ids=[])
            ],
            topics_task_ids=[],
            note_ids=[]
        )
        self.manager.save_week(self.week)

        # Tarea base en día 24
        self.task_day24 = self.manager.create_task(
            title="Tarea Base Día 24",
            year=2026,
            week_num=35,
            day_number=24
        )

        # Topic base
        self.topic_base = self.manager.create_task(
            title="Topic Semanal Base",
            year=2026,
            week_num=35,
            is_topic=True
        )

        # Nota base
        self.note_base = self.manager.add_note(
            title="Nota Base",
            content=["Punto original 1", "Punto original 2"],
            year=2026,
            week_num=35
        )

        # Recargar semana con todos los IDs vinculados
        self.week = self.manager.load_week(2026, 35)

        # Renderizar archivo Markdown inicial
        self.md_path = os.path.join(self.tmp_dir, "[2026][08]Week35.md")
        BitacoraRenderer.render_and_save_week(self.week, self.manager, self.md_path)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_sync_week_toggle_checkboxes(self):
        """Verifica que marcar una tarea con [x] a mano en el markdown actualiza el estado en YAML."""
        # Modificar archivo .md simulando edición manual en Obsidian
        with open(self.md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Marcar la tarea del día 24 como completada
        content_modified = content.replace("- [ ] Tarea Base Día 24", "- [x] Tarea Base Día 24")
        with open(self.md_path, "w", encoding="utf-8") as f:
            f.write(content_modified)

        # Ejecutar sincronizador
        synced = self.sync_service.sync_week_from_markdown(self.md_path, 2026, 35)
        self.assertTrue(synced)

        # Verificar que la tarea en EntityManager ahora está completada
        task = self.manager.tasks.get(self.task_day24.id)
        self.assertIsNotNone(task)
        self.assertTrue(task.is_done)
        self.assertEqual(task.status, "done")
        self.assertIsNotNone(task.completed_at)

    def test_sync_week_new_manual_task_in_day(self):
        """Verifica que añadir una tarea a mano bajo un día crea la tarea y la vincula en el YAML."""
        with open(self.md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Añadir nueva tarea en día 25
        content_modified = content.replace(
            "## 🚗25\n  - [ ]",
            "## 🚗25\n  - [ ] Nueva Tarea Escrita A Mano\n  - [ ]"
        )
        if "## 🚗25\n  - [ ]" not in content:
            content_modified = content.replace(
                "## 🚗25",
                "## 🚗25\n  - [ ] Nueva Tarea Escrita A Mano"
            )

        with open(self.md_path, "w", encoding="utf-8") as f:
            f.write(content_modified)

        synced = self.sync_service.sync_week_from_markdown(self.md_path, 2026, 35)
        self.assertTrue(synced)

        # Verificar que se creó la tarea
        created_tasks = [t for t in self.manager.tasks.values() if t.title == "Nueva Tarea Escrita A Mano"]
        self.assertEqual(len(created_tasks), 1)

        day25 = next(d for d in self.week.days if d.day_number == 25)
        self.assertIn(created_tasks[0].id, day25.task_ids)

    def test_sync_week_edited_notes_bullets(self):
        """Verifica que modificar viñetas de una nota en Markdown actualiza la nota en YAML."""
        with open(self.md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Modificar las viñetas de la nota de forma independiente de saltos de línea
        content_modified = content.replace("Punto original 1", "Punto editado 1")
        content_modified = content_modified.replace("Punto original 2", "Punto editado 2\n  - Nuevo punto 3")
        with open(self.md_path, "w", encoding="utf-8") as f:
            f.write(content_modified)

        synced = self.sync_service.sync_week_from_markdown(self.md_path, 2026, 35)
        self.assertTrue(synced)

        note = self.manager.notes.get(self.note_base.id)
        self.assertEqual(len(note.content), 3)
        self.assertEqual(note.content[0], "Punto editado 1")
        self.assertEqual(note.content[2], "Nuevo punto 3")

    def test_sync_ideas_from_markdown(self):
        """Verifica que crear o modificar ideas en [🧩GENERAL]🧠Ideas.md se sincronice a ideas.yaml."""
        # 1. Crear idea inicial
        self.manager.create_idea(
            title="Idea Existente",
            project_id="PROJ_A",
            content=["Hipótesis 1"]
        )
        ideas_path = os.path.join(self.tmp_dir, "[🧩GENERAL]🧠Ideas.md")
        BitacoraRenderer.render_and_save_ideas(self.manager, ideas_path)

        # 2. Modificar archivo .md a mano: aceptar la existente y crear una nueva
        with open(ideas_path, "r", encoding="utf-8") as f:
            ideas_content = f.read()

        # Aceptar la existente (- [x]) y añadir nueva idea bajo PROJ_A
        ideas_modified = ideas_content.replace(
            "- [ ] Idea Existente",
            "- [x] Idea Existente\n  - [ ] Segunda Idea Añadida A Mano\n    - Hipótesis manual"
        )
        with open(ideas_path, "w", encoding="utf-8") as f:
            f.write(ideas_modified)

        # 3. Sincronizar
        synced = self.sync_service.sync_ideas_from_markdown(ideas_path)
        self.assertTrue(synced)

        # 4. Verificar
        existing = next(i for i in self.manager.ideas.values() if i.title == "Idea Existente")
        self.assertEqual(existing.status, "accepted")

        new_idea = next((i for i in self.manager.ideas.values() if i.title == "Segunda Idea Añadida A Mano"), None)
        self.assertIsNotNone(new_idea)
        self.assertEqual(new_idea.project_id, "PROJ_A")
        self.assertIn("Hipótesis manual", new_idea.content)


    def test_sync_week_deduplicates_pending_tasks_across_days(self):
        """Verifica que si un markdown contiene la misma tarea pendiente en varios días, solo se asigna al último."""
        # Simular markdown con la misma tarea pendiente en día 24 y día 25
        with open(self.md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Añadir tarea pendiente en día 24 y en día 25
        content_modified = content.replace(
            "## 🚗25",
            "## 🚗25\n  - [ ] Tarea Base Día 24"
        )
        with open(self.md_path, "w", encoding="utf-8") as f:
            f.write(content_modified)

        synced = self.sync_service.sync_week_from_markdown(self.md_path, 2026, 35)
        self.assertTrue(synced)

        day24 = next(d for d in self.week.days if d.day_number == 24)
        day25 = next(d for d in self.week.days if d.day_number == 25)

        # Debe estar en día 25 (el último) y NO en día 24
        self.assertIn(self.task_day24.id, day25.task_ids)
        self.assertNotIn(self.task_day24.id, day24.task_ids)

    def test_sync_week_automatically_registers_new_weekend_day(self):
        """Verifica que si se añade un día de intervención a mano en el markdown, se registre en el YAML."""
        with open(self.md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Añadir día 29 al final del markdown
        content += "\n## 🛠️29 (Intervención)\n  - [ ] Tarea de guardia el sábado\n"
        with open(self.md_path, "w", encoding="utf-8") as f:
            f.write(content)

        synced = self.sync_service.sync_week_from_markdown(self.md_path, 2026, 35)
        self.assertTrue(synced)

        day29 = next((d for d in self.week.days if d.day_number == 29), None)
        self.assertIsNotNone(day29)
        self.assertEqual(day29.location_emoji, "🛠️")
        self.assertEqual(day29.location_note, "Intervención")
        self.assertEqual(len(day29.task_ids), 1)

        task_obj = self.manager.tasks[day29.task_ids[0]]
        self.assertEqual(task_obj.title, "Tarea de guardia el sábado")

    def test_sync_week_move_task_between_days_and_mark_done(self):
        """Verifica que mover una tarea a otro día y marcarla como [x] la quita del día original, la pone en el nuevo y la marca resuelta."""
        with open(self.md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # task_day24 estaba en día 24. Lo quitamos de día 24 y lo ponemos en día 25 como [x]
        content_modified = content.replace(f"  - [ ] {self.task_day24.title}\n", "")
        content_modified = content_modified.replace(
            "## 🚗25",
            f"## 🚗25\n  - [x] {self.task_day24.title}"
        )
        with open(self.md_path, "w", encoding="utf-8") as f:
            f.write(content_modified)

        synced = self.sync_service.sync_week_from_markdown(self.md_path, 2026, 35)
        self.assertTrue(synced)

        day24 = next(d for d in self.week.days if d.day_number == 24)
        day25 = next(d for d in self.week.days if d.day_number == 25)

        # Debe estar en día 25 y NO en día 24
        self.assertIn(self.task_day24.id, day25.task_ids)
        self.assertNotIn(self.task_day24.id, day24.task_ids)

        # Debe estar marcada como done
        self.assertTrue(self.task_day24.is_done)
        self.assertEqual(self.task_day24.status, "done")

    def test_sync_week_mark_task_as_cancelled_with_tildes(self):
        """Verifica que tachar una tarea con ~~...~~ en el markdown la marca como cancelled sin crear duplicados."""
        with open(self.md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Cambiar "  - [ ] Tarea Base Día 24" por "  - [ ] ~~Tarea Base Día 24~~"
        content_modified = content.replace(
            f"  - [ ] {self.task_day24.title}",
            f"  - [ ] ~~{self.task_day24.title}~~"
        )
        with open(self.md_path, "w", encoding="utf-8") as f:
            f.write(content_modified)

        initial_tasks_count = len(self.manager.tasks)
        synced = self.sync_service.sync_week_from_markdown(self.md_path, 2026, 35)
        self.assertTrue(synced)

        # No debe haber creado una nueva tarea duplicada
        self.assertEqual(len(self.manager.tasks), initial_tasks_count)

        # La tarea existente debe estar cancelada con título limpio
        task = self.manager.tasks[self.task_day24.id]
        self.assertTrue(task.is_cancelled)
        self.assertEqual(task.status, "cancelled")
        self.assertEqual(task.title, "Tarea Base Día 24")

        # Verificar renderizado de vuelta a Markdown
        rendered_md = BitacoraRenderer.render_week(self.week, self.manager)
        self.assertIn(f"  - [ ] ~~{self.task_day24.title}~~", rendered_md)

    def test_sync_week_create_new_cancelled_task(self):
        """Verifica que una nueva tarea introducida como tachada se crea con status cancelled y título limpio."""
        with open(self.md_path, "r", encoding="utf-8") as f:
            content = f.read()

        content_modified = content.replace(
            "## 🚗25",
            "## 🚗25\n  - [ ] ~~Reunión Anulada [GENERAL]~~"
        )
        with open(self.md_path, "w", encoding="utf-8") as f:
            f.write(content_modified)

        synced = self.sync_service.sync_week_from_markdown(self.md_path, 2026, 35)
        self.assertTrue(synced)

        day25 = next(d for d in self.week.days if d.day_number == 25)
        self.assertEqual(len(day25.task_ids), 1)

        task = self.manager.tasks[day25.task_ids[0]]
        self.assertTrue(task.is_cancelled)
        self.assertEqual(task.title, "Reunión Anulada [GENERAL]")
        self.assertNotIn("~~", task.title)


    def test_sync_week_erase_task_deletes_from_tasks_table(self):
        """Verifica que borrar la línea de una tarea en la bitácora la elimina de la tabla de tareas si no está en otras semanas."""
        task_id = self.task_day24.id
        self.assertIn(task_id, self.manager.tasks)

        with open(self.md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Eliminar la línea de la tarea completamente de la bitácora
        content_modified = content.replace(f"  - [ ] {self.task_day24.title}\n", "")
        with open(self.md_path, "w", encoding="utf-8") as f:
            f.write(content_modified)

        synced = self.sync_service.sync_week_from_markdown(self.md_path, 2026, 35)
        self.assertTrue(synced)

        # La tarea debe haber sido eliminada de la base de datos de tareas
        self.assertNotIn(task_id, self.manager.tasks)

        # Y el día ya no debe contener la tarea
        day24 = next(d for d in self.week.days if d.day_number == 24)
        self.assertNotIn(task_id, day24.task_ids)

    def test_sync_various_strikethrough_formats(self):
        """Verifica que diferentes formatos de tachado se reconocen como cancelled sin ser eliminados."""
        with open(self.md_path, "r", encoding="utf-8") as f:
            content = f.read()

        lines_to_add = (
            "  - [ ] ~~Tarea Con Ticket~~ [🎫TICKET-123]\n"
            "  - [ ] ~~Tarea Con Comentario~~ (comentada)\n"
            "  ~~- [ ] Tarea Con Tachado Exterior~~\n"
            "  - ~~[ ] Tarea Con Checkbox Dentro~~\n"
        )
        content_modified = content.replace("## 🚗25", f"## 🚗25\n{lines_to_add}")
        with open(self.md_path, "w", encoding="utf-8") as f:
            f.write(content_modified)

        synced = self.sync_service.sync_week_from_markdown(self.md_path, 2026, 35)
        self.assertTrue(synced)

        day25 = next(d for d in self.week.days if d.day_number == 25)
        self.assertEqual(len(day25.task_ids), 4)

        for tid in day25.task_ids:
            task = self.manager.tasks[tid]
            self.assertTrue(task.is_cancelled, f"Task {task.title} should be cancelled")
            self.assertNotIn("~~", task.title)
            self.assertFalse(task.title.startswith("[ ]"))

    def test_cancel_and_toggle_reactivation(self):
        """Verifica que cancel_task marca como cancelled y toggle_task reactiva a pending."""
        task = self.manager.create_task("Prueba Cancelar", year=2026, week_num=35, day_number=24)
        self.assertEqual(task.status, "pending")

        # Cancelar tarea
        self.manager.cancel_task(task.id)
        self.assertTrue(task.is_cancelled)
        self.assertIn(task.id, self.manager.tasks)

        # Reactivar con toggle_task
        self.manager.toggle_task(task.id)
        self.assertEqual(task.status, "pending")
        self.assertFalse(task.is_cancelled)


if __name__ == "__main__":
    unittest.main()

