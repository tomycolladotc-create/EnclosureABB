"""Actualiza inventario de CAD descargados sin mezclar referencia y archivo."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "datos" / "cad_argentina.json"
data = json.loads(INVENTORY.read_text(encoding="utf-8"))

files = {
    "XT1C 160 TMD 80-800 4p F F": [
        ("xt1/1SDH001295R0080_XT1_4P_FIXED_F.stp", "1SDH001295R0080", "B", "carcasa XT1 4P fijo F; STEP 3D"),
    ],
    "S804N-C32 4P": [
        ("s800/2D_S800_4pole_drawing.DXF", "9AKK106930A3272", "-", "carcasa S800 4P; DXF 2D"),
        ("s800/3D_S800_(-C,_-N,_-S,_-U)_4pole_drawing.STEP", "9AKK106930A3273", "-", "carcasa S800N 4P; STEP 3D"),
    ],
    "S201M-C10 1P": [
        ("s201m/S201M_2D_9AKK106930A4856.dwg", "9AKK106930A4856", "-", "carcasa S201M; DWG 2D"),
        ("s201m/S200M_1P_3D_9AKK106930A4834.stp", "9AKK106930A4834", "-", "carcasa S200M 1P; STEP 3D"),
    ],
    "S201M-C10NA 1P+N": [
        ("s201m_na/S201M_Na_S202M_2D_9AKK106930A4857.dwg", "9AKK106930A4857", "-", "carcasa S201M Na / S202M; DWG 2D; verificar inscripción C10"),
        ("s201m_na/S200M_1PN_2P_3D_9AKK106930A4835.stp", "9AKK106930A4835", "-", "carcasa S200M 1P+N / 2P; STEP 3D; verificar inscripción C10"),
    ],
    "XT2N 160 TMG 80-240 4p F F": [
        ("xt2/1SDH002230A1002_XT2_4P_FIXED_F.stp", "1SDH002230A1002", "A", "carcasa XT2 4P fijo F; STEP 3D"),
        ("xt2/1SDH000721R0101_XT2_F_FRONT_TERMINALS.dxf", "1SDH000721R0101", "E", "dibujo de bornes delanteros XT2; DXF 2D; no es el cuerpo completo"),
    ],
    "OT400E04P 4P": [
        ("ot400/OT315_400E04_1SCC301280F0001.dwg", "1SCC301280F0001", "A", "dibujo mecánico familia OT315-OT400E04; DWG 2D"),
        ("ot400/OT400M04M1_1SCC301279F0001.dxf", "1SCC301279F0001", "A", "dibujo mecánico OT400M04M1; DXF 2D; ABB lo entrega con extensión DWG"),
        ("ot400/OT315_400E04.igs", "OT315-400E04.IGS", "-", "modelo 3D familia OT315-OT400E04; IGS"),
    ],
}

for item in data["items"]:
    item["cadFiles"] = []
    for relative, document_id, revision, description in files.get(item["model"], []):
        path = ROOT / "cad" / "abb" / relative
        payload = path.read_bytes()
        item["cadFiles"].append({
            "path": "cad/abb/" + relative,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "abbDocumentId": document_id,
            "revision": revision,
            "description": description,
            "source": "https://search.abb.com/library/Download.aspx?Action=Launch&DocumentID=" + document_id + "&DocumentPartId=&DocumentRevisionId=" + revision + "&LanguageCode=en",
        })

data["cadFilesDownloaded"] = sum(len(item["cadFiles"]) for item in data["items"])
INVENTORY.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Inventario: {data['cadFilesDownloaded']} archivos CAD registrados")
