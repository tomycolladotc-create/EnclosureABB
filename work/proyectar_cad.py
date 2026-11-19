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
]


def from_step_or_iges(filename, kind, normal, xdir):
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
    return paths


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
    return result, [round(width, 2), round(height, 2)]


def main():
    fronts = json.loads(DEST.read_text(encoding="utf-8")) if DEST.exists() else {"schemaVersion": 1, "coordinateSystem": "normalized 0..1, origin lower left", "items": {}}
    for shell, relative, kind, normal, xdir, *opts in SOURCES:
        if len(sys.argv) > 1 and shell not in sys.argv[1:]:
            continue
        filename = ROOT / relative
        print(f"Proyectando {shell}: {filename.name}", flush=True)
        paths = from_dxf(filename) if kind == "dxf" else from_step_or_iges(filename, kind, normal, xdir)
        if "rot90ccw" in opts:
            paths = [[[-y, x] for x, y in p] for p in paths]
        normalized, source_size = normalize(paths)
        fronts["items"][shell] = {
            "source": relative, "method": "ABB DXF 2D" if kind == "dxf" else f"proyección frontal HLR de ABB {kind.upper()} 3D",
            "sourceProjectionExtent": source_size, "paths": normalized,
        }
        print(f"  {len(normalized)} trayectorias; extensión de origen {source_size}", flush=True)
        DEST.write_text(json.dumps(fronts, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
