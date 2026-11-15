# ESTADO — Topográficos de tableros ABB
> Foto actual del proyecto. Se reescribe (no se acumula). El historial va en BITACORA.md.
> Actualizado: 2026-11-15 19:00 · Claude

## Objetivo
PDF de unifilar de ABB e-Design DOC → topográfico (vista frontal 2D) del tablero con dispositivos y envolvente ABB reales → editar en interfaz → exportar DXF (AutoCAD, 1:1 mm, bloques y capas), PNG, SVG, PDF.

## Reglas del usuario (no romper)
- Nada hardcodeado: lo específico va en `datos/*.json`; código en módulos con comentarios de ayuda.
- Medidas de equipos fijas (no editables). Rieles DIN definidos por la envolvente elegida.
- Solo ABB y solo lo que se vende en Argentina; si no está la variante exacta, la más común, y anotarlo.
- Bloques desde CAD oficial ABB, con colores y marcado idénticos al equipo real (medido en fotos frontales ABB). No inventar datos: cada dato con fuente y estado.
- **Normativa argentina (requisito del usuario)**: todo tablero debe cumplir lo vigente (AEA 90364, IEC 61439). Reglas en `datos/normativa_argentina.json` con fuente y estado (todas 'por-verificar' hasta confirmar con el texto oficial). Hecho: `normativa.py` (control, `python normativa.py [proyecto.json]`) y `datos/accesorios_abb.json` inicial. Los accesorios genéricos (peines, bornes y barras PE/N, tapas) pueden ser de cualquier marca con equivalente (decisión del usuario). Hecho también: `accesorios.py` propone bornes de tierra (uno por QF, en hueco libre del riel), cubrebornes y peines entre S200 contiguos; panel 'Normativa argentina' en el editor (botones Completar/Revisar); el DXF dibuja los accesorios (capa ABB_ACCESORIOS) y escribe los avisos en ABB_NOTAS. Falta: dibujo real (CAD) de peines y bornes, bloques de distribución en el layout (corrientes altas), peines S800, elegir versión PS3/12, confirmar Argentina, pantalla Normativa en la maqueta.
- **Nada monopolar**: mínimo bipolar (1P+N cuenta como 2 polos). `catalogo_abb.json -> scope.minPoles`.
- Diseño pensado de entrada para que los cambios futuros sean chicos. Usar modelos de IA livianos.

## Estructura
| Ruta | Qué es |
|---|---|
| `app.py` | servidor del editor (`iniciar_editor.bat` → http://127.0.0.1:8765) |
| `importador.py` | lee el PDF y propone equipos; reglas en `catalogo_abb.json`: `importRules`, `series` (modelo → carcasa, con polos y fuente), `modelHints` |
| `cad_export.py` | exporta DXF con bloques por familia |
| `web/index.html` | interfaz |
| `datos/` | catálogo ABB, colores (`apariencias_abb.json`), bloques 2D (`frentes_cad.json`), inventario CAD (`cad_argentina.json`), proyecto TS4 |
| `cad/abb/` | CAD originales ABB → `work/proyectar_cad.py` → `datos/frentes_cad.json` |
| `tests/` | `python -m unittest discover tests` · 6 unifilares reales en `tests/unifilares/` |
| `work/cobertura_catalogo.py` | genera `docs/cobertura_unifilares.md` (familias que faltan) |

## Situación
- Editor funcionando con el TS4: importa, edita, rieles por envolvente, zoom, DXF/PNG/SVG/PDF con colores. Un proyecto por tablero (`proyectos.py`), accesorios y normativa (`accesorios.py`, `normativa.py`), ubicación en riel (`colocar.py`).
- **Armado automático** (`layout_auto.py`, botón 'Armar tablero automático', ruta `/api/autolayout`): elige el gabinete más chico del catálogo donde entra el contenido y acomoda seccionadores, equipos de kit y equipos de riel. Criterios en `datos/reglas_layout.json` (**propuestas de diseño, no datos de ABB**). TS4 hoy cae en SR2 SRN12630K (1200×600×300) con riel GD4006.
- **Gabinetes en `datos/catalogo_abb.json -> enclosures`** (31): 8 de estructura System pro E power 185 (catálogo ABB 1STC803009D0103, `structure` con banda 50 mm, hojas de puerta, lista de partes con página) y 23 SR2 monobloc con puerta ciega (catálogo ABB 1STC804013D0201 de 2011; externo = nominal + 3 mm; placa interna = (ancho-40)×(alto-40); `railOptions` GD4006/6006/8006). Cada gabinete trae `functionalOffset` y `railOptions`. Colores RAL 7035 (gabinete) y RAL 7012 (zócalo, sólo System pro E); hex aproximados.
- Los PDF de catálogo están en el repo: `docs/catalogos_abb/` (más el texto por página en `texto/`), registrados en `datos/fuentes_descargadas.json`. **Regla del usuario: todo lo que se descargue o actualice se sube al repo y se anota en ese registro.**
- Modelo de datos: **carcasa** (geometría CAD, `deviceShells`) ≠ **serie** (qué modelos la usan, `series`) ≠ **marcado** (lo impreso en el frente: `apariencias_abb.json -> marking`). Carcasas por polo (`poleModule`, S200): 2P-4P = polos repetidos.
- **Cubre 167 de 206 equipos** de los 6 unifilares. Faltan: S293, SN201L, XT3S, S251 (asignada por hipótesis a S201 NA), OT varios, T2S/T4S, E2.2N, S803S (ver `docs/cobertura_unifilares.md`).
- Series sin confirmar con fuente (`verified: false`): XT1 y XT2 para todas las versiones de poder de corte.
- Pruebas: 48, `python -m unittest discover tests`. Correrlas antes de cada push.

## Pendiente (anotarse con [Claude] / [Codex] antes de empezar)
0. **[Claude, en curso] Posición de los rieles DIN según el gabinete** (regla del usuario: la fija el gabinete). Hoy el riel se centra y se pega debajo de los equipos (propuesta mía). Datos reales leídos del catálogo SR2 (págs. 2/4 y 2/8, imagen verificada): con el kit KD las filas de riel son de 185 mm de alto, y hay 2 filas (KD5040K, 500×400), 3 (KD6040K, 600×400), 4 (KD8060K, 800×600, 25 módulos por fila), 5 (KD1060K, 1000×600, 25 mód.; KD1080K, 1000×800, 36 mód.), 6 (KD1260K, 1200×600, 25 mód.; KD1280K, 1200×800, 36 mód.); filas de 14 módulos para 400 mm de ancho. Paneles PM1414K/PM1625K/PM1836K (185×400/600/800). Plan: cargar `kdKit` por gabinete (kit, filas, módulos por fila, alto de fila 185, página) y que `layout_auto.py` ponga los modulares en esas filas y los XT/OT en la placa. **Sin dato del catálogo** (marcar como supuesto): ancho de los soportes laterales KD, desde qué altura arrancan las filas y a qué altura va el riel dentro de la fila de 185 mm. Hay un dibujo en la pág. 2/4 (filas 1, 2, 3 desde arriba), pero no cota la distancia al borde.
1. Marcado hecho para S200 (2P-4P, 1P+N) y S800. Falta medir foto frontal de XT1, XT2 y OT400 (sin `marking` no se imprime nada).
2. Robustez/funcionalidad (prioridad del usuario): falta duplicar y borrar proyectos; elegir gabinete al crear proyecto; ubicación automática ya cubre riel y kit, pero los kits de montaje XT/OT no tienen CAD ni medidas.
3. **Profundidades reales** de XT, OT400, S800 para validar el gabinete (hoy la regla `minDepthForKitDevicesMm: 200` es criterio propio).
4. **Gabinetes que faltan cargar**: SR2 con puerta vidriada (VK), zócalos ZA...., IS2 (de piso, pág. 4/ del catálogo), AM2. Verificar disponibilidad en Argentina de los SR2 (no verificada).
5. **Estructura System pro E**: montantes de 2200: PUPM2100 (págs. 20 y 23) o PUPM2001 (pág. 24), conflicto sin resolver; no hay CAD de montantes, bisagras ni manijas (PHLS0013 sin posición); STEP de la estructura (ABB publica kits 1STD...); kits de montaje XT están en el catálogo de tableros modulares, no en estos dos.
6. Peines: no hay peine definido para S804 (aviso 'QF81 y QF85 sin peine'); CAD de accesorios (PE, peines, bloques de distribución).
7. Normativa: las reglas siguen 'por-verificar'; hace falta el texto oficial AEA 90364 / IEC 61439.
8. Familias faltantes (no prioritario; OT quedan así por ahora): primero ver si comparten carcasa con una existente. Manija y eje del OT400E04P. QF89 S251: confirmar con ABB Argentina que S251 Na = S201 NA.
9. Sacar textos fijos del TS4 en `generar_topografico.py` (notas de la lámina). Validar con ABB Argentina gabinete, rieles y kits; cerrar BOM.

## Diseño de la interfaz (aprobado provisoriamente por el usuario; se ajustará con el uso)
- Maqueta de 4 pantallas (Tableros, Importar, Editor, Exportar) en un lienzo de diseño de claude.ai: https://claude.ai/artifact/GJvAU9SANz5x9u69j9mra2 (la ve solo el usuario). No es código: el editor real (`web/index.html`) todavía no la sigue.
- Orden previsto: 1) [hecho] un proyecto por tablero + lista de proyectos, 2) [descartado: la GENERAL es referencia], 3) [hecho] colocar equipos automáticamente + elegir gabinete, 4) rieles según kit del gabinete (pendiente 0), 5) llevar la maqueta al editor real.
