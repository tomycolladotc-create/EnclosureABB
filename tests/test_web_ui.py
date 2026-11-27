"""Contrato mínimo de la interfaz (tableros, editor, exportar) y sus recursos estáticos."""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "web" / "index.html"
STYLES = ROOT / "web" / "styles.css"


class WebUi(unittest.TestCase):
    def test_tres_pantallas_y_controles_criticos(self):
        html = INDEX.read_text(encoding="utf-8")
        for screen in ("projects", "editor", "export"):
            self.assertIn(f'id="screen-{screen}"', html)
        for control in ("projectCards", "pdfNew", "board", "exportDxf", "normaChip", "showAdd"):
            self.assertIn(f'id="{control}"', html)

    def test_sin_botones_de_normativa_manual(self):
        html = INDEX.read_text(encoding="utf-8")
        for gone in ("normaComplete", "normaCheck", "Confirmar</button>", "fixedSize", "cadInfo"):
            self.assertNotIn(gone, html)

    def test_seguridad_y_validacion_estan_conectadas(self):
        html = INDEX.read_text(encoding="utf-8")
        self.assertIn("beforeunload", html)
        self.assertIn("scheduleAutosave", html)
        self.assertIn('id="redo"', html)
        self.assertIn("/api/validate", html)
        self.assertIn('route == "/api/validate"', (ROOT / "app.py").read_text(encoding="utf-8"))

    def test_bom_y_revisiones_estan_conectadas(self):
        html = INDEX.read_text(encoding="utf-8")
        server = (ROOT / "app.py").read_text(encoding="utf-8")
        for token in ("bomTable", "exportBom", "revisionList", "addRevision"):
            self.assertIn(token, html)
        for route in ("/api/bom", "/api/export-bom", "/api/revision"):
            self.assertIn(route, server)

    def test_sin_cache_y_un_solo_rotulo(self):
        self.assertIn('"Cache-Control", "no-store"', (ROOT / "app.py").read_text(encoding="utf-8"))
        self.assertNotIn("yy-6-up", INDEX.read_text(encoding="utf-8"))

    def test_estilos_separados_y_servidos(self):
        self.assertTrue(STYLES.is_file())
        self.assertIn('href="/styles.css"', INDEX.read_text(encoding="utf-8"))
        self.assertIn('route == "/styles.css"', (ROOT / "app.py").read_text(encoding="utf-8"))

    def test_catalogo_filtrable_y_popup_arrastre(self):
        html = INDEX.read_text(encoding="utf-8")
        for token in ("tabCatalog", "catPoles", "catIn", "catKa", "catalogList", "dropCircuitPanel", "dropCircuit", "addPoles", "addIn", "addKa",
                      "signalsBtn", "signalsPop", "signalsBtnLabel", "entregaUseFmt"):
            self.assertIn(f'id="{token}"', html)


if __name__ == "__main__":
    unittest.main()
