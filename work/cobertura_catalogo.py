"""Lista qué equipos de los unifilares de tests/unifilares/ no tienen carcasa en el catálogo.

Uso (desde la raíz del repo):  python work/cobertura_catalogo.py > docs/cobertura_unifilares.md
Sirve para saber qué familias ABB buscar (medidas + CAD) a continuación.
"""
import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from importador import detect_devices  # noqa: E402
from pypdf import PdfReader  # noqa: E402

logging.getLogger("pypdf").setLevel(logging.ERROR)
catalog = json.loads((ROOT / "datos" / "catalogo_abb.json").read_text(encoding="utf-8"))
SERIE = re.compile(r"^(SN?\s?\d{3}[A-Z]*|XT\d[A-Z]?|T\d[A-Z]?|E\d\.\d[A-Z]?|OT\d+[A-Z]*\d*)", re.I)

missing = defaultdict(lambda: {"n": 0, "boards": set(), "examples": set()})
total = covered = 0
for pdf in sorted((ROOT / "tests" / "unifilares").glob("*.pdf")):
    text = "\n".join(p.extract_text() or "" for p in PdfReader(pdf).pages)
    board = pdf.stem.split("Unifilares-")[-1]
    for d in detect_devices(text, catalog):
        if d["upstream"]:
            continue
        total += 1
        if d["shell"]:
            covered += 1
            continue
        serie = SERIE.match(d["model"])
        key = (serie.group(1).replace(" ", "").upper() if serie else d["model"][:12], d["poles"])
        missing[key]["n"] += 1
        missing[key]["boards"].add(board)
        missing[key]["examples"].add(d["model"])

print(f"# Cobertura del catálogo sobre {len(list((ROOT / 'tests' / 'unifilares').glob('*.pdf')))} unifilares\n")
print(f"Equipos con carcasa: **{covered} de {total}**. Faltan estas familias (serie + polos), ordenadas por cantidad:\n")
print("| Serie | Polos | Equipos | Tableros | Ejemplos |\n|---|---|---|---|---|")
for (serie, poles), info in sorted(missing.items(), key=lambda kv: -kv[1]["n"]):
    ex = "; ".join(sorted(info["examples"])[:3])
    print(f"| {serie} | {poles if poles is not None else '?'} | {info['n']} | {', '.join(sorted(info['boards']))} | {ex} |")
