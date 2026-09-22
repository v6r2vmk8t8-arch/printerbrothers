// Liefert hochgeladene Produktfotos aus
import { IMG_KEY, shopStore } from "../lib/shop.mjs";

export default async (req, context) => {
  const key = context.params?.key || "";
  if (!IMG_KEY.test(key)) return new Response("Nicht gefunden", { status: 404 });
  const res = await shopStore().getWithMetadata("img/" + key, { type: "arrayBuffer" });
  if (!res) return new Response("Nicht gefunden", { status: 404 });
  return new Response(res.data, {
    headers: {
      "content-type": res.metadata?.type || "image/jpeg",
      "cache-control": "public, max-age=31536000, immutable",
    },
  });
};

export const config = { path: "/api/img/:key" };
