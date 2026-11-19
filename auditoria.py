"""Auditoría de armado: los errores que un armador de tableros marcaría al revisar el frente.

Nació de la revisión de los 24 tableros del plano GENERAL (2026-11-19, ver docs/LECCIONES.md).
Cada regla tiene un código estable; validacion.validate() suma estos hallazgos para que la
interfaz los muestre y los tests (tests/test_auditoria.py) impidan que vuelvan.

No inventa datos: si falta una corriente o una medida, la regla se saltea o avisa que falta.
"""
from __future__ import annotations

import re

MONOPOLAR_STATUS = "monopolar"


def _f(level, code, message, tags=()):
    return {"level": level, "code": code, "message": message, "tags": list(tags), "origen": "auditoria"}


def rated_current(device):
    """Corriente nominal en A leída del frente/modelo/plano. None si no se puede leer sin adivinar."""
    marking = device.get("marking") or {}
    raw = marking.get("In")
    if raw:
        try:
            return float(str(raw).replace(",", "."))
        except ValueError:
            pass
    model = str(device.get("model") or "")
    patterns = (
        r"^E\d\.\d[A-Z]\s+(\d+)",            # Emax 2: E2.2N 2000
        r"\b(\d+)\s*A\s*$",                  # Tmax T con relé electrónico: ... 320A
        r"^XT\d[A-Z]?\s+\d+\s+TM[A-Z]+\s+(\d+)",  # Tmax XT: XT1S 160 TMD 125-1250 -> 125
        r"^OT\s?(\d+)",                      # OT100F4
        r"-\s?[BCDKZ]\s?(\d+(?:[.,]\d+)?)\b",  # S804S-C100, S 293-C 80
    )
    for pattern in patterns:
        found = re.search(pattern, model, re.IGNORECASE)
        if found:
            return float(found.group(1).replace(",", "."))
    found = re.search(r"\b\dx(\d+)\s*-\s*\d", str(device.get("evidence") or ""))  # columna "I Nom - Icc": 3x80 - 10kA
    return float(found.group(1)) if found else None


def main_device(project):
    """El interruptor/seccionador de entrada: QS*, o el que el plano llama PRINCIPAL/GENERAL, o el único sin circuito."""
    devices = project.get("devices", [])
    for d in devices:
        if str(d.get("tag", "")).startswith("QS"):
            return d
    for d in devices:
        if re.search(r"\b(PRINCIPAL|GENERAL|SECCIONADOR)\b", str(d.get("evidence") or ""), re.IGNORECASE):
            return d
    sin_circuito = [d for d in devices if not d.get("circuit")]
    return sin_circuito[0] if len(sin_circuito) == 1 else None


def _rows(items):
    """Agrupa cajas que se solapan en altura (y hacia arriba) en filas, de arriba hacia abajo."""
    rows = []
    for b in sorted(items, key=lambda b: -(b["y"] + b["h"])):
        top, bottom = b["y"] + b["h"], b["y"]
        if rows and top > rows[-1]["bottom"] + 1e-6:
            rows[-1]["items"].append(b)
            rows[-1]["bottom"] = min(rows[-1]["bottom"], bottom)
            rows[-1]["top"] = max(rows[-1]["top"], top)
        else:
            rows.append({"top": top, "bottom": bottom, "items": [b]})
    return rows


def _natural(text):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(text or ""))]


def audit(project, catalog, rules=None, board_title=None):
    rules = rules or {}
    out = []
    devices = [d for d in project.get("devices", []) if d.get("x") is not None]
    accessories = [a for a in project.get("accessories", []) if a.get("placed", True) and a.get("x") is not None and a.get("w")]
    enclosure = project.get("enclosure", {})
    fh = enclosure.get("functional", {}).get("height", 0)
    shells = {s["id"]: s for s in catalog.get("deviceShells", [])}
    main = main_device(project)

    # A1 · el equipo de entrada va arriba (y solo en su fila si es de kit).
    if main and devices:
        top_row = _rows(devices)[0]
        if main not in top_row["items"]:
            out.append(_f("error", "main_not_on_top", f"{main['tag']} es el equipo de entrada y no está en la fila de arriba.", [main["tag"]]))
        elif shells.get(main.get("shell"), {}).get("mounting") != "din" and len(top_row["items"]) > 1:
            others = [d["tag"] for d in top_row["items"] if d is not main]
            out.append(_f("error", "main_shares_row", f"{main['tag']} (entrada) comparte la fila con {', '.join(others)}: el general va solo arriba.", [main["tag"], *others]))

    # A2 · orden del unifilar: de izquierda a derecha y de arriba hacia abajo, por circuito.
    order = {d["tag"]: i for i, d in enumerate(project.get("devices", []))}
    def din(d):
        return shells.get(d.get("shell"), {}).get("mounting") == "din" or d.get("mounting") == "din"
    ordered = [d for row in _rows(devices) for d in sorted(row["items"], key=lambda d: d["x"]) if d is not main]
    # Cajas moldeadas y equipos de riel van en bloques distintos: el orden se exige dentro de cada bloque.
    seq = [d for d in ordered if not din(d)] + [d for d in ordered if din(d)]
    keys = [order.get(d["tag"], 0) for d in seq]  # el orden de referencia es el del unifilar (orden de lectura del PDF)
    name = lambda d: d.get("circuit") or d["tag"]
    inversions = [f"{name(seq[i])} antes que {name(seq[i + 1])}" for i in range(len(seq) - 1) if keys[i] > keys[i + 1] and din(seq[i]) == din(seq[i + 1])]
    if inversions:
        out.append(_f("error", "order_not_unifilar", f"Los circuitos no siguen el orden del unifilar: {'; '.join(inversions[:4])}{' …' if len(inversions) > 4 else ''}.",
                      [d["tag"] for d in seq]))

    # A3 · cada fila de equipos tiene canaleta arriba y abajo (para cablear): entre la fila y la vecina (o el borde) tiene que haber una.
    ducts = [a for a in accessories if a.get("type") == "wiring_duct" and a.get("orientation") == "h"]
    if ducts:
        drows = _rows(devices)
        for k, row in enumerate(drows):
            xs = (min(d["x"] for d in row["items"]), max(d["x"] + d["w"] for d in row["items"]))
            ceiling = drows[k - 1]["bottom"] if k else fh
            floor = drows[k + 1]["top"] if k + 1 < len(drows) else 0
            def covered(du):
                return du["x"] <= xs[0] + 1 and du["x"] + du["w"] >= xs[1] - 1
            above = any(covered(du) and du["y"] >= row["top"] - 1 and du["y"] + du["h"] <= ceiling + 1 for du in ducts)
            below = any(covered(du) and du["y"] + du["h"] <= row["bottom"] + 1 and du["y"] >= floor - 1 for du in ducts)
            tags = [d["tag"] for d in row["items"]]
            if not above:
                out.append(_f("error", "row_without_duct_above", f"La fila de {', '.join(tags[:3])}{'…' if len(tags) > 3 else ''} no tiene canaleta arriba.", tags))
            if not below:
                out.append(_f("error", "row_without_duct_below", f"La fila de {', '.join(tags[:3])}{'…' if len(tags) > 3 else ''} no tiene canaleta abajo.", tags))

    # A4 · hueco muerto entre filas (el gabinete quedó grande o la fila se armó lejos).
    boxes = devices + [a for a in accessories if a.get("type") not in ("wiring_duct", "copper_busbar", "pe_bar")]  # las barras van al borde a propósito
    rows = _rows([{**b} for b in boxes])
    limit = rules.get("maxGapBetweenRowsMm", 200)
    for upper, lower in zip(rows, rows[1:]):
        gap = upper["bottom"] - lower["top"]
        if gap > limit:
            out.append(_f("error", "dead_gap_between_rows", f"Quedan {gap:.0f} mm vacíos entre dos filas de equipos (máximo {limit} mm): el armado dejó un hueco en el medio.", []))

    # A12 · gabinete sobredimensionado: el contenido ocupa menos de la mitad de la placa en altura
    # (lección 2026-11-19: TSMAQ1 y TS AUX 3 en 800×800 con una sola fila de riel).
    content = [b for b in boxes]
    min_ratio = rules.get("minHeightUseRatio", 0.40)
    if content and fh > rules.get("oversizeCheckFromMm", 400):
        span = max(b["y"] + b["h"] for b in content) - min(b["y"] for b in content)
        if span / fh < min_ratio:
            # Aviso (no error): el usuario puede elegir a propósito un gabinete más grande (reserva, obra futura).
            out.append(_f("warning", "board_oversized", f"El contenido ocupa {span:.0f} de {fh:.0f} mm de alto ({span / fh:.0%}): el gabinete es más grande de lo necesario.", []))

    # A5 · barra/bloque de distribución dimensionado por la entrada, no por la salida más grande.
    feed = rated_current(main) if main else None
    for a in project.get("accessories", []):
        if a.get("type") in ("copper_busbar", "distribution_block") and a.get("corrienteA") and feed and a["corrienteA"] < feed:
            out.append(_f("error", "busbar_undersized", f"{a.get('label')} ({a['corrienteA']:g} A) distribuye lo que entra por {main['tag']} ({feed:g} A).", [main["tag"]]))

    # A13 · una barra de neutro/tierra no reparte fases (lección 19: AA8010 propuesta como barra de distribución).
    if any(a.get("type") == "copper_busbar" and a.get("catalogId") == "abb-aa8010" and a.get("devices") for a in project.get("accessories", [])):
        out.append(_f("error", "neutral_bar_as_phase", "Se propuso la AA8010 (barra de neutro o tierra) para repartir fases.", []))

    # A6 · bornera PE: entrada que admita el PE de alimentación y una salida por circuito.
    pe_items = [a for a in project.get("accessories", []) if a.get("type") == "pe_terminal"]
    circuits = [d for d in project.get("devices", []) if str(d.get("tag", "")).startswith("QF")] + list(project.get("devicesNotDrawn", []))
    for a in pe_items:
        outs = (a.get("outputs") or 0) * (a.get("blocks") or 0) or a.get("count") or 0
        if outs and outs < len(circuits):
            out.append(_f("error", "pe_outputs_short", f"{a.get('label')}: {outs} salidas PE para {len(circuits)} circuitos.", []))
    pe_feed = (project.get("feeder") or {}).get("peMm2")
    max_in = 0
    if pe_items:
        from accesorios import load_accessory_catalog, pe_input_max_mm2
        terms = {t["id"]: t for t in load_accessory_catalog().get("earthTerminals", [])}
        max_in = max((pe_input_max_mm2(terms.get(t.get("catalogId"))) or 0 for t in pe_items), default=0)
    has_bar = any(a.get("type") == "pe_bar" for a in project.get("accessories", []))
    if pe_feed and pe_items and max_in and pe_feed > max_in and not has_bar:
        out.append(_f("error", "pe_input_undersized", f"El PE de alimentación es de {pe_feed:g} mm² y la bornera PE admite hasta {max_in:g} mm²: hace falta barra de tierra.", []))

    # A7 · un equipo sin dibujar (que no sea monopolar) deja el tablero chico: no hay lugar reservado.
    for d in project.get("devicesNotDrawn", []):
        if MONOPOLAR_STATUS not in str(d.get("status", "")).lower():
            out.append(_f("error", "not_drawn_no_space", f"{d.get('tag')} ({d.get('model')}) no está dibujado y no tiene lugar reservado: el gabinete puede quedar chico.", [d.get("tag")]))

    # A8 · restos de la plantilla (otro tablero) dentro del proyecto.
    families = {f"{d.get('series') or ''} {d.get('shell') or ''} {d.get('model') or ''}".lower() for d in project.get("devices", [])}
    for kit in (project.get("conceptualAssembly") or {}).get("mountingKits", []) or []:
        fam = str(kit.get("deviceFamily", "")).split()[0].lower()
        if fam and not any(fam in f for f in families):
            out.append(_f("error", "stale_template_data", f"El proyecto arrastra el kit {kit.get('type')} ({kit.get('deviceFamily')}) de otro tablero.", []))
            break

    # A11 · en System pro E cada caja moldeada necesita su kit de montaje (si no, la lista queda incompleta).
    if "System pro E" in str(enclosure.get("line", "")):
        sin_kit = [d["tag"] for d in devices if shells.get(d.get("shell"), {}).get("mounting") != "din" and not d.get("mountingKit")]
        if sin_kit:
            out.append(_f("error", "spe_kit_missing", f"En System pro E falta el kit de montaje de {', '.join(sin_kit)}.", sin_kit))

    # A9 · nombre del tablero = el del rótulo del unifilar.
    if board_title and project.get("project") != board_title:
        out.append(_f("warning", "board_name_mismatch", f"El tablero se llama «{project.get('project')}» y el unifilar dice «{board_title}».", []))

    # A10 · etiquetas que se pisan (texto ilegible en el plano).
    labels = [{"x": d["x"], "y": d["y"] - 14, "w": d["w"], "h": 14, "tag": d["tag"]} for d in devices]
    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            if a["x"] < b["x"] + b["w"] - 0.5 and b["x"] < a["x"] + a["w"] - 0.5 and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]:
                out.append(_f("error", "labels_overlap", f"Las etiquetas de {a['tag']} y {b['tag']} se pisan.", [a["tag"], b["tag"]]))
    return out
