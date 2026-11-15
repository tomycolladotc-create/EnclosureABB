"""Publica el editor portable y las cuatro salidas de revisión en outputs."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(r"C:\Users\Thomas\Documents\Codex\2026-11-15\qui\outputs")
OUT.mkdir(parents=True, exist_ok=True)

for filename in ("TS4_vista_2D.svg", "TS4_vista_2D.png", "TS4_vista_2D.pdf", "TS4_vista_2D.dxf"):
    shutil.copy2(ROOT / "salida" / filename, OUT / filename)

files = [ROOT / name for name in (
    "app.py", "cad_export.py", "generar_topografico.py", "iniciar_editor.bat",
    "iniciar_editor.py", "requirements.txt", "requirements_cad.txt", "README.md",
    "work/proyectar_cad.py",
)]
for folder in ("datos", "web", "cad", "referencias"):
    files.extend(p for p in (ROOT / folder).rglob("*") if p.is_file())

package = OUT / "Editor_ABB_TS4_vista_2D.zip"
with ZipFile(package, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
    for file in files:
        archive.write(file, file.relative_to(ROOT).as_posix())
with ZipFile(package) as archive:
    assert archive.testzip() is None
    print(f"{package}: {len(archive.namelist())} archivos, {package.stat().st_size} bytes")
