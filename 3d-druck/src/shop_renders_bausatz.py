"""Renderings Formel-Bausatz -> 3d-druck/formel-bausatz/ und public/images/formel-bausatz-<n>.jpg"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pb_formel_bausatz as B  # noqa: E402
_a = sys.argv; sys.argv = [sys.argv[0]]
import shop_renders as S  # noqa: E402
sys.argv = _a
from manifold3d import Manifold, OpType  # noqa: E402
from PIL import ImageDraw, ImageFont  # noqa: E402

RED, BLACK, GREY, YEL = "#D8382B", "#1F1F1F", "#9A9A9A", "#F2B705"
COL = {"fahrgestell": RED, "frontfluegel": RED, "heckfluegel": RED, "helm": YEL,
       "achse_hinten": GREY, "achse_vorne": GREY, "raeder_hinten": BLACK, "raeder_vorne": BLACK}
GLOSS = {"raeder_hinten": 0.25, "raeder_vorne": 0.25}
EXPLODE = {"frontfluegel": (-12, 0, 0), "heckfluegel": (0, -22, 6), "helm": (0, 0, 14),
           "achse_hinten": (0, 0, -8), "achse_vorne": (0, 0, -8), "raeder_hinten": (0, 0, -8), "raeder_vorne": (0, 0, -8)}
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def label(im, t):
    d = ImageDraw.Draw(im); f = ImageFont.truetype(FONT, 34)
    d.text((40, 30), t, fill=(60, 55, 50), font=f)
    return im


def main():
    asm = B.assembled()
    parts = [(B.to_tm(m), COL[k], GLOSS.get(k, 0.45)) for k, m in asm.items()]
    out_pub = B.ROOT / "public/images"
    S.render(parts, 22, -58, fill=0.86).save(out_pub / "formel-bausatz-1.jpg", quality=90)
    exp = []
    for k, m in asm.items():
        dx, dy, dz = EXPLODE.get(k, (0, 0, 0))
        if k.startswith("raeder") or k.startswith("achse"):
            # Räder seitlich nach außen ziehen
            halves = m.decompose() if k.startswith("raeder") else [m]
            for h in halves:
                bb = h.bounding_box(); sgn = 1 if (bb[1] + bb[4]) / 2 > 0 else -1
                off = (0, sgn * 9, 0) if k.startswith("raeder") else (0, 0, 0)
                exp.append((B.to_tm(h.translate(off)), COL[k], GLOSS.get(k, 0.45)))
        else:
            exp.append((B.to_tm(m.translate((dx, dy, dz))), COL[k], GLOSS.get(k, 0.45)))
    label(S.render(exp, 26, -52, fill=0.86), "So wird er gebaut").save(out_pub / "formel-bausatz-3.jpg", quality=90)
    plate = B.plate_layout(); grid, gates = B.sprue(plate)
    pl = Manifold.batch_boolean([m for m, _ in plate] + [grid, gates], OpType.Add)
    label(S.render([(B.to_tm(pl), RED, 0.45)], 48, -70, fill=0.92), "Bausatz am Gießast").save(out_pub / "formel-bausatz-2.jpg", quality=90)
    print("ok")


if __name__ == "__main__":
    main()
