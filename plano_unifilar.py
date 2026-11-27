"""Plano de fabricación por tablero: el UNIFILAR del usuario y, al lado, el TOPOGRÁFICO armado por la aplicación
(vista con la puerta abierta y con la puerta cerrada), dentro del formato de ploteo del usuario.

Entrada: el DXF de formato del usuario (guardado desde su DWG) con una presentación (layout) por tablero
que ya muestra su unifilar en el espacio modelo, un marco de hoja y un bloque de rótulo con atributos.
Salida: el mismo DXF, con cada presentación de tablero convertida en una hoja A1 a
escala 1:1 que contiene:
  - el unifilar del usuario, tal cual (misma ventana, escala 1:1, arriba a la izquierda);
  - el topográfico de la aplicación (cad_export.build_dxf, sin la lista ni las notas), dibujado 1:1 en el espacio
    modelo lejos de los unifilares y mostrado con dos ventanas a la misma escala normalizada: puerta abierta y
    puerta cerrada, con su título y escala;
  - el rótulo del usuario con «UNIFILAR Y TOPOGRÁFICO» en el título; el resto de sus datos no se toca.
Todas las medidas de la hoja salen del marco y del rótulo del propio formato (nada fijo para una sola obra).
"""
from __future__ import annotations

import io
import json
import math
import sys
from pathlib import Path

import ezdxf
from ezdxf import bbox
from ezdxf.addons.importer import Importer

from cad_export import build_dxf

import rutas
ROOT = rutas.BUNDLE_ROOT
RULES = rutas.read_json("reglas_layout.json")["planoUnifilar"]


def _block_size(doc, name):
    e = bbox.extents(doc.blocks.get(name))
    return e.extmin, e.extmax


def _sheet_inserts(layout, blocks):
    frame = next((i for i in layout.query("INSERT") if i.dxf.name == blocks["frameBlock"]), None)
    title = next((i for i in layout.query("INSERT") if i.dxf.name == blocks["titleBlock"]), None)
    return frame, title


def _norm(name):
    return " ".join(str(name or "").upper().replace("_", " ").split())


def detect_blocks(doc):
    """Marco y rótulo del formato, sin depender del cliente: el rótulo es el bloque con atributos que aparece en las
    presentaciones; el marco, el bloque sin atributos más grande que lo acompaña. Si no se encuentran, los nombres de
    reglas_layout.json → planoUnifilar."""
    from collections import Counter
    titles, frames = Counter(), Counter()
    for layout in doc.layouts:
        if layout.name == "Model":
            continue
        inserts = list(layout.query("INSERT"))
        with_attr = [i for i in inserts if len(i.attribs) >= 3]
        if not with_attr:
            continue
        titles[max(with_attr, key=lambda i: len(i.attribs)).dxf.name] += 1
        def area(i):
            try:
                e = bbox.extents(doc.blocks.get(i.dxf.name), fast=True)
                return (e.extmax.x - e.extmin.x) * (e.extmax.y - e.extmin.y) * i.dxf.xscale * i.dxf.yscale if e.has_data else 0
            except Exception:  # noqa: BLE001
                return 0
        plain = [i for i in inserts if not i.attribs and area(i) > 0]
        if plain:
            frames[max(plain, key=area).dxf.name] += 1
    return {"titleBlock": titles.most_common(1)[0][0] if titles else RULES["titleBlock"],
            "frameBlock": frames.most_common(1)[0][0] if frames else RULES["frameBlock"]}


def analyze_template(path):
    """Lo que necesita la ventana previa: presentaciones con hoja armable, nombre de los bloques y los campos del
    rótulo (etiqueta, texto de ayuda de AutoCAD, valor actual y si se completa solo con el nombre de cada tablero)."""
    doc = ezdxf.readfile(path)
    blocks = detect_blocks(doc)
    prompts = {}
    try:
        for a in doc.blocks.get(blocks["titleBlock"]).query("ATTDEF"):
            prompts[a.dxf.tag] = a.dxf.get("prompt", "") or ""
    except Exception:  # noqa: BLE001
        pass
    sheets, values, per_board = [], {}, None
    from collections import Counter
    hits = Counter()
    for layout in doc.layouts:
        if layout.name == "Model":
            continue
        frame, title = _sheet_inserts(layout, blocks)
        if not (frame and title):
            continue
        sheets.append(layout.name)
        for a in title.attribs:
            if _norm(a.dxf.text) == _norm(layout.name):
                hits[a.dxf.tag] += 1
            values.setdefault(a.dxf.tag, a.dxf.text)
    if hits and sheets:
        tag, n = hits.most_common(1)[0]
        per_board = tag if n >= max(1, len(sheets) // 2) else None
    order = list(prompts) or list(values)
    fields = [{"tag": t, "prompt": prompts.get(t, ""), "value": RULES["titleSuggestions"].get(values.get(t, ""), values.get(t, "")),
               "template": values.get(t, ""), "perBoard": t == per_board} for t in order if t in values or t in prompts]
    return {"sheets": sheets, "blocks": blocks, "fields": fields, "perBoardTag": per_board}


def content_tags(fields):
    """Atributos del rótulo que dicen qué contiene la hoja: los que en el formato traen un texto de
    RULES["titleSuggestions"] (p. ej. «UNIFILAR»). En el plano de fabricación llevan «UNIFILAR Y TOPOGRAFICO»; en el PDF
    de entrega, el contenido de cada hoja."""
    return [f["tag"] for f in fields if f.get("template", "") in RULES["titleSuggestions"]]


def sheet_frame(template_path):
    """Marco y rótulo del formato del usuario, solos, para dibujar otras hojas con el mismo rótulo (PDF de entrega).
    Toma la primera presentación con marco y rótulo y copia los dos tal cual están ahí (bloques, escala, posición y
    estilos de texto). Medidas en mm de papel: el bloque del marco está dibujado en mm de su hoja, así que una unidad del
    marco insertado a escala s es 1/s mm de papel. Devuelve {doc, title, paper, inner, titleBox, unitsPerMm}:
    `inner` es el recuadro interior del marco (la polilínea más grande dentro del borde), `titleBox` la caja del rótulo;
    los dos como (x0, y0, x1, y1) con y desde abajo."""
    src = ezdxf.readfile(template_path)
    blocks = detect_blocks(src)
    for layout in src.layouts:
        if layout.name == "Model":
            continue
        frame, title = _sheet_inserts(layout, blocks)
        if frame and title:
            break
    else:
        raise ValueError("El formato no tiene una presentación con marco y rótulo.")
    doc = ezdxf.new("R2018", setup=True)
    imp = Importer(src, doc)
    imp.import_entities([frame, title], doc.modelspace())
    imp.finalize()
    (bx0, by0, _), (bx1, by1, _) = _block_size(src, frame.dxf.name)
    s = frame.dxf.xscale
    ox, oy = frame.dxf.insert.x + bx0 * s, frame.dxf.insert.y + by0 * frame.dxf.yscale
    for e in doc.modelspace():
        e.translate(-ox, -oy, 0)
    new_title = next(i for i in doc.modelspace().query("INSERT") if i.dxf.name == title.dxf.name)
    pw, ph = bx1 - bx0, by1 - by0
    inner = (0.0, 0.0, pw, ph)
    best = 0.0
    for e in src.blocks.get(frame.dxf.name).query("LWPOLYLINE POLYLINE"):
        b = bbox.extents([e], fast=True)
        if not b.has_data:
            continue
        w, h = b.extmax.x - b.extmin.x, b.extmax.y - b.extmin.y
        if best < w * h < pw * ph * 0.98:
            best, inner = w * h, (b.extmin.x - bx0, b.extmin.y - by0, b.extmax.x - bx0, b.extmax.y - by0)
    tb = bbox.extents([new_title])
    return {"doc": doc, "title": new_title, "paper": (pw, ph), "inner": inner, "unitsPerMm": s,
            "titleBox": (tb.extmin.x / s, tb.extmin.y / s, tb.extmax.x / s, tb.extmax.y / s)}


def _unifilar_viewport(layout):
    """La ventana grande del unifilar (la de mayor área que no sea la ventana general de la presentación)."""
    vps = [v for v in layout.query("VIEWPORT") if v.dxf.get("id", 2) != 1]
    vps = [v for v in vps if v.dxf.width * v.dxf.height > 1000]
    general = max(vps, key=lambda v: v.dxf.width * v.dxf.height) if vps else None
    rest = [v for v in vps if v is not general]
    # la ventana general de la presentación cubre todo el papel y mira al propio papel; la del unifilar mira al modelo
    return max(rest, key=lambda v: v.dxf.width * v.dxf.height) if rest else general


def board_views(project, catalog, fronts, appearances):
    """Topográfico de la aplicación sin lista, notas ni cajetín propio: (doc, caja_frente, caja_puerta) en mm 1:1."""
    doc, front, door = split_views(project, catalog, fronts, appearances)
    return doc, bbox.extents(front, fast=True), bbox.extents(door, fast=True)


def split_views(project, catalog, fronts, appearances):
    """(doc, entidades_frente, entidades_puerta) del DXF del programa, sin lista, notas ni cajetín (también lo usa el PDF de entrega)."""
    doc = ezdxf.read(io.StringIO(build_dxf(project, catalog, fronts, appearances).decode("utf-8")))
    msp = doc.modelspace()
    for e in list(msp):
        if e.dxf.layer in RULES["dropLayers"]:
            msp.delete_entity(e)
    for dim in list(msp.query("DIMENSION")):  # el importador no copia el bloque anónimo de la cota: se explota en líneas y textos
        dim.explode()
    door_layers = set(RULES["doorLayers"])
    body_w = project["enclosure"]["externalBody"]["width"]
    door_x = body_w + RULES["doorGapMm"]  # misma separación que usa cad_export entre frente y puerta
    front, door = [], []
    for e in msp:
        try:
            b = bbox.extents([e], fast=True)
        except Exception:  # noqa: BLE001
            continue
        if not b.has_data:
            continue
        (door if (e.dxf.layer in door_layers or b.extmin.x >= door_x - 1) else front).append(e)
    return doc, front, door


def _fit_scale(views, region_w, region_h, gap, scales):
    """Mayor escala normalizada (1:N) con la que entran las dos vistas, lado a lado o una arriba de la otra."""
    best = None
    for n in scales:
        ws = [(v.extmax.x - v.extmin.x) / n for v in views]
        hs = [(v.extmax.y - v.extmin.y) / n for v in views]
        tw = [len(t) * RULES["titleTextMm"] * RULES["textWidthFactor"] for t in (RULES["frontTitle"], RULES["doorTitle"])]
        side = (sum(max(w, t) for w, t in zip(ws, tw)) + gap, max(hs))
        stack = (max(ws), sum(hs) + gap + RULES["viewTitleBandMm"])
        for mode, (w, h) in (("lado", side), ("arriba", stack)):
            if w <= region_w and h + RULES["viewTitleBandMm"] <= region_h:
                return n, mode
        best = n
    return best, "lado"


def compose(template_path, projects, catalog, fronts, appearances, layouts=None, title_values=None, only_generated=False):
    """Devuelve (texto DXF, informe). `projects`: {nombre de presentación: proyecto}. `title_values`: {atributo: texto}
    cargado por el usuario en la ventana previa (el atributo del nombre del tablero se completa solo con cada hoja).
    `only_generated`: deja en el archivo sólo las hojas armadas."""
    doc = ezdxf.readfile(template_path)
    blocks = detect_blocks(doc)
    info_tag = None
    if title_values is None:
        title_values = {}
    msp = doc.modelspace()
    k = RULES["sheetScale"]  # marco A2 → A1
    report = []
    ext = bbox.extents(msp, fast=True)
    base_x = ext.extmin.x
    base_y = ext.extmin.y - RULES["modelGapMm"]
    by_norm = {_norm(l.name): l.name for l in doc.layouts if l.name != "Model"}
    names = [n for n in (layouts or projects) if n in projects]
    done = []
    for i, name in enumerate(names):
        lname = by_norm.get(_norm(name))
        layout = doc.layouts.get(lname) if lname else None
        if layout is None:
            report.append(f"{name}: el formato no tiene una presentación con ese nombre (no se agregó)")
            continue
        frame, title = _sheet_inserts(layout, blocks)
        uvp = _unifilar_viewport(layout)
        if not (frame and title and uvp):
            report.append(f"{name}: falta el marco, el rótulo o la ventana del unifilar en la presentación")
            continue
        # 1) Hoja A1: el marco se agranda desde su esquina; el rótulo va a la nueva esquina inferior derecha.
        #    La separación al borde se agranda igual que el marco: el recuadro interior del marco también se aleja
        #    del borde ×k, y con la separación vieja el rótulo quedaba encima de esa línea.
        (fx0, fy0, _), (fx1, fy1, _) = _block_size(doc, frame.dxf.name)
        fw, fh = (fx1 - fx0) * frame.dxf.xscale, (fy1 - fy0) * frame.dxf.yscale
        ox, oy = frame.dxf.insert.x, frame.dxf.insert.y
        t_dx = (ox + fw) - title.dxf.insert.x
        t_dy = title.dxf.insert.y - oy
        frame.dxf.xscale *= k
        frame.dxf.yscale *= k
        W, H = fw * k, fh * k
        new_t = (ox + W - t_dx * k, oy + t_dy * k)
        title.translate(new_t[0] - title.dxf.insert.x, new_t[1] - title.dxf.insert.y, 0)  # mueve también sus atributos
        (tx0, ty0, _), (tx1, ty1, _) = _block_size(doc, title.dxf.name)
        title_w, title_h = (tx1 - tx0) * title.dxf.xscale, (ty1 - ty0) * title.dxf.yscale
        per_board = [a.dxf.tag for a in title.attribs if _norm(a.dxf.text) == _norm(layout.name)]
        for a in title.attribs:
            if a.dxf.tag in per_board:
                a.dxf.text = name  # el nombre del tablero, en cada hoja
            elif a.dxf.tag in title_values:
                a.dxf.text = str(title_values[a.dxf.tag])
        # 2) Unifilar: misma ventana y escala, arriba a la izquierda, con los márgenes del formato agrandados.
        left = uvp.dxf.center.x - uvp.dxf.width / 2 - ox
        top = (oy + fh) - (uvp.dxf.center.y + uvp.dxf.height / 2)
        ml, mt = left * k, top * k
        uvp.dxf.center = (ox + ml + uvp.dxf.width / 2, oy + H - mt - uvp.dxf.height / 2)
        u_right = ox + ml + uvp.dxf.width
        u_bottom = oy + H - mt - uvp.dxf.height
        # 3) Topográfico 1:1 en el modelo, lejos de los unifilares.
        src, front_box, door_box = board_views(projects[name], catalog, fronts, appearances)
        dx = base_x + i * RULES["modelPitchMm"]
        dy = base_y - (front_box.extmax.y if front_box.has_data else 0)
        for e in src.modelspace():
            e.translate(dx, dy, 0)
        imp = Importer(src, doc)
        imp.import_modelspace(msp)
        imp.finalize()
        views = []
        for label, box in ((RULES["frontTitle"], front_box), (RULES["doorTitle"], door_box)):
            if box.has_data:
                m = RULES["viewMarginMm"]
                b = bbox.BoundingBox([(box.extmin.x + dx - m, box.extmin.y + dy - m), (box.extmax.x + dx + m, box.extmax.y + dy + m)])
                views.append((label, b))
        # 4) Lugar para las vistas: a la derecha del unifilar (hasta el rótulo) o abajo (a la izquierda del rótulo).
        g = RULES["gapMm"]
        inner_right = ox + W - t_dx
        inner_bottom = oy + t_dy
        regions = {
            "derecha": (u_right + g, inner_bottom + title_h + g, inner_right - (u_right + g), (oy + H - mt) - (inner_bottom + title_h + g)),
            "abajo": (ox + ml, inner_bottom, (inner_right - title_w - g) - (ox + ml), (u_bottom - g) - inner_bottom),
        }
        choice = None
        for rname, (rx, ry, rw, rh) in regions.items():
            n, mode = _fit_scale([b for _, b in views], rw, rh, g, RULES["scales"])
            if choice is None or n < choice[1]:
                choice = (rname, n, mode, rx, ry, rw, rh)
        rname, n, mode, rx, ry, rw, rh = choice
        # 5) Ventanas a escala 1:n; debajo de cada una su título (dos renglones) y la escala. En la disposición lado a
        #    lado cada vista ocupa el ancho mayor entre la vista y su título (los títulos nunca se pisan) y todos los
        #    títulos van en la misma línea.
        cur_x, cur_y = rx, ry + rh
        band, th = RULES["viewTitleBandMm"], RULES["titleTextMm"]
        sized = [(label, b, (b.extmax.x - b.extmin.x) / n, (b.extmax.y - b.extmin.y) / n) for label, b in views]
        title_w = lambda label: len(label) * th * RULES["textWidthFactor"]
        baseline = cur_y - max(vh for _, _, _, vh in sized) - band * 0.35
        for label, b, vw, vh in sized:
            slot = max(vw, title_w(label)) if mode == "lado" else vw
            cx, cy = cur_x + slot / 2, cur_y - vh / 2
            vp = layout.add_viewport(center=(cx, cy), size=(vw, vh),
                                     view_center_point=((b.extmin.x + b.extmax.x) / 2, (b.extmin.y + b.extmax.y) / 2), view_height=vh * n)
            vp.dxf.layer = RULES["viewportLayer"]
            vp.dxf.status = 1
            y_title = baseline if mode == "lado" else cy - vh / 2 - band * 0.35
            for text, dy_t in ((label, 0.0), (f"ESC. 1:{n:g}", th * 1.5)):
                layout.add_text(text, dxfattribs={"layer": RULES["textLayer"], "height": th, "style": "Standard"}).set_placement(
                    (cx, y_title - dy_t), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
            if mode == "lado":
                cur_x += slot + g
            else:
                cur_y -= vh + g + band
        # 6) Ploteo: A1 a escala 1:1 sobre el marco.
        lay = layout.dxf_layout.dxf
        lay.scale_numerator, lay.scale_denominator, lay.unit_factor = 1.0, 1.0, 1.0
        lay.plot_window_x1, lay.plot_window_y1, lay.plot_window_x2, lay.plot_window_y2 = ox, oy, ox + W, oy + H
        lay.limmin, lay.limmax = (ox, oy, 0), (ox + W, oy + H, 0)
        if RULES.get("paperSize"):
            lay.paper_size = RULES["paperSize"]
            lay.paper_width, lay.paper_height = RULES["paperWidthMm"], RULES["paperHeightMm"]
        report.append(f"{name}: unifilar + topográfico ({len(views)} vistas, {mode}, ESC. 1:{n:g}, zona {rname})")
        done.append(layout.name)
    if only_generated and done:
        for layout in list(doc.layouts):
            if layout.name != "Model" and layout.name not in done:
                doc.layouts.delete(layout.name)
    for vp_layer, color in ((RULES["viewportLayer"], 8), (RULES["textLayer"], 7)):
        if vp_layer not in doc.layers:
            doc.layers.add(vp_layer, color=color)
    doc.layers.get(RULES["viewportLayer"]).dxf.plot = 0  # el borde de las ventanas no se plotea
    out = io.StringIO()
    doc.write(out)
    return out.getvalue(), report


if __name__ == "__main__":  # python plano_unifilar.py formato.dxf carpeta_con_proyectos_json salida.dxf
    template, folder, output = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    cat = json.loads((ROOT / "datos" / "catalogo_abb.json").read_text(encoding="utf-8"))
    fr = json.loads((ROOT / "datos" / "frentes_cad.json").read_text(encoding="utf-8"))
    ap = json.loads((ROOT / "datos" / "apariencias_abb.json").read_text(encoding="utf-8"))
    projs = {}
    for f in sorted(folder.glob("*.json")):
        p = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(p, dict) and p.get("devices") is not None and p.get("project"):
            projs[p["project"]] = p
    only = sys.argv[4].split(",") if len(sys.argv) > 4 else None
    text, rep = compose(template, projs, cat, fr, ap, only, title_values=None)
    Path(output).write_text(text, encoding="utf-8")
    print("\n".join(rep))
