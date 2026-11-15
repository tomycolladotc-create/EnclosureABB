# Arquitectura inicial: generador de topográficos de tableros

## Objetivo

Convertir un unifilar ABB e-Design DOC exportado a PDF en una propuesta editable de disposición física del tablero y exportarla a formatos de imagen y CAD. El unifilar aporta datos eléctricos; el montaje físico es una propuesta que se debe revisar y aprobar técnicamente.

El resultado principal es una **vista topográfica frontal 2D**, editable y en escala real. La vista exterior de la puerta y la vista del contrafrente de montaje se modelan como vistas distintas para evitar confundir lo visible con la ubicación de montaje.

## Principios que guían el diseño

- Ninguna dimensión, catálogo, regla de distribución, fabricante o formato de exportación queda mezclado con la interfaz.
- Datos de dispositivos y gabinetes viven en catálogos versionados y editables, con fuente, fecha y unidad explícitas.
- El proyecto se guarda en un formato neutral, con versión de esquema y migraciones para proyectos anteriores.
- La geometría interna trabaja en milímetros; los zooms y formatos de pantalla no alteran medidas.
- La importación presenta campos detectados, confianza y origen en el PDF. El operador puede corregir antes de generar el topográfico.
- Cada pieza del dibujo conserva referencia al dispositivo, catálogo y ubicación que la originó.
- El exportador DXF consume el mismo modelo geométrico que el PNG/PDF; no hay dibujos separados por formato.

## Módulos previstos

```text
app/
  core/             modelo del proyecto, unidades, validaciones, versionado
  importers/pdf/    extracción de texto y coordenadas; OCR como adaptador opcional
  importers/dxf/    lectura de geometría CAD si se agrega como entrada
  catalog/          carga, búsqueda, validación y edición de catálogos
  layout/           reglas de montaje, rieles, espacios y distribución inicial
  geometry/         figuras, cotas, capas y transformaciones en mm
  editor/           selección, arrastre, rotación, edición y borrado con undo/redo
  exporters/png/    render raster desde geometría compartida
  exporters/pdf/    impresión a escala
  exporters/dxf/    entidades CAD, capas, textos y unidades
  ui/               pantallas y componentes; sin reglas eléctricas embebidas
catalogs/
  devices/          por fabricante y familia, con procedencia de cada geometría
  enclosures/       líneas comerciales argentinas y tamaños normalizados
rules/              políticas de layout configurables y explicables
schemas/            esquema JSON de proyecto y catálogos
docs/               decisiones, guía para agregar fabricantes y exportadores
```

## Separación entre datos y código

Un catálogo de producto contiene identidad comercial, dimensiones, forma gráfica, puntos de anclaje y fuente. Las medidas exactas de montaje se guardan separadas de las medidas exteriores. Un dispositivo sin dimensión verificada se marca como estimado y no se presenta como geometría real.

Las reglas de layout reciben un tablero, su catálogo, los componentes y las restricciones. Devuelven una propuesta con advertencias explicables. No modifican el modelo eléctrico ni cambian especificaciones de protección.

Los dispositivos se muestran usando bloques vectoriales 2D o proyecciones ortogonales de CAD mecánico del modelo exacto. Cada bloque identifica su vista (frontal, lateral o montaje) y variante (polos, terminales, manija y montaje). Una foto o pictograma comercial no cuenta como bloque dimensional.

## Modelo de datos inicial

```json
{
  "schemaVersion": 1,
  "project": {"name": "", "sourceFile": "", "units": "mm"},
  "boards": [{
    "id": "board-1",
    "name": "TS4-PORT 11-12-13-14",
    "enclosure": {"catalogId": null, "width": null, "height": null, "depth": null},
    "devices": [{
      "id": "QF81",
      "tag": "-QF81",
      "catalogId": null,
      "source": {"page": 1, "text": "S804N-C32", "confidence": 1.0},
      "electrical": {"poles": 4, "ratedCurrentA": 32},
      "placement": {"x": 0, "y": 0, "rotation": 0}
    }]
  }]
}
```

Los valores desconocidos quedan como `null`; el sistema no completa dimensiones físicas por inferencia silenciosa.

Una instancia gráfica referencia `assetId`, vista, punto de inserción, giro y escala. El activo registra fabricante, modelo/variante, unidad nativa, dimensiones de referencia, fuente, revisión, huella del archivo original y formato convertido. El proyecto guarda instancias y ubicaciones, sin alterar el archivo fuente.

## Catálogos locales y estado de verificación

Primera carga útil: productos identificados en el PDF de ejemplo (ABB S804N-C32, XT1C 160, XT2N 160, S251 Na C10, S201M-C10 y seccionador OT400E04). Cada geometría física se incorpora desde dibujo/catálogo oficial ABB o ficha verificable, guardando URL, documento, página, fecha de consulta y revisión.

Flujo de adquisición de bloques: buscar primero el número de producto y variante en ABB Library/ABB CAD Download Center; descargar DWG/DXF o STEP si está disponible; comprobar vista, escala, configuración y revisión; preparar una versión interna normalizada conservando intacto el original, su procedencia y condiciones de uso. Para un equipo sin CAD descargable, usar dimensiones oficiales para construir un bloque paramétrico claramente identificado como reconstruido, hasta verificarlo con un dibujo mecánico.

Fuentes encontradas para iniciar: ABB CAD Download Center/PartCommunity contiene modelos configurables 2D/3D de Tmax XT; la ficha de ABB del OT400E04 publica dibujos mecánicos DWG/DXF y modelo 3D; ABB publica ficha y dibujo dimensional de S804N-C32, aunque hay que confirmar si existe CAD editable para esa referencia exacta. Fabricantes argentinos como Fayser, GENROD, TIPEM, 5M y TecnoBox publican líneas y dimensiones de gabinetes; se cargan bloques descargables o geometría basada en ficha verificable, nunca medidas supuestas.

Para gabinetes, el catálogo debe permitir filtrar familias modulares DIN, gabinetes estancos de chapa y armarios autoportantes. Las medidas comerciales se cargan por fabricante y línea, con ancho, alto y profundidad en mm. Las familias preliminares a investigar incluyen medidas publicadas en Argentina como 400x600x200, 600x800x250 y armarios desde 1800 mm; son referencias de mercado, no una recomendación automática para este tablero.

Una selección se calcula según ocupación, espacios de cableado, barras, borneras, ventilación y reserva configurable. El usuario puede elegir otra medida del catálogo o definir una envolvente propia.

## Importación PDF y flujo de revisión

1. Leer texto y coordenadas vectoriales del PDF; no rasterizar salvo que sea necesario.
2. Agrupar rótulos, símbolos y circuitos mediante posiciones y patrones configurables.
3. Mostrar tabla de dispositivos extraídos con tag, modelo, datos eléctricos, página y confianza.
4. Permitir corregir, agregar o quitar dispositivos antes de ubicar físicamente.
5. Resolver productos contra el catálogo. No coincidencias pasan a revisión del usuario.
6. Generar una propuesta física editable y exponer advertencias de datos faltantes o dimensión no verificada.

El PDF de muestra tiene texto extraíble y una hoja A1; sus metadatos indican que fue creado/imprimido desde AutoCAD 2027. El primer importador debe soportar este PDF y probarse también con un PDF exportado directamente desde DOC, ya que el orden de texto extraído del ejemplo intercaló algunos datos por columnas.

## Reglas para mantener el proyecto fácil de cambiar

- Todo adaptador externo implementa una interfaz pequeña y se puede reemplazar sin tocar el modelo central.
- Toda regla de distribución tiene identificador, parámetros y explicación visible.
- Las fuentes de catálogo se guardan junto al dato, no sólo en documentación aparte.
- Los ejemplos de proyecto y catálogos forman parte del repositorio.
- `docs/AGREGAR_FABRICANTE.md` describirá cómo añadir una familia sin cambiar código de editor.
- Las decisiones que afecten al formato del proyecto se registran en notas ADR (`docs/decisions/`).
- Los activos CAD quedan fuera de la interfaz y llevan un manifiesto de procedencia.
- Un validador avisa si la variante del bloque no coincide con la ficha del dispositivo o sus dimensiones.

## Etapas de construcción

1. Validar la extracción del PDF en una tabla editable y fijar el esquema del proyecto.
2. Crear la vista frontal 2D y el editor vectorial con gabinete, rieles, canaletas, barras y dispositivos movibles/borrables.
3. Cargar bloques CAD verificables para los productos del ejemplo y gabinetes comerciales argentinos seleccionados.
4. Crear distribución inicial con reglas visibles y ajuste manual.
5. Exportar DXF por capas, PNG y PDF; verificar unidades y abrir el DXF en AutoCAD.
6. Ampliar reconocimiento y catálogos con más unifilares reales.

## Criterio de aceptación del primer caso

El caso TS4 se importa sin perder identificadores; los elementos sin coincidencia se señalan; el usuario puede modificar y borrar; el tablero conserva sus medidas al exportar; DXF contiene entidades editables y capas separadas; la ficha de cada medida muestra fuente y estado verificado/estimado.
