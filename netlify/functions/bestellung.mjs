// Öffentlich: Bestellung aufgeben. Preise und Versand rechnet der Server selbst nach.
import { buildOrder, json, loadFilaments, loadProducts, loadSettings, orderStore, paymentInfo } from "../lib/shop.mjs";

export default async (req) => {
  if (req.method !== "POST") return json({ error: "Nur POST." }, 405);
  const raw = await req.text();
  if (raw.length > 60000) return json({ error: "Bestellung zu groß." }, 413);
  let input;
  try { input = JSON.parse(raw); } catch { return json({ error: "Ungültige Daten." }, 400); }
  if (input?.website) return json({ ok: true, number: "PB-SPAM" }); // Honigtopf-Feld: Bots
  try {
    const [products, settings, filaments] = await Promise.all([loadProducts(), loadSettings(), loadFilaments()]);
    const order = buildOrder(input, products, settings, filaments);
    await orderStore().setJSON("o/" + order.number + ".json", order);
    return json({ ok: true, order, pay: paymentInfo(order, settings) });
  } catch (e) {
    return json({ error: e?.message || "Bestellung fehlgeschlagen." }, 400);
  }
};

export const config = { path: "/api/bestellung" };
