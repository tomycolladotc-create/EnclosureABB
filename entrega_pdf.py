"""PDF único de entrega (Exportar → «PDF de entrega»).

Pedido de Thomas 2026-11-23: un solo PDF con carátula, índice, los frentes y las puertas de todos los tableros y la
lista consolidada, con páginas numeradas y un rótulo completo (proyecto, cliente, tablero, número de plano, revisión,
fecha, dibujó/revisó/aprobó y escala).

Cada hoja de tablero se dibuja desde el mismo DXF que exporta el programa (plano_unifilar.split_views): mismas formas,
pinturas y textos. ezdxf lo dibuja a SVG (rápido) y PyMuPDF lo pasa a PDF vectorial; el SVG de ezdxf pone los colores en
clases CSS que el lector de PyMuPDF no aplica, por eso se copian a cada elemento (_inline_css).
Medidas, textos y campos del rótulo: datos/reglas_layout.json → entregaPdf (una sola regla).
"""
import json
import re
from pathlib import Path

import pymupdf
from ezdxf import bbox
from ezdxf.addons.drawing import Frontend, RenderContext, layout, svg
from ezdxf.addons.drawing.properties import LayoutProperties

from excel_equipamiento import collect
from plano_unifilar import RULES as PLANO_RULES
from plano_unifilar import split_views

RULES = json.loads((Path(__file__).resolve().parent / "datos" / "reglas_layout.json").read_text(encoding="utf-8"))["entregaPdf"]
MM = 72 / 25.4  # puntos PDF por mm
FONT = "helv"


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
    title_band = RULES["viewTitleMm"] * 3
    n = pick_scale(box.extmax.x - box.extmin.x, box.extmax.y - box.extmin.y, area_w, area_h - title_band)
    msp = doc.modelspace()
    if not doc.layers.has_entry("TITULOS"):
        doc.layers.add("TITULOS", color=7)
    for part, label in ((front, RULES["frontTitle"]), (door, RULES["doorTitle"])):
        if not part:
            continue
        b = bbox.extents(part, fast=True)
        t = msp.add_text(f"{label}  ESC. 1:{n}", dxfattribs={"height": RULES["viewTitleMm"] * n, "layer": "TITULOS"})
        t.set_placement(((b.extmin.x + b.extmax.x) / 2, box.extmin.y - RULES["viewTitleMm"] * 1.8 * n), align=__import__("ezdxf").enums.TextEntityAlignment.TOP_CENTER)
        ents.append(t)
    # split_views ya dejó en el model space sólo el frente, la puerta y estos títulos.
    return _render(doc, area_w, area_h, n), n


def _render(doc, area_w, area_h, n):
    """Model space entero a escala 1:n en una página de area_w × area_h mm (PDF de una página). Fondo blanco: el color 7
    sale negro, como en el papel (draw_entities no aplica los colores de la hoja, por eso draw_layout)."""
    msp = doc.modelspace()
    props = LayoutProperties.from_layout(msp)
    props.set_colors("#ffffff")
    backend = svg.SVGBackend()
    Frontend(RenderContext(doc), backend).draw_layout(msp, layout_properties=props)
    page = layout.Page(area_w, area_h, layout.Units.mm, margins=layout.Margins.all(0))
    text = backend.get_string(page, settings=layout.Settings(scale=1 / n, fit_page=False))
    return pymupdf.open(stream=_inline_css(text).encode("utf-8"), filetype="svg").convert_to_pdf()


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
    """Dibujo de cada tablero; con varios, en paralelo (uno por núcleo): cada tablero es independiente."""
    import os
    from concurrent.futures import ProcessPoolExecutor
    workers = min(len(projects), os.cpu_count() or 1)
    if workers <= 1:
        return [_board_and_shop(p, catalog, fronts, appearances, accessories, area_w, area_h) for p in projects]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_board_and_shop, p, catalog, fronts, appearances, accessories, area_w, area_h) for p in projects]
        return [f.result() for f in futures]


def _cell(page, x, y, w, h, label, value, fs):
    page.draw_rect(pymupdf.Rect(x * MM, y * MM, (x + w) * MM, (y + h) * MM), color=(0, 0, 0), width=0.5)
    page.insert_text(((x + 1.2) * MM, (y + fs["label"] + 1) * MM), label, fontsize=fs["label"] * MM, fontname=FONT, color=(0.35, 0.35, 0.35))
    size = fs["cell"]
    while size > 1.4 and pymupdf.get_text_length(value, fontname=FONT, fontsize=size * MM) > (w - 2.4) * MM:
        size -= 0.1  # un texto largo se achica para no salir de su casillero
    page.insert_text(((x + 1.2) * MM, (y + h - 1.6) * MM), value, fontsize=size * MM, fontname=FONT)


def _title_block(page, values, sheet):
    """Rótulo en una franja a lo ancho del pie de la hoja: todos los casilleros cerrados."""
    pw, ph = RULES["pageMm"]
    m, band, fs = RULES["marginMm"], RULES["titleBandMm"], RULES["fontMm"]
    x0, y0, w = m, ph - m - band, pw - 2 * m
    page.draw_rect(pymupdf.Rect(m * MM, m * MM, (pw - m) * MM, (ph - m) * MM), color=(0, 0, 0), width=1.0)
    h = band / 2
    row1 = [("Proyecto", values.get("proyecto", ""), 0.30), ("Cliente", values.get("cliente", ""), 0.22),
            ("Contenido", sheet["content"], 0.30), ("Escala", sheet.get("scale", "—"), 0.08), ("Hoja", sheet["page"], 0.10)]
    row2 = [("N° de plano", sheet["number"], 0.22), ("Revisión", values.get("revision", ""), 0.08), ("Fecha", values.get("fecha", ""), 0.12),
            ("Dibujó", values.get("dibujo", ""), 0.16), ("Revisó", values.get("reviso", ""), 0.16), ("Aprobó", values.get("aprobo", ""), 0.16),
            ("Formato", sheet.get("format", "A3"), 0.10)]
    for row, y in ((row1, y0), (row2, y0 + h)):
        x = x0
        for label, value, frac in row:
            _cell(page, x, y, w * frac, h, label, str(value), fs)
            x += w * frac


BOM_COLS = [("N°", 10), ("Código", 34), ("Descripción", 210), ("Cant.", 14), ("Tableros", 92), ("Estado", 34)]
LINE = RULES["fontMm"]["table"] * 1.45  # alto de un renglón de texto de la lista, mm


def _wrap(text, width_mm, max_lines=4):
    size = RULES["fontMm"]["table"] * MM
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        cand = (cur + " " + w).strip()
        if pymupdf.get_text_length(cand, fontname=FONT, fontsize=size) <= (width_mm - 2) * MM:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] += " (ver Excel)"
    return lines or [""]


def _bom_chunks(items, qty, height_mm, cols=BOM_COLS):
    """Filas de la lista ya partidas en renglones, agrupadas por página según la altura disponible."""
    chunks, cur, used = [], [], 0
    for k, (key, g) in enumerate(items, start=1):
        status = "; ".join(sorted(g["status"]))
        state = "FALTA CÓDIGO" if g["code"] == "FALTA CÓDIGO" else ("a confirmar" if "confirmar" in status else "")
        color = (0.75, 0.1, 0.1) if state == "FALTA CÓDIGO" else (0.6, 0.45, 0) if state else (0, 0, 0)
        texts = [str(k), g["code"], g["description"], f"{qty[key]:g}", ", ".join(g["boards"]), state]
        cells = [_wrap(t, w) for t, (_, w) in zip(texts, cols)]
        h = LINE * max(len(c) for c in cells) + 1.2
        if cur and used + h > height_mm:
            chunks.append(cur)
            cur, used = [], 0
        cur.append((cells, color))
        used += h
    chunks.append(cur)
    return chunks


def _generic_sheet(values):
    """Hoja A3 con el rótulo propio del programa: sólo si el usuario todavía no cargó su formato."""
    pw, ph = RULES["pageMm"]
    m, band = RULES["marginMm"], RULES["titleBandMm"]
    return {"size": (pw, ph), "content": (m + 3, m + 3, pw - 2 * m - 6, ph - 2 * m - band - 6),
            "stamp": lambda page, info: _title_block(page, values, info), "format": "A3"}


def _format_sheet(template, values):
    """Hoja con el marco y el rótulo del formato del usuario (el mismo del plano de fabricación): tamaño de su marco,
    dibujo dentro del recuadro interior y por encima del rótulo. Cada hoja completa el rótulo con lo que cargó el
    usuario; el atributo del nombre del tablero lleva el tablero de la hoja y los de contenido, lo que contiene."""
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


def build_pdf(projects, catalog, fronts, appearances, values, shop=True, template=None):
    """projects: {nombre: proyecto} en el orden de entrega. shop: agrega detrás de cada tablero su hoja de taller
    (perforado de puerta y vista lateral). template: formato DXF del usuario (marco y rótulo); con él, `values` son los
    atributos de su rótulo {tag: texto} y todas las hojas salen con ese rótulo. Sin formato, rótulo propio en A3 con
    `values` de entregaPdf.fields. Devuelve bytes."""
    sheet = _format_sheet(template, values) if template else _generic_sheet(values)
    pw, ph = sheet["size"]
    cx, cy, area_w, area_h = sheet["content"]
    fs = RULES["fontMm"]
    base = values.get("documento") or "PL"
    detail, items = collect(projects, catalog)
    qty = {}
    for d in detail:
        qty[d["key"]] = qty.get(d["key"], 0) + d["quantity"]
    cols_scale = (area_w - 8) / sum(w for _, w in BOM_COLS)
    cols = [(label, w * cols_scale) for label, w in BOM_COLS]
    bom_chunks = _bom_chunks(items, qty, area_h - 22, cols)
    bom_pages = len(bom_chunks)
    per_board = 2 if shop else 1
    total = 2 + per_board * len(projects) + bom_pages
    accessories = json.loads((Path(__file__).resolve().parent / "datos" / "accesorios_abb.json").read_text(encoding="utf-8")) if shop else None
    number = (lambda n: RULES["sheetNumberFormat"].format(documento=base, n=n)) if not template else (lambda n: f"Hoja {n}")  # noqa: E731
    out = pymupdf.open()

    def new_page(i, kind, content, board="", scale=None):
        page = out.new_page(width=pw * MM, height=ph * MM)
        sheet["stamp"](page, {"kind": kind, "board": board, "content": content, "number": number(i),
                              "page": f"{i} de {total}", "scale": scale or "—", "format": sheet["format"]})
        return page

    # 1) Carátula
    page = new_page(1, "cover", "Carátula")
    title = values.get("proyecto") or "Tableros eléctricos"
    page.insert_text(((cx + 20) * MM, (cy + 50) * MM), title, fontsize=fs["title"] * MM, fontname="hebo")
    page.insert_text(((cx + 20) * MM, (cy + 65) * MM), "Frentes, puertas, planos de taller y lista de equipamiento" if shop else "Frentes, puertas y lista de equipamiento", fontsize=fs["subtitle"] * MM, fontname=FONT)
    y = cy + 90
    lines = sheet.get("cover") if template else [(f["label"], values[f["key"]]) for f in RULES["fields"] if values.get(f["key"])]
    for label, value in lines:
        page.insert_text(((cx + 20) * MM, y * MM), f"{label}: {value}", fontsize=fs["cell"] * 1.6 * MM, fontname=FONT)
        y += 9
    page.insert_text(((cx + 20) * MM, (y + 6) * MM), f"{len(projects)} tablero(s) · {total} hojas", fontsize=fs["cell"] * 1.6 * MM, fontname=FONT)

    # 2) Índice (se completa después de saber la escala de cada hoja)
    index = [(1, number(1), "Carátula", ""), (2, number(2), "Índice", "")]
    sheets = []
    drawings = _draw_all(list(projects.values()), catalog, fronts, appearances, area_w, area_h, accessories)
    for k, (name, ((pdf, n), shop_sheet)) in enumerate(zip(projects, drawings)):
        i = 3 + per_board * k
        sheets.append((i, "board", f"Tablero {name}", name, pdf, n))
        index.append((i, number(i), f"Tablero {name}: puerta abierta y cerrada", f"1:{n}"))
        if shop_sheet:
            sheets.append((i + 1, "shop", f"Taller {name}", name, shop_sheet[0], shop_sheet[1]))
            index.append((i + 1, number(i + 1), f"Tablero {name}: perforado de puerta y vista lateral", f"1:{shop_sheet[1]}"))
    for b in range(bom_pages):
        i = 3 + per_board * len(projects) + b
        index.append((i, number(i), "Lista de equipamiento eléctrico" + (f" ({b + 1}/{bom_pages})" if bom_pages > 1 else ""), ""))
    page = new_page(2, "index", "Índice")
    page.insert_text(((cx + 10) * MM, (cy + 20) * MM), "Índice", fontsize=fs["subtitle"] * 1.5 * MM, fontname="hebo")
    y = cy + 32
    for i, num, content, scale in index:
        for dx, text in ((10, f"Hoja {i}"), (35, "" if template else num), (95 if not template else 35, content), (300 if not template else 240, scale)):
            if text:
                page.insert_text(((cx + dx) * MM, y * MM), text, fontsize=fs["table"] * MM, fontname=FONT)
        y += fs["table"] * 2.2

    # 3) Una hoja por tablero, a escala real (el dibujo entra tal cual, sin estirar)
    for i, kind, content, board, pdf, n in sheets:
        page = new_page(i, kind, content, board, f"1:{n}")
        src = pymupdf.open("pdf", pdf)
        page.show_pdf_page(pymupdf.Rect(cx * MM, cy * MM, (cx + area_w) * MM, (cy + area_h) * MM), src, 0)

    # 4) Lista consolidada: la descripción se parte en renglones (nunca se achica hasta no leerse) y se pagina por altura
    for b, chunk in enumerate(bom_chunks):
        i = 3 + per_board * len(projects) + b
        page = new_page(i, "bom", "Lista de equipamiento eléctrico")
        y = cy + 7
        page.insert_text(((cx + 4) * MM, y * MM), "Lista de equipamiento eléctrico (sin canalizaciones ni montaje)", fontsize=fs["subtitle"] * MM, fontname="hebo")
        y += 8
        x = cx + 4
        for label, w in cols:
            page.insert_text((x * MM, y * MM), label, fontsize=fs["table"] * MM, fontname="hebo")
            x += w
        y += 1.5
        page.draw_line(((cx + 4) * MM, y * MM), ((cx + area_w - 4) * MM, y * MM), color=(0, 0, 0), width=0.6)
        for cells, color in chunk:
            lines = max(len(c) for c in cells)
            x = cx + 4
            for (label, w), text in zip(cols, cells):
                for k, line in enumerate(text):
                    page.insert_text((x * MM, (y + LINE * (k + 1)) * MM), line, fontsize=fs["table"] * MM, fontname=FONT,
                                     color=color if label == "Estado" else (0, 0, 0))
                x += w
            y += LINE * lines + 1.2
            page.draw_line(((cx + 4) * MM, y * MM), ((cx + area_w - 4) * MM, y * MM), color=(0.8, 0.8, 0.8), width=0.3)
    return out.tobytes(deflate=True, garbage=3)
