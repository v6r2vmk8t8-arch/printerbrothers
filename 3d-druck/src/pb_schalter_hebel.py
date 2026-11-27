"""PB Schalter-Hebel im Block-Stil: deckt den ganzen Lichtschalter ab, Hebel schaltet die Wippe.

Teile (Drucke ohne Stützen, für A1 mini):
  0. Montageplatte  flacher Rahmen um den Schalterrahmen, 2 Schrauben in die Wand (verdeckt)
  1. Sockel  99 × 132 × 49 mm (Proportionen 6 × 8 × 3 „Pixel“), Steinmuster vorne, hinten offen,
             wird über Schalter + Montageplatte gestülpt und rastet seitlich ein.
  2. Stab    Holzstab 21 × 21 × 100 mm (2 × 2 × 10 „Pixel“), steht 45° nach oben/unten
  3. Achse   mit Vierkant (wird durch den Stab gesteckt), Exzenter-Scheiben treiben den Mitnehmer
  4. Mitnehmer  kleine Gabel, wird mitten auf die Schalterwippe geklebt (3 Höhen zur Auswahl).
Funktion: Hebel kippen -> Zapfen schiebt die Gabel -> Wippe kippt. Der Schalter rastet selbst ein.

Koordinaten in Gebrauchslage: x waagrecht, y nach oben, z aus der Wand (z = 0 = Vorderseite Schalterrahmen,
Wand bei z = -FRAME_T).
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
# Proportionen wie der Block-Hebel im Spiel (1 Pixel = PX mm): Sockel 6 × 8 × 3 Pixel, Stab 2 × 2 × 10 Pixel, 45° gekippt.
PX = 16.5                      # Sockel deckt den ganzen Efapel-Rahmen (87 × 87 mm) ab; Wippe 57 × 57 mm
FRAME = 85.0                   # Schalterrahmen außen (nachgemessen 85 × 85 mm)
HOLE_CLEAR = 0.8               # Luft je Seite im Loch der Montageplatte (gedruckte Löcher werden ca. 0.2 mm kleiner)
FRAME_T = 10.0                 # Rahmen steht so weit von der Wand ab (Vorderseite Rahmen = z 0)
WALL = 2.4                     # Wandstärke Sockel
BASE_W, BASE_H = 6 * PX, 8 * PX                     # 99 × 132 mm
DEPTH = 3 * PX - FRAME_T                            # Vorderseite bei z = 39.5 (Gesamttiefe ab Wand 49.5 mm)
INNER_W, INNER_H = 60.5, 77.0  # Abstand der inneren Lagerböcke (Achsenlänge) / Freiraum Wippe
FRONT = 3.0                    # Stärke der Vorderwand
ZA = DEPTH - FRONT - 4.5 - 0.7  # Hebelachse knapp hinter der Vorderwand (Stab kommt aus der Mitte)
STICK = 22.0                   # Stab 22 × 22 mm (kräftig, aber nicht riesig)
STICK_L = 110.0                # Stab ab Achse
ROD_R = 4.5                    # Achse im Inneren
PIN_END_R = 2.0                # Lagerzapfen in den Seitenwänden
SLOT_R = 2.25                  # Lagerschlitz (offen nach hinten zur Wand)
ECC_R, ECC_E = 3.4, 3.1        # Exzenter: 3.1 mm außermittig -> ±2.2 mm Hub bei ±45° (Wippe ±4°, Achse jetzt weiter vorne)
ECC_X = (STICK / 2 + 0.3, STICK / 2 + 6.5)
ROCKER_AXIS_Z = -2.0           # angenommene Drehachse der Wippe (hinter der Rahmenfläche)
GAP = 0.4
SWING = 45.0                   # Hebel steht wie im Spiel 45° nach oben oder unten
ROCKER_H = [3.0, 5.0, 7.0]     # Höhe der Wippe über dem Rahmen (Mitte) – Mitnehmer-Varianten


def stones(seed=7):
    """Eigenes Steinblock-Muster (keine Spieltextur): zufällige Blöcke auf einem Halbpixel-Raster."""
    rng = np.random.default_rng(seed)
    cell = PX / 2
    nx, ny = int(round(BASE_W / cell)), int(round(BASE_H / cell))
    taken = np.zeros((ny, nx), bool)
    rects = []
    for j in range(ny):
        for i in range(nx):
            if taken[j, i]:
                continue
            w, h = int(rng.integers(1, 4)), int(rng.integers(1, 3))
            w = min(w, nx - i); h = min(h, ny - j)
            while w > 1 and taken[j, i:i + w].any():
                w -= 1
            taken[j:j + h, i:i + w] = True
            rects.append((i * cell, j * cell, w * cell, h * cell))
    return rects


def base():
    hx, hy = BASE_W / 2, BASE_H / 2
    z0 = -FRAME_T
    ix, iy = hx - WALL, hy - WALL
    shell = box(-hx, hx, -hy, hy, z0, DEPTH) - box(-ix, ix, -iy, iy, z0 - 1, DEPTH - FRONT)
    groove = box(-hx - 1, hx + 1, -hy - 1, hy + 1, DEPTH - 0.8, DEPTH + 1)
    st = []
    for x, y, w, h in stones():
        cs = CrossSection.square((w - 1.0, h - 1.0)).translate((x - hx + 0.5, y - hy + 0.5))
        st.append(Manifold.extrude(cs.offset(-0.4, 1).offset(0.4, 1), 0.81).translate((0, 0, DEPTH - 0.8)))
    shell = shell - groove + (Manifold.batch_boolean(st, OpType.Add) ^ box(-hx, hx, -hy, hy, z0, DEPTH))
    # Öffnung für den Stab (±45°)
    t = np.tan(np.radians(SWING))
    reach = (DEPTH - ZA) * t + STICK / 2 / np.cos(np.radians(SWING)) + 1.5
    shell = shell - box(-STICK / 2 - 0.8, STICK / 2 + 0.8, -reach, reach, DEPTH - FRONT - 1, DEPTH + 1)
    # Lagerböcke innen (hängen an der Vorderwand), Schlitz offen nach hinten, Einraster vor dem Lager
    bx = INNER_W / 2
    for s in (-1, 1):
        x0, x1 = (bx, bx + 3.0) if s > 0 else (-bx - 3.0, -bx)
        rib = box(x0, x1, -9, 9, ZA - 9, DEPTH - FRONT + 0.01)
        slot = box(x0 - 1, x1 + 1, -SLOT_R, SLOT_R, ZA - 10, ZA) + cyl_x(SLOT_R, x0 - 1, x1 + 1, 0, ZA)
        bumps = box(x0, x1, -SLOT_R - 0.1, -1.65, ZA - 3.4, ZA - 2.4) + box(x0, x1, 1.65, SLOT_R + 0.1, ZA - 3.4, ZA - 2.4)
        shell = shell + (rib - slot + bumps)
    # Rastnut innen in den Seitenwänden (greift über die Leiste der Montageplatte)
    zr = z0 + SNAP_Z
    for s in (-1, 1):
        x0, x1 = (ix - 0.01, ix + 0.9) if s > 0 else (-ix - 0.9, -ix + 0.01)
        shell = shell - box(x0, x1, -RAIL_L / 2 - 1, RAIL_L / 2 + 1, zr - 0.2, zr + 1.7)
    return shell


SNAP_Z = 6.0       # Höhe der Rastleiste über der Wand
RAIL_L = 70.0      # Länge der Rastleisten (senkrecht)


TAPE_T = 1.1      # Dicke Montageband (versenkt -> Platte liegt trotzdem plan an der Wand)


def plate(klebe=False):
    """Montageplatte: Ring um den Schalterrahmen, seitliche Rastleisten.
    klebe=False: 2 Senkschrauben oben/unten. klebe=True: versenkte Taschen für Montageband oben/unten."""
    hx, hy = BASE_W / 2 - WALL - 0.25, BASE_H / 2 - WALL - 0.25     # passt mit 0.25 mm Spiel in den Sockel
    z0, t = -FRAME_T, 3.0
    f = FRAME / 2 + HOLE_CLEAR
    p = box(-hx, hx, -hy, hy, z0, z0 + t) - box(-f, f, -f, f, z0 - 1, z0 + t + 1)
    # Seitenleisten (stehen hoch, tragen die Rastnase außen)
    for s in (-1, 1):
        x0, x1 = (hx - 2.2, hx) if s > 0 else (-hx, -hx + 2.2)
        p = p + box(x0, x1, -RAIL_L / 2, RAIL_L / 2, z0, z0 + SNAP_Z + 3.0)
        nx0, nx1 = (hx - 0.01, hx + 0.7) if s > 0 else (-hx - 0.7, -hx + 0.01)
        p = p + box(nx0, nx1, -RAIL_L / 2 + 6, RAIL_L / 2 - 6, z0 + SNAP_Z, z0 + SNAP_Z + 1.4)
    if klebe:
        # Taschen für Montageband auf der Rückseite (TAPE_T tief): Band bündig, Rastleisten bleiben auf Höhe
        for sy in (-1, 1):
            y0, y1 = sorted((sy * (f + 1.0), sy * (hy - 0.8)))
            p = p - box(-hx + 4.0, hx - 4.0, y0, y1, z0 - 1, z0 + TAPE_T)
        return p
    # Senkschrauben oben und unten (Ø 4 mm, Kopf Ø 8)
    for sy in (-1, 1):
        y = sy * (f + (hy - f) / 2)
        hole = Manifold.cylinder(t + 2, 2.2, 2.2, 32).translate((0, y, z0 - 1))
        sink = Manifold.cylinder(2.2, 2.2, 4.3, 32).translate((0, y, z0 + t - 2.2 + 0.01))
        p = p - hole - sink
    return p


SQ = 9.0            # Vierkant der Achse im Stab
KEY = (2.4, 1.3)    # Nase hinten am Vierkant (Breite, Höhe) -> Achse passt nur richtig herum


def axle():
    """Achse mit Vierkant (im Stab), Exzenter-Scheiben links/rechts und Lagerzapfen an den Enden."""
    hx, ix = BASE_W / 2, INNER_W / 2
    # runde Achse nur außerhalb der Exzenter (dort laufen die Zinken des Mitnehmers)
    rod = cyl_x(ROD_R, -(ix - GAP), -ECC_X[1] + 0.01, 0, ZA) + cyl_x(ROD_R, ECC_X[1] - 0.01, ix - GAP, 0, ZA)
    sq = box(-ECC_X[0] - 0.01, ECC_X[0] + 0.01, -SQ / 2, SQ / 2, ZA - SQ / 2, ZA + SQ / 2)
    key = box(-STICK / 2 - 0.01, STICK / 2 + 0.01, -KEY[0] / 2, KEY[0] / 2, ZA - SQ / 2 - KEY[1], ZA - SQ / 2 + 0.01)
    ends = cyl_x(PIN_END_R, -(ix + 2.6), -(ix - GAP) + 0.01, 0, ZA) + cyl_x(PIN_END_R, ix - GAP - 0.01, ix + 2.6, 0, ZA)
    ecc = cyl_x(ECC_R, -ECC_X[1], -ECC_X[0], 0, ZA - ECC_E) + cyl_x(ECC_R, ECC_X[0], ECC_X[1], 0, ZA - ECC_E)
    return rod + sq + key + ends + ecc


def stick_part():
    """Holzstab 2 × 2 × 10 Pixel; Vierkantloch für die Achse (mit Nut für die Nase)."""
    root_back = ZA - SQ / 2 - KEY[1] - 1.8
    st = box(-STICK / 2, STICK / 2, -STICK / 2, STICK / 2, root_back, ZA + STICK_L)
    st = st ^ Manifold.batch_hull([box(-STICK / 2, STICK / 2, -STICK / 2, STICK / 2, root_back, ZA + STICK_L - 1.0),
                                   box(-STICK / 2 + 1.0, STICK / 2 - 1.0, -STICK / 2 + 1.0, STICK / 2 - 1.0, root_back, ZA + STICK_L)])
    c = 0.15        # Presssitz: Loch 0.15 mm größer als der Vierkant
    hole = box(-STICK, STICK, -SQ / 2 - c, SQ / 2 + c, ZA - SQ / 2 - c, ZA + SQ / 2 + c)
    notch = box(-STICK, STICK, -KEY[0] / 2 - c, KEY[0] / 2 + c, ZA - SQ / 2 - KEY[1] - c, ZA - SQ / 2)
    return st - hole - notch


def lever():
    return stick_part() + axle()


def follower(h):
    """Gabel auf der Wippe: zwei Zinkenpaare umfassen die Exzenter-Scheiben links und rechts vom Stab."""
    t = 1.8
    w = ECC_X[1] + 2.5
    plate = box(-w, w, -11, 11, h, h + t)
    top = ZA - ECC_E + 0.6
    tines = []
    for s in (-1, 1):
        x0, x1 = (ECC_X[0] + 0.5, ECC_X[1] - 0.4) if s > 0 else (-ECC_X[1] + 0.4, -ECC_X[0] - 0.5)
        for sy in (-1, 1):
            y0, y1 = (ECC_R + 0.2, ECC_R + 3.2) if sy > 0 else (-ECC_R - 3.2, -ECC_R - 0.2)
            tines.append(box(x0, x1, y0, y1, h + t - 0.01, top))
        # Steg zwischen den Zinken unten (steifer)
        tines.append(box(x0, x1, -ECC_R - 3.2, ECC_R + 3.2, h + t - 0.01, h + t + 3.0))
    return plate + Manifold.batch_boolean(tines, OpType.Add)


def place_lever(lv, alpha):
    """Hebel um alpha (Grad, + = Stab nach oben) um die Achse drehen."""
    return lv.translate((0, 0, -ZA)).rotate((-alpha, 0, 0)).translate((0, 0, ZA))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    b, lv = base(), lever()
    print("== Prüfung ==")
    for a in (-SWING, -20, 0, 20, SWING):
        L = place_lever(lv, a)
        print(f"  Hebel {a:+5.0f}°: Hebel∩Sockel {(L ^ b).volume():.2f} mm³")
    for h in ROCKER_H:
        f = follower(h)
        worst = 0.0
        for a in range(-45, 46, 5):
            L = place_lever(lv, a)
            # Wippe kippt so weit, wie der Exzenter die Gabel seitlich verschiebt
            dy = -ECC_E * np.sin(np.radians(a))      # Scheibe sitzt hinter der Achse -> bewegt sich gegenläufig zum Stab
            beta = np.degrees(np.arctan2(dy, (ZA - ECC_E) - ROCKER_AXIS_Z))
            F = f.translate((0, 0, -ROCKER_AXIS_Z)).rotate((-beta, 0, 0)).translate((0, 0, ROCKER_AXIS_Z))
            worst = max(worst, (L ^ F).volume())
        print(f"  Mitnehmer h={h:.0f} mm: max. Überschneidung über ±45° {worst:.2f} mm³ | Wippe kippt bis ±{abs(beta):.1f}°")
    print(f"  Hub an der Gabel bei ±45°: ±{ECC_E * np.sin(np.radians(45)):.2f} mm")
    print(f"  Stab ∩ Achse (montiert): {(stick_part() ^ axle()).volume():.3f} mm³")
    P = plate()
    frame = box(-FRAME / 2, FRAME / 2, -FRAME / 2, FRAME / 2, -FRAME_T, 0)
    print(f"  Montageplatte ∩ Schalterrahmen: {(P ^ frame).volume():.2f} mm³ | Sockel ∩ Rahmen: {(b ^ frame).volume():.2f} mm³")
    print(f"  Sockel ∩ Montageplatte (Rastnase greift ein, gewollt klein): {(b ^ P).volume():.2f} mm³")
    # Drucklagen
    bp = b.rotate((180, 0, 0)); bp = bp.translate((0, 0, -bp.bounding_box()[2]))           # Vorderseite aufs Bett
    sp = stick_part().rotate((0, 90, 0)); sp = sp.translate((0, 0, -sp.bounding_box()[2]))  # Stab liegt auf der Seite, Loch senkrecht
    ap = axle().translate((0, 0, -ZA)).rotate((180, 0, 0)); ap = ap.translate((0, 0, -ap.bounding_box()[2]))  # Exzenter nach oben
    pl = plate(); pl = pl.translate((0, 0, -pl.bounding_box()[2]))
    pk = plate(klebe=True); pk = pk.translate((0, 0, -pk.bounding_box()[2]))
    yk = BASE_H / 2 - WALL - 0.25 - 0.8 - (FRAME / 2 + HOLE_CLEAR + 1.0)
    print(f"  Klebe-Version: 2 Taschen je {BASE_W - 2 * WALL - 0.5 - 8:.0f} × {yk:.1f} mm, {TAPE_T} mm tief")
    parts = {"montageplatte": pl, "montageplatte-klebe": pk, "sockel": bp, "stab": sp, "achse": ap}
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
