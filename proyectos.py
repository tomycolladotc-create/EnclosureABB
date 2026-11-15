"""Un proyecto por tablero: archivos JSON en datos/proyectos/<id>.json.

Compatibilidad: el proyecto histórico 'ts4' sigue en datos/ts4_topografia.json (lo usa generar_topografico.py).
Ningún dato del tablero va en el código: acá solo se leen y escriben los archivos.
"""
import copy
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "datos"
PROJECTS_DIR = DATA / "proyectos"
LEGACY = {"ts4": DATA / "ts4_topografia.json"}
ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,40}")


def slug(name):
    """Convierte un nombre ('TS AUX 1') en un id seguro para nombre de archivo ('ts-aux-1')."""
    text = re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")
    return text[:41] or "tablero"


def path_for(project_id, projects_dir=PROJECTS_DIR):
    if not ID_PATTERN.fullmatch(project_id or ""):
        raise ValueError("Id de proyecto inválido (solo minúsculas, números, guion y guion bajo)")
    return LEGACY.get(project_id) or Path(projects_dir) / f"{project_id}.json"


def list_projects(projects_dir=PROJECTS_DIR):
    found = {}
    for pid, file in LEGACY.items():
        if file.exists():
            found[pid] = file
    if Path(projects_dir).exists():
        for file in sorted(Path(projects_dir).glob("*.json")):
            found.setdefault(file.stem, file)
    out = []
    for pid, file in found.items():
        data = json.loads(file.read_text(encoding="utf-8"))
        out.append({"id": pid, "name": data.get("project", pid), "devices": len(data.get("devices", []))})
    return out


def load(project_id, projects_dir=PROJECTS_DIR):
    file = path_for(project_id, projects_dir)
    if not file.exists():
        raise FileNotFoundError(f"No existe el proyecto '{project_id}'")
    return json.loads(file.read_text(encoding="utf-8"))


def save(project_id, project, projects_dir=PROJECTS_DIR):
    file = path_for(project_id, projects_dir)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")


def create(name, template, projects_dir=PROJECTS_DIR):
    """Proyecto vacío con el mismo gabinete que `template`. Devuelve (id, proyecto). No pisa uno existente."""
    pid = slug(name)
    if path_for(pid, projects_dir).exists():
        raise ValueError(f"Ya existe un proyecto con id '{pid}'")
    project = copy.deepcopy(template)
    project.update(project=name, devices=[], accessories=[])
    save(pid, project, projects_dir)
    return pid, project
