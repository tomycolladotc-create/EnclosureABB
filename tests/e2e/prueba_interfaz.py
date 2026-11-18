"""Prueba de punta a punta de la interfaz con un navegador real (Playwright + Chrome).

Uso:  python tests/e2e/prueba_interfaz.py [URL]   (por defecto levanta app.py en un puerto libre)
Recorre todos los botones visibles; imprime PASS/FAIL y termina con código 1 si algo falla.
No toca datos/ts4_topografia.json: trabaja sobre copias en datos/proyectos/ que borra al final.
"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
PDFS = sorted((ROOT / "tests" / "unifilares").glob("*.pdf"))
CHROME = next((c for c in ("/usr/bin/google-chrome", "/usr/bin/chromium") if Path(c).exists()), None)
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""), flush=True)


def chip(pg):
    return pg.inner_text("#normaChip")


def chip_ok(pg):
    return "error" not in chip(pg)


def wait_idle(pg, ms=2500):
    pg.wait_for_timeout(ms)


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else None
    server = None
    ts4 = ROOT / "datos" / "ts4_topografia.json"
    ts4_backup = ts4.read_bytes()
    proj_dir = ROOT / "datos" / "proyectos"
    before = set(proj_dir.glob("*.json")) if proj_dir.exists() else set()
    if not url:
        port = "8797"
        env = {**os.environ, "ABB_EDITOR_PORT": port}
        server = subprocess.Popen([sys.executable, str(ROOT / "app.py")], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        time.sleep(2)
        url = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"]) if CHROME else p.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
            pg = ctx.new_page()
            errors = []
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.on("dialog", lambda d: d.accept("Copia prueba") if d.type == "prompt" else d.accept())

            # 1) Abrir el TS4 guardado: debe quedar dentro de normativa sin tocar nada.
            pg.goto(url + "/?id=ts4#editor")
            wait_idle(pg, 5000)
            check("abrir TS4: sin errores de normativa", chip_ok(pg), chip(pg))
            check("abrir TS4: lista de circuitos", pg.locator("#deviceList .item").count() >= 10)
            check("abrir TS4: sin botones viejos", pg.locator("#normaComplete, #normaCheck, #apply, #save").count() == 0)
            wait_idle(pg, 3000); pg.reload(); wait_idle(pg, 5000)
            check("reabrir TS4: no se vuelve a rearmar", "rearmado" not in pg.inner_text("#message"), pg.inner_text("#message")[:60])
            check("reabrir TS4: sin errores", chip_ok(pg) and pg.evaluate("validationResult.errors") == 0, chip(pg))

            # 2) Zoom.
            vb = pg.get_attribute("#board", "viewBox")
            pg.click("#zoomIn")
            check("zoom +", pg.get_attribute("#board", "viewBox") != vb)
            pg.click("#zoomOut"); pg.click("#focus"); pg.click("#fit")
            check("zoom: ver todo", pg.get_attribute("#board", "viewBox") is not None)

            # 3) Seleccionar y renombrar circuito.
            pg.click("#deviceList .item >> nth=0")
            check("seleccionar: tarjeta visible", pg.is_visible("#editor"))
            pg.fill("#circuit", "PRUEBA-1"); pg.press("#circuit", "Tab"); wait_idle(pg, 600)
            check("renombrar circuito", "PRUEBA-1" in pg.inner_text("#deviceList"))

            # 4) Deshacer / rehacer.
            pg.click("#undo"); wait_idle(pg, 400)
            check("deshacer", "PRUEBA-1" not in pg.inner_text("#deviceList"))
            pg.click("#redo"); wait_idle(pg, 400)
            check("rehacer", "PRUEBA-1" in pg.inner_text("#deviceList"))
            pg.keyboard.press("Control+z"); wait_idle(pg, 400)
            check("Ctrl+Z", "PRUEBA-1" not in pg.inner_text("#deviceList"))

            # 5) Arrastrar un equipo.
            q = pg.evaluate("project.devices.findIndex(d=>d.tag==='QS1')")  # QS1 está solo en su fila: hay lugar a los costados
            box = pg.locator(f"#board .device[data-index='{q}']").bounding_box()
            x0 = pg.evaluate(f"project.devices[{q}].x")
            pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            pg.mouse.down(); pg.mouse.move(box["x"] + box["width"] / 2 + 25, box["y"] + box["height"] / 2, steps=6); pg.mouse.up()
            wait_idle(pg, 1500)
            check("arrastrar equipo a lugar libre", pg.evaluate(f"project.devices[{q}].x") != x0)
            pg.keyboard.press("Control+z"); wait_idle(pg, 1500)
            # Soltarlo encima de otro: vuelve a su lugar y avisa.
            a, b = pg.evaluate("[0,1].map(k=>project.devices.filter(d=>d.tag.startsWith('QF')&&!isDin(d))[k].tag)")
            ia, ib = (pg.evaluate(f"project.devices.findIndex(d=>d.tag==='{t}')") for t in (a, b))
            ba, bb = (pg.locator(f"#board .device[data-index='{k}']").bounding_box() for k in (ia, ib))
            xa = pg.evaluate(f"project.devices[{ia}].x")
            pg.mouse.move(ba["x"] + ba["width"] / 2, ba["y"] + ba["height"] / 2)
            pg.mouse.down(); pg.mouse.move(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, steps=8); pg.mouse.up()
            wait_idle(pg, 800)
            check("soltar encima de otro: vuelve y avisa", pg.evaluate(f"project.devices[{ia}].x") == xa and "No hay lugar" in pg.inner_text("#message"))
            pg.keyboard.press("Control+z"); wait_idle(pg, 1500)
            # Equipo DIN (riel inferior): al soltarlo debe quedar en su riel, no saltar al primero.
            i = pg.evaluate("project.devices.findIndex(d=>isDin(d))")
            y0 = pg.evaluate(f"project.devices[{i}].y")
            box = pg.locator(f"#board .device[data-index='{i}']").bounding_box()
            pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            pg.mouse.down(); pg.mouse.move(box["x"] + box["width"] / 2 + 40, box["y"] + box["height"] / 2 + 3, steps=6); pg.mouse.up()
            wait_idle(pg, 2000)
            check("arrastrar DIN: queda en su riel", abs(pg.evaluate(f"project.devices[{i}].y") - y0) < 1, f"{y0} -> {pg.evaluate(f'project.devices[{i}].y')}")
            check("arrastrar DIN: sin errores geométricos", pg.evaluate("validationResult.errors") == 0, str(pg.evaluate("validationResult.findings.map(f=>f.message)"))[:120])
            pg.keyboard.press("Control+z"); wait_idle(pg, 1500)

            # 6) Agregar equipo.
            n = pg.evaluate("project.devices.length")
            pg.click("#showAdd")
            check("agregar: abre ventana", pg.is_visible("#addPanel"))
            pg.fill("#newCircuit", "NUEVO-1"); pg.click("#add"); wait_idle(pg, 4000)
            check("agregar: equipo sumado", pg.evaluate("project.devices.length") == n + 1)
            check("agregar: aparece en la lista", "NUEVO-1" in pg.inner_text("#deviceList"))
            check("agregar: sigue dentro de normativa", chip_ok(pg), chip(pg))
            pg.click("#showAdd"); pg.click("#addCancel")
            check("agregar: cancelar cierra", not pg.is_visible("#addPanel"))

            # 6b) Fluidez: valores propuestos, duplicar, Escape, clic en vacío, Supr, reordenar en el riel, tooltip.
            pg.click("#showAdd")
            check("agregar: propone el equipo más usado", pg.input_value("#shell") == pg.evaluate("usualShell()"))
            check("agregar: propone el siguiente circuito", pg.input_value("#newCircuit") == pg.evaluate("nextCircuit()") != "", pg.input_value("#newCircuit"))
            pg.click("#addCancel")
            pg.click("#deviceList .item >> nth=0"); k = pg.evaluate("project.devices.length")
            pg.click("#duplicate"); wait_idle(pg, 4000)
            check("duplicar equipo", pg.evaluate("project.devices.length") == k + 1 and pg.is_visible("#editor"))
            dup = pg.evaluate("project.devices[selected].tag")
            check("tooltip en el equipo", pg.evaluate("!!document.querySelector('#board .device title')"))
            pg.evaluate("document.activeElement.blur()"); pg.keyboard.press("Delete"); wait_idle(pg, 1500)
            check("Supr borra el equipo", pg.evaluate("project.devices.length") == k and not pg.evaluate(f"project.devices.some(d=>d.tag==='{dup}')"))
            pg.click("#deviceList .item >> nth=0"); pg.evaluate("document.activeElement.blur()"); pg.keyboard.press("Escape"); wait_idle(pg, 300)
            check("Escape quita la selección", pg.evaluate("selected===null") and not pg.is_visible("#editor"))
            pg.click("#deviceList .item >> nth=0"); bb = pg.locator("#board").bounding_box()
            pg.mouse.click(bb["x"] + 12, bb["y"] + bb["height"] - 12); wait_idle(pg, 300)
            check("clic en el vacío quita la selección", pg.evaluate("selected===null"))
            # reordenar: dos equipos DIN contiguos del mismo riel
            pair = pg.evaluate("""(()=>{const din=project.devices.filter(isDin);for(const a of din)for(const b of din)if(a!==b&&Math.abs(a.y-b.y)<1&&Math.abs(a.x+a.w-b.x)<1)return [a.tag,b.tag];return null})()""")
            if pair:
                ia, ib = (pg.evaluate(f"project.devices.findIndex(d=>d.tag==='{t}')") for t in pair)
                ba, bb2 = (pg.locator(f"#board .device[data-index='{i}']").bounding_box() for i in (ia, ib))
                pg.mouse.move(ba["x"] + ba["width"] / 2, ba["y"] + ba["height"] / 2); pg.mouse.down()
                pg.mouse.move(bb2["x"] + bb2["width"] * .8, bb2["y"] + bb2["height"] / 2, steps=8); pg.mouse.up(); wait_idle(pg, 1500)
                xa, xb = (pg.evaluate(f"project.devices.find(d=>d.tag==='{t}').x") for t in pair)
                check("reordenar en el riel (soltar sobre otro)", xa > xb and "movido" in pg.inner_text("#message"), f"{pair} {xa} {xb}")
                check("reordenar: sin superposiciones", pg.evaluate("validationResult.errors") == 0)
                pg.keyboard.press("Control+z"); wait_idle(pg, 1500)
            else:
                check("reordenar en el riel: hay dos DIN contiguos", False)

            # 7) Eliminar equipo.
            pg.click("#deviceList .item:has-text('NUEVO-1')"); pg.click("#remove"); wait_idle(pg, 1500)
            check("eliminar equipo", pg.evaluate("project.devices.length") == n)

            # 7a) Canaletas automáticas: verticales + horizontales; estirar desde un extremo (convierte a manual).
            check("canaletas automáticas: hay verticales", pg.evaluate("project.accessories.filter(a=>a.type==='wiring_duct'&&a.orientation==='v').length") >= 1)
            hi = pg.evaluate("project.accessories.findIndex(a=>a.type==='wiring_duct'&&a.orientation==='h'&&a.auto)")
            grip = pg.locator(f"#board .duct[data-auto='{hi}'] .grip[data-end='end']").bounding_box()
            w0 = pg.evaluate(f"project.accessories[{hi}].w"); x_start = pg.evaluate(f"project.accessories[{hi}].x")
            pg.mouse.move(grip["x"] + grip["width"] / 2, grip["y"] + grip["height"] / 2); pg.mouse.down()
            pg.mouse.move(grip["x"] - 60, grip["y"] + grip["height"] / 2, steps=6); pg.mouse.up(); wait_idle(pg, 800)
            d = pg.evaluate("(a=>a&&{w:a.w,x:a.x,manual:a.manual})(ductById(selDuct))")
            check("estirar canaleta desde el extremo derecho (acortar)", d and d["manual"] and d["w"] < w0 and d["x"] == x_start and d["w"] % 5 == 0, str(d))
            check("tocar una automática pasa todas a manual", pg.evaluate("project.ductMode") == "manual")
            id_ = pg.evaluate("selDuct"); grip = pg.locator(f"#board .duct[data-duct='{id_}'] .grip[data-end='start']").bounding_box()
            pg.mouse.move(grip["x"] + grip["width"] / 2, grip["y"] + grip["height"] / 2); pg.mouse.down()
            pg.mouse.move(grip["x"] + 40, grip["y"] + grip["height"] / 2, steps=6); pg.mouse.up(); wait_idle(pg, 800)
            d2 = pg.evaluate("(a=>({w:a.w,x:a.x}))(ductById(selDuct))")
            check("estirar desde el extremo izquierdo mueve el inicio", d2["x"] > d["x"] and abs((d2["x"] + d2["w"]) - (d["x"] + d["w"])) < 0.01, str(d2))
            vi = pg.evaluate("project.accessories.findIndex(a=>a.type==='wiring_duct'&&a.orientation==='v')")
            vid = pg.evaluate(f"project.accessories[{vi}].id"); grip = pg.locator(f"#board .duct[data-duct='{vid}'] .grip[data-end='end']").bounding_box()
            h0 = pg.evaluate(f"project.accessories[{vi}].h")
            pg.mouse.move(grip["x"] + grip["width"] / 2, grip["y"] + grip["height"] / 2); pg.mouse.down()
            pg.mouse.move(grip["x"] + grip["width"] / 2, grip["y"] + 80, steps=6); pg.mouse.up(); wait_idle(pg, 800)
            check("estirar canaleta vertical desde arriba", pg.evaluate(f"ductById('{vid}').h") < h0)
            pg.keyboard.press("Control+z"); pg.keyboard.press("Control+z"); pg.keyboard.press("Control+z"); pg.keyboard.press("Control+z"); wait_idle(pg, 1500)
            check("deshacer vuelve a canaletas automáticas", pg.evaluate("project.ductMode") != "manual", str(pg.evaluate("project.ductMode")))

            # 7b) Canaletas a mano.
            autos = pg.evaluate("project.accessories.filter(a=>a.type==='wiring_duct').length")
            pg.click("#showDuct")
            check("canaleta: abre ventana", pg.is_visible("#ductPanel"))
            pg.select_option("#newDuctOri", "v"); pg.fill("#newDuctLen", "600")
            sec = pg.evaluate("ducts.sections.findIndex(x=>x.widthMm===40&&x.heightMm===60)")
            pg.select_option("#newDuctSec", str(sec)); pg.click("#ductForm button[type=submit]"); wait_idle(pg, 1500)
            nd = pg.evaluate("project.accessories.filter(a=>a.type==='wiring_duct'&&a.manual).length")
            check("canaleta: automáticas pasan a editables", pg.evaluate("project.ductMode") == "manual" and nd == autos + 1, f"{autos}->{nd}")
            check("canaleta: vertical 40x600", pg.evaluate("(a=>[a.orientation,a.w,a.h])(ductById(selDuct))") == ["v", 40, 600])
            check("canaleta: tarjeta visible", pg.is_visible("#ductCard"))
            check("canaleta: no pisa equipos", pg.evaluate("!ductHits(ductById(selDuct))"))
            wait_idle(pg, 1500)
            check("canaleta: código ABB asignado", (pg.evaluate("ductById(selDuct).orderCode") or "").startswith("1SL9"), pg.evaluate("ductById(selDuct).orderCode"))
            x0 = pg.evaluate("ductById(selDuct).x")
            pg.evaluate("document.activeElement.blur()")
            pg.keyboard.press("ArrowRight"); wait_idle(pg, 300)
            check("canaleta: flecha mueve 5 mm", pg.evaluate("ductById(selDuct)?.x") == x0 + 5 or "No hay lugar" in pg.inner_text("#message"), str(pg.evaluate("ductById(selDuct)?.x")))
            pg.fill("#ductLen", "450"); pg.press("#ductLen", "Tab"); wait_idle(pg, 400)
            check("canaleta: cambiar largo", pg.evaluate("ductById(selDuct).h") == 450)
            pg.select_option("#ductSec", str(pg.evaluate("ducts.sections.findIndex(x=>x.widthMm===25&&x.heightMm===40)"))); wait_idle(pg, 400)
            check("canaleta: cambiar sección", pg.evaluate("(a=>[a.w,a.sectionMm,a.depthMm])(ductById(selDuct))") == [25, 25, 40])
            id_ = pg.evaluate("selDuct")
            box = pg.locator(f"#board .duct[data-duct='{id_}']").bounding_box()
            y0 = pg.evaluate("ductById(selDuct).y")
            pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            pg.mouse.down(); pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2 - 20, steps=5); pg.mouse.up(); wait_idle(pg, 500)
            moved = pg.evaluate("ductById(selDuct).y")
            check("canaleta: arrastrar", moved != y0 or "No hay lugar" in pg.inner_text("#message"), f"{y0}->{moved}")
            check("canaleta: posición en múltiplos de 5 mm", moved % 5 == 0)
            # soltarla sobre un equipo: vuelve
            dev = pg.locator("#board .device >> nth=0").bounding_box()
            box = pg.locator(f"#board .duct[data-duct='{id_}']").bounding_box()
            prev_pos = pg.evaluate("(a=>[a.x,a.y])(ductById(selDuct))")
            pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            pg.mouse.down(); pg.mouse.move(dev["x"] + dev["width"] / 2, dev["y"] + dev["height"] / 2, steps=8); pg.mouse.up(); wait_idle(pg, 500)
            check("canaleta: sobre un equipo vuelve a su lugar", pg.evaluate("(a=>[a.x,a.y])(ductById(selDuct))") == prev_pos)
            pg.click("#ductRotate"); wait_idle(pg, 400)
            rot = pg.evaluate("(a=>[a.orientation,a.w,a.h])(ductById(selDuct))")
            check("canaleta: girar", rot == ["h", 450, 25] or "No entra" in pg.inner_text("#message"), str(rot))
            wait_idle(pg, 1500)
            check("canaleta: dentro de normativa", chip_ok(pg), chip(pg))
            pg.click("#ductRemove"); wait_idle(pg, 500)
            check("canaleta: eliminar", pg.evaluate("project.accessories.filter(a=>a.type==='wiring_duct'&&a.manual).length") == autos)
            pg.click("#moreBtn")
            check("menú: volver a automáticas visible", pg.is_visible("#autoDucts"))
            pg.click("#autoDucts"); wait_idle(pg, 2000)
            check("volver a canaletas automáticas", pg.evaluate("project.ductMode") == "auto" and pg.evaluate("project.accessories.filter(a=>a.type==='wiring_duct'&&a.auto).length") == autos)

            # 8) Chip y menú.
            pg.click("#normaChip")
            check("chip: muestra detalle", pg.is_visible("#normaPanel") and len(pg.inner_text("#normaPanel")) > 5)
            pg.click("#board", position={"x": 10, "y": 10})
            check("chip: se cierra al hacer clic afuera", not pg.is_visible("#normaPanel"))
            pg.click("#moreBtn")
            check("menú ⋯ abre", pg.is_visible("#moreMenu"))
            pg.click("#autoFree"); wait_idle(pg, 4000)
            check("rearmar con riel libre", chip_ok(pg), chip(pg))
            pg.click("#moreBtn"); pg.click("#autoLayout"); wait_idle(pg, 4000)
            check("rearmar", chip_ok(pg), chip(pg))
            pg.click("#moreBtn")
            with pg.expect_download() as dl:
                pg.click("#exportJson")
            check("guardar copia JSON", Path(dl.value.path()).stat().st_size > 1000)
            check("menú se cierra al elegir una opción", not pg.is_visible("#moreMenu"))
            pg.click("#moreBtn")
            options = pg.eval_on_selector_all("#enclosure option", "o=>o.map(x=>x.value)")
            prev = pg.evaluate("project.enclosure.id")
            small = pg.evaluate("[...catalog.enclosures].sort((a,b)=>a.externalBody.width*a.externalBody.height-b.externalBody.width*b.externalBody.height)[0].id")
            pg.select_option("#enclosure", small); wait_idle(pg, 3000)
            check("gabinete chico donde no entra: se mantiene el anterior", pg.evaluate("project.enclosure.id") == prev and pg.input_value("#enclosure") == prev)
            big = pg.evaluate("[...catalog.enclosures].sort((a,b)=>b.externalBody.width*b.externalBody.height-a.externalBody.width*a.externalBody.height)[0].id")
            pg.click("#moreBtn"); pg.select_option("#enclosure", big); wait_idle(pg, 4000)
            check("cambiar a gabinete grande", pg.evaluate("project.enclosure.id") == big)
            check("cambiar gabinete: dentro de normativa", chip_ok(pg) and pg.evaluate("validationResult.errors") == 0, chip(pg))
            pg.click("#moreBtn"); pg.click("#autoLayout"); wait_idle(pg, 4000)

            # 8b) Vista con la puerta cerrada.
            pg.click("#viewDoor"); wait_idle(pg, 600)
            board = pg.inner_html("#board")
            check("puerta cerrada: placa con el nombre", pg.evaluate("project.project").upper()[:8] in board.upper())
            check("puerta cerrada: cartel de riesgo eléctrico", "RIESGO ELÉCTRICO" in board)
            n_lights = pg.evaluate("(project.signals?.pilotLights||[]).length")
            check("puerta cerrada: un orificio por piloto del unifilar", board.count('fill="url(#gLens)"') == n_lights, f"{n_lights} pilotos")
            box = pg.locator(".viewtoggle").first.bounding_box(); cbox = pg.locator(".canvas").bounding_box()
            check("selector de vista arriba a la izquierda (no lo tapa la tarjeta del equipo)", box["x"] < cbox["x"] + 40 and box["y"] < cbox["y"] + 40)
            pg.click("#viewInt"); wait_idle(pg, 600)
            pg.click("#deviceList .item >> nth=0"); wait_idle(pg, 400)
            known = pg.evaluate("!!knownCode(project.devices[selected])")
            ph = pg.get_attribute("#orderCode", "placeholder")
            check("tarjeta: muestra el código que va a la lista (o que falta)", ("verificado" in ph) if known else ("falta" in ph), ph)
            pg.keyboard.press("Escape")
            check("volver a la vista interior", pg.locator("#board .device").count() == pg.evaluate("project.devices.length"))

            # 9) Exportar.
            pg.click("[data-go=export]"); wait_idle(pg, 1500)
            check("exportar: pantalla", pg.is_visible("#screen-export"))
            for btn, size in (("#exportDxf", 5000), ("#exportSvg", 5000), ("#exportPng", 5000)):
                with pg.expect_download() as dl:
                    pg.click(btn)
                check(f"exportar {btn[7:]}", Path(dl.value.path()).stat().st_size > size)
            pg.click("#expDoor")
            with pg.expect_download() as dl:
                pg.click("#exportSvg")
            door_svg = Path(dl.value.path()).read_text(encoding="utf-8")
            check("exportar SVG de la puerta cerrada", "RIESGO" in door_svg and dl.value.suggested_filename.endswith("_puerta.svg"), dl.value.suggested_filename)
            check("exportar puerta: vuelve a la vista interior", not pg.evaluate("doorView"))
            pg.click("#expInt")
            with pg.expect_download() as dl:
                pg.click("#exportDxf")
            dxf = Path(dl.value.path()).read_text(encoding="utf-8", errors="ignore")
            check("DXF con la vista de puerta cerrada", "ABB_PUERTA_CERRADA" in dxf and "RIESGO ELECTRICO" in dxf)
            pg.click("summary:has-text('Lista de materiales')")
            check("lista de materiales", pg.locator("#bomTable tr").count() > 3)
            codes = pg.eval_on_selector_all("#bomTable tr td:nth-child(2)", "els=>els.map(e=>e.textContent.trim())")
            check("lista: sin códigos dobles ni ids internos", all("+" not in c and "_" not in c for c in codes), str([c for c in codes if "+" in c or "_" in c]))
            with pg.expect_download() as dl:
                pg.click("#exportBom")
            check("descargar CSV", Path(dl.value.path()).stat().st_size > 100)
            pg.click("[data-go=editor] >> nth=-1"); wait_idle(pg, 800)
            check("volver al editor", pg.is_visible("#screen-editor"))

            # 10) Tableros: duplicar, abrir y borrar.
            pg.click(".brand"); wait_idle(pg, 800)
            check("tableros: tarjetas", pg.locator(".card-p").count() >= 1)
            check("tableros: tarjeta con gabinete y fecha", "·" in pg.inner_text(".card-p >> nth=0"))
            pg.click("[data-dup=ts4]"); wait_idle(pg, 4000)
            pid = pg.evaluate("projectId")
            check("duplicar tablero", pid != "ts4", pid)
            check("duplicado dentro de normativa", chip_ok(pg), chip(pg))
            pg.click(".brand"); wait_idle(pg, 800)
            pg.click(f"[data-del='{pid}']"); wait_idle(pg, 2500)
            check("borrar tablero", pg.evaluate("projectId") == "ts4")

            # 11) Importar cada PDF de ejemplo desde Tableros.
            for pdf in PDFS:
                pg.goto(url + "/?id=ts4#projects"); pg.reload(); wait_idle(pg, 4000)
                n_proj = pg.locator(".card-p").count()
                pg.set_input_files("#pdfNew", str(pdf))
                name = pdf.stem[-12:]
                if "GENERAL" not in pdf.stem:
                    wait_idle(pg, 7000)
                if "GENERAL" in pdf.stem:  # unifilar de toda la planta: no entra en un gabinete; no debe quedar un tablero roto
                    try:
                        pg.wait_for_function("document.getElementById('message').textContent.includes('tableros distintos')", timeout=20000); ok = True
                    except Exception:
                        ok = False
                    check(f"importar {name}: avisa varios tableros", ok, pg.inner_text("#message")[:90])
                    check(f"importar {name}: no deja tablero roto", pg.is_visible("#screen-projects") and pg.locator(".card-p").count() == n_proj)
                    continue
                check(f"importar {name}: abre el editor", pg.is_visible("#screen-editor"))
                check(f"importar {name}: con equipos", pg.evaluate("project.devices.length") > 0, str(pg.evaluate("project.devices.length")))
                check(f"importar {name}: dentro de normativa", chip_ok(pg), chip(pg))
                check(f"importar {name}: nombre del tablero corto", "Unifilares" not in pg.inner_text("#projectName"), pg.inner_text("#projectName"))
                short = pg.inner_text("#projectName"); n_dev = pg.evaluate("project.devices.length")
                pg.click(".brand"); wait_idle(pg, 2500)
                card = pg.inner_text(".card-p.current") if pg.locator(".card-p.current").count() else ""
                check(f"importar {name}: tarjeta actualizada al volver", short in card and f"{n_dev} equipo" in card, card[:80])

            check("sin errores de JavaScript", not errors, "; ".join(errors[:3]))
            browser.close()
    finally:
        if server:
            server.terminate()
            server.wait(10)
        ts4.write_bytes(ts4_backup)
        for f in (set(proj_dir.glob("*.json")) if proj_dir.exists() else set()) - before:
            f.unlink()
        if proj_dir.exists() and not any(proj_dir.iterdir()) and not before:
            shutil.rmtree(proj_dir)
    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} OK" + (f" · fallan: {', '.join(failed)}" if failed else ""))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
