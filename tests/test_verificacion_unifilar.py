"""Lección 32: control independiente de los 24 tableros contra los unifilares ABB.
Lee cada PDF con PyMuPDF (el importador usa pypdf) y compara modelo, circuito, polos y calibre (I Nom) de cada
interruptor, seccionador y diferencial con el proyecto armado. También controla, dentro del propio unifilar, que el
modelo coincida con la columna «I Nom - Icc» (calibre y polos). Las correcciones pedidas por el usuario
(datos/correcciones_unifilar.json) se comparan con el modelo original del unifilar."""
import re
import sys
import unittest
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_regresion_general import BOARDS, result  # noqa: E402

TAG = re.compile(r"^-?(Q[A-Z]\d+)$")
RATING = re.compile(r"^(\d)x(\d+(?:,\d+)?)\s*-\s*(\d+(?:,\d+)?)\s*kA$")
STOP = re.compile(r"mm²|^INTERRUPTOR|^SECCIONADOR|^\d+(?:,\d+)?\s*kA$|^[RST]{1,3}N?$|^BARRA|^Uso$|^DIFERENCIAL")
key = lambda m: re.sub(r"[\s\-]+", "", str(m or "")).upper()
USE = {"IUG","TUG","IUE","TUE","OCE","ACU","ALIM"}
STOP = re.compile(r"mm²|^INTERRUPTOR|^SECCIONADOR|^\d+(?:,\d+)?\s*kA$|^[RST]{1,3}N?$|^BARRA|^Uso$|^DIFERENCIAL")
key = lambda m: re.sub(r"[\s\-]+", "", str(m or "")).upper()

def parse(pdf):
    lines = [l.strip() for p in pymupdf.open(pdf) for l in p.get_text().splitlines() if l.strip()]
    header_tag = None
    m = re.match(r"DE\s+.+?\s+-\s+-?(Q[A-Z]\d+)", lines[1]) if len(lines) > 1 else None
    if m: header_tag = m.group(1)
    idx = [i for i, l in enumerate(lines) if TAG.match(l)]
    out = {}
    for n, i in enumerate(idx):
        tag = TAG.match(lines[i]).group(1)
        block = lines[i + 1:(idx[n + 1] if n + 1 < len(idx) else len(lines))]
        model = []
        for l in block:
            if STOP.search(l) or l in USE: break
            model.append(l)
        circ = next((block[j + 1] for j, l in enumerate(block[:-1]) if l in USE), None)
        rat = next((RATING.match(l) for l in block if RATING.match(l)), None)
        out[tag] = {"model": " ".join(model), "circuit": circ, "ratingPoles": int(rat.group(1)) if rat else None,
                    "ratingIn": float(rat.group(2).replace(",", ".")) if rat else None, "kA": rat.group(3) if rat else None,
                    "raw": " | ".join(block[:14])}
    return out, header_tag

def model_in(model):
    for pat in (r"TMD\s+(\d+)-", r"Ekip\s+\w+\s+LI\s+(\d+)", r"PR\d+\S*\s+(\d+)A", r"\b[BCDKZ]\s?(\d+)\b", r"-[BCDKZ](\d+)", r"AC-(\d+)/", r"A-(\d+)/"):
        m = re.search(pat, model)
        if m: return float(m.group(1))
    return None

def model_poles(model):
    m = re.match(r"^S\s?(\d)(\d)(\d)", model)  # S2xy: y = polos (S201..S204), NA = 1P+N
    if m and m.group(1) in "28":
        p = int(m.group(3)); return 2 if re.search(r"\bNA\b", model, re.I) and p == 1 else p
    m = re.match(r"^S80(\d)", model)
    if m: return int(m.group(1))
    m = re.match(r"^F20(\d)", model)
    if m: return int(m.group(1))
    return None



class IgualAlUnifilar(unittest.TestCase):
    def test_modelo_circuito_polos_y_calibre_iguales_al_unifilar(self):
        for pdf in BOARDS:
            pdfdev, header = parse(pdf)
            proj = result(pdf)["project"]
            pd = {d["tag"]: d for d in proj["devices"]}
            nd = {d["tag"]: d for d in proj.get("devicesNotDrawn", [])}
            for tag, u in pdfdev.items():
                if tag == header and tag not in pd:
                    continue
                with self.subTest(tablero=pdf.stem, equipo=tag):
                    d = pd.get(tag) or nd.get(tag)
                    self.assertIsNotNone(d, "está en el unifilar y no en el proyecto")
                    orig = (d.get("correctedFrom") or {}).get("model") or d.get("model")
                    opol = (d.get("correctedFrom") or {}).get("poles") or d.get("poles")
                    self.assertEqual(key(orig), key(u["model"]), "modelo")
                    if u["circuit"]:
                        self.assertEqual(d.get("circuit"), u["circuit"], "circuito")
                    if u["ratingPoles"] and opol:
                        self.assertEqual(opol, u["ratingPoles"], "polos")
                    mi, mp = model_in(u["model"]), model_poles(u["model"])
                    if u["ratingIn"] and mi:
                        self.assertAlmostEqual(mi, u["ratingIn"], msg="el calibre del modelo no coincide con la columna I Nom")
                    if mp and u["ratingPoles"]:
                        self.assertEqual(mp, u["ratingPoles"], "los polos del modelo no coinciden con la columna I Nom")
            for tag in set(pd) | set(nd):
                with self.subTest(tablero=pdf.stem, equipo=tag):
                    self.assertIn(tag, pdfdev, "está en el proyecto y no en el unifilar")
