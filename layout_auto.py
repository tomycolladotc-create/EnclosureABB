"""Armado automático: elige el gabinete más chico que entra el contenido y acomoda los equipos.

- Los gabinetes candidatos salen de datos/catalogo_abb.json (enclosures); no hay medidas en el código.
- Los criterios de armado (márgenes, separaciones, largo de riel) están en datos/reglas_layout.json
  y son propuestas de diseño ajustables, NO datos de ABB.
- Orden de armado de arriba hacia abajo: seccionadores (QS) -> equipos de kit (XT/OT) -> equipos de riel DIN.
- Coordenadas del proyecto: origen abajo a la izquierda del área funcional, y hacia arriba.
"""
import copy
import json
from pathlib import Path

from accesorios import load_accessory_catalog

ROOT = Path(__file__).resolve().parent
RULES_FILE = ROOT / "datos" / "reglas_layout.json"
PE_RESERVE_FALLBACK_MM = 6.0


def load_rules(path=RULES_FILE):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _classify(devices, catalog, rules, main_tag=None):
    """Separa el equipo de entrada (main), los de kit/placa y los de riel, CONSERVANDO el orden del unifilar
    (lección 2026-11-19: ordenar por carcasa mezclaba los circuitos, p. ej. TSB-1.13 antes que TSB-1.1)."""
    shells = {s["id"]: s for s in catalog["deviceShells"]}
    din = {s["id"] for s in catalog["deviceShells"] if s.get("mounting") == "din"}
    main, kit, rail = [], [], []
    for d in devices:
        spec = shells.get(d.get("shell"), {})
        is_main = d.get("tag") == main_tag if main_tag else str(d.get("tag", "")).startswith(rules["mainTagPrefix"])
        if d.get("shell") in din or d.get("mounting") == "din":
            (rail.insert(0, d) if is_main else rail.append(d))  # el general de riel va primero (arriba a la izquierda)
        elif is_main:
            main.append(d)
        else:
            kit.append((d, spec))
    return main, kit, rail


def _wrap(items, width, gap):
    """Reparte (ancho) en filas sin pasar `width`. Devuelve lista de listas de índices o None si algún ítem no entra."""
    rows, cur, used = [], [], 0.0
    for i, w in enumerate(items):
        if w > width:
            return None
        add = w + (gap if cur else 0)
        if cur and used + add > width:
            rows.append(cur)
            cur, used = [], 0.0
            add = w
        cur.append(i)
        used += add
    if cur:
        rows.append(cur)
    return rows


def _pack_rail_rows(devs, length, col_gap, pe_reserve):
    """Reparte equipos de riel en filas de `length` mm: misma carcasa pegada (peine), distinta carcasa con separación. Deja lugar a los bornes PE en la última fila."""
    rows, cur, used = [], [], 0.0
    for d in devs:
        if d["w"] > length:
            return None
        add = d["w"] + (0 if not cur or cur[-1].get("shell") == d.get("shell") else col_gap)
        if cur and used + add > length:
            rows.append(cur)
            cur, used, add = [], 0.0, d["w"]
        cur.append(d)
        used += add
    rows.append(cur)
    if used + pe_reserve > length:
        rows.append([])
    return rows


def _place_row(row, rail, y_center, col_gap, placed):
    x, prev = rail["x"], None
    for d in row:
        x += 0 if prev is None or prev.get("shell") == d.get("shell") else col_gap
        placed[d["tag"]] = (round(x, 2), round(y_center - d["h"] / 2, 2))
        x += d["w"]
        prev = d


def _try(project, catalog, enc, rules, pe_reserve, extra_rows=0):
    fw, fh = enc["functional"]["width"], enc["functional"]["height"]
    margin, row_gap, col_gap = rules["margin"], rules["rowGap"], rules["colGap"]
    usable_w, usable_h = fw - 2 * margin, fh - 2 * margin
    from auditoria import main_device
    entry = main_device(project)
    main, kit, rail_devs = _classify(project["devices"], catalog, rules, entry["tag"] if entry else None)
    din_main = bool(entry) and bool(rail_devs) and rail_devs[0] is entry
    # Lugar para canaleta arriba de la primera fila y entre filas de cajas moldeadas (lección 2026-11-19).
    duct_band = rules.get("ductBandMm", 0)
    holder = rules.get("labelHolderMm", 14)
    if (main or kit) and enc["functional"]["depth"] < rules.get("minDepthForKitDevicesMm", 0):
        return None
    shells_by_id = {s["id"]: s for s in catalog["deviceShells"]}
    if any(shells_by_id.get(d.get("shell"), {}).get("floorStandingOnly") for d in project["devices"]) and "System pro E" not in str(enc.get("line", "")):
        return None  # Emax y equipos de bastidor abierto: sólo gabinete de piso
    placed, rails = {}, []
    cursor = 0.0  # distancia desde arriba del área funcional (sin margen)
    top_duct = max(0.0, rules.get("ductEdgeMm", 15) + duct_band - margin)  # canaleta sobre una primera fila de cajas (las de riel ya la traen en railRowGapMm)

    gap_rows = max(row_gap, holder + duct_band)  # entre filas de cajas: portaetiqueta + canaleta

    def row_block(devs, heights, gap):
        nonlocal cursor
        rows = _wrap([d["w"] for d in devs], usable_w, gap)
        if rows is None:
            return False
        if not placed:
            cursor += top_duct
        for idx in rows:
            row_h = max(heights[i] for i in idx)
            row_w = sum(devs[i]["w"] for i in idx) + gap * (len(idx) - 1)
            x = margin + (usable_w - row_w) / 2
            top = margin + cursor
            for i in idx:
                d = devs[i]
                placed[d["tag"]] = (round(x, 2), round(fh - top - row_h + (row_h - d["h"]) / 2, 2))
                x += d["w"] + gap
            cursor += row_h + gap_rows
        return True

    last_gap = row_gap  # separación ya sumada después de la última fila armada (el cursor la incluye)

    def kit_rows():
        nonlocal last_gap
        if main and not row_block(main, [d["h"] for d in main], col_gap):
            return False
        if kit:
            devs = [d for d, _ in kit]
            # La altura de módulo del kit (p. ej. PHDX: 200 mm) sólo rige en System pro E; en un gabinete con placa la caja se atornilla
            # a la placa y ocupa su propio alto (lección 2026-11-19: el TS4 salía de 1200 mm por usar 200 mm por fila).
            spe = "System pro E" in str(enc.get("line", ""))
            heights = [max(s.get("kitHeight") or 0, d["h"]) if rules.get("kitModuleHeightFromShell") and spe else d["h"] for d, s in kit]
            if not row_block(devs, heights, col_gap):
                return False
        if main or kit:
            last_gap = gap_rows
        return True

    bottom_limit = margin  # borde inferior permitido para lo que se arma de arriba hacia abajo
    tail_gap = row_gap  # separación que queda después de la última fila armada de arriba hacia abajo
    kd = enc.get("kdKit") if rail_devs else None
    if din_main and (main or kit) and kd:
        return None  # con kit KD las filas de riel quedan abajo: el general de riel no quedaría arriba
    if not rail_devs or kd or not din_main:
        if not kit_rows():
            return None
    if rail_devs:
        if kd:
            # Kit KD del gabinete: filas de riel fijas (185 mm de paso, largo = módulos x 17,5 mm); no se inventa otra posición.
            length, pitch = kd["modulesPerRow"] * kd["moduleMm"], kd["rowPitchMm"]
            rows = _pack_rail_rows(rail_devs, length, col_gap, pe_reserve)
            rows = rows + [[] for _ in range(extra_rows)] if rows is not None else None
            if rows is None or len(rows) > kd["rows"] or any(d["h"] > pitch for d in rail_devs) or length > fw:
                return None
            stack = len(rows) * pitch
            if stack > fh:
                return None
            # Pila de filas contiguas apoyada abajo. Arriba y abajo de la pila tiene que quedar lugar para una canaleta (entrada de cables):
            # lección 2026-11-19, el TSEP salía con 3 filas KD ocupando toda la placa, sin canaleta arriba ni abajo.
            band = rules.get("ductEdgeMm", 15) + duct_band
            base = max(margin, band)
            if base + stack + band > fh:
                return None
            bottom_limit = base + stack + row_gap
            for n, row in enumerate(rows, 1):
                y_center = base + (len(rows) - n) * pitch + pitch / 2
                rail = {"id": f"DIN-{n}", "type": f"Fila {n} del kit {kd['kit']}", "orderCode": None, "kdKit": kd["kit"], "fixed": True, "height": 35,
                        "x": round((fw - length) / 2, 2), "y": round(y_center, 2), "length": length}
                rails.append(rail)
                _place_row(row, rail, y_center, col_gap, placed)
        else:
            # Gabinete sin kit KD: riel más largo de railOptions que entra en el ancho útil, posición propuesta por el armado (no fijada por el gabinete).
            options = [o for o in enc.get("railOptions", []) if o["length"] <= usable_w]
            if options:
                template = copy.deepcopy(max(options, key=lambda o: o["length"]))
            elif enc.get("railOptions"):
                # El riel DIN se corta a medida (práctica habitual): el más corto del catálogo, cortado al ancho útil.
                template = copy.deepcopy(min(enc["railOptions"], key=lambda o: o["length"]))
                template.update(length=round(usable_w, 1), cutFromMm=template["length"])
            else:
                return None
            length = template["length"]
            rows = _pack_rail_rows(rail_devs, length, col_gap, pe_reserve)
            if rows is None:
                return None
            rows += [[] for _ in range(extra_rows)]  # fila libre para un bloque de distribución que no entró (ver autolayout_conforme)
            # Entre filas de riel libre se deja lugar para peine, etiqueta y canaleta (criterio de diseño en reglas_layout.json: railRowGapMm).
            rail_gap = max(row_gap, rules.get("railRowGapMm", row_gap))

            def rail_row(n, row):
                nonlocal cursor, last_gap
                cursor += rail_gap - last_gap
                row_h = max([d["h"] for d in row], default=44.5)
                y_center = fh - (margin + cursor) - row_h / 2
                rail = {**template, "id": f"DIN-{n}", "x": round((fw - length) / 2, 2), "y": round(y_center, 2), "length": length}
                rails.append(rail)
                _place_row(row, rail, y_center, col_gap, placed)
                cursor += row_h + rail_gap
                last_gap = rail_gap

            if din_main and (main or kit):
                # El general es de riel y hay cajas moldeadas: su fila de riel va arriba de todo y las cajas debajo.
                rail_row(1, rows[0])
                if not kit_rows():
                    return None
                rows_left = list(enumerate(rows[1:], 2))
            else:
                rows_left = list(enumerate(rows, 1))
            for n, row in rows_left:
                rail_row(n, row)
            tail_gap = last_gap
    else:
        tail_gap = last_gap
    if fh - (margin + cursor - tail_gap) < bottom_limit - 1e-6:  # lo de arriba no debe invadir el borde ni la pila de filas del kit
        return None
    if rails and not main and not kit and not enc.get("kdKit"):
        # Tablero sólo de riel libre: se centra el bloque de filas en la altura para que quede lugar a canaleta arriba Y abajo.
        shift = (fh - (margin + cursor - tail_gap) - margin) / 2
        if shift > 0:
            for r in rails:
                r["y"] = round(r["y"] - shift, 2)
            placed = {t: (x, round(y - shift, 2)) for t, (x, y) in placed.items()}
    return placed, rails


def _free_rail_alternative(project, candidates, catalog, rules, pe_reserve, chosen):
    """Gabinete más chico que entra usando riel GD de posición libre (sin kit KD), si es más chico que el elegido. Es opción del usuario: la posición del riel la propone el armado, no el gabinete."""
    area = lambda e: e["externalBody"]["width"] * e["externalBody"]["height"]
    for enc in candidates:
        if area(enc) >= area(chosen):
            break
        free = {**enc, "kdKit": None, "railOptions": (enc.get("kdKit") or {}).get("freeRailOptions", enc.get("railOptions", []))}
        if _try(project, catalog, free, rules, pe_reserve) is not None:
            return {"id": enc["id"], "label": enc["label"], "nota": "riel GD de posición libre (no fijada por el gabinete)"}
    return None


def autolayout(project, catalog, rules=None, free_rails=False, exclude=(), only=None, extra_rows=0):
    """Devuelve (proyecto_nuevo, resumen). El proyecto original no se modifica."""
    rules = rules or load_rules()
    try:
        circuits = sum(1 for d in project["devices"] if str(d.get("tag", "")).startswith("QF"))
        terms = load_accessory_catalog()["earthTerminals"]
        pe = next((t for t in terms if t["id"] == rules.get("peTerminalId")), None) or next(t for t in terms if t["id"] == "entrelec-m4-6p")
        if pe.get("estilo") == "repartidor":  # bloques repartidores + un tope en cada punta
            pe_reserve = (-(-circuits // pe["salidas"]["cantidad"]) * pe["anchoMm"] + 2 * (pe.get("tope") or {}).get("anchoMm", 0)) if circuits else 0.0
        else:
            pe_reserve = circuits * pe["pasoMm"]
    except (StopIteration, KeyError):
        pe_reserve = 0.0
    candidates = sorted(catalog["enclosures"], key=lambda e: (e["externalBody"]["width"] * e["externalBody"]["height"], e["externalBody"]["depth"]))
    tried = []
    for enc in candidates:
        if enc["id"] in exclude or (only and enc["id"] != only):
            continue
        if free_rails and enc.get("kdKit"):  # opción del usuario: riel GD de posición libre en vez de las filas fijas del kit KD
            enc = {**enc, "kdKit": None, "railOptions": enc["kdKit"].get("freeRailOptions", [])}
        result = _try(project, catalog, enc, rules, pe_reserve, extra_rows)
        tried.append({"id": enc["id"], "entra": result is not None})
        if result is None:
            continue
        placed, rails = result
        new = copy.deepcopy(project)
        plinth = enc["plinthHeight"]
        new["enclosure"] = {**new["enclosure"], "line": enc.get("line", new["enclosure"].get("line")), "functional": copy.deepcopy(enc["functional"]), "externalBody": copy.deepcopy(enc["externalBody"]),
                            "plinthHeight": plinth, "overallHeightWithPlinth": enc["externalBody"]["height"] + plinth,
                            "id": enc["id"], "functionalAreaOffset": copy.deepcopy(enc.get("functionalOffset", {"x": 50, "y": plinth + 50})),
                            "mountingLayout": {**copy.deepcopy(enc["mountingLayout"]), "dinRails": rails},
                            "structuralComponentReferences": {"parts": enc["parts"] + ([enc["kdKit"]["kit"]] if enc.get("kdKit") else [])}, "sources": [enc["source"]]}
        spe = "System pro E" in str(enc.get("line", ""))
        shells = {s["id"]: s for s in catalog["deviceShells"]}
        for d in new["devices"]:
            d["x"], d["y"] = placed[d["tag"]]
            spec = shells.get(d.get("shell"), {})
            if spe and spec.get("mounting") != "din" and not d.get("mountingKit"):
                # En System pro E cada caja moldeada va sobre su kit de montaje (lección 2026-11-19: el TGBT salía sin kits).
                d["mountingKit"] = ({"type": spec["kit"], "orderCode": spec.get("kitOrderCode"), "moduleHeight": spec.get("kitHeight"), "auto": True} if spec.get("kit")
                                    else {"type": f"System pro E para {spec.get('label', d.get('model'))} (código pendiente)", "orderCode": None, "auto": True})
            elif not spe and (d.get("mountingKit") or {}).get("auto"):
                d.pop("mountingKit")
            d.pop("unplaced", None)
            d.pop("placementNote", None)
        new["accessories"] = [a for a in new.get("accessories", []) if not a.get("auto")]
        return new, {"gabinete": enc["id"], "kit": (enc.get("kdKit") or {}).get("kit"), "intentos": tried, "rielLibre": free_rails, "alternativaRielLibre": None if free_rails else _free_rail_alternative(project, candidates, catalog, rules, pe_reserve, enc)}
    if only:
        raise ValueError(f"El contenido no entra en el gabinete elegido ({only}); se mantiene el anterior")
    raise ValueError("Ningún gabinete del catálogo aloja este contenido con los criterios de datos/reglas_layout.json")


def _conforme_loop(project, catalog, rules, free_rails, only, extra_rows):
    from accesorios import complete
    exclude, first = [], None
    while True:
        try:
            new, summary = autolayout(project, catalog, rules, free_rails, exclude, only, extra_rows)
        except ValueError:
            if first is None:
                raise
            return first, False
        complete(new, auto_confirm=True)
        first = first or (new, summary)
        # Sólo se prueba un gabinete más grande si falta LUGAR; si el catálogo no tiene la pieza, agrandar no lo arregla.
        if only or not any(a.get("placed") is False and a.get("catalogId") and a.get("type") in ("pe_terminal", "copper_busbar", "distribution_block") for a in new["accessories"]):
            summary["gabinetesDescartados"] = list(exclude)
            return (new, summary), True
        exclude.append(summary["gabinete"])


def autolayout_conforme(project, catalog, rules=None, free_rails=False, only=None):
    """Arma el tablero y completa los accesorios de normativa. Si un accesorio no entra (bornes PE, bloque de distribución),
    compara agrandar el gabinete contra agregar una fila de riel libre y se queda con el gabinete más chico
    (lección 2026-11-19: TSMAQ1 y TS AUX 3 pasaban de 500×400 a 800×800 por un bloque que entraba en una fila más)."""
    area = lambda r: r[0]["enclosure"]["externalBody"]["width"] * r[0]["enclosure"]["externalBody"]["height"]
    best, ok = _conforme_loop(project, catalog, rules, free_rails, only, 0)
    if best[1].get("gabinetesDescartados") or not ok:
        try:
            alt, ok2 = _conforme_loop(project, catalog, rules, free_rails, only, 1)
            if ok2 and (not ok or area(alt) < area(best)):
                alt[1]["filaExtraParaAccesorios"] = True
                best = alt
        except ValueError:
            pass
    return best
