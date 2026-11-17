"""Shop-Renderings des Kaffee-Klipps (Version 2, angelenkte Hülse) -> public/images/.

Aufruf:  python3 3d-druck/src/shop_renders.py
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.argv.append("--angelenkt")
sys.path.insert(0, str(Path(__file__).parent))
import pb_kaffeeklipp as k  # noqa: E402

OUT = k.ROOT / "public/images"
SIZE = 1100
SS = 2  # Supersampling


def hexrgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)]) / 255


def camera(elev, azim):
    e, a = np.radians(elev), np.radians(azim)
    view = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    right = np.cross([0, 0, 1], view)
    if np.linalg.norm(right) < 1e-6:
        right = np.array([1.0, 0, 0])
    right /= np.linalg.norm(right)
    up = np.cross(view, right)
    return np.stack([right, up, view]), view, right, up


def raster(tris2d, z, size, ids, zbuf, idbuf):
    for t, (p0, p1, p2), (z0, z1, z2) in zip(ids, tris2d, z):
        x0, y0 = np.floor(np.minimum(np.minimum(p0, p1), p2)).astype(int)
        x1, y1 = np.ceil(np.maximum(np.maximum(p0, p1), p2)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, size - 1), min(y1, size - 1)
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        d = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p2[0] - p0[0]) * (p1[1] - p0[1])
        if abs(d) < 1e-12:
            continue
        w1 = ((xs - p0[0]) * (p2[1] - p0[1]) - (p2[0] - p0[0]) * (ys - p0[1])) / d
        w2 = ((p1[0] - p0[0]) * (ys - p0[1]) - (xs - p0[0]) * (p1[1] - p0[1])) / d
        w0 = 1 - w1 - w2
        ins = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not ins.any():
            continue
        zz = w0 * z0 + w1 * z1 + w2 * z2
        sub = zbuf[y0:y1 + 1, x0:x1 + 1]
        upd = ins & (zz > sub)
        sub[upd] = zz[upd]
        idbuf[y0:y1 + 1, x0:x1 + 1][upd] = t


def render(parts, elev, azim, fill=0.80, bg=("#F3EEE7", "#D9D1C6"), light_from=(-0.45, 0.35, 0.82)):
    """parts: Liste (trimesh, farbe, glanz)."""
    size = SIZE * SS
    R, view, right, up = camera(elev, azim)
    tris, cols, gloss = [], [], []
    for m, c, g in parts:
        tris.append(m.triangles)
        cols.append(np.repeat(hexrgb(c)[None], len(m.faces), 0))
        gloss.append(np.full(len(m.faces), g))
    T = np.vstack(tris)
    C = np.vstack(cols)
    GL = np.concatenate(gloss)
    N = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12

    # Schatten: Geometrie entlang Licht auf z=0 projizieren
    L = np.array(light_from, float)
    L /= np.linalg.norm(L)
    Ts = T - (T[..., 2:3] / L[2]) * L[None, None, :]
    Ts[..., 2] = 0

    P = T @ R.T
    Ps = Ts @ R.T
    allp = np.vstack([P[..., :2].reshape(-1, 2), Ps[..., :2].reshape(-1, 2)])
    lo, hi = allp.min(0), allp.max(0)
    sc = size * fill / (hi - lo).max()
    off = (size - (hi - lo) * sc) / 2
    P2 = (P[..., :2] - lo) * sc + off
    S2 = (Ps[..., :2] - lo) * sc + off
    # Projektion merken (3D-Punkt -> Pixel im fertigen Bild), z. B. für Beschriftungen
    render.project = lambda pts: np.column_stack((((np.asarray(pts, float) @ R.T)[:, 0] - lo[0]) * sc + off[0],
                                                  size - (((np.asarray(pts, float) @ R.T)[:, 1] - lo[1]) * sc + off[1]))) / SS

    zbuf = np.full((size, size), -np.inf)
    idbuf = np.full((size, size), -1, int)
    raster(P2, P[..., 2], size, range(len(P2)), zbuf, idbuf)
    szb = np.full((size, size), -np.inf)
    sid = np.full((size, size), -1, int)
    raster(S2, Ps[..., 2], size, range(len(S2)), szb, sid)

    # Hintergrund: weicher Verlauf + Vignette
    yy, xx = np.mgrid[0:size, 0:size] / size
    top, bot = hexrgb(bg[0]), hexrgb(bg[1])
    t = np.clip(yy * 0.9 + 0.05, 0, 1)[..., None]
    img = top * (1 - t) + bot * t
    vig = 1 - 0.22 * (((xx - 0.5) ** 2 + (yy - 0.45) ** 2) * 2.2)
    img *= np.clip(vig, 0.75, 1)[..., None]
    shadow = Image.fromarray(((sid >= 0) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(size * 0.012))
    sh = np.asarray(shadow) / 255.0
    contact = Image.fromarray(((sid >= 0) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(size * 0.003))
    img *= (1 - 0.30 * sh - 0.15 * np.asarray(contact) / 255.0)[..., None]

    # Beleuchtung pro Fläche
    key = L
    fill_l = -0.6 * right + 0.2 * up + 0.5 * view
    fill_l /= np.linalg.norm(fill_l)
    rim = -view + 0.6 * up
    rim /= np.linalg.norm(rim)
    Nf = np.where((N @ view)[:, None] < 0, -N, N)  # zur Kamera drehen
    diff = 0.62 * np.clip(Nf @ key, 0, 1) + 0.22 * np.clip(Nf @ fill_l, 0, 1)
    rimv = 0.25 * np.clip(Nf @ rim, 0, 1) ** 2
    Hh = key + view
    Hh /= np.linalg.norm(Hh)
    spec = GL * np.clip(Nf @ Hh, 0, 1) ** 40
    amb = 0.24
    shade = C * (amb + diff)[:, None] + (rimv + spec)[:, None] * np.array([1, 1, 1])
    shade = np.clip(shade, 0, 1)

    mask = idbuf >= 0
    img[mask] = shade[idbuf[mask]]
    # leichte Kantenlinie (Silhouette/Tiefensprünge) für Plastizität
    zb = np.where(mask, zbuf, zbuf[mask].min() - 50 if mask.any() else 0)
    edge = (np.abs(np.diff(zb, axis=0, prepend=zb[:1])) > 1.5 / sc * 4) | (np.abs(np.diff(zb, axis=1, prepend=zb[:, :1])) > 1.5 / sc * 4)
    img[edge & mask] *= 0.55

    im = Image.fromarray((np.clip(img[::-1], 0, 1) * 255).astype(np.uint8))
    return im.resize((SIZE, SIZE), Image.LANCZOS)


def upright(azim):
    """Drehwinkel, damit das Logo (oben) aus Kamerarichtung aufrecht lesbar ist."""
    a = np.radians(azim)
    return np.degrees(np.arctan2(np.cos(a), -np.sin(a)))


def main():
    A, B = k.build_clip()
    S = k.build_sleeve()
    base, g, w, _ = k.build_cap()
    CLIP, CAP, GREEN, WHITE = "#2A2C2E", "#1C1D1F", "#39FF14", "#EDEDED"
    tm = k.to_tm
    z_cap = k.SL_TOP - k.CAP_SKIRT_H
    cap = lambda dx=0, dy=0, dz=0, rot=0: [(tm(p.rotate((0, 0, rot)).translate((k.XR + dx, dy, z_cap + dz))), c, gl)
                                           for p, c, gl in [(base, CAP, 0.35), (g, GREEN, 0.15), (w, WHITE, 0.25)]]
    sleeve_in = S.translate((k.XR, 0, 0))

    # 1) Hauptbild: geschlossen mit Deckel
    parts = [(tm(A), CLIP, 0.35), (tm(B), CLIP, 0.35), (tm(sleeve_in), CLIP, 0.35)] + cap(rot=upright(-62))
    render(parts, 30, -62, fill=0.86).save(OUT / "kaffeeklipp-1.jpg", quality=90)
    print("1 ok")

    # 2) Deckel mit Logo nah
    from manifold3d import Manifold
    box = Manifold.cube((120, 120, 80)).translate((k.XR - 60, -60, -5))
    parts = [(tm(A ^ box), CLIP, 0.35), (tm(B ^ box), CLIP, 0.35), (tm(sleeve_in), CLIP, 0.35)] + cap(rot=upright(-75))
    render(parts, 52, -75, fill=0.80).save(OUT / "kaffeeklipp-2.jpg", quality=90)
    print("2 ok")

    # 3) Offen: Hülse ausgeschwenkt, Deckel daneben
    P = k.PIV
    s_sw = S.translate((k.XR, 0, 0)).translate((-P[0], -P[1], 0)).rotate((0, 0, 70)).translate((P[0], P[1], 0))
    parts = [(tm(A), CLIP, 0.35), (tm(B.rotate((0, 0, 14))), CLIP, 0.35), (tm(s_sw), CLIP, 0.35)]
    # Deckel liegt mit Logo nach oben daneben
    capflat = [(tm(p.rotate((0, 0, upright(-58))).translate((k.XR + 45, -75, 0))), c, gl)
               for p, c, gl in [(base, CAP, 0.35), (g, GREEN, 0.15), (w, WHITE, 0.25)]]
    render(parts + capflat, 38, -58, fill=0.88).save(OUT / "kaffeeklipp-3.jpg", quality=90)
    print("3 ok")


if __name__ == "__main__":
    main()
