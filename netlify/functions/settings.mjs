// Öffentlich: Versand- und Zahlungsoptionen für den Warenkorb (ohne Bankdaten)
import { json, loadSettings, publicSettings } from "../lib/shop.mjs";

export default async () => {
  try {
    return json(publicSettings(await loadSettings()), 200, { "cache-control": "public, max-age=0, must-revalidate" });
  } catch (e) {
    return json({ error: "Einstellungen konnten nicht geladen werden." }, 500);
  }
};

export const config = { path: "/api/settings" };
