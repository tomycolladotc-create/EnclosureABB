# Topográficos de tableros

## Editor local

En Windows, abrí `iniciar_editor.bat`. También podés ejecutar `python -m pip install -r requirements.txt` y luego `python app.py`; la interfaz abre en **http://127.0.0.1:8765**.

La aplicación sigue cuatro pasos: **Tableros → Importar → Editor → Exportar**. Permite cargar el PDF exportado por DOC, revisar los equipos detectados, mover/agregar/borrar equipos, elegir una envolvente ABB, guardar el proyecto y exportar DXF, SVG, PNG o PDF mediante la impresión del navegador. Cada tablero se guarda por separado: se puede crear vacío eligiendo su envolvente ABB, duplicar uno completo o borrar los que ya no se usan; el TS4 base está protegido. También abre y descarga el proyecto en JSON. Las dimensiones de carcasas ABB son fijas en el catálogo. Los equipos modulares se alinean con el riel DIN del perfil seleccionado y el riel se exporta en una capa DXF propia. La extracción automática depende de que el PDF tenga texto seleccionable; los resultados deben revisarse.

El catálogo se encuentra en `datos/catalogo_abb.json`. Cada envolvente tiene un perfil de montaje con rieles ABB PDRS0600 y coordenadas definidas para este proyecto. ABB suministra el kit, pero la posición exacta del riel depende de la configuración interna y requiere validar el bastidor y la distribución. Las carcasas comparten dimensiones por familia y cada dispositivo conserva su etiqueta y modelo. El editor dibuja envolventes a escala; todavía faltan el frente CAD de S251, las inscripciones exactas, la selección completa de accesorios y el cálculo de montaje y barras.

## Archivos CAD oficiales

El catálogo registra la fuente CAD y el estado de adquisición por familia. En `cad/abb/` hay 12 archivos CAD oficiales descargados de ABB Library: XT1 y XT2 fijos 4P en STEP; S800 4P en DXF y STEP; S201M 1P en DWG y STEP como referencia complementaria; S201M Na 1P+N en DWG y STEP para QF90; familia OT315–OT400E04 en DWG, DXF e IGS; y un DXF adicional de bornes XT2. El inventario guarda el identificador ABB, revisión, tamaño y SHA-256 de cada archivo. Los frentes 2D de XT1, XT2, S800, S201M Na 1P+N y OT400E04 se extraen del CAD ABB y se guardan en `datos/frentes_cad.json`. El editor los muestra y el DXF crea un bloque reutilizable por familia. QF89 sigue marcado SIN CAD; las inscripciones y el kit de manija/eje del OT400E04P no están modelados.

El inventario `datos/cad_argentina.json` cruza cada referencia del TS4 con evidencia de oferta argentina y con la fuente CAD. La carcasa de familia compartida no cambia las inscripciones nominales: C32, C10, TMD y TMG deben incorporarse al bloque final. Para QS1 se seleccionó OT400E04P (1SCA022719R1810), listado por un distribuidor argentino con manija y eje; el unifilar indicaba OT400E04 base, por lo que la variante y el montaje deben aprobarse antes de fabricación. No hay datos para afirmar que la P sea la más vendida. El XT2 de código exacto aún no tiene una oferta local confirmada; sus CAD se conservan por corresponder al unifilar. El S251 Na C10 de QF89 se identificó como ABB histórico 1P+N de 6 kA (código 16060722 / EF0722); no se localizó CAD oficial ni oferta argentina vigente. QF90 corresponde a S201M-C10NA 1P+N (2CDS271103R0104); la carcasa frontal 2D está integrada desde STEP ABB, aunque faltan las inscripciones exactas y comprobar la oferta comercial argentina. La envolvente seleccionada también requiere verificar disponibilidad argentina de la configuración completa. En `referencias/abb/` quedó el PDF técnico de S800 con dibujo acotado, solo para cotejo dimensional.

El caso TS4 está separado en tres piezas:

- `datos/ts4_topografia.json`: modelo de gabinete, medidas, referencias, componentes y posiciones de los dispositivos.
- `generar_topografico.py`: genera el PDF, PNG y DXF a partir de esos datos.
- `salida/`: archivos generados para revisar o abrir en AutoCAD.

Las coordenadas del proyecto están en milímetros y son relativas al área funcional ABB. Para mover un dispositivo o corregir su rótulo, editá su registro en el JSON y volvé a ejecutar el generador. Las capas `ENVOLVENTE_DISPOSITIVO` y `PENDIENTE_VERIFICAR` en el DXF distinguen medidas de familia verificadas de equipos que requieren confirmación.

La envolvente seleccionada corresponde a ABB System pro E power 185 mm: bastidor funcional 1000 × 2100 × 500 mm, exterior 1100 × 2200 × 600 mm y zócalo de 100 mm. Para los seis Tmax XT1 y el XT2 se identificaron los kits ABB fijos PHDX1401 y PHDX2401, respectivamente, ambos de módulo H=200 mm.

La distribución interna sigue siendo preliminar: hay que coordinar los kits con la celda de barras y completar la BOM, el montaje del seccionador QS1, los dispositivos DIN, la geometría útil de montaje, las barras y el CAD frontal faltante de QF89 antes de liberar para fabricación.

## Vista 2D CAD

`python generar_topografico.py` produce SVG, PNG, PDF y DXF del TS4 en `salida/`. El editor ofrece zoom, vista de equipos y desplazamiento. El DXF usa unidades milimétricas y bloques por familia con las mismas trayectorias que la vista SVG. Para regenerar las trayectorias desde STEP/IGES/DXF oficiales, instalá `requirements_cad.txt` y ejecutá `python work/proyectar_cad.py`. Los CAD originales y el catálogo conservan la procedencia. La envolvente y el riel se representan como montaje propuesto, no como configuración ABB aprobada.

## Apariencia de los equipos

`datos/apariencias_abb.json` contiene las capas de color por familia: carcasa, franja ABB, mandos y ventanas de estado. Se calibraron visualmente con imágenes oficiales ABB y se dibujan debajo de las trayectorias CAD. Las capas también se exportan como sólidos RGB en el DXF. El CAD mecánico no aporta una textura fotográfica fiel; los colores vectoriales aproximan el aspecto real. Las inscripciones exactas siguen pendientes de cotejar con cada variante.
