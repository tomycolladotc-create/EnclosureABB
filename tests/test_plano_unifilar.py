"""Plano de fabricación: unifilar del usuario + topográfico de la aplicación en su formato (plano_unifilar.py).
Se arma un formato mínimo con los mismos bloques que el del usuario (marco A2 y rótulo con atributos) y se controla
que la hoja quede en A1 1:1, con el unifilar intacto y las dos vistas a escala normalizada sin pisar nada."""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

import ezdxf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from plano_unifilar import RULES, compose  # noqa: E402
from test_regresion_general import BOARDS, result  # noqa: E402

L = lambda n: json.loads((ROOT / "datos" / n).read_text(encoding="utf-8"))


def formato_minimo(path, board):
    doc = ezdxf.new("R2018")
    fr = doc.blocks.new(RULES["frameBlock"])
    fr.add_lwpolyline([(0, 0), (594, 0), (594, 420), (0, 420)], close=True)
    tb = doc.blocks.new(RULES["titleBlock"])
    tb.add_lwpolyline([(-180, 0), (0, 0), (0, 84), (-180, 84)], close=True)
    for i, tag in enumerate(["TITLE_3OF3", "TITLE_2OF3", "DOCN°"]):
        tb.add_attdef(tag, (-170, 10 + 10 * i), dxfattribs={"height": 2.5})
    msp = doc.modelspace()
    msp.add_lwpolyline([(9700, 0), (10250, 0), (10250, 310), (9700, 310)], close=True, dxfattribs={"layer": "UNI-MARCO"})
    lay = doc.layouts.new(board)
    lay.add_viewport(center=(317.1, 251.8), size=(559, 315.85), view_center_point=(9976.5, 158), view_height=315.85)
    lay.add_blockref(RULES["frameBlock"], (12.6, -0.3))
    t = lay.add_blockref(RULES["titleBlock"], (596.6, 9.7))
    t.add_auto_attribs({"TITLE_3OF3": board, "TITLE_2OF3": "UNIFILAR", "DOCN°": "X-001"})
    doc.saveas(path)


class PlanoUnifilar(unittest.TestCase):
    def test_hoja_a1_con_unifilar_y_dos_vistas(self):
        pdf = next(b for b in BOARDS if b.stem == "TSB")
        project = result(pdf)["project"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "formato.dxf"
            formato_minimo(path, "TSB")
            text, report = compose(str(path), {"TSB": project}, L("catalogo_abb.json"), L("frentes_cad.json"), L("apariencias_abb.json"))
        doc = ezdxf.read(io.StringIO(text))
        lay = doc.layouts.get("TSB")
        d = lay.dxf_layout.dxf
        self.assertEqual((d.scale_numerator, d.scale_denominator), (1.0, 1.0))
        x0, y0, x1, y1 = d.plot_window_x1, d.plot_window_y1, d.plot_window_x2, d.plot_window_y2
        self.assertAlmostEqual(x1 - x0, 840.04, delta=1)
        self.assertAlmostEqual(y1 - y0, 593.97, delta=1)
        vps = [v for v in lay.query("VIEWPORT") if v.dxf.layer == RULES["viewportLayer"]]
        self.assertEqual(len(vps), 2, report)
        uni = next(v for v in lay.query("VIEWPORT") if v.dxf.layer != RULES["viewportLayer"])
        self.assertEqual((round(uni.dxf.width, 2), round(uni.dxf.view_height, 2)), (559.0, 315.85))  # unifilar intacto, 1:1
        title = next(i for i in lay.query("INSERT") if i.dxf.name == RULES["titleBlock"])
        tx = title.dxf.insert.x
        box = lambda v: (v.dxf.center.x - v.dxf.width / 2, v.dxf.center.y - v.dxf.height / 2, v.dxf.center.x + v.dxf.width / 2, v.dxf.center.y + v.dxf.height / 2)
        overlap = lambda a, b: a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
        rotulo = (tx - 180, title.dxf.insert.y, tx, title.dxf.insert.y + 84)
        for v in vps:
            n = v.dxf.view_height / v.dxf.height
            self.assertIn(round(n, 3), [float(s) for s in RULES["scales"]])
            b = box(v)
            self.assertTrue(x0 <= b[0] and b[2] <= x1 and y0 <= b[1] and b[3] <= y1, "vista fuera de la hoja")
            self.assertFalse(overlap(b, box(uni)), "vista sobre el unifilar")
            self.assertFalse(overlap(b, rotulo), "vista sobre el rótulo")
        self.assertFalse(overlap(box(vps[0]), box(vps[1])))
        attrs = {a.dxf.tag: a.dxf.text for a in title.attribs}
        self.assertEqual(attrs["TITLE_2OF3"], RULES["titleAttributes"]["TITLE_2OF3"])
        self.assertEqual(attrs["DOCN°"], "X-001")  # los datos del usuario no se tocan
        texts = [t.dxf.text for t in lay.query("TEXT")]
        self.assertIn(RULES["frontTitle"], texts)
        self.assertIn(RULES["doorTitle"], texts)
