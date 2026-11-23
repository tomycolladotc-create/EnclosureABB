# BITÁCORA
> Una entrada por sesión, **la más nueva arriba**, máximo 6 líneas. Al empezar, leer solo las 3 primeras.
> Si pasa de 15 entradas, mover las viejas a `docs/bitacora_vieja.md`.
> Formato: `## fecha hora · agente` + Hecho / Archivos / Ojo / Siguiente.

## 2026-11-22 21:15 · Claude · Plano de fabricación: unifilar del usuario + topográfico en su formato
- Hecho: plano_unifilar.py toma el DXF de formato del usuario (BAF-E-EL-PL-104-0 Unifilares, una presentación por tablero con marco A2 y rótulo Rotulo_BA_ferial) y en cada hoja deja su unifilar tal cual (misma ventana 1:1) y agrega el topográfico de la aplicación con puerta abierta y cerrada, a escala normalizada (1:2 a 1:10 según el tablero), en A1 1:1; rótulo con «UNIFILAR Y TOPOGRAFICO» (resto de los datos sin tocar). Reglas en reglas_layout.json → planoUnifilar. Las cotas se explotan antes de importar (el importador no copia el bloque de la cota). Placa grabada de la puerta: factor de ancho 0,75 (los nombres largos salían de la placa).
- Resultado: 24 hojas, auditoría ezdxf 0 errores/0 arreglos; 174 tests; 124/124 interfaz.
- Ojo: el DWG del usuario (AC1032) no se puede leer acá: se trabaja con el DXF que él guarda desde AutoCAD; la salida es DXF (AutoCAD la guarda como DWG).

## 2026-11-20 18:30 · Claude · Verificación contra unifilares + Excel de equipamiento eléctrico
- Hecho: los 173 interruptores/seccionadores/diferenciales de los 24 tableros releídos con otro lector (PyMuPDF) y comparados: modelo, circuito, polos y calibre iguales al unifilar (única diferencia, a propósito: QF62 de TSB). Test permanente nuevo. Excel del equipamiento eléctrico (sin canalizaciones ni montaje): 85 renglones con código, cantidad (SUMIFS del detalle), circuitos y tableros; hojas de detalle por tablero y de verificación.
- Ojo: 57 de 85 renglones siguen sin código de pedido (XT, E2.2, OT, S800, varios S200, manijas OT, barras a dimensionar).

## 2026-11-20 17:30 · Claude · QF62 de TSB cambiado a 1P+N por pedido del usuario
- Hecho: el unifilar de TSB trae un monopolar (QF62 S201M B16, TSB-1.7 «Bombeo pluvial», fase S + neutro). A pedido del usuario se dibuja como S201M-B16 NA (1P+N, mismo bastidor y curva; código 2CDS271103R0165). Mecanismo nuevo y único: datos/correcciones_unifilar.json, aplicado por importador.apply_corrections al importar (editor y regresión); sólo vale si coinciden tablero + etiqueta + modelo del PDF; si el unifilar cambia, no se aplica y la interfaz avisa. La lista dice «CAMBIADO por pedido del usuario: el unifilar dice S201M B16 (1P)».
- Resultado: 172 tests; huella aceptada a propósito (sólo TSB: 19 equipos dibujados, 0 sin dibujar, mismo gabinete).

## 2026-11-20 16:30 · Claude · S290 (S293-C80) dibujado con su frente
- Hecho: buscados los equipos sin dibujar en los 24 tableros: sólo los S293-C80 (TSB ×2, TS AUX 1, TS AUX 2) salían como recuadro; el monopolar QF62 de TSB queda fuera por regla. Frente del S290 desde el dibujo vectorial del catálogo ABB NN31/05_04 (bajado con el navegador de la PC del usuario; ABB Library no se alcanza desde el espacio de trabajo). Código GHS2932001R0804 verificado en la tabla de pedido del catálogo.
- Resultado: 168 tests, regresión igual, auditoría 0; test nuevo: ningún equipo de 2+ polos sin frente en los 24 tableros.
- Ojo: el dibujo de catálogo no está a escala en alto (94,3 vs 90 mm): se dibuja centrado sin deformar (cadAspectNote).

## 2026-11-19 21:30 · Claude · 2.ª revisión de los 24 tableros: pintura por superficies del CAD, encuadre, etiquetas, lista
- Hecho: revisados los 24 a tamaño completo + puertas + listas. Corregido en origen: colores sobre superficies del CAD (semillas) y logos calculados; pantalla y DXF dibujan la misma pintura (pintura.resolve en el servidor, con candado y precálculo); encuadre de exportación medido (cotas cortadas, PNG estirado); subtítulo alto×ancho; etiquetas con letra mínima y misma regla en Python y JS (verificado con node); «a confirmar» en la lista; pruebas fuera de datos/proyectos (los 24 subidos por error se sacaron del repo).
- Resultado: 167 tests, 122/122 interfaz, regresión igual, auditoría 0 en los 24.
- Ojo: 37 rectángulos libres casi alineados quedan congelados hasta verificarlos con foto ABB; S290 sigue sin CAD (contorno con el modelo); 63 renglones de equipos sin código de pedido.

## 2026-11-19 18:00 · Claude · Frentes del CAD sin deformar y medidas verificadas contra el CAD
- Hecho: el frente se dibuja con escala uniforme y centrado (pintura.fit, web y DXF); OT400 4P pasa a 258 mm (contorno real del CAD con orejas) y su logo ABB queda dentro de la etiqueta roja; las diferencias catálogo/CAD que quedan (S800 DXF, SN201) están explicadas en cadAspectNote. Tests nuevos: medida = CAD (≤2 %) o nota; textos impresos dentro del equipo.
- Resultado: 160 tests, regresión de 24 tableros igual (ningún tablero del GENERAL usa OT400), 118/118 de interfaz, auditoría 0 en los 24 rearmados.
- Ojo: S800 sigue con DXF 2D de otra proporción → pendiente el STEP 3D de ABB Library (no se alcanza desde el espacio de trabajo).

## 2026-11-19 16:30 · Claude · Sin parches: pintura calculada del CAD, reglas en un solo lugar y regresión con 24 tableros
- Hecho: silueta exacta de cada frente (malla STEP/IGES proyectada o relleno del DXF) + agujeros; pintura = fondo sobre la silueta y detalles recortados (pintura.py, clipPath). Reglas sueltas en el código pasadas a reglas_layout/reglas_validacion/importRules; colocar.py usaba 4 mm y el armado 25 mm (unificado); testigos propuestos por el backend. Regresión: los 24 tableros reales en cada test, con huella aceptada.
- Archivos: work/proyectar_cad.py, datos/frentes_cad.json (silhouette), pintura.py, web/index.html, cad_export.py, auditoria.py, accesorios.py, normativa.py, colocar.py, layout_auto.py, app.py, datos/reglas_*.json, catalogo_abb.json, tests/regresion_general.py, tests/test_regresion_general.py, tests/unifilares/general/.
- Resultado: misma huella en los 24 tableros antes y después del cambio (el refactor no movió nada); 158 tests y 118/118 de interfaz.
- Ojo: OT160–250 4P: la etiqueta roja no coincide exacto con las letras ABB del CAD (detalle visual). Siguiente: ubicar la etiqueta por las letras del CAD.

## 2026-11-19 15:00 · Claude · Testigos de fase en la puerta con sus fusibles ubicados en el riel
- Hecho: opción en ⋯ «Testigos de fase en la puerta (con fusibles)»: agrega/quita las luces (una por fase según el general) y un portafusible ABB E 91/32 (2CSM200923R1801, 18 × 85 mm, ficha ABB) por luz, dibujado y ubicado en el riel (web y DXF, con la fase R/S/T). Los del unifilar se cargan solos al importar. El armado reserva su lugar; si no hay riel, crea uno.
- Lista: portafusibles E 91/32 + fusibles E 9F10 GG1 (2CSM277113R1801, código de distribuidor: confirmar) + luces CL2-523R. Auditoría `signal_fuses_missing/unplaced`.
- Archivos: accesorios.py, layout_auto.py, bom.py, auditoria.py, cad_export.py, web/index.html, web/styles.css, app.py, datos/accesorios_abb.json, tests.
- Ojo: el color de las luces sigue «rojo propuesto, confirmar». Siguiente: poner los fusibles junto al general en vez de junto a la bornera PE.

## 2026-11-19 13:30 · Claude · Revisión de los 24 tableros del GENERAL: 19 errores corregidos y auditoría para que no vuelvan
- Hecho: revisión tablero por tablero (a ojo + auditoría nueva `auditoria.py`, que corre dentro de la validación). Errores: restos del TS4 de plantilla en todos, nombres inventados, orden fuera de unifilar, general no arriba/compartiendo fila, filas sin canaleta, huecos y gabinetes de más, barras chicas o de neutro usadas para fases, PE grueso sin barra, S290 sin lugar, S803 mal medido, kits SPE y manijas OT fuera de la lista, Emax en caja mural, E2.2 mal pintado.
- Archivos: auditoria.py (nuevo), layout_auto.py, accesorios.py, bom.py, importador.py (detect_board), proyectos.py, normativa.py, catálogos, docs/LECCIONES.md (nuevo), tests/test_auditoria.py (nuevo).
- Resultado: los 24 tableros regenerados con 0 errores de auditoría y 0 equipos confundidos.
- Ojo: barras de 400/2000 A y barras de tierra quedan «a dimensionar» (no hay pieza ABB en el catálogo); kits SPE de E2.2/XT3/T4/T2/XT1 3P sin código.
- Siguiente: códigos de pedido faltantes; reservar lugar del bloque en el armado en vez de sumar fila.

## 2026-11-19 01:30 · Claude · Los 24 tableros del plano GENERAL armados y exportados
- 8 CAD ABB nuevos (E2.2 IV F, XT3 4P, XT1 3P, T4 4P, T2 3P, DXF S800 3P, OT63-80F3/F4) bajados de ABB Library desde la PC de Thomas → cad/abb/{e2_2,xt3,xt1_3p,t4,t2,s800/x,ot63_80}; SHA-256 en fuentes_descargadas.json. Frentes proyectados, carcasas/series/apariencias (paleta genérica de familia) en el catálogo; OT63/80F rotados 90° (bornes arriba/abajo, en riel).
- Los 24 tableros importados por la interfaz como usuario (armado automático) y exportados: DXF, PDF A3, PNG y lista CSV. Cruce automático equipo por equipo contra el texto de cada PDF: 0 faltantes, 0 cambios de modelo/polos, 0 carcasas de otra familia.
- Corregido en la prueba: nombre del tablero "4 5 6" cuando el archivo termina en números (ahora "TS2-PORT 4-5-6") y `source` del proyecto heredaba el PDF del TS4 de plantilla.
- Ojo: S 293-C 80 (TSB, TA-1, TA-2) sigue sin CAD: no se dibuja, va a la lista con aviso. Códigos de pedido de E2.2/XT3/T4/T2/XT1 3P/OT63-80 sin verificar (FALTA CÓDIGO). Tmax T2/T4 son generación anterior: confirmar disponibilidad.

## 2026-11-18 21:30 · Claude · Carcasas nuevas desde CAD ABB (OT, F200, SN201)
- 7 CAD públicos de ABB Library bajados con el navegador de la PC de Thomas (con su permiso) → cad/abb/{f200,sn201,ot100_125,ot160_250}; registrados con SHA-256 en fuentes_descargadas.json.
- Frentes proyectados con work/proyectar_cad.py (opción rot90ccw para OT160…250E: mecanismo a la izquierda). Carcasas, series y apariencias nuevas en el catálogo. OT100/125F en riel DIN (ficha ABB); OT160…250E en placa. S200P mapeado a S200 como HIPÓTESIS (verified=false).
- BOM: sin panel ciego PC del kit KD si hay un equipo en placa (el eje de la manija pasaría por el panel). DXF: cajetín mostraba la etiqueta de un equipo en vez del gabinete.
- Colores OT (pedido de Thomas): gris oscuro + banda roja ABB según foto de familia OT de ABB y la paleta del OT400; OT160…250E con fondo transparente y terminales de estaño (base "none", soportado en editor y DXF).
- Ojo: S 293 (S290) sin CAD en ABB (discontinuado); OT63F3/OT80F4 y cajas grandes del GENERAL siguen sin carcasa. Tests 118 OK; e2e 114/114.

## 2026-11-18 02:15 · Claude · Prueba como usuario final (ronda 1) + regla permanente
- Thomas pide probar siempre como consumidor final. Regla agregada en AGENTS.md y ESTADO.md; BITACORA reordenada (más nueva arriba, como dice AGENTS).
- Ronda: importar los 5 unifilares, puerta, lista, agregar 6 equipos, borrar/deshacer. Corregido: cartel fuera de la puerta en gabinetes de 300 mm (editor y DXF), título/selector superpuestos, cotas de rieles pisadas, cotas de interior en la puerta, "Agregar" repetía un circuito no dibujado y usaba un modelo genérico sin código, tarjeta sin el código que va a la lista, tramos de peine repetidos, favicon 404.
- Archivos: web/index.html, web/styles.css, app.py (/api/catalog incluye orderCodes), bom.py, cad_export.py, tests. Hallazgos y pendientes en docs/MEJORAS.md.
- Tests 114 OK; e2e 114/114.

## 2026-11-18 · Claude · Lista de materiales sin errores de compra + vista con la puerta cerrada
- Thomas: la lista no puede inducir una compra errónea; quiere ver la puerta cerrada con los orificios de los pilotos del unifilar, la nomenclatura grabada y el cartel de riesgo eléctrico.
- BOM (`bom.py`), errores encontrados y corregidos: gabinete repetido; placa PF pedida aunque viene con el SR2; menú de opciones GD como código; id interno "terminal_cover" como código; canaletas por pieza (ahora tiras de 2 m con despiece); equipos no dibujados ausentes; QD diferenciales no detectados; pilotos y fusibles ausentes; paneles ciegos PC sobre cajas moldeadas; peine PS2/12 insuficiente para 14 polos; peines del mismo código en varios renglones (ahora uno, con los tramos); System pro E: renglón "envolvente" PUPM2100 = mismo artículo que los montantes 1STQ007035A0000 (pedido doble) → se compra pieza por pieza; "PDLB1127 + PDNB1507" en un renglón → dos; panel lateral "uno por lado" → 2; riel sin opción de catálogo ya no dice "? mm".
- Códigos de pedido de equipos: `datos/codigos_pedido_abb.json` (19 modelos de los unifilares de prueba, cada uno con la URL donde se verificó; clave por modelo + polos). Sin verificar (quedan FALTA CÓDIGO con el motivo): OT100F4 (variante N2/C), S 293-C 80, SN201L B16, F204-SX AC-40/0,3. OT160EV03: nota "no incluye manija ni eje".
- Controles (`bom_issues`): sin código, no dibujados, códigos repetidos, cantidades, conteo de equipos, códigos con "+"/espacios. Van en pantalla, en el CSV y en el DXF.
- Puerta cerrada: editor (botón Interior/Puerta cerrada, centrado arriba), exportación PDF/PNG/SVG con selector de vista (sufijo `_puerta`), DXF con la puerta al lado del interior (capas ABB_PUERTA_*: corte Ø22 y bisel Ø30 por piloto, placa grabada, triángulo con rayo y leyenda). BOM del DXF movida a la derecha de la puerta; títulos y avisos ya no tapan el dibujo; textos DXF sin "?" (Ø → %%c, tildes fuera).
- Tests 113 OK; e2e 113/113.

## 2026-11-18 02:10 · Claude · Tableros más compactos (prueba desde cero con 5 unifilares)
- Thomas: el tablero queda demasiado grande. Causas encontradas en layout_auto.py:
  1. Si el riel GD más corto (400 mm) no entraba en el ancho útil se descartaba el gabinete → ahora el riel se corta a medida (`cutFromMm` en el riel).
  2. Kit KD que llena la placa (3 × 185 = 555 de 560 mm) + margen de 40 → se descartaba; ahora la pila de filas puede ocupar la placa sin margen.
  3. La reserva para la bornera PE usaba la M4/6.P; ahora usa la bornera configurada (DBL125: bloques + topes).
  4. `railRowGapMm` 110 → 80 (ya no existe la franja del rótulo superior).
  5. Tableros sólo de riel libre: el bloque de filas se centra en altura (canaleta arriba y abajo).
- Resultado: TSB y TSEP 600×600 → 600×400 (kit KD 3 filas); TA-1 500×400 → 300×400; TSL2 y TSFT3 500×400 → 300×300; TS4 sin cambio. Todos sin errores de normativa ni geométricos.
- Pendiente detectado en la prueba: equipos sin carcasa en el catálogo quedan afuera (OT100F4, OT160EV03, S 293-C 80 ×3, SN201L B16) → hay tableros sin su interruptor general. Propuesto a Thomas cargarlos con medidas ABB.
- Tests 88 OK; e2e 104/104.

## 2026-11-18 01:40 · Claude · Bloque de distribución y barra de cobre realistas
- BRT125A (1SNA179535R2300): 4 polos, 4 x 12 conexiones = 1 entrada (35 mm²) + 11 salidas (16 mm²) por polo, 128 x 85 x 60 mm, tapa y etiqueta de advertencia (Farnell, RS, Rapid). Dibujo: 4 barras de cobre L1 L2 L3 N con colores IRAM (marrón, negro, rojo, celeste), bornes de latón, tapa, triángulo de riesgo eléctrico; DXF con barras y bornes. Ubicación de bornes esquemática (anotado).
- Barra AA8010: agujeros M6 cada 25 mm (catálogo) y soportes aislantes (esquemáticos).
- Bugs: el bloque sólo buscaba lugar en el primer riel (ahora en todos); para >125 A se elegía un bloque sin medidas (Schneider Distribloc 160) que no se podía ubicar → ahora sólo bloques con medidas y, si no hay, la barra ABB.
- Tests 88 OK; e2e 104/104.

## 2026-11-18 01:00 · Claude · Bornera equipotencial PE realista
- Thomas pidió una bornera de PAT más gráfica y fiel a la realidad (ejemplo: repartidor con tapa transparente). Se eligió el tipo usado en tableros industriales: repartidor unipolar como bornera equipotencial.
- Producto: TE ENTRELEC (ex ABB) DBL125 1SNL312510R0000: 125 A, 1 entrada Ø9,8 (10…35 mm²), 7 salidas (1×Ø6,8 + 6×Ø6,4; 2,5…16 mm²), 28,2 × 75 × 50,7 mm, Icw 4200 A 1 s, marcador PE incluido; topes BAM4 1SNK900001R0000 (10 mm). Fuentes en datos/accesorios_abb.json y datos/fuentes_descargadas.json (consultadas). La disposición de bornes en el frente es esquemática (el fabricante no publica el frente acotado) y está anotada.
- `reglas_layout.json: peTerminalId` elige la bornera (vuelve a M4/6.P con "entrelec-m4-6p"). Un bloque cada 7 circuitos + 2 topes; cómputo con renglón de topes (`bomExtra` en bom.py). Dibujo en editor (cuerpo gris, tapa, bornes de latón, marcador verde-amarillo, topes) y en DXF (bloques, bornes como círculos).
- Tests 88 OK; e2e 104/104.

- 01:15 · Identificación PAT: cuerpo verde-amarillo rayado, símbolo de tierra y rótulo amarillo "PAT" de punta a punta de los bloques (como el rótulo de obra de la foto de Thomas); en DXF, símbolo de tierra. Disponibilidad en Argentina: no se verifica para este accesorio (pedido de Thomas).

## 2026-11-18 00:30 · Claude · Canaletas automáticas con criterio de armador + estirar desde los extremos
- Thomas mostró un tablero armado por él: canaletas verticales a ambos lados y horizontales arriba y abajo de cada fila (también cajas moldeadas en kit KD), lo más anchas que entren.
- `accesorios._propose_ducts` reescrito: verticales laterales (hasta `ductSideMaxWidthMm` 60) si hay lugar entre borde y equipos/rieles; filas = equipos/accesorios solapados en altura (no sólo rieles DIN); canaleta arriba y abajo de cada fila, de vertical a vertical; entre filas una compartida o una pegada a cada fila si sobran `ductMinFreeBetweenMm`; ancho = el mayor del catálogo que entra (25..`ductMaxWidthMm` 80). Se quitó la franja de 30 mm sobre los equipos (era para el rótulo superior eliminado el 16/11).
- Editor: todas las canaletas se pueden tocar; al tocar una automática pasan todas a manual (aviso). Extremos con "agarre" (cursor ↔ / ↕): arrastrar estira o acorta en pasos de 5 mm (mín. 50 mm); si queda sobre un equipo, vuelve.
- Bugs: al pasar a manual se perdía la orientación vertical; canaleta nueva sin hueco libre caía sobre equipos (ahora puede cruzar canaletas, nunca equipos).
- Tests 87 OK; e2e 104/104 (dos corridas).

## 2026-11-17 23:15 · Claude · Fluidez (simulación de uso real)
Simulación de un tablerista (importar TSEP/TSFT3, revisar, agregar, canaleta, exportar). Arreglos:
- Nombre del tablero al importar: prefijo común de los circuitos (TSEP-1.. → "TSEP"); si no hay, el final del nombre del archivo.
- Gabinete en una sola línea (antes repetía medidas contradictorias 800×600 / 603×803).
- "Agregar equipo": propone el equipo más usado del tablero y el siguiente circuito (TSEP-16), seleccionado para sobrescribir.
- Botón "Duplicar" en la tarjeta del equipo (misma carcasa/modelo, siguiente circuito).
- Si al rearmar cambia el gabinete, se avisa "El gabinete cambió: A → B"; si no cambia, se conserva el zoom.
- Escape y clic en el vacío quitan la selección; Supr borra el equipo seleccionado (Ctrl+Z deshace).
- Reordenar en el riel: soltar un equipo DIN sobre otro del mismo riel lo inserta ahí y corre a los demás (también reordena `project.devices`, así un rearmado conserva el orden entre equipos de la misma carcasa).
- Tooltip al pasar el mouse (circuito · modelo · QF; canaleta · orientación · largo). La lista lateral se desplaza hasta el equipo elegido en el dibujo.
- Tableros: la revisión al abrir (rearmar si no cumple) sólo corre al entrar al editor; la lista se refresca al volver (antes mostraba datos viejos); tarjetas con gabinete y fecha, orden por última modificación (`proyectos.list_projects` devuelve `enclosure`, `modified`).
- e2e: 98/98.
Propuestas sin hacer (para decidir): separar PDF de planta en tableros; cajetín en el PDF; estirar canaletas desde los extremos e imán a bordes; fijar gabinete al agregar equipos; quitar "Nuevo tablero vacío" y "Revisiones" si no se usan.

## 2026-11-17 22:50 · Claude · Canaletas a mano
- Pedido de Thomas: las canaletas automáticas no sirven bien; quiere dibujarlas él con medidas estándar donde quiera.
- Editor: botón "＋ Canaleta" (sección del catálogo ABB `wiringDucts.sections`, orientación H/V, largo). Al agregar la primera, `project.ductMode = "manual"`: las automáticas existentes se convierten en editables y `accesorios.propose` deja de proponer canaletas. Menú ⋯ → "Volver a canaletas automáticas".
- Canaleta seleccionada: tarjeta con sección, largo, girar, eliminar; arrastre con paso de 5 mm; flechas 5 mm (Shift 1 mm); Supr elimina. No puede quedar sobre un equipo (vuelve a su lugar); si un rearmado la deja encima de un equipo, el chip de normativa lo marca como error.
- Servidor: `accesorios._manual_duct` normaliza la canaleta (código 1SL90../1SL91.. según ranura, largo, descripción para el cómputo); `GET /api/ducts`; DXF dibuja canaletas verticales.
- Bug corregido: la revisión de normativa en segundo plano podía pisar un cambio recién hecho (respuesta vieja). Ahora se descarta si el proyecto cambió.
- Tests 86 OK; e2e 78/78 (dos corridas).

## 2026-11-16 13:30 · Claude · Prueba de punta a punta y bugs de fondo
- Nuevo `tests/e2e/prueba_interfaz.py` (Playwright + Chrome): recorre todos los botones (abrir/reabrir, zoom, renombrar, deshacer/rehacer, arrastrar, agregar/eliminar, chip, menú, rearmar, riel libre, cambiar gabinete, JSON, exportar DXF/SVG/PNG/CSV, duplicar/borrar, importar los 6 PDF de ejemplo). 61/61 OK. CORRERLA ANTES DE ENTREGAR CAMBIOS DE INTERFAZ.
- Bug de fondo (venía de antes): al abrir un tablero se reemplazaban los rieles del armado automático por los del catálogo y todo DIN iba al primer riel → "QF81 es DIN pero no está sobre un riel". Ahora se respetan los rieles guardados; `alignDin` usa el riel más cercano.
- Al abrir, si el tablero no cumple, se rearma solo (una vez).
- Soltar un equipo encima de otro: vuelve a su lugar y avisa.
- Cambiar gabinete (menú ⋯) rearma dentro de ese gabinete (`/api/autolayout?enclosure=id`); si no entra, se mantiene el anterior.
- Navegación: `location.search` con `#editor` metía el hash en el id del proyecto (duplicar/abrir/crear). Corregido con `location.href`.
- PDF de toda la planta (25_GENERAL, 132 equipos de ~20 tableros): ya no crea un tablero roto; avisa qué tableros contiene. Idea a futuro: separar automáticamente un tablero por prefijo de circuito (TS-1, TSB-1…).
- Menú ⋯ se cierra al elegir una opción; aviso (toast) visible en todas las pantallas.

## 2026-11-16 12:30 · Claude · Frontend limpio y tablero ya conforme a normativa
- Pedido de Thomas: interfaz más limpia, sin botones inútiles; que el tablero salga ya dentro de normativa (sin Completar/Revisar/Confirmar).
- `web/index.html` + `web/styles.css` reescritos: 3 pantallas (Tableros, Editor, Exportar). Editor: lista de circuitos + "＋ Agregar equipo" (ventana), lienzo con zoom flotante, tarjeta del equipo seleccionado (sólo circuito, modelo, eliminar), chip "Normativa ✓ · N observaciones" con panel, menú "⋯" (gabinete, rearmar, riel libre, importar otro PDF, JSON). Autoguardado: ya no hay botón Guardar.
- Importar PDF desde Tableros crea un tablero nuevo con el nombre del archivo y lo arma solo; "Importar otro unifilar" (menú ⋯) agrega al tablero abierto.
- `accesorios.complete(..., auto_confirm=True)` confirma sola bloque/barra de distribución; `/api/normativa/complete` se llama solo tras cada cambio (si cambian los accesorios, se redibuja).
- `layout_auto.autolayout_conforme`: si bornes PE/barras no entran, prueba el gabinete siguiente. Los PE se buscan en todos los rieles (antes sólo el primero).
- Peines: un peine sólo une equipos con los mismos polos (antes "mezcla de polos" daba error de normativa).
- Observaciones que quedan (honestas, por falta de datos): peine S804 4P con neutro; mezcla de polos adyacentes sin peine; masas a tierra (manual en obra); profundidades ABB pendientes (aparecen como "datos pendientes", no cuentan en el chip).
- Tests: 82 OK (nuevos: UI sin botones de normativa, auto-confirmación).

## 2026-11-16 12:20 · Claude · Un solo rótulo por equipo
- Pedido de Thomas: el nombre del circuito aparecía dos veces (arriba del equipo y en el porta-etiqueta). Se quitó el de arriba en el editor (render) y en el DXF el texto pasó a un porta-etiqueta bajo el equipo (rectángulo 12 mm + texto, capa ABB_ETIQUETAS), igual que en pantalla.
- Tests 82 OK; e2e 61/61 OK.

## 2026-11-16 11:40 · Claude
- Pedido: tablero automático, sin botones. Importar PDF → agrega equipos propios y arma todo (gabinete, rieles, peines, canaletas) y abre el editor. 'Agregar equipo' (no tenía acción) ahora salta al formulario con QF sugerido + campo Circuito y rearma el tablero al agregar.
- Filas de riel libre: `railRowGapMm`=110 y zonas de etiqueta/portaetiqueta reservadas al proponer canaletas (se veían etiquetas y peines pisando la fila de arriba). 80 pruebas OK. Probado con TSB (15 equipos → SRN6625K) en navegador real.
- Ojo [Codex]: las pruebas de navegador crean proyectos en `datos/proyectos/`; borrarlos antes de commitear.

## 2026-11-16 03:00 · Claude
- Pedido del usuario: (1) en lugar del QF mostrar el nombre del circuito del plano (ej. TS-4.2); (2) sin descripciones de accesorios en el dibujo, solo en el cómputo de materiales.
- (1) `circuit` por equipo (importador + TS4 cargado desde Unifilares-25_GENERAL.pdf: QF82→TS-4.2 … QF163→TSMAQ2, QF89/90→TSI-6/7). Se muestra en editor, DXF, BOM y avisos; el QF queda como `tag` interno (peines, normativa y revisiones siguen usándolo).
- (2) Se quitaron textos de accesorios y del riel (DIN-n) en editor y DXF; BOM con categorías Canaleta/Peine/Borne PE/Riel DIN/Kit de soportes DIN. Zona de etiqueta reservada sobre los equipos (30 mm) al proponer canaletas. 79 pruebas OK.
- Ojo [Codex]: el DXF todavía trae la tabla 'LISTA DE MATERIALES' que armaste, ahora con las descripciones de accesorios; si el usuario no la quiere en el plano, sacala del DXF y dejala solo en el export CSV.

## 2026-11-16 02:10 · Claude
- Peines visibles (cuerpo + clavijas por polo, sobre los equipos) y canaletas horizontales propuestas (`wiringDucts`, 22 secciones del catálogo SR2 pág. 6/5; lógica en `accesorios._propose_ducts`). Capas DXF nuevas ABB_CANALETAS / ABB_PEINES. En el editor las etiquetas de los equipos con peine suben para no taparse. 76 pruebas OK.
- Supuestos marcados: B = cara visible y H = profundidad de la canaleta (convención, no cotado); ranura = ancho / paso; ancho de uñas laterales esquemático. TS4 con riel libre: canaletas 40x40 abajo y 15x17 arriba.
- Pendiente [Claude/Codex]: canaletas verticales, edición manual de canaletas, línea RAL 7030.

## 2026-11-16 02:00 · Claude
- Cierre de sesión: el usuario instaló/corre el editor en su PC (`Descargas\EnclosureABB`, Python 3.12 ya instalado pero fuera del PATH; el .bat ahora lo encuentra). Plan, decisiones abiertas y sugerencias para la próxima sesión escritos en ESTADO.md ('PRÓXIMA SESIÓN'). Nada sin subir.

## 2026-11-15 23:55 · Claude
- S251 resuelto como hipótesis: 'S 251 Na C 10' (QF79, QF80, QF89) se importa con la carcasa del S201 NA (35 x 88 x 69 mm, ficha ABB vía RS) en la serie `s251-na` con `verified: false`. El estado del equipo dice 'carcasa compartida sin confirmar'. Falta confirmar con ABB Argentina; el marcado impreso de esa designación no está validado.
- Pendiente sin CAD: S293 (S290), SN201L, XT1 3P, XT3S 4P. Detalle en `datos/carcasas_pendientes.json`.

## 2026-11-15 23:40 · Claude
- Búsqueda de las carcasas que faltan (pedido del usuario): resultados en `datos/carcasas_pendientes.json`, con fuente y estado por familia.
- Mejor cubiertas: XT1 3P (76,2 x 130 x 70 mm, CAD 1SDH001295R0008) y XT3S 4P (140 x 150 x 70 mm, dos códigos de dibujo en conflicto). Parciales: S293 (S290, 26,25 mm por polo), SN201L (conflicto de profundidad 69/85). S251: nombre antiguo, sin carcasa asignada.
- Límite: la shell de la sesión no puede bajar archivos de ABB (proxy 403). Los CAD hay que bajarlos desde el navegador de la PC del usuario o por Codex.
- Tarea para Codex: bajar 1SDH001295R0008, el CAD de XT3S 4P, S290 y SN201 (+ datasheet 2CSC400002D0209) a cad/abb/<familia>/ y registrarlos en datos/cad_argentina.json.

## 2026-11-15 23:40 · Claude
- Kit KD cargado en 11 SR2 (`kdKit`); `layout_auto` arma con filas fijas de 185 mm; opción riel libre GD (`?free=1`, botón en el editor). TS4 queda en SRN12830K (1200x800) con filas fijas; con riel libre entra en SRN12630K (1200x600).
- Arreglos: peine sin corriente porque faltaba `poles` en QF90 (ahora se deduce de la carcasa: 1pn=2 polos); el bloque de distribución se dibujaba sobre los bornes PE (ahora los respeta). Pendiente conocido: peine con neutro para S804 (QF81/QF85 siguen 'sin peine').
- Ojo [Codex]: el servidor de prueba autoguarda el proyecto abierto en `datos/ts4_topografia.json`; si corrés el editor con el TS4, verificá `git status` antes de commitear.
- 72 pruebas OK.

## 2026-11-15 23:10 · Claude
- Aclaración del usuario: la lámina GENERAL NO es un tablero a separar, es referencia de los modelos que más usa. Descartada la separación; agregado el ranking de uso a docs/cobertura_unifilares.md. Prioridad de carcasas faltantes: S293 3P, SN201L, XT3S, S251, XT1S 3P.
- Hecho: ubicación automática en riel DIN (`colocar.py`, ruta /api/place, botón 'Agregar todos y ubicar en el riel'). Misma carcasa pegada (para el peine), distinta con 4 mm. Si no entra, el equipo queda `unplaced` y la normativa lo avisa. Probado con el TSB: 15 equipos entran en el riel de 600 mm. Tests: 39 OK. Rótulos de equipo más chicos para que no se pisen.
- Pendiente: equipos de kit (XT/OT) y varios rieles según gabinete (solo hay 1 riel en el catálogo); elegir gabinete según contenido.
- Tarea para Codex: carcasas S293 3P, SN201L, XT3S, XT1S 3P y S251 (CAD ABB).

## 2026-11-15 23:06 · Codex
- Hecho: BOM agrupada en interfaz/DXF, descarga CSV para Excel y control de revisiones numeradas por proyecto.
- Archivos: `bom.py`, `revisiones.py`, `app.py`, `cad_export.py`, `web/index.html`, pruebas y documentación.
- TS4: 18 renglones (envolvente, 8 estructura, 6 equipos, 2 kits, 1 riel); revisión de prueba 0 no persistida.
- Pruebas: 67 OK; JavaScript válido; DXF verifica capa `ABB_BOM` y texto de revisión.
- Ojo: códigos dudosos siguen marcados por confirmar; no se modificaron datos ni geometría KD asignados a Claude.

## 2026-11-15 22:45 · Claude
- Hecho: un proyecto por tablero. `proyectos.py` (listar, cargar, guardar, crear), rutas `/api/projects`, `/api/project?id=`, `/api/save?id=`, `/api/project-new`; selector y 'Crear' en el editor (la URL lleva `?id=`). Tests: 33 OK. Probado en el navegador: crear 'Prueba TSB' lo guardó aparte y el TS4 quedó idéntico (mismo md5).
- Pendiente: duplicar y borrar proyectos; el proyecto nuevo copia el gabinete del TS4 (elegir gabinete al crear).
- Siguiente [Claude]: importar un PDF directo a un tablero nuevo y separar la lámina GENERAL por tablero.

## 2026-11-15 22:25 · Codex
- Hecho: autoguardado, borrador recuperable, aviso al salir, estado visible, deshacer/rehacer y validación geométrica/técnica en el editor.
- Archivos: `validacion.py`, `datos/reglas_validacion.json`, `app.py`, `web/index.html`, pruebas y documentación.
- Valida: solapamientos, límites de placa, riel DIN, capacidad lineal y profundidad; datos de profundidad faltantes se advierten sin inventar.
- Pruebas: 62 OK, JavaScript válido, API real sobre TS4: 0 errores y 1 advertencia de profundidades ABB pendientes.
- Ojo: no se tocaron datos ni geometría de kits KD asignados a Claude; servidor local activo para revisión.

## 2026-11-15 22:15 · Claude
- Hecho: bloque de distribución propuesto cuando In supera el peine (elige el de menor corriente que alcance; BRT125A 128x85 mm provisional); regla `accesorio-sin-lugar` avisa si un accesorio no entra en el riel. Tests: 27 OK.
- Límite: solo el BRT125A tiene medidas de frente; los demás bloques quedan 'sin medidas' hasta tener hoja de datos.
- Siguiente [Claude]: un proyecto por tablero + lista de proyectos.

## 2026-11-15 22:10 · Claude
- Medidas (ancho x alto x largo, mm) de las fichas ABB leídas por WebFetch: PS1/4 21x18x67, PS1/60 20x17x1050, PS3/60 14,8x29x1056, PS4/12 19,3x30,5x212. La ficha trae 'Pitch 44698' (error de planilla): no se copió. El CAD de ABB está en un visor dinámico de la página del producto (new.abb.com/products/<código>, sección 'CAD outline drawing') que no se pudo bajar con el navegador integrado; pendiente [Claude/Codex]: probar con Chrome o pedirlo al usuario.

## 2026-11-15 22:08 · Codex
- Hecho: maqueta Claude Artifact convertida en interfaz real de cuatro pasos: Tableros, Importar, Editor y Exportar.
- Archivos: `web/index.html`, nuevo `web/styles.css`, ruta estática en `app.py`, contrato en `tests/test_web_ui.py`.
- Integrado: proyectos/envolventes, PDF, dibujo SVG, edición, normativa y DXF/PNG/SVG/PDF; vista verificada en navegador.
- Pruebas: 57 OK; JavaScript válido; CSS servido HTTP 200. No se alteraron medidas, catálogo ni trabajo KD de Claude.
- Siguiente: Claude puede continuar rieles KD; la UI nueva es desde ahora la interfaz oficial.

## 2026-11-15 21:50 · Claude
- Hecho: `accesorios.py` (propuesta), rutas `/api/normativa` y `/api/normativa/complete`, panel en el editor, accesorios y avisos en el DXF. Tests: 24 OK. El TS4 real queda sin errores comprobables tras 'Completar accesorios'.
- Límites: geometría esquemática (rectángulos punteados = provisional); un borne PE por QF es simplificación; el cubrebornes no tiene dibujo; S800 sin peine.
- Siguiente [Claude]: bloque de distribución cuando In supera el peine (usar BRT125A 128 mm, a confirmar); luego un proyecto por tablero.

## 2026-11-15 21:50 · Claude
- Pedido del usuario: el programa propone y el usuario elige (barra de cobre / bloque); completar los datos faltantes de peines y barras.
- Datos cargados con fuente (web, fichas ABB reproducidas por distribuidores; nada se bajó como archivo): PS1/4, PS1/60, PS3/60, PS2/12 (código 2CDL220001R1012), PS4/12 (código 2CDL240101R1012 según Voltimum), S803-BB250 (2CCS800900R0071) con alimentación S803-BBPC120, barras AA8010 (320 A, 20x5, 1000 mm, soportes AA8011) y PBFC2005. Lo que no figuraba en ninguna fuente quedó en null y anotado (Icw del PS2, medidas de varios, corriente de PBFC2005).
- Código: `accesorios.propose` propone `copper_busbar` cuando ningún bloque alcanza y una barra del catálogo sí; `decision` confirmed/discarded; UI con botones en el panel de normativa; límite de peines S200 corregido. Tests: 52 OK.
- Aviso importante: el catálogo ABB describe AA8010 como barra de **neutro o tierra**; su uso como barra de fase es decisión del usuario y está marcado en la nota de la propuesta.
- Siguiente [Claude]: canaletas (ver entrada anterior) y reservar espacio para ellas en layout_auto; CAD de peines/bornes.

## 2026-11-15 21:47 · Codex
- Hecho: gestión completa de proyectos: crear con envolvente ABB elegida, duplicar contenido/posiciones y borrar; TS4 queda protegido.
- Archivos: `proyectos.py`, `app.py`, `web/index.html`, `tests/test_proyectos.py`, `README.md`.
- Pruebas: 55 OK y flujo HTTP real completo; interfaz verificada con 31 envolventes y controles visibles.
- Ojo: no se tocó el trabajo de rieles DIN asignado a Claude; los nombres con tildes ahora generan ids ASCII estables.
- Siguiente: tomar profundidad real de equipos o una familia faltante mientras Claude termina los kits KD.

## 2026-11-15 21:32 · Codex
- Hecho: marcado frontal XT1/XT2 y logo OT400 medidos sobre imágenes oficiales ABB; el parser separa bastidor, disparador e In de Tmax.
- Archivos: `importador.py`, `generar_topografico.py`, `datos/apariencias_abb.json`, `datos/fuentes_descargadas.json`, `docs/imagenes_abb/`, prueba de importador.
- Ojo: las fotos XT usan etiqueta genérica; los valores variables salen del unifilar. La foto OT no muestra modelo/corriente y no se inventaron.
- Pruebas: 53 OK; generación SVG/PNG/PDF/DXF; auditoría DXF 0 errores y 58 atributos.
- Siguiente: profundidad real de equipos o familias faltantes; no tocar rieles mientras Claude siga asignado.

## 2026-11-15 21:24 · Codex
- Hecho: Git local autenticado y clon oficial preparado; protocolo reforzado para que todo cambio se suba durante la misma sesión.
- Archivos: `AGENTS.md`, `ESTADO.md`.
- Ojo: después de cambios grandes o antes de cerrar una sesión, actualizar coordinación y subir incluso el trabajo parcial.
- Siguiente: respetar la asignación activa de Claude sobre rieles DIN y tomar un pendiente libre antes de modificar código.

## 2026-11-15 21:20 · Claude
- Hecho: medidas y corrientes de peines PS1/12 y PS3/12 (63 A, 25 kA), BRT125A (128 mm de ancho), bloques Steck (5 referencias), Legrand y Schneider Domae (listado en se.com/ar). Todo por-confirmar salvo lo indicado.
- Conflictos anotados en el JSON: PS3/12 tiene dos versiones con medidas distintas; BRT125A figura con 4x12 y con 11 vías.
- Para Codex: consultar el buscador de ABB Argentina (new.abb.com/low-voltage/efinder-country/ar) por 2CDL210001R1012 y 2CDL230001R1012; elegir qué versión de PS3/12 se vende.

## 2026-11-15 21:20 · Claude
- Pedido del usuario: más detalle en la vista. Agregado: cotas (exterior, placa, altura de cada riel desde la placa) en el editor y en el DXF (capa ABB_COTAS, cotas lineales reales de ezdxf) y porta-etiquetas con el tag bajo cada equipo (tamaño propuesto, no dato ABB).
- Evaluado y NO hecho por falta de dato claro: canaletas (el catálogo 1STC804013D0201 las trae en págs. 9/40-9/43 y 6/2-6/3, pero las medidas de sección no se leen bien del texto; hay que mirar la imagen) y barra PE AA8010 (1000 mm, no entra en la placa de 560 mm). Siguiente [Claude]: canaletas con medidas de la imagen de la pág. 9/40 y propuesta de ubicación (sobre y bajo cada riel); barra de tierra que entre en la placa.

## 2026-11-15 20:55 · Claude
- Pedido del usuario: la vista se sentía plana, todo en una capa. Hecho en `web/index.html` (sólo estética, no cambia medidas ni datos): degradado de chapa en gabinete y placa, sombra de la placa sobre el fondo, sombra proyectada de cada equipo, riel DIN con relieve/ranuras/tornillos de fijación, bloque de tierra con terminales, tornillos de la placa (a 14 mm del borde, pág. 9/7 del catálogo SR2), cerraduras en las posiciones del catálogo (pág. 9/6) y bisagras esquemáticas. Título y subtítulo con el gabinete real (antes decía System pro E fijo). Datos nuevos: `structure.locks` en los SR2.
- Pendiente de esta línea [Claude/Codex]: el DXF todavía no dibuja relieve (es 2D plano por diseño); herrajes de los gabinetes System pro E (manijas PHLS0013, bisagras) sin posición; ranuras del riel y bisagras son esquemáticas (pitch 25 mm y posición de bisagras son supuestos visuales, no datos ABB).

## 2026-11-15 20:50 · Claude
- Hecho: catálogo con `distributionBlocks` (ABB BRT125A, Steck SDM9904/9907, Schneider Distribloc 125/160 A) y familias de peine PS2/PS4; todo por-confirmar. El aviso de `peine-corriente` ahora manda al bloque de distribución.
- Layout: el peine no ocupa ancho extra; el bloque de distribución sí (módulos DIN a confirmar con ficha). Pendiente: fichas y medidas.
- Tarea para Codex: fichas de BRT125A, SDM9904/9907 y Distribloc (corriente, módulos, medidas) y disponibilidad en Argentina.

## 2026-11-15 20:40 · Claude
- Cierre de sesión por límite de uso: ESTADO.md actualizado (Situación y Pendiente completos, con el punto 0 en curso).
- Estado exacto de lo que estaba haciendo: leí la tabla de selección SR2 (pág. 2/4, imagen) con las filas KD por gabinete; NO hay cambios de código de ese tema todavía. Punto de partida para [Codex]/[Claude]: agregar `kdKit` a los `enclosures` SR2 (datos en ESTADO.md punto 0) y extender `layout_auto._try` para poner los modulares en filas de 185 mm y los XT/OT en la placa.
- Pedido del usuario: 'segui así' con la posición de los rieles según el gabinete; supuestos sin dato a marcar en el JSON con su `status`.
- Último commit antes de esto: 297039d (SR2 como candidatos). Tests 48 OK.

## 2026-11-15 20:25 · Claude
- Pedido del usuario: en tableros de corriente elevada (TS, auxiliares) se usan barras de distribución o peines según la corriente. Agregada regla `peine-corriente` (error si In del equipo > corriente del peine) y categoría `distributionBars` vacía en el catálogo de accesorios.
- Tarea sugerida para Codex: buscar barras/bloques de distribución usados en Argentina (ABB o equivalente) con corriente, paso y medidas.

## 2026-11-15 20:10 · Claude
- Hecho: `normativa.py` ejecuta las reglas de `normativa_argentina.json` (PE, un borne por conductor, cubrebornes, peines entre equipos contiguos; masas a PE queda manual). Tests en `tests/test_normativa.py`. Política: accesorios genéricos de cualquier marca.
- Ojo: 'un borne PE por circuito QF' es una simplificación declarada hasta confirmar con el texto oficial.
- Siguiente [Claude]: `accessories` en el proyecto y en el editor (agregar barra PE, peines, cubrebornes), avisos en pantalla y DXF.

## 2026-11-15 20:10 · Claude
- Pedido del usuario: el gabinete seguía siendo demasiado grande para el TS4.
- Hecho: catálogo ABB 'Enclosures for Automation' 1STC804013D0201 (02.2011) bajado con el navegador (Descargas del usuario) y leído. Cargados los 23 gabinetes SR2 con puerta ciega (códigos SRN...K, págs. 2/5 y 9/6): externo = nominal + 3 mm, placa interna = (ancho-40) x (alto-40) (coincide con la tabla de placas PF.... de la pág. 9/7), rieles GD4006/6006/8006 (pág. 2/8). `layout_auto.py` ahora usa `railOptions` y `functionalOffset` por gabinete y descarta gabinetes con profundidad menor a `minDepthForKitDevicesMm` (200, propuesta de diseño en `datos/reglas_layout.json`). TS4 -> SRN12630K 1200 x 600 x 300 con riel GD4006. Tests: 48 OK.
- Supuestos marcados: la placa está centrada en el gabinete (el catálogo no da su posición); profundidad externa = nominal; la profundidad mínima de 200 mm para XT/OT es criterio propio, no dato ABB (no tenemos profundidades de los equipos). Los códigos de las págs. 2/5 se leyeron de texto; las medidas de la pág. 9/6 se verificaron mirando la imagen.
- No cargado: versiones con puerta vidriada (VK), zócalos ZA...., IS2 (gabinetes de piso) y el catálogo SR2 de dimensiones internas de kits KD.
- Siguiente [Claude]: profundidades reales de XT/OT/S800 para validar el gabinete; kits KD con paneles modulares para el riel; verificar disponibilidad SR2 en Argentina.

## 2026-11-15 19:50 · Claude
- Hecho: `datos/accesorios_abb.json` (peines PS1/PS3 de ABB paso 17,5; bornes de tierra Entrelec M4/6.P y M6/8.P) con fuente y estado; lista de pendientes dentro del archivo.
- Hallazgos: ABB Argentina certifica 'Peines de conexión PSx' (confirma que existen allá, no qué códigos). La línea de borneras DIN de ABB (Entrelec) ahora es de TE Connectivity: avisar al usuario/verificar con ABB Argentina. Para S800 no apareció peine de fase.
- Tarea sugerida para Codex: confirmar códigos PSx en Argentina (catálogo ABB Argentina / distribuidores) y bajar CAD de PS1/PS3 y M4/6.P.
- Siguiente [Claude]: `normativa.py` (control de reglas) y peines automáticos en el editor.

## 2026-11-15 19:40 · Claude
- Hecho: marcado real en el frente (logo ABB, serie, curva+In, tensión, recuadros Icn y clase; S800: serie, curva, 240/415V~kA, In=) medido en fotos frontales ABB y calibrado con aristas del CAD. Barra común de palancas en S200 2P-4P. Sin monopolares (scope.minPoles=2). Colores S800 corregidos (verde estaba mal ubicado).
- Archivos: `marcado.py` (nuevo), `importador.py` (marking_fields, ensure_marking), `cad_export.py`, `web/index.html`, `datos/apariencias_abb.json` (marking, tieBar), `datos/catalogo_abb.json`, tests (13 OK).
- Ojo: proyectos guardados sin evidencia no tienen kA → ese renglón no se dibuja (no se inventa).
- Siguiente: fotos frontales XT1/XT2/OT400 para su marcado; un proyecto por tablero.

## 2026-11-15 19:20 · Claude
- Hecho: requisito del usuario de normativa argentina. Creado `datos/normativa_argentina.json` (5 reglas con fuente, todas por-verificar). Sin código aún.
- Siguiente (en orden): 1) `normativa.py` que controle las reglas; 2) catálogo de accesorios ABB (peines S200/S800, bornes/barras PE y N, tapas) con disponibilidad en Argentina; 3) avisos en editor y DXF; 4) pantalla Normativa en la maqueta.
- Pedir al usuario el texto oficial (771.20, 771.19, IEC 61439) para pasar reglas a verificada.

## 2026-11-15 19:00 · Claude
- Hecho: maqueta de la interfaz (4 pantallas) en el lienzo de diseño; aprobada provisoriamente por el usuario. Sin cambios de código.
- Siguiente: un proyecto por tablero (app.py guarda siempre en datos/ts4_topografia.json) y lista de proyectos.

## 2026-11-15 18:45 · Claude
- Hecho: etiquetas QF centradas y ajustadas al ancho (ya no se pisan). Inscripción APAGADA (`enabled:false` en `apariencias_abb.json`) porque la posición era a ojo: el CAD ABB no trae lo impreso. Título del DXF usa el nombre del proyecto (antes fijo "TS4").
- Ojo: el usuario quiere la inscripción idéntica a la real. Falta foto de frente de S201/S201M, S804N, XT1, XT2, OT400 para fijar posición, renglones y tamaño; recién ahí `enabled:true` + `verifiedWith`.
- Siguiente: posición real de la inscripción; después un proyecto por tablero.

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

## 2026-11-15 01:10 · Claude
- Pedido del usuario: criterio al elegir el gabinete (el 1100 x 2200 era desproporcionado para 12 equipos) y colores reales en el dibujo (no fondo blanco).
- Hecho: `layout_auto.py` elige el gabinete más chico del catálogo que aloja el contenido y acomoda seccionadores, equipos de kit (filas por módulo de kit de 200 mm) y equipos de riel (riel PDRS0600 centrado, misma carcasa pegada, lugar para bornes PE). Criterios en `datos/reglas_layout.json` (propuestas ajustables, no datos de ABB). Ruta `/api/autolayout` y botón 'Armar tablero automático'. Catálogo ampliado con los tamaños del catálogo ABB 1STC803009D0103 (anchos 500/750/1000/1250 funcionales, alturas 1800/2100). Colores: RAL 7035 gabinete y RAL 7012 zócalo (pág. 46 del catálogo; hex aproximados), chapa galvanizada como gris representativo. TS4 -> 850 x 1900 x 600. Tests: 47 OK.
- Límites: el riel PDRS0600 (600 mm) no entra en gabinetes de 500 mm funcionales; no hay otro riel en los datos. La altura mínima de esta familia es 1900 y el TS4 ocupa poco más de la mitad: para tableros chicos conviene sumar la familia de gabinetes de pared/piso SR2 o IS2 (otro catálogo ABB).
- Siguiente [Claude]: cargar la familia SR2/IS2 como candidatos más chicos; kits de montaje XT del catálogo de tableros modulares; STEP de la estructura.

## 2026-11-15 00:30 · Claude
- Hecho: estructura real del gabinete con datos del catálogo técnico ABB `1STC803009D0103` (descargado a la PC del usuario con el navegador y leído desde el repo): `enclosures[].structure` en `catalogo_abb.json` (banda de 50 mm = externo - funcional, hojas de puerta 550+550, lista de partes con código ABB y página). El editor y el DXF dibujan marco, hojas de puerta (retiradas, de trazos), zócalo y la lista de partes en un cajetín (capas ABB_ESTRUCTURA, ABB_PUERTAS, ABB_CAJETIN). Tests: 41 OK.
- Conflicto sin resolver: montantes de 2200 = PUPM2100 (págs. 20 y 23) o PUPM2001 (pág. 24). Corregido typo PFCM0500 -> PCFM0500 en `parts`.
- Sigue esquemático: no hay CAD de las piezas (montantes, manijas, bisagras); manija de palanca PHLS0013 sin posición. El catálogo trae páginas de medidas generales (págs. 129-136) en dibujo, aún sin interpretar.
- Pendiente: kits de montaje de XT (no están en este catálogo; son del catálogo de tableros modulares), STEP de estructura (1STD...), peines y barras en el layout.
