// Öffentlich: freigegebene Bewertungen lesen (GET) und neue Bewertung abgeben (POST, erscheint erst nach Freigabe)
import { buildReview, json, loadProducts, loadReviews, publicReview, reviewStore } from "../lib/shop.mjs";

export default async (req) => {
  try {
    if (req.method === "GET") {
      const list = (await loadReviews()).filter((r) => r.status === "freigegeben").map(publicReview);
      return json(list, 200, { "cache-control": "public, max-age=60" });
    }
    if (req.method === "POST") {
      const raw = await req.text();
      if (raw.length > 5000) return json({ error: "Zu lang." }, 413);
      let input;
      try { input = JSON.parse(raw); } catch { return json({ error: "Ungültige Daten." }, 400); }
      if (input?.website) return json({ ok: true }); // Honigtopf: Bots
      const review = await buildReview(input, await loadProducts());
      await reviewStore().setJSON("r/" + review.id + ".json", review);
      return json({ ok: true, verified: review.verified });
    }
    return json({ error: "Nicht erlaubt." }, 405);
  } catch (e) {
    return json({ error: e?.message || "Fehler." }, 400);
  }
};

export const config = { path: "/api/bewertungen" };
