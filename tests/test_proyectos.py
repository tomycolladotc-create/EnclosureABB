"""Pruebas del almacenamiento de un proyecto por tablero (proyectos.py)."""
import json
import tempfile
import unittest
from pathlib import Path

import proyectos

TEMPLATE = {"project": "TS4", "enclosure": {"functional": {"width": 1000}}, "devices": [{"tag": "QF1"}], "accessories": [{"type": "pe_terminal"}]}


class Proyectos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_slug(self):
        self.assertEqual(proyectos.slug("TS AUX 1"), "ts-aux-1")
        self.assertEqual(proyectos.slug("  ¡¡ "), "tablero")

    def test_crear_copia_gabinete_sin_equipos_ni_accesorios(self):
        pid, project = proyectos.create("TSB", TEMPLATE, self.dir)
        self.assertEqual(pid, "tsb")
        self.assertEqual(project["devices"], [])
        self.assertEqual(project["accessories"], [])
        self.assertEqual(project["enclosure"], TEMPLATE["enclosure"])
        self.assertEqual(TEMPLATE["devices"], [{"tag": "QF1"}])  # la plantilla no se toca

    def test_no_pisa_uno_existente(self):
        proyectos.create("TSB", TEMPLATE, self.dir)
        with self.assertRaises(ValueError):
            proyectos.create("tsb", TEMPLATE, self.dir)

    def test_guardar_y_cargar_son_independientes(self):
        proyectos.save("a", {"project": "A", "devices": [1]}, self.dir)
        proyectos.save("b", {"project": "B", "devices": [1, 2]}, self.dir)
        self.assertEqual(proyectos.load("a", self.dir)["devices"], [1])
        names = {p["id"]: p["devices"] for p in proyectos.list_projects(self.dir)}
        self.assertEqual((names["a"], names["b"]), (1, 2))

    def test_id_invalido_no_sale_de_la_carpeta(self):
        for bad in ("../x", "a/b", "", "A", "x" * 60):
            with self.assertRaises(ValueError):
                proyectos.path_for(bad, self.dir)

    def test_ts4_historico_sigue_en_su_lugar(self):
        self.assertEqual(proyectos.path_for("ts4", self.dir), proyectos.LEGACY["ts4"])


if __name__ == "__main__":
    unittest.main()
