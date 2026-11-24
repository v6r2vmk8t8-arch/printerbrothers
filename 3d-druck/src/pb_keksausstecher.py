"""Keksausstecher mit Präge-Stempel (Kundenauftrag Dani).

  1. Zagreb-Herz:   Herzumriss als Ausstecher, die innere weiße Linie als Prägung.
  2. Sretan Božić:  runder Ausstecher, Stempel mit Schriftzug + Volkskunst-Ornamenten.

Aufbau wie das Referenz-Set (set.3mf): Ausstecher (offener Rahmen, Griffrand unten,
Schneide oben) + separater Stempel (Platte mit erhabener Prägung), der genau in den
Ausstecher passt. Anwendung: ausstechen, Ausstecher im Teig lassen, Stempel mit der
Prägung nach unten hineinlegen, andrücken, Ausstecher abheben.

Druck: beide Teile flach, ohne Support. Der Stempel liegt mit der glatten Rückseite auf
dem Bett, die Prägung zeigt nach oben. Schrift ist deshalb gespiegelt modelliert,
damit sie auf dem Keks richtig herum steht.

Aufruf:  python3 3d-druck/src/pb_keksausstecher.py
"""
import sys
from pathlib import Path

import numpy as np
import trimesh
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from manifold3d import CrossSection, FillRule, JoinType, Manifold, set_circular_segments
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, MultiPolygon
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".claude/skills/stl-designer/scripts"))
from stl_tools import export_parts  # noqa: E402

set_circular_segments(128)

# ---------------------------------------------------------------- Parameter
# Ausstecher
H_CUT = 14.5        # Gesamthöhe Ausstecher
WALL = 1.2          # Wandstärke (3 Linien)
TIP_H = 2.5         # Höhe der angeschrägten Schneide oben
TIP_W = 0.6         # Wandstärke an der Schneide (innen bleibt bündig)
FLANGE_W = 3.0      # Griffrand: so weit steht er außen über
FLANGE_H = 2.0      # Griffrand: Höhe

# Stempel
GAP = 0.8           # Spiel Stempel ↔ Innenwand des Ausstechers
PLATE = 2.0         # Plattenstärke
RELIEF = 2.0        # Höhe der Prägung (erhaben)

# Zagreb-Herz
HEART_W = 57.0      # Keksbreite (= Innenmaß Ausstecher) → Höhe ≈ 46 mm
HEART_LINE_IN = 3.6 # Abstand der Prägelinie vom Keksrand (Mitte der Linie)
HEART_LINE_W = 1.4  # Strichstärke der Prägelinie

# Sretan Božić
ROUND_D = 57.0      # Keksdurchmesser (= Innenmaß Ausstecher)
TEXT_W = 35.0       # Breite von "Sretan" auf dem Keks
THICKEN = 0.2       # Prägung rundum verdicken (Haarstriche ≥ 0,8 mm)

OUT = ROOT / "3d-druck"


# ---------------------------------------------------------------- Helfer
def to_cs(geom):
    """shapely (Multi)Polygon → CrossSection (Löcher bleiben erhalten)."""
    polys = geom.geoms if isinstance(geom, MultiPolygon) else [geom]
    rings = []
    for p in polys:
        if p.is_empty:
            continue
        ext = np.asarray(p.exterior.coords)[:-1]
        rings.append(ext if p.exterior.is_ccw else ext[::-1])
        for i in p.interiors:
            r = np.asarray(i.coords)[:-1]
            rings.append(r[::-1] if i.is_ccw else r)
    return CrossSection([r.tolist() for r in rings], FillRule.Positive)


def to_tm(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)


def smooth(p, r):
    """Ecken runden (öffnen + schließen)."""
    return p.buffer(r, 64).buffer(-2 * r, 64).buffer(r, 64)


def cutter(inner: Polygon) -> Manifold:
    """Ausstecher um die Keksform `inner` (Innenkante = Keksrand)."""
    hole = to_cs(inner)
    wall = to_cs(inner.buffer(WALL, 64)) - hole
    tip = to_cs(inner.buffer(TIP_W, 64)) - hole
    flange = to_cs(inner.buffer(WALL + FLANGE_W, 64)) - hole
    body = wall.extrude(H_CUT - TIP_H + 0.01)
    body += flange.extrude(FLANGE_H)
    # Schneide: Außenseite in Stufen von 0,2 mm (Schichthöhe) schräg zur Spitze
    n = int(round(TIP_H / 0.2))
    for k in range(n):
        w = WALL - (WALL - TIP_W) * (k + 1) / n
        ring = to_cs(inner.buffer(w, 64)) - hole
        body += ring.extrude(TIP_H / n + 0.01).translate((0, 0, H_CUT - TIP_H + k * TIP_H / n))
    return body


def stamp(inner: Polygon, relief) -> Manifold:
    plate = to_cs(inner.buffer(-GAP, 64)).extrude(PLATE)
    rel = to_cs(relief).extrude(RELIEF + 0.05).translate((0, 0, PLATE - 0.05))
    return plate + rel


# ---------------------------------------------------------------- Schrift (Lobster, OFL)
class Font:
    def __init__(self):
        self.fonts = [TTFont(SRC / "fonts/lobster-latin.ttf"), TTFont(SRC / "fonts/lobster-latin-ext.ttf")]

    def glyph(self, ch):
        for f in self.fonts:
            g = f.getBestCmap().get(ord(ch))
            if g:
                return f, g
        raise KeyError(ch)

    def text(self, s, steps=12):
        """Text als shapely-Geometrie (Einheiten: 1000 = 1 em), Grundlinie y=0."""
        x, parts = 0.0, []
        for ch in s:
            f, gname = self.glyph(ch)
            pen = RecordingPen(); f.getGlyphSet()[gname].draw(pen)
            rings, cur = [], []
            for op, args in pen.value:
                if op == "moveTo":
                    cur = [args[0]]
                elif op == "lineTo":
                    cur.append(args[0])
                elif op == "qCurveTo":
                    pts = [cur[-1]] + list(args)
                    # implizite Zwischenpunkte bei TrueType-Quadratkurven
                    seq = [pts[0]]
                    for i in range(1, len(pts) - 1):
                        seq.append(pts[i])
                        if i < len(pts) - 2:
                            seq.append(((pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2))
                    seq.append(pts[-1])
                    p0 = seq[0]
                    for i in range(1, len(seq) - 1, 2):
                        c, p1 = seq[i], seq[i + 1]
                        for t in np.linspace(0, 1, steps)[1:]:
                            cur.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0],
                                        (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1]))
                        p0 = p1
                elif op == "curveTo":
                    p0 = cur[-1]; c1, c2, p1 = args
                    for t in np.linspace(0, 1, steps)[1:]:
                        cur.append(tuple((1 - t) ** 3 * np.array(p0) + 3 * (1 - t) ** 2 * t * np.array(c1)
                                         + 3 * (1 - t) * t * t * np.array(c2) + t ** 3 * np.array(p1)))
                elif op in ("closePath", "endPath"):
                    if len(cur) > 2:
                        rings.append(Polygon(cur).buffer(0))
                    cur = []
            # Nonzero/Even-odd: verschachtelte Konturen per XOR
            g = Polygon()
            for r in sorted(rings, key=lambda r: -r.area):
                g = g.symmetric_difference(r)
            parts.append(affinity.translate(g, x, 0))
            x += f["hmtx"][gname][0]
        return unary_union(parts)


def fit_text(font, s, width, cy):
    g = font.text(s)
    x0, y0, x1, y1 = g.bounds
    k = width / (x1 - x0)
    g = affinity.scale(g, k, k, origin=(0, 0))
    x0, y0, x1, y1 = g.bounds
    return affinity.translate(g, -(x0 + x1) / 2, cy - (y0 + y1) / 2)


# ---------------------------------------------------------------- Ornamente (Eigenentwurf, Volkskunst-Stil)
def heart(w):
    t = np.linspace(0, 2 * np.pi, 200)
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    p = Polygon(np.c_[x, y]).buffer(0)
    k = w / 32.0
    p = affinity.scale(p, k, k, origin=(0, 0))
    c = p.centroid
    return affinity.translate(p, -c.x, -c.y)


def leaf(length, width, bend=0.25):
    """Gebogenes Blatt, Stiel bei (0,0), Spitze Richtung +x."""
    t = np.linspace(0, 1, 60)
    top = np.c_[t * length, np.sin(np.pi * t) * width / 2 + bend * length * t * t]
    bot = np.c_[t * length, -np.sin(np.pi * t) * width / 2 * 0.6 + bend * length * t * t][::-1]
    return Polygon(np.r_[top, bot]).buffer(0.15).buffer(-0.15)


def fan_ornament():
    """Herz in der Mitte (Spitze unten), je Seite zwei geschwungene Blätter fächerförmig nach oben."""
    parts = [heart(6.6)]
    for sx in (1, -1):
        for ang, L, W, off in ((12, 6.4, 3.0, (2.6, 0.4)), (50, 5.4, 2.8, (1.6, 2.2))):
            lf = affinity.translate(affinity.rotate(leaf(L, W, 0.22), ang, origin=(0, 0)), *off)
            parts.append(affinity.scale(lf, sx, 1, origin=(0, 0)))
    return unary_union(parts).buffer(0.2).buffer(-0.2)


def sprig():
    """Kleiner Zweig für links/rechts: Bogen mit drei Blättern."""
    t = np.linspace(-1, 1, 30)
    stem = LineString(np.c_[0.8 * (1 - t * t), t * 3.0]).buffer(0.5)
    parts = [stem]
    for y, a in ((2.0, 45), (0.0, 10), (-2.0, -25)):
        x = 0.8 * (1 - (y / 3) ** 2)
        parts.append(affinity.translate(affinity.rotate(leaf(3.4, 2.0, 0.12), a, origin=(0, 0)), x, y))
    return unary_union(parts).buffer(0.2).buffer(-0.2)


# ---------------------------------------------------------------- Modelle
def zagreb_herz():
    pts = np.loadtxt(SRC / "data/zagreb_herz_umriss.csv", delimiter=",")
    h = Polygon(pts * HEART_W)
    h = smooth(h.buffer(0), 1.2)
    k = HEART_W / (h.bounds[2] - h.bounds[0])
    inner = affinity.scale(h, k, k, origin=(0, 0))
    # Prägelinie: weiße Innenlinie = Herz versetzt nach innen
    a = inner.buffer(-(HEART_LINE_IN - HEART_LINE_W / 2), 64)
    b = inner.buffer(-(HEART_LINE_IN + HEART_LINE_W / 2), 64)
    line = smooth(a, 0.8).difference(smooth(b, 0.8))
    return inner, line


def sretan_bozic():
    inner = Point(0, 0).buffer(ROUND_D / 2, 256)
    font = Font()
    s1 = fit_text(font, "Sretan", TEXT_W, 4.4)
    k = TEXT_W / (font.text("Sretan").bounds[2] - font.text("Sretan").bounds[0])
    s2 = font.text("Božić")
    s2 = affinity.scale(s2, k, k, origin=(0, 0))
    x0, y0, x1, y1 = s2.bounds
    s2 = affinity.translate(s2, -(x0 + x1) / 2 + 1.5, -6.6 - (y0 + y1) / 2)
    top = affinity.translate(fan_ornament(), 0, 17.6)
    bot = affinity.translate(affinity.scale(fan_ornament(), 1, -1, origin=(0, 0)), 0, -19.6)
    left = affinity.translate(affinity.scale(sprig(), -1, 1, origin=(0, 0)), -21.0, -1.4)
    right = affinity.translate(sprig(), 21.0, -1.4)
    design = unary_union([s1, s2, top, bot, left, right])
    # Haarstriche der Schrift auf druckbare Stärke bringen (≥ 0,8 mm = 2 Linien)
    design = design.buffer(THICKEN, 32)
    # alles muss sicher auf der Stempelplatte liegen
    design = design.intersection(inner.buffer(-GAP - 1.0))
    # Spiegeln: Stempel wird umgedreht aufgedrückt
    return inner, affinity.scale(design, -1, 1, origin=(0, 0)), design


def build(name, inner, relief, size):
    c = cutter(inner)
    s = stamp(inner, relief)
    # nebeneinander auf die Platte legen (Bauraum 180 × 180)
    w = inner.bounds[2] - inner.bounds[0] + 2 * (WALL + FLANGE_W)
    s = s.translate((w / 2 + 4 + (inner.bounds[2] - inner.bounds[0]) / 2, 0, 0))
    c = c.translate((-w / 2 + 2, 0, 0)); s = s.translate((-w / 2 + 2, 0, 0))
    for m, n in ((c, "ausstecher"), (s, "stempel")):
        assert len(m.decompose()) == 1, f"{n} besteht aus mehreren Teilen"
    export_parts({"ausstecher": to_tm(c), "stempel": to_tm(s)}, OUT / f"{name}_{size}mm")
    print(f"{name}: Ausstecher {c.volume() / 1000 * 1.24:.1f} g, Stempel {s.volume() / 1000 * 1.24:.1f} g (PLA)")


if __name__ == "__main__":
    inner, line = zagreb_herz()
    b = inner.bounds
    print(f"Herz: {b[2] - b[0]:.1f} × {b[3] - b[1]:.1f} mm (Keks)")
    build("keks-zagreb-herz", inner, line, round(HEART_W))

    inner, relief, design = sretan_bozic()
    build("keks-sretan-bozic", inner, relief, round(ROUND_D))

    # Vorschau, wie der Keks aussieht (Prägung richtig herum)
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from shapely.plotting import plot_polygon
    fig, ax = plt.subplots(1, 2, figsize=(10, 5))
    for a, (inn, d, t) in zip(ax, ((zagreb_herz()[0], zagreb_herz()[1], "Zagreb-Herz"),
                                   (inner, design, "Sretan Božić"))):
        plot_polygon(inn, ax=a, add_points=False, facecolor="#e8b778", edgecolor="#8a5a2b")
        plot_polygon(d, ax=a, add_points=False, facecolor="#a8763c", edgecolor="#6b4420", linewidth=0.4)
        a.set_aspect("equal"); a.axis("off"); a.set_title(f"{t} – so sieht der Keks aus")
    fig.savefig(OUT / "keks-ausstecher_keks-vorschau.png", dpi=150, bbox_inches="tight")
    print("Keks-Vorschau gespeichert")
