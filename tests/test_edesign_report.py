"""Pruebas del importador de informes completos ABB e-Design DOC, series Formula A1 / S261-S281
y control de canaletas en layout_auto._conforme_loop."""
import json
import unittest
from pathlib import Path

import auditoria
import bom
import importador
import layout_auto

ROOT = Path(__file__).resolve().parent.parent
CATALOG = json.loads((ROOT / "datos" / "catalogo_abb.json").read_text(encoding="utf-8"))


class SeriesNuevasYCorriente(unittest.TestCase):
    def test_formula_a1_4p_y_3p_en_catalogo_y_corriente(self):
        s4, sh4, err4 = importador.find_series("A1C 125 TMF 70-700", 4, CATALOG)
        self.assertIsNone(err4)
        self.assertEqual(s4["id"], "formula-a1-4p")
        self.assertEqual((sh4["width"], sh4["height"]), (101.6, 130))
        self.assertEqual(auditoria.rated_current({"model": "A1C 125 TMF 70-700"}, CATALOG["importRules"]), 70.0)

        s3, sh3, err3 = importador.find_series("A1C 125 TMF 80-800", 3, CATALOG)
        self.assertIsNone(err3)
        self.assertEqual(s3["id"], "formula-a1-3p")
        self.assertEqual((sh3["width"], sh3["height"]), (76.2, 130))
        self.assertEqual(auditoria.rated_current({"model": "A1C 125 TMF 80-800"}, CATALOG["importRules"]), 80.0)

    def test_s261_s271_s281_1pn_en_catalogo(self):
        for model in ("S 261-C 20 NA", "S 271 Na C 10", "S 271 Na C 16", "S 281-B 16 NA"):
            s, sh, err = importador.find_series(model, 2, CATALOG)
            self.assertIsNone(err, model)
            self.assertEqual(s["id"], "s260-280-na", model)
            self.assertEqual(sh["id"], "abb.s200m.1pn.front", model)

    def test_bom_estado_codigo_edesign(self):
        proj = {
            "project": "Test",
            "enclosure": CATALOG["enclosures"][10],
            "devices": [
                {"tag": "QF1", "circuit": "C-1", "model": "A1C 125 TMF 70-700", "poles": 4,
                 "shell": "abb.tmax.xt1.4p.fixed.front", "orderCode": "1SDA066752R1", "orderCodeSource": "edesign"},
            ],
            "accessories": [],
        }
        rows = bom.build_bom(proj, CATALOG)
        eq = next(r for r in rows if r["category"] == "Equipo")
        self.assertEqual(eq["code"], "1SDA066752R1")
        self.assertEqual(eq["status"], "código del informe e-Design")

    def test_bom_prioriza_codigo_verificado_sobre_legado_edesign(self):
        proj = {
            "project": "Test",
            "enclosure": CATALOG["enclosures"][10],
            "devices": [
                {"tag": "QF1", "circuit": "C-1", "model": "S201L-C10 NA", "poles": 2,
                 "shell": "abb.s200m.1pn.front", "orderCode": "S598378", "orderCodeSource": "edesign"},
                {"tag": "QF2", "circuit": "C-2", "model": "S201L-C10 NA", "poles": 2,
                 "shell": "abb.s200m.1pn.front", "orderCode": "2CDS241801R0104", "orderCodeSource": "edesign"},
            ],
            "accessories": [],
        }
        rows = bom.build_bom(proj, CATALOG)
        eqs = [r for r in rows if r["category"] == "Equipo"]
        self.assertEqual(len(eqs), 1)
        self.assertEqual(eqs[0]["code"], "2CDS241801R0104")
        self.assertEqual(eqs[0]["quantity"], 2)
        self.assertEqual(eqs[0]["status"], "verificado")

    def test_marcado_formula_a1_y_s271_na(self):
        fa1 = importador.marking_fields("A1C 125 TMF 70-700", "", CATALOG["importRules"])
        self.assertEqual(fa1["family"], "FORMULA")
        self.assertEqual(fa1["serie"], "A1C")
        self.assertEqual(fa1["In"], "70")

        s271 = importador.marking_fields("S 271 Na C 10", "", CATALOG["importRules"])
        self.assertEqual(s271["serieS"], "S 271")
        self.assertEqual(s271["sufijoGuion"], "-NA")
        self.assertEqual(s271["curva"], "C")
        self.assertEqual(s271["In"], "10")

    def test_bomba_principal_no_roba_el_general_de_entrada(self):
        """Lección 42: un circuito de salida cuya descripción dice 'Bomba principal 1' no puede ser main_device."""
        proj = {
            "devices": [
                {"tag": "QD137", "circuit": None, "model": "F204 AC-63/0,03", "evidence": "F204 AC-63/0,03 TSB"},
                {"tag": "QF58", "circuit": "TSB-1.3", "model": "S 293-C 80", "evidence": "S 293-C 80 TSB-1.3 Bomba principal 1"},
            ]
        }
        self.assertEqual(auditoria.main_device(proj)["tag"], "QD137")

    def test_bom_generica_sin_marcas_y_detallada(self):
        import excel_equipamiento
        proj = {
            "project": "Tablero Prueba",
            "enclosure": CATALOG["enclosures"][10],
            "devices": [
                {"tag": "QD1", "circuit": None, "model": "F204 AC-40/0,03", "poles": 4, "shell": "abb.f204.4p.front", "x": 10, "y": 100, "w": 70, "h": 88},
                {"tag": "QF1", "circuit": "C-1", "model": "S201L-C16 NA", "poles": 2, "shell": "abb.s200m.1pn.front",
                 "marking": {"curva": "C", "In": "16", "kA": "6"}, "x": 80, "y": 100, "w": 35, "h": 88},
                {"tag": "QF2", "circuit": "C-2", "model": "S201-C16 NA", "poles": 2, "shell": "abb.s200m.1pn.front", "x": 115, "y": 100, "w": 35, "h": 88},
                {"tag": "QF3", "circuit": "C-3", "model": "A1C 125 TMF 70-700", "poles": 4, "shell": "abb.tmax.xt1.4p.fixed.front", "x": 10, "y": 220, "w": 101.6, "h": 130},
                {"tag": "QF4", "circuit": "C-4", "model": "S804S-C50", "poles": 4, "shell": "abb.s804n.4p.front", "x": 150, "y": 100, "w": 106, "h": 95},
                {"tag": "QF0", "circuit": "Main", "model": "E2.2N 2000 Ekip Dip LI 2000", "poles": 4, "shell": "abb.emax2.e22.4p.fixed.front", "x": 10, "y": 400, "w": 366, "h": 371},
            ],
            "accessories": [],
        }
        rows = bom.build_bom(proj, CATALOG, mode="generic")
        self.assertEqual(bom.bom_issues(rows, proj), [])
        enc_row = next(r for r in rows if r["category"] == "Envolvente")
        self.assertRegex(enc_row["description"], r"^Gabinete de chapa de acero · alto \d+ × ancho \d+ × prof\. \d+ mm$")
        for r in rows:
            self.assertEqual(r["code"], "")
            self.assertNotIn("ABB", r["description"])
            self.assertNotIn("S201", r["description"])
            self.assertNotIn("A1C", r["description"])
            self.assertNotIn("extraíble", r["description"].lower())
            self.assertNotIn("extraíble", r["status"].lower())
        descs = {r["description"]: r["quantity"] for r in rows if r["category"] == "Equipo"}
        # QF1 (6 kA por unifilar) y QF2 (S200 6 kA) tienen idéntica especificación técnica → se agrupan en 2 u
        self.assertEqual(descs["Interruptor termomagnético 1P+N, curva C, 16 A, 6 kA (riel DIN)"], 2)
        self.assertEqual(descs["Interruptor diferencial 4P, 40 A, 30 mA, clase AC (riel DIN)"], 1)
        self.assertEqual(descs["Interruptor en caja moldeada (MCCB) 4P, marco 125 A, In 70 A, disparador termomagnético fijo (TMF), 25 kA"], 1)
        self.assertEqual(descs["Interruptor termomagnético de alta capacidad 4P, curva C, 50 A, 50 kA (riel DIN)"], 1)
        self.assertEqual(descs["Interruptor automático abierto (ACB) 4P fijo, marco 2000 A, In 2000 A, relé electrónico LI, 66 kA"], 1)
        xlsx = excel_equipamiento.build_xlsx({"Tablero Prueba": proj}, CATALOG, mode="generic")
        self.assertGreater(len(xlsx), 2000)


class CanaletaEnAutolayoutConforme(unittest.TestCase):
    def test_no_acepta_gabinete_sin_canaleta_abajo(self):
        """Reproduce el caso TSMAQ2 (S803N-C40 de 95 mm + 2×S203): en SRN3415K no entra canaleta
        abajo de la fila, así que autolayout_conforme debe pasar al gabinete siguiente."""
        proj = {
            "project": "TSMAQ2",
            "enclosure": CATALOG["enclosures"][0],
            "devices": [
                {"tag": "QF160", "circuit": "TSMAQ2-1.1", "model": "S803N-C40", "poles": 3,
                 "shell": "abb.s803.3p.front", "w": 81, "h": 95, "x": 0, "y": 0},
                {"tag": "QF161", "circuit": "TSMAQ2-1.2", "model": "S203-Z40", "poles": 3,
                 "shell": "abb.s200m.1p.front", "w": 52.5, "h": 88, "x": 0, "y": 0},
                {"tag": "QF162", "circuit": "TSMAQ2-1.3", "model": "S203-Z25", "poles": 3,
                 "shell": "abb.s200m.1p.front", "w": 52.5, "h": 88, "x": 0, "y": 0},
            ],
            "accessories": [],
        }
        new, _summary = layout_auto.autolayout_conforme(proj, CATALOG)
        errs = [f["code"] for f in auditoria.audit(new, CATALOG, board_title="TSMAQ2") if f["level"] == "error"]
        self.assertNotIn("row_without_duct_below", errs)
        self.assertNotIn("row_without_duct_above", errs)
        self.assertEqual(errs, [])


class InformeEdesignMultiTablero(unittest.TestCase):
    def test_unifilar_autocad_simple_devuelve_none(self):
        sample = next((ROOT / "tests" / "unifilares").glob("*.pdf"), None)
        if sample is None:
            self.skipTest("sin PDF de unifilar simple en tests/unifilares")
        self.assertIsNone(importador.detect_edesign_report(sample.read_bytes(), CATALOG))

    def test_informe_edesign_sintetico_dos_tableros(self):
        import pymupdf
        doc = pymupdf.open()
        # Página 1: TGBT (-B1) con -QF1 (general) y -QF2 (alimenta TSAA)
        p1 = doc.new_page(width=595, height=842)
        p1.insert_text((140, 424), "TGBT", fontsize=8)
        p1.insert_text((488, 383), "-B1", fontsize=8)
        p1.insert_text((143, 393), "-QF1", fontsize=8)
        p1.insert_text((163, 393), "-QF2", fontsize=8)
        # Página 2: TSAA (-B2) con -QD144 arriba de barra y -QF31 abajo
        p2 = doc.new_page(width=595, height=842)
        p2.insert_text((56, 242.3), "TSAA", fontsize=8)
        p2.insert_text((56, 249.4), "-QD144", fontsize=8)
        p2.insert_text((113, 261.4), "-B2", fontsize=8)
        p2.insert_text((77, 268.4), "-QF31", fontsize=8)
        # Página 3: Informe de cables / protecciones
        p3 = doc.new_page(width=595, height=842)
        for idx, line in enumerate([
            "Overload: OK", "-QF1", "18x(1x300)+6x(1x150)+6G150", "LLLN / TN-S", "Alimentacion Principal", "-WC119",
            "Overload: OK", "-QF2", "3x(1x16)+1x(1x16)+1G16", "LLLN / TN-S", "TSAA", "-WC1",
            "Overload: OK", "-QF31", "2x(1x4)+1G4", "LN / TN-S", "TSAA-1.1", "-WC30",
        ]):
            p3.insert_text((30, 40 + idx * 14), line, fontsize=8)
        # Página 4: Lista de aparatos de BT
        p4 = doc.new_page(width=595, height=842)
        p4.insert_text((240, 40), "Lista de aparatos de BT", fontsize=9)
        rows = [
            ("-QF1", "1SDA071661R1", "E2.2N 2000 Ekip Dip LI 2000", "Alimentacion Principal"),
            ("-QF2", "1SDA066752R1", "A1C 125 TMF 70-700", "TSAA"),
            ("-QD144", "2CSF202001R1250", "F202 AC-25/0,03", "TSAA"),
            ("-QF31", "2CDS241801R0164", "S201L-C16 NA", "TSAA-1.1"),
        ]
        for idx, (tag, code, model, desc1) in enumerate(rows):
            y = 80 + idx * 14
            p4.insert_text((26, y), tag, fontsize=7)
            p4.insert_text((77, y), code, fontsize=7)
            p4.insert_text((142, y), model, fontsize=7)
            p4.insert_text((356, y), desc1, fontsize=7)
        pdf_bytes = doc.tobytes()
        doc.close()

        rep = importador.detect_edesign_report(pdf_bytes, CATALOG)
        self.assertIsNotNone(rep)
        self.assertTrue(rep["multiBoard"])
        self.assertEqual(len(rep["boards"]), 2)
        self.assertEqual(rep["totalDevices"], 4)
        self.assertEqual(rep["unmatchedApparatus"], [])

        tgbt, tsaa = rep["boards"]
        self.assertEqual(tgbt["title"], "TGBT")
        self.assertEqual(tgbt["feeder"]["peMm2"], 150.0)
        self.assertEqual(tgbt["feeder"]["peParallel"], 6)
        self.assertIsNone(tgbt["devices"][0]["circuit"])  # general QF1 sin circuito largo
        self.assertEqual(tsaa["title"], "TSAA")
        self.assertEqual(tsaa["feeder"]["from"], "TGBT")
        self.assertEqual(tsaa["feeder"]["peMm2"], 16.0)
        self.assertEqual([d["tag"] for d in tsaa["devices"]], ["QD144", "QF31"])
        self.assertEqual([d["poles"] for d in tsaa["devices"]], [2, 2])


if __name__ == "__main__":
    unittest.main()
