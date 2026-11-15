# ESTADO DEL PROYECTO — Topográficos de tableros ABB

> Archivo compartido entre Codex/ChatGPT y Claude. Leerlo al empezar cada sesión y actualizarlo al terminar.
> Última actualización: 2026-11-15 17:20 (Claude).

## Objetivo
Programa que toma un **unifilar en PDF exportado desde ABB e-Design DOC** y genera el **topográfico del tablero** (vista frontal 2D) con los dispositivos reales. Debe tener:
- Interfaz fácil para revisar, mover, agregar y borrar equipos.
- Exportación a **DXF (AutoCAD, a escala 1:1 en mm, por capas y con bloques)**, PNG, SVG y PDF.
- Proyecto guardable y reabrible.

## Reglas del usuario (no romper)
- **Nada hardcodeado.** Código segmentado en módulos, con catálogos en datos (JSON), comentarios/guías para encontrar cosas rápido.
- **Diseño bien pensado desde el inicio**, para que los cambios futuros sean menores.
- **Dimensiones de los equipos fijas**: el usuario no puede cambiar ancho/alto.
- **Rieles DIN definidos por la envolvente elegida**, no ubicables libremente. Cambiar el gabinete cambia la disposición de rieles y reubica los modulares.
- **Envolventes de la línea ABB** (no genéricas).
- **Solo equipos que se vendan en Argentina.** Si no hay la variante exacta, usar la más común disponible y dejarlo registrado.
- **Bloques reales**: geometría de CAD oficial ABB, y con **colores reales** (no solo líneas grises).
- No inventar datos: cada dato lleva su fuente y un estado (verificado / estimado / pendiente).
- Usar el modelo de IA más liviano que alcance (el usuario cuida el límite).

## Arquitectura
Módulos separados: importación de PDF → modelo del proyecto → catálogos (equipos, envolventes, paletas de color) → reglas de distribución → editor → exportadores.
Unidades internas en mm. Cada equipo y gabinete guarda la procedencia de su geometría.

## Estructura del repo
- `app.py` servidor local del editor (`iniciar_editor.bat` → http://127.0.0.1:8765) · `cad_export.py` exportación DXF · `generar_topografico.py` generador por línea de comandos
- `datos/` catálogos y proyecto en JSON (catálogo ABB, apariencias/colores, frentes 2D ya proyectados, inventario CAD Argentina, proyecto TS4)
- `web/index.html` interfaz del editor
- `work/` scripts auxiliares (proyectar STEP a frente 2D, empaquetar, manifest)
- `docs/` arquitectura, catálogo inicial y estado de la búsqueda de CAD
- **No están en el repo** (por peso): `cad/abb/` con los STEP/DWG/DXF originales de ABB, `referencias/`, `salida/`. Quedan en la compu de Thomas; su fuente y SHA-256 están en `datos/cad_argentina.json`. Solo hacen falta para regenerar `datos/frentes_cad.json`.

## Dónde está todo (compu de Thomas)
- **App principal:** `C:\Users\Thomas\Documents\ChatGPT\Topograficos Tableros\`
  - `iniciar_editor.bat` → editor local en http://127.0.0.1:8765
  - `datos/catalogo_abb.json` → catálogo ABB separado del código
  - `generar_topografico.py`, `README.md`, `salida/`
- **Carpeta de trabajo de Codex:** `C:\Users\Thomas\Documents\Codex\2026-11-15\qui\`
  - `work/ARQUITECTURA.md`, `work/catalogo_abb_inicial.json`
  - `outputs/` → vistas TS4 (PNG/SVG/PDF/DXF), `ABB_CAD_TS4_Argentina.zip` (12 CAD), `inventario_CAD_ABB_Argentina_TS4.json`, `estado_busqueda_CAD_TS4.md`, `Editor_ABB_TS4_vista_2D.zip`
- **Unifilar de referencia:** `BAF-E-EL-PL-104-0 Unifilares-15 TS4-PORT 11-12-13-14.pdf` (BA Ferial, Pabellón 6)

## Caso de referencia: tablero TS4-PORT 11-12-13-14
| Ref | Equipo | Estado |
|---|---|---|
| QS1 | Seccionador OT400E04 → se usa **OT400E04P** (1SCA022719R1810, 400 A 4P, con manija y eje; a la venta en AR) | CAD de familia OT400 ok; manija/eje sin cotejar |
| QF81–QF88 aprox. | **XT1C 160 TMD 80-800 4P** (6 unidades, carcasa compartida) | CAD ok, oferta AR ok |
| — | **XT2N TMG 80-240 4P** | CAD ok; oferta AR exacta sin confirmar |
| — | **S804N-C32 4P** | CAD ok, oferta AR ok |
| QF90 | **S201M-C10 NA, 1P+N**, 35 mm / 2 módulos | CAD ok (DWG+STEP) |
| QF89 | **S251 Na C10, 1P+N, 6 kA** (modelo ABB histórico) | **Sin CAD**, sin oferta AR |
| QF7 | Alimentador externo (no va en el tablero) | — |

**Envolvente:** ABB System pro E power, barras 185 mm. Funcional 1000×2100×500 mm, exterior 1100×2200×600 mm, zócalo 100 mm. Kits fijos 200 mm: 6× PHDX1401 (XT1) y 1× PHDX2401 (XT2). Riel DIN: kit PDRS0600 (600 mm). Fuente: catálogo ABB SPEP 185 2024 Rev 3.

## Hecho
- Arquitectura y catálogo inicial (6 familias, 11 instancias).
- Importador de PDF: detecta QS1, los 11 QF y QF7 desde el texto del PDF.
- Editor local: cargar PDF, revisar equipos, elegir envolvente, mover/agregar/borrar, deshacer, guardar, zoom/desplazamiento, selección.
- Rieles DIN según perfil de envolvente (dos envolventes cargadas).
- 12 CAD ABB descargados y verificados (SHA-256).
- Frentes 2D proyectados desde STEP (XT1, XT2, QF90) y DXF (S800); OT400 desde dibujo de familia.
- DXF exportado con bloques por familia (5 bloques, 11 inserciones), auditado sin errores.

- Colores por familia en la vista 2D (paleta en `datos/apariencias_abb.json`, basada en fotos ABB) y en el DXF (capa `ABB_CAD_COLORES`, true color).
- [Claude] Corregido bug del DXF: los rellenos de color salían como triángulos cruzados por el orden de vértices de SOLID. Verificado renderizando el DXF del TS4.

## Pendiente (en orden)
1. Inscripciones exactas en los frentes.
2. Manija y eje del OT400E04P.
3. CAD para QF89 (S251), o reemplazo por equivalente actual vendido en AR.
4. Validar con ABB Argentina la configuración del gabinete y la posición de rieles/kits; confirmar venta local de la envolvente y del XT2 exacto.
5. Coordinar kits con la celda de barras y cerrar la lista de materiales (BOM).
6. Probar con otros unifilares de DOC (que funcione en general y no solo con el TS4).

## Cómo trabajamos en paralelo
- **Codex/ChatGPT** y **Claude** trabajan sobre este repo. Antes de empezar: `git pull` y leer este archivo.
- Tomar una tarea de "Pendiente", anotarse al lado (`[Claude]` / `[Codex]`) y hacer commit de eso antes de arrancar.
- Al terminar: actualizar "Hecho" y "Pendiente", commit y push.
- No trabajar los dos sobre el mismo archivo a la vez.
