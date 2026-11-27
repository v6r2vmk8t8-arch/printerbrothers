"""Linzer-Keksausstecher „Schneeblüte“ mit Herz-Fenster (Kundenauftrag Dani, nach Foto).

Sechsblättrige Blütenform, geprägte Ornamente (Mandelblatt + zwei Ranken + zwei Ovale je Blatt)
und ein Herz-Ausstecher in der Mitte des Stempels für das Marmeladen-Fenster.

Teile (alle ohne Support):
  - Ausstecher (wie bei den anderen Keksen)
  - Stempel: Platte mit Prägung, in der Mitte eine Herz-Schneide; die Platte ist dort offen,
    damit man das ausgestochene Teig-Herz nach oben herausdrücken kann
  - Griffe: zwei kleine Knäufe, extra gedruckt und in die zwei Mulden links/rechts vom Herz
    auf der Stempel-Rückseite geklebt

Linzer: Unterteile nur mit dem Ausstecher, Oberteile mit Ausstecher + Stempel.
Aufruf:  python3 3d-druck/src/pb_keks_linzer.py
"""
import sys
from pathlib import Path

import numpy as np
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pb_keksausstecher as K  # noqa: E402  (Ausstecher, Helfer, gemeinsame Maße)
from pb_keksausstecher import Manifold, to_cs, to_tm  # noqa: E402,F401
from stl_tools import export_parts, preview  # noqa: E402

# ---------------------------------------------------------------- Parameter
SIZE = 57.0         # Keks von Blattspitze zu Blattspitze
HEART_W = 18.0      # Breite des Herz-Fensters
CUT_H = 6.0         # Herz-Schneide: Höhe über der Platte (Teig bis ca. 4 mm)
CUT_W = 1.0         # Herz-Schneide: Wandstärke unten
CUT_TIP = 0.6       # Herz-Schneide: Wandstärke oben
RELIEF = 1.8        # Höhe der Prägung
LINE = 1.1          # Strichstärke der Ranken
# Griffe: zwei kleine Knäufe (wie bei den anderen Stempeln, nur kleiner) auf zwei gegenüber-
# liegenden Blättern (dort ist am meisten Platz neben der Herz-Schneide)
KNOB_R = 18.5       # Abstand Knauf-Mitte ↔ Keksmitte
KNOB_ANG = 30.0     # Richtung: Blatt rechts oben (+ das gegenüber links unten)
KNOB_FOOT_D = 12.0  # Fuß-Ø
KNOB_NECK_D = 7.0   # Hals-Ø
KNOB_TOP_D = 12.0   # Knauf-Ø oben
KNOB_H = 15.0       # Höhe
POCKET_D = 12.4     # Zentriermulde (0,2 mm Spiel je Seite)
POCKET_T = 0.6      # Tiefe der Mulde


# ---------------------------------------------------------------- Formen
def outline():
    """Sechsblättrige Blüte mit leicht spitzen, gezackten Blattenden (Blatt oben/unten)."""
    R = SIZE / 2
    parts = [Point(0, 0).buffer(R * 0.66, 128)]
    for k in range(6):
        a = 90 + 60 * k
        lobe = [Point(0, R * 0.60).buffer(R * 0.34, 64),              # Blattkörper
                Point(0, R - 2.6).buffer(2.6, 32),                    # Spitze
                Point(-4.4, R * 0.85).buffer(2.6, 32),                # Zacken links
                Point(4.4, R * 0.85).buffer(2.6, 32)]                 # Zacken rechts
        parts.append(affinity.rotate(unary_union(lobe), a - 90, origin=(0, 0)))
    o = unary_union(parts)
    o = o.buffer(1.6, 64).buffer(-1.6, 64)     # Täler rund ausfüllen
    o = o.buffer(-0.6, 64).buffer(0.6, 64)     # Spitzen leicht runden
    k = SIZE / (o.bounds[3] - o.bounds[1])
    return affinity.scale(o, k, k, origin=(0, 0)).simplify(0.01)   # weniger Punkte → kleine STL


def heart_hole():
    h = K.heart(HEART_W)
    return h.buffer(0.6, 64).buffer(-0.6, 64).simplify(0.01)   # Kerbe oben weich (Teig löst sich besser)


def teardrop(length, width):
    """Tropfen längs der y-Achse: unten spitz, oben rund, Mitte bei (0,0)."""
    r = width / 2
    top = Point(0, length / 2 - r).buffer(r, 48)
    return top.union(Point(0, -length / 2).buffer(0.05)).convex_hull.buffer(0.2).buffer(-0.2)


def curl(side):
    """Ranke wie im Foto: beginnt unten an der Mittelachse, schwingt nach oben/außen
    und rollt sich außen nach unten ein (Schnecke außen)."""
    t = np.linspace(0, 1, 60)
    # Stiel: quadratische Kurve vom Fuß an der Achse bis zum Scheitel oben
    p0, p1, p2 = np.array([0.15, 12.8]), np.array([1.6, 19.0]), np.array([4.3, 21.4])
    stem = ((1 - t) ** 2)[:, None] * p0 + (2 * (1 - t) * t)[:, None] * p1 + (t ** 2)[:, None] * p2
    # Schnecke: vom Scheitel nach außen, runter und wieder nach innen, Radius nimmt ab
    cx, cy = 5.0, 19.6
    a0 = np.arctan2(p2[1] - cy, p2[0] - cx)
    a = a0 - np.linspace(0, 1.55 * np.pi, 60)
    r = np.hypot(*(p2 - [cx, cy])) * np.linspace(1, 0.45, 60)
    spiral = np.c_[cx + r * np.cos(a), cy + r * np.sin(a)]
    pts = np.r_[stem, spiral[1:]]
    pts[:, 0] *= side
    line = LineString(pts).buffer(LINE / 2, 16)
    end = Point(*pts[-1]).buffer(LINE * 0.7, 16)
    return unary_union([line, end])


def motif():
    """Ornament für das obere Blatt (Achse = +y): Tropfen oben, zwei Ranken, zwei Ovale."""
    parts = [affinity.translate(teardrop(6.6, 3.0), 0, 22.9)]
    for s in (1, -1):
        parts.append(curl(s))
        ov = affinity.rotate(affinity.scale(Point(0, 0).buffer(1.0, 32), 0.75, 1.2), -s * 20)
        parts.append(affinity.translate(ov, s * 4.6, 15.2))
    return unary_union(parts)


def design():
    m = motif()
    return unary_union([affinity.rotate(m, 60 * k, origin=(0, 0)) for k in range(6)])


# ---------------------------------------------------------------- Teile
def stamp(inner, hole, deco):
    plate_shape = inner.buffer(-K.GAP, 64)
    plate = to_cs(plate_shape.difference(hole)).extrude(K.PLATE)
    rel = to_cs(deco.intersection(plate_shape.buffer(-1.0))).extrude(RELIEF + 0.05).translate((0, 0, K.PLATE - 0.05))
    # Herz-Schneide, Innenseite bündig mit dem Loch, außen schräg zur Spitze
    hcs = to_cs(hole)
    wall = (to_cs(hole.buffer(CUT_W, 64)) - hcs).extrude(CUT_H - 1.5 + 0.05).translate((0, 0, K.PLATE - 0.05))
    n = 8
    for i in range(n):
        w = CUT_W - (CUT_W - CUT_TIP) * (i + 1) / n
        z = K.PLATE + CUT_H - 1.5 + i * 1.5 / n
        wall += (to_cs(hole.buffer(w, 64)) - hcs).extrude(1.5 / n + 0.01).translate((0, 0, z))
    # zwei Zentriermulden für die Griffe auf der Rückseite (= Unterseite beim Druck)
    pockets = None
    for x, y in knob_pos():
        pk = K.CrossSection.circle(POCKET_D / 2).extrude(POCKET_T).translate((x, y, -0.01))
        pockets = pk if pockets is None else pockets + pk
    return plate + rel + wall - pockets


def knob_pos():
    a = np.radians(KNOB_ANG)
    return [(KNOB_R * np.cos(a), KNOB_R * np.sin(a)), (-KNOB_R * np.cos(a), -KNOB_R * np.sin(a))]


def knob():
    """Kleiner Pilz-Knauf, stehend gedruckt, alle Übergänge 45° → ohne Support."""
    rf, rn, rt = KNOB_FOOT_D / 2, KNOB_NECK_D / 2, KNOB_TOP_D / 2
    z1 = 1.6
    z2 = z1 + (rf - rn)
    z4 = KNOB_H - 2.0
    z3 = z4 - (rt - rn)
    prof = [(0, 0), (rf - 0.4, 0), (rf, 0.4), (rf, z1), (rn, z2), (rn, z3), (rt, z4),
            (rt, KNOB_H - 0.8), (rt - 0.8, KNOB_H), (0, KNOB_H)]
    return Manifold.revolve(K.CrossSection([prof]), 96)


if __name__ == "__main__":
    inner, hole, deco = outline(), heart_hole(), design()
    b = inner.bounds
    print(f"Keks: {b[2] - b[0]:.1f} × {b[3] - b[1]:.1f} mm, Herz-Fenster {HEART_W:.0f} mm")
    # Abstände prüfen
    print(f"Prägung ↔ Herz-Schneide: {deco.distance(hole.buffer(CUT_W)):.2f} mm,"
          f" Prägung ↔ Stempelrand: {inner.buffer(-K.GAP).exterior.distance(deco):.2f} mm")

    c, s = K.cutter(inner), stamp(inner, hole, deco)
    g = knob() + knob().translate((KNOB_FOOT_D + 4, 0, 0))     # zwei Griffe
    name, size = "keks-linzer-schneebluete", round(SIZE)
    flip = s.mirror((0, 0, 1)).translate((0, 0, K.PLATE + CUT_H + 0.5))
    z0 = K.PLATE + CUT_H + 0.5 + POCKET_T
    (x1, y1), (x2, y2) = knob_pos()
    # Stempel ist umgedreht (gespiegelt an z) → Lage in x/y bleibt gleich
    knobs = knob().translate((x1, y1, z0)) + knob().translate((x2, y2, z0))
    preview({"ausstecher": to_tm(c.mirror((0, 0, 1)).translate((0, 0, K.H_CUT))), "stempel": to_tm(flip),
             "griff": to_tm(knobs)},
            K.OUT / f"{name}_{size}mm_montiert.png",
            colors={"ausstecher": "#2e9e4f", "stempel": "#e6e6e6", "griff": "#ff7a2f"})
    w = b[2] - b[0] + 2 * (K.WALL + K.FLANGE_W)
    c = c.translate((-w / 2 - 2, 0, 0))
    s = s.translate((w / 2 + 2, 0, 0))
    g = g.translate((-(KNOB_FOOT_D + 4) / 2, -(b[3] - b[1]) / 2 - 12, 0))
    for m, n, k in ((c, "ausstecher", 1), (s, "stempel", 1), (g, "griff", 2)):
        assert len(m.decompose()) == k, f"{n}: falsche Anzahl Teile"
    # Mulden müssen frei von Herz-Schneide und Stempelrand liegen
    for x, y in knob_pos():
        pk = Point(x, y).buffer(POCKET_D / 2)
        print(f"Mulde ({x:+.1f}, {y:+.1f}): Abstand Herz-Schneide {pk.distance(hole.buffer(CUT_W)):.2f} mm,"
              f" Stempelrand {inner.buffer(-K.GAP).exterior.distance(pk):.2f} mm")
    export_parts({"ausstecher": to_tm(c), "stempel": to_tm(s), "griff": to_tm(g)}, K.OUT / f"{name}_{size}mm")
    print(f"Gewicht: Ausstecher {c.volume() / 1000 * 1.24:.1f} g, Stempel {s.volume() / 1000 * 1.24:.1f} g, "
          f"2 Griffe {g.volume() / 1000 * 1.24:.1f} g (PLA)")

    # Keks-Vorschau
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from shapely.plotting import plot_polygon
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    plot_polygon(inner, ax=ax, add_points=False, facecolor="#e8b778", edgecolor="#8a5a2b")
    plot_polygon(deco.intersection(inner.buffer(-K.GAP - 1.0)), ax=ax, add_points=False, facecolor="#a8763c", edgecolor="#6b4420", linewidth=0.4)
    plot_polygon(hole, ax=ax, add_points=False, facecolor="#b3121d", edgecolor="#6b0a10")
    ax.set_aspect("equal"); ax.axis("off"); ax.set_title("Linzer „Schneeblüte“ – so sieht der Keks aus")
    fig.savefig(K.OUT / f"{name}_keks-vorschau.png", dpi=150, bbox_inches="tight")
