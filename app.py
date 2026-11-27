"""Servidor local del editor. Los datos ABB y el proyecto viven fuera del código."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, parse_qs, urlparse
import gc
import gzip
import json
import threading
import logging
import os
import sys

import rutas
from importador import apply_corrections, detect_board, detect_devices, detect_edesign_report, detect_signals, ensure_marking, shell_size
from accesorios import complete, load_accessory_catalog
from colocar import place_din
from layout_auto import autolayout, autolayout_conforme
from normativa import check_project
from validacion import validate
from bom import build_bom, bom_issues, to_csv
from revisiones import add_revision
import proyectos

ROOT = rutas.BUNDLE_ROOT
CATALOG = rutas.data_file("catalogo_abb.json")
FRONTS = rutas.data_file("frentes_cad.json")
APPEARANCES = rutas.data_file("apariencias_abb.json")
PRECOMPUTED_FRONTS = rutas.data_file("frentes_resueltos.json.gz")
ICON = rutas.data_file("icon.ico")
_RESOLVED = {}
_RESOLVED_BYTES = {}
_RESOLVE_LOCK = threading.Lock()
DESKTOP_MODE = False
ON_PING = None
ON_BYE = None
ON_REQ_START = None
ON_REQ_END = None


def _load_precomputed_dict():
    if not PRECOMPUTED_FRONTS.exists():
        return None
    stamp = ("precomputed", PRECOMPUTED_FRONTS.stat().st_mtime_ns) if rutas.IS_FROZEN else ("precomputed", rutas.drawing_sources_stamp())
    try:
        with gzip.open(PRECOMPUTED_FRONTS, "rt", encoding="utf-8") as fh:
            cached = json.load(fh)
        if rutas.IS_FROZEN or cached.get("stamp") == stamp[1]:
            return stamp, cached["fronts"], cached["appearances"]
    except Exception:
        return None
    return None


def resolved_drawing_data():
    """Frentes CAD y apariencias resueltos por pintura.resolve; se recalculan sólo si cambió algún archivo.
    En modo congelado (ejecutable) se leen desde frentes_resueltos.json.gz sin retener dicts pesados en RAM."""
    with _RESOLVE_LOCK:
        pre = _load_precomputed_dict()
        if pre is not None:
            stamp, fronts, appearances = pre
            if rutas.IS_FROZEN:
                return fronts, appearances
            _RESOLVED.update(stamp=stamp, data=(fronts, appearances))
            return _RESOLVED["data"]
        return _resolved_locked()


def resolved_drawing_bytes(kind):
    """JSON UTF-8 compacto de fronts/appearances para /api/fronts y /api/appearances (~2 MB en vez de ~25 MB de dicts)."""
    with _RESOLVE_LOCK:
        if PRECOMPUTED_FRONTS.exists():
            stamp = ("precomputed", PRECOMPUTED_FRONTS.stat().st_mtime_ns) if rutas.IS_FROZEN else ("precomputed", rutas.drawing_sources_stamp())
            if _RESOLVED_BYTES.get("stamp") == stamp:
                return _RESOLVED_BYTES[kind]
            pre = _load_precomputed_dict()
            if pre is not None:
                st, fronts, appearances = pre
                _RESOLVED_BYTES.clear()
                _RESOLVED_BYTES.update(
                    stamp=st,
                    fronts=json.dumps(fronts, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
                    appearances=json.dumps(appearances, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
                )
                del fronts, appearances
                gc.collect()
                return _RESOLVED_BYTES[kind]
        fronts, appearances = _resolved_locked()
        return json.dumps(fronts if kind == "fronts" else appearances, ensure_ascii=False).encode("utf-8")


def _resolved_locked():
    from pintura import resolve
    stamp = tuple(p.stat().st_mtime_ns for p in (FRONTS, APPEARANCES, CATALOG))
    if _RESOLVED.get("stamp") != stamp:
        _RESOLVED.update(stamp=stamp, data=resolve(json.loads(FRONTS.read_text(encoding="utf-8")),
                                                  json.loads(APPEARANCES.read_text(encoding="utf-8")),
                                                  json.loads(CATALOG.read_text(encoding="utf-8"))))
    return _RESOLVED["data"]


VALIDATION_RULES = rutas.data_file("reglas_validacion.json")
WEB = rutas.WEB_DIR / "index.html"
WEB_STYLES = rutas.WEB_DIR / "styles.css"
MAX_PDF = 30 * 1024 * 1024
MAX_FORMAT = 200 * 1024 * 1024  # el DXF de formato con todos los unifilares puede pesar decenas de MB
FORMATS = rutas.formats_dir()  # (las pruebas usan una carpeta temporal) formato de ploteo del usuario (DXF) y los últimos datos del rótulo; no se sube al repo
logging.getLogger("pypdf").setLevel(logging.ERROR)


class Handler(BaseHTTPRequestHandler):
    def handle_one_request(self):
        if callable(ON_REQ_START):
            ON_REQ_START()
        try:
            super().handle_one_request()
        finally:
            if callable(ON_REQ_END):
                ON_REQ_END()

    def log_message(self, format, *args):
        if sys.stderr is not None and not DESKTOP_MODE:
            super().log_message(format, *args)
    def send_data(self, status, body, mime="application/json"):
        blob = (json.dumps(body, ensure_ascii=False).encode() if isinstance(body, (dict, list)) else body)
        self.send_response(status)
        self.send_header("Content-Type", mime + ("; charset=utf-8" if mime.startswith(("text/", "application/json")) else ""))
        self.send_header("Content-Length", str(len(blob)))
        self.send_header("Cache-Control", "no-store")  # programa local: el navegador nunca debe mostrar una versión vieja del editor
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
        if route == "/favicon.ico":
            if ICON.exists():
                return self.send_data(200, ICON.read_bytes(), "image/x-icon")
            return self.send_data(204, b"", "image/x-icon")
        if route == "/api/ping":
            if callable(ON_PING):
                ON_PING()
            return self.send_data(200, {"app": "EnclosureABB", "desktop": bool(DESKTOP_MODE)})
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
            data = json.loads(CATALOG.read_text(encoding="utf-8"))
            from bom import catalog_devices, load_order_codes
            codes = load_order_codes()
            data["orderCodes"] = codes  # códigos verificados: el editor muestra cuál irá a la lista
            data["deviceCatalog"] = catalog_devices(data, codes)
            rules = json.loads((ROOT / "datos" / "reglas_layout.json").read_text(encoding="utf-8"))
            data["layoutRules"] = {"labels": rules["labels"], "plano": {k: rules["planoUnifilar"][k] for k in ("fieldLabels", "revisionColumns")}}

            return self.send_data(200, data)
        if route == "/api/ducts":  # secciones estándar de canaleta (catálogo ABB) para dibujarlas a mano
            return self.send_data(200, load_accessory_catalog().get("wiringDucts", {}))
        if route == "/api/entrega/datos":  # campos del rótulo del PDF de entrega y lo último que se cargó
            rules = json.loads((ROOT / "datos" / "reglas_layout.json").read_text(encoding="utf-8"))["entregaPdf"]
            saved = FORMATS / "entrega.json"
            data = {"fields": rules["fields"], "values": json.loads(saved.read_text(encoding="utf-8")) if saved.exists() else {}}
            if (FORMATS / "formato.json").exists() and (FORMATS / "formato.dxf").exists():  # con formato cargado, su rótulo
                from plano_unifilar import content_tags
                meta = json.loads((FORMATS / "formato.json").read_text(encoding="utf-8"))
                meta["contentTags"] = content_tags(meta.get("fields", []))
                data["format"] = meta
            return self.send_data(200, data)
        if route == "/api/plano/formato":  # formato cargado la última vez, con los datos del rótulo que se usaron
            meta = FORMATS / "formato.json"
            if not meta.exists():
                return self.send_data(404, {"error": "Todavía no se cargó un formato"})
            return self.send_data(200, json.loads(meta.read_text(encoding="utf-8")))
        if route in ("/api/fronts", "/api/appearances"):  # ya resueltos (pintura.resolve): pantalla y DXF usan lo mismo
            return self.send_data(200, resolved_drawing_bytes("fronts" if route == "/api/fronts" else "appearances"))
        self.send_data(404, {"error": "Ruta inexistente"})

    def do_POST(self):
        route = urlparse(self.path).path
        if route == "/api/bye":
            if callable(ON_BYE):
                ON_BYE()
            return self.send_data(204, b"", "text/plain")
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > (MAX_FORMAT if route == "/api/plano/formato" else MAX_PDF):
            return self.send_data(400, {"error": "Archivo vacío o demasiado grande (máximo 30 MB)"})
        blob = self.rfile.read(length)
        if route == "/api/import-pdf":
            if not blob.startswith(b"%PDF"):
                return self.send_data(400, {"error": "El archivo no es un PDF"})
            try:
                catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
                report = detect_edesign_report(blob, catalog)
                if report is not None:
                    gc.collect()
                    return self.send_data(200, report)
                from io import BytesIO
                from pypdf import PdfReader
                reader = PdfReader(BytesIO(blob))
                content = "\n".join(page.extract_text() or "" for page in reader.pages)
                devices, board = detect_devices(content, catalog), detect_board(content)
                unused = apply_corrections(devices, board, catalog)  # cambios de equipo pedidos por el usuario (datos/correcciones_unifilar.json)
                from verificacion_unifilar import check  # segunda lectura del plano, por posición: modelo, polos y corriente de cada circuito
                verification = check(blob, devices, catalog)
                res = {"pages": len(reader.pages), "devices": devices, "signals": detect_signals(content, catalog), "board": board,
                       "correctionsNotApplied": unused, "textAvailable": bool(content.strip()), "verification": verification}
                gc.collect()
                return self.send_data(200, res)
            except Exception as exc:
                return self.send_data(422, {"error": f"No se pudo leer el PDF: {exc}"})
        if route == "/api/import-batch":
            try:
                data = json.loads(blob)
                boards = data.get("boards") or []
                if not boards:
                    raise ValueError("No hay tableros seleccionados para importar.")
                source = str(data.get("source") or "e-Design.pdf")
                overwrite = bool(data.get("overwrite", True))
                catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
                template = proyectos.load("ts4")
                from auditoria import audit
                results, created, updated, skipped, failed = [], 0, 0, 0, 0
                for b in boards:
                    title = str(b.get("title") or "").strip() or "Tablero"
                    pid = proyectos.slug(title)
                    if pid in proyectos.LEGACY:
                        pid = f"{pid}-imp"
                    exists = proyectos.path_for(pid).exists()
                    if exists and not overwrite:
                        skipped += 1
                        results.append({"id": pid, "name": title, "status": "skipped"})
                        continue
                    try:
                        import copy
                        proj = copy.deepcopy(template)
                        for k in proyectos.TEMPLATE_CONTENT_KEYS:
                            proj.pop(k, None)
                        all_devs = [d for d in (b.get("devices") or []) if not d.get("upstream")]
                        drawn = [{**d, "x": 150, "y": 150, "unplaced": True} for d in all_devs if d.get("shell")]
                        not_drawn = [{k: d.get(k) for k in ("tag", "circuit", "model", "poles", "status", "orderCode") if d.get(k) is not None}
                                     for d in all_devs if not d.get("shell")]
                        proj.update(project=title, source=source, devices=drawn, devicesNotDrawn=not_drawn, accessories=[])
                        if b.get("feeder"):
                            proj["feeder"] = b["feeder"]
                        if b.get("verification"):
                            proj["sourceCheck"] = {"file": source, **b["verification"]}
                        new_proj, summary = autolayout_conforme(proj, catalog)
                        proyectos.save(pid, new_proj)
                        aud = audit(new_proj, catalog, board_title=title)
                        errs = [f for f in aud if f["level"] == "error"]
                        warns = [f for f in aud if f["level"] != "error"]
                        if exists:
                            updated += 1
                        else:
                            created += 1
                        results.append({"id": pid, "name": title, "status": "updated" if exists else "created",
                                        "enclosure": summary["gabinete"], "devices": len(new_proj["devices"]),
                                        "notDrawn": len(not_drawn), "errors": len(errs), "warnings": len(warns),
                                        "errorMessages": [e["message"] for e in errs]})
                    except Exception as exc:
                        failed += 1
                        results.append({"id": pid, "name": title, "status": "failed", "error": str(exc)})
                return self.send_data(200, {"results": results, "created": created, "updated": updated, "skipped": skipped, "failed": failed})
            except (ValueError, KeyError, TypeError) as exc:
                return self.send_data(422, {"error": str(exc)})
        if route == "/api/signals-default":  # testigos de fase propuestos (regla única en accesorios.default_signals)
            try:
                from accesorios import default_signals
                query = parse_qs(urlparse(self.path).query)
                payload = json.loads(blob)
                poles = (query.get("poles") or [None])[0]
                if isinstance(payload, dict) and isinstance(payload.get("project"), dict):
                    if poles is None:
                        poles = payload.get("poles")
                    payload = payload["project"]
                if poles is not None and str(poles).isdigit():
                    poles = int(poles)
                return self.send_data(200, default_signals(payload, poles=poles))
            except ValueError as exc:
                return self.send_data(422, {"error": str(exc)})
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
                query = parse_qs(urlparse(self.path).query)
                new, summary = autolayout_conforme(project, catalog, free_rails=query.get("free") == ["1"], only=(query.get("enclosure") or [None])[0])
                return self.send_data(200, {"project": new, "summary": summary, "findings": check_project(new)})
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
                query = parse_qs(urlparse(self.path).query)
                mode = "generic" if (query.get("mode") or ["abb"])[0] == "generic" else "abb"
                rows = build_bom(project, catalog, mode=mode)
                issues = bom_issues(rows, project)
                if route == "/api/export-bom":
                    return self.send_data(200, to_csv(rows, issues), "text/csv")
                return self.send_data(200, {"rows": rows, "issues": issues, "mode": mode})
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
                    complete(project, auto_confirm=True)
                return self.send_data(200, {"accessories": project.get("accessories", []), "findings": check_project(project)})
            except (ValueError, UnicodeDecodeError, KeyError, StopIteration) as exc:
                return self.send_data(422, {"error": str(exc)})
        if route == "/api/plano/formato":  # formato de ploteo del usuario (DXF guardado desde su DWG)
            if b"SECTION" not in blob[:4096]:
                return self.send_data(400, {"error": "El archivo no es un DXF. En AutoCAD: Guardar como → AutoCAD 2018 DXF."})
            try:
                from plano_unifilar import analyze_template
                FORMATS.mkdir(parents=True, exist_ok=True)
                (FORMATS / "formato.dxf").write_bytes(blob)
                meta = analyze_template(str(FORMATS / "formato.dxf"))
                if not meta["sheets"]:
                    return self.send_data(422, {"error": "El formato no tiene ninguna presentación con marco y rótulo con atributos."})
                meta["filename"] = unquote(self.headers.get("X-Filename", "formato.dxf"))
                (FORMATS / "formato.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
                return self.send_data(200, meta)
            except Exception as exc:  # noqa: BLE001
                return self.send_data(422, {"error": f"No se pudo leer el formato: {exc}"})
        if route == "/api/plano/generar":  # hoja de fabricación con el rótulo que completó el usuario
            try:
                from plano_unifilar import compose
                req = json.loads(blob)
                if not (FORMATS / "formato.dxf").exists():
                    return self.send_data(422, {"error": "Primero cargá el formato (DXF)."})
                projects = {}
                for pid in req.get("projects", []):
                    p = proyectos.load(pid)
                    projects[p.get("project", pid)] = p
                if not projects:
                    return self.send_data(422, {"error": "Elegí al menos un tablero."})
                catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
                fronts, appearances = resolved_drawing_data()
                values = {k: str(v) for k, v in (req.get("values") or {}).items()}
                text, report = compose(str(FORMATS / "formato.dxf"), projects, catalog, fronts, appearances,
                                       title_values=values, only_generated=True)
                meta = json.loads((FORMATS / "formato.json").read_text(encoding="utf-8"))
                for f in meta["fields"]:  # la próxima vez la ventana arranca con lo último que se cargó
                    if f["tag"] in values:
                        f["value"] = values[f["tag"]]
                meta["lastFilename"] = req.get("filename")
                (FORMATS / "formato.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
                missing = [r for r in report if "no tiene" in r or "falta" in r]
                if len(missing) == len(report):
                    return self.send_data(422, {"error": "Ningún tablero se pudo armar: " + "; ".join(report)})
                self.send_response(200)
                body = text.encode("utf-8")
                self.send_header("Content-Type", "application/dxf")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("X-Report", quote(" | ".join(report)))
                self.end_headers()
                self.wfile.write(body)
                return None
            except (ValueError, FileNotFoundError, KeyError) as exc:
                return self.send_data(422, {"error": str(exc)})
        if route == "/api/export/entrega":  # PDF único de entrega: carátula, índice, tableros y lista consolidada
            try:
                from entrega_pdf import build_pdf
                req = json.loads(blob)
                projects = {}
                for pid in req.get("projects", []):
                    p = proyectos.load(pid)
                    projects[p.get("project", pid)] = p
                if not projects:
                    return self.send_data(422, {"error": "Elegí al menos un tablero."})
                values = {k: str(v) for k, v in (req.get("values") or {}).items()}
                FORMATS.mkdir(parents=True, exist_ok=True)  # la próxima vez la ventana arranca con lo último que se cargó
                template = None
                if req.get("format"):  # rótulo del formato del usuario: los datos son los mismos del plano de fabricación
                    if not (FORMATS / "formato.dxf").exists():
                        return self.send_data(422, {"error": "Primero cargá el formato (DXF) en «Plano de fabricación»."})
                    template = str(FORMATS / "formato.dxf")
                    meta = json.loads((FORMATS / "formato.json").read_text(encoding="utf-8"))
                    for f in meta.get("fields", []):
                        if f["tag"] in values:
                            f["value"] = values[f["tag"]]
                    (FORMATS / "formato.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
                else:
                    (FORMATS / "entrega.json").write_text(json.dumps(values, ensure_ascii=False, indent=1), encoding="utf-8")
                catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
                fronts, appearances = resolved_drawing_data()
                bom_mode = "generic" if req.get("bomMode") == "generic" else "abb"
                pdf_bytes = build_pdf(projects, catalog, fronts, appearances, values, shop=bool(req.get("shop", True)), template=template, bom_mode=bom_mode)
                gc.collect()
                return self.send_data(200, pdf_bytes, "application/pdf")
            except (ValueError, FileNotFoundError, KeyError) as exc:
                return self.send_data(422, {"error": str(exc)})
        if route == "/api/export/equipamiento":  # Excel de equipamiento eléctrico de los tableros elegidos
            try:
                from excel_equipamiento import build_xlsx
                req = json.loads(blob)
                projects = {}
                for pid in req.get("projects", []):
                    p = proyectos.load(pid)
                    projects[p.get("project", pid)] = p
                if not projects:
                    return self.send_data(422, {"error": "Elegí al menos un tablero."})
                catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
                mode = "generic" if req.get("mode") == "generic" else "abb"
                xlsx_bytes = build_xlsx(projects, catalog, mode=mode)
                gc.collect()
                return self.send_data(200, xlsx_bytes,
                                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except (ValueError, FileNotFoundError, KeyError) as exc:
                return self.send_data(422, {"error": str(exc)})
        if route == "/api/export-dxf":
            try:
                from cad_export import build_dxf
                project = json.loads(blob)
                catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
                fronts, appearances = resolved_drawing_data()
                dxf_bytes = build_dxf(project, catalog, fronts, appearances)
                gc.collect()
                return self.send_data(200, dxf_bytes, "application/dxf")
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
    threading.Thread(target=resolved_drawing_data, daemon=True).start()  # pintura lista antes de que el navegador la pida
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
