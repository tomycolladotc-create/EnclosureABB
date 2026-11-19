"""Textos que describen un gabinete: una sola regla para el subtítulo del dibujo, la lista de materiales y el editor.

Lección 27 (2026-11-19): las etiquetas estaban escritas a mano en el catálogo y mezclaban órdenes: el SR2 decía
«300 × 400 × 150 (placa 360 × 260)» (gabinete alto × ancho, placa ancho × alto) y el System pro E power «750 × 1800 × 500»
(ancho × alto). Ahora cada medida lleva su nombre y el orden es siempre alto × ancho × profundidad.
"""


def enclosure_label(spec):
    """«ABB SR2 SRN3415K · alto 300 × ancho 400 × prof. 150 mm · placa alto 260 × ancho 360 mm».
    `nominal` es la medida comercial del catálogo ABB; `functional` el área de montaje (placa o estructura)."""
    n, f = spec["nominal"], spec["functional"]
    head = f"{spec['labelPrefix']} · alto {n['height']:g} × ancho {n['width']:g} × prof. {n['depth']:g} mm"
    if spec.get("family") == "SR2":
        head += f" · placa alto {f['height']:g} × ancho {f['width']:g} mm"
    return head


def label_boxes(devices, plate_width, rules):
    """Portaetiquetas de los equipos (coordenadas de placa, mm): [{"x", "w", "font"}] en el orden de `devices`.
    1) ancho = el del equipo (−2·pad), entre minWidthMm y maxWidthMm; la letra, la que entra, hasta fontMaxMm;
    2) si la letra quedaría por debajo de fontMinMm, se ensancha la etiqueta para escribirla con fontMinMm;
    3) en cada fila (equipos con la misma base) las etiquetas se acomodan de izquierda a derecha sin pisarse,
       lo más centradas posible bajo su equipo y dentro de la placa.
    La misma regla está en web/index.html (labelBoxes) y el test test_etiquetas_iguales_en_python_y_en_el_editor
    comprueba que den lo mismo."""
    r = rules
    out = []
    for d in devices:
        name = str(d.get("circuit") or d.get("tag") or "")
        n = max(len(name), 1)
        w = min(max(d["w"] - 2 * r["padMm"], r["minWidthMm"]), r["maxWidthMm"])
        font = min(r["fontMaxMm"], (w - r["padMm"]) / (n * r["charWidth"]))
        if font < r["fontMinMm"]:
            font = r["fontMinMm"]
            w = min(n * r["charWidth"] * font + r["padMm"] * 2, r["maxWidthMm"])
            font = min(font, (w - r["padMm"]) / (n * r["charWidth"]))
        out.append({"x": d["x"] + (d["w"] - w) / 2, "w": w, "font": round(font, 2), "row": round(d["y"], 1)})
    rows = {}
    for i, b in enumerate(out):
        rows.setdefault(b["row"], []).append(i)
    for idx in rows.values():
        idx.sort(key=lambda i: out[i]["x"] + out[i]["w"] / 2)
        lo, hi = 0.0, float(plate_width)
        right = lo - r["betweenMm"]
        for i in idx:  # de izquierda a derecha: nunca antes que el borde derecho de la anterior
            out[i]["x"] = max(out[i]["x"], right + r["betweenMm"], lo)
            right = out[i]["x"] + out[i]["w"]
        left = hi + r["betweenMm"]
        for i in reversed(idx):  # de derecha a izquierda: nunca fuera de la placa ni encima de la siguiente
            out[i]["x"] = min(out[i]["x"], left - r["betweenMm"] - out[i]["w"])
            left = out[i]["x"]
    for b in out:
        b["x"] = round(b["x"], 2)
        b["w"] = round(b["w"], 2)
        del b["row"]
    return out
