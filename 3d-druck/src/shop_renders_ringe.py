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
PATTERNS = ["glatt", "senkrecht", "waagrecht", "tentakel"]


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


def lying(m):
    """Ring hinlegen (Achse senkrecht), Sockel nach hinten-rechts drehen, auf z=0 stellen."""
    m = m.rotate((90, 0, 0)).rotate((0, 0, 110))
    return m.translate((0, 0, -m.bounding_box()[2]))


def labels(im, texts, y=0.84):
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 34)
    n = len(texts)
    for k, t in enumerate(texts):
        w = d.textlength(t, font=f)
        x = (k + 0.5) * im.width / n - w / 2
        d.text((x, im.height * y), t, fill=(60, 55, 50), font=f)
    return im


def diamond(stud_top, z_bot, d=9.0):
    """Facettierter Edelstein (Brillantform) mit Stift, der in die hohle Noppe gesteckt ist."""
    rg = d / 2
    h_crown, h_pav, lift = 0.32 * d, 0.43 * d, 0.4
    z_g = stud_top + lift + h_pav                     # Rundiste
    pts = []
    for k in range(8):                                # Tafel (Achteck)
        a = 2 * np.pi * (k + 0.5) / 8
        pts.append((0.55 * rg * np.cos(a), 0.55 * rg * np.sin(a), z_g + h_crown))
    for k in range(16):                               # Krone-Facetten + Rundiste
        a = 2 * np.pi * k / 16
        pts.append((0.82 * rg * np.cos(a + np.pi / 16), 0.82 * rg * np.sin(a + np.pi / 16), z_g + 0.55 * h_crown))
        pts.append((rg * np.cos(a), rg * np.sin(a), z_g + 0.08))
        pts.append((rg * np.cos(a), rg * np.sin(a), z_g - 0.08))
    for k in range(8):                                # Pavillon-Facetten
        a = 2 * np.pi * (k + 0.5) / 8
        pts.append((0.45 * rg * np.cos(a), 0.45 * rg * np.sin(a), z_g - 0.55 * h_pav))
    pts.append((0, 0, z_g - h_pav))                   # Kalette (Spitze)
    gem = Manifold.hull_points(pts)
    peg = Manifold.cylinder(z_g - h_pav + 0.5 - z_bot, 1.55, 1.55, 48).translate((0, 0, z_bot))
    return gem, peg


def main():
    for v, (col, fn) in PRODUCTS.items():
        g = 0.45
        # 1) Titelbild
        hero = R.build(v, 17, "glatt")
        S.render([(tm(hero), col, g)], 24, -58, fill=0.70).save(OUT / f"{fn}-1.jpg", quality=90)
        # 2) Muster: Ringe liegend (wie auf dem Tisch), Blick seitlich auf den Reif ->
        #    "senkrecht" erscheint senkrecht, "waagrecht" waagrecht; Noppen zeigen schräg nach hinten
        ms = row([lying(R.build(v, 17, p)) for p in PATTERNS], gap=6.0)
        labels(S.render([(m, col, g) for m in ms], 20, -90, fill=0.92), ["glatt", "senkrecht", "waagrecht", "Tentakel"], y=0.64).save(OUT / f"{fn}-2.jpg", quality=90)
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
            stud_top = z_top + R.STUD_H
            gem, peg = diamond(stud_top, z_bot)
            S.render([(tm(ring), col, g), (tm(peg), "#E8ECEF", 0.9), (tm(gem), "#DDF3FF", 0.95)],
                     26, -58, fill=0.78).save(OUT / f"{fn}-4.jpg", quality=90)
        print(v, "ok")


if __name__ == "__main__":
    main()
