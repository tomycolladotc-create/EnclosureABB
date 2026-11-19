"""Exportación DXF: bloques ABB 2D compartidos con la vista del editor.

Los trazos de cada bloque vienen de datos/frentes_cad.json, generados por
work/proyectar_cad.py desde CAD ABB. El JSON del proyecto sólo guarda instancias.
"""

import json
from io import StringIO
from pathlib import Path

import ezdxf
from pintura import fit as paint_fit, resolve as paint_resolve
from etiquetas import label_boxes
LABEL_RULES = json.loads((Path(__file__).resolve().parent / "datos" / "reglas_layout.json").read_text(encoding="utf-8"))["labels"]
from ezdxf.colors import rgb2int

from importador import shell_size
from marcado import resolve
from normativa import check_project
from bom import build_bom, bom_issues


def _color(value):
    value = value.lstrip("#")
    return rgb2int(tuple(int(value[j:j + 2], 16) for j in (0, 2, 4)))


_TRANSLIT = {"×": "x", "—": "-", "–": "-", "Ø": "%%c", "ø": "%%c", "²": "2", "³": "3", "°": "%%d", "±": "%%p", "·": "-", "≥": ">=", "≤": "<=", "“": '"', "”": '"', "‘": "'", "’": "'", "…": "..."}


def _ascii(text):
    """Texto apto para cualquier CAD: saca tildes (ó→o), usa los códigos DXF para Ø/°/± y no deja '?' sueltos."""
    import unicodedata
    out = "".join(_TRANSLIT.get(ch, ch) for ch in str(text))
    out = unicodedata.normalize("NFKD", out).encode("ascii", "ignore").decode("ascii")
    return out


def _door_view(space, ox, project, structure, body, plinth):
    """Puerta cerrada: placa grabada con la nomenclatura, perforaciones de los pilotos del unifilar
    (corte Ø22 de catálogo y bisel Ø30 de CL2-523R) y cartel de riesgo eléctrico. Misma geometría que la
    vista 'Puerta cerrada' del editor, con el eje Y hacia arriba."""
    w, hb = body["width"], body["height"]
    top = plinth + hb

    def Y(y):  # coordenada desde el borde superior de la puerta
        return top - y

    def poly(points, layer, close=True):
        space.add_lwpolyline(points, close=close, dxfattribs={"layer": layer})

    def box(x, y, bw, bh, layer):
        poly([(ox + x, Y(y)), (ox + x + bw, Y(y)), (ox + x + bw, Y(y + bh)), (ox + x, Y(y + bh))], layer)

    def text(value, x, y, height, layer, bold=True):
        space.add_text(_ascii(value), dxfattribs={"height": height, "layer": layer,
                                                  "style": "ABB_ARIAL_BOLD" if bold else "ABB_ARIAL"}).set_placement(
            (ox + x, Y(y)), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

    box(0, 0, w, hb, "ABB_PUERTA_CERRADA")
    box(7, 7, w - 14, hb - 14, "ABB_PUERTA_CERRADA")
    if plinth:
        poly([(ox, 0), (ox + w, 0), (ox + w, plinth), (ox, plinth)], "ABB_PUERTA_CERRADA")
    for hy in (hb * 0.12, hb * 0.88):  # bisagras
        box(0, hy - 22, 9, 44, "ABB_PUERTA_CERRADA")
    locks = (structure or {}).get("locks")
    lock_ys = [hb / 2] if not locks or locks.get("count") == 1 else [locks["F"], hb - locks["F"]]
    for ly in lock_ys:
        space.add_circle((ox + w - 34, Y(ly)), 15, dxfattribs={"layer": "ABB_PUERTA_CERRADA"})
        space.add_circle((ox + w - 34, Y(ly)), 9.5, dxfattribs={"layer": "ABB_PUERTA_CERRADA"})
    # Placa grabada con la nomenclatura del tablero.
    name = str(project.get("project") or "TABLERO").upper()
    pw = min(w * 0.62, 280)
    phh = max(26, min(56, hb * 0.07))
    px, py = (w - pw) / 2, max(40, hb * 0.09)
    fs = min(phh * 0.55, pw * 0.88 / max(len(name), 1) / 0.62)
    box(px, py, pw, phh, "ABB_PUERTA_GRABADO")
    box(px + 3, py + 3, pw - 6, phh - 6, "ABB_PUERTA_GRABADO")
    text(name, w / 2, py + phh / 2, fs, "ABB_PUERTA_GRABADO")
    # Pilotos de presencia de tensión detectados en el unifilar: corte Ø22, bisel Ø30, letra grabada.
    lights = (project.get("signals") or {}).get("pilotLights") or []
    pitch = 48
    ly = py + phh + max(55, hb * 0.07)
    lx0 = w / 2 - (len(lights) - 1) * pitch / 2
    if lights:
        text("PRESENCIA DE TENSION", w / 2, ly - 29, 9.5, "ABB_PUERTA_SENIALIZACION")
    for i, light in enumerate(lights):
        cx = lx0 + i * pitch
        space.add_circle((ox + cx, Y(ly)), 11, dxfattribs={"layer": "ABB_PUERTA_SENIALIZACION"})
        space.add_circle((ox + cx, Y(ly)), 15, dxfattribs={"layer": "ABB_PUERTA_SENIALIZACION"})
        text(light.get("label", ""), cx, ly + 27, 12, "ABB_PUERTA_SENIALIZACION")
    # Cartel de riesgo eléctrico (triángulo amarillo con rayo + leyenda).
    ty = ly + 60 if lights else py + phh + 50
    ts = max(36, min(w * 0.26, 130, (hb - 24 - ty) / 1.25))  # el cartel siempre dentro de la puerta
    tx = w / 2 - ts / 2

    def P(x, y):
        return (ox + tx + x, Y(ty + y))

    poly([P(ts / 2, 0), P(ts, ts * 0.87), P(0, ts * 0.87)], "ABB_PUERTA_CARTEL")
    poly([P(ts * 0.54, ts * 0.22), P(ts * 0.4, ts * 0.52), P(ts * 0.52, ts * 0.52), P(ts * 0.44, ts * 0.76),
          P(ts * 0.64, ts * 0.44), P(ts * 0.52, ts * 0.44), P(ts * 0.6, ts * 0.22)], "ABB_PUERTA_CARTEL")
    box(tx - ts * 0.08, ty + ts * 0.95, ts * 1.16, ts * 0.28, "ABB_PUERTA_CARTEL")
    text("PELIGRO", w / 2, ty + ts * 1.03, ts * 0.09, "ABB_PUERTA_CARTEL")
    text("RIESGO ELECTRICO", w / 2, ty + ts * 1.15, ts * 0.09, "ABB_PUERTA_CARTEL")
    text("VISTA CON LA PUERTA CERRADA", w / 2, hb + plinth + 30, 14, "ABB_NOTAS")


def build_dxf(project, catalog, fronts, appearances):
    if not all("paint" in f for sid, f in fronts["items"].items() if sid in appearances["items"]):
        fronts, appearances = paint_resolve(fronts, appearances, catalog)  # misma pintura y marcado que la pantalla
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4  # mm
    doc.styles.add("ABB_ARIAL", font="arial.ttf")
    doc.styles.add("ABB_ARIAL_BOLD", font="arialbd.ttf")
    layers = {
        "ABB_ENVOLVENTE": 7, "ABB_AREA_FUNCIONAL": 8,
        "ABB_RIEL_DIN_PROPUESTO": 4, "ABB_CAD_COLORES": 7, "ABB_CAD_FRENTE": 7,
        "ABB_SIN_CAD": 2, "ABB_ETIQUETAS": 3, "ABB_NOTAS": 1, "ABB_MARCADO": 7, "ABB_ACCESORIOS": 3, "ABB_CANALETAS": 8, "ABB_PEINES": 30, "ABB_ESTRUCTURA": 8, "ABB_PUERTAS": 9, "ABB_CAJETIN": 7, "ABB_COTAS": 6, "ABB_BOM": 5, "ABB_PUERTA_CERRADA": 7, "ABB_PUERTA_GRABADO": 7, "ABB_PUERTA_SENIALIZACION": 1, "ABB_PUERTA_CARTEL": 2,
    }
    for name, color in layers.items():
        doc.layers.new(name, dxfattribs={"color": color})
    space = doc.modelspace()

    def rect(x, y, width, height, layer):
        space.add_lwpolyline(
            [(x, y), (x + width, y), (x + width, y + height), (x, y + height)],
            close=True, dxfattribs={"layer": layer},
        )

    cabinet = project["enclosure"]
    body = cabinet["externalBody"]
    plinth = cabinet["plinthHeight"]
    fx = cabinet["functionalAreaOffset"]["x"]
    fy = cabinet["functionalAreaOffset"]["y"]
    rect(0, plinth, body["width"], body["height"], "ABB_ENVOLVENTE")
    rect(0, 0, body["width"], plinth, "ABB_ENVOLVENTE")
    # Estructura real (catalogo_abb.json -> enclosures[].structure): banda de montantes/travesaños y hojas de puerta.
    enclosure_spec = spec = next((e for e in catalog["enclosures"] if e["id"] == cabinet.get("id")), None) or next(
        (e for e in catalog["enclosures"] if e["functional"] == cabinet["functional"]), None)
    structure = (spec or {}).get("structure")
    if structure:
        band = structure["frameBand"]
        if band:  # gabinete de estructura (montantes/travesaños); el monobloc no tiene banda
            space.add_lwpolyline([(band, plinth + band), (body["width"] - band, plinth + band), (body["width"] - band, plinth + body["height"] - band),
                                  (band, plinth + body["height"] - band)], close=True, dxfattribs={"layer": "ABB_ESTRUCTURA"})
        left = 0
        for leaf in structure["doorLeaves"]:
            space.add_lwpolyline([(left + 3, plinth + 3), (left + leaf - 3, plinth + 3), (left + leaf - 3, plinth + body["height"] - 3),
                                  (left + 3, plinth + body["height"] - 3)], close=True, dxfattribs={"layer": "ABB_PUERTAS", "linetype": "DASHED"})
            left += leaf
    area = cabinet["functional"]
    rect(fx, fy, area["width"], area["height"], "ABB_AREA_FUNCIONAL")
    for rail in cabinet.get("mountingLayout", {}).get("dinRails", []):
        rect(fx + rail["x"], fy + rail["y"] - rail["height"] / 2,
             rail["length"], rail["height"], "ABB_RIEL_DIN_PROPUESTO")

    shells = {s["id"]: s for s in catalog["deviceShells"]}
    palettes = appearances["items"]
    blocks = {}

    def front_block(shell_id, poles):
        """Bloque por carcasa (y por cantidad de polos si la carcasa es por polo), con un atributo por texto impreso."""
        spec = shells[shell_id]
        tiles = poles if spec.get("poleModule") and poles else 1
        key = (shell_id, tiles if spec.get("poleModule") else None)
        if key in blocks:
            return blocks[key]
        name = f"ABB_{shell_id.replace('abb.', '').replace('.', '_').upper()}" + (f"_{tiles}P" if key[1] else "")
        block = doc.blocks.new(name)
        width, height = shell_size(spec, poles)
        pole_w = width / tiles
        palette = palettes.get(shell_id, {})
        front = fronts["items"][shell_id]
        fx0, fy0, fw_, fh_ = paint_fit(front.get("sourceProjectionExtent"), pole_w, height)  # sin deformar el CAD
        for t in range(tiles):
            ox = t * pole_w + fx0

            if palette:
                # Pintura calculada (pintura.py): silueta exacta del CAD, agujeros y detalles recortados a la silueta.
                for zone in front["paint"]:
                    rings, tint = zone["rings"], zone["color"]
                    hatch = block.add_hatch(dxfattribs={"layer": "ABB_CAD_COLORES", "true_color": _color(tint)})
                    for ring in rings:
                        hatch.paths.add_polyline_path([(round(ox + x * fw_, 4), round(fy0 + y * fh_, 4)) for x, y in ring], is_closed=True)
                if "logo" in palette:
                    lx, ly, word = palette["logo"]
                    block.add_text(word, dxfattribs={"layer": "ABB_CAD_COLORES", "true_color": _color("#ffffff"),
                                                        "height": height * .035, "insert": (ox + lx * fw_, fy0 + ly * fh_)})
            for path in front["paths"]:
                if len(path) >= 2:
                    block.add_lwpolyline(
                        [(round(ox + x * fw_, 4), round(fy0 + y * fh_, 4)) for x, y in path],
                        dxfattribs={"layer": "ABB_CAD_FRENTE", "true_color": _color(palette.get("lineColor", "#273746"))},
                    )
        bar = palette.get("tieBar")
        if bar and tiles >= bar.get("minPoles", 2):
            bx0, bx1 = bar["x0"], width - bar["x1End"]
            block.add_solid([(bx0, bar["y0"]), (bx1, bar["y0"]), (bx0, bar["y1"]), (bx1, bar["y1"])],
                            dxfattribs={"layer": "ABB_CAD_COLORES", "true_color": _color(bar["color"])})
            block.add_lwpolyline([(bx0, bar["y0"]), (bx1, bar["y0"]), (bx1, bar["y1"]), (bx0, bar["y1"])], close=True,
                                 dxfattribs={"layer": "ABB_CAD_FRENTE", "true_color": _color(palette.get("lineColor", "#273746"))})
        # Marcado impreso (apariencias_abb.json -> marking): recuadros fijos en el bloque y un
        # atributo por texto, así el texto viaja con el equipo y se edita con doble clic en AutoCAD.
        marking = palette.get("marking")
        for n, item in enumerate((marking or {}).get("items", [])):
            if "box" in item:
                x0, y0, x1, y1 = item["box"]
                block.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True,
                                     dxfattribs={"layer": "ABB_MARCADO", "true_color": _color(item["color"])})
            block.add_attdef(f"M{n + 1}", (item["x"], item["y"]), dxfattribs={
                "layer": "ABB_MARCADO", "height": item["h"], "true_color": _color(item["color"]),
                "style": "ABB_ARIAL_BOLD" if item.get("bold") else "ABB_ARIAL", "prompt": item["text"],
            })
        blocks[key] = name
        return name

    label_box = {id(d): b for d, b in zip(project["devices"], label_boxes(project["devices"], cabinet["functional"]["width"], LABEL_RULES))}
    for device in project["devices"]:
        x = fx + float(device["x"])
        y = fy + float(device["y"])
        spec = shells.get(device.get("shell"))
        poles = device.get("poles")
        width, height = shell_size(spec, poles) if spec else (device["w"], device["h"])
        if spec and device["shell"] in fronts["items"]:
            ref = space.add_blockref(front_block(device["shell"], poles), (x, y))
            marking = palettes.get(device["shell"], {}).get("marking")
            items = marking.get("items", []) if marking else []
            shown = {it["index"]: it for it in resolve(marking, device.get("marking", {}), poles)} if marking else {}
            for n, item in enumerate(items):
                res = shown.get(n)
                if not res:
                    continue  # dato que el plano no trae o condición de polos: no se inventa
                attrib = ref.add_attrib(f"M{n + 1}", _ascii(res["text"]), (0, 0), dxfattribs={
                    "layer": "ABB_MARCADO", "height": item["h"], "true_color": _color(item["color"]),
                    "style": "ABB_ARIAL_BOLD" if item.get("bold") else "ABB_ARIAL"})
                ax, ay = x + item["x"], y + item["y"]
                if item.get("w"):
                    attrib.set_placement((ax, ay - item["h"] / 2), (ax + item["w"], ay - item["h"] / 2),
                                         align=ezdxf.enums.TextEntityAlignment.FIT)
                else:
                    attrib.set_placement((ax, ay), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER
                                         if item.get("align") == "center" else ezdxf.enums.TextEntityAlignment.MIDDLE_LEFT)
        else:
            rect(x, y, width, height, "ABB_SIN_CAD")  # contorno de la ficha: sin frente CAD de ABB, se rotula el modelo
            space.add_text(str(device.get("model") or ""), dxfattribs={"height": round(min(5.7, width / max(len(str(device.get("model") or "")), 1) / 0.75), 2),
                                                                     "layer": "ABB_SIN_CAD"}).set_placement((x + width / 2, y + height / 2), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
        # Porta-etiqueta bajo el equipo con el nombre del circuito (igual que en el editor; un solo rótulo por equipo).
        name = device.get("circuit") or device["tag"]  # en el dibujo va el nombre del circuito; el QF queda como dato
        box = label_box[id(device)]
        lw, lh = box["w"], LABEL_RULES["heightMm"]
        lx, ly = fx + box["x"], y - LABEL_RULES["gapBelowMm"] - lh
        rect(lx, ly, lw, lh, "ABB_ETIQUETAS")
        tag_h = box["font"] * 0.716  # alto de mayúscula de la letra del editor (Arial)
        space.add_text(name, dxfattribs={"height": tag_h, "layer": "ABB_ETIQUETAS"}).set_placement(
            (lx + lw / 2, ly + lh / 2), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    # Accesorios de normativa (bornes de tierra, peines): geometría esquemática marcada como provisoria.
    for acc in project.get("accessories", []):
        if acc.get("placed", True) and acc.get("decision") != "discarded" and "x" in acc and acc.get("w"):
            layer = {"wiring_duct": "ABB_CANALETAS", "comb": "ABB_PEINES"}.get(acc["type"], "ABB_ACCESORIOS")
            rect(fx + acc["x"], fy + acc["y"], acc["w"], acc["h"], layer)
            if acc["type"] == "wiring_duct":  # tapa central: las uñas laterales quedan a cada lado (esquemático)
                if acc.get("orientation") == "v":
                    finger = max(3, acc["w"] * 0.3)
                    for xx in (acc["x"] + finger, acc["x"] + acc["w"] - finger):
                        space.add_line((fx + xx, fy + acc["y"]), (fx + xx, fy + acc["y"] + acc["h"]), dxfattribs={"layer": layer})
                else:
                    finger = max(3, acc["h"] * 0.3)
                    for yy in (acc["y"] + finger, acc["y"] + acc["h"] - finger):
                        space.add_line((fx + acc["x"], fy + yy), (fx + acc["x"] + acc["w"], fy + yy), dxfattribs={"layer": layer})
            if acc["type"] == "pe_terminal" and acc.get("style") == "repartidor":  # bloques repartidores PE + topes (bornes esquemáticos)
                sw, bw, H = acc.get("stopW", 0), acc.get("blockW", acc["w"]), acc["h"]
                for i in range(acc.get("blocks", 1)):
                    bx = fx + acc["x"] + sw + i * bw
                    space.add_line((bx, fy + acc["y"]), (bx, fy + acc["y"] + H), dxfattribs={"layer": layer})
                    space.add_circle((bx + bw / 2, fy + acc["y"] + H * 0.9), 4.9, dxfattribs={"layer": layer})  # entrada Ø9,8
                    for k in range(acc.get("outputs", 7)):
                        space.add_circle((bx + bw * (0.7 if k % 2 else 0.3), fy + acc["y"] + H * (0.63 - 0.145 * (k // 2))), 3.2, dxfattribs={"layer": layer})
                space.add_line((fx + acc["x"] + acc["w"] - sw, fy + acc["y"]), (fx + acc["x"] + acc["w"] - sw, fy + acc["y"] + H), dxfattribs={"layer": layer})
                ex, ey, es = fx + acc["x"] + sw + 6, fy + acc["y"] + H * 0.1, 3.5  # símbolo de tierra para identificar la bornera PAT
                for x1, y1, x2, y2 in ((ex, ey + es, ex, ey), (ex - es * .9, ey, ex + es * .9, ey), (ex - es * .6, ey - es * .38, ex + es * .6, ey - es * .38), (ex - es * .3, ey - es * .76, ex + es * .3, ey - es * .76)):
                    space.add_line((x1, y1), (x2, y2), dxfattribs={"layer": layer})
            if acc["type"] == "distribution_block":  # 4 barras con sus bornes (esquemático)
                n, ins, outs = acc.get("poles") or 4, acc.get("inputsPerPole") or 1, acc.get("outputsPerPole") or 11
                top, rh = acc["y"] + acc["h"] * 0.08, acc["h"] * 0.82 / n
                for p in range(n):
                    cy = fy + top + rh * (p + 0.5)
                    space.add_line((fx + acc["x"] + 16, cy - rh * .22), (fx + acc["x"] + acc["w"] - 6, cy - rh * .22), dxfattribs={"layer": layer})
                    space.add_line((fx + acc["x"] + 16, cy + rh * .22), (fx + acc["x"] + acc["w"] - 6, cy + rh * .22), dxfattribs={"layer": layer})
                    bx, bw = fx + acc["x"] + 16, acc["w"] - 22
                    for k in range(ins):
                        space.add_circle((bx + 6 + k * 10, cy), min(4.2, rh * .3), dxfattribs={"layer": layer})
                    for k in range(outs):
                        space.add_circle((bx + 6 + ins * 10 + 3 + k * ((bw - ins * 10 - 12) / max(1, outs - 1)), cy), min(2.6, rh * .2), dxfattribs={"layer": layer})
            if acc["type"] == "signal_fuses":  # portafusibles 1P (uno por testigo de fase): divisiones, ventana del fusible y fase
                n, pw = acc.get("count", 1), acc.get("poleW") or acc["w"] / max(1, acc.get("count", 1))
                for i in range(n):
                    bx = fx + acc["x"] + i * pw
                    if i:
                        space.add_line((bx, fy + acc["y"]), (bx, fy + acc["y"] + acc["h"]), dxfattribs={"layer": layer})
                    rect(bx + pw * 0.08, fy + acc["y"] + acc["h"] * 0.25, pw * 0.84, acc["h"] * 0.5, layer)
                    rect(bx + pw * 0.3, fy + acc["y"] + acc["h"] * 0.38, pw * 0.4, acc["h"] * 0.3, layer)
                    phase = (acc.get("phases") or [None] * n)[i] if i < len(acc.get("phases") or []) else None
                    if phase:
                        space.add_text(_ascii(str(phase)), dxfattribs={"height": min(5, pw * 0.35), "layer": "ABB_ETIQUETAS"}).set_placement(
                            (bx + pw / 2, fy + acc["y"] + acc["h"] * 0.3), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
            if acc["type"] == "copper_busbar":  # agujeros M6 cada 25 mm
                pitch = acc.get("holePitchMm")  # del catálogo de la barra; sin dato, la barra va sin agujeros dibujados
                for k in range(int((acc["w"] - pitch / 2) // pitch) if pitch else 0):
                    space.add_circle((fx + acc["x"] + pitch / 2 + k * pitch, fy + acc["y"] + acc["h"] / 2), 3.2, dxfattribs={"layer": layer})
            if acc["type"] == "comb":  # una clavija por polo
                n = acc.get("poleCount") or max(1, round(acc["w"] / (acc.get("pitchMm") or 17.5)))
                for i in range(n):
                    cx = fx + acc["x"] + (i + 0.5) * acc["w"] / n
                    rect(cx - 2.2, fy + acc["y"] + acc["h"] * 0.2, 4.4, acc["h"] * 0.6, layer)
            # Sin texto en el dibujo: la descripción de accesorios va solo en el cómputo de materiales (bom.py).
    # Cotas: exterior y placa/área funcional (valores del catálogo y del proyecto)
    for base, p1, p2, ang in (((0, -28), (0, 0), (body["width"], 0), 0), ((body["width"] + 40, 0), (body["width"], 0), (body["width"], body["height"] + plinth), 90)):
        dim = space.add_linear_dim(base=base, p1=p1, p2=p2, angle=ang, dxfattribs={"layer": "ABB_COTAS"})
        dim.render()
    revision = str(project.get("currentRevision", "SIN REVISION"))
    top_y = plinth + body["height"]
    title = f"{project.get('project', 'TABLERO')} - REV. {revision} - VISTA 2D FRONTAL (PUERTA RETIRADA)"
    space.add_text(_ascii(title), dxfattribs={"height": 17, "layer": "ABB_NOTAS", "insert": (0, top_y + 30)})
    # Cajetín debajo del tablero: partes del gabinete. Mismo criterio que la lista de materiales (bom.py) para
    # que el plano no contradiga la compra: sin menús de opciones ni la placa que ya viene con el gabinete.
    y = -60
    if structure:
        space.add_text(_ascii("PARTES DEL GABINETE (" + (enclosure_spec or {}).get("label", cabinet.get("line", "ABB")) + ")"), dxfattribs={"height": 14, "layer": "ABB_CAJETIN", "insert": (0, y)})
        plate_included = str(structure["bom"][0].get("codigo", "")).startswith("SRN") if structure["bom"] else False
        for n, part in enumerate(structure["bom"]):
            code = str(part.get("codigo", ""))
            if " / " in code or (n and plate_included and "placa" in str(part.get("parte", "")).lower()):
                continue
            y -= 16
            line = f"{part['parte']}: {code}" + (f" ({part['orden']})" if part.get("orden") else "") + f" - cat. pag. {part['pagina']}"
            space.add_text(_ascii(line), dxfattribs={"height": 10, "layer": "ABB_CAJETIN", "insert": (0, y)})
        if plate_included:
            y -= 16
            space.add_text("La placa interna viene incluida con el gabinete (no se compra aparte).", dxfattribs={"height": 10, "layer": "ABB_CAJETIN", "insert": (0, y)})
        y -= 18
        space.add_text(_ascii("FUENTE: " + structure["source"]), dxfattribs={"height": 7, "layer": "ABB_CAJETIN", "insert": (0, y)})
    # Avisos de normativa fuera del dibujo (debajo del cajetín), para que no se pierdan ni tapen equipos.
    y -= 30
    space.add_text("GABINETE Y RIEL: CONFIGURACION PRELIMINAR; VALIDAR CON ABB ARGENTINA", dxfattribs={"height": 10, "layer": "ABB_NOTAS", "insert": (0, y)})
    for finding in check_project(project):
        tag = "ERROR" if finding["severity"] == "error" else "AVISO"
        note = f"NORMATIVA {tag}: {finding['message']}" + ("" if finding["ruleStatus"] == "verificada" else " (regla por verificar)")
        y -= 14
        space.add_text(_ascii(note), dxfattribs={"height": 8, "layer": "ABB_NOTAS", "insert": (0, y)})
    # Vista con la puerta cerrada, al lado del frente interior (misma escala 1:1).
    door_x = body["width"] + 150
    _door_view(space, door_x, project, structure, body, plinth)
    # BOM agrupada a la derecha de la vista de puerta, con los controles anti-error de compra al final.
    bom_x, bom_y = door_x + body["width"] + 150, top_y
    space.add_text(_ascii(f"LISTA DE MATERIALES - REV. {revision}"), dxfattribs={"height": 14, "layer": "ABB_BOM", "insert": (bom_x, bom_y)})
    rows = build_bom(project, catalog)
    for n, row in enumerate(rows):
        line = f"{row['quantity']} {row.get('unit', 'u')} [{row['category']}] {row['code']} - {row['description']}"
        space.add_text(_ascii(line), dxfattribs={"height": 8, "layer": "ABB_BOM", "insert": (bom_x, bom_y - 22 - 13 * n)})
    issues = bom_issues(rows, project)
    for k, issue in enumerate(issues):
        text = issue.get("message", issue) if isinstance(issue, dict) else issue
        space.add_text(_ascii("CONTROL: " + str(text)[:220]), dxfattribs={"height": 8, "layer": "ABB_NOTAS", "insert": (bom_x, bom_y - 40 - 13 * (len(rows) + k))})
    stream = StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")
