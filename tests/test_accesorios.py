"""Pruebas de la propuesta de accesorios (accesorios.py) y su integración con el control de normativa."""
import json
import unittest
from pathlib import Path

from accesorios import complete
from normativa import check_project

ROOT = Path(__file__).resolve().parents[1]


def s200(tag, x, poles, in_amps="16"):
    return {"tag": tag, "shell": "abb.s200m.1p.front", "x": x, "y": 761, "w": 17.5 * poles, "h": 88, "poles": poles, "marking": {"In": in_amps}}


def project(devices):
    rail = {"id": "DIN-1", "x": 200, "y": 805, "length": 600, "height": 35}
    return {"devices": devices, "enclosure": {"mountingLayout": {"dinRails": [rail]}}}


class Accesorios(unittest.TestCase):
    def test_ts4_real_queda_sin_errores_comprobables(self):
        data = json.loads((ROOT / "datos" / "ts4_topografia.json").read_text(encoding="utf-8"))
        complete(data)
        errors = [f for f in check_project(data) if f["severity"] == "error" and not f["manual"]]
        self.assertEqual(errors, [])

    def test_borne_pe_cae_en_hueco_libre_del_riel(self):
        p = complete(project([s200("QF1", 200, 3), s200("QF2", 300, 2)]))
        pe = next(a for a in p["accessories"] if a["type"] == "pe_terminal")
        self.assertTrue(pe["placed"])
        for d in p["devices"]:
            self.assertTrue(pe["x"] + pe["w"] <= d["x"] or pe["x"] >= d["x"] + d["w"], d["tag"])

    def test_sin_lugar_en_el_riel_queda_sin_ubicar(self):
        devices = [s200(f"QF{i}", 200 + 17.5 * 4 * i, 4) for i in range(8)]  # 8 x 70 mm = 560 mm; quedan 40 mm
        p = complete(project(devices))
        pe = next(a for a in p["accessories"] if a["type"] == "pe_terminal")  # 8 x 6 mm = 48 mm
        self.assertFalse(pe["placed"])
        self.assertTrue([f for f in check_project(p) if f["rule"] == "accesorio-sin-lugar"])  # y el control lo avisa

    def test_peine_para_equipos_contiguos_y_se_reemplaza_al_repetir(self):
        p = project([s200("QF1", 200, 3), s200("QF2", 252.5, 3)])
        complete(p)
        complete(p)
        combs = [a for a in p["accessories"] if a["type"] == "comb"]
        self.assertEqual(len(combs), 1)
        self.assertEqual(combs[0]["devices"], ["QF1", "QF2"])
        self.assertEqual(combs[0]["corrienteA"], 63)
        self.assertFalse([f for f in check_project(p) if f["rule"] == "peines-entre-termomagneticas"])

    def test_bloque_de_distribucion_para_corriente_alta(self):
        p = complete(project([s200("QF1", 200, 2, "100")]))
        block = next(a for a in p["accessories"] if a["type"] == "distribution_block")
        self.assertEqual(block["catalogId"], "abb-brt125a")
        self.assertTrue(block["placed"])
        self.assertEqual(block["w"], 128)

    def test_sin_bloque_en_catalogo_lo_dice(self):
        p = complete(project([s200("QF1", 200, 2, "400")]))
        block = next(a for a in p["accessories"] if a["type"] == "distribution_block")
        self.assertFalse(block["placed"])
        self.assertIn("catálogo", block["note"])

    def test_corriente_normal_no_pide_bloque(self):
        p = complete(project([s200("QF1", 200, 2, "40")]))
        self.assertFalse([a for a in p["accessories"] if a["type"] == "distribution_block"])

    def test_se_conservan_los_accesorios_manuales(self):
        p = project([s200("QF1", 200, 2)])
        p["accessories"] = [{"type": "pe_terminal", "count": 1, "label": "manual"}]
        complete(p)
        self.assertIn("manual", [a.get("label") for a in p["accessories"]])


if __name__ == "__main__":
    unittest.main()
