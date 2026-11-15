# ESTADO — Topográficos de tableros ABB
> Foto actual del proyecto. Se reescribe (no se acumula). El historial va en BITACORA.md.
> Actualizado: 2026-11-15 19:00 · Claude

## Objetivo
PDF de unifilar de ABB e-Design DOC → topográfico (vista frontal 2D) del tablero con dispositivos y envolvente ABB reales → editar en interfaz → exportar DXF (AutoCAD, 1:1 mm, bloques y capas), PNG, SVG, PDF.

## Reglas del usuario (no romper)
- Nada hardcodeado: lo específico va en `datos/*.json`; código en módulos con comentarios de ayuda.
- Medidas de equipos fijas (no editables). Rieles DIN definidos por la envolvente elegida.
- Solo ABB y solo lo que se vende en Argentina; si no está la variante exacta, la más común, y anotarlo.
- Bloques desde CAD oficial ABB, con colores y marcado idénticos al equipo real (medido en fotos frontales ABB). No inventar datos: cada dato con fuente y estado.
- **Normativa argentina (requisito del usuario)**: todo tablero debe cumplir lo vigente (AEA 90364, IEC 61439). Reglas en `datos/normativa_argentina.json` con fuente y estado (todas 'por-verificar' hasta confirmar con el texto oficial). Hecho: `normativa.py` (control, `python normativa.py [proyecto.json]`) y `datos/accesorios_abb.json` inicial. Los accesorios genéricos (peines, bornes y barras PE/N, tapas) pueden ser de cualquier marca con equivalente (decisión del usuario). Hecho también: `accesorios.py` propone bornes de tierra (uno por QF, en hueco libre del riel), cubrebornes y peines entre S200 contiguos; panel 'Normativa argentina' en el editor (botones Completar/Revisar); el DXF dibuja los accesorios (capa ABB_ACCESORIOS) y escribe los avisos en ABB_NOTAS. Falta: dibujo real (CAD) de peines y bornes, bloques de distribución en el layout (corrientes altas), peines S800, elegir versión PS3/12, confirmar Argentina, pantalla Normativa en la maqueta.
- **Nada monopolar**: mínimo bipolar (1P+N cuenta como 2 polos). `catalogo_abb.json -> scope.minPoles`.
- Diseño pensado de entrada para que los cambios futuros sean chicos. Usar modelos de IA livianos.

## Estructura
| Ruta | Qué es |
|---|---|
| `app.py` | servidor del editor (`iniciar_editor.bat` → http://127.0.0.1:8765) |
| `importador.py` | lee el PDF y propone equipos; reglas en `catalogo_abb.json`: `importRules`, `series` (modelo → carcasa, con polos y fuente), `modelHints` |
| `cad_export.py` | exporta DXF con bloques por familia |
| `web/index.html` | interfaz |
| `datos/` | catálogo ABB, colores (`apariencias_abb.json`), bloques 2D (`frentes_cad.json`), inventario CAD (`cad_argentina.json`), proyecto TS4 |
| `cad/abb/` | CAD originales ABB → `work/proyectar_cad.py` → `datos/frentes_cad.json` |
| `tests/` | `python -m unittest discover tests` · 6 unifilares reales en `tests/unifilares/` |
| `work/cobertura_catalogo.py` | genera `docs/cobertura_unifilares.md` (familias que faltan) |

## Situación
- Editor funcionando con el TS4: importa, edita, rieles por envolvente, zoom, DXF/PNG/SVG/PDF con colores.
- Envolvente: ABB System pro E power 185 (1000×2100×500 funcional). Rieles y kits: posición **preliminar**.
- Modelo de datos: **carcasa** (geometría CAD, `deviceShells`) ≠ **serie** (qué modelos la usan, `series`) ≠ **marcado** (lo impreso en el frente: `apariencias_abb.json -> marking`, posiciones en mm medidas en fotos ABB; los datos variables salen del plano; en el DXF son atributos del bloque). Carcasas por polo (`poleModule`, S200): 2P-4P = polos repetidos.
- **Cubre 167 de 206 equipos** de los 6 unifilares. Faltan: S293, SN201L, XT3S, S251, OT varios, T2S/T4S, E2.2N, S803S (ver `docs/cobertura_unifilares.md`).
- Series sin confirmar con fuente (`verified: false`): XT1 y XT2 para todas las versiones de poder de corte.

## Pendiente (anotarse con [Claude] / [Codex] antes de empezar)
0. Marcado hecho para S200 (2P-4P, 1P+N) y S800. Falta medir foto frontal de XT1, XT2 y OT400 (sin `marking` no se imprime nada).
1. Robustez/funcionalidad (prioridad del usuario): separar la lámina GENERAL por tablero; un proyecto por tablero (hoy `app.py` guarda siempre en `datos/ts4_topografia.json`); ubicación automática de los equipos importados en rieles/kits.
2. Familias faltantes (no prioritario; OT quedan así por ahora): primero ver si comparten carcasa con una existente.
3. Manija y eje del OT400E04P. QF89 S251: CAD o reemplazo actual vendido en Argentina.
4. Sacar textos fijos del TS4 en `generar_topografico.py` (notas de la lámina).
5. Validar con ABB Argentina gabinete, rieles y kits; cerrar BOM.

## Diseño de la interfaz (aprobado provisoriamente por el usuario; se ajustará con el uso)
- Maqueta de 4 pantallas (Tableros, Importar, Editor, Exportar) en un lienzo de diseño de claude.ai: https://claude.ai/artifact/GJvAU9SANz5x9u69j9mra2 (la ve solo el usuario). No es código: el editor real (`web/index.html`) todavía no la sigue.
- Orden previsto: 1) un proyecto por tablero + lista de proyectos, 2) separar la lámina GENERAL, 3) colocar equipos automáticamente en rieles, 4) llevar la maqueta al editor real.
