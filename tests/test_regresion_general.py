"""Regresión con los 24 tableros reales del plano GENERAL (pedido de Thomas 2026-11-19: «un pequeño cambio puede causar
otro problema, todo tiene que estar previsto»). En cada cambio se vuelven a armar los 24 como lo hace la interfaz y se
exige: auditoría sin errores ni avisos, todos los equipos del unifilar presentes con su modelo y polos, lista sin
renglones rotos y la misma huella que la versión aceptada. Si un cambio la modifica a propósito:
`python tests/regresion_general.py` muestra qué cambió y `--aceptar` la guarda."""
import json
import unittest

from regresion_general import BOARDS, EXPECTED, build, fingerprint

RESULTS = {}


def result(pdf):
    if pdf.stem not in RESULTS:
        RESULTS[pdf.stem] = build(pdf)
    return RESULTS[pdf.stem]


class Regresion24Tableros(unittest.TestCase):
    def test_hay_24_tableros(self):
        self.assertEqual(len(BOARDS), 24)

    def test_auditoria_sin_errores_ni_avisos(self):
        for pdf in BOARDS:
            with self.subTest(tablero=pdf.stem):
                self.assertEqual([f"{f['code']}: {f['message']}" for f in result(pdf)["findings"]], [])

    def test_todos_los_equipos_del_unifilar_con_su_modelo_y_polos(self):
        for pdf in BOARDS:
            r = result(pdf)
            drawn = {d["tag"]: d for d in r["project"]["devices"]}
            not_drawn = {d["tag"] for d in r["project"].get("devicesNotDrawn", [])}
            with self.subTest(tablero=pdf.stem):
                for d in r["detected"]:
                    if d["upstream"]:
                        continue
                    self.assertTrue(d["tag"] in drawn or d["tag"] in not_drawn, f"falta {d['tag']}")
                    if d["tag"] in drawn:
                        self.assertEqual((drawn[d["tag"]]["model"], drawn[d["tag"]]["poles"]), (d["model"], d["poles"]), d["tag"])
                for tag in not_drawn:  # sólo los monopolares quedan sin dibujar (regla del usuario)
                    status = next(x for x in r["project"]["devicesNotDrawn"] if x["tag"] == tag)["status"]
                    self.assertIn("monopolar", status, tag)

    def test_lista_de_materiales_sana(self):
        for pdf in BOARDS:
            r = result(pdf)
            with self.subTest(tablero=pdf.stem):
                for row in r["bom"]:
                    self.assertTrue(row["description"].strip(), row)
                    self.assertNotIn("  A ()", row["description"])
                    self.assertIsInstance(row["quantity"], int)
                    self.assertGreater(row["quantity"], 0, row)
                self.assertFalse([i for i in r["issues"] if "repetido" in i or "inválida" in i or "más de un artículo" in i or "La lista tiene" in i])

    def test_huella_igual_a_la_aceptada(self):
        expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
        for pdf in BOARDS:
            with self.subTest(tablero=pdf.stem):
                self.assertEqual(fingerprint(result(pdf)), expected[pdf.stem],
                                 "cambió el armado: revisar con `python tests/regresion_general.py` y aceptar con --aceptar si es intencional")


if __name__ == "__main__":
    unittest.main()
