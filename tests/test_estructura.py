"""Pruebas de la estructura real del gabinete (catalogo_abb.json -> enclosures[].structure) y su salida en el DXF."""
import json
import unittest
from io import StringIO
from pathlib import Path

import ezdxf

import cad_export

DATOS = Path(__file__).resolve().parents[1] / "datos"


def load(name):
    return json.loads((DATOS / name).read_text(encoding="utf-8"))


class Estructura(unittest.TestCase):
    def test_banda_y_puertas_cuadran_con_el_catalogo(self):
        for e in load("catalogo_abb.json")["enclosures"]:
            st = e["structure"]
            ext, fun = e["externalBody"]["width"], e["functional"]["width"]
            if st.get("kind") == "monobloc":  # SR2: placa = (nominal - 40), externo = nominal + 3 (cat. 1STC804013D0201 págs. 9/6-9/7)
                self.assertEqual(ext - fun, 43, e["id"])
            else:
                self.assertEqual(ext - fun, 2 * st["frameBand"], e["id"])  # funcional = externo - 100 (cat. ABB pág. 46)
            self.assertEqual(sum(st["doorLeaves"]), ext, e["id"])
            self.assertTrue(all(p.get("pagina") for p in st["bom"]), e["id"])  # cada parte dice de qué página sale

    def test_dxf_trae_marco_puertas_y_lista_de_partes(self):
        data = cad_export.build_dxf(load("ts4_topografia.json"), load("catalogo_abb.json"), load("frentes_cad.json"), load("apariencias_abb.json"))
        entities = list(ezdxf.read(StringIO(data.decode("utf-8"))).modelspace())
        layers = [e.dxf.layer for e in entities]
        self.assertEqual(layers.count("ABB_PUERTAS"), 2)
        self.assertEqual(layers.count("ABB_ESTRUCTURA"), 1)
        self.assertGreater(layers.count("ABB_CAJETIN"), 5)
        self.assertGreater(layers.count("ABB_BOM"), 5)
        self.assertTrue(any("REV. SIN REVISION" in entity.dxf.text for entity in entities if entity.dxftype() == "TEXT"))


if __name__ == "__main__":
    unittest.main()
