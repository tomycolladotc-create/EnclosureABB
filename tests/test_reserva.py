"""Reserva de espacio por tablero (pedido de Thomas 2026-11-23): se marca un porcentaje, el armado lo respeta y se informa."""
import copy
import json
import unittest
from pathlib import Path

from layout_auto import autolayout_conforme
from regresion_general import BOARDS, build
from validacion import rail_reserve, validate

ROOT = Path(__file__).resolve().parent.parent
CATALOG = json.loads((ROOT / "datos" / "catalogo_abb.json").read_text(encoding="utf-8"))
RULES = json.loads((ROOT / "datos" / "reglas_validacion.json").read_text(encoding="utf-8"))


class Reserva(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.projects = {pdf.stem: build(pdf)["project"] for pdf in BOARDS}

    def test_se_informa_el_libre_real(self):
        for name, p in self.projects.items():
            with self.subTest(tablero=name):
                r = validate(p, CATALOG, RULES)["reserve"]
                self.assertIsNotNone(r["freePercent"])
                self.assertTrue(0 <= r["freePercent"] <= 100)

    def test_el_armado_respeta_la_reserva_pedida(self):
        for name in ("TS3-PORT_7-8-9-10", "TSB", "TSI1", "TS_AUX_4"):
            p = next((v for k, v in self.projects.items() if k.upper().replace("_", "") == name.upper().replace("_", "")), None)
            self.assertIsNotNone(p, name)
            with self.subTest(tablero=name):
                q = copy.deepcopy(p)
                q["reservePercent"] = 20
                new, _ = autolayout_conforme(q, CATALOG)
                v = validate(new, CATALOG, RULES)
                self.assertGreaterEqual(v["reserve"]["freePercent"], 20)
                self.assertEqual(v["errors"], 0, [f["message"] for f in v["findings"] if f["level"] == "error"])
                self.assertNotIn("reserve_below", {f["code"] for f in v["findings"]})

    def test_aviso_si_queda_por_debajo(self):
        p = copy.deepcopy(min(self.projects.values(), key=lambda q: rail_reserve(q, CATALOG, RULES)["freePercent"]))
        p["reservePercent"] = 50
        self.assertIn("reserve_below", {f["code"] for f in validate(p, CATALOG, RULES)["findings"]})
