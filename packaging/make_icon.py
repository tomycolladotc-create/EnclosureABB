"""Genera el ícono multi-resolución (datos/icon.ico) para la app y el instalador."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "datos" / "icon.ico"


def render_icon(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 256.0
    r = lambda v: int(round(v * s))

    # Fondo redondeado azul acero técnico
    d.rounded_rectangle([r(12), r(12), r(244), r(244)], radius=r(42), fill=(21, 44, 68, 255))
    # Gabinete interior RAL 7035
    d.rounded_rectangle([r(42), r(32), r(214), r(224)], radius=r(14), fill=(224, 229, 234, 255), outline=(255, 255, 255, 220), width=max(1, r(4)))
    # Placa interior
    d.rectangle([r(58), r(48), r(198), r(208)], fill=(242, 245, 248, 255), outline=(140, 155, 170, 255), width=max(1, r(2)))
    # Dos rieles DIN horizontales
    for ry in (98, 162):
        d.rectangle([r(66), r(ry - 7), r(190), r(ry + 7)], fill=(158, 171, 184, 255))
    # Interruptor general arriba a la izquierda (cuerpo gris + palanca roja ABB)
    d.rounded_rectangle([r(72), r(64), r(116), r(132)], radius=r(5), fill=(72, 86, 102, 255), outline=(34, 46, 58, 255), width=max(1, r(2)))
    d.rectangle([r(84), r(92), r(104), r(108)], fill=(217, 45, 32, 255))
    # 3 interruptores modulares DIN arriba a la derecha
    for i in range(3):
        bx = 124 + i * 21
        d.rectangle([r(bx), r(72), r(bx + 18), r(124)], fill=(255, 255, 255, 255), outline=(72, 86, 102, 255), width=max(1, r(2)))
        d.rectangle([r(bx + 4), r(93), r(bx + 14), r(103)], fill=(38, 52, 68, 255))
    # 4 interruptores modulares DIN fila inferior
    for i in range(4):
        bx = 74 + i * 27
        d.rectangle([r(bx), r(138), r(bx + 23), r(188)], fill=(255, 255, 255, 255), outline=(72, 86, 102, 255), width=max(1, r(2)))
        d.rectangle([r(bx + 5), r(158), r(bx + 18), r(168)], fill=(38, 52, 68, 255))
    # Barra PE verde/amarillo al pie
    d.rectangle([r(72), r(194), r(184), r(202)], fill=(34, 139, 68, 255))
    return img


def main():
    base = render_icon(256)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    base.save(OUT, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Icono generado: {OUT} ({OUT.stat().st_size:,} B)")


if __name__ == "__main__":
    main()
