"""Pruebas del control de normativa (normativa.py)."""
import unittest
from normativa import check_project, load_rules


def dev(tag, x, shell="abb.s200m.1p.front", w=35.0, y=761):
    return {"tag": tag, "shell": shell, "x": x, "y": y, "w": w, "h": 88}


class Normativa(unittest.TestCase):
    def ids(self, project):
        return {f["rule"] for f in check_project(project)}

    def test_tablero_sin_accesorios_falla(self):
        found = self.ids({"devices": [dev("QF1", 100)]})
        self.assertTrue({"pe-barra", "pe-un-conductor-por-borne", "bornes-con-barrera"} <= found)

    def test_tablero_con_accesorios_pasa_lo_comprobable(self):
        project = {"devices": [dev("QF1", 100), dev("QF2", 135.5)],
                   "accessories": [{"type": "pe_terminal", "count": 2}, {"type": "terminal_cover"},
                                   {"type": "comb", "devices": ["QF1", "QF2"]}]}
        self.assertEqual(self.ids(project), {"instrumentos-a-tierra"})  # solo queda la verificación manual

    def test_equipos_juntos_sin_peine(self):
        project = {"devices": [dev("QF1", 100), dev("QF2", 135)], "accessories": []}
        messages = [f["message"] for f in check_project(project) if f["rule"] == "peines-entre-termomagneticas"]
        self.assertEqual(messages, ["QF1 y QF2 están juntos sin peine."])

    def test_todas_las_reglas_tienen_fuente_y_estado(self):
        for rule in load_rules():
            self.assertTrue(rule["source"] and rule["status"], rule["id"])


if __name__ == "__main__":
    unittest.main()
