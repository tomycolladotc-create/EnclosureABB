# Instrucciones para agentes (Codex, Claude, etc.)

**Al empezar** (para ponerse al día gastando poco):
1. `git pull`
2. Leer `ESTADO.md` (foto actual) y **solo las 3 primeras entradas** de `BITACORA.md`. No leer más archivos hasta saber qué tarea vas a tomar.
3. Anotarte en un pendiente de ESTADO.md (`[Codex]` / `[Claude]`), commit + push **antes** de trabajar, así el otro no la toma.

**Mientras trabajás**
- Respetar las "Reglas del usuario" de ESTADO.md. Lo específico va en `datos/*.json`, no en el código.
- No tocar archivos que el otro agente tenga anotados.
- Antes de subir: `python -m unittest discover tests` tiene que pasar.

**Al terminar**
1. Agregar una entrada **arriba** en `BITACORA.md` (máx. 6 líneas: Hecho / Archivos / Ojo / Siguiente).
2. Reescribir `ESTADO.md` si cambió la foto (no acumular historial ahí).
3. Commit con mensaje claro + push.

No subir: salidas generadas (`salida/`), ZIPs, capturas de prueba. Los CAD de ABB sí van, en `cad/abb/<familia>/`, registrados en `datos/cad_argentina.json`.
Idioma: español.
