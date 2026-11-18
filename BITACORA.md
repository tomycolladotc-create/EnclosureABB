# BITÁCORA
> Una entrada por sesión, **la más nueva arriba**, máximo 6 líneas. Al empezar, leer solo las 3 primeras.
> Si pasa de 15 entradas, mover las viejas a `docs/bitacora_vieja.md`.
> Formato: `## fecha hora · agente` + Hecho / Archivos / Ojo / Siguiente.

## 2026-11-15 23:06 · Codex
- Hecho: BOM agrupada en interfaz/DXF, descarga CSV para Excel y control de revisiones numeradas por proyecto.
- Archivos: `bom.py`, `revisiones.py`, `app.py`, `cad_export.py`, `web/index.html`, pruebas y documentación.
- TS4: 18 renglones (envolvente, 8 estructura, 6 equipos, 2 kits, 1 riel); revisión de prueba 0 no persistida.
- Pruebas: 67 OK; JavaScript válido; DXF verifica capa `ABB_BOM` y texto de revisión.
- Ojo: códigos dudosos siguen marcados por confirmar; no se modificaron datos ni geometría KD asignados a Claude.

## 2026-11-15 22:25 · Codex
- Hecho: autoguardado, borrador recuperable, aviso al salir, estado visible, deshacer/rehacer y validación geométrica/técnica en el editor.
- Archivos: `validacion.py`, `datos/reglas_validacion.json`, `app.py`, `web/index.html`, pruebas y documentación.
- Valida: solapamientos, límites de placa, riel DIN, capacidad lineal y profundidad; datos de profundidad faltantes se advierten sin inventar.
- Pruebas: 62 OK, JavaScript válido, API real sobre TS4: 0 errores y 1 advertencia de profundidades ABB pendientes.
- Ojo: no se tocaron datos ni geometría de kits KD asignados a Claude; servidor local activo para revisión.

## 2026-11-15 22:08 · Codex
- Hecho: maqueta Claude Artifact convertida en interfaz real de cuatro pasos: Tableros, Importar, Editor y Exportar.
- Archivos: `web/index.html`, nuevo `web/styles.css`, ruta estática en `app.py`, contrato en `tests/test_web_ui.py`.
- Integrado: proyectos/envolventes, PDF, dibujo SVG, edición, normativa y DXF/PNG/SVG/PDF; vista verificada en navegador.
- Pruebas: 57 OK; JavaScript válido; CSS servido HTTP 200. No se alteraron medidas, catálogo ni trabajo KD de Claude.
- Siguiente: Claude puede continuar rieles KD; la UI nueva es desde ahora la interfaz oficial.

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

## 2026-11-16 11:40 · Claude
- Pedido: tablero automático, sin botones. Importar PDF → agrega equipos propios y arma todo (gabinete, rieles, peines, canaletas) y abre el editor. 'Agregar equipo' (no tenía acción) ahora salta al formulario con QF sugerido + campo Circuito y rearma el tablero al agregar.
- Filas de riel libre: `railRowGapMm`=110 y zonas de etiqueta/portaetiqueta reservadas al proponer canaletas (se veían etiquetas y peines pisando la fila de arriba). 80 pruebas OK. Probado con TSB (15 equipos → SRN6625K) en navegador real.
- Ojo [Codex]: las pruebas de navegador crean proyectos en `datos/proyectos/`; borrarlos antes de commitear.

## 2026-11-16 02:00 · Claude
- Cierre de sesión: el usuario instaló/corre el editor en su PC (`Descargas\EnclosureABB`, Python 3.12 ya instalado pero fuera del PATH; el .bat ahora lo encuentra). Plan, decisiones abiertas y sugerencias para la próxima sesión escritos en ESTADO.md ('PRÓXIMA SESIÓN'). Nada sin subir.

## 2026-11-16 03:00 · Claude
- Pedido del usuario: (1) en lugar del QF mostrar el nombre del circuito del plano (ej. TS-4.2); (2) sin descripciones de accesorios en el dibujo, solo en el cómputo de materiales.
- (1) `circuit` por equipo (importador + TS4 cargado desde Unifilares-25_GENERAL.pdf: QF82→TS-4.2 … QF163→TSMAQ2, QF89/90→TSI-6/7). Se muestra en editor, DXF, BOM y avisos; el QF queda como `tag` interno (peines, normativa y revisiones siguen usándolo).
- (2) Se quitaron textos de accesorios y del riel (DIN-n) en editor y DXF; BOM con categorías Canaleta/Peine/Borne PE/Riel DIN/Kit de soportes DIN. Zona de etiqueta reservada sobre los equipos (30 mm) al proponer canaletas. 79 pruebas OK.
- Ojo [Codex]: el DXF todavía trae la tabla 'LISTA DE MATERIALES' que armaste, ahora con las descripciones de accesorios; si el usuario no la quiere en el plano, sacala del DXF y dejala solo en el export CSV.

## 2026-11-16 02:10 · Claude
- Peines visibles (cuerpo + clavijas por polo, sobre los equipos) y canaletas horizontales propuestas (`wiringDucts`, 22 secciones del catálogo SR2 pág. 6/5; lógica en `accesorios._propose_ducts`). Capas DXF nuevas ABB_CANALETAS / ABB_PEINES. En el editor las etiquetas de los equipos con peine suben para no taparse. 76 pruebas OK.
- Supuestos marcados: B = cara visible y H = profundidad de la canaleta (convención, no cotado); ranura = ancho / paso; ancho de uñas laterales esquemático. TS4 con riel libre: canaletas 40x40 abajo y 15x17 arriba.
- Pendiente [Claude/Codex]: canaletas verticales, edición manual de canaletas, línea RAL 7030.

## 2026-11-15 23:40 · Claude
- Kit KD cargado en 11 SR2 (`kdKit`); `layout_auto` arma con filas fijas de 185 mm; opción riel libre GD (`?free=1`, botón en el editor). TS4 queda en SRN12830K (1200x800) con filas fijas; con riel libre entra en SRN12630K (1200x600).
- Arreglos: peine sin corriente porque faltaba `poles` en QF90 (ahora se deduce de la carcasa: 1pn=2 polos); el bloque de distribución se dibujaba sobre los bornes PE (ahora los respeta). Pendiente conocido: peine con neutro para S804 (QF81/QF85 siguen 'sin peine').
- Ojo [Codex]: el servidor de prueba autoguarda el proyecto abierto en `datos/ts4_topografia.json`; si corrés el editor con el TS4, verificá `git status` antes de commitear.
- 72 pruebas OK.

## 2026-11-15 22:10 · Claude
- Medidas (ancho x alto x largo, mm) de las fichas ABB leídas por WebFetch: PS1/4 21x18x67, PS1/60 20x17x1050, PS3/60 14,8x29x1056, PS4/12 19,3x30,5x212. La ficha trae 'Pitch 44698' (error de planilla): no se copió. El CAD de ABB está en un visor dinámico de la página del producto (new.abb.com/products/<código>, sección 'CAD outline drawing') que no se pudo bajar con el navegador integrado; pendiente [Claude/Codex]: probar con Chrome o pedirlo al usuario.

## 2026-11-15 21:50 · Claude
- Pedido del usuario: el programa propone y el usuario elige (barra de cobre / bloque); completar los datos faltantes de peines y barras.
- Datos cargados con fuente (web, fichas ABB reproducidas por distribuidores; nada se bajó como archivo): PS1/4, PS1/60, PS3/60, PS2/12 (código 2CDL220001R1012), PS4/12 (código 2CDL240101R1012 según Voltimum), S803-BB250 (2CCS800900R0071) con alimentación S803-BBPC120, barras AA8010 (320 A, 20x5, 1000 mm, soportes AA8011) y PBFC2005. Lo que no figuraba en ninguna fuente quedó en null y anotado (Icw del PS2, medidas de varios, corriente de PBFC2005).
- Código: `accesorios.propose` propone `copper_busbar` cuando ningún bloque alcanza y una barra del catálogo sí; `decision` confirmed/discarded; UI con botones en el panel de normativa; límite de peines S200 corregido. Tests: 52 OK.
- Aviso importante: el catálogo ABB describe AA8010 como barra de **neutro o tierra**; su uso como barra de fase es decisión del usuario y está marcado en la nota de la propuesta.
- Siguiente [Claude]: canaletas (ver entrada anterior) y reservar espacio para ellas en layout_auto; CAD de peines/bornes.

## 2026-11-15 21:20 · Claude
- Pedido del usuario: más detalle en la vista. Agregado: cotas (exterior, placa, altura de cada riel desde la placa) en el editor y en el DXF (capa ABB_COTAS, cotas lineales reales de ezdxf) y porta-etiquetas con el tag bajo cada equipo (tamaño propuesto, no dato ABB).
- Evaluado y NO hecho por falta de dato claro: canaletas (el catálogo 1STC804013D0201 las trae en págs. 9/40-9/43 y 6/2-6/3, pero las medidas de sección no se leen bien del texto; hay que mirar la imagen) y barra PE AA8010 (1000 mm, no entra en la placa de 560 mm). Siguiente [Claude]: canaletas con medidas de la imagen de la pág. 9/40 y propuesta de ubicación (sobre y bajo cada riel); barra de tierra que entre en la placa.

## 2026-11-15 20:55 · Claude
- Pedido del usuario: la vista se sentía plana, todo en una capa. Hecho en `web/index.html` (sólo estética, no cambia medidas ni datos): degradado de chapa en gabinete y placa, sombra de la placa sobre el fondo, sombra proyectada de cada equipo, riel DIN con relieve/ranuras/tornillos de fijación, bloque de tierra con terminales, tornillos de la placa (a 14 mm del borde, pág. 9/7 del catálogo SR2), cerraduras en las posiciones del catálogo (pág. 9/6) y bisagras esquemáticas. Título y subtítulo con el gabinete real (antes decía System pro E fijo). Datos nuevos: `structure.locks` en los SR2.
- Pendiente de esta línea [Claude/Codex]: el DXF todavía no dibuja relieve (es 2D plano por diseño); herrajes de los gabinetes System pro E (manijas PHLS0013, bisagras) sin posición; ranuras del riel y bisagras son esquemáticas (pitch 25 mm y posición de bisagras son supuestos visuales, no datos ABB).

## 2026-11-15 20:40 · Claude
- Cierre de sesión por límite de uso: ESTADO.md actualizado (Situación y Pendiente completos, con el punto 0 en curso).
- Estado exacto de lo que estaba haciendo: leí la tabla de selección SR2 (pág. 2/4, imagen) con las filas KD por gabinete; NO hay cambios de código de ese tema todavía. Punto de partida para [Codex]/[Claude]: agregar `kdKit` a los `enclosures` SR2 (datos en ESTADO.md punto 0) y extender `layout_auto._try` para poner los modulares en filas de 185 mm y los XT/OT en la placa.
- Pedido del usuario: 'segui así' con la posición de los rieles según el gabinete; supuestos sin dato a marcar en el JSON con su `status`.
- Último commit antes de esto: 297039d (SR2 como candidatos). Tests 48 OK.

## 2026-11-15 20:10 · Claude
- Pedido del usuario: el gabinete seguía siendo demasiado grande para el TS4.
- Hecho: catálogo ABB 'Enclosures for Automation' 1STC804013D0201 (02.2011) bajado con el navegador (Descargas del usuario) y leído. Cargados los 23 gabinetes SR2 con puerta ciega (códigos SRN...K, págs. 2/5 y 9/6): externo = nominal + 3 mm, placa interna = (ancho-40) x (alto-40) (coincide con la tabla de placas PF.... de la pág. 9/7), rieles GD4006/6006/8006 (pág. 2/8). `layout_auto.py` ahora usa `railOptions` y `functionalOffset` por gabinete y descarta gabinetes con profundidad menor a `minDepthForKitDevicesMm` (200, propuesta de diseño en `datos/reglas_layout.json`). TS4 -> SRN12630K 1200 x 600 x 300 con riel GD4006. Tests: 48 OK.
- Supuestos marcados: la placa está centrada en el gabinete (el catálogo no da su posición); profundidad externa = nominal; la profundidad mínima de 200 mm para XT/OT es criterio propio, no dato ABB (no tenemos profundidades de los equipos). Los códigos de las págs. 2/5 se leyeron de texto; las medidas de la pág. 9/6 se verificaron mirando la imagen.
- No cargado: versiones con puerta vidriada (VK), zócalos ZA...., IS2 (gabinetes de piso) y el catálogo SR2 de dimensiones internas de kits KD.
- Siguiente [Claude]: profundidades reales de XT/OT/S800 para validar el gabinete; kits KD con paneles modulares para el riel; verificar disponibilidad SR2 en Argentina.

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

## 2026-11-15 23:55 · Claude
- S251 resuelto como hipótesis: 'S 251 Na C 10' (QF79, QF80, QF89) se importa con la carcasa del S201 NA (35 x 88 x 69 mm, ficha ABB vía RS) en la serie `s251-na` con `verified: false`. El estado del equipo dice 'carcasa compartida sin confirmar'. Falta confirmar con ABB Argentina; el marcado impreso de esa designación no está validado.
- Pendiente sin CAD: S293 (S290), SN201L, XT1 3P, XT3S 4P. Detalle en `datos/carcasas_pendientes.json`.

## 2026-11-15 23:40 · Claude
- Búsqueda de las carcasas que faltan (pedido del usuario): resultados en `datos/carcasas_pendientes.json`, con fuente y estado por familia.
- Mejor cubiertas: XT1 3P (76,2 x 130 x 70 mm, CAD 1SDH001295R0008) y XT3S 4P (140 x 150 x 70 mm, dos códigos de dibujo en conflicto). Parciales: S293 (S290, 26,25 mm por polo), SN201L (conflicto de profundidad 69/85). S251: nombre antiguo, sin carcasa asignada.
- Límite: la shell de la sesión no puede bajar archivos de ABB (proxy 403). Los CAD hay que bajarlos desde el navegador de la PC del usuario o por Codex.
- Tarea para Codex: bajar 1SDH001295R0008, el CAD de XT3S 4P, S290 y SN201 (+ datasheet 2CSC400002D0209) a cad/abb/<familia>/ y registrarlos en datos/cad_argentina.json.

## 2026-11-15 23:10 · Claude
- Aclaración del usuario: la lámina GENERAL NO es un tablero a separar, es referencia de los modelos que más usa. Descartada la separación; agregado el ranking de uso a docs/cobertura_unifilares.md. Prioridad de carcasas faltantes: S293 3P, SN201L, XT3S, S251, XT1S 3P.
- Hecho: ubicación automática en riel DIN (`colocar.py`, ruta /api/place, botón 'Agregar todos y ubicar en el riel'). Misma carcasa pegada (para el peine), distinta con 4 mm. Si no entra, el equipo queda `unplaced` y la normativa lo avisa. Probado con el TSB: 15 equipos entran en el riel de 600 mm. Tests: 39 OK. Rótulos de equipo más chicos para que no se pisen.
- Pendiente: equipos de kit (XT/OT) y varios rieles según gabinete (solo hay 1 riel en el catálogo); elegir gabinete según contenido.
- Tarea para Codex: carcasas S293 3P, SN201L, XT3S, XT1S 3P y S251 (CAD ABB).

## 2026-11-15 22:45 · Claude
- Hecho: un proyecto por tablero. `proyectos.py` (listar, cargar, guardar, crear), rutas `/api/projects`, `/api/project?id=`, `/api/save?id=`, `/api/project-new`; selector y 'Crear' en el editor (la URL lleva `?id=`). Tests: 33 OK. Probado en el navegador: crear 'Prueba TSB' lo guardó aparte y el TS4 quedó idéntico (mismo md5).
- Pendiente: duplicar y borrar proyectos; el proyecto nuevo copia el gabinete del TS4 (elegir gabinete al crear).
- Siguiente [Claude]: importar un PDF directo a un tablero nuevo y separar la lámina GENERAL por tablero.

## 2026-11-15 22:15 · Claude
- Hecho: bloque de distribución propuesto cuando In supera el peine (elige el de menor corriente que alcance; BRT125A 128x85 mm provisional); regla `accesorio-sin-lugar` avisa si un accesorio no entra en el riel. Tests: 27 OK.
- Límite: solo el BRT125A tiene medidas de frente; los demás bloques quedan 'sin medidas' hasta tener hoja de datos.
- Siguiente [Claude]: un proyecto por tablero + lista de proyectos.

## 2026-11-15 21:50 · Claude
- Hecho: `accesorios.py` (propuesta), rutas `/api/normativa` y `/api/normativa/complete`, panel en el editor, accesorios y avisos en el DXF. Tests: 24 OK. El TS4 real queda sin errores comprobables tras 'Completar accesorios'.
- Límites: geometría esquemática (rectángulos punteados = provisional); un borne PE por QF es simplificación; el cubrebornes no tiene dibujo; S800 sin peine.
- Siguiente [Claude]: bloque de distribución cuando In supera el peine (usar BRT125A 128 mm, a confirmar); luego un proyecto por tablero.

## 2026-11-15 21:20 · Claude
- Hecho: medidas y corrientes de peines PS1/12 y PS3/12 (63 A, 25 kA), BRT125A (128 mm de ancho), bloques Steck (5 referencias), Legrand y Schneider Domae (listado en se.com/ar). Todo por-confirmar salvo lo indicado.
- Conflictos anotados en el JSON: PS3/12 tiene dos versiones con medidas distintas; BRT125A figura con 4x12 y con 11 vías.
- Para Codex: consultar el buscador de ABB Argentina (new.abb.com/low-voltage/efinder-country/ar) por 2CDL210001R1012 y 2CDL230001R1012; elegir qué versión de PS3/12 se vende.

## 2026-11-15 20:50 · Claude
- Hecho: catálogo con `distributionBlocks` (ABB BRT125A, Steck SDM9904/9907, Schneider Distribloc 125/160 A) y familias de peine PS2/PS4; todo por-confirmar. El aviso de `peine-corriente` ahora manda al bloque de distribución.
- Layout: el peine no ocupa ancho extra; el bloque de distribución sí (módulos DIN a confirmar con ficha). Pendiente: fichas y medidas.
- Tarea para Codex: fichas de BRT125A, SDM9904/9907 y Distribloc (corriente, módulos, medidas) y disponibilidad en Argentina.

## 2026-11-15 20:25 · Claude
- Pedido del usuario: en tableros de corriente elevada (TS, auxiliares) se usan barras de distribución o peines según la corriente. Agregada regla `peine-corriente` (error si In del equipo > corriente del peine) y categoría `distributionBars` vacía en el catálogo de accesorios.
- Tarea sugerida para Codex: buscar barras/bloques de distribución usados en Argentina (ABB o equivalente) con corriente, paso y medidas.

## 2026-11-15 20:10 · Claude
- Hecho: `normativa.py` ejecuta las reglas de `normativa_argentina.json` (PE, un borne por conductor, cubrebornes, peines entre equipos contiguos; masas a PE queda manual). Tests en `tests/test_normativa.py`. Política: accesorios genéricos de cualquier marca.
- Ojo: 'un borne PE por circuito QF' es una simplificación declarada hasta confirmar con el texto oficial.
- Siguiente [Claude]: `accessories` en el proyecto y en el editor (agregar barra PE, peines, cubrebornes), avisos en pantalla y DXF.

## 2026-11-15 19:50 · Claude
- Hecho: `datos/accesorios_abb.json` (peines PS1/PS3 de ABB paso 17,5; bornes de tierra Entrelec M4/6.P y M6/8.P) con fuente y estado; lista de pendientes dentro del archivo.
- Hallazgos: ABB Argentina certifica 'Peines de conexión PSx' (confirma que existen allá, no qué códigos). La línea de borneras DIN de ABB (Entrelec) ahora es de TE Connectivity: avisar al usuario/verificar con ABB Argentina. Para S800 no apareció peine de fase.
- Tarea sugerida para Codex: confirmar códigos PSx en Argentina (catálogo ABB Argentina / distribuidores) y bajar CAD de PS1/PS3 y M4/6.P.
- Siguiente [Claude]: `normativa.py` (control de reglas) y peines automáticos en el editor.

## 2026-11-15 19:20 · Claude
- Hecho: requisito del usuario de normativa argentina. Creado `datos/normativa_argentina.json` (5 reglas con fuente, todas por-verificar). Sin código aún.
- Siguiente (en orden): 1) `normativa.py` que controle las reglas; 2) catálogo de accesorios ABB (peines S200/S800, bornes/barras PE y N, tapas) con disponibilidad en Argentina; 3) avisos en editor y DXF; 4) pantalla Normativa en la maqueta.
- Pedir al usuario el texto oficial (771.20, 771.19, IEC 61439) para pasar reglas a verificada.

## 2026-11-15 19:00 · Claude
- Hecho: maqueta de la interfaz (4 pantallas) en el lienzo de diseño; aprobada provisoriamente por el usuario. Sin cambios de código.
- Siguiente: un proyecto por tablero (app.py guarda siempre en datos/ts4_topografia.json) y lista de proyectos.

## 2026-11-15 19:40 · Claude
- Hecho: marcado real en el frente (logo ABB, serie, curva+In, tensión, recuadros Icn y clase; S800: serie, curva, 240/415V~kA, In=) medido en fotos frontales ABB y calibrado con aristas del CAD. Barra común de palancas en S200 2P-4P. Sin monopolares (scope.minPoles=2). Colores S800 corregidos (verde estaba mal ubicado).
- Archivos: `marcado.py` (nuevo), `importador.py` (marking_fields, ensure_marking), `cad_export.py`, `web/index.html`, `datos/apariencias_abb.json` (marking, tieBar), `datos/catalogo_abb.json`, tests (13 OK).
- Ojo: proyectos guardados sin evidencia no tienen kA → ese renglón no se dibuja (no se inventa).
- Siguiente: fotos frontales XT1/XT2/OT400 para su marcado; un proyecto por tablero.

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


## 2026-11-16 12:30 · Claude · Frontend limpio y tablero ya conforme a normativa
- Pedido de Thomas: interfaz más limpia, sin botones inútiles; que el tablero salga ya dentro de normativa (sin Completar/Revisar/Confirmar).
- `web/index.html` + `web/styles.css` reescritos: 3 pantallas (Tableros, Editor, Exportar). Editor: lista de circuitos + "＋ Agregar equipo" (ventana), lienzo con zoom flotante, tarjeta del equipo seleccionado (sólo circuito, modelo, eliminar), chip "Normativa ✓ · N observaciones" con panel, menú "⋯" (gabinete, rearmar, riel libre, importar otro PDF, JSON). Autoguardado: ya no hay botón Guardar.
- Importar PDF desde Tableros crea un tablero nuevo con el nombre del archivo y lo arma solo; "Importar otro unifilar" (menú ⋯) agrega al tablero abierto.
- `accesorios.complete(..., auto_confirm=True)` confirma sola bloque/barra de distribución; `/api/normativa/complete` se llama solo tras cada cambio (si cambian los accesorios, se redibuja).
- `layout_auto.autolayout_conforme`: si bornes PE/barras no entran, prueba el gabinete siguiente. Los PE se buscan en todos los rieles (antes sólo el primero).
- Peines: un peine sólo une equipos con los mismos polos (antes "mezcla de polos" daba error de normativa).
- Observaciones que quedan (honestas, por falta de datos): peine S804 4P con neutro; mezcla de polos adyacentes sin peine; masas a tierra (manual en obra); profundidades ABB pendientes (aparecen como "datos pendientes", no cuentan en el chip).
- Tests: 82 OK (nuevos: UI sin botones de normativa, auto-confirmación).


## 2026-11-16 13:30 · Claude · Prueba de punta a punta y bugs de fondo
- Nuevo `tests/e2e/prueba_interfaz.py` (Playwright + Chrome): recorre todos los botones (abrir/reabrir, zoom, renombrar, deshacer/rehacer, arrastrar, agregar/eliminar, chip, menú, rearmar, riel libre, cambiar gabinete, JSON, exportar DXF/SVG/PNG/CSV, duplicar/borrar, importar los 6 PDF de ejemplo). 61/61 OK. CORRERLA ANTES DE ENTREGAR CAMBIOS DE INTERFAZ.
- Bug de fondo (venía de antes): al abrir un tablero se reemplazaban los rieles del armado automático por los del catálogo y todo DIN iba al primer riel → "QF81 es DIN pero no está sobre un riel". Ahora se respetan los rieles guardados; `alignDin` usa el riel más cercano.
- Al abrir, si el tablero no cumple, se rearma solo (una vez).
- Soltar un equipo encima de otro: vuelve a su lugar y avisa.
- Cambiar gabinete (menú ⋯) rearma dentro de ese gabinete (`/api/autolayout?enclosure=id`); si no entra, se mantiene el anterior.
- Navegación: `location.search` con `#editor` metía el hash en el id del proyecto (duplicar/abrir/crear). Corregido con `location.href`.
- PDF de toda la planta (25_GENERAL, 132 equipos de ~20 tableros): ya no crea un tablero roto; avisa qué tableros contiene. Idea a futuro: separar automáticamente un tablero por prefijo de circuito (TS-1, TSB-1…).
- Menú ⋯ se cierra al elegir una opción; aviso (toast) visible en todas las pantallas.


## 2026-11-16 12:20 · Claude · Un solo rótulo por equipo
- Pedido de Thomas: el nombre del circuito aparecía dos veces (arriba del equipo y en el porta-etiqueta). Se quitó el de arriba en el editor (render) y en el DXF el texto pasó a un porta-etiqueta bajo el equipo (rectángulo 12 mm + texto, capa ABB_ETIQUETAS), igual que en pantalla.
- Tests 82 OK; e2e 61/61 OK.


## 2026-11-17 22:50 · Claude · Canaletas a mano
- Pedido de Thomas: las canaletas automáticas no sirven bien; quiere dibujarlas él con medidas estándar donde quiera.
- Editor: botón "＋ Canaleta" (sección del catálogo ABB `wiringDucts.sections`, orientación H/V, largo). Al agregar la primera, `project.ductMode = "manual"`: las automáticas existentes se convierten en editables y `accesorios.propose` deja de proponer canaletas. Menú ⋯ → "Volver a canaletas automáticas".
- Canaleta seleccionada: tarjeta con sección, largo, girar, eliminar; arrastre con paso de 5 mm; flechas 5 mm (Shift 1 mm); Supr elimina. No puede quedar sobre un equipo (vuelve a su lugar); si un rearmado la deja encima de un equipo, el chip de normativa lo marca como error.
- Servidor: `accesorios._manual_duct` normaliza la canaleta (código 1SL90../1SL91.. según ranura, largo, descripción para el cómputo); `GET /api/ducts`; DXF dibuja canaletas verticales.
- Bug corregido: la revisión de normativa en segundo plano podía pisar un cambio recién hecho (respuesta vieja). Ahora se descarta si el proyecto cambió.
- Tests 86 OK; e2e 78/78 (dos corridas).


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


## 2026-11-18 00:30 · Claude · Canaletas automáticas con criterio de armador + estirar desde los extremos
- Thomas mostró un tablero armado por él: canaletas verticales a ambos lados y horizontales arriba y abajo de cada fila (también cajas moldeadas en kit KD), lo más anchas que entren.
- `accesorios._propose_ducts` reescrito: verticales laterales (hasta `ductSideMaxWidthMm` 60) si hay lugar entre borde y equipos/rieles; filas = equipos/accesorios solapados en altura (no sólo rieles DIN); canaleta arriba y abajo de cada fila, de vertical a vertical; entre filas una compartida o una pegada a cada fila si sobran `ductMinFreeBetweenMm`; ancho = el mayor del catálogo que entra (25..`ductMaxWidthMm` 80). Se quitó la franja de 30 mm sobre los equipos (era para el rótulo superior eliminado el 16/11).
- Editor: todas las canaletas se pueden tocar; al tocar una automática pasan todas a manual (aviso). Extremos con "agarre" (cursor ↔ / ↕): arrastrar estira o acorta en pasos de 5 mm (mín. 50 mm); si queda sobre un equipo, vuelve.
- Bugs: al pasar a manual se perdía la orientación vertical; canaleta nueva sin hueco libre caía sobre equipos (ahora puede cruzar canaletas, nunca equipos).
- Tests 87 OK; e2e 104/104 (dos corridas).
