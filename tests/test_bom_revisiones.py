import unittest

from bom import build_bom, to_csv
from revisiones import add_revision


CATALOG = {"enclosures": [{"id": "enc", "label": "Gabinete ABB", "source": "abb", "structure": {"status": "catálogo", "source": "abb", "bom": [{"parte": "Montantes (x4)", "codigo": "M", "orden": "ORD-M"}]}}],
           "deviceShells": [{"id": "s200", "label": "S200", "cadSource": "cad"}]}
PROJECT = {"project": "T", "enclosure": {"id": "enc", "mountingLayout": {"dinRails": [{"type": "R", "orderCode": "ORD-R", "length": 600}]}},
           "devices": [{"tag": "Q1", "model": "S202 C10", "shell": "s200", "poles": 2, "status": "verificado"}, {"tag": "Q2", "model": "S202 C10", "shell": "s200", "poles": 2, "status": "verificado"}], "accessories": []}


class BomRevisiones(unittest.TestCase):
    def test_bom_agrupa_equipos_y_cantidades_estructurales(self):
        rows = build_bom(PROJECT, CATALOG)
        equipment = next(row for row in rows if row["category"] == "Equipo")
        structure = next(row for row in rows if row["category"] == "Envolvente (estructura)")
        self.assertEqual((equipment["quantity"], equipment["tags"]), (2, "Q1, Q2"))
        self.assertEqual(structure["quantity"], 4)

    def test_csv_es_compatible_con_excel_en_espanol(self):
        data = to_csv(build_bom(PROJECT, CATALOG))
        self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
        self.assertIn(b";", data)

    def test_revision_incremental_no_modifica_original(self):
        first, item0 = add_revision(PROJECT, "Emisión inicial", "Thomas")
        second, item1 = add_revision(first, "Cambio de gabinete", "Thomas")
        self.assertEqual((item0["code"], item1["code"]), ("0", "1"))
        self.assertNotIn("revisions", PROJECT)
        self.assertEqual(second["currentRevision"], "1")

    def test_revision_exige_descripcion(self):
        with self.assertRaises(ValueError):
            add_revision(PROJECT, "  ")


if __name__ == "__main__":
    unittest.main()
