"""Compila el ejecutable Windows (--onedir), el instalador Inno Setup y el ZIP portable.

Uso:
    python packaging/build_exe.py [--version 1.0.0]

Salidas (todas en salida/instalador/, fuera de git):
    - salida/dist/EnclosureABB/EnclosureABB.exe      (carpeta ejecutable)
    - salida/instalador/EnclosureABB-Setup.exe       (instalador Windows sin permisos de Admin)
    - salida/instalador/EnclosureABB-Portable.zip    (versión portable USB con portable.flag)
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_BUILD = ROOT / "salida" / "build_exe"
OUT_DIST = ROOT / "salida" / "dist"
OUT_INST = ROOT / "salida" / "instalador"
PRECOMP = ROOT / "datos" / "frentes_resueltos.json.gz"


def build_icon():
    import runpy
    runpy.run_path(str(ROOT / "packaging" / "make_icon.py"), run_name="__main__")


def build_precomputed_fronts():
    """Precalcula pintura.resolve en datos/frentes_resueltos.json.gz para evitar OpenCV en runtime."""
    import app
    import rutas

    fronts, appearances = app.resolved_drawing_data()
    payload = {
        "stamp": rutas.drawing_sources_stamp(),
        "fronts": fronts,
        "appearances": appearances,
    }
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    with gzip.open(PRECOMP, "wb", compresslevel=6) as fh:
        fh.write(raw)
    print(f"Frentes precalculados: {PRECOMP.name} ({PRECOMP.stat().st_size / 1024:.1f} KB)")


def run_pyinstaller():
    OUT_BUILD.mkdir(parents=True, exist_ok=True)
    OUT_DIST.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--workpath", str(OUT_BUILD),
        "--distpath", str(OUT_DIST),
        str(ROOT / "packaging" / "enclosure_abb.spec"),
    ]
    print("Ejecutando PyInstaller...")
    subprocess.run(cmd, cwd=str(ROOT), check=True)
    exe = OUT_DIST / "EnclosureABB" / "EnclosureABB.exe"
    assert exe.is_file(), f"No se generó {exe}"
    total_b = sum(p.stat().st_size for p in (OUT_DIST / "EnclosureABB").rglob("*") if p.is_file())
    print(f"Ejecutable OK: {exe} (carpeta total: {total_b / 1048576:.1f} MB)")


def find_iscc() -> Path | None:
    candidates = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    ]
    for p in candidates:
        if p.is_file():
            return p
    found = shutil.which("iscc")
    return Path(found) if found else None


def build_installer(version: str) -> Path | None:
    iscc = find_iscc()
    if not iscc:
        print("AVISO: Inno Setup (ISCC.exe) no encontrado; se omite EnclosureABB-Setup.exe")
        return None
    OUT_INST.mkdir(parents=True, exist_ok=True)
    cmd = [str(iscc), f"/DAppVersion={version}", str(ROOT / "packaging" / "enclosure_abb.iss")]
    print("Compilando instalador con Inno Setup...")
    subprocess.run(cmd, cwd=str(ROOT), check=True)
    setup_exe = OUT_INST / "EnclosureABB-Setup.exe"
    assert setup_exe.is_file(), f"No se generó {setup_exe}"
    print(f"Instalador OK: {setup_exe} ({setup_exe.stat().st_size / 1048576:.1f} MB)")
    return setup_exe


def build_portable_zip() -> Path:
    OUT_INST.mkdir(parents=True, exist_ok=True)
    zip_path = OUT_INST / "EnclosureABB-Portable.zip"
    if zip_path.exists():
        zip_path.unlink()
    src_dir = OUT_DIST / "EnclosureABB"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in sorted(src_dir.rglob("*")):
            if p.is_file():
                zf.write(p, f"EnclosureABB/{p.relative_to(src_dir).as_posix()}")
        zf.writestr("EnclosureABB/portable.flag", "Modo portable: los tableros se guardan en ./datos_usuario/\n")
    print(f"ZIP portable OK: {zip_path} ({zip_path.stat().st_size / 1048576:.1f} MB)")
    return zip_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="1.0.0")
    args = parser.parse_args()

    build_icon()
    build_precomputed_fronts()
    try:
        run_pyinstaller()
    finally:
        # El cache precalculado es un artefacto de compilación: no queda ensuciando datos/ en el repo
        if PRECOMP.exists():
            PRECOMP.unlink()
    build_installer(args.version)
    build_portable_zip()
    print("\nCOMPILACION COMPLETA.")


if __name__ == "__main__":
    main()
