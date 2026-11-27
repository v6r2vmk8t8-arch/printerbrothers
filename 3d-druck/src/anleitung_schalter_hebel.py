"""Ein-Bild-Anleitungen für den Block-Schalter-Hebel -> 3d-druck/schalter-hebel/

  pb-schalter-hebel_anleitung.png       Klebe-Version (Montageplatte mit Montageband)
  pb-schalter-hebel_anleitung-clip.png  Sockel-Clip (rastet in die Nut am Schalterrahmen, keine Platte)

Aufruf:  python3 3d-druck/src/anleitung_schalter_hebel.py
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import pb_schalter_hebel as S  # noqa: E402
from pb_handy_staender import box, to_tm  # noqa: E402
from manifold3d import Manifold, OpType  # noqa: E402

_a = sys.argv; sys.argv = [sys.argv[0]]
import shop_renders as R  # noqa: E402
sys.argv = _a

FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
GREEN, RED, INK = "#2E9E4F", "#D8382B", "#222222"
STONE, WOOD, AXLE, PLATE, FOLL = "#9A9EA3", "#A0703F", "#6B4A2B", "#7A7F84", "#D8382B"
TAPE, TOOL = "#F2C230", "#2F6FD0"
LIGHT = (-0.3, -0.6, 0.75)
P = 760                                     # Bildgröße je Schritt


def add(lst):
    return Manifold.batch_boolean(lst, OpType.Add)


def font(sz, bold=False):
    return ImageFont.truetype(FB if bold else FR, sz)


def up(m):
    """Gebrauchslage (z aus der Wand) -> Renderer (z nach oben): Wand steht senkrecht."""
    return m.rotate((90, 0, 0))


def shot(parts, elev=16, azim=-55, fill=0.8, raw=False):
    """raw=True: Teile sind schon in Renderer-Koordinaten (z nach oben)."""
    R.SIZE = P
    im = R.render([(to_tm(m if raw else up(m)), c, g) for m, c, g in parts], elev, azim, fill=fill,
                  bg=("#FFFFFF", "#F1F1F1"), light_from=LIGHT if not raw else (-0.45, 0.35, 0.82))
    proj = R.render.project

    def px(pt):                              # Punkt in Gebrauchslage -> Pixel
        q = np.array([pt], float)
        if not raw:
            q = np.column_stack((q[:, 0], -q[:, 2], q[:, 1]))     # gleiche Drehung wie up()
        return tuple(proj(q)[0])
    return im, px


def arrow(d, a, b, col=GREEN, w=7):
    d.line([a, b], fill=col, width=w)
    v = np.array(b) - np.array(a); v = v / (np.linalg.norm(v) + 1e-9); n = np.array([-v[1], v[0]])
    tip = np.array(b)
    d.polygon([tuple(tip), tuple(tip - v * 26 + n * 14), tuple(tip - v * 26 - n * 14)], fill=col)


def label(d, xy, text, col=INK, sz=26, bold=True):
    f = font(sz, bold)
    x, y = xy
    w = d.textlength(text, font=f)
    d.rounded_rectangle((x - 8, y - 6, x + w + 8, y + sz + 8), 8, fill="white", outline=col, width=3)
    d.text((x, y), text, font=f, fill=col)


def main(clip=False):
    FT = S.FRAME_T
    F2 = S.FRAME / 2
    hy = S.BASE_H / 2
    wall = box(-95, 95, -110, 110, -FT - 3, -FT)
    frame = box(-F2, F2, -F2, F2, -FT, 0)
    rocker = box(-28.5, 28.5, -28.5, 28.5, 0, 5)
    base = S.base_clip() if clip else S.base()
    stick, axle, foll, plate = S.stick_part(), S.axle(), S.follower(5), S.plate(klebe=True)
    switch = [(wall, "#EDE8E0", 0.05), (frame, "#F7F7F5", 0.4), (rocker, "#FDFDFC", 0.4)]
    pl = [] if clip else [(plate, PLATE, 0.2)]            # Montageplatte nur bei der Klebe-Version
    pad = box(-8, 8, -8, 8, 5, 5.0 + 0.9)                 # Klebepad unter dem Mitnehmer
    steps = []

    # 1 – Teile (liegend wie nach dem Druck), beschriftet
    lay = {} if clip else {"Platte": (plate.translate((0, 0, FT)).translate((-110, 30, 0)), PLATE)}
    lay.update({
        "Sockel-Clip" if clip else "Sockel":
            (base.rotate((180, 0, 0)).translate((0, 0, S.DEPTH)).translate((-45 if clip else 10, 40, 0)), STONE),
        "Stab": (stick.translate((0, 0, -S.ZA)).rotate((-90, 0, 0)).translate((-40, -105, 11)), WOOD),
        "Achse": (axle.translate((0, 0, -S.ZA)).translate((60, -85, 4.5)), AXLE),
        "Mitnehmer": (foll.translate((0, 0, -5)).translate((95, 30, 0) if clip else (110, -40, 0)), FOLL),
    })
    im, px = shot([(m, c, 0.25) for m, c in lay.values()], 38, -70, 0.9, raw=True)
    d = ImageDraw.Draw(im)
    for name, (m, c) in lay.items():
        bbx = m.bounding_box(); x, y = px(((bbx[0] + bbx[3]) / 2, (bbx[1] + bbx[4]) / 2, bbx[5]))
        label(d, (x - 40, y - 60), name, INK, 22)
    if clip:
        label(d, (30, 30), "Keine Platte, kein Werkzeug nötig")
    steps.append(("Teile", im))

    if not clip:
        # Klebeband in die Taschen (Rückseite), dann Platte um den Rahmen an die Wand
        tape = add([box(-42, 42, *sorted((sy * 46.5, sy * 62.0)), -FT - 0.4, -FT + 1.0) for sy in (-1, 1)])
        back = [(plate.rotate((180, 0, 0)), PLATE, 0.2), (tape.rotate((180, 0, 0)), TAPE, 0.2)]
        im1, _ = shot(back, 55, -80, 0.86, raw=True)
        im2, px = shot(switch + [(plate.translate((0, 0, 55)), PLATE, 0.2)], 16, -68, 0.8)
        im = im2.copy(); im.paste(im1.resize((330, 330)), (P - 345, P - 345))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((P - 345, P - 345, P - 15, P - 15), 14, outline="#BBBBBB", width=3)
        arrow(d, px((0, 75, 64)), px((0, 75, -2)))
        label(d, (30, 30), "Montageband in die 2 Taschen,")
        label(d, (30, 78), "um den Rahmen an die Wand drücken", INK, 22, False)
        steps.append(("Kleben", im))

    # Mitnehmer mittig auf die Wippe
    parts = switch + pl + [(foll.translate((0, 0, 40)), FOLL, 0.3)]
    if clip:
        parts.append((pad.translate((0, 0, 22)), TAPE, 0.2))
    im, px = shot(parts, 22, -72, 1.25)
    d = ImageDraw.Draw(im)
    arrow(d, px((0, 0, 70)), px((0, 0, 14)))
    label(d, (30, 30), "Mitnehmer genau in die Mitte" if clip else "genau in die Mitte")
    if clip:
        label(d, (30, 78), "mit Klebepad auf die Wippe kleben", INK, 22, False)
    steps.append(("Mitnehmer", im))

    # Achse in den Stab (Nase zur Wand)
    st = S.place_lever(stick, 0)
    im, px = shot([(st, WOOD, 0.25), (axle.translate((60, 0, 0)), AXLE, 0.3)], 24, -62, 0.86)
    d = ImageDraw.Draw(im)
    arrow(d, px((95, 0, S.ZA)), px((22, 0, S.ZA)))
    label(d, (30, 30), "Nase zur Wand")
    steps.append(("Achse", im))

    # Sockel mit der Vorderseite auf den Tisch, Hebel von hinten in die Lagerböcke klicken
    flip = lambda m: m.rotate((180, 0, 0)).translate((0, 0, S.DEPTH))
    lev = flip(S.place_lever(stick + axle, -45)).translate((0, 0, 45))
    im, px = shot([(flip(base), STONE, 0.2), (lev, WOOD, 0.25)], 50, -60, 0.86, raw=True)
    d = ImageDraw.Draw(im)
    za = S.DEPTH - S.ZA
    for sx in (-1, 1):
        arrow(d, px((sx * (S.INNER_W / 2 + 1.5), 0, za + 60)), px((sx * (S.INNER_W / 2 + 1.5), 0, za + 8)))
    label(d, (30, 30), "Stab durchstecken, Achse klicken!", GREEN)
    steps.append(("Einklicken", im))

    lever = [(S.place_lever(stick, 45), WOOD, 0.25), (S.place_lever(axle, 45), AXLE, 0.3)]
    if clip:
        # Sockel-Clip aufdrücken, bis die Federarme links und rechts in die Nut klicken
        lift = 85
        mv = lambda m: m.translate((0, 0, lift))
        parts = switch + [(foll, FOLL, 0.3), (mv(base), STONE, 0.2)] + [(mv(m), c, g) for m, c, g in lever]
        im, px = shot(parts, 14, -62, 0.8)
        d = ImageDraw.Draw(im)
        for sx in (-1, 1):
            x = sx * (S.BASE_W / 2 + 6)
            arrow(d, px((x, -20, lift + 10)), px((x, -20, 4)))
        label(d, (30, 30), "Gerade aufdrücken,")
        label(d, (30, 78), "bis es links + rechts klickt", GREEN, 24)
        label(d, (30, P - 70), "Schlitz zeigt nach unten", INK, 22, False)
        steps.append(("Aufdrücken", im))

        # Fertig + Abnehmen: Ansicht von schräg unten auf den Schlitz
        screwdriver = add([box(-1.5, 1.5, -hy - 60, -hy - 8, -FT + 0.2, -FT + 1.0),
                           box(-4.5, 4.5, -hy - 110, -hy - 60, -FT - 3.5, -FT + 5.5)])
        parts = switch + [(foll, FOLL, 0.3), (base, STONE, 0.2)] + lever + [(screwdriver, TOOL, 0.3)]
        im, px = shot(parts, -18, -58, 0.8)
        d = ImageDraw.Draw(im)
        arrow(d, px((0, -hy - 40, -FT + 0.6)), px((0, -hy - 4, -FT + 0.6)), TOOL)
        label(d, (30, 30), "Hebel hoch / runter = Licht an / aus", GREEN, 24)
        label(d, (30, P - 118), "Abnehmen: Schraubenzieher in den", INK, 22, False)
        label(d, (30, P - 70), "Schlitz unten, sanft hebeln", INK, 22, False)
        steps.append(("Fertig", im))
    else:
        # Sockel aufstecken, Hebel schaltet
        im, px = shot(switch + pl + [(foll, FOLL, 0.3), (base, STONE, 0.2)] + lever, 14, -62, 0.8)
        d = ImageDraw.Draw(im)
        label(d, (30, 30), "Sockel aufstecken – rastet ein")
        label(d, (30, P - 70), "Hebel hoch / runter = Licht an / aus", GREEN, 24)
        steps.append(("Fertig", im))

    # Seite zusammensetzen
    W, H = 2 * P + 90, 3 * P + 260
    page = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(page)
    d.rectangle((0, 0, W, 14), fill=RED)
    d.text((40, 44), "Block-Hebel für den Lichtschalter", font=font(58, True), fill=INK)
    sub = ("Sockel-Clip · Efapel Logus 90 (85,6 mm) · ohne Werkzeug · 1 Klebepad für den Mitnehmer"
           if clip else "Klebe-Version · Werkzeug: keins · Montageband (bis 18 mm breit, ca. 1 mm dick)")
    d.text((42, 120), sub, font=font(30), fill="#555")
    for k, (title, im) in enumerate(steps):
        x, y = 30 + (k % 2) * (P + 30), 190 + (k // 2) * (P + 20)
        page.paste(im, (x, y))
        d.rounded_rectangle((x, y, x + P, y + P), 18, outline="#DDDDDD", width=3)
        d.ellipse((x + P - 96, y + 18, x + P - 18, y + 96), fill=RED)
        d.text((x + P - 57, y + 57), str(k + 1), font=font(44, True), fill="white", anchor="mm")
    name = "pb-schalter-hebel_anleitung" + ("-clip" if clip else "")
    page.save(S.OUT / f"{name}.png")
    page.resize((W // 2, H // 2), Image.LANCZOS).save(S.OUT / f"{name}_klein.png")
    print("Anleitung:", S.OUT / f"{name}.png", page.size)


if __name__ == "__main__":
    main(clip=False)
    main(clip=True)
