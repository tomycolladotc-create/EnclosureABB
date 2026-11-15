# Instrucciones para agentes (Codex, Claude, etc.)

1. Antes de empezar: `git pull` y leer **ESTADO.md** completo.
2. Tomar una tarea de "Pendiente" en ESTADO.md, anotar `[Codex]` o `[Claude]` al lado y hacer commit+push de ese cambio ANTES de trabajar (así el otro agente no la toma).
3. Respetar las "Reglas del usuario" de ESTADO.md (nada hardcodeado, catálogos en JSON, medidas de equipos fijas, solo equipos ABB vendidos en Argentina, no inventar datos).
4. Al terminar: actualizar "Hecho" / "Pendiente" en ESTADO.md, commit con mensaje claro y push.
5. No subir archivos generados ni pesados (ver .gitignore): salidas PNG/PDF/DXF de prueba, ZIPs. Los CAD de ABB van en `cad/` solo si pesan poco; si no, se registran en el inventario con su fuente.
6. Comunicarse en español.
