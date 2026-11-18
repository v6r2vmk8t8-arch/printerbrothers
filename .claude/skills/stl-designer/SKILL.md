---
name: stl-designer
description: Entwirft und erstellt druckfertige STL-Dateien für Bambu Studio (Bambu Lab 3D-Drucker) per Code-CAD (build123d). Verwenden, wenn der Nutzer ein 3D-Druck-Teil, eine STL, ein Modell, einen Halter, Anhänger, ein Schild, eine Box, einen Ersatzteil o. ä. entworfen, erstellt oder angepasst haben möchte – auch mehrfarbig (AMS).
---

# STL-Designer für Bambu Studio

Erzeuge funktionale, maßgenaue, druckbare Teile mit Python-Code und liefere STL-Dateien,
die direkt in Bambu Studio geladen werden können.

## Werkzeuge

- **build123d** (bevorzugt) für parametrische CAD-Teile: Boxen, Halter, Gewinde-/Schraublöcher, Fasen, Rundungen, Text, SVG-Import.
- **trimesh / manifold3d** für Mesh-Operationen (Boolesche Ops auf bestehenden STLs, Reparatur, Skalieren).
- **Hilfsskript** `.claude/skills/stl-designer/scripts/stl_tools.py`:
  - `export_parts({"farbe": objekt, ...}, "3d-druck/<name>_<größe>")` → STL je Farbe, `_einfarbig.stl`, `_vorschau.png`, Druckbarkeits-Check
  - `python3 .claude/skills/stl-designer/scripts/stl_tools.py datei.stl` → bestehende STL prüfen

Falls die Bibliotheken fehlen: `pip install -q build123d trimesh manifold3d matplotlib shapely networkx`

**Alternative für mechanische Teile: manifold3d direkt** (schnell, robust, siehe `3d-druck/src/pb_kaffeeklipp.py` als Vorlage):
2D-Konturen mit `CrossSection` (offset/rounding), `Manifold.extrude/revolve`, Booleans, Gewinde als
Helix-Mesh, Spielprüfung mit `a.min_gap(b, 2.0)` und Kollision mit `(a ^ b).volume()`.
- Manifold → trimesh immer mit `process=False` (sonst werden Punkte verschmolzen und das Mesh undicht).
- Teile, die sich nur flächig berühren, verschmelzen nicht → immer ≥ 0,05 mm überlappen lassen; mit
  `len(m.decompose()) == 1` prüfen.
- SVG-Logos mit nur M/L/Z-Pfaden direkt per Regex einlesen (y = Höhe − y), in `CrossSection` umwandeln.

## Ablauf

1. **Anforderungen klären** – nur fragen, was wirklich fehlt: Hauptmaße, Zweck/Belastung, Befestigung (Schraubengröße), Farben, Drucker. Bei Fotos/Skizzen Maße daraus ableiten und Annahmen nennen.
2. **Modellskript schreiben** unter `3d-druck/src/<name>.py` – alle Maße als benannte Parameter oben im Skript, damit spätere Änderungen einfach sind.
3. **Ausführen** → `export_parts(...)` mit Basispfad `3d-druck/<name>_<größe>` (z. B. `3d-druck/pb-anhaenger_45mm`).
4. **Vorschau-PNG ansehen** (Read-Tool) und kritisch prüfen: Stimmt die Form? Sind Details sichtbar? Liegt das Teil flach?
5. **Check-Ausgabe beachten**: Jede Warnung (nicht wasserdicht, zu groß …) beheben, bevor geliefert wird.
6. **Im Admin bereitstellen**: `python3 3d-druck/src/dateien_abgleich.py` lädt neue/geänderte Dateien aus
   `3d-druck/` in den Admin-Reiter „3D-Dateien → Von Claude“ (braucht den API-Schlüssel der Umgebung).
   Vorher mit `--trocken` prüfen. **Standardmäßig wird nichts gelöscht**, weil andere Sitzungen auf anderen
   Branches dort Dateien ablegen, die im eigenen Checkout fehlen. Wer Dateien bewusst aus dem Repo entfernt hat
   und sie auch im Admin loswerden will, ruft das Skript mit `--loeschen` auf. Gelöscht wird dann nur, was lokal
   fehlt, laut `git log --diff-filter=D` im aktuellen Branch gelöscht wurde und in keinem bekannten Branch
   (lokal/`origin/*`) mehr existiert. Alles andere wird nur als „behalten“ aufgelistet.
   Ebenso wird eine vorhandene Admin-Datei nur überschrieben, wenn deren Inhalt einer früheren Version aus der
   Git-Historie des eigenen Branches entspricht. Unbekannte Admin-Versionen (vermutlich aus einer anderen Sitzung)
   werden als „nicht überschrieben“ gemeldet; nur nach Rücksprache mit `--ueberschreiben` erzwingen.
7. **Liefern**: Maße, geschätztes Gewicht, empfohlene Druckausrichtung und Slicer-Tipps (Support ja/nein, Wände, Infill) kurz nennen. Committen und pushen, damit der Nutzer die Dateien herunterladen kann.

## Dateikonvention (bestehend im Repo)

- Ordner `3d-druck/`, Namen klein mit Bindestrich: `<name>_<größe>mm_<farbe>.stl`
- Mehrfarbig: ein STL pro Farbe (`_gruen`, `_weiss`, `_schwarz`, …) + `_einfarbig.stl` (alles zusammen)
- In Bambu Studio: alle Farb-STLs gleichzeitig importieren → „Als ein Objekt mit mehreren Teilen laden?“ mit **Ja** bestätigen → jedem Teil ein Filament zuweisen. Die Teile sind deckungsgleich positioniert.
- Quellskript in `3d-druck/src/` mitcommitten.

## Drucker des Nutzers

**Bambu Lab A1 mini** mit **Textured PEI Plate**, 0,4-mm-Düse, AMS lite (max. 4 Farben).

- Bauraum **180 × 180 × 180 mm** (Standard im Hilfsskript). Größere Teile teilen (mit Zapfen/Nut, 0,2 mm Spiel) und das sagen.
- Max. **4 Farben** pro Teil (AMS lite). Mehr Farben → vereinfachen oder Farbwechsel per Pause vorschlagen.
- Textured Plate: Die Unterseite bekommt automatisch eine matte, strukturierte Oberfläche – Sichtseiten
  (z. B. Schilder, Anhänger, Untersetzer) gerne **nach unten** legen. Kein Kleber nötig bei PLA/PETG.
- Feine Details (Schrift < 8 mm, Linien < 1 mm) **nicht** auf die Unterseite – die Struktur schluckt sie;
  solche Details oben als Relief modellieren.
- Bettschlinger (Y-Achse bewegt das Teil): hohe, schmale Teile (Höhe > 3 × Grundfläche) wackeln →
  breitere Basis, Brim-Empfehlung oder liegend drucken.

## Bewegliche Teile (print-in-place)

- Gelenk mit senkrechter Achse: Scheiben mit **45°-Kegeln** statt flacher Flächen stapeln (keine Brücken),
  0,4 mm radiales und 0,6 mm vertikales Spiel; Kollision in mehreren Winkelstellungen prüfen.
- Schnapper: Federfinger ≥ 15 mm frei, Dehnung 1,5·t·δ/L² < 1 % (PLA), Hinterschnitt ≥ 1 mm.
- Gewinde für Schraubdeckel: 2-gängig (Steigung 10 mm → ca. ½ Umdrehung), Flanken ≥ 45°, 0,5 mm Spiel.
- Mehrfarbige Logos auf Deckeln: Logo-Seite nach unten, bündiges Inlay 0,6 mm → Farbwechsel nur in 3 Schichten.

## Druck-Regeln (Bambu Lab, 0,4-mm-Düse, PLA)

| Regel | Wert |
|---|---|
| Druckbett | **A1 mini: 180 × 180 × 180 mm** (zum Vergleich X1C / P1S / A1: 256 mm) |
| Mindestwandstärke | 1,2 mm (3 Linien), tragend ≥ 2 mm |
| Kleinste Details / Schrift | Strichstärke ≥ 0,8 mm, Schrifthöhe ≥ 5 mm, Relief 0,6–1,0 mm |
| Mehrfarb-Schicht oben | ≥ 0,6 mm (3 Lagen à 0,2 mm) |
| Überhänge | ≤ 45° ohne Support; Brücken ≤ 10 mm |
| Spiel Steckverbindung | 0,2 mm pro Seite (lose: 0,3 mm, Presssitz: 0,1 mm) |
| Löcher | +0,2 mm auf Nennmaß (M3 → 3,4 mm, M4 → 4,4 mm, M5 → 5,4 mm) |
| Senkkopf | 90°-Senkung, Kopf-Ø + 0,4 mm |
| Heißeinsatz M3 | Loch 4,0–4,2 mm, Tiefe 5,5 mm |
| Unterkante | Fase 0,4–0,6 mm statt Rundung (gegen Elefantenfuß, kein Support nötig) |
| Ausrichtung | Größte flache Fläche nach unten; Kräfte quer zu den Layern vermeiden |

## build123d-Kurzreferenz

```python
from build123d import *
with BuildPart() as p:
    Box(40, 20, 4, align=(Align.CENTER, Align.CENTER, Align.MIN))
    fillet(p.edges().filter_by(Axis.Z), 3)          # senkrechte Kanten runden
    chamfer(p.edges().group_by(Axis.Z)[0], 0.5)     # Unterkante fasen
    with Locations((-12, 0, 4)):
        CounterSinkHole(radius=2.2, counter_sink_radius=4.2)
    with BuildSketch(p.faces().sort_by(Axis.Z)[-1]):
        Text("PB", 9)
    extrude(amount=0.8)                              # Relief (mode=Mode.SUBTRACT für Gravur)
# SVG-Logo: import_svg("logo.svg") -> Faces, dann extrude(...)
```

Mehrfarbig: Basis und Relief als **getrennte** Parts bauen (Relief nicht mit der Basis vereinigen) und als
`{"gruen": basis, "weiss": relief}` an `export_parts` übergeben. Bei Einlagen bündig zur Oberfläche: die Einlage-Form
von der Basis abziehen (`basis - einlage`), damit sich die Teile nicht überlappen.

## Grenzen

Code-CAD ist ideal für technische, funktionale und geometrische Teile, Schilder, Logos und Gehäuse.
Organische Formen (Figuren, Gesichter) gehen damit nur eingeschränkt – dann ehrlich sagen und Alternativen vorschlagen.
Slicen und Drucken macht der Nutzer selbst in Bambu Studio.
