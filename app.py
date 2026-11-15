"""Servidor local del editor. Los datos ABB y el proyecto viven fuera del código."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import json
import re
import logging
import os

from pypdf import PdfReader
from cad_export import build_dxf

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT / "datos" / "ts4_topografia.json"
CATALOG = ROOT / "datos" / "catalogo_abb.json"
FRONTS = ROOT / "datos" / "frentes_cad.json"
APPEARANCES = ROOT / "datos" / "apariencias_abb.json"
WEB = ROOT / "web" / "index.html"
MAX_PDF = 30 * 1024 * 1024
logging.getLogger("pypdf").setLevel(logging.ERROR)


def detect_devices(text, catalog):
    """Extrae etiquetas y propone familias; conserva el fragmento original para revisar."""
    shells = {item["id"]: item for item in catalog["deviceShells"]}
    matches = list(re.finditer(r"-(QF\d+|QS\d+)\b", text))
    found = []
    for index, match in enumerate(matches):
        context = text[max(0, match.start() - 35):match.start()].upper()
        upstream = "DE TGBT" in context
        raw = text[match.end(): min(match.end() + 90, matches[index + 1].start() if index + 1 < len(matches) else len(text))]
        snippet = " ".join(raw.split())[:90]
        upper = snippet.upper()
        shell_id = None
        if "XT1" in upper:
            shell_id = "abb.tmax.xt1.4p.fixed.front"
        elif "XT2" in upper:
            shell_id = "abb.tmax.xt2.4p.fixed.front"
        elif "S804N" in upper:
            shell_id = "abb.s804n.4p.front"
        elif "S201M" in upper:
            shell_id = "abb.s200m.1pn.front" if "NA" in upper or "1P+N" in upper else "abb.s200m.1p.front"
        elif "OT400" in upper:
            shell_id = "abb.ot400e04.4p.front"
        item = shells.get(shell_id, {})
        found.append({
            "tag": match.group(1), "evidence": snippet, "shell": shell_id,
            "model": snippet.split("3x")[0].split("4x")[0][:40].strip(),
            "w": item.get("width", 80), "h": item.get("height", 100),
            "status": "alimentador externo; no pertenece al tablero" if upstream else ("detectado; revisar modelo y polos" if shell_id else "sin familia identificada"),
            "upstream": upstream
        })
    return found


class Handler(BaseHTTPRequestHandler):
    def send_data(self, status, body, mime="application/json"):
        blob = (json.dumps(body, ensure_ascii=False).encode() if isinstance(body, (dict, list)) else body)
        self.send_response(status)
        self.send_header("Content-Type", mime + ("; charset=utf-8" if mime.startswith(("text/", "application/json")) else ""))
        self.send_header("Content-Length", str(len(blob)))
        self.end_headers()
        self.wfile.write(blob)

    def do_GET(self):
        route = urlparse(self.path).path
        if route == "/":
            return self.send_data(200, WEB.read_bytes(), "text/html")
        if route == "/api/project":
            return self.send_data(200, json.loads(PROJECT.read_text(encoding="utf-8")))
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
                        device["w"], device["h"] = spec["width"], spec["height"]
                PROJECT.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
                return self.send_data(200, {"saved": True})
            except (ValueError, UnicodeDecodeError) as exc:
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


if __name__ == "__main__":
    port = int(os.environ.get("ABB_EDITOR_PORT", "8765"))
    print(f"Editor ABB: http://127.0.0.1:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
