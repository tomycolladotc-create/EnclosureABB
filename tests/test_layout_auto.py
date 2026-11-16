"""Pruebas del armado automático (layout_auto.py): elige el gabinete más chico y no pisa equipos."""
import json
import unittest
from pathlib import Path

from layout_auto import autolayout

DATOS = Path(__file__).resolve().parents[1] / "datos"


def load(name):
    return json.loads((DATOS / name).read_text(encoding="utf-8"))


def boxes(project):
    return [(d["tag"], d["x"], d["y"], d["x"] + d["w"], d["y"] + d["h"]) for d in project["devices"]]


class LayoutAuto(unittest.TestCase):
    def setUp(self):
        self.catalog = load("catalogo_abb.json")
        self.new, self.summary = autolayout(load("ts4_topografia.json"), self.catalog)

    def test_elige_un_gabinete_mas_chico_que_el_actual(self):
        ext = self.new["enclosure"]["externalBody"]
        self.assertLess(ext["width"] * ext["height"], 1100 * 2200)

    def test_ts4_entra_en_un_sr2_con_filas_fijas_del_kit_kd(self):
        e = self.new["enclosure"]
        self.assertTrue(e["id"].startswith("sr2-"))
        self.assertGreaterEqual(e["functional"]["depth"], 200)  # reglas_layout.json: minDepthForKitDevicesMm
        kd = next(x for x in self.catalog["enclosures"] if x["id"] == e["id"])["kdKit"]
        rails = e["mountingLayout"]["dinRails"]
        self.assertLessEqual(len(rails), kd["rows"])
        self.assertIn(kd["kit"], e["structuralComponentReferences"]["parts"])
        ys = sorted(r["y"] for r in rails)
        self.assertTrue(all(abs((b - a) - kd["rowPitchMm"]) < 0.01 for a, b in zip(ys, ys[1:])))  # filas contiguas a 185 mm
        for r in rails:
            self.assertTrue(r["fixed"])
            self.assertEqual(r["length"], kd["modulesPerRow"] * kd["moduleMm"])

    def test_los_equipos_de_kit_no_invaden_la_pila_de_filas(self):
        rails = self.new["enclosure"]["mountingLayout"]["dinRails"]
        stack_top = max(r["y"] for r in rails) + 185 / 2
        din = {s["id"] for s in self.catalog["deviceShells"] if s.get("mounting") == "din"}
        for d in self.new["devices"]:
            if d["shell"] not in din:
                self.assertGreaterEqual(d["y"], stack_top, d["tag"])

    def test_informa_alternativa_con_riel_libre_solo_si_es_mas_chica(self):
        alt = self.summary["alternativaRielLibre"]
        if alt:
            area = lambda i: (lambda b: b["width"] * b["height"])(next(e for e in self.catalog["enclosures"] if e["id"] == i)["externalBody"])
            self.assertLess(area(alt["id"]), area(self.new["enclosure"]["id"]))

    def test_riel_libre_usa_gd_y_un_gabinete_no_mayor(self):
        free, summary = autolayout(load("ts4_topografia.json"), self.catalog, free_rails=True)
        rails = free["enclosure"]["mountingLayout"]["dinRails"]
        self.assertTrue(all(r["type"].startswith("GD") and not r.get("fixed") for r in rails))
        area = lambda e: e["externalBody"]["width"] * e["externalBody"]["height"]
        self.assertLessEqual(area(free["enclosure"]), area(self.new["enclosure"]))

    def test_filas_de_riel_libre_dejan_lugar_a_peine_etiqueta_y_canaleta(self):
        free, _ = autolayout(load("ts4_topografia.json"), self.catalog, free_rails=True)
        gap = load("reglas_layout.json")["railRowGapMm"]
        rails = sorted(free["enclosure"]["mountingLayout"]["dinRails"], key=lambda r: -r["y"])
        spans = []
        for r in rails:
            row = [d for d in free["devices"] if d["y"] <= r["y"] <= d["y"] + d["h"] and d["x"] < r["x"] + r["length"] and r["x"] < d["x"] + d["w"]]
            if row:
                spans.append((min(d["y"] for d in row), max(d["y"] + d["h"] for d in row)))
        for upper, lower in zip(spans, spans[1:]):
            self.assertGreaterEqual(upper[0] - lower[1], gap - 1e-6)

    def test_es_el_primero_que_entra_del_mas_chico_al_mas_grande(self):
        tried = self.summary["intentos"]
        self.assertTrue(tried[-1]["entra"])
        self.assertFalse(any(t["entra"] for t in tried[:-1]))
        areas = [next(e for e in self.catalog["enclosures"] if e["id"] == t["id"])["externalBody"] for t in tried]
        self.assertEqual(areas, sorted(areas, key=lambda b: b["width"] * b["height"]))

    def test_todo_queda_dentro_del_area_funcional_y_sin_pisarse(self):
        f = self.new["enclosure"]["functional"]
        items = boxes(self.new)
        for tag, x0, y0, x1, y1 in items:
            self.assertGreaterEqual(x0, 0, tag)
            self.assertGreaterEqual(y0, 0, tag)
            self.assertLessEqual(x1, f["width"], tag)
            self.assertLessEqual(y1, f["height"], tag)
        for i, a in enumerate(items):
            for b in items[i + 1:]:
                overlap = a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6 and a[2] < b[4] - 1e-6 and b[2] < a[4] - 1e-6
                self.assertFalse(overlap, f"{a[0]} y {b[0]} se pisan")

    def test_equipos_de_riel_quedan_sobre_un_riel_del_gabinete(self):
        rails = self.new["enclosure"]["mountingLayout"]["dinRails"]
        din = {s["id"] for s in self.catalog["deviceShells"] if s.get("mounting") == "din"}
        for d in self.new["devices"]:
            if d["shell"] in din:
                self.assertTrue(any(abs(d["y"] + d["h"] / 2 - r["y"]) < 0.01 and r["x"] <= d["x"] and d["x"] + d["w"] <= r["x"] + r["length"] for r in rails), d["tag"])

    def test_no_modifica_el_proyecto_original(self):
        original = load("ts4_topografia.json")
        autolayout(original, self.catalog)
        self.assertEqual(original, load("ts4_topografia.json"))

    def test_contenido_que_no_entra_da_error_claro(self):
        big = load("ts4_topografia.json")
        big["devices"] = [dict(big["devices"][0], tag=f"QF{i}", w=2000) for i in range(3)]
        with self.assertRaises(ValueError):
            autolayout(big, self.catalog)


if __name__ == "__main__":
    unittest.main()
