"""Shop-Renderings Renn-Flitzer -> public/images/renn-flitzer-<n>.jpg

Aufruf:  python3 3d-druck/src/shop_renders_flitzer.py
"""
import sys
from pathlib import Path

sys.argv = [sys.argv[0], "--steck"]
sys.path.insert(0, str(Path(__file__).parent))
import pb_renn_flitzer as C  # noqa: E402

sys.argv = [sys.argv[0]]
import shop_renders as S  # noqa: E402

OUT = C.ROOT / "public/images"
BODY, WHEEL, AXLE = "#D8382B", "#1F1F1F", "#9A9A9A"


def parts(explode=0.0):
    body = C.build_body()
    pin, wh = C.build_pin(), C.build_wheel()
    wt = wh.rotate((0, 180, 0)).translate((0, 0, C.W))
    car = lambda m: C.to_tm(m.rotate((90, 0, 0)))          # Fahrlage
    out = [(car(body), BODY, 0.5)]
    for x in C.WHEELS_X:
        out.append((car(wh.translate((x, C.WHEEL_H, -explode))), WHEEL, 0.25))
        out.append((car(wt.translate((x, C.WHEEL_H, explode))), WHEEL, 0.25))
        out.append((car(pin.translate((x, C.WHEEL_H, 0))), AXLE, 0.5))
    return out


def main():
    p = parts()
    S.render(p, 22, -58, fill=0.86).save(OUT / "renn-flitzer-1.jpg", quality=90)     # Titel: schräg vorne
    S.render(p, 4, -90, fill=0.90).save(OUT / "renn-flitzer-2.jpg", quality=90)      # Seitenansicht
    S.render(p, 24, -130, fill=0.86).save(OUT / "renn-flitzer-3.jpg", quality=90)    # schräg hinten
    S.render(parts(9.0), 28, -52, fill=0.86).save(OUT / "renn-flitzer-4.jpg", quality=90)  # Steck-System
    print("ok")


if __name__ == "__main__":
    main()
