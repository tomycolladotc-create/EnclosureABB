"""Importador de unifilares en PDF de ABB e-Design DOC.

Todo lo específico (formato de etiquetas, cómo se marca el alimentador, qué texto
corresponde a qué carcasa ABB) vive en datos/catalogo_abb.json:
  - importRules: expresiones para cortar el texto y leer modelo y polos.
  - deviceShells[].match: {modelRegex, poles} que identifica cada carcasa.
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


def find_shell(model, poles, catalog):
    """Devuelve (carcasa, motivo). La carcasa exige modelo y polos coincidentes."""
    same_family = []
    for shell in catalog["deviceShells"]:
        rule = shell.get("match")
        if not rule or not re.search(rule["modelRegex"], model, re.IGNORECASE):
            continue
        same_family.append(shell)
        if poles is None or rule.get("poles") in (None, poles):
            return shell, None
    if same_family:
        known = ", ".join(f'{s["match"].get("poles")}P' for s in same_family)
        return None, f"familia en catálogo, pero sin carcasa de {poles}P (hay: {known})"
    return None, "familia sin carcasa en el catálogo"


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
        shell, reason = find_shell(model, poles, catalog)
        hint = next((h for h in hints if re.search(h["modelRegex"], model, re.IGNORECASE)), None)
        if upstream:
            status = "alimentador externo; no pertenece al tablero"
        elif shell:
            status = "detectado; revisar modelo y polos"
        elif hint:
            status = hint["note"]
        else:
            status = reason
        if poles is None and not upstream:
            status += "; polos no indicados en el plano"
        item = shell or {}
        found.append({
            "tag": match.group(1), "evidence": snippet, "shell": item.get("id"),
            "model": model[:40], "poles": poles,
            "w": item.get("width", 80), "h": item.get("height", 100),
            "status": status, "upstream": upstream,
            **({"mounting": hint["mounting"]} if hint and not shell else {}),
        })
    return found
