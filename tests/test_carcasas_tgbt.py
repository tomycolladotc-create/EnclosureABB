"""Carcasas cargadas el 2026-11-19 para el plano GENERAL (TGBT y tableros auxiliares): E2.2, XT3, XT1 3P, T4, T2, S803, OT63/80F."""
import json
import unittest
from pathlib import Path

from importador import detect_devices, find_series

ROOT = Path(__file__).resolve().parents[1]
CAT = json.loads((ROOT / "datos" / "catalogo_abb.json").read_text(encoding="utf-8"))
FRONTS = json.loads((ROOT / "datos" / "frentes_cad.json").read_text(encoding="utf-8"))["items"]
LOOK = json.loads((ROOT / "datos" / "apariencias_abb.json").read_text(encoding="utf-8"))["items"]
SOURCES = {a["archivo"] for a in json.loads((ROOT / "datos" / "fuentes_descargadas.json").read_text(encoding="utf-8"))["archivos"]}
SHELLS = {s["id"]: s for s in CAT["deviceShells"]}

# Modelos tal como los escribe el unifilar e-Design del plano GENERAL.
CASOS = [("E2.2N 2000 Ekip Dip LI 2000", 4, "abb.emax.e22.4p.fixed.front"),
         ("XT3S 250 TMD 200-2000 N=50%", 4, "abb.tmax.xt3.4p.fixed.front"),
         ("XT1S 160 TMD 125-1250", 3, "abb.tmax.xt1.3p.fixed.front"),
         ("XT1S 160 TMD 125-1250 N=50%", 4, "abb.tmax.xt1.4p.fixed.front"),
         ("T4S 320 PR221DS-LS/I 320A", 4, "abb.tmax.t4.4p.fixed.front"),
         ("T2S 160 PR221DS-LS 160A", 3, "abb.tmax.t2.3p.fixed.front"),
         ("S803S-C63", 3, "abb.s803.3p.front"), ("S804S-C100", 4, "abb.s804n.4p.front"),
         ("OT80F4", 4, "abb.ot63_80f4.4p.front"), ("OT63F3", 3, "abb.ot63_80f3.3p.front")]


NUEVAS = {c[2] for c in CASOS} - {"abb.tmax.xt1.4p.fixed.front", "abb.s804n.4p.front"}  # las previas se cargaron antes del registro


class CarcasasTGBT(unittest.TestCase):
    def test_modelos_encuentran_su_carcasa(self):
        for model, poles, shell in CASOS:
            serie, _, motivo = find_series(model, poles, CAT)
            self.assertIsNotNone(serie, f"{model}: {motivo}")
            self.assertEqual(serie["shell"], shell, model)

    def test_frente_apariencia_archivo_y_fuente(self):
        for _, _, shell in CASOS:
            spec = SHELLS[shell]
            self.assertIn(shell, FRONTS)
            self.assertIn(shell, LOOK)
            for f in spec.get("cadFiles", []):
                self.assertTrue((ROOT / f).exists(), f)
                if shell in NUEVAS:
                    self.assertIn(f, SOURCES, f"{f} sin registrar en fuentes_descargadas.json")
            w, h = FRONTS[shell]["sourceProjectionExtent"]
            self.assertLess(abs(w / h - spec["width"] / spec["height"]) / (w / h), 0.08, shell)

    def test_medidas_del_cad(self):
        self.assertEqual((SHELLS["abb.tmax.xt3.4p.fixed.front"]["width"], SHELLS["abb.tmax.xt3.4p.fixed.front"]["height"]), (140, 150))
        self.assertEqual((SHELLS["abb.tmax.t4.4p.fixed.front"]["width"], SHELLS["abb.tmax.t4.4p.fixed.front"]["height"]), (140, 205))
        self.assertEqual(SHELLS["abb.s803.3p.front"]["width"], 79.5)  # 3 × 26,5 mm (S804N = 106)

    def test_montaje(self):
        for shell in ("abb.ot63_80f3.3p.front", "abb.ot63_80f4.4p.front", "abb.s803.3p.front"):
            self.assertEqual(SHELLS[shell].get("mounting"), "din", shell)
        for shell in ("abb.emax.e22.4p.fixed.front", "abb.tmax.xt3.4p.fixed.front", "abb.tmax.t4.4p.fixed.front"):
            self.assertIsNone(SHELLS[shell].get("mounting"), shell)

    def test_s290_sin_cad_no_se_dibuja_pero_se_avisa(self):
        text = "-QF58\nS 293-C 803x25+PE16 mm² Cu\nACU\nTSB-1.3\nRST\n0,00 (*)\n"
        d = next(x for x in detect_devices(text, CAT) if x["tag"] == "QF58")
        self.assertIsNone(d["shell"])
        self.assertEqual(d.get("mounting"), "din")
        self.assertIn("lista de materiales", d["status"])


if __name__ == "__main__":
    unittest.main()
