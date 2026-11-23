"""Verificación automática contra el unifilar antes de mostrar el tablero (pedido de Thomas 2026-11-23, TSB-1.12).

Los 24 tableros reales tienen que coincidir enteros con su plano (modelo, polos y corriente de cada circuito), y un
equipo cambiado tiene que aparecer como diferencia con el dato del plano."""
import copy
import json
import sys
import unittest
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from importador import apply_corrections, detect_board, detect_devices  # noqa: E402
from validacion import validate  # noqa: E402
from verificacion_unifilar import check, findings, read_words  # noqa: E402

CATALOG = json.loads((ROOT / "datos" / "catalogo_abb.json").read_text(encoding="utf-8"))
BOARDS = sorted((ROOT / "tests" / "unifilares" / "general").glob("*.pdf"))


def importar(pdf):
    text = "\n".join(p.extract_text() or "" for p in PdfReader(pdf).pages)
    devices = detect_devices(text, CATALOG)
    apply_corrections(devices, detect_board(text), CATALOG)
    return devices


class VerificacionUnifilar(unittest.TestCase):
    def test_los_24_tableros_coinciden_con_su_plano(self):
        self.assertEqual(len(BOARDS), 24)
        for pdf in BOARDS:
            with self.subTest(tablero=pdf.stem):
                r = check(pdf.read_bytes(), importar(pdf), CATALOG)
                self.assertEqual(r["issues"], [])
                self.assertEqual(r["unverified"], [], "cada equipo tiene que quedar verificado")
                self.assertGreater(r["checked"], 0)

    def test_un_equipo_distinto_al_plano_se_detecta(self):
        pdf = next(p for p in BOARDS if p.stem.endswith("TSB"))
        devices = importar(pdf)
        words = read_words(pdf.read_bytes())
        d = next(d for d in devices if d.get("circuit") == "TSB-1.12")
        self.assertEqual(d["model"], "S201L-C10 NA")  # lo que dice el plano (rótulo y tabla «2x10 - 6kA»)
        wrong = copy.deepcopy(devices)
        next(x for x in wrong if x.get("circuit") == "TSB-1.12")["model"] = "S201L-C20 NA"
        r = check(None, wrong, CATALOG, words=words)
        kinds = {i["kind"] for i in r["issues"] if i["circuit"] == "TSB-1.12"}
        self.assertEqual(kinds, {"modelo", "corriente"})
        polos = copy.deepcopy(devices)
        next(x for x in polos if x.get("circuit") == "TSB-1.12")["poles"] = 4
        self.assertIn("polos", {i["kind"] for i in check(None, polos, CATALOG, words=words)["issues"]})

    def test_la_diferencia_queda_como_error_en_la_validacion(self):
        sys.path.insert(0, str(ROOT / "tests"))
        from regresion_general import build
        project = build(next(p for p in BOARDS if p.stem.endswith("TSB")))["project"]
        next(d for d in project["devices"] if d["tag"] == "QF124")["model"] = "S201L-C20 NA"
        project["sourceCheck"] = {"issues": [{"circuit": "TSB-1.12", "tag": "QF124", "kind": "corriente", "boardModel": "S201L-C20 NA",
                                               "message": "TSB-1.12 (QF124): la tabla del plano dice 10 A"}], "unverified": []}
        self.assertEqual([f["level"] for f in findings(project)], ["error"])
        rules = json.loads((ROOT / "datos" / "reglas_validacion.json").read_text(encoding="utf-8"))
        self.assertIn("unifilar_distinto", {f["code"] for f in validate(project, CATALOG, rules)["findings"]})
        next(d for d in project["devices"] if d["tag"] == "QF124")["model"] = "S201L-C10 NA"  # el usuario lo cambió a mano: ya no hay diferencia comprobada
        self.assertEqual([f["code"] for f in findings(project)], ["unifilar_sin_verificar"])
