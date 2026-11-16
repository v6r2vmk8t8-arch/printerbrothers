"""Printer Brothers Kaffeebeutel-Klipp (Variante 2 mit angelenkter Hülse: --angelenkt) mit Schraub-Ausgießer und Logo-Deckel.

Eigenentwurf (Funktionsprinzip: Klemme + Ausgießer + Schraubdeckel).
Optimiert für Bambu Lab A1 mini (180 mm Bett), kurze Druckzeit:
  - Klipp 12 mm hoch, print-in-place Gelenk + Schnappverschluss, keine Stützen
  - Deckel kopfüber gedruckt, Logo als bündiges Inlay nur in den ersten 3 Schichten

Aufruf:  python3 3d-druck/src/pb_kaffeeklipp.py              (Version 1: lose Hülse)
         python3 3d-druck/src/pb_kaffeeklipp.py --angelenkt (Version 2: angelenkte Hülse)
"""
import re
import sys
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold, Mesh, set_circular_segments

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude/skills/stl-designer/scripts"))
from stl_tools import check, export_parts, preview  # noqa: E402

set_circular_segments(96)

# ---------------------------------------------------------------- Parameter
H = 14.0          # Höhe der Arme (Druck-Z)
G = 0.4           # Spalt zwischen den Klemmflächen (geschlossen)
W = 10.0          # Breite eines Arms
OPEN_DEG = 4.0    # Druckstellung: Arm B um 4° geöffnet (diagonal aufs Bett)

# Gelenk (print-in-place, 45°-Kegel statt Brücken)
R_K = 8.5         # Außenradius der Gelenkscheiben
R_PIN = 5.0       # Bolzen (Ø 10 mm)
CL = 0.4          # radiales Spiel
GZ = 0.6          # vertikales Spiel an den Kegeln
Z_A1 = 2.0        # Oberkante untere A-Scheibe (bei R_K)
Z_B2 = 11.2       # Oberkante B-Scheibe (bei R_K)

# Schnappverschluss (am Ende hinter dem Ausgießer, eingerahmt von massivem Endblock)
FINGER_T = 2.6    # Federfinger, freie Länge ~21 mm -> Dehnung < 0.9 %
BARB = 1.7        # Fangnase ragt 1.7 mm über die Spitze von Arm B (v2: +0.5 mm, hält sicherer)
BARB_RAMP = 2.7   # Höhe der Einlaufschräge (proportional zur Fangnase)
BULGE = 6.0       # Verstärkungsbalken unter dem Finger (6 x 14 mm)
END_L = 14.0      # Länge Endblock hinter Arm B

# Klemmring + Hülse (Folie wird rundum zwischen Hülse und Ring eingespannt)
R_SL_IN = 15.0    # Hülse innen (Ø 30 mm Öffnung)
R_TUBE = 17.4     # Hülse außen = Gewindekern
FILM = 0.4        # radialer Spalt für die Beutelfolie
R_CUP = R_TUBE + FILM   # Ring innen
R_RING = 24.0     # Ring außen
RIDGE_H = 0.9     # Halterippen auf der Hülse
RIDGE_Z = (4.5, 9.5)
SL_TOP = H + 12.0 # Oberkante Hülse
XR = 165.0        # Mitte Ring (Beutelecke) – Klemmlänge bis zur Ecke ~ 160 mm
XB = XR + 34.0    # Spitze Arm B (hinter dem Ring)

# Variante 2: angelenkte Hülse (python3 ... --angelenkt)
HINGED = "--angelenkt" in sys.argv
PIV = (XR - 34.0, -7.0)   # Drehachse auf Arm A (vor dem Ring)
R_PIV = 3.0               # Bolzen
LINK_Z0 = H + 1.0         # Steg 1 mm über dem Klipp (Arm B klappt darunter durch)
LINK_T = 2.8
if HINGED:
    SL_TOP = H + 15.0     # Gewinde beginnt oberhalb vom Steg

# Gewinde (2-gängig, Steigung 10 mm -> ca. halbe Umdrehung zum Schließen)
TH_DEPTH = 1.2
TH_LEAD = 10.0
TH_STARTS = 2
TH_CLEAR = 0.5    # radiales Spiel (Platz für die Beutelfolie)

# Deckel
CAP_PLATE_R = 28.0   # Ø 56 Logo-Platte
CAP_PLATE_T = 2.4
CAP_SKIRT_R = 23.6   # Außenradius Schraubrand
CAP_SKIRT_H = 9.0
INLAY = 0.6          # Logo-Inlay-Tiefe (3 Schichten à 0.2)
LOGO_R = 22.0        # Logo passt in diesen Radius


# ---------------------------------------------------------------- Helfer
def rect(x0, y0, x1, y1):
    return CrossSection([[(x0, y0), (x1, y0), (x1, y1), (x0, y1)]])


def poly(pts):
    cs = CrossSection([pts])
    if cs.area() == 0:
        cs = CrossSection([pts[::-1]])
    return cs


def circle(r, cx=0.0, cy=0.0):
    return CrossSection.circle(r).translate((cx, cy))


def rounded(cs, r):
    """Konvexe Ecken abrunden."""
    return cs.offset(-r, JoinType.Round).offset(r, JoinType.Round)


def ext(cs, h, z0=0.0):
    return Manifold.extrude(cs, h).translate((0, 0, z0))


def revolve_profile(pts):
    """pts: (r, z)-Polygon -> Rotationskörper um Z."""
    return Manifold.revolve(poly(pts), 96)


def prism_x(tri_yz, x0, x1):
    """Dreiecksprisma entlang X; tri_yz = [(y,z),...]."""
    cs = poly(tri_yz)
    m = Manifold.extrude(cs, x1 - x0)          # entlang Z
    # (y,z,x) -> (x,y,z): Z->X, X->Y, Y->Z
    M = [[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]]
    return m.transform(M)


def to_tm(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)


def thread(r_root, depth, z0, z1, inward=False, base_w=3.2, crest_w=0.8, steps_per_turn=120, fade_deg=60):
    """Helix-Gewinderippen als Manifold (mehrgängig), Enden auslaufend."""
    bodies = []
    turns = (z1 - z0) / TH_LEAD
    n = max(8, int(turns * steps_per_turn))
    sgn = -1.0 if inward else 1.0
    embed = 0.3
    for s in range(TH_STARTS):
        phase = 2 * np.pi * s / TH_STARTS
        verts, faces = [], []
        total = turns * 2 * np.pi
        for i in range(n + 1):
            t = i / n
            th = t * total
            z = z0 + t * (z1 - z0)
            # Auslauf an beiden Enden
            a = min(th, total - th)
            f = max(0.08, min(1.0, a / np.radians(fade_deg)))
            r0 = r_root - sgn * embed
            r1 = r_root + sgn * depth * f
            prof = [(r0, -base_w / 2), (r1, -crest_w / 2), (r1, crest_w / 2), (r0, base_w / 2)]
            c, si = np.cos(th + phase), np.sin(th + phase)
            for r, dz in prof:
                verts.append((r * c, r * si, z + dz))
        verts = np.array(verts)
        for i in range(n):
            a, b = 4 * i, 4 * (i + 1)
            for k in range(4):
                k2 = (k + 1) % 4
                faces.append((a + k, b + k, b + k2))
                faces.append((a + k, b + k2, a + k2))
        faces.append((0, 1, 2)); faces.append((0, 2, 3))
        e = 4 * n
        faces.append((e, e + 2, e + 1)); faces.append((e, e + 3, e + 2))
        faces = np.array(faces)
        tm = trimesh.Trimesh(verts, faces, process=True)
        if tm.volume < 0:
            tm.invert()
        bodies.append(Manifold(Mesh(vert_properties=np.asarray(tm.vertices, np.float32),
                                    tri_verts=np.asarray(tm.faces, np.uint32))))
    return Manifold.batch_boolean(bodies, __import__("manifold3d").OpType.Add)


def elephant_foot(m, inset=0.25, h=0.4):
    """Erste 0.4 mm leicht einrücken (gegen Elefantenfuß / Verkleben im Gelenk)."""
    sec = m.slice(h / 2)
    bottom = ext(sec.offset(-inset, JoinType.Round), h + 0.05)
    top = m.trim_by_plane((0, 0, 1), h)
    return top + bottom


# ---------------------------------------------------------------- Klipp
def build_clip():
    hole = circle(R_K + CL)
    spout_hole = circle(R_CUP, XR)
    y_a = -G / 2 - W          # Außenkante Arm A
    y_b = G / 2 + W           # Außenkante Arm B
    half_a = rect(-50, -100, 400, -G / 2)
    half_b = rect(-50, G / 2, 400, 100)

    # --- Gelenk
    a_hinge = revolve_profile([(0, 0), (R_K, 0), (R_K, Z_A1), (R_PIN, Z_A1 + (R_K - R_PIN)),
                               (R_PIN, Z_B2 + GZ - (R_K - R_PIN)), (R_K, Z_B2 + GZ), (R_K, H), (0, H)])
    zb1 = Z_A1 + GZ
    rh = R_PIN + CL
    b_hinge = revolve_profile([(rh, zb1 + (R_K - rh)), (R_K, zb1), (R_K, Z_B2), (rh, Z_B2 - (R_K - rh))])

    # --- Arm A (y<0): Arm + halber Ausgießer-Ring + Verstärkung + Endblock
    y_out = y_a - BULGE
    xf0, xf1 = XB + 0.6, XB + 0.6 + FINGER_T
    x_blk = xf1 + 2.0   # Ausweichraum für den Federfinger
    x_end = XB + END_L
    base = rect(0, y_a, x_end, -G / 2)
    base = base + (circle(R_RING, XR) ^ half_a)
    base = base + poly([(XB - 16, y_a), (XB - 4, y_out), (x_end, y_out), (x_end, y_a)])
    base = base + rect(x_blk, y_out, x_end, y_b - 2.0)
    base = base.offset(3.0, JoinType.Round).offset(-3.0, JoinType.Round)   # Hohlkehlen
    base = rounded(base, 1.5) ^ (half_a + rect(x_blk - 1, -100, 400, 100))
    # Tasche für den Federfinger (Finger hängt nur am 6-mm-Balken)
    base = base - rect(XB, y_a, x_blk, 100)
    yc = y_b + 0.15                                # Fangkante
    y_tip = yc + BARB_RAMP + 3.0
    finger = rect(xf0, y_a - 0.05, xf1, y_tip)
    barb = poly([(xf0 + 0.01, yc), (XB - BARB, yc), (xf0 + 0.01, yc + BARB_RAMP)])
    knob = rounded(rect(xf0, y_tip - 3.0, xf1 + 1.2, y_tip), 0.5)
    fillets = poly([(xf0, y_a + 1.6), (xf0, y_a + 0.01), (XB + 0.05, y_a + 0.01)]) + \
        poly([(xf1, y_a + 1.4), (xf1, y_a + 0.01), (xf1 + 1.4, y_a + 0.01)])
    a_2d = base + finger + barb + knob + fillets - spout_hole
    a_arm = ext(a_2d - hole, H)
    a_band2d = (rect(0, y_a, R_K + CL + 1, -G / 2) - circle(R_K - 0.05)) ^ circle(R_K + CL + 1)
    a_band = ext(a_band2d, Z_A1) + ext(a_band2d, H - Z_B2 - GZ, Z_B2 + GZ)
    A = a_arm + a_hinge + a_band

    # --- Arm B (y>0): Arm + halber Ausgießer-Ring
    bb2 = rect(0, G / 2, XB, y_b) + (circle(R_RING, XR) ^ half_b)
    bb2 = bb2.offset(3.0, JoinType.Round).offset(-3.0, JoinType.Round)
    bb2 = rounded(bb2, 1.5) ^ rect(-50, G / 2, XB, 100)
    # Spitze außen scharfkantig (Fangfläche), nur 0.3 mm Fase
    bb2 = bb2 + (rect(XB - 6, G / 2 + 1.5, XB, y_b) - poly([(XB - 0.3, y_b + 1), (XB + 1, y_b + 1), (XB + 1, y_b - 0.3 - 1.3), (XB, y_b - 0.3)]))
    b_2d = bb2 - spout_hole
    b_full = ext(b_2d - hole, H)
    b_band2d = (b_2d ^ circle(R_K + CL + 0.5)) - circle(R_K - 0.05)
    b_band = ext(b_band2d, Z_B2 - zb1, zb1)
    B = b_full + b_band + b_hinge

    if HINGED:
        ear = CrossSection.hull(circle(8.5, *PIV) + rect(PIV[0] - 16, y_a, PIV[0] + 16, -G / 2)) ^ half_a
        ear = ear.offset(2.5, JoinType.Round).offset(-2.5, JoinType.Round) ^ half_a
        A = A + ext(ear, H)
        bore = revolve_profile([(0, -0.01), (R_PIV + 2.0 + 0.55, -0.01), (R_PIV + 0.4, 2.0 + 0.55 - 0.4 + 0.01),
                                (R_PIV + 0.4, H + 0.01), (0, H + 0.01)])
        A = A - bore.translate((PIV[0], PIV[1], 0))
        # Einlauffase an der Ringkante (Hülse dreht hier leicht nach -x aus)
        xe = XR - R_CUP
        lead = poly([(xe + 0.6, -G / 2 - 2.6), (xe - 2.2, -G / 2 + 0.01), (xe + 0.6, -G / 2 + 0.01)])
        A = A - ext(lead, H + 2, -1)

    # --- Klemmprofil: V-Nut in A, V-Rippe an B (nicht im Ausgießer-Loch)
    zc = H / 2
    no_hole = ext(circle(R_CUP + 0.6, XR), H + 2, -1)
    groove = prism_x([(-G / 2 + 0.3, zc - 1.9), (-G / 2 - 1.6, zc), (-G / 2 + 0.3, zc + 1.9)], R_K + 1.5, XB - 2.0)
    rib = prism_x([(G / 2 + 0.3, zc - 1.6), (G / 2 - 1.3, zc), (G / 2 + 0.3, zc + 1.6)], R_K + 3.0, XB - 4.0) - no_hole
    A = A - groove
    B = B + rib

    # --- Nuten für die Halterippen der Hülse + Einlauffasen (beide Ringhälften)
    cut = Manifold()
    for zr in RIDGE_Z:
        d = RIDGE_H + 0.45
        cut = cut + revolve_profile([(R_CUP - 0.01, zr - d - 0.2), (R_CUP + d, zr), (R_CUP - 0.01, zr + d + 0.2)])
    cut = cut + revolve_profile([(R_CUP - 0.01, -0.01), (R_CUP + 1.2, -0.01), (R_CUP - 0.01, 1.2)])
    cut = cut + revolve_profile([(R_CUP - 0.01, H + 0.01), (R_CUP + 1.2, H + 0.01), (R_CUP - 0.01, H - 1.2)])
    cut = cut.translate((XR, 0, 0))
    A = A - cut
    B = B - cut

    A = elephant_foot(A)
    B = elephant_foot(B)
    return A, B


# ---------------------------------------------------------------- Hülse
def build_sleeve():
    """Hülse in Einbaulage (Unterkante z=0 = Unterkante Klipp)."""
    sl = revolve_profile([(R_SL_IN, 0), (R_TUBE - 0.8, 0), (R_TUBE, 0.8), (R_TUBE, SL_TOP - 0.8),
                          (R_TUBE - 0.8, SL_TOP), (R_SL_IN + 0.8, SL_TOP), (R_SL_IN, SL_TOP - 0.8),
                          (R_SL_IN, 0.8), (R_SL_IN + 0.8, 0)][::-1])
    for zr in RIDGE_Z:
        sl = sl + revolve_profile([(R_TUBE - 0.2, zr - RIDGE_H - 0.2), (R_TUBE + RIDGE_H, zr), (R_TUBE - 0.2, zr + RIDGE_H + 0.2)])
    th_z0 = (LINK_Z0 + LINK_T + 2.4) if HINGED else H + 2.6
    sl = sl + thread(R_TUBE, TH_DEPTH, th_z0, SL_TOP - 2.6)
    if HINGED:
        px, py = PIV[0] - XR, PIV[1]
        pin = revolve_profile([(0, 0), (R_PIV + 2.0, 0), (R_PIV, 2.0), (R_PIV, LINK_Z0 + LINK_T), (0, LINK_Z0 + LINK_T)])
        u = np.array([px, py]) / np.hypot(px, py)
        link = CrossSection.hull(circle(5.0, px, py) + circle(7.0, *(u * (R_TUBE - 3.0))))
        link = rounded(link, 1.0) - circle(R_SL_IN)
        sl = sl + pin.translate((px, py, 0)) + ext(link, LINK_T, LINK_Z0)
        sl = elephant_foot(sl)
    return sl


# ---------------------------------------------------------------- Logo
def load_logo():
    s = (ROOT / "public/brand/pb-icon.svg").read_text()
    groups = {}
    for fill, d in re.findall(r'<path fill="(#[0-9A-Fa-f]{6})" d="([^"]+)"', s):
        polys = []
        for sub in re.split(r"[Zz]", d):
            pts = re.findall(r"(-?[\d.]+),(-?[\d.]+)", sub)
            if len(pts) >= 3:
                polys.append([(float(x), 256 - float(y)) for x, y in pts])
        groups[fill.upper()] = polys
    green = CrossSection(groups["#39FF14"])
    white = CrossSection(groups["#EDEDED"])
    pts = np.vstack([np.array(p) for g in groups.values() for p in g])
    # kleinster umschließender Kreis (Näherung über Raster)
    best = None
    for cx in np.linspace(pts[:, 0].min(), pts[:, 0].max(), 60):
        for cy in np.linspace(pts[:, 1].min(), pts[:, 1].max(), 60):
            r = np.hypot(pts[:, 0] - cx, pts[:, 1] - cy).max()
            if best is None or r < best[0]:
                best = (r, cx, cy)
    r, cx, cy = best
    sc = LOGO_R / r
    green = green.translate((-cx, -cy)).scale((sc, sc))
    white = white.translate((-cx, -cy)).scale((sc, sc))
    return green, white, sc


# ---------------------------------------------------------------- Deckel
LIP_INTERF = 0.15   # Übermaß der Dichtlippe (radial)
LIP_WALL = 0.9      # Wandstärke (2 Linien) – gibt nach und legt sich rundum an
LIP_H = 3.0         # Höhe der Lippe
LIP_STRAIGHT = 1.8  # gerader Dichtbereich, danach Einführschräge


def seal_lip():
    """Ring an der Deckel-Innenseite (z=CAP_SKIRT_H), ragt LIP_H nach unten in die Hülse."""
    z0 = CAP_SKIRT_H + 0.3                 # 0.3 in die Deckelplatte eingebettet
    r_out = R_SL_IN + LIP_INTERF            # Dichtbereich
    r_tip = R_SL_IN - 0.4                   # Spitze kleiner als die Öffnung -> findet selbst hinein
    zs = CAP_SKIRT_H - LIP_STRAIGHT
    zt = CAP_SKIRT_H - LIP_H
    return revolve_profile([(r_out - LIP_WALL, z0), (r_out, z0), (r_out, zs), (r_tip, zt),
                            (r_tip - LIP_WALL + 0.3, zt), (r_out - LIP_WALL, zs + 0.3)])


def build_cap():
    """Deckel in Gebrauchslage modelliert: Schraubrand unten (z=0), Logo-Platte oben."""
    green, white, sc = load_logo()
    # Streifen-Lücken leicht verbreitern -> sauber druckbar mit 0.4er Düse
    green = green.offset(-0.06, JoinType.Miter)
    white = white.offset(-0.06, JoinType.Miter)
    ring_line = circle(LOGO_R + 3.0) - circle(LOGO_R + 2.0)
    green = green + ring_line

    r_bore = R_TUBE + TH_DEPTH + TH_CLEAR          # Gewindegrund Deckel
    z_top = CAP_SKIRT_H + CAP_PLATE_T
    # Griffrand mit Rillen
    skirt2d = circle(CAP_SKIRT_R)
    for i in range(24):
        a = 2 * np.pi * i / 24
        skirt2d = skirt2d - circle(0.9, CAP_SKIRT_R * np.cos(a) + 0.2 * np.cos(a), CAP_SKIRT_R * np.sin(a))
    skirt = ext(skirt2d - circle(r_bore), CAP_SKIRT_H)
    plate2d = circle(CAP_PLATE_R)
    for i in range(16):
        a = 2 * np.pi * i / 16
        plate2d = plate2d - circle(1.6, (CAP_PLATE_R + 0.9) * np.cos(a), (CAP_PLATE_R + 0.9) * np.sin(a))
    plate = ext(rounded(plate2d, 0.5), CAP_PLATE_T, CAP_SKIRT_H)
    cap = skirt + plate
    th = thread(r_bore, TH_DEPTH, 2.2, CAP_SKIRT_H - 0.6, inward=True)
    cap = cap + th
    # Einlauffase unten innen
    cap = cap - revolve_profile([(r_bore - 0.01, -0.01), (r_bore + 1.0, -0.01), (r_bore - 0.01, 1.0)])
    # Außenkante der Logo-Seite leicht fasen (liegt auf dem Bett)
    cap = cap - revolve_profile([(CAP_PLATE_R + 2, z_top + 0.01), (CAP_PLATE_R - 0.6, z_top + 0.01), (CAP_PLATE_R + 2, z_top - 2.6)])
    # Dichtlippe: dünner Ring, wird mit leichtem Übermaß in die Hülsenöffnung gepresst
    cap = cap + seal_lip()

    g = ext(green, INLAY, z_top - INLAY)
    w = ext(white, INLAY, z_top - INLAY)
    base = cap - g - w
    engraved = cap - ext(green + white, 0.4, z_top - 0.4)
    return base, g, w, engraved


def flip_for_print(m):
    """Logo-Seite nach unten (Rotation, keine Spiegelung)."""
    m = m.rotate((180, 0, 0))
    return m


# ---------------------------------------------------------------- Prüfungen
def checks(A, B, sleeve, base, g, w):
    print("\n== Kollisions-/Spielprüfung ==")
    ok = True
    sl = sleeve.translate((XR, 0, 0))
    for ang in [0, 2, 4, 10, 20, 30]:
        Bt = B.rotate((0, 0, ang))
        # Verschlussbereich separat: dort überdeckt der Schnapper beim Einrasten absichtlich
        rest = A.trim_by_plane((-1, 0, 0), -(XB - 3))
        inter = (rest ^ Bt).volume() + (sl ^ Bt).volume()
        gap = min(rest.min_gap(Bt, 2.0), sl.min_gap(Bt, 2.0))
        latch = (A ^ Bt).volume() - (rest ^ Bt).volume()
        flag = "OK" if inter < 1e-3 and gap >= 0.3 else "!!"
        ok &= flag == "OK"
        note = f", Schnapper überdeckt {latch:.1f} mm³ (rastet ein)" if latch > 1e-3 else ""
        print(f"  Arm B bei {ang:2d}° (Hülse eingesetzt): Überschneidung {inter:.4f} mm³, min. Spalt {gap:.2f} mm  {flag}{note}")
    v = (sl ^ A).volume()
    gap_sl = min(sl.min_gap(A, 2.0), sl.min_gap(B, 2.0))
    print(f"  Hülse im Ring: Überschneidung {v:.4f} mm³, Folienspalt {gap_sl:.2f} mm  {'OK' if v < 1e-3 and gap_sl >= 0.3 else '!!'}")
    if HINGED:
        Bopen = B.rotate((0, 0, 40))
        worst = None
        for ang in range(0, 121, 5):
            st = sl.translate((-PIV[0], -PIV[1], 0)).rotate((0, 0, ang)).translate((PIV[0], PIV[1], 0))
            v = (st ^ A).volume() + (st ^ Bopen).volume()
            gp = min(st.min_gap(A, 2.0), st.min_gap(Bopen, 2.0))
            if worst is None or (v, -gp) > (worst[0], -worst[1]):
                worst = (v, gp, ang)
            if v > 1e-3:
                print(f"    Schwenk {ang}°: Überschneidung {v:.2f} mm³")
        print(f"  Hülse ausschwenken 0–120° (Arm B offen): max. Überschneidung {worst[0]:.4f} mm³, "
              f"min. Spalt {worst[1]:.2f} mm (bei {worst[2]}°)  {'OK' if worst[0] < 1e-3 else '!!'}")
        ok &= worst[0] < 1e-3
    cap = base + g + w
    z_off = SL_TOP - CAP_SKIRT_H
    lip = seal_lip()
    # Kollision ohne Lippe prüfen (die Lippe hat absichtlich Übermaß)
    cap_wo_lip = cap - Manifold.cylinder(LIP_H, R_SL_IN + 0.5, R_SL_IN + 0.5, 96).translate((0, 0, CAP_SKIRT_H - LIP_H))
    best = None
    for phi in range(0, 180, 6):
        c = cap_wo_lip.rotate((0, 0, phi)).translate((XR, 0, z_off + 0.05))
        v = (sl ^ c).volume() + ((A + B) ^ c).volume()
        best = min(best, (v, phi)) if best else (v, phi)
    print(f"  Deckel auf Hülse (ohne Lippe): min. Überschneidung {best[0]:.4f} mm³  {'OK' if best[0] < 1e-3 else '!!'}")
    press = (sl ^ lip.translate((XR, 0, z_off))).volume()
    ring_area = np.pi * ((R_SL_IN + LIP_INTERF) ** 2 - R_SL_IN ** 2)
    print(f"  Dichtlippe: Presssitz {press:.1f} mm³ (≈ {LIP_INTERF} mm Übermaß auf {press / ring_area:.1f} mm Höhe)  "
          f"{'OK' if 0 < press < 60 else '!!'}")
    return ok and best[0] < 1e-3


def place_free(clip, r, taken=()):
    """Freie Ecke für ein rundes Teil (Radius r) suchen."""
    probe = Manifold.cylinder(12, r + 0.5, r + 0.5, 96)
    best = None
    for x in np.arange(3 + r, 178 - r, 2.0):
        for y in np.arange(3 + r, 178 - r, 2.0):
            if any(np.hypot(x - tx, y - ty) < r + tr + 4 for tx, ty, tr in taken):
                continue
            gap = clip.min_gap(probe.translate((x, y, 0)), 6)
            if gap >= 4 and (best is None or np.hypot(x - 90, y - 90) > best[0]):
                best = (np.hypot(x - 90, y - 90), x, y)
    return best[1], best[2]


def main():
    out = ROOT / "3d-druck"
    A, B = build_clip()
    sleeve = build_sleeve()
    base, g, w, engraved = build_cap()
    checks(A, B, sleeve, base, g, w)

    # Druckanordnung (A1 mini, 180 x 180): Klipp diagonal, Deckel + Hülse in die freien Ecken
    if HINGED:
        A = A + sleeve.translate((XR, 0, 0))     # Hülse wird in der Ringhälfte mitgedruckt
    clip = (A + B.rotate((0, 0, OPEN_DEG))).rotate((0, 0, 45))
    bb = clip.bounding_box()
    clip = clip.translate((90 - (bb[0] + bb[3]) / 2, 90 - (bb[1] + bb[4]) / 2, 0))
    bb = clip.bounding_box()
    print(f"\nKlipp diagonal: {bb[3]-bb[0]:.1f} x {bb[4]-bb[1]:.1f} x {bb[5]-bb[2]:.1f} mm (Bett 180 x 180)")
    cx, cy = place_free(clip, CAP_PLATE_R)
    if not HINGED:
        r_sl = R_TUBE + TH_DEPTH + RIDGE_H
        sx, sy = place_free(clip, r_sl, taken=[(cx, cy, CAP_PLATE_R)])
        print(f"Deckel bei ({cx:.0f}, {cy:.0f}), Hülse bei ({sx:.0f}, {sy:.0f})")

    capparts = {k: flip_for_print(v) for k, v in {"schwarz": base, "gruen": g, "weiss": w}.items()}
    zmin = min(v.bounding_box()[2] for v in capparts.values())
    capparts = {k: v.translate((cx, cy, -zmin)) for k, v in capparts.items()}
    eng = flip_for_print(engraved)
    eng = eng.translate((cx, cy, -eng.bounding_box()[2]))
    pre = "pb-kaffeeklipp-1kg-angelenkt" if HINGED else "pb-kaffeeklipp-1kg"
    for f in out.glob(pre + "_*"):
        f.unlink()
    clip_tm = to_tm(clip)
    plate = {"schwarz": clip_tm}
    if HINGED:
        export_parts({"einfarbig": clip_tm}, out / f"{pre}_klipp-mit-huelse_225mm", bed=(180, 180, 180), write_preview=False)
    else:
        sl_tm = to_tm(sleeve.translate((sx, sy, 0)))
        export_parts({"einfarbig": clip_tm}, out / f"{pre}_klipp_225mm", bed=(180, 180, 180), write_preview=False)
        export_parts({"einfarbig": sl_tm}, out / f"{pre}_huelse_37mm", bed=(180, 180, 180), write_preview=False)
        plate["huelse"] = sl_tm
    export_parts({k: to_tm(v) for k, v in capparts.items()}, out / f"{pre}_deckel_56mm",
                 write_combined=False, write_preview=False, bed=(180, 180, 180))
    eng_tm = to_tm(eng)
    check(eng_tm, "deckel einfarbig (Logo graviert)", (180, 180, 180))
    eng_tm.export(out / f"{pre}_deckel_56mm_einfarbig.stl")

    plate.update({"deckel": to_tm(capparts["schwarz"]),
                  "gruen": to_tm(capparts["gruen"]), "weiss": to_tm(capparts["weiss"])})
    allm = trimesh.util.concatenate(list(plate.values()))
    print(f"\nDruckplatte gesamt: {np.round(allm.bounds[0],1)} .. {np.round(allm.bounds[1],1)}")
    preview(plate, out / f"{pre}_vorschau.png",
            colors={"schwarz": "#2b2b2b", "huelse": "#2b2b2b", "deckel": "#2b2b2b", "gruen": "#39ff14", "weiss": "#ededed"})

    asm = {"klipp": to_tm(A + B)} if HINGED else {"klipp": to_tm(A + B), "huelse": to_tm(sleeve.translate((XR, 0, 0)))}
    for k, v in {"deckel": base, "gruen": g, "weiss": w}.items():
        asm[k] = to_tm(v.translate((XR, 0, SL_TOP - CAP_SKIRT_H)))
    preview(asm, out / f"{pre}_montiert.png",
            colors={"klipp": "#2b2b2b", "huelse": "#6b6b6b", "deckel": "#3a3a3a", "gruen": "#39ff14", "weiss": "#ededed"})


if __name__ == "__main__":
    main()
