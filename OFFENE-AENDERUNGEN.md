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
| Netlify-Regel: nur deployen, wenn sich die Website ändert | `3bc30ba` | `netlify.toml` |

Alles liegt auf `main`. Renn-Flitzer-Bilder hat der Nutzer bereits selbst im Admin eingetragen – nichts mehr zu tun
(die Dateien `public/images/renn-flitzer-*.jpg` auf dem Branch gehen beim Merge einfach mit, schaden nicht).

## Ablauf am 23.11.
1. In Netlify prüfen bzw. den Nutzer fragen, ob Credits wieder da sind (Banner „operational credits“ weg).
2. Branch nach `main` bringen (Fast-Forward) – **ein** Push = **ein** Deploy.
3. Warten, bis live; prüfen: `/admin/index.html` enthält `uploadBtn` und `ownGroup`,
   Ringbilder haben die neuen MD5-Summen.
4. Diese Datei danach löschen.

## Ab jetzt sparsam deployen
- Website-Änderungen auf dem Branch sammeln und gebündelt nach `main` pushen.
- Reine STL-/Skript-Änderungen lösen dank `ignore`-Regel in `netlify.toml` keinen Deploy mehr aus.
- Produkte/Bilder/Dateien im Admin brauchen keinen Deploy (Netlify Blobs über die Admin-API).
- 3D-Dateien in den Admin bringen: `python3 3d-druck/src/dateien_abgleich.py` (kein Deploy nötig).
