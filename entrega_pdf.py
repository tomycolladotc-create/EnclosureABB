"""PDF único de entrega (Exportar → «PDF de entrega»).

Un solo PDF con carátula, índice de documentación, los frentes y las puertas de todos los tableros,
planos de taller opcionales y el cómputo consolidado de equipamiento, con páginas numeradas,
tipografía TrueType prolija (Segoe UI con fallbacks del sistema) y rótulo técnico de esquina
inferior derecha sin logos de marcas comerciales (o el formato DXF propio si el usuario lo cargó).

Cada hoja de tablero se dibuja desde el mismo DXF que exporta el programa (plano_unifilar.split_views):
mismas formas, pinturas y textos. ezdxf lo dibuja a SVG y PyMuPDF lo pasa a PDF vectorial; el SVG de
ezdxf pone los colores en clases CSS que el lector de PyMuPDF no aplica, por eso se copian a cada
elemento (_inline_css).
Medidas, tipografía, paleta y campos del rótulo: datos/reglas_layout.json → entregaPdf.
"""
import json
import os
import re
from pathlib import Path

import pymupdf
from ezdxf import bbox
from ezdxf.addons.drawing import Frontend, RenderContext, layout, svg
from ezdxf.addons.drawing.properties import LayoutProperties

import rutas
from excel_equipamiento import collect
from plano_unifilar import RULES as PLANO_RULES
from plano_unifilar import split_views

RULES = rutas.read_json("reglas_layout.json")["entregaPdf"]
MM = 72 / 25.4  # puntos PDF por mm
_FONT_CACHE = None


def _font_dirs():
    dirs = []
    win = os.environ.get("WINDIR")
    if win:
        dirs.append(Path(win) / "Fonts")
    local = os.environ.get("LOCALAPPDATA")
    if local:
        dirs.append(Path(local) / "Microsoft" / "Windows" / "Fonts")
    dirs.extend([Path("/usr/share/fonts"), Path("/System/Library/Fonts")])
    return [d for d in dirs if d.is_dir()]


def _resolve_fonts():
    """Resuelve fuentes TrueType del sistema (Segoe UI → Calibri → Arial → fallback PDF base)."""
    global _FONT_CACHE
    if _FONT_CACHE is not None:
        return _FONT_CACHE
    typo = RULES.get("typography") or {}
    dirs = _font_dirs()
    fallbacks = {"regular": "helv", "semibold": "hebo", "bold": "hebo", "mono": "cour"}
    resolved = {}
    for role, base_fb in fallbacks.items():
        path = None
        for fname in typo.get(role, []):
            for d in dirs:
                cand = d / fname
                if cand.is_file():
                    path = cand
                    break
            if path is not None:
                break
        if path is not None:
            resolved[role] = {"name": f"enc_{role}", "path": str(path), "font": pymupdf.Font(fontfile=str(path))}
        else:
            resolved[role] = {"name": base_fb, "path": None, "font": pymupdf.Font(base_fb)}
    _FONT_CACHE = resolved
    return resolved


def _register_fonts(page):
    for spec in _resolve_fonts().values():
        if spec["path"]:
            page.insert_font(fontname=spec["name"], fontfile=spec["path"])


def _fname(role="regular"):
    return _resolve_fonts()[role]["name"]


def _text_len_mm(text, size_mm, role="regular"):
    spec = _resolve_fonts()[role]
    return spec["font"].text_length(str(text), fontsize=size_mm * MM) / MM


def _color(key, default=(0.1, 0.13, 0.18)):
    colors = (RULES.get("typography") or {}).get("colors") or {}
    val = colors.get(key)
    return tuple(val) if val else default


def _fit_size(text, max_w_mm, start_mm, min_mm=1.4, role="regular"):
    size = start_mm
    while size > min_mm and _text_len_mm(text, size, role) > max_w_mm:
        size = round(size - 0.12, 2)
    return max(size, min_mm)


def _draw_text(page, x_mm, y_mm, text, size_mm, role="regular", color=None, align="left", max_w_mm=None, min_mm=1.4, rotate=0):
    text = str(text or "")
    if not text:
        return
    col = _color("ink") if color is None else color
    if max_w_mm is not None and rotate == 0:
        size_mm = _fit_size(text, max_w_mm, size_mm, min_mm=min_mm, role=role)
    w_mm = _text_len_mm(text, size_mm, role)
    tx = x_mm
    if rotate == 0:
        if align == "center":
            tx = x_mm - w_mm / 2
        elif align == "right":
            tx = x_mm - w_mm
    page.insert_text((tx * MM, y_mm * MM), text, fontsize=size_mm * MM, fontname=_fname(role), color=col, rotate=rotate)


def _wrap_lines(text, width_mm, size_mm, role="regular", max_lines=4, suffix=""):
    words = str(text or "").split()
    if not words:
        return [""]
    lines, cur = [], ""
    for w in words:
        cand = (cur + " " + w).strip()
        if _text_len_mm(cand, size_mm, role) <= width_mm:
            cur = cand
        else:
            if cur:
                lines.append(cur)
                cur = w
            else:
                lines.append(w)
                cur = ""
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        if suffix:
            lines[-1] = lines[-1] + suffix
    return lines or [""]


def _inline_css(text):
    css = " ".join(re.findall(r"<style[^>]*>(.*?)</style>", text, re.S))
    rules = {k.strip(): v.strip() for k, v in re.findall(r"\.([\w-]+)\s*\{([^}]*)\}", css)}
    return re.sub(r'class="([^"]*)"', lambda m: 'style="' + ";".join(rules.get(c, "") for c in m.group(1).split()) + '"', text)


def pick_scale(width, height, area_w, area_h):
    """Mayor escala normalizada 1:N con la que el dibujo entra en el área (las escalas son las del plano de fabricación)."""
    for n in PLANO_RULES["scales"]:
        if width / n <= area_w and height / n <= area_h:
            return n
    return PLANO_RULES["scales"][-1]


def _board_drawing(project, catalog, fronts, appearances, area_w, area_h):
    """(pdf de una página con el dibujo a escala, escala N). Frente a la izquierda, puerta cerrada a la derecha, con títulos."""
    doc, front, door = split_views(project, catalog, fronts, appearances)
    ents = front + door
    box = bbox.extents(ents, fast=True)
    title_band = RULES["viewTitleMm"] * 3.2
    n = pick_scale(box.extmax.x - box.extmin.x, box.extmax.y - box.extmin.y, area_w, area_h - title_band)
    msp = doc.modelspace()
    if not doc.layers.has_entry("TITULOS"):
        doc.layers.add("TITULOS", color=7, lineweight=9)
    if not doc.styles.has_entry("ABB_UI_BOLD"):
        doc.styles.add("ABB_UI_BOLD", font="segoeuib.ttf")
    for part, label in ((front, RULES["frontTitle"]), (door, RULES["doorTitle"])):
        if not part:
            continue
        b = bbox.extents(part, fast=True)
        t_att = {"height": RULES["viewTitleMm"] * n, "layer": "TITULOS", "style": "ABB_UI_BOLD"}
        t = msp.add_text(f"{label}  ·  ESC. 1:{n}", dxfattribs=t_att)
        t.set_placement(((b.extmin.x + b.extmax.x) / 2, box.extmin.y - RULES["viewTitleMm"] * 1.8 * n), align=__import__("ezdxf").enums.TextEntityAlignment.TOP_CENTER)
        ents.append(t)
    # split_views ya dejó en el model space sólo el frente, la puerta y estos títulos.
    return _render(doc, area_w, area_h, n), n


def _plot_color(entity, properties):
    """Ploteo monocromático para los colores índice de CAD: true color (carcasas y colores ABB) se conserva."""
    if RULES["plot"]["indexColors"] != "pen":
        return
    if entity.dxf.hasattr("true_color"):
        return
    color = entity.dxf.get("color", 256)
    if color == 256 and entity.doc is not None:  # por capa: manda el color de la capa
        layer = entity.doc.layers.get(entity.dxf.layer)
        if layer is not None and layer.dxf.hasattr("true_color"):
            return
    properties.color = RULES["plot"]["pen"]


def _render(doc, area_w, area_h, n):
    """Model space entero a escala 1:n en una página de area_w × area_h mm (PDF de una página)."""
    msp = doc.modelspace()
    props = LayoutProperties.from_layout(msp)
    props.set_colors("#ffffff")
    backend = svg.SVGBackend()
    front = Frontend(RenderContext(doc), backend)
    front.push_property_override_function(_plot_color)
    front.draw_layout(msp, layout_properties=props)
    page = layout.Page(area_w, area_h, layout.Units.mm, margins=layout.Margins.all(0))
    text = backend.get_string(page, settings=layout.Settings(scale=1 / n, fit_page=False))
    with pymupdf.open(stream=_inline_css(text).encode("utf-8"), filetype="svg") as svg_doc:
        pdf_bytes = svg_doc.convert_to_pdf()
    pymupdf.TOOLS.store_shrink(100)
    return pdf_bytes


def _shop_drawing(project, catalog, accessories, area_w, area_h):
    """Hoja de taller: perforado de puerta acotado y vista lateral (taller.shop_doc), a escala normalizada."""
    from taller import shop_doc
    n = PLANO_RULES["scales"][0]
    for _ in range(4):  # textos y cotas crecen con la escala: se arma, se mide y se vuelve a elegir hasta que no cambie
        doc = shop_doc(project, catalog, accessories, n)
        box = bbox.extents(doc.modelspace(), fast=True)
        new = pick_scale(box.extmax.x - box.extmin.x, box.extmax.y - box.extmin.y, area_w, area_h)
        if new <= n:
            break
        n = new
    return _render(doc, area_w, area_h, n), n


def _board_and_shop(project, catalog, fronts, appearances, accessories, area_w, area_h):
    front = _board_drawing(project, catalog, fronts, appearances, area_w, area_h)
    return front, (_shop_drawing(project, catalog, accessories, area_w, area_h) if accessories is not None else None)


def _draw_all(projects, catalog, fronts, appearances, area_w, area_h, accessories=None):
    """Dibujo de cada tablero; en modo ejecutable corre en un solo proceso para mantener RAM mínima."""
    import gc
    from concurrent.futures import ProcessPoolExecutor
    max_w = 1 if rutas.IS_FROZEN else min(4, os.cpu_count() or 1)
    workers = min(len(projects), max_w)
    if workers <= 1:
        out = []
        for p in projects:
            out.append(_board_and_shop(p, catalog, fronts, appearances, accessories, area_w, area_h))
            if rutas.IS_FROZEN:
                gc.collect()
        return out
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_board_and_shop, p, catalog, fronts, appearances, accessories, area_w, area_h) for p in projects]
        return [f.result() for f in futures]


def _draw_rect(page, x, y, w, h, color=(0, 0, 0), width=0.5, fill=None):
    page.draw_rect(pymupdf.Rect(x * MM, y * MM, (x + w) * MM, (y + h) * MM), color=color, width=width, fill=fill)


def _draw_line(page, x0, y0, x1, y1, color=(0, 0, 0), width=0.5):
    page.draw_line((x0 * MM, y0 * MM), (x1 * MM, y1 * MM), color=color, width=width)


def _draw_frame(page):
    """Marco técnico IRAM / plano de ingeniería con banda de zonas (C-B-A / 2-1) y marcas de centrado."""
    pw, ph = RULES["pageMm"]
    m = RULES.get("marginMm", 8)
    ml = RULES.get("marginLeftMm", 18)
    zb = RULES.get("zoneBandMm", 4.5)
    ox0, oy0, ox1, oy1 = ml, m, pw - m, ph - m
    ix0, iy0, ix1, iy1 = ox0 + zb, oy0 + zb, ox1 - zb, oy1 - zb
    black = (0.08, 0.1, 0.14)
    gray = (0.35, 0.4, 0.46)

    # Recuadro exterior fino y recuadro interior más marcado
    _draw_rect(page, ox0, oy0, ox1 - ox0, oy1 - oy0, color=gray, width=0.45)
    _draw_rect(page, ix0, iy0, ix1 - ix0, iy1 - iy0, color=black, width=0.95)

    # Referencias de zonas horizontales (C, B, A)
    cols = RULES.get("zoneCols") or ["C", "B", "A"]
    cw = (ix1 - ix0) / len(cols)
    for k, lbl in enumerate(cols):
        cx = ix0 + (k + 0.5) * cw
        _draw_text(page, cx, oy0 + zb * 0.72, lbl, 2.3, role="semibold", color=gray, align="center")
        _draw_text(page, cx, iy1 + zb * 0.72, lbl, 2.3, role="semibold", color=gray, align="center")
        if k > 0:
            xdiv = ix0 + k * cw
            _draw_line(page, xdiv, oy0, xdiv, iy0, color=gray, width=0.4)
            _draw_line(page, xdiv, iy1, xdiv, oy1, color=gray, width=0.4)

    # Referencias de zonas verticales (2, 1)
    rows = RULES.get("zoneRows") or ["2", "1"]
    rh = (iy1 - iy0) / len(rows)
    for k, lbl in enumerate(rows):
        cy = iy0 + (k + 0.5) * rh
        _draw_text(page, ox0 + zb * 0.5, cy + 0.85, lbl, 2.3, role="semibold", color=gray, align="center")
        _draw_text(page, ix1 + zb * 0.5, cy + 0.85, lbl, 2.3, role="semibold", color=gray, align="center")
        if k > 0:
            ydiv = iy0 + k * rh
            _draw_line(page, ox0, ydiv, ix0, ydiv, color=gray, width=0.4)
            _draw_line(page, ix1, ydiv, ox1, ydiv, color=gray, width=0.4)

    return ix0, iy0, ix1, iy1


def _content_lines(sheet):
    """Arma las 2-3 líneas centradas para el casillero CONTENIDO del rótulo."""
    kind = sheet.get("kind")
    board = sheet.get("board") or ""
    if kind == "cover":
        return ["DOCUMENTACIÓN TÉCNICA", "CARÁTULA"]
    if kind == "index":
        return ["DOCUMENTACIÓN TÉCNICA", "ÍNDICE DE PLANOS"]
    if kind == "board":
        return ["PLANO TOPOGRÁFICO", f"Tablero {board}".strip()]
    if kind == "shop":
        return ["PLANO DE TALLER", f"Taller {board}".strip()]
    if kind == "bom":
        return ["CÓMPUTO CONSOLIDADO", sheet.get("content") or "Lista de equipamiento eléctrico"]
    return [sheet.get("content") or ""]


def _title_block(page, values, sheet):
    """Marco técnico + rótulo de esquina inferior derecha (estructura del plano de referencia, sin logos de marca)."""
    ix0, iy0, ix1, iy1 = _draw_frame(page)
    tb = RULES["titleBlock"]
    rw, rh = tb["widthMm"], tb["heightMm"]
    rx0, ry0 = ix1 - rw, iy1 - rh
    rx1, ry1 = ix1, iy1
    black = (0.06, 0.08, 0.12)
    ink = _color("ink")
    muted = _color("muted")

    # Fondo blanco limpio del bloque del rótulo
    _draw_rect(page, rx0, ry0, rw, rh, color=black, width=0.55, fill=(1, 1, 1))

    # Nombre de archivo rotado 90° pegado al borde izquierdo del rótulo
    fname = values.get("archivo") or f"{values.get('documento') or 'Entrega_tableros'}.pdf"
    _draw_text(page, rx0 - 1.6, ry1 - 1.2, fname, 2.2, role="regular", color=muted, rotate=90)

    # 1) Tabla superior de Revisiones (3 filas de datos + 1 fila de encabezados en negrita)
    rev_h = tb["revHeightMm"]
    hdr_h = tb["revHeaderMm"]
    n_rows = tb.get("revDataRows", 3)
    row_h = (rev_h - hdr_h) / n_rows
    rev_cols = tb["revCols"]
    hdr_y = ry0 + n_rows * row_h
    body_y = ry0 + rev_h

    # Filas horizontales de revisiones
    for r in range(1, n_rows + 1):
        _draw_line(page, rx0, ry0 + r * row_h, rx1, ry0 + r * row_h, color=black, width=0.45)

    # Columnas verticales de revisiones y textos de cabecera + fila activa (la inferior, pegada a los encabezados)
    rev_code = str(values.get("revision") or "0")
    rev_desc = str(values.get("descripcion_rev") or tb.get("defaultRevDesc") or "EMISIÓN PARA REVISIÓN")
    rev_vals = [
        rev_code,
        rev_desc,
        str(values.get("dibujo") or ""),
        str(values.get("reviso") or ""),
        str(values.get("aprobo") or ""),
        str(values.get("fecha") or ""),
    ]
    cx = rx0
    active_row_y = ry0 + (n_rows - 1) * row_h
    for k, col in enumerate(rev_cols):
        cw = rw * col["frac"]
        if k > 0:
            _draw_line(page, cx, ry0, cx, body_y, color=black, width=0.45)
        # Encabezado en negrita centrado
        _draw_text(page, cx + cw / 2, hdr_y + hdr_h * 0.68, col["label"], 2.35, role="bold", color=ink, align="center", max_w_mm=cw - 1.4)
        # Dato de la revisión actual en la fila inferior de datos
        val = rev_vals[k]
        if val:
            if k == 1:
                _draw_text(page, cx + 1.4, active_row_y + row_h * 0.72, val, 2.0, role="regular", color=ink, align="left", max_w_mm=cw - 2.6, min_mm=1.3)
            else:
                _draw_text(page, cx + cw / 2, active_row_y + row_h * 0.72, val, 2.0, role="regular", color=ink, align="center", max_w_mm=cw - 1.4, min_mm=1.3)
        cx += cw

    # 2) Cuerpo principal con marco exterior grueso (idéntico al plano de referencia)
    b1_h, b2_h, b3_h = tb["bandHeightsMm"]
    y_b1 = body_y
    y_b2 = y_b1 + b1_h
    y_b3 = y_b2 + b2_h
    vx = rx0 + rw * tb["splitX"]
    vr = rx0 + rw * tb["revColX"]
    left_w = vx - rx0
    right_w = rx1 - vx

    _draw_rect(page, rx0, y_b1, rw, ry1 - y_b1, color=black, width=1.15)
    _draw_line(page, rx0, y_b2, rx1, y_b2, color=black, width=0.55)
    _draw_line(page, rx0, y_b3, rx1, y_b3, color=black, width=0.55)
    _draw_line(page, vx, y_b1, vx, ry1, color=black, width=0.55)

    # --- Banda 1 izquierda: Etapa + Proyecto (sin logo de marca) ---
    etapa = str(values.get("etapa") or tb.get("defaultStage") or "DOCUMENTACIÓN DE TABLEROS").upper()
    proyecto = str(values.get("proyecto") or "Tableros eléctricos")
    _draw_text(page, rx0 + left_w / 2, y_b1 + 5.2, etapa, 2.25, role="semibold", color=muted, align="center", max_w_mm=left_w - 4)
    proj_lines = _wrap_lines(proyecto, left_w - 6, 3.6, role="bold", max_lines=2)
    if len(proj_lines) == 1:
        _draw_text(page, rx0 + left_w / 2, y_b1 + 14.2, proj_lines[0], 3.7, role="bold", color=ink, align="center", max_w_mm=left_w - 5, min_mm=2.0)
    else:
        for idx_l, ln in enumerate(proj_lines):
            _draw_text(page, rx0 + left_w / 2, y_b1 + 11.4 + idx_l * 4.5, ln, 3.1, role="bold", color=ink, align="center", max_w_mm=left_w - 5, min_mm=1.8)

    # --- Banda 1 derecha (sin logos comerciales): Cliente arriba + Escala / Hoja / Formato abajo ---
    y_b1_mid = y_b1 + b1_h * 0.53
    _draw_line(page, vx, y_b1_mid, rx1, y_b1_mid, color=black, width=0.45)
    _draw_text(page, vx + 1.6, y_b1 + 3.2, "CLIENTE:", 1.85, role="semibold", color=muted)
    cliente = str(values.get("cliente") or "")
    if cliente:
        _draw_text(page, vx + right_w / 2, y_b1 + 8.4, cliente, 2.85, role="semibold", color=ink, align="center", max_w_mm=right_w - 4, min_mm=1.6)

    # Sub-casilleros Escala | Hoja | Formato alineados con vr (REV)
    x_hoja = vx + (vr - vx) * 0.48
    _draw_line(page, x_hoja, y_b1_mid, x_hoja, y_b2, color=black, width=0.45)
    _draw_line(page, vr, y_b1_mid, vr, y_b2, color=black, width=0.45)
    sub_specs = [
        (vx, x_hoja, "ESCALA:", str(sheet.get("scale") or "S/E"), "bold"),
        (x_hoja, vr, "HOJA:", str(sheet.get("page") or ""), "semibold"),
        (vr, rx1, "FORMATO:", str(sheet.get("format") or "A3"), "semibold"),
    ]
    for sx0, sx1, lbl, val, role_v in sub_specs:
        sw = sx1 - sx0
        _draw_text(page, sx0 + sw / 2, y_b1_mid + 3.1, lbl, 1.75, role="semibold", color=muted, align="center")
        _draw_text(page, sx0 + sw / 2, y_b2 - 2.0, val, 2.55, role=role_v, color=ink, align="center", max_w_mm=sw - 2, min_mm=1.5)

    # --- Banda 2: SECTOR DE OBRA | DOC N°: | REV: ---
    _draw_line(page, vr, y_b2, vr, y_b3, color=black, width=0.55)
    _draw_text(page, rx0 + left_w / 2, y_b2 + 4.0, "SECTOR DE OBRA", 2.05, role="semibold", color=muted, align="center")
    sector = str(values.get("sector") or "")
    if sector:
        _draw_text(page, rx0 + left_w / 2, y_b3 - 2.8, sector, 3.1, role="bold", color=ink, align="center", max_w_mm=left_w - 5, min_mm=1.7)

    doc_w = vr - vx
    _draw_text(page, vx + doc_w / 2, y_b2 + 4.0, "DOC N°:", 2.05, role="semibold", color=muted, align="center")
    _draw_text(page, vx + doc_w / 2, y_b3 - 2.8, str(sheet.get("number") or ""), 3.0, role="bold", color=ink, align="center", max_w_mm=doc_w - 3, min_mm=1.6)

    rev_w = rx1 - vr
    _draw_text(page, vr + rev_w / 2, y_b2 + 4.0, "REV:", 2.05, role="semibold", color=muted, align="center")
    _draw_text(page, vr + rev_w / 2, y_b3 - 2.6, rev_code, 3.4, role="bold", color=ink, align="center", max_w_mm=rev_w - 2, min_mm=1.8)

    # --- Banda 3: CONTENIDO: | NOMBRE ASESOR: ---
    _draw_text(page, rx0 + 1.8, y_b3 + 4.0, "CONTENIDO:", 2.05, role="semibold", color=muted)
    c_lines = _content_lines(sheet)
    # Si la segunda línea es muy larga, partir en 2 líneas limpias
    expanded = []
    for idx_c, cl in enumerate(c_lines):
        if idx_c == 0:
            expanded.append((cl, 2.55, "semibold", muted))
        else:
            for wln in _wrap_lines(cl, left_w - 8, 3.3, role="bold", max_lines=2):
                expanded.append((wln, 3.3, "bold", ink))
    y_start = y_b3 + 9.2 if len(expanded) <= 2 else y_b3 + 8.0
    step_c = 5.4 if len(expanded) <= 2 else 4.5
    for idx_e, (txt, sz, rle, col) in enumerate(expanded[:3]):
        _draw_text(page, rx0 + left_w / 2, y_start + idx_e * step_c, txt, sz, role=rle, color=col, align="center", max_w_mm=left_w - 6, min_mm=1.7)

    _draw_text(page, vx + 1.8, y_b3 + 4.0, "NOMBRE ASESOR:", 2.05, role="semibold", color=muted)
    asesor = str(values.get("asesor") or "")
    if asesor:
        a_lines = _wrap_lines(asesor, right_w - 6, 2.9, role="semibold", max_lines=2)
        for idx_a, ln in enumerate(a_lines):
            _draw_text(page, vx + right_w / 2, y_b3 + 12.0 + idx_a * 4.5, ln, 2.9, role="semibold", color=ink, align="center", max_w_mm=right_w - 5, min_mm=1.7)


BOM_COLS = [("N°", 11), ("Código", 38), ("Descripción técnica", 206), ("Cant.", 15), ("Tableros", 90), ("Estado", 30)]
LINE = RULES["fontMm"]["table"] * 1.48  # alto de un renglón de texto de la lista, mm


def _wrap(text, width_mm, max_lines=4, role="regular"):
    return _wrap_lines(text, width_mm - 3.0, RULES["fontMm"]["table"], role=role, max_lines=max_lines, suffix=" (ver Excel)")


def _bom_chunks(items, qty, height_mm, cols=BOM_COLS):
    """Filas de la lista ya partidas en renglones, agrupadas por página según la altura disponible."""
    chunks, cur, used = [], [], 0
    for k, (key, g) in enumerate(items, start=1):
        status = "; ".join(sorted(g["status"]))
        state = "FALTA CÓDIGO" if g["code"] == "FALTA CÓDIGO" else ("a confirmar" if "confirmar" in status else "")
        color = _color("danger") if state == "FALTA CÓDIGO" else (_color("warn") if state else _color("ink"))
        texts = [str(k), g["code"], g["description"], f"{qty[key]:g}", ", ".join(g["boards"]), state]
        roles = ["regular", "mono", "regular", "semibold", "regular", "semibold"]
        cells = [_wrap(t, w, role=r) for t, (_, w), r in zip(texts, cols, roles)]
        h = LINE * max(len(c) for c in cells) + 2.2
        if cur and used + h > height_mm:
            chunks.append(cur)
            cur, used = [], 0
        cur.append((cells, color))
        used += h
    chunks.append(cur)
    return chunks


def _generic_sheet(values):
    """Hoja A3 con marco técnico IRAM y rótulo de esquina inferior derecha (sin marcas comerciales)."""
    pw, ph = RULES["pageMm"]
    m = RULES.get("marginMm", 8)
    ml = RULES.get("marginLeftMm", 18)
    zb = RULES.get("zoneBandMm", 4.5)
    tb = RULES["titleBlock"]
    ix0, iy0, ix1, iy1 = ml + zb, m + zb, pw - m - zb, ph - m - zb
    ry0 = iy1 - tb["heightMm"]
    rx0 = ix1 - tb["widthMm"]
    pad = 4.0
    return {
        "size": (pw, ph),
        "content": (ix0 + pad, iy0 + pad, (ix1 - ix0) - 2 * pad, (ry0 - iy0) - 2 * pad),
        "coverLeftMaxX": rx0 - 7.0,
        "coverLeftMaxY": iy1 - 5.0,
        "stamp": lambda page, info: _title_block(page, values, info),
        "format": "A3",
    }


def _format_sheet(template, values):
    """Hoja con el marco y el rótulo del formato del usuario (el mismo del plano de fabricación)."""
    from plano_unifilar import content_tags, sheet_frame
    meta_path = Path(template).with_suffix(".json")
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    if not meta.get("fields"):
        from plano_unifilar import analyze_template
        meta = analyze_template(str(template))
    per_board = meta.get("perBoardTag")
    content = content_tags(meta.get("fields", []))
    frame = sheet_frame(str(template))
    pw, ph = frame["paper"]
    ix0, iy0, ix1, iy1 = frame["inner"]
    tx0, ty0, tx1, ty1 = frame["titleBox"]
    g = RULES["format"]["gapMm"]
    texts = RULES["format"]["content"]

    def stamp(page, info):
        for a in frame["title"].attribs:
            tag = a.dxf.tag
            if tag == per_board:
                a.dxf.text = info.get("board", "")
            elif tag in content:
                a.dxf.text = texts[info["kind"]]
            elif tag in values:
                a.dxf.text = str(values[tag])
        src = pymupdf.open("pdf", _render(frame["doc"], pw, ph, frame["unitsPerMm"]))
        page.show_pdf_page(page.rect, src, 0, overlay=False)

    from plano_unifilar import RULES as PR
    rev_cols = PR.get("revisionColumns", [])
    labels = PR.get("fieldLabels", {})
    cover = []
    for f in meta.get("fields", []):
        tag = f["tag"]
        rev = re.match(r"^(.*?)(\d)$", tag)
        if tag in content or tag == per_board or (rev and rev.group(1) in rev_cols) or not str(values.get(tag, "")).strip():
            continue
        cover.append((labels.get(tag) or f.get("prompt") or tag, str(values[tag])))
    return {"size": (pw, ph), "content": (ix0 + g, ph - iy1 + g, ix1 - ix0 - 2 * g, (iy1 - ty1) - 2 * g),
            "stamp": stamp, "format": f"{pw:g} × {ph:g}", "cover": cover}


def _draw_cover(page, sheet, projects, catalog, items, values, total_pages, shop, bom_mode, template):
    """Carátula técnica limpia con barra de acento, resumen ejecutivo, datos del proyecto y listado de tableros."""
    cx, cy, area_w, area_h = sheet["content"]
    primary = _color("primary")
    accent = _color("accentGeneric" if bom_mode == "generic" else "accentAbb")
    ink = _color("ink")
    muted = _color("muted")
    soft = _color("softBg")
    rule = _color("rule")

    left_x = cx + 6
    max_y = sheet.get("coverLeftMaxY", cy + area_h - 4)
    left_max_x = sheet.get("coverLeftMaxX", cx + area_w * 0.56)

    # Barra vertical de acento sobria a la izquierda
    bar_h = min(max_y - (cy + 6), max(area_h - 12, 120))
    _draw_rect(page, left_x, cy + 6, 2.8, bar_h, color=None, width=0, fill=primary)
    _draw_rect(page, left_x, cy + 6, 2.8, 16, color=None, width=0, fill=accent)

    tx = left_x + 9
    tw = (cx + area_w - 6) - tx

    # Kicker superior + Título del proyecto + Subtítulo
    _draw_text(page, tx, cy + 12.5, "DOCUMENTACIÓN TÉCNICA · TABLEROS ELÉCTRICOS DE BAJA TENSIÓN", 2.7, role="semibold", color=accent)
    title = str(values.get("proyecto") or "Tableros eléctricos")
    t_lines = _wrap_lines(title, tw, 8.2, role="bold", max_lines=2)
    y_cur = cy + 24.5
    for ln in t_lines:
        _draw_text(page, tx, y_cur, ln, 8.2, role="bold", color=ink, max_w_mm=tw, min_mm=5.0)
        y_cur += 10.0

    sub = (
        "Planos topográficos (puerta abierta y cerrada), planos de taller y cómputo consolidado de equipamiento"
        if shop else
        "Planos topográficos (puerta abierta y cerrada) y cómputo consolidado de equipamiento"
    )
    _draw_text(page, tx, y_cur + 1.5, sub, 3.6, role="regular", color=muted, max_w_mm=tw, min_mm=2.5)
    y_cur += 7.5
    _draw_line(page, tx, y_cur, cx + area_w - 6, y_cur, color=rule, width=0.6)

    # Tarjetas KPI de resumen ejecutivo
    y_kpi = y_cur + 5.5
    kpis = [
        ("TABLEROS", str(len(projects))),
        ("HOJAS TOTALES", str(total_pages)),
        ("ÍTEMS EN CÓMPUTO", str(len(items))),
        ("ESPECIFICACIÓN", "Genérica (sin marca)" if bom_mode == "generic" else "ABB (con códigos)"),
    ]
    gap = 4.5
    kw = (tw - gap * (len(kpis) - 1)) / len(kpis)
    kh = 16.5
    for idx_k, (klbl, kval) in enumerate(kpis):
        kx = tx + idx_k * (kw + gap)
        _draw_rect(page, kx, y_kpi, kw, kh, color=rule, width=0.45, fill=soft)
        _draw_rect(page, kx, y_kpi, kw, 1.1, color=None, width=0, fill=primary)
        _draw_text(page, kx + 3.5, y_kpi + 5.6, klbl, 2.0, role="semibold", color=muted)
        _draw_text(page, kx + 3.5, y_kpi + 13.0, kval, 4.0 if idx_k < 3 else 3.0, role="bold", color=ink, max_w_mm=kw - 6, min_mm=2.1)

    y_sec = y_kpi + kh + 9.0

    # Columna izquierda: Datos generales del proyecto
    meta_w = max(120, left_max_x - tx - 4)
    _draw_text(page, tx, y_sec, "DATOS DEL PROYECTO Y EMISIÓN", 2.55, role="bold", color=primary)
    _draw_line(page, tx, y_sec + 2.0, tx + meta_w, y_sec + 2.0, color=primary, width=0.55)

    meta_lines = (
        sheet.get("cover") if template else
        [(f["label"], values[f["key"]]) for f in RULES["fields"] if values.get(f["key"])]
    )
    if not meta_lines:
        meta_lines = [("Contenido", f"{len(projects)} tablero(s) · {total_pages} hojas")]

    y_m = y_sec + 7.5
    col2 = len(meta_lines) > 6 and meta_w >= 150
    col_w = (meta_w - 8) / 2 if col2 else meta_w
    per_col = (len(meta_lines) + 1) // 2 if col2 else len(meta_lines)
    for idx_m, (mlbl, mval) in enumerate(meta_lines):
        col_i = idx_m // per_col if col2 else 0
        row_i = idx_m % per_col if col2 else idx_m
        mx = tx + col_i * (col_w + 8)
        my = y_m + row_i * 11.0
        if my + 6 > max_y:
            break
        _draw_text(page, mx, my, mlbl.upper(), 1.95, role="semibold", color=muted, max_w_mm=col_w)
        _draw_text(page, mx, my + 4.4, str(mval), 3.05, role="regular", color=ink, max_w_mm=col_w, min_mm=1.9)
        _draw_line(page, mx, my + 6.8, mx + col_w, my + 6.8, color=rule, width=0.3)

    # Columna derecha (arriba del rótulo): Tableros incluidos en la entrega
    rx_box = tx + meta_w + 10
    rw_box = (cx + area_w - 6) - rx_box
    if rw_box >= 85 and (cy + area_h - y_sec) >= 40:
        _draw_text(page, rx_box, y_sec, "TABLEROS INCLUIDOS", 2.55, role="bold", color=primary)
        _draw_line(page, rx_box, y_sec + 2.0, rx_box + rw_box, y_sec + 2.0, color=primary, width=0.55)
        encs = {e["id"]: e for e in catalog.get("enclosures", [])}
        y_b = y_sec + 7.2
        max_b_y = cy + area_h - 4
        board_names = list(projects.keys())
        for idx_b, bname in enumerate(board_names):
            if y_b + 6.5 > max_b_y:
                rem = len(board_names) - idx_b
                _draw_text(page, rx_box + 2, y_b, f"+ {rem} tablero(s) adicional(es) — ver Índice", 2.3, role="semibold", color=muted)
                break
            proj = projects[bname]
            enc = encs.get((proj.get("enclosure") or {}).get("id"), {})
            eb = (proj.get("enclosure") or {}).get("externalBody") or {}
            if bom_mode == "generic":
                enc_txt = f"Gabinete {eb.get('height', '?'):g}×{eb.get('width', '?'):g}×{eb.get('depth', '?'):g} mm"
            else:
                enc_txt = (enc.get("label") or (proj.get("enclosure") or {}).get("line") or "Envolvente ABB").split("·")[0].strip()
            ndev = len(proj.get("devices") or [])
            if idx_b % 2 == 0:
                _draw_rect(page, rx_box, y_b - 3.6, rw_box, 6.2, color=None, width=0, fill=soft)
            _draw_text(page, rx_box + 2, y_b + 0.4, bname, 2.55, role="semibold", color=ink, max_w_mm=rw_box * 0.42, min_mm=1.8)
            _draw_text(page, rx_box + rw_box - 2, y_b + 0.4, f"{ndev} eq. · {enc_txt}", 2.25, role="regular", color=muted, align="right", max_w_mm=rw_box * 0.54, min_mm=1.6)
            y_b += 6.4


def _draw_index_pages(out, new_page, sheet, index_rows, total_pages, n_boards, template):
    """Dibuja el Índice de documentación con tabla formal y paginación automática si excede una hoja."""
    cx, cy, area_w, area_h = sheet["content"]
    primary = _color("primary")
    ink = _color("ink")
    muted = _color("muted")
    zebra = _color("zebra")
    rule = _color("rule")

    row_h = 6.2
    header_y_off = 17.0
    max_rows = max(8, int((area_h - header_y_off - 10) // row_h))
    chunks = [index_rows[k:k + max_rows] for k in range(0, len(index_rows), max_rows)] or [[]]

    x0 = cx + 4
    tw = area_w - 8
    if template:
        cols = [("Hoja", 22, "center"), ("Contenido", tw - 48, "left"), ("Escala", 26, "center")]
    else:
        cols = [("Hoja", 20, "center"), ("Documento", 56, "left"), ("Contenido", tw - 102, "left"), ("Escala", 26, "center")]

    for p_idx, chunk in enumerate(chunks):
        page_num = 2 + p_idx
        suffix = f" ({p_idx + 1}/{len(chunks)})" if len(chunks) > 1 else ""
        page = new_page(page_num, "index", f"Índice{suffix}")
        _draw_rect(page, x0, cy + 2.5, 2.2, 8.5, color=None, width=0, fill=primary)
        _draw_text(page, x0 + 5.5, cy + 7.2, f"Índice de documentación{suffix}", 5.0, role="bold", color=ink)
        _draw_text(page, x0 + 5.5, cy + 11.4, f"{n_boards} tablero(s) · {total_pages} hojas totales", 2.6, role="regular", color=muted)

        y = cy + header_y_off
        _draw_rect(page, x0, y, tw, 6.8, color=None, width=0, fill=primary)
        xc = x0
        for lbl, w, al in cols:
            tx = xc + w / 2 if al == "center" else xc + 2.5
            _draw_text(page, tx, y + 4.7, lbl, 2.45, role="semibold", color=(1, 1, 1), align=al)
            xc += w
        y += 6.8

        for r_idx, (i, num, content, scale) in enumerate(chunk):
            if r_idx % 2 == 1:
                _draw_rect(page, x0, y, tw, row_h, color=None, width=0, fill=zebra)
            vals = [f"{i}", content, scale or "—"] if template else [f"{i}", num, content, scale or "—"]
            roles = ["semibold", "regular", "semibold"] if template else ["semibold", "mono", "regular", "semibold"]
            xc = x0
            for (lbl, w, al), val, rle in zip(cols, vals, roles):
                tx = xc + w / 2 if al == "center" else xc + 2.5
                col = muted if val == "—" else ink
                _draw_text(page, tx, y + row_h * 0.68, val, 2.45, role=rle, color=col, align=al, max_w_mm=w - 4, min_mm=1.6)
                xc += w
            y += row_h
            _draw_line(page, x0, y, x0 + tw, y, color=rule, width=0.3)


def _draw_bom_pages(new_page, sheet, bom_chunks, cols, start_page, n_items, n_boards, bom_mode):
    """Dibuja las páginas de la Lista consolidada de equipamiento eléctrico con tabla moderna."""
    cx, cy, area_w, area_h = sheet["content"]
    primary = _color("primary")
    ink = _color("ink")
    muted = _color("muted")
    zebra = _color("zebra")
    rule = _color("rule")
    x0 = cx + 4
    tw = sum(w for _, w in cols)
    n_pages = len(bom_chunks)
    mode_txt = "Especificación técnica genérica (sin marca)" if bom_mode == "generic" else "Especificación ABB (con códigos de pedido)"
    aligns = ["right", "left", "left", "right", "left", "center"]
    roles = ["regular", "mono", "regular", "semibold", "regular", "semibold"]

    for b, chunk in enumerate(bom_chunks):
        i = start_page + b
        title_suf = f" ({b + 1}/{n_pages})" if n_pages > 1 else ""
        page = new_page(i, "bom", f"Lista de equipamiento eléctrico{title_suf}")
        _draw_rect(page, x0, cy + 2.0, 2.2, 8.2, color=None, width=0, fill=primary)
        _draw_text(page, x0 + 5.5, cy + 6.6, f"Lista de equipamiento eléctrico{title_suf}", 4.6, role="bold", color=ink)
        _draw_text(page, x0 + 5.5, cy + 10.6, f"{mode_txt} · Sin canalizaciones ni materiales de montaje · {n_items} ítem(s) en {n_boards} tablero(s)", 2.4, role="regular", color=muted, max_w_mm=tw - 8)

        y = cy + 14.0
        hdr_h = 6.6
        _draw_rect(page, x0, y, tw, hdr_h, color=None, width=0, fill=primary)
        xc = x0
        for (label, w), al in zip(cols, aligns):
            tx = (xc + w / 2) if al == "center" else ((xc + w - 2.2) if al == "right" else (xc + 2.0))
            _draw_text(page, tx, y + 4.5, label, 2.35, role="semibold", color=(1, 1, 1), align=al)
            xc += w
        y += hdr_h

        for r_idx, (cells, state_color) in enumerate(chunk):
            lines = max(len(c) for c in cells)
            rh = LINE * lines + 2.2
            if r_idx % 2 == 1:
                _draw_rect(page, x0, y, tw, rh, color=None, width=0, fill=zebra)
            xc = x0
            for (label, w), cell_lines, al, rle in zip(cols, cells, aligns, roles):
                col = state_color if label == "Estado" else (muted if label == "N°" else ink)
                tx = (xc + w / 2) if al == "center" else ((xc + w - 2.2) if al == "right" else (xc + 2.0))
                for k, line in enumerate(cell_lines):
                    _draw_text(page, tx, y + 0.8 + LINE * (k + 1), line, RULES["fontMm"]["table"], role=rle, color=col, align=al, max_w_mm=w - 3.0, min_mm=1.5)
                xc += w
            y += rh
            _draw_line(page, x0, y, x0 + tw, y, color=rule, width=0.3)


def build_pdf(projects, catalog, fronts, appearances, values, shop=True, template=None, bom_mode="abb"):
    """projects: {nombre: proyecto} en el orden de entrega. shop: agrega detrás de cada tablero su hoja de taller
    (perforado de puerta y vista lateral). template: formato DXF del usuario (marco y rótulo); sin formato, marco
    técnico A3 con rótulo de esquina inferior derecha (sin marcas comerciales). bom_mode: 'abb' o 'generic'."""
    sheet = _format_sheet(template, values) if template else _generic_sheet(values)
    pw, ph = sheet["size"]
    cx, cy, area_w, area_h = sheet["content"]
    base = values.get("documento") or "PL"
    detail, items = collect(projects, catalog, mode=bom_mode)
    qty = {}
    for d in detail:
        qty[d["key"]] = qty.get(d["key"], 0) + d["quantity"]
    cols_scale = (area_w - 8) / sum(w for _, w in BOM_COLS)
    cols = [(label, w * cols_scale) for label, w in BOM_COLS]
    bom_chunks = _bom_chunks(items, qty, area_h - 24, cols)
    bom_pages = len(bom_chunks)
    per_board = 2 if shop else 1

    # Calculamos cuántas hojas ocupa el índice (puede superar 1 hoja si hay muchos tableros)
    raw_index_count = 1 + per_board * len(projects) + bom_pages  # + índice(s)
    max_idx_rows = max(8, int((area_h - 27.0) // 6.2))
    index_pages = 1
    while (raw_index_count + index_pages) > index_pages * max_idx_rows:
        index_pages += 1

    total = 1 + index_pages + per_board * len(projects) + bom_pages
    accessories = rutas.read_json("accesorios_abb.json") if shop else None
    number = (lambda n: RULES["sheetNumberFormat"].format(documento=base, n=n)) if not template else (lambda n: f"Hoja {n}")  # noqa: E731
    out = pymupdf.open()

    def new_page(i, kind, content, board="", scale=None):
        page = out.new_page(width=pw * MM, height=ph * MM)
        _register_fonts(page)
        sheet["stamp"](page, {
            "kind": kind,
            "board": board,
            "content": content,
            "number": number(i),
            "page": f"{i} de {total}",
            "scale": scale or "S/E",
            "format": sheet["format"],
        })
        return page

    # 1) Carátula
    cover_page = new_page(1, "cover", "Carátula")
    _draw_cover(cover_page, sheet, projects, catalog, items, values, total, shop, bom_mode, template)

    # 2) Dibujos de tableros + planos de taller (se calculan antes del índice para informar las escalas reales)
    first_board_page = 1 + index_pages + 1
    index_rows = [(1, number(1), "Carátula", "")]
    for p_idx in range(index_pages):
        suf = f" ({p_idx + 1}/{index_pages})" if index_pages > 1 else ""
        index_rows.append((2 + p_idx, number(2 + p_idx), f"Índice de documentación{suf}", ""))

    sheets = []
    drawings = _draw_all(list(projects.values()), catalog, fronts, appearances, area_w, area_h, accessories)
    for k, (name, ((pdf, n), shop_sheet)) in enumerate(zip(projects, drawings)):
        i = first_board_page + per_board * k
        sheets.append((i, "board", f"Tablero {name}", name, pdf, n))
        index_rows.append((i, number(i), f"Tablero {name} — Puerta abierta y cerrada", f"1:{n}"))
        if shop_sheet:
            sheets.append((i + 1, "shop", f"Taller {name}", name, shop_sheet[0], shop_sheet[1]))
            index_rows.append((i + 1, number(i + 1), f"Tablero {name} — Perforado de puerta y vista lateral", f"1:{shop_sheet[1]}"))

    bom_start = first_board_page + per_board * len(projects)
    for b in range(bom_pages):
        i = bom_start + b
        suf = f" ({b + 1}/{bom_pages})" if bom_pages > 1 else ""
        index_rows.append((i, number(i), f"Lista de equipamiento eléctrico{suf}", ""))

    # 2b) Páginas de índice
    _draw_index_pages(out, new_page, sheet, index_rows, total, len(projects), template)

    # 3) Hojas de tablero y taller a escala normalizada
    for i, kind, content, board, pdf, n in sheets:
        page = new_page(i, kind, content, board, f"1:{n}")
        src = pymupdf.open("pdf", pdf)
        page.show_pdf_page(pymupdf.Rect(cx * MM, cy * MM, (cx + area_w) * MM, (cy + area_h) * MM), src, 0)

    # 4) Lista consolidada de equipamiento eléctrico
    _draw_bom_pages(new_page, sheet, bom_chunks, cols, bom_start, len(items), len(projects), bom_mode)

    try:
        out.subset_fonts()
    except Exception:
        pass
    return out.tobytes(deflate=True, garbage=3)
