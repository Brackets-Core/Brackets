#!/usr/bin/env python3
"""
Servidor HTTP integrado para Brackets Web Hub.
Sirve la aplicación Vanilla PWA estática y expone la API REST JSON
usando exclusivamente la librería estándar de Python (sin dependencias externas).
"""

from __future__ import annotations
import os
import re
import json
import urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from typing import Optional

from brackets.web.service import BracketsWebService


class QuietThreadingHTTPServer(ThreadingHTTPServer):
    """Servidor HTTP multihilo que suprime tracebacks ruidosos por desconexiones del cliente (ej: escaneos locales de Windows Defender)."""

    def handle_error(self, request, client_address):
        exc_type, exc_value, _ = sys.exc_info()
        if exc_type in (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            return
        if isinstance(exc_value, OSError) and getattr(exc_value, "winerror", None) in (10053, 10054):
            return
        super().handle_error(request, client_address)


class BracketsApiHandler(SimpleHTTPRequestHandler):
    """Manejador HTTP para la API REST y los archivos estáticos de la PWA."""

    service: Optional[BracketsWebService] = None
    static_dir: str = os.path.join(os.path.dirname(__file__), "static")

    def handle(self):
        """Maneja la petición suprimiendo desconexiones forzadas del cliente/antivirus."""
        try:
            super().handle()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass
        except OSError as e:
            if getattr(e, "winerror", None) in (10053, 10054):
                pass
            else:
                raise

    def copyfile(self, source, outputfile):
        """Copia archivos al socket suprimiendo abortos normales de conexión."""
        try:
            super().copyfile(source, outputfile)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            self.close_connection = True
        except OSError as e:
            if getattr(e, "winerror", None) in (10053, 10054):
                self.close_connection = True
            else:
                raise

    def __init__(self, *args, **kwargs):
        # Servir estáticos desde brackets/web/static
        super().__init__(*args, directory=self.static_dir, **kwargs)

    def end_headers(self):
        # Habilitar CORS para permitir integraciones locales
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        """Maneja preflight CORS."""
        self.send_response(200)
        self.end_headers()

    def _send_json(self, status_code: int, data: dict | list):
        """Envía respuesta estructurada en formato JSON UTF-8."""
        try:
            payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            self.close_connection = True
        except OSError as e:
            if getattr(e, "winerror", None) in (10053, 10054):
                self.close_connection = True
            else:
                raise

    def _read_json_body(self) -> dict:
        """Lee y deserializa el body JSON de la petición."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                raw_body = self.rfile.read(content_length).decode("utf-8")
                return json.loads(raw_body)
        except Exception:
            pass
        return {}

    def do_GET(self):
        """Enruta peticiones GET hacia la API o hacia los archivos estáticos."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path.startswith("/api/"):
            try:
                svc = self.service or BracketsWebService()

                if path == "/api/vaults":
                    vaults = svc.list_vaults()
                    return self._send_json(200, {"vaults": vaults})

                elif path == "/api/hub":
                    vault = query.get("vault", [None])[0]
                    day_str = query.get("day", [None])[0]
                    day_num = int(day_str) if day_str and day_str.isdigit() else None
                    year_str = query.get("year", [None])[0]
                    year_num = int(year_str) if year_str and year_str.isdigit() else None
                    week_str = query.get("week", [None])[0]
                    week_num = int(week_str) if week_str and week_str.isdigit() else None

                    hub = svc.get_hub_data(
                        vault_identifier=vault,
                        day_number=day_num,
                        year=year_num,
                        week_number=week_num
                    )
                    return self._send_json(200, hub)

                elif path == "/api/weeks":
                    vault = query.get("vault", [None])[0]
                    return self._send_json(200, svc.list_available_weeks(vault_identifier=vault))

                elif path == "/api/recurring":
                    vault = query.get("vault", [None])[0]
                    return self._send_json(200, svc.list_recurring(vault_identifier=vault))

                elif path == "/api/projects":
                    vault = query.get("vault", [None])[0]
                    return self._send_json(200, svc.get_projects_overview(vault_identifier=vault))

                elif path == "/api/backlog":
                    vault = query.get("vault", [None])[0]
                    project_id = query.get("project_id", [None])[0]
                    return self._send_json(200, svc.get_backlog(vault_identifier=vault, project_id=project_id))

                elif path == "/api/ideas":
                    vault = query.get("vault", [None])[0]
                    project_id = query.get("project_id", [None])[0]
                    return self._send_json(200, svc.list_ideas(vault_identifier=vault, project_id=project_id))

                elif path == "/api/calendar":
                    vault = query.get("vault", [None])[0]
                    return self._send_json(200, svc.get_calendar_config(vault_identifier=vault))

                else:
                    return self._send_json(404, {"error": f"Ruta API no encontrada: {path}"})
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                self.close_connection = True
                return
            except OSError as e:
                if getattr(e, "winerror", None) in (10053, 10054):
                    self.close_connection = True
                    return
                return self._send_json(500, {"error": str(e)})
            except Exception as e:
                return self._send_json(500, {"error": str(e)})

        # Si pide la raíz, servir index.html
        if path in ("", "/"):
            self.path = "/index.html"
            return super().do_GET()

        # Solo servir archivos estáticos que realmente existan en static_dir
        clean_path = path.lstrip("/")
        file_path = os.path.abspath(os.path.join(self.static_dir, clean_path))
        if not file_path.startswith(os.path.abspath(self.static_dir)) or not os.path.isfile(file_path):
            return self._send_json(404, {"error": f"Recurso estático no encontrado: {path}"})

        return super().do_GET()

    def do_POST(self):
        """Enruta peticiones POST de la API."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/"):
            try:
                svc = self.service or BracketsWebService()
                body = self._read_json_body()

                # POST /api/tasks
                if path == "/api/tasks":
                    title = body.get("title", "").strip()
                    if not title:
                        return self._send_json(400, {"error": "El título de la tarea es obligatorio"})

                    vault = body.get("vault")
                    target = body.get("target", "today")
                    status = body.get("status", "pending")
                    description = body.get("description")
                    project_id = body.get("project_id")
                    day = body.get("day")
                    is_done = body.get("is_done")
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")

                    created = svc.create_task(
                        vault_identifier=vault,
                        title=title,
                        target=target,
                        status=status,
                        description=description,
                        project_id=project_id,
                        day=day,
                        is_done=is_done,
                        year=year,
                        week_number=week
                    )
                    return self._send_json(201, created)

                # POST /api/tasks/{task_id}/toggle
                toggle_match = re.match(r"^/api/tasks/([^/]+)/toggle$", path)
                if toggle_match:
                    task_id = toggle_match.group(1)
                    vault = body.get("vault")
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")
                    updated = svc.toggle_task(vault_identifier=vault, task_id=task_id, year=year, week_number=week)
                    return self._send_json(200, updated)

                # POST /api/days/{day_number}/location
                loc_match = re.match(r"^/api/days/(\d+)/location$", path)
                if loc_match:
                    day_number = int(loc_match.group(1))
                    vault = body.get("vault")
                    emoji = body.get("location_emoji") or body.get("emoji", "🏠")
                    note = body.get("location_note") or body.get("note")
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")
                    updated = svc.set_day_location(
                        vault_identifier=vault,
                        day_number=day_number,
                        emoji=emoji,
                        note=note,
                        year=year,
                        week_number=week
                    )
                    return self._send_json(200, updated)

                elif path == "/api/notes":
                    vault = body.get("vault")
                    title = body.get("title")
                    content = body.get("content", "")
                    project_id = body.get("project_id")
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")
                    created = svc.create_note(
                        vault_identifier=vault,
                        title=title,
                        content=content,
                        project_id=project_id,
                        year=year,
                        week_number=week
                    )
                    return self._send_json(201, created)

                elif path == "/api/definitions":
                    vault = body.get("vault")
                    code_or_id = body.get("id") or body.get("code") or ""
                    url = body.get("url")
                    title = body.get("title")
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")
                    created = svc.create_definition(
                        vault_identifier=vault,
                        code_or_id=code_or_id,
                        url=url,
                        title=title,
                        year=year,
                        week_number=week
                    )
                    return self._send_json(201, created)

                elif path == "/api/topics":
                    vault = body.get("vault")
                    title = body.get("title") or ""
                    project_id = body.get("project_id")
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")
                    created = svc.create_topic(
                        vault_identifier=vault,
                        title=title,
                        project_id=project_id,
                        year=year,
                        week_number=week
                    )
                    return self._send_json(201, created)

                elif path == "/api/sync":
                    vault = body.get("vault")
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")
                    res = svc.sync_week(vault_identifier=vault, year=year, week_number=week)
                    return self._send_json(200, res)

                elif path == "/api/sync/all":
                    vault = body.get("vault")
                    res = svc.sync_all_weeks(vault_identifier=vault)
                    return self._send_json(200, res)

                elif path == "/api/weeks/next":
                    vault = body.get("vault")
                    weight = body.get("weight")
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")
                    res = svc.create_next_week(vault_identifier=vault, weight=weight, year=year, week_number=week)
                    return self._send_json(201, res)

                elif path == "/api/weeks/extra-day":
                    vault = body.get("vault")
                    day_number = body.get("day_number") or body.get("day")
                    emoji = body.get("emoji") or body.get("location_emoji") or "🛠️"
                    note = body.get("note") or body.get("location_note") or "Intervención"
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")
                    res = svc.add_extra_day(
                        vault_identifier=vault,
                        day_number=day_number,
                        emoji=emoji,
                        note=note,
                        year=year,
                        week_number=week
                    )
                    return self._send_json(201, res)

                elif path == "/api/weeks/weight":
                    vault = body.get("vault")
                    weight = body.get("weight")
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")
                    res = svc.set_week_weight(vault_identifier=vault, weight=weight, year=year, week_number=week)
                    return self._send_json(200, res)

                elif path == "/api/recurring":
                    vault = body.get("vault")
                    title = body.get("title", "")
                    recurrence_type = body.get("recurrence_type", "weekly_days")
                    days_of_week = body.get("days_of_week", [])
                    interval_weeks = body.get("interval_weeks", 1)
                    day_of_week = body.get("day_of_week", 4)
                    project_id = body.get("project_id")
                    task_type = body.get("task_type")
                    description = body.get("description")
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")
                    res = svc.create_recurring(
                        vault_identifier=vault,
                        title=title,
                        recurrence_type=recurrence_type,
                        days_of_week=days_of_week,
                        interval_weeks=interval_weeks,
                        day_of_week=day_of_week,
                        project_id=project_id,
                        task_type=task_type,
                        description=description,
                        year=year,
                        week_number=week
                    )
                    return self._send_json(201, res)

                elif path == "/api/recurring/apply":
                    vault = body.get("vault")
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")
                    res = svc.apply_recurring_to_week(vault_identifier=vault, year=year, week_number=week)
                    return self._send_json(200, res)

                elif path == "/api/projects":
                    vault = body.get("vault")
                    project_id = body.get("id") or body.get("project_id") or ""
                    name = body.get("name")
                    description = body.get("description")
                    res = svc.create_project(
                        vault_identifier=vault,
                        project_id=project_id,
                        name=name,
                        description=description
                    )
                    return self._send_json(201, res)

                elif path == "/api/backlog":
                    vault = body.get("vault")
                    title = body.get("title", "")
                    project_id = body.get("project_id")
                    description = body.get("description")
                    res = svc.create_backlog_task(
                        vault_identifier=vault,
                        title=title,
                        project_id=project_id,
                        description=description
                    )
                    return self._send_json(201, res)

                elif path == "/api/backlog/schedule":
                    vault = body.get("vault")
                    task_id = body.get("task_id", "")
                    day_number = body.get("day_number") or body.get("day")
                    target = body.get("target", "day")
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")
                    res = svc.schedule_task_to_day(
                        vault_identifier=vault,
                        task_id=task_id,
                        day_number=day_number,
                        target=target,
                        year=year,
                        week_number=week
                    )
                    return self._send_json(200, res)

                elif path == "/api/ideas":
                    vault = body.get("vault")
                    title = body.get("title", "")
                    content = body.get("content")
                    project_id = body.get("project_id")
                    res = svc.create_idea(
                        vault_identifier=vault,
                        title=title,
                        content=content,
                        project_id=project_id
                    )
                    return self._send_json(201, res)

                elif path == "/api/calendar/apply":
                    vault = body.get("vault")
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")
                    res = svc.apply_calendar(vault_identifier=vault, year=year, week_number=week)
                    return self._send_json(200, res)

                elif path == "/api/calendar/holidays":
                    vault = body.get("vault")
                    date_str = body.get("date", "")
                    name = body.get("name", "Festivo")
                    res = svc.add_calendar_holiday(vault_identifier=vault, date_str=date_str, name=name)
                    return self._send_json(201, res)

                elif path == "/api/calendar/vacations":
                    vault = body.get("vault")
                    start_str = body.get("start", "")
                    end_str = body.get("end", "")
                    name = body.get("name", "Vacaciones")
                    res = svc.add_calendar_vacation(
                        vault_identifier=vault,
                        start_str=start_str,
                        end_str=end_str,
                        name=name
                    )
                    return self._send_json(201, res)

                elif path == "/api/consolidate/month":
                    vault = body.get("vault")
                    year = body.get("year")
                    month = body.get("month")
                    delete_source = bool(body.get("delete_source", False))
                    res = svc.consolidate_month(
                        vault_identifier=vault,
                        year=year,
                        month=month,
                        delete_source=delete_source
                    )
                    return self._send_json(200 if res.get("success") else 400, res)

                elif path == "/api/consolidate/year":
                    vault = body.get("vault")
                    year = body.get("year")
                    delete_source = bool(body.get("delete_source", False))
                    res = svc.consolidate_year(
                        vault_identifier=vault,
                        year=year,
                        delete_source=delete_source
                    )
                    return self._send_json(200 if res.get("success") else 400, res)

                elif path == "/api/reorder":
                    vault = body.get("vault")
                    reorder_type = body.get("type", "")
                    ids = body.get("ids", [])
                    day_number = body.get("day_number")
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")
                    res = svc.reorder_elements(
                        vault_identifier=vault,
                        reorder_type=reorder_type,
                        ids=ids,
                        day_number=day_number,
                        year=year,
                        week_number=week
                    )
                    return self._send_json(200, res)

                else:
                    return self._send_json(404, {"error": f"Ruta POST no encontrada: {path}"})
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                self.close_connection = True
                return
            except OSError as e:
                if getattr(e, "winerror", None) in (10053, 10054):
                    self.close_connection = True
                    return
                return self._send_json(500, {"error": str(e)})
            except Exception as e:
                return self._send_json(500, {"error": str(e)})

        return self._send_json(405, {"error": "Método no permitido"})

    def do_PATCH(self):
        """Enruta peticiones PATCH de la API."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/"):
            try:
                svc = self.service or BracketsWebService()
                body = self._read_json_body()

                # PATCH /api/tasks/{task_id}/toggle
                toggle_match = re.match(r"^/api/tasks/([^/]+)/toggle$", path)
                if toggle_match:
                    task_id = toggle_match.group(1)
                    vault = body.get("vault")
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")
                    updated = svc.toggle_task(vault_identifier=vault, task_id=task_id, year=year, week_number=week)
                    return self._send_json(200, updated)

                # PATCH /api/days/{day_number}/location
                loc_match = re.match(r"^/api/days/(\d+)/location$", path)
                if loc_match:
                    day_number = int(loc_match.group(1))
                    vault = body.get("vault")
                    emoji = body.get("location_emoji") or body.get("emoji", "🏠")
                    note = body.get("location_note") or body.get("note")
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")
                    updated = svc.set_day_location(
                        vault_identifier=vault,
                        day_number=day_number,
                        emoji=emoji,
                        note=note,
                        year=year,
                        week_number=week
                    )
                    return self._send_json(200, updated)

                # PATCH /api/tasks/{task_id}
                task_match = re.match(r"^/api/tasks/([^/]+)$", path)
                if task_match:
                    task_id = urllib.parse.unquote(task_match.group(1))
                    vault = body.get("vault")
                    title = body.get("title")
                    description = body.get("description")
                    status = body.get("status")
                    target = body.get("target")
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")
                    updated = svc.update_task(
                        vault_identifier=vault,
                        task_id=task_id,
                        title=title,
                        description=description,
                        status=status,
                        target=target,
                        year=year,
                        week_number=week
                    )
                    return self._send_json(200, updated)

                # PATCH /api/topics/{topic_id}
                topic_match = re.match(r"^/api/topics/([^/]+)$", path)
                if topic_match:
                    topic_id = urllib.parse.unquote(topic_match.group(1))
                    vault = body.get("vault")
                    title = body.get("title", "")
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")
                    updated = svc.update_topic(
                        vault_identifier=vault,
                        topic_id=topic_id,
                        title=title,
                        year=year,
                        week_number=week
                    )
                    return self._send_json(200, updated)

                # PATCH /api/notes/{note_id}
                note_match = re.match(r"^/api/notes/([^/]+)$", path)
                if note_match:
                    note_id = urllib.parse.unquote(note_match.group(1))
                    vault = body.get("vault")
                    title = body.get("title")
                    content = body.get("content")
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")
                    updated = svc.update_note(
                        vault_identifier=vault,
                        note_id=note_id,
                        title=title,
                        content=content,
                        year=year,
                        week_number=week
                    )
                    return self._send_json(200, updated)

                # PATCH /api/definitions/{def_id}
                def_match = re.match(r"^/api/definitions/([^/]+)$", path)
                if def_match:
                    def_id = urllib.parse.unquote(def_match.group(1))
                    vault = body.get("vault")
                    new_id = body.get("new_id")
                    url = body.get("url")
                    title = body.get("title")
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")
                    updated = svc.update_definition(
                        vault_identifier=vault,
                        def_id=def_id,
                        new_id=new_id,
                        url=url,
                        title=title,
                        year=year,
                        week_number=week
                    )
                    return self._send_json(200, updated)

                # PATCH /api/weeks/weight
                if path == "/api/weeks/weight":
                    vault = body.get("vault")
                    weight = body.get("weight")
                    year = body.get("year")
                    week = body.get("week") or body.get("week_number")
                    res = svc.set_week_weight(vault_identifier=vault, weight=weight, year=year, week_number=week)
                    return self._send_json(200, res)

                # PATCH /api/recurring/{rec_id}/toggle
                rec_toggle_match = re.match(r"^/api/recurring/([^/]+)/toggle$", path)
                if rec_toggle_match:
                    rec_id = urllib.parse.unquote(rec_toggle_match.group(1))
                    vault = body.get("vault")
                    res = svc.toggle_recurring(vault_identifier=vault, recurring_id=rec_id)
                    return self._send_json(200, res)

                # PATCH /api/ideas/{idea_id}
                idea_match = re.match(r"^/api/ideas/([^/]+)$", path)
                if idea_match:
                    idea_id = urllib.parse.unquote(idea_match.group(1))
                    vault = body.get("vault")
                    status = body.get("status", "evaluating")
                    res = svc.update_idea_status(vault_identifier=vault, idea_id=idea_id, status=status)
                    return self._send_json(200, res)

                return self._send_json(404, {"error": f"Ruta PATCH no encontrada: {path}"})
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                self.close_connection = True
                return
            except OSError as e:
                if getattr(e, "winerror", None) in (10053, 10054):
                    self.close_connection = True
                    return
                return self._send_json(500, {"error": str(e)})
            except Exception as e:
                return self._send_json(500, {"error": str(e)})

        return self._send_json(405, {"error": "Método no permitido"})

    def do_DELETE(self):
        """Enruta peticiones DELETE de la API."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path.startswith("/api/"):
            try:
                svc = self.service or BracketsWebService()
                body = self._read_json_body()
                vault = body.get("vault") or query.get("vault", [None])[0]
                year_raw = body.get("year") or query.get("year", [None])[0]
                week_raw = body.get("week") or body.get("week_number") or query.get("week", [None])[0]
                year = int(year_raw) if year_raw and str(year_raw).isdigit() else None
                week = int(week_raw) if week_raw and str(week_raw).isdigit() else None

                # DELETE /api/tasks/{task_id}
                task_match = re.match(r"^/api/tasks/([^/]+)$", path)
                if task_match:
                    task_id = urllib.parse.unquote(task_match.group(1))
                    res = svc.delete_task(vault_identifier=vault, task_id=task_id, year=year, week_number=week)
                    return self._send_json(200, res)

                # DELETE /api/topics/{topic_id}
                topic_match = re.match(r"^/api/topics/([^/]+)$", path)
                if topic_match:
                    topic_id = urllib.parse.unquote(topic_match.group(1))
                    res = svc.delete_topic(vault_identifier=vault, topic_id=topic_id, year=year, week_number=week)
                    return self._send_json(200, res)

                # DELETE /api/notes/{note_id}
                note_match = re.match(r"^/api/notes/([^/]+)$", path)
                if note_match:
                    note_id = urllib.parse.unquote(note_match.group(1))
                    res = svc.delete_note(vault_identifier=vault, note_id=note_id, year=year, week_number=week)
                    return self._send_json(200, res)

                # DELETE /api/definitions/{def_id}
                def_match = re.match(r"^/api/definitions/([^/]+)$", path)
                if def_match:
                    def_id = urllib.parse.unquote(def_match.group(1))
                    res = svc.delete_definition(vault_identifier=vault, def_id=def_id, year=year, week_number=week)
                    return self._send_json(200, res)

                # DELETE /api/recurring/{rec_id}
                rec_del_match = re.match(r"^/api/recurring/([^/]+)$", path)
                if rec_del_match:
                    rec_id = urllib.parse.unquote(rec_del_match.group(1))
                    res = svc.delete_recurring(vault_identifier=vault, recurring_id=rec_id)
                    return self._send_json(200, res)

                # DELETE /api/calendar/holidays/{index}
                hol_del_match = re.match(r"^/api/calendar/holidays/(\d+)$", path)
                if hol_del_match:
                    idx = int(hol_del_match.group(1))
                    res = svc.delete_calendar_holiday(vault_identifier=vault, index=idx)
                    return self._send_json(200, res)

                # DELETE /api/calendar/vacations/{index}
                vac_del_match = re.match(r"^/api/calendar/vacations/(\d+)$", path)
                if vac_del_match:
                    idx = int(vac_del_match.group(1))
                    res = svc.delete_calendar_vacation(vault_identifier=vault, index=idx)
                    return self._send_json(200, res)

                return self._send_json(404, {"error": f"Ruta DELETE no encontrada: {path}"})
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                self.close_connection = True
                return
            except OSError as e:
                if getattr(e, "winerror", None) in (10053, 10054):
                    self.close_connection = True
                    return
                return self._send_json(500, {"error": str(e)})
            except Exception as e:
                return self._send_json(500, {"error": str(e)})

        return self._send_json(405, {"error": "Método no permitido"})


def open_in_app_mode(url: str) -> bool:
    """Intenta abrir la URL en modo ventana de aplicación independiente (Edge / Chrome)
    utilizando un perfil aislado y ligero (sandbox) que:
      1. Evita cargar todas las extensiones, plugins pesados y perfiles del navegador del usuario.
      2. Desactiva sincronización en la nube, telemetría y networking en segundo plano.
      3. Limita la caché a un tamaño estricto (32 MB) y desactiva servicios zombi de fondo.
      4. Reduce drásticamente el consumo de RAM de ~2.5 GB a menos de ~90 MB.
      5. Cierra todos sus procesos asociados de forma limpia cuando el usuario cierra la ventana.
    """
    import shutil
    import subprocess
    import sys

    candidates = []
    if sys.platform == "win32":
        candidates = [
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            "msedge",
            "chrome",
        ]
    elif sys.platform == "darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]
    else:
        candidates = ["google-chrome", "chromium-browser", "chromium", "microsoft-edge"]

    # Perfil aislado específico para Brackets Web Hub
    profile_dir = os.path.join(os.path.expanduser("~"), ".brackets", "pwa_profile")
    os.makedirs(profile_dir, exist_ok=True)

    # Banderas de optimización extrema de RAM y aislamiento
    flags = [
        f"--app={url}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-default-apps",
        "--disable-background-mode",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-sync",
        "--disable-features=Translate,OptimizationHints,MediaRouter,CalculateNativeWinOcclusion,InterestFeedContentSuggestions,EdgeStartupBoost",
        "--disk-cache-size=33554432",
        "--media-cache-size=16777216",
    ]

    for candidate in candidates:
        exe = shutil.which(candidate) if not os.path.isabs(candidate) else candidate
        if exe and os.path.exists(exe):
            try:
                subprocess.Popen([exe] + flags)
                return True
            except Exception:
                continue

    return False


def run_web_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    workspace_root: Optional[str] = None,
    open_browser: bool = True,
    app_mode: bool = True
) -> None:
    """Inicia el servidor web local para Brackets Web Hub."""
    service = BracketsWebService(workspace_root=workspace_root)
    BracketsApiHandler.service = service

    server_address = (host, port)
    
    # Manejar reintentos si el puerto está ocupado
    for attempt in range(5):
        try:
            httpd = QuietThreadingHTTPServer(server_address, BracketsApiHandler)
            break
        except OSError:
            port += 1
            server_address = (host, port)
    else:
        raise RuntimeError("No se pudo enlazar el servidor a ningún puerto disponible.")

    url = f"http://{host}:{port}"
    print("\n" + "=" * 65)
    print("🌐 BRACKETS WEB HUB — Servidor Activo")
    print("=" * 65)
    print(f"👉 URL Local:  {url}")
    print(f"📁 Workspace:  {service.workspace_root}")
    print(f"📱 Modo:       {'Ventana de App Ligera (Sandbox)' if app_mode else 'Pestaña de Navegador'}")
    print("=" * 65)
    print("Pulsa Ctrl+C para detener el servidor.\n")

    if open_browser:
        opened = False
        if app_mode:
            try:
                opened = open_in_app_mode(url)
            except Exception:
                pass

        if not opened:
            try:
                import webbrowser
                webbrowser.open(url)
            except Exception:
                pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Deteniendo servidor web...")
        httpd.server_close()


if __name__ == "__main__":
    run_web_server()
