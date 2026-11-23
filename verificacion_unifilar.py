"""Verificación automática contra el unifilar, antes de mostrar el tablero (pedido de Thomas 2026-11-23).

El importador lee el PDF como texto corrido (pypdf). Esta verificación lo vuelve a leer por otro camino, por posición
(PyMuPDF: palabras con coordenadas), y para cada circuito compara lo que quedó en el tablero contra dos datos del plano:

1. el rótulo del equipo encima de su salida (p. ej. «-QF124 / S201L-C10 / NA»): mismo modelo;
2. la fila de protección de la tabla de su columna (p. ej. «2x10 - 6kA»): mismos polos y misma corriente nominal.

Lo que no coincide es un error: la interfaz lo muestra antes de abrir el tablero y la validación lo deja en rojo.
No inventa: si el plano no trae alguno de los dos datos, ese control se saltea y se informa como no verificado.
Reglas en catalogo_abb.json → importRules.sourceCheck.
"""
from __future__ import annotations

import re

from auditoria import rated_current


def _norm(text):
    return re.sub(r"[\s\-]", "", str(text or "")).upper()


def _rules(catalog):
    return catalog["importRules"]["sourceCheck"]


def _columns(words, rules):
    """Circuitos del plano con su columna: {circuito: (página, x0, x1, y)}. Las columnas las marcan todas las palabras de
    la fila de nombres de circuito (también alimentadores sin número, p. ej. «TSAA»): cada columna va hasta la mitad de
    la distancia a la vecina; sin vecina de un lado, se refleja la del otro."""
    found = {}
    for page, w in words:
        if not re.fullmatch(rules["circuitPattern"], w[4]) or w[4] in found:
            continue
        h = w[3] - w[1]
        row = sorted((a[0] + a[2]) / 2 for p, a in words if p == page and abs(a[1] - w[1]) < h * 0.3)
        xc = (w[0] + w[2]) / 2
        i = min(range(len(row)), key=lambda k: abs(row[k] - xc))
        left = xc - row[i - 1] if i else None
        right = row[i + 1] - xc if i + 1 < len(row) else None
        left, right = left or right or rules["defaultHalfColumn"] * 2, right or left or rules["defaultHalfColumn"] * 2
        found[w[4]] = (page, xc - left / 2, xc + right / 2, w[1])
    return found


def _in_column(words, column, below=None):
    page, x0, x1, y = column
    out = [w for p, w in words if p == page and x0 <= (w[0] + w[2]) / 2 <= x1]
    if below is True:
        out = [w for w in out if w[1] > y]
    elif below is False:
        out = [w for w in out if w[1] < y]
    return sorted(out, key=lambda w: (w[1], w[0]))


def _tokens(text):
    return {t for t in re.split(r"[\s\-]+", str(text or "").upper()) if t}


def _label(words, tag, rules):
    """Texto del rótulo del equipo en el plano: los renglones debajo de la etiqueta (con o sin guion) que empiezan
    alineados con ella, mientras no haya un salto de más de 1,6 renglones; cada renglón llega hasta la etiqueta vecina
    de la misma fila. None si la etiqueta no aparece una sola vez."""
    hits = [(p, w) for p, w in words if _norm(w[4]) in (_norm("-" + tag), _norm(tag))]
    if len(hits) != 1:
        return None
    page, t = hits[0]
    line = t[3] - t[1]
    same_row = [w[0] for p, w in words if p == page and abs(w[1] - t[1]) < line * 0.3 and w[0] > t[2]]
    limit = min(same_row) if same_row else t[0] + line * 15
    out, y = [], t[1]
    for _ in range(rules["modelLines"]):
        starts = [w for p, w in words if p == page and abs(w[0] - t[0]) < line * 0.8 and line * 0.5 < w[1] - y < line * 1.6]
        if not starts:
            break
        y = min(w[1] for w in starts)
        out += sorted((w for p, w in words if p == page and abs(w[1] - y) < line * 0.3 and t[0] - line * 0.8 < w[0] < limit),
                      key=lambda w: w[0])
    return " ".join(w[4] for w in out) or None


def read_words(pdf_bytes):
    import pymupdf
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    return [(i, w) for i, page in enumerate(doc) for w in page.get_text("words")]


def check(pdf_bytes, devices, catalog, words=None):
    """Devuelve {checked, issues, unverified}: issues = [{circuit, tag, kind, message}] con lo que no coincide."""
    rules = _rules(catalog)
    words = words if words is not None else read_words(pdf_bytes)
    columns = _columns(words, rules)
    issues, unverified, checked = [], [], 0
    for d in devices:
        if d.get("upstream"):
            continue
        circuit = d.get("circuit")
        name = circuit or d.get("tag")
        column = columns.get(circuit) if circuit else None
        corrected = d.get("correctedFrom")  # cambio pedido por el usuario: se compara lo que decía el plano
        model = corrected["model"] if corrected else d.get("model")
        poles = corrected["poles"] if corrected else d.get("poles")
        tag = str(d.get("tag") or "")
        done = False
        # 1) rótulo del equipo: la etiqueta «-QF124» y los renglones de abajo alineados con ella (el modelo)
        label = _label(words, tag, rules)
        if label:
            done = True
            missing = _tokens(model) - _tokens(label)
            if missing:
                issues.append({"circuit": name, "tag": tag, "kind": "modelo", "boardModel": model,
                               "message": f"{name} ({tag}): el plano dice «{label}», el tablero tiene «{model}»"})
        if column is None:
            if not done:
                unverified.append({"circuit": name, "tag": tag, "message": "sin rótulo ni columna de circuito en el plano para comparar"})
            else:
                checked += 1
            continue
        # 2) fila de protección de la tabla: polos x corriente - poder de corte
        below = _in_column(words, column, below=True)
        text = " ".join(w[4] for w in below)
        m = re.search(rules["protectionPattern"], text)
        if m:
            done = True
            p_plan, in_plan = int(m.group(1)), float(m.group(2).replace(",", "."))
            in_board = rated_current({"model": model}, catalog["importRules"])
            if poles is not None and int(poles) != p_plan:
                issues.append({"circuit": name, "tag": tag, "kind": "polos", "boardModel": model,
                               "message": f"{name} ({tag}): la tabla del plano dice {p_plan} polos ({m.group(0)}), el tablero tiene {poles}"})
            if in_board is not None and abs(in_board - in_plan) > 1e-6:
                issues.append({"circuit": name, "tag": tag, "kind": "corriente", "boardModel": model,
                               "message": f"{name} ({tag}): la tabla del plano dice {in_plan:g} A ({m.group(0)}), el equipo del tablero es de {in_board:g} A ({model})"})
        if done:
            checked += 1
        else:
            unverified.append({"circuit": name, "tag": tag, "message": "el plano no trae rótulo ni fila de protección legibles"})
    return {"checked": checked, "issues": issues, "unverified": unverified}


def findings(project):
    """Hallazgos de la verificación guardada en el proyecto (project["sourceCheck"], hecha al importar): cada diferencia
    con el unifilar es un error mientras el equipo siga con el modelo que se comparó; si el usuario lo cambió, la
    diferencia ya no vale (no hay plano para volver a comparar) y se avisa que ese equipo quedó sin verificar."""
    check = project.get("sourceCheck")
    if not check:
        return []
    current = {d.get("tag"): d.get("model") for d in project.get("devices", []) + project.get("devicesNotDrawn", [])}
    out = []
    for issue in check.get("issues", []):
        if current.get(issue["tag"]) == issue.get("boardModel"):
            out.append({"level": "error", "code": "unifilar_distinto", "message": f"No coincide con el unifilar: {issue['message']}.",
                        "tags": [issue["tag"]], "origen": "verificación"})
        else:
            out.append({"level": "warning", "code": "unifilar_sin_verificar", "tags": [issue["tag"]], "origen": "verificación",
                        "message": f"{issue['circuit']} ({issue['tag']}) se cambió a mano después de importar: verificalo contra el unifilar."})
    for u in check.get("unverified", []):
        out.append({"level": "warning", "code": "unifilar_sin_verificar", "tags": [u["tag"]], "origen": "verificación",
                    "message": f"{u['circuit']} ({u['tag']}) no se pudo verificar contra el unifilar: {u['message']}."})
    return out
