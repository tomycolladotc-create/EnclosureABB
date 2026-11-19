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

import json


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
    return any(point_in_silhouette(x + dx * tol, y + dy * tol, silhouette)
               for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)))


CAD_REGION_MM_PER_PX = 0.25   # misma resolución que la silueta (work/proyectar_cad.py)
CAD_REGION_MIN_AREA_MM2 = 4.0  # zonas más chicas son letras o trazos, no superficies para pintar


def cad_regions(front):
    """Zonas cerradas por las líneas del CAD (cada superficie que se ve en el frente), en coordenadas normalizadas
    y hacia arriba: [{"ring", "bbox": (x, y, w, h), "area"}]. Se calculan de las mismas líneas que se dibujan, así un
    color puesto con una semilla (parts → {"seed": [x, y]}) llena exactamente la superficie del equipo real."""
    return _cad_regions(_key(front), front)


_KEYS: dict = {}


def _key(front):
    """Clave por contenido (no por objeto: un frente distinto nunca reusa el resultado de otro). Se guarda una referencia
    al frente para que su id no se reutilice mientras la clave está en uso."""
    import hashlib
    hit = _KEYS.get(id(front))
    if hit is None or hit[0] is not front:
        hit = (front, hashlib.sha1(json.dumps([front.get("sourceProjectionExtent"), front.get("paths")]).encode()).hexdigest())
        _KEYS[id(front)] = hit
    return hit[1]


_REGION_CACHE: dict = {}


def _cad_regions(key, front):
    if key in _REGION_CACHE:
        return _REGION_CACHE[key]
    import cv2
    import numpy as np
    cw, ch = front.get("sourceProjectionExtent") or (100.0, 100.0)
    W, H = max(8, round(cw / CAD_REGION_MM_PER_PX)), max(8, round(ch / CAD_REGION_MM_PER_PX))
    pad = 2
    im = np.zeros((H + 2 * pad, W + 2 * pad), np.uint8)
    for path in front.get("paths") or []:
        pts = np.array([[pad + x * W, pad + (1 - y) * H] for x, y in path], np.int32)
        cv2.polylines(im, [pts], False, 255, 1)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(255 - im, connectivity=4)
    body = np.zeros_like(im)  # silueta del equipo (con sus agujeros): una zona cerrada fuera de ella es aire, no superficie
    for ring_set, value in ((front.get("silhouette") or [], 255), (front.get("silhouetteHoles") or [], 0)):
        for ring in ring_set:
            cv2.fillPoly(body, [np.array([[pad + x * W, pad + (1 - y) * H] for x, y in ring], np.int32)], value)
    min_px = CAD_REGION_MIN_AREA_MM2 / CAD_REGION_MM_PER_PX ** 2
    out = []
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if a < min_px or x == 0 or y == 0 or x + w >= W + 2 * pad or y + h >= H + 2 * pad:
            continue  # muy chica, o toca el borde: no la cierran las líneas del CAD (es aire alrededor del equipo)
        mask = (lab == i).astype(np.uint8)
        if front.get("silhouette") and (body[mask > 0] > 0).mean() < 0.9:
            continue  # cerrada por líneas pero fuera del cuerpo (p. ej. entre las patas de un soporte)
        mask = cv2.dilate(mask, np.ones((3, 3), np.uint8))  # recupera el ancho de la línea que la rodea
        if front.get("silhouette"):
            mask &= (body > 0).astype(np.uint8)  # y nunca sale del cuerpo (mismo criterio que el recorte de los rectángulos)
        cs, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        to_ring = lambda c: [(round((px - pad) / W, 5), round(1 - (py - pad) / H, 5))
                             for px, py in cv2.approxPolyDP(c, 0.2 / CAD_REGION_MM_PER_PX, True)[:, 0, :]]
        outer = max((k for k in range(len(cs)) if hier[0][k][3] < 0), key=lambda k: cv2.contourArea(cs[k]))
        # agujeros: las otras superficies que esta encierra (se pintan aparte o quedan del color del cuerpo)
        holes = [to_ring(cs[k]) for k in range(len(cs)) if hier[0][k][3] == outer and cv2.contourArea(cs[k]) >= min_px]
        ring = to_ring(cs[outer])
        if len(ring) >= 3:
            out.append({"ring": ring, "rings": [ring] + [h for h in holes if len(h) >= 3],
                        "bbox": ((x - pad) / W, 1 - (y - pad + h) / H, w / W, h / H), "area": a / (W * H), "label": i})
    _REGION_CACHE[key] = out
    _REGION_CACHE[key + ":lab"] = (lab, W, H, pad)
    return out


def region_at(front, x, y):
    """La zona cerrada del CAD a la que pertenece el punto (x, y) (la superficie que se ve ahí, no las que encierra), o None."""
    zones = cad_regions(front)
    lab, W, H, pad = _REGION_CACHE[_key(front) + ":lab"]
    by_label = {r["label"]: r for r in zones}
    px, py = round(pad + x * W), round(pad + (1 - y) * H)
    for r in range(0, 3):  # si cae justo sobre una línea, la zona vecina
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if 0 <= py + dy < lab.shape[0] and 0 <= px + dx < lab.shape[1] and lab[py + dy, px + dx] in by_label:
                    return by_label[lab[py + dy, px + dx]]
    return None


def _iou(a, b):
    ax, ay, aw, ah = a[:4]
    bx, by, bw, bh = b[:4]
    i = max(0, min(ax + aw, bx + bw) - max(ax, bx)) * max(0, min(ay + ah, by + bh) - max(ay, by))
    return i / (aw * ah + bw * bh - i) if i else 0.0


SIMILAR_IOU = 0.5        # un rectángulo que se superpone así con una superficie del CAD la quiere representar
SIMILAR_SIZE_RATIO = 1.5  # o tiene casi el mismo tamaño (cada lado dentro de ×1,5) ...
SIMILAR_OFFSET = 0.5      # ... y su centro corrido menos de medio lado


def similar_region(front, rect):
    """La superficie del CAD que un rectángulo puesto a mano intenta representar (o None). Regla única que usan la
    conversión a semillas y el test que impide volver a poner rectángulos a ojo sobre superficies que el CAD ya dibuja."""
    x, y, w, h = rect[:4]
    best, score = None, 0.0
    for r in cad_regions(front):
        bx, by, bw, bh = r["bbox"]
        v = _iou(rect, r["bbox"])
        same_size = 1 / SIMILAR_SIZE_RATIO <= bw / w <= SIMILAR_SIZE_RATIO and 1 / SIMILAR_SIZE_RATIO <= bh / h <= SIMILAR_SIZE_RATIO
        near = abs(bx + bw / 2 - x - w / 2) <= SIMILAR_OFFSET * w and abs(by + bh / 2 - y - h / 2) <= SIMILAR_OFFSET * h
        if (v >= SIMILAR_IOU or (same_size and near)) and v > score:
            best, score = r, v
    return best


NEAR_MISS_MM = (0.6, 3.0)  # un borde a esta distancia de una línea paralela del CAD está "casi" alineado: fue puesto a ojo
NEAR_MISS_SHARE = 0.6      # ... si la línea acompaña al menos el 60 % del borde


def near_miss_edges(front, rect):
    """Bordes de un rectángulo libre que corren paralelos a una línea del CAD a 0,6–3 mm sin coincidir con ella
    (se ve corrido). Devuelve [(borde, corrimiento normalizado)], borde ∈ {"x0", "x1", "y0", "y1"}."""
    import numpy as np
    cad_regions(front)
    lab, W, H, pad = _REGION_CACHE[_key(front) + ":lab"]
    line = lab == 0
    cw, ch = front.get("sourceProjectionExtent") or (100.0, 100.0)
    x, y, w, h = rect[:4]
    lo, hi = (round(v / CAD_REGION_MM_PER_PX) for v in NEAR_MISS_MM)
    out = []
    def scan(edge, fixed_px, span_px, horizontal):
        a, b = sorted(span_px)
        a, b = max(a, 0), min(b, (line.shape[1] if horizontal else line.shape[0]) - 1)
        if b - a < 8:
            return
        def share(off):
            k = fixed_px + off
            if not 0 <= k < (line.shape[0] if horizontal else line.shape[1]):
                return 0.0
            seg = line[k, a:b] if horizontal else line[a:b, k]
            return float(seg.mean())
        if max(share(o) for o in range(-1, 2)) >= NEAR_MISS_SHARE:
            return  # ya coincide con una línea
        best = max((o for o in list(range(-hi, -lo + 1)) + list(range(lo, hi + 1))), key=share)
        if share(best) >= NEAR_MISS_SHARE:
            out.append((edge, best / (H if horizontal else W) * (-1 if horizontal else 1)))
    X0, X1 = round(pad + x * W), round(pad + (x + w) * W)
    Y0, Y1 = round(pad + (1 - y) * H), round(pad + (1 - y - h) * H)  # filas de la imagen (y hacia abajo)
    scan("y0", Y0, (X0, X1), True)
    scan("y1", Y1, (X0, X1), True)
    scan("x0", X0, (Y1, Y0), False)
    scan("x1", X1, (Y1, Y0), False)
    return out


def text_box(front, search, pad):
    """Recuadro de las letras que el CAD dibuja dentro de `search` (x, y, w, h normalizado), agrandado `pad`
    (normalizado en x e y). Para la etiqueta de color detrás de un logo: queda centrada en las letras del CAD."""
    cad_regions(front)
    lab, W, H, padpx = _REGION_CACHE[_key(front) + ":lab"]
    x, y, w, h = search
    c0, c1 = round(padpx + x * W), round(padpx + (x + w) * W)
    r0, r1 = round(padpx + (1 - y - h) * H), round(padpx + (1 - y) * H)
    import cv2
    import numpy as np
    window = (lab[r0:r1, c0:c1] == 0).astype(np.uint8)  # píxeles de línea
    n, comp, st, _ = cv2.connectedComponentsWithStats(window, connectivity=8)
    hh, ww = window.shape
    # sólo los trazos enteros dentro de la ventana (las letras); las líneas largas del cuerpo la cruzan y se descartan
    keep = [i for i in range(1, n) if st[i][0] > 0 and st[i][1] > 0 and st[i][0] + st[i][2] < ww and st[i][1] + st[i][3] < hh]
    ys, xs = np.nonzero(np.isin(comp, keep)) if keep else ((), ())
    if not len(xs):
        raise ValueError(f"no hay letras del CAD enteras dentro de {search}")
    px0, px1, py0, py1 = c0 + xs.min(), c0 + xs.max() + 1, r0 + ys.min(), r0 + ys.max() + 1
    return ((px0 - padpx) / W - pad[0], 1 - (py1 - padpx) / H - pad[1],
            (px1 - px0) / W + 2 * pad[0], (py1 - py0) / H + 2 * pad[1])


def part_rect(front, part):
    """Recuadro (x, y, w, h normalizado) que ocupa un detalle, sea rectángulo, semilla o etiqueta detrás de letras."""
    if isinstance(part, dict) and "seed" in part:
        zone = region_at(front, *part["seed"])
        if zone is None:
            raise ValueError(f"la semilla {part['seed']} no cae dentro de ninguna superficie cerrada del CAD")
        return zone["bbox"]
    if isinstance(part, dict) and "behindCadText" in part:
        cw, ch = front.get("sourceProjectionExtent") or (1.0, 1.0)
        pad = part.get("padMm", 0.0)
        return text_box(front, part["behindCadText"], (pad / cw, pad / ch))
    return tuple(part[:4])


def regions(front, palette):
    """Zonas de color del frente, en coordenadas normalizadas: [(anillos, color, tipo)], en orden de pintado.
    tipo: "fondo" (la silueta), "agujero" (los agujeros del CAD, un tono más oscuro), "superficie" (zona cerrada del CAD
    elegida con una semilla, forma exacta con sus agujeros) y "detalle" (rectángulo recortado a la silueta)."""
    outers = front.get("silhouette") or [[(0, 0), (1, 0), (1, 1), (0, 1)]]  # sin silueta: el rectángulo del equipo
    holes = front.get("silhouetteHoles") or []
    base = (palette or {}).get("base")
    out = []
    if base and base != "none":
        out.append((outers, base, "fondo"))
        if holes:  # agujeros del CAD (bornes, ojales, eje): se ve el interior, un tono más oscuro que el cuerpo
            out.append((holes, (palette or {}).get("holeColor") or shade(base, 0.55), "agujero"))
    for part in (palette or {}).get("parts", []):
        if isinstance(part, dict) and "seed" in part:  # semilla: la superficie del CAD que la contiene (calculada)
            part_rect(front, part)  # valida la semilla
            out.append((region_at(front, *part["seed"])["rings"], part["color"], "superficie"))  # con sus agujeros
            continue
        if isinstance(part, dict):  # etiqueta detrás de las letras del CAD: recuadro calculado de las letras
            (x, y, w, h), color = part_rect(front, part), part["color"]
        else:  # rectángulo libre: sólo para colores que el CAD no encierra con líneas (lo controla el test)
            x, y, w, h, color = part[:5]
        pieces = clip_rect(outers + holes, x, y, x + w, y + h)  # los detalles tampoco tapan los agujeros
        if pieces:
            out.append((pieces, color, "detalle"))
    return out


def resolve(fronts, appearances, catalog):
    """Datos listos para dibujar, iguales para la pantalla (app.py → /api/fronts, /api/appearances) y el DXF:
    - fronts.items[id].paint: zonas de color calculadas por `regions` (la pantalla no repite la regla);
    - marking.items[i] con "anchor": {"part": n}: el texto se centra en el detalle n (x, y en mm del equipo),
      así un logo nunca queda corrido de su etiqueta aunque cambie la medida o el CAD.
    No modifica los originales."""
    import copy
    shells = {s["id"]: s for s in catalog.get("deviceShells", [])}
    fr, ap = copy.deepcopy(fronts), copy.deepcopy(appearances)
    for sid, front in fronts.get("items", {}).items():
        pal = appearances.get("items", {}).get(sid)
        if not pal:
            continue
        fr["items"][sid]["paint"] = [{"rings": rings, "color": color, "kind": kind} for rings, color, kind in regions(front, pal)]
        spec = shells.get(sid)
        items = (ap["items"][sid].get("marking") or {}).get("items", [])
        if spec and any("anchor" in it for it in items):
            W = (spec.get("poleModule") or {}).get("width") or spec["width"]
            dx, dy, dw, dh = fit(front.get("sourceProjectionExtent"), W, spec["height"])
            for it in items:
                if "anchor" in it:
                    bx, by, bw, bh = part_rect(front, pal["parts"][it["anchor"]["part"]])
                    it["x"], it["y"], it["align"] = round(dx + (bx + bw / 2) * dw, 2), round(dy + (by + bh / 2) * dh, 2), "center"
    return fr, ap
