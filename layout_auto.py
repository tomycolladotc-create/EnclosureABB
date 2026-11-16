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


def _classify(devices, catalog, rules):
    shells = {s["id"]: s for s in catalog["deviceShells"]}
    din = {s["id"] for s in catalog["deviceShells"] if s.get("mounting") == "din"}
    main, kit, rail = [], [], []
    for d in devices:
        spec = shells.get(d.get("shell"), {})
        if d.get("shell") in din or d.get("mounting") == "din":
            rail.append(d)
        elif str(d.get("tag", "")).startswith(rules["mainTagPrefix"]):
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


def _try(project, catalog, enc, rules, pe_reserve):
    fw, fh = enc["functional"]["width"], enc["functional"]["height"]
    margin, row_gap, col_gap = rules["margin"], rules["rowGap"], rules["colGap"]
    usable_w, usable_h = fw - 2 * margin, fh - 2 * margin
    main, kit, rail_devs = _classify(project["devices"], catalog, rules)
    if (main or kit) and enc["functional"]["depth"] < rules.get("minDepthForKitDevicesMm", 0):
        return None
    placed, rails, cursor = {}, [], 0.0  # cursor: distancia desde arriba del área funcional (sin margen)

    def row_block(devs, heights, gap):
        nonlocal cursor
        rows = _wrap([d["w"] for d in devs], usable_w, gap)
        if rows is None:
            return False
        for idx in rows:
            row_h = max(heights[i] for i in idx)
            row_w = sum(devs[i]["w"] for i in idx) + gap * (len(idx) - 1)
            x = margin + (usable_w - row_w) / 2
            top = margin + cursor
            for i in idx:
                d = devs[i]
                placed[d["tag"]] = (round(x, 2), round(fh - top - row_h + (row_h - d["h"]) / 2, 2))
                x += d["w"] + gap
            cursor += row_h + row_gap
        return True

    if main and not row_block(main, [d["h"] for d in main], col_gap):
        return None
    if kit:
        kit = sorted(kit, key=lambda t: t[0].get("shell") or "")
        devs = [d for d, _ in kit]
        heights = [max(s.get("kitHeight") or 0, d["h"]) if rules.get("kitModuleHeightFromShell") else d["h"] for d, s in kit]
        if not row_block(devs, heights, col_gap):
            return None
    bottom_limit = margin  # borde inferior permitido para lo que se arma de arriba hacia abajo
    tail_gap = row_gap  # separación que queda después de la última fila armada de arriba hacia abajo
    if rail_devs:
        kd = enc.get("kdKit")
        rail_devs = sorted(rail_devs, key=lambda d: d.get("shell") or "")
        if kd:
            # Kit KD del gabinete: filas de riel fijas (185 mm de paso, largo = módulos x 17,5 mm); no se inventa otra posición.
            length, pitch = kd["modulesPerRow"] * kd["moduleMm"], kd["rowPitchMm"]
            rows = _pack_rail_rows(rail_devs, length, col_gap, pe_reserve)
            if rows is None or len(rows) > kd["rows"] or any(d["h"] > pitch for d in rail_devs) or length > usable_w:
                return None
            bottom_limit = margin + len(rows) * pitch + row_gap  # pila de filas contiguas apoyada abajo de la placa
            for n, row in enumerate(rows, 1):
                y_center = margin + (len(rows) - n) * pitch + pitch / 2
                rail = {"id": f"DIN-{n}", "type": f"Fila {n} del kit {kd['kit']}", "orderCode": None, "kdKit": kd["kit"], "fixed": True, "height": 35,
                        "x": round((fw - length) / 2, 2), "y": round(y_center, 2), "length": length}
                rails.append(rail)
                _place_row(row, rail, y_center, col_gap, placed)
        else:
            # Gabinete sin kit KD: riel más largo de railOptions que entra en el ancho útil, posición propuesta por el armado (no fijada por el gabinete).
            options = [o for o in enc.get("railOptions", []) if o["length"] <= usable_w]
            if not options:
                return None
            template = copy.deepcopy(max(options, key=lambda o: o["length"]))
            length = template["length"]
            rows = _pack_rail_rows(rail_devs, length, col_gap, pe_reserve)
            if rows is None:
                return None
            # Entre filas de riel libre se deja lugar para peine, etiqueta y canaleta (criterio de diseño en reglas_layout.json: railRowGapMm).
            rail_gap = max(row_gap, rules.get("railRowGapMm", row_gap))
            cursor += rail_gap - row_gap
            tail_gap = rail_gap
            for n, row in enumerate(rows, 1):
                row_h = max([d["h"] for d in row], default=44.5)
                y_center = fh - (margin + cursor) - row_h / 2
                rail = {**template, "id": f"DIN-{n}", "x": round((fw - length) / 2, 2), "y": round(y_center, 2), "length": length}
                rails.append(rail)
                _place_row(row, rail, y_center, col_gap, placed)
                cursor += row_h + rail_gap
    if fh - (margin + cursor - tail_gap) < bottom_limit - 1e-6:  # lo de arriba no debe invadir el borde ni la pila de filas del kit
        return None
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


def autolayout(project, catalog, rules=None, free_rails=False):
    """Devuelve (proyecto_nuevo, resumen). El proyecto original no se modifica."""
    rules = rules or load_rules()
    try:
        circuits = sum(1 for d in project["devices"] if str(d.get("tag", "")).startswith("QF"))
        pe_reserve = circuits * next(t["pasoMm"] for t in load_accessory_catalog()["earthTerminals"] if t["id"] == "entrelec-m4-6p")
    except (StopIteration, KeyError):
        pe_reserve = 0.0
    candidates = sorted(catalog["enclosures"], key=lambda e: (e["externalBody"]["width"] * e["externalBody"]["height"], e["externalBody"]["depth"]))
    tried = []
    for enc in candidates:
        if free_rails and enc.get("kdKit"):  # opción del usuario: riel GD de posición libre en vez de las filas fijas del kit KD
            enc = {**enc, "kdKit": None, "railOptions": enc["kdKit"].get("freeRailOptions", [])}
        result = _try(project, catalog, enc, rules, pe_reserve)
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
        for d in new["devices"]:
            d["x"], d["y"] = placed[d["tag"]]
            d.pop("unplaced", None)
            d.pop("placementNote", None)
        new["accessories"] = [a for a in new.get("accessories", []) if not a.get("auto")]
        return new, {"gabinete": enc["id"], "kit": (enc.get("kdKit") or {}).get("kit"), "intentos": tried, "rielLibre": free_rails, "alternativaRielLibre": None if free_rails else _free_rail_alternative(project, candidates, catalog, rules, pe_reserve, enc)}
    raise ValueError("Ningún gabinete del catálogo aloja este contenido con los criterios de datos/reglas_layout.json")
