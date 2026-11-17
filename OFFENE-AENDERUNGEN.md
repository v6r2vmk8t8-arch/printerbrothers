# Offene Website-Änderungen (warten auf Netlify-Credits)

**Stand: 17.11.2026** – Netlify-Deploy-Credits sind aufgebraucht, Produktions-Deploys pausiert.
Neue Credits ab **23.11.2026** → dann alles mit **einem einzigen** Deploy veröffentlichen.

Letzter erfolgreich veröffentlichter Stand: Commit `dd6dc8a` (Admin-Reiter „3D-Dateien“).

## Was live gehen muss
| Änderung | Commit | Wo prüfen |
|---|---|---|
| Admin 3D-Dateien: „+ Dateien hochladen“ fest oben neben „Eigene Dateien“, schwebender Knopf im Reiter ausgeblendet | `344062c` | `/admin` → 3D-Dateien |
| Admin 3D-Dateien: Suchfeld im Admin-Stil (dunkel) | `344062c` | `/admin` → 3D-Dateien |
| Admin 3D-Dateien: „Eigene Dateien“ als zuklappbare Gruppe, bei Suche automatisch offen | `4d782f8` | `/admin` → 3D-Dateien |
| Shopbilder Noppen-Ringe mit höheren/breiteren Noppen (1,95 mm / Ø 4,95) | `afcf6e4` | `/images/noppen-ring-*.jpg` |
| Shopbilder Renn-Flitzer (4 Bilder) | `0f7abb6` (nur auf Branch) | `/images/renn-flitzer-1..4.jpg` |
| Netlify-Regel: nur deployen, wenn sich die Website ändert | `3bc30ba` | `netlify.toml` |

Alles liegt auf `main`, außer den Renn-Flitzer-Bildern (Branch `claude/gifted-ritchie-pe23g2`).

## Ablauf am 23.11.
1. In Netlify prüfen bzw. den Nutzer fragen, ob Credits wieder da sind (Banner „operational credits“ weg).
2. Branch nach `main` bringen (Fast-Forward) – **ein** Push = **ein** Deploy.
3. Warten, bis live; prüfen: `/admin/index.html` enthält `uploadBtn` und `ownGroup`,
   `/images/renn-flitzer-1.jpg` liefert 200, Ringbilder haben die neuen MD5-Summen.
4. Fragen, ob die Renn-Flitzer-Bilder ins Produkt sollen (Produkt im Admin: 5 €, Text vom Nutzer
   eingetragen; Farben „Karosserie“ / „Räder“). Bilder können auch ohne Deploy über die Admin-API
   hochgeladen werden.
5. Diese Datei danach löschen.

## Ab jetzt sparsam deployen
- Website-Änderungen auf dem Branch sammeln und gebündelt nach `main` pushen.
- Reine STL-/Skript-Änderungen lösen dank `ignore`-Regel in `netlify.toml` keinen Deploy mehr aus.
- Produkte/Bilder/Dateien im Admin brauchen keinen Deploy (Netlify Blobs über die Admin-API).
- 3D-Dateien in den Admin bringen: `python3 3d-druck/src/dateien_abgleich.py` (kein Deploy nötig).
