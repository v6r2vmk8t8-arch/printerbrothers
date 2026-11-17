"""Bauanleitung Formel-Modellbausatz (A4 hoch, PNG + PDF) -> 3d-druck/formel-modellbausatz/

Aufruf:  python3 3d-druck/src/bauanleitung_formel.py
"""
import sys
from pathlib import Path

import trimesh
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import pb_formel_modellbausatz as K  # noqa: E402

_a = sys.argv; sys.argv = [sys.argv[0]]
import shop_renders as S  # noqa: E402
sys.argv = _a

OUT = K.OUT
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
RED, BLK, GRY, YEL, NEW = "#D8382B", "#2B2B2B", "#9A9A9A", "#F2B705", "#39B54A"

STEPS = [
    ("Rumpf", ["A1 Rumpf links", "A2 Rumpf rechts"],
     "A1 + A2 mit 4 Passstiften A14 zusammenstecken und verkleben (Sekundenkleber)."),
    ("Unterboden & Seitenkästen", ["A3 Unterboden", "A4 Seitenkasten links", "A5 Seitenkasten rechts"],
     "Unterboden A3 mit den Zapfen von unten einkleben. Seitenkästen A4/A5 mit je 2 Passstiften A14 ankleben."),
    ("Frontflügel", ["A6 Frontflügel", "A7 Front-Flap rechts", "A7 Front-Flap links", "A8 Endplatte vorne links", "A9 Endplatte vorne rechts"],
     "Frontflügel A6 seitlich durch den Schlitz in der Nase schieben, mittig ausrichten, kleben. Flaps A7 und Endplatten A8 aufstecken."),
    ("Heckflügel", ["A14 Pylon", "A10 Heckflügel", "A11 Heck-Flap", "A12 Endplatte hinten links", "A13 Endplatte hinten rechts"],
     "Pylon A12 in den Schlitz der Motorabdeckung kleben, Heckflügel A9 aufsetzen, Flap A10 und Endplatten A11 anbringen."),
    ("Cockpit & Details", ["B Fahrer", "B Lenkrad", "A15 Spiegel links", "A16 Spiegel rechts", "B Auspuff"],
     "Fahrer B6 ins Cockpit, Lenkrad B7 davor, Spiegel A13 auf die Cockpitkante, Auspuff B8 ins Heck stecken."),
    ("Fahrwerk", None,
     "Querlenker B5 in die Taschen kleben. Achsen B3 (hinten) / B4 (vorne) durchschieben, Räder B1 / B2 aufdrücken – NICHT kleben, damit sie rollen."),
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


def step_image(P, done, new, size=760):
    parts = []
    for n in done:
        c, g = color(n)
        parts.append((K.to_tm(P[n]), c, g))
    for n in new:
        parts.append((K.to_tm(P[n]), NEW, 0.5))
    return S.render(parts, 28, -55, fill=0.9).resize((size, size))


def main():
    P = K.assembled()
    names = list(P)
    fahrwerk = [n for n in names if n.startswith(("B Querlenker", "B Achse", "B Räder"))]
    W, H = 1654, 2339                              # A4 bei 200 dpi
    pages = []
    # Seite 1: Titel + Teileübersicht
    pg = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(pg)
    d.text((90, 80), "FORMEL PB", font=ImageFont.truetype(FB, 96), fill=RED)
    d.text((95, 200), "Modellbausatz · Printer Brothers", font=ImageFont.truetype(FR, 44), fill="#333")
    hero = S.render([(K.to_tm(m),) + color(n) for n, m in P.items()], 22, -58, fill=0.86).resize((1460, 1460))
    pg.paste(hero, (97, 300))
    f = ImageFont.truetype(FR, 34)
    tips = ["Werkzeug: Seitenschneider, feine Feile/Schleifpapier, Sekundenkleber.",
            "Teile mit dem Seitenschneider vom Gießast trennen, Angussreste glatt feilen.",
            "Vor dem Kleben immer trocken anpassen. Räder NICHT kleben.",
            "Spritzling A = Karosserie, Spritzling B = Fahrwerk – Nummern stehen am Rahmen."]
    for k, t in enumerate(tips):
        d.text((110, 1810 + k * 62), "•  " + t, font=f, fill="#222")
    pages.append(pg)
    # Bauschritte, 2 pro Seite
    done = []
    for i in range(0, len(STEPS), 2):
        pg = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(pg)
        for j, (title, new, text) in enumerate(STEPS[i:i + 2]):
            new = new if new is not None else fahrwerk
            y0 = 90 + j * 1120
            d.text((90, y0), f"{i + j + 1}", font=ImageFont.truetype(FB, 110), fill=RED)
            d.text((230, y0 + 22), title, font=ImageFont.truetype(FB, 58), fill="#222")
            # Text umbrechen
            words, line, yy = text.split(), "", y0 + 120
            ft = ImageFont.truetype(FR, 36)
            for w_ in words:
                if d.textlength(line + " " + w_, font=ft) > W - 200:
                    d.text((100, yy), line.strip(), font=ft, fill="#333"); yy += 50; line = ""
                line += " " + w_
            d.text((100, yy), line.strip(), font=ft, fill="#333")
            pg.paste(step_image(P, done, new, 840), (400, y0 + 220))
            d.text((1260, y0 + 240), "grün = neu", font=ImageFont.truetype(FR, 30), fill=NEW)
            done += new
        pages.append(pg)
    pages[0].save(OUT / "pb-formel-modellbausatz_bauanleitung.pdf", save_all=True, append_images=pages[1:], resolution=200)
    for k, p in enumerate(pages, 1):
        p.resize((827, 1170)).save(OUT / f"pb-formel-modellbausatz_bauanleitung_seite{k}.png")
    print("Bauanleitung:", len(pages), "Seiten")


if __name__ == "__main__":
    main()
