"""Lecciones de la revisión de los 24 tableros del plano GENERAL (2026-11-19, docs/LECCIONES.md).

Cada test fija un error que se cometió para que no vuelva: la auditoría lo detecta y el generador no lo produce.
"""
import copy
import json
import unittest
from pathlib import Path

from accesorios import complete, propose
from auditoria import audit, main_device, rated_current
from bom import build_bom
from importador import detect_board
from layout_auto import autolayout_conforme
from proyectos import TEMPLATE_CONTENT_KEYS, create

ROOT = Path(__file__).resolve().parents[1]
L = lambda n: json.loads((ROOT / "datos" / n).read_text(encoding="utf-8"))
CAT = L("catalogo_abb.json")
SHELLS = {s["id"]: s for s in CAT["deviceShells"]}


def dev(tag, model, shell, circuit=None, evidence="", poles=None):
    s = SHELLS[shell]
    w = s["width"] if not s.get("poleModule") else s["poleModule"]["width"] * poles
    return {"tag": tag, "model": model, "shell": shell, "circuit": circuit, "evidence": evidence, "poles": poles, "w": w, "h": s["height"], "marking": {}}


def project(devices, **extra):
    base = L("ts4_topografia.json")
    p = {k: copy.deepcopy(v) for k, v in base.items() if k not in TEMPLATE_CONTENT_KEYS}
    p.update({"project": "prueba", "devices": devices, "accessories": [], **extra})
    return p


def codes(p):
    return {f["code"] for f in audit(p, CAT)}


class CorrienteYEntrada(unittest.TestCase):
    def test_corriente_nominal_de_cada_familia(self):
        casos = {"E2.2N 2000 Ekip Dip LI 2000": 2000, "T4S 320 PR221DS-LS/I 320A": 320, "XT1S 160 TMD 125-1250": 125,
                 "OT100F4": 100, "S804S-C100": 100, "S 293-C 80": 80}
        for model, amps in casos.items():
            self.assertEqual(rated_current({"model": model}), amps, model)

    def test_entrada_por_principal_aunque_sea_qf(self):
        d = dev("QF1", "E2.2N 2000 Ekip Dip LI 2000", "abb.emax.e22.4p.fixed.front", evidence="E2.2N 2000 INTERRUPTOR PRINCIPAL 66 kA")
        self.assertIs(main_device(project([d, dev("QF2", "XT3S 250 TMD 200-2000", "abb.tmax.xt3.4p.fixed.front", "TS1")])), d)


class ArmadoComoUnArmador(unittest.TestCase):
    """El TGBT de 2000 A: general solo arriba, kits en System pro E, barra por la entrada, canaletas en todas las filas."""

    @classmethod
    def setUpClass(cls):
        devs = [dev("QF1", "E2.2N 2000 Ekip Dip LI 2000", "abb.emax.e22.4p.fixed.front", evidence="INTERRUPTOR PRINCIPAL")]
        devs += [dev(f"QF{n}", "XT3S 250 TMD 200-2000 N=50%", "abb.tmax.xt3.4p.fixed.front", f"TS{n}") for n in range(2, 5)]
        devs += [dev("QF5", "XT1S 160 TMD 125-1250", "abb.tmax.xt1.3p.fixed.front", "TSA"), dev("QF6", "T2S 160 PR221DS-LS 160A", "abb.tmax.t2.3p.fixed.front", "TSB")]
        devs += [dev(f"QF{n}", "S804S-C32", "abb.s804n.4p.front", f"TSF{n}") for n in range(7, 10)]
        cls.p, cls.summary = autolayout_conforme(project(devs, feeder={"peMm2": 150.0, "peParallel": 6}), CAT)
        cls.found = codes(cls.p)

    def test_sin_errores_de_auditoria(self):
        errors = [f for f in audit(self.p, CAT) if f["level"] == "error"]
        self.assertEqual(errors, [], "\n".join(f["message"] for f in errors))

    def test_emax_va_en_gabinete_de_piso(self):
        self.assertIn("System pro E", self.p["enclosure"]["line"])

    def test_general_solo_en_la_fila_de_arriba(self):
        top = max(self.p["devices"], key=lambda d: d["y"] + d["h"])
        self.assertEqual(top["tag"], "QF1")
        same_row = [d["tag"] for d in self.p["devices"] if d["tag"] != "QF1" and d["y"] + d["h"] > top["y"]]
        self.assertEqual(same_row, [])

    def test_orden_del_unifilar(self):
        from auditoria import _rows
        kit = [d for row in _rows(self.p["devices"]) for d in sorted(row["items"], key=lambda d: d["x"]) if d["tag"] != "QF1" and "s804" not in d["shell"]]
        self.assertEqual([d["tag"] for d in kit], ["QF2", "QF3", "QF4", "QF5", "QF6"])

    def test_kits_system_pro_e_en_la_lista(self):
        rows = build_bom(self.p, CAT)
        kit_rows = [r for r in rows if r["category"] == "Kit de montaje"]
        self.assertEqual(sum(r["quantity"] for r in kit_rows), 6)  # E2.2 + 3 XT3 + XT1 + T2 (sin código: FALTA CÓDIGO, pero en la lista)

    def test_barra_dimensionada_por_la_entrada(self):
        bars = [a for a in self.p["accessories"] if a["type"] in ("copper_busbar", "distribution_block")]
        self.assertTrue(bars)
        for a in bars:
            self.assertTrue(a.get("corrienteA") is None or a["corrienteA"] >= 2000, a)
        rows = build_bom(self.p, CAT)
        self.assertTrue(any("2000 A" in r["description"] and r["category"] == "Barra de distribución" for r in rows), "la barra que falta igual va a la lista")

    def test_pe_de_alimentacion_grueso_pide_barra_de_tierra(self):
        self.assertTrue(any(a["type"] == "pe_bar" for a in self.p["accessories"]))
        rows = build_bom(self.p, CAT)
        self.assertTrue(any(r["category"] == "Barra de tierra (PE)" for r in rows))


class GeneralDeRielArriba(unittest.TestCase):
    def test_seccionador_de_riel_va_arriba_de_las_cajas(self):
        """TS6: el OT63F4 (riel) quedaba abajo y las XT1 arriba, con un hueco de 370 mm en el medio."""
        devs = [dev("QS1", "OT80F4", "abb.ot63_80f4.4p.front", evidence="SECCIONADOR BAJO CARGA")]
        devs += [dev(f"QF{n}", "XT1S 160 TMD 125-1250 N=50%", "abb.tmax.xt1.4p.fixed.front", f"TS-6.{n}") for n in range(2, 5)]
        devs += [dev("QF5", "S804S-C25", "abb.s804n.4p.front", "TS-6.5")]
        p, _ = autolayout_conforme(project(devs), CAT)
        from auditoria import _rows
        self.assertIn("QS1", [d["tag"] for d in _rows(p["devices"])[0]["items"]])
        found = codes(p)
        for code in ("main_not_on_top", "dead_gap_between_rows", "row_without_duct_above", "row_without_duct_below"):
            self.assertNotIn(code, found)


class GabineteJusto(unittest.TestCase):
    def test_bloque_que_no_entra_suma_una_fila_en_vez_de_agrandar(self):
        """TSMAQ1: OT80F4 + 3 S204 + bloque BRT125A salía en 800×800 con una sola fila; con una fila más entra en 400×600."""
        devs = [dev("QS1", "OT80F4", "abb.ot63_80f4.4p.front", evidence="SECCIONADOR BAJO CARGA 80 A - 4P")]
        for n, (model, amps) in enumerate([("S204-C40", "40"), ("S204-C25", "25"), ("S204-C25", "25")], 1):
            d = dev(f"QF{156 + n}", model, "abb.s200m.1p.front", f"TSMAQ1-1.{n}", poles=4)
            d["marking"] = {"In": amps}
            devs.append(d)
        p, _ = autolayout_conforme(project(devs), CAT)
        body = p["enclosure"]["externalBody"]
        self.assertLessEqual(body["width"] * body["height"], 405 * 605)  # 400 × 600 nominal (exterior 403 × 603)
        self.assertNotIn("board_oversized", codes(p))
        self.assertTrue(all(a.get("placed") is not False for a in p["accessories"] if a.get("catalogId")))


class OrdenYLugar(unittest.TestCase):
    def test_riel_en_orden_de_unifilar(self):
        """TSB: se ordenaba por carcasa y quedaba TSB-1.13 antes que TSB-1.1."""
        devs = [dev("QS1", "OT100F4", "abb.ot100_125f4.4p.front", evidence="SECCIONADOR")]
        models = [("S201L-C16 NA", "abb.s200m.1pn.front", 2), ("S203-C10", "abb.s200m.1p.front", 3), ("S 293-C 80", "abb.s290.3p.outline", 3),
                  ("S203-C16", "abb.s200m.1p.front", 3), ("S201L-C16 NA", "abb.s200m.1pn.front", 2)]
        for n, (model, shell, poles) in enumerate(models, 1):
            devs.append(dev(f"QF{55 + n}", model, shell, f"TSB-1.{n}", poles=poles))
        p, _ = autolayout_conforme(project(devs), CAT)
        from auditoria import _rows
        din = [d for row in _rows(p["devices"]) for d in sorted(row["items"], key=lambda d: d["x"]) if d["tag"] != "QS1"]
        self.assertEqual([d["circuit"] for d in din], [f"TSB-1.{n}" for n in range(1, 6)])
        self.assertNotIn("order_not_unifilar", codes(p))

    def test_equipo_sin_dibujar_se_avisa(self):
        p = project([], devicesNotDrawn=[{"tag": "QF9", "model": "X 999", "status": "serie sin carcasa en el catálogo"}])
        self.assertIn("not_drawn_no_space", codes(p))


class PlantillaYNombre(unittest.TestCase):
    def test_proyecto_nuevo_no_arrastra_la_plantilla(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            _, p = create("Nuevo", L("ts4_topografia.json"), projects_dir=Path(tmp))
        for key in TEMPLATE_CONTENT_KEYS:
            self.assertNotIn(key, p)
        self.assertNotIn("stale_template_data", codes(p))

    def test_nombre_del_rotulo_del_unifilar(self):
        text = "TS AUX 1\nDE TGBT - -QF10 T2S 160 PR221DS-LS 160A\n-WC9 - 3x50+PE25 mm² Cu PVC - L = 94 m\n"
        board = detect_board(text)
        self.assertEqual(board["title"], "TS AUX 1")
        self.assertEqual(board["feeder"]["upstreamTag"], "QF10")
        self.assertEqual(board["feeder"]["peMm2"], 25)
        self.assertIsNone(detect_board("-QF1\nS204-C20\n"))
        p = project([], project="TA-1")
        self.assertTrue(any(f["code"] == "board_name_mismatch" for f in audit(p, CAT, board_title="TS AUX 1")))


class ListaDeCompra(unittest.TestCase):
    def test_ot_pide_manija(self):
        p = project([dict(dev("QS1", "OT160EV03", "abb.ot160_250e03.3p.front", evidence="SECCIONADOR"), x=0, y=0)])
        rows = build_bom(p, CAT)
        self.assertTrue(any(r["category"] == "Accionamiento OT" for r in rows))

    def test_barra_de_neutro_no_reparte_fases(self):
        cat = L("accesorios_abb.json")
        devs = [dict(dev("QS1", "OT200E04", "abb.ot160_250e04.4p.front", evidence="SECCIONADOR"), x=10, y=300),
                dict(dev("QF1", "XT1B 160 TMD 80-800", "abb.tmax.xt1.4p.fixed.front", "A-1"), x=10, y=100, marking={"In": "80"})]
        for a in propose(project(devs), cat):
            self.assertNotEqual(a.get("catalogId"), "abb-aa8010")

    def test_bloques_de_otras_marcas_nunca_se_proponen(self):
        cat = L("accesorios_abb.json")
        devs = [dict(dev("QS1", "OT100F4", "abb.ot100_125f4.4p.front", evidence="SECCIONADOR"), x=10, y=300, marking={"In": "100"}),
                dict(dev("QF1", "S804S-C80", "abb.s804n.4p.front", "A-1"), x=10, y=100, marking={"In": "80"})]
        p = project(devs)
        for a in propose(p, cat):
            if a["type"] in ("distribution_block", "copper_busbar") and a.get("catalogId"):
                item = next(x for x in cat["distributionBlocks"] + cat["distributionBars"] if x["id"] == a["catalogId"])
                self.assertIn("ABB", item.get("marca", "ABB"))


if __name__ == "__main__":
    unittest.main()
