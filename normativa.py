"""Control de reglas de normativa sobre un proyecto (tablero).

Las reglas viven en datos/normativa_argentina.json (con fuente y estado). Este módulo solo
las EJECUTA: cada regla nombra una comprobación ('check') y acá está su implementación.
Para una regla nueva: agregarla al JSON y escribir su función en CHECKS.

Un proyecto puede traer 'accessories': [{"type": "pe_terminal"|"comb"|"terminal_cover", ...}].
No se inventa nada: lo que el programa no puede comprobar se devuelve como 'manual'.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RULES_FILE = ROOT / "datos" / "normativa_argentina.json"
GAP_MM = 1.0  # separación máxima para considerar dos equipos contiguos (peine posible)


def load_rules(path=RULES_FILE):
    return json.loads(Path(path).read_text(encoding="utf-8"))["rules"]


def _acc(project, kind):
    return [a for a in project.get("accessories", []) if a.get("type") == kind]


def board_has_pe_bar(project, rule):
    if _acc(project, "pe_terminal"):
        return []
    return ["El tablero no tiene barra ni bornera de puesta a tierra (PE)."]


def pe_terminals_enough(project, rule):
    # Simplificación declarada: un borne PE por circuito de salida (equipos QF). Revisar con el texto oficial.
    circuits = [d for d in project.get("devices", []) if str(d.get("tag", "")).startswith("QF")]
    have = sum(int(a.get("count", 1)) for a in _acc(project, "pe_terminal"))
    if have >= len(circuits):
        return []
    return [f"Hay {have} bornes PE y {len(circuits)} circuitos (QF): falta un borne por conductor."]


def live_terminals_covered(project, rule):
    if _acc(project, "terminal_cover"):
        return []
    return ["No hay cubrebornes (barrera aislante transparente) para los bornes con tensión."]


def comb_between_adjacent(project, rule):
    devices = [d for d in project.get("devices", []) if d.get("shell")]
    combs = _acc(project, "comb")
    out = []
    for i, a in enumerate(devices):
        for b in devices[i + 1:]:
            if a["shell"] != b["shell"] or abs(a["y"] - b["y"]) > 0.5:
                continue
            left, right = (a, b) if a["x"] <= b["x"] else (b, a)
            if 0 <= right["x"] - (left["x"] + left["w"]) <= GAP_MM:
                covered = any(left["tag"] in c.get("devices", []) and right["tag"] in c.get("devices", []) for c in combs)
                if not covered:
                    out.append(f"{left['tag']} y {right['tag']} están juntos sin peine.")
    return out


def masses_to_pe(project, rule):
    return ["Confirmar manualmente que las masas de instrumentos y relés van a la barra de tierra."]


CHECKS = {f.__name__: f for f in (board_has_pe_bar, pe_terminals_enough, live_terminals_covered, comb_between_adjacent, masses_to_pe)}
MANUAL = {"masses_to_pe"}  # no se pueden comprobar desde el dibujo


def check_project(project, rules=None):
    """Devuelve una lista de hallazgos: {rule, severity, message, ruleStatus, manual}."""
    findings = []
    for rule in rules if rules is not None else load_rules():
        func = CHECKS.get(rule["check"])
        if func is None:
            findings.append({"rule": rule["id"], "severity": "aviso", "message": f"Sin implementación para '{rule['check']}'.", "ruleStatus": rule["status"], "manual": True})
            continue
        for message in func(project, rule):
            findings.append({"rule": rule["id"], "severity": rule["severity"], "message": message,
                             "ruleStatus": rule["status"], "manual": rule["check"] in MANUAL})
    return findings


if __name__ == "__main__":
    import sys
    project = json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "datos" / "ts4_topografia.json").read_text(encoding="utf-8"))
    for f in check_project(project):
        print(f"[{f['severity'].upper()}] {f['rule']}: {f['message']}" + ("" if f["ruleStatus"] == "verificada" else "  (regla por verificar)"))
