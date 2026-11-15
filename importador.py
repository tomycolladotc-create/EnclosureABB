"""Importador de unifilares en PDF de ABB e-Design DOC.

Todo lo específico (formato de etiquetas, cómo se marca el alimentador, qué texto
corresponde a qué carcasa ABB) vive en datos/catalogo_abb.json:
  - importRules: expresiones para cortar el texto y leer modelo y polos.
  - series: qué modelos usan cada carcasa (deviceShells) y con qué polos.
    Varias series pueden compartir carcasa: solo cambia la inscripción.
  - modelHints: modelos conocidos sin carcasa CAD (p. ej. montaje en riel).
Para que reconozca un equipo nuevo se edita el catálogo, no este archivo.
"""
import re


def _first_group(patterns, text):
    for pattern in patterns:
        found = re.search(pattern, text)
        if found:
            return int(found.group(1))
    return None


def parse_model(snippet, rules):
    """Texto del modelo: lo que hay antes del primer terminador (cable, -WC, SECCIONADOR)."""
    cut = len(snippet)
    for pattern in rules["modelTerminators"]:
        found = re.search(pattern, snippet)
        if found:
            cut = min(cut, found.start())
    return snippet[:cut].strip()


def shell_size(shell, poles):
    """Medidas fijas del equipo: de la carcasa, o polos × módulo si la carcasa es por polo."""
    module = shell.get("poleModule")
    if module and poles:
        return module["width"] * poles, shell["height"]
    return shell["width"], shell["height"]


def find_series(model, poles, catalog):
    """Devuelve (serie, carcasa, motivo). Exige modelo y polos admitidos por la serie."""
    shells = {s["id"]: s for s in catalog["deviceShells"]}
    same_family = []
    for serie in catalog.get("series", []):
        if "modelRegex" not in serie or not re.search(serie["modelRegex"], model, re.IGNORECASE):
            continue
        same_family.append(serie)
        if poles is None or poles in serie["poles"]:
            return serie, shells[serie["shell"]], None
    if same_family:
        known = sorted({p for s in same_family for p in s["poles"]})
        return None, None, f"serie en catálogo, pero sin carcasa de {poles}P (hay: {known})"
    return None, None, "serie sin carcasa en el catálogo"


def detect_devices(text, catalog):
    """Extrae etiquetas, modelo, polos y carcasa propuesta; conserva el texto original para revisar."""
    rules = catalog["importRules"]
    hints = catalog.get("modelHints", [])
    matches = list(re.finditer(rules["tagPattern"], text))
    found = []
    for index, match in enumerate(matches):
        before = text[max(0, match.start() - rules["upstreamContextChars"]):match.start()]
        upstream = bool(re.search(rules["upstreamPattern"], before, re.IGNORECASE))
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end():end]
        snippet = " ".join(block[:rules["evidenceChars"]].split())
        model = parse_model(snippet, rules)
        poles = _first_group(rules["polesPatterns"], block)
        serie, shell, reason = find_series(model, poles, catalog)
        hint = next((h for h in hints if re.search(h["modelRegex"], model, re.IGNORECASE)), None)
        if upstream:
            status = "alimentador externo; no pertenece al tablero"
        elif shell:
            status = "detectado; revisar modelo y polos" if serie["verified"] else "detectado; carcasa compartida sin confirmar"
        elif hint:
            status = hint["note"]
        else:
            status = reason
        if poles is None and not upstream:
            status += "; polos no indicados en el plano"
        width, height = shell_size(shell, poles) if shell else (80, 100)
        found.append({
            "tag": match.group(1), "evidence": snippet, "shell": shell and shell["id"],
            "series": serie and serie["id"], "model": model[:40], "poles": poles,
            "w": width, "h": height,
            "status": status, "upstream": upstream,
            **({"mounting": hint["mounting"]} if hint and not shell else {}),
        })
    return found
