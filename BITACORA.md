# BITÁCORA
> Una entrada por sesión, **la más nueva arriba**, máximo 6 líneas. Al empezar, leer solo las 3 primeras.
> Si pasa de 15 entradas, mover las viejas a `docs/bitacora_vieja.md`.
> Formato: `## fecha hora · agente` + Hecho / Archivos / Ojo / Siguiente.

## 2026-11-15 18:30 · Claude
- Hecho: carcasa ≠ serie ≠ inscripción. `series` en el catálogo (con polos y fuente ABB); S200 por polo (2P-4P repitiendo el frente 1P, proyectado del STEP S200M 1P). Inscripción del modelo en pantalla y DXF (atributo MODELO). Cobertura 41 → 167 de 206.
- Archivos: `datos/catalogo_abb.json`, `datos/apariencias_abb.json` (inscription), `datos/frentes_cad.json` (+s200m.1p), `importador.py`, `cad_export.py`, `web/index.html`, `app.py`, `work/proyectar_cad.py`, tests.
- Ojo: quité la etiqueta de modelo debajo de cada equipo (se superponía; ahora va grabada). XT1/XT2 multiversión sin confirmar.
- Siguiente: separar lámina GENERAL por tablero y un proyecto por tablero.

## 2026-11-15 17:45 · Claude
- Hecho: importador ahora usa el catálogo (sin modelos en el código) y lee polos de "I Nom - Icc"; ya no asigna carcasa 4P a equipos 3P. Pruebas con 6 unifilares reales + TS4 (7/7 OK). Informe de cobertura.
- Archivos: `importador.py` (nuevo), `app.py`, `datos/catalogo_abb.json` (importRules, match, modelHints), `web/index.html` (isDin), `tests/`, `work/cobertura_catalogo.py`, `docs/cobertura_unifilares.md`.
- Ojo: QF1 del GENERAL (E2.2N) no trae polos en el plano: se marca, no se inventa. La lámina GENERAL mezcla tableros.
- Siguiente: familias faltantes del catálogo (pendiente 1), empezando por S201L 1P+N.

## 2026-11-15 17:20 · Claude
- Hecho: repo creado desde la carpeta de Codex; CAD ABB subidos (SHA-256 verificados); corregido DXF (rellenos de color salían como triángulos cruzados).
- Archivos: todo el repo; `cad_export.py`; `.gitattributes` (CAD como binarios).

## 2026-11-15 13:46–17:00 · Codex
- Hecho: arquitectura, catálogo inicial, editor local, rieles por envolvente, 12 CAD ABB descargados, frentes 2D proyectados desde STEP, colores por familia, DXF con bloques. Caso de referencia: TS4-PORT 11-12-13-14.
- Detalle: `docs/ARQUITECTURA.md`, `docs/estado_busqueda_CAD_TS4.md`.
