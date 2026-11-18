"""Noppen-Ring: Fingerring mit Bausteinsockel, kompatibel mit gängigen Klemmbausteinen.

Varianten: 1x1 (1 Noppe), 1x2 (2 Noppen), 2x2 (4 Noppen) – je glatt und mit Streifen,
Innendurchmesser 15/17/20 mm. Alle Varianten werden STEHEND gedruckt (Noppen oben), ohne Stützen –
so passen die Noppen nach Testdruck am besten (liegend klemmten die Steine nicht zuverlässig).
LYING = True schaltet die liegende Variante (Ringachse senkrecht) für 1x1/1x2 wieder ein.

Hinweis: „LEGO“ ist eine geschützte Marke – im Shop z. B. „Noppen-Ring“ nennen.

Aufruf:  python3 3d-druck/src/pb_noppen_ring.py            (alle Varianten)
         python3 3d-druck/src/pb_noppen_ring.py 2x2 18     (nur eine)
"""
import sys
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold, OpType, set_circular_segments

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude/skills/stl-designer/scripts"))
from stl_tools import check, preview  # noqa: E402

set_circular_segments(128)

# ---------------------------------------------------------------- Bausteinmaße (Systemstandard)
PITCH = 8.0        # Noppenraster
GAP = 0.1          # Spiel je Seite -> 7.8 mm Grundmaß
STUD_D = 4.90      # Noppen-Ø (Nennmaß 4.8; Testdrucke: 4.85 zu locker, 4.95 etwas zu breit)
STUD_H = 2.15      # Noppenhöhe (Nennmaß 1.7; +0.45 nach Testdrucken für mehr Halt)
STUD_CHAMFER = 0.25

# ---------------------------------------------------------------- Ring
BAND = 2.4         # Wandstärke Reif
SOCKET_ABOVE = 2.2 # Sockel ragt so weit über den Reif hinaus
FLAT = 0.5         # Abflachung unten (Haftung auf dem Druckbett)
EDGE = 0.5         # (alt) Kantenfase innen – ersetzt durch ROUND
ROUND = 1.0        # Kantenradius Reif innen + außen (keine scharfen Kanten, Verletzungsschutz)
SOCK_ROUND = 0.8   # Radius der senkrechten Sockelkanten
TOP_CHAMFER = 0.4  # Fase an der oberen Sockelkante
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


def tentacles(ro, zc, band_w, lx):
    """3 Tentakel als Kugelketten (Hülle je zweier Nachbarn): vom Sockel weg um den Reif,
    seitlich gewellt, zur Spitze dünner, Spitze eingerollt. Erhaben max. ~0.75 mm."""
    r_base, r_tip, embed = 1.4, 0.45, 0.5
    rc = ro - embed                                   # Bahnradius (Mittellinie)
    amp = max(0.5, band_w / 2 - ROUND - 0.1 - r_base)
    a0 = np.arcsin(min(0.95, (lx / 2 - 0.6) / ro))     # Start knapp unter dem Sockel
    specs = [  # (Richtung, Bogen in Grad, Wellen, Phase)
        (+1, 215, 1.7, 0.0),
        (-1, 200, 1.5, np.pi),
        (-1, 140, 1.15, np.pi / 2),
    ]
    bodies = []
    for sgn, arc, waves, ph in specs:
        pts = []
        n = int(arc / 2.2)
        for k in range(n + 1):
            t = k / n
            a = sgn * (a0 + np.radians(arc) * t)
            y = amp * np.sin(2 * np.pi * waves * t + ph) * (0.35 + 0.65 * min(1, t * 4))
            r = r_base + (r_tip - r_base) * t ** 0.8
            pts.append((a, y, r))
        # eingerollte Spitze: kleine Spirale in der (Bogen, Breite)-Ebene
        a_end, y_end, _ = pts[-1]
        side = -1 if y_end > 0 else 1
        for k in range(1, 15):
            s = k / 14
            rr = 1.3 * (1 - 0.65 * s)
            ang = s * 1.7 * np.pi
            a = a_end + sgn * (rr * np.sin(ang)) / rc
            y = y_end + side * rr * (1 - np.cos(ang))
            pts.append((a, y, max(0.28, r_tip * (1 - 0.3 * s))))
        spheres = [Manifold.sphere(r, 20).translate((rc * np.sin(a), y, zc + rc * np.cos(a))) for a, y, r in pts]
        hulls = [Manifold.batch_hull([spheres[i], spheres[i + 1]]) for i in range(len(spheres) - 1)]
        body = Manifold.batch_boolean(hulls, OpType.Add)
        # Saugnäpfe: kleine Mulden auf der Außenseite, jede 3. Station (nur wo dick genug)
        cups = []
        for a, y, r in pts[2:-14:3]:
            if r < 0.7:
                continue
            rr = rc + r * 0.95
            cups.append(Manifold.sphere(0.32 * r, 16).translate((rr * np.sin(a), y, zc + rr * np.cos(a))))
        if cups:
            body = body - Manifold.batch_boolean(cups, OpType.Add)
        bodies.append(body)
    return Manifold.batch_boolean(bodies, OpType.Add)


LYING = False      # Testdruck: liegende Ringe funktionierten nicht – alle stehend


def lies_flat(variant):
    """Druck liegend? Nur wenn LYING an ist, und nie bei 2x2 (Sockel breiter als der Reif)."""
    nx, ny, band_w = VARIANTS[variant][:3]
    return LYING and ny * PITCH - 2 * GAP <= band_w + 0.01


def build(variant, inner_d, stripes, stud_d=None, orient=True):
    """stripes: 'glatt', 'senkrecht', 'waagrecht' oder 'tentakel' (True = senkrecht, für ältere Aufrufe).
    Modell entsteht stehend (Ringachse = Y, Noppen oben). Liegende Varianten: ohne Abflachung und
    ohne Lochspitze; mit orient=True zum Schluss in Drucklage gekippt (Ringachse = Z)."""
    stripes = {True: 'senkrecht', False: 'glatt'}.get(stripes, stripes)
    lying = lies_flat(variant)
    stud_d = stud_d or STUD_D
    nx, ny, band_w = VARIANTS[variant][:3]
    hollow = len(VARIANTS[variant]) > 3
    ri = inner_d / 2
    ro = ri + BAND
    zc = ro - FLAT                       # Ringmitte über dem Bett
    lx, ly = nx * PITCH - 2 * GAP, ny * PITCH - 2 * GAP
    z_top = zc + ro + SOCKET_ABOVE       # Oberkante Sockel = Noppenbasis

    # Reif als Rotationskörper: Querschnitt (Radius x Breite) mit gerundeten Außenkanten.
    # Innenkanten rundet der Loch-Schnitt (siehe unten), daher innen eckig mit Reserve.
    prof = CrossSection.square((ro - ri + 1.0, band_w)).translate((ri - 1.0, -band_w / 2))
    outer_round = prof.offset(-ROUND, JoinType.Round).offset(ROUND, JoinType.Round)
    inner_part = CrossSection.square((ROUND + 1.2, band_w)).translate((ri - 1.0, -band_w / 2))
    band = Manifold.revolve(outer_round + inner_part, 160)          # Achse = Z
    band = band.rotate((90, 0, 0)).translate((0, 0, zc))             # Achse -> Y
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
    # Sockel: senkrechte Kanten gerundet, obere Kante angefast
    def rrect(w, h, r):
        return CrossSection.square((w, h)).translate((-w / 2, -h / 2)).offset(-r, JoinType.Round).offset(r, JoinType.Round)
    body = Manifold.extrude(rrect(lx, ly, SOCK_ROUND), z_top - TOP_CHAMFER - zc + 0.01).translate((0, 0, zc))
    top = Manifold.extrude(rrect(lx - 2 * TOP_CHAMFER, ly - 2 * TOP_CHAMFER, max(0.05, SOCK_ROUND - TOP_CHAMFER)), 0.01).translate((0, 0, z_top - 0.01))
    sock = sock ^ Manifold.batch_hull([body, top])
    ring = band + sock
    if not lying:
        ring = ring ^ Manifold.cube((200, 200, 200)).translate((-100, -100, 0))   # Abflachung unten

    # Fingerloch: Kreis + oben 45°-Spitze, gekappt (kein Durchhängen ohne Stützen)
    hole2d = CrossSection.circle(ri).translate((0, zc))
    peak = CrossSection([[(-ri / np.sqrt(2), zc + ri / np.sqrt(2)), (ri / np.sqrt(2), zc + ri / np.sqrt(2)), (0, zc + ri * np.sqrt(2))]])
    cap = CrossSection.square((4 * ri, 4 * ri)).translate((-2 * ri, zc - 2 * ri))
    cap = cap ^ CrossSection.square((4 * ri, ri + 0.6 + 2 * ri)).translate((-2 * ri, zc - 2 * ri))
    if not lying:                                        # liegend: Loch einfach rund
        hole2d = (hole2d + peak) ^ cap
    # Loch-Schnitt mit gerundeten Innenkanten: zu beiden Seiten hin als Viertelkreis aufgeweitet
    cutters = [ext_y(hole2d, band_w - 2 * ROUND + 0.04)]
    steps = 10
    for j in range(steps):
        s0, s1 = j * ROUND / steps, (j + 1) * ROUND / steps
        sm = (s0 + s1) / 2
        off = ROUND - np.sqrt(max(0.0, ROUND ** 2 - sm ** 2))
        cs = hole2d.offset(off, JoinType.Round)
        for sgn in (1, -1):
            y0 = band_w / 2 - ROUND + s0
            seg = ext_y(cs, (s1 - s0) + 0.02).translate((0, sgn * (y0 + (s1 - s0) / 2), 0))
            cutters.append(seg)
    for sgn in (1, -1):                                   # außerhalb des Reifs voll offen
        cutters.append(ext_y(hole2d.offset(ROUND, JoinType.Round), max(band_w, ly) + 4)
                       .translate((0, sgn * (band_w / 2 + (max(band_w, ly) + 4) / 2 - 0.01), 0)))
    ring = ring - Manifold.batch_boolean(cutters, OpType.Add)

    # Waagrechte Streifen: Rillen rund um den Reif (parallel zu den Kanten), nicht im Sockel,
    # unten frei für die Auflagefläche
    if stripes == "waagrecht":
        n = max(2, int(round(band_w / 2.4)))             # 3 Rillen bei 7.8 mm, 4 bei 9 mm
        pitch = band_w / (n + 1)
        rings = []
        for k in range(n):
            y = -band_w / 2 + pitch * (k + 1)
            ann = CrossSection.circle(ro + 1) - CrossSection.circle(ro - STRIPE_D)
            g = Manifold.extrude(ann.translate((0, zc)), STRIPE_W).translate((0, 0, -STRIPE_W / 2)).rotate((90, 0, 0))
            rings.append(g.translate((0, y, 0)))
        cut = Manifold.batch_boolean(rings, OpType.Add)
        keep = Manifold.cube((lx + 2 * STRIPE_W, 40, 40)).translate((-lx / 2 - STRIPE_W, -20, zc))  # Sockelbereich
        floor = Manifold.cube((200, 40, STRIPE_D + 0.6)).translate((-100, -20, 0))                   # Auflage
        ring = ring - ((cut - keep) if lying else (cut - keep - floor))
    # Senkrechte Streifen (Rillen quer über den Reif), nicht unter dem Sockel
    if stripes == "senkrecht":
        cuts = []
        for k in range(STRIPES):
            a = 2 * np.pi * k / STRIPES
            x, z = ro * np.sin(a), zc + ro * np.cos(a)
            if abs(x) < lx / 2 + STRIPE_W and z > zc:      # vom Sockel verdeckt
                continue
            if not lying and z < STRIPE_D + 0.6:            # stehend: Auflagefläche unten frei lassen
                continue
            g = Manifold.cube((STRIPE_W, band_w + 2, STRIPE_D * 2)).translate((-STRIPE_W / 2, -band_w / 2 - 1, -STRIPE_D))
            g = g.rotate((0, -np.degrees(a), 0)).translate((x, 0, z))
            cuts.append(g)
        if cuts:
            ring = ring - Manifold.batch_boolean(cuts, OpType.Add)

    # Tentakel: wachsen unter dem Sockel hervor und winden sich um den Reif (flaches Relief)
    if stripes == "tentakel":
        ring = ring + tentacles(ro, zc, band_w, lx)
        if not lying:
            ring = ring ^ Manifold.cube((200, 200, 200)).translate((-100, -100, 0))

    # Noppen
    studs = []
    for i in range(nx):
        for j in range(ny):
            x = (i - (nx - 1) / 2) * PITCH
            y = (j - (ny - 1) / 2) * PITCH
            r = stud_d / 2
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
    if lying and orient:
        ring = ring.rotate((90, 0, 0))                   # Ringachse Y -> Z, Noppen zeigen nach -Y
        ring = ring.translate((0, 0, -ring.bounding_box()[2]))
    return ring


def to_tm(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)


NAMED_SIZES = {15: "klein", 17: "mittel", 20: "gross"}   # Innendurchmesser -> Bezeichnung


def passtest():
    """Passungstest liegend: drei 1x1-Ringe (17 mm) mit Noppen-Ø 4.85 / 4.90 / 4.95,
    gekennzeichnet mit 1 / 2 / 3 Punkten oben auf dem Sockel. Eine Platte, ~10 min Druck."""
    out = ROOT / "3d-druck/noppen-ring/passtest"
    out.mkdir(parents=True, exist_ok=True)
    ri = 17 / 2; ro = ri + BAND; zc = ro - FLAT
    rings = []
    for k, d in enumerate((4.85, 4.90, 4.95), 1):
        m = build("1x1", 17, "glatt", stud_d=d)
        top = m.bounding_box()[5]
        yc = -(zc + ro + 0.9)                           # flache Sockeloberseite außerhalb des Reifs
        dots = [Manifold.cylinder(0.6, 0.5, 0.5, 32).translate(((j - (k - 1) / 2) * 1.7, yc, top - 0.5)) for j in range(k)]
        m = m - Manifold.batch_boolean(dots, OpType.Add)
        tm = to_tm(m)
        check(tm, f"passtest_{k}_noppe-{d:.2f}", (180, 180, 180))
        tm.export(out / f"noppen-ring_passtest-{k}_noppe-{d:.2f}mm.stl")
        rings.append(m.translate(((k - 2) * 26.0, 0, 0)))
    plate = Manifold.batch_boolean(rings, OpType.Add)
    tm = to_tm(plate)
    check(tm, "passtest_alle-3", (180, 180, 180))
    tm.export(out / "noppen-ring_passtest_alle-3.stl")
    preview({"t": tm}, out / "noppen-ring_passtest.png", colors={"t": "#E8452C"})


def main():
    """Standard: Kinder/Frauen/Männer. Mit --alle: 16–20 mm in alle-groessen/. Zahlen = eigene Größen."""
    if "--passtest" in sys.argv:
        return passtest()
    base = ROOT / "3d-druck/noppen-ring"
    alle = "--alle" in sys.argv
    out = base / "alle-groessen" if alle else base
    out.mkdir(parents=True, exist_ok=True)
    only = [a for a in sys.argv[1:] if a in VARIANTS]
    sizes = [int(a) for a in sys.argv[1:] if a.isdigit()] or (SIZES if alle else list(NAMED_SIZES))
    shown = {}
    for v in only or VARIANTS:
        for d in sizes:
            for stripes in ("glatt", "senkrecht", "tentakel"):   # „waagrecht“ auf Wunsch entfernt (Muster bleibt im Code)
                m = build(v, d, stripes)
                tm = to_tm(m)
                label = f"{NAMED_SIZES[d]}-{d}mm" if (d in NAMED_SIZES and not alle) else f"{d}mm"
                name = f"noppen-ring_{v}_{stripes}_{label}"
                probs = check(tm, name, (180, 180, 180))
                parts = len(m.decompose())
                if parts != 1:
                    print(f"  !! {parts} Körper")
                tm.export(out / f"{name}.stl")
                if d == 17:
                    shown[f"{v}_{stripes}"] = tm
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
                colors={k: {"glatt": "#E8452C", "senkrecht": "#2a6fd6", "waagrecht": "#2e9e4f", "tentakel": "#8e44ad"}[k.split("_")[-1]] for k in layout})


if __name__ == "__main__":
    main()
