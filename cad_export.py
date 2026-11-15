"""Exportación DXF: bloques ABB 2D compartidos con la vista del editor.

Los trazos de cada bloque vienen de datos/frentes_cad.json, generados por
work/proyectar_cad.py desde CAD ABB. El JSON del proyecto sólo guarda instancias.
"""

from io import StringIO

import ezdxf
from ezdxf.colors import rgb2int

from importador import shell_size


def _color(value):
    value = value.lstrip("#")
    return rgb2int(tuple(int(value[j:j + 2], 16) for j in (0, 2, 4)))


def inscription_height(text, width, height):
    """Altura de texto que entra en el frente: como mucho 7 % del alto y ~90 % del ancho."""
    return round(min(height * 0.07, width * 0.9 / max(len(text), 1) / 0.8), 2)


def build_dxf(project, catalog, fronts, appearances):
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4  # mm
    layers = {
        "ABB_ENVOLVENTE": 7, "ABB_AREA_FUNCIONAL": 8,
        "ABB_RIEL_DIN_PROPUESTO": 4, "ABB_CAD_COLORES": 7, "ABB_CAD_FRENTE": 7,
        "ABB_SIN_CAD": 2, "ABB_ETIQUETAS": 3, "ABB_NOTAS": 1, "ABB_INSCRIPCION": 7,
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
    palettes = appearances["items"]
    blocks = {}

    def front_block(shell_id, poles):
        """Bloque por carcasa (y por cantidad de polos si la carcasa es por polo), con atributo MODELO."""
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
        spot = palette.get("inscription")
        if spot and spot.get("enabled"):  # solo con posición verificada en el equipo real
            block.add_attdef("MODELO", (width / 2, spot["y"] * height), dxfattribs={
                "layer": "ABB_INSCRIPCION", "height": inscription_height("XXXXXXXXXX", width, height),
                "true_color": _color(spot["color"]), "prompt": "Modelo grabado en el frente",
            }).set_placement((width / 2, spot["y"] * height), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
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
            text = (device.get("model") or "").encode("ascii", "replace").decode("ascii")[:24]
            if palettes.get(device["shell"], {}).get("inscription", {}).get("enabled"):
                ref.add_auto_attribs({"MODELO": text})
                for attrib in ref.attribs:
                    attrib.dxf.height = inscription_height(text, width, height)
        else:
            rect(x, y, width, height, "ABB_SIN_CAD")
        # Etiqueta centrada y achicada para que no se pise con la del equipo vecino.
        tag_h = round(min(12, width * 0.95 / max(len(device["tag"]), 1) / 0.75), 2)
        space.add_text(device["tag"], dxfattribs={"height": tag_h, "layer": "ABB_ETIQUETAS"}).set_placement(
            (x + width / 2, y + height + 4), align=ezdxf.enums.TextEntityAlignment.BOTTOM_CENTER)
    space.add_text(f"{project.get('project', 'TABLERO')} - VISTA 2D FRONTAL - GEOMETRIA ABB DONDE HAY CAD".encode("ascii", "replace").decode("ascii"), dxfattribs={"height": 17, "layer": "ABB_NOTAS", "insert": (35, plinth + body["height"] - 35)})
    space.add_text("GABINETE Y RIEL: CONFIGURACION PRELIMINAR; VALIDAR CON ABB ARGENTINA", dxfattribs={"height": 10, "layer": "ABB_NOTAS", "insert": (35, 35)})
    stream = StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")
