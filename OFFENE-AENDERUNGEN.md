# Offene Website-Änderungen (warten auf Netlify-Credits)

> 23.11.: Shop startet im **Anfrage-Modus** (Bestellungen aus), Verein in Gründung. Impressum ohne Gewerbe/UID.

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
| Firmenlogo: Schalter im Admin „Firmen können ihr eigenes Logo mitschicken“; im Warenkorb Logo-Feld je Stück; „Logo-Anfrage an uns senden“ übernimmt Produkte + Logo ins Anfrage-Formular (SVG/PDF jetzt erlaubt) | Branch | Shop-Karte „◆ Für Firmen …“, Warenkorb, Formular `#kontakt` |

Die ersten Zeilen liegen schon auf `main` (Deploy pausiert), die letzten zwei nur auf dem Branch
`claude/gifted-ritchie-pe23g2` – dort liegen auch alle aktuellen STLs, Skripte und die Formel-PB-Bauanleitung.
3D-Dateien und Bauanleitung sind bereits im Admin unter „3D-Dateien“ (Blobs, kein Deploy nötig). Renn-Flitzer-Bilder hat der Nutzer bereits selbst im Admin eingetragen – nichts mehr zu tun
(die Dateien `public/images/renn-flitzer-*.jpg` auf dem Branch gehen beim Merge einfach mit, schaden nicht).

## Shop geht live (echte Bestellungen) – kommt mit demselben Deploy
| Änderung | Wo prüfen |
|---|---|
| Helles Design, folgt System (hell/dunkel), Umschalter im Menü | Startseite, Rechtsseiten |
| Kasse: Lieferung AT/DE/Abholung, Zahlung Überweisung/PayPal.me/Bar, Summen inkl. 20 % USt, „Zahlungspflichtig bestellen“ | Warenkorb → Zur Kasse |
| Server: `/api/bestellung` (Preise am Server nachgerechnet, Speicher „orders“), `/api/settings` | Testbestellung |
| Benachrichtigung je Bestellung über Netlify-Formular „bestellung“ (mit Logo-Dateien) | Netlify → Forms |
| Admin: Reiter „Bestellungen“ (Status, Notiz) und „Einstellungen“ (Versand, Abholung, Bank, PayPal.me) | `/admin` |
| Rechtsseiten: Impressum, Datenschutz, AGB + Widerrufsbelehrung + Muster-Formular, Versand & Zahlung | Fußzeile |
| Schriften + three.js lokal (keine Verbindung zu Google/jsDelivr) | Netzwerk-Tab: nur eigene Domain |
| Vorschau-Hinweise im Shop entfernt | Shop-Bereich |
| Shop-Suche (Name + Beschreibung, ä/ae egal) mit Trefferzahl | Shop: Suchfeld über den Produkten |
| Bis zu 6 Fotos pro Produkt (Admin: 3 Spalten) | `/admin` → Produkt bearbeiten |
| Bewertungen 1–5 Sterne je Produkt, erst nach Freigabe sichtbar, „Verifizierter Kauf“ per Bestellnummer, Antwort möglich | Shop-Karte „★ Bewertungen“; Admin-Reiter „Bewertungen“; `/api/bewertungen` |

### VOR dem Deploy vom Nutzer nötig
1. **GISA-Zahl + Gewerbewortlaut** fürs Impressum (`public/impressum.html`, gelb markiert) – sonst nicht live schalten.
2. Gewerbebehörde/Kammer im Impressum bestätigen (eingetragen: MBA 16, WKO Wien).
3. Rechtstexte (AGB, Widerruf, Datenschutz) kurz gegenlesen – Vorlage, keine Rechtsberatung.

### NACH dem Deploy
1. Admin → Einstellungen: **IBAN/BIC**, **PayPal.me-Name**, Versandpreise prüfen (Standard AT 5,90 / DE 12,90).
2. Netlify → Forms → Formular „bestellung“: **E-Mail-Benachrichtigung** an die Shop-Adresse einschalten (sonst merkt man neue Bestellungen nur im Admin).
3. Testbestellung (Abholung + Bar) machen, im Admin auf „storniert“ setzen.
4. Kund:innen bekommen (noch) keine automatische Bestätigungs-Mail – im Admin auf die E-Mail-Adresse klicken und manuell bestätigen. Optional später: Mail-Dienst (z. B. Resend) anbinden.

## Ablauf am 23.11.
1. In Netlify prüfen bzw. den Nutzer fragen, ob Credits wieder da sind (Banner „operational credits“ weg).
2. Branch nach `main` bringen (Fast-Forward) – **ein** Push = **ein** Deploy.
3. Warten, bis live; prüfen: `/admin/index.html` enthält `uploadBtn` und `ownGroup`,
   Ringbilder haben die neuen MD5-Summen.
4. **Nach dem Deploy:** beim Produkt `formel-modellbausatz` per Admin-API `linkLabel: "Bauanleitung (PDF)"`,
   `linkUrl: "/anleitungen/formel-pb-bauanleitung.pdf"` setzen (vorher speichert der alte Server das Feld nicht).
   Produkt ist sichtbar (24,90 €, vom Nutzer bestätigt).
   **Firmenlogo einschalten** (`logo: true`) bei allen Produkten mit PB-Logo/Schriftzug:
   `kaffeeklipp`, `taschen-disc`, `stand`, `staender-z`, `formel-modellbausatz` – danach Testbestellung mit Logo bis ins Formular.
5. Diese Datei danach löschen.

## Ab jetzt sparsam deployen
- Website-Änderungen auf dem Branch sammeln und gebündelt nach `main` pushen.
- Reine STL-/Skript-Änderungen lösen dank `ignore`-Regel in `netlify.toml` keinen Deploy mehr aus.
- Produkte/Bilder/Dateien im Admin brauchen keinen Deploy (Netlify Blobs über die Admin-API).
- 3D-Dateien in den Admin bringen: `python3 3d-druck/src/dateien_abgleich.py` (kein Deploy nötig).
