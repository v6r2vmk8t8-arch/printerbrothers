// Admin: Login prüfen, Produkte und Filamente speichern, Fotos hochladen
import { checkAuth, cleanupImages, json, loadFilaments, loadProducts, loadSettings, ORDER_STATUS, orderStore, sanitizeFilaments, sanitizeList, sanitizeSettings, saveFilaments, saveProducts, saveSettings, shopStore } from "../lib/shop.mjs";

const TYPES = { "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp" };
const MAX_BYTES = 4 * 1024 * 1024;

export default async (req) => {
  const route = new URL(req.url).pathname.replace(/^\/api\/admin\/?/, "").replace(/\/$/, "");
  const denied = await checkAuth(req);
  if (denied) return denied;

  try {
    if (route === "login" && req.method === "POST") return json({ ok: true });

    if (route === "products" && req.method === "GET") return json(await loadProducts());

    if (route === "products" && req.method === "PUT") {
      const list = sanitizeList(await req.json());
      await saveProducts(list);
      cleanupImages(list).catch(() => {});
      return json({ ok: true, products: list });
    }

    if (route === "filaments" && req.method === "GET") return json(await loadFilaments());

    if (route === "filaments" && req.method === "PUT") {
      const list = sanitizeFilaments(await req.json());
      await saveFilaments(list);
      return json({ ok: true, filaments: list });
    }

    if (route === "settings" && req.method === "GET") return json(await loadSettings());

    if (route === "settings" && req.method === "PUT") {
      const st = sanitizeSettings(await req.json());
      await saveSettings(st);
      return json({ ok: true, settings: st });
    }

    if (route === "orders" && req.method === "GET") {
      const store = orderStore();
      const { blobs } = await store.list({ prefix: "o/" });
      const orders = (await Promise.all(blobs.map((b) => store.get(b.key, { type: "json" })))).filter(Boolean);
      orders.sort((a, b) => String(b.createdAt).localeCompare(String(a.createdAt)));
      return json(orders);
    }

    const om = route.match(/^orders\/(PB-\d{6}-[A-Z0-9]{4})$/);
    if (om && req.method === "PUT") {
      const store = orderStore();
      const key = "o/" + om[1] + ".json";
      const order = await store.get(key, { type: "json" });
      if (!order) return json({ error: "Bestellung nicht gefunden." }, 404);
      const body = await req.json();
      if (body.status !== undefined) {
        if (!ORDER_STATUS.includes(body.status)) return json({ error: "Status ungültig." }, 400);
        order.status = body.status;
      }
      if (body.adminNote !== undefined) order.adminNote = String(body.adminNote).slice(0, 500);
      order.updatedAt = new Date().toISOString();
      await store.setJSON(key, order);
      return json({ ok: true, order });
    }

    if (route === "upload" && req.method === "POST") {
      const type = (req.headers.get("content-type") || "").split(";")[0].trim();
      const ext = TYPES[type];
      if (!ext) return json({ error: "Nur JPG, PNG oder WebP." }, 415);
      const buf = await req.arrayBuffer();
      if (!buf.byteLength) return json({ error: "Leere Datei." }, 400);
      if (buf.byteLength > MAX_BYTES) return json({ error: "Foto zu groß (max. 4 MB)." }, 413);
      const key = Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8) + "." + ext;
      await shopStore().set("img/" + key, buf, { metadata: { type } });
      return json({ ok: true, url: "/api/img/" + key });
    }

    return json({ error: "Unbekannte Aktion." }, 404);
  } catch (e) {
    return json({ error: e?.message || "Fehler beim Speichern." }, 400);
  }
};

export const config = { path: "/api/admin/*" };
