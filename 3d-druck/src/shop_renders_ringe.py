"""Shop-Renderings der Noppen-Ringe -> public/images/noppen-ring-<variante>-<n>.jpg

Aufruf:  python3 3d-druck/src/shop_renders_ringe.py
"""
import sys
from pathlib import Path

import numpy as np
from manifold3d import Manifold
from PIL import ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import pb_noppen_ring as R  # noqa: E402

_argv = sys.argv
sys.argv = [sys.argv[0]]
import shop_renders as S  # noqa: E402
sys.argv = _argv

OUT = R.ROOT / "public/images"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
PRODUCTS = {   # Variante: (Farbe, Dateiname)
    "1x1": ("#D8382B", "noppen-ring-1"),
    "1x2": ("#2A6FD6", "noppen-ring-2"),
    "2x2": ("#F2B705", "noppen-ring-4"),
    "1x1-loch": ("#2E9E4F", "noppen-ring-loch"),
}
SIZES = [(15, "Kinder"), (17, "Frauen"), (20, "Männer")]
PATTERNS = ["glatt", "senkrecht", "waagrecht"]


def tm(m):
    return R.to_tm(m)


def row(meshes, gap=7.0):
    """Teile nebeneinander entlang X legen."""
    out, x = [], 0.0
    for m in meshes:
        t = tm(m)
        t.apply_translation((x - t.bounds[0][0], 0, 0))
        x = t.bounds[1][0] + gap
        out.append(t)
    return out


def labels(im, texts):
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 34)
    n = len(texts)
    for k, t in enumerate(texts):
        w = d.textlength(t, font=f)
        x = (k + 0.5) * im.width / n - w / 2
        d.text((x, im.height * 0.84), t, fill=(60, 55, 50), font=f)
    return im


def main():
    for v, (col, fn) in PRODUCTS.items():
        g = 0.45
        # 1) Titelbild
        hero = R.build(v, 17, "glatt")
        S.render([(tm(hero), col, g)], 24, -58, fill=0.70).save(OUT / f"{fn}-1.jpg", quality=90)
        # 2) Muster
        ms = row([R.build(v, 17, p) for p in PATTERNS])
        labels(S.render([(m, col, g) for m in ms], 20, -78, fill=0.92), ["glatt", "senkrecht", "waagrecht"]).save(OUT / f"{fn}-2.jpg", quality=90)
        # 3) Größen
        gs = row([R.build(v, d, "waagrecht") for d, _ in SIZES])
        labels(S.render([(m, col, g) for m in gs], 20, -78, fill=0.92), [f"{n} {d} mm" for d, n in SIZES]).save(OUT / f"{fn}-3.jpg", quality=90)
        # 4) Ring mit Loch: Stange eingesteckt
        if v == "1x1-loch":
            ring = R.build(v, 17, "glatt")
            ri = 17 / 2
            ro = ri + R.BAND
            z_top = (ro - R.FLAT) + ro + R.SOCKET_ABOVE
            z_bot = (ro - R.FLAT) + ro - R.BAR_DEPTH_INTO_RING
            bar = Manifold.cylinder(28, 1.6, 1.6, 64).translate((0, 0, z_bot))
            knob = Manifold.sphere(2.6, 64).translate((0, 0, z_bot + 28))
            S.render([(tm(ring), col, g), (tm(bar), "#3A3A3A", 0.6), (tm(knob), "#3A3A3A", 0.6)],
                     22, -58, fill=0.78).save(OUT / f"{fn}-4.jpg", quality=90)
        print(v, "ok")


if __name__ == "__main__":
    main()
