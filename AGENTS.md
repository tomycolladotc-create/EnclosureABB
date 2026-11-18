# Instrucciones para agentes (Codex, Claude, etc.)

**Al empezar** (para ponerse al día gastando poco):
1. `git pull`
2. Leer `ESTADO.md` (foto actual) y **solo las 3 primeras entradas** de `BITACORA.md`. No leer más archivos hasta saber qué tarea vas a tomar.
3. Anotarte en un pendiente de ESTADO.md (`[Codex]` / `[Claude]`), commit + push **antes** de trabajar, así el otro no la toma.

**Mientras trabajás**
- Respetar las "Reglas del usuario" de ESTADO.md. Lo específico va en `datos/*.json`, no en el código.
- No tocar archivos que el otro agente tenga anotados.
- Resolver de forma autónoma las decisiones técnicas ordinarias. Consultar al usuario solo cuando falte un dato no inferible o una decisión cambie materialmente el resultado.
- Toda mejora funcional, dato, fuente o corrección debe quedar en un commit y subirse al repositorio durante la misma sesión. El repo es la fuente única de verdad.
- Antes de subir: `python -m unittest discover tests` tiene que pasar, y también la prueba de interfaz `python tests/e2e/prueba_interfaz.py`.
- **Probar como usuario final, siempre** (pedido de Thomas, 2026-11-18): en cada sesión usar el programa como lo usaría un tablerista (importar un unifilar, revisar el tablero armado, corregir a mano, exportar DXF/PDF y la lista de materiales) y mirar las capturas. Cada error encontrado se arregla o se anota; cada mejora o agregado posible va a `docs/MEJORAS.md`. Objetivo: un producto fácil de usar, útil, confiable y que sirva de verdad.

**Al terminar**
1. Agregar una entrada **arriba de todo** en `BITACORA.md` (la más nueva primero; nunca al final) (máx. 6 líneas: Hecho / Archivos / Ojo / Siguiente).
2. Reescribir `ESTADO.md` si cambió la foto (no acumular historial ahí).
3. Commit con mensaje claro + push.

Después de un cambio grande, actualizar `ESTADO.md` y `BITACORA.md` inmediatamente. Si la sesión está por terminar o el límite está cerca, actualizar ambos archivos y subir el trabajo parcial antes de continuar en otra sesión.

No subir: salidas generadas (`salida/`), ZIPs, capturas de prueba. Los CAD de ABB sí van, en `cad/abb/<familia>/`, registrados en `datos/cad_argentina.json`.
Idioma: español.
- Todo archivo descargado (catálogos, CAD, hojas de datos) se guarda en el repo y se registra en `datos/fuentes_descargadas.json` (origen, fecha, hash, uso). Pedido del usuario 2026-11-15.
