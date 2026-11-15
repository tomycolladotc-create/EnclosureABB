# BITÁCORA
> Una entrada por sesión, **la más nueva arriba**, máximo 6 líneas. Al empezar, leer solo las 3 primeras.
> Si pasa de 15 entradas, mover las viejas a `docs/bitacora_vieja.md`.
> Formato: `## fecha hora · agente` + Hecho / Archivos / Ojo / Siguiente.

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
