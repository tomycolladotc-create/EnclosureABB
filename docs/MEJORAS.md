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

## Hallazgos de la prueba como usuario (2026-11-19, 24 tableros del GENERAL)
- Corregido: nombre del tablero tomado de la cola numérica del archivo ("4 5 6") → nombre completo si la cola no tiene letras.
- Corregido: el proyecto nuevo guardaba como `source` el PDF del TS4 de plantilla.
- Pendiente: nombres por circuito quedan "TSB-1", "TSI1-1", "TA-1" (el prefijo común de los circuitos); leer el nombre del tablero del rótulo del unifilar.
- Pendiente: TGBT con E2.2 — el general comparte fila con el T2; un armador lo pondría solo arriba (o en columna propia). Kit/travesaño de montaje del Emax y kits de XT3/T4/T2/XT1 3P sin código.
- Pendiente: TS-6 y TA-1 quedan con mucho hueco (el gabinete lo fija el kit de cajas moldeadas); evaluar fila mixta caja moldeada + riel.
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
- Exportar la lista de materiales también a Excel con formato (hoy CSV).
