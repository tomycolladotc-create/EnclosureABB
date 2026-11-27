"""Un proyecto por tablero: archivos JSON en datos/proyectos/<id>.json.

Compatibilidad: el proyecto histórico 'ts4' sigue en datos/ts4_topografia.json (lo usa generar_topografico.py).
Ningún dato del tablero va en el código: acá solo se leen y escriben los archivos.
"""
import copy
import json
import re
import unicodedata
import os
from pathlib import Path

import rutas

ROOT = rutas.BUNDLE_ROOT
DATA = rutas.DATA_DIR
# ABB_PROJECTS_DIR: carpeta de proyectos para pruebas automáticas (lección 30: una corrida de prueba dejó 24 tableros
# en datos/proyectos y se subieron al repositorio; las pruebas nunca escriben en los proyectos del usuario).
PROJECTS_DIR = rutas.projects_dir()
LEGACY = {"ts4": DATA / "ts4_topografia.json"}
ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,40}")


def _sanitize_frozen_sample(data):
    """En el ejecutable distribuido, la plantilla base se muestra con nombre y origen 100 % genéricos."""
    out = copy.deepcopy(data)
    out["project"] = "Tablero de ejemplo"
    out["source"] = "Ejemplo incluido"
    out["notes"] = ["Tablero de ejemplo incluido para probar el editor. Importá tu propio unifilar PDF o creá un tablero nuevo."]
    return out


def slug(name):
    """Convierte un nombre ('TS AUX 1') en un id seguro para nombre de archivo ('ts-aux-1')."""
    ascii_name = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return text[:41] or "tablero"


def path_for(project_id, projects_dir=PROJECTS_DIR):
    if not ID_PATTERN.fullmatch(project_id or ""):
        raise ValueError("Id de proyecto inválido (solo minúsculas, números, guion y guion bajo)")
    if project_id in LEGACY:
        if rutas.IS_FROZEN:
            user_copy = Path(projects_dir) / f"{project_id}.json"
            if user_copy.exists():
                return user_copy
        return LEGACY[project_id]
    return Path(projects_dir) / f"{project_id}.json"


def list_projects(projects_dir=PROJECTS_DIR):
    found = {}
    if Path(projects_dir).exists():
        for file in sorted(Path(projects_dir).glob("*.json")):
            found[file.stem] = (file, False)
    for pid, file in LEGACY.items():
        if pid not in found and file.exists():
            found[pid] = (file, rutas.IS_FROZEN)
    out = []
    for pid, (file, is_frozen_tpl) in found.items():
        data = json.loads(file.read_text(encoding="utf-8"))
        if is_frozen_tpl:
            data = _sanitize_frozen_sample(data)
        out.append({"id": pid, "name": data.get("project", pid), "devices": len(data.get("devices", [])),
                    "enclosure": data.get("enclosure", {}).get("id"), "modified": int(file.stat().st_mtime * 1000)})
    return sorted(out, key=lambda p: -p["modified"])  # el último que tocaste, primero


def load(project_id, projects_dir=PROJECTS_DIR):
    file = path_for(project_id, projects_dir)
    if not file.exists():
        raise FileNotFoundError(f"No existe el proyecto '{project_id}'")
    data = json.loads(file.read_text(encoding="utf-8"))
    if rutas.IS_FROZEN and project_id in LEGACY and file == LEGACY[project_id]:
        return _sanitize_frozen_sample(data)
    return data


def save(project_id, project, projects_dir=PROJECTS_DIR):
    if rutas.IS_FROZEN and project_id in LEGACY:
        file = Path(projects_dir) / f"{project_id}.json"
    else:
        file = path_for(project_id, projects_dir)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")


def enclosure_from_catalog(spec):
    """Convierte una envolvente declarativa del catálogo al formato guardado en un proyecto."""
    return {
        "id": spec["id"],
        "line": spec.get("line", spec.get("label", "ABB")),
        "functional": copy.deepcopy(spec["functional"]),
        "externalBody": copy.deepcopy(spec["externalBody"]),
        "plinthHeight": spec.get("plinthHeight", 0),
        "overallHeightWithPlinth": spec.get(
            "overallHeightWithPlinth",
            spec["externalBody"]["height"] + spec.get("plinthHeight", 0),
        ),
        "functionalAreaOffset": copy.deepcopy(spec.get("functionalOffset", {"x": 0, "y": 0})),
        "mountingLayout": copy.deepcopy(spec.get("mountingLayout", {})),
        "structuralComponentReferences": {"parts": copy.deepcopy(spec.get("parts", []))},
        "sources": [spec["source"]] if spec.get("source") else [],
    }


TEMPLATE_CONTENT_KEYS = ("source", "conceptualAssembly", "notes", "devicesNotDrawn", "signals", "feeder", "revisions", "ductMode")


def create(name, template, projects_dir=PROJECTS_DIR, enclosure=None):
    """Crea un proyecto vacío. La envolvente elegida siempre sale del catálogo."""
    pid = slug(name)
    if path_for(pid, projects_dir).exists():
        raise ValueError(f"Ya existe un proyecto con id '{pid}'")
    project = copy.deepcopy(template)
    # Sólo se hereda la estructura (unidades, escala, gabinete): nada del contenido del tablero de plantilla
    # (lección 2026-11-19: los 24 tableros del GENERAL arrastraban kits, notas y origen del TS4).
    for key in TEMPLATE_CONTENT_KEYS:
        project.pop(key, None)
    project.update(project=name, devices=[], accessories=[])
    if enclosure is not None:
        project["enclosure"] = enclosure_from_catalog(enclosure)
    save(pid, project, projects_dir)
    return pid, project


def duplicate(source_id, name, projects_dir=PROJECTS_DIR):
    """Copia completa de un tablero con otro nombre/id, sin compartir estructuras mutables."""
    source = load(source_id, projects_dir)
    pid = slug(name)
    if path_for(pid, projects_dir).exists():
        raise ValueError(f"Ya existe un proyecto con id '{pid}'")
    project = copy.deepcopy(source)
    project["project"] = name
    save(pid, project, projects_dir)
    return pid, project


def delete(project_id, projects_dir=PROJECTS_DIR):
    """Borra un proyecto normal. El TS4 histórico queda protegido como plantilla y caso de prueba."""
    if project_id in LEGACY:
        raise ValueError(f"El proyecto base '{project_id}' no se puede borrar")
    file = path_for(project_id, projects_dir)
    if not file.exists():
        raise FileNotFoundError(f"No existe el proyecto '{project_id}'")
    file.unlink()
