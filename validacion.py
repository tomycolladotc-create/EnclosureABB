"""Validación geométrica y de datos del tablero, sin modificar el proyecto.

Las reglas ajustables viven en datos/reglas_validacion.json. La falta de una
profundidad oficial nunca se reemplaza por un valor inventado: se informa.
"""
from __future__ import annotations


def _finding(level, code, message, tags=()):
    return {"level": level, "code": code, "message": message, "tags": list(tags)}


def _overlap(a, b):
    return (
        a.get("x", 0) < b.get("x", 0) + b.get("w", 0)
        and a.get("x", 0) + a.get("w", 0) > b.get("x", 0)
        and a.get("y", 0) < b.get("y", 0) + b.get("h", 0)
        and a.get("y", 0) + a.get("h", 0) > b.get("y", 0)
    )


def _is_din(device, shells):
    shell = shells.get(device.get("shell"), {})
    return device.get("mounting") == "din" or shell.get("mounting") == "din"


def validate(project, catalog, rules):
    """Devuelve resumen y hallazgos deterministas para un proyecto."""
    findings = []
    devices = project.get("devices", [])
    enclosure = project.get("enclosure", {})
    functional = enclosure.get("functional", {})
    width, height = functional.get("width", 0), functional.get("height", 0)
    shells = {item["id"]: item for item in catalog.get("deviceShells", [])}

    for device in devices:
        tag = device.get("tag", "sin etiqueta")
        x, y = device.get("x", 0), device.get("y", 0)
        w, h = device.get("w", 0), device.get("h", 0)
        if x < 0 or y < 0 or x + w > width or y + h > height:
            findings.append(_finding("error", "outside_functional_area", f"{tag} queda fuera de la placa de montaje.", [tag]))

    for index, first in enumerate(devices):
        for second in devices[index + 1 :]:
            if _overlap(first, second):
                tags = [first.get("tag", "?"), second.get("tag", "?")]
                findings.append(_finding("error", "device_overlap", f"{tags[0]} se superpone con {tags[1]}.", tags))

    rails = enclosure.get("mountingLayout", {}).get("dinRails", [])
    tolerance = rules.get("railPositionToleranceMm", 2)
    end_clearance = rules.get("railEndClearanceMm", 0)
    din_devices = [device for device in devices if _is_din(device, shells)]
    assigned = {rail.get("id", str(i)): [] for i, rail in enumerate(rails)}
    for device in din_devices:
        tag = device.get("tag", "sin etiqueta")
        center_y = device.get("y", 0) + device.get("h", 0) / 2
        candidates = [rail for rail in rails if abs(center_y - rail.get("y", 0)) <= tolerance]
        if not candidates:
            findings.append(_finding("error", "din_without_rail", f"{tag} es DIN pero no está colocado sobre un riel.", [tag]))
            continue
        rail = min(candidates, key=lambda item: abs(center_y - item.get("y", 0)))
        rail_id = rail.get("id", str(rails.index(rail)))
        assigned.setdefault(rail_id, []).append(device)
        left = rail.get("x", 0) + end_clearance
        right = rail.get("x", 0) + rail.get("length", 0) - end_clearance
        if device.get("x", 0) < left or device.get("x", 0) + device.get("w", 0) > right:
            findings.append(_finding("error", "outside_rail", f"{tag} excede la longitud útil del riel {rail_id}.", [tag]))

    for rail in rails:
        rail_id = rail.get("id", str(rails.index(rail)))
        used = sum(device.get("w", 0) for device in assigned.get(rail_id, []))
        available = max(0, rail.get("length", 0) - 2 * end_clearance)
        if used > available:
            findings.append(_finding("error", "rail_capacity", f"{rail_id} ocupa {used:g} mm y dispone de {available:g} mm.", [d.get("tag", "?") for d in assigned[rail_id]]))

    # La profundidad funcional es el espacio útil declarado; la exterior sólo es respaldo.
    body_depth = functional.get("depth") or enclosure.get("externalBody", {}).get("depth")
    required_depths = []
    unknown_depth = []
    for device in devices:
        shell = shells.get(device.get("shell"), {})
        depth = device.get("depth") or shell.get("depthMm")  # clave del catálogo: depthMm (antes se leía "depth" y nunca había dato)
        if depth:
            required_depths.append((device.get("tag", "?"), depth))
        elif not _is_din(device, shells):
            unknown_depth.append(device.get("tag", "?"))
    clearance = rules.get("depthSafetyClearanceMm", 0)
    for tag, depth in required_depths:
        if body_depth and depth + clearance > body_depth:
            findings.append(_finding("error", "insufficient_depth", f"{tag} requiere {depth:g} mm y el gabinete tiene {body_depth:g} mm de profundidad.", [tag]))
    if unknown_depth:
        provisional = rules.get("fallbackMinDepthForKitDevicesMm", 200)
        text = f"Falta confirmar la profundidad ABB de: {', '.join(unknown_depth)}."
        if body_depth and body_depth < provisional:
            text += f" El gabinete tiene {body_depth:g} mm y el criterio provisional es {provisional:g} mm."
        findings.append(_finding("warning", "depth_unknown", text, unknown_depth))

    # Auditoría de armado (lecciones de la revisión de los 24 tableros del GENERAL, docs/LECCIONES.md).
    from auditoria import audit
    findings.extend(audit(project, catalog, rules))

    counts = {"errors": 0, "warnings": 0}
    for finding in findings:
        counts["errors" if finding["level"] == "error" else "warnings"] += 1
    return {"ok": counts["errors"] == 0, **counts, "findings": findings}
