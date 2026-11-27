"""PDF único de entrega (pedido de Thomas 2026-11-23): carátula, índice, frentes y puertas, lista, rótulo y hojas numeradas."""
import json
import unittest
from pathlib import Path

import pymupdf

from app import resolved_drawing_data
from entrega_pdf import build_pdf, pick_scale
from regresion_general import BOARDS, build

CATALOG = json.loads((Path(__file__).resolve().parent.parent / "datos" / "catalogo_abb.json").read_text(encoding="utf-8"))
VALUES = {"proyecto": "Obra de prueba", "sector": "Sector industrial", "etapa": "PROYECTO EJECUTIVO",
          "cliente": "Cliente X", "documento": "CLI-PL-1", "revision": "B", "descripcion_rev": "EMISIÓN PARA REVISIÓN",
          "fecha": "23/11/2026", "dibujo": "TC", "reviso": "RV", "aprobo": "AP", "asesor": "Estudio Técnico",
          "archivo": "Entrega_prueba.pdf"}


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
        self.assertGreaterEqual(n, 2 + 2 * len(self.projects) + 1)
        for i, t in enumerate(self.texts, start=1):
            with self.subTest(hoja=i):
                self.assertIn(f"{i} de {n}", t)
                for v in ("Obra de prueba", "Cliente X", "23/11/2026", "TC", "RV", "AP"):
                    self.assertIn(v, t)
                self.assertIn(f"CLI-PL-1-{i:02d}", t)

    def test_indice_y_tableros_con_escala(self):
        self.assertIn("Índice", self.texts[1])
        for k, name in enumerate(self.projects):
            t = self.texts[2 + 2 * k]  # cada tablero: su hoja y detrás la de taller
            self.assertIn(f"Tablero {name}", t)
            self.assertRegex(t, r"\n1:[\d.]+\n")  # casilla Escala del rótulo (los títulos de las vistas son dibujo, no texto)
            self.assertGreater(len(self.doc[2 + 2 * k].get_drawings()), 100, "la hoja no tiene el dibujo del tablero")
            self.assertIn(f"Taller {name}", self.texts[3 + 2 * k])

    def test_lista_consolidada(self):
        self.assertIn("Lista de equipamiento eléctrico", self.texts[-1])

    def test_escala_normalizada(self):
        self.assertEqual(pick_scale(890, 2030, 394, 240), 10)
        self.assertEqual(pick_scale(300, 400, 394, 240), 2)

    def test_rotulo_tecnico_esquina_y_tipografia_truetype(self):
        # Todas las hojas llevan la estructura del rótulo técnico (revisiones, sector, DOC N°, REV, contenido, asesor) sin logos
        for i, t in enumerate(self.texts, start=1):
            with self.subTest(hoja=i):
                for lbl in ("Rev", "Descripción", "Proy", "Revis", "Apr", "Fecha",
                            "SECTOR DE OBRA", "DOC N°:", "REV:", "CONTENIDO:", "NOMBRE ASESOR:",
                            "Sector industrial", "PROYECTO EJECUTIVO", "Estudio Técnico", "Entrega_prueba.pdf"):
                    self.assertIn(lbl, t)
        # Tipografía embebida TrueType prolija con fidelidad Unicode (LeelawUI / Liberation / Bahnschrift)
        fonts = {f[3] for f in self.doc[0].get_fonts(full=True)}
        self.assertTrue(any(any(k in fn.lower() for k in ("leelaw", "liberation", "bahn", "artifakt", "dejavu")) for fn in fonts), fonts)


class EntregaConFormatoDelUsuario(unittest.TestCase):
    """Con el formato del usuario cargado, todas las hojas salen con SU marco y SU rótulo (pedido de Thomas 2026-11-23:
    el PDF traía un rótulo propio del programa en vez del suyo)."""

    @classmethod
    def setUpClass(cls):
        import sys
        import tempfile
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_plano_unifilar import formato_minimo
        from plano_unifilar import analyze_template
        small = sorted(BOARDS, key=lambda p: p.stat().st_size)[:1]
        p = build(small[0])["project"]
        cls.name = p.get("project") or small[0].stem
        cls.tmp = tempfile.TemporaryDirectory()
        path = Path(cls.tmp.name) / "formato.dxf"
        formato_minimo(path, "HOJA X")
        meta = analyze_template(str(path))
        meta["perBoardTag"] = "TITLE_3OF3"  # el formato mínimo tiene una sola hoja: el atributo del tablero se fija
        (Path(cls.tmp.name) / "formato.json").write_text(json.dumps(meta), encoding="utf-8")
        fronts, appearances = resolved_drawing_data()
        values = {"DOCN°": "CLI-XYZ-77"}
        # El rótulo se dibuja como el DXF (textos en trazos): se anota qué atributos tenía al dibujar cada hoja.
        import entrega_pdf
        cls.stamps, real = [], entrega_pdf._render

        def spy(doc, *a):
            from plano_unifilar import RULES as PR
            ins = [i for i in doc.modelspace().query("INSERT") if i.dxf.name == PR["titleBlock"]]
            if ins:
                cls.stamps.append({x.dxf.tag: x.dxf.text for x in ins[0].attribs})
            return real(doc, *a)
        entrega_pdf._render = spy
        try:
            cls.doc = pymupdf.open("pdf", build_pdf({cls.name: p}, CATALOG, fronts, appearances, values, template=str(path)))
        finally:
            entrega_pdf._render = real
        cls.texts = [page.get_text() for page in cls.doc]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_hoja_del_tamano_del_marco_del_usuario(self):
        for page in self.doc:
            self.assertAlmostEqual(page.rect.width / 72 * 25.4, 594, delta=0.5)
            self.assertAlmostEqual(page.rect.height / 72 * 25.4, 420, delta=0.5)

    def test_rotulo_del_usuario_en_todas_las_hojas_y_ninguno_propio(self):
        from entrega_pdf import RULES
        content = RULES["format"]["content"]
        kinds = ["cover", "index", "board", "shop"] + ["bom"] * (len(self.texts) - 4)
        self.assertEqual(len(self.stamps), len(self.texts))
        for i, (t, a, kind) in enumerate(zip(self.texts, self.stamps, kinds), start=1):
            with self.subTest(hoja=i):
                self.assertEqual(a["DOCN°"], "CLI-XYZ-77")  # dato cargado por el usuario, en su rótulo
                self.assertEqual(a["TITLE_2OF3"], content[kind])  # atributo de contenido según la hoja
                self.assertEqual(a["TITLE_3OF3"], self.name if kind in ("board", "shop") else "")
                self.assertNotIn("N° de plano", t)  # el rótulo propio del programa no aparece


class PloteoMonocromatico(unittest.TestCase):
    """Colores índice de CAD (verde, celeste…) salen en la pluma negra; los colores propios (true color ABB) se ven."""

    def test_indice_negro_true_color_se_conserva(self):
        import ezdxf
        from entrega_pdf import _render
        doc = ezdxf.new()
        doc.layers.add("VERDE", color=3)
        msp = doc.modelspace()
        msp.add_line((0, 0), (100, 0), dxfattribs={"layer": "VERDE"})  # por capa, índice 3
        msp.add_line((0, 10), (100, 10), dxfattribs={"color": 4})  # índice directo
        msp.add_line((0, 20), (100, 20), dxfattribs={"true_color": ezdxf.rgb2int((200, 16, 46))})  # rojo ABB
        page = pymupdf.open("pdf", _render(doc, 120, 40, 1))[0]
        colors = {tuple(round(c, 2) for c in d["color"]) for d in page.get_drawings() if d.get("color")}
        self.assertIn((0.0, 0.0, 0.0), colors)
        self.assertIn((round(200 / 255, 2), round(16 / 255, 2), round(46 / 255, 2)), colors)
        self.assertNotIn((0.0, 1.0, 0.0), colors)
        self.assertNotIn((0.0, 1.0, 1.0), colors)
