"""Servidor local del editor. Los datos ABB y el proyecto viven fuera del código."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import json
import logging
import os

from pypdf import PdfReader
from cad_export import build_dxf
from importador import detect_devices, ensure_marking, shell_size
from accesorios import complete
from colocar import place_din
from layout_auto import autolayout
from normativa import check_project
from validacion import validate
from bom import build_bom, to_csv
from revisiones import add_revision
import proyectos

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "datos" / "catalogo_abb.json"
FRONTS = ROOT / "datos" / "frentes_cad.json"
APPEARANCES = ROOT / "datos" / "apariencias_abb.json"
VALIDATION_RULES = ROOT / "datos" / "reglas_validacion.json"
WEB = ROOT / "web" / "index.html"
WEB_STYLES = ROOT / "web" / "styles.css"
MAX_PDF = 30 * 1024 * 1024
logging.getLogger("pypdf").setLevel(logging.ERROR)


class Handler(BaseHTTPRequestHandler):
    def send_data(self, status, body, mime="application/json"):
        blob = (json.dumps(body, ensure_ascii=False).encode() if isinstance(body, (dict, list)) else body)
        self.send_response(status)
        self.send_header("Content-Type", mime + ("; charset=utf-8" if mime.startswith(("text/", "application/json")) else ""))
        self.send_header("Content-Length", str(len(blob)))
        self.end_headers()
        self.wfile.write(blob)

    def project_id(self):
        return (parse_qs(urlparse(self.path).query).get("id") or ["ts4"])[0]

    def do_GET(self):
        route = urlparse(self.path).path
        if route == "/":
            return self.send_data(200, WEB.read_bytes(), "text/html")
        if route == "/styles.css":
            return self.send_data(200, WEB_STYLES.read_bytes(), "text/css")
        if route == "/api/projects":
            return self.send_data(200, proyectos.list_projects())
        if route == "/api/project":
            try:
                project = proyectos.load(self.project_id())
            except (ValueError, FileNotFoundError) as exc:
                return self.send_data(404, {"error": str(exc)})
            catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
            for device in project.get("devices", []):
                ensure_marking(device, catalog)
            return self.send_data(200, project)
        if route == "/api/catalog":
            return self.send_data(200, json.loads(CATALOG.read_text(encoding="utf-8")))
        if route == "/api/fronts":
            return self.send_data(200, json.loads(FRONTS.read_text(encoding="utf-8")))
        if route == "/api/appearances":
            return self.send_data(200, json.loads(APPEARANCES.read_text(encoding="utf-8")))
        self.send_data(404, {"error": "Ruta inexistente"})

    def do_POST(self):
        route = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_PDF:
            return self.send_data(400, {"error": "Archivo vacío o demasiado grande (máximo 30 MB)"})
        blob = self.rfile.read(length)
        if route == "/api/import-pdf":
            if not blob.startswith(b"%PDF"):
                return self.send_data(400, {"error": "El archivo no es un PDF"})
            try:
                from io import BytesIO
                reader = PdfReader(BytesIO(blob))
                content = "\n".join(page.extract_text() or "" for page in reader.pages)
                catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
                return self.send_data(200, {"pages": len(reader.pages), "devices": detect_devices(content, catalog), "textAvailable": bool(content.strip())})
            except Exception as exc:
                return self.send_data(422, {"error": f"No se pudo leer el PDF: {exc}"})
        if route == "/api/save":
            try:
                project = json.loads(blob)
                if not isinstance(project.get("devices"), list) or not isinstance(project.get("enclosure"), dict):
                    raise ValueError("Proyecto incompleto")
                catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
                shells = {item["id"]: item for item in catalog["deviceShells"]}
                for device in project["devices"]:
                    spec = shells.get(device.get("shell"))
                    if spec:
                        device["w"], device["h"] = shell_size(spec, device.get("poles"))
                proyectos.save(self.project_id(), project)
                return self.send_data(200, {"saved": True, "id": self.project_id()})
            except (ValueError, UnicodeDecodeError) as exc:
                return self.send_data(422, {"error": str(exc)})
        if route == "/api/autolayout":
            try:
                project = json.loads(blob)
                catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
                new, summary = autolayout(project, catalog)
                complete(new)
                return self.send_data(200, {"project": new, "summary": summary})
            except (ValueError, UnicodeDecodeError, KeyError) as exc:
                return self.send_data(422, {"error": str(exc)})
        if route == "/api/validate":
            try:
                project = json.loads(blob)
                catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
                rules = json.loads(VALIDATION_RULES.read_text(encoding="utf-8"))
                return self.send_data(200, validate(project, catalog, rules))
            except (ValueError, KeyError, TypeError) as exc:
                return self.send_data(422, {"error": str(exc)})
        if route in ("/api/bom", "/api/export-bom"):
            try:
                project = json.loads(blob)
                catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
                rows = build_bom(project, catalog)
                if route == "/api/export-bom":
                    return self.send_data(200, to_csv(rows), "text/csv")
                return self.send_data(200, {"rows": rows})
            except (ValueError, KeyError, TypeError) as exc:
                return self.send_data(422, {"error": str(exc)})
        if route == "/api/revision":
            try:
                data = json.loads(blob)
                updated, revision = add_revision(data["project"], data.get("description", ""), data.get("author", ""))
                return self.send_data(200, {"project": updated, "revision": revision})
            except (ValueError, KeyError, TypeError) as exc:
                return self.send_data(422, {"error": str(exc)})
        if route == "/api/place":
            try:
                project = json.loads(blob)
                catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
                failed = place_din(project, catalog)
                return self.send_data(200, {"devices": project["devices"], "failed": failed})
            except (ValueError, UnicodeDecodeError, KeyError) as exc:
                return self.send_data(422, {"error": str(exc)})
        if route == "/api/project-new":
            try:
                data = json.loads(blob)
                name = str(data.get("name", "")).strip()
                if not name:
                    raise ValueError("Ingresá un nombre para el tablero")
                catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
                enclosure_id = str(data.get("enclosureId", "")).strip()
                enclosure = next((item for item in catalog["enclosures"] if item["id"] == enclosure_id), None)
                if enclosure is None:
                    raise ValueError("Elegí una envolvente ABB válida")
                pid, project = proyectos.create(name, proyectos.load("ts4"), enclosure=enclosure)
                return self.send_data(200, {"id": pid, "project": project})
            except (ValueError, UnicodeDecodeError, FileNotFoundError) as exc:
                return self.send_data(422, {"error": str(exc)})
        if route == "/api/project-duplicate":
            try:
                data = json.loads(blob)
                name = str(data.get("name", "")).strip()
                if not name:
                    raise ValueError("Ingresá un nombre para la copia")
                pid, project = proyectos.duplicate(str(data.get("sourceId", "")), name)
                return self.send_data(200, {"id": pid, "project": project})
            except (ValueError, UnicodeDecodeError, FileNotFoundError) as exc:
                return self.send_data(422, {"error": str(exc)})
        if route in ("/api/normativa", "/api/normativa/complete"):
            try:
                project = json.loads(blob)
                if route.endswith("/complete"):
                    complete(project)
                return self.send_data(200, {"accessories": project.get("accessories", []), "findings": check_project(project)})
            except (ValueError, UnicodeDecodeError, KeyError, StopIteration) as exc:
                return self.send_data(422, {"error": str(exc)})
        if route == "/api/export-dxf":
            try:
                project = json.loads(blob)
                catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
                fronts = json.loads(FRONTS.read_text(encoding="utf-8"))
                appearances = json.loads(APPEARANCES.read_text(encoding="utf-8"))
                return self.send_data(200, build_dxf(project, catalog, fronts, appearances), "application/dxf")
            except (ValueError, UnicodeDecodeError, KeyError) as exc:
                return self.send_data(422, {"error": str(exc)})
        self.send_data(404, {"error": "Ruta inexistente"})

    def do_DELETE(self):
        route = urlparse(self.path).path
        if route != "/api/project":
            return self.send_data(404, {"error": "Ruta inexistente"})
        try:
            project_id = self.project_id()
            proyectos.delete(project_id)
            return self.send_data(200, {"deleted": True, "id": project_id})
        except ValueError as exc:
            return self.send_data(409, {"error": str(exc)})
        except FileNotFoundError as exc:
            return self.send_data(404, {"error": str(exc)})


if __name__ == "__main__":
    port = int(os.environ.get("ABB_EDITOR_PORT", "8765"))
    print(f"Editor ABB: http://127.0.0.1:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
