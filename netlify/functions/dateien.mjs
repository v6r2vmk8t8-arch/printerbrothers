// Admin: 3D-Dateien (Netlify Blobs, Speicher "dateien")
//   quelle "claude": Spiegel des Ordners 3d-druck/ aus dem GitHub-Repository
//                    (abgeglichen mit 3d-druck/src/dateien_abgleich.py)
//   quelle "eigene": von euch hochgeladene Dateien
// Dateien werden in 4-MB-Teilen übertragen (ein Netlify-Funktionsaufruf ist auf ca. 6 MB begrenzt).
// Alles nur mit Admin-Login (Passwort oder API-Schlüssel).
import { getStore } from "@netlify/blobs";
import { createHash } from "node:crypto";
import { checkAuth, json } from "../lib/shop.mjs";

const CHUNK = 4 * 1024 * 1024;
const MAX_CHUNKS = 50;                       // max. 200 MB pro Datei
const EXT = /\.(stl|3mf|step|stp|obj|zip|gcode|scad|f3d|png|jpe?g|pdf)$/i;
const QUELLEN = ["claude", "eigene"];
const ID = /^[a-z0-9-]{6,24}$/;
const store = () => getStore({ name: "dateien", consistency: "strong" });

const cleanName = (s) => String(s || "").replace(/[\u0000-\u001f\\]/g, "").trim().slice(0, 160);
const cleanPath = (s) => cleanName(s).split("/").filter((p) => p && p !== "." && p !== "..").join("/");
const newId = () => Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8);
const pathId = (p) => "c" + createHash("sha1").update(p).digest("hex").slice(0, 16);

async function removeFile(quelle, id) {
  const meta = await store().get(`meta/${quelle}/${id}`, { type: "json" });
  const n = meta?.chunks || MAX_CHUNKS;
  await store().delete(`meta/${quelle}/${id}`);
  await Promise.all(Array.from({ length: n }, (_, k) => store().delete(`teil/${quelle}/${id}/${k}`)));
}

export default async (req) => {
  const denied = await checkAuth(req);
  if (denied) return denied;
  const url = new URL(req.url);
  const route = url.pathname.replace(/^\/api\/dateien\/?/, "").replace(/\/$/, "");
  const q = url.searchParams;
  const quelle = q.get("quelle") || "eigene";
  if (route !== "liste" && !QUELLEN.includes(quelle)) return json({ error: "Unbekannte Quelle." }, 400);

  try {
    // ---------- Übersicht ----------
    if (route === "liste" && req.method === "GET") {
      const out = {};
      for (const qu of QUELLEN) {
        const { blobs } = await store().list({ prefix: `meta/${qu}/` });
        const metas = await Promise.all(blobs.map((b) => store().get(b.key, { type: "json" })));
        out[qu] = metas.filter(Boolean).sort((a, b) =>
          qu === "claude" ? a.pfad.localeCompare(b.pfad, "de") : b.uploaded - a.uploaded);
      }
      return json(out);
    }

    // ---------- Datei (ein Teil) herunterladen ----------
    if (route === "datei" && req.method === "GET") {
      const id = q.get("id") || "";
      if (!ID.test(id)) return json({ error: "Ungültige Datei." }, 400);
      const meta = await store().get(`meta/${quelle}/${id}`, { type: "json" });
      if (!meta) return json({ error: "Datei nicht gefunden." }, 404);
      const i = Math.min(Math.max(0, parseInt(q.get("teil") || "0", 10) || 0), meta.chunks - 1);
      const buf = await store().get(`teil/${quelle}/${id}/${i}`, { type: "arrayBuffer" });
      if (!buf) return json({ error: "Dateiteil fehlt." }, 404);
      return new Response(buf, {
        headers: {
          "content-type": "application/octet-stream", "cache-control": "no-store",
          "x-teil": String(i), "x-teile": String(meta.chunks), "x-groesse": String(meta.size),
          "x-name": encodeURIComponent(meta.name),
        },
      });
    }

    // ---------- Hochladen (ein Teil pro Aufruf) ----------
    if (route === "hochladen" && req.method === "POST") {
      const pfad = quelle === "claude" ? cleanPath(q.get("pfad")) : "";
      const name = quelle === "claude" ? pfad.split("/").pop() : cleanName(q.get("name")).replace(/\//g, "");
      const chunks = parseInt(q.get("teile") || "0", 10);
      const i = parseInt(q.get("teil") || "-1", 10);
      const size = parseInt(q.get("groesse") || "0", 10);
      if (!name || !EXT.test(name)) return json({ error: "Dateityp nicht erlaubt (z. B. STL, 3MF, STEP, OBJ, ZIP)." }, 415);
      if (!(chunks >= 1 && chunks <= MAX_CHUNKS) || !(i >= 0 && i < chunks)) return json({ error: "Datei zu groß (max. 200 MB)." }, 413);
      let id = q.get("id") || "";
      if (quelle === "claude") id = pathId(pfad);
      else if (i === 0) id = newId();
      if (!ID.test(id)) return json({ error: "Ungültiger Upload." }, 400);
      const buf = await req.arrayBuffer();
      if (!buf.byteLength || buf.byteLength > CHUNK) return json({ error: "Ungültiger Dateiteil." }, 400);
      if (quelle === "claude" && i === 0) {
        const old = await store().get(`meta/claude/${id}`, { type: "json" });
        if (old) await removeFile("claude", id);          // ersetzt ältere Version
      }
      await store().set(`teil/${quelle}/${id}/${i}`, buf);
      if (i === chunks - 1) {
        const meta = { id, name, size, chunks, uploaded: Date.now() };
        if (quelle === "claude") { meta.pfad = pfad; meta.md5 = String(q.get("md5") || "").slice(0, 32); }
        await store().setJSON(`meta/${quelle}/${id}`, meta);
      }
      return json({ ok: true, id, fertig: i === chunks - 1 });
    }

    // ---------- Löschen ----------
    if (route === "datei" && req.method === "DELETE") {
      const id = q.get("id") || "";
      if (!ID.test(id)) return json({ error: "Ungültige Datei." }, 400);
      await removeFile(quelle, id);
      return json({ ok: true });
    }

    return json({ error: "Unbekannte Aktion." }, 404);
  } catch (e) {
    return json({ error: e?.message || "Fehler." }, 500);
  }
};

export const config = { path: "/api/dateien/*" };
