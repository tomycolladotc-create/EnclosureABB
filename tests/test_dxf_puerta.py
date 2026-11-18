"""El DXF trae la vista con la puerta cerrada (pilotos, placa grabada, cartel) y no superpone la lista de materiales."""
import json
import unittest
from io import StringIO
from pathlib import Path

import ezdxf

from cad_export import _ascii, build_dxf

ROOT = Path(__file__).resolve().parents[1]
L = lambda n: json.loads((ROOT / "datos" / n).read_text(encoding="utf-8"))


class PuertaCerradaDXF(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = L("ts4_topografia.json")
        p["signals"] = {"pilotLights": [{"label": x, "function": "presencia de tensión", "voltage": "220 Vca"} for x in "RST"]}
        cls.p = p
        cls.doc = ezdxf.read(StringIO(build_dxf(p, L("catalogo_abb.json"), L("frentes_cad.json"), L("apariencias_abb.json")).decode("utf-8")))
        cls.msp = cls.doc.modelspace()

    def test_capas_de_la_puerta(self):
        for layer in ("ABB_PUERTA_CERRADA", "ABB_PUERTA_GRABADO", "ABB_PUERTA_SENIALIZACION", "ABB_PUERTA_CARTEL"):
            self.assertTrue(len(self.msp.query(f'*[layer=="{layer}"]')), layer)

    def test_un_agujero_por_piloto_del_unifilar(self):
        holes = [c for c in self.msp.query('CIRCLE[layer=="ABB_PUERTA_SENIALIZACION"]') if abs(c.dxf.radius - 11) < 0.01]
        self.assertEqual(len(holes), 3)

    def test_nombre_grabado_y_cartel(self):
        texts = [t.dxf.text for t in self.msp.query("TEXT")]
        self.assertIn(str(self.p["project"]).upper(), texts)
        self.assertIn("RIESGO ELECTRICO", texts)

    def test_bom_a_la_derecha_de_la_puerta(self):
        door_right = max(e.dxf.center.x for e in self.msp.query('CIRCLE[layer=="ABB_PUERTA_CERRADA"]'))
        bom_left = min(t.dxf.insert.x for t in self.msp.query('TEXT[layer=="ABB_BOM"]'))
        self.assertGreater(bom_left, door_right + 50)

    def test_texto_sin_signos_de_pregunta(self):
        self.assertEqual(_ascii("Canaleta 25×40 · Ø22 · tensión"), "Canaleta 25x40 - %%c22 - tension")
        bad = [t.dxf.text for t in self.msp.query('TEXT[layer=="ABB_BOM"]') if "?" in t.dxf.text]
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
