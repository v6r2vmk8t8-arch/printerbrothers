"""Halteclip (T-Teil mit Grundplatte + Steg) – parametrisch nachgebaut.

Koordinaten (mm): X = Länge der Grundplatte (50), Y = Breite (17), Z = Höhe.
Druckorientierung: Grundplatte liegt flach auf dem Druckbett, Steg zeigt nach oben.
Aufruf:  python3 halteclip.py   -> erzeugt halteclip.stl + halteclip_vorschau.png
"""
import numpy as np
import trimesh
from manifold3d import Manifold, CrossSection

# ---------------- Maße (aus Skizze / Fotos) ----------------
L, B, T = 50.0, 17.0, 5.0          # Grundplatte Länge x Breite x Dicke
R_LINKS, R_RECHTS = 3.0, 1.5       # Eckenradien (Seite Y=0 / Seite Y=B)
LANGLOCH_L, LANGLOCH_B = 9.0, 5.0  # Langloch Länge (0,9 cm) x Breite (5 mm)
LANGLOCH_RAND_X = 4.0              # Abstand Plattenende -> Langloch (4 mm)
LANGLOCH_RAND_Y = 4.0              # Abstand linke Kante -> Langloch (4 | 5 | 8 mm)
KERBE_L, KERBE_T = 10.0, 0.0       # Kerbe in der rechten Kante (0 = keine)

GESAMT_H = 30.0                    # Grundplatte + Steg = 30 mm
STEG_B = 16.0                      # Steg-Breite entlang der Platte
STEG_D = 2.0                       # Wandstärke Steg (Rücken)
FLANSCH_B, FLANSCH_H = 1.5, 2.0    # Seitenwände des U-Profils (Breite, Tiefe)
SPITZE_FASE_H, SPITZE_FASE_T = 3.0, 1.0   # Anfasung an der Steg-Spitze
RIPPEN_ZONE = (9.0, 21.0)          # Z-Bereich der Griffrippen
RIPPEN_TEILUNG, RIPPEN_H, RIPPEN_RAND = 1.2, 0.6, 1.5
SEGMENTE = 64


def rounded_rect(w, h, r_left, r_right):
    """2D-Rechteck 0..w x 0..h, Ecken bei y=0 mit r_left, bei y=h mit r_right."""
    pts = []
    def arc(cx, cy, r, a0, a1):
        for a in np.linspace(a0, a1, SEGMENTE // 4):
            pts.append((cx + r * np.cos(a), cy + r * np.sin(a)))
    arc(w - r_left, r_left, r_left, -np.pi / 2, 0)
    arc(w - r_right, h - r_right, r_right, 0, np.pi / 2)
    arc(r_right, h - r_right, r_right, np.pi / 2, np.pi)
    arc(r_left, r_left, r_left, np.pi, 1.5 * np.pi)
    return CrossSection([pts])


def slot(x0, y0, length, width):
    r = width / 2
    c = CrossSection.circle(r, SEGMENTE)
    return CrossSection.batch_hull([c.translate((x0 + r, y0 + r)),
                                    c.translate((x0 + length - r, y0 + r))])


def prism_yz(poly_yz, x0, x1):
    """2D-Profil in der Y/Z-Ebene entlang X extrudieren."""
    cs = CrossSection([[(y, z) for y, z in poly_yz]])
    m = Manifold.extrude(cs, x1 - x0)                     # (y,z,x)
    m = m.transform([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0]])  # -> (x,y,z)
    return m.translate((x0, 0, 0))


def box(x0, y0, z0, x1, y1, z1):
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


# ---------------- Grundplatte ----------------
outline = rounded_rect(L, B, R_LINKS, R_RECHTS)
if KERBE_T > 0:
    outline = outline - CrossSection.square((KERBE_L, KERBE_T + 1)).translate(
        ((L - KERBE_L) / 2, B - KERBE_T))
outline = outline - slot(LANGLOCH_RAND_X, LANGLOCH_RAND_Y, LANGLOCH_L, LANGLOCH_B)
outline = outline - slot(L - LANGLOCH_RAND_X - LANGLOCH_L, LANGLOCH_RAND_Y,
                         LANGLOCH_L, LANGLOCH_B)
platte = Manifold.extrude(outline, T)

# ---------------- Steg (U-Profil, öffnet zur Plattenkante hin) ----------------
# Rücken innen, Seitenwände reichen bis zur Kante (bündig), Rippen auf der Innenseite.
x0, x1 = (L - STEG_B) / 2, (L + STEG_B) / 2
y_kante = B                                 # Seitenwände bündig mit der Plattenkante
y_ruecken_aussen = y_kante - FLANSCH_H      # Außenfläche Rücken (Rippenseite)
y_innen = y_ruecken_aussen - STEG_D         # Innenfläche Rücken (Richtung Langlöcher)
z0 = T - 0.01
ruecken = prism_yz([(y_innen, z0), (y_ruecken_aussen, z0),
                    (y_ruecken_aussen, GESAMT_H),
                    (y_innen + SPITZE_FASE_T, GESAMT_H),
                    (y_innen, GESAMT_H - SPITZE_FASE_H)], x0, x1)
flansch_l = box(x0, y_ruecken_aussen - 0.01, z0, x0 + FLANSCH_B, y_kante, GESAMT_H)
flansch_r = box(x1 - FLANSCH_B, y_ruecken_aussen - 0.01, z0, x1, y_kante, GESAMT_H)

rippen = []
z = RIPPEN_ZONE[0]
while z + RIPPEN_TEILUNG / 2 <= RIPPEN_ZONE[1]:
    # Trapezrippe auf der Innenseite des Rückens (Richtung Langlöcher, gegen Uhrzeigersinn)
    rippen.append(prism_yz([(y_innen + 0.01, z + RIPPEN_TEILUNG * 0.75),
                            (y_innen - RIPPEN_H, z + RIPPEN_TEILUNG * 0.5),
                            (y_innen - RIPPEN_H, z + RIPPEN_TEILUNG * 0.25),
                            (y_innen + 0.01, z)],
                           x0 + FLANSCH_B + RIPPEN_RAND, x1 - FLANSCH_B - RIPPEN_RAND))
    z += RIPPEN_TEILUNG

teil = platte + ruecken + flansch_l + flansch_r
for r in rippen:
    teil = teil + r
print("Manifold-Status:", teil.status(), "Genus:", teil.genus())

mesh = teil.to_mesh()
tm = trimesh.Trimesh(mesh.vert_properties[:, :3], mesh.tri_verts, process=False)
assert tm.is_watertight, "Mesh nicht dicht!"
tm.export("halteclip.stl")
print("Volumen %.2f cm³, Maße %s mm, wasserdicht=%s" %
      (tm.volume / 1000, np.round(tm.extents, 2), tm.is_watertight))
