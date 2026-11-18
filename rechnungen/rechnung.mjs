// Erstellt eine Printer-Brothers-Rechnung als PDF.
//
// Aufruf:  node rechnungen/rechnung.mjs rechnungen/daten/2026-001.json
// Ergebnis: rechnungen/pdf/Rechnung_2026-001.pdf
//
// Die Rechnungsdaten stehen in einer JSON-Datei (Vorlage: daten/2026-001.json):
//   nummer, datum (JJJJ-MM-TT), kunde (Zeilen, optional), zahlung (Text vor der IBAN, optional),
//   ust_satz (optional, Standard 20),
//   positionen: [{ produkt: "<Shop-ID>", menge, preis?, name?, zusatz?, bild? }]
// Name, Preis und Vorschaubild kommen aus dem Shop (/api/products); preis/name/bild
// in der Position überschreiben das. bild darf eine URL oder ein Pfad im Repo sein.
// Für Positionen ohne Shop-Produkt einfach produkt weglassen und name+preis angeben.
import { readFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve, basename, extname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';

const SHOP = 'https://printerbrothers.netlify.app';
const HIER = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HIER, '..');

// ── Absenderdaten (hier ändern, falls sich etwas ändert) ─────────────────────
const ABSENDER = {
  name: 'Printer Brothers',
  inhaber: 'Matthias Habringer',          // Rechnungsaussteller (Einzelunternehmer)
  rechtsform: 'Einzelunternehmer',
  team: 'Nathanael & Marlon',             // Unterschrift unter dem Dankeschön
  strasse: 'Rosenthal 67/1',
  ort: '2500 Siegenfeld',
  land: 'Österreich',
  uid: 'ATU69412405',
  iban: 'AT65 3200 0000 1210 3834',
  kontoinhaber: 'Matthias Habringer',
  mail: 'Titanael@icloud.com',
  web: 'printerbrothers.netlify.app',
};
// Shop-Preise sind Bruttopreise; die Umsatzsteuer wird herausgerechnet.
const UST_SATZ = 20;

const datei = process.argv[2];
if (!datei) { console.error('Aufruf: node rechnungen/rechnung.mjs <daten.json>'); process.exit(1); }
const R = JSON.parse(readFileSync(datei, 'utf8'));

const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const eur = n => n.toLocaleString('de-AT', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €';
const datum = iso => { const [j, m, t] = iso.split('-'); return `${t}.${m}.${j}`; };
// curl statt fetch: nutzt Proxy-/Zertifikat-Einstellungen der Umgebung zuverlässig
const laden = url => execFileSync('curl', ['-sSfL', '--max-time', '60', url], { maxBuffer: 64 << 20 });
const MIME = { '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.svg': 'image/svg+xml' };

async function alsDataUrl(quelle) {
  if (!quelle) return null;
  if (/^https?:|^\//.test(quelle) && !quelle.startsWith(REPO)) {
    const url = quelle.startsWith('/') ? SHOP + quelle : quelle;
    const typ = MIME[extname(new URL(url).pathname).toLowerCase()] || 'image/jpeg';
    return `data:${typ};base64,${laden(url).toString('base64')}`;
  }
  const p = resolve(REPO, quelle);
  return `data:${MIME[extname(p).toLowerCase()] || 'image/png'};base64,${readFileSync(p).toString('base64')}`;
}

const produkte = (d => d.products || d)(JSON.parse(laden(SHOP + '/api/products')));
const posten = [];
for (const pos of R.positionen) {
  const p = pos.produkt ? produkte.find(x => x.id === pos.produkt) : null;
  if (pos.produkt && !p) throw new Error(`Produkt „${pos.produkt}“ nicht im Shop gefunden`);
  const preis = pos.preis ?? p?.price;
  if (preis == null) throw new Error(`Kein Preis für ${pos.name || pos.produkt}`);
  posten.push({
    name: pos.name || p.name,
    zusatz: pos.zusatz || '',
    menge: pos.menge ?? 1,
    preis,
    bild: await alsDataUrl(pos.bild || p?.image),
  });
}
const cent = n => Math.round(n * 100) / 100;
const summe = cent(posten.reduce((s, x) => s + x.menge * x.preis, 0));        // brutto
const satz = R.ust_satz ?? UST_SATZ;
const netto = cent(summe / (1 + satz / 100));
const ust = cent(summe - netto);

// Logo für dunklen Hintergrund (Kopfband)
const logo = readFileSync(resolve(REPO, 'public/brand/pb-logo-horizontal-dark-bg.svg'), 'utf8');

const html = `<!doctype html><html lang="de"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@100..125,500..900&family=Instrument+Sans:wght@400..600&family=Azeret+Mono:wght@400..600&display=swap" rel="stylesheet">
<style>
  @page { size: A4; margin: 0; }
  :root { --schwarz:#0B0B0C; --gruen:#39FF14; --gruen-dunkel:#1F8F0A; --grau:#6B6B70; --linie:#E4E4E6; }
  * { box-sizing: border-box; }
  html, body { margin: 0; background: #fff; }
  body { font: 10pt/1.45 'Instrument Sans', system-ui, sans-serif; color: var(--schwarz);
         width: 210mm; height: 297mm; position: relative; }
  .kopf { background: var(--schwarz); height: 38mm; padding: 0 18mm; display: flex; align-items: center; justify-content: space-between; }
  .kopf svg { height: 20mm; width: auto; display: block; }
  .kopf .titel { color: #fff; text-align: right; font-family: 'Archivo', sans-serif; font-stretch: 112%; }
  .kopf .titel b { display: block; font-size: 22pt; font-weight: 800; letter-spacing: .02em; }
  .kopf .titel span { font-family: 'Azeret Mono', monospace; font-size: 9pt; color: var(--gruen); }
  .streifen { height: 2.2mm; background: var(--gruen); }
  main { padding: 12mm 18mm 0; }
  .absenderzeile { font-size: 7.5pt; color: var(--grau); border-bottom: 0.3mm solid var(--linie); padding-bottom: 1mm; margin-bottom: 3mm; display: inline-block; }
  .adressblock { display: flex; justify-content: space-between; align-items: flex-start; min-height: 34mm; }
  .kunde { font-size: 10.5pt; line-height: 1.5; }
  .meta { display: grid; grid-template-columns: auto auto; gap: 1.2mm 6mm; font-size: 9pt; }
  .meta dt { color: var(--grau); }
  .meta dd { margin: 0; font-family: 'Azeret Mono', monospace; text-align: right; }
  h1 { font-family: 'Archivo', sans-serif; font-stretch: 112%; font-size: 15pt; font-weight: 800; margin: 8mm 0 2mm; }
  .einleitung { margin: 10mm 0 6mm; color: #333; }
  table { width: 100%; border-collapse: collapse; }
  th { font-size: 7.5pt; text-transform: uppercase; letter-spacing: .08em; color: var(--grau); font-weight: 600;
       text-align: left; padding: 0 2mm 2mm; border-bottom: 0.5mm solid var(--schwarz); }
  td { padding: 3mm 2mm; border-bottom: 0.3mm solid var(--linie); vertical-align: middle; }
  .zahl { text-align: right; font-family: 'Azeret Mono', monospace; white-space: nowrap; }
  .bild { width: 18mm; padding-left: 0; }
  .bild div { width: 15mm; height: 15mm; border-radius: 2.5mm; background: #F2F2F3 center/cover no-repeat; border: 0.3mm solid var(--linie); }
  .artikel b { font-weight: 600; font-size: 10.5pt; }
  .artikel small { display: block; color: var(--grau); font-size: 8.5pt; }
  .summe td { border-bottom: none; padding-top: 1.5mm; padding-bottom: 1.5mm; }
  .summe.erste td { padding-top: 4mm; }
  .summe.gesamt td { padding-top: 3mm; }
  .summe.klein td { color: #333; font-size: 9.5pt; }
  .summe .betrag { font-family: 'Archivo', sans-serif; font-stretch: 112%; font-size: 14pt; font-weight: 800; }
  .summe .label { text-align: right; font-weight: 600; }
  .summe .betrag span { border-bottom: 1.2mm solid var(--gruen); }
  .hinweise { margin-top: 10mm; font-size: 9pt; color: #333; }
  .hinweise p { margin: 0 0 2mm; }
  .danke { margin-top: 8mm; font-family: 'Archivo', sans-serif; font-stretch: 112%; font-weight: 700; font-size: 11pt; }
  .danke span { color: var(--gruen-dunkel); }
  footer { position: absolute; left: 0; right: 0; bottom: 0; }
  footer .inhalt { display: grid; grid-template-columns: 1.2fr 1fr 1fr; gap: 6mm; padding: 5mm 18mm 8mm;
                   border-top: 0.5mm solid var(--schwarz); font-size: 8pt; color: #333; }
  footer b { display: block; font-size: 7pt; text-transform: uppercase; letter-spacing: .08em; color: var(--grau); margin-bottom: 1mm; }
  footer .marke { display: flex; gap: 3mm; align-items: flex-start; }
  footer .marke svg { width: 11mm; height: 11mm; flex: none; }
  footer .streifen { height: 1.5mm; }
</style></head><body>
<header class="kopf">${logo}<div class="titel"><b>RECHNUNG</b><span>Nr. ${esc(R.nummer)}</span></div></header>
<div class="streifen"></div>
<main>
  <div class="absenderzeile">${esc(ABSENDER.name)} · ${esc(ABSENDER.inhaber)} · ${esc(ABSENDER.strasse)} · ${esc(ABSENDER.ort)}</div>
  <div class="adressblock">
    <div class="kunde">${(R.kunde || []).map(esc).join('<br>')}</div>
    <dl class="meta">
      <dt>Rechnungsnr.</dt><dd>${esc(R.nummer)}</dd>
      <dt>Rechnungsdatum</dt><dd>${datum(R.datum)}</dd>
      <dt>Lieferdatum</dt><dd>${datum(R.lieferdatum || R.datum)}</dd>
    </dl>
  </div>
  <p class="einleitung">${esc(R.einleitung || 'Vielen Dank für eure Bestellung! Wir berechnen folgende 3D-gedruckte Artikel:')}</p>
  <table>
    <thead><tr><th></th><th>Artikel</th><th class="zahl">Menge</th><th class="zahl">Einzelpreis</th><th class="zahl">Gesamt</th></tr></thead>
    <tbody>
      ${posten.map(x => `<tr>
        <td class="bild"><div style="${x.bild ? `background-image:url('${x.bild}')` : ''}"></div></td>
        <td class="artikel"><b>${esc(x.name)}</b>${x.zusatz ? `<small>${esc(x.zusatz)}</small>` : ''}</td>
        <td class="zahl">${x.menge}</td><td class="zahl">${eur(x.preis)}</td><td class="zahl">${eur(x.menge * x.preis)}</td>
      </tr>`).join('')}
      <tr class="summe klein erste"><td></td><td></td><td class="label" colspan="2">Nettobetrag</td><td class="zahl">${eur(netto)}</td></tr>
      <tr class="summe klein"><td></td><td></td><td class="label" colspan="2">zzgl. ${satz} % USt</td><td class="zahl">${eur(ust)}</td></tr>
      <tr class="summe gesamt"><td></td><td></td><td class="label" colspan="2">Gesamtbetrag</td><td class="zahl betrag"><span>${eur(summe)}</span></td></tr>
    </tbody>
  </table>
  <div class="hinweise">
    <p>Alle Preise inkl. ${satz} % Umsatzsteuer.</p>
    <p>${esc(R.zahlung || 'Bitte den Gesamtbetrag innerhalb von 14 Tagen auf folgendes Konto überweisen:')}<br>
       <b>IBAN ${esc(ABSENDER.iban)}</b> · lautend auf ${esc(ABSENDER.kontoinhaber)} · Verwendungszweck: Rechnung ${esc(R.nummer)}</p>
  </div>
  <div class="danke">Danke, dass ihr unsere Drucke unterstützt! <span>— ${esc(ABSENDER.team)}</span></div>
</main>
<footer>
  <div class="inhalt">
    <div class="marke">${readFileSync(resolve(REPO, 'public/brand/pb-icon.svg'), 'utf8')}
      <div><b>Printer Brothers</b>${esc(ABSENDER.inhaber)}, ${esc(ABSENDER.rechtsform)}<br>${esc(ABSENDER.strasse)}<br>${esc(ABSENDER.ort)}, ${esc(ABSENDER.land)}</div></div>
    <div><b>Kontakt</b>${esc(ABSENDER.mail)}<br>${esc(ABSENDER.web)}<br>UID: ${esc(ABSENDER.uid)}</div>
    <div><b>Bankverbindung</b>IBAN ${esc(ABSENDER.iban)}<br>Kontoinhaber: ${esc(ABSENDER.kontoinhaber)}</div>
  </div>
  <div class="streifen"></div>
</footer>
</body></html>`;

const ziel = resolve(HIER, 'pdf', `Rechnung_${basename(R.nummer)}.pdf`);
mkdirSync(dirname(ziel), { recursive: true });
const { chromium } = createRequire(import.meta.url)('playwright'); // global installiertes Playwright
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 794, height: 1123 } });
await page.setContent(html, { waitUntil: 'networkidle' });
await page.evaluate(() => document.fonts.ready);
await page.pdf({ path: ziel, format: 'A4', printBackground: true, preferCSSPageSize: true });
if (process.argv.includes('--png')) await page.screenshot({ path: ziel.replace(/\.pdf$/, '.png'), fullPage: true });
await browser.close();
console.log(`✓ ${ziel}  (${posten.length} Positionen, ${eur(summe)})`);
