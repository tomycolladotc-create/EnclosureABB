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
                    if row["status"] == "verificado":  # lección 29: «verificado» no puede convivir con un aviso de confirmar
                        self.assertNotRegex(row["description"].lower(), r"confirmar antes de comprar|código de distribuidor", row)
                self.assertFalse([i for i in r["issues"] if "repetido" in i or "inválida" in i or "más de un artículo" in i or "La lista tiene" in i])

    def test_etiquetas_iguales_en_python_y_en_el_editor(self):
        """La regla de los portaetiquetas existe en Python (DXF, auditoría) y en el editor (JS): se corre la del editor
        con node sobre los 24 tableros y tiene que dar exactamente lo mismo (lección 28)."""
        import re
        import shutil
        import subprocess
        from pathlib import Path
        from etiquetas import label_boxes
        node = shutil.which("node")
        if not node:
            self.skipTest("sin node")
        root = Path(__file__).resolve().parents[1]
        html = (root / "web" / "index.html").read_text(encoding="utf-8")
        js = re.search(r"// LABEL-RULE-BEGIN.*?\n(.*?)// LABEL-RULE-END", html, re.S).group(1)
        rules = json.loads((root / "datos" / "reglas_layout.json").read_text(encoding="utf-8"))["labels"]
        cases = []
        for pdf in BOARDS:
            p = result(pdf)["project"]
            cases.append({"name": pdf.stem, "devices": [{k: d.get(k) for k in ("x", "y", "w", "circuit", "tag")} for d in p["devices"]],
                          "plate": p["enclosure"]["functional"]["width"]})
        script = js + f"\nconst cases={json.dumps(cases)},r={json.dumps(rules)};console.log(JSON.stringify(cases.map(c=>labelBoxes(c.devices,c.plate,r))));"
        out = json.loads(subprocess.run([node, "-e", script], capture_output=True, text=True, check=True).stdout)
        for case, js_boxes in zip(cases, out):
            py = label_boxes(case["devices"], case["plate"], rules)
            with self.subTest(tablero=case["name"]):
                self.assertEqual(len(py), len(js_boxes))
                for a, b in zip(py, js_boxes):
                    for k in ("x", "w", "font"):
                        self.assertAlmostEqual(a[k], b[k], places=2)

    def test_todos_los_equipos_dibujados_con_su_frente(self):
        """Lección 31: los S293-C80 de TSB, TS AUX 1 y TS AUX 2 salían como un recuadro «sin CAD». Todo equipo dibujado
        tiene que tener frente (CAD, DXF o dibujo vectorial de catálogo ABB); los monopolares quedan fuera por regla."""
        from pathlib import Path
        fronts = json.loads((Path(__file__).resolve().parents[1] / "datos" / "frentes_cad.json").read_text(encoding="utf-8"))["items"]
        for pdf in BOARDS:
            p = result(pdf)["project"]
            with self.subTest(tablero=pdf.stem):
                sin_frente = [f"{d['tag']} {d.get('model')}" for d in p["devices"] if d.get("shell") not in fronts]
                self.assertFalse(sin_frente, f"equipos sin frente: {sin_frente}")
                fuera = [d for d in p.get("devicesNotDrawn", []) if int(d.get("poles") or 0) >= 2]
                self.assertFalse(fuera, f"equipos de 2+ polos sin dibujar: {fuera}")

    def test_correcciones_del_usuario_aplicadas_y_avisadas_en_la_lista(self):
        for pdf in BOARDS:
            r = result(pdf)
            with self.subTest(tablero=pdf.stem):
                self.assertEqual(r["correctionsNotApplied"], [], "corrección pedida que ya no coincide con el unifilar")
                for d in r["project"]["devices"]:
                    if d.get("correctedFrom"):
                        row = next(x for x in r["bom"] if x["category"] == "Equipo" and x["description"].startswith(d["model"] + " "))
                        self.assertIn("CAMBIADO por pedido del usuario", row["description"])

    def test_letra_de_las_etiquetas_legible(self):
        rules = json.loads((EXPECTED.parents[2].parent / "datos" / "reglas_layout.json").read_text(encoding="utf-8"))["labels"]
        from etiquetas import label_boxes
        for pdf in BOARDS:
            p = result(pdf)["project"]
            with self.subTest(tablero=pdf.stem):
                fonts = [b["font"] for b in label_boxes(p["devices"], p["enclosure"]["functional"]["width"], rules)]
                self.assertGreaterEqual(min(fonts), rules["fontMinMm"] - 0.01)

    def test_huella_igual_a_la_aceptada(self):
        expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
        for pdf in BOARDS:
            with self.subTest(tablero=pdf.stem):
                self.assertEqual(fingerprint(result(pdf)), expected[pdf.stem],
                                 "cambió el armado: revisar con `python tests/regresion_general.py` y aceptar con --aceptar si es intencional")


if __name__ == "__main__":
    unittest.main()
