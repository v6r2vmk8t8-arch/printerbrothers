"""PB Taschen-Disc: kleine Wurfscheibe (Ø 100 mm) für die Hosentasche.

- Gedruckt KOPFÜBER (Oberseite auf der texturierten Platte -> schöne Struktur oben), ohne Stützen.
- Schwerer Rand mit leicht eingerollter Lippe (Kreiselstabilität, guter Griff), dünne Scheibe.
- Oberseite: Printer-Brothers-Logo + Ring + „PRINTER BROTHERS“ im Bogen.
  einfarbig: graviert (0.4 mm) | zweifarbig (AMS): bündiges Inlay in den ersten 3 Schichten.

Aufruf:  python3 3d-druck/src/pb_taschen_disc.py
"""
import sys
from pathlib import Path

import numpy as np
from manifold3d import CrossSection, JoinType, Manifold, OpType, set_circular_segments

sys.path.insert(0, str(Path(__file__).parent))
import pb_kaffeeklipp as KK  # noqa: E402  (Logo-Import)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude/skills/stl-designer/scripts"))
from stl_tools import check, export_parts, preview  # noqa: E402

set_circular_segments(256)
OUT = ROOT / "3d-druck/taschen-disc"

R = 50.0          # Außenradius (Ø 100)
H = 11.0          # Gesamthöhe
PLATE = 1.8       # Scheibendicke
RIM_IN = 2.6      # Randdicke oben (innen senkrecht)
LIP = 4.0         # Randdicke unten (eingerollte Lippe)
INLAY = 0.6       # Logo-Inlay (3 Schichten à 0.2)
ENGRAVE = 0.4
LOGO_R = 19.0
TEXT_R = 29.5     # Radius der Bogenschrift (Mitte der Buchstaben)
TEXT_SIZE = 5.2


def revolve(pts):
    cs = CrossSection([pts])
    if cs.area() <= 0 or cs.is_empty():
        cs = CrossSection([pts[::-1]])
    return Manifold.revolve(cs, 256)


def body():
    """Gebrauchslage: Oberseite bei z=H, Rand zeigt nach unten (z=0)."""
    zp = H - PLATE
    pts = [(0, H), (R - 1.0, H), (R, H - 1.0),                     # Oberkante gefast
           (R - 0.5, 1.4)]                                          # Außenwand leicht eingezogen
    for k in range(1, 8):                                           # Unterkante gerundet
        a = np.pi / 2 * k / 8
        pts.append((R - 0.5 - 1.4 * (1 - np.cos(a)) * 0.9, 1.4 - 1.4 * np.sin(a)))
    pts += [(R - 2.2, 0.0), (R - LIP + 0.7, 0.0)]
    for k in range(1, 6):                                           # Lippe innen gerundet
        a = np.pi / 2 * k / 6
        pts.append((R - LIP + 0.7 - 0.7 * np.sin(a), 0.7 - 0.7 * np.cos(a)))
    pts += [(R - LIP, 2.2), (R - RIM_IN, 6.0),                      # Lippe: im Druck 22° Überhang
            (R - RIM_IN, zp - 1.5)]
    for k in range(1, 7):                                           # Hohlkehle Rand/Scheibe
        a = np.pi / 2 * k / 6
        pts.append((R - RIM_IN - 1.5 * (1 - np.cos(a)), zp - 1.5 + 1.5 * np.sin(a)))
    pts += [(0, zp)]
    return revolve(pts)


def arc_text(s, r, size, z, h):
    """Schrift im Bogen oben, Buchstaben stehen radial (lesbar von oben)."""
    from build123d import Align, BuildPart, BuildSketch, FontStyle, Text, extrude
    import pb_formel_modellbausatz as FM
    widths = []
    for ch in s:
        if ch == " ":
            widths.append(size * 0.35); continue
        with BuildPart() as bp:
            with BuildSketch():
                Text(ch, size, font_style=FontStyle.BOLD, align=(Align.CENTER, Align.CENTER))
            extrude(amount=h)
        bb = bp.part.bounding_box()
        widths.append(bb.size.X)
    gap = size * 0.12
    total = sum(widths) + gap * (len(s) - 1)
    ang = total / r                                                # Bogenlänge -> Winkel
    a = np.pi / 2 + ang / 2
    out = []
    for ch, w in zip(s, widths):
        a_c = a - (w / 2) / r
        if ch != " ":
            m = FM.text_relief(ch, size, 0, 0, 0, h, bold=True)
            m = m.rotate((0, 0, np.degrees(a_c - np.pi / 2))).translate((r * np.cos(a_c), r * np.sin(a_c), z))
            out.append(m)
        a -= (w + gap) / r
    return Manifold.batch_boolean(out, OpType.Add)


def deco_2d():
    green, white, _ = load_logo()
    return green, white


def load_logo():
    KK.LOGO_R = LOGO_R
    green, white, sc = KK.load_logo()
    green = green.offset(-0.06, JoinType.Miter)
    white = white.offset(-0.06, JoinType.Miter)
    return green, white, sc


def ring2d(r0, r1):
    return CrossSection.circle(r1) - CrossSection.circle(r0)


def build():
    b = body()
    green, white, _ = load_logo()
    # Grafik: Logo (grün+weiß), Ring um das Logo, Schrift im Bogen, äußerer Zierring
    def layer(depth):
        z0 = H - depth
        g = Manifold.extrude(green + ring2d(LOGO_R + 2.0, LOGO_R + 3.0) + ring2d(R - 6.0, R - 5.0), depth).translate((0, 0, z0))
        t = arc_text("PRINTER BROTHERS", TEXT_R, TEXT_SIZE, z0, depth)
        w = Manifold.extrude(white, depth).translate((0, 0, z0))
        return g + t, w
    g, w = layer(INLAY)
    base = b - g - w
    eg, ew = layer(ENGRAVE)
    engraved = b - eg - ew
    return base, g, w, engraved


def flip(m):
    m = m.rotate((180, 0, 0))                    # Oberseite nach unten (keine Spiegelung)
    return m.translate((0, 0, -m.bounding_box()[2]))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base, g, w, engraved = build()
    to_tm = KK.to_tm
    shift = -min(flip(x).bounding_box()[2] for x in (base, g, w))
    parts = {k: to_tm(v.rotate((180, 0, 0)).translate((90, 90, H))) for k, v in
             {"basis": base, "logo-gruen": g, "logo-weiss": w}.items()}
    export_parts(parts, OUT / "pb-taschen-disc_100mm", write_combined=False, write_preview=False)
    eng = to_tm(flip(engraved).translate((90, 90, 0)))
    check(eng, "einfarbig (graviert)", (180, 180, 180))
    eng.export(OUT / "pb-taschen-disc_100mm_einfarbig.stl")
    print(f"Masse PLA (1.24 g/cm³): {engraved.volume() / 1000 * 1.24:.1f} g")
    use = {"disc": to_tm(engraved)}
    preview(use, OUT / "pb-taschen-disc_vorschau.png", colors={"disc": "#E8452C"})


if __name__ == "__main__":
    main()
