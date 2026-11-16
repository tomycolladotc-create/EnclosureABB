import copy
import tempfile
import unittest
from pathlib import Path

import proyectos


TEMPLATE = {
    "project": "Plantilla",
    "enclosure": {"id": "anterior"},
    "devices": [{"tag": "QF1", "x": 10}],
    "accessories": [{"type": "pe_terminal"}],
}

ENCLOSURE = {
    "id": "sr2-prueba",
    "label": "SR2 prueba",
    "line": "ABB SR2",
    "functional": {"width": 560, "height": 760, "depth": 250},
    "externalBody": {"width": 603, "height": 803, "depth": 300},
    "plinthHeight": 0,
    "functionalOffset": {"x": 21.5, "y": 21.5},
    "mountingLayout": {"dinRails": []},
    "parts": ["placa"],
    "source": "catalogo.pdf",
}


class Proyectos(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_slug_seguro_y_sin_tildes(self):
        self.assertEqual(proyectos.slug("TS AUX 1"), "ts-aux-1")
        self.assertEqual(proyectos.slug("Copia producción"), "copia-produccion")
        self.assertEqual(proyectos.slug("  ¡¡ "), "tablero")

    def test_crear_vacio_con_envolvente_elegida(self):
        pid, project = proyectos.create("Tablero Auxiliar", TEMPLATE, self.folder, ENCLOSURE)
        self.assertEqual(pid, "tablero-auxiliar")
        self.assertEqual(project["devices"], [])
        self.assertEqual(project["accessories"], [])
        self.assertEqual(project["enclosure"]["id"], "sr2-prueba")
        self.assertEqual(project["enclosure"]["externalBody"]["depth"], 300)
        self.assertEqual(proyectos.load(pid, self.folder), project)

    def test_duplicar_conserva_contenido_sin_compartirlo(self):
        original = copy.deepcopy(TEMPLATE)
        proyectos.save("original", original, self.folder)
        pid, duplicate = proyectos.duplicate("original", "Copia producción", self.folder)
        self.assertEqual(pid, "copia-produccion")
        self.assertEqual(duplicate["devices"], original["devices"])
        self.assertEqual(duplicate["accessories"], original["accessories"])
        duplicate["devices"][0]["x"] = 99
        self.assertEqual(proyectos.load("original", self.folder)["devices"][0]["x"], 10)

    def test_borrar_y_proteger_base(self):
        proyectos.save("temporal", TEMPLATE, self.folder)
        proyectos.delete("temporal", self.folder)
        self.assertFalse((self.folder / "temporal.json").exists())
        with self.assertRaisesRegex(ValueError, "no se puede borrar"):
            proyectos.delete("ts4", self.folder)

    def test_no_pisa_un_proyecto_existente(self):
        proyectos.create("TSB", TEMPLATE, self.folder)
        with self.assertRaises(ValueError):
            proyectos.create("tsb", TEMPLATE, self.folder)

    def test_guardar_listar_y_cargar_son_independientes(self):
        proyectos.save("a", {"project": "A", "devices": [1]}, self.folder)
        proyectos.save("b", {"project": "B", "devices": [1, 2]}, self.folder)
        self.assertEqual(proyectos.load("a", self.folder)["devices"], [1])
        names = {item["id"]: item["devices"] for item in proyectos.list_projects(self.folder)}
        self.assertEqual((names["a"], names["b"]), (1, 2))

    def test_id_invalido_no_sale_de_la_carpeta(self):
        for bad in ("../x", "a/b", "", "A", "x" * 60):
            with self.assertRaises(ValueError):
                proyectos.path_for(bad, self.folder)

    def test_ts4_historico_sigue_en_su_lugar(self):
        self.assertEqual(proyectos.path_for("ts4", self.folder), proyectos.LEGACY["ts4"])


if __name__ == "__main__":
    unittest.main()
