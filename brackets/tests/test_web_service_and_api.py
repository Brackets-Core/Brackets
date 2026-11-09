#!/usr/bin/env python3
"""
Tests unitarios para la capa Web y API REST de Brackets.
Cubre BracketsWebService, la API HTTP y la integración de flags CLI (--web).
"""

import os
import shutil
import tempfile
import unittest
import threading
import json
import urllib.request
import urllib.parse
from http.server import ThreadingHTTPServer

from brackets.core.cli_parser import build_cli_parser
from brackets.core.cli_actions import has_action_flags
from brackets.web.service import BracketsWebService
from brackets.web.server import BracketsApiHandler


class TestWebServiceAndApi(unittest.TestCase):
    """Pruebas de la capa de servicio Web y de los endpoints REST."""

    def setUp(self):
        """Crear un workspace temporal con un vault mock."""
        self.temp_dir = tempfile.mkdtemp(prefix="brackets_web_test_")
        self.vault_dir = os.path.join(self.temp_dir, "MyTestVault")
        data_dir = os.path.join(self.vault_dir, "data")
        tables_dir = os.path.join(data_dir, "tables")
        weeks_dir = os.path.join(data_dir, "weeks")
        os.makedirs(tables_dir, exist_ok=True)
        os.makedirs(weeks_dir, exist_ok=True)

        # config.yaml
        with open(os.path.join(data_dir, "config.yaml"), "w", encoding="utf-8") as f:
            f.write("vault_type: work\ndays_per_week: 5\nuser_name: Tester\n")

        # task_types.yaml
        with open(os.path.join(data_dir, "task_types.yaml"), "w", encoding="utf-8") as f:
            f.write(
                "task_types:\n"
                "  - key: meeting\n    label: Reunión\n    premoji: '🫱🏼‍🫲🏽'\n    text_prefixes: ['reunión:']\n"
                "  - key: bug\n    label: Bug\n    premoji: '🐛'\n    text_prefixes: ['bug:']\n"
            )

        # work_calendar.yaml
        with open(os.path.join(data_dir, "work_calendar.yaml"), "w", encoding="utf-8") as f:
            f.write("default_pattern:\n  monday: 🏠\n  tuesday: 🚗\n  wednesday: 🚗\n  thursday: 🏠\n  friday: 🏠\n")

        # tasks.yaml vacío
        with open(os.path.join(tables_dir, "tasks.yaml"), "w", encoding="utf-8") as f:
            f.write("tasks: []\n")

        self.service = BracketsWebService(workspace_root=self.temp_dir)

    def tearDown(self):
        """Limpiar directorio temporal."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cli_parser_and_flags(self):
        """Verifica que el parser acepte --web, --port y --no-browser y active action_flags."""
        parser = build_cli_parser()
        args = parser.parse_args(["--web", "--port", "9090", "--no-browser"])
        self.assertTrue(args.web)
        self.assertEqual(args.port, 9090)
        self.assertTrue(args.no_browser)
        self.assertTrue(has_action_flags(args))

    def test_list_vaults(self):
        """Verifica la detección del vault y sus metadatos."""
        vaults = self.service.list_vaults()
        self.assertEqual(len(vaults), 1)
        self.assertEqual(vaults[0]["name"], "MyTestVault")
        self.assertEqual(vaults[0]["vault_type"], "work")
        self.assertEqual(vaults[0]["days_per_week"], 5)

        resolved = self.service.resolve_vault_path("MyTestVault")
        self.assertEqual(os.path.abspath(resolved), os.path.abspath(self.vault_dir))

    def test_hub_data_initialization(self):
        """Verifica que get_hub_data cree la estructura de la semana si no existía."""
        hub = self.service.get_hub_data(self.vault_dir, year=2026, week_number=40)
        self.assertIn("week", hub)
        self.assertEqual(hub["week"]["year"], 2026)
        self.assertEqual(hub["week"]["week_number"], 40)
        self.assertEqual(len(hub["week"]["days"]), 5)
        self.assertIn("task_types", hub)
        self.assertTrue(any(t["key"] == "meeting" for t in hub["task_types"]))

    def test_create_and_toggle_task(self):
        """Verifica creación de tarea completada y pendiente con descripción y cambio de estado."""
        # 1. Crear tarea completada con descripción y tag en la semana
        res = self.service.create_task(
            vault_identifier=self.vault_dir,
            title="Revisar pull request de seguridad #[Security]",
            target="week",
            is_done=True,
            description="Detalles de la revisión:\n- Token JWT expiraba\n- Sanitización de inputs",
            year=2026,
            week_number=40,
        )
        self.assertTrue(res["success"])
        task_data = res["task"]
        task_id = task_data["id"]
        self.assertEqual(task_data["status"], "done")
        self.assertEqual(task_data["project_id"], "Security")
        self.assertEqual(task_data["title"], "Revisar pull request de seguridad")
        self.assertIn("Token JWT", task_data.get("description", ""))

        # Verificar en Hub
        hub = self.service.get_hub_data(self.vault_dir, year=2026, week_number=40)
        week_tasks = hub["week"]["week_tasks"]
        found = next((t for t in week_tasks if t["id"] == task_id), None)
        self.assertIsNotNone(found)
        self.assertEqual(found["status"], "done")
        self.assertEqual(found["description"], "Detalles de la revisión:\n- Token JWT expiraba\n- Sanitización de inputs")

        # 2. Toggle a pendiente
        res_toggle = self.service.toggle_task(self.vault_dir, task_id, year=2026, week_number=40)
        self.assertTrue(res_toggle["success"])
        self.assertEqual(res_toggle["new_status"], "pending")

        # 3. Toggle de vuelta a completada
        res_toggle2 = self.service.toggle_task(self.vault_dir, task_id, year=2026, week_number=40)
        self.assertTrue(res_toggle2["success"])
        self.assertEqual(res_toggle2["new_status"], "done")

    def test_toggle_week_task_auto_moves_to_today(self):
        """Verifica que una tarea semanal al resolverse se traslada automáticamente a las tareas del día actual."""
        hub = self.service.get_hub_data(self.vault_dir, year=2026, week_number=40)
        res_create = self.service.create_task(
            self.vault_dir,
            title="Tarea de backlog semanal",
            target="week",
            year=2026,
            week_number=40
        )
        task_id = res_create["task"]["id"]

        hub_after = self.service.get_hub_data(self.vault_dir, year=2026, week_number=40)
        self.assertTrue(any(t["id"] == task_id for t in hub_after["week_tasks"]))
        self.assertFalse(any(t["id"] == task_id for t in hub_after["today_tasks"]))

        res_toggle = self.service.toggle_task(self.vault_dir, task_id, year=2026, week_number=40)
        self.assertTrue(res_toggle["success"])
        self.assertEqual(res_toggle["new_status"], "done")

        hub_final = self.service.get_hub_data(self.vault_dir, year=2026, week_number=40)
        self.assertFalse(any(t["id"] == task_id for t in hub_final["week_tasks"]))
        self.assertTrue(any(t["id"] == task_id for t in hub_final["today_tasks"]))

    def test_schedule_week_task_to_today_button(self):
        """Verifica el traslado manual de una tarea de la semana al día actual con target='today'."""
        res_create = self.service.create_task(
            self.vault_dir,
            title="Tarea para agendar hoy",
            target="week",
            year=2026,
            week_number=40
        )
        task_id = res_create["task"]["id"]

        res_update = self.service.update_task(
            self.vault_dir,
            task_id=task_id,
            target="today",
            year=2026,
            week_number=40
        )
        self.assertTrue(res_update["success"])

        hub = self.service.get_hub_data(self.vault_dir, year=2026, week_number=40)
        self.assertFalse(any(t["id"] == task_id for t in hub["week_tasks"]))
        self.assertTrue(any(t["id"] == task_id for t in hub["today_tasks"]))

    def test_create_task_in_specific_day(self):
        """Verifica creación de tarea asignada a un día específico."""
        hub = self.service.get_hub_data(self.vault_dir, year=2026, week_number=40)
        first_day_number = hub["week"]["days"][0]["day_number"]

        res = self.service.create_task(
            vault_identifier=self.vault_dir,
            title="Reunión: Daily standup con equipo",
            day=first_day_number,
            is_done=False,
            description="",
            year=2026,
            week_number=40,
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["task"]["task_type"], "meeting")
        self.assertEqual(res["task"]["status"], "pending")

        hub_updated = self.service.get_hub_data(self.vault_dir, year=2026, week_number=40)
        day_tasks = hub_updated["week"]["days"][0]["tasks"]
        self.assertEqual(len(day_tasks), 1)
        self.assertEqual(day_tasks[0]["id"], res["task"]["id"])
        self.assertEqual(day_tasks[0]["premoji"], "🫱🏼‍🫲🏽")

    def test_set_day_location(self):
        """Verifica la actualización de ubicación (emoji) de un día."""
        hub = self.service.get_hub_data(self.vault_dir, year=2026, week_number=40)
        target_day = hub["week"]["days"][1]["day_number"]

        res = self.service.set_day_location(
            vault_identifier=self.vault_dir,
            day=target_day,
            location_emoji="🏖️",
            location_note="Día libre",
            year=2026,
            week_number=40,
        )
        self.assertTrue(res["success"])

        hub_after = self.service.get_hub_data(self.vault_dir, year=2026, week_number=40)
        day_obj = next(d for d in hub_after["week"]["days"] if d["day_number"] == target_day)
        self.assertEqual(day_obj["location_emoji"], "🏖️")
        self.assertEqual(day_obj["location_note"], "Día libre")

    def test_create_note_and_reflection(self):
        """Verifica la creación de notas con proyecto y viñetas."""
        res = self.service.create_note(
            vault_identifier=self.vault_dir,
            title="Decisión de diseño #[Architecture]",
            content=["Punto 1: Usar PWA nativa", "Punto 2: Reconciliación con Markdown"],
            year=2026,
            week_number=40
        )
        self.assertTrue(res["success"])
        note = res["note"]
        self.assertEqual(note["title"], "Decisión de diseño")
        self.assertEqual(note["project_id"], "Architecture")
        self.assertEqual(len(note["content"]), 2)

        # Verificar reflejo en hub_data
        hub = self.service.get_hub_data(self.vault_dir, year=2026, week_number=40)
        self.assertEqual(len(hub["notes"]), 1)
        self.assertEqual(hub["notes"][0]["title"], "Decisión de diseño")

    def test_create_definition_jira_normalization(self):
        """Verifica la creación de definiciones y normalización de tickets Jira."""
        res = self.service.create_definition(
            vault_identifier=self.vault_dir,
            code_or_id="SYSC-73125",
            year=2026,
            week_number=40
        )
        self.assertTrue(res["success"])
        defi = res["definition"]
        self.assertEqual(defi["id"], "[🎫SYSC-73125]")
        self.assertTrue("SYSC-73125" in defi["url"])

        # Auto-extracción desde URL con código vacío
        res_url = self.service.create_definition(
            vault_identifier=self.vault_dir,
            code_or_id="",
            url="https://mangospain.atlassian.net/browse/ATLM-14036",
            year=2026,
            week_number=40
        )
        self.assertTrue(res_url["success"])
        defi_url = res_url["definition"]
        self.assertEqual(defi_url["id"], "[🎫ATLM-14036]")
        self.assertEqual(defi_url["url"], "https://mangospain.atlassian.net/browse/ATLM-14036")

        # Hub data incluye las definiciones
        hub = self.service.get_hub_data(self.vault_dir, year=2026, week_number=40)
        self.assertTrue(any(d["id"] == "[🎫SYSC-73125]" for d in hub.get("definitions", [])))
        self.assertTrue(any(d["id"] == "[🎫ATLM-14036]" for d in hub.get("definitions", [])))

    def test_create_topic_and_reflection(self):
        """Verifica la creación de topics y reflejo en el Hub."""
        res = self.service.create_topic(
            vault_identifier=self.vault_dir,
            title="Refactorización del Motor #[Core]",
            year=2026,
            week_number=40
        )
        self.assertTrue(res["success"])
        topic = res["topic"]
        self.assertEqual(topic["title"], "Refactorización del Motor")
        self.assertEqual(topic["project_id"], "Core")

        hub = self.service.get_hub_data(self.vault_dir, year=2026, week_number=40)
        self.assertTrue(any(t["title"] == "Refactorización del Motor" for t in hub.get("topics", [])))



    def test_update_and_delete_task(self):
        """Verifica edición completa y eliminación de una tarea en el servicio."""
        # Crear tarea en semana
        created = self.service.create_task(
            vault_identifier=self.vault_dir,
            title="Tarea Original #[Old]",
            target="week",
            year=2026,
            week_number=40
        )
        t_id = created["task"]["id"]

        # Modificar título, proyecto, estado y moverla al primer día
        hub = self.service.get_hub_data(self.vault_dir, year=2026, week_number=40)
        target_day = hub["week"]["days"][0]["day_number"]
        updated = self.service.update_task(
            vault_identifier=self.vault_dir,
            task_id=t_id,
            title="Tarea Editada #[NewProj]",
            description="Nueva descripción",
            status="done",
            target=f"day:{target_day}",
            year=2026,
            week_number=40
        )
        self.assertTrue(updated["success"])
        self.assertEqual(updated["task"]["title"], "Tarea Editada")
        self.assertEqual(updated["task"]["project_id"], "NewProj")
        self.assertEqual(updated["task"]["status"], "done")
        self.assertEqual(updated["task"]["day_number"], target_day)

        # Verificar eliminación
        deleted = self.service.delete_task(self.vault_dir, t_id, year=2026, week_number=40)
        self.assertTrue(deleted["success"])
        hub_after = self.service.get_hub_data(self.vault_dir, year=2026, week_number=40)
        self.assertFalse(any(t["id"] == t_id for d in hub_after["week"]["days"] for t in d["tasks"]))

    def test_update_and_delete_topic_and_note(self):
        """Verifica edición y borrado de topics y notas."""
        top = self.service.create_topic(self.vault_dir, "Topic Original #[A]", year=2026, week_number=40)
        top_id = top["topic"]["id"]
        top_up = self.service.update_topic(self.vault_dir, top_id, "Topic Nuevo #[B]", year=2026, week_number=40)
        self.assertEqual(top_up["topic"]["title"], "Topic Nuevo")
        self.assertEqual(top_up["topic"]["project_id"], "B")

        self.service.delete_topic(self.vault_dir, top_id, year=2026, week_number=40)
        hub = self.service.get_hub_data(self.vault_dir, year=2026, week_number=40)
        self.assertFalse(any(t["id"] == top_id for t in hub.get("topics", [])))

        # Nota
        note = self.service.create_note(self.vault_dir, "Nota Orig", content=["L1"], year=2026, week_number=40)
        note_id = note["note"]["id"]
        note_up = self.service.update_note(self.vault_dir, note_id, "Nota Editada #[Docs]", content=["P1", "P2"], year=2026, week_number=40)
        self.assertEqual(note_up["note"]["title"], "Nota Editada")
        self.assertEqual(note_up["note"]["project_id"], "Docs")
        self.assertEqual(len(note_up["note"]["content"]), 2)

        self.service.delete_note(self.vault_dir, note_id, year=2026, week_number=40)
        hub2 = self.service.get_hub_data(self.vault_dir, year=2026, week_number=40)
        self.assertFalse(any(n["id"] == note_id for n in hub2.get("notes", [])))

    def test_update_work_pattern_and_apply(self):
        """Verifica la actualización del patrón de trabajo semanal y su aplicación."""
        res = self.service.update_work_pattern(
            vault_identifier=self.vault_dir,
            defaults={"monday": "office", "tuesday": "home", "wednesday": "home", "thursday": "office", "friday": "home"}
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["work_pattern"]["defaults"]["tuesday"], "home")

        # Reaplicar a la semana
        app_res = self.service.apply_calendar(vault_identifier=self.vault_dir, year=2026, week_number=40)
        self.assertTrue(app_res["success"])

class TestHttpServerIntegration(unittest.TestCase):
    """Pruebas de integración HTTP sobre un servidor local efímero."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="brackets_http_test_")
        cls.vault_dir = os.path.join(cls.temp_dir, "HttpVault")
        data_dir = os.path.join(cls.vault_dir, "data")
        os.makedirs(os.path.join(data_dir, "tables"), exist_ok=True)
        os.makedirs(os.path.join(data_dir, "weeks"), exist_ok=True)

        with open(os.path.join(data_dir, "config.yaml"), "w", encoding="utf-8") as f:
            f.write("vault_type: work\ndays_per_week: 5\n")
        with open(os.path.join(data_dir, "tables", "tasks.yaml"), "w", encoding="utf-8") as f:
            f.write("tasks: []\n")

        cls.service = BracketsWebService(workspace_root=cls.temp_dir)
        BracketsApiHandler.service = cls.service

        # Bind to port 0 for an ephemeral OS-assigned port
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), BracketsApiHandler)
        cls.port = cls.httpd.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_static_files(self):
        """Verifica que index.html, manifest.webmanifest, style.css y app.js se sirvan correctamente."""
        for path in ["/", "/manifest.webmanifest", "/style.css", "/app.js"]:
            url = f"{self.base_url}{path}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                content = resp.read()
                self.assertGreater(len(content), 0)
                decoded = content.decode("utf-8")
                if path == "/":
                    self.assertIn("collapsible-section", decoded)
                    self.assertIn("today-tasks", decoded)
                    self.assertIn("week-tasks", decoded)
                    self.assertIn("week-notes", decoded)
                    self.assertIn("todayCountBadge", decoded)
                    self.assertIn("weekCountBadge", decoded)
                elif path == "/style.css":
                    self.assertIn(".collapsible-section", decoded)
                    self.assertIn(".section-header-btn", decoded)
                    self.assertIn(".task-count-badge", decoded)
                elif path == "/app.js":
                    self.assertIn("setupCollapsibleSections", decoded)
                    self.assertIn("updateTaskCountBadge", decoded)

    def test_api_vaults(self):
        """GET /api/vaults devuelve lista con HttpVault."""
        url = f"{self.base_url}/api/vaults"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("vaults", data)
            self.assertEqual(len(data["vaults"]), 1)
            self.assertEqual(data["vaults"][0]["name"], "HttpVault")

    def test_api_hub_and_task_lifecycle(self):
        """Ciclo completo: GET /api/hub -> POST /api/tasks -> POST /api/tasks/<id>/toggle."""
        # 1. GET /api/hub
        hub_url = f"{self.base_url}/api/hub?vault=HttpVault&year=2026&week=40"
        with urllib.request.urlopen(hub_url) as resp:
            self.assertEqual(resp.status, 200)
            hub_data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(hub_data["vault_name"], "HttpVault")

        # 2. POST /api/tasks (Crear tarea completada con descripción)
        create_url = f"{self.base_url}/api/tasks"
        body = json.dumps({
            "vault": "HttpVault",
            "title": "Configurar pipeline de testing #[DevOps]",
            "day": None,
            "is_done": True,
            "description": "Automatización con GitHub Actions",
            "year": 2026,
            "week": 40
        }).encode("utf-8")
        req_post = urllib.request.Request(create_url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req_post) as resp:
            self.assertEqual(resp.status, 201)
            created = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(created["success"])
            task_id = created["task"]["id"]
            self.assertEqual(created["task"]["status"], "done")

        # 3. POST /api/tasks/<id>/toggle
        toggle_url = f"{self.base_url}/api/tasks/{task_id}/toggle"
        toggle_body = json.dumps({
            "vault": "HttpVault",
            "year": 2026,
            "week": 40
        }).encode("utf-8")
        req_toggle = urllib.request.Request(toggle_url, data=toggle_body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req_toggle) as resp:
            self.assertEqual(resp.status, 200)
            toggled = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(toggled["success"])
            self.assertEqual(toggled["new_status"], "pending")

    def test_api_day_location(self):
        """POST /api/days/<day>/location actualiza el icono del día."""
        # Obtener primer día de la semana
        hub_url = f"{self.base_url}/api/hub?vault=HttpVault&year=2026&week=40"
        with urllib.request.urlopen(hub_url) as resp:
            hub_data = json.loads(resp.read().decode("utf-8"))
            day_num = hub_data["week"]["days"][0]["day_number"]

        loc_url = f"{self.base_url}/api/days/{day_num}/location"
        body = json.dumps({
            "vault": "HttpVault",
            "location_emoji": "🏠",
            "location_note": "Teletrabajo completo",
            "year": 2026,
            "week": 40
        }).encode("utf-8")
        req = urllib.request.Request(loc_url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            res = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(res["success"])
            self.assertEqual(res["location_emoji"], "🏠")

    def test_api_create_note_and_definition(self):
        """POST /api/notes y POST /api/definitions se reflejan en GET /api/hub."""
        # 1. Crear nota vía API
        note_url = f"{self.base_url}/api/notes"
        note_body = json.dumps({
            "vault": "HttpVault",
            "title": "Nota vía REST #[Testing]",
            "content": ["Elemento A", "Elemento B"],
            "year": 2026,
            "week": 40
        }).encode("utf-8")
        req_note = urllib.request.Request(note_url, data=note_body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req_note) as resp:
            self.assertEqual(resp.status, 201)
            created_note = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(created_note["success"])
            self.assertEqual(created_note["note"]["title"], "Nota vía REST")
            self.assertEqual(created_note["note"]["project_id"], "Testing")

        # 2. Crear definición vía API
        def_url = f"{self.base_url}/api/definitions"
        def_body = json.dumps({
            "vault": "HttpVault",
            "code": "DOCS-WIKI",
            "url": "https://wiki.example.com",
            "year": 2026,
            "week": 40
        }).encode("utf-8")
        req_def = urllib.request.Request(def_url, data=def_body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req_def) as resp:
            self.assertEqual(resp.status, 201)
            created_def = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(created_def["success"])
            self.assertEqual(created_def["definition"]["id"], "[DOCS-WIKI]")
            self.assertEqual(created_def["definition"]["url"], "https://wiki.example.com")

        # 3. Crear topic vía API
        topic_url = f"{self.base_url}/api/topics"
        topic_body = json.dumps({
            "vault": "HttpVault",
            "title": "Topic vía REST #[DevOps]",
            "year": 2026,
            "week": 40
        }).encode("utf-8")
        req_top = urllib.request.Request(topic_url, data=topic_body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req_top) as resp:
            self.assertEqual(resp.status, 201)
            created_top = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(created_top["success"])
            self.assertEqual(created_top["topic"]["title"], "Topic vía REST")
            self.assertEqual(created_top["topic"]["project_id"], "DevOps")

        # 4. GET /api/hub refleja notas, definiciones y topics
        hub_url = f"{self.base_url}/api/hub?vault=HttpVault&year=2026&week=40"
        with urllib.request.urlopen(hub_url) as resp:
            self.assertEqual(resp.status, 200)
            hub_data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(any(n["title"] == "Nota vía REST" for n in hub_data.get("notes", [])))
            self.assertTrue(any(d["id"] == "[DOCS-WIKI]" for d in hub_data.get("definitions", [])))
            self.assertTrue(any(t["title"] == "Topic vía REST" for t in hub_data.get("topics", [])))



    def test_api_patch_and_delete_endpoints(self):
        """Verifica endpoints PATCH y DELETE para tareas, topics, notas y definiciones."""
        # 1. Crear tarea y luego editarla vía PATCH
        post_url = f"{self.base_url}/api/tasks"
        body = json.dumps({"vault": "HttpVault", "title": "Tarea Inicial", "target": "week", "year": 2026, "week": 40}).encode("utf-8")
        req = urllib.request.Request(post_url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            task_id = json.loads(resp.read().decode("utf-8"))["task"]["id"]

        patch_url = f"{self.base_url}/api/tasks/{task_id}"
        patch_body = json.dumps({
            "vault": "HttpVault",
            "title": "Tarea Modificada #[Actualizado]",
            "description": "Detalles nuevos",
            "status": "done",
            "year": 2026,
            "week": 40
        }).encode("utf-8")
        req_patch = urllib.request.Request(patch_url, data=patch_body, headers={"Content-Type": "application/json"}, method="PATCH")
        with urllib.request.urlopen(req_patch) as resp:
            self.assertEqual(resp.status, 200)
            res_patch = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(res_patch["success"])
            self.assertEqual(res_patch["task"]["title"], "Tarea Modificada")
            self.assertEqual(res_patch["task"]["project_id"], "Actualizado")

        # Eliminar vía DELETE
        del_url = f"{self.base_url}/api/tasks/{task_id}"
        del_body = json.dumps({"vault": "HttpVault", "year": 2026, "week": 40}).encode("utf-8")
        req_del = urllib.request.Request(del_url, data=del_body, headers={"Content-Type": "application/json"}, method="DELETE")
        with urllib.request.urlopen(req_del) as resp:
            self.assertEqual(resp.status, 200)
            self.assertTrue(json.loads(resp.read().decode("utf-8"))["success"])

    def test_reorder_elements_service_and_api(self):
        """Verifica la reordenación de tareas, notas y topics vía servicio y API /api/reorder."""
        # 1. Crear dos tareas en el día 28
        t1 = self.service.create_task("HttpVault", "Tarea A", target="28", year=2026, week_number=40)["task"]
        t2 = self.service.create_task("HttpVault", "Tarea B", target="28", year=2026, week_number=40)["task"]

        # Reordenar mediante servicio: B antes que A
        reordered = self.service.reorder_elements(
            vault_identifier="HttpVault",
            reorder_type="today_tasks",
            ids=[t2["id"], t1["id"]],
            day_number=28,
            year=2026,
            week_number=40
        )
        self.assertTrue(reordered["success"])

        hub = self.service.get_hub_data("HttpVault", year=2026, week_number=40, day_number=28)
        task_ids = [t["id"] for t in hub["today_tasks"]]
        self.assertEqual(task_ids[:2], [t2["id"], t1["id"]])

        # 2. Reordenar tareas de la semana mediante HTTP POST /api/reorder
        wt1 = self.service.create_task("HttpVault", "Semanal 1", target="week", year=2026, week_number=40)["task"]
        wt2 = self.service.create_task("HttpVault", "Semanal 2", target="week", year=2026, week_number=40)["task"]

        reorder_url = f"{self.base_url}/api/reorder"
        body = json.dumps({
            "vault": "HttpVault",
            "type": "week_tasks",
            "ids": [wt2["id"], wt1["id"]],
            "year": 2026,
            "week": 40
        }).encode("utf-8")
        req = urllib.request.Request(reorder_url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data["success"])

        # Verificar en Hub
        hub_url = f"{self.base_url}/api/hub?vault=HttpVault&year=2026&week=40"
        with urllib.request.urlopen(hub_url) as resp:
            hub_data = json.loads(resp.read().decode("utf-8"))
            wt_ids = [t["id"] for t in hub_data["week_tasks"]]
            self.assertEqual(wt_ids, [wt2["id"], wt1["id"]])

    def test_top_menu_and_advanced_cli_endpoints(self):
        """Verifica el menú superior declarativo y los nuevos endpoints CLI (semanas, peso, día extra, recurrentes, proyectos, backlog, ideas, calendario y consolidación)."""
        # 1. GET /api/hub devuelve top_menu y available_weeks
        hub_url = f"{self.base_url}/api/hub?vault=HttpVault&year=2026&week=40"
        with urllib.request.urlopen(hub_url) as resp:
            hub_data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("top_menu", hub_data)
            self.assertGreaterEqual(len(hub_data["top_menu"]), 4)
            self.assertIn("available_weeks", hub_data)

        # 2. POST /api/weeks/weight y POST /api/weeks/extra-day
        weight_url = f"{self.base_url}/api/weeks/weight"
        weight_body = json.dumps({"vault": "HttpVault", "weight": 80.5, "year": 2026, "week": 40}).encode("utf-8")
        req_w = urllib.request.Request(weight_url, data=weight_body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req_w) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(json.loads(resp.read().decode("utf-8"))["weight"], 80.5)

        extra_url = f"{self.base_url}/api/weeks/extra-day"
        extra_body = json.dumps({
            "vault": "HttpVault",
            "day_number": 3,
            "emoji": "🛠️",
            "note": "Guardia Sábado",
            "year": 2026,
            "week": 40
        }).encode("utf-8")
        req_ex = urllib.request.Request(extra_url, data=extra_body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req_ex) as resp:
            self.assertEqual(resp.status, 201)
            self.assertEqual(json.loads(resp.read().decode("utf-8"))["day"]["day_number"], 3)

        # 3. POST /api/recurring & GET /api/recurring
        rec_url = f"{self.base_url}/api/recurring"
        rec_body = json.dumps({
            "vault": "HttpVault",
            "title": "Reunión: Weekly Sync #[CORE]",
            "recurrence_type": "weekly_days",
            "days_of_week": [0, 2],
            "year": 2026,
            "week": 40
        }).encode("utf-8")
        req_rec = urllib.request.Request(rec_url, data=rec_body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req_rec) as resp:
            self.assertEqual(resp.status, 201)
            rec_data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(rec_data["success"])

        with urllib.request.urlopen(f"{self.base_url}/api/recurring?vault=HttpVault") as resp:
            recs = json.loads(resp.read().decode("utf-8"))["recurring_tasks"]
            self.assertGreaterEqual(len(recs), 1)

        # 4. POST /api/projects, POST /api/backlog, POST /api/ideas
        proj_url = f"{self.base_url}/api/projects"
        proj_body = json.dumps({"vault": "HttpVault", "id": "GRAFANA", "name": "Grafana Dashboards"}).encode("utf-8")
        with urllib.request.urlopen(urllib.request.Request(proj_url, data=proj_body, headers={"Content-Type": "application/json"})) as resp:
            self.assertEqual(resp.status, 201)

        bl_url = f"{self.base_url}/api/backlog"
        bl_body = json.dumps({"vault": "HttpVault", "title": "Optimizar queries #[GRAFANA]"}).encode("utf-8")
        with urllib.request.urlopen(urllib.request.Request(bl_url, data=bl_body, headers={"Content-Type": "application/json"})) as resp:
            self.assertEqual(resp.status, 201)
            bl_task_id = json.loads(resp.read().decode("utf-8"))["task"]["id"]

        with urllib.request.urlopen(f"{self.base_url}/api/backlog?vault=HttpVault") as resp:
            bl_list = json.loads(resp.read().decode("utf-8"))["backlog_tasks"]
            self.assertTrue(any(t["id"] == bl_task_id for t in bl_list))

        idea_url = f"{self.base_url}/api/ideas"
        idea_body = json.dumps({"vault": "HttpVault", "title": "Exportador Prometheus #[GRAFANA]"}).encode("utf-8")
        with urllib.request.urlopen(urllib.request.Request(idea_url, data=idea_body, headers={"Content-Type": "application/json"})) as resp:
            self.assertEqual(resp.status, 201)
            idea_id = json.loads(resp.read().decode("utf-8"))["idea"]["id"]

        patch_idea_url = f"{self.base_url}/api/ideas/{idea_id}"
        patch_idea_body = json.dumps({"vault": "HttpVault", "status": "accepted"}).encode("utf-8")
        req_pi = urllib.request.Request(patch_idea_url, data=patch_idea_body, headers={"Content-Type": "application/json"}, method="PATCH")
        with urllib.request.urlopen(req_pi) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(json.loads(resp.read().decode("utf-8"))["idea"]["status"], "accepted")

        # 5. Consolidación mensual y anual
        cons_m_url = f"{self.base_url}/api/consolidate/month"
        cons_m_body = json.dumps({"vault": "HttpVault", "year": 2026, "month": 9, "delete_source": False}).encode("utf-8")
        with urllib.request.urlopen(urllib.request.Request(cons_m_url, data=cons_m_body, headers={"Content-Type": "application/json"})) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(json.loads(resp.read().decode("utf-8"))["file"], "[2026][09].md")

        cons_y_url = f"{self.base_url}/api/consolidate/year"
        cons_y_body = json.dumps({"vault": "HttpVault", "year": 2026, "delete_source": False}).encode("utf-8")
        with urllib.request.urlopen(urllib.request.Request(cons_y_url, data=cons_y_body, headers={"Content-Type": "application/json"})) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(json.loads(resp.read().decode("utf-8"))["file"], "[2026].md")


if __name__ == "__main__":
    unittest.main()
