import { getStore } from "@netlify/blobs";
import { createHash, timingSafeEqual } from "node:crypto";
import SEED from "./seed.mjs";
import FILAMENT_SEED from "./filament-seed.mjs";

export const ICONS = ["drache", "vase", "schach", "stand", "flitzer"];
export const IMG_KEY = /^[a-z0-9-]{6,40}\.(jpg|png|webp)$/;
const PRODUCTS_KEY = "products.json";
const FILAMENTS_KEY = "filaments.json";
export const MAX_COLORS = 4; // A1 mini + AMS lite: bis zu 4 Farben pro Druck
export const MAX_IMAGES = 6;
export const MAX_OPTIONS = 3; // Auswahlfelder pro Produkt (z. B. Größe, Muster)

export const shopStore = () => getStore({ name: "shop", consistency: "strong" });

export function json(body, status = 200, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...headers },
  });
}

export async function loadProducts() {
  const data = await shopStore().get(PRODUCTS_KEY, { type: "json" });
  return Array.isArray(data) ? data : SEED;
}

export async function saveProducts(list) {
  await shopStore().setJSON(PRODUCTS_KEY, list);
}

export async function loadFilaments() {
  const data = await shopStore().get(FILAMENTS_KEY, { type: "json" });
  return Array.isArray(data) ? data : FILAMENT_SEED;
}

export async function saveFilaments(list) {
  await shopStore().setJSON(FILAMENTS_KEY, list);
}

/* ---------- Passwort ---------- */
const hash = (s) => createHash("sha256").update(String(s)).digest();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function checkAuth(req) {
  // Optional: eigener API-Schlüssel (z. B. für Claude), unabhängig vom Admin-Passwort.
  // Netlify-Variable ADMIN_API_TOKEN (mind. 24 Zeichen); Aufruf mit "Authorization: Bearer <Schlüssel>".
  // Löschen der Variable (+ neu deployen) sperrt den Schlüssel sofort.
  const token = process.env.ADMIN_API_TOKEN || "";
  const bearer = (req.headers.get("authorization") || "").match(/^Bearer\s+(.+)$/i)?.[1]?.trim() || "";
  if (token.length >= 24 && bearer) {
    if (timingSafeEqual(hash(bearer), hash(token))) return null; // alles ok
    await sleep(800);
    return json({ error: "Falscher API-Schlüssel." }, 401);
  }

  const pw = process.env.ADMIN_PASSWORD || "";
  if (pw.length < 8) return json({ error: "Am Server ist noch kein Admin-Passwort (mind. 8 Zeichen) eingerichtet." }, 503);
  const given = req.headers.get("x-admin-password") || "";
  if (!timingSafeEqual(hash(given), hash(pw))) {
    await sleep(800); // bremst Durchprobieren
    return json({ error: "Falsches Passwort." }, 401);
  }
  return null; // alles ok
}

/* ---------- Eingaben prüfen ---------- */
const str = (v, max) => String(v ?? "").replace(/[\u0000-\u001f]/g, " ").trim().slice(0, max);

const isImageUrl = (u) => /^\/api\/img\/[a-z0-9.-]+$/.test(u) || /^\/images\/[A-Za-z0-9._-]+$/.test(u);

export function sanitizeList(input) {
  if (!Array.isArray(input)) throw new Error("Ungültige Daten.");
  if (input.length > 200) throw new Error("Maximal 200 Produkte.");
  const seen = new Set();
  return input.map((p, i) => {
    const name = str(p?.name, 60);
    if (!name) throw new Error(`Produkt ${i + 1}: Name fehlt.`);
    let id = str(p?.id, 40).toLowerCase().replace(/[^a-z0-9-]/g, "");
    if (!id || seen.has(id)) id = "p-" + Date.now().toString(36) + "-" + i;
    seen.add(id);
    const price = Math.round(Number(p?.price) * 100) / 100;
    if (!Number.isFinite(price) || price < 0 || price > 10000) throw new Error(`„${name}“: Preis ungültig.`);
    // Fotos: bis zu 6, das erste ist das Titelbild. Ältere Daten haben nur "image".
    const rawImages = Array.isArray(p?.images) ? p.images : p?.image ? [p.image] : [];
    const images = [...new Set(rawImages.map((u) => String(u ?? "")).filter(isImageUrl))].slice(0, MAX_IMAGES);
    const image = images[0] || null;
    const icon = ICONS.includes(p?.icon) ? p.icon : null;
    // Farbteile: ein Eintrag pro wählbarer Farbe (Name darf leer sein, z. B. ["Körper", "Augen"])
    let parts = Array.isArray(p?.parts) ? p.parts.slice(0, MAX_COLORS).map((t) => str(t, 24)) : [""];
    if (!parts.length) parts = [""];
    // Optional: Kund:innen schreiben etwas dazu (z. B. den Namen für einen Anhänger)
    const note = p?.note === true;
    const noteLabel = note ? str(p?.noteLabel, 40) || "Dein Text" : "";
    // Optional: Auswahl-Optionen (z. B. Größe, Muster) – bis zu 3, je bis zu 10 Werte
    const options = (Array.isArray(p?.options) ? p.options : []).slice(0, MAX_OPTIONS).map((o) => ({
      name: str(o?.name, 20),
      values: [...new Set((Array.isArray(o?.values) ? o.values : []).map((v) => str(v, 30)).filter(Boolean))].slice(0, 10),
    })).filter((o) => o.name && o.values.length >= 2);
    // Optional: Link, z. B. zur PDF-Bauanleitung (nur eigene Dateien unter /anleitungen/ oder https)
    let linkUrl = str(p?.linkUrl, 300);
    if (!/^\/anleitungen\/[A-Za-z0-9._-]+$/.test(linkUrl) && !/^https:\/\/[^\s"'<>]+$/.test(linkUrl)) linkUrl = "";
    const linkLabel = linkUrl ? str(p?.linkLabel, 40) || "Anleitung (PDF)" : "";
    // Optional: Firmen schicken ihr eigenes Logo mit (statt des Printer-Brothers-Logos)
    const logo = p?.logo === true;
    return { id, name, desc: str(p?.desc, 240), price, image, images, icon: image ? null : icon, parts, note, noteLabel, logo, options, linkLabel, linkUrl, visible: p?.visible !== false };
  });
}

export function sanitizeFilaments(input) {
  if (!Array.isArray(input)) throw new Error("Ungültige Daten.");
  if (input.length > 40) throw new Error("Maximal 40 Filamente.");
  const seen = new Set();
  return input.map((f, i) => {
    const name = str(f?.name, 30);
    if (!name) throw new Error(`Filament ${i + 1}: Name fehlt.`);
    let id = str(f?.id, 40).toLowerCase().replace(/[^a-z0-9-]/g, "");
    if (!id || seen.has(id)) id = "f-" + Date.now().toString(36) + "-" + i;
    seen.add(id);
    let hex = str(f?.hex, 7).toUpperCase();
    if (!/^#[0-9A-F]{6}$/.test(hex)) throw new Error(`„${name}“: Farbcode ungültig.`);
    return { id, name, hex, translucent: f?.translucent === true, available: f?.available !== false };
  });
}

/* Bilder löschen, die kein Produkt mehr verwendet */
export async function cleanupImages(list) {
  const used = new Set(list.flatMap((p) => (p.images?.length ? p.images : [p.image])).filter((u) => u && u.startsWith("/api/img/")).map((u) => "img/" + u.slice(9)));
  const store = shopStore();
  const { blobs } = await store.list({ prefix: "img/" });
  const cutoff = Date.now() - 60 * 60 * 1000; // frische Uploads (< 1 h) nie anrühren
  await Promise.all(blobs.filter((b) => !used.has(b.key)).map(async (b) => {
    const ts = parseInt(b.key.slice(4).split("-")[0], 36);
    if (Number.isFinite(ts) && ts < cutoff) await store.delete(b.key);
  }));
}

/* ---------- Shop-Einstellungen (Versand, Zahlung) ---------- */
const SETTINGS_KEY = "settings.json";
export const SETTINGS_DEFAULT = {
  shipping: { AT: 5.9, DE: 12.9 },  // Versandpauschale je Land (inkl. USt)
  freeFrom: 0,                       // ab diesem Warenwert versandkostenfrei (0 = nie)
  pickup: { enabled: true, text: "Abholung in 1160 Wien nach Vereinbarung" },
  payments: { transfer: true, paypal: true, cash: true },
  bank: { holder: "Matthias Habringer", iban: "", bic: "", name: "" },
  paypalMe: "",                      // z. B. "printerbrothers" -> https://paypal.me/printerbrothers
  vatRate: 20,
  open: true,                        // Bestellungen annehmen
};

const num = (v, d, max = 1000) => { const n = Math.round(Number(v) * 100) / 100; return Number.isFinite(n) && n >= 0 && n <= max ? n : d; };

export function sanitizeSettings(s) {
  const D = SETTINGS_DEFAULT;
  const iban = str(s?.bank?.iban, 40).toUpperCase().replace(/\s+/g, "");
  if (iban && !/^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$/.test(iban)) throw new Error("IBAN sieht ungültig aus.");
  const paypalMe = str(s?.paypalMe, 40).replace(/^https?:\/\/(www\.)?paypal\.me\//i, "").replace(/[^A-Za-z0-9._-]/g, "");
  return {
    shipping: { AT: num(s?.shipping?.AT, D.shipping.AT, 200), DE: num(s?.shipping?.DE, D.shipping.DE, 200) },
    freeFrom: num(s?.freeFrom, 0, 10000),
    pickup: { enabled: s?.pickup?.enabled !== false, text: str(s?.pickup?.text, 120) || D.pickup.text },
    payments: { transfer: s?.payments?.transfer !== false, paypal: s?.payments?.paypal !== false, cash: s?.payments?.cash !== false },
    bank: { holder: str(s?.bank?.holder, 70), iban, bic: str(s?.bank?.bic, 11).toUpperCase().replace(/\s+/g, ""), name: str(s?.bank?.name, 60) },
    paypalMe,
    vatRate: D.vatRate,
    open: s?.open !== false,
  };
}

export async function loadSettings() {
  const data = await shopStore().get(SETTINGS_KEY, { type: "json" });
  return sanitizeSettings({ ...SETTINGS_DEFAULT, ...(data || {}) });
}

export async function saveSettings(s) {
  await shopStore().setJSON(SETTINGS_KEY, s);
}

/* Was Kund:innen sehen dürfen (ohne Bankdaten) */
export function publicSettings(s) {
  return {
    shipping: s.shipping, freeFrom: s.freeFrom, pickup: s.pickup, vatRate: s.vatRate, open: s.open,
    payments: { transfer: s.payments.transfer, paypal: s.payments.paypal && !!s.paypalMe, cash: s.payments.cash && s.pickup.enabled },
  };
}

/* ---------- Bestellungen ---------- */
export const orderStore = () => getStore({ name: "orders", consistency: "strong" });
export const ORDER_STATUS = ["neu", "bezahlt", "in Arbeit", "versendet", "abgeholt", "storniert"];
const EMAIL = /^[^\s@<>"]+@[^\s@<>"]+\.[a-z]{2,}$/i;

export function newOrderNumber() {
  const d = new Date();
  const ymd = String(d.getUTCFullYear()).slice(2) + String(d.getUTCMonth() + 1).padStart(2, "0") + String(d.getUTCDate()).padStart(2, "0");
  const rnd = Array.from({ length: 4 }, () => "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"[Math.floor(Math.random() * 32)]).join("");
  return `PB-${ymd}-${rnd}`;
}

/* Bestellung prüfen und Preise am Server neu rechnen (der Browser bestimmt keine Preise) */
export function buildOrder(input, products, settings) {
  if (!settings.open) throw new Error("Der Shop nimmt gerade keine Bestellungen an.");
  const byId = new Map(products.filter((p) => p.visible !== false).map((p) => [p.id, p]));
  const rawItems = Array.isArray(input?.items) ? input.items : [];
  if (!rawItems.length) throw new Error("Der Warenkorb ist leer.");
  if (rawItems.length > 30) throw new Error("Zu viele Positionen.");
  const items = rawItems.map((it) => {
    const p = byId.get(String(it?.id || ""));
    if (!p) throw new Error("Ein Produkt im Warenkorb gibt es nicht mehr – bitte Seite neu laden.");
    const qty = Math.floor(Number(it?.qty));
    if (!(qty >= 1 && qty <= 99)) throw new Error(`„${p.name}“: Menge ungültig.`);
    const colors = (Array.isArray(it?.colors) ? it.colors : []).slice(0, MAX_COLORS).map((c) => str(c, 30));
    const opts = (p.options || []).map((o, i) => {
      const v = str(it?.opts?.[i], 30);
      if (!o.values.includes(v)) throw new Error(`„${p.name}“: ${o.name} ungültig.`);
      return { name: o.name, value: v };
    });
    const note = p.note ? str(it?.note, 60) : "";
    if (p.note && !note) throw new Error(`„${p.name}“: ${p.noteLabel} fehlt noch.`);
    const logo = p.logo ? str(it?.logo, 100) : "";
    return { id: p.id, name: p.name, price: p.price, qty, parts: p.parts, colors, opts, note, noteLabel: p.note ? p.noteLabel : "", logo };
  });
  const c = input?.customer || {};
  const delivery = ["AT", "DE", "pickup"].includes(input?.delivery) ? input.delivery : "";
  if (!delivery) throw new Error("Bitte eine Lieferart wählen.");
  if (delivery === "pickup" && !settings.pickup.enabled) throw new Error("Abholung ist gerade nicht möglich.");
  const customer = {
    name: str(c.name, 80), email: str(c.email, 120), phone: str(c.phone, 40),
    street: str(c.street, 100), zip: str(c.zip, 10), city: str(c.city, 60),
    country: delivery === "DE" ? "Deutschland" : "Österreich",
  };
  if (customer.name.length < 3) throw new Error("Bitte Vor- und Nachnamen angeben.");
  if (!EMAIL.test(customer.email)) throw new Error("Bitte eine gültige E-Mail-Adresse angeben.");
  if (delivery !== "pickup") {
    if (!customer.street || !customer.city) throw new Error("Bitte die Lieferadresse vollständig angeben.");
    if (!(delivery === "AT" ? /^\d{4}$/ : /^\d{5}$/).test(customer.zip)) throw new Error("Bitte eine gültige Postleitzahl angeben.");
  }
  const pub = publicSettings(settings);
  const payment = String(input?.payment || "");
  if (!(pub.payments[payment])) throw new Error("Bitte eine Zahlungsart wählen.");
  if (payment === "cash" && delivery !== "pickup") throw new Error("Barzahlung geht nur bei Abholung.");
  if (input?.accept !== true) throw new Error("Bitte die AGB akzeptieren.");
  const round = (n) => Math.round(n * 100) / 100;
  const subtotal = round(items.reduce((s, i) => s + i.price * i.qty, 0));
  const shipping = delivery === "pickup" || (settings.freeFrom > 0 && subtotal >= settings.freeFrom) ? 0 : settings.shipping[delivery];
  const total = round(subtotal + shipping);
  const vat = round(total - total / (1 + settings.vatRate / 100));
  return {
    number: newOrderNumber(), createdAt: new Date().toISOString(), status: "neu",
    items, customer, delivery, payment, message: str(input?.message, 500),
    subtotal, shipping, total, vat, vatRate: settings.vatRate,
  };
}

/* Zahlungsinfos für die Bestätigung */
export function paymentInfo(order, settings) {
  const amount = order.total.toFixed(2);
  if (order.payment === "transfer") return { kind: "transfer", bank: settings.bank, reference: order.number, amount };
  if (order.payment === "paypal") return { kind: "paypal", url: `https://paypal.me/${encodeURIComponent(settings.paypalMe)}/${amount}EUR`, amount };
  return { kind: "cash", amount, pickup: settings.pickup.text };
}

/* ---------- Bewertungen (werden vor der Veröffentlichung im Admin freigegeben) ---------- */
export const reviewStore = () => getStore({ name: "reviews", consistency: "strong" });
export const REVIEW_STATUS = ["neu", "freigegeben", "abgelehnt"];

export async function loadReviews() {
  const store = reviewStore();
  const { blobs } = await store.list({ prefix: "r/" });
  const list = (await Promise.all(blobs.map((b) => store.get(b.key, { type: "json" })))).filter(Boolean);
  return list.sort((a, b) => String(b.createdAt).localeCompare(String(a.createdAt)));
}

/* Neue Bewertung prüfen; mit Bestellnummer wird geprüft, ob das Produkt wirklich bestellt wurde */
export async function buildReview(input, products) {
  const p = products.find((x) => x.id === String(input?.productId || "") && x.visible !== false);
  if (!p) throw new Error("Produkt nicht gefunden.");
  const stars = Math.round(Number(input?.stars));
  if (!(stars >= 1 && stars <= 5)) throw new Error("Bitte 1 bis 5 Sterne wählen.");
  const name = str(input?.name, 40);
  if (name.length < 2) throw new Error("Bitte einen Namen (oder Vornamen) angeben.");
  const text = str(input?.text, 600);
  if (text.length < 3) throw new Error("Bitte ein paar Worte zum Produkt schreiben.");
  if (/https?:\/\/|www\./i.test(text + name)) throw new Error("Bitte keine Links in die Bewertung schreiben.");
  let verified = false;
  const order = str(input?.order, 20).toUpperCase();
  if (order) {
    if (!/^PB-\d{6}-[A-Z0-9]{4}$/.test(order)) throw new Error("Die Bestellnummer sieht nicht richtig aus (z. B. PB-261124-AB12).");
    const o = await orderStore().get("o/" + order + ".json", { type: "json" });
    verified = !!(o && o.status !== "storniert" && o.items.some((i) => i.id === p.id));
  }
  const id = Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8);
  return { id, productId: p.id, productName: p.name, stars, name, text, verified, order: verified ? order : "", status: "neu", createdAt: new Date().toISOString() };
}

/* Öffentliche Ansicht: nur freigegebene, ohne Bestellnummer */
export function publicReview(r) {
  return { id: r.id, productId: r.productId, stars: r.stars, name: r.name, text: r.text, verified: r.verified, date: r.createdAt.slice(0, 10), reply: r.reply || "" };
}
