# Mejoras, agregados y cosas por hacer

> Lista viva: el detalle de cada cambio está en BITACORA.md y la foto del proyecto en ESTADO.md.
> Actualizado: 2026-11-18 · Claude. Marcar `[Claude]` / `[Codex]` al tomar un ítem.

## Hecho (últimas sesiones)
- Lista de materiales a prueba de compra errónea: sin renglones repetidos, placa PF fuera si viene con el SR2, System pro E pieza por pieza, códigos combinados separados, canaletas en tiras de 2 m con despiece, peines por código con tramos, equipos no dibujados incluidos, controles antes de comprar (pantalla, CSV y DXF).
- Códigos de pedido verificados (con link) para 19 equipos de los unifilares de prueba: `datos/codigos_pedido_abb.json`.
- Vista con la puerta cerrada: placa grabada con el nombre, orificios de los pilotos del unifilar, cartel de riesgo eléctrico; en editor, PDF/PNG/SVG (selector de vista) y DXF (al lado del interior).
- Bornera equipotencial PE realista (DBL125 + topes), bloque de distribución BRT125A y barra AA8010 con agujeros reales.
- Canaletas automáticas con criterio de armador (verticales a los costados, arriba y abajo de cada fila, lo más anchas que entren); canaletas manuales con medidas estándar; estirar/acortar desde los extremos.
- Tableros más compactos (riel cortado a medida, kit KD sin margen, reserva PE real).
- Fluidez: agregar/duplicar equipo con el siguiente circuito, reordenar en el riel arrastrando, Esc/Supr/Ctrl+Z, aviso si cambia el gabinete.

## Por hacer (prioridad)
1. **Cargar las carcasas que faltan** para que se dibujen (hoy van sólo a la lista): OT100F4, OT160EV03, S 293-C 80, SN201L B16, F204 — con medidas ABB y fuente. Sin esto, algunos tableros quedan sin su interruptor general en el dibujo.
2. **Códigos sin verificar** (quedan "FALTA CÓDIGO"): variante del OT100F4 (N2 seccionador / C conmutador), S 293-C 80, SN201L B16, F204-SX AC-40/0,3 (¿AC o A selectivo?). Fusible tabaquera y portafusible de los testigos; cubrebornes.
3. **Accesorios del OT**: manija y eje (OT160EV03 no los trae; OT400E04P tampoco cargados).
4. **Color de los pilotos**: el unifilar no lo indica; hoy se propone rojo (a confirmar). Permitir elegir color/función por piloto en el editor.
5. **System pro E**: confirmar si montantes/travesaños se venden por unidad o por juego; conflicto PUPM2100 / PUPM2001; manija "una por puerta" con 2 hojas.
6. **Profundidades reales** de XT, OT400 y S800 para validar el gabinete (hoy criterio propio de 200 mm).
7. **Normativa**: reglas todavía "por verificar" hasta tener el texto oficial AEA 90364 / IEC 61439.
8. **Gabinetes que faltan**: SR2 con puerta vidriada, zócalos, IS2, AM2; disponibilidad en Argentina sin verificar.
9. Puerta cerrada: agregar otros elementos de puerta si el unifilar los trae (voltímetro/amperímetro, selectoras, pulsadores de emergencia).

## Propuestas para decidir (Thomas)
- Separar automáticamente un PDF de planta (varios tableros) en un tablero por unifilar.
- Cajetín (rótulo) en el PDF exportado.
- Imán a bordes al mover canaletas.
- Fijar el gabinete al agregar equipos (que no salte a uno más grande sin preguntar).
- Quitar "Nuevo tablero vacío" y "Revisiones" si no se usan.
- Exportar la lista de materiales también a Excel con formato (hoy CSV).
