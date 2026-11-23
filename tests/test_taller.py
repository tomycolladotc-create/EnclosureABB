"""Planos de taller (pedido de Thomas 2026-11-23): perforado de puerta, vista lateral y placas de identificación."""
import json
import unittest
from pathlib import Path

from cad_export import door_features
from excel_equipamiento import nameplates
from regresion_general import BOARDS, build
from taller import depth_check, door_holes, shop_doc

ROOT = Path(__file__).resolve().parent.parent
CATALOG = json.loads((ROOT / "datos" / "catalogo_abb.json").read_text(encoding="utf-8"))
ACC = json.loads((ROOT / "datos" / "accesorios_abb.json").read_text(encoding="utf-8"))


class Taller(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.projects = [build(pdf)["project"] for pdf in BOARDS]

    def test_perforaciones_iguales_a_la_vista_de_puerta_y_al_catalogo(self):
        pilot = ACC["pilotLights"][0]
        for p in self.projects:
            with self.subTest(tablero=p.get("project")):
                f, holes = door_holes(p, CATALOG, ACC)
                lights = (p.get("signals") or {}).get("pilotLights") or []
                self.assertEqual(len(holes), len(lights))
                for h in holes:
                    self.assertEqual(h["d"], pilot["agujeroMm"])
                    self.assertTrue(any(abs(h["x"] - l["x"]) < 0.1 and abs(h["y"] - l["y"]) < 0.1 and l["cutR"] * 2 == h["d"] for l in f["lights"]))
                    self.assertTrue(0 < h["x"] < f["w"] and 0 < h["y"] < f["h"], "agujero fuera de la puerta")

    def test_ningun_equipo_mas_profundo_que_el_gabinete(self):
        for p in self.projects:
            with self.subTest(tablero=p.get("project")):
                dc = depth_check(p, CATALOG)
                self.assertIsNotNone(dc["deepest"])
                self.assertGreaterEqual(dc["margin"], 0, dc)

    def test_cotas_en_mm_con_coma(self):
        p = self.projects[0]
        doc = shop_doc(p, CATALOG, ACC, 10)
        texts = {e.dxf.text for b in doc.blocks if b.name.startswith("*D") for e in b if e.dxftype() in ("MTEXT", "TEXT")}
        self.assertIn(f"{p['enclosure']['externalBody']['width']:g}", texts)  # ancho de la puerta tal cual, sin ×100
        self.assertFalse(any("." in t for t in texts))

    def test_placas_con_el_texto_del_dibujo(self):
        p = self.projects[0]
        rows = nameplates({"X": p}, CATALOG)
        self.assertEqual(rows[0][3], str(p.get("project")).upper())
        self.assertEqual(len(rows), 1 + len(p["devices"]))
        for r, d in zip(rows[1:], p["devices"]):
            self.assertEqual(r[3], str(d.get("circuit") or d.get("tag")))
