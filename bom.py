"""Lista de materiales agrupada a partir del proyecto y el catálogo ABB."""
from __future__ import annotations

import csv
import io
import re


def _pending(text):
    return bool(re.search(r"pendiente|confirm|placeholder|conflict|variant|revisar", str(text), re.I))


def build_bom(project, catalog):
    enclosures = {item["id"]: item for item in catalog.get("enclosures", [])}
    shells = {item["id"]: item for item in catalog.get("deviceShells", [])}
    enclosure = project.get("enclosure", {})
    spec = enclosures.get(enclosure.get("id"), {}) or next(
        (item for item in catalog.get("enclosures", []) if item.get("functional") == enclosure.get("functional")), {}
    )
    rows = []

    def add(category, code, description, quantity=1, tags=(), status="verificado", source=""):
        rows.append({"category": category, "code": code or "POR CONFIRMAR", "description": description,
                     "quantity": quantity, "tags": ", ".join(tags), "status": status, "source": source})

    add("Envolvente", spec.get("id") or enclosure.get("id"), spec.get("label") or enclosure.get("line", "Envolvente ABB"),
        status=spec.get("argentinaStatus", "por confirmar"), source=spec.get("source", ""))

    structure = spec.get("structure", {})
    for part in structure.get("bom", []):
        match = re.search(r"\(x(\d+)\)", part.get("parte", ""), re.I)
        add("Estructura", part.get("orden") or part.get("codigo"), part.get("parte", "Pieza de envolvente"),
            int(match.group(1)) if match else 1, status=structure.get("status", "por confirmar"), source=structure.get("source", ""))

    rails = enclosure.get("mountingLayout", {}).get("dinRails", [])
    for kit in sorted({r["kdKit"] for r in rails if r.get("kdKit")}):
        kd = spec.get("kdKit") or {}
        add("Kit de soportes DIN", kit, f"Kit KD de soportes para paneles modulares: {kd.get('rows', '?')} filas de {kd.get('modulesPerRow', '?')} módulos (paso {kd.get('rowPitchMm', 185)} mm)",
            status="catálogo SR2 pág. 2/4; confirmar con ABB si incluye los rieles", source=kd.get("source", ""))
    for rail in rails:
        if rail.get("kdKit"):
            add("Riel DIN", rail.get("orderCode") or "POR CONFIRMAR", f"Riel DIN de la {rail.get('type', 'fila')} · largo {rail.get('length', '?')} mm (confirmar si lo incluye el kit)",
                status="por confirmar")
            continue
        add("Riel DIN", rail.get("orderCode") or rail.get("type"), f"{rail.get('type', 'Riel DIN')} · {rail.get('length', '?')} mm",
            status=enclosure.get("mountingLayout", {}).get("status", "por confirmar"))

    grouped = {}
    for device in project.get("devices", []):
        key = (device.get("model", ""), device.get("shell", ""), device.get("poles"))
        grouped.setdefault(key, []).append(device)
    for (model, shell_id, poles), devices in grouped.items():
        shell = shells.get(shell_id, {})
        statuses = [device.get("status", "") for device in devices]
        add("Equipo", model or shell.get("label", shell_id), f"{model or shell.get('label', shell_id)}" + (f" · {poles} polos" if poles else ""),
            len(devices), [(f"{device['circuit']} ({device.get('tag', '?')})" if device.get("circuit") else device.get("tag", "?")) for device in devices], "por confirmar" if any(_pending(value) for value in statuses) or shell.get("provisional") else "catálogo/proyecto",
            shell.get("cadSource", ""))

    kits = {}
    for device in project.get("devices", []):
        kit = device.get("mountingKit") or {}
        code = kit.get("orderCode") or kit.get("type") or kit.get("kit")
        if code:
            kits.setdefault((code, kit.get("type") or kit.get("kit") or "Kit de montaje"), []).append(device.get("tag", "?"))
    for (code, description), tags in kits.items():
        add("Kit de montaje", code, description, len(tags), tags, "identificado; validar BOM de montaje")

    grouped_accessories = {}
    for item in project.get("accessories", []):
        if item.get("decision") == "discarded":
            continue
        category = item.get("bomCategory") or "Accesorio"
        description = item.get("description") or item.get("label") or item.get("type")
        key = (category, item.get("orderCode") or item.get("id") or item.get("type"), description)
        grouped_accessories[key] = grouped_accessories.get(key, 0) + int(item.get("quantity", 1))
        for extra in item.get("bomExtra", []):  # renglones asociados (p. ej. topes de la bornera)
            k = (extra["bomCategory"], extra.get("orderCode") or "POR CONFIRMAR", extra["description"])
            grouped_accessories[k] = grouped_accessories.get(k, 0) + int(extra.get("quantity", 1))
    for (category, code, description), quantity in grouped_accessories.items():
        add(category, code, description, quantity, status="propuesta por confirmar")
    return rows


def to_csv(rows):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=("category", "code", "description", "quantity", "tags", "status", "source"), delimiter=";")
    writer.writerow({"category": "Categoría", "code": "Código", "description": "Descripción", "quantity": "Cantidad", "tags": "Tags", "status": "Estado", "source": "Fuente"})
    writer.writerows(rows)
    return ("\ufeff" + output.getvalue()).encode("utf-8")
