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


BAR_MARGIN_MM = 40.0  # criterio de diseño propuesto (no dato ABB): separación de la barra al borde de la placa
BAR_FACE_MM = 20.0  # cara de la barra AA8010 (20x5 mm)


def load_accessory_catalog(path=CATALOG_FILE):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _in_amps(device):
    try:
        return float(str(device.get("marking", {}).get("In", "")).replace(",", "."))
    except ValueError:
        return None


def _free_x(devices, rail, width, height=None):
    """Primer hueco libre de `width` mm sobre el riel, buscando desde el extremo derecho. None si no entra."""
    band = max(RAIL_BAND_MM, (height or 0) / 2)
    lo, hi = rail["y"] - band, rail["y"] + band
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
    # 4) Bloque de distribución cuando algún equipo supera la corriente de los peines (corrientes elevadas).
    comb_limit = max((c["corrienteA"] for c in catalog["combs"] if c.get("corrienteA") and "S200" in c.get("compatibleCon", [])), default=None)  # sólo peines de la línea S200: un peine de S800 (250 A) no sirve para S200
    amps = [(a, d["tag"]) for d in devices if (a := _in_amps(d)) is not None]
    heavy = [(a, tag) for a, tag in amps if comb_limit is not None and a > comb_limit]
    if heavy:
        need = max(a for a, _ in heavy)
        usable = sorted((b for b in catalog.get("distributionBlocks", []) if b.get("corrienteA") and b["corrienteA"] >= need),
                        key=lambda b: (b["corrienteA"], b.get("anchoMm") is None))
        item = {"type": "distribution_block", "auto": True, "provisional": True, "needsConfirmation": True, "decision": None, "devices": [tag for _, tag in heavy], "needA": need}
        if not usable:
            # Sin bloque que alcance: barra de cobre del catálogo (distributionBars) si su corriente alcanza; el usuario confirma o descarta.
            bars = sorted((b for b in catalog.get("distributionBars", []) if b.get("corrienteA") and b["corrienteA"] >= need), key=lambda b: b["corrienteA"])
            if not bars:
                item.update(catalogId=None, label="Barra de distribución", placed=False,
                            note=f"el catálogo no tiene bloque ni barra de {need:g} A o más: dimensionar la barra según IEC 61439 o tabla del fabricante")
            else:
                bar = bars[0]
                fw, fh = project["enclosure"]["functional"]["width"], project["enclosure"]["functional"]["height"]
                width, height = min(bar["largoMm"], fw - 2 * BAR_MARGIN_MM), BAR_FACE_MM
                y = BAR_MARGIN_MM
                if any(d["y"] < y + height + 10 and d["x"] < BAR_MARGIN_MM + width and BAR_MARGIN_MM < d["x"] + d["w"] for d in devices):
                    y = fh - BAR_MARGIN_MM - height  # el borde inferior está ocupado: va arriba
                item.update(type="copper_busbar", catalogId=bar["id"], corrienteA=bar["corrienteA"], label=f"{bar['orderCode']} {bar['corrienteA']:g} A", x=BAR_MARGIN_MM, y=y, w=width, h=height, placed=True,
                            note=("barra de cobre propuesta: confirmar o descartar. " + ("Se acortó a la placa; el catálogo no dice que se corte a medida. " if width < bar["largoMm"] else "")
                                  + bar.get("status", "")))
        else:
            block = usable[0]
            width, height = block.get("anchoMm"), block.get("alturaFrenteMm")
            item.update(catalogId=block["id"], corrienteA=block["corrienteA"], label=f"{block.get('tipo', block['id'])} {block['corrienteA']:g} A")
            x = _free_x(devices, rails[0], width, height) if rails and width and height else None
            if x is None:
                item.update(placed=False, note="sin lugar en el riel o sin medidas de frente en el catálogo")
            else:
                item.update(placed=True, x=x, y=rails[0]["y"] - height / 2, w=width, h=height)
        out.append(item)
    return out


def complete(project, catalog=None):
    """Reemplaza las propuestas anteriores (auto) y conserva los accesorios cargados a mano."""
    manual = [a for a in project.get("accessories", []) if not a.get("auto")]
    # Las decisiones del usuario (confirmar/descartar una propuesta) se conservan al recalcular.
    key = lambda a: (a.get("type"), tuple(a.get("devices", [])))
    decided = {key(a): a["decision"] for a in project.get("accessories", []) if a.get("auto") and a.get("decision")}
    new = propose(project, catalog)
    for a in new:
        if a.get("needsConfirmation") and key(a) in decided:
            a["decision"] = decided[key(a)]
    project["accessories"] = manual + new
    return project
