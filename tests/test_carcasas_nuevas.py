"""Carcasas cargadas el 2026-11-18 desde CAD ABB: OT100/125F, OT160…250E, F202/F204, SN201 (+ S200P como hipótesis)."""
import json
import unittest
from pathlib import Path

from importador import find_series

ROOT = Path(__file__).resolve().parents[1]
CAT = json.loads((ROOT / "datos" / "catalogo_abb.json").read_text(encoding="utf-8"))
FRONTS = json.loads((ROOT / "datos" / "frentes_cad.json").read_text(encoding="utf-8"))["items"]
LOOK = json.loads((ROOT / "datos" / "apariencias_abb.json").read_text(encoding="utf-8"))["items"]
SHELLS = {s["id"]: s for s in CAT["deviceShells"]}

CASOS = [("OT100F4", 4, "abb.ot100_125f4.4p.front"), ("OT125F4", 4, "abb.ot100_125f4.4p.front"), ("OT125F3", 3, "abb.ot100_125f3.3p.front"),
         ("OT160EV03", 3, "abb.ot160_250e03.3p.front"), ("OT250E04", 4, "abb.ot160_250e04.4p.front"),
         ("F204 AC-40/0,03", 4, "abb.f204.4p.front"), ("F202 AC-25/0,03", 2, "abb.f202.2p.front"), ("SN201L B16", 2, "abb.sn201.1pn.front"),
         ("S204P-C25", 4, "abb.s200m.1p.front")]


class CarcasasNuevas(unittest.TestCase):
    def test_modelos_del_unifilar_encuentran_su_carcasa(self):
        for model, poles, shell in CASOS:
            serie, _, motivo = find_series(model, poles, CAT)
            self.assertIsNotNone(serie, f"{model}: {motivo}")
            self.assertEqual(serie["shell"], shell, model)

    def test_cada_carcasa_tiene_frente_cad_apariencia_y_archivo(self):
        for _, _, shell in CASOS:
            spec = SHELLS[shell]
            self.assertIn(shell, FRONTS)
            self.assertIn(shell, LOOK)
            for f in spec.get("cadFiles", []):
                self.assertTrue((ROOT / f).exists(), f)
            w, h = FRONTS[shell]["sourceProjectionExtent"]
            self.assertLess(abs(w / h - spec["width"] / spec["height"]) / (w / h), 0.08, shell)  # el dibujo no se deforma

    def test_montaje(self):
        self.assertEqual(SHELLS["abb.ot100_125f4.4p.front"].get("mounting"), "din")  # ficha ABB: DIN-rail mountable
        self.assertIsNone(SHELLS["abb.ot160_250e03.3p.front"].get("mounting"))  # base mounted


class PanelCiego(unittest.TestCase):
    def test_sin_panel_ciego_si_hay_un_ot_en_placa(self):
        from bom import build_bom
        p = {"project": "x", "enclosure": {"id": "sr2-srn5420k", "mountingLayout": {"dinRails": [{"id": "DIN-1", "kdKit": "KD5040K"}]}},
             "devices": [{"tag": "QS1", "model": "OT160EV03", "poles": 3, "shell": "abb.ot160_250e03.3p.front"},
                         {"tag": "QF1", "model": "S203-C50", "poles": 3, "shell": "abb.s200m.1p.front", "railId": "DIN-1"}], "accessories": []}
        codes = [r["code"] for r in build_bom(p, CAT)]
        self.assertFalse(any(str(c).startswith("PC1") for c in codes), codes)


if __name__ == "__main__":
    unittest.main()
