"""Bauanleitung Formel-Modellbausatz (A4 hoch, PDF + PNG je Seite) -> 3d-druck/formel-modellbausatz/

Seiten: Titel/Werkzeug, Teileübersicht Spritzling A, Teileübersicht Spritzling B, Bauschritte, Fertig.
Aufruf:  python3 3d-druck/src/bauanleitung_formel.py
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import pb_formel_modellbausatz as K  # noqa: E402

_a = sys.argv; sys.argv = [sys.argv[0]]
import shop_renders as S  # noqa: E402
sys.argv = _a

OUT = K.OUT
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
RED, BLK, GRY, YEL, NEW = "#D8382B", "#2B2B2B", "#9A9A9A", "#F2B705", "#2E9E4F"
INK, MUTED = "#222222", "#555555"
W, H = 1654, 2339                                   # A4 hoch bei 200 dpi


def font(sz, bold=False):
    return ImageFont.truetype(FB if bold else FR, sz)


# ------------------------------------------------------------------ Teileliste (Nummern wie am Gießast)
PARTS = {
    "A1": ("Rumpf, linke Hälfte", 1), "A2": ("Rumpf, rechte Hälfte", 1), "A3": ("Unterboden", 1),
    "A4": ("Seitenkasten links", 1), "A5": ("Seitenkasten rechts", 1), "A6": ("Frontflügel", 1),
    "A7": ("Front-Flap", 2), "A8": ("Endplatte vorne", 2), "A9": ("Heckflügel", 1),
    "A10": ("Heck-Flap", 1), "A11": ("Endplatte hinten", 2), "A12": ("Heckflügel-Pylon", 1),
    "A13": ("Rückspiegel", 2), "A14": ("Passstift", 8),
    "B1": ("Hinterrad", 2), "B2": ("Vorderrad", 2), "B3": ("Hinterachse (lang)", 1),
    "B4": ("Vorderachse (kurz)", 1), "B5": ("Querlenker", 8), "B6": ("Fahrer", 1),
    "B7": ("Lenkrad", 1), "B8": ("Auspuff", 1), "B9": ("Ausstellungs-Ständer", 1),
}

# Bauteil im Zusammenbau -> Nummer am Gießast
def nr_of(name):
    fixed = {"A8 Endplatte vorne links": "A8", "A9 Endplatte vorne rechts": "A8", "A10 Heckflügel": "A9",
             "A11 Heck-Flap": "A10", "A12 Endplatte hinten links": "A11", "A13 Endplatte hinten rechts": "A11",
             "A14 Pylon": "A12", "A15 Spiegel links": "A13", "A16 Spiegel rechts": "A13",
             "B Räder hinten": "B1", "B Räder vorne": "B2", "B Achse hinten": "B3", "B Achse vorne": "B4",
             "B Fahrer": "B6", "B Lenkrad": "B7", "B Auspuff": "B8"}
    if name in fixed:
        return fixed[name]
    if name.startswith("B Querlenker"):
        return "B5"
    return name.split()[0]


STEPS = [
    ("Rumpf", ["A1 Rumpf links", "A2 Rumpf rechts"], [("A1", 1), ("A2", 1), ("A14", 4)],
     ["4 Passstifte A14 in die Löcher einer Rumpfhälfte stecken.",
      "A1 und A2 erst trocken zusammenstecken – die Hälften müssen ohne Spalt aufeinanderliegen.",
      "Dünn Sekundenkleber auf die Teilungsfläche, zusammendrücken, 30 Sekunden halten."]),
    ("Unterboden & Seitenkästen", ["A3 Unterboden", "A4 Seitenkasten links", "A5 Seitenkasten rechts"],
     [("A3", 1), ("A4", 1), ("A5", 1), ("A14", 4)],
     ["Unterboden A3 mit den Zapfen von unten in den Rumpf stecken und verkleben.",
      "Je 2 Passstifte A14 in die Seitenkästen stecken.",
      "Seitenkasten A4 links, A5 rechts an den Rumpf kleben (schmales Ende nach vorne)."]),
    ("Frontflügel", ["A6 Frontflügel", "A7 Front-Flap rechts", "A7 Front-Flap links",
                     "A8 Endplatte vorne links", "A9 Endplatte vorne rechts"],
     [("A6", 1), ("A7", 2), ("A8", 2)],
     ["Frontflügel A6 seitlich durch den Schlitz in der Nase schieben und mittig ausrichten.",
      "Mit einem Tropfen Kleber in der Nase fixieren.",
      "Die beiden Flaps A7 hinten auf den Flügel kleben, dann die Endplatten A8 außen ankleben."]),
    ("Heckflügel", ["A14 Pylon", "A10 Heckflügel", "A11 Heck-Flap", "A12 Endplatte hinten links",
                    "A13 Endplatte hinten rechts"],
     [("A12", 1), ("A9", 1), ("A10", 1), ("A11", 2)],
     ["Pylon A12 von oben in den Schlitz der Motorabdeckung kleben.",
      "Heckflügel A9 mit dem Schlitz auf den Pylon setzen, Flap A10 dahinter ankleben.",
      "Endplatten A11 links und rechts an die Flügelenden kleben – auf rechten Winkel achten."]),
    ("Cockpit & Details", ["B Fahrer", "B Lenkrad", "A15 Spiegel links", "A16 Spiegel rechts", "B Auspuff"],
     [("B6", 1), ("B7", 1), ("A13", 2), ("B8", 1)],
     ["Fahrer B6 ins Cockpit setzen (Blick nach vorne) und einkleben.",
      "Lenkrad B7 vor den Fahrer an die Cockpitkante kleben.",
      "Rückspiegel A13 links und rechts auf die Cockpitkante, Auspuff B8 hinten ins Heck stecken."]),
    ("Querlenker", None, [("B5", 8)],
     ["Je 4 Querlenker B5 vorne und hinten in die Taschen am Rumpf kleben (oben und unten).",
      "Kleber sparsam verwenden – die Achsbohrung muss frei bleiben!"]),
    ("Achsen & Räder", ["B Achse hinten", "B Achse vorne", "B Räder hinten", "B Räder vorne"],
     [("B3", 1), ("B4", 1), ("B1", 2), ("B2", 2)],
     ["Lange Achse B3 hinten, kurze Achse B4 vorne durch die Bohrung schieben.",
      "Räder mit der D-Bohrung passend zur Abflachung der Achse aufdrücken: große Räder B1 hinten, kleine B2 vorne.",
      "NICHT kleben! Die Achse dreht sich im Rumpf – so rollt das Auto."]),
]


def color(n):
    if n.startswith("B Räder"):
        return BLK, 0.25
    if n.startswith("B Achse"):
        return GRY, 0.5
    if n.startswith("B Querlenker"):
        return BLK, 0.35
    if n == "B Fahrer":
        return YEL, 0.5
    if n in ("B Lenkrad", "B Auspuff"):
        return "#555555", 0.5
    if any(k in n for k in ("Flügel", "Flap", "Endplatte", "Pylon")):
        return BLK, 0.4
    return RED, 0.5


# ------------------------------------------------------------------ Zeichen-Helfer
def bubble(d, x, y, txt, r=24, col=RED, fsz=None):
    d.ellipse((x - r, y - r, x + r, y + r), fill="white", outline=col, width=max(3, r // 7))
    f = font(fsz or (int(r * 0.85) if len(txt) < 3 else int(r * 0.72)), True)
    d.text((x, y), txt, font=f, fill=col, anchor="mm")


def wrap(d, text, f, maxw):
    lines, line = [], ""
    for w_ in text.split():
        if line and d.textlength(line + " " + w_, font=f) > maxw:
            lines.append(line); line = w_
        else:
            line = (line + " " + w_).strip()
    return lines + [line]


def bullets(d, x, y, items, maxw, f=None, gap=16):
    f = f or font(33)
    for it in items:
        ls = wrap(d, it, f, maxw - 40)
        d.ellipse((x, y + 14, x + 12, y + 26), fill=RED)
        for k, l in enumerate(ls):
            d.text((x + 34, y + k * 44), l, font=f, fill=INK)
        y += len(ls) * 44 + gap
    return y


def chip(d, x, y, nr, cnt):
    txt = f"{cnt}× {nr}" if cnt > 1 else nr
    f = font(32, True)
    w = d.textlength(txt, font=f) + 34
    col = RED if nr.startswith("A") else BLK
    d.rounded_rectangle((x, y, x + w, y + 52), 26, fill=col)
    d.text((x + w / 2, y + 26), txt, font=f, fill="white", anchor="mm")
    return x + w + 12


def callouts(d, img_xy, size, pts_labels, r=24):
    """Nummern-Blasen außen um das Bild verteilen, Hinweislinie zum Bauteil."""
    ox, oy = img_xy
    c = np.array([size / 2, size / 2])
    items = []
    for (px, py), lab in pts_labels:
        p = np.array([px, py], float)
        v = p - c
        v = v / (np.linalg.norm(v) + 1e-9)
        items.append([p, p + v * 95, lab])
    for _ in range(200):                              # Blasen auseinanderschieben
        moved = False
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i][1], items[j][1]
                dv = b - a; dist = np.linalg.norm(dv)
                if dist < 2 * r + 10:
                    dv = dv / (dist + 1e-9) if dist > 1e-6 else np.array([1.0, 0])
                    push = (2 * r + 10 - dist) / 2 + 0.5
                    items[i][1] = a - dv * push; items[j][1] = b + dv * push; moved = True
        for it in items:
            it[1] = np.clip(it[1], r + 4, size - r - 4)
        if not moved:
            break
    for p, q, lab in items:
        d.line((ox + p[0], oy + p[1], ox + q[0], oy + q[1]), fill=NEW, width=3)
        d.ellipse((ox + p[0] - 5, oy + p[1] - 5, ox + p[0] + 5, oy + p[1] + 5), fill=NEW)
    for p, q, lab in items:
        bubble(d, ox + q[0], oy + q[1], lab, r, NEW)


def header(d, title, sub=None):
    d.rectangle((0, 0, W, 16), fill=RED)
    d.text((90, 60), title, font=font(64, True), fill=INK)
    if sub:
        d.text((92, 150), sub, font=font(34), fill=MUTED)


def footer(d, k):
    d.text((W - 90, H - 70), f"FORMEL PB · Seite {k}", font=font(26), fill=MUTED, anchor="ra")


# ------------------------------------------------------------------ Seiten
def page_title(P):
    pg = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(pg)
    d.rectangle((0, 0, W, 16), fill=RED)
    d.text((90, 70), "FORMEL PB", font=font(110, True), fill=RED)
    d.text((95, 205), "Modellbausatz · Maßstab-Rennwagen ca. 11 cm · 43 Teile", font=font(40), fill=MUTED)
    hero = S.render([(K.to_tm(m),) + color(n) for n, m in P.items()], 22, -58, fill=0.86).resize((1300, 1300))
    pg.paste(hero, (177, 285))
    y = 1630
    d.text((90, y), "Im Bausatz", font=font(44, True), fill=INK)
    d.rounded_rectangle((90, y + 70, 790, y + 170), 18, fill="#FBE9E7")
    d.text((120, y + 120), "Spritzling A · Karosserie · 25 Teile", font=font(32, True), fill=RED, anchor="lm")
    d.rounded_rectangle((864, y + 70, 1564, y + 170), 18, fill="#ECECEC")
    d.text((894, y + 120), "Spritzling B · Fahrwerk · 18 Teile", font=font(32, True), fill=BLK, anchor="lm")
    d.text((90, y + 210), "Werkzeug & Tipps", font=font(44, True), fill=INK)
    bullets(d, 95, y + 280, [
        "Seitenschneider, feine Feile oder Schleifpapier (240er), Sekundenkleber (Gel).",
        "Teile mit dem Seitenschneider ein kleines Stück vom Teil entfernt abtrennen, dann den Rest bündig nachschneiden – nicht abbrechen.",
        "Jedes Teil zuerst trocken anpassen, dann kleben. Räder NICHT kleben.",
        "Die Nummer jedes Teils steht auf dem runden Schild am Gießast daneben – siehe Teileübersicht auf Seite 2 und 3.",
    ], W - 190, font(31), gap=10)
    return pg


def page_sprue(kind):
    plate, placed, _, Wf, Hf = K.build_sprue(kind)
    col, g = (RED, 0.45) if kind == "A" else ("#3A3A3A", 0.4)
    old = S.SIZE; S.SIZE = 1480
    im = S.render([(K.to_tm(plate), col, g)], 89.5, -90, fill=0.98, bg=("#FFFFFF", "#F1F1F1"))
    proj = S.render.project
    S.SIZE = old
    pg = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(pg)
    header(d, f"Teileübersicht Spritzling {kind}",
           "Karosserie – rot" if kind == "A" else "Fahrwerk – schwarz")
    x0, y0 = 87, 220
    pg.paste(im, (x0, y0))
    for m, nr in placed:
        bb = m.bounding_box()
        (px, py), = proj([((bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, bb[5])])
        small = min(bb[3] - bb[0], bb[4] - bb[1]) < 5
        bubble(d, x0 + px, y0 + py, nr, 19 if small else 26, RED if kind == "A" else BLK)
    # Teileliste
    items = [(k, v) for k, v in PARTS.items() if k.startswith(kind)]
    y = y0 + 1480 + 30
    d.text((90, y), "Teileliste", font=font(42, True), fill=INK)
    y += 70
    half = (len(items) + 1) // 2
    for i, (nr, (name, cnt)) in enumerate(items):
        cx = 90 + (i // half) * 760
        cy = y + (i % half) * 66
        bubble(d, cx + 30, cy + 26, nr, 26, RED if kind == "A" else BLK)
        d.text((cx + 76, cy + 26), name, font=font(32), fill=INK, anchor="lm")
        d.text((cx + 700, cy + 26), f"{cnt}×", font=font(32, True), fill=MUTED, anchor="rm")
    return pg


def step_block(pg, d, P, k, step, done, y0):
    title, new, need, text = step
    d.text((90, y0), str(k), font=font(120, True), fill=RED)
    d.text((240, y0 + 30), title, font=font(60, True), fill=INK)
    d.line((90, y0 + 150, W - 90, y0 + 150), fill="#E2E2E2", width=3)
    size = 880
    parts = [(K.to_tm(P[n]),) + color(n) for n in done] + [(K.to_tm(P[n]), NEW, 0.5) for n in new]
    old = S.SIZE; S.SIZE = size
    im = S.render(parts, 28, -55, fill=0.80, bg=("#FFFFFF", "#F2F2F2"))
    proj = S.render.project
    S.SIZE = old
    ix, iy = 70, y0 + 175
    pg.paste(im, (ix, iy))
    pts = []
    for n in new:
        comps = [c for c in P[n].decompose() if c.volume() > 5] or [P[n]]
        for comp in comps[:2]:                       # z. B. Räderpaar -> jedes Rad einzeln beschriften
            b = comp.bounding_box()
            c = np.array([[(b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2]])
            pts.append((tuple(proj(c)[0]), nr_of(n)))
    callouts(d, (ix, iy), size, pts, 25)
    # rechte Spalte: benötigte Teile + Text
    rx = 990
    d.text((rx, iy + 10), "Du brauchst:", font=font(34, True), fill=INK)
    x, yy = rx, iy + 70
    for nr, cnt in need:
        w = d.textlength(f"{cnt}× {nr}" if cnt > 1 else nr, font=font(32, True)) + 46
        if x + w > W - 70:
            x, yy = rx, yy + 66
        x = chip(d, x, yy, nr, cnt)
    yy = bullets(d, rx, yy + 100, text, W - 70 - rx, font(30), gap=14)
    d.text((rx, min(yy + 10, iy + size - 40)), "grün = neue Teile in diesem Schritt", font=font(26), fill=NEW)
    return new


def finish_block(pg, d, P, y0):
    d.text((90, y0), "✓", font=font(110, True), fill=NEW)
    d.text((240, y0 + 30), "Fertig!", font=font(60, True), fill=INK)
    d.line((90, y0 + 150, W - 90, y0 + 150), fill="#E2E2E2", width=3)
    st = K.stand()
    wz = min(P[n].bounding_box()[2] for n in P if n.startswith("B Räder"))
    st = st.translate((53, 0, wz - 3.0))
    scene = [(K.to_tm(m),) + color(n) for n, m in P.items()] + [(K.to_tm(st), "#3A3A3A", 0.35)]
    im = S.render(scene, 24, -62, fill=0.92, bg=("#FFFFFF", "#F1F1F1")).resize((880, 880))
    pg.paste(im, (70, y0 + 175))
    rx = 990
    d.text((rx, y0 + 185), "Ständer B9:", font=font(34, True), fill=INK)
    bullets(d, rx, y0 + 250, [
        "Das Auto mit den Rädern in die vier Mulden des Ständers B9 stellen – fertig für die Vitrine oder das Regal.",
        "Für Rennen auf dem Tisch einfach herausnehmen. Läuft ein Rad schwer: Achse leicht drehen, bis sie frei läuft.",
        "Abgebrochene Teile mit Sekundenkleber reparieren. Viel Spaß mit deinem FORMEL PB!",
    ], W - 70 - rx, font(30), gap=14)


def main():
    P = K.assembled()
    fahrwerk = [n for n in P if n.startswith("B Querlenker")]
    pages = [page_title(P), page_sprue("A"), page_sprue("B")]
    done = []
    steps = [(t, n if n is not None else fahrwerk, nd, tx) for t, n, nd, tx in STEPS]
    for i in range(0, len(steps), 2):
        pg = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(pg)
        d.rectangle((0, 0, W, 16), fill=RED)
        for j, st in enumerate(steps[i:i + 2]):
            done += step_block(pg, d, P, i + j + 1, st, list(done), 70 + j * 1120)
        if len(steps[i:i + 2]) == 1:
            finish_block(pg, d, P, 70 + 1120)
        pages.append(pg)
    for k, pg in enumerate(pages, 1):
        footer(ImageDraw.Draw(pg), k)
    for old in OUT.glob("pb-formel-modellbausatz_bauanleitung_seite*.png"):
        old.unlink()
    pages[0].save(OUT / "pb-formel-modellbausatz_bauanleitung.pdf", save_all=True, append_images=pages[1:], resolution=200)
    for k, p in enumerate(pages, 1):
        p.resize((827, 1170), Image.LANCZOS).save(OUT / f"pb-formel-modellbausatz_bauanleitung_seite{k}.png")
    print("Bauanleitung:", len(pages), "Seiten")


if __name__ == "__main__":
    main()
