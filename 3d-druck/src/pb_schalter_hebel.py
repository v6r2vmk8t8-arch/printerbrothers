"""PB Schalter-Hebel im Block-Stil: Hebel zum Aufkleben auf einen normalen Wippen-Lichtschalter.

Teile (3 kleine Drucke, ohne Stützen, für A1 mini):
  1. Sockel  66 × 66 × 24 mm, Steinblock-Muster vorne, hinten offen (sitzt über der Wippe),
             wird mit doppelseitigem Klebeband auf den Schalterrahmen geklebt.
  2. Hebel   Holzstab 8 × 8 mm mit Achse; Zapfen hinten greift in den Mitnehmer.
  3. Mitnehmer  kleine Gabel, wird mitten auf die Schalterwippe geklebt (3 Höhen zur Auswahl).
Funktion: Hebel kippen -> Zapfen schiebt die Gabel -> Wippe kippt. Der Schalter rastet selbst ein.

Koordinaten in Gebrauchslage: x waagrecht, y nach oben, z aus der Wand (z = 0 = Vorderseite Schalterrahmen).
Aufruf:  python3 3d-druck/src/pb_schalter_hebel.py
"""
import sys
from pathlib import Path

import numpy as np
from manifold3d import CrossSection, Manifold, OpType, set_circular_segments

sys.path.insert(0, str(Path(__file__).parent))
from pb_handy_staender import box, cyl_x, prism_x, teardrop_x, to_tm  # noqa: E402
from stl_tools import check, preview  # noqa: E402

set_circular_segments(64)
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "3d-druck/schalter-hebel"

# ---------------------------------------------------------------- Maße
OUTER = 66.0        # Sockel außen (passt auf 80er-Rahmen)
INNER = 60.0        # Hohlraum: Wippe bis ca. 58 × 58 mm
DEPTH = 24.0        # Sockeltiefe (z)
FRONT = 3.0         # Stärke der Vorderwand
ZA = 17.0           # Hebelachse (Abstand von der Rahmenfläche)
STICK = 8.0         # Stab-Querschnitt
STICK_L = 50.0      # Stab ab Achse
ROD_R = 4.0         # Achse im Inneren (Ø 8, liegt beim Druck auf dem Bett auf)
PIN_END_R = 2.0     # Lagerzapfen in den Seitenwänden
SLOT_R = 2.25       # Lagerschlitz (offen nach hinten zur Wand)
ECC_R, ECC_E = 3.0, 2.2      # Exzenter-Scheiben: Ø 6, 2.2 mm außermittig -> ±1.1 mm Hub bei ±30°
ECC_X = (4.0, 10.2)          # Lage der Scheiben links/rechts vom Stab
ROCKER_AXIS_Z = -2.0         # angenommene Drehachse der Wippe (hinter der Rahmenfläche)
GAP = 0.4
SWING = 32.0        # max. Ausschlag des Hebels (Schlitz vorne)
ROCKER_H = [3.0, 5.0, 7.0]   # Höhe der Wippe über dem Rahmen (Mitte) – Mitnehmer-Varianten


def stones(seed=7):
    """Eigenes Steinblock-Muster: zufällige Blöcke auf 4-mm-Raster, getrennt durch Fugen."""
    rng = np.random.default_rng(seed)
    n, cell = 16, OUTER / 16
    taken = np.zeros((n, n), bool)
    rects = []
    for j in range(n):
        for i in range(n):
            if taken[j, i]:
                continue
            w, h = int(rng.integers(2, 5)), int(rng.integers(2, 4))
            w = min(w, n - i); h = min(h, n - j)
            while w > 1 and taken[j, i:i + w].any():
                w -= 1
            taken[j:j + h, i:i + w] = True
            rects.append((i * cell, j * cell, w * cell, h * cell))
    return rects


def base():
    hw, ih = OUTER / 2, INNER / 2
    shell = box(-hw, hw, -hw, hw, 0, DEPTH) - box(-ih, ih, -ih, ih, -1, DEPTH - FRONT)
    # Fugen-Muster vorne (0.8 tief): ganze Fläche einsenken, Steine wieder aufsetzen
    groove = box(-hw - 1, hw + 1, -hw - 1, hw + 1, DEPTH - 0.8, DEPTH + 1)
    st = []
    for x, y, w, h in stones():
        x0, y0 = x - hw + 0.45, y - hw + 0.45
        cs = CrossSection.square((w - 0.9, h - 0.9)).translate((x0, y0))
        st.append(Manifold.extrude(cs.offset(-0.3, 1).offset(0.3, 1), 0.81).translate((0, 0, DEPTH - 0.8)))
    shell = shell - groove + (Manifold.batch_boolean(st, OpType.Add) ^ box(-hw, hw, -hw, hw, 0, DEPTH))
    # Schlitz für den Stab vorne
    reach = (DEPTH - ZA) * np.tan(np.radians(SWING)) + STICK / 2 / np.cos(np.radians(SWING)) + 1.0
    shell = shell - box(-STICK / 2 - 0.6, STICK / 2 + 0.6, -reach, reach, DEPTH - FRONT - 1, DEPTH + 1)
    # Lagerschlitze in den Seitenwänden: offen nach hinten (Wand), Einraster kurz vor dem Lager
    for s in (-1, 1):
        x0, x1 = (ih - 0.5, hw + 1) if s > 0 else (-hw - 1, -ih + 0.5)
        slot = box(x0, x1, -SLOT_R, SLOT_R, -1, ZA) + cyl_x(SLOT_R, x0, x1, 0, ZA)
        # Einraster: Schlitz kurz vor dem Lager auf 3.3 mm verengt (Zapfen Ø 4 schnappt durch)
        bumps = (box(x0, x1, -SLOT_R - 0.1, -1.65, ZA - 3.4, ZA - 2.4) + box(x0, x1, 1.65, SLOT_R + 0.1, ZA - 3.4, ZA - 2.4))
        shell = shell - slot + (bumps ^ box(-hw, hw, -hw, hw, 0, DEPTH) ^ box(-hw, hw, -hw, hw, 0, DEPTH) - box(-ih, ih, -ih, ih, -1, DEPTH))
    # Klebeflächen hinten: kleine Fasen innen für leichtes Aufsetzen
    return shell


def lever():
    hw, ih = OUTER / 2, INNER / 2
    root_back = ZA - ROD_R
    stick = box(-STICK / 2, STICK / 2, -STICK / 2, STICK / 2, root_back, ZA + STICK_L)
    # Stab vorne leicht fasen
    stick = stick ^ Manifold.batch_hull([box(-STICK / 2, STICK / 2, -STICK / 2, STICK / 2, root_back, ZA + STICK_L - 0.8),
                                         box(-STICK / 2 + 0.8, STICK / 2 - 0.8, -STICK / 2 + 0.8, STICK / 2 - 0.8, root_back, ZA + STICK_L)])
    rod = cyl_x(ROD_R, -(ih - GAP), -ECC_X[1], 0, ZA) + cyl_x(ROD_R, ECC_X[1], ih - GAP, 0, ZA)
    ends = cyl_x(PIN_END_R, -(hw - 0.6), -(ih - GAP) + 0.01, 0, ZA) + cyl_x(PIN_END_R, ih - GAP - 0.01, hw - 0.6, 0, ZA)
    ecc = cyl_x(ECC_R, -ECC_X[1] - 0.01, -ECC_X[0] + 0.01, 0, ZA - ECC_E) + cyl_x(ECC_R, ECC_X[0] - 0.01, ECC_X[1] + 0.01, 0, ZA - ECC_E)
    return stick + rod + ends + ecc


def follower(h):
    """Gabel auf der Wippe: zwei Zinkenpaare umfassen die Exzenter-Scheiben links und rechts vom Stab."""
    t = 1.6
    plate = box(-11, 11, -11, 11, h, h + t) - box(-4.6, 4.6, -8.8, 8.8, h - 1, h + t + 1)
    top = ZA - ECC_E + 0.6           # knapp über die Scheibenmitte
    tines = []
    for s in (-1, 1):
        x0, x1 = (ECC_X[0] + 0.5, ECC_X[1] - 0.4) if s > 0 else (-ECC_X[1] + 0.4, -ECC_X[0] - 0.5)
        for sy in (-1, 1):
            y0, y1 = (ECC_R + 0.2, ECC_R + 2.6) if sy > 0 else (-ECC_R - 2.6, -ECC_R - 0.2)
            tines.append(box(x0, x1, y0, y1, h + t - 0.01, top))
    return plate + Manifold.batch_boolean(tines, OpType.Add)


def place_lever(lv, alpha):
    """Hebel um alpha (Grad, + = Stab nach oben) um die Achse drehen."""
    return lv.translate((0, 0, -ZA)).rotate((-alpha, 0, 0)).translate((0, 0, ZA))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    b, lv = base(), lever()
    print("== Prüfung ==")
    for a in (-SWING + 2, -15, 0, 15, SWING - 2):
        L = place_lever(lv, a)
        print(f"  Hebel {a:+5.0f}°: Hebel∩Sockel {(L ^ b).volume():.2f} mm³")
    for h in ROCKER_H:
        f = follower(h)
        worst = 0.0
        for a in range(-30, 31, 5):
            L = place_lever(lv, a)
            # Wippe kippt so weit, wie der Exzenter die Gabel seitlich verschiebt
            dy = -ECC_E * np.sin(np.radians(a))      # Scheibe sitzt hinter der Achse -> bewegt sich gegenläufig zum Stab
            beta = np.degrees(np.arctan2(dy, (ZA - ECC_E) - ROCKER_AXIS_Z))
            F = f.translate((0, 0, -ROCKER_AXIS_Z)).rotate((-beta, 0, 0)).translate((0, 0, ROCKER_AXIS_Z))
            worst = max(worst, (L ^ F).volume())
        print(f"  Mitnehmer h={h:.0f} mm: max. Überschneidung über ±30° {worst:.2f} mm³ | Wippe kippt bis ±{abs(beta):.1f}°")
    print(f"  Hub an der Gabel bei ±30°: ±{ECC_E * np.sin(np.radians(30)):.2f} mm")
    # Drucklagen
    bp = b.rotate((180, 0, 0)); bp = bp.translate((0, 0, -bp.bounding_box()[2]))        # Vorderseite aufs Bett
    lp = lv.translate((0, 0, -ZA)).rotate((-90, 0, 0)); lp = lp.translate((0, 0, -lp.bounding_box()[2]))  # Stab liegt flach
    parts = {"sockel": bp, "hebel": lp}
    for h in ROCKER_H:
        parts[f"mitnehmer-{h:.0f}mm"] = follower(h).translate((0, 0, -h))
    for k, m in parts.items():
        tm = to_tm(m)
        check(tm, k, (180, 180, 180))
        print("   Körper:", len(m.decompose()))
        tm.export(OUT / f"pb-schalter-hebel_{k}.stl")
    return b, lv


if __name__ == "__main__":
    main()
