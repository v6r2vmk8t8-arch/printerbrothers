"""PB Handy- & Tablet-Ständer „Z“ – elegante Z-Form mit sichtbarem Scharnier oben.

Teile (2 Drucke, ohne Stützen, ohne Schrauben):
  1. Rahmen (zwei Arme + Ablage + Scharnierrolle oben) mit eingeklapptem Bein – Print-in-Place
     (Kegelzapfen-Scharnier, 45°-Kegel -> druckt liegend ohne Stütze)
  2. Fuß: flache Platte mit Lagerschalen vorne und verdeckter Rastleiste hinten (Gradzahlen)
Benutzung: Rahmen mit den Zapfen in die Lagerschalen legen, Bein nach hinten ausklappen und in die
gewünschte Raste stellen. Zusammengeklappt ist alles flach.

Aufruf:  python3 3d-druck/src/pb_handy_staender_z.py
"""
import sys
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold, OpType, set_circular_segments

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude/skills/stl-designer/scripts"))
sys.path.insert(0, str(Path(__file__).parent))
from stl_tools import check  # noqa: E402
from pb_handy_staender import box, cyl_x, prism_x  # noqa: E402

set_circular_segments(96)
OUT = ROOT / "3d-druck/handy-staender"

# ---------------------------------------------------------------- Maße
T = 8.0            # Dicke Arme / Bein
W = 92.0           # Gesamtbreite Rahmen
AW = 11.0          # Armbreite
GAP = 0.5          # Print-in-Place-Spalt
Y_PIV = 6.0        # Drehzapfen (Fuß) über der Rahmen-Unterkante
LB = 94.0          # Drehzapfen -> Scharnier oben
RB = 6.5           # Radius Scharnierrolle
Y_TOP = Y_PIV + LB
ZB = RB            # Scharnierachse über dem Bett (Rolle liegt auf)
LEG_END = 10.6     # Bein endet hier (über dem Ablage-Steg)
LS = Y_TOP - LEG_END
CONE_R = 3.0       # Kegelzapfen 45°
PIVOT_R = T / 2
PIVOT_L = 5.5
LEDGE_D, LEDGE_T = 13.0, 4.0
CABLE = 18.0
STEP = 0.2         # Kantenrundung in Schichthöhe

BT = 4.0           # Fußplatte
ZP = BT + 7.4      # Drehachse über Bett (Ablage-Steg schwenkt darunter frei)
GROOVE = 2.6
Z_DECK = 21.0      # erhöhter Keil hinten: Rasten liegen oben drauf (Bein reicht so auch für steile Winkel)
DECK_Y0 = 30.0     # Beginn der Keil-Schräge
ANGLES = [45, 52, 59, 66, 73]


def soft(cs, h, r=1.2, z0=0.0, top=True, bottom=False):
    """Profil extrudieren, obere (und/oder untere) Kante in 0.2-mm-Stufen viertelkreisförmig gerundet."""
    n = max(1, int(round(r / STEP)))
    parts = []
    lo, hi = z0, z0 + h
    core_lo = lo + (r if bottom else 0)
    core_hi = hi - (r if top else 0)
    parts.append(Manifold.extrude(cs, core_hi - core_lo).translate((0, 0, core_lo)))
    for k in range(n):
        dz = r * (k + 1) / n
        inset = r - np.sqrt(max(0.0, r ** 2 - (dz - r / n / 2) ** 2))
        c = cs.offset(-inset, JoinType.Round)
        if c.is_empty():
            continue
        if top:
            parts.append(Manifold.extrude(c, r / n + 0.001).translate((0, 0, core_hi + dz - r / n)))
        if bottom:
            parts.append(Manifold.extrude(c, r / n + 0.001).translate((0, 0, core_lo - dz)))
    return Manifold.batch_boolean(parts, OpType.Add)


def rr(x0, x1, y0, y1, r):
    return CrossSection.square((x1 - x0 - 2 * r, y1 - y0 - 2 * r)).translate((x0 + r, y0 + r)).offset(r, JoinType.Round)


def cone_x(r, x_base, direction, y, z):
    """45°-Kegel entlang X: Grundfläche bei x_base, Spitze in Richtung direction (+1/-1)."""
    c = Manifold.cylinder(r, r, 0.0, 64).rotate((0, 90 if direction > 0 else -90, 0))
    return c.translate((x_base, y, z))


# ---------------------------------------------------------------- Rahmen + Bein (Drucklage: Rückseite auf dem Bett)
def frame_and_leg():
    xi = W / 2 - AW                                   # Innenkante Arm
    # Arme + Ablage-Steg unten als ein Profil
    outline = rr(-W / 2, W / 2, 0, Y_TOP, 7.0) - rr(-xi, xi, LEG_END - GAP, Y_TOP + 20, 4.0)
    frame = soft(outline, T, 1.6)
    # Scharnierrolle: äußere Knöchel an den Armen
    for s in (-1, 1):
        x0, x1 = (xi, W / 2) if s > 0 else (-W / 2, -xi)
        frame = frame + cyl_x(RB, x0, x1, Y_TOP, ZB)
        # Kegelzapfen nach innen
        frame = frame + cone_x(CONE_R, s * xi, -s, Y_TOP, ZB)
    frame = frame ^ box(-W, W, -5, Y_TOP + RB + 0.01, 0, 40)
    # Drehzapfen unten außen
    frame = frame + cyl_x(PIVOT_R, -W / 2 - PIVOT_L, W / 2 + PIVOT_L, Y_PIV, T / 2)
    # Ablage (zeigt im Druck nach oben), gerundeter Rand, Kabelschlitz
    z0, z1 = T - 0.01, T + LEDGE_D
    y0 = 0.0
    prof = [(y0, z0), (y0 + LEDGE_T, z0), (y0 + LEDGE_T, z1 - 4.5), (y0 + LEDGE_T + 2.6, z1 - 1.9),
            (y0 + LEDGE_T + 2.6, z1 - 0.8), (y0 + LEDGE_T + 1.8, z1), (y0 + 0.9, z1), (y0, z1 - 0.9)]
    ledge = prism_x(prof, -W / 2 + 2.0, W / 2 - 2.0)
    ledge = ledge + prism_x([(y0 + LEDGE_T - 0.01, z0), (y0 + LEDGE_T + 3.0, z0), (y0 + LEDGE_T - 0.01, z0 + 3.0)],
                            -W / 2 + 2.0, W / 2 - 2.0)               # Hohlkehle
    slot = Manifold.extrude(rr(-CABLE / 2, CABLE / 2, -5, 20, 3.0), 40).translate((0, 0, z0 + 0.02))
    ledge = (ledge - slot) ^ Manifold.extrude(rr(-W / 2 + 2, W / 2 - 2, -5, 30, 4.0), 60).translate((0, 0, -1))
    frame = frame + ledge
    # Bein: Platte mit Fenster, oben Knöchel um die Achse, Kegelsitze
    lx = xi - GAP
    leg_cs = rr(-lx, lx, LEG_END, Y_TOP, 3.0) - rr(-lx + 10, lx - 10, LEG_END + 14, Y_TOP - 16, 6.0)
    leg = soft(leg_cs, T, 1.6) + cyl_x(RB, -lx, lx, Y_TOP, ZB)
    leg = leg ^ box(-W, W, -5, Y_TOP + RB + 0.01, 0, 40)
    for s in (-1, 1):
        leg = leg - cone_x(CONE_R + 0.75, s * xi, -s, Y_TOP, ZB)      # Kegelsitz, 0.4 mm Abstand senkrecht zur Fläche
    # Freiraum Rolle: Rahmen-Arme dürfen das Bein beim Schwenken nicht berühren (Bein ist schmaler -> ok)
    return frame, leg


# ---------------------------------------------------------------- Fuß
def base_part(notches):
    BW = W + 2 * (0.6 + 5.4)
    y_back = max(w for _, w in notches) + 9
    plate = soft(rr(-BW / 2, BW / 2, -16, y_back, 9.0), BT, 1.6)
    xi = W / 2 + 0.6
    for s in (-1, 1):
        x0, x1 = (xi, BW / 2) if s > 0 else (-BW / 2, -xi)
        tower = soft(rr(x0, x1, -9, 9, 2.6), ZP + 4.5, 1.2)
        slot = box(x0 - 1, x1 + 1, -(PIVOT_R + 0.35), PIVOT_R + 0.35, ZP, ZP + 20) + cyl_x(PIVOT_R + 0.35, x0 - 1, x1 + 1, 0, ZP)
        lead = prism_x([(-(PIVOT_R + 0.35), ZP + 3.0), (PIVOT_R + 0.35, ZP + 3.0), (PIVOT_R + 1.8, ZP + 4.55),
                        (-(PIVOT_R + 1.8), ZP + 4.55)], x0 - 1, x1 + 1)
        plate = plate + (tower - slot - lead)
    xr = W / 2 - AW - GAP + 1.5                   # Rasten 1.5 mm breiter als das Bein je Seite
    # Keil: 45°-Schräge vorne, oben flach mit den Rasten, Kanten weich
    y_end = y_back - 0.01
    prof = [(DECK_Y0, BT - 0.01), (DECK_Y0 + (Z_DECK - BT), Z_DECK), (y_end - 6.0, Z_DECK), (y_end, Z_DECK - 6.0), (y_end, BT - 0.01)]
    deck = prism_x(prof, -BW / 2, BW / 2) ^ soft(rr(-BW / 2, BW / 2, -16, y_back, 9.0), Z_DECK + 1, 2.0)
    deck = deck ^ box(-BW, BW, -40, 300, 0, Z_DECK)
    zt, zb = Z_DECK, Z_DECK - GROOVE
    grooves = [prism_x([(f - GROOVE * 0.6, zt + 0.5), (w, zt + 0.5), (w, zb), (f, zb)], -xr, xr) for f, w in notches]
    plate = plate + (deck - Manifold.batch_boolean(grooves, OpType.Add))
    import pb_formel_modellbausatz as FM
    marks = [FM.text_relief(f"{a}°", 4.0, xr + 6.0, (f + w) / 2, Z_DECK - 0.5, 0.6, bold=True) for a, (f, w) in zip(ANGLES, notches)]
    marks.append(FM.text_relief("PRINTER BROTHERS", 4.6, 0, -9.5, BT - 0.5, 0.6, bold=True))
    return plate - Manifold.batch_boolean(marks, OpType.Add)


# ---------------------------------------------------------------- Gebrauchslage / Simulation
def rot_x(m, deg, y, z):
    return m.translate((0, -y, -z)).rotate((deg, 0, 0)).translate((0, y, z))


def place(frame, leg, theta, phi):
    """Rahmen um theta aufstellen (Drehzapfen bei y=0, z=ZP), Bein um phi nach hinten ausklappen."""
    l = rot_x(leg, phi, Y_TOP, ZB)                    # Bein zeigt nach -y -> +phi klappt es zur Rückseite
    out = []
    for m in (frame, l):
        m = m.translate((0, -Y_PIV, -T / 2)).rotate((theta, 0, 0)).translate((0, 0, ZP))
        out.append(m)
    return out


def solve_phi(frame, leg, obstacle, theta):
    """Bein von hinten absenken (Öffnungswinkel verkleinern), bis es das Hindernis berührt."""
    def hits(phi):
        _, l = place(frame, leg, theta, phi)
        return (l ^ obstacle).volume() > 0.02 or l.bounding_box()[2] < 0
    hi = 150.0                                   # weit geöffnet, Fuß hängt hinten in der Luft
    while hi > 0 and not hits(hi - 2):
        hi -= 2
    lo = hi - 2                                  # bei lo berührt es
    for _ in range(14):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if hits(mid) else (lo, mid)
    return hi


def notch_positions(frame, leg):
    zr = Z_DECK - GROOVE
    floor = box(-80, 80, DECK_Y0 + (Z_DECK - BT), 260, zr - 5, zr)
    slab = box(-80, 80, -40, 260, zr - 0.01, Z_DECK + 0.3)
    out = []
    for a in ANGLES:
        phi = solve_phi(frame, leg, floor, a)
        _, l = place(frame, leg, a, phi)
        bb = (l ^ slab).bounding_box()
        out.append((bb[1] - 0.6, bb[4] + 0.35))
    return out


def to_tm(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frame, leg = frame_and_leg()
    print(f"Rahmen ∩ Bein: {(frame ^ leg).volume():.3f} mm³ | min. Spalt {frame.min_gap(leg, 2):.2f} mm")
    sweep = [(p, (rot_x(leg, p, Y_TOP, ZB) ^ frame).volume()) for p in range(0, 121, 10)]
    print("Schwenken:", " ".join(f"{p}°:{v:.1f}" for p, v in sweep))
    notches = notch_positions(frame, leg)
    print("Rasten (vorne, Wand):", [(round(f, 1), round(w, 1)) for f, w in notches])
    base = base_part(notches)
    for a, (f, w) in zip(ANGLES, notches):
        phi = solve_phi(frame, leg, base, a)
        fr, l = place(frame, leg, a, phi)
        hit = (l ^ base.translate((0, 0, 0.15))).bounding_box()
        ok = hit[0] < hit[3] and hit[2] < Z_DECK - GROOVE + 0.3
        print(f"  {a}°: Bein {phi:5.1f}° | {'IN DER RASTE' if ok else '!! NICHT in der Raste'} | "
              f"Rahmen∩Fuß {(fr ^ base).volume():.2f} | Rahmen∩Bein {(fr ^ l).volume():.2f} mm³")
    fl = frame + leg
    t1 = to_tm(fl); check(t1, "rahmen-mit-bein", (180, 180, 180)); print("  Körper:", len(fl.decompose()))
    t1.export(OUT / "pb-handy-staender-z_druck1_rahmen-mit-bein.stl")
    t2 = to_tm(base); check(t2, "fuss", (180, 180, 180))
    t2.export(OUT / "pb-handy-staender-z_druck2_fuss.stl")
    return frame, leg, base, notches


if __name__ == "__main__":
    main()
