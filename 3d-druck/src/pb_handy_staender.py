"""PB Handy- & Tablet-Ständer, Neigung in 5 Stufen verstellbar (40° … 80°).

Zwei Drucke, ohne Stützen, ohne Schrauben:
  1. Rückenlehne mit Ablage und eingebauter Stütze (Print-in-Place-Scharnier, flach gedruckt)
  2. Fuß mit Lagerböcken und Rastleiste (Stufen mit Gradzahlen)
Zusammenbau: Lehne mit ihren seitlichen Zapfen von oben in die Lagerböcke legen, Stütze ausklappen,
in die gewünschte Raste stellen. Zum Mitnehmen: Stütze einklappen, Lehne herausheben – alles flach.

Aufruf:  python3 3d-druck/src/pb_handy_staender.py
"""
import sys
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, Manifold, OpType, set_circular_segments

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude/skills/stl-designer/scripts"))
sys.path.insert(0, str(Path(__file__).parent))
from stl_tools import check  # noqa: E402

set_circular_segments(96)
OUT = ROOT / "3d-druck/handy-staender"

# ---------------------------------------------------------------- Maße
T = 7.0            # Dicke Lehne / Stütze
W = 90.0           # Breite Lehne
LB = 136.0         # Länge Lehne (ab Drehachse)
LH = 55.0          # Abstand Drehachse -> Stützen-Scharnier
LS = 68.0          # Länge Stütze (Scharnier -> Fuß)
SW = 50.0          # Breite Stütze
GAP = 0.5          # Spalt Stütze/Lehne (Print-in-Place)
SWING = 13.0       # Fenster reicht so weit unter das Scharnier (Freiraum beim Ausklappen)
PIN_R, HOLE_R = 1.6, 2.0                     # Scharnierstift / -loch
PIVOT_R = T / 2                              # Drehzapfen der Lehne (liegt auf dem Bett auf)
PIVOT_L = 6.0                                # Zapfenlänge je Seite
LEDGE_D, LEDGE_T, LIP = 13.0, 4.5, 3.5       # Ablage: Tiefe (Gerätedicke), Wandstärke, Rand
CABLE = 16.0       # Kabelschlitz in der Ablage

BT = 4.0           # Fußplatte
BW = W + 2 * (0.6 + 6.4)                     # Fußbreite (Lehne + Spiel + Lagerbock)
ZP = BT + PIVOT_R + 0.9                      # Höhe Drehachse über Bett
Y_FRONT, Y_BACK = -20.0, 112.0
RACK_H, GROOVE = 3.0, 2.5
ANGLES = [40, 50, 60, 70, 80]


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def cyl_x(r, x0, x1, y, z, n=96):
    """Zylinder entlang X."""
    return Manifold.cylinder(x1 - x0, r, r, n).rotate((0, 90, 0)).translate((x0, y, z))


def prism_x(pts_yz, x0, x1):
    """Profil in der (y, z)-Ebene, entlang X extrudiert."""
    cs = CrossSection([pts_yz])
    if cs.area() <= 0:
        cs = CrossSection([pts_yz[::-1]])
    return Manifold.extrude(cs, x1 - x0).rotate((90, 0, 90)).translate((x0, 0, 0))


def teardrop_x(r, x0, x1, y, z):
    """Liegendes Loch mit 45°-Spitze nach oben (druckt ohne Stütze)."""
    c = cyl_x(r, x0, x1, y, z)
    k = r / np.sqrt(2)
    tip = prism_x([(y - k, z + k), (y + k, z + k), (y, z + r * np.sqrt(2))], x0, x1)
    return c + tip


def rrect_xy(x0, x1, y0, y1, r, z0, z1):
    cs = CrossSection.square((x1 - x0 - 2 * r, y1 - y0 - 2 * r)).translate((x0 + r, y0 + r)).offset(r, 1)
    return Manifold.extrude(cs, z1 - z0).translate((0, 0, z0))


# ---------------------------------------------------------------- Lehne + Stütze (Drucklage: Rückseite auf dem Bett)
def backrest():
    zc = T / 2
    plate = rrect_xy(-W / 2, W / 2, -10, LB, 6.0, 0, T) ^ box(-W, W, 0, LB + 1, -1, T + 1)
    plate = plate + cyl_x(PIVOT_R, -W / 2 - PIVOT_L, W / 2 + PIVOT_L, 0, zc)     # Drehzapfen = runde Unterkante
    # Fenster für die Stütze + Griffmulde oben
    yh = LH
    cut = box(-SW / 2 - GAP, SW / 2 + GAP, yh - SWING, yh + LS + GAP, -1, T + 1)   # unter dem Scharnier frei zum Schwenken
    cut = cut + cyl_x(T / 2 + GAP, -SW / 2 - GAP, SW / 2 + GAP, yh, zc)
    cut = cut + Manifold.cylinder(T + 2, 9.0, 9.0, 64).translate((0, yh + LS + GAP, -1))
    plate = plate - cut
    # Ablage vorne (zeigt im Druck nach oben)
    z0, z1 = T - 0.01, T + LEDGE_D
    ledge = prism_x([(0.6, z0), (0.6 + LEDGE_T, z0), (0.6 + LEDGE_T, z1 - LIP - 3.2),
                     (0.6 + LEDGE_T + 3.0, z1 - LIP), (0.6 + LEDGE_T + 3.0, z1), (0.6, z1)], -W / 2, W / 2)
    ledge = ledge + prism_x([(0.6 + LEDGE_T - 0.01, z0), (0.6 + LEDGE_T + 2.5, z0), (0.6 + LEDGE_T - 0.01, z0 + 2.5)],
                            -W / 2, W / 2)                                         # Hohlkehle
    ledge = ledge - box(-CABLE / 2, CABLE / 2, -1, 20, z0 + 0.02, z1 + 1)          # Kabelschlitz
    ledge = ledge ^ rrect_xy(-W / 2, W / 2, -5, 30, 3.0, -1, 40)
    plate = plate + ledge
    # Stütze mit gerundetem Scharnier-Ende
    strut = box(-SW / 2, SW / 2, yh, yh + LS, 0, T) + cyl_x(T / 2, -SW / 2, SW / 2, yh, zc)
    strut = strut - box(-SW, SW, yh - T, yh, -1, T + 1) + cyl_x(T / 2, -SW / 2, SW / 2, yh, zc)
    strut = strut - teardrop_x(HOLE_R, -SW / 2 - 1, -SW / 2 + 4.6, yh, zc) - teardrop_x(HOLE_R, SW / 2 - 4.6, SW / 2 + 1, yh, zc)
    # Stifte aus der Lehne ins Loch der Stütze
    pins = cyl_x(PIN_R, -SW / 2 - GAP - 0.3, -SW / 2 + 4.0, yh, zc) + cyl_x(PIN_R, SW / 2 - 4.0, SW / 2 + GAP + 0.3, yh, zc)
    return plate + pins, strut


# ---------------------------------------------------------------- Fuß
def base_parts(notches):
    plate = rrect_xy(-BW / 2, BW / 2, Y_FRONT, Y_BACK, 8.0, 0, BT)
    plate = plate - Manifold.extrude(CrossSection.square((BW - 34, 16)).translate((-(BW - 34) / 2, 13)).offset(5, 1), BT + 2).translate((0, 0, -1))
    # Lagerböcke mit U-Schlitz von oben
    xi = W / 2 + 0.6
    for s in (-1, 1):
        x0, x1 = (xi, BW / 2) if s > 0 else (-BW / 2, -xi)
        blk = rrect_xy(x0, x1, -11, 11, 2.0, 0, ZP + 6.0)
        slot = box(x0 - 1, x1 + 1, -(PIVOT_R + 0.35), PIVOT_R + 0.35, ZP, ZP + 20) + cyl_x(PIVOT_R + 0.35, x0 - 1, x1 + 1, 0, ZP)
        lead = prism_x([(-(PIVOT_R + 0.35), ZP + 4.5), (PIVOT_R + 0.35, ZP + 4.5), (PIVOT_R + 1.8, ZP + 6.05), (-(PIVOT_R + 1.8), ZP + 6.05)], x0 - 1, x1 + 1)
        plate = plate + (blk - slot - lead)
    # Rastleiste: Sägezahn, senkrechte Wand hinten (Fuß drückt nach hinten)
    xr = SW / 2 + 3
    y0, y1 = min(f for f, _ in notches) - 6, max(w for _, w in notches) + 5
    rack = rrect_xy(-xr, xr, y0, y1, 2.0, BT - 0.01, BT + RACK_H)
    zt, zb = BT + RACK_H, BT + RACK_H - GROOVE
    grooves = [prism_x([(f - GROOVE * 0.6, zt + 0.5), (w, zt + 0.5), (w, zb), (f, zb)], -xr - 1, xr + 1)
               for f, w in notches]
    rack = rack - Manifold.batch_boolean(grooves, OpType.Add)
    plate = plate + rack
    # Gradzahlen + Schriftzug (graviert)
    import pb_formel_modellbausatz as FM
    marks = [FM.text_relief(f"{a}°", 4.2, xr + 6.5, (f + w) / 2, BT - 0.5, 0.6, bold=True).rotate((0, 0, 0)) for a, (f, w) in zip(ANGLES, notches)]
    marks.append(FM.text_relief("PRINTER BROTHERS", 5.0, 0, Y_FRONT + 8.0, BT - 0.5, 0.6, bold=True))
    plate = plate - Manifold.batch_boolean(marks, OpType.Add)
    return plate


# ---------------------------------------------------------------- Gebrauchslage
def rot_x(m, deg, y, z):
    return m.translate((0, -y, -z)).rotate((deg, 0, 0)).translate((0, y, z))


def place(back, strut, theta, phi):
    """Lehne um Winkel theta (Grad, gegen Waagrechte) aufstellen, Stütze um phi (Grad, nach hinten) ausklappen."""
    s = rot_x(strut, -phi, LH, T / 2)                 # Stütze im Lehnen-System zur Rückseite drehen
    b = back.translate((0, 0, -T / 2))
    s = s.translate((0, 0, -T / 2))
    b = b.rotate((theta, 0, 0)).translate((0, 0, ZP))
    s = s.rotate((theta, 0, 0)).translate((0, 0, ZP))
    return b, s


def notch_positions(back, strut):
    """Je Winkel per Simulation: Stütze auf eine Ebene in Rasttiefe stellen. Der Teil der Stütze, der
    dann unter der Zahnoberkante liegt, bestimmt die Raste: vorne Schräge, hinten senkrechte Wand."""
    zr = BT + RACK_H - GROOVE
    floor = box(-80, 80, -40, 200, zr - 5, zr)
    slab = box(-80, 80, -40, 200, zr - 0.01, BT + RACK_H + 0.3)
    out = []
    for a in ANGLES:
        phi = solve_phi(back, strut, floor, a)
        _, s = place(back, strut, a, phi)
        bb = (s ^ slab).bounding_box()
        out.append((bb[1] - 0.6, bb[4] + 0.35))   # (vorderer Rand Raste, Rastwand)
    return out


def solve_phi(back, strut, base, theta):
    """Stütze so weit ausklappen, bis sie die Rastleiste berührt."""
    lo, hi = 0.0, 179.0
    for _ in range(40):
        mid = (lo + hi) / 2
        b, s = place(back, strut, theta, mid)
        if (s ^ base).volume() > 0.02 or s.bounding_box()[2] < 0:
            hi = mid
        else:
            lo = mid
    return lo


def device(w, h, t, theta):
    """Gerät (Handy/Tablet) als Platzhalter für Bilder: steht auf der Ablage, lehnt an der Lehne."""
    y0 = 0.6 + LEDGE_T + 0.3
    body = rrect_xy(-w / 2, w / 2, y0, y0 + h, min(8.0, w / 8), T + 0.3, T + 0.3 + t)
    screen = rrect_xy(-w / 2 + 3, w / 2 - 3, y0 + 3, y0 + h - 3, min(6.0, w / 10), T + 0.3 + t - 0.01, T + 0.3 + t + 0.05)
    out = []
    for m in (body, screen):
        out.append(m.translate((0, 0, -T / 2)).rotate((theta, 0, 0)).translate((0, 0, ZP)))
    return out


def to_tm(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    back, strut = backrest()
    notches = notch_positions(back, strut)
    print("Rasten (vorne, Wand) =", [(round(f, 1), round(w, 1)) for f, w in notches])
    base = base_parts(notches)
    print("== Prüfung Print-in-Place ==")
    print(f"  Lehne ∩ Stütze: {(back ^ strut).volume():.3f} mm³ | min. Spalt {back.min_gap(strut, 2):.2f} mm")
    print("== Gebrauchslage ==")
    for a, (f, d) in zip(ANGLES, notches):
        phi = solve_phi(back, strut, base, a)
        b, s = place(back, strut, a, phi)
        hit = (s ^ base.translate((0, 0, 0.15))).bounding_box()
        cy = (hit[1] + hit[4]) / 2 if hit[0] < hit[3] else float("nan")
        zmin = hit[2] if hit[0] < hit[3] else float("nan")
        in_groove = zmin < BT + RACK_H - GROOVE + 0.3
        print(f"  {a}°: Stütze {phi:5.1f}° ausgeklappt, Fuß bei y={cy:5.1f} (Wand {d:5.1f}) "
              f"{'IN DER RASTE' if in_groove else '!! liegt auf dem Zahn'} | Lehne∩Fuß {(b ^ base).volume():.2f} mm³ | Lehne∩Stütze {(b ^ s).volume():.2f} mm³")
    one = back + strut
    tm = to_tm(one)
    check(tm, "lehne-mit-stuetze", (180, 180, 180))
    print("  Körper:", len(one.decompose()))
    tm.export(OUT / "pb-handy-staender_druck1_lehne-mit-stuetze.stl")
    tb = to_tm(base)
    check(tb, "fuss", (180, 180, 180))
    tb.export(OUT / "pb-handy-staender_druck2_fuss.stl")
    return back, strut, base, notches


if __name__ == "__main__":
    main()
