"""Excel de equipamiento eléctrico de varios tableros (botón «Excel de equipamiento» en Exportar).

Pedido de Thomas (2026-11-19 y 2026-11-23): sólo el equipamiento eléctrico, sin canalizaciones, con el código en una
columna, la cantidad en otra y en otra a qué circuitos y tableros va; que salga del programa con un botón.
Qué categorías entran o quedan afuera se define en datos/reglas_layout.json → equipamientoExcel (una sola regla).
La cantidad de cada renglón es una fórmula SUMIFS sobre la hoja de detalle, así un cambio en el detalle se refleja solo.
"""
import io
import json
import re
from pathlib import Path

from bom import MISSING, build_bom

RULES = json.loads((Path(__file__).resolve().parent / "datos" / "reglas_layout.json").read_text(encoding="utf-8"))["equipamientoExcel"]


def _generic(category, description):
    """Texto del renglón agrupado: sin la fase de cada luz piloto o peine (eso queda en el detalle)."""
    text = description.split(" · ")[0] if category in ("Señalización", "Peine") else description
    return re.sub(r" de fase [RST\-]+", "", text)


def unclassified(rows):
    """Categorías de la lista que la regla no clasifica: no deben existir (una categoría nueva no puede perderse sin aviso)."""
    known = set(RULES["include"]) | set(RULES["exclude"])
    return sorted({r["category"] for r in rows} - known)


def collect(projects, catalog, mode="abb"):
    """projects: {nombre del tablero: proyecto}. Devuelve (detalle, grupos) sólo con las categorías incluidas.
    mode='abb' (con códigos ABB) o 'generic' (especificación técnica sin marca)."""
    order = {c: i for i, c in enumerate(RULES["include"])}
    detail, groups = [], {}
    for board, project in projects.items():
        rows = build_bom(project, catalog, mode=mode)
        missing = unclassified(rows)
        if missing:
            raise ValueError("Categorías sin clasificar en equipamientoExcel: " + ", ".join(missing))
        for r in rows:
            if r["category"] not in order:
                continue
            has = bool(r["code"]) and r["code"] != MISSING
            desc_base = _generic(r["category"], r["description"])
            key = f"{r['category']}|{r['code'] if has else desc_base}"
            detail.append({"key": key, "board": board, **r})
            g = groups.setdefault(key, {"category": r["category"], "code": r["code"], "unit": r["unit"],
                                        "description": desc_base if (has or mode == "generic") else r["description"],
                                        "circuits": [], "boards": [], "status": set()})
            if r.get("tags"):
                g["circuits"].append(r["tags"])
            if board not in g["boards"]:
                g["boards"].append(board)
            g["status"].add(r["status"])
    detail.sort(key=lambda d: (order[d["category"]], d["board"], d["description"]))
    items = sorted(groups.items(), key=lambda kv: (order[kv[1]["category"]], kv[1]["code"] == MISSING, kv[1]["description"]))
    return detail, items


def nameplates(projects, catalog):
    """Placas para grabar, con el mismo texto y tamaño del dibujo: la placa de la puerta (cad_export.door_features) y el
    portaetiquetas de cada equipo (etiquetas.label_boxes, la misma regla del editor y del DXF)."""
    from cad_export import LABEL_RULES, door_features
    from etiquetas import label_boxes
    rows = []
    for board, project in projects.items():
        cab = project["enclosure"]
        spec = next((e for e in catalog["enclosures"] if e["id"] == cab.get("id")), None) or {}
        door = door_features(project, spec.get("structure"), cab["externalBody"])
        pl = door["plate"]
        rows.append([board, "Puerta", "Placa del tablero", pl["text"], round(pl["w"], 1), round(pl["h"], 1), round(pl["font"], 1)])
        devices = project.get("devices", [])
        for d, b in zip(devices, label_boxes(devices, cab["functional"]["width"], LABEL_RULES)):
            text = str(d.get("circuit") or d.get("tag") or "")
            rows.append([board, d.get("tag", ""), d.get("model", ""), text, round(b["w"], 1), LABEL_RULES["heightMm"], round(b["font"], 1)])
    return rows


def build_xlsx(projects, catalog, mode="abb"):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    detail, items = collect(projects, catalog, mode=mode)
    font, colors = RULES["font"], RULES["colors"]
    head = Font(name=font, bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor=colors["header"])
    normal, bold = Font(name=font, size=10), Font(name=font, size=10, bold=True)
    fills = {"missing": PatternFill("solid", fgColor=colors["missing"]), "confirm": PatternFill("solid", fgColor=colors["confirm"])}
    side = Side(style="thin", color="BFBFBF")
    box = Border(left=side, right=side, top=side, bottom=side)
    wrap = Alignment(wrap_text=True, vertical="top")

    wb = Workbook()
    ws = wb.active
    ws.title = "Equipamiento eléctrico"
    ws.append(["N°", "Categoría", "Código", "Descripción", "Cantidad", "Unidad", "Circuitos", "Tableros", "Estado", "Clave"])
    ds = wb.create_sheet("Detalle por tablero")
    ds.append(["Clave", "Tablero", "Categoría", "Código", "Descripción", "Cantidad", "Unidad", "Circuitos", "Estado", "Fuente"])
    for d in detail:
        ds.append([d["key"], d["board"], d["category"], d["code"], d["description"], d["quantity"], d["unit"], d.get("tags") or "",
                   d["status"], d.get("source") or ""])
    last_detail = max(ds.max_row, 2)
    for i, (key, g) in enumerate(items, start=1):
        r = i + 1
        ws.append([i, g["category"], g["code"], g["description"],
                   f"=SUMIFS('Detalle por tablero'!$F$2:$F${last_detail},'Detalle por tablero'!$A$2:$A${last_detail},J{r})",
                   g["unit"], ", ".join(g["circuits"]) or "—", ", ".join(g["boards"]), "; ".join(sorted(g["status"])), key])
    rows_main = ws.max_row - 1

    def style(sheet, widths, qty_col, code_col, status_col, hidden):
        for c in sheet[1]:
            c.font, c.fill, c.alignment, c.border = head, head_fill, Alignment(wrap_text=True, vertical="center"), box
        for row in sheet.iter_rows(min_row=2):
            for c in row:
                c.font, c.alignment, c.border = normal, wrap, box
            row[qty_col - 1].number_format, row[qty_col - 1].font = "0", bold
            code, status = row[code_col - 1].value, str(row[status_col - 1].value or "")
            fill = fills["missing"] if code == MISSING else fills["confirm"] if ("confirmar" in status or "CAMBIADO" in str(row[code_col].value)) else None
            if fill:
                for c in row:
                    c.fill = fill
        for i, w in enumerate(widths, start=1):
            sheet.column_dimensions[get_column_letter(i)].width = w
        sheet.column_dimensions[hidden].hidden = True
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions

    style(ws, [5, 18, 18, 60, 10, 8, 55, 30, 30, 10], 5, 3, 9, "J")
    style(ds, [10, 20, 18, 18, 70, 10, 8, 45, 28, 40], 6, 4, 9, "A")

    ps = wb.create_sheet("Placas de identificación")
    ps.append(["Tablero", "Equipo", "Modelo", "Texto a grabar", "Ancho (mm)", "Alto (mm)", "Letra (mm)"])
    for row in nameplates(projects, catalog):
        ps.append(row)
    for c in ps[1]:
        c.font, c.fill, c.alignment, c.border = head, head_fill, Alignment(wrap_text=True, vertical="center"), box
    for row in ps.iter_rows(min_row=2):
        for c in row:
            c.font, c.alignment, c.border = normal, wrap, box
        for c in row[4:7]:
            c.number_format = "0.0"
    for i, w in enumerate([22, 10, 30, 40, 11, 10, 10], start=1):
        ps.column_dimensions[get_column_letter(i)].width = w
    ps.freeze_panes = "A2"
    ps.auto_filter.ref = ps.dimensions

    ns = wb.create_sheet("Notas", 0)
    missing = sum(1 for _, g in items if g["code"] == MISSING)
    generic = sum(1 for _, g in items if not g["code"])
    confirm = sum(1 for _, g in items if g["code"] != MISSING and any(str(s).startswith("a confirmar") for s in g["status"]))
    mode_label = "lista genérica (sin marca, especificación técnica)" if mode == "generic" else "códigos de pedido ABB"
    notes = [
        f"Equipamiento eléctrico ({mode_label}) · {len(projects)} tablero(s): " + ", ".join(projects),
        "",
        f"Renglones: {rows_main}. Con código: {rows_main - missing - generic}. Genéricos: {generic}. "
        f"Falta código: {missing}. A confirmar antes de comprar: {confirm}.",
        "Incluye: " + ", ".join(RULES["include"]) + ".",
        "Excluye (canalizaciones y montaje): " + ", ".join(RULES["exclude"]) + ".",
        "Cantidad = suma de la hoja «Detalle por tablero» (fórmula SUMIFS): si se corrige el detalle, el total se actualiza.",
        "Colores: rojo claro = falta el código de pedido (no comprar sin definirlo); amarillo = a confirmar antes de comprar "
        "(variante que el unifilar deja abierta) o cambiado por pedido del usuario.",
        "Los códigos salen de datos/codigos_pedido_abb.json; la fuente de cada uno está en la columna Fuente del detalle.",
        "Hoja «Placas de identificación»: el texto y el tamaño de cada chapita son los mismos del dibujo (placa grabada de la puerta y portaetiqueta de cada equipo).",
    ]
    for t in notes:
        ns.append([t])
    ns.column_dimensions["A"].width = 140
    for row in ns.iter_rows():
        for c in row:
            c.font, c.alignment = normal, Alignment(wrap_text=True, vertical="top")
    ns["A1"].font = Font(name=font, size=12, bold=True)
    wb.active = 1
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
