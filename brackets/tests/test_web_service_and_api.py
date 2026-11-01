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


if __name__ == "__main__":
    unittest.main()
