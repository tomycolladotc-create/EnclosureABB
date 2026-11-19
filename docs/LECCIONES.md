# Lecciones aprendidas (errores que no se vuelven a cometer)

> Cada lección tiene: qué pasó, por qué, qué se cambió y **qué lo impide ahora** (regla de `auditoria.py` y/o test).
> La auditoría corre dentro de `validacion.validate()`: la interfaz muestra estos errores al armar o editar un tablero.
> **Regla para quien trabaje en el proyecto (persona o Claude):** antes de entregar tableros, correr la auditoría sobre
> cada uno (ver «Cómo revisar» al final) y dejarla en 0 errores. Si aparece un error nuevo, se agrega acá, se le hace
> una regla en `auditoria.py` y un test en `tests/test_auditoria.py`.

## Revisión de los 24 tableros del plano GENERAL — 2026-11-19

| # | Error encontrado (tableros) | Causa | Corrección | Lo impide |
|---|---|---|---|---|
| 1 | Todos los proyectos nuevos arrastraban datos del TS4 de plantilla: kits PHDX1401/PHDX2401, notas y `source` (24/24) | `proyectos.create` copiaba la plantilla entera | Sólo se hereda la estructura; `TEMPLATE_CONTENT_KEYS` se borran | `stale_template_data` · `test_proyecto_nuevo_no_arrastra_la_plantilla` |
| 2 | Nombre inventado del tablero: «TSB-1», «TA-1», «TSI1-1», «4 5 6» (16/24) | Se armaba con el prefijo de los circuitos o el nombre del archivo | Se lee el rótulo del unifilar (1.ª línea + «DE …»): `importador.detect_board` | `board_name_mismatch` · `test_nombre_del_rotulo_del_unifilar` |
| 3 | Circuitos fuera del orden del unifilar (TSB-1.13 antes que TSB-1.1; TS-1.11 antes que TS-1.2) (9/24) | `layout_auto` ordenaba por carcasa | Se conserva el orden de lectura del unifilar; los peines se arman igual entre contiguos | `order_not_unifilar` · `test_riel_en_orden_de_unifilar` |
| 4 | General del TGBT (E2.2) compartiendo la fila de arriba con el T2 | Sólo se reconocía como general a «QS…» | `auditoria.main_device`: QS, o el que el plano llama PRINCIPAL/GENERAL/SECCIONADOR, o el único sin circuito; va solo arriba | `main_shares_row` · `test_general_solo_en_la_fila_de_arriba` |
| 5 | Seccionador general de riel (OT63/80F) abajo y las cajas moldeadas arriba (TS6) | Las filas de riel siempre iban después de las cajas | Si el general es de riel, su fila va arriba de todo y las cajas debajo | `main_not_on_top` · `test_seccionador_de_riel_va_arriba_de_las_cajas` |
| 6 | Filas sin canaleta arriba o abajo (general del TS1–TS5 y TA-1, filas de cajas del TGBT, filas KD del TSEP) (11/24) | 40 mm de margen/separación: no entraba ninguna canaleta; el kit KD ocupaba toda la placa | `ductBandMm` (canaleta + aire) arriba de la primera fila y entre filas de cajas; las pilas KD dejan esa franja arriba y abajo | `row_without_duct_above/below` |
| 7 | Hueco muerto entre filas (TS6 370 mm, TS4 280 mm) y gabinetes de más | Altura de módulo del kit PHDX (200 mm) aplicada en cajas murales; filas KD fijas abajo | `kitHeight` sólo en System pro E | `dead_gap_between_rows` |
| 8 | Barra de distribución de 320 A en el TGBT de 2000 A; BRT125A con general de 200–400 A (6/24) | La barra se elegía por la salida más grande | Se dimensiona por la corriente del general; si el catálogo no tiene, va a la lista «a dimensionar» | `busbar_undersized` · `test_barra_dimensionada_por_la_entrada` |
| 9 | Lo que no tenía pieza o lugar desaparecía de la lista de materiales | `bom.py` salteaba `placed: false` | Va igual, con aviso «NO está en el dibujo» y sin código | `test_barra_dimensionada_por_la_entrada` (renglón en la lista) |
| 10 | PE de alimentación de 70/95/6×150 mm² contra una bornera que admite 35 mm² | No se leía el cable de alimentación | `feeder.peMm2` del rótulo; si supera la entrada de la bornera, se pide barra de tierra | `pe_input_undersized` · `test_pe_de_alimentacion_grueso_pide_barra_de_tierra` |
| 11 | S 293-C 80 sin dibujar: el gabinete quedaba sin su lugar (TSB, TA-1, TA-2) | Sin CAD → no se dibujaba | Contorno con las medidas de la ficha ABB (78,8 × 90 mm), marcado «SIN CAD» | `not_drawn_no_space` · `test_s290_se_dibuja_con_el_contorno_de_la_ficha` |
| 12 | S803 dibujado de 79,5 mm (3 × 26,5): la ficha dice 81 mm | Medida calculada, no leída | 81 mm de la ficha S803S-C80 | `test_medidas_del_cad` — **regla: las medidas salen de una ficha o del CAD, nunca de una cuenta** |
| 13 | TGBT sin kits de montaje en la lista (System pro E) | Los kits sólo se cargaban a mano | En System pro E cada caja moldeada recibe su kit (con código si está en el catálogo, si no «código pendiente») | `spe_kit_missing` · `test_kits_system_pro_e_en_la_lista` |
| 14 | E2.2 de 2000 A en una caja mural | Nada lo impedía | `floorStandingOnly` en la carcasa: sólo gabinete de piso | `test_emax_va_en_gabinete_de_piso` |
| 15 | Seccionadores OT en la lista sin manija («pedirlos aparte» pero sin renglón) | Sólo una nota | Renglón «Accionamiento OT» (sin código, elegir variante) | `test_ot_pide_manija` |
| 16 | E2.2: el relleno de color corrido y el resto del interruptor (cuerpo del 4.º polo, pies de fijación, borneras de auxiliares) quedaba como líneas grises sueltas | Paleta estimada a ojo sobre el dibujo | Rellenos medidos pieza por pieza sobre el STEP (`/tmp/cadx/solids.py`: cajas de cada sólido) | **regla: la paleta se mide sobre las piezas del CAD, no a ojo** · revisión visual |
| 18 | TSMAQ1 y TS AUX 3 en 800×800 con una sola fila de riel (contenido al 15 % del alto) | Si el bloque de distribución no entraba en el riel, se agrandaba el gabinete | Se compara agrandar contra sumar una fila de riel libre y se elige el gabinete más chico | `board_oversized` · `test_bloque_que_no_entra_suma_una_fila_en_vez_de_agrandar` |
| 19 | AA8010 (barra de **neutro o tierra** según el catálogo ABB) propuesta para repartir fases en TS1–TS5 y TA-1 | El catálogo de barras no distinguía el uso | Campo `uso` en `distributionBars`; sólo `fase` reparte fases; si no hay, «a dimensionar» | `neutral_bar_as_phase` · `test_barra_de_neutro_no_reparte_fases` |
| 20 | E2.2 (y orejas de los OT160–250 E): partes del interruptor quedaban como líneas grises sueltas fuera de la pintura; **la revisión no lo detectó** | La pintura se ubicó a ojo y la revisión visual se hizo en miniaturas, donde no se distingue | Pintura medida sobre las piezas del CAD; test que exige que toda línea del frente caiga sobre una zona pintada | `test_todas_las_lineas_del_cad_quedan_sobre_una_zona_pintada` · **regla: la revisión visual se hace a tamaño real, equipo por equipo, no en miniatura** |
| 17 | El catálogo de bloques tiene Schneider/Legrand/Steck como referencia; un empate de corriente podía elegir otra marca | Orden de la lista | Filtro `_abb()` al proponer | `test_bloques_de_otras_marcas_nunca_se_proponen` |

### Lo que la auditoría todavía NO ve (revisar a ojo)
- Que el dibujo de cada equipo coincida con el equipo real (colores, frente del CAD).
- Que el tablero sea el más chico razonable (sólo se detecta el hueco en el medio, no la reserva de abajo).
- La coordinación de corrientes aguas arriba/abajo (eso es del unifilar, no del armado).

## Cómo revisar un lote de tableros
1. Importar cada PDF por la interfaz (armado automático).
2. Correr `auditoria.audit(proyecto, catálogo, board_title=<rótulo>)` sobre cada proyecto: **0 errores y 0 avisos** (el aviso `board_oversized` sólo se acepta si el gabinete grande lo eligió el usuario).
3. Mirar cada PNG **a tamaño real** (recortes por zona, no la miniatura del tablero entero): lo de «todavía no ve».
4. Revisar la lista: ningún renglón vacío, lo que falta va «FALTA CÓDIGO» con su motivo.
