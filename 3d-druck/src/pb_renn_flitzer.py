"""Printer Brothers Renn-Flitzer – flacher Sportwagen mit mitgedruckten, rollenden Rädern.

Eigenes Design (kein reales Automodell), etwa Hot-Wheels-Größe (75 x 30 mm).
Gedruckt auf der SEITE liegend (Druck-Z = Autobreite):
  - Je Achse ein starres Teil (Rad + Achse + Rad), läuft in einer senkrechten Bohrung
  - 45°-Schrägen statt Brücken zwischen Rad und Karosserie -> keine Stützen, nichts verklebt
  - 2 Farben: Karosserie + Räder

Aufruf:  python3 3d-druck/src/pb_renn_flitzer.py
"""
import sys
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold, OpType, set_circular_segments

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude/skills/stl-designer/scripts"))
from stl_tools import check, export_parts, preview  # noqa: E402

set_circular_segments(96)

# ---------------------------------------------------------------- Parameter (Auto-Koordinaten: x Länge, h Höhe)
L = 75.0          # Länge
W = 30.0          # Breite (= Druck-Z)
BELT = 11.6       # Gürtellinie: darüber die eingezogene Kabine
UNDER = 2.4       # Bodenfreiheit Karosserie
CHAMFER = 1.0     # Kantenfase an beiden Seiten
LAYER = 0.2

R_W = 5.5         # Radradius (Ø 11 mm)
T_W = 4.6         # Radbreite
R_AX = 1.8        # Achse
CL = 0.45         # radiales Spiel Achse/Bohrung
GAP_R = 0.6       # radiales Spiel Rad/Radhaus
GZ = 0.6          # vertikales Spiel an den 45°-Schrägen
WHEELS_X = (15.0, 60.0)
WHEEL_H = R_W     # Radmitte (Rad steht auf dem Boden)

R_ARCH = R_W + GAP_R
# Steck-Version (python3 ... --steck): Karosserie und Räder getrennt drucken, Räder auf Achse pressen
STECK = "--steck" in sys.argv
GZ_STECK = 0.5     # Spalt Radinnenseite/Karosserie
AX_FLAT = 1.35     # D-Achse: flache Seite 1.35 mm unter der Mitte (Druckauflage + Verdrehschutz)
WHEEL_PRESS = 0.05 # Rad-Loch im Modell 0.05 mm größer; gedruckte Löcher werden ~0.1 kleiner -> Presssitz
FENDER = 1.4      # Kotflügel-Wandstärke über dem Rad
D_FENDER = 7.0    # Kotflügelbreite von der Seite aus; danach 45° zur Haube abfallend
NOSE_TAPER = 4.0  # Nase/Heck in der Draufsicht 45° angeschrägt
TAIL_TAPER = 2.5
R_BORE = R_AX + CL
Z_F0 = T_W + GZ                       # Unterkante Karosserie über dem unteren Rad
Z_TOP0 = W - T_W - (R_W - R_AX)       # Beginn der Kegel-Innenseite des oberen Rads


# ---------------------------------------------------------------- Helfer
def poly(pts):
    cs = CrossSection([pts])
    return cs if cs.area() > 0 else CrossSection([pts[::-1]])


def chaikin(pts, n=3, keep=()):
    pts = [np.array(p, float) for p in pts]
    for _ in range(n):
        out = []
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            if i in keep:
                out.append(a)
            out += [0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b]
        pts = out
        keep = ()
    return [tuple(p) for p in pts]


def ext(cs, h, z0=0.0):
    return Manifold.extrude(cs, h).translate((0, 0, z0))


def revolve(pts):
    return Manifold.revolve(poly(pts), 96)


def to_tm(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)


# ---------------------------------------------------------------- Silhouette (Seitenansicht)
def silhouettes():
    body = [
        (3.0, UNDER), (1.0, 4.2), (0.0, 7.2), (0.5, 9.8), (2.6, 10.9),       # Heck
        (13.0, 11.4), (21.0, 12.0),                                          # Heckdeck
        (29.0, 16.3), (37.0, 16.9), (44.0, 16.4),                            # Dach
        (54.0, 11.8),                                                        # Frontscheibe
        (63.0, 10.0), (70.0, 8.2), (74.3, 6.4), (75.0, 4.6), (74.0, 3.0),    # Haube, Nase
        (70.0, UNDER),                                                       # Frontsplitter
    ]
    body = chaikin(body, 3)
    body = [(x, max(h, UNDER)) for x, h in body]
    sil = poly(body) + poly([(4, UNDER), (70, UNDER), (70, UNDER + 2), (4, UNDER + 2)])
    # Seitenschweller-Einzug zwischen den Rädern (optisch flacher)
    sil = sil - poly([(22.5, UNDER - 1), (52.5, UNDER - 1), (52.5, UNDER + 0.9), (22.5, UNDER + 0.9)])
    # Heckflügel: Flügelblatt + Stützen
    wing = poly(chaikin([(0.2, 13.4), (11.0, 14.6), (11.4, 15.5), (0.6, 14.9)], 2))
    posts = [poly([(3.0, 10.6), (4.4, 10.6), (5.0, 14.4), (3.6, 14.2)]),
             poly([(8.0, 11.0), (9.4, 11.0), (9.8, 14.9), (8.4, 14.7)])]
    return sil, wing, posts


# ---------------------------------------------------------------- Karosserie
def build_body():
    sil, wing, posts = silhouettes()
    lower = sil ^ poly([(-5, -5), (L + 5, -5), (L + 5, BELT), (-5, BELT)])
    cabin = sil - lower
    # Kotflügel lang gezogen (Hülle zweier Kreise) -> weiche, sportliche Linie
    fenders = CrossSection.batch_boolean(
        [CrossSection.batch_hull([CrossSection.circle(R_ARCH + FENDER).translate((x + dx, WHEEL_H - abs(dx) * 0.25))
                                  for dx in (-7.0, 0.0, 7.0)]) for x in WHEELS_X], OpType.Add)
    fenders = fenders ^ poly([(-5, UNDER), (L + 5, UNDER), (L + 5, 40), (-5, 40)])
    f_top = WHEEL_H + R_ARCH + FENDER
    slices = []
    n = int(round(W / LAYER))
    for i in range(n):
        z = i * LAYER
        zc = z + LAYER / 2
        edge = min(zc, W - zc)                         # Abstand zur nächsten Seite
        inset = max(0.0, CHAMFER - edge)               # Kantenfase
        # Kotflügel: außen volle Höhe, zur Mitte 45° abfallend
        hlim = f_top + 1 if edge <= D_FENDER else f_top - (edge - D_FENDER)
        cs = lower + (fenders ^ poly([(-5, -5), (L + 5, -5), (L + 5, hlim), (-5, hlim)]))
        cs = cs.offset(3.0, JoinType.Round).offset(-3.0, JoinType.Round)   # weiche Übergänge
        # Draufsicht: Nase und Heck an den Ecken 45° angeschrägt
        x0 = max(0.0, TAIL_TAPER - edge)
        x1 = L - max(0.0, NOSE_TAPER - edge)
        cs = cs ^ poly([(x0, -5), (x1, -5), (x1, 40), (x0, 40)])
        cs = cs.offset(-inset, JoinType.Round) if inset > 0 else cs
        # Kabine 45° eingezogen (Tumblehome) -> druckbar ohne Überhang
        hmax = BELT + max(0.0, edge - 0.4)
        cab = cabin ^ poly([(-5, BELT - 0.01), (L + 5, BELT - 0.01), (L + 5, hmax), (-5, hmax)])
        if inset > 0:
            cab = cab.offset(-inset, JoinType.Round)
        slices.append(ext(cs + cab, LAYER + 0.02, z))
    body = Manifold.batch_boolean(slices, OpType.Add)
    # Heckflügel über die ganze Breite, Stützen nur an zwei Stellen
    body = body + ext(wing, W - 2 * 0.4, 0.4)
    for zp in (5.0, W - 5.0 - 3.0):
        for p in posts:
            body = body + ext(p, 3.0, zp)
    if STECK:
        # Steck-Version: Räder werden separat gedruckt -> unten 45°-Trichter (druckbar ohne Rad
        # darunter), oben einfaches Radhaus, durchgehende Bohrung für die Achse
        for x in WHEELS_X:
            z0 = T_W + GZ_STECK
            bottom_cut = revolve([(0, -1), (R_ARCH, -1), (R_ARCH, z0), (R_BORE, z0 + (R_ARCH - R_BORE)),
                                  (0, z0 + (R_ARCH - R_BORE))])
            top_cut = Manifold.cylinder(T_W + GZ_STECK + 1, R_ARCH, R_ARCH, 96).translate((0, 0, W - T_W - GZ_STECK))
            bore = Manifold.cylinder(W + 4, R_BORE, R_BORE, 96).translate((0, 0, -2))
            body = body - (bottom_cut + top_cut + bore).translate((x, WHEEL_H, 0))
        return body
    # Radhäuser: unten Trichter (45°), oben Kegel passend zum Rad, Bohrung für die Achse
    for x in WHEELS_X:
        bottom_cut = revolve([(0, -1), (R_ARCH, -1), (R_ARCH, Z_F0), (R_BORE, Z_F0 + (R_ARCH - R_BORE)),
                              (0, Z_F0 + (R_ARCH - R_BORE))])
        zc = lambda r: Z_TOP0 + (r - R_AX) - GZ
        top_cut = revolve([(0, W + 1), (0, zc(R_BORE)), (R_BORE, zc(R_BORE)), (R_ARCH, zc(R_ARCH)), (R_ARCH, W + 1)])
        bore = Manifold.cylinder(W + 4, R_BORE, R_BORE, 96).translate((0, 0, -2))
        cut = (bottom_cut + top_cut + bore).translate((x, WHEEL_H, 0))
        body = body - cut
    return body


# ---------------------------------------------------------------- Räder (je Achse ein Teil)
def build_axle():
    prof = [(0, 0), (R_W - 0.4, 0), (R_W, 0.4), (R_W, T_W), (R_AX, T_W),
            (R_AX, Z_TOP0), (R_W, Z_TOP0 + (R_W - R_AX)), (R_W, W - 0.4), (R_W - 0.4, W), (0, W)]
    ax = revolve(prof)
    # Felgen-Optik: Rille + Nabe auf beiden Außenseiten
    for z0, z1 in ((-0.01, 0.4), (W - 0.4, W + 0.01)):
        ring = revolve([(3.0, z0), (3.7, z0), (3.7, z1), (3.0, z1)])
        hub = revolve([(0, z0), (1.0, z0), (1.0, z1), (0, z1)])
        ax = ax - ring - hub
    return ax


# ---------------------------------------------------------------- Steck-Version: Achse + 4 Räder
def d_profile(extra=0.0):
    """D-Querschnitt der Achse (flache Seite unten = Druckauflage, verhindert Verdrehen im Rad)."""
    r = R_AX + extra
    return CrossSection.circle(r) ^ CrossSection.square((4 * r, 2 * r)).translate((-2 * r, -AX_FLAT - extra))


def build_pin():
    """Achse entlang Z (Einbaulage), Länge W - 2*0.3, Enden angefast."""
    L_ax = W - 0.6
    core = Manifold.extrude(d_profile(), L_ax - 0.6).translate((0, 0, 0.3))
    tips = [Manifold.extrude(d_profile(-0.3), 0.31).translate((0, 0, 0.0)),
            Manifold.extrude(d_profile(-0.3), 0.31).translate((0, 0, L_ax - 0.31))]
    pin = Manifold.batch_hull([core, tips[0]]) + Manifold.batch_hull([core, tips[1]])
    return pin.translate((0, 0, 0.3))


def build_wheel():
    """Rad, Außenseite bei z=0 (wird so auf dem Bett gedruckt), D-Loch mit Presssitz."""
    wh = revolve([(0, 0), (R_W - 0.4, 0), (R_W, 0.4), (R_W, T_W - 0.4), (R_W - 0.4, T_W), (0, T_W)])
    wh = wh - revolve([(3.0, -0.01), (3.7, -0.01), (3.7, 0.4), (3.0, 0.4)])          # Felgenrille außen
    hole = Manifold.extrude(d_profile(WHEEL_PRESS), T_W + 2).translate((0, 0, -1))
    lead = Manifold.extrude(d_profile(WHEEL_PRESS + 0.3), 0.31).translate((0, 0, T_W - 0.3))  # Einführfase innen
    return wh - hole - lead


def main_steck():
    out = ROOT / "3d-druck"
    body = build_body()
    pin, wheel = build_pin(), build_wheel()
    # Einbaulage: Rad unten (Außenseite z=0), Rad oben gewendet (Außenseite z=W)
    w_bot = wheel
    w_top = wheel.rotate((0, 180, 0)).translate((0, 0, W))   # um Y wenden: D-Fläche bleibt unten
    asm_w, asm_p = [], []
    for x in WHEELS_X:
        asm_w += [w_bot.translate((x, WHEEL_H, 0)), w_top.translate((x, WHEEL_H, 0))]
        asm_p.append(pin.translate((x, WHEEL_H, 0)))
    wheels = Manifold.batch_boolean(asm_w, OpType.Add)
    pins = Manifold.batch_boolean(asm_p, OpType.Add)

    print("== Prüfung Steck-Version ==")
    print(f"  Karosserie: {len(body.decompose())} Körper")
    for name, part, need in (("Räder", wheels, 0.35), ("Achsen", pins, 0.35)):
        inter = (body ^ part).volume(); gap = body.min_gap(part, 2.0)
        print(f"  Karosserie/{name}: Überschneidung {inter:.4f} mm³, min. Spalt {gap:.2f} mm  {'OK' if inter < 1e-3 and gap >= need else '!!'}")
    press = (wheels ^ pins).volume()
    print(f"  Presssitz Rad/Achse: {press:.2f} mm³ Überdeckung (gewollt, {WHEEL_PRESS:+.2f} mm im Modell)")
    print(f"  Achse im Rad: {T_W - 0.3:.1f} mm Steckweg je Seite, Achsenden 0,3 mm versenkt")

    # Druck 1: Karosserie (liegt auf der Seite)
    bb = body.bounding_box()
    body_p = body.translate((90 - (bb[0] + bb[3]) / 2, 90 - (bb[1] + bb[4]) / 2, 0))
    # Druck 2: 4 Räder (Außenseite unten) + 2 Achsen (liegend, flache Seite unten)
    plate = []
    for k in range(4):
        plate.append(wheel.translate((70 + (k % 2) * 16, 80 + (k // 2) * 16, 0)))
    # Achse liegend: entlang X, flache Seite (lokal -Y) nach unten (-Z)
    pin_lying = pin.rotate((0, 90, 0)).rotate((90, 0, 0))
    pb = pin_lying.bounding_box()
    for k in range(2):
        plate.append(pin_lying.translate((60 - pb[0], 115 + k * 8 - pb[1], -pb[2])))
    plate = Manifold.batch_boolean(plate, OpType.Add)
    export_parts({"einfarbig": to_tm(body_p)}, out / "pb-renn-flitzer-steck_druck1_karosserie",
                 write_preview=False, bed=(180, 180, 180))
    export_parts({"einfarbig": to_tm(plate)}, out / "pb-renn-flitzer-steck_druck2_raeder-achsen",
                 write_preview=False, bed=(180, 180, 180))
    to_car = lambda m: m.rotate((90, 0, 0))
    preview({"karosserie": to_tm(to_car(body)), "raeder": to_tm(to_car(wheels)), "achsen": to_tm(to_car(pins))},
            out / "pb-renn-flitzer-steck_vorschau.png",
            colors={"karosserie": "#FF7A2F", "raeder": "#2b2b2b", "achsen": "#9a9a9a"})
    return body, wheels, pins, plate


def main():
    if STECK:
        return main_steck()
    out = ROOT / "3d-druck"
    body = build_body()
    axle = build_axle()
    wheels = Manifold.batch_boolean([axle.translate((x, WHEEL_H, 0)) for x in WHEELS_X], OpType.Add)

    print("== Prüfung ==")
    print(f"  Karosserie: {len(body.decompose())} Körper, Räder: {len(wheels.decompose())} Achsen")
    inter = (body ^ wheels).volume()
    gap = body.min_gap(wheels, 2.0)
    print(f"  Karosserie/Räder: Überschneidung {inter:.4f} mm³, min. Spalt {gap:.2f} mm  {'OK' if inter < 1e-3 and gap >= 0.35 else '!!'}")
    for ang in (15, 45, 90):
        w = Manifold.batch_boolean([axle.rotate((0, 0, ang)).translate((x, WHEEL_H, 0)) for x in WHEELS_X], OpType.Add)
        print(f"  Räder um {ang}° gedreht: Überschneidung {(body ^ w).volume():.4f} mm³")
    # Bodenfreiheit im Fahrbetrieb: tiefster Karosseriepunkt über dem Boden (Druck-Y)
    print(f"  Bodenfreiheit Karosserie: {body.bounding_box()[1]:.1f} mm (Räder berühren den Boden bei 0)")

    # Druckanordnung: liegt bereits auf der Seite (Z = Breite); in die Bettmitte
    bb = (body + wheels).bounding_box()
    off = (90 - (bb[0] + bb[3]) / 2, 90 - (bb[1] + bb[4]) / 2, 0)
    body_p, wheels_p = body.translate(off), wheels.translate(off)
    export_parts({"karosserie": to_tm(body_p), "raeder": to_tm(wheels_p)}, out / "pb-renn-flitzer_75mm",
                 write_preview=False, bed=(180, 180, 180))

    # Vorschau in Fahrlage (Breite -> y, Höhe -> z)
    to_car = lambda m: m.rotate((90, 0, 0))   # Druck-Y (Höhe) -> Z, Druck-Z (Breite) -> -Y
    preview({"karosserie": to_tm(to_car(body)), "raeder": to_tm(to_car(wheels))},
            out / "pb-renn-flitzer_vorschau.png", colors={"karosserie": "#FF7A2F", "raeder": "#2b2b2b"})


if __name__ == "__main__":
    main()
