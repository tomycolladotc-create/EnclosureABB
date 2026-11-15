"""Texto impreso en el frente de cada equipo (lo que se lee en el equipo real).

Las posiciones salen de datos/apariencias_abb.json -> items[carcasa].marking, medidas
en fotos frontales de ABB. Los datos variables salen del plano (importador.marking_fields).
La misma lógica está en web/index.html (markingSvg) para que pantalla y DXF coincidan.
"""
import re

FIELD = re.compile(r"\{(\w+)\}")


def _when_ok(rule, poles):
    if not rule:
        return True
    found = re.fullmatch(r"poles\s*(>=|<=|==|>|<)\s*(\d+)", rule.strip())
    if not found or poles is None:
        return False
    op, value = found.group(1), int(found.group(2))
    return {">=": poles >= value, "<=": poles <= value, "==": poles == value,
            ">": poles > value, "<": poles < value}[op]


def resolve(marking, fields, poles):
    """Lista de textos listos para dibujar. Omite los que necesitan un dato que el plano no trae."""
    result = []
    for index, item in enumerate((marking or {}).get("items", [])):
        if not _when_ok(item.get("when"), poles):
            continue
        names = FIELD.findall(item["text"])
        if any(fields.get(n) is None for n in names):
            continue
        text = FIELD.sub(lambda m: str(fields[m.group(1)]), item["text"])
        result.append({**item, "text": text, "variable": bool(names), "index": index})
    return result
