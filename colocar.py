"""Ubicación automática de equipos de riel DIN sobre los rieles del gabinete elegido.

Los rieles (posición y largo) los define el gabinete en datos/catalogo_abb.json: acá NO se inventan rieles.
Si un equipo no entra, queda marcado `unplaced` y el control de normativa lo avisa.
Solo se ubican equipos de riel DIN; los de kit (XT, OT) siguen ubicándose a mano.
"""
import json
from pathlib import Path

# La misma regla que el armado automático (layout_auto.py): distinta carcasa → colGap; misma carcasa → pegados (peine).
# Antes acá había 4 mm fijos y el armado usaba 25 mm: ubicar a mano y armar solo daban resultados distintos (2026-11-19).
GAP_OTHER_SERIES_MM = float(json.loads((Path(__file__).resolve().parent / "datos" / "reglas_layout.json").read_text(encoding="utf-8"))["colGap"])
GAP_SAME_SERIES_MM = 0.0


def _gap(a_shell, b_shell):
    return GAP_SAME_SERIES_MM if a_shell == b_shell else GAP_OTHER_SERIES_MM


def _first_fit(rail, busy, shell, width):
    """busy: lista (inicio, fin, carcasa) ordenada. Devuelve x o None."""
    x, prev_shell = rail["x"], None
    for start, end, other in busy:
        gap_left = 0 if prev_shell is None else _gap(prev_shell, shell)
        if x + gap_left + width + _gap(shell, other) <= start:
            return x + gap_left
        x, prev_shell = max(x, end), other
    gap_left = 0 if prev_shell is None else _gap(prev_shell, shell)
    return x + gap_left if x + gap_left + width <= rail["x"] + rail["length"] else None


def place_din(project, catalog):
    """Ubica los equipos con `unplaced: true` en el primer riel con lugar. Devuelve la lista de equipos que no entraron."""
    din = {s["id"] for s in catalog["deviceShells"] if s.get("mounting") == "din"}
    rails = project.get("enclosure", {}).get("mountingLayout", {}).get("dinRails", [])
    failed = []
    for device in project.get("devices", []):
        if not device.get("unplaced") or device.get("shell") not in din:
            continue
        spot = None
        for rail in rails:
            lo, hi = rail["y"] - device["h"] / 2, rail["y"] + device["h"] / 2
            busy = sorted((d["x"], d["x"] + d["w"], d.get("shell")) for d in project["devices"]
                          if d is not device and not d.get("unplaced") and d["y"] < hi and d["y"] + d["h"] > lo)
            x = _first_fit(rail, busy, device["shell"], device["w"])
            if x is not None:
                spot = (x, rail["y"] - device["h"] / 2)
                break
        if spot:
            device["x"], device["y"] = spot
            device.pop("unplaced", None)
            device.pop("placementNote", None)
        else:
            device["placementNote"] = f"no entra en los rieles del gabinete ({len(rails)} riel(es))"
            failed.append(device["tag"])
    return failed
