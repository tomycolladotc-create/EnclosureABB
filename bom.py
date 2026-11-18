"""Lista de materiales (cómputo) a partir del proyecto y los catálogos ABB.

Reglas para no inducir una compra errónea:
- un renglón por artículo a comprar (mismo código = mismo renglón), con cantidad y unidad de venta;
- nada duplicado: la placa de los SR2 con puerta ciega viene incluida (catálogo pág. 2/5);
- el kit KD son sólo soportes: cada fila usada lleva un panel PM (trae el riel DIN) y cada fila vacía un panel ciego PC;
- rieles libres: un GD por riel (el más corto que alcanza; si se corta, se indica el largo);
- canaletas: se suman por código y se calculan las tiras de 2 m (despiece de cortes);
- equipos del unifilar que no se dibujan (sin carcasa en el catálogo, monopolares) igual se compran;
- sin código de pedido conocido → "FALTA CÓDIGO", nunca un id interno del programa.
"""
from __future__ import annotations

import csv
import io
import re

MISSING = "FALTA CÓDIGO"


def _pending(text):
    return bool(re.search(r"pendiente|confirm|placeholder|conflict|variant|revisar", str(text), re.I))


def _code(value):
    """Un código de pedido real o FALTA CÓDIGO (los ids internos del programa no son códigos)."""
    if not value or not isinstance(value, str) or "_" in value or value.islower() or " / " in value:
        return MISSING
    return value


def _strips(pieces, strip):
    """Despiece first-fit decreasing: cuántas tiras de `strip` mm hacen falta para cortar `pieces` (mm)."""
    bins = []
    for p in sorted(pieces, reverse=True):
        for b in bins:
            if sum(b) + p <= strip + 1e-6:
                b.append(p)
                break
        else:
            bins.append([p])
    return bins


ORDER_CODES_FILE = __import__("pathlib").Path(__file__).resolve().parent / "datos" / "codigos_pedido_abb.json"


def model_key(model):
    """Clave de búsqueda de un modelo: sin espacios ni guiones, coma decimal → punto, mayúsculas ('S201M B16' = 'S201M-B16')."""
    return re.sub(r"[\s\-]+", "", str(model or "")).replace(",", ".").upper()


def load_order_codes(path=ORDER_CODES_FILE):
    try:
        import json
        return json.loads(__import__("pathlib").Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"items": [], "sinVerificar": []}


def lookup_order_code(model, poles, codes):
    """Código verificado para el modelo (y la cantidad de polos, si ambos la tienen); None si no hay uno seguro."""
    key = model_key(model)
    for item in codes.get("items", []):
        if model_key(item["model"]) == key and (not poles or not item.get("poles") or int(poles) == int(item["poles"])):
            return item
    return None


def unverified_note(model, codes):
    key = model_key(model)
    return next((x["motivo"] for x in codes.get("sinVerificar", []) if model_key(x["model"]) == key), None)


def build_bom(project, catalog, accessory_catalog=None, order_codes=None):
    if accessory_catalog is None:
        from accesorios import load_accessory_catalog
        accessory_catalog = load_accessory_catalog()
    enclosures = {item["id"]: item for item in catalog.get("enclosures", [])}
    shells = {item["id"]: item for item in catalog.get("deviceShells", [])}
    enclosure = project.get("enclosure", {})
    spec = enclosures.get(enclosure.get("id"), {}) or next(  # proyectos viejos sin id: mismo criterio que el DXF (área funcional)
        (e for e in catalog.get("enclosures", []) if enclosure.get("functional") and e.get("functional") == enclosure.get("functional")), {})
    panels = catalog.get("sr2Panels", {})
    codes = load_order_codes() if order_codes is None else order_codes
    rows = []

    def add(category, code, description, quantity=1, unit="u", tags=(), status="verificado", source=""):
        rows.append({"category": category, "code": _code(code), "description": description, "quantity": quantity, "unit": unit,
                     "tags": ", ".join(tags), "status": status if _code(code) != MISSING else "falta código de pedido", "source": source})

    # 1) Envolvente. SR2 (monobloc): un solo artículo, con la placa incluida. Gabinetes de estructura (System pro E):
    # no hay un código de "gabinete"; se compra pieza por pieza (montantes, travesaños, fondo, puertas, laterales...).
    parts = spec.get("parts") or []
    structure_bom = (spec.get("structure", {}) or {}).get("bom", [])
    enc_code = parts[0] if parts else None
    monobloc = (enc_code or "").startswith("SRN") or not structure_bom
    if monobloc:
        plate_note = " · incluye placa interna galvanizada (no comprar PF aparte)" if spec.get("line", "").startswith("SR2") or (enc_code or "").startswith("SRN") else ""
        add("Envolvente", enc_code, (spec.get("label") or enclosure.get("line", "Envolvente ABB")) + plate_note,
            status="verificado" if enc_code else "falta código", source=spec.get("source", ""))
    else:
        label = spec.get("label") or enclosure.get("line", "Envolvente ABB")
        for part in structure_bom:
            codes_ = [c.strip() for c in str(part.get("codigo") or "").split("+") if c.strip()]
            if " / " in str(part.get("codigo")):  # menú de opciones del catálogo, no un artículo
                continue
            text = part.get("parte", "Pieza de envolvente")
            match = re.search(r"\(x(\d+)\)", text, re.I)
            qty = int(match.group(1)) if match else (2 if re.search(r"uno por lado", text, re.I) else 1)
            if len(codes_) > 1:  # "PDLB1127 + PDNB1507": dos artículos distintos → dos renglones
                for c in codes_:
                    add("Envolvente (estructura)", c, f"{text} · {label}", 1, source=spec.get("source", ""))
                continue
            code = part.get("orden") or part.get("codigo")
            ref = f" (tipo {part['codigo']})" if part.get("orden") and part.get("codigo") else ""
            add("Envolvente (estructura)", code, f"{text}{ref} · {label}", qty, source=spec.get("source", ""))

    # 2) Montaje DIN: kit KD + paneles PM/PC, o rieles GD libres.
    rails = enclosure.get("mountingLayout", {}).get("dinRails", [])
    kd = spec.get("kdKit") or {}
    kd_rails = [r for r in rails if r.get("kdKit")]
    if kd_rails:
        add("Montaje DIN", kd.get("kit"), f"Kit KD de soportes para paneles modulares ({kd.get('rows', '?')} filas de {kd.get('modulesPerRow', '?')} módulos)",
            source=panels.get("source", ""))
        by = (panels.get("porModulos") or {}).get(str(kd.get("modulesPerRow")), {})
        used = len(kd_rails)
        add("Montaje DIN", by.get("pm"), f"{panels.get('pmDescripcion', 'Panel modular + riel DIN')} · {kd.get('modulesPerRow')} módulos", used, "u",
            [r["id"] for r in kd_rails], source=panels.get("source", ""))
        free_rows = max(0, int(kd.get("rows", used)) - used)
        all_din = all((shells.get(d.get("shell"), {}).get("mount") or "").startswith("din") or not d.get("mountingKit") for d in project.get("devices", [])) \
            and not any(d.get("mountingKit") for d in project.get("devices", []))
        if free_rows and all_din:  # con cajas moldeadas en placa, las filas "libres" las ocupan esos equipos: no se pide panel ciego
            add("Montaje DIN", by.get("pc"), f"{panels.get('pcDescripcion', 'Panel modular ciego')} para las filas sin equipos", free_rows, source=panels.get("source", ""))
    options = sorted(spec.get("railOptions") or (kd.get("freeRailOptions") or []), key=lambda o: o["length"])
    gd = {}
    for rail in rails:
        if rail.get("kdKit"):
            continue
        need = rail.get("length", 0)
        opt = next((o for o in options if o["length"] >= need - 0.5), options[-1] if options else {})
        cut = need < opt.get("length", need) - 0.5
        key = (opt.get("orderCode") or opt.get("type"), round(need) if cut else None)
        gd.setdefault(key, []).append(rail.get("id", "riel"))
    for (code, cut_to), ids in gd.items():
        opt = next((o for o in options if (o.get("orderCode") or o.get("type")) == code), {})
        text = (f"Riel DIN con soportes {opt['length']} mm" + (f" · cortar a {cut_to} mm" if cut_to else "")) if opt.get("length") else \
            "Riel DIN 35 mm: el gabinete no tiene opciones de riel en el catálogo; definir código y largo"
        add("Montaje DIN", code, text, len(ids), "u", ids,
            source=panels.get("source", ""))

    # 3) Equipos: los dibujados y los del unifilar que no se dibujan.
    grouped = {}
    for device in project.get("devices", []):
        grouped.setdefault((device.get("model", ""), device.get("shell", ""), device.get("poles")), []).append(device)
    for (model, shell_id, poles), devices in grouped.items():
        shell = shells.get(shell_id, {})
        code = next((d.get("orderCode") for d in devices if d.get("orderCode")), None)
        known = None if code else lookup_order_code(model, poles, codes)
        ref = model or shell.get("label", shell_id)
        tags = [(f"{d['circuit']} ({d.get('tag', '?')})" if d.get("circuit") else d.get("tag", "?")) for d in devices]
        extra = (f" · {known['descripcion']}" if known else "") + (f" · {known['note']}" if known and known.get("note") else "")
        hint = None if (code or known) else unverified_note(model, codes)
        add("Equipo", code or (known or {}).get("orderCode"), f"{ref}" + (f" · {poles} polos" if poles and str(poles) not in ref else "") + extra + (f" · {hint}" if hint else ""),
            len(devices), "u", tags, "código cargado por el usuario" if code else ("verificado" if known else "falta código de pedido"),
            (known or {}).get("source") or shell.get("cadSource", ""))
    missing_drawn = {}
    for device in project.get("devicesNotDrawn", []):
        missing_drawn.setdefault((device.get("model", ""), device.get("poles")), []).append(device)
    for (model, poles), devices in missing_drawn.items():
        tags = [(f"{d['circuit']} ({d.get('tag', '?')})" if d.get("circuit") else d.get("tag", "?")) for d in devices]
        reason = devices[0].get("status", "sin carcasa en el catálogo")
        known = None if devices[0].get("orderCode") else lookup_order_code(model, poles, codes)
        hint = None if known or devices[0].get("orderCode") else unverified_note(model, codes)
        add("Equipo (no dibujado)", devices[0].get("orderCode") or (known or {}).get("orderCode"),
            f"{model or '?'}" + (f" · {poles} polos" if poles else "") + (f" · {known['note']}" if known and known.get("note") else "")
            + f" · NO está en el dibujo: {reason}" + (f" · {hint}" if hint else ""),
            len(devices), "u", tags, "falta en el dibujo", (known or {}).get("source", ""))

    # Señalización del unifilar (testigos de presencia de tensión en la puerta y sus fusibles).
    sig = project.get("signals") or {}
    lights = sig.get("pilotLights") or []
    if lights:
        pl = next(iter(accessory_catalog.get("pilotLights", [])), {})
        add("Señalización", pl.get("orderCode"), f"Luz piloto {pl.get('tipo', '')} {pl.get('descripcion', '')} (22 mm, en la puerta) · testigos de presencia de tensión {'-'.join(l['label'] for l in lights)} {lights[0].get('voltage', '')}"
            + (f" · {pl['status']}" if pl.get("status") else ""), len(lights), "u", [l["label"] for l in lights], "a confirmar (color)", pl.get("source", ""))
    fuses = sig.get("fuses") or {}
    if fuses.get("count"):
        add("Señalización", None, f"Fusible {fuses.get('type', '')} {fuses.get('rating', '')} con su portafusible, para los testigos de fase (según unifilar)", int(fuses["count"]), "u")

    kits = {}
    for device in project.get("devices", []):
        kit = device.get("mountingKit") or {}
        code = kit.get("orderCode")
        if code or kit.get("type"):
            kits.setdefault((code, kit.get("type") or kit.get("kit") or "Kit de montaje"), []).append(device)
    for (code, kind), devices in kits.items():
        models = sorted({d.get("model", "") for d in devices})
        add("Kit de montaje", code, f"Kit de montaje en placa {kind} para {', '.join(models)}", len(devices), "u",
            [d.get("circuit") or d.get("tag", "?") for d in devices], "verificado" if code else "falta código")

    # 4) Accesorios. Canaletas: por código, en tiras con despiece de cortes.
    duct_spec = accessory_catalog.get("wiringDucts", {}) or {}
    strip = duct_spec.get("lengthMm", 2000)
    ducts, grouped_acc = {}, {}
    for item in project.get("accessories", []):
        if item.get("decision") == "discarded" or item.get("placed") is False:
            continue
        if item.get("type") == "wiring_duct":
            sec = item.get("sectionMm") or (item["w"] if item.get("orientation") == "v" else item["h"])
            ducts.setdefault((item.get("orderCode"), sec, item.get("depthMm"), item.get("slot")), []).append(round(item.get("lengthMm") or max(item["w"], item["h"])))
            continue
        category = item.get("bomCategory") or "Accesorio"
        description = item.get("description") or item.get("label") or item.get("type")
        code = _code(item.get("orderCode"))
        base = description if code == MISSING else description.split(", equipos:")[0]
        if item.get("type") == "comb" and code != MISSING:  # un peine por código: los tramos (polos por fila) van en la descripción
            base = re.sub(r" para \S+ polos", "", base)
        key = (category, code, base)  # mismo código = un solo renglón
        entry = grouped_acc.setdefault(key, {"q": 0, "tags": [], "spans": []})
        if item.get("type") == "comb":
            entry["spans"].append(f"{item.get('quantity', 1)}×{item.get('poleCount', '?')}")
        entry["q"] += int(item.get("quantity", 1))
        entry["tags"] += item.get("devices", [])
        for extra in item.get("bomExtra", []):  # renglones asociados (p. ej. topes de la bornera)
            k = (extra["bomCategory"], _code(extra.get("orderCode")), extra["description"])
            grouped_acc.setdefault(k, {"q": 0, "tags": [], "spans": []})["q"] += int(extra.get("quantity", 1))
    for (code, sec, depth, slot), pieces in ducts.items():
        bins = _strips([p for p in pieces if p <= strip], strip) + [[p] for p in pieces if p > strip]
        n = sum(-(-sum(b) // strip) for b in bins)
        cuts = ", ".join(f"{pieces.count(p)}×{p}" for p in sorted(set(pieces), reverse=True))
        pack = next((s.get("packMeters") for s in duct_spec.get("sections", []) if s["widthMm"] == sec and s["heightMm"] == depth), None)
        add("Canaleta", code, f"Canaleta ranurada {sec:g}x{depth:g} mm gris RAL 7035, ranura {slot} · tiras de {strip / 1000:g} m · cortes: {cuts} mm"
            + (f" · se vende por caja de {pack} m" if pack else ""), n, f"tira {strip / 1000:g} m", source=duct_spec.get("source", ""))
    for (category, code, description), entry in grouped_acc.items():
        if entry["spans"]:
            description += " · tramos (piezas × polos a puentear): " + ", ".join(entry["spans"])
        add(category, code, description, entry["q"], "u", entry["tags"], status="verificado" if code != MISSING else "falta código de pedido")
    return rows


def bom_issues(rows, project=None):
    """Controles antes de comprar: devuelve una lista de textos (vacía = listo para pedir)."""
    issues = []
    missing = [r for r in rows if r["code"] == MISSING]
    if missing:
        issues.append(f"{len(missing)} renglón(es) sin código de pedido: " + "; ".join(f"{r['category']}: {r['description'][:60]}" for r in missing))
    not_drawn = [r for r in rows if r["category"] == "Equipo (no dibujado)"]
    if not_drawn:
        issues.append(f"{sum(r['quantity'] for r in not_drawn)} equipo(s) del unifilar no están en el dibujo pero sí en la lista: " + "; ".join(r["tags"] for r in not_drawn))
    seen = {}
    for r in rows:
        if r["code"] != MISSING:
            seen.setdefault(r["code"], []).append(r)
    dup = [c for c, rs in seen.items() if len(rs) > 1]
    if dup:
        issues.append("Código repetido en más de un renglón (revisar que no se pida dos veces): " + ", ".join(dup))
    if any(not isinstance(r["quantity"], int) or r["quantity"] <= 0 for r in rows):
        issues.append("Hay renglones con cantidad inválida.")
    odd = [r["code"] for r in rows if r["code"] != MISSING and re.search(r"[\s+/,]", r["code"])]
    if odd:
        issues.append("Código con más de un artículo o con espacios (separar antes de pedir): " + ", ".join(odd))
    if project is not None:
        drawn = sum(r["quantity"] for r in rows if r["category"] == "Equipo")
        if drawn != len(project.get("devices", [])):
            issues.append(f"La lista tiene {drawn} equipos y el tablero {len(project.get('devices', []))}.")
    return issues


def to_csv(rows, issues=()):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=("category", "code", "description", "quantity", "unit", "tags", "status", "source"), delimiter=";")
    writer.writerow({"category": "Categoría", "code": "Código", "description": "Descripción", "quantity": "Cantidad", "unit": "Unidad",
                     "tags": "Circuitos", "status": "Estado", "source": "Fuente"})
    writer.writerows(rows)
    for text in issues:
        writer.writerow({"category": "CONTROL", "description": text})
    return ("﻿" + output.getvalue()).encode("utf-8")
