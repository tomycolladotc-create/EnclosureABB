"""Propone los accesorios que exige la normativa (bornes de tierra, cubrebornes, peines) para un proyecto.

Los datos de cada accesorio salen de datos/accesorios_abb.json; las reglas, de normativa_argentina.json.
Todo lo que arma este módulo es una PROPUESTA marcada con auto=True: se reemplaza al volver a proponer.
La geometría es esquemática (rectángulos con las medidas del catálogo) hasta tener el CAD de cada pieza.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATALOG_FILE = ROOT / "datos" / "accesorios_abb.json"
GAP_MM = 1.0           # separación máxima para considerar dos equipos contiguos
RAIL_BAND_MM = 22.25   # franja vertical (mitad de 44,5 mm) que ocupa un borne de riel alrededor del eje del riel


def load_accessory_catalog(path=CATALOG_FILE):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _in_amps(device):
    try:
        return float(str(device.get("marking", {}).get("In", "")).replace(",", "."))
    except ValueError:
        return None


def _free_x(devices, rail, width):
    """Primer hueco libre de `width` mm sobre el riel, buscando desde el extremo derecho. None si no entra."""
    lo, hi = rail["y"] - RAIL_BAND_MM, rail["y"] + RAIL_BAND_MM
    busy = sorted((d["x"], d["x"] + d["w"]) for d in devices if d["y"] < hi and d["y"] + d["h"] > lo)
    cursor = rail["x"] + rail["length"]
    for start, end in reversed(busy):
        if end <= rail["x"] or start >= cursor:
            continue
        if cursor - max(end, rail["x"]) >= width:
            return cursor - width
        cursor = min(cursor, start)
    return cursor - width if cursor - rail["x"] >= width else None


def propose(project, catalog=None):
    """Devuelve la lista completa de accesorios propuestos para `project`."""
    catalog = catalog or load_accessory_catalog()
    devices = [d for d in project.get("devices", []) if d.get("shell")]
    rails = project.get("enclosure", {}).get("mountingLayout", {}).get("dinRails", [])
    out = []

    # 1) Bornes de puesta a tierra: uno por circuito de salida (QF). Simplificación declarada.
    circuits = [d for d in project.get("devices", []) if str(d.get("tag", "")).startswith("QF")]
    pe = next(t for t in catalog["earthTerminals"] if t["id"] == "entrelec-m4-6p")
    if circuits:
        width, height = len(circuits) * pe["pasoMm"], pe["alturaMm"]
        item = {"type": "pe_terminal", "auto": True, "catalogId": pe["id"], "count": len(circuits), "w": width, "h": height,
                "label": f"PE x{len(circuits)}", "provisional": True}
        x = _free_x(devices, rails[0], width) if rails else None
        if x is None:
            item.update(placed=False)
        else:
            item.update(placed=True, x=x, y=rails[0]["y"] - height / 2)
        out.append(item)

    # 2) Cubrebornes transparentes (barrera aislante): uno general; sin geometría hasta tener el CAD.
    if devices:
        out.append({"type": "terminal_cover", "auto": True, "catalogId": None, "label": "Cubrebornes", "provisional": True})

    # 3) Peines entre equipos S200 contiguos, mismo riel y misma serie.
    combs = {c["id"]: c for c in catalog["combs"]}
    s200 = sorted((d for d in devices if "s200" in d["shell"]), key=lambda d: (round(d["y"]), d["x"]))
    group = []
    groups = []
    for d in s200:
        if group and abs(group[-1]["y"] - d["y"]) <= 0.5 and 0 <= d["x"] - (group[-1]["x"] + group[-1]["w"]) <= GAP_MM:
            group.append(d)
        else:
            if len(group) > 1:
                groups.append(group)
            group = [d]
    if len(group) > 1:
        groups.append(group)
    for g in groups:
        poles = {d.get("poles") for d in g}
        comb = combs["abb-ps3-12"] if poles == {3} else combs["abb-ps2"] if poles == {2} else combs["abb-ps4"] if poles == {4} else None
        out.append({"type": "comb", "auto": True, "catalogId": comb["id"] if comb else None, "corrienteA": comb.get("corrienteA") if comb else None,
                    "devices": [d["tag"] for d in g], "x": g[0]["x"], "y": g[0]["y"] + g[0]["h"] - 12, "w": g[-1]["x"] + g[-1]["w"] - g[0]["x"], "h": 4,
                    "label": "Peine", "provisional": True,
                    "note": None if comb else "mezcla de polos: sin peine definido"})
    return out


def complete(project, catalog=None):
    """Reemplaza las propuestas anteriores (auto) y conserva los accesorios cargados a mano."""
    manual = [a for a in project.get("accessories", []) if not a.get("auto")]
    project["accessories"] = manual + propose(project, catalog)
    return project
