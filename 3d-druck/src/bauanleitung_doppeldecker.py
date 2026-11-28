"""Bauanleitung PB Doppeldecker (A4 hoch, PDF + PNG je Seite) -> 3d-druck/doppeldecker-bausatz/
und public/anleitungen/pb-doppeldecker-bauanleitung.pdf

Seiten: Titel/Werkzeug, Teileübersicht A, B, C, 7 Bauschritte, Fertig.
Aufruf:  python3 3d-druck/src/bauanleitung_doppeldecker.py
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import pb_doppeldecker_bausatz as D  # noqa: E402

_a = sys.argv; sys.argv = [sys.argv[0]]
import shop_renders as S  # noqa: E402
sys.argv = _a

OUT = D.OUT
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
RED, CREAM, BLK, BROWN, NEW = "#D8382B", "#EFE3C4", "#2B2B2B", "#7A4E2D", "#2E9E4F"
GOLD = "#A9842E"                       # Schriftfarbe für Spritzling B (creme wäre auf Weiß unsichtbar)
INK, MUTED = "#222222", "#555555"
W, H = 1654, 2339                      # A4 hoch bei 200 dpi
KCOL = {"A": RED, "B": GOLD, "C": BLK}


def font(sz, bold=False):
    return ImageFont.truetype(FB if bold else FR, sz)


PARTS = {
    "A1": ("Rumpf, linke Hälfte", 1), "A2": ("Rumpf, rechte Hälfte", 1), "A3": ("Motorhaube", 1),
    "A4": ("Seitenflosse", 1), "A5": ("Seitenruder", 1), "A6": ("Höhenleitwerk", 1), "A7": ("Höhenruder", 2),
    "A8": ("Kopfstütze", 1), "A9": ("Passstift", 6),
    "B1": ("Oberflügel", 1), "B2": ("Unterflügel", 1), "B3": ("Querruder", 4), "B4": ("Flügelstrebe (N)", 2),
    "B5": ("Baldachinstrebe", 2), "B6": ("Fahrwerksbein", 2), "B7": ("Windschutzscheibe", 1),
    "C1": ("Propeller", 1), "C2": ("Spinner", 1), "C3": ("Propellerwelle", 1), "C4": ("Stellring", 1),
    "C5": ("Motorgehäuse", 1), "C6": ("Zylinder", 7), "C7": ("Rad", 2), "C8": ("Radkappe", 2),
    "C9": ("Radachse", 1), "C10": ("Sporn", 1), "C11": ("Pilot", 1), "C12": ("Instrumentenbrett", 1),
    "C13": ("Auspuff", 2), "C14": ("Ständer-Fuß", 1), "C15": ("Ständer-Stab", 1),
}
SPRUE_NAMES = {"A": "Rumpf", "B": "Tragflächen", "C": "Details"}


def nr_of(name):
    return name.split()[0]


def sel(P, *nrs):
    return [n for n in P if nr_of(n) in nrs]


def steps(P):
    return [
        ("Rumpf schließen", sel(P, "A1", "A2", "C3", "C4"), [("A1", 1), ("A2", 1), ("A9", 6), ("C3", 1), ("C4", 1)],
         ["Stellring C4 auf die Propellerwelle C3 drücken – bis 1,5 mm vor das hintere Ende (D-Form beachten).",
          "6 Passstifte A9 in A1 stecken, Welle mit Stellring in die Rinne vorne legen.",
          "A2 trocken aufsetzen, dann Teilungsfläche dünn kleben und zusammendrücken. Die Welle NICHT kleben – sie muss sich drehen."]),
        ("Leitwerk", sel(P, "A6", "A7", "A4", "A5", "C10"), [("A6", 1), ("A7", 2), ("A4", 1), ("A5", 1), ("C10", 1)],
         ["Höhenleitwerk A6 seitlich durch den Schlitz im Heck schieben, mittig ausrichten, verkleben.",
          "Höhenruder A7 auf die Stufen hinten am Leitwerk kleben.",
          "Seitenflosse A4 von oben in den Schlitz kleben, Seitenruder A5 auf die Stufe. Sporn C10 unten ins Heck."]),
        ("Unterflügel & Fahrwerk", sel(P, "B2", "B6", "C9", "C7", "C8") + sel(P, "B3")[2:],
         [("B2", 1), ("B3", 2), ("B6", 2), ("C9", 1), ("C7", 2), ("C8", 2)],
         ["Unterflügel B2 von unten in die Aussparung im Rumpf drücken (Rippen oben), verkleben. Querruder B3 auf die Stufen.",
          "Radachse C9 durch beide Fahrwerksbeine B6 stecken, Beine mit den Zapfen durch den Flügel in den Rumpf kleben.",
          "Räder C7 aufdrücken (NICHT kleben!), dann Radkappen C8 aufkleben."]),
        ("Cockpit", sel(P, "C12", "C11", "B7", "A8", "C13"), [("C12", 1), ("C11", 1), ("B7", 1), ("A8", 1), ("C13", 2)],
         ["Instrumentenbrett C12 an die vordere Cockpitwand kleben (Anzeigen nach hinten).",
          "Pilot C11 einsetzen (Blick nach vorne), Windschutz B7 vor das Cockpit kleben.",
          "Kopfstütze A8 auf die flache Stelle hinter dem Cockpit, Auspuffrohre C13 seitlich vorne einstecken."]),
        ("Streben", sel(P, "B5", "B4"), [("B5", 2), ("B4", 2)],
         ["Baldachinstreben B5 mit den langen Zapfen oben in den Rumpf kleben (Schrägstrebe zeigt nach vorne oben).",
          "Flügelstreben B4 in die Löcher außen am Unterflügel kleben.",
          "Alle Streben senkrecht ausrichten (von vorne prüfen) und gut trocknen lassen."]),
        ("Oberflügel", sel(P, "B1") + sel(P, "B3")[:2], [("B1", 1), ("B3", 2)],
         ["Querruder B3 auf die Stufen am Oberflügel B1 kleben.",
          "Oberflügel trocken auf alle 8 Strebenzapfen setzen – wenn alles passt: je ein Tropfen Kleber in die Löcher und aufdrücken.",
          "Von vorne und von oben prüfen: Flügel parallel und gerade? Dann 10 Minuten nicht berühren."]),
        ("Motor & Propeller", sel(P, "C5", "C6", "A3", "C1", "C2"),
         [("C5", 1), ("C6", 7), ("A3", 1), ("C1", 1), ("C2", 1)],
         ["7 Zylinder C6 mit dem kleinen Zapfen in die Löcher des Motorgehäuses C5 kleben (Kühlrippen außen).",
          "Motor über die Welle auf die Rumpfnase kleben, Motorhaube A3 darum herum kleben.",
          "Propeller C1 auf die Welle drücken (nicht kleben), Spinner C2 vorne auf den Propeller kleben. Kein Kleber an die Welle!"]),
    ]


def color(n):
    k = nr_of(n)
    if k == "C11":
        return BROWN, 0.4
    if k in ("C7", "C8"):
        return BLK, 0.25
    if k[0] == "A":
        return RED, 0.5
    if k[0] == "B":
        return CREAM, 0.4
    return "#3A3A3A", 0.45


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


def bullets(d, x, y, items, maxw, f=None, gap=16, lh=44):
    f = f or font(33)
    for it in items:
        ls = wrap(d, it, f, maxw - 40)
        d.ellipse((x, y + 14, x + 12, y + 26), fill=RED)
        for k, l in enumerate(ls):
            d.text((x + 34, y + k * lh), l, font=f, fill=INK)
        y += len(ls) * lh + gap
    return y


def chip(d, x, y, nr, cnt):
    txt = f"{cnt}× {nr}" if cnt > 1 else nr
    f = font(32, True)
    w = d.textlength(txt, font=f) + 34
    d.rounded_rectangle((x, y, x + w, y + 52), 26, fill=KCOL[nr[0]])
    d.text((x + w / 2, y + 26), txt, font=f, fill="white", anchor="mm")
    return x + w + 12


def callouts(d, img_xy, size, pts_labels, r=24):
    ox, oy = img_xy
    c = np.array([size / 2, size / 2])
    items = []
    for (px, py), lab in pts_labels:
        p = np.array([px, py], float)
        v = p - c
        v = v / (np.linalg.norm(v) + 1e-9)
        items.append([p, p + v * 95, lab])
    for _ in range(300):
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
    d.text((W - 90, H - 70), f"PB DOPPELDECKER · Seite {k}", font=font(26), fill=MUTED, anchor="ra")


def scene(P, extra=()):
    return [(D.to_tm(m),) + color(n) for n, m in P.items()] + list(extra)


# ------------------------------------------------------------------ Seiten
def page_title(P):
    pg = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(pg)
    d.rectangle((0, 0, W, 16), fill=RED)
    d.text((90, 70), "PB DOPPELDECKER", font=font(104, True), fill=RED)
    d.text((95, 205), "Modellbausatz · Spannweite 15 cm · 52 Teile · 3 Gießäste", font=font(40), fill=MUTED)
    hero = S.render(scene(P), 20, -55, fill=0.88).resize((1300, 1300))
    pg.paste(hero, (177, 275))
    y = 1600
    d.text((90, y), "Im Bausatz", font=font(44, True), fill=INK)
    for i, (k, nm, n, bg) in enumerate((("A", "Rumpf", 15, "#FBE9E7"), ("B", "Tragflächen", 13, "#F7F1E1"), ("C", "Details", 24, "#ECECEC"))):
        x = 90 + i * 495
        d.rounded_rectangle((x, y + 70, x + 470, y + 170), 18, fill=bg)
        d.text((x + 24, y + 102), f"Spritzling {k} · {nm}", font=font(30, True), fill=KCOL[k], anchor="lm")
        d.text((x + 24, y + 142), f"{n} Teile", font=font(28), fill=MUTED, anchor="lm")
    d.text((90, y + 210), "Werkzeug & Tipps", font=font(44, True), fill=INK)
    bullets(d, 95, y + 280, [
        "Seitenschneider, feine Feile oder Schleifpapier (240er), Sekundenkleber (Gel), Pinzette für die Kleinteile.",
        "Teile ein Stück vom Teil entfernt abtrennen, Rest bündig nachschneiden – nicht abbrechen.",
        "Jedes Teil zuerst trocken anpassen, dann kleben. Propeller und Räder NICHT kleben – sie drehen sich.",
        "Die Nummer steht auf dem runden Schild am Gießast. Bauzeit: ca. 2–3 Stunden.",
    ], W - 190, font(31), gap=10)
    return pg


def page_sprue(kind):
    plate, placed, _, Wf, Hf = D.build_sprue(kind)
    col, g = {"A": (RED, 0.45), "B": ("#E2D3AA", 0.4), "C": ("#3A3A3A", 0.4)}[kind]
    items = [(k, v) for k, v in PARTS.items() if k.startswith(kind)]
    ncol = 3 if len(items) > 10 else 2
    rows = (len(items) + ncol - 1) // ncol
    isz = min(1480, H - 220 - 140 - 110 - rows * 62 - 40)
    old = S.SIZE; S.SIZE = isz
    im = S.render([(D.to_tm(plate), col, g)], 89.5, -90, fill=0.98, bg=("#FFFFFF", "#F1F1F1"))
    proj = S.render.project
    S.SIZE = old
    pg = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(pg)
    header(d, f"Teileübersicht Spritzling {kind}", f"{SPRUE_NAMES[kind]} – {len(placed)} Teile")
    x0, y0 = (W - isz) // 2, 220
    pg.paste(im, (x0, y0))
    seen = {}
    for m, nr in placed:
        bb = m.bounding_box()
        seen[nr] = seen.get(nr, 0) + 1
        if seen[nr] > 2 and nr in ("A9", "C6"):
            continue
        (px, py), = proj([((bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, bb[5])])
        small = min(bb[3] - bb[0], bb[4] - bb[1]) < 6
        bubble(d, x0 + px, y0 + py, nr, 18 if small else 24, KCOL[kind])
    y = y0 + isz + 30
    d.text((90, y), "Teileliste", font=font(42, True), fill=INK)
    y += 70
    cw = (W - 180) // ncol
    for i, (nr, (name, cnt)) in enumerate(items):
        cx = 90 + (i // rows) * cw
        cy = y + (i % rows) * 62
        bubble(d, cx + 28, cy + 26, nr, 25, KCOL[kind])
        d.text((cx + 70, cy + 26), name, font=font(29), fill=INK, anchor="lm")
        d.text((cx + cw - 24, cy + 26), f"{cnt}×", font=font(29, True), fill=MUTED, anchor="rm")
    return pg


def step_block(pg, d, P, k, step, done, y0):
    title, new, need, text = step
    d.text((90, y0), str(k), font=font(120, True), fill=RED)
    d.text((240, y0 + 30), title, font=font(60, True), fill=INK)
    d.line((90, y0 + 150, W - 90, y0 + 150), fill="#E2E2E2", width=3)
    size = 880
    parts = [(D.to_tm(P[n]),) + color(n) for n in done] + [(D.to_tm(P[n]), NEW, 0.5) for n in new]
    old = S.SIZE; S.SIZE = size
    im = S.render(parts, 26, -52, fill=0.82, bg=("#FFFFFF", "#F2F2F2"))
    proj = S.render.project
    S.SIZE = old
    ix, iy = 70, y0 + 175
    pg.paste(im, (ix, iy))
    pts, cnt = [], {}
    for n in new:
        nr = nr_of(n)
        cnt[nr] = cnt.get(nr, 0) + 1
        if cnt[nr] > 2:
            continue
        b = P[n].bounding_box()
        c = np.array([[(b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2]])
        pts.append((tuple(proj(c)[0]), nr))
    callouts(d, (ix, iy), size, pts, 25)
    rx = 990
    d.text((rx, iy + 10), "Du brauchst:", font=font(34, True), fill=INK)
    x, yy = rx, iy + 70
    for nr, c in need:
        w = d.textlength(f"{c}× {nr}" if c > 1 else nr, font=font(32, True)) + 46
        if x + w > W - 70:
            x, yy = rx, yy + 66
        x = chip(d, x, yy, nr, c)
    yy = bullets(d, rx, yy + 90, text, W - 70 - rx, font(28), gap=12, lh=40)
    d.text((rx, min(yy + 10, iy + size - 40)), "grün = neue Teile in diesem Schritt", font=font(26), fill=NEW)
    return new


def finish_block(pg, d, P, y0):
    d.text((90, y0), "✓", font=font(110, True), fill=NEW)
    d.text((240, y0 + 30), "Fertig!", font=font(60, True), fill=INK)
    d.line((90, y0 + 150, W - 90, y0 + 150), fill="#E2E2E2", width=3)
    base, pole = D.on_stand(P)
    sc = scene(P, [(D.to_tm(base), "#3A3A3A", 0.35), (D.to_tm(pole), "#3A3A3A", 0.35)])
    im = S.render(sc, 18, -58, fill=0.92, bg=("#FFFFFF", "#F1F1F1")).resize((880, 880))
    pg.paste(im, (70, y0 + 175))
    rx = 990
    d.text((rx, y0 + 185), "Ständer C14 + C15:", font=font(34, True), fill=INK)
    bullets(d, rx, y0 + 250, [
        "Stab C15 in den Ständer-Fuß C14 kleben.",
        "Den Doppeldecker mit dem viereckigen Loch unter dem Unterflügel auf den Stab stecken – nicht kleben, dann kann er auch auf dem Tisch stehen.",
        "Pusten: Der Propeller dreht sich. Abgebrochene Teile mit Sekundenkleber reparieren. Guten Flug!",
    ], W - 70 - rx, font(28), gap=12, lh=40)


def build_pages():
    P = D.assembled()
    pages = [page_title(P)] + [page_sprue(k) for k in "ABC"]
    done = []
    st = steps(P)
    for i in range(0, len(st), 2):
        pg = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(pg)
        d.rectangle((0, 0, W, 16), fill=RED)
        for j, s in enumerate(st[i:i + 2]):
            done += step_block(pg, d, P, i + j + 1, s, list(done), 70 + j * 1120)
        if len(st[i:i + 2]) == 1:
            finish_block(pg, d, P, 70 + 1120)
        pages.append(pg)
    for k, pg in enumerate(pages, 1):
        footer(ImageDraw.Draw(pg), k)
    return pages


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pages = build_pages()
    for old in OUT.glob(f"{D.NAME}_bauanleitung_seite*.png"):
        old.unlink()
    pdf = OUT / f"{D.NAME}_bauanleitung.pdf"
    pages[0].save(pdf, save_all=True, append_images=pages[1:], resolution=200)
    pub = D.ROOT / "public/anleitungen/pb-doppeldecker-bauanleitung.pdf"
    pub.write_bytes(pdf.read_bytes())
    for k, p in enumerate(pages, 1):
        p.resize((827, 1170), Image.LANCZOS).save(OUT / f"{D.NAME}_bauanleitung_seite{k}.png")
    print("Bauanleitung:", len(pages), "Seiten")


if __name__ == "__main__":
    main()
