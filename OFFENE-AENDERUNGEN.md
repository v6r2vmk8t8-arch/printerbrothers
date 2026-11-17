# Offene Website-Änderungen (warten auf Netlify-Credits)

**Stand: 17.11.2026 (aktualisiert)** – Netlify-Deploy-Credits sind aufgebraucht, Produktions-Deploys pausiert.
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
| Shopbilder Noppen-Ringe „Muster“ mit 4. Muster Tentakel (`noppen-ring-*-2.jpg`) | `5b350c7` | nur auf Branch `claude/gifted-ritchie-pe23g2` |
| Bilder `formel-bausatz-*.jpg` (einfacher Bausatz, noch kein Produkt) | `b6f98ff` | nur auf Branch |
| Shopbilder Noppen-Ringe liegend/rund | Branch | `/images/noppen-ring-*.jpg` |
| Produkt-Link (z. B. PDF-Anleitung): Feld „Link-Text/Link-Adresse“ im Admin, Link unter der Beschreibung im Shop | Branch | `/admin` → Produkt bearbeiten; Shop-Karte |
| PDF `public/anleitungen/formel-pb-bauanleitung.pdf` | Branch | `/anleitungen/formel-pb-bauanleitung.pdf` |

Die ersten Zeilen liegen schon auf `main` (Deploy pausiert), die letzten zwei nur auf dem Branch
`claude/gifted-ritchie-pe23g2` – dort liegen auch alle aktuellen STLs, Skripte und die Formel-PB-Bauanleitung.
3D-Dateien und Bauanleitung sind bereits im Admin unter „3D-Dateien“ (Blobs, kein Deploy nötig). Renn-Flitzer-Bilder hat der Nutzer bereits selbst im Admin eingetragen – nichts mehr zu tun
(die Dateien `public/images/renn-flitzer-*.jpg` auf dem Branch gehen beim Merge einfach mit, schaden nicht).

## Ablauf am 23.11.
1. In Netlify prüfen bzw. den Nutzer fragen, ob Credits wieder da sind (Banner „operational credits“ weg).
2. Branch nach `main` bringen (Fast-Forward) – **ein** Push = **ein** Deploy.
3. Warten, bis live; prüfen: `/admin/index.html` enthält `uploadBtn` und `ownGroup`,
   Ringbilder haben die neuen MD5-Summen.
4. **Nach dem Deploy:** beim Produkt `formel-modellbausatz` per Admin-API `linkLabel: "Bauanleitung (PDF)"`,
   `linkUrl: "/anleitungen/formel-pb-bauanleitung.pdf"` setzen (vorher speichert der alte Server das Feld nicht).
   Produkt ist sichtbar (24,90 €, vom Nutzer bestätigt).
5. Diese Datei danach löschen.

## Ab jetzt sparsam deployen
- Website-Änderungen auf dem Branch sammeln und gebündelt nach `main` pushen.
- Reine STL-/Skript-Änderungen lösen dank `ignore`-Regel in `netlify.toml` keinen Deploy mehr aus.
- Produkte/Bilder/Dateien im Admin brauchen keinen Deploy (Netlify Blobs über die Admin-API).
- 3D-Dateien in den Admin bringen: `python3 3d-druck/src/dateien_abgleich.py` (kein Deploy nötig).
