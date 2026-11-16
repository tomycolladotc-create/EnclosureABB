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
HOLDER_ZONE_MM = 14.0  # portaetiqueta bajo cada equipo
TAG_ZONE_MM = 30.0  # franja libre sobre los equipos para el texto de la etiqueta (criterio de dibujo)
COMB_FACE_FALLBACK_MM = 18.0  # sin altura en el catálogo: valor esquemático, marcado en el dibujo como provisorio
BAR_FACE_MM = 20.0  # cara de la barra AA8010 (20x5 mm)


def load_accessory_catalog(path=CATALOG_FILE):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _in_amps(device):
    try:
        return float(str(device.get("marking", {}).get("In", "")).replace(",", "."))
    except ValueError:
        return None


def _poles(d):
    """Polos del equipo: el dato cargado, o el que dice la carcasa (1pn = 1P+N = 2 polos; 2p/3p/4p). None si no se puede saber."""
    if d.get("poles"):
        return d["poles"]
    m = re.search(r"\.(1pn|[234]p)\.", d.get("shell", ""))
    return None if not m else 2 if m.group(1) == "1pn" else int(m.group(1)[0])


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


def _describe(item, catalog):
    """Datos para el cómputo de materiales (bom.py): categoría, descripción, código y cantidad. El dibujo NO lleva estos textos."""
    t = item["type"]
    by = lambda key: next((x for x in catalog.get(key, []) if x["id"] == item.get("catalogId")), {})
    if t == "pe_terminal":
        pe = by("earthTerminals")
        item.update(bomCategory="Borne PE", orderCode=pe.get("orderCode"), quantity=item.get("count", 1),
                    description=f"Borne de tierra {pe.get('tipo', '')} {pe.get('seccionMm2', '')} mm² para riel DIN ({pe.get('marca', '')})".replace("  ", " "))
    elif t == "terminal_cover":
        item.update(bomCategory="Cubrebornes", orderCode=None, quantity=1, description="Cubrebornes transparente (barrera aislante); código por definir")
    elif t == "comb":
        comb = by("combs")
        item.update(bomCategory="Peine", quantity=1, orderCode=item.get("orderCode") or comb.get("orderCode"),
                    description=f"Peine de conexión {comb.get('familia', '')} para {item.get('poleCount', '?')} polos (paso {item.get('pitchMm', 17.5)} mm), equipos: {', '.join(item.get('devices', []))}".replace("  ", " "))
    elif t == "distribution_block":
        blk = by("distributionBlocks")
        item.update(bomCategory="Bloque de distribución", quantity=1, orderCode=blk.get("orderCode"), description=f"Bloque de distribución {blk.get('tipo', '')} {blk.get('corrienteA', '')} A ({blk.get('marca', '')})".replace("  ", " "))
    elif t == "copper_busbar":
        bar = by("distributionBars")
        item.update(bomCategory="Barra de cobre", quantity=1, orderCode=bar.get("orderCode"), description=f"Barra de distribución {bar.get('tipo', '')} {bar.get('corrienteA', '')} A; soportes {bar.get('soportes', {}).get('orderCode', 'por definir')} x{bar.get('soportes', {}).get('cantidad', '?')}")
    elif t == "wiring_duct":
        item.update(bomCategory="Canaleta", quantity=1,
                    description=f"Canaleta ranurada {item['h']:g}x{item['depthMm']:g} mm, gris RAL 7035, ranura {item['slot']}; largo a cortar {item['lengthMm']:g} mm (tira de 2000 mm)")


def _load_rules():
    return json.loads((ROOT / "datos" / "reglas_layout.json").read_text(encoding="utf-8"))


def _overlap_x(a, b):
    return a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"]


def _propose_ducts(project, catalog, rails, devices, placed_acc):
    """Canaletas horizontales en el hueco libre arriba y abajo de cada fila de riel (compartida si dos filas la rodean).
    Criterios en datos/reglas_layout.json (propuesta de diseño); secciones y códigos de datos/accesorios_abb.json (catálogo ABB)."""
    spec = catalog.get("wiringDucts")
    if not spec or not rails:
        return []
    rules = _load_rules()
    clear, max_w, pref_h, edge = rules.get("ductClearanceMm", 5), rules.get("ductMaxWidthMm", 60), rules.get("ductPreferredDepthMm", 40), rules.get("ductEdgeMm", 15)
    slot = rules.get("ductSlot", "8x12")
    fh = project["enclosure"]["functional"]["height"]
    boxes = [{"x": d["x"], "y": d["y"], "w": d["w"], "h": d["h"], "tag": d.get("tag"), "up": TAG_ZONE_MM, "down": HOLDER_ZONE_MM} for d in devices]
    boxes += [{"x": a["x"], "y": a["y"], "w": a["w"], "h": a["h"], "tag": None, "devs": a.get("devices"), "up": TAG_ZONE_MM if a["type"] == "comb" else 0, "down": 0} for a in placed_acc
              if a.get("placed", True) and a.get("x") is not None and a.get("w") and a.get("h")]
    lanes = {}
    for rail in rails:
        span = {"x": rail["x"], "w": rail["length"]}
        row = [b for b in boxes if _overlap_x(b, span) and b["y"] <= rail["y"] <= b["y"] + b["h"]]
        tags = {b["tag"] for b in row if b["tag"]}
        row += [b for b in boxes if b.get("devs") and set(b["devs"]) & tags and b not in row]  # el peine apoyado arriba es parte de la fila
        if not row:
            continue
        lo = min(b["y"] - b.get("down", 0) for b in row)  # bajo los equipos va el portaetiqueta
        hi = max(b["y"] + b["h"] + b.get("up", 0) for b in row)  # sobre los equipos (y su peine) va el texto de la etiqueta
        others = [b for b in boxes if b not in row and _overlap_x(b, span)]
        up = min([b["y"] - b.get("down", 0) for b in others if b["y"] >= hi - TAG_ZONE_MM - 1e-6], default=fh - edge)
        down = max([b["y"] + b["h"] + b.get("up", 0) for b in others if b["y"] + b["h"] <= lo + HOLDER_ZONE_MM + 1e-6], default=edge)
        for a, b in ((hi, min(up, fh - edge)), (max(down, edge), lo)):
            key = (round(a), round(b))
            cur = lanes.setdefault(key, [a, b, rail["x"], rail["x"] + rail["length"]])
            cur[2], cur[3] = min(cur[2], rail["x"]), max(cur[3], rail["x"] + rail["length"])
    out = []
    for (a, b, x0, x1) in sorted(lanes.values()):
        gap = b - a - 2 * clear
        fits = [s for s in spec["sections"] if s["widthMm"] <= gap and s["widthMm"] <= max_w]
        if not fits:
            continue
        sec = max(fits, key=lambda s: (s["widthMm"], -abs(s["heightMm"] - pref_h)))
        code = sec["code8x12"] if slot == "8x12" else sec["code4x6"]
        out.append({"type": "wiring_duct", "auto": True, "provisional": True, "catalogId": "wiringDucts", "orderCode": code,
                    "label": f"Canaleta {sec['widthMm']}x{sec['heightMm']} {code}", "x": round(x0, 2), "y": round(a + clear + (gap - sec["widthMm"]) / 2, 2),
                    "w": round(x1 - x0, 2), "h": sec["widthMm"], "depthMm": sec["heightMm"], "slot": slot, "lengthMm": round(x1 - x0, 2),
                    "note": "canaleta propuesta; sección no dimensionada por llenado de cables"})
    return out


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
        poles = {_poles(d) for d in g}
        comb = combs["abb-ps3-12"] if poles == {3} else combs["abb-ps2"] if poles == {2} else combs["abb-ps4"] if poles == {4} else None
        # El peine se apoya sobre la cara superior de los equipos; la altura visible sale del catálogo (alturaMm, o ancho si falta): la cara de frente no está cotada.
        face = (comb.get("alturaMm") or comb.get("anchoMm") or COMB_FACE_FALLBACK_MM) if comb else COMB_FACE_FALLBACK_MM
        span = g[-1]["x"] + g[-1]["w"] - g[0]["x"]
        out.append({"type": "comb", "auto": True, "catalogId": comb["id"] if comb else None, "corrienteA": comb.get("corrienteA") if comb else None,
                    "orderCode": comb.get("orderCode") if comb else None,
                    "devices": [d["tag"] for d in g], "x": g[0]["x"], "y": g[0]["y"] + g[0]["h"], "w": span, "h": face,
                    "pitchMm": (comb or {}).get("pasoMm") or 17.5, "poleCount": round(span / ((comb or {}).get("pasoMm") or 17.5)),
                    "label": "Peine " + (comb.get("orderCode") or "") if comb else "Peine", "provisional": True,
                    "note": (None if comb else "mezcla de polos: sin peine definido") if comb else "mezcla de polos: sin peine definido"})
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
            taken = devices + [a for a in out if a.get("placed") and a.get("x") is not None and a.get("w")]  # los bornes PE ya puestos también ocupan el riel
            x = _free_x(taken, rails[0], width, height) if rails and width and height else None
            if x is None:
                item.update(placed=False, note="sin lugar en el riel o sin medidas de frente en el catálogo")
            else:
                item.update(placed=True, x=x, y=rails[0]["y"] - height / 2, w=width, h=height)
        out.append(item)
    out.extend(_propose_ducts(project, catalog, rails, devices, out))
    for item in out:
        _describe(item, catalog)
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
