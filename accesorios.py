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
# Criterios de armado: datos/reglas_layout.json (contiguousGapMm, railTerminalBandMm, busbarMarginMm, combFaceFallbackMm, labelHolderMm).


def load_accessory_catalog(path=CATALOG_FILE):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _in_amps(device):
    """Corriente nominal: la del frente (marking.In) o, si falta, la del modelo (p. ej. E2.2N 2000, OT100F4, T4S 320 ... 320A)."""
    try:
        return float(str(device.get("marking", {}).get("In", "")).replace(",", "."))
    except ValueError:
        from auditoria import rated_current
        return rated_current(device)


def pe_input_max_mm2(terminal):
    """Sección máxima de entrada de la bornera PE (de su ficha: «10…35 mm²»). None si la ficha no la trae."""
    text = str(((terminal or {}).get("entradas") or {}).get("seccion") or "")
    nums = [float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", text)]
    return max(nums) if nums else None


def default_signals(project, catalog=None):
    """Testigos de fase que se proponen cuando el usuario los agrega a mano: una luz por fase del equipo de entrada
    (3 o 4 polos → R-S-T; 2 polos → una luz en la fase). Tensión y fusible de signalDefaults (accesorios_abb.json).
    Única fuente de esta regla (la interfaz la pide a /api/signals-default). Error si no se sabe cuántos polos tiene la entrada."""
    from auditoria import main_device
    catalog = catalog or load_accessory_catalog()
    defaults = catalog.get("signalDefaults", {})
    main = main_device(project)
    if not main:
        raise ValueError("No se encontró el equipo de entrada del tablero: no se puede saber cuántas fases tiene")
    poles = main.get("poles")
    if not poles:
        found = re.search(r"\.(\d)p", str(main.get("shell", "")))
        poles = int(found.group(1)) if found else None
    if not poles:
        raise ValueError(f"No se sabe cuántos polos tiene {main.get('tag')}: cargalos para proponer los testigos")
    phases = defaults.get("phasesByPoles", {}).get(str(min(int(poles), 4)))
    if not phases:
        raise ValueError(f"signalDefaults.phasesByPoles no define {poles} polos")
    return {"pilotLights": [{"label": p, "function": "presencia de tensión", "voltage": defaults["voltage"]} for p in phases],
            "fuses": {"count": len(phases), "type": "tabaquera", "rating": f"{defaults['fuseA']:g} A"}, "origin": "agregado en el editor"}


def _abb(item):
    """Sólo productos ABB (o de la ex ABB Entrelec): el catálogo guarda otras marcas como referencia, nunca para proponer."""
    return "ABB" in str(item.get("marca", "ABB"))


def _poles(d):
    """Polos del equipo: el dato cargado, o el que dice la carcasa (1pn = 1P+N = 2 polos; 2p/3p/4p). None si no se puede saber."""
    if d.get("poles"):
        return d["poles"]
    m = re.search(r"\.(1pn|[234]p)\.", d.get("shell", ""))
    return None if not m else 2 if m.group(1) == "1pn" else int(m.group(1)[0])


def _free_x(devices, rail, width, height=None):
    """Primer hueco libre de `width` mm sobre el riel, buscando desde el extremo derecho. None si no entra."""
    band = max(_load_rules()["railTerminalBandMm"], (height or 0) / 2)
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
    if t == "pe_terminal" and item.get("style") == "repartidor":
        pe = by("earthTerminals")
        stop = pe.get("tope") or {}
        item.update(bomCategory="Bornera de tierra (PE)", orderCode=pe.get("orderCode"), quantity=item.get("blocks", 1),
                    description=f"Repartidor unipolar {pe.get('tipo')} {pe.get('corrienteA')} A como bornera equipotencial PE: {pe['entradas']['cantidad']} entrada {pe['entradas']['seccion']} + {pe['salidas']['cantidad']} salidas {pe['salidas']['seccion']}, marcador PE ({pe.get('marca')})",
                    bomExtra=[{"bomCategory": "Bornera de tierra (PE)", "orderCode": stop.get("orderCode"), "quantity": 2,
                               "description": f"Tope de fin de bornera {stop.get('tipo')} ({stop.get('anchoMm')} mm), uno en cada punta"}] if stop else [])
    elif t == "pe_terminal":
        pe = by("earthTerminals")
        item.update(bomCategory="Borne PE", orderCode=pe.get("orderCode"), quantity=item.get("count", 1),
                    description=f"Borne de tierra {pe.get('tipo', '')} {pe.get('seccionMm2', '')} mm² para riel DIN ({pe.get('marca', '')})".replace("  ", " "))
    elif t == "terminal_cover":
        item.update(bomCategory="Cubrebornes", orderCode=None, quantity=1, description="Cubrebornes transparente (barrera aislante); código por definir")
    elif t == "comb":
        comb = by("combs")
        pins = comb.get("modulos")  # pines por pieza (PS2/12 = 12): un grupo más largo lleva más de una pieza
        item.update(bomCategory="Peine", quantity=-(-int(item.get("poleCount") or 1) // pins) if pins else 1, orderCode=item.get("orderCode") or comb.get("orderCode"),
                    description=f"Peine de conexión {comb.get('familia', '')}/{pins} ({pins} pines por pieza) para {item.get('poleCount', '?')} polos (paso {item.get('pitchMm', 17.5)} mm), equipos: {', '.join(item.get('devices', []))}".replace("  ", " "))
    elif t == "distribution_block":
        blk = by("distributionBlocks")
        if blk:
            item.update(bomCategory="Bloque de distribución", quantity=1, orderCode=blk.get("orderCode"), description=f"Bloque de distribución {blk.get('tipo', '')} {blk.get('corrienteA', '')} A ({blk.get('marca', '')})".replace("  ", " "))
        else:  # sin pieza en el catálogo: igual se pide, con la corriente que tiene que soportar (no queda un renglón vacío)
            item.update(bomCategory="Barra de distribución", quantity=1, orderCode=None,
                        description=f"Barra/juego de barras de distribución de al menos {item.get('needA', 0):g} A (lo que entra por el general), a dimensionar")
    elif t == "copper_busbar":
        bar = by("distributionBars")
        item.update(bomCategory="Barra de cobre", quantity=1, orderCode=bar.get("orderCode"), description=f"Barra de distribución {bar.get('tipo', '')} {bar.get('corrienteA', '')} A; soportes {bar.get('soportes', {}).get('orderCode', 'por definir')} x{bar.get('soportes', {}).get('cantidad', '?')}")
    elif t == "signal_fuses":
        holder = by("signalFuseHolders")
        fuse = next((x for x in catalog.get("signalFuses", []) if x["id"] == item.get("fuseCatalogId")), {})
        phases = "-".join(p for p in item.get("phases", []) if p)
        item.update(bomCategory="Señalización", orderCode=holder.get("orderCode"), quantity=item.get("count", 1),
                    description=f"Portafusible {holder.get('tipo', '')} 1P 10x38 (tabaquera) para los testigos de fase {phases} ({holder.get('marca', 'ABB')})",
                    bomExtra=[{"bomCategory": "Señalización", "orderCode": fuse.get("orderCode"), "quantity": item.get("count", 1),
                               "description": f"Fusible {fuse.get('tipo', '10x38')} {fuse.get('descripcion', '')} para los testigos" + (f" · {fuse['status']}" if fuse.get("status") else "")}])
    elif t == "pe_bar":
        item.update(quantity=1)
    elif t == "wiring_duct":
        item.update(bomCategory="Canaleta", quantity=1,
                    description=f"Canaleta ranurada {item.get('sectionMm', item['h']):g}x{item['depthMm']:g} mm, gris RAL 7035, ranura {item['slot']}; largo a cortar {item['lengthMm']:g} mm (tira de 2000 mm)")


def _manual_duct(item, catalog):
    """Canaleta dibujada por el usuario: sección estándar del catálogo ABB (ancho visible x profundidad), horizontal o vertical."""
    spec = catalog.get("wiringDucts") or {}
    vertical = item.get("orientation") == "v"
    width = item.get("sectionMm") or (item["w"] if vertical else item["h"])
    sec = next((x for x in spec.get("sections", []) if x["widthMm"] == width and x["heightMm"] == item.get("depthMm")), None) \
        or next((x for x in spec.get("sections", []) if x["widthMm"] == width), None)
    if sec is None:
        raise ValueError(f"Sección de canaleta {width} mm no está en el catálogo ABB")
    slot = item.get("slot") or _load_rules().get("ductSlot", "8x12")
    length = item["h"] if vertical else item["w"]
    code = sec["code8x12"] if slot == "8x12" else sec["code4x6"]
    if vertical:
        item["w"] = sec["widthMm"]
    else:
        item["h"] = sec["widthMm"]
    item.update(auto=False, manual=True, provisional=False, catalogId="wiringDucts", sectionMm=sec["widthMm"], depthMm=sec["heightMm"],
                slot=slot, orderCode=code, lengthMm=round(length, 2), label=f"Canaleta {sec['widthMm']}x{sec['heightMm']} {code}")
    item.pop("note", None)
    _describe(item, catalog)


def _load_rules():
    return json.loads((ROOT / "datos" / "reglas_layout.json").read_text(encoding="utf-8"))


def _overlap_x(a, b):
    return a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"]


def _propose_ducts(project, catalog, rails, devices, placed_acc):
    """Canaletas automáticas con el criterio de un armador (ejemplo de Thomas, 2026-11-17):
    - una vertical a cada lado de la placa, de arriba abajo, si hay lugar entre el borde y los equipos/rieles;
    - horizontales arriba y abajo de cada fila de equipos (cajas moldeadas, seccionadores o DIN), de vertical a vertical;
      entre dos filas cercanas la canaleta es compartida; si el hueco es grande, una pegada a cada fila;
    - siempre la más ancha del catálogo ABB que entra (hasta ductMaxWidthMm), profundidad lo más cercana a ductPreferredDepthMm.
    Criterios en datos/reglas_layout.json (propuesta de diseño); secciones y códigos de datos/accesorios_abb.json."""
    spec = catalog.get("wiringDucts")
    if not spec:
        return []
    rules = _load_rules()
    clear, max_w, pref_h, edge = rules.get("ductClearanceMm", 5), rules.get("ductMaxWidthMm", 80), rules.get("ductPreferredDepthMm", 40), rules.get("ductEdgeMm", 15)
    side_max = rules.get("ductSideMaxWidthMm", max_w)
    slot = rules.get("ductSlot", "8x12")
    fw, fh = project["enclosure"]["functional"]["width"], project["enclosure"]["functional"]["height"]
    holder = rules["labelHolderMm"]  # portaetiqueta bajo cada equipo (la misma regla que usan el armado y la auditoría)
    boxes = [{"x": d["x"], "y": d["y"] - holder, "w": d["w"], "h": d["h"] + holder} for d in devices]
    boxes += [{"x": a["x"], "y": a["y"], "w": a["w"], "h": a["h"]} for a in placed_acc
              if a.get("placed", True) and a.get("x") is not None and a.get("w") and a.get("h")]
    if not boxes:
        return []

    def pick(gap, limit):
        fits = [x for x in spec["sections"] if rules.get("ductMinWidthMm", 25) <= x["widthMm"] <= min(gap, limit)]
        return max(fits, key=lambda x: (x["widthMm"], -abs(x["heightMm"] - pref_h))) if fits else None

    def duct(sec, x, y, w, h, orientation):
        code = sec["code8x12"] if slot == "8x12" else sec["code4x6"]
        length = h if orientation == "v" else w
        return {"type": "wiring_duct", "auto": True, "provisional": True, "catalogId": "wiringDucts", "orderCode": code, "orientation": orientation,
                "label": f"Canaleta {sec['widthMm']}x{sec['heightMm']} {code}", "x": round(x, 2), "y": round(y, 2), "w": round(w, 2), "h": round(h, 2),
                "sectionMm": sec["widthMm"], "depthMm": sec["heightMm"], "slot": slot, "lengthMm": round(length, 2),
                "note": "canaleta propuesta; sección no dimensionada por llenado de cables"}

    out = []
    # 1) Verticales laterales: el hueco entre el borde (menos ductEdgeMm) y lo más cercano (equipos, accesorios, rieles).
    spans = boxes + [{"x": r["x"], "w": r["length"]} for r in rails]
    left_free = min(b["x"] for b in spans) - edge - clear
    right_free = fw - edge - max(b["x"] + b["w"] for b in spans) - clear
    x0, x1 = edge, fw - edge  # tramo horizontal disponible
    sec = pick(left_free, side_max)
    if sec:
        out.append(duct(sec, edge, edge, sec["widthMm"], fh - 2 * edge, "v"))
        x0 = edge + sec["widthMm"]
    sec = pick(right_free, side_max)
    if sec:
        out.append(duct(sec, fw - edge - sec["widthMm"], edge, sec["widthMm"], fh - 2 * edge, "v"))
        x1 = fw - edge - sec["widthMm"]

    # 2) Filas de equipos: cajas que se solapan en altura forman una fila.
    rows = []
    for b in sorted(boxes, key=lambda b: b["y"]):
        if rows and b["y"] < rows[-1][1] - 1e-6:
            rows[-1][1] = max(rows[-1][1], b["y"] + b["h"])
        else:
            rows.append([b["y"], b["y"] + b["h"]])
    # 3) Huecos: bajo la primera fila, entre filas y sobre la última. Cada fila lleva canaleta arriba y abajo.
    gaps = [(edge, rows[0][0], "below")] + [(rows[k][1], rows[k + 1][0], "between") for k in range(len(rows) - 1)] + [(rows[-1][1], fh - edge, "above")]
    for lo, hi, kind in gaps:
        free = hi - lo - 2 * clear
        sec = pick(free, max_w)
        if not sec:
            continue
        w = sec["widthMm"]
        if kind == "between" and free >= 2 * w + clear + rules.get("ductMinFreeBetweenMm", 50):
            # hueco grande: una canaleta pegada a cada fila
            out.append(duct(sec, x0, hi - clear - w, x1 - x0, w, "h"))
            out.append(duct(sec, x0, lo + clear, x1 - x0, w, "h"))
        elif kind == "below":
            out.append(duct(sec, x0, hi - clear - w, x1 - x0, w, "h"))  # pegada bajo la fila de abajo
        elif kind == "above":
            out.append(duct(sec, x0, lo + clear, x1 - x0, w, "h"))  # pegada sobre la fila de arriba
        else:
            out.append(duct(sec, x0, lo + clear + (free - w) / 2, x1 - x0, w, "h"))  # compartida, centrada
    return out


def propose(project, catalog=None):
    """Devuelve la lista completa de accesorios propuestos para `project`."""
    catalog = catalog or load_accessory_catalog()
    rules = _load_rules()
    devices = [d for d in project.get("devices", []) if d.get("shell")]
    rails = project.get("enclosure", {}).get("mountingLayout", {}).get("dinRails", [])
    out = []

    # 1) Bornes de puesta a tierra: uno por circuito de salida (QF). Simplificación declarada.
    circuits = [d for d in project.get("devices", []) if str(d.get("tag", "")).startswith("QF")]
    pe_id = _load_rules().get("peTerminalId", "entrelec-m4-6p")
    pe = next((t for t in catalog["earthTerminals"] if t["id"] == pe_id), None) or next(t for t in catalog["earthTerminals"] if t["id"] == "entrelec-m4-6p")
    if circuits:
        if pe.get("estilo") == "repartidor":
            # Bornera equipotencial: bloques repartidores agrupados (cada uno con N salidas) y un tope en cada punta.
            outs = pe["salidas"]["cantidad"]
            blocks = -(-len(circuits) // outs)
            stop = (pe.get("tope") or {}).get("anchoMm", 0)
            width, height = blocks * pe["anchoMm"] + 2 * stop, pe["altoFrenteMm"]
            item = {"type": "pe_terminal", "style": "repartidor", "auto": True, "catalogId": pe["id"], "count": blocks * outs, "blocks": blocks,
                    "blockW": pe["anchoMm"], "stopW": stop, "outputs": outs, "inputs": pe["entradas"]["cantidad"], "w": width, "h": height,
                    "label": f"Bornera PE {pe['tipo']} x{blocks}", "provisional": True}
        else:
            width, height = len(circuits) * pe["pasoMm"], pe["alturaMm"]
            item = {"type": "pe_terminal", "auto": True, "catalogId": pe["id"], "count": len(circuits), "w": width, "h": height,
                    "label": f"PE x{len(circuits)}", "provisional": True}
        spot = next(((x, r) for r in rails if (x := _free_x(devices, r, width)) is not None), None)  # primer riel con hueco
        if spot is None:
            item.update(placed=False)
        else:
            item.update(placed=True, x=spot[0], y=spot[1]["y"] - height / 2)
        out.append(item)

    # 1a) Fusibles de los testigos de fase (luces en la puerta): un portafusible por luz, sobre el riel (pedido de Thomas 2026-11-19).
    lights = (project.get("signals") or {}).get("pilotLights") or []
    holder = next(iter(catalog.get("signalFuseHolders", [])), None)
    if lights and holder:
        n = len(lights)
        width, height = n * holder["anchoMm"], holder["altoMm"]
        fuse = next(iter(catalog.get("signalFuses", [])), {})
        item = {"type": "signal_fuses", "auto": True, "catalogId": holder["id"], "fuseCatalogId": fuse.get("id"), "count": n, "poleW": holder["anchoMm"],
                "phases": [l.get("label") for l in lights], "w": width, "h": height, "label": f"Fusibles testigos x{n}", "provisional": False}
        taken = devices + [a for a in out if a.get("placed") and a.get("x") is not None and a.get("w")]
        spot = next(((x, r) for r in rails if (x := _free_x(taken, r, width, height)) is not None), None)
        if spot is None:
            item.update(placed=False, note="no entra en el riel")
        else:
            item.update(placed=True, x=spot[0], y=spot[1]["y"] - height / 2)
        out.append(item)

    # 1b) PE de alimentación más grueso que lo que admite la bornera: hace falta barra de tierra (lección 2026-11-19: TGBT con 6×PE150 y TS con PE70/95).
    feeder = project.get("feeder") or {}
    pe_max = pe_input_max_mm2(pe)
    if circuits and feeder.get("peMm2") and pe_max and feeder["peMm2"] > pe_max:
        n = feeder.get("peParallel") or 1
        out.append({"type": "pe_bar", "auto": True, "provisional": True, "catalogId": None, "placed": False, "orderCode": None,
                    "label": "Barra de tierra PE", "bomCategory": "Barra de tierra (PE)",
                    "description": f"Barra de cobre de tierra (PE) para recibir el PE de alimentación {(str(n) + '×') if n > 1 else ''}{feeder['peMm2']:g} mm² y repartir a los circuitos",
                    "note": f"la bornera {pe.get('tipo')} admite hasta {pe_max:g} mm² de entrada: dimensionar la barra según IEC 61439-1 / AEA 90364 (no hay barra de tierra en el catálogo)"})

    # 2) Cubrebornes transparentes (barrera aislante): uno general; sin geometría hasta tener el CAD.
    if devices:
        out.append({"type": "terminal_cover", "auto": True, "catalogId": None, "label": "Cubrebornes", "provisional": True})

    # 3) Peines entre equipos S200 contiguos, mismo riel y misma serie.
    combs = {c["id"]: c for c in catalog["combs"]}
    s200 = sorted((d for d in devices if "s200" in d["shell"]), key=lambda d: (round(d["y"]), d["x"]))
    group = []
    groups = []
    for d in s200:
        if group and abs(group[-1]["y"] - d["y"]) <= 0.5 and 0 <= d["x"] - (group[-1]["x"] + group[-1]["w"]) <= rules["contiguousGapMm"] and _poles(d) == _poles(group[-1]):  # un peine sólo une equipos con los mismos polos
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
        face = (comb.get("alturaMm") or comb.get("anchoMm") or rules["combFaceFallbackMm"]) if comb else rules["combFaceFallbackMm"]
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
    from auditoria import main_device, rated_current
    entry = main_device(project)
    feed = rated_current(entry) if entry else None
    if heavy:
        # La barra/bloque reparte lo que entra por el general: se dimensiona por la entrada, no por la salida más grande
        # (lección 2026-11-19: en el TGBT de 2000 A se había propuesto una barra de 320 A).
        need = max([a for a, _ in heavy] + ([feed] if feed else []))
        # sólo bloques con medidas de frente (se pueden dibujar y ubicar); si no hay, barra de cobre del catálogo
        usable = sorted((b for b in catalog.get("distributionBlocks", []) if _abb(b) and b.get("corrienteA") and b["corrienteA"] >= need and b.get("anchoMm") and b.get("alturaFrenteMm")),
                        key=lambda b: b["corrienteA"])
        item = {"type": "distribution_block", "auto": True, "provisional": True, "needsConfirmation": True, "decision": None, "devices": [tag for _, tag in heavy], "needA": need}
        if not usable:
            # Sin bloque que alcance: barra de cobre del catálogo (distributionBars) si su corriente alcanza; el usuario confirma o descarta.
            bars = sorted((b for b in catalog.get("distributionBars", []) if _abb(b) and b.get("uso", "fase") == "fase" and b.get("corrienteA") and b["corrienteA"] >= need), key=lambda b: b["corrienteA"])
            if not bars:
                item.update(catalogId=None, label="Barra de distribución", placed=False,
                            note=f"el catálogo no tiene bloque ni barra de {need:g} A o más: dimensionar la barra según IEC 61439 o tabla del fabricante")
            else:
                bar = bars[0]
                fw, fh = project["enclosure"]["functional"]["width"], project["enclosure"]["functional"]["height"]
                margin = rules["busbarMarginMm"]
                face = float(re.match(r"(\d+(?:[.,]\d+)?)", str(bar.get("seccion", ""))).group(1).replace(",", "."))  # cara de la barra: «20x5 mm» → 20
                width, height = min(bar["largoMm"], fw - 2 * margin), face
                y = margin
                if any(d["y"] < y + height + 10 and d["x"] < margin + width and margin < d["x"] + d["w"] for d in devices):
                    y = fh - margin - height  # el borde inferior está ocupado: va arriba
                pitch = re.search(r"cada (\d+) mm", str(bar.get("paso", "")))
                item.update(type="copper_busbar", catalogId=bar["id"], corrienteA=bar["corrienteA"], holePitchMm=float(pitch.group(1)) if pitch else None, supports=(bar.get("soportes") or {}).get("cantidad"), label=f"{bar['orderCode']} {bar['corrienteA']:g} A", x=margin, y=y, w=width, h=height, placed=True,
                            note=("barra de cobre propuesta: confirmar o descartar. " + ("Se acortó a la placa; el catálogo no dice que se corte a medida. " if width < bar["largoMm"] else "")
                                  + bar.get("status", "")))
        else:
            block = usable[0]
            width, height = block.get("anchoMm"), block.get("alturaFrenteMm")
            item.update(catalogId=block["id"], corrienteA=block["corrienteA"], label=f"{block.get('tipo', block['id'])} {block['corrienteA']:g} A",
                        poles=block.get("polos") if isinstance(block.get("polos"), int) else None, inputsPerPole=block.get("entradasPorPolo"), outputsPerPole=block.get("salidasPorPolo"))
            taken = devices + [a for a in out if a.get("placed") and a.get("x") is not None and a.get("w")]  # los bornes PE ya puestos también ocupan el riel
            spot = next(((x, r) for r in rails if (x := _free_x(taken, r, width, height)) is not None), None) if width and height else None
            if spot is None:
                item.update(placed=False, note="sin lugar en el riel o sin medidas de frente en el catálogo")
            else:
                item.update(placed=True, x=spot[0], y=spot[1]["y"] - height / 2, w=width, h=height)
        out.append(item)
    if project.get("ductMode") != "manual":  # en modo manual las canaletas las dibuja el usuario
        out.extend(_propose_ducts(project, catalog, rails, devices, out))
    for item in out:
        _describe(item, catalog)
    return out


def complete(project, catalog=None, auto_confirm=False):
    """Reemplaza las propuestas anteriores (auto) y conserva los accesorios cargados a mano."""
    catalog = catalog or load_accessory_catalog()
    manual = [a for a in project.get("accessories", []) if not a.get("auto")]
    for a in manual:
        if a.get("type") == "wiring_duct":
            _manual_duct(a, catalog)
    # Las decisiones del usuario (confirmar/descartar una propuesta) se conservan al recalcular.
    key = lambda a: (a.get("type"), tuple(a.get("devices", [])))
    decided = {key(a): a["decision"] for a in project.get("accessories", []) if a.get("auto") and a.get("decision")}
    new = propose(project, catalog)
    for a in new:
        if a.get("needsConfirmation") and key(a) in decided:
            a["decision"] = decided[key(a)]
        elif auto_confirm and a.get("needsConfirmation"):
            a["decision"] = "confirmed"
    project["accessories"] = manual + new
    return project
