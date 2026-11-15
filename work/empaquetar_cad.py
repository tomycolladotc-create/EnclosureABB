"""Crea un paquete portable con CAD ABB y su inventario verificable."""

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parents[1]
inventory = root / "datos" / "cad_argentina.json"
data = json.loads(inventory.read_text(encoding="utf-8"))
out = Path(r"C:\Users\Thomas\Documents\Codex\2026-11-15\qui\outputs")
out.mkdir(parents=True, exist_ok=True)
package = out / "ABB_CAD_TS4_Argentina.zip"
with ZipFile(package, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
    archive.write(inventory, "datos/cad_argentina.json")
    archive.write(root / "README.md", "README.md")
    for item in data["items"]:
        for drawing in item["cadFiles"]:
            archive.write(root / drawing["path"], drawing["path"])
(out / "inventario_CAD_ABB_Argentina_TS4.json").write_text(
    inventory.read_text(encoding="utf-8"), encoding="utf-8"
)
print(package, package.stat().st_size)
