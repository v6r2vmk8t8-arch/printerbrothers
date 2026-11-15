"""Printer Brothers Kaffeebeutel-Klipp mit Schraub-Ausgießer und Logo-Deckel.

Eigenentwurf (Funktionsprinzip: Klemme + Ausgießer + Schraubdeckel).
Optimiert für Bambu Lab A1 mini (180 mm Bett), kurze Druckzeit:
  - Klipp 12 mm hoch, print-in-place Gelenk + Schnappverschluss, keine Stützen
  - Deckel kopfüber gedruckt, Logo als bündiges Inlay nur in den ersten 3 Schichten

Aufruf:  python3 3d-druck/src/pb_kaffeeklipp.py
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
XB = 172.0        # Länge Arm B (Gelenkachse bis Spitze) ~ Klemmlänge 163 mm (1-kg-Beutel)
OPEN_DEG = 4.0    # Druckstellung: Arm B um 4° geöffnet (diagonal aufs Bett)

# Gelenk (print-in-place, 45°-Kegel statt Brücken)
R_K = 8.5         # Außenradius der Gelenkscheiben
R_PIN = 5.0       # Bolzen (Ø 10 mm)
CL = 0.4          # radiales Spiel
GZ = 0.6          # vertikales Spiel an den Kegeln
Z_A1 = 2.0        # Oberkante untere A-Scheibe (bei R_K)
Z_B2 = 11.2       # Oberkante B-Scheibe (bei R_K)

# Schnappverschluss
FINGER_T = 3.0    # Dicke Federfinger (Dehnung < 0.9 %)
BARB = 1.2        # Hinterschnitt (Finger-Dehnung < 1 %)
BULGE = 4.0       # Verstärkung Arm A am Verschluss

# Ausgießer
R_IN = 16.0       # Innenradius (Ø 32 mm Öffnung)
R_RING = 22.0     # Außenradius Ring auf Armhöhe
R_TUBE = 18.4     # Außenradius Rohr (Gewindekern)
Z_TUBE = H + 12.0 # Oberkante Rohr
XR = XB + 4.8 + R_RING  # Mitte Ausgießer

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

    # --- Gelenk
    a_hinge = revolve_profile([(0, 0), (R_K, 0), (R_K, Z_A1), (R_PIN, Z_A1 + (R_K - R_PIN)),
                               (R_PIN, Z_B2 + GZ - (R_K - R_PIN)), (R_K, Z_B2 + GZ), (R_K, H), (0, H)])
    zb1 = Z_A1 + GZ
    rh = R_PIN + CL
    b_hinge = revolve_profile([(rh, zb1 + (R_K - rh)), (R_K, zb1), (R_K, Z_B2), (rh, Z_B2 - (R_K - rh))])

    # --- Arm A (unten, y<0)
    a_main = rect(0, -G / 2 - W, XB, -G / 2) - hole
    y_out = -G / 2 - W - BULGE
    strip = poly([(XB - 22, -G / 2 - W), (XB - 8, y_out), (XR, y_out), (XR, -G / 2 - W), ])
    xf0, xf1 = XB + 0.6, XB + 0.6 + FINGER_T
    yc = G / 2 + W + 0.15                       # Fangkante
    y_tip = yc + 1.9 + 2.6
    finger = rect(xf0, -G / 2 - W - 0.05, xf1, y_tip)
    barb = poly([(xf0 + 0.01, yc), (XB - BARB, yc), (xf0 + 0.01, yc + 1.9)])
    knob = rounded(rect(xf0, y_tip - 3.0, xf1 + 1.2, y_tip), 0.5)
    root = poly([(xf0 - 0.0, -G / 2 - W + 2.0), (xf0, -G / 2 - W), (XB + 0.05, -G / 2 - W)]) + \
        poly([(xf1, -G / 2 - W + 1.4), (xf1, -G / 2 - W), (xf1 + 1.4, -G / 2 - W)])
    neck = rect(xf1 + 1.6, y_out, XR, -G / 2)
    ring = circle(R_RING, XR) - circle(R_IN, XR)
    a_2d = rounded(a_main + strip + neck, 1.0) + finger + barb + knob + root + ring
    a_2d = a_2d - circle(R_IN, XR)
    a_arm = ext(a_2d, H)
    # Anbindung Gelenkscheiben an Arm A (nur unten/oben)
    a_band2d = (rect(0, -G / 2 - W, R_K + CL + 1, -G / 2) - circle(R_K - 0.05)) ^ circle(R_K + CL + 1)
    a_band = ext(a_band2d, Z_A1) + ext(a_band2d, H - Z_B2 - GZ, Z_B2 + GZ)
    A = a_arm + a_hinge + a_band

    # Nut in Klemmfläche A (V-Profil 45°)
    zc = H / 2
    groove = prism_x([(-G / 2 + 0.3, zc - 1.9), (-G / 2 - 1.6, zc), (-G / 2 + 0.3, zc + 1.9)], R_K + 1.5, XB - 2.0)
    A = A - groove

    # Ausgießer-Rohr + Gewinde
    tube = ext(circle(R_TUBE) - circle(R_IN), Z_TUBE - H, H).translate((XR, 0, 0))
    th = thread(R_TUBE, TH_DEPTH, H + 2.2, Z_TUBE - 2.6).translate((XR, 0, 0))
    A = A + tube + th
    # Fasen: Innenkante unten (Folie schonen) + Rohr-Oberkante
    cham_in = revolve_profile([(R_IN - 0.01, -0.01), (R_IN + 1.2, -0.01), (R_IN - 0.01, 1.2)]).translate((XR, 0, 0))
    cham_top = revolve_profile([(R_IN - 0.01, Z_TUBE + 0.01), (R_IN + 0.8, Z_TUBE + 0.01), (R_IN - 0.01, Z_TUBE - 0.8)]).translate((XR, 0, 0))
    cham_out = revolve_profile([(R_TUBE + 0.01, Z_TUBE + 0.01), (R_TUBE - 0.8, Z_TUBE + 0.01), (R_TUBE + 0.01, Z_TUBE - 0.8)]).translate((XR, 0, 0))
    A = A - cham_in - cham_top - cham_out

    # --- Arm B (oben, y>0)
    b_2d = rect(0, G / 2, XB, G / 2 + W)
    b_2d = rounded(b_2d, 1.0)
    # Spitze außen anfasen (Einlauf für Schnapper)
    b_2d = b_2d - poly([(XB - 1.2, G / 2 + W + 1), (XB + 1, G / 2 + W + 1), (XB + 1, G / 2 + W - 1.2)])
    b_full = ext(b_2d - hole, H)
    b_band2d = (b_2d ^ circle(R_K + CL + 0.5)) - circle(R_K - 0.05)
    b_band = ext(b_band2d, Z_B2 - zb1, zb1)
    B = b_full + b_band + b_hinge
    rib = prism_x([(G / 2 + 0.3, zc - 1.6), (G / 2 - 1.3, zc), (G / 2 + 0.3, zc + 1.6)], R_K + 3.0, XB - 4.0)
    B = B + rib

    A = elephant_foot(A)
    B = elephant_foot(B)
    return A, B


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
def checks(A, B, base, g, w):
    print("\n== Kollisions-/Spielprüfung ==")
    ok = True
    for ang in [0, 2, 4, 10, 20, 30]:
        Bt = B.rotate((0, 0, ang))
        # Verschlussbereich separat: dort überdeckt der Schnapper beim Einrasten absichtlich
        rest = A.trim_by_plane((-1, 0, 0), -(XB - 2))
        inter = (rest ^ Bt).volume()
        gap = rest.min_gap(Bt, 2.0)
        latch = (A ^ Bt).volume() - inter
        flag = "OK" if inter < 1e-3 and gap >= 0.3 else "!!"
        if flag == "!!":
            ok = False
        note = f", Schnapper überdeckt {latch:.1f} mm³ (rastet ein)" if latch > 1e-3 else ""
        print(f"  Arm B bei {ang:2d}°: Gelenk/Arme Überschneidung {inter:.4f} mm³, min. Spalt {gap:.2f} mm  {flag}{note}")
    # Deckel auf Ausgießer: gibt es eine Drehlage, in der er ganz aufsitzt?
    cap = base + g + w
    z_off = Z_TUBE - CAP_SKIRT_H
    best = None
    for phi in range(0, 180, 6):
        c = cap.rotate((0, 0, phi)).translate((XR, 0, z_off + 0.05))
        v = (A ^ c).volume()
        best = min(best, (v, phi)) if best else (v, phi)
    print(f"  Deckel aufgeschraubt: min. Überschneidung {best[0]:.4f} mm³ (bei {best[1]}°)  {'OK' if best[0] < 1e-3 else '!!'}")
    c = cap.rotate((0, 0, best[1])).translate((XR, 0, z_off + 0.05))
    print(f"  Deckel-Gewindespiel: {A.min_gap(c, 3.0):.2f} mm")
    return ok and best[0] < 1e-3


def main():
    out = ROOT / "3d-druck"
    A, B = build_clip()
    base, g, w, engraved = build_cap()
    checks(A, B, base, g, w)

    # Druckanordnung (A1 mini, 180 x 180)
    clip = (A + B.rotate((0, 0, OPEN_DEG))).rotate((0, 0, 45))
    bb = clip.bounding_box()
    clip = clip.translate((90 - (bb[0] + bb[3]) / 2, 90 - (bb[1] + bb[4]) / 2, 0))
    bb = clip.bounding_box()
    print(f"\nKlipp diagonal: {bb[3]-bb[0]:.1f} x {bb[4]-bb[1]:.1f} x {bb[5]-bb[2]:.1f} mm (Bett 180 x 180)")

    capparts = {k: flip_for_print(v) for k, v in {"schwarz": base, "gruen": g, "weiss": w}.items()}
    zmin = min(v.bounding_box()[2] for v in capparts.values())
    # Deckel in die freie Ecke (größter Abstand zum Klipp)
    probe = Manifold.cylinder(12, CAP_PLATE_R + 0.5, CAP_PLATE_R + 0.5, 96)
    best = None
    for dx, dy in [(3 + CAP_PLATE_R, 177 - CAP_PLATE_R), (177 - CAP_PLATE_R, 3 + CAP_PLATE_R)]:
        gap = clip.min_gap(probe.translate((dx, dy, 0)), 50)
        if best is None or gap > best[0]:
            best = (gap, dx, dy)
    _, dx, dy = best
    print(f"Deckel bei ({dx:.0f}, {dy:.0f}), Abstand zum Klipp {best[0]:.1f} mm")
    capparts = {k: v.translate((dx, dy, -zmin)) for k, v in capparts.items()}
    eng = flip_for_print(engraved)
    eng = eng.translate((dx, dy, -eng.bounding_box()[2]))

    clip_tm = to_tm(clip)
    export_parts({"einfarbig": clip_tm}, out / "pb-kaffeeklipp-1kg_235mm", bed=(180, 180, 180), write_preview=False)
    export_parts({k: to_tm(v) for k, v in capparts.items()}, out / "pb-kaffeeklipp-deckel_56mm",
                 write_combined=False, write_preview=False, bed=(180, 180, 180))
    eng_tm = to_tm(eng)
    check(eng_tm, "deckel einfarbig (Logo graviert)", (180, 180, 180))
    eng_tm.export(out / "pb-kaffeeklipp-deckel_56mm_einfarbig.stl")

    # Gesamtplatte prüfen + Vorschau
    plate = {"schwarz": clip_tm, "deckel": to_tm(capparts["schwarz"]),
             "gruen": to_tm(capparts["gruen"]), "weiss": to_tm(capparts["weiss"])}
    allm = trimesh.util.concatenate(list(plate.values()))
    print(f"\nDruckplatte gesamt: {np.round(allm.bounds[0],1)} .. {np.round(allm.bounds[1],1)}")
    preview(plate, out / "pb-kaffeeklipp-1kg_vorschau.png",
            colors={"schwarz": "#2b2b2b", "deckel": "#2b2b2b", "gruen": "#39ff14", "weiss": "#ededed"})

    # Montiert (geschlossen, Deckel drauf) – nur Vorschau
    cap_up = {"deckel": to_tm(base), "gruen": to_tm(g), "weiss": to_tm(w)}
    z_off = Z_TUBE - CAP_SKIRT_H + 0.0
    asm = {"klipp": to_tm(A + B)}
    for k, v in cap_up.items():
        v = v.copy(); v.apply_translation((XR, 0, z_off)); asm[k] = v
    preview(asm, out / "pb-kaffeeklipp-1kg_montiert.png",
            colors={"klipp": "#2b2b2b", "deckel": "#3a3a3a", "gruen": "#39ff14", "weiss": "#ededed"})


if __name__ == "__main__":
    main()
