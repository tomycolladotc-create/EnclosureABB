# Mejoras, agregados y cosas por hacer

> Lista viva: el detalle de cada cambio está en BITACORA.md y la foto del proyecto en ESTADO.md.
> Actualizado: 2026-11-19 · Claude. Marcar `[Claude]` / `[Codex]` al tomar un ítem.

## Hecho (últimas sesiones)
- Lista de materiales a prueba de compra errónea: sin renglones repetidos, placa PF fuera si viene con el SR2, System pro E pieza por pieza, códigos combinados separados, canaletas en tiras de 2 m con despiece, peines por código con tramos, equipos no dibujados incluidos, controles antes de comprar (pantalla, CSV y DXF).
- Códigos de pedido verificados (con link) para 19 equipos de los unifilares de prueba: `datos/codigos_pedido_abb.json`.
- Vista con la puerta cerrada: placa grabada con el nombre, orificios de los pilotos del unifilar, cartel de riesgo eléctrico; en editor, PDF/PNG/SVG (selector de vista) y DXF (al lado del interior).
- Bornera equipotencial PE realista (DBL125 + topes), bloque de distribución BRT125A y barra AA8010 con agujeros reales.
- Canaletas automáticas con criterio de armador (verticales a los costados, arriba y abajo de cada fila, lo más anchas que entren); canaletas manuales con medidas estándar; estirar/acortar desde los extremos.
- Tableros más compactos (riel cortado a medida, kit KD sin margen, reserva PE real).
- Fluidez: agregar/duplicar equipo con el siguiente circuito, reordenar en el riel arrastrando, Esc/Supr/Ctrl+Z, aviso si cambia el gabinete.

## Testigos de fase (2026-11-19)
- Hecho: opción en ⋯ para agregar/quitar testigos en la puerta con sus fusibles E 91/32 ubicados en el riel; van a la lista con código.
- Pendiente: ubicar los fusibles al lado del general (hoy van al final del riel, junto a la bornera PE); elegir color de las luces desde el editor; confirmar el código del fusible E 9F10 GG1 con ABB Argentina.

## Revisión de errores (2026-11-19, tarde) → ver `docs/LECCIONES.md`
- Corregidos los 19 errores de la revisión (tabla en LECCIONES). La auditoría los detecta en la interfaz.
- Pendiente: barras de fase ABB de más de 125 A en el catálogo (hoy quedan «a dimensionar»); barra de tierra ABB para PE grueso.
- Pendiente: códigos de los kits System pro E para E2.2, XT3, T4, T2 y XT1 3P.
- Pendiente: con kit KD, ofrecer automáticamente riel libre si da un gabinete más chico (hoy es opción del usuario).

## Hallazgos de la prueba como usuario (2026-11-19, 24 tableros del GENERAL)
- Corregido: nombre del tablero tomado de la cola numérica del archivo ("4 5 6") → nombre completo si la cola no tiene letras.
- Corregido: el proyecto nuevo guardaba como `source` el PDF del TS4 de plantilla.
- Corregido (tarde): el nombre sale del rótulo del unifilar.
- Corregido (tarde): el general va solo arriba; los kits SPE van a la lista (sin código los que falten).
- Corregido (tarde): TS-6 sin hueco (general de riel arriba) y gabinetes más chicos.
- Pendiente: el botón PDF abre el diálogo de impresión del navegador; ofrecer descarga directa de PDF.

## Hallazgos de la prueba como usuario (2026-11-18, ronda 1) — corregidos
- Puerta de gabinete chico (300 mm): el cartel de riesgo se salía de la puerta → se ajusta al lugar libre (editor y DXF).
- Título del dibujo tapado por el selector de vista y subtítulo cortado en gabinetes chicos → título proporcional; selector arriba a la izquierda (a la derecha lo tapaba la tarjeta del equipo).
- Cotas de rieles superpuestas ("76 mm222.25 mm") → cotas encadenadas y redondeadas al mm.
- Vista de puerta mostraba cotas de placa y rieles → sólo medidas exteriores.
- "Agregar equipo" proponía un circuito que ya existía entre los equipos no dibujados (TSL2-3) y un modelo genérico sin código ("S201M Na") → siguiente circuito libre real y el modelo más usado del tablero (con su código).
- Tarjeta del equipo: ahora muestra qué código de pedido va a la lista (verificado) o si falta.
- Peines: tramos iguales se suman ("2×14, 2×14" → "4×14"). Favicon (error 404 en consola).

## Por hacer (prioridad)
- Códigos de pedido de los equipos: 63 renglones de interruptores/seccionadores sin código (XT, S200, S800, OT…): cargarlos desde las tablas de pedido de los catálogos ABB (no deducirlos del modelo).
- Verificar con fotos ABB los 37 rectángulos de color de la lista congelada (reglas_validacion.json → freeRectNearMissKnown) y pasarlos a semillas o ajustarlos.
- S290: hoy el frente sale del dibujo vectorial del catálogo ABB (no a escala en alto); si ABB publica CAD, reemplazarlo.
- Bajar el STEP 3D de S800 (S803/S804N) de ABB Library y reemplazar el DXF 2D (hoy el frente se dibuja centrado con margen porque su proporción difiere de la ficha).
1. ~~Cargar las carcasas que faltan~~ **Hecho 2026-11-18** con CAD ABB: OT100/125F4, OT125F3, OT160EV03/OT200-250E03, OT160EV04/OT200-250E04, F204, F202, SN201 (+ S200P como hipótesis). **2026-11-19:** cargados E2.2 4P, XT3 4P, XT1 3P, T4 4P, T2 3P, S803, OT63/80F3/F4. **Queda sin dibujar:** S 293-C 80 (S290, sin CAD en ABB Library: decidir reemplazo). Colores e inscripciones de las carcasas nuevas: medir con foto frontal ABB.
2. **Códigos sin verificar** (quedan "FALTA CÓDIGO"): variante del OT100F4 (N2 seccionador / C conmutador), S 293-C 80, SN201L B16, F204-SX AC-40/0,3 (¿AC o A selectivo?). Fusible tabaquera y portafusible de los testigos; cubrebornes.
3. **Accesorios del OT**: manija y eje (OT160EV03 no los trae; OT400E04P tampoco cargados).
4. **Color de los pilotos**: el unifilar no lo indica; hoy se propone rojo (a confirmar). Permitir elegir color/función por piloto en el editor.
5. **System pro E**: confirmar si montantes/travesaños se venden por unidad o por juego; conflicto PUPM2100 / PUPM2001; manija "una por puerta" con 2 hojas.
6. **Profundidades reales** de XT, OT400 y S800 para validar el gabinete (hoy criterio propio de 200 mm).
7. **Normativa**: reglas todavía "por verificar" hasta tener el texto oficial AEA 90364 / IEC 61439.
8. **Gabinetes que faltan**: SR2 con puerta vidriada, zócalos, IS2, AM2; disponibilidad en Argentina sin verificar.
9. Puerta cerrada: agregar otros elementos de puerta si el unifilar los trae (voltímetro/amperímetro, selectoras, pulsadores de emergencia).

10. **Siempre "FALTA CÓDIGO" en todos los tableros**: cubrebornes (no hay producto elegido) y fusible "tabaquera" + portafusible de los testigos. Elegir productos reales (ABB) para que la lista salga completa.
11. Al agregar equipos el gabinete cambia solo (se avisa); evaluar pedir confirmación antes de cambiarlo.

## Propuestas para decidir (Thomas)
- Canaletas: la lista pide tiras de 2 m pero ABB las vende por caja (32–48 m). ¿Mostrar la cantidad en cajas, o en tiras porque el distribuidor las vende sueltas?
- Separar automáticamente un PDF de planta (varios tableros) en un tablero por unifilar.
- Cajetín (rótulo) en el PDF exportado.
- Imán a bordes al mover canaletas.
- Fijar el gabinete al agregar equipos (que no salte a uno más grande sin preguntar).
- Quitar "Nuevo tablero vacío" y "Revisiones" si no se usan.
- Hecho 2026-11-23: Excel de equipamiento eléctrico de varios tableros desde Exportar.
- Plano de fabricación: lista de materiales del tablero en el espacio libre de la hoja; opción A0 si el topográfico queda chico.
- Plano de fabricación: guardar varios juegos de rótulo (uno por cliente) y elegir cuál usar.
- Hecho 2026-11-23: PDF único de entrega (carátula, índice, tableros a escala, lista) con rótulo completo y hojas numeradas.
