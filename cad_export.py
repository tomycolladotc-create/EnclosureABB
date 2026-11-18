"""Exportación DXF: bloques ABB 2D compartidos con la vista del editor.

Los trazos de cada bloque vienen de datos/frentes_cad.json, generados por
work/proyectar_cad.py desde CAD ABB. El JSON del proyecto sólo guarda instancias.
"""

from io import StringIO

import ezdxf
from ezdxf.colors import rgb2int

from importador import shell_size
from marcado import resolve
from normativa import check_project
from bom import build_bom


def _color(value):
    value = value.lstrip("#")
    return rgb2int(tuple(int(value[j:j + 2], 16) for j in (0, 2, 4)))


def build_dxf(project, catalog, fronts, appearances):
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4  # mm
    doc.styles.add("ABB_ARIAL", font="arial.ttf")
    doc.styles.add("ABB_ARIAL_BOLD", font="arialbd.ttf")
    layers = {
        "ABB_ENVOLVENTE": 7, "ABB_AREA_FUNCIONAL": 8,
        "ABB_RIEL_DIN_PROPUESTO": 4, "ABB_CAD_COLORES": 7, "ABB_CAD_FRENTE": 7,
        "ABB_SIN_CAD": 2, "ABB_ETIQUETAS": 3, "ABB_NOTAS": 1, "ABB_MARCADO": 7, "ABB_ACCESORIOS": 3, "ABB_CANALETAS": 8, "ABB_PEINES": 30, "ABB_ESTRUCTURA": 8, "ABB_PUERTAS": 9, "ABB_CAJETIN": 7, "ABB_COTAS": 6, "ABB_BOM": 5,
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
    spec = next((e for e in catalog["enclosures"] if e["id"] == cabinet.get("id")), None) or next(
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
        for t in range(tiles):
            ox = t * pole_w

            def fill_rect(x, y, w, h, tint):
                # SOLID de DXF usa orden en "Z" (0-1-3-2): si se pasa el rectángulo en orden
                # perimetral, AutoCAD lo dibuja como dos triángulos cruzados ("moño").
                points = [(ox + x * pole_w, y * height), (ox + (x + w) * pole_w, y * height),
                          (ox + x * pole_w, (y + h) * height), (ox + (x + w) * pole_w, (y + h) * height)]
                block.add_solid(points, dxfattribs={"layer": "ABB_CAD_COLORES", "true_color": _color(tint)})
            if palette:
                fill_rect(0, 0, 1, 1, palette["base"])
                for x, y, w, h, tint in palette["parts"]:
                    fill_rect(x, y, w, h, tint)
                if "logo" in palette:
                    lx, ly, word = palette["logo"]
                    block.add_text(word, dxfattribs={"layer": "ABB_CAD_COLORES", "true_color": _color("#ffffff"),
                                                        "height": height * .035, "insert": (ox + lx * pole_w, ly * height)})
            for path in front["paths"]:
                if len(path) >= 2:
                    block.add_lwpolyline(
                        [(round(ox + x * pole_w, 4), round(y * height, 4)) for x, y in path],
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
                attrib = ref.add_attrib(f"M{n + 1}", res["text"].encode("ascii", "replace").decode("ascii"), (0, 0), dxfattribs={
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
            rect(x, y, width, height, "ABB_SIN_CAD")
        # Porta-etiqueta bajo el equipo con el nombre del circuito (igual que en el editor; un solo rótulo por equipo).
        name = device.get("circuit") or device["tag"]  # en el dibujo va el nombre del circuito; el QF queda como dato
        lw, lh = min(max(width - 4, 14), 64), 12
        lx, ly = x + (width - lw) / 2, y - 4 - lh
        rect(lx, ly, lw, lh, "ABB_ETIQUETAS")
        tag_h = round(min(8.5, lw / max(len(name), 1) / 0.75), 2)
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
            if acc["type"] == "comb":  # una clavija por polo
                n = acc.get("poleCount") or max(1, round(acc["w"] / (acc.get("pitchMm") or 17.5)))
                for i in range(n):
                    cx = fx + acc["x"] + (i + 0.5) * acc["w"] / n
                    rect(cx - 2.2, fy + acc["y"] + acc["h"] * 0.2, 4.4, acc["h"] * 0.6, layer)
            # Sin texto en el dibujo: la descripción de accesorios va solo en el cómputo de materiales (bom.py).
    # Avisos de normativa dentro del dibujo, para que no se pierdan al exportar.
    for n, finding in enumerate(check_project(project)):
        tag = "ERROR" if finding["severity"] == "error" else "AVISO"
        note = f"NORMATIVA {tag}: {finding['message']}" + ("" if finding["ruleStatus"] == "verificada" else " (regla por verificar)")
        space.add_text(note.encode("ascii", "replace").decode("ascii"), dxfattribs={"height": 8, "layer": "ABB_NOTAS", "insert": (35, 60 + 14 * n)})
    # Cotas: exterior y placa/área funcional (valores del catálogo y del proyecto)
    for base, p1, p2, ang in (((0, -28), (0, 0), (body["width"], 0), 0), ((body["width"] + 40, 0), (body["width"], 0), (body["width"], body["height"] + plinth), 90)):
        dim = space.add_linear_dim(base=base, p1=p1, p2=p2, angle=ang, dxfattribs={"layer": "ABB_COTAS"})
        dim.render()
    # Cajetín debajo del tablero: lista de partes del gabinete con códigos ABB y página del catálogo.
    if structure:
        top = -60
        space.add_text("LISTA DE PARTES DEL GABINETE (" + spec["label"] + ")", dxfattribs={"height": 14, "layer": "ABB_CAJETIN", "insert": (0, top)})
        for n, part in enumerate(structure["bom"]):
            line = f"{part['parte']}: {part['codigo']}" + (f" ({part['orden']})" if part.get("orden") else "") + f" - cat. pag. {part['pagina']}"
            space.add_text(line.encode("ascii", "replace").decode("ascii"), dxfattribs={"height": 10, "layer": "ABB_CAJETIN", "insert": (0, top - 24 - 16 * n)})
        space.add_text(("FUENTE: " + structure["source"]).encode("ascii", "replace").decode("ascii"), dxfattribs={"height": 7, "layer": "ABB_CAJETIN", "insert": (0, top - 40 - 16 * len(structure["bom"]))})
    # BOM agrupada a la derecha del tablero. La versión CSV conserva además fuentes y estados completos.
    bom_x, bom_y = body["width"] + 100, plinth + body["height"]
    revision = str(project.get("currentRevision", "SIN REVISION"))
    space.add_text(f"LISTA DE MATERIALES - REV. {revision}".encode("ascii", "replace").decode("ascii"), dxfattribs={"height": 14, "layer": "ABB_BOM", "insert": (bom_x, bom_y)})
    for n, row in enumerate(build_bom(project, catalog)):
        line = f"{row['quantity']} x [{row['category']}] {row['code']} - {row['description']}"
        space.add_text(line.encode("ascii", "replace").decode("ascii"), dxfattribs={"height": 8, "layer": "ABB_BOM", "insert": (bom_x, bom_y - 22 - 13 * n)})
    title = f"{project.get('project', 'TABLERO')} - REV. {revision} - VISTA 2D FRONTAL - GEOMETRIA ABB DONDE HAY CAD"
    space.add_text(title.encode("ascii", "replace").decode("ascii"), dxfattribs={"height": 17, "layer": "ABB_NOTAS", "insert": (35, plinth + body["height"] - 35)})
    space.add_text("GABINETE Y RIEL: CONFIGURACION PRELIMINAR; VALIDAR CON ABB ARGENTINA", dxfattribs={"height": 10, "layer": "ABB_NOTAS", "insert": (35, 35)})
    stream = StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")
