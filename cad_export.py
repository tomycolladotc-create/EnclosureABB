"""Exportación DXF: bloques ABB 2D compartidos con la vista del editor.

Los trazos de cada bloque vienen de datos/frentes_cad.json, generados por
work/proyectar_cad.py desde CAD ABB. El JSON del proyecto sólo guarda instancias.
"""

from io import StringIO

import ezdxf
from ezdxf.colors import rgb2int


def build_dxf(project, catalog, fronts, appearances):
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4  # mm
    layers = {
        "ABB_ENVOLVENTE": 7, "ABB_AREA_FUNCIONAL": 8,
        "ABB_RIEL_DIN_PROPUESTO": 4, "ABB_CAD_COLORES": 7, "ABB_CAD_FRENTE": 7,
        "ABB_SIN_CAD": 2, "ABB_ETIQUETAS": 3, "ABB_NOTAS": 1,
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
    area = cabinet["functional"]
    rect(fx, fy, area["width"], area["height"], "ABB_AREA_FUNCIONAL")
    for rail in cabinet.get("mountingLayout", {}).get("dinRails", []):
        rect(fx + rail["x"], fy + rail["y"] - rail["height"] / 2,
             rail["length"], rail["height"], "ABB_RIEL_DIN_PROPUESTO")

    shells = {s["id"]: s for s in catalog["deviceShells"]}
    block_names = {}
    palettes = appearances["items"]
    for i, (shell_id, front) in enumerate(fronts["items"].items(), 1):
        spec = shells.get(shell_id)
        if not spec:
            continue
        name = f"ABB_FRONT_{i:02d}"
        block = doc.blocks.new(name)
        width, height = spec["width"], spec["height"]
        palette = palettes.get(shell_id, {})
        def color(value):
            value = value.lstrip("#")
            return rgb2int(tuple(int(value[j:j + 2], 16) for j in (0, 2, 4)))
        def fill_rect(x, y, w, h, tint):
            # SOLID de DXF usa orden en "Z" (0-1-3-2): si se pasa el rectángulo en orden
            # perimetral, AutoCAD lo dibuja como dos triángulos cruzados ("moño").
            points = [(x * width, y * height), ((x + w) * width, y * height),
                      (x * width, (y + h) * height), ((x + w) * width, (y + h) * height)]
            block.add_solid(points, dxfattribs={"layer": "ABB_CAD_COLORES", "true_color": color(tint)})
        if palette:
            fill_rect(0, 0, 1, 1, palette["base"])
            for x, y, w, h, tint in palette["parts"]:
                fill_rect(x, y, w, h, tint)
            if "logo" in palette:
                lx, ly, word = palette["logo"]
                block.add_text(word, dxfattribs={"layer": "ABB_CAD_COLORES", "true_color": color("#ffffff"),
                                                    "height": height * .035, "insert": (lx * width, ly * height)})
        for path in front["paths"]:
            if len(path) >= 2:
                block.add_lwpolyline(
                    [(round(x * width, 4), round(y * height, 4)) for x, y in path],
                    dxfattribs={"layer": "ABB_CAD_FRENTE", "true_color": color(palette.get("lineColor", "#273746"))},
                )
        block_names[shell_id] = name

    for device in project["devices"]:
        x = fx + float(device["x"])
        y = fy + float(device["y"])
        spec = shells.get(device.get("shell"), {})
        width, height = spec.get("width", device["w"]), spec.get("height", device["h"])
        name = block_names.get(device.get("shell"))
        if name:
            space.add_blockref(name, (x, y))
        else:
            rect(x, y, width, height, "ABB_SIN_CAD")
        space.add_text(device["tag"], dxfattribs={"height": 12, "layer": "ABB_ETIQUETAS", "insert": (x, y + height + 7)})
        label = device.get("model", "")[:32].encode("ascii", "replace").decode("ascii")
        space.add_text(label, dxfattribs={"height": 7, "layer": "ABB_ETIQUETAS", "insert": (x, y - 12)})
    space.add_text("TS4 - VISTA 2D FRONTAL - GEOMETRIA ABB DONDE HAY CAD", dxfattribs={"height": 17, "layer": "ABB_NOTAS", "insert": (35, plinth + body["height"] - 35)})
    space.add_text("GABINETE Y RIEL: CONFIGURACION PRELIMINAR; VALIDAR CON ABB ARGENTINA", dxfattribs={"height": 10, "layer": "ABB_NOTAS", "insert": (35, 35)})
    stream = StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")
