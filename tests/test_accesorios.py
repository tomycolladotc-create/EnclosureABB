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
    return {"devices": devices, "enclosure": {"functional": {"width": 560, "height": 1160, "depth": 300}, "mountingLayout": {"dinRails": [rail]}}}


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


    def test_corriente_alta_propone_barra_de_cobre_y_espera_decision(self):
        p = complete(project([s200("QF1", 200, 3, "250")]))
        bar = next(a for a in p["accessories"] if a["type"] == "copper_busbar")
        self.assertTrue(bar["needsConfirmation"])
        self.assertIsNone(bar["decision"])
        self.assertEqual(bar["catalogId"], "abb-aa8010")
        self.assertLessEqual(bar["x"] + bar["w"], 560)  # entra en la placa

    def test_la_decision_del_usuario_se_conserva_al_recalcular(self):
        p = complete(project([s200("QF1", 200, 3, "250")]))
        next(a for a in p["accessories"] if a["type"] == "copper_busbar")["decision"] = "confirmed"
        complete(p)
        self.assertEqual(next(a for a in p["accessories"] if a["type"] == "copper_busbar")["decision"], "confirmed")

    def test_corriente_mayor_que_toda_barra_del_catalogo_no_inventa_barra(self):
        p = complete(project([s200("QF1", 200, 3, "630")]))
        item = next(a for a in p["accessories"] if a["type"] == "distribution_block")
        self.assertFalse(item["placed"])
        self.assertIn("dimensionar", item["note"])

    def test_el_peine_de_s800_no_sube_el_limite_de_los_s200(self):
        p = complete(project([s200("QF1", 200, 3, "80")]))  # 80 A > 63 A (peines S200); el S803-BB250 de 250 A no cuenta
        self.assertTrue([a for a in p["accessories"] if a["type"] == "distribution_block"])


if __name__ == "__main__":
    unittest.main()


class PolosYSolape(unittest.TestCase):
    def test_polos_de_la_carcasa_si_falta_el_dato(self):
        from accesorios import _poles
        self.assertEqual(_poles({"shell": "abb.s200m.1pn.front"}), 2)
        self.assertEqual(_poles({"shell": "abb.s200.3p.front"}), 3)
        self.assertEqual(_poles({"shell": "abb.s200.3p.front", "poles": 4}), 4)
        self.assertIsNone(_poles({"shell": "abb.s804n.front"}))

    def test_bloque_no_pisa_los_bornes_pe(self):
        import json
        from layout_auto import autolayout
        L = lambda n: json.load(open(ROOT / "datos" / n, encoding="utf-8"))
        base = L("ts4_topografia.json")
        for d in base["devices"]:
            if d["tag"].startswith("QF8") and "xt" in d["shell"]:
                d["marking"] = {**d.get("marking", {}), "In": "80"}  # corriente alta: obliga a proponer bloque de distribución
        new, _ = autolayout(base, L("catalogo_abb.json"))
        complete(new)
        pe = next(a for a in new["accessories"] if a["type"] == "pe_terminal")
        blk = next(a for a in new["accessories"] if a["type"] == "distribution_block")
        self.assertTrue(pe.get("placed") and blk.get("placed"))
        if True:
            self.assertTrue(pe["x"] + pe["w"] <= blk["x"] + 1e-6 or blk["x"] + blk["w"] <= pe["x"] + 1e-6)


class CanaletasYPeines(unittest.TestCase):
    def setUp(self):
        from layout_auto import autolayout
        self.L = lambda n: json.load(open(ROOT / "datos" / n, encoding="utf-8"))
        self.acc_cat = self.L("accesorios_abb.json")
        self.layouts = {}
        for free in (False, True):
            new, _ = autolayout(self.L("ts4_topografia.json"), self.L("catalogo_abb.json"), free_rails=free)
            complete(new)
            self.layouts[free] = new

    def test_canaletas_usan_secciones_y_codigos_del_catalogo(self):
        sections = {(s["widthMm"], s["heightMm"]): {s["code8x12"], s["code4x6"]} for s in self.acc_cat["wiringDucts"]["sections"]}
        for new in self.layouts.values():
            ducts = [a for a in new["accessories"] if a["type"] == "wiring_duct"]
            self.assertTrue(ducts)
            for d in ducts:
                self.assertIn(d["orderCode"], sections[(d["sectionMm"], d["depthMm"])])
                self.assertEqual(d["sectionMm"], d["w"] if d["orientation"] == "v" else d["h"])

    def test_criterio_armador_verticales_y_filas(self):
        """Ejemplo de Thomas: verticales a los lados y horizontales arriba y abajo de cada fila, de vertical a vertical."""
        for new in self.layouts.values():
            ducts = [a for a in new["accessories"] if a["type"] == "wiring_duct"]
            vert = [a for a in ducts if a["orientation"] == "v"]
            hor = [a for a in ducts if a["orientation"] == "h"]
            fw = new["enclosure"]["functional"]["width"]
            if len(vert) == 2:
                left, right = sorted(vert, key=lambda a: a["x"])
                for h in hor:
                    self.assertAlmostEqual(h["x"], left["x"] + left["w"], places=1)
                    self.assertAlmostEqual(h["x"] + h["w"], right["x"], places=1)
            # cada fila de equipos tiene una canaleta horizontal arriba o abajo a menos de 60 mm
            for d in new["devices"]:
                near = [h for h in hor if 0 <= d["y"] - (h["y"] + h["h"]) <= 60 or 0 <= h["y"] - (d["y"] + d["h"]) <= 60]
                self.assertTrue(near, d["tag"])
            self.assertTrue(all(25 <= a["sectionMm"] <= 80 for a in ducts))

    def test_canaletas_no_pisan_equipos_ni_salen_de_la_placa(self):
        for new in self.layouts.values():
            fun = new["enclosure"]["functional"]
            boxes = [(d["x"], d["y"], d["w"], d["h"], d["tag"]) for d in new["devices"]]
            boxes += [(a["x"], a["y"], a["w"], a["h"], a["type"]) for a in new["accessories"] if a.get("placed") and a["type"] != "wiring_duct" and a.get("w")]
            for a in (a for a in new["accessories"] if a["type"] == "wiring_duct"):
                self.assertGreaterEqual(a["y"], 0)
                self.assertLessEqual(a["y"] + a["h"], fun["height"])
                self.assertLessEqual(a["x"] + a["w"], fun["width"] + 1e-6)
                for x, y, w, h, name in boxes:
                    clash = a["x"] < x + w and x < a["x"] + a["w"] and a["y"] < y + h and y < a["y"] + a["h"]
                    self.assertFalse(clash, f"canaleta pisa {name}")

    def test_peine_apoyado_sobre_equipos_y_con_clavija_por_polo(self):
        new = self.layouts[True]
        comb = next(a for a in new["accessories"] if a["type"] == "comb")
        devs = [d for d in new["devices"] if d["tag"] in comb["devices"]]
        self.assertAlmostEqual(comb["y"], max(d["y"] + d["h"] for d in devs))
        self.assertGreater(comb["h"], 10)
        self.assertEqual(comb["poleCount"], round(comb["w"] / comb["pitchMm"]))

    def test_dxf_trae_capas_de_canaletas_y_peines(self):
        import cad_export, ezdxf
        from io import StringIO
        data = cad_export.build_dxf(self.layouts[True], self.L("catalogo_abb.json"), self.L("frentes_cad.json"), self.L("apariencias_abb.json"))
        layers = [e.dxf.layer for e in ezdxf.read(StringIO(data.decode("utf-8"))).modelspace()]
        self.assertGreaterEqual(layers.count("ABB_CANALETAS"), 3)  # rectángulo + 2 líneas de la tapa por canaleta
        self.assertGreater(layers.count("ABB_PEINES"), 4)


class CircuitosYComputo(unittest.TestCase):
    def setUp(self):
        from layout_auto import autolayout
        self.L = lambda n: json.load(open(ROOT / "datos" / n, encoding="utf-8"))
        self.new, _ = autolayout(self.L("ts4_topografia.json"), self.L("catalogo_abb.json"), free_rails=True)
        complete(self.new)

    def test_importador_extrae_el_circuito(self):
        from importador import circuit_name
        self.assertEqual(circuit_name("QF82", "XT1C 160\nTMD 80-8003x25 mm² Cu\nOCE\nTS-4.2\nRSTN\n34,74"), "TS-4.2")
        self.assertEqual(circuit_name("QF163", "XT1C 160\nALIM\nTSMAQ2\nRSTN"), "TSMAQ2")
        self.assertEqual(circuit_name("QF125", "S201L-C10\nNA\nCu —\nTSEP-2\nT\n0,10"), "TSEP-2")  # sin código de uso
        self.assertIsNone(circuit_name("QS1", "OT160\nACU\nX-1"))
        self.assertIsNone(circuit_name("QF10", "T2S 160\nRST"))

    def test_dxf_rotula_con_el_circuito_y_sin_texto_de_accesorios(self):
        import cad_export, ezdxf
        from io import StringIO
        data = cad_export.build_dxf(self.new, self.L("catalogo_abb.json"), self.L("frentes_cad.json"), self.L("apariencias_abb.json"))
        ents = list(ezdxf.read(StringIO(data.decode("utf-8"))).modelspace())
        labels = [e.dxf.text for e in ents if e.dxftype() == "TEXT" and e.dxf.layer == "ABB_ETIQUETAS"]
        self.assertIn("TS-4.2", labels)
        self.assertNotIn("QF82", labels)
        for layer in ("ABB_ACCESORIOS", "ABB_CANALETAS", "ABB_PEINES"):
            self.assertEqual([e for e in ents if e.dxftype() == "TEXT" and e.dxf.layer == layer], [], layer)

    def test_computo_lista_accesorios_con_descripcion_y_cantidad(self):
        from bom import build_bom
        rows = build_bom(self.new, self.L("catalogo_abb.json"))
        cats = {r["category"] for r in rows}
        for want in ("Canaleta", "Peine", "Bornera de tierra (PE)", "Montaje DIN"):
            self.assertIn(want, cats)
        ducts = [r for r in rows if r["category"] == "Canaleta"]
        self.assertTrue(all("cortes:" in r["description"] and r["code"].startswith("1SL9") and r["unit"].startswith("tira") for r in ducts))
        pe = next(r for r in rows if r["category"] == "Bornera de tierra (PE)" and r["code"] == "1SNL312510R0000")
        self.assertEqual(pe["quantity"], -(-sum(1 for d in self.new["devices"] if d["tag"].startswith("QF")) // 7))
        equipos = [r for r in rows if r["category"] == "Equipo"]
        self.assertTrue(any("TS-4.2 (QF82)" in r["tags"] for r in equipos))


class AutoConfirmacion(unittest.TestCase):
    def test_complete_con_auto_confirm_deja_propuestas_confirmadas(self):
        import json
        from accesorios import complete
        from layout_auto import autolayout
        root = Path(__file__).resolve().parents[1]
        catalog = json.loads((root / "datos" / "catalogo_abb.json").read_text(encoding="utf-8"))
        project = json.loads((root / "datos" / "ts4_topografia.json").read_text(encoding="utf-8"))
        new, _ = autolayout(project, catalog)
        complete(new, auto_confirm=True)
        pend = [a for a in new["accessories"] if a.get("needsConfirmation") and a.get("decision") != "confirmed"]
        self.assertEqual(pend, [])


class CanaletasManuales(unittest.TestCase):
    def setUp(self):
        import json
        from layout_auto import autolayout_conforme
        root = Path(__file__).resolve().parents[1]
        self.catalog = json.loads((root / "datos" / "catalogo_abb.json").read_text(encoding="utf-8"))
        project = json.loads((root / "datos" / "ts4_topografia.json").read_text(encoding="utf-8"))
        self.project, _ = autolayout_conforme(project, self.catalog)

    def test_modo_manual_conserva_la_canaleta_y_no_propone_otras(self):
        from accesorios import complete
        p = self.project
        p["ductMode"] = "manual"
        p["accessories"] = [a for a in p["accessories"] if a["type"] != "wiring_duct"]
        p["accessories"].append({"type": "wiring_duct", "id": "duct-1", "manual": True, "orientation": "v",
                                 "sectionMm": 60, "depthMm": 60, "w": 60, "h": 700, "x": 10, "y": 100})
        complete(p, auto_confirm=True)
        ducts = [a for a in p["accessories"] if a["type"] == "wiring_duct"]
        self.assertEqual(len(ducts), 1)
        d = ducts[0]
        self.assertEqual((d["w"], d["h"], d["lengthMm"]), (60, 700, 700))
        self.assertTrue(d["orderCode"].startswith("1SL90"))
        self.assertIn("60x60", d["description"])

    def test_seccion_fuera_de_catalogo_se_rechaza(self):
        from accesorios import complete
        p = self.project
        p["accessories"].append({"type": "wiring_duct", "id": "x", "manual": True, "orientation": "h", "sectionMm": 33, "depthMm": 40, "w": 300, "h": 33, "x": 0, "y": 0})
        with self.assertRaises(ValueError):
            complete(p)

    def test_bom_y_dxf_con_canaleta_vertical(self):
        import ezdxf, io
        from accesorios import complete
        from bom import build_bom
        from cad_export import build_dxf
        p = self.project
        p["ductMode"] = "manual"
        p["accessories"] = [a for a in p["accessories"] if a["type"] != "wiring_duct"]
        p["accessories"].append({"type": "wiring_duct", "id": "duct-1", "manual": True, "orientation": "v", "sectionMm": 40, "depthMm": 40, "w": 40, "h": 500, "x": 5, "y": 200})
        complete(p, auto_confirm=True)
        rows = build_bom(p, self.catalog)
        self.assertTrue(any(r["category"] == "Canaleta" and "500 mm" in r["description"] for r in rows))
        import json
        root = Path(__file__).resolve().parents[1] / "datos"
        doc = build_dxf(p, self.catalog, json.loads((root / "frentes_cad.json").read_text(encoding="utf-8")), json.loads((root / "apariencias_abb.json").read_text(encoding="utf-8")))
        if isinstance(doc, (bytes, str)):
            doc = ezdxf.read(io.StringIO(doc.decode() if isinstance(doc, bytes) else doc))
        lines = [e for e in doc.modelspace() if e.dxf.layer == "ABB_CANALETAS" and e.dxftype() == "LINE"]
        self.assertTrue(any(abs(e.dxf.start.x - e.dxf.end.x) < 1e-6 and abs(e.dxf.start.y - e.dxf.end.y) > 400 for e in lines))



class BorneraEquipotencial(unittest.TestCase):
    def test_repartidores_pe_con_topes_y_salidas_suficientes(self):
        import json
        from accesorios import complete
        from layout_auto import autolayout_conforme
        from bom import build_bom
        root = Path(__file__).resolve().parents[1]
        cat = json.loads((root / "datos" / "catalogo_abb.json").read_text(encoding="utf-8"))
        project = json.loads((root / "datos" / "ts4_topografia.json").read_text(encoding="utf-8"))
        new, _ = autolayout_conforme(project, cat)
        pe = next(a for a in new["accessories"] if a["type"] == "pe_terminal")
        qf = sum(1 for d in new["devices"] if d["tag"].startswith("QF"))
        self.assertEqual(pe["style"], "repartidor")
        self.assertGreaterEqual(pe["count"], qf)
        self.assertEqual(pe["blocks"], -(-qf // 7))
        self.assertAlmostEqual(pe["w"], pe["blocks"] * 28.2 + 2 * 10)
        self.assertEqual(pe["h"], 75)
        rows = [r for r in build_bom(new, cat) if r["category"] == "Bornera de tierra (PE)"]
        codes = {r["code"]: r["quantity"] for r in rows}
        self.assertEqual(codes.get("1SNL312510R0000"), pe["blocks"])
        self.assertEqual(codes.get("1SNK900001R0000"), 2)
