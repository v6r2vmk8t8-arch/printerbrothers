import { getStore } from "@netlify/blobs";
import { createHash, timingSafeEqual } from "node:crypto";
import SEED from "./seed.mjs";

export const ICONS = ["drache", "vase", "schach", "stand", "flitzer"];
export const IMG_KEY = /^[a-z0-9-]{6,40}\.(jpg|png|webp)$/;
const PRODUCTS_KEY = "products.json";

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

/* ---------- Passwort ---------- */
const hash = (s) => createHash("sha256").update(String(s)).digest();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function checkAuth(req) {
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
    let image = p?.image ? String(p.image) : null;
    if (image && !(/^\/api\/img\/[a-z0-9.-]+$/.test(image) || /^\/images\/[A-Za-z0-9._-]+$/.test(image))) image = null;
    const icon = ICONS.includes(p?.icon) ? p.icon : null;
    return { id, name, desc: str(p?.desc, 240), price, image, icon: image ? null : icon, visible: p?.visible !== false };
  });
}

/* Bilder löschen, die kein Produkt mehr verwendet */
export async function cleanupImages(list) {
  const used = new Set(list.map((p) => p.image).filter((u) => u && u.startsWith("/api/img/")).map((u) => "img/" + u.slice(9)));
  const store = shopStore();
  const { blobs } = await store.list({ prefix: "img/" });
  const cutoff = Date.now() - 60 * 60 * 1000; // frische Uploads (< 1 h) nie anrühren
  await Promise.all(blobs.filter((b) => !used.has(b.key)).map(async (b) => {
    const ts = parseInt(b.key.slice(4).split("-")[0], 36);
    if (Number.isFinite(ts) && ts < cutoff) await store.delete(b.key);
  }));
}
