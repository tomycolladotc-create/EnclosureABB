"""Abre el editor local; reutiliza uno activo o elige un puerto libre."""

from http.server import ThreadingHTTPServer
from urllib.request import urlopen
import webbrowser

from app import Handler


def main():
    for port in range(8765, 8775):
        url = f"http://127.0.0.1:{port}"
        try:
            with urlopen(url + "/api/appearances", timeout=0.5) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    print("Editor ABB activo:", url)
                    return
        except Exception:
            pass
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        except OSError:
            continue
        print("Editor ABB:", url, flush=True)
        webbrowser.open(url)
        server.serve_forever()
        return
    raise RuntimeError("No hay un puerto local disponible entre 8765 y 8774")


if __name__ == "__main__":
    main()
