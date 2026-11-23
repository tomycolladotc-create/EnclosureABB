"""Excel de equipamiento eléctrico (pedido de Thomas 2026-11-23: «que salga con un botón, con las mismas columnas»)."""
import io
import json
import unittest
from pathlib import Path

from openpyxl import load_workbook

from bom import build_bom
from excel_equipamiento import RULES, build_xlsx, unclassified
from regresion_general import BOARDS, build

ROOT = Path(__file__).resolve().parent.parent
CATALOG = json.loads((ROOT / "datos" / "catalogo_abb.json").read_text(encoding="utf-8"))


class ExcelEquipamiento(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.projects = {}
        for pdf in BOARDS[:6]:
            p = build(pdf)["project"]
            cls.projects[p.get("project") or pdf.stem] = p
        cls.wb = load_workbook(io.BytesIO(build_xlsx(cls.projects, CATALOG)))

    def test_todas_las_categorias_de_la_lista_estan_clasificadas(self):
        for pdf in BOARDS:
            with self.subTest(tablero=pdf.stem):
                self.assertEqual(unclassified(build_bom(build(pdf)["project"], CATALOG)), [])

    def test_columnas_pedidas(self):
        head = [c.value for c in self.wb["Equipamiento eléctrico"][1]]
        for col in ("Código", "Cantidad", "Circuitos", "Tableros"):
            self.assertIn(col, head)

    def test_sin_canalizaciones_ni_montaje(self):
        cats = {r[1] for r in self.wb["Equipamiento eléctrico"].iter_rows(min_row=2, values_only=True) if r[1]}
        self.assertFalse(cats & set(RULES["exclude"]), cats & set(RULES["exclude"]))

    def test_cantidad_es_formula_sobre_el_detalle(self):
        for r in self.wb["Equipamiento eléctrico"].iter_rows(min_row=2, values_only=True):
            self.assertTrue(str(r[4]).startswith("=SUMIFS('Detalle por tablero'"), r)

    def test_cada_tablero_figura(self):
        boards = {r[1] for r in self.wb["Detalle por tablero"].iter_rows(min_row=2, values_only=True)}
        self.assertEqual(boards, set(self.projects))
