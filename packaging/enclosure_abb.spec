# -*- mode: python ; coding: utf-8 -*-
"""Especificación PyInstaller (--onedir, bajo consumo de RAM, sin consola) para EnclosureABB."""
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent
DATOS = ROOT / "datos"
WEB = ROOT / "web"

# Sólo archivos de catálogo/reglas/frentes (nunca datos/proyectos ni datos/formatos del usuario)
data_files = [
    (str(p), "datos")
    for p in sorted(DATOS.iterdir())
    if p.is_file() and p.suffix in (".json", ".gz", ".ico")
]
data_files += [
    (str(WEB / "index.html"), "web"),
    (str(WEB / "styles.css"), "web"),
]

hidden = [
    "app",
    "rutas",
    "accesorios",
    "auditoria",
    "bom",
    "cad_export",
    "colocar",
    "entrega_pdf",
    "etiquetas",
    "excel_equipamiento",
    "importador",
    "layout_auto",
    "marcado",
    "normativa",
    "pintura",
    "plano_unifilar",
    "proyectos",
    "revisiones",
    "taller",
    "validacion",
    "verificacion_unifilar",
    "pypdf",
    "openpyxl",
    "pymupdf",
    "ezdxf",
    "ezdxf.addons.drawing",
    "ezdxf.addons.drawing.svg",
    "ezdxf.addons.drawing.properties",
    "ezdxf.addons.importer",
]

excludes = [
    # OpenCV no hace falta en runtime: frentes_resueltos.json.gz se precalcula al compilar (~60 MB menos)
    "cv2",
    # Extras pesados de pymupdf 2.x que el editor no usa (~100 MB menos)
    "onnxruntime",
    "pymupdf_layout",
    "pymupdf4llm",
    "networkx",
    "tabulate",
    "yaml",
    "psutil",
    "lxml",
    # Otras dependencias de desarrollo / herramientas no usadas por el editor
    "cairosvg",
    "cairocffi",
    "matplotlib",
    "scipy",
    "pandas",
    "tkinter",
    "_tkinter",
    "pytest",
    "playwright",
    "IPython",
    "jupyter",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6",
    "wx",
    "webview",
]

a = Analysis(
    [str(ROOT / "escritorio.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=data_files,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)

def _keep_entry(entry):
    dest = str(entry[0]).replace("\\", "/").lower()
    # Quitar modelos ONNX de pymupdf/layout (~45 MB) y headers/libs C++ mupdf-devel (~8 MB) no usados en runtime
    if "pymupdf/layout/" in dest or "pymupdf/mupdf-devel/" in dest:
        return False
    return True


a.datas = [e for e in a.datas if _keep_entry(e)]
a.binaries = [e for e in a.binaries if _keep_entry(e)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="EnclosureABB",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(DATOS / "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="EnclosureABB",
)
