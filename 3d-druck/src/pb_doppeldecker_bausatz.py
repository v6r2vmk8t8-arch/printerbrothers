"""Printer Brothers Doppeldecker – Modellbausatz zum Heraustrennen und Kleben (3 Spritzlinge, 52 Teile).

Klassischer Sport-Doppeldecker (kein Nachbau eines bestimmten Flugzeugs), ca. 13 cm lang, 15 cm Spannweite.
  Spritzling A (Rumpf):        Rumpfhälften, Motorhaube, Seitenflosse/-ruder, Höhenleitwerk/-ruder, Kopfstütze, Passstifte
  Spritzling B (Tragflächen):  Ober-/Unterflügel, 4 Querruder, Flügel- und Baldachinstreben, Fahrwerksbeine, Windschutz
  Spritzling C (Details):      Propeller, Welle, Sternmotor mit 7 einzelnen Zylindern, Räder, Pilot, Sporn, Ständer
Propeller und Räder drehen sich nach dem Zusammenbau (D-Wellen mit Presssitz, wie beim Formel-Bausatz).

Aufruf:  python3 3d-druck/src/pb_doppeldecker_bausatz.py
"""
import sys
from pathlib import Path

import numpy as np
from manifold3d import CrossSection, JoinType, Manifold, OpType

sys.path.insert(0, str(Path(__file__).parent))
import pb_formel_modellbausatz as K  # noqa: E402  (Loft, Spritzling, Packen, Achsen, Räder …)
from pb_formel_modellbausatz import box, cyl_y, poly, to_tm, d_profile, check  # noqa: E402

ROOT = K.ROOT
OUT = ROOT / "3d-druck/doppeldecker-bausatz"
NAME = "pb-doppeldecker-bausatz"

# ---------------------------------------------------------------- Hauptmaße (Fluglage: x Nase->Heck, y Spannweite, z hoch)
ZC = 32.0                      # Propellerachse
FUS = [  # x, halbe Breite, z unten, z oben
    (10, 12.0, 19.5, 44.5), (16, 12.2, 19.6, 45.2), (24, 12.0, 20.3, 45.5), (36, 11.6, 20.6, 45.5),
    (50, 10.8, 21.5, 45.0), (62, 9.6, 23.0, 44.2), (76, 7.8, 26.0, 42.8), (90, 5.8, 29.0, 41.3),
    (104, 3.8, 32.0, 40.0), (116, 2.0, 34.0, 39.0), (121, 1.2, 34.8, 38.6)]
EXPO = 2.6
CHORD, WT = 27.0, 3.0          # Flügeltiefe, max. Profildicke
UW_X, UW_Z, UW_S = 14.0, 56.0, 75.0   # Oberflügel: Vorderkante, Unterseite, halbe Spannweite
LW_X, LW_Z, LW_S = 23.0, 20.0, 68.0   # Unterflügel
TE_MIN, SHELF = 1.1, 0.5       # Hinterkante min. Dicke, Ruder-Auflage
AIL = (6.0, 22.0)              # Querruder Tiefe / Länge
PIN, SOCK = 1.6, 1.95          # Streben-Zapfen / Loch (quadratisch)
ST = 1.6                       # Strebenstärke
GEAR_Y, GEAR_T = 8.0, 2.0      # Fahrwerksbein Lage / Stärke
X_W, Z_W, R_W, W_W = 21.0, 9.0, 9.0, 6.0   # Rad
BORE = K.BORE
STAB_Z, STAB_T = 35.4, 1.6
FIN_T = 1.6
COCK = (46.0, 60.0, 5.6, 35.0)  # Cockpit x0, x1, halbe Breite, Boden
SLOT_G = 0.08                  # Spiel je Seite in Schlitzen


def interp(i, x):
    xs = [s[0] for s in FUS]
    return float(np.interp(x, xs, [s[i] for s in FUS]))


def z_top(x, y):
    hw, zb, zt = interp(1, x), interp(2, x), interp(3, x)
    hh, zc = (zt - zb) / 2, (zt + zb) / 2
    q = min(abs(y) / hw, 1.0) ** EXPO
    return zc + hh * (1 - q) ** (1 / EXPO)


def z_bot(x, y):
    hw, zb, zt = interp(1, x), interp(2, x), interp(3, x)
    hh, zc = (zt - zb) / 2, (zt + zb) / 2
    q = min(abs(y) / hw, 1.0) ** EXPO
    return zc - hh * (1 - q) ** (1 / EXPO)


def plate_xz(pts, y0, t):
    """Platte in der x-z-Ebene, Stärke t ab y0 (gedruckt: flach liegend)."""
    return Manifold.extrude(poly(pts), t).rotate((90, 0, 0)).translate((0, y0 + t, 0))


def plate_xy(pts, z0, t):
    return Manifold.extrude(poly(pts), t).translate((0, 0, z0))


# ---------------------------------------------------------------- Flügelprofil
def thick(t):
    t = np.clip(t, 0, 1)
    yt = 5 * (0.2969 * np.sqrt(t) - 0.126 * t - 0.3516 * t ** 2 + 0.2843 * t ** 3 - 0.1036 * t ** 4)
    return np.maximum(WT * 2 * yt, np.where(t > 0.5, TE_MIN, 0.7))


def profile(off=0.0):
    ts = np.linspace(0, 1, 60)
    top = [(CHORD * t, float(thick(t))) for t in ts]
    cs = poly([(0, 0)] + top[1:] + [(CHORD, 0)])
    return cs.offset(off, JoinType.Round) if off else cs


def wing_raw(x0, z0, S, ribs_skip=0.0):
    sec = Manifold.extrude(profile(), 2 * S + 2).rotate((90, 0, 0)).translate((0, S + 1, 0))   # Spannweite entlang y
    plan = CrossSection.square((CHORD, 2 * S)).translate((0, -S)).offset(-9, JoinType.Round).offset(9, JoinType.Round)
    w = sec ^ Manifold.extrude(plan, 10).translate((0, 0, -1))
    # Rippen (Stoff über Rippen): 0.25 mm erhaben, alle 9 mm
    skin = w.translate((0, 0, 0.25)) - w
    slabs = []
    for k in range(-int(S // 9), int(S // 9) + 1):
        y = k * 9.0
        if abs(y) < ribs_skip or abs(y) > S - 5:
            continue
        slabs.append(box(-1, CHORD + 1, y - 0.4, y + 0.4, -1, 10))
    w = w + (skin ^ Manifold.batch_boolean(slabs, OpType.Add))
    return w.translate((x0, 0, z0))


def aileron_region(x0, z0, y0, y1, gap=0.0):
    return box(x0 + CHORD - AIL[0] - gap, x0 + CHORD + 1, y0 - gap, y1 + gap, z0 + SHELF, z0 + 10)


AIL_Y_U = (43.0, 65.0)     # Querruder Oberflügel (|y|)
AIL_Y_L = (40.0, 62.0)     # Unterflügel


def lw_top(x):
    return LW_Z + float(thick((x - LW_X) / CHORD))


# Strebenpunkte
CAB = [(18.0, 20.0), (30.0, 32.0)]          # Baldachin: (x unten am Rumpf, x oben am Flügel)
NST = [(29.0, 20.0), (41.0, 32.0)]          # Flügelstrebe: (x Unterflügel, x Oberflügel)
NST_Y = 52.0
GEAR_X = [27.0, 41.0]                        # Fahrwerk: Zapfen durch den Unterflügel
STAND_X = 36.0


def sock(x, y, z0, z1, s=SOCK):
    return box(x - s / 2, x + s / 2, y - s / 2, y + s / 2, z0, z1)


def upper_wing_full():
    w = wing_raw(UW_X, UW_Z, UW_S)
    cuts = []
    for sg in (-1, 1):
        for _, xu in CAB:
            cuts.append(sock(xu, sg * GEAR_Y, UW_Z - 1, UW_Z + 1.4))
        for _, xu in NST:
            cuts.append(sock(xu, sg * NST_Y, UW_Z - 1, UW_Z + 1.4))
    return w - Manifold.batch_boolean(cuts, OpType.Add)


def lower_wing_full():
    w = wing_raw(LW_X, LW_Z, LW_S, ribs_skip=14)
    cuts = []
    for sg in (-1, 1):
        for xl, _ in NST:
            cuts.append(sock(xl, sg * NST_Y, lw_top(xl) - 1.4, LW_Z + 6))
        for xg in GEAR_X:
            cuts.append(sock(xg, sg * GEAR_Y, LW_Z - 1, LW_Z + 6, GEAR_T + 0.3))
    cuts.append(sock(STAND_X, 0, LW_Z - 1, LW_Z + 6, 4.3))
    return w - Manifold.batch_boolean(cuts, OpType.Add)


def split_ailerons(w, x0, z0, yr):
    regs = [aileron_region(x0, z0, sg * yr[1] if sg < 0 else yr[0], -yr[0] if sg < 0 else yr[1]) for sg in (-1, 1)]
    gaps = [aileron_region(x0, z0, sg * yr[1] if sg < 0 else yr[0], -yr[0] if sg < 0 else yr[1], 0.15) for sg in (-1, 1)]
    ails = [w ^ r for r in regs]
    return w - (gaps[0] + gaps[1]), ails


def upper_wing():
    return split_ailerons(upper_wing_full(), UW_X, UW_Z, AIL_Y_U)


def lower_wing():
    return split_ailerons(lower_wing_full(), LW_X, LW_Z, AIL_Y_L)


# ---------------------------------------------------------------- Rumpf
NOSE_BORE = (10.0, 26.0)
COLLAR = (21.0, 23.5, 3.8)      # x0, x1, Außenradius Stellring
SHAFT = (-3.3, 25.0)
DOWELS = [(14, 40), (14, 24), (42, 28.5), (66, 32), (84, 34), (98, 35.5)]
EXH = [(13.0, 26.0)]
SKID_X = (106.0, 112.0)
LAND = (61.0, 79.0, 3.8, 42.2)  # Kopfstützen-Auflage x0, x1, halbe Breite, z


def fuselage_full():
    b = fuselage_body()
    cuts = []
    # Unterflügel-Schlitz (Profil + 0.15 Spiel) quer durch den Rumpf, nach unten offen
    sec = Manifold.extrude(profile(0.15), 40).rotate((90, 0, 0)).translate((LW_X, 20, LW_Z))
    cuts += [sec, box(LW_X - 0.15, LW_X + CHORD + 0.15, -20, 20, LW_Z - 5, LW_Z + 0.5)]
    # Fahrwerkszapfen + Ständer (durch den Flügel weiter in den Rumpf)
    for sg in (-1, 1):
        for xg in GEAR_X:
            cuts.append(sock(xg, sg * GEAR_Y, LW_Z, lw_top(xg) + 3.0, GEAR_T + 0.3))
    cuts.append(sock(STAND_X, 0, LW_Z, 28.0, 4.3))
    # Baldachin-Zapfen (oben, 3 mm tief)
    for sg in (-1, 1):
        for xb, _ in CAB:
            zt = z_top(xb, GEAR_Y)
            cuts.append(sock(xb, sg * GEAR_Y, zt - 3.0, zt + 6))
    # Propellerwelle + Stellring-Tasche
    cuts.append(Manifold.cylinder(NOSE_BORE[1] - NOSE_BORE[0] + 1, BORE, BORE, 48).rotate((0, 90, 0)).translate((NOSE_BORE[0] - 1, 0, ZC)))
    cuts.append(Manifold.cylinder(COLLAR[1] - COLLAR[0] + 1.0, COLLAR[2] + 0.5, COLLAR[2] + 0.5, 48).rotate((0, 90, 0))
                .translate((COLLAR[0] - 0.5, 0, ZC)))
    # Cockpit (vorne gerade Wand fürs Instrumentenbrett)
    x0, x1, ch, zf = COCK
    ck = CrossSection.square((x1 - x0 + 6, 2 * ch)).translate((x0 - 6, -ch)).offset(-4, JoinType.Round).offset(4, JoinType.Round)
    ck = ck ^ CrossSection.square((x1 - x0, 2 * ch + 2)).translate((x0, -ch - 1))
    cuts.append(Manifold.extrude(ck, 30).translate((0, 0, zf)))
    # Kopfstützen-Auflage (eben)
    a0, a1, ah, az = LAND
    cuts.append(box(a0, a1, -ah, ah, az, 60))
    # Höhenleitwerk-Schlitz quer, Seitenflossen-Schlitz oben, Sporn unten
    cuts.append(box(101.8, 125, -20, 20, STAB_Z - 0.15, STAB_Z + STAB_T + 0.15))
    cuts.append(box(103.3, 125, -FIN_T / 2 - SLOT_G, FIN_T / 2 + SLOT_G, STAB_Z + STAB_T - 0.1, 60))
    cuts.append(box(SKID_X[0] - 0.1, SKID_X[1] + 0.1, -0.8 - SLOT_G, 0.8 + SLOT_G, 20, interp(2, SKID_X[1]) + 1.7))
    # Auspuff-Löcher
    for x, z in EXH:
        for sg in (-1, 1):
            ys = abs(interp(1, x)) * 0.94
            cuts.append(cyl_y(1.35, 6, x, z, y0=ys - 2.6 if sg > 0 else -ys - 3.4))
    # Passstift-Löcher auf der Teilungsebene
    for x, z in DOWELS:
        cuts.append(cyl_y(K.DOWEL_HOLE, 6.2, x, z))
    return b - Manifold.batch_boolean(cuts, OpType.Add)


def fuselage_halves():
    b = fuselage_full()
    return b ^ box(0, 130, -40, 0, -10, 70), b ^ box(0, 130, 0, 40, -10, 70)


def headrest():
    a0, a1, ah, az = LAND
    st = []
    for x in np.linspace(a0, a1, 16):
        k = (x - a0) / (a1 - a0)
        hw = ah - 0.15 - 2.4 * k
        h = 5.0 * (1 - k) ** 0.8 + 0.6
        st.append((x, 0.0, hw, az - h, az + h))
    return K.loft(st, n=40, expo=2.4) ^ box(a0 - 1, a1 + 1, -10, 10, az, az + 10)


def cowl():
    """Motorhaube (Ring), steht im Druck auf der Rückseite."""
    prof = [(11.0, 0), (13.6, 0), (13.6, 6.5), (13.0, 8.4), (12.0, 9.0), (9.8, 9.0), (9.8, 7.8), (11.0, 7.4)]
    return Manifold.revolve(poly(prof), 96)          # z = 0 hinten … 9 vorne


def stabilizer():
    pl = poly([(102, -2.0), (102, 2.0), (108, 28), (126, 28), (126, -28), (108, -28)])
    pl = pl.offset(-4, JoinType.Round).offset(4, JoinType.Round)
    s = Manifold.extrude(pl, STAB_T).translate((0, 0, STAB_Z))
    zs = STAB_Z + SHELF
    rec = box(118.0, 130, 1.4, 25.5, zs, zs + 5) + box(118.0, 130, -25.5, -1.4, zs, zs + 5)
    elev = [s ^ box(118.15, 130, 1.55, 25.35, zs, zs + 5), s ^ box(118.15, 130, -25.35, -1.55, zs, zs + 5)]
    return s - rec, elev


FIN_PTS = [(103.5, STAB_Z + STAB_T + 0.05), (126.0, STAB_Z + STAB_T + 0.05), (127.5, 39.0), (128.0, 50.0),
           (125.5, 55.5), (119.5, 57.0), (113.5, 55.5), (104.0, 41.0)]
RUD = (117.0, 39.4)


def fin():
    f = plate_xz(FIN_PTS, -FIN_T / 2, FIN_T)
    rec = box(RUD[0], 140, -FIN_T / 2 + 0.6, 5, RUD[1], 70)
    rudder = f ^ box(RUD[0] + 0.15, 140, -FIN_T / 2 + 0.6, 5, RUD[1] + 0.15, 70)
    return f - rec, rudder


# ---------------------------------------------------------------- Streben, Fahrwerk
def strut(p_bot, p_top, y0, w=2.6, diag=None, pin_bot=1.2, pin_top=1.2):
    """N-/V-Strebe in der x-z-Ebene. p_bot/p_top: Listen von Punkten (x, z) der Bein-Enden."""
    parts = []
    for (xb, zb), (xt, zt) in zip(p_bot, p_top):
        parts.append(poly([(xb - w / 2, zb), (xb + w / 2, zb), (xt + w / 2, zt), (xt - w / 2, zt)]))
        parts.append(CrossSection.square((PIN, pin_top)).translate((xt - PIN / 2, zt - 0.05)))
        parts.append(CrossSection.square((PIN, pin_bot)).translate((xb - PIN / 2, zb - pin_bot + 0.05)))
    if diag:
        (xa, za), (xc, zc) = diag
        v = np.array([xc - xa, zc - za]); n = np.array([-v[1], v[0]]) / np.linalg.norm(v) * (w * 0.4)
        parts.append(poly([(xa + n[0], za + n[1]), (xa - n[0], za - n[1]), (xc - n[0], zc - n[1]), (xc + n[0], zc + n[1])]))
    cs = parts[0]
    for p in parts[1:]:
        cs = cs + p
    return Manifold.extrude(cs, ST).rotate((90, 0, 0)).translate((0, y0 + ST, 0))


def cabane(sg):
    bots = [(xb, z_top(xb, GEAR_Y) - 0.3) for xb, _ in CAB]
    tops = [(xt, UW_Z) for _, xt in CAB]
    s = strut(bots, tops, sg * GEAR_Y - ST / 2, diag=(bots[1], tops[0]), pin_bot=2.6)
    pins = Manifold.batch_boolean([box(xb - PIN / 2, xb + PIN / 2, sg * GEAR_Y - ST / 2, sg * GEAR_Y + ST / 2, zb - 2.55, zb + 1.0)
                                   for xb, zb in bots], OpType.Add)
    return (s - fuselage_body()) + (pins ^ s)


_BODY = []


def fuselage_body():
    if not _BODY:
        st = [(x, 0.0, interp(1, x), interp(2, x), interp(3, x)) for x in np.linspace(10, 121, 60)]
        _BODY.append(K.loft(st, n=56, expo=EXPO))
    return _BODY[0]


def nstrut(sg):
    bots = [(xl, lw_top(xl)) for xl, _ in NST]
    tops = [(xu, UW_Z) for _, xu in NST]
    return strut(bots, tops, sg * NST_Y - ST / 2, diag=(bots[0], tops[1]))


def gear_leg(sg):
    cs = CrossSection.circle(3.6, 48).translate((X_W, Z_W))
    for xg in GEAR_X:
        cs = cs + poly([(X_W - 1.3, Z_W), (X_W + 1.3, Z_W), (xg + 1.3, LW_Z), (xg - 1.3, LW_Z)])
        cs = cs + CrossSection.square((GEAR_T, lw_top(xg) + 2.8 - LW_Z)).translate((xg - GEAR_T / 2, LW_Z - 0.05))
    cs = cs + poly([(X_W + 2, 14.5), (37.0, LW_Z - 0.01), (31.0, LW_Z - 0.01)])   # Versteifung
    cs = cs - CrossSection.circle(BORE, 48).translate((X_W, Z_W))
    return Manifold.extrude(cs, GEAR_T).rotate((90, 0, 0)).translate((0, sg * GEAR_Y - GEAR_T / 2 + GEAR_T, 0))


def skid():
    zb0, zb1 = interp(2, SKID_X[0]), interp(2, SKID_X[1])
    pts = [(SKID_X[0], zb0 + 1.6), (SKID_X[1], zb1 + 1.6), (SKID_X[1], zb1 - 0.3), (117.5, 24.2), (116.8, 22.9),
           (115.0, 23.2), (SKID_X[0] + 1.5, zb0 - 1.2), (SKID_X[0], zb0 - 0.3)]
    return plate_xz(pts, -0.8, 1.6)


def windscreen():
    x = COCK[0] - 1.6
    ys = np.linspace(-5.0, 5.0, 21)
    bot = [(y, z_top(x, y) - 0.25) for y in ys]
    ztop = z_top(x, 0) + 5.0
    pts = bot + [(4.0, ztop), (-4.0, ztop)]
    w = Manifold.extrude(poly(pts), 1.0)                 # y-z-Profil, Stärke in "x"
    w = w.rotate((90, 0, 0)).rotate((0, 0, 90))          # Profil -> y-z-Ebene, Stärke entlang x
    bb = w.bounding_box()
    w = w.translate((x - bb[0] - 1.0, 0, 0))
    zc = z_top(x, 0)
    return w.translate((-x, 0, -zc)).rotate((0, 18, 0)).translate((x, 0, zc))


def panel():
    cs = CrossSection.square((9.2, 4.2)).translate((-4.6, 0)) + CrossSection.circle(4.6, 48).translate((0, 4.2)) \
        ^ CrossSection.square((9.2, 6.4)).translate((-4.6, 0))
    p = Manifold.extrude(cs.offset(-0.6, JoinType.Round).offset(0.6, JoinType.Round), 1.0)
    for x, y, r in ((-2.6, 3.2, 1.1), (0, 4.0, 1.2), (2.6, 3.2, 1.1), (0, 1.3, 0.7)):
        p = p - Manifold.cylinder(1, r, r, 32).translate((x, y, 0.55))
    return p   # flach: Vorderseite (Anzeigen) oben


def panel_placed():
    # flach (x', y', z') -> Wand: y' -> z, x' -> y, z' -> -x (Anzeigen zum Piloten = +x)
    p = panel().rotate((90, 0, 0)).rotate((0, 0, 90))     # z'->y? siehe Prüfung unten
    bb = p.bounding_box()
    return p.translate((COCK[0] + 0.02 - bb[0], -(bb[1] + bb[4]) / 2, COCK[3] + 2.4 - bb[2]))


# ---------------------------------------------------------------- Antrieb
def prop():
    hub = Manifold.cylinder(4.0, 3.2, 3.2, 48)
    blades = []
    for sg in (1, -1):
        pts = [(-2.3, 2.5), (2.3, 2.5), (2.0, 16.0), (1.0, 17.8), (-1.0, 17.8), (-2.0, 16.0)]
        b = Manifold.extrude(poly(pts), 1.5)
        # Keil (Steigung): Hinterkante oben dünner
        b = b - box(-0.4, 3, 0, 20, 1.5, 3).rotate((0, -14, 0)).translate((0.4, 0, -0.1))
        blades.append(b if sg > 0 else b.rotate((0, 0, 180)))
    p = hub + blades[0] + blades[1]
    hole = Manifold.extrude(d_profile(K.WHEEL_PRESS), 6).translate((0, 0, -1))
    return p - hole          # flach: Vorderseite (Spinner) unten


def spinner():
    s = Manifold.revolve(poly([(0, 0), (3.4, 0), (3.2, 1.6), (2.5, 3.6), (1.4, 5.2), (0, 5.8)]), 64)
    return s


def collar():
    c = Manifold.cylinder(COLLAR[1] - COLLAR[0], COLLAR[2], COLLAR[2], 48)
    return c - Manifold.extrude(d_profile(K.WHEEL_PRESS), 5).translate((0, 0, -1))


def crankcase():
    """Motorgehäuse: Siebeneck, 7 Löcher für die Zylinder, Nabe vorne, Lagerbohrung."""
    hept = CrossSection.circle(5.0 / np.cos(np.pi / 7), 7)
    c = Manifold.extrude(hept, 4.0)
    c = c + Manifold.cylinder(6.0, 2.7, 2.7, 48).translate((0, 0, -2.0))       # Nabe vorne (z<0) + Montagering hinten
    c = c + Manifold.cylinder(1.0, 3.4, 3.4, 48).translate((0, 0, 3.99))
    c = c - Manifold.cylinder(12, BORE, BORE, 48).translate((0, 0, -3))
    for k in range(7):
        a = 360 / 7 * k + 360 / 14
        h = Manifold.cylinder(2.2, 0.95, 0.95, 24).rotate((0, 90, 0)).translate((5.0 - 1.6, 0, 2.0)).rotate((0, 0, a))
        c = c - h
    return c      # z = Flugrichtung rückwärts (z=-2 vorne … 5 hinten)


def cylinder():
    prof = [(0, 0), (0.75, 0), (0.75, 1.45), (1.9, 1.45), (1.9, 5.4), (1.5, 6.2), (0, 6.2)]
    c = Manifold.revolve(poly(prof), 40)
    for k in range(4):
        z = 2.2 + k * 0.85
        c = c - Manifold.revolve(poly([(1.55, z), (3, z), (3, z + 0.4), (1.55, z + 0.4)]), 40)
    return c


def shaft():
    return K.axle(SHAFT[1] - SHAFT[0])


def exhaust():
    e = Manifold.extrude(CrossSection.circle(1.2, 32) ^ CrossSection.square((3, 2.2)).translate((-1.5, -1.0)), 6.0)
    return e - Manifold.cylinder(3, 0.6, 0.6, 24).translate((0, 0.1, 4.0))


def hubcap():
    return Manifold.revolve(poly([(0, 0), (5.0, 0), (4.6, 0.6), (3.0, 1.0), (0, 1.1)]), 64)


def pilot():
    """Pilot mit Lederkappe, Brille und Schal; flacher Boden, Blick nach -x."""
    s = 1.25
    torso = K.loft([(x, 0.0, 4.0 - 0.22 * x, 0.0, 4.5 - 0.1 * x) for x in np.linspace(0, 6, 6)], n=32, expo=2.6)
    neck = Manifold.cylinder(3.0, 1.6, 1.6, 32).translate((3.2, 0, 3.5))
    head = Manifold.sphere(3.0, 48).translate((3.2, 0, 6.8))
    cap = (Manifold.sphere(3.3, 48).translate((3.2, 0, 6.9)) ^ box(-5, 12, -5, 5, 6.6, 12))
    flaps = box(1.6, 4.4, -3.4, 3.4, 4.8, 7.2) ^ Manifold.sphere(3.45, 48).translate((3.2, 0, 6.8))
    goggles = Manifold.cylinder(1.2, 1.0, 1.0, 24).rotate((0, 90, 0)).translate((5.9, 1.25, 7.5)) \
        + Manifold.cylinder(1.2, 1.0, 1.0, 24).rotate((0, 90, 0)).translate((5.9, -1.25, 7.5))
    scarf = Manifold.cylinder(1.2, 2.4, 2.4, 32).translate((3.2, 0, 4.4)) + box(0.0, 1.5, 1.2, 2.8, 1.5, 5.0)
    d = torso + neck + head + cap + flaps + goggles + scarf
    d = d ^ box(-10, 20, -10, 10, 0, 20)
    return d.scale((s, s, s))


def stand_base():
    base = Manifold.extrude(CrossSection.square((104, 58)).translate((-52, -29)).offset(-12, JoinType.Round).offset(12, JoinType.Round), 4.0)
    base = base - Manifold.extrude(CrossSection.square((96, 50)).translate((-48, -25)).offset(-9, JoinType.Round).offset(9, JoinType.Round), 2).translate((0, 0, 3.4))
    base = base + Manifold.cylinder(7.4, 7.0, 5.0, 64).translate((0, 0, 0.6))
    base = base - box(-2.15, 2.15, -2.15, 2.15, 1.0, 20)
    base = base + K.text_relief("PRINTER BROTHERS", 5.0, 0, -18.5, 3.39) + K.text_relief("PB DOPPELDECKER", 4.2, 0, 18.0, 3.39)
    return base           # Oberseite Sockel bei z = 8


STAND_LEN = 8.0 + 28.0 + 30.0 - 1.0 - 0.3


def stand_pole():
    return Manifold.batch_hull([box(-1.6, 1.6, -1.6, 1.6, 0, 0.4), box(-2, 2, -2, 2, 0.4, STAND_LEN - 0.4),
                                box(-1.6, 1.6, -1.6, 1.6, STAND_LEN - 0.4, STAND_LEN)])


# ---------------------------------------------------------------- Zusammenbau
def assembled():
    P = {}
    L, R = fuselage_halves()
    P["A1 Rumpf links"], P["A2 Rumpf rechts"] = L, R
    P["A3 Motorhaube"] = cowl().rotate((0, -90, 0)).translate((10.0 - 0.02, 0, ZC))
    f, rud = fin()
    P["A4 Seitenflosse"], P["A5 Seitenruder"] = f, rud
    s, el = stabilizer()
    P["A6 Höhenleitwerk"] = s
    P["A7 Höhenruder rechts"], P["A7 Höhenruder links"] = el[0], el[1]
    P["A8 Kopfstütze"] = headrest()
    uw, ua = upper_wing()
    lw, la = lower_wing()
    P["B1 Oberflügel"], P["B2 Unterflügel"] = uw, lw
    P["B3 Querruder oben links"], P["B3 Querruder oben rechts"] = ua
    P["B3 Querruder unten links"], P["B3 Querruder unten rechts"] = la
    for sg, nm in ((-1, "links"), (1, "rechts")):
        P[f"B4 Flügelstrebe {nm}"] = nstrut(sg)
        P[f"B5 Baldachinstrebe {nm}"] = cabane(sg)
        P[f"B6 Fahrwerksbein {nm}"] = gear_leg(sg)
    P["B7 Windschutz"] = windscreen()
    # Antrieb (dreht): Propeller vorne flach (Spinner-Seite bei x = -3.5)
    P["C1 Propeller"] = prop().rotate((0, 90, 0)).translate((-3.5, 0, ZC))
    P["C2 Spinner"] = spinner().rotate((0, -90, 0)).translate((-3.5 + 0.01, 0, ZC))
    P["C3 Propellerwelle"] = shaft().rotate((0, 90, 0)).translate((SHAFT[0], 0, ZC))
    P["C4 Stellring"] = collar().rotate((0, 90, 0)).translate((COLLAR[0], 0, ZC))
    cc = crankcase()
    P["C5 Motorgehäuse"] = cc.rotate((0, 90, 0)).translate((10.0 - 5.0 - 0.01, 0, ZC))
    for k in range(7):
        a = 360 / 7 * k + 360 / 14
        cy = cylinder().rotate((0, 90, 0)).translate((5.0 - 1.4, 0, 2.0)).rotate((0, 0, a))   # radial in der Gehäuse-Ebene
        P[f"C6 Zylinder {k + 1}"] = cy.rotate((0, 90, 0)).translate((10.0 - 5.0 - 0.01, 0, ZC))
    # Räder (drehen) + Achse
    y_in = GEAR_Y + GEAR_T / 2 + 0.6
    La = 2 * (y_in + W_W) - 0.6
    P["C9 Radachse"] = K.axle(La).translate((0, 0, -La / 2)).rotate((90, 0, 0)).translate((X_W, 0, Z_W))
    wh = K.wheel(R_W, W_W)
    P["C7 Rad rechts"] = wh.rotate((-90, 0, 0)).translate((X_W, y_in, Z_W))
    P["C7 Rad links"] = wh.rotate((-90, 0, 0)).rotate((0, 0, 180)).translate((X_W, -y_in, Z_W))
    hc = hubcap()
    P["C8 Radkappe rechts"] = hc.rotate((-90, 0, 0)).translate((X_W, y_in + W_W - 0.4, Z_W))
    P["C8 Radkappe links"] = hc.rotate((-90, 0, 0)).rotate((0, 0, 180)).translate((X_W, -y_in - W_W + 0.4, Z_W))
    P["C10 Sporn"] = skid()
    P["C11 Pilot"] = pilot().mirror((1, 0, 0)).translate((COCK[1] - 3.0, 0, COCK[3]))
    P["C12 Instrumentenbrett"] = panel_placed()
    for sg, nm in ((1, "rechts"), (-1, "links")):
        x, z = EXH[0]
        ys = abs(interp(1, x)) * 0.94
        e = exhaust().rotate((90, 0, 0)) if sg < 0 else exhaust().rotate((-90, 0, 0))
        P[f"C13 Auspuff {nm}"] = e.translate((x, sg * (ys - 2.3), z))
    return P


def on_stand(P):
    base = stand_base().translate((STAND_X, 0, -30.0 - 8.0))
    pole = stand_pole().translate((STAND_X, 0, -30.0 - 8.0 + 1.0))
    return base, pole


# ---------------------------------------------------------------- Spritzlinge (Druckausrichtung)
T_LEFT, T_RIGHT = K.T_LEFT, K.T_RIGHT
FLAT_XZ = (-90, 0, 0)            # Platte x-z -> flach


def kit(kind):
    P = assembled()
    if kind == "A":
        f, rud = fin()
        s, el = stabilizer()
        parts = [("A1", P["A1 Rumpf links"].transform(T_LEFT)), ("A2", P["A2 Rumpf rechts"].transform(T_RIGHT)),
                 ("A3", cowl()), ("A4", f.rotate((90, 0, 0))), ("A5", rud.rotate((90, 0, 0))),
                 ("A6", s), ("A7", el[0]), ("A7", el[1]), ("A8", headrest())]
        parts += [("A9", K.dowel(6.0).rotate((90, 0, 0))) for _ in DOWELS]
    elif kind == "B":
        uw, ua = upper_wing()
        lw, la = lower_wing()
        parts = [("B1", uw), ("B2", lw)] + [("B3", a) for a in ua + la]
        for sg in (-1, 1):
            parts += [("B4", nstrut(sg).rotate(FLAT_XZ)), ("B5", cabane(sg).rotate(FLAT_XZ)), ("B6", gear_leg(sg).rotate(FLAT_XZ))]
        ws = windscreen().rotate((0, -18, 0))
        parts.append(("B7", ws.rotate((0, 90, 0))))
    else:
        y_in = GEAR_Y + GEAR_T / 2 + 0.6
        La = 2 * (y_in + W_W) - 0.6
        parts = [("C1", prop()), ("C2", spinner()), ("C3", shaft().rotate((0, 90, 0)).rotate((90, 0, 0))),
                 ("C4", collar()), ("C5", crankcase().rotate((180, 0, 0)))]
        parts += [("C6", cylinder()) for _ in range(7)]
        parts += [("C7", K.wheel(R_W, W_W)), ("C7", K.wheel(R_W, W_W)), ("C8", hubcap()), ("C8", hubcap()),
                  ("C9", K.axle(La).rotate((0, 90, 0)).rotate((90, 0, 0))), ("C10", skid().rotate(FLAT_XZ)),
                  ("C11", pilot()), ("C12", panel()), ("C13", exhaust()), ("C13", exhaust()),
                  ("C14", stand_base()), ("C15", stand_pole().rotate((0, 90, 0)))]
    return [(nr, m) for nr, m in parts]


LABELS = {"A": "A  RUMPF", "B": "B  TRAGFLÄCHEN", "C": "C  DETAILS"}
SPRUE_TAGS = {}


def extra_tags(placed, W, H, runners, tags):
    """Nummernschilder, für die K.sprue keinen Platz fand: freie Stelle auf Rahmen/Läufer nahe am Teil suchen."""
    from shapely.geometry import LineString, Point
    from shapely.ops import unary_union
    b = 1.5
    lines = [LineString([(b, b), (W - b, b), (W - b, H - b), (b, H - b), (b, b)])] + [LineString(r) for r in runners]
    allfp = unary_union([K.footprint(m) for m, _ in placed])
    have = {nr for nr, _, _ in tags}
    add = []
    for m, nr in placed:
        if nr in have:
            continue
        fp = K.footprint(m)
        best = None
        for ln in lines:
            for d in np.arange(2, ln.length - 2, 0.5):
                q = ln.interpolate(d)
                if q.y > H - 12 and q.x < 56:                      # Rahmenschild
                    continue
                if allfp.distance(q) <= K.TAG_R + 0.9 or any(np.hypot(q.x - tx, q.y - ty) <= 2 * K.TAG_R + 1.5 for _, tx, ty in tags):
                    continue
                dist = fp.distance(q)
                if best is None or dist < best[0]:
                    best = (dist, q)
        if best is None or best[0] > 30:
            print(f"  !! {nr}: kein Platz für Nummernschild"); continue
        q = best[1]
        tags.append((nr, q.x, q.y)); have.add(nr)
        add.append(Manifold.cylinder(2.2, K.TAG_R, K.TAG_R, 48).translate((q.x, q.y, 0))
                   + K.text_relief(nr, 5.0 if len(nr) < 3 else 4.3, q.x, q.y, 2.2 - 0.01, 0.8, bold=True))
    return Manifold.batch_boolean(add, OpType.Add) if add else Manifold()


def build_sprue(kind):
    W = 170.0 if kind == "B" else 166.0
    placed, runners, used_h = K.pack(kit(kind), W, 176.0, gap=4.6)
    H = used_h + 3.0 + 12.0
    if kind == "C":       # Räder neben dem Ständer: senkrechte Läufer zwischen Ständer und Rädern
        y_r = runners[0][0][1]
        xs = sorted(m.bounding_box()[0] for m, nr in placed if nr == "C7")
        x_base = max(m.bounding_box()[3] for m, nr in placed if nr == "C14")
        for x in ((x_base + xs[0]) / 2, (xs[0] + 18.0 + xs[1]) / 2):
            runners.append(((x, 1.5), (x, y_r)))
    grid, gates, tags = K.sprue(placed, W, H, runners, LABELS[kind])
    grid = grid + extra_tags(placed, W, H, runners, tags)
    SPRUE_TAGS[kind] = tags
    allp = Manifold.batch_boolean([m for m, _ in placed], OpType.Add)
    touch = (allp ^ grid).volume()
    plate = Manifold.batch_boolean([allp, grid, gates], OpType.Add)
    comps = [c for c in plate.decompose() if c.volume() > 0.01]          # Null-Volumen-Splitter weg
    plate = Manifold.batch_boolean(comps, OpType.Add)
    return plate, placed, touch, W, H


def assembly_check(P):
    nr = lambda n: n.split()[0]
    moving = {"prop": [n for n in P if nr(n) in ("C1", "C2", "C3", "C4")],
              "wheels": [n for n in P if nr(n) in ("C7", "C8", "C9")]}
    mv = set(sum(moving.values(), []))
    statics = [n for n in P if n not in mv]
    stat = Manifold.batch_boolean([P[n] for n in statics], OpType.Add)
    ok = True
    for grp, names in moving.items():
        g = Manifold.batch_boolean([P[n] for n in names], OpType.Add)
        v = (g ^ stat).volume(); gap = g.min_gap(stat, 3.0)
        good = v < 1e-3 and gap >= 0.25; ok &= good
        print(f"  dreht {grp:7s}: Überschneidung {v:7.3f} mm³, min. Spalt {gap:.2f} mm  {'OK' if good else '!!'}")
    worst = []
    for i, a in enumerate(statics):
        for b in statics[i + 1:]:
            v = (P[a] ^ P[b]).volume()
            if v > 0.5:
                worst.append((v, a, b))
    for v, a, b in sorted(worst, reverse=True)[:12]:
        print(f"  !! {a} ∩ {b}: {v:.1f} mm³"); ok = False
    if not worst:
        print("  statische Teile: keine Überschneidungen (> 0.5 mm³)")
    # alles hängt zusammen? (Teile berühren sich bzw. stecken ineinander)
    return ok


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("== Zusammenbau ==")
    P = assembled()
    assembly_check(P)
    bb = Manifold.batch_boolean(list(P.values()), OpType.Add).bounding_box()
    print(f"  Maße: Länge {bb[3] - bb[0]:.1f}, Spannweite {bb[4] - bb[1]:.1f}, Höhe {bb[5] - bb[2]:.1f} mm")
    total = 0
    for kind, nm in (("A", "rumpf"), ("B", "tragflaechen"), ("C", "details")):
        plate, placed, touch, W, H = build_sprue(kind)
        total += len(placed)
        tm = to_tm(plate)
        name = f"{NAME}_spritzling-{kind}_{nm}"
        print(f"== Spritzling {kind}: {len(placed)} Teile, Rahmen {W:.0f} x {H:.0f} mm ==")
        print(f"  Teile berühren Rahmen/Schilder: {touch:.3f} mm³ | ein zusammenhängender Druck: {len(plate.decompose()) == 1}")
        check(tm, name, (180, 180, 180))
        tm.export(OUT / f"{name}.stl")
    print("Teile gesamt:", total)
    return P


if __name__ == "__main__":
    main()
