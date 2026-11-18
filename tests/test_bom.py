"""La lista de materiales no debe inducir una compra errónea."""
import json
import unittest
from pathlib import Path

from bom import MISSING, _strips, bom_issues, build_bom
from layout_auto import autolayout_conforme

ROOT = Path(__file__).resolve().parents[1]
CAT = json.loads((ROOT / "datos" / "catalogo_abb.json").read_text(encoding="utf-8"))


def ts4(**marks):
    p = json.loads((ROOT / "datos" / "ts4_topografia.json").read_text(encoding="utf-8"))
    for d in p["devices"]:
        if d.get("circuit") in marks:
            d.setdefault("marking", {})["In"] = marks[d["circuit"]]
    new, _ = autolayout_conforme(p, CAT)
    return new


class Peines(unittest.TestCase):
    def test_grupo_mas_largo_que_el_peine_pide_mas_piezas_y_un_solo_renglon(self):
        p = {"project": "x", "enclosure": {"id": "sr2-srn6420k", "mountingLayout": {"dinRails": []}}, "devices": [],
             "accessories": [{"type": "comb", "orderCode": "2CDL220001R1012", "catalogId": "abb-ps2", "poleCount": 14, "quantity": 3, "devices": ["QF1"], "bomCategory": "Peine", "description": "Peine PS2, equipos: QF1"},
                             {"type": "comb", "orderCode": "2CDL220001R1012", "catalogId": "abb-ps2", "poleCount": 4, "quantity": 1, "devices": ["QF2"], "bomCategory": "Peine", "description": "Peine PS2, equipos: QF2"}]}
        rows = [r for r in build_bom(p, CAT) if r["category"] == "Peine"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["quantity"], 4)

    def test_cantidad_de_piezas_segun_pines(self):
        from accesorios import _describe, load_accessory_catalog
        item = {"type": "comb", "catalogId": "abb-ps2", "poleCount": 14, "devices": ["a"]}
        _describe(item, load_accessory_catalog())
        self.assertEqual(item["quantity"], 2)  # PS2/12: 12 pines por pieza


class Despiece(unittest.TestCase):
    def test_tiras_first_fit(self):
        self.assertEqual(len(_strips([1130, 1130, 650, 650], 2000)), 2)
        self.assertEqual(len(_strips([650, 650, 650], 2000)), 1)
        self.assertEqual(len(_strips([1990, 20], 2000)), 2)


class SinErroresDeCompra(unittest.TestCase):
    def setUp(self):
        self.p = ts4(TSMAQ2=80)
        self.rows = build_bom(self.p, CAT)

    def test_gabinete_una_sola_vez_y_sin_placa_aparte(self):
        enc = self.p["enclosure"]["id"]
        codes = [r["code"] for r in self.rows]
        self.assertEqual(sum(1 for r in self.rows if r["category"] == "Envolvente"), 1)
        self.assertFalse(any(c.startswith("PF") for c in codes), "la placa viene incluida en el SR2 con puerta ciega")
        self.assertFalse(any(" / " in c for c in codes), "no debe quedar un menú de opciones como código")

    def test_ningun_codigo_repetido_ni_id_interno(self):
        codes = [r["code"] for r in self.rows if r["code"] != MISSING]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertFalse(any("_" in c or c.islower() for c in codes))

    def test_cantidades_y_unidades(self):
        for r in self.rows:
            self.assertIsInstance(r["quantity"], int)
            self.assertGreater(r["quantity"], 0)
            self.assertTrue(r["unit"])

    def test_todos_los_equipos_del_tablero(self):
        self.assertEqual(sum(r["quantity"] for r in self.rows if r["category"] == "Equipo"), len(self.p["devices"]))

    def test_canaletas_en_tiras_alcanzan_para_los_cortes(self):
        ducts = [a for a in self.p["accessories"] if a["type"] == "wiring_duct"]
        for r in (r for r in self.rows if r["category"] == "Canaleta"):
            total = sum(a["lengthMm"] for a in ducts if a["orderCode"] == r["code"])
            self.assertGreaterEqual(r["quantity"] * 2000, total)

    def test_kit_kd_con_paneles_y_sin_paneles_ciegos_sobre_cajas_moldeadas(self):
        cats = {r["code"]: r for r in self.rows}
        self.assertIn("KD1280K", cats)
        self.assertIn("PM1836K", cats)
        self.assertNotIn("PC1806K", cats)  # las filas libres las ocupan las XT montadas en placa

    def test_equipos_no_dibujados_van_a_la_lista_y_se_avisan(self):
        p = dict(self.p)
        p["devicesNotDrawn"] = [{"tag": "QS9", "model": "OT100F4", "poles": 4, "status": "serie sin carcasa en el catálogo"}]
        rows = build_bom(p, CAT)
        nd = [r for r in rows if r["category"] == "Equipo (no dibujado)"]
        self.assertEqual(len(nd), 1)
        self.assertIn("OT100F4", nd[0]["description"])
        self.assertTrue(any("no están en el dibujo" in t for t in bom_issues(rows, p)))

    def test_codigo_cargado_por_el_usuario(self):
        p = json.loads(json.dumps(self.p))
        for d in p["devices"]:
            if d["model"].startswith("XT1C"):
                d["orderCode"] = "1SDA067415R1"
        rows = build_bom(p, CAT)
        self.assertTrue(any(r["code"] == "1SDA067415R1" and r["quantity"] == 6 for r in rows))

    def test_tablero_todo_din_con_kit_pide_paneles_ciegos(self):
        p = {"project": "x", "enclosure": {"id": "sr2-srn6420k", "mountingLayout": {"dinRails": [{"id": "DIN-1", "kdKit": "KD6040K", "length": 245}]}},
             "devices": [], "accessories": []}
        codes = {r["code"]: r["quantity"] for r in build_bom(p, CAT)}
        self.assertEqual(codes.get("PM1414K"), 1)
        self.assertEqual(codes.get("PC1406K"), 2)

    def test_riel_libre_cortado(self):
        p = {"project": "x", "enclosure": {"id": "sr2-srn3415k", "mountingLayout": {"dinRails": [{"id": "DIN-1", "length": 280, "cutFromMm": 400}]}},
             "devices": [], "accessories": []}
        rail = next(r for r in build_bom(p, CAT) if r["category"] == "Montaje DIN")
        self.assertEqual(rail["code"], "GD4006")
        self.assertIn("cortar a 280 mm", rail["description"])


class CodigosDePedido(unittest.TestCase):
    CODES = {"items": [{"model": "S201L-C16NA", "poles": 2, "orderCode": "2CDS241801R0164", "descripcion": "S200L 1P+N C 16 A", "source": "x"},
                       {"model": "OT160EV03", "poles": 3, "orderCode": "1SCA120509R1001", "descripcion": "OT", "source": "x", "note": "No incluye manija ni eje"}],
             "sinVerificar": [{"model": "OT100F4", "motivo": "definir variante"}]}

    def bom(self, devices, not_drawn=()):
        p = {"project": "x", "enclosure": {"id": "sr2-srn6420k", "mountingLayout": {"dinRails": []}}, "devices": devices,
             "devicesNotDrawn": list(not_drawn), "accessories": []}
        return build_bom(p, CAT, order_codes=self.CODES)

    def test_modelo_conocido_toma_el_codigo_verificado(self):
        row = next(r for r in self.bom([{"tag": "QF1", "model": "S201L-C16 NA", "poles": 2}]) if r["category"] == "Equipo")
        self.assertEqual(row["code"], "2CDS241801R0164")

    def test_otra_cantidad_de_polos_no_hereda_el_codigo(self):
        row = next(r for r in self.bom([{"tag": "QF1", "model": "S201L-C16 NA", "poles": 4}]) if r["category"] == "Equipo")
        self.assertEqual(row["code"], MISSING)

    def test_nota_de_compra_y_variante_sin_definir(self):
        rows = self.bom([], [{"tag": "QS1", "model": "OT160EV03", "poles": 3}, {"tag": "QS2", "model": "OT100F4", "poles": 4}])
        ot160 = next(r for r in rows if "OT160" in r["description"])
        self.assertIn("manija", ot160["description"])
        ot100 = next(r for r in rows if "OT100" in r["description"])
        self.assertEqual(ot100["code"], MISSING)
        self.assertIn("definir variante", ot100["description"])

    def test_codigo_del_usuario_tiene_prioridad(self):
        row = next(r for r in self.bom([{"tag": "QF1", "model": "S201L-C16 NA", "poles": 2, "orderCode": "MIO123"}]) if r["category"] == "Equipo")
        self.assertEqual(row["code"], "MIO123")

    def test_catalogo_real_sin_codigos_inventados(self):
        from bom import load_order_codes
        data = load_order_codes()
        for item in data["items"]:
            self.assertTrue(item["source"].startswith("http"), item["model"])
            self.assertRegex(item["orderCode"], r"^[0-9A-Z]{10,16}$", item["model"])


class PeinesMismoCodigo(unittest.TestCase):
    def test_tramos_del_mismo_peine_en_un_renglon(self):
        acc = [{"type": "comb", "orderCode": "2CDL220001R1012", "poleCount": n, "quantity": q, "devices": [f"QF{n}"], "bomCategory": "Peine",
                "description": f"Peine de conexión PS2/12 (12 pines por pieza) para {n} polos (paso 17.5 mm), equipos: QF{n}"} for n, q in ((14, 2), (6, 1))]
        p = {"project": "x", "enclosure": {"id": "sr2-srn6420k", "mountingLayout": {"dinRails": []}}, "devices": [], "accessories": acc}
        rows = [r for r in build_bom(p, CAT) if r["category"] == "Peine"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["quantity"], 3)
        self.assertIn("2×14", rows[0]["description"])


class GabineteDeEstructura(unittest.TestCase):
    def test_system_pro_e_sin_renglon_duplicado_y_codigos_separados(self):
        p = json.loads((ROOT / "datos" / "ts4_topografia.json").read_text(encoding="utf-8"))
        rows = build_bom(p, CAT)
        codes = [r["code"] for r in rows]
        self.assertNotIn("PUPM2100", codes)  # es el mismo artículo que 1STQ007035A0000 (montantes)
        self.assertIn("1STQ007035A0000", codes)
        self.assertTrue(all("+" not in c for c in codes))
        self.assertIn("PDLB1127", codes)
        self.assertIn("PDNB1507", codes)
        lateral = next(r for r in rows if "lateral" in r["description"].lower())
        self.assertEqual(lateral["quantity"], 2)


if __name__ == "__main__":
    unittest.main()
