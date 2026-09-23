# Printer Brothers – Website mit Shop-Verwaltung

## Aufbau
- `public/` – die Website (index.html, Bilder) und die Admin-Seite (`public/admin/`)
- `netlify/functions/` – kleine Server-Programme für Produkte, Fotos und Admin
- `netlify.toml` – Einstellungen für Netlify

## Produkte verwalten
1. https://printerbrothers.netlify.app/admin öffnen
2. Passwort eingeben
3. „+ Neues Produkt“: Foto aufnehmen/auswählen, Name, Beschreibung, Preis → Speichern
4. Auf ein Produkt tippen zum Bearbeiten, Ausblenden oder Löschen; ▲▼ ändert die Reihenfolge

Änderungen sind sofort im Shop sichtbar – kein neues Hochladen nötig.

## Mehrere Fotos pro Produkt
Im Produkt-Editor können bis zu 4 Fotos hinzugefügt werden (auch mehrere auf einmal).
Das erste Foto ist das Titelbild – mit ★ wird ein anderes Foto zum Titelbild, mit ✕ entfernt.
Im Shop kann man auf der Produktkarte durch die Fotos wischen (am Computer: Pfeile).

## Farben pro Produkt
Im Produkt-Editor bei „Wie viele Farben hat das Teil?“ 1–4 wählen.
Bei mehreren Farben können die Teile benannt werden (z. B. Körper, Augen) –
so steht es dann im Warenkorb.

## Filamente verwalten
1. Im Admin oben auf „Filamente“ tippen
2. „+ Neues Filament“: Name, Farbe (Farbwähler oder Code wie #FF7A2F), ggf. „Transluzent“
3. Ist eine Rolle leer: Filament antippen → „Vorrätig“ ausschalten. Dann ist die Farbe
   im Shop nicht mehr wählbar, bleibt aber gespeichert.
4. ▲▼ ändert die Reihenfolge im Warenkorb

## Passwort ändern
Netlify → Site configuration → Environment variables → `ADMIN_PASSWORD` bearbeiten
→ danach Deploys → „Trigger deploy“.
