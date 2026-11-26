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
import json
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
GENERIC_RULES_FILE = __import__("pathlib").Path(__file__).resolve().parent / "datos" / "reglas_bom_generico.json"


def load_generic_rules(path=GENERIC_RULES_FILE):
    try:
        return json.loads(__import__("pathlib").Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"breakingCapacityKa": {"rules": []}, "tripLabels": {}, "combLabels": {}}


def _fmt_num(val):
    s = f"{float(val):g}"
    return s.replace(".", ",")


def _ka_for_device(device, rules):
    """Poder de corte en kA: primero el del unifilar (marking.kA), si no la tabla IEC de la serie."""
    mk = device.get("marking") or {}
    if mk.get("kA"):
        return str(mk["kA"]).replace(".", ",")
    model = str(device.get("model") or "").strip()
    in_val = None
    if mk.get("In"):
        try:
            in_val = float(str(mk["In"]).replace(",", "."))
        except ValueError:
            pass
    for r in (rules.get("breakingCapacityKa") or {}).get("rules", []):
        if re.search(r["regex"], model, re.IGNORECASE):
            if r.get("maxInForKa") and in_val is not None:
                for limit, ka in r["maxInForKa"]:
                    if in_val <= limit:
                        return ka
            return r["kA"]
    return None


def generic_device_spec(device, rules=None):
    """Descripción técnica genérica (sin marca ni serie ABB) pero completa y sin ambigüedades:
    tipo de aparato, polos, curva/disparador, calibre In y poder de corte kA."""
    spec = _generic_device_spec_base(device, rules)
    setting = str(device.get("setting") or "").strip()
    if setting and setting.lower() not in spec.lower():
        spec = f"{spec}, regulado {setting}"
    return spec


def _generic_device_spec_base(device, rules=None):
    rules = rules or load_generic_rules()
    model = str(device.get("model") or "").strip()
    poles = device.get("poles")
    mk = device.get("marking") or {}
    ka = _ka_for_device(device, rules)
    ka_txt = f", {ka} kA" if ka else ""

    # 1) Interruptor diferencial (F202 / F204 / F204-SX)
    rcd = re.match(r"^F20(?P<p>\d)(?P<sel>-SX?)?\s+(?P<cls>AC|A|B|F)\s*-\s*(?P<in>\d+)\s*/\s*(?P<sens>\d+[.,]\d+)", model, re.IGNORECASE)
    if rcd:
        p = int(rcd.group("p"))
        sens_ma = int(round(float(rcd.group("sens").replace(",", ".")) * 1000))
        sel_txt = " selectivo (tipo S)" if rcd.group("sel") else ""
        return f"Interruptor diferencial{sel_txt} {p}P, {rcd.group('in')} A, {sens_ma} mA, clase {rcd.group('cls').upper()} (riel DIN)"

    # 2) Interruptor automático abierto (ACB, ej. E2.2N 2000 Ekip Dip LI 2000)
    acb = re.match(r"^E\d\.\d[A-Z]\s+(?P<frame>\d+)\s+(?:Ekip\s+(?:Dip\s+|Touch\s+)?)?(?P<rel>[A-Z/]+)?\s*(?P<in>\d+)?", model, re.IGNORECASE)
    if acb:
        p_txt = f"{poles}P" if poles else "4P"
        frame = acb.group("frame")
        in_a = acb.group("in") or frame
        rel = f", relé electrónico {acb.group('rel').upper()}" if acb.group("rel") else ""
        return f"Interruptor automático abierto (ACB) {p_txt} fijo, marco {frame} A, In {in_a} A{rel}{ka_txt}"

    # 3) Interruptor en caja moldeada (MCCB: Formula A1, Tmax XT, Tmax T)
    mccb_tm = re.match(r"^(?:XT\d[A-Z]?|A1[ABCN]|T\d[A-Z]?)\s+(?P<frame>\d+)\s+(?P<trip>TM[A-Z]+)\s+(?P<in>\d+(?:[.,]\d+)?)", model, re.IGNORECASE)
    if mccb_tm:
        p_txt = f"{poles}P" if poles else "4P"
        trip_code = mccb_tm.group("trip").upper()
        trip_txt = (rules.get("tripLabels") or {}).get(trip_code, f"disparador {trip_code}")
        n50 = ", neutro al 50%" if re.search(r"N\s*=\s*50%", model, re.IGNORECASE) else ""
        in_a = _fmt_num(mccb_tm.group("in").replace(",", "."))
        return f"Interruptor en caja moldeada (MCCB) {p_txt}, marco {mccb_tm.group('frame')} A, In {in_a} A, {trip_txt}{n50}{ka_txt}"

    mccb_el = re.match(r"^(?:XT\d[A-Z]?|T\d[A-Z]?)\s+(?P<frame>\d+)\s+(?:PR\d+[A-Z]*|Ekip\s*[A-Z]*)[-\s]*(?P<rel>[A-Z/]+)?\s+(?P<in>\d+)A?\b", model, re.IGNORECASE)
    if mccb_el:
        p_txt = f"{poles}P" if poles else "4P"
        rel = f"relé electrónico {mccb_el.group('rel').upper()}" if mccb_el.group("rel") else "relé electrónico"
        return f"Interruptor en caja moldeada (MCCB) {p_txt}, marco {mccb_el.group('frame')} A, In {mccb_el.group('in')} A, {rel}{ka_txt}"

    # 4) Seccionador bajo carga (OT)
    ot = re.match(r"^OT\s?(?P<in>\d+)(?P<ser>[A-Z]+)(?P<p>\d+)", model, re.IGNORECASE)
    if ot:
        p = poles or int(ot.group("p"))
        din_txt = " (riel DIN, sin manija)" if int(ot.group("in")) <= 125 else " (montaje en base, sin manija ni eje)"
        return f"Seccionador bajo carga {p}P, {ot.group('in')} A{din_txt}"

    # 5) Interruptor termomagnético modular (MCB riel DIN: S200/L/M/P, SN201, S251-S290, S800)
    is_1pn = bool(re.search(r"\bNA\b|^SN\s?201", model, re.IGNORECASE))
    high_cap = bool(re.match(r"^S\s?(?:80|29)", model, re.IGNORECASE))
    curva = mk.get("curva")
    in_a = mk.get("In")
    if not curva or not in_a:
        mcb = re.search(r"(?:[-\s]|NA\s+)(?P<c>[BCDKZ])\s?(?P<in>\d+(?:[.,]\d+)?)\b", model, re.IGNORECASE)
        if mcb:
            curva = curva or mcb.group("c").upper()
            in_a = in_a or mcb.group("in").replace(".", ",")
    if curva and in_a:
        p_txt = "1P+N" if is_1pn else (f"{poles}P" if poles else "")
        kind = "Interruptor termomagnético de alta capacidad" if high_cap else "Interruptor termomagnético"
        parts = [f"{kind} {p_txt}".strip(), f"curva {curva}", f"{in_a} A"]
        return ", ".join(parts) + f"{ka_txt} (riel DIN)"

    # Fallback seguro: si un modelo futuro no matchea ningún patrón, no inventar datos
    return f"{model or 'Equipo eléctrico'}" + (f", {poles}P" if poles else "") + ka_txt


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


def _known_status(item):
    """Estado de un código verificado: si el unifilar deja abierta una variante, «a confirmar: …» (la lista lo junta en el aviso de compra)."""
    return f"a confirmar: {item['confirm']}" if item.get("confirm") else "verificado"


def unverified_note(model, codes):
    key = model_key(model)
    return next((x["motivo"] for x in codes.get("sinVerificar", []) if model_key(x["model"]) == key), None)


def _generic_accessory_desc(item, gen_rules):
    """Descripción técnica genérica (sin marca ni código de fabricante) para un accesorio."""
    t = item.get("type")
    if t == "comb":
        base = (gen_rules.get("combLabels") or {}).get(item.get("catalogId"))
        if base:
            return base
        return f"Peine de conexión modular, paso {item.get('pitchMm') or 17.5:g} mm"
    if t == "copper_busbar":
        amp = item.get("corrienteA")
        sec = str(item.get("seccion") or "100×10 mm").replace("x", "×")
        icw = f", Icw {item['icwKA']:g} kA" if item.get("icwKA") else ""
        l_mm = f", L = {item['largoMm']:g} mm" if item.get("largoMm") else ""
        p = item.get("poles") or 3
        return f"Juego de barras principales de cobre electrolítico {p}P ({p}×{sec}{l_mm}), In {amp:g} A{icw}, con soportes aislantes (IEC 61439)"
    if t == "pe_bar":
        sec = str(item.get("seccion") or "").replace("x", "×")
        sec_mm2 = item.get("seccionMm2")
        f_pe = item.get("feederPe") or ""
        l_mm = f", L = {item['largoMm']:g} mm" if item.get("largoMm") else ""
        if sec and item.get("placed") is not False:
            cap = f" ({sec_mm2:g} mm²)" if sec_mm2 else ""
            perf = "perforaciones M10 (hasta 8×240 mm²)" if (sec_mm2 or 0) >= 300 else "agujeros roscados M6 cada 25 mm"
            f_txt = f", para PE de alimentación {f_pe} y derivaciones" if f_pe else ""
            return f"Barra colectora de tierra (PE) de cobre electrolítico {sec}{cap}{l_mm}, {perf}, con soportes{f_txt}"
        desc = item.get("description") or item.get("label") or "Barra de tierra (PE)"
        return re.sub(r"\bla bornera [A-Z0-9\-]+\b", "la bornera repartidora PE", desc)
    if t == "distribution_block":
        if item.get("placed") is False and not item.get("catalogId"):
            return item.get("description") or item.get("label") or "Barra de distribución"
        p = item.get("poles") or 4
        amp = item.get("corrienteA")
        return f"Bloque repartidor {p}P{f', {amp:g} A' if amp else ''} (riel DIN)"
    if t == "pe_terminal":
        if item.get("style") == "repartidor":
            outs = item.get("outputs") or 7
            return f"Bornera equipotencial repartidora PE 125 A (1 entrada 10–35 mm², {outs} salidas, riel DIN)"
        return "Borne de puesta a tierra PE para riel DIN"
    if t == "signal_fuses":
        return "Portafusible unipolar 1P para fusible cilíndrico 10×38 mm (riel DIN)"
    if t == "terminal_cover":
        return "Cubrebornes transparente (barrera aislante de protección)"
    desc = item.get("description") or item.get("label") or t
    return re.sub(r"\bla bornera [A-Z0-9\-]+\b", "la bornera repartidora PE", desc)


def build_bom(project, catalog, accessory_catalog=None, order_codes=None, mode="abb"):
    """Lista de materiales del tablero.
    mode='abb' (por defecto): códigos de pedido ABB verificados.
    mode='generic': especificación técnica genérica sin marca ni códigos de fabricante."""
    is_generic = (mode == "generic")
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
    gen_rules = load_generic_rules() if is_generic else None
    rows = []

    def add(category, code, description, quantity=1, unit="u", tags=(), status="verificado", source="", *, generic=False):
        use_gen = generic or is_generic
        code = "" if use_gen else _code(code)
        if use_gen:
            st = status if str(status).startswith("a confirmar") else "genérico"
            src = ""
        else:
            st = status if code != MISSING else "falta código de pedido"
            src = source
        rows.append({"category": category, "code": code, "description": description, "quantity": quantity, "unit": unit,
                     "tags": ", ".join(tags), "status": st, "source": src})

    # 1) Envolvente. SR2 (monobloc): un solo artículo, con la placa incluida. Gabinetes de estructura (System pro E):
    # no hay un código de "gabinete"; se compra pieza por pieza (montantes, travesaños, fondo, puertas, laterales...).
    parts = spec.get("parts") or []
    structure_bom = (spec.get("structure", {}) or {}).get("bom", [])
    enc_code = parts[0] if parts else None
    monobloc = (enc_code or "").startswith("SRN") or not structure_bom
    if is_generic:
        nom = spec.get("nominal") or enclosure.get("externalBody") or {}
        fun = spec.get("functional") or enclosure.get("functional") or {}
        ext = spec.get("externalBody") or enclosure.get("externalBody") or {}
        material = spec.get("material") or enclosure.get("material") or "chapa de acero"
        dims = (nom if nom.get("height") else ext) if monobloc else (ext if ext.get("height") else fun)
        add("Envolvente", None,
            f"Gabinete de {material} · alto {dims.get('height', '?'):g} × ancho {dims.get('width', '?'):g} × prof. {dims.get('depth', '?'):g} mm",
            generic=True)
    elif monobloc:
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
        add("Montaje DIN", kd.get("kit"),
            (f"Kit de soportes para paneles modulares ({kd.get('rows', '?')} filas de {kd.get('modulesPerRow', '?')} módulos)" if is_generic
             else f"Kit KD de soportes para paneles modulares ({kd.get('rows', '?')} filas de {kd.get('modulesPerRow', '?')} módulos)"),
            source=panels.get("source", ""))
        by = (panels.get("porModulos") or {}).get(str(kd.get("modulesPerRow")), {})
        used = len(kd_rails)
        add("Montaje DIN", by.get("pm"), f"{panels.get('pmDescripcion', 'Panel modular + riel DIN')} · {kd.get('modulesPerRow')} módulos", used, "u",
            [r["id"] for r in kd_rails], source=panels.get("source", ""))
        free_rows = max(0, int(kd.get("rows", used)) - used)
        all_din = all(shells.get(d.get("shell"), {}).get("mounting") == "din" or d.get("mounting") == "din"
                      for d in project.get("devices", []))
        if free_rows and all_din:
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
        if is_generic:
            text = (f"Riel DIN simétrico 35×7,5 mm (EN 60715) con soportes · largo {opt['length']} mm" + (f" (cortar a {cut_to} mm)" if cut_to else "")) if opt.get("length") else \
                "Riel DIN simétrico 35×7,5 mm (EN 60715) con soportes (definir largo)"
        else:
            text = (f"Riel DIN con soportes {opt['length']} mm" + (f" · cortar a {cut_to} mm" if cut_to else "")) if opt.get("length") else \
                "Riel DIN 35 mm: el gabinete no tiene opciones de riel en el catálogo; definir código y largo"
        add("Montaje DIN", code, text, len(ids), "u", ids, source=panels.get("source", ""))

    # 3) Equipos: los dibujados y los del unifilar que no se dibujan.
    if is_generic:
        g_drawn = {}
        for device in project.get("devices", []):
            spec_txt = generic_device_spec(device, gen_rules)
            g_drawn.setdefault(spec_txt, []).append(device)
        for spec_txt, devices in g_drawn.items():
            tags = [(f"{d['circuit']} ({d.get('tag', '?')})" if d.get("circuit") else d.get("tag", "?")) for d in devices]
            add("Equipo", None, spec_txt, len(devices), "u", tags, "genérico", generic=True)
        g_nd = {}
        for device in project.get("devicesNotDrawn", []):
            spec_txt = generic_device_spec(device, gen_rules)
            g_nd.setdefault(spec_txt, []).append(device)
        for spec_txt, devices in g_nd.items():
            tags = [(f"{d['circuit']} ({d.get('tag', '?')})" if d.get("circuit") else d.get("tag", "?")) for d in devices]
            add("Equipo (no dibujado)", None, spec_txt + " · NO está en el dibujo", len(devices), "u", tags, "genérico", generic=True)
    else:
        grouped = {}
        for device in project.get("devices", []):
            grouped.setdefault((device.get("model", ""), device.get("shell", ""), device.get("poles"), json.dumps(device.get("correctedFrom"), sort_keys=True)), []).append(device)
        for (model, shell_id, poles, _corr), devices in grouped.items():
            shell = shells.get(shell_id, {})
            code = next((d.get("orderCode") for d in devices if d.get("orderCode")), None)
            code_src = next((d.get("orderCodeSource") for d in devices if d.get("orderCode") and d.get("orderCodeSource")), None)
            known = lookup_order_code(model, poles, codes)
            # Si el código vino automáticamente del informe e-Design (p. ej. códigos legados S598378) y nuestro catálogo
            # tiene el código comercial ABB verificado (2CDS...), prevalece el verificado para no dividir renglones ni comprar obsoletos.
            manual_code = code if (code and code_src != "edesign") else None
            final_code = manual_code or (known or {}).get("orderCode") or code
            use_known = bool(known) and (not manual_code or known.get("orderCode") == manual_code)
            ref = model or shell.get("label", shell_id)
            tags = [(f"{d['circuit']} ({d.get('tag', '?')})" if d.get("circuit") else d.get("tag", "?")) for d in devices]
            extra = (f" · {known['descripcion']}" if use_known else "") + (f" · {known['note']}" if use_known and known.get("note") else "")
            hint = None if final_code else unverified_note(model, codes)
            corr = devices[0].get("correctedFrom")
            if corr:  # cambio pedido por el usuario: la lista lo dice para que nadie compre lo que figura en el unifilar
                extra += f" · CAMBIADO por pedido del usuario: el unifilar dice {corr['model']} ({corr['poles']}P)"
            if use_known:
                status = _known_status(known)
            elif manual_code:
                status = "código cargado por el usuario"
            elif final_code:
                status = "código del informe e-Design"
            else:
                status = "falta código de pedido"
            add("Equipo", final_code, f"{ref}" + (f" · {poles} polos" if poles and str(poles) not in ref else "") + extra + (f" · {hint}" if hint else ""),
                len(devices), "u", tags, status,
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
                + (f" · A CONFIRMAR: {known['confirm']}" if known and known.get("confirm") else "")
                + f" · NO está en el dibujo: {reason}" + (f" · {hint}" if hint else ""),
                len(devices), "u", tags, "falta en el dibujo", (known or {}).get("source", ""))

    # Señalización del unifilar (testigos de presencia de tensión en la puerta y sus fusibles).
    sig = project.get("signals") or {}
    lights = sig.get("pilotLights") or []
    if lights:
        pl = next(iter(accessory_catalog.get("pilotLights", [])), {})
        if is_generic:
            v_txt = lights[0].get("voltage") or "230 V AC"
            add("Señalización", None,
                f"Luz piloto LED {v_txt}, Ø 22 mm (en puerta) · testigos de presencia de tensión {'-'.join(l['label'] for l in lights)}",
                len(lights), "u", [l["label"] for l in lights], "a confirmar (color)", generic=True)
        else:
            add("Señalización", pl.get("orderCode"), f"Luz piloto {pl.get('tipo', '')} {pl.get('descripcion', '')} (22 mm, en la puerta) · testigos de presencia de tensión {'-'.join(l['label'] for l in lights)} {lights[0].get('voltage', '')}"
                + (f" · {pl['status']}" if pl.get("status") else ""), len(lights), "u", [l["label"] for l in lights], "a confirmar (color)", pl.get("source", ""))
    fuses = sig.get("fuses") or {}
    fuse_holders = [a for a in project.get("accessories", []) if a.get("type") == "signal_fuses"]
    active_holders = [a for a in fuse_holders if a.get("decision") != "discarded"]
    fuse_quantity = sum(int(a.get("count", a.get("quantity", 1))) for a in active_holders)
    if not fuse_holders:
        fuse_quantity = int(fuses.get("count") or 0)
    if fuse_quantity:
        defaults = accessory_catalog.get("signalDefaults", {})
        holder = next(iter(accessory_catalog.get("signalFuseHolders", [])), {})
        rating = fuses.get("rating") or (f"{defaults['fuseA']:g} A" if defaults.get("fuseA") else "")
        spec = " ".join(p for p in (holder.get("fusible"), defaults.get("fuseClass"), rating) if p)
        add("Señalización", None, f"Fusible cilíndrico {spec} para los testigos de fase", fuse_quantity,
            status="genérico", generic=True)
        if not fuse_holders:
            add("Señalización", holder.get("orderCode"),
                ("Portafusible unipolar 1P para fusible cilíndrico 10×38 mm (riel DIN)" if is_generic
                 else f"Portafusible {holder.get('tipo', '')} 1P {holder.get('fusible', '')} para los testigos de fase"),
                fuse_quantity, source=holder.get("source", ""))

    # Seccionadores OT: se venden sin manija (y sin eje si se accionan desde la puerta); sin ellos no se pueden operar.
    ot = [d for d in project.get("devices", []) + project.get("devicesNotDrawn", []) if re.match(r"^OT\s?\d", str(d.get("model", ""))) and not re.search(r"WP\b", str(d.get("model", "")))]
    if ot:
        add("Accionamiento" if is_generic else "Accionamiento OT", None,
            ("Manija de accionamiento para seccionador bajo carga (directa sobre el equipo o de puerta con eje)" if is_generic
             else "Manija para el seccionador OT (directa sobre el equipo, o de puerta con su eje): elegir según la variante; el OT se vende sin manija"),
            len(ot), "u", [d.get("tag", "?") for d in ot], "genérico" if is_generic else "falta código de pedido")

    kits = {}
    for device in project.get("devices", []):
        kit = device.get("mountingKit") or {}
        code = kit.get("orderCode")
        if code or kit.get("type"):
            if is_generic:
                kits.setdefault((None, "Kit de montaje en gabinete de piso"), []).append(device)
            else:
                kits.setdefault((code, kit.get("type") or kit.get("kit") or "Kit de montaje"), []).append(device)
    for (code, kind), devices in kits.items():
        if is_generic:
            models = sorted({generic_device_spec(d, gen_rules).split(",")[0] for d in devices})
            add("Kit de montaje", None, f"Kit de montaje en gabinete de piso para {', '.join(models)} (según marca elegida)", len(devices), "u",
                [d.get("circuit") or d.get("tag", "?") for d in devices], "genérico", generic=True)
        else:
            models = sorted({d.get("model", "") for d in devices})
            add("Kit de montaje", code, f"Kit de montaje {kind} para {', '.join(models)}", len(devices), "u",
                [d.get("circuit") or d.get("tag", "?") for d in devices], "verificado" if code else "falta código")

    # 4) Accesorios. Canaletas: por código, en tiras con despiece de cortes.
    duct_spec = accessory_catalog.get("wiringDucts", {}) or {}
    strip = duct_spec.get("lengthMm", 2000)
    ducts, grouped_acc = {}, {}
    for item in project.get("accessories", []):
        if item.get("decision") == "discarded":
            continue
        if item.get("placed") is False:
            item = {**item, "description": (item.get("description") or item.get("label") or item.get("type")) + " · NO está en el dibujo: "
                    + (item.get("note") or "sin lugar o sin pieza en el catálogo")}
        if item.get("type") == "wiring_duct":
            sec = item.get("sectionMm") or (item["w"] if item.get("orientation") == "v" else item["h"])
            ducts.setdefault((None if is_generic else item.get("orderCode"), sec, item.get("depthMm"), item.get("slot")), []).append(round(item.get("lengthMm") or max(item["w"], item["h"])))
            continue
        category = item.get("bomCategory") or "Accesorio"
        if is_generic:
            description = _generic_accessory_desc(item, gen_rules)
            code = ""
            base = description
        else:
            description = item.get("description") or item.get("label") or item.get("type")
            code = _code(item.get("orderCode"))
            base = description if code == MISSING else description.split(", equipos:")[0]
            if item.get("type") == "comb" and code != MISSING:
                base = re.sub(r" para \S+ polos", "", base)
        key = (category, code, base)
        entry = grouped_acc.setdefault(key, {"q": 0, "tags": [], "spans": [], "check": item.get("purchaseCheck")})
        if item.get("type") == "comb":
            entry["spans"].append((item.get("poleCount", "?"), int(item.get("quantity", 1))))
        entry["q"] += int(item.get("quantity", 1))
        entry["tags"] += item.get("devices", [])
        extras = [] if item.get("type") == "signal_fuses" else item.get("bomExtra", [])
        for extra in extras:
            if is_generic:
                raw_ex = str(extra.get("description", ""))
                if "Tope" in raw_ex:
                    ex_desc = "Tope de fin para riel DIN (10 mm), uno en cada punta"
                elif "neutro" in raw_ex.lower():
                    ex_desc = "Barra horizontal de neutro (N) 100 % de cobre electrolítico, In 2000 A, L = 578 mm (hasta 7×240 mm² M10, con soportes)"
                elif "soportes aislantes" in raw_ex.lower() and "tierra" in raw_ex.lower():
                    ex_desc = "Juego de 5 soportes aislantes para barra colectora de tierra (PE) 20×5 mm"
                else:
                    ex_desc = re.sub(r"\b(?:AA\d{4}|PPHC\d+|ZXPHC\d+|BAM\d+|1STQ\w+|2CPX\w+)\b", "", raw_ex).replace("  ", " ").strip()
                k = (extra["bomCategory"], "", ex_desc)
            else:
                k = (extra["bomCategory"], _code(extra.get("orderCode")), extra["description"])
            grouped_acc.setdefault(k, {"q": 0, "tags": [], "spans": [], "check": extra.get("purchaseCheck")})["q"] += int(extra.get("quantity", 1))
    for (code, sec, depth, slot), pieces in ducts.items():
        bins = _strips([p for p in pieces if p <= strip], strip) + [[p] for p in pieces if p > strip]
        n = sum(-(-sum(b) // strip) for b in bins)
        cuts = ", ".join(f"{pieces.count(p)}×{p}" for p in sorted(set(pieces), reverse=True))
        pack = next((s.get("packMeters") for s in duct_spec.get("sections", []) if s["widthMm"] == sec and s["heightMm"] == depth), None)
        add("Canaleta", code, f"Canaleta ranurada {sec:g}x{depth:g} mm gris RAL 7035, ranura {slot} · tiras de {strip / 1000:g} m · cortes: {cuts} mm"
            + (f" · se vende por caja de {pack} m" if pack else ""), n, f"tira {strip / 1000:g} m", source=duct_spec.get("source", ""))
    for (category, code, description), entry in grouped_acc.items():
        if entry["spans"]:
            spans = {}
            for poles_, q in entry["spans"]:  # mismos tramos se suman: "2×14, 2×14" → "4×14"
                spans[poles_] = spans.get(poles_, 0) + q
            description += " · tramos (piezas × polos a puentear): " + ", ".join(f"{q}×{n}" for n, q in sorted(spans.items(), key=lambda x: -int(x[0]) if str(x[0]).isdigit() else 0))
        add(category, code, description, entry["q"], "u", entry["tags"],
            status=f"a confirmar: {entry['check']}" if entry.get("check") else "verificado" if code != MISSING else "falta código de pedido")

    # 5) Cables de potencia y distribución (sección, material/aislación y longitud en metros extraídos de e-Design).
    # Sólo la acometida principal sin tablero padre (upstreamTag=None) + las salidas propias del tablero, para no
    # duplicar cables entre tablero padre e hijo al consolidar varios tableros en Excel o PDF de entrega.
    cable_groups = {}
    def _add_cable(sec, length_m, insulation, label, is_main=False):
        sec_clean = str(sec or "").strip()
        if not sec_clean:
            return
        ins_clean = str(insulation or "").strip()
        key = (sec_clean, ins_clean, bool(is_main))
        g = cable_groups.setdefault(key, {"length": 0.0, "has_len": False, "missing_len": False, "tags": []})
        if length_m is not None:
            val = float(length_m)
            g["length"] += val
            g["has_len"] = True
            l_txt = f"{int(val) if val.is_integer() else round(val, 1)} m"
            g["tags"].append(f"{label} ({l_txt})")
        else:
            g["missing_len"] = True
            g["tags"].append(label)

    feeder = project.get("feeder") or {}
    if feeder.get("cable") and not feeder.get("upstreamTag") and feeder.get("lengthM") is not None:
        _add_cable(feeder["cable"], feeder.get("lengthM"), feeder.get("insulation"),
                   feeder.get("from") or "Alimentación principal", is_main=True)
    for device in project.get("devices", []) + project.get("devicesNotDrawn", []):
        if device.get("cable"):
            lbl = device.get("circuit") or device.get("tag") or "Circuito"
            _add_cable(device["cable"], device.get("cableLengthM"), device.get("cableInsulation"), lbl)
    for (sec_clean, ins_clean, is_main), g in cable_groups.items():
        sec_fmt = sec_clean.replace("x", "×")
        ins_txt = f"{ins_clean} · " if ins_clean else ""
        main_txt = " (acometida principal)" if is_main else ""
        if g["has_len"]:
            qty_m = int(round(g["length"])) if abs(g["length"] - round(g["length"])) < 1e-6 else round(g["length"], 1)
            st = "a confirmar: falta longitud en algún circuito" if g["missing_len"] else "genérico"
            add("Cable", None, f"Cable {ins_txt}{sec_fmt} mm²{main_txt}", qty_m, "m", g["tags"], st, generic=True)
        else:
            add("Cable", None, f"Cable {ins_txt}{sec_fmt} mm²{main_txt}", 1, "u", g["tags"],
                "a confirmar: definir longitud en metros", generic=True)
    return rows


def bom_issues(rows, project=None):
    """Controles antes de comprar: devuelve una lista de textos (vacía = listo para pedir)."""
    issues = []
    to_check = [r for r in rows if str(r.get("status", "")).startswith("a confirmar:") and r["code"] != MISSING]
    if to_check:
        issues.append(f"{len(to_check)} renglón(es) a confirmar antes de comprar: " + "; ".join(f"{r['code'] or r['category']}: {r['status'][13:80]}" for r in to_check))
    missing = [r for r in rows if r["code"] == MISSING]
    if missing:
        issues.append(f"{len(missing)} renglón(es) sin código de pedido: " + "; ".join(f"{r['category']}: {r['description'][:60]}" for r in missing))
    not_drawn = [r for r in rows if r["category"] == "Equipo (no dibujado)"]
    if not_drawn:
        issues.append(f"{sum(r['quantity'] for r in not_drawn)} equipo(s) del unifilar no están en el dibujo pero sí en la lista: " + "; ".join(r["tags"] for r in not_drawn))
    seen = {}
    for r in rows:
        if r["code"] and r["code"] != MISSING:
            seen.setdefault(r["code"], []).append(r)
    dup = [c for c, rs in seen.items() if len(rs) > 1]
    if dup:
        issues.append("Código repetido en más de un renglón (revisar que no se pida dos veces): " + ", ".join(dup))
    if any(isinstance(r["quantity"], bool) or not isinstance(r["quantity"], (int, float)) or r["quantity"] <= 0 for r in rows):
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
