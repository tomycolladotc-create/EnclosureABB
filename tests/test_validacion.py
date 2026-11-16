import unittest

from validacion import validate


CATALOG = {"deviceShells": [{"id": "din", "mounting": "din", "depth": 70}, {"id": "kit"}]}
RULES = {"railPositionToleranceMm": 2, "railEndClearanceMm": 0, "fallbackMinDepthForKitDevicesMm": 200}


def project(devices, width=300, height=300, depth=150):
    return {"devices": devices, "enclosure": {"functional": {"width": width, "height": height}, "externalBody": {"depth": depth}, "mountingLayout": {"dinRails": [{"id": "R1", "x": 10, "y": 100, "length": 200}]}}}


class Validacion(unittest.TestCase):
    def test_detecta_superposicion_y_salida_de_placa(self):
        result = validate(project([
            {"tag": "A", "shell": "kit", "x": 250, "y": 10, "w": 60, "h": 50},
            {"tag": "B", "shell": "kit", "x": 260, "y": 20, "w": 20, "h": 20},
        ]), CATALOG, RULES)
        self.assertEqual({item["code"] for item in result["findings"]} & {"device_overlap", "outside_functional_area"}, {"device_overlap", "outside_functional_area"})
        self.assertFalse(result["ok"])

    def test_controla_riel_y_profundidad_conocida(self):
        result = validate(project([
            {"tag": "DIN1", "shell": "din", "x": 190, "y": 90, "w": 40, "h": 20},
        ], depth=60), CATALOG, RULES)
        codes = {item["code"] for item in result["findings"]}
        self.assertIn("outside_rail", codes)
        self.assertIn("insufficient_depth", codes)

    def test_informa_profundidad_desconocida_sin_inventarla(self):
        result = validate(project([{"tag": "XT", "shell": "kit", "x": 10, "y": 10, "w": 40, "h": 50}]), CATALOG, RULES)
        item = next(item for item in result["findings"] if item["code"] == "depth_unknown")
        self.assertEqual(item["level"], "warning")
        self.assertIn("Falta confirmar", item["message"])

    def test_proyecto_valido(self):
        result = validate(project([{"tag": "DIN1", "shell": "din", "x": 20, "y": 90, "w": 40, "h": 20}], depth=100), CATALOG, RULES)
        self.assertTrue(result["ok"])
        self.assertEqual(result["errors"], 0)


if __name__ == "__main__":
    unittest.main()
