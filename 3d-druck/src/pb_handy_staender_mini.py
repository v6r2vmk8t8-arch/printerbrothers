"""PB Taschen-Handyständer „Mini“ – zusammengeklappt ca. 7 × 3 cm, passt in die Hosentasche.

Gleiche Mechanik wie der große Ständer (pb_handy_staender.py), verkleinert:
  1. Lehne mit Ablage und eingebauter Stütze (Print-in-Place-Scharnier, flach gedruckt)
  2. Fuß 30 × 70 mm: Rasten IN die Platte versenkt (zusammengeklappt liegt die Lehne flach auf),
     Lagerböcke zum EINRASTEN der Lehne (sie fällt in der Tasche nicht heraus)
Zum Einpacken: Stütze einklappen, Lehne nach hinten flach auf den Fuß legen.

Aufruf:  python3 3d-druck/src/pb_handy_staender_mini.py
"""
import sys
from pathlib import Path

import numpy as np
from manifold3d import Manifold, OpType

sys.path.insert(0, str(Path(__file__).parent))
import pb_handy_staender as H  # noqa: E402
from stl_tools import check  # noqa: E402

OUT = H.OUT
# ---------------------------------------------------------------- Maße (überschreiben die des großen Ständers)
H.T = 5.0
H.W = 24.0
H.LB = 70.0
H.LH = 31.0
H.LS = 34.8
H.SW = 12.0
H.GAP = 0.4
H.SWING = 14.0
H.PIN_R, H.HOLE_R = 1.1, 1.5
H.PIVOT_R = H.T / 2
H.PIVOT_L = 3.2
H.LEDGE_D, H.LEDGE_T, H.LIP = 9.5, 3.0, 2.5
H.CABLE = 9.0
H.THUMB_R = 4.5
BT = 4.2                               # Fußplatte (Rasten werden hineingeschnitten)
H.BT = BT
GROOVE = 1.8
H.GROOVE = GROOVE
H.RACK_H = 0.0                         # keine aufgesetzte Leiste: Oberkante = Plattenoberkante
H.ZP = BT + H.PIVOT_R + 0.35           # Achse so tief, dass die Lehne zusammengeklappt auf der Platte liegt
BW = 32.0
Y_FRONT, LENGTH = -8.0, 80.0
H.ANGLES = ANGLES = [54, 64, 74]
PHONES = {"Handy 16 cm": (75, 160, 9, 180), "großes Handy 17 cm": (78, 170, 10, 230)}  # B, H, Dicke mm, g
STAND_G = 25          # Ständer ca. 25 g
STAB = []
SNAP = 0.35                            # Einrast-Übermaß je Seite


def base(notches):
    yb = Y_FRONT + LENGTH
    plate = H.rrect_xy(-BW / 2, BW / 2, Y_FRONT, yb, 5.0, 0, BT)
    # Rasten in die Platte: vorne Schräge, hinten senkrechte Wand
    xr = H.SW / 2 + 1.2
    zt, zb = BT, BT - GROOVE
    grooves = [H.prism_x([(f - GROOVE * 0.7, zt + 0.5), (w, zt + 0.5), (w, zb), (f, zb)], -xr, xr) for f, w in notches]
    plate = plate - Manifold.batch_boolean(grooves, OpType.Add)
    # Lagerböcke mit Einrast-Schlitz: Eingang schmaler als der Zapfen, Sitz rund
    xi = H.W / 2 + 0.4
    r = H.PIVOT_R
    for s in (-1, 1):
        x0, x1 = (xi, BW / 2) if s > 0 else (-BW / 2, -xi)
        blk = H.rrect_xy(x0, x1, -6.0, 6.0, 1.2, 0, H.ZP + r + 1.4)
        seat = H.cyl_x(r + 0.2, x0 - 1, x1 + 1, 0, H.ZP)
        neck = H.box(x0 - 1, x1 + 1, -(r - SNAP), r - SNAP, H.ZP, H.ZP + 10)
        lead = H.prism_x([(-(r - SNAP), H.ZP + r + 0.2), (r - SNAP, H.ZP + r + 0.2), (r + 0.9, H.ZP + r + 1.45),
                          (-(r + 0.9), H.ZP + r + 1.45)], x0 - 1, x1 + 1)
        # Entlastungsschlitz unten: die beiden Backen federn beim Einrasten
        relief = H.box(x0 - 1, x1 + 1, -0.5, 0.5, BT + 0.4, H.ZP)
        plate = plate + (blk - seat - neck - lead - relief)
    # Daumenmulde zum Aufklappen + Gradzahlen
    import pb_formel_modellbausatz as FM
    marks = [FM.text_relief(f"{a}°", 3.2, xr + 4.6, (f + w) / 2, BT - 0.4, 0.5, bold=True) for a, (f, w) in zip(ANGLES, notches)]
    marks.append(FM.text_relief("PB", 5.0, 0, yb - 6.0, BT - 0.4, 0.5, bold=True))
    return plate - Manifold.batch_boolean(marks, OpType.Add)


def taper(strut):
    """Fußende der Stütze keilförmig auf 2 mm zuspitzen -> schmale Rasten, mehr Stufen auf kurzem Fuß."""
    ye, L, tip = H.LH + H.LS, 5.0, 1.0
    x0, x1 = -H.SW, H.SW
    top = H.prism_x([(ye - L, H.T + 0.01), (ye + 1, H.T + 0.01), (ye + 1, H.T / 2 + tip)], x0, x1)
    bot = H.prism_x([(ye - L, -0.01), (ye + 1, -0.01), (ye + 1, H.T / 2 - tip)], x0, x1)
    return strut - top - bot


def notch_positions(back, strut):
    zb = BT - GROOVE
    floor = H.box(-80, 80, 5, 200, zb - 5, zb)
    slab = H.box(-80, 80, -40, 200, zb - 0.01, BT + 0.3)
    out = []
    for a in ANGLES:
        phi = H.solve_phi(back, strut, floor, a)
        _, s = H.place(back, strut, a, phi)
        bb = (s ^ slab).bounding_box()
        out.append((bb[1] - 0.5, bb[4] + 1.0))   # Wand mit 1 mm Luft: Stütze lässt sich von oben einsetzen
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    back, strut = H.backrest()
    strut = taper(strut)
    print(f"Lehne ∩ Stütze: {(back ^ strut).volume():.3f} mm³ | min. Spalt {back.min_gap(strut, 2):.2f} mm")
    notches = notch_positions(back, strut)
    print("Rasten (vorne, Wand):", [(round(f, 1), round(w, 1)) for f, w in notches])
    for (f0, w0), (f1, w1) in zip(notches, notches[1:]):
        print(f"  Steg zwischen zwei Rasten: {(f0 - GROOVE * 0.7) - w1:.1f} mm")
    b = base(notches)
    zb = BT - GROOVE
    floor = H.box(-80, 80, 5, 200, zb - 5, zb)
    for a, (f, w) in zip(ANGLES, notches):
        # Endstellung: Stütze von oben in die Raste gesetzt, Fuß liegt am Rastgrund
        phi = H.solve_phi(back, strut, floor, a)
        B, S = H.place(back, strut, a, phi)
        wall = H.box(-H.SW, H.SW, w, w + 3, zb, BT)
        ok = (S ^ b).volume() < 0.05 and S.min_gap(wall, 5) < 1.5
        # Kippsicherheit: Schwerpunkt von Handy (180 g) + Ständer muss über dem Fuß liegen
        res = []
        for name, (w_, h_, t_, g_) in PHONES.items():
            body, _ = H.device(w_, h_, t_, a)
            cm = H.to_tm(body).center_mass
            tot = g_ + STAND_G
            y = (cm[1] * g_ + (Y_FRONT + LENGTH / 2) * STAND_G) / tot
            back_margin, front_margin = (Y_FRONT + LENGTH) - y, y - Y_FRONT
            res.append(f"{name}: hinten {back_margin:4.0f} / vorne {front_margin:3.0f} mm")
            STAB.append(min(back_margin, front_margin))
        print(f"  {a}°: Stütze {phi:5.1f}° | {'sitzt in der Raste, Wand dahinter' if ok else '!! nicht in der Raste'} | Lehne∩Fuß {(B ^ b).volume():.2f} | Lehne∩Stütze {(B ^ S).volume():.2f}")
        print("        Kipp-Reserve " + " · ".join(res))
    # zusammengeklappt: Lehne flach nach hinten auf dem Fuß, Stütze eingeklappt
    Bf, Sf = H.place(back, strut, 0.0, 0.0)
    pack = Manifold.batch_boolean([b, Bf, Sf], OpType.Add).bounding_box()
    print(f"  zusammengeklappt: Lehne∩Fuß {(Bf ^ b).volume():.2f} mm³ | Paket {pack[3]-pack[0]:.0f} × {pack[4]-pack[1]:.0f} × {pack[5]-pack[2]:.0f} mm")
    one = back + strut
    t1 = H.to_tm(one); check(t1, "mini-lehne-mit-stuetze", (180, 180, 180))
    t1.export(OUT / "pb-handy-staender-mini_druck1_lehne-mit-stuetze.stl")
    t2 = H.to_tm(b); check(t2, "mini-fuss", (180, 180, 180))
    t2.export(OUT / "pb-handy-staender-mini_druck2_fuss.stl")
    return back, strut, b, notches


if __name__ == "__main__":
    main()
