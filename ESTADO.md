# ESTADO — Topográficos de tableros ABB
> Foto actual del proyecto. Se reescribe (no se acumula). El historial va en BITACORA.md.
> Actualizado: 2026-11-26 · Antigravity

## Objetivo
PDF de unifilar de ABB e-Design DOC → topográfico (vista frontal 2D) del tablero con dispositivos y envolvente ABB reales → editar en interfaz → exportar DXF (AutoCAD, 1:1 mm, bloques y capas), PNG, SVG, PDF.

- **Testigos de fase en la puerta** (⋯ → «Testigos de fase en la puerta»): luces y portafusibles E 91/32 con código. Los fusibles van como genéricos en la lista, con formato, clase, calibre y cantidad.

## Reglas del usuario (no romper)
- **Programa 100 % genérico (2026-11-26)**: el repositorio contiene únicamente el programa genérico, catálogo ABB, reglas, documentación técnica y pruebas; no se suben entregas, informes ni referencias a obras o clientes particulares.
- **No repetir errores**: `docs/LECCIONES.md` + auditoría (`auditoria.py`) en 0 errores antes de entregar un tablero (2026-11-19).
- Nada hardcodeado: lo específico va en `datos/*.json`; código en módulos con comentarios de ayuda.
- Medidas de equipos fijas (no editables). Rieles DIN definidos por la envolvente elegida.
- Solo ABB y solo lo que se vende en Argentina; si no está la variante exacta, la más común, y anotarlo.
- Bloques desde CAD oficial ABB, con colores y marcado idénticos al equipo real (medido en fotos frontales ABB). No inventar datos: cada dato con fuente y estado.
- **Normativa argentina (requisito del usuario)**: todo tablero debe cumplir lo vigente (AEA 90364, IEC 61439). Reglas en `datos/normativa_argentina.json` con fuente y estado (todas 'por-verificar' hasta confirmar con el texto oficial). Hecho: `normativa.py` (control, `python normativa.py [proyecto.json]`) y `datos/accesorios_abb.json` inicial. Los accesorios genéricos (peines, bornes y barras PE/N, tapas) pueden ser de cualquier marca con equivalente (decisión del usuario). Hecho también: `accesorios.py` propone bornes de tierra (uno por QF, en hueco libre del riel), cubrebornes y peines entre S200 contiguos; panel 'Normativa argentina' en el editor (botones Completar/Revisar); el DXF dibuja los accesorios (capa ABB_ACCESORIOS) y escribe los avisos en ABB_NOTAS. Falta: dibujo real (CAD) de peines y bornes, bloques de distribución en el layout (corrientes altas), peines S800, elegir versión PS3/12, confirmar Argentina, pantalla Normativa en la maqueta.
- **Nada monopolar**: mínimo bipolar (1P+N cuenta como 2 polos). `catalogo_abb.json -> scope.minPoles`. Si el usuario pide cambiar un equipo de un unifilar puntual: `datos/correcciones_unifilar.json` (tablero + etiqueta + modelo del PDF); nunca editar el PDF ni el proyecto a mano.
- **Lista de materiales (2026-11-25)**: selector **ABB / Genérica** en pantalla, CSV, Excel y PDF de entrega (`datos/reglas_bom_generico.json`). Los interruptores abiertos (ACB) **nunca son extraíbles** (siempre versión fija, sin aviso a confirmar). En modo genérico el gabinete indica solo material y dimensiones.
- **Probar como usuario final en cada sesión** y anotar errores/mejoras en `docs/MEJORAS.md`: producto fácil, útil, confiable.
- Diseño pensado de entrada para que los cambios futuros sean chicos. Usar modelos de IA livianos.
- El repositorio es la fuente única de verdad: toda actualización debe quedar commiteada y subida durante la misma sesión.
- Después de cambios grandes o antes de que termine una sesión, actualizar `ESTADO.md` y `BITACORA.md`. Los agentes resuelven autónomamente las decisiones técnicas ordinarias y consultan solo decisiones materiales o datos no inferibles.

## Estructura
| Ruta | Qué es |
|---|---|
| `rutas.py` | resolución única de rutas (desarrollo vs ejecutable congelado: recursos en `_MEIPASS`, datos de usuario en `%LOCALAPPDATA%\EnclosureABB` o modo portable) |
| `escritorio.py` | lanzador Windows de baja RAM (instancia única, ventana `--app` en Edge/Chrome sin WebView2, autocierre limpio tras cerrar la ventana) |
| `packaging/` | build ejecutable (`build_exe.py`, `enclosure_abb.spec`, `enclosure_abb.iss`, `make_icon.py`) → `EnclosureABB-Setup.exe` y `EnclosureABB-Portable.zip` en `salida/instalador/` |
| `verificacion_unifilar.py` | segunda lectura del unifilar por posición: modelo, polos y corriente de cada equipo contra el plano, al importar |
| `app.py` | servidor del editor (`iniciar_editor.bat` → http://127.0.0.1:8765) |
| `importador.py` | lee el PDF y propone equipos; reglas en `catalogo_abb.json`: `importRules`, `series` (modelo → carcasa, con polos y fuente), `modelHints` |
| `cad_export.py` | exporta DXF con bloques por familia + vista con la puerta cerrada (capas ABB_PUERTA_*) + lista de materiales y controles |
| `bom.py` | lista de materiales anti-error de compra (`build_bom`, `bom_issues`); códigos de equipos en `datos/codigos_pedido_abb.json` (sólo verificados, con URL) |
| `web/index.html` | interfaz |
| `datos/` | catálogo ABB, colores (`apariencias_abb.json`), bloques 2D (`frentes_cad.json`), inventario CAD (`cad_argentina.json`), proyecto TS4 |
| `cad/abb/` | CAD originales ABB → `work/proyectar_cad.py` → `datos/frentes_cad.json` |
| `tests/` | `python -m unittest discover tests` · 6 unifilares reales en `tests/unifilares/` |
| `work/cobertura_catalogo.py` | genera `docs/cobertura_unifilares.md` (familias que faltan) |

## Situación
- **Poder de corte y barras de cobre/PE (2026-11-26)**: auditoría A16 (`breaking_capacity_low`) contrasta `Icn/Icu` de cada interruptor contra `Ik 3F / Ik 1F` de las barras (`project.busbar`); `accesorios.propose` ubica y dibuja en editor/DXF barras principales de cobre (`PPHC2593` + neutro `PPHC2119`, 2.000 A) y barras colectoras PE (`ZXPHC218` 40×10 / `AA8010` 20×5 + `AA8011`) con cómputo ABB y genérico. Auditoría de nombres de alimentadores (`audit_feeder_names`) entre tablero padre e hijo.
- Editor funcionando con el TS4: importa, edita, rieles por envolvente, zoom, DXF/PNG/SVG/PDF con colores. Un proyecto por tablero (`proyectos.py`), accesorios y normativa (`accesorios.py`, `normativa.py`), ubicación en riel (`colocar.py`).
- **Armado automático** (`layout_auto.py`, botón 'Armar tablero automático', ruta `/api/autolayout`): elige el gabinete más chico del catálogo donde entra el contenido y acomoda seccionadores, equipos de kit y equipos de riel. Criterios en `datos/reglas_layout.json` (**propuestas de diseño, no datos de ABB**). TS4 hoy cae en SR2 SRN12630K (1200×600×300) con riel GD4006.
- **Gabinetes en `datos/catalogo_abb.json -> enclosures`** (31): 8 de estructura System pro E power 185 (catálogo ABB 1STC803009D0103, `structure` con banda 50 mm, hojas de puerta, lista de partes con página) y 23 SR2 monobloc con puerta ciega (catálogo ABB 1STC804013D0201 de 2011; externo = nominal + 3 mm; placa interna = (ancho-40)×(alto-40); `railOptions` GD4006/6006/8006). Cada gabinete trae `functionalOffset` y `railOptions`. Colores RAL 7035 (gabinete) y RAL 7012 (zócalo, sólo System pro E); hex aproximados.
- Los PDF de catálogo están en el repo: `docs/catalogos_abb/` (más el texto por página en `texto/`), registrados en `datos/fuentes_descargadas.json`. **Regla del usuario: todo lo que se descargue o actualice se sube al repo y se anota en ese registro.**
- Modelo de datos: **carcasa** (geometría CAD, `deviceShells`) ≠ **serie** (qué modelos la usan, `series`) ≠ **marcado** (lo impreso en el frente: `apariencias_abb.json -> marking`). Marcado frontal cargado para S200, S800, XT1, XT2 y logo visible de OT400; carcasas por polo (`poleModule`, S200): 2P-4P = polos repetidos.
- **Plano GENERAL (24 tableros)**: todos los equipos de 2+ polos tienen frente; el S 293-C 80 (S290, sin CAD en ABB Library) usa el dibujo vectorial del catálogo ABB NN31/05_04. Carcasas 2026-11-19: E2.2, XT3, XT1 3P, T4, T2, S803, OT63/80F.
- Series sin confirmar con fuente (`verified: false`): XT1 y XT2 para todas las versiones de poder de corte.
- **Pintura de los frentes (2026-11-19)**: los colores se ponen sobre las superficies cerradas del CAD (semillas, `pintura.cad_regions`); el servidor resuelve todo (`pintura.resolve` → `/api/fronts`, `/api/appearances`) y la pantalla y el DXF dibujan lo mismo. Etiquetas con letra mínima (`etiquetas.label_boxes`, misma regla en el editor). Encuadre de exportación medido sobre lo dibujado.
- **Plano de fabricación** (2026-11-22): `python3 plano_unifilar.py formato.dxf carpeta_proyectos salida.dxf [tableros]` → unifilar del usuario + topográfico (puerta abierta/cerrada) en su formato. En la interfaz: Exportar → «Plano de fabricación» (carga el formato una vez, se completa el rótulo por cliente antes de generar, sale DXF sólo con las hojas elegidas).
- **Ejecutable Windows de baja RAM (2026-11-26)**: `python packaging/build_exe.py` genera `salida/instalador/EnclosureABB-Setup.exe` (38,9 MB, Inno Setup por usuario sin Admin) y `EnclosureABB-Portable.zip` (52,0 MB). Precalcula `frentes_resueltos.json.gz` (elimina OpenCV y ~60 MB de modelos ONNX/headers), usa imports perezosos, bytes JSON directos y ventana `--app` de Edge/Chrome (arranque ~0,9 s, ~34 MB RAM en reposo, autocierre en 4,8 s).
- **Fluidez de edición y espesores DXF/DWG (2026-11-26)**: en el editor (`web/index.html`, `web/styles.css`) los símbolos CAD viven en un `<defs id="boardDefs">` persistente (sin reconstruir el SVG ni disparar validación al arrastrar; movimiento por `transform` en `requestAnimationFrame` a ~0,05 ms/movimiento para equipos y canaletas, con vista previa ligera al estirar canaletas y sin `feDropShadow` por equipo). En DXF/DWG (`datos/reglas_layout.json -> dxfLayers`, `cad_export.py`, `taller.py`, `plano_unifilar.py`), todas las capas, capa `0`, estilo de cotas `EZDXF` y polilíneas `ABB_CAD_FRENTE` llevan espesor explícito (`0,05 / 0,09 / 0,18 mm`) + `$LWDISPLAY=0` y `$CELWEIGHT=9` (0 líneas en `DEFAULT` 0,25 mm; 0 errores `_AUDIT` en AutoCAD 2027).
- Pruebas: 215 unitarias, incluida la regresión de 24 tableros, control A16 de poder de corte, espesores DXF y pruebas de rutas/escritorio, y 136 controles de interfaz. Correr `python -m unittest discover tests` y `python tests/e2e/prueba_interfaz.py` antes de cada push. Las pruebas automáticas usan `ABB_PROJECTS_DIR`, nunca `datos/proyectos`.

## PRÓXIMA SESIÓN — empezar por acá (escrito por Claude, 2026-11-16 01:50)

**Pedido del usuario 2026-11-16 (11:05):** que el tablero se genere SOLO, sin apretar botones: al elegir el PDF en 'Importar' se agregan todos los equipos propios, se arma gabinete/rieles/peines/canaletas y se abre el editor (`web/index.html`, manejador de `#pdf`; `runAuto` devuelve `{ok,error,gabinete}`). Al agregar un equipo a mano ('Agregar equipo' ahora lleva al formulario con etiqueta QF sugerida y campo Circuito) el tablero se rearma solo. Antes el botón 'Agregar equipo' no tenía acción (bug).

**Lo que se hizo en esta tanda (Claude, commits fca97d6 → b5bfb32; 79 pruebas OK):**
1. Medidas de peines PS1/4, PS1/60, PS3/60, PS4/12 desde fichas ABB (`accesorios_abb.json`).
2. Rieles según el kit KD del SR2 (`kdKit` en 11 gabinetes; `layout_auto` usa filas fijas de 185 mm) + botón 'Armar con riel libre (GD)' (`/api/autolayout?free=1`).
3. Arreglos: peine sin corriente (polos deducidos de la carcasa en `accesorios._poles`), bloque de distribución pisaba los bornes PE.
4. Peines visibles (cuerpo + clavija por polo, sobre los equipos) y canaletas propuestas (`wiringDucts`, 22 secciones, págs. 6/5 del catálogo SR2; `accesorios._propose_ducts`; capas DXF ABB_CANALETAS / ABB_PEINES).
5. Nombre de circuito (`circuit`, ej. TS-4.2) en lugar del QF en editor, DXF, BOM y avisos; el QF sigue como `tag` interno. `importador.circuit_name` lo lee del plano; TS4 cargado desde Unifilares-25_GENERAL.pdf.
6. Accesorios SIN texto en dibujo y DXF: la descripción/código/cantidad sale solo en el cómputo de materiales (`accesorios._describe` + `bom.py`: Canaleta, Peine, Borne PE, Riel DIN, Kit de soportes DIN, Bloque, Barra).
7. `iniciar_editor.bat` busca Python en `py`, `python` (ignora el atajo de la Tienda) y `%LOCALAPPDATA%\Programs\Python\Python312`. El usuario ya lo corre en `Descargas\EnclosureABB` (copia mínima de 31 archivos, sin CAD ni PDF).

**Decisiones abiertas con el usuario (preguntar o decidir con criterio):**
- (RESUELTO 2026-11-16 11:30) Separación entre filas con canaleta: `reglas_layout.json` → `railRowGapMm` 110 (peine + etiqueta + portaetiqueta + canaleta + aire) para filas de riel libre; `accesorios._propose_ducts` reserva TAG_ZONE_MM (30) arriba y HOLDER_ZONE_MM (14) abajo de cada equipo. Con kit KD el paso sigue siendo 185 mm.
- El DXF trae la tabla 'LISTA DE MATERIALES' (la armó Codex) y ahora lleva descripciones de accesorios: el usuario pidió accesorios sin texto en el dibujo; decidir si esa tabla queda en el plano o solo en el CSV.
- Archivo `datos/ts4_topografia.json`: el editor lo autoguarda; no commitear cambios accidentales (usar `git status`).

**Tareas, en este orden (anotarse antes con [Claude]/[Codex]):**
1. Probar el editor corriendo en la PC del usuario (`Descargas\EnclosureABB`) y corregir lo que reporte; exportar DXF y abrirlo en AutoCAD (capas, escalas, textos, cotas).
2. Separación de filas con canaletas (ver arriba) y canaletas verticales a los costados (hoy solo horizontales).
3. Editar canaletas a mano en el editor (mover, borrar, cambiar sección y ranura 4x6/8x12).
4. Peine con neutro para S804 (QF81/QF85 siguen 'sin peine'); Icw del PS2/12; corriente de PBFC2005.
5. Profundidades reales de XT/OT/S800 para validar la regla de 200 mm (`minDepthForKitDevicesMm`).
6. System pro E: posición de rieles y estructura (PUPM2100 vs PUPM2001); XT/OT sobre placa (kit de montaje).
7. Normativa AEA 90364 / IEC 61439: cargar texto oficial (hoy todo 'por-verificar').
8. Línea termoplástica RAL 7030 de canaletas (pág. 6/6) y disponibilidad en Argentina de cada código (consultar distribuidor / ABB Argentina).

**Sugerencias de mejora para pensar mañana (no pedidas, a validar con el usuario):**
- Un único botón 'Armar y proponer todo' (gabinete, rieles, peines, canaletas, bornes PE) con una vista previa y un resumen de qué se propuso y por qué.
- Resumen por tablero antes de exportar: gabinete elegido, alternativa más chica, % de ocupación de la placa, reserva (norma suele pedir ~20 % libre) y lista de avisos.
- Comparar gabinetes lado a lado (kit KD vs riel libre) con el tamaño y el costo relativo, para que el usuario elija.
- Hecho (2026-11-23): Exportar → «Excel de equipamiento» (`excel_equipamiento.py`), varios tableros, códigos, cantidades (SUMIFS), circuitos y tableros.
- Duplicar un tablero y reutilizar plantillas (tableros típicos TS, TSB, TSEP) para armar más rápido.
- Distribuir como programa de Windows (.exe) o instalador, para que el usuario no dependa de Python en el PATH.
- Probar con los otros unifilares de `tests/unifilares` (TSB, TSEP, TS_AUX_1, GENERAL) y registrar qué falla; la importación de circuitos cubre la mayoría pero no los alimentadores de cabecera.

## Pendiente (anotarse con [Claude] / [Codex] antes de empezar)
> Lista resumida y priorizada de mejoras, agregados y pendientes: `docs/MEJORAS.md`.
13. **Lista de materiales anti-error y puerta cerrada (Claude, 2026-11-18):** hecho (ver BITACORA). Códigos de pedido: todos los equipos verificados salvo S 251 Na C 10 (no está en el catálogo vigente) y F204-SX (ambiguo); variantes abiertas marcadas «a confirmar» (2026-11-23); carcasas OT/F200/SN201 cargadas (2026-11-18); falta S 293 (sin CAD ABB); color de los pilotos (el unifilar no lo dice: se propone rojo); confirmar si los montantes/travesaños System pro E se venden por unidad o por juego.
12. **BOM y revisiones completadas:** `bom.py` agrupa envolvente, estructura, rieles, equipos, kits y accesorios; exporta CSV UTF-8/Excel y dibuja la tabla en la capa DXF `ABB_BOM`. `revisiones.py` emite revisiones numéricas con fecha, descripción y responsable, persistidas en el JSON del proyecto y mostradas en Exportar/DXF. TS4 genera 18 renglones agrupados. No se tocaron datos ni geometría KD de Claude.
11. **Seguridad y validación completadas:** autoguardado con borrador local recuperable, indicador Guardado/Cambios pendientes/Error, advertencia al salir, deshacer/rehacer y validación visual/manual. `validacion.py` controla superposición, límites de placa, posición/capacidad de riel y profundidad; si falta el dato ABB emite advertencia sin inventarlo. Reglas en `datos/reglas_validacion.json`, ruta `/api/validate` y pruebas dedicadas. No modifica la geometría KD asignada a Claude.
10. **Interfaz de cuatro pasos completada:** la maqueta Claude Artifact ya está implementada en el editor real como Tableros → Importar → Editor → Exportar. Usa las API existentes de proyectos, importación, edición y exportación; estilos separados en `web/styles.css` y contrato básico en `tests/test_web_ui.py`.
0. **Rieles DIN según el gabinete (hecho para SR2 con kit KD, 2026-11-15):** `kdKit` en cada SR2 que tiene kit (11 gabinetes: KD5040K…KD1280K, filas de 185 mm, módulos por fila, pág. 2/4 del catálogo 1STC804013D0201). `layout_auto` usa esas filas fijas (`fixed:true`, largo = módulos x 17,5 mm), apiladas contiguas abajo de la placa; si no entra en el kit, prueba el gabinete siguiente. Botón 'Armar con riel libre (GD)' (`/api/autolayout?free=1`) usa riel GD de posición propuesta; el resumen informa si existe una alternativa más chica así. **Supuestos marcados en `kdKit.assumptions`** (el catálogo no da): ancho de soportes laterales, altura de arranque de las filas, altura del riel dentro de la fila. Pendiente: System pro E (rieles PDRS0600, posición no fijada), XT/OT sobre placa (sin kit de montaje).

0c. **Nombre de circuito y cómputo (2026-11-16):** cada interruptor lleva `circuit` (columna 'Circuito' del unifilar, ej. TS-4.2; el QF queda en `tag` como identificador interno). `importador.circuit_name` lo extrae (celda siguiente al código de uso ACU/TUG/IUG/IUE/TUE/OCE/ALIM, o patrón LETRAS-n.n si no hay código). Editor, DXF, lista de equipos, BOM y avisos de normativa muestran el circuito si existe; en el panel se edita el campo 'Circuito'. **Los accesorios (canaleta, peine, bornes PE, riel DIN, bloque/barra) ya no llevan texto en el dibujo ni en el DXF**: su descripción, código y cantidad salen solo en el cómputo de materiales (`bom.py`, campos `bomCategory`/`description`/`orderCode`/`quantity` que arma `accesorios._describe`). Pendiente: circuitos de otros proyectos importados se leen al importar; proyectos viejos sin `circuit` muestran el QF.

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


### Actualización 2026-11-16 (frontend)
La UI ahora tiene 3 pantallas (Tableros / Editor / Exportar) y el tablero sale ya conforme a normativa (chip de estado en vez de panel Completar/Revisar). Ver BITACORA 12:30. Pendiente de decidir: si el DXF conserva la tabla "LISTA DE MATERIALES".

Antes de entregar cambios de interfaz: `python tests/e2e/prueba_interfaz.py` (61 chequeos en navegador real). Ver BITACORA 13:30.
