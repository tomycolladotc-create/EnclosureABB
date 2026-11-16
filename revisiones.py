"""Control de revisiones embebido en cada archivo de proyecto."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime


def next_code(project):
    codes = [str(item.get("code", "")) for item in project.get("revisions", [])]
    numeric = [int(code) for code in codes if code.isdigit()]
    return str(max(numeric, default=-1) + 1)


def add_revision(project, description, author=""):
    description = str(description).strip()
    if not description:
        raise ValueError("Ingresá una descripción para la revisión")
    updated = deepcopy(project)
    item = {"code": next_code(updated), "date": datetime.now().astimezone().isoformat(timespec="seconds"),
            "description": description, "author": str(author).strip() or "Sin indicar"}
    updated.setdefault("revisions", []).append(item)
    updated["currentRevision"] = item["code"]
    return updated, item
