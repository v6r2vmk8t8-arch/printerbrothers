"""Hilfsfunktionen: Export, Druckbarkeits-Check und Vorschau für STL-Teile.

Verwendung im eigenen Modellskript:
    import sys; sys.path.insert(0, ".claude/skills/stl-designer/scripts")
    from stl_tools import export_parts
    export_parts({"gruen": teil_a, "weiss": teil_b}, "3d-druck/name_60mm")
Akzeptiert build123d-Objekte oder trimesh.Trimesh.
"""
import sys
from pathlib import Path

import numpy as np
import trimesh


def to_mesh(obj, tol=0.01, ang=0.1):
    if isinstance(obj, trimesh.Trimesh):
        return obj
    verts, faces = obj.tessellate(tol, ang)
    v = np.array([[p.X, p.Y, p.Z] for p in verts])
    return trimesh.Trimesh(vertices=v, faces=np.array(faces), process=True)


def place_on_bed(mesh):
    """Unterseite auf Z=0 legen."""
    m = mesh.copy()
    m.apply_translation([0, 0, -m.bounds[0][2]])
    return m


def check(mesh, name="teil", bed=(180, 180, 180), need_z0=True):
    """Gibt Bericht aus und liefert Liste von Problemen zurück."""
    probs = []
    ext = mesh.extents
    if not mesh.is_watertight:
        probs.append("nicht wasserdicht (Löcher im Mesh)")
    if not mesh.is_winding_consistent:
        probs.append("inkonsistente Normalen")
    if mesh.is_watertight and mesh.volume <= 0:
        probs.append("negatives/null Volumen")
    if any(e > b for e, b in zip(ext, bed)):
        probs.append(f"größer als Druckbett {bed}")
    if need_z0 and abs(mesh.bounds[0][2]) > 1e-3:
        probs.append("liegt nicht auf Z=0")
    bodies = len(mesh.split(only_watertight=False))
    print(f"[{name}] {ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.1f} mm | "
          f"Volumen {mesh.volume/1000:.2f} cm³ (~{mesh.volume/1000*1.24:.1f} g PLA massiv) | "
          f"Körper: {bodies} | Dreiecke: {len(mesh.faces)}")
    for p in probs:
        print(f"  ⚠ {p}")
    if not probs:
        print("  ✓ druckbereit")
    return probs


def _render(meshes, colors, size=900, elev=30, azim=-55):
    """Einfacher Z-Buffer-Renderer (pixelgenaue Verdeckung). Liefert RGB-Array."""
    default = {"gruen": "#2e9e4f", "weiss": "#f0f0f0", "schwarz": "#333333", "rot": "#d33333",
               "blau": "#2a6fd6", "gelb": "#f2c230", "orange": "#ff7a2f", "einfarbig": "#2e9e4f"}
    pal = ["#2e9e4f", "#f0f0f0", "#333333", "#ff7a2f", "#2a6fd6"]
    def rgb(h): h = h.lstrip("#"); return np.array([int(h[k:k+2], 16) for k in (0, 2, 4)]) / 255
    e, a = np.radians(elev), np.radians(azim)
    view = np.array([np.cos(e)*np.cos(a), np.cos(e)*np.sin(a), np.sin(e)])  # Richtung zur Kamera
    right = np.cross([0, 0, 1], view); right /= np.linalg.norm(right)
    up = np.cross(view, right)
    R = np.stack([right, up, view])
    light = 0.6*view + 0.5*up + 0.3*right; light /= np.linalg.norm(light)
    tris, cols = [], []
    for i, (name, m) in enumerate(meshes.items()):
        c = rgb((colors or {}).get(name, default.get(name, pal[i % len(pal)])))
        shade = 0.35 + 0.65*np.abs(m.face_normals @ light)
        tris.append(m.triangles); cols.append(c[None]*shade[:, None])
    T = np.vstack(tris) @ R.T; C = np.clip(np.vstack(cols), 0, 1)
    lo, hi = T[..., :2].reshape(-1, 2).min(0), T[..., :2].reshape(-1, 2).max(0)
    sc = (size*0.9) / (hi - lo).max(); off = (size - (hi - lo)*sc) / 2
    P = (T[..., :2] - lo)*sc + off; Z = T[..., 2]
    zbuf = np.full((size, size), -np.inf); img = np.ones((size, size, 3))
    for (p0, p1, p2), (z0, z1, z2), col in zip(P, Z, C):
        x0, y0 = np.floor(np.minimum(np.minimum(p0, p1), p2)).astype(int)
        x1, y1 = np.ceil(np.maximum(np.maximum(p0, p1), p2)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, size-1), min(y1, size-1)
        if x1 < x0 or y1 < y0: continue
        xs, ys = np.meshgrid(np.arange(x0, x1+1)+0.5, np.arange(y0, y1+1)+0.5)
        d = (p1[0]-p0[0])*(p2[1]-p0[1]) - (p2[0]-p0[0])*(p1[1]-p0[1])
        if abs(d) < 1e-12: continue
        w1 = ((xs-p0[0])*(p2[1]-p0[1]) - (p2[0]-p0[0])*(ys-p0[1])) / d
        w2 = ((p1[0]-p0[0])*(ys-p0[1]) - (xs-p0[0])*(p1[1]-p0[1])) / d
        w0 = 1 - w1 - w2
        ins = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not ins.any(): continue
        z = w0*z0 + w1*z1 + w2*z2
        sub = zbuf[y0:y1+1, x0:x1+1]
        upd = ins & (z > sub)
        sub[upd] = z[upd]; img[y0:y1+1, x0:x1+1][upd] = col
    return img[::-1]


def preview(meshes, path, colors=None):
    """Speichert zwei Ansichten (schräg von vorne + von oben) als PNG."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(12, 6), dpi=110)
    for ax, (el, az, t) in zip(axs, [(30, -55, "schräg"), (89, -90, "von oben")]):
        ax.imshow(_render(meshes, colors, 700, el, az)); ax.set_title(t); ax.axis("off")
    fig.savefig(path, bbox_inches="tight", facecolor="white"); plt.close(fig)
    print(f"Vorschau: {path}")


def export_parts(parts, basepath, write_combined=True, write_preview=True, bed=(180, 180, 180)):
    """parts: {farbname: objekt}. Schreibt <basepath>_<farbe>.stl je Teil,
    bei >1 Teil zusätzlich <basepath>_einfarbig.stl, plus Vorschau-PNG."""
    base = Path(basepath); base.parent.mkdir(parents=True, exist_ok=True)
    meshes = {k: to_mesh(v) for k, v in parts.items()}
    # gemeinsam auf Z=0 legen, damit Farbteile in Bambu Studio deckungsgleich bleiben
    zmin = min(m.bounds[0][2] for m in meshes.values())
    for m in meshes.values():
        m.apply_translation([0, 0, -zmin])
    probs = []
    for name, m in meshes.items():
        p = f"{base}_{name}.stl" if len(meshes) > 1 or name != "einfarbig" else f"{base}_einfarbig.stl"
        probs += [f"{name}: {x}" for x in check(m, name, bed, need_z0=len(meshes) == 1)]
        m.export(p); print(f"  → {p}")
    if write_combined and len(meshes) > 1:
        comb = trimesh.util.concatenate(list(meshes.values()))
        p = f"{base}_einfarbig.stl"; comb.export(p); print(f"  → {p} (alle Teile zusammen)")
    if write_preview:
        preview(meshes, f"{base}_vorschau.png")
    if probs:
        print("PROBLEME gefunden – bitte beheben:", *probs, sep="\n  ")
    return meshes


if __name__ == "__main__":
    for f in sys.argv[1:]:
        check(trimesh.load(f, force="mesh"), Path(f).name, need_z0=False)
