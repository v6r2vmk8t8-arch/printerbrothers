"""Printer Brothers Formel-Bausatz: kleiner Formel-Rennwagen zum Selberbauen.

Alle Teile liegen flach in einem Gießast-Rahmen (wie ein Modellbausatz), ein einziger Druck,
einfarbig. Teile ausbrechen und zusammenstecken:
  1 Fahrgestell   2 Frontflügel   3 Heckflügel   4 Fahrerhelm
  5 Hinterachse   6 Vorderachse   7 Hinterräder (2)   8 Vorderräder (2)
Achsen mit D-Profil, Räder mit Presssitz (wie beim Renn-Flitzer); Achsen drehen in den Bohrungen.

Aufruf:  python3 3d-druck/src/pb_formel_bausatz.py
"""
import sys
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold, OpType, set_circular_segments
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import nearest_points, unary_union

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude/skills/stl-designer/scripts"))
from stl_tools import check, preview  # noqa: E402

set_circular_segments(96)

# ---------------------------------------------------------------- Maße (Fahrgestell-Koordinaten: x Länge, y Breite, z Höhe)
L = 78.0
X_FRONT, X_REAR = 16.0, 66.0          # Achspositionen
Z_FRONT, Z_REAR = 3.0, 4.0            # Achshöhe im Fahrgestell (Unterseite = 0)
RW_F, WW_F = 6.0, 5.0                 # Vorderrad Radius / Breite
RW_R, WW_R = 7.0, 6.0                 # Hinterrad
R_AX, AX_FLAT = 1.8, 1.35             # D-Achse
BORE = R_AX + 0.45                    # Bohrung im Fahrgestell
WHEEL_PRESS = 0.05                    # Rad-Loch +0.05 (Druck macht Löcher ~0.1 kleiner -> Presssitz)
GAP_W = 0.5                           # Rad <-> Fahrgestell
SLOT = 1.6 + 0.12                     # Steckschlitze für 1.6 mm Flügel
WING_T = 1.6


def poly(pts):
    cs = CrossSection([pts])
    return cs if cs.area() > 0 else CrossSection([pts[::-1]])


def plan(points_half):
    """Draufsicht aus (x, halbe Breite)-Punkten, symmetrisch gespiegelt."""
    top = [(x, hw) for x, hw in points_half]
    bot = [(x, -hw) for x, hw in reversed(points_half)]
    return poly(top + bot)


def side_extrude(profile_xz, y0, y1):
    """Seitenprofil (x, z) entlang Y von y0 bis y1 extrudieren."""
    m = Manifold.extrude(poly(profile_xz), y1 - y0)            # (x, z, e)
    return m.transform([[1, 0, 0, 0], [0, 0, 1, y0], [0, 1, 0, 0]])  # e -> y, z bleibt


def to_tm(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)


def d_profile(extra=0.0):
    r = R_AX + extra
    return CrossSection.circle(r) ^ CrossSection.square((4 * r, 2 * r)).translate((-2 * r, -AX_FLAT - extra))


# ---------------------------------------------------------------- 1 Fahrgestell
def hw_at(x):
    """halbe Breite der Achsen-Durchführung bei x (für Achslängen)."""
    return 4.5 if x < 30 else 6.4


def chassis():
    # Hauptkörper: Nase (mit Flügelblock), Monocoque, Heck
    main_plan = plan([(0, 4.5), (8, 4.5), (23, 4.5), (28, 6.0), (31, 7.0), (56, 7.0), (58.5, 6.4), (L, 6.4)])
    main_side = [(0, 0), (L, 0), (L, 7.5), (60, 7.5), (56, 8.5), (28, 8.5), (24, 7.0), (8, 5.6), (0, 4.6)]
    body = Manifold.extrude(main_plan, 20) ^ side_extrude(main_side, -20, 20)
    # Seitenkästen
    pods_plan = plan([(30, 7.5), (34, 11.0), (56, 11.0), (58, 9.0)])
    pods_side = [(30, 0), (58, 0), (58, 5.2), (40, 6.2), (32, 5.0)]
    body = body + (Manifold.extrude(pods_plan, 20) ^ side_extrude(pods_side, -20, 20))
    # Motorhaube / Airbox hinter dem Cockpit
    air_plan = plan([(44, 2.2), (50, 3.4), (72, 3.0), (76, 2.0)])
    air_side = [(44, 0), (76, 0), (76, 7.6), (60, 9.5), (50, 11.2), (45, 10.6)]
    body = body + (Manifold.extrude(air_plan, 20) ^ side_extrude(air_side, -20, 20))
    # Cockpit-Öffnung + Zapfen für den Helm
    cockpit = Manifold.extrude(CrossSection.circle(1.0).scale((8.0, 4.2)).translate((36.5, 0)), 10).translate((0, 0, 4.0))
    body = body - cockpit
    body = body + Manifold.cylinder(3.2, 1.35, 1.35, 48).translate((36.5, 0, 4.0 - 0.01))
    # Achsbohrungen (quer, entlang Y)
    for x, z in ((X_FRONT, Z_FRONT), (X_REAR, Z_REAR)):
        bore = Manifold.cylinder(40, BORE, BORE, 64).translate((0, 0, -20)).rotate((90, 0, 0)).translate((x, 0, z))
        body = body - bore
    # Frontflügel-Schlitz in der Nasenspitze
    body = body - Manifold.cube((5.5, 6.4, SLOT)).translate((-0.01, -3.2, 0.7))
    # Heckflügel-Halter: zwei Finnen mit waagrechtem Schlitz
    for sy in (-1, 1):
        fin = Manifold.cube((8.0, 1.6, 15.5 - 6.0)).translate((69.0, sy * 4.6 - 0.8, 6.0))
        slot = Manifold.cube((6.6, 3.0, SLOT)).translate((69.7, sy * 4.6 - 1.5, 12.4))
        body = body + (fin - slot)
    return body


# ---------------------------------------------------------------- Kleinteile
def front_wing():
    w = Manifold.extrude(plan([(0, 15.0), (2.0, 17.0), (7.0, 17.0), (8.0, 15.5)]).translate((0, 0)), WING_T)
    tab = Manifold.cube((5.4, 6.0, WING_T)).translate((8.0, -3.0, 0))      # wird in die Nase gesteckt
    endplates = [Manifold.cube((7.0, 1.0, 3.0)).translate((0.5, s * 16.5 - 0.5, 0)) for s in (-1, 1)]
    return Manifold.batch_boolean([w, tab] + endplates, OpType.Add)


def rear_wing():
    span, chord = 22.0, 6.0
    w = Manifold.cube((chord, span, WING_T)).translate((0, -span / 2, 0))
    endplates = [Manifold.cube((chord + 1.0, 1.0, 4.0)).translate((-0.5, s * (span / 2 + 0.5) - 0.5, 0)) for s in (1,)]
    return w + endplates[0]          # Endplatte nur an einer Seite -> lässt sich durchschieben


def helmet():
    dome = Manifold.sphere(3.8, 64).scale((1.15, 1.0, 1.05))
    dome = dome ^ Manifold.cube((20, 20, 20)).translate((-10, -10, 0))
    visor = Manifold.cube((6, 8, 1.2)).translate((2.0, -4, 1.8))       # Visierschlitz (Gravur)
    hole = Manifold.cylinder(3.4, 1.35 + 0.18, 1.35 + 0.18, 48).translate((0, 0, -0.01))
    return dome - visor - hole


def axle(length):
    core = Manifold.extrude(d_profile(), length - 0.6).translate((0, 0, 0.3))
    tip = Manifold.extrude(d_profile(-0.3), 0.31)
    return Manifold.batch_hull([core, tip]) + Manifold.batch_hull([core, tip.translate((0, 0, length - 0.31))])


def wheel(r, w):
    wh = Manifold.revolve(poly([(0, 0), (r - 0.4, 0), (r, 0.4), (r, w - 0.4), (r - 0.4, w), (0, w)]), 96)
    wh = wh - Manifold.revolve(poly([(r * 0.55, -0.01), (r * 0.67, -0.01), (r * 0.67, 0.4), (r * 0.55, 0.4)]), 96)
    hole = Manifold.extrude(d_profile(WHEEL_PRESS), w + 2).translate((0, 0, -1))
    lead = Manifold.extrude(d_profile(WHEEL_PRESS + 0.3), 0.31).translate((0, 0, w - 0.3))
    return wh - hole - lead


def axle_len(x, ww):
    return 2 * hw_at(x) + 2 * (GAP_W + ww) - 0.6


# ---------------------------------------------------------------- Zusammenbau (Fahrlage, Boden z=0)
def assembled():
    lift = RW_R - Z_REAR                       # Fahrgestell-Unterseite über Boden (vorne gleich: RW_F - Z_FRONT)
    parts = {"fahrgestell": chassis()}
    fw = front_wing().translate((-8.15, 0, 0.7 + 0.06))          # Lasche steckt im Schlitz
    rw = rear_wing().translate((70.0, 0, 12.4 + 0.06))
    hm = helmet().translate((36.5, 0, 4.0))
    parts.update({"frontfluegel": fw, "heckfluegel": rw, "helm": hm})
    for name, x, z, r, w in (("hinten", X_REAR, Z_REAR, RW_R, WW_R), ("vorne", X_FRONT, Z_FRONT, RW_F, WW_F)):
        L_ax = axle_len(x, w)
        ax = axle(L_ax).translate((0, 0, -L_ax / 2)).rotate((90, 0, 0)).translate((x, 0, z))
        y_in = hw_at(x) + GAP_W
        # Rx(90): Außenseite zeigt nach +y, D-Fläche bleibt unten; links zusätzlich um Z gewendet
        wr = wheel(r, w).rotate((90, 0, 0)).translate((x, y_in + w, z))
        wl = wheel(r, w).rotate((90, 0, 0)).rotate((0, 0, 180)).translate((x, -(y_in + w), z))
        parts[f"achse_{name}"] = ax
        parts[f"raeder_{name}"] = wl + wr
    return {k: m.translate((0, 0, lift)) for k, m in parts.items()}


# ---------------------------------------------------------------- Gießast
def footprint(m):
    sec = m.slice(0.2)
    polys = [Polygon(p) for p in sec.to_polygons() if len(p) >= 3]
    return unary_union(polys)


def sprue(parts):
    """parts: Liste (Manifold flach auf z=0, Nummer). Rahmen + Läufer + Angüsse + Nummern."""
    W, H, BAR, BH = 150.0, 112.0, 3.0, 2.0
    frame = (CrossSection.square((W, H)) - CrossSection.square((W - 2 * BAR, H - 2 * BAR)).translate((BAR, BAR)))
    runners_cs = CrossSection.square((W - 2 * BAR, BAR)).translate((BAR, 56 - BAR / 2)) + \
        CrossSection.square((BAR, 56 - BAR)).translate((96 - BAR / 2, BAR))
    grid = frame + runners_cs
    grid_m = Manifold.extrude(grid.offset(-0.6, JoinType.Round).offset(0.6, JoinType.Round), BH)
    runner_lines = [LineString([(BAR / 2, BAR / 2), (W - BAR / 2, BAR / 2), (W - BAR / 2, H - BAR / 2), (BAR / 2, H - BAR / 2), (BAR / 2, BAR / 2)]),
                    LineString([(BAR, 56), (W - BAR, 56)]), LineString([(96, BAR), (96, 56)])]
    gates, tags = [], []
    for m, nr in parts:
        fp = footprint(m)
        cands = []
        for ln in runner_lines:
            p_part, p_run = nearest_points(fp, ln)
            cands.append((p_part.distance(p_run), p_part, p_run))
        cands.sort(key=lambda c: c[0])
        for d, p_part, p_run in cands[:2]:
            if d > 30:
                continue
            v = np.array([p_run.x - p_part.x, p_run.y - p_part.y]); n = np.linalg.norm(v)
            if n < 1e-6:
                continue
            u = v / n
            a = np.array([p_part.x, p_part.y]) - u * 0.4          # 0.4 ins Teil hinein
            b = np.array([p_run.x, p_run.y]) + u * 1.0
            perp = np.array([-u[1], u[0]])
            # Anguss: am Teil schmal (Sollbruchstelle 0.7), am Läufer 1.4 breit, 1.0 hoch
            quad = [a + perp * 0.35, a - perp * 0.35, b - perp * 0.7, b + perp * 0.7]
            gates.append(Manifold.extrude(poly([tuple(q) for q in quad]), 1.0))
        # Nummer auf einem Schildchen am Läufer, 7 mm neben dem Anguss (berührt das Teil nicht)
        _, p_part, p_run = cands[0]
        ln = min(runner_lines, key=lambda l: l.distance(p_run))
        s0 = ln.project(p_run)
        for off in (7.0, -7.0, 11.0, -11.0, 15.0, -15.0):
            q = ln.interpolate(min(max(s0 + off, 0), ln.length))
            if fp.distance(q) > 3.0 + 1.5:
                tags.append((nr, q.x, q.y)); break
    return grid_m + number_tags(tags, BH), Manifold.batch_boolean(gates, OpType.Add)


def number_tags(tags, bh):
    """Schildchen mit erhabener Nummer (build123d-Text)."""
    from build123d import BuildPart, BuildSketch, Text, extrude, Align
    out = []
    for nr, x, y in tags:
        plate = Manifold.cylinder(1.2, 3.0, 3.0, 48).translate((x, y, 0))
        with BuildPart() as bp:
            with BuildSketch():
                Text(str(nr), 4.2, align=(Align.CENTER, Align.CENTER))
            extrude(amount=0.6)
        v, f = bp.part.tessellate(0.02, 0.2)
        tm = trimesh.Trimesh([[p.X, p.Y, p.Z] for p in v], f, process=True)
        from manifold3d import Mesh
        txt = Manifold(Mesh(vert_properties=np.asarray(tm.vertices, np.float32), tri_verts=np.asarray(tm.faces, np.uint32)))
        out.append(plate + txt.translate((x, y, 1.2 - 0.01)))
    return Manifold.batch_boolean(out, OpType.Add)


def plate_layout():
    """Teile flach auf z=0 an ihren Plätzen im Rahmen (Druck-Koordinaten)."""
    def place(m, x, y, rot=0.0):
        m = m.rotate((0, 0, rot))
        bb = m.bounding_box()
        return m.translate((x - (bb[0] + bb[3]) / 2, y - (bb[1] + bb[4]) / 2, -bb[2]))
    L_r, L_f = axle_len(X_REAR, WW_R), axle_len(X_FRONT, WW_F)
    ax_r = axle(L_r).rotate((0, 90, 0)).rotate((90, 0, 0))     # liegend, flache Seite unten
    ax_f = axle(L_f).rotate((0, 90, 0)).rotate((90, 0, 0))
    parts = [
        (place(chassis(), 50, 72), 1),
        (place(front_wing(), 124, 88, 0), 2),
        (place(rear_wing(), 124, 64, 90), 3),
        (place(helmet(), 138, 34), 4),
        (place(ax_r, 120, 40), 5),
        (place(ax_f, 120, 20), 6),
        (place(wheel(RW_R, WW_R), 18, 38), 7), (place(wheel(RW_R, WW_R), 40, 38), 7),
        (place(wheel(RW_F, WW_F), 18, 17), 8), (place(wheel(RW_F, WW_F), 40, 17), 8),
    ]
    return parts


def main():
    out = ROOT / "3d-druck/formel-bausatz"
    out.mkdir(parents=True, exist_ok=True)
    asm = assembled()
    print("== Prüfung Zusammenbau ==")
    ch = asm["fahrgestell"]
    for k, m in asm.items():
        if k == "fahrgestell":
            continue
        v = (ch ^ m).volume()
        g = ch.min_gap(m, 2.0)
        note = "(steckt/klemmt – gewollt)" if k in ("frontfluegel", "heckfluegel", "helm") else ""
        print(f"  {k:14s}: Überschneidung {v:.3f} mm³, min. Spalt {g:.2f} mm {note}")
    for nm in ("hinten", "vorne"):
        print(f"  Presssitz Räder {nm}: Überdeckung {(asm['raeder_' + nm] ^ asm['achse_' + nm]).volume():.3f} mm³ (0 = Spiel im Modell, Presssitz durch Druckschrumpf)")
    z_min = min(m.bounding_box()[2] for k, m in asm.items() if k.startswith("raeder"))
    print(f"  Bodenfreiheit Fahrgestell: {ch.bounding_box()[2] - z_min:.1f} mm")

    parts = plate_layout()
    grid, gates = sprue(parts)
    # kein Teil darf Rahmen/Schildchen berühren (nur über die Angüsse verbunden)
    allparts = Manifold.batch_boolean([m for m, _ in parts], OpType.Add)
    print(f"  Teile berühren Rahmen/Schilder: {(allparts ^ grid).volume():.3f} mm³, min. Abstand {allparts.min_gap(grid, 5):.2f} mm")
    print(f"  Teile untereinander: {len(allparts.decompose())} getrennte Körper (erwartet 10)")
    plate = Manifold.batch_boolean([allparts, grid, gates], OpType.Add)
    tm = to_tm(plate)
    check(tm, "formel-bausatz (Druckplatte)", (180, 180, 180))
    print("  Teile am Gießast verbunden:", len(plate.decompose()) == 1)
    tm.export(out / "pb-formel-bausatz_150mm_einfarbig.stl")
    preview({"bausatz": tm}, out / "pb-formel-bausatz_druckplatte.png", colors={"bausatz": "#D8382B"})
    preview({k: to_tm(m) for k, m in asm.items()}, out / "pb-formel-bausatz_zusammengebaut.png",
            colors={"fahrgestell": "#D8382B", "frontfluegel": "#2b2b2b", "heckfluegel": "#2b2b2b", "helm": "#f2c230",
                    "achse_hinten": "#9a9a9a", "achse_vorne": "#9a9a9a", "raeder_hinten": "#222222", "raeder_vorne": "#222222"})
    return asm, plate


if __name__ == "__main__":
    main()
