"""Genera la lámina 2D y el DXF desde los mismos frentes CAD del editor."""

from html import escape
import json
from pathlib import Path

import cairosvg

from cad_export import build_dxf

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "salida"


def load(name):
    return json.loads((ROOT / "datos" / name).read_text(encoding="utf-8"))


def svg_document(project, catalog, fronts, appearances):
    cabinet = project["enclosure"]
    body, total = cabinet["externalBody"], cabinet["overallHeightWithPlinth"]
    plinth = cabinet["plinthHeight"]
    fx, fy = (cabinet["functionalAreaOffset"][key] for key in ("x", "y"))
    left, top = 95, 125
    specs = {s["id"]: s for s in catalog["deviceShells"]}
    ids = {key: f"front-{i}" for i, key in enumerate(fronts["items"], 1)}
    out = ['<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="420mm" height="500mm" viewBox="0 0 2050 2450">',
           '<rect width="2050" height="2450" fill="#f8fafc"/>',
           '<text x="95" y="66" font-family="Arial" font-size="35" font-weight="bold" fill="#15243a">TS4 - VISTA 2D FRONTAL</text>',
           '<text x="95" y="100" font-family="Arial" font-size="20" fill="#4b6179">ABB System pro E power 185 · esquema de montaje para revisión</text>', '<defs>']
    for shell, front in fronts["items"].items():
        paint = appearances["items"].get(shell)
        out.append(f'<symbol id="{ids[shell]}" viewBox="0 0 1 1">')
        if paint:
            out.append('<g transform="translate(0 1) scale(1 -1)">')
            out.append(f'<rect width="1" height="1" fill="{paint["base"]}"/>')
            for x, y, w, h, tint in paint["parts"]:
                out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{tint}"/>')
            out.append('</g>')
            if "logo" in paint:
                lx, ly, word = paint["logo"]
                out.append(f'<text x="{lx}" y="{1-ly}" fill="white" font-family="Arial" font-size="0.035" font-weight="bold">{escape(word)}</text>')
        out.append(f'<g transform="translate(0 1) scale(1 -1)" fill="none" stroke="{paint["lineColor"] if paint else "#273746"}" stroke-width="0.0035" stroke-linecap="round" stroke-linejoin="round">')
        for path in front["paths"]:
            out.append('<path d="M' + 'L'.join(' '.join(map(str, point)) for point in path) + '"/>')
        out.append('</g></symbol>')
    out.append('</defs>')
    out.append(f'<rect x="{left}" y="{top}" width="{body["width"]}" height="{total}" fill="white" stroke="#1c3045" stroke-width="5"/>')
    out.append(f'<rect x="{left}" y="{top+body["height"]}" width="{body["width"]}" height="{plinth}" fill="#dfe6ec" stroke="#61758b" stroke-width="2"/>')
    area = cabinet["functional"]
    out.append(f'<rect x="{left+fx}" y="{top+total-fy-area["height"]}" width="{area["width"]}" height="{area["height"]}" fill="none" stroke="#8799ab" stroke-dasharray="8 5" stroke-width="2"/>')
    for rail in cabinet.get("mountingLayout", {}).get("dinRails", []):
        x, y = left+fx+rail["x"], top+total-fy-rail["y"]-rail["height"]/2
        out.append(f'<rect x="{x}" y="{y}" width="{rail["length"]}" height="{rail["height"]}" fill="#c4d0dc" stroke="#556a80" stroke-width="2"/>')
    for device in project["devices"]:
        spec = specs.get(device.get("shell"), {})
        w, h = spec.get("width", device["w"]), spec.get("height", device["h"])
        x, y = left+fx+device["x"], top+total-fy-device["y"]-h
        source = ids.get(device.get("shell"))
        if source:
            out.append(f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="0 0 1 1" preserveAspectRatio="none"><use xlink:href="#{source}"/></svg>')
        else:
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#fff1d8" stroke="#b27a20" stroke-width="2" stroke-dasharray="5 3"/>')
            out.append(f'<text x="{x+w/2}" y="{y+h/2}" text-anchor="middle" font-family="Arial" font-size="8" fill="#7c5217">SIN CAD</text>')
        out.append(f'<text x="{x+w/2}" y="{y-8}" text-anchor="middle" font-family="Arial" font-size="15" font-weight="bold" fill="#182c40">{escape(device["tag"])}</text>')
    panel_x = 1270
    out.append(f'<rect x="{panel_x}" y="125" width="700" height="{total}" fill="white" stroke="#cdd8e2" stroke-width="2"/>')
    out.append(f'<text x="{panel_x+30}" y="180" font-family="Arial" font-size="24" font-weight="bold" fill="#15243a">EQUIPOS</text>')
    for i, device in enumerate(project["devices"]):
        y = 225+i*83
        out.append(f'<text x="{panel_x+30}" y="{y}" font-family="Arial" font-size="18" font-weight="bold" fill="#18314e">{escape(device["tag"])}</text>')
        out.append(f'<text x="{panel_x+130}" y="{y}" font-family="Arial" font-size="16" fill="#344d64">{escape(device["model"][:50])}</text>')
        if device.get("shell") not in ids:
            out.append(f'<text x="{panel_x+130}" y="{y+22}" font-family="Arial" font-size="13" fill="#a26616">Frente CAD pendiente</text>')
    notes = ['GEOMETRÍA Y ESTADO', 'Frentes CAD ABB: XT1, XT2, S800, S201M Na', '1P+N y familia OT400E04.', 'Colores vectoriales según fotos ABB.', 'QF89 S251 Na: sin frente CAD localizado.', 'Inscripciones nominales: revisar en equipo real.', 'Riel ABB PDRS0600: posición propuesta.', 'Gabinete y riel: montaje aún no validado', 'por ABB Argentina para fabricar.', 'DXF: bloques ABB editables, unidades en mm.']
    for i, line in enumerate(notes):
        out.append(f'<text x="{panel_x+30}" y="{1470+i*37}" font-family="Arial" font-size="17" fill="#344d64">{escape(line)}</text>')
    out.append(f'<text x="{panel_x+30}" y="{top+total-55}" font-family="Arial" font-size="21" font-weight="bold" fill="#9a5422">PRELIMINAR · NO FABRICAR</text></svg>')
    return ''.join(out)


def main():
    OUT.mkdir(exist_ok=True)
    project, catalog, fronts, appearances = (load(name) for name in ('ts4_topografia.json', 'catalogo_abb.json', 'frentes_cad.json', 'apariencias_abb.json'))
    svg = svg_document(project, catalog, fronts, appearances)
    (OUT / 'TS4_vista_2D.svg').write_text(svg, encoding='utf-8')
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(OUT/'TS4_vista_2D.png'), output_width=2050, output_height=2450)
    cairosvg.svg2pdf(bytestring=svg.encode(), write_to=str(OUT/'TS4_vista_2D.pdf'))
    (OUT/'TS4_vista_2D.dxf').write_bytes(build_dxf(project, catalog, fronts, appearances))
    print('TS4: SVG, PNG, PDF y DXF generados en', OUT)


if __name__ == '__main__':
    main()
