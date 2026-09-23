// Öffentlich: Filamentfarben, die gerade vorrätig sind (für die Farbauswahl im Warenkorb)
import { json, loadFilaments } from "../lib/shop.mjs";

export default async () => {
  try {
    const list = await loadFilaments();
    return json(list.filter((f) => f.available !== false), 200, { "cache-control": "public, max-age=0, must-revalidate" });
  } catch (e) {
    return json({ error: "Filamente konnten nicht geladen werden." }, 500);
  }
};

export const config = { path: "/api/filaments" };
