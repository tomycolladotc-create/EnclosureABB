"""Pruebas unitarias de resolución de rutas (desarrollo vs ejecutable) y endpoints de escritorio."""
import gzip
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import app
import proyectos
import rutas


class RutasYEscritorio(unittest.TestCase):
    def test_rutas_desarrollo_y_frozen_appdata_o_portable(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            with patch.object(rutas, "IS_FROZEN", True), patch.object(rutas, "EXE_DIR", tdp):
                with patch.dict(os.environ, {"LOCALAPPDATA": str(tdp / "local")}, clear=False):
                    os.environ.pop("ENCLOSUREABB_DATA_DIR", None)
                    self.assertEqual(rutas.user_data_dir(), tdp / "local" / "EnclosureABB")
                # Modo portable: portable.flag al lado del .exe guarda en ./datos_usuario
                (tdp / "portable.flag").write_text("portable", encoding="utf-8")
                self.assertEqual(rutas.user_data_dir(), tdp / "datos_usuario")

    def test_proyectos_ts4_en_modo_frozen_es_generico_y_escribe_en_usuario(self):
        with tempfile.TemporaryDirectory() as td:
            pdir = Path(td)
            with patch.object(rutas, "IS_FROZEN", True):
                sample = proyectos.load("ts4", projects_dir=pdir)
                self.assertEqual(sample["project"], "Tablero de ejemplo")
                self.assertNotIn("BAF-E-", sample.get("source", ""))
                sample["project"] = "Mi Tablero Editado"
                proyectos.save("ts4", sample, projects_dir=pdir)
                self.assertTrue((pdir / "ts4.json").exists())
                reloaded = proyectos.load("ts4", projects_dir=pdir)
                self.assertEqual(reloaded["project"], "Mi Tablero Editado")

    def test_frentes_precalculados_evitan_recalculo_y_coinciden_con_pintura(self):
        fronts, apps = app.resolved_drawing_data()
        with tempfile.TemporaryDirectory() as td:
            gz = Path(td) / "frentes_resueltos.json.gz"
            with gzip.open(gz, "wb") as fh:
                fh.write(json.dumps({
                    "stamp": rutas.drawing_sources_stamp(),
                    "fronts": fronts,
                    "appearances": apps,
                }).encode("utf-8"))
            old_resolved = dict(app._RESOLVED)
            try:
                app._RESOLVED.clear()
                with patch.object(app, "PRECOMPUTED_FRONTS", gz):
                    f2, a2 = app.resolved_drawing_data()
                self.assertEqual(set(f2["items"].keys()), set(fronts["items"].keys()))
                self.assertEqual(set(a2["items"].keys()), set(apps["items"].keys()))
            finally:
                app._RESOLVED.clear()
                app._RESOLVED.update(old_resolved)


if __name__ == "__main__":
    unittest.main()
