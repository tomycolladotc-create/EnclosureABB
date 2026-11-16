# ESTADO — Topográficos de tableros ABB
> Foto actual del proyecto. Se reescribe (no se acumula). El historial va en BITACORA.md.
> Actualizado: 2026-11-15 23:06 · Codex

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
- El repositorio es la fuente única de verdad: toda actualización debe quedar commiteada y subida durante la misma sesión.
- Después de cambios grandes o antes de que termine una sesión, actualizar `ESTADO.md` y `BITACORA.md`. Los agentes resuelven autónomamente las decisiones técnicas ordinarias y consultan solo decisiones materiales o datos no inferibles.

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
- Editor funcionando con el TS4: importa, edita, rieles por envolvente, zoom, DXF/PNG/SVG/PDF con colores. Un proyecto por tablero (`proyectos.py`), accesorios y normativa (`accesorios.py`, `normativa.py`), ubicación en riel (`colocar.py`).
- **Armado automático** (`layout_auto.py`, botón 'Armar tablero automático', ruta `/api/autolayout`): elige el gabinete más chico del catálogo donde entra el contenido y acomoda seccionadores, equipos de kit y equipos de riel. Criterios en `datos/reglas_layout.json` (**propuestas de diseño, no datos de ABB**). TS4 hoy cae en SR2 SRN12630K (1200×600×300) con riel GD4006.
- **Gabinetes en `datos/catalogo_abb.json -> enclosures`** (31): 8 de estructura System pro E power 185 (catálogo ABB 1STC803009D0103, `structure` con banda 50 mm, hojas de puerta, lista de partes con página) y 23 SR2 monobloc con puerta ciega (catálogo ABB 1STC804013D0201 de 2011; externo = nominal + 3 mm; placa interna = (ancho-40)×(alto-40); `railOptions` GD4006/6006/8006). Cada gabinete trae `functionalOffset` y `railOptions`. Colores RAL 7035 (gabinete) y RAL 7012 (zócalo, sólo System pro E); hex aproximados.
- Los PDF de catálogo están en el repo: `docs/catalogos_abb/` (más el texto por página en `texto/`), registrados en `datos/fuentes_descargadas.json`. **Regla del usuario: todo lo que se descargue o actualice se sube al repo y se anota en ese registro.**
- Modelo de datos: **carcasa** (geometría CAD, `deviceShells`) ≠ **serie** (qué modelos la usan, `series`) ≠ **marcado** (lo impreso en el frente: `apariencias_abb.json -> marking`). Marcado frontal cargado para S200, S800, XT1, XT2 y logo visible de OT400; carcasas por polo (`poleModule`, S200): 2P-4P = polos repetidos.
- **Cubre 167 de 206 equipos** de los 6 unifilares. Faltan: S293, SN201L, XT3S, S251 (asignada por hipótesis a S201 NA), OT varios, T2S/T4S, E2.2N, S803S (ver `docs/cobertura_unifilares.md`).
- Series sin confirmar con fuente (`verified: false`): XT1 y XT2 para todas las versiones de poder de corte.
- Pruebas: 67, `python -m unittest discover tests`. Correrlas antes de cada push.

## Pendiente (anotarse con [Claude] / [Codex] antes de empezar)
12. **BOM y revisiones completadas:** `bom.py` agrupa envolvente, estructura, rieles, equipos, kits y accesorios; exporta CSV UTF-8/Excel y dibuja la tabla en la capa DXF `ABB_BOM`. `revisiones.py` emite revisiones numéricas con fecha, descripción y responsable, persistidas en el JSON del proyecto y mostradas en Exportar/DXF. TS4 genera 18 renglones agrupados. No se tocaron datos ni geometría KD de Claude.
11. **Seguridad y validación completadas:** autoguardado con borrador local recuperable, indicador Guardado/Cambios pendientes/Error, advertencia al salir, deshacer/rehacer y validación visual/manual. `validacion.py` controla superposición, límites de placa, posición/capacidad de riel y profundidad; si falta el dato ABB emite advertencia sin inventarlo. Reglas en `datos/reglas_validacion.json`, ruta `/api/validate` y pruebas dedicadas. No modifica la geometría KD asignada a Claude.
10. **Interfaz de cuatro pasos completada:** la maqueta Claude Artifact ya está implementada en el editor real como Tableros → Importar → Editor → Exportar. Usa las API existentes de proyectos, importación, edición y exportación; estilos separados en `web/styles.css` y contrato básico en `tests/test_web_ui.py`.
0. **Rieles DIN según el gabinete (hecho para SR2 con kit KD, 2026-11-15):** `kdKit` en cada SR2 que tiene kit (11 gabinetes: KD5040K…KD1280K, filas de 185 mm, módulos por fila, pág. 2/4 del catálogo 1STC804013D0201). `layout_auto` usa esas filas fijas (`fixed:true`, largo = módulos x 17,5 mm), apiladas contiguas abajo de la placa; si no entra en el kit, prueba el gabinete siguiente. Botón 'Armar con riel libre (GD)' (`/api/autolayout?free=1`) usa riel GD de posición propuesta; el resumen informa si existe una alternativa más chica así. **Supuestos marcados en `kdKit.assumptions`** (el catálogo no da): ancho de soportes laterales, altura de arranque de las filas, altura del riel dentro de la fila. Pendiente: System pro E (rieles PDRS0600, posición no fijada), XT/OT sobre placa (sin kit de montaje).

0b. **Peines y canaletas visibles (2026-11-16):** los peines se dibujan apoyados sobre la cara superior de los equipos (cuerpo + una clavija de cobre por polo; altura visible = `alturaMm`/`anchoMm` del catálogo, esquemática). Canaletas: `wiringDucts` en `accesorios_abb.json` (22 secciones 15x17…120x80 con códigos 1SL90../1SL91.., pág. 6/5 del catálogo SR2); `accesorios._propose_ducts` las propone horizontales arriba y abajo de cada fila de riel en el hueco libre (criterios en `reglas_layout.json`: ductClearanceMm, ductMaxWidthMm, ductPreferredDepthMm, ductEdgeMm, ductSlot; son de diseño, no de ABB). Capas DXF `ABB_CANALETAS` y `ABB_PEINES`; salen en la BOM. **Pendiente:** canaletas verticales a los costados, dimensionar por llenado (faltan secciones de cables), línea termoplástica RAL 7030 (pág. 6/6), elegir ranura 4x6/8x12 desde el editor, mover/borrar una canaleta a mano.
1. Marcado frontal completado para XT1 y XT2 (ABB, SACE Tmax, serie, bastidor, disparador e In) y para el logo visible del OT400. Imágenes oficiales guardadas en `docs/imagenes_abb/` y registradas; la foto OT no muestra modelo/corriente en el frente, por eso no se inventan. Falta cotejar en equipo real los textos pequeños y obtener una vista frontal de mayor resolución si ABB la publica.
2. **Robustez/funcionalidad completada:** el editor crea proyectos vacíos con la envolvente ABB elegida, duplica el tablero completo y borra proyectos; TS4 queda protegido. La ubicación automática ya cubre riel y kit, pero los kits de montaje XT/OT no tienen CAD ni medidas.
3. **Profundidades reales** de XT, OT400, S800 para validar el gabinete (hoy la regla `minDepthForKitDevicesMm: 200` es criterio propio).
4. **Gabinetes que faltan cargar**: SR2 con puerta vidriada (VK), zócalos ZA...., IS2 (de piso, pág. 4/ del catálogo), AM2. Verificar disponibilidad en Argentina de los SR2 (no verificada).
5. **Estructura System pro E**: montantes de 2200: PUPM2100 (págs. 20 y 23) o PUPM2001 (pág. 24), conflicto sin resolver; no hay CAD de montantes, bisagras ni manijas (PHLS0013 sin posición); STEP de la estructura (ABB publica kits 1STD...); kits de montaje XT están en el catálogo de tableros modulares, no en estos dos.
6. Peines y barras (completado 2026-11-15 con fuentes en `datos/accesorios_abb.json`): PS1/4, PS1/60, PS2/12 (1P+N), PS3/60, PS4/12 y S803-BB250 (S800, 3 fases, 250 A) con corriente y datos; barras de cobre AA8010 (SR2, 320 A, **neutro/tierra** según catálogo) y PBFC2005. Medidas de PS1/4, PS1/60, PS3/60 y PS4 cargadas desde fichas ABB. Faltan: Icw del PS2; peine con neutro para S804 (4 polos); barra de **fase** dimensionada (IEC 61439); CAD de accesorios; disponibilidad en Argentina de cada código.
   - Propuesta y decisión: bloque o barra de distribución se **proponen** (`needsConfirmation`) y el usuario confirma o descarta en el panel de normativa (`decision`); `accesorios.complete()` conserva la decisión al recalcular; el DXF omite las descartadas y rotula 'PROPUESTA SIN CONFIRMAR' las pendientes. El límite de corriente de peines considera sólo peines compatibles con S200 (antes incluía Schneider 80 A por error).
7. Normativa: las reglas siguen 'por-verificar'; hace falta el texto oficial AEA 90364 / IEC 61439.
8. Familias faltantes (no prioritario; OT quedan así por ahora): primero ver si comparten carcasa con una existente. Manija y eje del OT400E04P. QF89 S251: confirmar con ABB Argentina que S251 Na = S201 NA.
9. Sacar textos fijos del TS4 en `generar_topografico.py` (notas de la lámina). Validar con ABB Argentina gabinete, rieles y kits; cerrar BOM.

## Diseño de la interfaz (aprobado provisoriamente por el usuario; se ajustará con el uso)
- Maqueta de 4 pantallas (Tableros, Importar, Editor, Exportar) en https://claude.ai/artifact/GJvAU9SANz5x9u69j9mra2. Implementada en el editor real (`web/index.html` + `web/styles.css`) el 2026-11-15.
- Flujo real: Tableros administra proyectos y envolventes; Importar revisa el PDF; Editor conserva el SVG interactivo y normativa; Exportar prioriza DXF y resume capas, gabinete y equipos. Pendiente independiente: rieles según kit del gabinete (punto 0).
