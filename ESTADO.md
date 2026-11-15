# ESTADO — Topográficos de tableros ABB
> Foto actual del proyecto. Se reescribe (no se acumula). El historial va en BITACORA.md.
> Actualizado: 2026-11-15 17:45 · Claude

## Objetivo
PDF de unifilar de ABB e-Design DOC → topográfico (vista frontal 2D) del tablero con dispositivos y envolvente ABB reales → editar en interfaz → exportar DXF (AutoCAD, 1:1 mm, bloques y capas), PNG, SVG, PDF.

## Reglas del usuario (no romper)
- Nada hardcodeado: lo específico va en `datos/*.json`; código en módulos con comentarios de ayuda.
- Medidas de equipos fijas (no editables). Rieles DIN definidos por la envolvente elegida.
- Solo ABB y solo lo que se vende en Argentina; si no está la variante exacta, la más común, y anotarlo.
- Bloques desde CAD oficial ABB, con colores reales. No inventar datos: cada dato con fuente y estado.
- Diseño pensado de entrada para que los cambios futuros sean chicos. Usar modelos de IA livianos.

## Estructura
| Ruta | Qué es |
|---|---|
| `app.py` | servidor del editor (`iniciar_editor.bat` → http://127.0.0.1:8765) |
| `importador.py` | lee el PDF y propone equipos; reglas en `catalogo_abb.json` (`importRules`, `deviceShells[].match`, `modelHints`) |
| `cad_export.py` | exporta DXF con bloques por familia |
| `web/index.html` | interfaz |
| `datos/` | catálogo ABB, colores (`apariencias_abb.json`), bloques 2D (`frentes_cad.json`), inventario CAD (`cad_argentina.json`), proyecto TS4 |
| `cad/abb/` | CAD originales ABB → `work/proyectar_cad.py` → `datos/frentes_cad.json` |
| `tests/` | `python -m unittest discover tests` · 6 unifilares reales en `tests/unifilares/` |
| `work/cobertura_catalogo.py` | genera `docs/cobertura_unifilares.md` (familias que faltan) |

## Situación
- Editor funcionando con el TS4: importa, edita, rieles por envolvente, zoom, DXF/PNG/SVG/PDF con colores.
- Envolvente: ABB System pro E power 185 (1000×2100×500 funcional). Rieles y kits: posición **preliminar**.
- Catálogo: 6 carcasas (XT1 4P, XT2 4P, S804N 4P, S201M 1P y 1P+N, OT400E04). **Cubre 41 de 206 equipos** de los 6 unifilares.
- Faltan sobre todo S201L 1P+N (76 equipos), S203, S204, S203M, S293, S201 (ver `docs/cobertura_unifilares.md`).

## Pendiente (anotarse con [Claude] / [Codex] antes de empezar)
1. Agregar familias faltantes al catálogo por orden de cantidad: medidas oficiales + CAD + oferta en Argentina. Aprovechar carcasas compartidas (S200: S201/S201L/S201M/S201P, solo cambia la inscripción, si las medidas lo confirman).
2. Separar la lámina GENERAL (varios tableros en una hoja) en un tablero por bloque.
3. Inscripciones exactas en los frentes.
4. Manija y eje del OT400E04P. QF89 S251: CAD o reemplazo actual vendido en Argentina.
5. Sacar textos fijos del TS4 en `generar_topografico.py` (notas de la lámina).
6. Validar con ABB Argentina gabinete, rieles y kits; cerrar BOM.
