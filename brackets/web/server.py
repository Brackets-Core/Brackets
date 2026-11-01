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


class BracketsApiHandler(SimpleHTTPRequestHandler):
    """Manejador HTTP para la API REST y los archivos estáticos de la PWA."""

    service: Optional[BracketsWebService] = None
    static_dir: str = os.path.join(os.path.dirname(__file__), "static")

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
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

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

                else:
                    return self._send_json(404, {"error": f"Ruta API no encontrada: {path}"})
            except Exception as e:
                return self._send_json(500, {"error": str(e)})

        # Si pide la raíz o rutas sin archivo, servir index.html
        if path == "/" or not os.path.exists(os.path.join(self.static_dir, path.lstrip("/"))):
            self.path = "/index.html"

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

                elif path == "/api/sync":
                    vault = body.get("vault")
                    res = svc.sync_week(vault_identifier=vault)
                    return self._send_json(200, res)

                else:
                    return self._send_json(404, {"error": f"Ruta POST no encontrada: {path}"})
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

                return self._send_json(404, {"error": f"Ruta PATCH no encontrada: {path}"})
            except Exception as e:
                return self._send_json(500, {"error": str(e)})

        return self._send_json(405, {"error": "Método no permitido"})


def run_web_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    workspace_root: Optional[str] = None,
    open_browser: bool = True
) -> None:
    """Inicia el servidor web local para Brackets Web Hub."""
    service = BracketsWebService(workspace_root=workspace_root)
    BracketsApiHandler.service = service

    server_address = (host, port)
    
    # Manejar reintentos si el puerto está ocupado
    for attempt in range(5):
        try:
            httpd = ThreadingHTTPServer(server_address, BracketsApiHandler)
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
    print(f"📱 Instalable como PWA en Windows y móvil.")
    print("=" * 65)
    print("Pulsa Ctrl+C para detener el servidor.\n")

    if open_browser:
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
