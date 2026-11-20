"""Arma los 24 tableros reales del plano GENERAL igual que la interfaz (importar PDF → armado automático → accesorios)
y devuelve, para cada uno, el proyecto, la auditoría, la lista y una huella para comparar entre versiones.

Lo usan tests/test_regresion_general.py (en cada cambio) y, para aceptar un cambio intencional de la huella,
`python tests/regresion_general.py --aceptar` (muestra qué cambió antes de guardarlo).
"""
import copy
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pypdf import PdfReader  # noqa: E402

from auditoria import audit  # noqa: E402
from bom import bom_issues, build_bom  # noqa: E402
from importador import apply_corrections, detect_board, detect_devices, detect_signals  # noqa: E402
from layout_auto import autolayout_conforme  # noqa: E402
from proyectos import TEMPLATE_CONTENT_KEYS  # noqa: E402

BOARDS = sorted((ROOT / "tests" / "unifilares" / "general").glob("*.pdf"))
EXPECTED = ROOT / "tests" / "unifilares" / "general" / "esperado.json"
L = lambda n: json.loads((ROOT / "datos" / n).read_text(encoding="utf-8"))


def build(pdf, catalog=None):
    catalog = catalog or L("catalogo_abb.json")
    text = "\n".join(p.extract_text() or "" for p in PdfReader(str(pdf)).pages)
    detected = detect_devices(text, catalog)
    board = detect_board(text)
    unused = apply_corrections(detected, board, catalog)
    template = L("ts4_topografia.json")
    project = {k: copy.deepcopy(v) for k, v in template.items() if k not in TEMPLATE_CONTENT_KEYS}
    project.update(project=(board or {}).get("title") or pdf.stem, devices=[], accessories=[], source=pdf.name)
    if board:
        project["feeder"] = board["feeder"]
    project["devicesNotDrawn"] = [{k: d.get(k) for k in ("tag", "circuit", "model", "poles", "status")} for d in detected if not d["upstream"] and not d["shell"]]
    signals = detect_signals(text, catalog)
    if signals:
        project["signals"] = signals
    project["devices"] = [{**d, "x": 150, "y": 150, "unplaced": True} for d in detected if not d["upstream"] and d["shell"]]
    new, summary = autolayout_conforme(project, catalog)
    findings = audit(new, catalog, board_title=(board or {}).get("title"))
    rows = build_bom(new, catalog)
    return {"project": new, "summary": summary, "findings": findings, "bom": rows, "issues": bom_issues(rows, new), "detected": detected,
            "correctionsNotApplied": unused}


def fingerprint(result):
    p = result["project"]
    return {"gabinete": p["enclosure"]["id"], "equipos": len(p["devices"]), "noDibujados": len(p.get("devicesNotDrawn", [])),
            "rieles": len(p["enclosure"]["mountingLayout"].get("dinRails", [])),
            "accesorios": dict(sorted(Counter(a["type"] for a in p["accessories"]).items())),
            "renglonesLista": len(result["bom"])}


def main():
    current = {pdf.stem: fingerprint(build(pdf)) for pdf in BOARDS}
    old = json.loads(EXPECTED.read_text(encoding="utf-8")) if EXPECTED.exists() else {}
    for name in sorted(set(current) | set(old)):
        if current.get(name) != old.get(name):
            print(f"{name}:\n  antes:   {old.get(name)}\n  ahora:   {current.get(name)}")
    if "--aceptar" in sys.argv:
        EXPECTED.write_text(json.dumps(current, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"Guardada la huella de {len(current)} tableros en {EXPECTED.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
