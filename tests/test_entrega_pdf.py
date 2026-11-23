"""PDF único de entrega (pedido de Thomas 2026-11-23): carátula, índice, frentes y puertas, lista, rótulo y hojas numeradas."""
import json
import unittest
from pathlib import Path

import pymupdf

from app import resolved_drawing_data
from entrega_pdf import build_pdf, pick_scale
from regresion_general import BOARDS, build

CATALOG = json.loads((Path(__file__).resolve().parent.parent / "datos" / "catalogo_abb.json").read_text(encoding="utf-8"))
VALUES = {"proyecto": "Obra de prueba", "cliente": "Cliente X", "documento": "CLI-PL-1", "revision": "B", "fecha": "23/11/2026",
          "dibujo": "TC", "reviso": "RV", "aprobo": "AP"}


class EntregaPdf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        small = sorted(BOARDS, key=lambda p: p.stat().st_size)[:2]
        cls.projects = {}
        for pdf in small:
            p = build(pdf)["project"]
            cls.projects[p.get("project") or pdf.stem] = p
        fronts, appearances = resolved_drawing_data()
        cls.doc = pymupdf.open("pdf", build_pdf(cls.projects, CATALOG, fronts, appearances, VALUES))
        cls.texts = [page.get_text() for page in cls.doc]

    def test_hojas_numeradas_y_todas_con_rotulo(self):
        n = self.doc.page_count
        self.assertGreaterEqual(n, 2 + len(self.projects) + 1)
        for i, t in enumerate(self.texts, start=1):
            with self.subTest(hoja=i):
                self.assertIn(f"{i} de {n}", t)
                for v in ("Obra de prueba", "Cliente X", "23/11/2026", "TC", "RV", "AP"):
                    self.assertIn(v, t)
                self.assertIn(f"CLI-PL-1-{i:02d}", t)

    def test_indice_y_tableros_con_escala(self):
        self.assertIn("Índice", self.texts[1])
        for k, name in enumerate(self.projects):
            t = self.texts[2 + k]
            self.assertIn(f"Tablero {name}", t)
            self.assertRegex(t, r"\n1:[\d.]+\n")  # casilla Escala del rótulo (los títulos de las vistas son dibujo, no texto)
            self.assertGreater(len(self.doc[2 + k].get_drawings()), 100, "la hoja no tiene el dibujo del tablero")

    def test_lista_consolidada(self):
        self.assertIn("Lista de equipamiento eléctrico", self.texts[-1])

    def test_escala_normalizada(self):
        self.assertEqual(pick_scale(890, 2030, 394, 240), 10)
        self.assertEqual(pick_scale(300, 400, 394, 240), 2)
