# Revisión final de la entrega eléctrica de Pabellón 6

**Resultado del 26/11/2026: quedan observaciones que impiden cerrar la entrega para ejecución.** Se revisó `Entrega_Electrica_Pabellon6_OT1.zip`, SHA-256 `a389721ae180381c6ecc1743770ab28afeb4841076ff4614d7d27536d52270bb`. Las dos copias locales del ZIP son idénticas y sus 15 archivos pasaron la verificación de integridad.

## Puntos por resolver antes de emitir

| Hallazgo | Dónde aparece y qué falta |
|---|---|
| **Poder de corte** | Hay 53 salidas en 11 tableros con poder de corte declarado inferior a la `Ik máx` de sus barras. El pliego, §7.2, admite una combinación con filiación certificada o un equipo cuyo poder de corte propio cubra la `Ik`. El paquete no identifica las combinaciones certificadas. Prioridad para `QF104` de TS5 (6 kA frente a 30,6 kA), `CSB-1.3`/`.4` (6 kA frente a 6,5 kA) y `CSB-1.13` más los seis circuitos de emergencia (4,5 kA frente a 6,5 kA). Ver PL-104, hojas 36 y 60, y la planilla PN-103. |
| **Barras de distribución y tierra** | PL-104, hoja 5, deja a dimensionar la barra de distribución del TGBT de 2.000 A. Las hojas 5, 8, 17, 29 y 32 dejan fuera del dibujo las barras PE para la acometida de `6×150 mm²` y los PE de `70/70/95/95 mm²` de TS1 a TS4. Las listas declaran una bornera con entrada de hasta 35 mm². Falta definir las barras, sus terminales y su ubicación en los topográficos. |
| **Recorridos sin identificación en planta** | Los 126 circuitos derivados figuran en la planilla y en sus unifilares. En las plantas y DWG entregados quedan sin rótulo de circuito o recorrido individual identificable 16 salidas a rooftop (`CA-1.1` a `CA-4.4`), tres de termotanques (`CSB-1.8` a `.10`) y tres de Food Trucks (`CSFT1-1`, `CSFT2-1`, `CSFT3-1`). PL-002 sí ubica los tableros de rooftop y de Food Trucks. La segunda bomba está contemplada en la abreviatura `CSB-1.3/1.4` y se excluyó del conteo de 22. |
| **Escalas gráficas superpuestas** | En PL-001, PL-002, PL-105, PL-106 y PL-107, la escala 1:250 se superpone al testigo de 2 cm y al texto de control de impresión, sobre el cajetín inferior derecho. PL-101 tiene esa zona despejada. Hace falta corregir las presentaciones y volver a plotear los cinco A0. |

### Salidas que requieren verificar el poder de corte

| Tablero | Ik en barras | Salidas a cotejar con la filiación |
|---|---:|---|
| TS1 | 9,3 kA | QF19 hacia TSAA, CS-1.2 a .5, CS-1.12, QF30 hacia TSL1, CSI-1 y CSI-2 (9) |
| TS2 | 15,4 kA | CSI-3 y QF96 hacia TSI1 (2) |
| TSMAQ1 | 8,2 kA | CSMAQ1-1.1 a .3 (3) |
| TS3 | 21,2 kA | CSI-4 y CSI-5 (2) |
| TS4 | 24,7 kA | CSI-6 y CSI-7 (2) |
| TS5 | 30,6 kA | CSI-8 y QF104 hacia TSI2 (2) |
| TS AUX 1 | 6,3 kA | CA-1.1 a .4 (4) |
| TS AUX 2 | 9,6 kA | CA-2.1 a .4 (4) |
| TS AUX 3 | 14,9 kA | CA-3.1 a .4 (4) |
| TS AUX 4 | 14,1 kA | CA-4.1 a .4 (4) |
| TSB | 6,5 kA | CSB-1.1 a .6 y CSB-1.8 a .18 (17) |

En TSB, el pliego informa 47 A en régimen normal con las bombas principales excluidas por simultaneidad y 66,5 A nominales por bomba principal. Falta documentar la demanda y el arranque con una bomba en servicio y las demás cargas que queden activas, con la protección de alimentación de 100 A. La verificación en placa ya está pedida en el §7.2. Para la emergencia, el §7.8 exige supervisar la falta de tensión del alumbrado normal por sector. PL-107 identifica la alimentación permanente y los seis circuitos, pero no representa esa supervisión.

## Otras diferencias entre documentos

- **Nombre `TSI2`.** El unifilar y la lista de TS5, hojas 36 y 38, y la fila de `QF104` de PN-103 dicen `TSl2` con ele minúscula. El topográfico, hoja 37, el tablero de destino, hojas 42–44, y PL-002 indican `TSI2`. La descripción, `QF104`, `WC103` y los 23 m identifican el mismo alimentador.
- **Columna «Cabecera (Genérica)» en PN-103.** En TS1–TS6, TS AUX 1–4 y TSMAQ1/2 muestra una salida del propio tablero. Por ejemplo, para TS1 muestra el termomagnético de 25 A `QF19` que alimenta TSAA, cuando la protección de entrada se encuentra en TGBT (`QF2`, 200 A). Los 12 unifilares de estos tableros dibujan la entrada directa a barras. La columna debe identificar la protección aguas arriba o indicar entrada directa a barras, según lo que se quiera informar.
- **Ítems de cotización.** El resumen del pliego, §15, y CM-001 usan los mismos números para partidas distintas. Por ejemplo, 15.2.1 corresponde a la acometida y zanja de 40 m en el pliego, y a 2.082 m de cable `2×(1×2,5)+1G2,5` en el Excel. El 15.1.2 agrupa seis tableros en el pliego y corresponde sólo a TS1 en el Excel. Hace falta una numeración de resúmenes distinta o remisiones explícitas a los ítems del Excel.
- **Terminaciones de termotanques.** CM-001 15.3.8 agrupa nueve terminales de bombas, presurización y termotanques. Los nueve circuitos `CSB-1.2` a `.10` alimentan diez equipos, porque `CSB-1.8` comprende dos termotanques. El detalle en planta debe aclarar si comparten la caja y cómo se contemplan ambas conexiones.
- **CCTV.** Los 20 enlaces de PL-106 suman 948 m y su tabla indica que incluyen 3 m de reserva por enlace. CM-001 item 15.6.2 y el pliego computan 1.150 m, sin explicar los 202 m adicionales. La nota de la boca y el pliego piden 1,5 m de reserva en el punto de conexión. PL-106 también dibuja una UPS de 1 kVA, ausente como suministro explícito del ítem 15.6.4 del rack.
- **Formaciones de cable.** El pliego, §15, menciona 26 tipos LS0H. Hay 27 formaciones distintas al incluir la acometida XLPE, que aparece como un renglón propio en CM-001. El total eléctrico permanece en 6.774 m.
- **Estado de los DWG.** AutoCAD 2027 abrió los cuatro archivos y exportó sus presentaciones a DXF. Las seis presentaciones tienen papel de 1189 × 841 mm y los dibujos carecen de referencias externas DWG. `AUDIT` en modo de lectura informó 39 incidencias en cada DWG. Una corrida de diagnóstico en copia de PL-005 identificó referencias XData sin destino y tipos de línea discordantes en vértices de polilíneas. AutoCAD sustituyó las fuentes Open Sans en esta instalación. El ZIP no trae un DWG editable de PL-104. Conviene explicitar el alcance de la entrega editable y sanear los DWG antes de emitir.

## Verificaciones que cerraron

- PL-104 contiene las 77 hojas A1 numeradas e indexadas. Los 24 tableros tienen su unifilar, ambas vistas topográficas y su lista individual. Se verificaron los contornos a la escala indicada y se leyeron los 161 portaetiquetas en recortes. Los 161 aparatos figuran en las listas individuales y en la suma del consolidado.
- El cruce de PN-103 con los unifilares, por tablero y etiqueta, conserva los 150 tendidos únicos (acometida, 23 alimentadores y 126 derivados), con sus formaciones y longitudes. El total de 6.774 m coincide con CM-001 y PL-104. Coinciden también las 12 bajadas de 32 A, las 24 de 63 A y el ajuste especificado `Ir = 63 A`.
- Los 97 renglones del consolidado PL-104 coinciden en cantidades y unidades con la hoja `Tableros - BOM Generica`. La cotización tiene 92 partidas y siete subtotales que cubren sus filas. El total de PN-103 suma `L4:L153`. Los libros están configurados para recalcular al abrir y se comprobaron las referencias de las fórmulas y los totales a partir de los datos de entrada.
- Las 59 direcciones de incendio aparecen en PL-105. Se comprobaron los 20 puntos de CCTV de PL-106 y los seis circuitos dedicados de PL-107, con idénticas longitudes de emergencia en PN-103. PL-107, pliego y CM-001 coinciden en 67 equipos autónomos y seis carteles pasivos.
- Se renderizaron las 83 hojas de ploteo y las nueve páginas del pliego. Se cotejó el texto del Word con el PDF emitido desde Word. Las diferencias de formato, dimensiones nominales frente a exteriores y redondeo de un metro en el subtotal de bandejas se trataron como menores.

La revisión cruzó los archivos emitidos y los 24 proyectos locales. El informe original de cálculo que los proyectos identifican como `correccion cargas v2.pdf` no está incluido en el ZIP. Quedan abiertos los cálculos de coordinación y arranque, el dimensionado de barras, el trazado de recorridos sin identificar y la comprobación del ploteo A0 corregido. La auditoría geométrica de los proyectos dio cero errores. La nueva auditoría de nombres del lote detectó el vínculo `QF104`. El control de impresión se hizo sobre los PDF a escala de papel.
