"""Extrae frentes 2D reutilizables de CAD ABB oficiales.

Se ejecuta al incorporar un CAD nuevo; la aplicación usa el JSON resultante y no
necesita cargar STEP ni DXF durante la edición. Las coordenadas de cada trayectoria
se normalizan al contorno frontal del equipo; el catálogo fija las medidas reales.
"""

import json
import sys
from pathlib import Path

import ezdxf
from ezdxf import path as dxf_path
from ezdxf import bbox as dxf_bbox
from OCP.STEPControl import STEPControl_Reader
from OCP.IGESControl import IGESControl_Reader
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.HLRBRep import HLRBRep_PolyAlgo, HLRBRep_PolyHLRToShape
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_FACE
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Pnt2d
import numpy as np
import cv2

SILHOUETTE_RES_MM = 0.25   # resolución del raster de la silueta (mm por píxel)
SILHOUETTE_TOL_MM = 0.2    # tolerancia al simplificar el contorno (mm)

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "datos" / "frentes_cad.json"

SOURCES = [
    ("abb.tmax.xt1.4p.fixed.front", "cad/abb/xt1/1SDH001295R0080_XT1_4P_FIXED_F.stp", "step", (0, 1, 0), (-1, 0, 0)),
    ("abb.tmax.xt2.4p.fixed.front", "cad/abb/xt2/1SDH002230A1002_XT2_4P_FIXED_F.stp", "step", (0, 1, 0), (-1, 0, 0)),
    ("abb.s804n.4p.front", "cad/abb/s800/2D_S800_4pole_drawing.DXF", "dxf", None, None),
    ("abb.s200m.1p.front", "cad/abb/s201m/S200M_1P_3D_9AKK106930A4834.stp", "step", (0, 1, 0), (0, 0, 1)),
    ("abb.s200m.1pn.front", "cad/abb/s201m_na/S200M_1PN_2P_3D_9AKK106930A4835.stp", "step", (0, 1, 0), (0, 0, 1)),
    ("abb.ot400e04.4p.front", "cad/abb/ot400/OT315_400E04.igs", "iges", (0, 0, 1), (0, -1, 0)),
    # 2026-11-18: CAD públicos de ABB Library (ver datos/fuentes_descargadas.json). Vista elegida comparando las 6 proyecciones.
    ("abb.f204.4p.front", "cad/abb/f200/F204_3D_9AKK106354A0756_B.stp", "step", (0, 0, 1), (1, 0, 0)),
    ("abb.f202.2p.front", "cad/abb/f200/F202_3D_9AKK106354A0757_A.stp", "step", (0, 0, 1), (1, 0, 0)),
    ("abb.sn201.1pn.front", "cad/abb/sn201/SN201_3D_9AKK106930A4363.stp", "step", (0, 1, 0), (-1, 0, 0)),
    ("abb.ot100_125f4.4p.front", "cad/abb/ot100_125/OT100-125F4N2.stp", "step", (0, 0, 1), (1, 0, 0)),
    ("abb.ot100_125f3.3p.front", "cad/abb/ot100_125/OT100-125F3.stp", "step", (0, 0, 1), (1, 0, 0)),
    # OT160...250E: en el CAD el mecanismo queda arriba; montado va a la IZQUIERDA (tipo 03/04 = mecanismo en el extremo izquierdo), se rota 90°.
    ("abb.ot160_250e03.3p.front", "cad/abb/ot160_250/OT200-250E03.stp", "step", (0, 1, 0), (-1, 0, 0), "rot90ccw"),
    ("abb.ot160_250e04.4p.front", "cad/abb/ot160_250/OT200-250E04.stp", "step", (0, 0, 1), (1, 0, 0), "rot90ccw"),
    # 2026-11-19: CAD del TGBT / tableros del plano GENERAL (ver datos/fuentes_descargadas.json).
    ("abb.emax.e22.4p.fixed.front", "cad/abb/e2_2/1SDH001252R0123_1PA_001_01_E2.2_IV_F.stp", "step", (0, 1, 0), (-1, 0, 0)),
    ("abb.tmax.xt3.4p.fixed.front", "cad/abb/xt3/1SDH001295R0483_XT3 4p FIXED F.stp", "step", (0, 1, 0), (-1, 0, 0)),
    ("abb.tmax.xt1.3p.fixed.front", "cad/abb/xt1_3p/1SDH001295R0008_XT1 3p FIXED F.stp", "step", (0, 1, 0), (-1, 0, 0)),
    ("abb.tmax.t4.4p.fixed.front", "cad/abb/t4/x/T4 4 poles Fixed.igs", "iges", (0, 1, 0), (-1, 0, 0)),
    ("abb.tmax.t2.3p.fixed.front", "cad/abb/t2/x/T2_fixed_3poles_F.igs", "iges", (0, 1, 0), (-1, 0, 0)),
    ("abb.s803.3p.front", "cad/abb/s800/x/2D S800 3pole drawing.DXF", "dxf", None, None),
    ("abb.ot63_80f3.3p.front", "cad/abb/ot63_80/OT63-80F3.igs", "iges", (0, 1, 0), (-1, 0, 0), "rot90ccw"),
    ("abb.ot63_80f4.4p.front", "cad/abb/ot63_80/ot63-80f4n2.stp", "step", (0, 1, 0), (-1, 0, 0), "rot90ccw"),
    # 2026-11-20: S290 sin CAD en ABB Library; se usa el dibujo vectorial de medidas del catálogo ABB NN31/05_04 (pág. 6/4,
    # «Celkové rozměry S 280, S 290»), vista frontal 3P. Escala por la cota de ABB: 78,75 mm de ancho.
    ("abb.s290.3p.front", "cad/abb/s290/ABB_NN31_05_04_p6-4_rozmery_S280_S290.pdf", "pdf", None, None,
     {"page": 0, "rect": (261.5, 343.0, 329.5, 424.5), "widthMm": 78.75}),
]


def from_step_or_iges(filename, kind, normal, xdir):
    """Devuelve (trayectorias visibles HLR, triángulos proyectados de la malla). Los triángulos dan la silueta exacta del equipo."""
    reader = STEPControl_Reader() if kind == "step" else IGESControl_Reader()
    if reader.ReadFile(str(filename)) != 1:
        raise ValueError(f"No se pudo leer {filename}")
    reader.TransferRoots()
    shape = reader.OneShape()
    BRepMesh_IncrementalMesh(shape, 0.35)
    hlr = HLRBRep_PolyAlgo()
    hlr.Load(shape)
    hlr.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*normal), gp_Dir(*xdir))))
    hlr.Update()
    drawing = HLRBRep_PolyHLRToShape()
    drawing.Update(hlr)
    visible = drawing.VCompound()
    explorer = TopExp_Explorer(visible, TopAbs_EDGE)
    paths = []
    while explorer.More():
        edge = TopoDS.Edge_s(explorer.Current())
        curve = BRepAdaptor_Curve(edge)
        sample = GCPnts_QuasiUniformDeflection(curve, 0.3)
        if sample.IsDone() and sample.NbPoints() >= 2:
            pts = [[sample.Value(i).X(), sample.Value(i).Y()] for i in range(1, sample.NbPoints() + 1)]
            paths.append(pts)
        explorer.Next()
    projector = HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*normal), gp_Dir(*xdir)))
    triangles = []
    faces = TopExp_Explorer(shape, TopAbs_FACE)
    while faces.More():
        face = TopoDS.Face_s(faces.Current())
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face, loc)
        if tri is not None:
            trsf = loc.Transformation()
            pts = []
            for i in range(1, tri.NbNodes() + 1):
                p3, p2 = tri.Node(i).Transformed(trsf), gp_Pnt2d()
                projector.Project(p3, p2)
                pts.append((p2.X(), p2.Y()))
            for i in range(1, tri.NbTriangles() + 1):
                a, b, c = tri.Triangle(i).Get()
                triangles.append((pts[a - 1], pts[b - 1], pts[c - 1]))
        faces.Next()
    return paths, triangles


def silhouette(paths, triangles, bbox):
    """Silueta exacta del frente: une la proyección de todos los triángulos de la malla (o, en un DXF 2D, todo lo que
    encierra el dibujo) y la vectoriza. Devuelve polígonos normalizados al mismo contorno que las trayectorias.
    Así la pintura del equipo sale del CAD y no de rectángulos puestos a mano (lección 2026-11-19)."""
    xmin, ymin, width, height = bbox
    pad = 4
    W, H = int(width / SILHOUETTE_RES_MM) + 2 * pad, int(height / SILHOUETTE_RES_MM) + 2 * pad
    to_px = lambda x, y: (int(round((x - xmin) / SILHOUETTE_RES_MM)) + pad, int(round((ymin + height - y) / SILHOUETTE_RES_MM)) + pad)
    mask = np.zeros((H, W), np.uint8)
    if triangles:
        # Un triángulo por vez: fillPoly con una lista aplica par-impar y los solapes quedarían como agujeros falsos.
        for t in triangles:
            cv2.fillConvexPoly(mask, np.array([to_px(*v) for v in t], np.int32), 255)
    else:  # DXF 2D: se dibujan las líneas y se rellena todo lo que no se alcanza desde afuera
        for p in paths:
            cv2.polylines(mask, [np.array([to_px(*v) for v in p], np.int32)], False, 255, 2)
        outside = mask.copy()
        cv2.floodFill(outside, np.zeros((H + 2, W + 2), np.uint8), (0, 0), 128)
        mask = np.where(outside == 128, 0, 255).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    outer, holes = [], []
    for c, h in zip(contours, hierarchy[0] if hierarchy is not None else []):
        if cv2.contourArea(c) * SILHOUETTE_RES_MM ** 2 < 4:  # menos de 4 mm²: ruido de la malla
            continue
        c = cv2.approxPolyDP(c, SILHOUETTE_TOL_MM / SILHOUETTE_RES_MM, True)
        ring = [[round(((px - pad) * SILHOUETTE_RES_MM) / width, 5), round(1 - ((py - pad) * SILHOUETTE_RES_MM) / height, 5)] for px, py in c[:, 0, :]]
        (holes if h[3] >= 0 else outer).append(ring)  # con padre = agujero (p. ej. el ojal de una oreja de fijación)
    return outer, holes


def from_dxf(filename):
    drawing = ezdxf.readfile(filename)
    space = drawing.modelspace()
    paths = []
    for entity in space:
        try:
            points = [[p.x, p.y] for p in dxf_path.make_path(entity).flattening(distance=0.25)]
        except (TypeError, ValueError):
            continue
        if len(points) >= 2:
            paths.append(points)
    return paths


def from_pdf_vector(filename, page, rect, width_mm):
    """Trayectorias del dibujo vectorial de un catálogo ABB dentro de `rect` (pt): todo lo trazado y el contorno de los
    rellenos de color (franja roja, palanca); los rellenos blancos son letras o tapas y no son aristas. Escala uniforme
    tomada de la cota de ancho de ABB (pt → mm); y hacia arriba como en los CAD."""
    import pymupdf
    pg = pymupdf.open(filename)[page]
    box = pymupdf.Rect(*rect)
    drawings = [d for d in pg.get_drawings() if box.contains(d["rect"])]
    body = pymupdf.Rect(min(d["rect"].x0 for d in drawings), min(d["rect"].y0 for d in drawings),
                        max(d["rect"].x1 for d in drawings), max(d["rect"].y1 for d in drawings))
    k = width_mm / body.width
    to_mm = lambda q: [round((q.x - body.x0) * k, 4), round((body.y1 - q.y) * k, 4)]
    paths = []
    for d in drawings:
        white_fill = d.get("fill") and min(d["fill"]) > 0.95 and not d.get("color")
        if white_fill:
            continue
        if d.get("fill") and d["items"]:  # un relleno se cierra solo: se agrega el lado que cierra su contorno
            first, last = d["items"][0], d["items"][-1]
            if first[0] in ("l", "c") and last[0] in ("l", "c"):
                paths.append([to_mm(last[-1]), to_mm(first[1])])
        for it in d["items"]:
            if it[0] == "l":
                paths.append([to_mm(it[1]), to_mm(it[2])])
            elif it[0] == "re":
                r = it[1]
                paths.append([to_mm(r.tl), to_mm(r.tr), to_mm(r.br), to_mm(r.bl), to_mm(r.tl)])
            elif it[0] == "qu":
                q = it[1]
                paths.append([to_mm(q.ul), to_mm(q.ur), to_mm(q.lr), to_mm(q.ll), to_mm(q.ul)])
            elif it[0] == "c":
                p0, c1, c2, p3 = it[1:5]
                pts = []
                for i in range(9):
                    t = i / 8
                    pts.append(pymupdf.Point((1 - t) ** 3 * p0.x + 3 * (1 - t) ** 2 * t * c1.x + 3 * (1 - t) * t ** 2 * c2.x + t ** 3 * p3.x,
                                             (1 - t) ** 3 * p0.y + 3 * (1 - t) ** 2 * t * c1.y + 3 * (1 - t) * t ** 2 * c2.y + t ** 3 * p3.y))
                paths.append([to_mm(q) for q in pts])
    return paths


def normalize(paths):
    paths = [p for p in paths if len(p) >= 2]
    xmin = min(v[0] for p in paths for v in p)
    xmax = max(v[0] for p in paths for v in p)
    ymin = min(v[1] for p in paths for v in p)
    ymax = max(v[1] for p in paths for v in p)
    width, height = xmax - xmin, ymax - ymin
    if width <= 0 or height <= 0:
        raise ValueError("Geometría frontal sin extensión")
    result = []
    seen = set()
    for path in paths:
        points = [[round((x - xmin) / width, 5), round((y - ymin) / height, 5)] for x, y in path]
        compact = [points[0]]
        for point in points[1:]:
            if point != compact[-1]:
                compact.append(point)
        if len(compact) < 2:
            continue
        if max(abs(compact[-1][0] - compact[0][0]) * width, abs(compact[-1][1] - compact[0][1]) * height) < 0.15 and len(compact) == 2:
            continue
        key = tuple(map(tuple, compact))
        reverse = tuple(reversed(key))
        if key in seen or reverse in seen:
            continue
        seen.add(key)
        result.append(compact)
    return result, [round(width, 2), round(height, 2)], (xmin, ymin, width, height)


def main():
    fronts = json.loads(DEST.read_text(encoding="utf-8")) if DEST.exists() else {"schemaVersion": 1, "coordinateSystem": "normalized 0..1, origin lower left", "items": {}}
    for shell, relative, kind, normal, xdir, *opts in SOURCES:
        if len(sys.argv) > 1 and shell not in sys.argv[1:]:
            continue
        filename = ROOT / relative
        print(f"Proyectando {shell}: {filename.name}", flush=True)
        if kind == "pdf":
            o = opts[0]
            paths, triangles = from_pdf_vector(filename, o["page"], o["rect"], o["widthMm"]), []
        else:
            paths, triangles = (from_dxf(filename), []) if kind == "dxf" else from_step_or_iges(filename, kind, normal, xdir)
        if "rot90ccw" in [o for o in opts if isinstance(o, str)]:
            paths = [[[-y, x] for x, y in p] for p in paths]
            triangles = [tuple((-y, x) for x, y in t) for t in triangles]
        normalized, source_size, bbox = normalize(paths)
        fronts["items"][shell] = {
            "source": relative, "method": {"dxf": "ABB DXF 2D", "pdf": "dibujo vectorial de medidas del catálogo ABB"}.get(kind, f"proyección frontal HLR de ABB {kind.upper()} 3D"),
            "sourceProjectionExtent": source_size, "paths": normalized,
            **dict(zip(("silhouette", "silhouetteHoles"), silhouette(paths, triangles, bbox))),
            "silhouetteMethod": "unión de la malla proyectada" if triangles else "relleno de lo encerrado por el dibujo 2D",
        }
        print(f"  {len(normalized)} trayectorias; extensión de origen {source_size}", flush=True)
        DEST.write_text(json.dumps(fronts, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
