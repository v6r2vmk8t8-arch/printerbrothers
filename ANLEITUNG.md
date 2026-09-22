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

## Passwort ändern
Netlify → Site configuration → Environment variables → `ADMIN_PASSWORD` bearbeiten
→ danach Deploys → „Trigger deploy“.
