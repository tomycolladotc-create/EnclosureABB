"""Lanzador de escritorio liviano para Windows (bajo consumo de RAM).

- Arranca el servidor local en un puerto libre (8765–8799); si ya hay una instancia
  corriendo, abre una ventana nueva sobre esa instancia y sale (instancia única).
- Abre la interfaz en modo ventana de aplicación con Edge/Chrome (`--app=...`), que
  comparte el proceso del navegador del sistema en lugar de levantar un runtime
  WebView2/Chromium adicional (~180-250 MB menos de RAM) y conserva descargas e
  impresión nativas. Si no encuentra Edge/Chrome, abre el navegador predeterminado.
- Cuando se cierra la ventana (`POST /api/bye` sin recarga en 4 s, o sin latido
  durante 25 s tras haberse conectado), detiene el servidor y libera el 100 % de RAM.
"""
from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from urllib.request import urlopen
import webbrowser


def _setup_logging():
    """En modo --noconsole (stdout/stderr = None), redirige a un log pequeño en AppData."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    try:
        import rutas
        log_dir = rutas.user_data_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = open(log_dir / "enclosure_abb.log", "w", encoding="utf-8", buffering=1)
        sys.stdout = fh
        sys.stderr = fh
    except Exception:
        fh = open(os.devnull, "w", encoding="utf-8")
        sys.stdout = fh
        sys.stderr = fh


def _find_app_browser() -> str | None:
    """Busca Microsoft Edge (preinstalado en Windows 10/11) o Google Chrome para abrir modo --app."""
    pf = os.environ.get("PROGRAMFILES", r"C:\Program Files")
    pf86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
    local = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        Path(pf86) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(pf) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(pf) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(pf86) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(local) / "Google" / "Chrome" / "Application" / "chrome.exe",
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return shutil.which("msedge") or shutil.which("chrome")


def _open_window(url: str) -> None:
    browser = _find_app_browser()
    if browser:
        try:
            creation = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            subprocess.Popen(
                [browser, f"--app={url}", "--window-size=1360,860"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation,
            )
            return
        except Exception:
            pass
    webbrowser.open(url)


def _find_running_instance(ports) -> str | None:
    for port in ports:
        url = f"http://127.0.0.1:{port}"
        try:
            with urlopen(url + "/api/ping", timeout=0.35) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("app") == "EnclosureABB":
                        return url
        except Exception:
            continue
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description="EnclosureABB — Editor de topográficos ABB")
    parser.add_argument("--port", type=int, default=0, help="Puerto fijo (0 = automático 8765..8799)")
    parser.add_argument("--no-browser", action="store_true", help="No abrir ventana del navegador")
    parser.add_argument("--no-autoshutdown", action="store_true", help="No cerrar automáticamente al cerrar la ventana")
    args = parser.parse_args(argv)

    _setup_logging()

    ports = [args.port] if args.port else list(range(8765, 8800))
    if not args.port:
        running = _find_running_instance(ports)
        if running:
            if not args.no_browser:
                _open_window(running)
            return

    import app

    app.DESKTOP_MODE = not args.no_autoshutdown
    state = {"seen": False, "last_ping": time.monotonic(), "bye_at": None, "active": 0}
    lock = threading.Lock()

    def on_ping():
        with lock:
            state["seen"] = True
            state["last_ping"] = time.monotonic()
            state["bye_at"] = None

    def on_bye():
        with lock:
            state["seen"] = True
            state["bye_at"] = time.monotonic()

    def on_req_start():
        with lock:
            state["active"] += 1
            state["last_ping"] = time.monotonic()

    def on_req_end():
        with lock:
            state["active"] = max(0, state["active"] - 1)
            state["last_ping"] = time.monotonic()

    app.ON_PING = on_ping
    app.ON_BYE = on_bye
    app.ON_REQ_START = on_req_start
    app.ON_REQ_END = on_req_end

    server = None
    chosen_port = None
    for port in ports:
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), app.Handler)
            chosen_port = port
            break
        except OSError:
            continue
    if server is None:
        raise RuntimeError("No hay ningún puerto local libre entre 8765 y 8799")

    url = f"http://127.0.0.1:{chosen_port}"
    print(f"EnclosureABB activo en {url}", flush=True)

    # Pre-cargar sólo los 2 MB de bytes JSON (sin retener dicts pesados ni OpenCV en RAM)
    threading.Thread(target=lambda: app.resolved_drawing_bytes("fronts"), daemon=True).start()

    if not args.no_autoshutdown:
        def watchdog():
            started = time.monotonic()
            while True:
                time.sleep(1.0)
                now = time.monotonic()
                with lock:
                    seen = state["seen"]
                    last_ping = state["last_ping"]
                    bye_at = state["bye_at"]
                    active = state["active"]
                if active > 0:
                    continue
                if bye_at is not None and (now - bye_at) >= 4.0:
                    server.shutdown()
                    return
                # 150 s cubre pestañas minimizadas (Edge/Chrome limitan setInterval a 1 min en segundo plano)
                if seen and (now - last_ping) >= 150.0:
                    server.shutdown()
                    return
                if not seen and (now - started) >= 90.0:
                    server.shutdown()
                    return

        threading.Thread(target=watchdog, daemon=True).start()

    if not args.no_browser:
        threading.Thread(target=_open_window, args=(url,), daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
