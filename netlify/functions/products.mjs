// Öffentlich: Liste der sichtbaren Produkte für den Shop
import { json, loadProducts } from "../lib/shop.mjs";

export default async () => {
  try {
    const list = await loadProducts();
    return json(list.filter((p) => p.visible !== false), 200, { "cache-control": "public, max-age=0, must-revalidate" });
  } catch (e) {
    return json({ error: "Produkte konnten nicht geladen werden." }, 500);
  }
};

export const config = { path: "/api/products" };
