"""Shop-Bilder PB Doppeldecker -> 3d-druck/doppeldecker-bausatz/pb-doppeldecker-bausatz_shop-<n>.jpg

  shop-1  fertiges Modell auf dem Ständer
  shop-2  die 3 Gießäste
  shop-3  Ansicht schräg vorne (Sternmotor, Fahrwerk)
  shop-4  Explosionszeichnung „So wird er gebaut“
Aufruf:  python3 3d-druck/src/shop_renders_doppeldecker.py
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import bauanleitung_doppeldecker as B  # noqa: E402  (Farben, Szene)
import pb_doppeldecker_bausatz as D  # noqa: E402

S = B.S
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def label(im, t):
    d = ImageDraw.Draw(im); f = ImageFont.truetype(FONT, 34)
    d.text((40, 30), t, fill=(60, 55, 50), font=f)
    return im


EXPLODE = {"B1": (0, 0, 22), "B3": (0, 0, 22), "B4": (0, 0, 11), "B5": (0, 0, 11), "A3": (-14, 0, 0),
           "C1": (-30, 0, 0), "C2": (-38, 0, 0), "C5": (-8, 0, 0), "C6": (-8, 0, 0), "A4": (0, 0, 12), "A5": (6, 0, 12),
           "A6": (8, 0, 0), "A7": (14, 0, 0), "B6": (0, 0, -12), "C9": (0, 0, -12), "C7": (0, 0, -12), "C8": (0, 0, -12),
           "B2": (0, 0, -6), "C11": (0, 0, 16), "A8": (0, 0, 8), "B7": (0, 0, 10), "C10": (0, 0, -8)}


def main():
    D.OUT.mkdir(parents=True, exist_ok=True)
    P = D.assembled()
    q = 90
    base, pole = D.on_stand(P)
    sc = B.scene(P, [(D.to_tm(base), "#3A3A3A", 0.35), (D.to_tm(pole), "#3A3A3A", 0.35)])
    S.render(sc, 16, -60, fill=0.9).save(D.OUT / f"{D.NAME}_shop-1.jpg", quality=q)

    S.render(B.scene(P), 12, -150, fill=0.86).save(D.OUT / f"{D.NAME}_shop-3.jpg", quality=q)

    exp = []
    for n, m in P.items():
        dx, dy, dz = EXPLODE.get(B.nr_of(n), (0, 0, 0))
        if B.nr_of(n) in ("B3", "B4", "B5", "B6", "C7", "C8", "A7", "C13"):
            bb = m.bounding_box(); sg = 1 if (bb[1] + bb[4]) / 2 > 0 else -1
            dy += sg * (6 if B.nr_of(n) in ("C7", "C8") else 0)
        exp.append((D.to_tm(m.translate((dx, dy, dz))),) + B.color(n))
    label(S.render(exp, 24, -55, fill=0.88), "So wird er gebaut – 52 Teile").save(D.OUT / f"{D.NAME}_shop-4.jpg", quality=q)

    parts = []
    for k, (dx, dy) in zip("ABC", ((0, 0), (185, 0), (92, -170))):
        plate, *_ = D.build_sprue(k)
        col = {"A": B.RED, "B": "#E2D3AA", "C": "#3A3A3A"}[k]
        parts.append((D.to_tm(plate.translate((dx, dy, 0))), col, 0.45))
    label(S.render(parts, 52, -82, fill=0.94), "3 Gießäste zum Heraustrennen").save(D.OUT / f"{D.NAME}_shop-2.jpg", quality=q)
    print("ok")


if __name__ == "__main__":
    main()
