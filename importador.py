"""Importador de unifilares en PDF de ABB e-Design DOC.

Todo lo específico (formato de etiquetas, cómo se marca el alimentador, qué texto
corresponde a qué carcasa ABB) vive en datos/catalogo_abb.json:
  - importRules: expresiones para cortar el texto y leer modelo y polos.
  - series: qué modelos usan cada carcasa (deviceShells) y con qué polos.
    Varias series pueden compartir carcasa: solo cambia la inscripción.
  - modelHints: modelos conocidos sin carcasa CAD (p. ej. montaje en riel).
Para que reconozca un equipo nuevo se edita el catálogo, no este archivo.
"""
import json
import re
from pathlib import Path


def _first_group(patterns, text):
    for pattern in patterns:
        found = re.search(pattern, text)
        if found:
            return int(found.group(1))
    return None


def parse_model(snippet, rules):
    """Texto del modelo: lo que hay antes del primer terminador (cable, -WC, SECCIONADOR)."""
    cut = len(snippet)
    for pattern in rules["modelTerminators"]:
        found = re.search(pattern, snippet)
        if found:
            cut = min(cut, found.start())
    return snippet[:cut].strip()


def shell_size(shell, poles):
    """Medidas fijas del equipo: de la carcasa, o polos × módulo si la carcasa es por polo."""
    module = shell.get("poleModule")
    if module and poles:
        return module["width"] * poles, shell["height"]
    return shell["width"], shell["height"]


def marking_fields(model, block, rules):
    """Datos que van impresos en el frente: serie, curva, In (del modelo) y kA (de I Nom - Icc)."""
    fields = {}
    parts = re.match(rules["modelParts"], model, re.IGNORECASE)
    if parts:
        serie = re.sub(r"\s+", "", parts.group("serie") or "").upper()
        fields["serie"] = serie
        fields["serieS"] = re.sub(r"^([A-Z]+)(\d)", r"\1 \2", serie)  # S201M -> "S 201M" (así figura en S200)
        if parts.group("curva"):
            fields["curva"] = parts.group("curva").upper()
        if parts.group("In"):
            fields["In"] = parts.group("In").replace(".", ",")
        if parts.group("sufijo"):
            fields["sufijo"] = parts.group("sufijo").upper()
            fields["sufijoGuion"] = "-" + fields["sufijo"]
    if "serie" in fields:
        fields.setdefault("sufijoGuion", "")
    # Los Tmax y Formula A1 escriben primero el bastidor (160/125) y recién después la unidad de
    # disparo y su corriente: "XT1C 160 TMD 80-800", "A1C 125 TMF 70-700". La regla genérica no debe
    # confundir el tamaño de bastidor con In.
    tmax = re.search(
        r"\b(?P<serie>XT\d[A-Z]?|A1[ABCN])\s+(?P<frame>\d+)\s+"
        r"(?P<trip>TM[A-Z]+)\s+(?P<In>\d+(?:[.,]\d+)?)"
        r"(?:-(?P<setting>\d+(?:[.,]\d+)?))?\b",
        model, re.IGNORECASE,
    )
    if tmax:
        fields.update({
            "serie": tmax.group("serie").upper(),
            "frame": tmax.group("frame"),
            "trip": tmax.group("trip").upper(),
            "In": tmax.group("In").replace(".", ","),
        })
        if tmax.group("setting"):
            fields["setting"] = tmax.group("setting").replace(".", ",")
    rating = re.search(rules["ratingPattern"], block)
    if rating:
        ka = rating.group(3)
        fields["kA"] = ka
        fields["Icn"] = str(int(round(float(ka.replace(",", ".")) * 1000)))
    return fields


def find_series(model, poles, catalog):
    """Devuelve (serie, carcasa, motivo). Exige modelo y polos admitidos por la serie."""
    shells = {s["id"]: s for s in catalog["deviceShells"]}
    same_family = []
    for serie in catalog.get("series", []):
        if "modelRegex" not in serie or not re.search(serie["modelRegex"], model, re.IGNORECASE):
            continue
        same_family.append(serie)
        if poles is None or poles in serie["poles"]:
            return serie, shells[serie["shell"]], None
    if same_family:
        known = sorted({p for s in same_family for p in s["poles"]})
        return None, None, f"serie en catálogo, pero sin carcasa de {poles}P (hay: {known})"
    return None, None, "serie sin carcasa en el catálogo"


CIRCUIT_RE = re.compile(r"^[A-Z][A-Z0-9]*-\d+(?:\.\d+)*$")


USE_CODES = {"IUG", "TUG", "IUE", "TUE", "OCE", "ACU", "ALIM"}


def circuit_name(tag, block, lines=14):
    """Nombre del circuito (columna 'Circuito' de la tabla del unifilar, ej. TS-4.2) de un interruptor QF.
    1) La celda que sigue al código de uso (IUG/TUG/IUE/TUE/OCE/ACU/ALIM). 2) Si el plano no trae el código de uso, la primera
    celda con forma LETRAS-número[.número]. None si el plano no trae el circuito."""
    if not str(tag).startswith("QF"):
        return None
    cells = [c.strip() for c in block.splitlines()[:lines]]
    for n, cell in enumerate(cells[:-1]):
        if cell in USE_CODES and cells[n + 1]:
            return cells[n + 1]
    for cell in cells:
        if CIRCUIT_RE.match(cell):
            return cell
    return None


def detect_devices(text, catalog):
    """Extrae etiquetas, modelo, polos y carcasa propuesta; conserva el texto original para revisar."""
    rules = catalog["importRules"]
    hints = catalog.get("modelHints", [])
    matches = list(re.finditer(rules["tagPattern"], text))
    found = []
    for index, match in enumerate(matches):
        before = text[max(0, match.start() - rules["upstreamContextChars"]):match.start()]
        upstream = bool(re.search(rules["upstreamPattern"], before, re.IGNORECASE))
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end():end]
        snippet = " ".join(block[:rules["evidenceChars"]].split())
        model = parse_model(snippet, rules)
        poles = _first_group(rules["polesPatterns"], block)
        if poles is None:  # sin tabla (ej. interruptor general): fases del cable de salida, línea "RSTN"/"RST"/"RN"
            phases = next((ln.strip() for ln in block.splitlines()[:8] if re.fullmatch(r"[RST]{1,3}N?", ln.strip())), None)
            poles = len(phases) if phases else None
        serie, shell, reason = find_series(model, poles, catalog)
        hint = next((h for h in hints if re.search(h["modelRegex"], model, re.IGNORECASE)), None)
        min_poles = catalog.get("scope", {}).get("minPoles")
        if upstream:
            status = "alimentador externo; no pertenece al tablero"
        elif min_poles and poles is not None and poles < min_poles:
            shell, serie = None, None
            status = f"monopolar: fuera de alcance (mínimo {min_poles} polos)"
        elif shell:
            status = "detectado; revisar modelo y polos" if serie["verified"] else "detectado; carcasa compartida sin confirmar"
        elif hint:
            status = hint["note"]
        else:
            status = reason
        if poles is None and not upstream:
            status += "; polos no indicados en el plano"
        width, height = shell_size(shell, poles) if shell else (80, 100)
        found.append({
            "tag": match.group(1), "circuit": circuit_name(match.group(1), block), "evidence": snippet, "shell": shell and shell["id"],
            "series": serie and serie["id"], "model": model[:40], "poles": poles,
            "marking": marking_fields(model, block, rules),
            "w": width, "h": height,
            "status": status, "upstream": upstream,
            **({"mounting": hint["mounting"]} if hint and not shell else {}),
        })
    return found


def detect_signals(text, catalog):
    """Bloque de señalización del unifilar: luces testigo de presencia de tensión por fase y sus fusibles (van en la puerta)."""
    pattern = catalog["importRules"].get("signalPattern")
    m = re.search(pattern, " ".join(text.split()), re.IGNORECASE) if pattern else None
    if not m:
        return None
    n = int(m.group("n"))
    phases = list(m.group("fases"))[:n] if len(m.group("fases")) >= n else [f"L{i + 1}" for i in range(n)]
    return {"pilotLights": [{"label": p, "function": "presencia de tensión", "voltage": m.group("v")} for p in phases],
            "fuses": {"count": n, "type": m.group("fusible").lower(), "rating": m.group("fusA").replace(" ", " ")},
            "evidence": m.group(0)[:160]}


def ensure_marking(device, catalog):
    """Proyectos guardados antes del marcado: deduce los datos impresos del modelo (y de la evidencia, si está)."""
    if "marking" not in device and device.get("model"):
        device["marking"] = marking_fields(device["model"], device.get("evidence", ""), catalog["importRules"])
    return device

CORRECTIONS_FILE = Path(__file__).resolve().parent / "datos" / "correcciones_unifilar.json"


def _model_key(model):
    return re.sub(r"[\s\-]+", "", str(model or "")).upper()


def apply_corrections(devices, board, catalog, corrections=None):
    """Cambios de equipo pedidos por el usuario para un tablero puntual (datos/correcciones_unifilar.json).
    Se aplica sólo si coinciden tablero, etiqueta y modelo del PDF; el equipo se vuelve a buscar en el catálogo con el
    modelo nuevo (carcasa, medidas, marcado) y queda marcado con correctedFrom. Devuelve las correcciones de este
    tablero que no encontraron su equipo (el PDF cambió): las avisa la auditoría."""
    if corrections is None:
        try:
            corrections = json.loads(CORRECTIONS_FILE.read_text(encoding="utf-8")).get("items", [])
        except (OSError, ValueError):
            corrections = []
    title = (board or {}).get("title")
    mine = [c for c in corrections if title and c["board"] == title]
    unused = []
    for c in mine:
        d = next((d for d in devices if d["tag"] == c["tag"] and _model_key(d.get("model")) == _model_key(c["fromModel"])), None)
        if d is None:
            unused.append(c)
            continue
        serie, shell, reason = find_series(c["model"], c["poles"], catalog)
        d["correctedFrom"] = {"model": d.get("model"), "poles": d.get("poles"), "reason": c["reason"], "date": c["date"]}
        d.update(model=c["model"], poles=c["poles"], shell=shell and shell["id"], series=serie and serie["id"],
                 marking=marking_fields(c["model"], d.get("evidence", ""), catalog["importRules"]))
        d["w"], d["h"] = shell_size(shell, c["poles"]) if shell else (80, 100)
        d["status"] = (f"modelo cambiado por pedido del usuario: el unifilar dice {d['correctedFrom']['model']} ({d['correctedFrom']['poles']}P)"
                       if shell else f"corrección sin carcasa: {reason}")
    return unused


def detect_board(text):
    """Rótulo del tablero en el unifilar e-Design: 1.ª línea = nombre, 2.ª = «DE <tablero> - -QFn <modelo>», 3.ª = cable de alimentación.
    Devuelve {"title", "feeder": {...}} o None si el PDF no trae ese encabezado (no se adivina)."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()][:4]
    if len(lines) < 2 or not lines[1].upper().startswith("DE "):
        return None
    feeder = {"from": None, "upstreamTag": None, "upstreamModel": None, "cable": None, "peMm2": None, "peParallel": None}
    head = re.match(r"DE\s+(?P<src>.+?)\s+-\s+-?(?P<tag>Q[A-Z]\d+)\s+(?P<model>.+)$", lines[1])
    if head:
        feeder.update({"from": head.group("src"), "upstreamTag": head.group("tag"), "upstreamModel": head.group("model").strip()})
    else:
        feeder["from"] = lines[1][3:].strip(" -")
    if len(lines) > 2 and re.match(r"-?WC\d+", lines[2]):
        feeder["cable"] = lines[2].lstrip("-")
        pe = re.search(r"(?:(\d+)x)?PE\s?(\d+(?:[.,]\d+)?)", lines[2])
        if pe:
            feeder["peParallel"] = int(pe.group(1) or 1)
            feeder["peMm2"] = float(pe.group(2).replace(",", "."))
    return {"title": lines[0], "feeder": feeder}


def _norm_board_key(name):
    return re.sub(r"[^A-Z0-9]+", "", str(name or "").upper())


def _parse_pe_from_cable(cable, pattern):
    m = re.search(pattern, str(cable or ""))
    if not m:
        return None, None
    return int(m.group(1) or 1), float(m.group(2).replace(",", "."))


def detect_edesign_report(pdf_bytes, catalog):
    """Importa un informe completo PDF de ABB e-Design DOC (múltiples tableros en un archivo).
    Combina: esquemas unifilares (barras -B#), informe de cables/protecciones (polos y cable/PE)
    y 'Lista de aparatos de BT' (modelo exacto, código ABB y circuito).
    Devuelve None si el PDF no es un informe multi-tablero de e-Design DOC (p. ej. unifilar AutoCAD de 1 tablero)."""
    rules = catalog["importRules"]
    cfg = rules.get("edesignReport")
    if not cfg:
        return None
    import pymupdf
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    header = cfg["apparatusHeader"]
    app_pages = [p for p in range(len(doc)) if header in (doc[p].get_text("text") or "")]
    if not app_pages:
        return None

    tag_re = re.compile(r"^-?(Q[A-Z]\d+)$")
    bus_re = re.compile(f"^{cfg['busPattern']}$")
    wc_re = re.compile(f"^{cfg['cablePattern']}$")
    sys_poles = cfg["systemPoles"]
    sys_re = re.compile(r"^(" + "|".join(re.escape(k) for k in sorted(sys_poles, key=len, reverse=True)) + r")\s*/\s*TN")
    cols_cfg = cfg["apparatusColumns"]
    row_tol = cfg["rowToleranceY"]

    # 1) Lista de aparatos de BT: símbolo -> código ABB, modelo, circuito (desc1) y descripción (desc2).
    apparatus = {}
    for p in app_pages:
        by_y = {}
        for w in doc[p].get_text("words"):
            ky = next((k for k in by_y if abs(k - w[1]) < row_tol), round(w[1], 1))
            by_y.setdefault(ky, []).append(w)
        for _y, ws in sorted(by_y.items()):
            ws.sort(key=lambda w: w[0])
            m = tag_re.fullmatch(ws[0][4]) if ws else None
            if not m:
                continue
            tag = m.group(1)
            code, model, desc1, desc2 = [], [], [], []
            for w in ws[1:]:
                x = w[0]
                if x < cols_cfg["codeMaxX"]:
                    code.append(w[4])
                elif x < cols_cfg["modelMaxX"]:
                    model.append(w[4])
                elif cols_cfg["desc1MinX"] <= x < cols_cfg["desc1MaxX"]:
                    desc1.append(w[4])
                elif x >= cols_cfg["desc1MaxX"]:
                    desc2.append(w[4])
            apparatus[tag] = {
                "orderCode": " ".join(code).strip() or None,
                "model": " ".join(model).strip(),
                "desc1": " ".join(desc1).strip(),
                "desc2": " ".join(desc2).strip(),
            }

    # 2) Páginas de verificación de cables/protecciones: sistema (polos) y cable/PE por etiqueta.
    markers = tuple(cfg["protectionMarkers"])
    sys_map = {}
    for p in range(len(doc)):
        txt = doc[p].get_text("text") or ""
        if not any(mk in txt for mk in markers):
            continue
        lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
        for i, ln in enumerate(lines):
            if not wc_re.fullmatch(ln):
                continue
            chunk = lines[max(0, i - 28):i + 1]
            qfs = [tag_re.fullmatch(c).group(1) for c in chunk if tag_re.fullmatch(c)]
            if not qfs:
                continue
            sys_m = [sys_re.match(c) for c in chunk if sys_re.match(c)]
            cables = [c for c in chunk if re.match(r"^\d+x\(", c)]
            cable = cables[-1] if cables else None
            pe_par, pe_mm2 = _parse_pe_from_cable(cable, cfg["peCablePattern"])
            sys_map[qfs[-1]] = {
                "system": sys_m[-1].group(0) if sys_m else None,
                "poles": sys_poles[sys_m[-1].group(1)] if sys_m else None,
                "cable": cable,
                "peParallel": pe_par,
                "peMm2": pe_mm2,
                "wc": ln.lstrip("-"),
            }

    # 3) Páginas de esquema unifilar (cada página con barra -B# es un tablero).
    hints = catalog.get("modelHints", [])
    min_poles = catalog.get("scope", {}).get("minPoles")
    main_kw = re.compile(r"\b(" + "|".join(map(re.escape, rules.get("mainDeviceKeywords", []))) + r")\b", re.IGNORECASE)
    boards = []
    seen_all_tags = set()
    for p in range(len(doc)):
        words = doc[p].get_text("words")
        buses = [w for w in words if bus_re.fullmatch(w[4])]
        if not buses:
            continue
        bus_y = buses[0][1]
        title_ws = [w for w in words if abs(w[1] - (bus_y + cfg["titleOffsetY"])) <= cfg["titleToleranceY"]]
        title = " ".join(w[4] for w in sorted(title_ws, key=lambda w: w[0])).strip()
        if not title:
            fb = cfg.get("mainBoardFallback", "TGBT")
            title = fb if any(w[4] == fb for w in words) else f"Tablero {p + 1}"
        q_ws = [w for w in words if tag_re.fullmatch(w[4])]
        above = sorted([w for w in q_ws if w[1] < bus_y], key=lambda w: w[0])
        below = sorted([w for w in q_ws if w[1] >= bus_y], key=lambda w: w[0])
        seen, devs = set(), []
        issues, unverified, checked = [], [], 0
        for is_above, w in [(True, x) for x in above] + [(False, x) for x in below]:
            tag = tag_re.fullmatch(w[4]).group(1)
            if tag in seen:
                continue
            seen.add(tag)
            seen_all_tags.add(tag)
            info = apparatus.get(tag)
            sm = sys_map.get(tag, {})
            model = (info or {}).get("model", "")
            desc1 = (info or {}).get("desc1", "")
            desc2 = (info or {}).get("desc2", "")
            order_code = (info or {}).get("orderCode")
            poles = sm.get("poles") or _first_group(rules["polesPatterns"], model)
            is_entry = is_above or (not above and bool(main_kw.search(desc1)))
            circuit = None if is_entry else (desc1 or None)
            evidence = " ".join(x for x in (model, desc1, desc2, sm.get("cable")) if x)
            serie, shell, reason = find_series(model, poles, catalog)
            hint = next((h for h in hints if re.search(h["modelRegex"], model, re.IGNORECASE)), None)
            if min_poles and poles is not None and poles < min_poles:
                shell, serie = None, None
                status = f"monopolar: fuera de alcance (mínimo {min_poles} polos)"
            elif shell:
                status = "detectado; revisar modelo y polos" if serie["verified"] else "detectado; carcasa compartida sin confirmar"
            elif hint:
                status = hint["note"]
            else:
                status = reason or "sin modelo en Lista de aparatos de BT"
            if poles is None:
                status += "; polos no indicados en el plano"
            width, height = shell_size(shell, poles) if shell else (80, 100)
            dev = {
                "tag": tag, "circuit": circuit, "evidence": evidence[:160],
                "shell": shell and shell["id"], "series": serie and serie["id"],
                "model": model[:40], "poles": poles,
                "marking": marking_fields(model, evidence, rules),
                "w": width, "h": height, "status": status, "upstream": False,
                **({"orderCode": order_code, "orderCodeSource": "edesign"} if order_code else {}),
                **({"description": desc2} if desc2 else {}),
                **({"mounting": hint["mounting"]} if hint and not shell else {}),
            }
            devs.append(dev)
            if info and model and poles:
                checked += 1
            else:
                unverified.append({"circuit": circuit or tag, "tag": tag, "message": "faltan datos en Lista de aparatos de BT o tabla de cables"})
        boards.append({
            "page": p + 1, "bus": buses[0][4], "title": title, "devices": devs,
            "feeder": None, "verification": {"checked": checked, "issues": issues, "unverified": unverified},
        })

    if not boards:
        return None

    # 4) Alimentador de cada tablero (desde la salida del tablero padre que lo alimenta, o desde la entrada del TGBT).
    outgoing_by_key = {}
    for b in boards:
        for d in b["devices"]:
            if not d.get("circuit"):
                continue
            sm = sys_map.get(d["tag"], {})
            if sm.get("cable"):
                entry = {"from": b["title"], "upstreamTag": d["tag"], "upstreamModel": d["model"],
                         "cable": sm["cable"], "peMm2": sm["peMm2"], "peParallel": sm["peParallel"]}
                k = _norm_board_key(d["circuit"])
                outgoing_by_key.setdefault(k, entry)
                outgoing_by_key.setdefault(k.replace("L", "I"), entry)  # tolera errata TSl2 vs TSI2 en e-Design
    for b in boards:
        k = _norm_board_key(b["title"])
        feeder = outgoing_by_key.get(k) or outgoing_by_key.get(k.replace("L", "I"))
        if feeder:
            b["feeder"] = dict(feeder)
        elif b["devices"]:
            first_sm = sys_map.get(b["devices"][0]["tag"], {})
            if first_sm.get("cable") and not b["devices"][0].get("circuit"):
                b["feeder"] = {"from": "Alimentación principal", "upstreamTag": None, "upstreamModel": None,
                               "cable": first_sm["cable"], "peMm2": first_sm["peMm2"], "peParallel": first_sm["peParallel"]}

    unmatched = sorted(set(apparatus) - seen_all_tags)
    return {
        "multiBoard": True,
        "pages": len(doc),
        "boards": boards,
        "totalDevices": sum(len(b["devices"]) for b in boards),
        "apparatusCount": len(apparatus),
        "unmatchedApparatus": unmatched,
    }
