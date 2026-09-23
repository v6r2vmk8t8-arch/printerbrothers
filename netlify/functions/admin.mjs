// Admin: Login prüfen, Produkte und Filamente speichern, Fotos hochladen
import { checkAuth, cleanupImages, json, loadFilaments, loadProducts, sanitizeFilaments, sanitizeList, saveFilaments, saveProducts, shopStore } from "../lib/shop.mjs";

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
