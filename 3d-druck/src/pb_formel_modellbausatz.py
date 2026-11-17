"""Printer Brothers Formel-Modellbausatz – klassischer Bausatz zum Heraustrennen und Kleben.

Zwei Spritzlinge (je ein Druck, je eine Farbe), Teile flach gedruckt, mit Angüssen für den
Seitenschneider und Teilenummern am Rahmen:
  Spritzling A (Karosserie): Rumpfhälften, Unterboden, Seitenkästen, Flügel, Pylon, Spiegel, Passstifte
  Spritzling B (Fahrwerk):    Räder, Achsen, Querlenker, Fahrer, Lenkrad, Auspuff, Sockel
Rumpf in linke/rechte Hälfte geteilt (wie bei Flugzeugmodellen), ausgerichtet mit Passstiften.
Räder mit D-Achse und Presssitz – rollen nach dem Zusammenbau.

Aufruf:  python3 3d-druck/src/pb_formel_modellbausatz.py
"""
import sys
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold, Mesh, OpType, set_circular_segments
from shapely.geometry import LineString, Polygon
from shapely.ops import nearest_points, unary_union

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude/skills/stl-designer/scripts"))
from stl_tools import check, preview  # noqa: E402

set_circular_segments(72)
OUT = ROOT / "3d-druck/formel-modellbausatz"

# ---------------------------------------------------------------- Hauptmaße (Fahrlage: x Nase->Heck, y quer, z hoch, Boden z=0)
Z_FLOOR = 3.0            # Unterboden-Unterseite (Bodenfreiheit)
FLOOR_T = 1.2
Z_BODY = Z_FLOOR + FLOOR_T
X_F, X_R = 24.0, 88.0    # Achsen
R_F, W_F = 10.0, 10.0    # Vorderrad Radius / Breite
R_R, W_R = 12.0, 13.0    # Hinterrad
Z_AF, Z_AR = Z_FLOOR + 7.0, Z_FLOOR + 9.0   # Achshöhe = Radradius
R_AX, AX_FLAT = 2.0, 1.5 # D-Achse
BORE = R_AX + 0.45
SPACE = 6.0              # sichtbarer Abstand Rumpf -> Rad (Querlenker)
WHEEL_PRESS = 0.05
SLOT = 1.6 + 0.15        # Schlitze für 1.6-mm-Platten
PL = 1.6                 # Plattenstärke Flügel/Lenker
DOWEL_R = 1.0            # Passstift Ø2.0
DOWEL_HOLE = 1.15        # Loch Ø2.3
POD_IN, POD_OUT = 11.0, 19.5   # Seitenkasten: Innenseite (=Rumpfseite) / Außenkante


def poly(pts):
    cs = CrossSection([pts])
    return cs if cs.area() > 0 else CrossSection([pts[::-1]])


def to_tm(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)


def from_arrays(v, f):
    tm = trimesh.Trimesh(v, f, process=True)
    trimesh.repair.fix_winding(tm)          # einheitliche Orientierung (Kappen + Mantel)
    if tm.volume < 0:
        tm.invert()
    return Manifold(Mesh(vert_properties=np.asarray(tm.vertices, np.float32), tri_verts=np.asarray(tm.faces, np.uint32)))


def loft(stations, n=48, expo=3.2):
    """Lofted Körper aus Querschnitten (x, y-Mitte, halbe Breite, z unten, z oben).
    Querschnitt = Superellipse (abgerundetes Rechteck) – glatte Modellbau-Form."""
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    ex = 2.0 / expo
    rings = []
    for x, yc, hw, zb, zt in stations:
        hh, zc = (zt - zb) / 2, (zt + zb) / 2
        y = yc + hw * np.sign(c) * np.abs(c) ** ex
        z = zc + hh * np.sign(s) * np.abs(s) ** ex
        rings.append(np.stack([np.full(n, x), y, z], 1))
    V = np.vstack(rings)
    F = []
    for i in range(len(rings) - 1):
        a, b = i * n, (i + 1) * n
        for k in range(n):
            k2 = (k + 1) % n
            F += [(a + k, b + k, b + k2), (a + k, b + k2, a + k2)]
    # Endkappen (Fächer um Mittelpunkte)
    for idx, flip in ((0, True), (len(rings) - 1, False)):
        ctr = len(V)
        V = np.vstack([V, rings[idx].mean(0)])
        base = idx * n
        for k in range(n):
            k2 = (k + 1) % n
            F.append((ctr, base + k2, base + k) if flip else (ctr, base + k, base + k2))
    return from_arrays(V, np.array(F))


def interp(table, x):
    xs, vs = zip(*table)
    return float(np.interp(x, xs, vs))


def cyl_y(r, length, x, z, y0=None):
    """Zylinder entlang Y (zentriert, oder ab y0)."""
    m = Manifold.cylinder(length, r, r, 48).rotate((-90, 0, 0))     # entlang +Y, ab y=0
    return m.translate((x, (-length / 2) if y0 is None else y0, z))


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def d_profile(extra=0.0):
    r = R_AX + extra
    return CrossSection.circle(r) ^ CrossSection.square((4 * r, 2 * r)).translate((-2 * r, -AX_FLAT - extra))


# ---------------------------------------------------------------- Rumpf (ganz, dann geteilt)
HW = [(0, 3.0), (6, 5.0), (16, 6.6), (24, 7.8), (34, 10.0), (42, POD_IN), (74, POD_IN), (84, 10.2), (96, 8.0), (106, 6.0)]
ZT = [(0, 7.0), (8, 10.0), (24, 14.5), (34, 16.0), (40, 16.5), (56, 16.5), (62, 17.5), (86, 17.0), (98, 14.0), (106, 11.0)]
COCKPIT = (36.0, 56.0, 5.2, 9.5)   # x0, x1, halbe Breite, Boden-z


def hw_at(x):
    return interp(HW, x)


def body_full():
    st = [(x, 0.0, interp(HW, x), Z_BODY, interp(ZT, x)) for x in np.linspace(0, 106, 54)]
    body = loft(st, n=56, expo=3.4)
    # Airbox / Überrollbügel hinter dem Fahrer
    AZ = [(54, 15.5), (58, 25.0), (66, 24.0), (80, 20.0), (94, 15.0)]
    AW = [(54, 3.0), (58, 4.2), (70, 3.6), (94, 2.4)]
    air = loft([(x, 0.0, interp(AW, x), 12.0, interp(AZ, x)) for x in np.linspace(54, 94, 24)], n=40, expo=2.6)
    body = body + air
    # Lufteinlass vorne in der Airbox
    body = body - box(53.0, 57.5, -2.4, 2.4, 19.0, 23.0)
    # Cockpit
    x0, x1, ch, zf = COCKPIT
    ck = loft([(x, 0.0, ch * min(1, (x - x0 + 0.5) / 4, (x1 - x + 0.5) / 4) ** 0.5, zf, 30) for x in np.linspace(x0, x1, 18)], n=40, expo=3.0)
    body = body - ck
    return body


def body_details(body):
    """Bohrungen, Schlitze, Taschen am ganzen Rumpf (vor dem Teilen)."""
    cuts = []
    # Achsbohrungen
    cuts.append(cyl_y(BORE, 60, X_F, Z_AF))
    cuts.append(cyl_y(BORE, 60, X_R, Z_AR))
    # Frontflügel: Schlitz quer durch die Nasenspitze
    cuts.append(box(0.4, 11.0, -10, 10, Z_BODY + 0.6, Z_BODY + 0.6 + SLOT))
    # Heckflügel-Pylon: Schlitz in der Mitte der Motorabdeckung (je Hälfte halbe Stärke)
    cuts.append(box(93.0, 103.5, -SLOT / 2, SLOT / 2, 9.0, 30))
    # Auspuff-Loch im Heck
    cuts.append(Manifold.cylinder(3.0, 1.75, 1.75, 32).rotate((0, 90, 0)).translate((103.6, 0, 9.5)))
    # Querlenker-Taschen (oben/unten) seitlich, vorne + hinten
    for x, za, sgn in ((X_F, Z_AF, 1), (X_F, Z_AF, -1), (X_R, Z_AR, 1), (X_R, Z_AR, -1)):
        hw = hw_at(x)
        for dz in (+3.6, -3.6):
            z = za + dz
            cuts.append(box(x - 5.2, x + 5.2, sgn * (hw - 3.0) - (3.5 if sgn < 0 else 0), sgn * (hw - 3.0) + (3.5 if sgn > 0 else 0),
                            z - SLOT / 2, z + SLOT / 2))
    # Passstift-Löcher Rumpfhälften (auf der Teilungsebene)
    for x, z in ((14, 8.0), (46, 7.0), (78, 9.0), (100, 9.0)):
        cuts.append(cyl_y(DOWEL_HOLE, 6.2, x, z))
    # Unterboden-Zapfen (senkrecht von unten)
    for x in (18.0, 62.0, 96.0):
        for sy in (-1, 1):
            cuts.append(Manifold.cylinder(3.2, DOWEL_HOLE, DOWEL_HOLE, 32).translate((x, sy * 3.2, Z_BODY - 0.01)))
    # Seitenkasten-Passstifte (in der Rumpfseite)
    for x in (50.0, 66.0):
        for sy in (-1, 1):
            cuts.append(cyl_y(DOWEL_HOLE, 3.2, x, 9.0, y0=(POD_IN - 3.1) if sy > 0 else -POD_IN - 0.1))
    return body - Manifold.batch_boolean(cuts, OpType.Add)


def body_halves():
    b = body_details(body_full())
    left = b ^ box(-10, 120, -40, 0, -10, 40)
    right = b ^ box(-10, 120, 0, 40, -10, 40)
    return left, right


# ---------------------------------------------------------------- Unterboden, Seitenkästen
def floor():
    pts_top = [(4, 3.5), (16, 6.6), (34, 10.0), (40, POD_OUT - 1.0), (74, POD_OUT - 1.0), (80, 10.2), (100, 8.0), (104, 6.5)]
    pl = poly([(x, y) for x, y in pts_top] + [(x, -y) for x, y in reversed(pts_top)])
    pl = pl.offset(-0.8, JoinType.Round).offset(0.8, JoinType.Round)
    f = Manifold.extrude(pl, FLOOR_T).translate((0, 0, Z_FLOOR))
    # Zapfen in den Rumpf
    for x in (18.0, 62.0, 96.0):
        for sy in (-1, 1):
            f = f + Manifold.cylinder(3.0, DOWEL_R, DOWEL_R, 32).translate((x, sy * 3.2, Z_BODY - 0.01))
    # Diffusor-Andeutung: Rillen hinten
    for k in range(5):
        y = -6 + 3 * k
        f = f - box(92, 104.5, y - 0.4, y + 0.4, Z_BODY - 0.4, Z_BODY + 0.1)
    return f


def sidepod(sgn):
    """Seitenkasten; Innenseite liegt an der Rumpfseite (y = ±POD_IN)."""
    def st(x):
        k = (x - 42) / 32
        zt = 13.5 - 2.5 * k
        w = (POD_OUT - POD_IN) * (0.75 + 0.25 * min(1, (x - 42) / 6)) * (1 - 0.35 * max(0, k - 0.6) / 0.4)
        return (x, sgn * (POD_IN + w / 2), w / 2, Z_BODY, zt)
    pod = loft([st(x) for x in np.linspace(42, 74, 20)], n=48, expo=3.0)
    pod = pod ^ box(30, 90, -40, 40, Z_BODY, 40)
    # Kühler-Einlass vorne
    pod = pod - box(41.0, 44.5, sgn * POD_IN + (1.2 if sgn > 0 else -POD_OUT + POD_IN + 1.2) * 1, sgn * POD_IN + (POD_OUT - POD_IN - 1.2) * (1 if sgn > 0 else -1), Z_BODY + 1.5, 11.5) \
        if False else pod - box(41.0, 44.5, min(sgn * (POD_IN + 1.2), sgn * (POD_OUT - 1.2)), max(sgn * (POD_IN + 1.2), sgn * (POD_OUT - 1.2)), Z_BODY + 1.5, 11.0)
    # Innenseite plan (klebt am Rumpf) + Passstift-Löcher
    pod = pod ^ (box(30, 90, POD_IN, 40, -10, 40) if sgn > 0 else box(30, 90, -40, -POD_IN, -10, 40))
    for x in (50.0, 66.0):
        pod = pod - cyl_y(DOWEL_HOLE, 3.2, x, 9.0, y0=POD_IN - 0.1 if sgn > 0 else -POD_IN - 3.1)
    return pod


# ---------------------------------------------------------------- Flügel
def plate_xy(points, t=PL):
    return Manifold.extrude(poly(points), t)


def front_wing_main():
    span = 24.0
    return plate_xy([(0, -span), (0, span), (9.6, span), (10.2, span - 1), (10.2, -span + 1), (9.6, -span)])


def front_wing_flap():
    """Eine Flap-Hälfte (rechts; links = um X gedreht/gespiegelt verbaut). Innen frei für die Nase."""
    return plate_xy([(0, 6.2), (0, 21.5), (4.5, 21.5), (4.5, 6.2)])


def endplate_front():
    """Endplatte (liegend gedruckt): x Länge, y = Höhe im Auto; Schlitze für Hauptblatt + Flap."""
    ep = plate_xy([(0, 0), (12.5, 0), (12.5, 6.0), (8.0, 9.5), (0, 9.5)], t=1.4)
    ep = ep - box(1.0, 11.4, 1.0, 1.0 + SLOT, -1, 3)           # Hauptblatt
    ep = ep - box(6.6, 11.6, 3.6, 3.6 + SLOT, -1, 3)           # Flap
    return ep


def rear_wing_main():
    return plate_xy([(0, -13.5), (0, 13.5), (12.0, 13.5), (12.0, -13.5)]) - box(2.6, 9.0, -0.85, 0.85, -1, 3)  # Pylon-Schlitz


def rear_wing_flap():
    return plate_xy([(0, -13.5), (0, 13.5), (6.0, 13.5), (6.0, -13.5)])


def endplate_rear():
    ep = plate_xy([(0, 0), (17.0, 0), (17.0, 13.0), (2.0, 13.0), (0, 10.0)], t=1.4)
    ep = ep - box(2.0, 14.4, 4.0, 4.0 + SLOT, -1, 3)
    ep = ep - box(9.0, 15.4, 8.0, 8.0 + SLOT, -1, 3)
    return ep


def pylon():
    """Heckflügel-Pylon: unten Lasche in den Rumpfschlitz, oben Lasche durch das Hauptblatt."""
    return plate_xy([(0, 0), (10.4, 0), (10.4, 9.0), (8.0, 9.0), (7.2, 13.0), (8.6, 13.0), (8.6, 14.8),
                     (2.8, 14.8), (2.8, 13.0), (4.2, 13.0), (3.4, 9.0), (0, 9.0)])


# ---------------------------------------------------------------- Fahrwerk
def axle(length):
    core = Manifold.extrude(d_profile(), length - 0.6).translate((0, 0, 0.3))
    tip = Manifold.extrude(d_profile(-0.3), 0.31)
    return Manifold.batch_hull([core, tip]) + Manifold.batch_hull([core, tip.translate((0, 0, length - 0.31))])


def wheel(r, w):
    """Rad mit Profilrillen und 5-Speichen-Felge (Außenseite oben, d.h. z=w ist außen)."""
    prof = [(0, 0), (r - 0.5, 0), (r, 0.5), (r, w - 0.5), (r - 0.5, w), (0, w)]
    wh = Manifold.revolve(poly(prof), 96)
    for k in range(3):                                         # Profilrillen
        z = w * (k + 1) / 4
        wh = wh - Manifold.revolve(poly([(r - 0.5, z - 0.35), (r + 1, z - 0.35), (r + 1, z + 0.35), (r - 0.5, z + 0.35)]), 96)
    rim_r = r * 0.62
    wh = wh - Manifold.revolve(poly([(0, w - 1.6), (rim_r, w - 1.6), (rim_r + 1.6, w + 1), (0, w + 1)]), 96)  # Felgenschüssel
    spokes = []
    for k in range(5):
        a = 72 * k
        sp = box(0, rim_r + 0.2, -0.9, 0.9, w - 1.7, w - 0.4).rotate((0, 0, a))
        spokes.append(sp)
    wh = wh + Manifold.batch_boolean(spokes, OpType.Add) + Manifold.cylinder(1.3, 3.2, 3.2, 48).translate((0, 0, w - 1.7))
    hole = Manifold.extrude(d_profile(WHEEL_PRESS), w + 2).translate((0, 0, -1))
    lead = Manifold.extrude(d_profile(WHEEL_PRESS + 0.3), 0.31).translate((0, 0, -0.01))  # Einführung innen (z=0)
    return wh - hole - lead


def axle_len(x, w):
    return 2 * (hw_at(x) + SPACE + w) - 0.6


def wishbone(x_axle, length):
    """V-Querlenker (flach): Fuß 10.4 breit (steckt 3 mm in der Rumpftasche), Spitze am Radträger."""
    root = 3.0
    pts = [(-5.0, 0), (5.0, 0), (5.0, root), (1.0, length), (-1.0, length), (-5.0, root)]
    v = plate_xy(pts)
    inner = poly([(-2.6, root + 0.8), (2.6, root + 0.8), (0, length - 3.0)])
    v = v - Manifold.extrude(inner, PL + 2).translate((0, 0, -1))
    return v


def driver():
    """Fahrer: Schultern + Helm mit Visier, flacher Boden (sitzt im Cockpit)."""
    torso = loft([(x, 0.0, 4.0 - 0.22 * x, 0.0, 4.5 - 0.1 * x) for x in np.linspace(0, 6, 6)], n=32, expo=2.6)
    helmet = Manifold.sphere(3.3, 48).scale((1.15, 1.0, 1.05)).translate((3.2, 0, 6.8))
    neck = Manifold.cylinder(3.0, 1.6, 1.6, 32).translate((3.2, 0, 3.5))
    visor = box(5.4, 9, -2.6, 2.6, 6.6, 7.9)
    d = torso + neck + helmet - visor
    return d ^ box(-10, 20, -10, 10, 0, 20)


def steering_wheel():
    sw = Manifold.cylinder(1.2, 3.4, 3.4, 48) - Manifold.cylinder(3, 2.2, 2.2, 48).translate((0, 0, -1))
    sw = sw + box(-3.0, 3.0, -0.5, 0.5, 0, 1.2) + box(-0.5, 0.5, -3.0, 0, 0, 1.2)
    return sw + box(-0.7, 0.7, -0.7, 0.7, 0, 1.2) + Manifold.cylinder(1.2, 0.9, 0.9, 24)


def mirror(sgn):
    return plate_xy([(0, 0), (1.2, 0), (1.2, 4.0), (3.4, 4.6), (3.4, 6.8), (-0.6, 6.8), (-0.6, 4.6), (0, 4.0)], t=1.2)


def exhaust():
    e = Manifold.extrude(CrossSection.circle(1.6) ^ CrossSection.square((4, 3.2)).translate((-2, -1.2)), 9.0)
    return e - Manifold.cylinder(5, 0.9, 0.9, 24).translate((0, 0.2, 4.5))


def dowel(length=6.0):
    return Manifold.extrude(CrossSection.circle(DOWEL_R) ^ CrossSection.square((3, 2)).translate((-1.5, -0.85)), length)


def stand():
    """Präsentationssockel mit Radmulden und erhabener Schrift."""
    base = Manifold.extrude(CrossSection.square((122, 62)).translate((-61, -31)).offset(-4, JoinType.Round).offset(4, JoinType.Round), 4.0)
    base = base - Manifold.extrude(CrossSection.square((114, 54)).translate((-57, -27)).offset(-3, JoinType.Round).offset(3, JoinType.Round), 2).translate((0, 0, 3.4))
    for x, y_in, w, r in ((X_F - 53, hw_at(X_F) + SPACE, W_F, R_F), (X_R - 53, hw_at(X_R) + SPACE, W_R, R_R)):
        for sg in (-1, 1):
            yc = sg * (y_in + w / 2)
            base = base - box(x - r * 0.55, x + r * 0.55, yc - w / 2 - 0.4, yc + w / 2 + 0.4, 3.0, 5)
    base = base + text_relief("PRINTER BROTHERS", 5.0, 0, -23.0, 3.39) + text_relief("FORMEL PB", 3.6, 0, 24.0, 3.39)
    return base


def text_relief(s, size, x, y, z, h=0.8, bold=False):
    from build123d import Align, BuildPart, BuildSketch, FontStyle, Text, extrude
    with BuildPart() as bp:
        with BuildSketch():
            Text(s, size, font_style=FontStyle.BOLD if bold else FontStyle.REGULAR, align=(Align.CENTER, Align.CENTER))
        extrude(amount=h)
    v, f = bp.part.tessellate(0.02, 0.2)
    m = from_arrays(np.array([[p.X, p.Y, p.Z] for p in v]), np.array(f))
    return m.translate((x, y, z))


# ---------------------------------------------------------------- Zusammenbau (Fahrlage)
def assembled():
    L, R = body_halves()
    parts = {"A1 Rumpf links": L, "A2 Rumpf rechts": R, "A3 Unterboden": floor(),
             "A4 Seitenkasten links": sidepod(-1), "A5 Seitenkasten rechts": sidepod(1)}
    zf = Z_BODY + 0.6 + 0.08
    parts["A6 Frontflügel"] = front_wing_main().translate((0.6, 0, zf))
    parts["A7 Front-Flap rechts"] = front_wing_flap().translate((6.2, 0, zf + PL + 0.7))
    parts["A7 Front-Flap links"] = front_wing_flap().mirror((0, 1, 0)).translate((6.2, 0, zf + PL + 0.7))
    for nm, sg in (("A8 Endplatte vorne links", -1), ("A9 Endplatte vorne rechts", 1)):
        ep = endplate_front().rotate((90, 0, 0))                # Platte steht senkrecht (x-z)
        parts[nm] = ep.translate((-0.7, sg * 24.0 + (0.7 if sg > 0 else -0.7) + (-0.7 if sg > 0 else 0.7) * 0 , zf - 1.0 - 0.08))
    x_rw, z_rw = 92.9, 9.05 + 13.0
    parts["A10 Heckflügel"] = rear_wing_main().translate((x_rw, 0, z_rw))
    parts["A11 Heck-Flap"] = rear_wing_flap().translate((x_rw + 7.0, 0, z_rw + 4.0))
    for nm, sg in (("A12 Endplatte hinten links", -1), ("A13 Endplatte hinten rechts", 1)):
        parts[nm] = endplate_rear().rotate((90, 0, 0)).translate((x_rw - 2.0, sg * 13.5 + (1.4 if sg > 0 else 0), z_rw - 4.0 - 0.08))
    parts["A14 Pylon"] = pylon().rotate((90, 0, 0)).translate((93.0, PL / 2, 9.05))
    parts["A15 Spiegel links"] = mirror(-1).rotate((90, 0, 0)).translate((40.0, -9.0 + 0.6, 15.8))
    parts["A16 Spiegel rechts"] = mirror(1).rotate((90, 0, 0)).translate((40.0, 9.0 + 0.6, 15.8))
    for nm, x, w, r, za in (("hinten", X_R, W_R, R_R, Z_AR), ("vorne", X_F, W_F, R_F, Z_AF)):
        La = axle_len(x, w)
        parts[f"B Achse {nm}"] = axle(La).translate((0, 0, -La / 2)).rotate((90, 0, 0)).translate((x, 0, za))
        y_in = hw_at(x) + SPACE
        wr = wheel(r, w).rotate((-90, 0, 0)).translate((x, y_in, za))                 # außen bei +y
        wl = wheel(r, w).rotate((-90, 0, 0)).rotate((0, 0, 180)).translate((x, -y_in, za))
        parts[f"B Räder {nm}"] = wr + wl
        hw = hw_at(x)
        Lw = SPACE + 3.0 - 1.0
        for dz in (3.6, -3.6):
            for sg in (-1, 1):
                wb = wishbone(x, Lw).translate((0, 0, -PL / 2))
                wb = wb if sg > 0 else wb.rotate((0, 0, 180))
                parts[f"B Querlenker {nm} {'o' if dz > 0 else 'u'}{sg}"] = wb.translate((x, sg * (hw - 3.0), za + dz))
    parts["B Fahrer"] = driver().mirror((1, 0, 0)).translate((48.5, 0, COCKPIT[3]))   # Blick nach vorne (-x)
    parts["B Lenkrad"] = steering_wheel().rotate((0, 70, 0)).translate((39.6, 0, 13.0))
    parts["B Auspuff"] = exhaust().rotate((0, 90, 0)).translate((104.0, 0, 9.5 + 0.0))
    return parts


# ---------------------------------------------------------------- Spritzlinge
def footprint(m):
    sec = m.slice(0.3)
    polys = [Polygon(p) for p in sec.to_polygons() if len(p) >= 3]
    return unary_union([p.buffer(0) for p in polys])


def flat(m):
    bb = m.bounding_box()
    return m.translate((-bb[0], -bb[1], -bb[2]))


def place(m, x, y, rot=0.0):
    m = flat(m.rotate((0, 0, rot)))
    bb = m.bounding_box()
    return m.translate((x - bb[3] / 2, y - bb[4] / 2, 0))


TAG_R = 5.0   # Nummernschild-Radius am Läufer


def sprue(parts, W, H, runners, label):
    """parts: [(Manifold, 'A1')]; runners: Liste von Linien [(x0,y0),(x1,y1)] zusätzlich zum Rahmen."""
    BAR, BH = 3.0, 2.2
    frame = CrossSection.square((W, H)) - CrossSection.square((W - 2 * BAR, H - 2 * BAR)).translate((BAR, BAR))
    lines = [LineString([(BAR / 2, BAR / 2), (W - BAR / 2, BAR / 2), (W - BAR / 2, H - BAR / 2), (BAR / 2, H - BAR / 2), (BAR / 2, BAR / 2)])]
    grid = frame
    for (x0, y0), (x1, y1) in runners:
        ln = LineString([(x0, y0), (x1, y1)])
        lines.append(ln)
        grid = grid + poly([tuple(c) for c in list(ln.buffer(1.4, cap_style=2).exterior.coords)[:-1]])   # Drehrichtung egal
    grid_m = Manifold.extrude(grid.offset(-0.5, JoinType.Round).offset(0.5, JoinType.Round), BH)
    # Rahmenschild mit Bezeichnung (oben links auf dem Rahmen)
    tag = Manifold.extrude(CrossSection.square((46, 9)).offset(0, JoinType.Round), BH).translate((6, H - 10.5, 0))
    grid_m = grid_m + tag + text_relief(label, 4.2, 29, H - 6.0, BH - 0.01, 0.7)
    gates, tags, fps = [], [], {}
    allfp = unary_union([footprint(m) for m, _ in parts])
    for m, nr in parts:
        fp = footprint(m)
        fps[nr] = fp
        cands = sorted(((fp.distance(ln),) + tuple(nearest_points(fp, ln)) + (ln,) for ln in lines), key=lambda c: c[0])
        used = 0
        for d, pp, pr, ln in cands:
            if d > 26 or used >= 2:
                continue
            seg = LineString([pp, pr])
            others = allfp.difference(fp.buffer(0.01))
            if seg.buffer(0.8).intersects(others):
                continue
            v = np.array([pr.x - pp.x, pr.y - pp.y]); n = np.linalg.norm(v)
            if n < 0.5:
                continue
            u = v / n; perp = np.array([-u[1], u[0]])
            a = np.array([pp.x, pp.y]) - u * 0.3
            b = np.array([pr.x, pr.y]) + u * 1.0
            quad = [a + perp * 0.4, a - perp * 0.4, b - perp * 0.75, b + perp * 0.75]
            gates.append(Manifold.extrude(poly([tuple(q) for q in quad]), 0.9))
            used += 1
            if used == 1:
                s0 = ln.project(pr)
                for off in (7.0, -7.0, 10.0, -10.0, 13.0, -13.0, 16.0, -16.0, 20.0, -20.0, 0.0):
                    q = ln.interpolate(min(max(s0 + off, 2), ln.length - 2))
                    if allfp.distance(q) > TAG_R + 0.9 and all(np.hypot(q.x - tx, q.y - ty) > 2 * TAG_R + 1.5 for _, tx, ty in tags):
                        tags.append((nr, q.x, q.y)); break
        if used == 0:
            print(f"  !! {nr}: kein Anguss möglich")
    tag_m = []
    for nr, x, y in tags:
        # Nummernschild: flache Scheibe, Nummer fett und 0.8 mm erhaben (lesbar mit 0.4er Düse)
        # Scheibe so hoch wie der Läufer, Nummer liegt OBEN drauf (sonst verdeckt der Läufer sie)
        tag_m.append(Manifold.cylinder(BH, TAG_R, TAG_R, 48).translate((x, y, 0))
                     + text_relief(nr, 5.0 if len(nr) < 3 else 4.3, x, y, BH - 0.01, 0.8, bold=True))
    grid_m = grid_m + Manifold.batch_boolean(tag_m, OpType.Add)
    missing = sorted({nr for _, nr in parts} - {nr for nr, _, _ in tags})
    if missing:
        print("  !! ohne Nummernschild:", missing)
    return grid_m, Manifold.batch_boolean(gates, OpType.Add), tags


# Druckausrichtung der Teile (alle flach auf z=0)
T_LEFT = [[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0]]     # z' = -y : linke Hälfte, Teilungsebene nach unten
T_RIGHT = [[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0]]    # z' = +y : rechte Hälfte


def kit_A():
    L, R = body_halves()
    parts = [("A1", L.transform(T_LEFT)), ("A2", R.transform(T_RIGHT)), ("A3", floor()),
             ("A4", sidepod(-1).transform(T_LEFT)), ("A5", sidepod(1).transform(T_RIGHT)),
             ("A6", front_wing_main()), ("A7", front_wing_flap()), ("A7", front_wing_flap()),
             ("A8", endplate_front()), ("A8", endplate_front()),
             ("A9", rear_wing_main()), ("A10", rear_wing_flap()),
             ("A11", endplate_rear()), ("A11", endplate_rear()), ("A12", pylon()),
             ("A13", mirror(1)), ("A13", mirror(1))]
    parts += [("A14", dowel(6.0).rotate((90, 0, 0))) for _ in range(8)]   # liegend, Abflachung unten      # 4 Rumpf + 4 Seitenkästen
    return parts


def kit_B():
    Lw = SPACE + 3.0 - 1.0
    parts = [("B1", wheel(R_R, W_R)), ("B1", wheel(R_R, W_R)), ("B2", wheel(R_F, W_F)), ("B2", wheel(R_F, W_F)),
             ("B3", axle(axle_len(X_R, W_R)).rotate((0, 90, 0)).rotate((90, 0, 0))),
             ("B4", axle(axle_len(X_F, W_F)).rotate((0, 90, 0)).rotate((90, 0, 0)))]
    parts += [("B5", wishbone(X_F, Lw)) for _ in range(8)]
    parts += [("B6", driver()), ("B7", steering_wheel()), ("B8", exhaust()), ("B9", stand())]
    return parts


def pack(parts, W, H, gap=5.5, bar=3.0):
    """Regal-Packung: Teile (liegend, längste Seite waagrecht) in Reihen, zwischen den Reihen ein Läufer."""
    items = []
    for nr, m in parts:
        m = flat(m)
        bb = m.bounding_box()
        if bb[4] - bb[1] > bb[3] - bb[0] + 0.01:
            m = flat(m.rotate((0, 0, 90)))
        bb = m.bounding_box()
        items.append((nr, m, bb[3] - bb[0], bb[4] - bb[1]))
    items.sort(key=lambda t: -t[3])
    placed, runners = [], []
    y = bar + gap
    x0 = bar + gap
    while items:
        row, x, rh = [], x0, 0.0
        for it in list(items):
            if x + it[2] <= W - bar - gap:
                row.append((it, x)); x += it[2] + gap; rh = max(rh, it[3]); items.remove(it)
        if not row:
            raise RuntimeError("Teil zu breit für den Rahmen")
        for (nr, m, w, h), xx in row:
            placed.append((m.translate((xx, y + (rh - h) / 2, 0)), nr))
        y += rh + gap
        if items:
            runners.append(((bar, y + 1.4), (W - bar, y + 1.4)))
            y += 2.8 + gap
    if y > H - bar - 9:
        raise RuntimeError(f"Rahmen zu niedrig: brauche {y + bar + 9:.0f} mm")
    return placed, runners, y


SPRUE_TAGS = {}


def build_sprue(kind):
    W = 172.0 if kind == "A" else 168.0
    parts = kit_A() if kind == "A" else kit_B()
    placed, runners, used_h = pack(parts, W, 176.0, gap=5.0 if kind == "A" else 5.5)
    H = used_h + 3.0 + 12.0
    label = "A  KAROSSERIE" if kind == "A" else "B  FAHRWERK"
    grid, gates, tags = sprue(placed, W, H, runners, label)
    SPRUE_TAGS[kind] = tags
    allp = Manifold.batch_boolean([m for m, _ in placed], OpType.Add)
    touch = (allp ^ grid).volume()
    plate = Manifold.batch_boolean([allp, grid, gates], OpType.Add)
    return plate, placed, touch, W, H


def assembly_check(P):
    names = list(P)
    rolling = [n for n in names if n.startswith("B Räder")]
    statics = [n for n in names if not n.startswith("B Räder") and not n.startswith("B Achse")]
    stat = Manifold.batch_boolean([P[n] for n in statics], OpType.Add)
    ok = True
    for n in rolling + [n for n in names if n.startswith("B Achse")]:
        v = (P[n] ^ stat).volume(); g = P[n].min_gap(stat, 3.0)
        good = v < 1e-3 and g >= 0.3; ok &= good
        print(f"  {n:22s}: Überschneidung {v:7.3f} mm³, min. Spalt {g:.2f} mm  {'OK' if good else '!!'}")
    worst = []
    for i, a in enumerate(statics):
        for b in statics[i + 1:]:
            v = (P[a] ^ P[b]).volume()
            if v > 0.5:
                worst.append((v, a, b))
    for v, a, b in sorted(worst, reverse=True)[:8]:
        print(f"  !! {a} ∩ {b}: {v:.1f} mm³"); ok = False
    if not worst:
        print("  statische Teile: keine Überschneidungen (> 0.5 mm³)")
    return ok


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("== Zusammenbau ==")
    P = assembled()
    assembly_check(P)
    for kind in ("A", "B"):
        plate, placed, touch, W, H = build_sprue(kind)
        tm = to_tm(plate)
        name = f"pb-formel-modellbausatz_spritzling-{kind}_{'karosserie' if kind == 'A' else 'fahrwerk'}"
        print(f"== Spritzling {kind}: {len(placed)} Teile, Rahmen {W:.0f} x {H:.0f} mm ==")
        print(f"  Teile berühren Rahmen/Schilder: {touch:.3f} mm³ | ein zusammenhängender Druck: {len(plate.decompose()) == 1}")
        check(tm, name, (180, 180, 180))
        tm.export(OUT / f"{name}.stl")
    return P


if __name__ == "__main__":
    main()
