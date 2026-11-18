"""Printer Brothers Klick-Kreisel: Fidget-Scheibe, print-in-place, ohne Stützen.

Eigenentwurf. Nabe + zwei Ringe drehen sich unabhängig auf 45°-Rautenlagern
(gefangen, fallen nicht auseinander). Federarme mit Rastnasen sorgen für spürbare Klicks:
  - innerer Ring: 12 Rasten (grob, kräftiger Klick)
  - äußerer Ring: 24 Rasten (fein, schnelles Rattern)
Oben Daumenmulde in der Nabe, Markierungsrillen auf dem inneren Ring, Riffelrand außen.

Drei getrennte Körper -> je Teil eine Farbe (AMS) oder einfarbig.
Optimiert für Bambu Lab A1 mini, ca. 40 min Druckzeit (0,2 mm, 15 % Infill).

Aufruf:  python3 3d-druck/src/pb_klick_kreisel.py
"""
import sys
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold, set_circular_segments

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude/skills/stl-designer/scripts"))
from stl_tools import export_parts, preview  # noqa: E402

set_circular_segments(128)

# ---------------------------------------------------------------- Parameter
H = 7.0            # Höhe der Scheibe
D = 1.0            # Tiefe der 45°-Rautenflanke (hält die Teile axial gefangen)
GAP = 0.35         # Spalt zwischen den Teilen (senkrecht zur Fläche)
R_HUB = 10.0       # Nabe: Radius an Ober-/Unterseite
R_R1 = 17.0        # Ring 1: Außenradius an Ober-/Unterseite (Lager für Ring 2)
R_OUT = 23.0       # Ring 2: Außenradius (Ø 46 mm)

# Rastung
NUB_R = 0.9        # Radius der Rastnase
ENGAGE = 0.5       # so weit greift die Nase in die Raste -> Federweg des Arms
ARM_T = 1.2        # Armdicke an Ober-/Unterseite (in der Mitte + D)
SLOT = 0.8         # Schlitzbreite hinter dem Arm
# (Lager-Radius, Anzahl Arme, Bogen je Arm in °, Rasten im äußeren Teil)
STAGES = [(R_HUB, 3, 75.0, 12), (R_R1, 4, 50.0, 24)]

KNURL = 30         # Riffeln am Außenrand
EDGE = 0.6         # Fase Außenkante Ring 2


# ---------------------------------------------------------------- Helfer
def poly(pts):
    cs = CrossSection([pts])
    if cs.area() == 0:
        cs = CrossSection([pts[::-1]])
    return cs


def revolve(cs):
    return Manifold.revolve(cs, 128)


def ext(cs, h, z0=0.0):
    return Manifold.extrude(cs, h).translate((0, 0, z0))


def circle(r, cx=0.0, cy=0.0):
    return CrossSection.circle(r).translate((cx, cy))


def polar(r, a):
    return r * np.cos(a), r * np.sin(a)


def sector(r0, r1, a0, a1, n=64):
    a = np.linspace(a0, a1, n)
    pts = [polar(r1, t) for t in a] + [polar(r0, t) for t in a[::-1]]
    return poly(pts)


def diamond(r):
    """(r,z)-Profil eines Lagerkerns: Radius r an Ober-/Unterseite, r+D in der Mitte."""
    return poly([(0, 0), (r, 0), (r + D, D), (r + D, H - D), (r, H), (0, H)])


def cavity(r):
    """Lagerbohrung im äußeren Teil = Kernprofil um GAP aufgedickt (gleicher Spalt auf allen Flächen)."""
    return revolve(diamond(r).offset(GAP, JoinType.Miter, 2.0) ^ poly([(0, -2), (60, -2), (60, H + 2), (0, H + 2)]))


def elephant_foot(m, inset=0.25, h=0.4):
    sec = m.slice(h / 2)
    return m.trim_by_plane((0, 0, 1), h) + ext(sec.offset(-inset, JoinType.Round), h + 0.05)


def to_tm(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)


# ---------------------------------------------------------------- Rastung
def detent(inner, outer, r, n_arms, span_deg, n_notch):
    """Federarme mit Nasen in `inner`, Rasten in `outer`. Nasen liegen beim Druck mittig in einer Raste."""
    s = r + D + GAP                     # Lagerfläche des äußeren Teils
    rc = s + ENGAGE - NUB_R             # Mittelpunkt der Nase
    r_s1 = r - ARM_T                    # Schlitz hinter dem Arm
    r_s0 = r_s1 - SLOT
    span = np.radians(span_deg)
    cuts, nubs, tips = CrossSection(), CrossSection(), []
    for i in range(n_arms):
        a0 = 2 * np.pi * i / n_arms
        a1 = a0 + span
        arc = sector(r_s0, r_s1 + 0.01, a0, a1)
        end = sector(r_s0, r + D + 2.0, a1, a1 + SLOT / r)        # freies Ende
        cuts = cuts + (arc + end).offset(-0.2, JoinType.Round).offset(0.2, JoinType.Round)
        cuts = cuts + circle(SLOT / 2, *polar((r_s0 + r_s1) / 2, a0))  # runde Armwurzel (keine Kerbe)
        at = a1 - (NUB_R + 0.6) / rc
        tips.append(at)
        nubs = nubs + circle(NUB_R, *polar(rc, at))
    inner = inner - ext(cuts, H + 2, -1)
    inner = inner + ext(nubs, H - 2 * D - 0.6, D + 0.3)
    notch = CrossSection()
    for k in range(n_notch):
        notch = notch + circle(NUB_R + GAP, *polar(rc, tips[0] + 2 * np.pi * k / n_notch))
    outer = outer - ext(notch, H - 2 * D, D)
    strain = 1.5 * (ARM_T + D / 2) * ENGAGE / (r * span) ** 2
    print(f"  Rastung r={r:.0f}: {n_arms} Arme à {r * span:.1f} mm, {n_notch} Rasten, Federweg {ENGAGE} mm, Dehnung {strain * 100:.1f} %")
    return inner, outer


# ---------------------------------------------------------------- Teile
def build():
    hub = revolve(diamond(R_HUB))
    # Daumenmulde (flache Kugelkappe, 0.9 mm tief)
    rs = 18.0
    hub = hub - Manifold.sphere(rs, 256).translate((0, 0, H + rs - 0.9))

    ring1 = revolve(diamond(R_R1)) - cavity(R_HUB)
    # Markierungsrillen oben (tastbar, zeigen die Rasten)
    marks = CrossSection()
    for k in range(12):
        a = 2 * np.pi * k / 12 + np.pi / 12
        marks = marks + sector(R_HUB + D + 2.0, R_HUB + D + 4.2, a - 0.035, a + 0.035, 4)
    ring1 = ring1 - ext(marks.offset(0.3, JoinType.Round), 1.0, H - 0.5)

    o = R_OUT
    ring2 = revolve(poly([(0, 0), (o - EDGE, 0), (o, EDGE), (o, H - EDGE), (o - EDGE, H), (0, H)]))
    knurl = CrossSection()
    for k in range(KNURL):
        knurl = knurl + circle(1.1, *polar(o + 0.5, 2 * np.pi * k / KNURL))
    ring2 = ring2 - ext(knurl, H + 2, -1) - cavity(R_R1)

    print("== Rastung ==")
    (r_i, n, sp, nn), (r_o, n2, sp2, nn2) = STAGES
    hub, ring1 = detent(hub, ring1, r_i, n, sp, nn)
    ring1, ring2 = detent(ring1, ring2, r_o, n2, sp2, nn2)
    return elephant_foot(hub), elephant_foot(ring1), elephant_foot(ring2)


def checks(hub, ring1, ring2):
    print("== Prüfung ==")
    ok = True
    for name, m in (("Nabe", hub), ("Ring 1", ring1), ("Ring 2", ring2)):
        n = len(m.decompose())
        print(f"  {name}: {n} Körper  {'OK' if n == 1 else '!!'}")
        ok &= n == 1
    for (na, a), (nb, b), nn in ((("Nabe", hub), ("Ring 1", ring1), 12), (("Ring 1", ring1), ("Ring 2", ring2), 24)):
        g = a.min_gap(b, 2.0)
        print(f"  {na} / {nb} wie gedruckt: Spalt {g:.2f} mm, Überschneidung {(a ^ b).volume():.4f} mm³  {'OK' if g >= 0.25 else '!!'}")
        ok &= g >= 0.25
        step = 360 / nn
        g2 = a.min_gap(b.rotate((0, 0, step)), 2.0)
        bh = b.rotate((0, 0, step / 2))
        v = (a ^ bh).volume()
        print(f"    eine Raste weiter: Spalt {g2:.2f} mm  |  halbe Raste: Nasen drücken {v:.2f} mm³ ein (= Klick)")
        ok &= g2 >= 0.25 and v > 0.05
    # axial gefangen?
    for na, a, b in (("Ring 1 auf Nabe", ring1, hub), ("Ring 2 auf Ring 1", ring2, ring1)):
        lift = next((dz for dz in np.arange(0.1, 3.0, 0.1) if (a.translate((0, 0, dz)) ^ b).volume() > 1e-2), None)
        print(f"  {na}: axial nach {lift:.1f} mm blockiert (fällt nicht heraus)")
    return ok


def main():
    out = ROOT / "3d-druck/klick-kreisel"
    out.mkdir(parents=True, exist_ok=True)
    hub, ring1, ring2 = build()
    ok = checks(hub, ring1, ring2)
    print("Alle Prüfungen OK" if ok else "!! Prüfung fehlgeschlagen")
    t = lambda m: to_tm(m.translate((90, 90, 0)))  # noqa: E731
    parts = {"gruen": t(hub), "weiss": t(ring1), "schwarz": t(ring2)}
    export_parts(parts, out / "pb-klick-kreisel_46mm", bed=(180, 180, 180), write_preview=False)
    preview(parts, out / "pb-klick-kreisel_46mm_vorschau.png",
            colors={"gruen": "#39ff14", "weiss": "#ededed", "schwarz": "#2b2b2b"})


if __name__ == "__main__":
    main()
