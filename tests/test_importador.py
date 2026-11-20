"""Pruebas del importador. Correr desde la raíz del repo:  python -m unittest discover tests

- TS4: el resultado tiene que coincidir carcasa por carcasa con el caso de referencia.
- Unifilares reales en tests/unifilares/: reglas que valen para cualquier tablero
  (nunca asignar una carcasa con otra cantidad de polos, detectar el alimentador, etc.).
Para agregar un caso: copiar el PDF a tests/unifilares/ y volver a correr.
"""
import json
import logging
import unittest
from pathlib import Path

from importador import detect_devices, shell_size
from marcado import resolve

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / "datos" / "catalogo_abb.json").read_text(encoding="utf-8"))
SERIES = {s["id"]: s for s in CATALOG["series"] if "id" in s}
SHELLS = {s["id"]: s for s in CATALOG["deviceShells"]}
APPEAR = json.loads((ROOT / "datos" / "apariencias_abb.json").read_text(encoding="utf-8"))["items"]
FRONTS = json.loads((ROOT / "datos" / "frentes_cad.json").read_text(encoding="utf-8"))["items"]

TS4_ESPERADO = {
    "QF7": None, "QS1": "abb.ot400e04.4p.front",
    "QF81": "abb.s804n.4p.front", "QF85": "abb.s804n.4p.front",
    "QF82": "abb.tmax.xt1.4p.fixed.front", "QF83": "abb.tmax.xt1.4p.fixed.front",
    "QF84": "abb.tmax.xt1.4p.fixed.front", "QF86": "abb.tmax.xt1.4p.fixed.front",
    "QF87": "abb.tmax.xt1.4p.fixed.front", "QF163": "abb.tmax.xt1.4p.fixed.front",
    "QF88": "abb.tmax.xt2.4p.fixed.front", "QF89": "abb.s200m.1pn.front", "QF90": "abb.s200m.1pn.front",
}


def pdf_text(path):
    from pypdf import PdfReader
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)


class TS4(unittest.TestCase):
    def setUp(self):
        text = (ROOT / "tests" / "fixtures" / "ts4_texto_extraido.txt").read_text(encoding="utf-8")
        self.devices = {d["tag"]: d for d in detect_devices(text, CATALOG)}

    def test_carcasas(self):
        self.assertEqual({t: d["shell"] for t, d in self.devices.items()}, TS4_ESPERADO)

    def test_alimentador_externo(self):
        self.assertTrue(self.devices["QF7"]["upstream"])
        self.assertEqual([t for t, d in self.devices.items() if d["upstream"]], ["QF7"])

    def test_modelos_y_polos(self):
        self.assertEqual(self.devices["QF81"]["model"], "S804N-C32")
        self.assertEqual(self.devices["QF89"]["model"], "S 251 Na C 10")
        # S251 Na: hipótesis (serie s251-na, verified=false): comparte la carcasa del S201 NA y lo dice en el estado.
        self.assertIn("sin confirmar", self.devices["QF89"]["status"])
        self.assertEqual(self.devices["QF90"]["poles"], 2)
        self.assertEqual(self.devices["QS1"]["poles"], 4)


class Catalogo(unittest.TestCase):
    def test_series_apuntan_a_carcasas_con_frente(self):
        for serie in SERIES.values():
            with self.subTest(serie=serie["id"]):
                self.assertIn(serie["shell"], SHELLS)
                if not SHELLS[serie["shell"]].get("outlineOnly"):  # sin CAD publicado: contorno con medidas de ficha (p. ej. S290)
                    self.assertIn(serie["shell"], FRONTS, "la carcasa no tiene frente 2D en frentes_cad.json")
                else:
                    self.assertTrue(SHELLS[serie["shell"]].get("dimensionsSource"), "contorno sin CAD: las medidas tienen que salir de una ficha")
                self.assertTrue(serie.get("basis"), "toda serie necesita su fuente")

    def test_ancho_por_polos(self):
        s200 = SHELLS["abb.s200m.1p.front"]
        self.assertEqual(shell_size(s200, 3), (52.5, 88))


class Marcado(unittest.TestCase):
    """Lo impreso en el frente sale del plano y respeta lo medido en las fotos ABB."""

    def textos(self, tag, devices):
        d = devices[tag]
        return [i["text"] for i in resolve(APPEAR[d["shell"]].get("marking"), d["marking"], d["poles"])]

    def test_s800_ts4(self):
        text = (ROOT / "tests" / "fixtures" / "ts4_texto_extraido.txt").read_text(encoding="utf-8")
        devices = {d["tag"]: d for d in detect_devices(text, CATALOG)}
        self.assertEqual(self.textos("QF81", devices), ["ABB", "S804N", "C32", "240/415V~36kA", "In=32A"])
        self.assertEqual(self.textos("QF90", devices), ["ABB", "S 201M-NA", "C 10", "10000", "3"])

    def test_tmax_y_ot_ts4(self):
        text = (ROOT / "tests" / "fixtures" / "ts4_texto_extraido.txt").read_text(encoding="utf-8")
        devices = {d["tag"]: d for d in detect_devices(text, CATALOG)}
        self.assertEqual(self.textos("QF82", devices), ["ABB", "SACE Tmax", "XT1C", "160", "In=80A", "TMD"])
        self.assertEqual(self.textos("QF88", devices), ["ABB", "SACE Tmax", "XT2N", "160", "In=80A", "TMG"])
        self.assertEqual(self.textos("QS1", devices), ["ABB"])

    def test_s200_tripolar_lleva_tension(self):
        pdf = ROOT / "tests" / "unifilares" / "BAF-E-EL-PL-104-0_Unifilares-12_TSB.pdf"
        devices = {d["tag"]: d for d in detect_devices(pdf_text(pdf), CATALOG)}
        self.assertEqual(self.textos("QF57", devices), ["ABB", "S 203", "C 10", "~400V", "6000", "3"])
        self.assertNotIn("~400V", self.textos("QF164", devices))  # bipolar: no verificado

    def test_no_inventa_si_falta_dato(self):
        mk = APPEAR["abb.s804n.4p.front"]["marking"]
        self.assertNotIn("240/415V~kA", [i["text"] for i in resolve(mk, {"serie": "S804N", "curva": "C", "In": "32"}, 4)])
        self.assertEqual(len(resolve(mk, {"serie": "S804N", "curva": "C", "In": "32"}, 4)), 4)

    def test_sin_monopolares(self):
        pdf = ROOT / "tests" / "unifilares" / "BAF-E-EL-PL-104-0_Unifilares-12_TSB.pdf"
        qf62 = {d["tag"]: d for d in detect_devices(pdf_text(pdf), CATALOG)}["QF62"]
        self.assertIsNone(qf62["shell"])
        self.assertIn("fuera de alcance", qf62["status"])
        for serie in SERIES.values():
            self.assertGreaterEqual(min(serie["poles"]), 2, serie["id"])


class UnifilaresReales(unittest.TestCase):
    PDFS = sorted((ROOT / "tests" / "unifilares").glob("*.pdf"))

    def test_hay_casos(self):
        self.assertTrue(self.PDFS, "No hay PDFs en tests/unifilares/")

    def test_polos_coinciden_con_la_carcasa(self):
        for pdf in self.PDFS:
            for d in detect_devices(pdf_text(pdf), CATALOG):
                if d["shell"] and d["poles"] is not None:
                    with self.subTest(pdf=pdf.name, tag=d["tag"]):
                        self.assertIn(d["poles"], SERIES[d["series"]]["poles"])
                        self.assertEqual((d["w"], d["h"]), shell_size(SHELLS[d["shell"]], d["poles"]))

    def test_salidas_tienen_modelo_y_polos(self):
        for pdf in self.PDFS:
            for d in detect_devices(pdf_text(pdf), CATALOG):
                if d["tag"].startswith("QF") and not d["upstream"]:
                    with self.subTest(pdf=pdf.name, tag=d["tag"]):
                        self.assertTrue(d["model"])
                        # Si el plano no indica polos (p. ej. interruptor principal), se avisa; nunca se inventan.
                        self.assertTrue(d["poles"] is not None or "polos no indicados" in d["status"])

    def test_tablero_simple_tiene_un_alimentador(self):
        for pdf in self.PDFS:
            if "GENERAL" in pdf.name:  # lámina con varios tableros: ver PENDIENTE de separación por tablero
                continue
            with self.subTest(pdf=pdf.name):
                upstream = [d["tag"] for d in detect_devices(pdf_text(pdf), CATALOG) if d["upstream"]]
                self.assertEqual(len(upstream), 1, upstream)


if __name__ == "__main__":
    unittest.main()


class CorreccionesDelUsuario(unittest.TestCase):
    """2026-11-20: el usuario pidió cambiar el monopolar QF62 de TSB (S201M B16) por un 1P+N (S201M-B16 NA)."""

    def setUp(self):
        from importador import apply_corrections, detect_board
        self.apply, self.detect_board = apply_corrections, detect_board
        self.text = pdf_text(ROOT / "tests" / "unifilares" / "general" / "TSB.pdf")

    def test_qf62_de_tsb_se_dibuja_como_1p_n(self):
        devices = detect_devices(self.text, CATALOG)
        unused = self.apply(devices, self.detect_board(self.text), CATALOG)
        qf62 = {d["tag"]: d for d in devices}["QF62"]
        self.assertEqual(unused, [])
        self.assertEqual((qf62["model"], qf62["poles"], qf62["shell"]), ("S201M-B16 NA", 2, "abb.s200m.1pn.front"))
        self.assertEqual(qf62["correctedFrom"]["model"], "S201M B16")

    def test_no_se_aplica_si_el_unifilar_cambio(self):
        devices = detect_devices(self.text, CATALOG)
        fix = [{"board": "TSB", "tag": "QF62", "fromModel": "S201M C20", "model": "S201M-C20 NA", "poles": 2, "reason": "x", "date": "x"}]
        unused = self.apply(devices, self.detect_board(self.text), CATALOG, fix)
        self.assertEqual(len(unused), 1)
        self.assertEqual({d["tag"]: d for d in devices}["QF62"]["poles"], 1)

    def test_no_se_aplica_a_otro_tablero(self):
        devices = detect_devices(self.text, CATALOG)
        fix = [{"board": "TSL1", "tag": "QF62", "fromModel": "S201M B16", "model": "S201M-B16 NA", "poles": 2, "reason": "x", "date": "x"}]
        self.assertEqual(self.apply(devices, self.detect_board(self.text), CATALOG, fix), [])
        self.assertNotIn("correctedFrom", {d["tag"]: d for d in devices}["QF62"])
