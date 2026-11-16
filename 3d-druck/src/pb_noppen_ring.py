"""Noppen-Ring: Fingerring mit Bausteinsockel, kompatibel mit gängigen Klemmbausteinen.

Varianten: 1x1 (1 Noppe), 1x2 (2 Noppen), 2x2 (4 Noppen) – je glatt und mit Streifen,
Innendurchmesser 16–20 mm. Gedruckt stehend (Noppen oben), ohne Stützen.

Hinweis: „LEGO“ ist eine geschützte Marke – im Shop z. B. „Noppen-Ring“ nennen.

Aufruf:  python3 3d-druck/src/pb_noppen_ring.py            (alle Varianten)
         python3 3d-druck/src/pb_noppen_ring.py 2x2 18     (nur eine)
"""
import sys
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, Manifold, OpType, set_circular_segments

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude/skills/stl-designer/scripts"))
from stl_tools import check, preview  # noqa: E402

set_circular_segments(128)

# ---------------------------------------------------------------- Bausteinmaße (Systemstandard)
PITCH = 8.0        # Noppenraster
GAP = 0.1          # Spiel je Seite -> 7.8 mm Grundmaß
STUD_D = 4.85      # Noppen-Ø (Nennmaß 4.8; +0.05, weil gedruckte Noppen leicht schrumpfen)
STUD_H = 1.7
STUD_CHAMFER = 0.25

# ---------------------------------------------------------------- Ring
BAND = 2.4         # Wandstärke Reif
SOCKET_ABOVE = 2.2 # Sockel ragt so weit über den Reif hinaus
FLAT = 0.5         # Abflachung unten (Haftung auf dem Druckbett)
EDGE = 0.5         # Kantenfase innen (Tragekomfort)
STRIPES = 36       # Streifen rundum
STRIPE_W = 0.8
STRIPE_D = 0.4

BAR_HOLE_D = 3.3   # Loch für Stangen (Nennmaß 3.2; gedruckte Löcher werden etwas kleiner)
BAR_DEPTH_INTO_RING = 0.4   # Loch reicht so weit unter die Sockelunterkante

VARIANTS = {       # Name: (Noppen in X, Noppen in Y, Reifbreite[, hohle Noppe])
    "1x1": (1, 1, 7.8),
    "1x1-loch": (1, 1, 7.8, True),
    "1x2": (2, 1, 7.8),
    "2x2": (2, 2, 9.0),
}
SIZES = [16, 17, 18, 19, 20]


def ext_y(cs, w):
    """2D-Querschnitt in der X-Z-Ebene, um w entlang Y (Ringachse) extrudiert, mittig."""
    m = Manifold.extrude(cs, w).translate((0, 0, -w / 2))
    return m.rotate((90, 0, 0))        # (x, y) -> (x, z), Extrusion entlang -Y


def build(variant, inner_d, stripes):
    nx, ny, band_w = VARIANTS[variant][:3]
    hollow = len(VARIANTS[variant]) > 3
    ri = inner_d / 2
    ro = ri + BAND
    zc = ro - FLAT                       # Ringmitte über dem Bett
    lx, ly = nx * PITCH - 2 * GAP, ny * PITCH - 2 * GAP
    z_top = zc + ro + SOCKET_ABOVE       # Oberkante Sockel = Noppenbasis

    # Reif (Querschnitt in X-Z), unten abgeflacht
    band = ext_y(CrossSection.circle(ro).translate((0, zc)), band_w)
    # Sockel: senkrechte Wände bis auf den Reif; in Y bei 2x2 mit 45°-Schrägen
    sock = Manifold.cube((lx, ly, z_top - zc)).translate((-lx / 2, -ly / 2, zc))
    if ly > band_w + 0.01:
        over = (ly - band_w) / 2
        z_full = z_top - 1.6 - 0.0          # obere 1.6 mm volle Breite (Plattenrand)
        # Querschnitt in Y-Z: Trapez (45°) unten auf Reifbreite
        prof = CrossSection([[(-band_w / 2, zc), (band_w / 2, zc), (band_w / 2, z_full - over),
                              (ly / 2, z_full), (ly / 2, z_top), (-ly / 2, z_top), (-ly / 2, z_full),
                              (-band_w / 2, z_full - over)]])
        sock = Manifold.extrude(prof, lx)                 # Profil in (y,z), Extrusion entlang z
        sock = sock.transform([[0, 0, 1, -lx / 2], [1, 0, 0, 0], [0, 1, 0, 0]])   # (y,z,x)->(x,y,z)
    ring = band + sock
    ring = ring ^ Manifold.cube((200, 200, 200)).translate((-100, -100, 0))   # Abflachung unten

    # Fingerloch: Kreis + oben 45°-Spitze, gekappt (kein Durchhängen ohne Stützen)
    hole2d = CrossSection.circle(ri).translate((0, zc))
    peak = CrossSection([[(-ri / np.sqrt(2), zc + ri / np.sqrt(2)), (ri / np.sqrt(2), zc + ri / np.sqrt(2)), (0, zc + ri * np.sqrt(2))]])
    cap = CrossSection.square((4 * ri, 4 * ri)).translate((-2 * ri, zc - 2 * ri))
    cap = cap ^ CrossSection.square((4 * ri, ri + 0.6 + 2 * ri)).translate((-2 * ri, zc - 2 * ri))
    hole2d = (hole2d + peak) ^ cap
    ring = ring - ext_y(hole2d, max(band_w, ly) + 4)
    # Innenkanten fasen (Kegel an beiden Seiten des Lochs)
    for sgn in (1, -1):
        cone = Manifold.cylinder(EDGE * 2, ri + EDGE, ri - EDGE, 128).translate((0, 0, -EDGE))
        cone = cone.rotate((90, 0, 0)) if sgn > 0 else cone.rotate((-90, 0, 0))
        ring = ring - cone.translate((0, sgn * band_w / 2, zc))

    # Senkrechte Streifen (Rillen quer über den Reif), nicht unter dem Sockel
    if stripes:
        cuts = []
        for k in range(STRIPES):
            a = 2 * np.pi * k / STRIPES
            x, z = ro * np.sin(a), zc + ro * np.cos(a)
            if abs(x) < lx / 2 + STRIPE_W and z > zc:      # vom Sockel verdeckt
                continue
            if z < STRIPE_D + 0.6:                          # Auflagefläche unten frei lassen
                continue
            g = Manifold.cube((STRIPE_W, band_w + 2, STRIPE_D * 2)).translate((-STRIPE_W / 2, -band_w / 2 - 1, -STRIPE_D))
            g = g.rotate((0, -np.degrees(a), 0)).translate((x, 0, z))
            cuts.append(g)
        if cuts:
            ring = ring - Manifold.batch_boolean(cuts, OpType.Add)

    # Noppen
    studs = []
    for i in range(nx):
        for j in range(ny):
            x = (i - (nx - 1) / 2) * PITCH
            y = (j - (ny - 1) / 2) * PITCH
            r = STUD_D / 2
            s = Manifold.cylinder(STUD_H - STUD_CHAMFER, r, r, 96) + \
                Manifold.cylinder(STUD_CHAMFER, r, r - STUD_CHAMFER, 96).translate((0, 0, STUD_H - STUD_CHAMFER))
            studs.append(s.translate((x, y, z_top - 0.01)))
    ring = ring + Manifold.batch_boolean(studs, OpType.Add)
    if hollow:
        # Hohle Noppe: Loch für Stangen bis knapp unter den Sockel, Eingang angefast
        rb = BAR_HOLE_D / 2
        z_bot = zc + ro - BAR_DEPTH_INTO_RING
        z_end = z_top + STUD_H
        hole = Manifold.cylinder(z_end - z_bot + 1, rb, rb, 96).translate((0, 0, z_bot))
        lead = Manifold.cylinder(0.31, rb, rb + 0.3, 96).translate((0, 0, z_end - 0.3))
        ring = ring - hole - lead
    return ring


def to_tm(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)


def main():
    out = ROOT / "3d-druck/noppen-ring"
    out.mkdir(parents=True, exist_ok=True)
    only = [a for a in sys.argv[1:] if a in VARIANTS]
    sizes = [int(a) for a in sys.argv[1:] if a.isdigit()] or SIZES
    shown = {}
    for v in only or VARIANTS:
        for d in sizes:
            for stripes in (False, True):
                m = build(v, d, stripes)
                tm = to_tm(m)
                name = f"noppen-ring_{v}_{'streifen' if stripes else 'glatt'}_{d}mm"
                probs = check(tm, name, (180, 180, 180))
                parts = len(m.decompose())
                if parts != 1:
                    print(f"  !! {parts} Körper")
                tm.export(out / f"{name}.stl")
                if d == 18:
                    shown[f"{v}_{'streifen' if stripes else 'glatt'}"] = tm
    if shown:
        # Übersicht: nebeneinander legen
        x = 0
        layout = {}
        for k, tm in shown.items():
            t = tm.copy()
            t.apply_translation((x - t.bounds[0][0], 0, 0))
            x = t.bounds[1][0] + 8
            layout[k] = t
        preview(layout, out / "noppen-ring_uebersicht.png",
                colors={k: "#E8452C" if "glatt" in k else "#2a6fd6" for k in layout})


if __name__ == "__main__":
    main()
