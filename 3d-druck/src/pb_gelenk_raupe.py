"""Printer Brothers Gelenk-Raupe: Fidget-Kette zum Rollen, Wickeln und Klappen. Print-in-place, ohne Stützen.

Eigenentwurf. Glieder mit Kegelzapfen-Gelenken (Achse waagrecht, quer zur Kette):
  - Zunge (Mitte) mit Kegelpfannen, Gabel (außen) mit Kegelzapfen – 45°, druckt ohne Stützen
  - großes Spiel (0,5 mm): darf locker sein, verklebt nicht
  - Freiraum über der Zunge mit 45°-Dach (Tropfenform) -> keine hängende Brücke
Kopf mit Augen, Schwanz abgerundet. Glieder abwechselnd zwei Farben (AMS) oder einfarbig.

Aufruf:  python3 3d-druck/src/pb_gelenk_raupe.py
"""
import sys
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold, set_circular_segments

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude/skills/stl-designer/scripts"))
from stl_tools import export_parts, preview  # noqa: E402

set_circular_segments(96)

# ---------------------------------------------------------------- Parameter
N = 10            # Anzahl Glieder
P = 14.0          # Gelenkabstand
H = 7.0           # Höhe (Druck-Z)
W = 15.0          # Breite
YC = 3.5          # halbe Zungenbreite
G = 0.5           # Spiel überall (großzügig = robust)
R = 4.2           # Radius Gelenkrolle (Zunge/Gabel) um die Achse
CONE_R = 2.2      # Kegelzapfen: Fußradius
CONE_H = 1.8      # Kegelzapfen: Höhe (45°)
EDGE = 1.0        # 45°-Fase an den Längskanten
ZA = H / 2        # Achshöhe


# ---------------------------------------------------------------- Helfer
def box(x0, x1, y0, y1, z0=-1.0, z1=H + 1.0):
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def xz_prism(cs, y0, y1):
    """CrossSection in (x,z) -> Prisma entlang y von y0 bis y1."""
    m = Manifold.extrude(cs, y1 - y0)              # entlang Z
    # (x, z_cs, t) -> (x, y0 + t, z_cs)
    return m.transform([[1, 0, 0, 0], [0, 0, 1, y0], [0, 1, 0, 0]])


def roller(x, r, y0, y1):
    return xz_prism(CrossSection.circle(r).translate((x, ZA)), y0, y1)


def teardrop(x, r, y0, y1):
    """Freiraum um die Achse: Kreis + 45°-Dach nach oben (druckbar ohne Brücke)."""
    s = r * np.sqrt(2)
    roof = CrossSection([[(x - r / np.sqrt(2), ZA + r / np.sqrt(2)), (x, ZA + s),
                          (x + r / np.sqrt(2), ZA + r / np.sqrt(2)), (x, ZA)]])
    return xz_prism(CrossSection.circle(r).translate((x, ZA)) + roof, y0, y1)


def cone_y(x, y_base, r0, r1, length, sign):
    """Kegelstumpf mit Achse parallel y: Fuß bei y_base (Radius r0), Spitze bei y_base + sign*length (Radius r1)."""
    c = Manifold.cylinder(length, r0, r1, 96)        # entlang +z
    c = c.rotate((-90 * sign, 0, 0))                   # +z -> sign*y
    return c.translate((x, y_base, ZA))


def profile_clip():
    """Querschnitt (y,z) mit Fasen an den Längskanten, als langes Prisma entlang x."""
    e = EDGE
    cs = CrossSection([[(-W / 2 + e, 0), (W / 2 - e, 0), (W / 2, e), (W / 2, H - e), (W / 2 - e, H),
                        (-W / 2 + e, H), (-W / 2, H - e), (-W / 2, e)]])
    m = Manifold.extrude(cs, 400)
    return m.transform([[0, 0, 1, -200], [1, 0, 0, 0], [0, 1, 0, 0]])


def to_tm(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)


# ---------------------------------------------------------------- Glied
def link(i):
    xl, xr = -P / 2, P / 2
    first, last = i == 0, i == N - 1
    y_f = YC + G                                      # Innenfläche der Gabel
    body = box(xl, xr, -W / 2, W / 2)
    if last:                                           # Schwanz: hinten rund
        body = body - box(xr - P / 2 + 1, xr + 1, -W, W) + roller(xr - P / 2 + 1, P / 2 - 1, -W / 2, W / 2)
    if not last:                                       # Zunge nach rechts
        body = body + roller(xr, R, -YC, YC)
    if not first:                                      # Gabel nach links
        body = body + roller(xl, R, y_f, W / 2) + roller(xl, R, -W / 2, -y_f)
        body = body - teardrop(xl, R + G, -y_f, y_f)   # Platz für die Zunge des Vorgängers
        body = body + cone_y(xl, y_f + 0.01, CONE_R, CONE_R - CONE_H, CONE_H + 0.01, -1)
        body = body + cone_y(xl, -y_f - 0.01, CONE_R, CONE_R - CONE_H, CONE_H + 0.01, +1)
    else:                                              # Kopf: vorne rund
        body = body - box(xl - 1, xl + P / 2 - 1, -W, W) + roller(xl + P / 2 - 1, P / 2 - 1, -W / 2, W / 2)
    if not last:
        body = body - teardrop(xr, R + G, YC, W) - teardrop(xr, R + G, -W, -YC)   # Platz für die Gabel
        # Kegelpfannen in der Zunge: Zapfenfläche um G (senkrecht) versetzt
        d = G * np.sqrt(2) - G
        for s in (1, -1):
            r0 = CONE_R + d + 0.01
            body = body - cone_y(xr, s * (YC + 0.01), r0, r0 - (CONE_H + 0.01), CONE_H + 0.01, -s)
    body = body ^ box(-50, 50, -W, W, 0, H) ^ profile_clip()
    for end, cx, d in ((first, xl + W / 2, 1), (last, xr - W / 2, -1)):   # Kopf/Schwanz auch von oben rund
        if end:
            plan = CrossSection.circle(W / 2).translate((cx, 0)) + \
                CrossSection([[(cx, -W), (cx + 60 * d, -W), (cx + 60 * d, W), (cx, W)]])
            body = body ^ Manifold.extrude(plan, H + 2).translate((0, 0, -1))
    if first:                                          # Augen
        for s in (1, -1):
            body = body - Manifold.sphere(1.6, 48).translate((xl + 3.2, s * 3.2, H + 0.6))
    return body.translate((i * P, 0, 0))


def elephant_foot(m, inset=0.25, h=0.4):
    sec = m.slice(h / 2)
    return m.trim_by_plane((0, 0, 1), h) + Manifold.extrude(sec.offset(-inset, JoinType.Round), h + 0.05)


# ---------------------------------------------------------------- Prüfung
def checks(links):
    print("== Prüfung ==")
    ok = True
    for i, m in enumerate(links):
        if len(m.decompose()) != 1:
            print(f"  Glied {i}: {len(m.decompose())} Körper !!")
            ok = False
    gap = min(links[i].min_gap(links[i + 1], 2.0) for i in range(N - 1))
    inter = sum((links[i] ^ links[i + 1]).volume() for i in range(N - 1))
    print(f"  wie gedruckt: min. Spalt {gap:.2f} mm, Überschneidung {inter:.4f} mm³  {'OK' if gap >= 0.4 and inter < 1e-3 else '!!'}")
    ok &= gap >= 0.4 and inter < 1e-3
    # Biegebereich eines mittleren Gelenks (Glied k+1 um die Achse drehen)
    k = N // 2 - 1
    ax = (k + 0.5) * P
    rest = links[k]
    lim = {}
    for sgn in (1, -1):
        a = 0
        while a < 180:
            a2 = a + 5
            m = links[k + 1].translate((-ax, 0, -ZA)).rotate((0, sgn * a2, 0)).translate((ax, 0, ZA))
            if (m ^ rest).volume() > 0.05:
                break
            a = a2
        lim[sgn] = a
    print(f"  Gelenk knickt frei: {lim[-1]}° nach oben, {lim[1]}° nach unten  {'OK' if min(lim.values()) >= 60 else '!!'}")
    ok &= min(lim.values()) >= 60
    # seitlich gefangen?
    m = links[k + 1]
    free = next((dy for dy in np.arange(0.1, 4, 0.1) if (m.translate((0, dy, 0)) ^ rest).volume() > 0.01), None)
    print(f"  seitlich blockiert nach {free:.1f} mm (Kegel halten, fällt nicht auseinander)")
    pull = next((dx for dx in np.arange(0.1, 4, 0.1) if (m.translate((dx, 0, 0)) ^ rest).volume() > 0.01), None)
    print(f"  auseinanderziehen blockiert nach {pull:.1f} mm")
    return ok


def main():
    out = ROOT / "3d-druck/gelenk-raupe"
    out.mkdir(parents=True, exist_ok=True)
    links = [elephant_foot(link(i)) for i in range(N)]
    ok = checks(links)
    print("Alle Prüfungen OK" if ok else "!! Prüfung fehlgeschlagen")
    L = links[-1].bounding_box()[3] - links[0].bounding_box()[0]
    x0 = 90 - (links[0].bounding_box()[0] + links[-1].bounding_box()[3]) / 2
    even = sum(links[0::2], Manifold()).translate((x0, 90, 0))
    odd = sum(links[1::2], Manifold()).translate((x0, 90, 0))
    print(f"Länge {L:.1f} mm")
    parts = {"gruen": to_tm(even), "weiss": to_tm(odd)}
    export_parts(parts, out / f"pb-gelenk-raupe_{L:.0f}mm", bed=(180, 180, 180), write_preview=False)
    preview(parts, out / f"pb-gelenk-raupe_{L:.0f}mm_vorschau.png", colors={"gruen": "#39ff14", "weiss": "#ededed"})


if __name__ == "__main__":
    main()
