"""Planos de taller por tablero (pedido de Thomas 2026-11-23): perforado de la puerta con cotas y vista lateral con la
profundidad útil del gabinete contra el equipo más profundo. Las placas de identificación salen en el Excel
(excel_equipamiento: hoja «Placas de identificación»).

La geometría de la puerta es la misma de la vista «puerta cerrada» (cad_export.door_features): las perforaciones del
plano de taller no pueden diferir del dibujo. El diámetro de corte de los pilotos sale del catálogo de accesorios.
Medidas en mm; textos y separaciones: datos/reglas_layout.json → taller.
"""
import json
from pathlib import Path

import ezdxf
from ezdxf.enums import TextEntityAlignment

from cad_export import door_features
from validacion import _is_din

import rutas
ROOT = rutas.BUNDLE_ROOT
RULES = rutas.read_json("reglas_layout.json")["taller"]
DIM = {"dimlfac": 1, "dimdec": 1, "dimdsep": ord(","), "dimzin": 8}  # dimlfac 1: el estilo EZDXF supone metros y multiplica por 100; cotas en mm con coma decimal, un decimal y sin ceros sobrantes (349,5 / 250)


def _spec(project, catalog):
    cab = project["enclosure"]
    return next((e for e in catalog["enclosures"] if e["id"] == cab.get("id")), None) or next(
        (e for e in catalog["enclosures"] if e["functional"] == cab["functional"]), None) or {}


def door_holes(project, catalog, accessories):
    """Perforaciones a hacer en la puerta: [{n, x, y, d, uso}] (x desde el borde izquierdo, y desde el borde superior)."""
    f = door_features(project, _spec(project, catalog).get("structure"), project["enclosure"]["externalBody"])
    pilot = next(iter(accessories.get("pilotLights", [])), {})
    holes = []
    for light in f["lights"]:
        holes.append({"x": round(light["x"], 1), "y": round(light["y"], 1), "d": pilot.get("agujeroMm", light["cutR"] * 2),
                      "uso": f"Luz piloto {pilot.get('tipo', '')} fase {light['label']}".strip()})
    for k, h in enumerate(sorted(holes, key=lambda h: (h["y"], h["x"])), start=1):
        h["n"] = k
    return f, holes


def depth_check(project, catalog):
    """Profundidad útil del gabinete contra el equipo más profundo (equipo + riel DIN si va en riel)."""
    cab = project["enclosure"]
    useful = cab["functional"]["depth"]
    shells = {s["id"]: s for s in catalog["deviceShells"]}
    best, unknown = None, []
    for d in project.get("devices", []):
        shell = shells.get(d.get("shell"), {})
        depth = shell.get("depthMm")
        if not depth:
            unknown.append(d.get("tag", "?"))
            continue
        on_rail = _is_din(d, shells)
        total = depth + (RULES["dinRailDepthMm"] if on_rail else 0)
        if not best or total > best["total"]:
            best = {"tag": d.get("tag"), "model": d.get("model"), "depth": depth, "total": total, "rail": on_rail,
                    "source": shell.get("depthSource", "")}
    return {"useful": useful, "external": cab["externalBody"]["depth"], "deepest": best, "unknown": unknown,
            "margin": round(useful - best["total"], 1) if best else None}


def shop_doc(project, catalog, accessories, scale=1):
    """DXF (ezdxf) con el perforado de puerta acotado y la vista lateral, en mm 1:1. `scale` = N de la escala 1:N con que
    se va a imprimir: los textos, cotas y separaciones se dan en mm de papel (reglas) y se multiplican por N."""
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4
    doc.header["$LWDISPLAY"] = 0
    doc.header["$CELWEIGHT"] = 9
    doc.layers.get("0").dxf.lineweight = 9
    if "EZDXF" in doc.dimstyles:
        ds = doc.dimstyles.get("EZDXF")
        ds.dxf.dimlwd = 5
        ds.dxf.dimlwe = 5
    msp = doc.modelspace()
    if not doc.styles.has_entry("ABB_UI"):
        doc.styles.add("ABB_UI", font="segoeui.ttf")
    if not doc.styles.has_entry("ABB_UI_BOLD"):
        doc.styles.add("ABB_UI_BOLD", font="segoeuib.ttf")
    t, ts, off = RULES["textMm"] * scale, RULES["smallTextMm"] * scale, RULES["dimOffsetMm"] * scale
    for name, color, lw in (("TALLER", 7, 18), ("TALLER_FABRICA", 8, 9), ("TALLER_COTAS", 1, 5), ("TALLER_PEGADO", 5, 9)):
        doc.layers.add(name, color=color, lineweight=lw)
    f, holes = door_holes(project, catalog, accessories)
    w, h = f["w"], f["h"]
    Y = lambda y: h - y  # noqa: E731  (y desde el borde superior → eje hacia arriba)

    def rect(x, y, rw, rh, layer, dashed=False):
        msp.add_lwpolyline([(x, Y(y)), (x + rw, Y(y)), (x + rw, Y(y + rh)), (x, Y(y + rh))], close=True,
                           dxfattribs={"layer": layer, "linetype": "DASHED" if dashed else "CONTINUOUS"})

    def text(value, x, y, height, layer="TALLER", align=TextEntityAlignment.MIDDLE_CENTER, bold=False):
        style = "ABB_UI_BOLD" if bold else "ABB_UI"
        msp.add_text(value, dxfattribs={"height": height, "layer": layer, "style": style}).set_placement((x, y), align=align)

    rect(0, 0, w, h, "TALLER")
    for hy, hh in f["hinges"]:
        rect(0, hy, 9, hh, "TALLER_FABRICA")
    for lx, ly in f["locks"]:
        msp.add_circle((lx, Y(ly)), f["lockR"][0], dxfattribs={"layer": "TALLER_FABRICA"})
    pl, sg = f["plate"], f["sign"]
    rect(pl["x"], pl["y"], pl["w"], pl["h"], "TALLER_PEGADO", dashed=True)
    rect(sg["x"] - sg["size"] * 0.08, sg["y"], sg["size"] * 1.16, sg["size"] * 1.23, "TALLER_PEGADO", dashed=True)
    for hole in holes:
        cx, cy = hole["x"], Y(hole["y"])
        msp.add_circle((cx, cy), hole["d"] / 2, dxfattribs={"layer": "TALLER"})
        msp.add_line((cx - hole["d"] * 0.8, cy), (cx + hole["d"] * 0.8, cy), dxfattribs={"layer": "TALLER_COTAS"})
        msp.add_line((cx, cy - hole["d"] * 0.8), (cx, cy + hole["d"] * 0.8), dxfattribs={"layer": "TALLER_COTAS"})
        text(str(hole["n"]), cx + hole["d"] * 0.75, cy + hole["d"] * 0.75, ts, "TALLER_COTAS")
    # Cotas de posición desde el borde superior izquierdo (el borde de referencia del taller).
    xs = sorted({hole["x"] for hole in holes})
    ys = sorted({hole["y"] for hole in holes})
    for k, x in enumerate(xs):
        dim = msp.add_linear_dim(base=(0, h + off * (1 + k)), p1=(0, h), p2=(x, Y(ys[0])), angle=0,
                                 dxfattribs={"layer": "TALLER_COTAS"}, override={**DIM, "dimtxt": t, "dimasz": t * 0.8, "dimexe": 2 * scale, "dimexo": 2 * scale})
        dim.render()
    for k, y in enumerate(ys):
        dim = msp.add_linear_dim(base=(-off * (1 + k), 0), p1=(0, h), p2=(xs[0], Y(y)), angle=90,
                                 dxfattribs={"layer": "TALLER_COTAS"}, override={**DIM, "dimtxt": t, "dimasz": t * 0.8, "dimexe": 2 * scale, "dimexo": 2 * scale})
        dim.render()
    for x0, x1 in ((0, w),):
        msp.add_linear_dim(base=(0, -off), p1=(x0, 0), p2=(x1, 0), dxfattribs={"layer": "TALLER_COTAS"},
                           override={**DIM, "dimtxt": t, "dimasz": t * 0.8}).render()
    msp.add_linear_dim(base=(w + off, 0), p1=(w, 0), p2=(w, h), angle=90, dxfattribs={"layer": "TALLER_COTAS"},
                       override={**DIM, "dimtxt": t, "dimasz": t * 0.8}).render()
    # Tabla de perforaciones y referencias, debajo de la puerta.
    y = -off * 2.5
    text(RULES["doorTitle"], w / 2, y, t * 1.3, bold=True)
    y -= t * 3
    def _fmt(v):
        return f"{v:g}".replace(".", ",")

    rows = [("N°", "X (mm)", "Y (mm)", "Ø (mm)", "Uso")] + [(str(hh["n"]), _fmt(hh["x"]), _fmt(hh["y"]), _fmt(hh["d"]), hh["uso"]) for hh in holes]
    cols = [c * scale for c in (0, 12, 34, 56, 78)]
    for idx_r, row in enumerate(rows or []):
        for cx, value in zip(cols, row):
            text(value, cx, y, ts, "TALLER", TextEntityAlignment.LEFT, bold=(idx_r == 0))
        y -= ts * 1.8
    if not holes:
        text("Sin perforaciones: tablero sin testigos de tensión en la puerta.", 0, y, ts, "TALLER", TextEntityAlignment.LEFT)
        y -= ts * 1.8
    for note in ("Cotas al centro de cada agujero, desde el borde superior izquierdo de la puerta (vista desde afuera).",
                 "Trazo fino: cerradura y bisagras de fábrica (no se perforan).",
                 "Línea punteada: placa grabada con el nombre y cartel de riesgo eléctrico (pegados, sin perforar)."):
        text(note, 0, y, ts, "TALLER", TextEntityAlignment.LEFT)
        y -= ts * 1.8

    # Vista lateral: profundidad exterior y útil, y el equipo más profundo apoyado en la placa.
    dc = depth_check(project, catalog)
    ox = w + RULES["gapMm"] * scale + off * 2
    ext, use = dc["external"], dc["useful"]
    msp.add_lwpolyline([(ox, 0), (ox + ext, 0), (ox + ext, h), (ox, h)], close=True, dxfattribs={"layer": "TALLER"})
    msp.add_lwpolyline([(ox + ext - use, 0), (ox + ext, 0), (ox + ext, h), (ox + ext - use, h)], close=True,
                       dxfattribs={"layer": "TALLER_FABRICA", "linetype": "DASHED"})
    msp.add_linear_dim(base=(ox, h + off), p1=(ox, h), p2=(ox + ext, h), dxfattribs={"layer": "TALLER_COTAS"},
                       override={**DIM, "dimtxt": t, "dimasz": t * 0.8}).render()
    msp.add_linear_dim(base=(ox, -off), p1=(ox + ext - use, 0), p2=(ox + ext, 0), dxfattribs={"layer": "TALLER_COTAS"},
                       override={**DIM, "dimtxt": t, "dimasz": t * 0.8}).render()
    d = dc["deepest"]
    if d:  # equipo apoyado en el fondo útil (lado derecho = placa de montaje), sobresale hacia la puerta (izquierda)
        dx = ox + ext - d["total"]
        msp.add_lwpolyline([(dx, h * 0.4), (ox + ext, h * 0.4), (ox + ext, h * 0.6), (dx, h * 0.6)], close=True, dxfattribs={"layer": "TALLER"})
        msp.add_linear_dim(base=(ox, h * 0.6 + off), p1=(dx, h * 0.6), p2=(ox + ext, h * 0.6), dxfattribs={"layer": "TALLER_COTAS"},
                           override={**DIM, "dimtxt": t, "dimasz": t * 0.8}).render()
    y = -off * 2.5
    text(RULES["sideTitle"], ox + ext / 2, y, t * 1.3, bold=True)
    lines = [f"Profundidad exterior: {_fmt(ext)} mm · útil (catálogo ABB): {_fmt(use)} mm"]
    if d:
        lines.append(f"Equipo más profundo: {d['tag']} {d['model']} · {_fmt(d['depth'])} mm" + (f" + riel DIN {_fmt(RULES['dinRailDepthMm'])} mm ({RULES['dinRailSource']})" if d["rail"] else ""))
        lines.append(("ENTRA" if dc["margin"] >= 0 else "NO ENTRA") + f": margen {_fmt(dc['margin'])} mm hasta el fondo útil (sin contar la separación de la placa, que el catálogo no da)")
    from validacion import rail_reserve
    rr = rail_reserve(project, catalog, json.loads((ROOT / "datos" / "reglas_validacion.json").read_text(encoding="utf-8")))
    if rr["freePercent"] is not None:
        lines.append(f"Reserva libre en los rieles DIN: {_fmt(rr['freePercent'])} % de {_fmt(rr['railMm'])} mm" + (f" (pedida {_fmt(rr['requested'])} %)" if rr["requested"] else ""))
    if dc["unknown"]:
        lines.append("Sin profundidad en el catálogo: " + ", ".join(dc["unknown"]) + " (confirmar con la ficha ABB)")
    y -= t * 3
    for line in lines:
        text(line, ox, y, ts, "TALLER", TextEntityAlignment.LEFT)
        y -= ts * 1.8
    return doc
