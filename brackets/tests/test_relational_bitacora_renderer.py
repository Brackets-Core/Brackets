#!/usr/bin/env python3
"""
Tests para el motor relacional YAML-First y el BitacoraRenderer de Brackets.
"""

import sys
import os
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from brackets.models.entities import Task, Note, Definition, WeekSchedule
from brackets.managers.entity_manager import EntityManager
from brackets.generators.bitacora_renderer import BitacoraRenderer


class TestRelationalBitacoraRenderer(unittest.TestCase):
    """Pruebas unitarias para EntityManager y BitacoraRenderer."""

    def setUp(self):
        # Crear directorio temporal y copiar mock data
        self.tmp_dir = tempfile.mkdtemp()
        self.mock_source = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data", "mock"
        )
        # Copiar estructura mock a temporal
        shutil.copytree(self.mock_source, os.path.join(self.tmp_dir, "mock_data"))
        self.data_dir = os.path.join(self.tmp_dir, "mock_data")
        self.manager = EntityManager(self.data_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_load_entities(self):
        """Verifica que las tablas de entidades se carguen correctamente."""
        self.assertGreater(len(self.manager.tasks), 0)
        self.assertGreater(len(self.manager.definitions), 0)
        self.assertGreater(len(self.manager.notes), 0)

        first_task = list(self.manager.tasks.values())[0]
        self.assertIsNotNone(first_task)
        self.assertTrue(first_task.id.startswith("TSK-"))

    def test_render_week_markdown(self):
        """Verifica que el renderizado Markdown coincida con el formato oficial de Bitácoras."""
        week = self.manager.load_week(2026, 34)
        self.assertIsNotNone(week)

        markdown = BitacoraRenderer.render_week(week, self.manager)

        # 1. Encabezado
        self.assertIn("# 🗓️Week 34", markdown)

        # 2. Topics
        self.assertIn("## 🎯Topics", markdown)

        # 3. Week Tasks
        self.assertIn("## 📋Week Tasks", markdown)

        # 4. Notes
        self.assertIn("## 📝Notes", markdown)

        # 4. Días
        self.assertTrue(len(week.days) > 0)
        first_day = week.days[0]
        self.assertIn(f"## {first_day.location_emoji}{first_day.day_number}", markdown)

        # 5. Definiciones al pie
        self.assertIn("## Definiciones", markdown)
        self.assertIn("<!-- Definiciones -->", markdown)

    def test_toggle_task_and_regenerate(self):
        """Valida que alternar el estado de una tarea actualice el YAML y regenere el [x] en Markdown."""
        week = self.manager.load_week(2026, 34)
        
        # Buscar la primera tarea pendiente de la semana
        task_id = None
        for tid in week.topics_task_ids:
            t = self.manager.tasks.get(tid)
            if t and t.is_pending:
                task_id = tid
                break

        if not task_id:
            for d in week.days:
                for tid in d.task_ids:
                    t = self.manager.tasks.get(tid)
                    if t and t.is_pending:
                        task_id = tid
                        break
                if task_id:
                    break

        if not task_id:
            # Crear una tarea para el test si todas estaban completadas
            t_obj = self.manager.create_task(title="Tarea de prueba para toggle", year=2026, week_num=34, is_topic=True)
            task_id = t_obj.id

        task = self.manager.tasks.get(task_id)
        self.assertTrue(task.is_pending)

        # Cambiar a completada
        self.manager.toggle_task(task_id)
        self.assertTrue(task.is_done)
        self.assertIsNotNone(task.completed_at)

        # Regenerar markdown
        markdown = BitacoraRenderer.render_week(week, self.manager)
        self.assertIn(f"- [x] {task.title}", markdown)

        # Cambiar de nuevo a pendiente
        self.manager.toggle_task(task_id)
        self.assertTrue(task.is_pending)
        markdown2 = BitacoraRenderer.render_week(week, self.manager)
        self.assertIn(f"- [ ] {task.title}", markdown2)

    def test_add_jira_task_auto_definitions(self):
        """Valida que al añadir una tarea con Jira ticket, la definición aparezca automáticamente."""
        week = self.manager.load_week(2026, 34)

        # 1. Asegurar definición Jira
        jira_def = self.manager.ensure_jira_definition("ATLM-99999")
        self.assertEqual(jira_def.id, "[🎫ATLM-99999]")

        # 2. Crear tarea asociada al día 21
        new_task = self.manager.create_task(
            title=f"Revisar nueva funcionalidad de pagos {jira_def.id}",
            year=2026,
            week_num=34,
            day_number=21
        )

        # 3. Renderizar markdown
        markdown = BitacoraRenderer.render_week(week, self.manager)

        self.assertIn(f"- [ ] Revisar nueva funcionalidad de pagos {jira_def.id}", markdown)
        self.assertIn(f"[🎫ATLM-99999]: {self.manager.jira_base_url}ATLM-99999", markdown)

    def test_add_note_and_render(self):
        """Valida que añadir una nota la incorpore en la sección ## 📝Notes."""
        week = self.manager.load_week(2026, 34)

        self.manager.add_note(
            content="Conclusión importante: El flujo de AMRs no requiere DXC.",
            year=2026,
            week_num=34
        )

        markdown = BitacoraRenderer.render_week(week, self.manager)
        self.assertIn("- Conclusión importante: El flujo de AMRs no requiere DXC.", markdown)

    def test_structured_note_with_title_and_indented_content(self):
        """Valida que las notas con título se rendericen con - ### Título y viñetas indentadas."""
        week = self.manager.load_week(2026, 34)

        note = self.manager.add_note(
            title="Upgrade versión de InfluxDB 25/02/2026",
            content=[
                "@MarcCristany propone hacer un upgrade de la versión de InfluxDB",
                "Tanto @FerranVallalta como @PabloMartinez están de acuerdo"
            ],
            year=2026,
            week_num=34,
            project_id="METRICS_INFLUXDB"
        )

        markdown = BitacoraRenderer.render_week(week, self.manager)
        self.assertIn("- ### Upgrade versión de InfluxDB 25/02/2026", markdown)
        self.assertIn("  - @MarcCristany propone hacer un upgrade de la versión de InfluxDB", markdown)
        self.assertIn("  - Tanto @FerranVallalta como @PabloMartinez están de acuerdo", markdown)

    def test_monthly_notes_persistence(self):
        """Verifica que las notas se guarden y carguen organizadas por mes en tables/notes/YYYY-MM.yaml."""
        # Agregar una nota en un mes específico
        self.manager.add_note(
            title="Nota de prueba mensual",
            content=["Punto 1", "Punto 2"],
            year=2026,
            week_num=34,
            month="2026-08",
            project_id="ROVO_AI"
        )

        # Verificar archivo físico
        monthly_file = os.path.join(self.manager.notes_dir, "2026-08.yaml")
        self.assertTrue(os.path.exists(monthly_file))

        # Crear nuevo manager sobre el mismo directorio para validar recarga limpia
        new_manager = EntityManager(self.data_dir)
        matching = [n for n in new_manager.notes.values() if n.title == "Nota de prueba mensual"]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].month, "2026-08")
        self.assertEqual(matching[0].project_id, "ROVO_AI")

    def test_render_ideas_grouped_by_project_without_id(self):
        """Valida que render_ideas agrupe por proyecto, sin IDs visibles y con formato limpio."""
        # Crear ideas en distintos proyectos
        self.manager.create_idea(
            title="Evaluar DuckDB para analítica",
            content=["Soporta SQL", "Muy rápido"],
            project_id="METRICS_INFLUXDB",
            status="evaluating"
        )
        self.manager.create_idea(
            title="Diagrama de arquitectura BT",
            content=[],
            project_id="GENERAL",
            status="accepted"
        )

        md = BitacoraRenderer.render_ideas(self.manager)

        # Encabezado
        self.assertIn("# 🧠Ideas", md)
        # Secciones por proyecto
        self.assertIn("## 📁 METRICS_INFLUXDB", md)
        self.assertIn("## 📁 GENERAL", md)
        # Ideas renderizadas
        self.assertIn("- [ ] Evaluar DuckDB para analítica", md)
        self.assertIn("  - Soporta SQL", md)
        self.assertIn("- [x] Diagrama de arquitectura BT", md)
        # Sin ID técnico visible
        self.assertNotIn("IDEA-", md)

    def test_render_backlog_grouped_by_project(self):
        """Valida que render_backlog agrupe las tareas pendientes no agendadas por proyecto."""
        proj = self.manager.ensure_project("BACKLOG_TEST_PROJ", name="Backlog Test Proj")
        task = self.manager.create_task(
            title="Tarea no agendada de prueba",
            project_id=proj.id
        )

        md = BitacoraRenderer.render_backlog(self.manager, scheduled_task_ids=set())

        self.assertIn("# ✅BackLog de Proyectos", md)
        self.assertIn(f"## 📁 {proj.id}", md)
        self.assertIn(f"- [ ] {task.title}", md)

    def test_day_rollover_tasks(self):
        """Valida que rollover_day_tasks mueva tareas pendientes de días previos al día actual."""
        week = self.manager.load_week(2026, 34)
        day1 = week.days[0]  # Día previo
        day2 = week.days[1]  # Día actual

        # Crear tarea en día 1
        task = self.manager.create_task(
            title="Tarea pendiente del día 1",
            year=2026,
            week_num=34,
            day_number=day1.day_number
        )
        self.assertIn(task.id, day1.task_ids)
        self.assertNotIn(task.id, day2.task_ids)

        # Ejecutar rollover sobre día 2
        rolled = self.manager.rollover_day_tasks(week, day2.day_number)
        self.assertGreaterEqual(rolled, 1)
        self.assertIn(task.id, day2.task_ids)
        self.assertNotIn(task.id, day1.task_ids)

    def test_two_weeks_rollover_rule(self):
        """Valida que una tarea arrastrada durante 2 semanas se desagenda y pasa a backlog."""
        week1 = self.manager.load_week(2026, 31)
        week2 = self.manager.load_week(2026, 32)
        week3 = self.manager.load_week(2026, 33)

        # Crear tarea pendiente en semana 1
        task_old = self.manager.create_task(title="Tarea muy antigua", year=2026, week_num=31, is_topic=True)
        task_new = self.manager.create_task(title="Tarea reciente", year=2026, week_num=32, is_topic=True)

        # Añadir task_old también a week2 (como si se hubiera arrastrado de week1)
        week2.topics_task_ids.append(task_old.id)
        self.manager.save_week(week2)

        # Rollover de week2 a week3 con prev_prev_week=week1
        self.manager.rollover_week_to_new_week(
            prev_week=week2,
            new_week=week3,
            prev_prev_week=week1
        )

        # task_new debe haberse arrastrado a week3 topics
        self.assertIn(task_new.id, week3.topics_task_ids)
        # task_old tiene 2 semanas de antigüedad -> se desagenda (no entra a week3 topics)
    def test_add_weekend_intervention_day(self):
        """Valida que add_day_to_week añada un día de guardia/intervención y BitacoraRenderer lo formatee."""
        week = self.manager.load_week(2026, 35)
        # Inicialmente 5 días
        self.assertEqual(len(week.days), 5)

        # Añadir Sábado 29
        new_day = self.manager.add_day_to_week(
            week=week,
            day_number=29,
            location_emoji="🛠️",
            location_note="Intervención"
        )
        self.assertEqual(new_day.day_number, 29)
        self.assertEqual(new_day.location_emoji, "🛠️")
        self.assertEqual(len(week.days), 6)
        self.assertEqual(week.days[-1].day_number, 29)

        # Crear tarea en el nuevo día
        task = self.manager.create_task(
            title="Soporte y monitoreo de switches en caliente",
            year=2026,
            week_num=35,
            day_number=29
        )

        md = BitacoraRenderer.render_week(week, self.manager)
        self.assertIn("## 🛠️29 (Intervención)", md)
        self.assertIn("- [ ] Soporte y monitoreo de switches en caliente", md)

    def test_always_render_pending_tasks_first(self):
        """Valida que BitacoraRenderer y EntityManager ordenen siempre las tareas pendientes primero."""
        week = self.manager.load_week(2026, 35)
        day = week.days[0]

        # Crear 3 tareas: 1 hecha, 1 cancelada, 1 pendiente
        t_done = self.manager.create_task(title="Tarea Terminada", status="done", day_number=day.day_number, year=2026, week_num=35)
        t_canc = self.manager.create_task(title="Tarea Cancelada", status="cancelled", day_number=day.day_number, year=2026, week_num=35)
        t_pend = self.manager.create_task(title="Tarea Pendiente", status="pending", day_number=day.day_number, year=2026, week_num=35)

        # Forzar un orden desordenado en day.task_ids: [done, canc, pend]
        day.task_ids = [t_done.id, t_canc.id, t_pend.id]

        # 1. Probar sort_day_tasks_pending_first
        self.manager.sort_day_tasks_pending_first(day)
        self.assertEqual(day.task_ids[0], t_pend.id)
        self.assertEqual(day.task_ids[1], t_done.id)
        self.assertEqual(day.task_ids[2], t_canc.id)

        # 2. Probar render_week garantiza pendientes primero incluso si day.task_ids estuviera desordenado
        day.task_ids = [t_done.id, t_canc.id, t_pend.id]
        md = BitacoraRenderer.render_week(week, self.manager)

        # Extraer líneas de tareas del primer día
        lines = md.splitlines()
        day_header = f"## {day.location_emoji}{day.day_number}"
        day_idx = lines.index(day_header)
        next_section_idx = len(lines)
        for i in range(day_idx + 1, len(lines)):
            if lines[i].startswith("## "):
                next_section_idx = i
                break

        day_lines = [l.strip() for l in lines[day_idx + 1:next_section_idx] if l.strip().startswith("- [")]
        # La tarea pendiente debe ser la primera
        self.assertIn("Tarea Pendiente", day_lines[0])
        self.assertTrue(day_lines[0].startswith("- [ ]"))


if __name__ == "__main__":
    unittest.main()

