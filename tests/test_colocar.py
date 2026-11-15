"""Pruebas de la ubicación automática en riel DIN (colocar.py)."""
import unittest

from colocar import GAP_OTHER_SERIES_MM, place_din

CATALOG = {"deviceShells": [{"id": "din.a", "mounting": "din"}, {"id": "din.b", "mounting": "din"}, {"id": "kit.x"}]}
RAIL = {"id": "DIN-1", "x": 200, "y": 805, "length": 600, "height": 35}


def dev(tag, shell="din.a", w=35, unplaced=True, x=150, y=150):
    return {"tag": tag, "shell": shell, "w": w, "h": 88, "x": x, "y": y, "unplaced": unplaced}


def project(devices, rails=(RAIL,)):
    return {"devices": devices, "enclosure": {"mountingLayout": {"dinRails": list(rails)}}}


class Colocar(unittest.TestCase):
    def test_misma_carcasa_va_pegada(self):
        p = project([dev("A"), dev("B")])
        self.assertEqual(place_din(p, CATALOG), [])
        self.assertEqual([d["x"] for d in p["devices"]], [200, 235])
        self.assertTrue(all(d["y"] == 805 - 44 for d in p["devices"]))
        self.assertFalse(any(d.get("unplaced") for d in p["devices"]))

    def test_distinta_carcasa_deja_separacion(self):
        p = project([dev("A"), dev("B", shell="din.b")])
        place_din(p, CATALOG)
        self.assertEqual(p["devices"][1]["x"], 235 + GAP_OTHER_SERIES_MM)

    def test_respeta_equipos_ya_ubicados(self):
        p = project([dev("A", unplaced=False, x=200, y=761), dev("B")])
        place_din(p, CATALOG)
        self.assertEqual(p["devices"][1]["x"], 235)

    def test_llena_el_hueco_del_medio(self):
        p = project([dev("A", unplaced=False, x=200, y=761), dev("C", unplaced=False, x=300, y=761), dev("B")])
        place_din(p, CATALOG)
        self.assertEqual(p["devices"][2]["x"], 235)

    def test_si_no_entra_queda_marcado(self):
        p = project([dev(f"Q{i}", w=70) for i in range(9)])  # 630 mm > 600 mm de riel
        failed = place_din(p, CATALOG)
        self.assertEqual(failed, ["Q8"])
        self.assertTrue(p["devices"][8]["unplaced"])
        self.assertIn("no entra", p["devices"][8]["placementNote"])

    def test_equipos_de_kit_no_se_tocan(self):
        p = project([dev("X", shell="kit.x")])
        place_din(p, CATALOG)
        self.assertTrue(p["devices"][0]["unplaced"])
        self.assertEqual((p["devices"][0]["x"], p["devices"][0]["y"]), (150, 150))


if __name__ == "__main__":
    unittest.main()
