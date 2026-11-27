"""Resolución central de rutas (modo desarrollo y ejecutable empaquetado).

- Recursos de solo lectura (datos/*.json, web/): en desarrollo viven junto al código;
  en el ejecutable empaquetado viven dentro de sys._MEIPASS.
- Datos del usuario (proyectos/, formatos/): en desarrollo siguen en datos/ (o
  ABB_PROJECTS_DIR / ABB_FORMATS_DIR en pruebas); en el ejecutable viven en
  %LOCALAPPDATA%/EnclosureABB (o ./datos_usuario junto al .exe si existe portable.flag),
  así las actualizaciones del programa nunca pisan los tableros del usuario ni piden
  permisos de Administrador.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

IS_FROZEN = bool(getattr(sys, "frozen", False))
BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
EXE_DIR = Path(sys.executable).resolve().parent if IS_FROZEN else Path(__file__).resolve().parent
DATA_DIR = BUNDLE_ROOT / "datos"
WEB_DIR = BUNDLE_ROOT / "web"


def user_data_dir() -> Path:
    if not IS_FROZEN:
        return DATA_DIR
    custom = os.environ.get("ENCLOSUREABB_DATA_DIR")
    if custom:
        return Path(custom)
    if (EXE_DIR / "portable.flag").exists():
        return EXE_DIR / "datos_usuario"
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    return (Path(base) if base else Path.home()) / "EnclosureABB"


def projects_dir() -> Path:
    env = os.environ.get("ABB_PROJECTS_DIR")
    return Path(env) if env else user_data_dir() / "proyectos"


def formats_dir() -> Path:
    env = os.environ.get("ABB_FORMATS_DIR")
    return Path(env) if env else user_data_dir() / "formatos"


def data_file(name: str) -> Path:
    return DATA_DIR / name


def read_json(name: str):
    return json.loads(data_file(name).read_text(encoding="utf-8"))


def drawing_sources_stamp() -> str:
    """Huella SHA-256 de frentes + apariencias + catálogo para validar frentes_resueltos.json.gz."""
    h = hashlib.sha256()
    for name in ("frentes_cad.json", "apariencias_abb.json", "catalogo_abb.json"):
        p = data_file(name)
        if p.exists():
            h.update(p.read_bytes())
    return h.hexdigest()
