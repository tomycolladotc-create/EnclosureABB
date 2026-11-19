"""Pintura de los frentes de los equipos, calculada a partir del CAD.

- El color de fondo de cada equipo se aplica a su SILUETA EXACTA (datos/frentes_cad.json -> silhouette), que
  work/proyectar_cad.py calcula uniendo la proyección de la malla del STEP/IGES (o rellenando lo encerrado por
  el DXF 2D). Así ninguna parte del equipo queda sin pintar y nada se pinta fuera del equipo.
- Los detalles de color (apariencias_abb.json -> parts: rectángulos normalizados) se RECORTAN contra la silueta
  (intersección exacta por franjas, clip_rect).
  Un detalle mal ubicado puede quedar feo, pero nunca puede salirse del equipo.
- La misma regla la aplica la pantalla (web/index.html, con clipPath) y el DXF (cad_export.py, con este módulo).

Lección 2026-11-19 (docs/LECCIONES.md, 20 y 21): la pintura se ponía con rectángulos a mano y quedaban partes del
E2.2 y de los OT sin pintar.
"""
from __future__ import annotations


def clip_rect(rings, x0, y0, x1, y1):
    """Intersección EXACTA del rectángulo [x0,x1]×[y0,y1] con la región par-impar de `rings` (silueta con agujeros),
    como lista de trapecios (franjas horizontales). Sirve para cualquier silueta, cóncava o con agujeros: cada franja se
    corta en los vértices y donde un borde cruza x0/x1, así dentro de la franja todo es lineal y el recorte es exacto."""
    edges = []
    for ring in rings:
        for i in range(len(ring)):
            (xa, ya), (xb, yb) = ring[i - 1], ring[i]
            if ya != yb:
                edges.append((xa, ya, xb, yb) if ya < yb else (xb, yb, xa, ya))
    if not edges:
        return []
    def x_at(e, y):
        xa, ya, xb, yb = e
        return xa + (xb - xa) * (y - ya) / (yb - ya)
    levels = {y0, y1}
    for xa, ya, xb, yb in edges:
        for y in (ya, yb):
            if y0 < y < y1:
                levels.add(y)
        for xc in (x0, x1):
            if (xa - xc) * (xb - xc) < 0:
                y = ya + (yb - ya) * (xc - xa) / (xb - xa)
                if y0 < y < y1:
                    levels.add(y)
    levels = sorted(levels)
    out = []
    for lo, hi in zip(levels, levels[1:]):
        if hi - lo < 1e-9:
            continue
        mid = (lo + hi) / 2
        crossing = sorted((e for e in edges if e[1] <= lo + 1e-12 and e[3] >= hi - 1e-12), key=lambda e: x_at(e, mid))
        for left, right in zip(crossing[0::2], crossing[1::2]):
            clamp = lambda v: min(max(v, x0), x1)
            la, lb, ra, rb = clamp(x_at(left, lo)), clamp(x_at(left, hi)), clamp(x_at(right, lo)), clamp(x_at(right, hi))
            if ra - la > 1e-9 or rb - lb > 1e-9:
                out.append([(la, lo), (ra, lo), (rb, hi), (lb, hi)])
    return out


def fit(cad_extent, box_w, box_h):
    """Dónde se dibuja el frente CAD dentro del rectángulo del equipo SIN deformarlo: escala única (la que entra),
    centrado. Devuelve (dx, dy, ancho, alto). Si el catálogo y el CAD coinciden (control en los tests) llena el rectángulo."""
    cw, ch = cad_extent or (box_w, box_h)
    scale = min(box_w / cw, box_h / ch)
    w, h = cw * scale, ch * scale
    return (box_w - w) / 2, (box_h - h) / 2, w, h


def shade(color, factor):
    """Oscurece un color #rrggbb multiplicando cada canal (factor < 1)."""
    c = color.lstrip("#")
    return "#" + "".join(f"{max(0, min(255, round(int(c[i:i + 2], 16) * factor))):02x}" for i in (0, 2, 4))


def point_in_silhouette(x, y, silhouette, tol=0.0):
    """Regla par-impar sobre todos los anillos (los agujeros quedan afuera). `tol` (normalizado) acepta puntos sobre el borde."""
    inside = False
    for ring in silhouette:
        n = len(ring)
        for i in range(n):
            (xa, ya), (xb, yb) = ring[i - 1], ring[i]
            if (ya > y) != (yb > y) and x < xa + (xb - xa) * (y - ya) / ((yb - ya) or 1e-12):
                inside = not inside
    if inside or tol <= 0:
        return inside
    return any(point_in_silhouette(x + dx, y + dy, silhouette) for dx, dy in ((tol, 0), (-tol, 0), (0, tol), (0, -tol)))


def regions(front, palette):
    """Zonas de color del frente, en coordenadas normalizadas: [(anillos, color, tipo)], en orden de pintado.
    tipo: "fondo" (la silueta), "agujero" (los agujeros del CAD, un tono más oscuro) y "detalle" (recortado a la silueta)."""
    outers = front.get("silhouette") or [[(0, 0), (1, 0), (1, 1), (0, 1)]]  # sin silueta: el rectángulo del equipo
    holes = front.get("silhouetteHoles") or []
    base = (palette or {}).get("base")
    out = []
    if base and base != "none":
        out.append((outers, base, "fondo"))
        if holes:  # agujeros del CAD (bornes, ojales, eje): se ve el interior, un tono más oscuro que el cuerpo
            out.append((holes, (palette or {}).get("holeColor") or shade(base, 0.55), "agujero"))
    for x, y, w, h, color in (palette or {}).get("parts", []):
        pieces = clip_rect(outers + holes, x, y, x + w, y + h)  # los detalles tampoco tapan los agujeros
        if pieces:
            out.append((pieces, color, "detalle"))
    return out
