"""Spiegelt den Ordner 3d-druck/ in den Admin-Bereich „3D-Dateien → Von Claude“.

Lädt neue/geänderte Dateien hoch (Vergleich per MD5) und entfernt dort nur Dateien,
die in diesem Zweig gelöscht wurden (Dateien anderer Claude-Sitzungen bleiben). Quellskripte (src/) werden nicht übertragen.

Aufruf:  python3 3d-druck/src/dateien_abgleich.py [--trocken]

Benötigt Zugriff auf die Admin-API (in der Cloud-Umgebung wird der API-Schlüssel
automatisch mitgeschickt; lokal: Umgebungsvariable PB_API_TOKEN setzen).
"""
import hashlib
import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path

BASE = "https://printerbrothers.netlify.app/api/dateien/"
ROOT = Path(__file__).resolve().parents[1]           # 3d-druck/
EXT = {".stl", ".3mf", ".step", ".stp", ".obj", ".zip", ".gcode", ".scad", ".f3d", ".png", ".jpg", ".jpeg", ".pdf"}
CHUNK = 4 * 1024 * 1024
DRY = "--trocken" in sys.argv


def curl(args, data=None):
    cmd = ["curl", "-sS", "--fail-with-body", "--max-time", "120", "--retry", "3"]
    tok = os.environ.get("PB_API_TOKEN")
    if tok:
        cmd += ["-H", f"Authorization: Bearer {tok}"]
    cmd += args
    r = subprocess.run(cmd, input=data, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:3])}: {r.stdout[:300]!r} {r.stderr[:300]!r}")
    return r.stdout


def lokale_dateien():
    out = {}
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT).as_posix()
        if p.is_file() and p.suffix.lower() in EXT and not rel.startswith("src/") and "/." not in "/" + rel:
            out[rel] = p
    return out


_GELOESCHT = None


def im_zweig_geloescht():
    """Pfade (relativ zu 3d-druck/), die in der Git-Geschichte dieses Zweigs gelöscht wurden."""
    global _GELOESCHT
    if _GELOESCHT is None:
        out = subprocess.run(["git", "log", "--no-renames", "--diff-filter=D", "--name-only", "--format=", "HEAD", "--", "."],
                             cwd=ROOT, capture_output=True, text=True).stdout
        _GELOESCHT = {l[len("3d-druck/"):] for l in out.split() if l.startswith("3d-druck/")}
    return _GELOESCHT


def main():
    remote = {m["pfad"]: m for m in json.loads(curl([BASE + "liste"]))["claude"]}
    local = lokale_dateien()
    neu = gleich = 0
    for rel, p in local.items():
        data = p.read_bytes()
        md5 = hashlib.md5(data).hexdigest()
        if rel in remote and remote[rel].get("md5") == md5 and remote[rel].get("size") == len(data):
            gleich += 1
            continue
        n = max(1, -(-len(data) // CHUNK))
        print(f"↑ {rel} ({len(data) / 1e6:.1f} MB, {n} Teil{'e' if n > 1 else ''})")
        neu += 1
        if DRY:
            continue
        for i in range(n):
            qs = urllib.parse.urlencode({"quelle": "claude", "pfad": rel, "teile": n, "teil": i,
                                         "groesse": len(data), "md5": md5})
            curl(["-X", "POST", "-H", "content-type: application/octet-stream", "--data-binary", "@-",
                  BASE + "hochladen?" + qs], data=data[i * CHUNK:(i + 1) * CHUNK])
    # Nur löschen, was in DIESEM Zweig nachweislich gelöscht wurde. Dateien, die dieser Zweig nie hatte,
    # stammen aus anderen Claude-Sitzungen/Zweigen und bleiben stehen (sonst löschen sich Sitzungen gegenseitig).
    weg = [m for pfad, m in remote.items() if pfad not in local and pfad in im_zweig_geloescht()]
    fremd = [p for p in remote if p not in local and p not in im_zweig_geloescht()]
    if fremd:
        print(f"  {len(fremd)} Datei(en) aus anderen Zweigen bleiben unangetastet, z. B. {fremd[0]}")
    for m in weg:
        print(f"✕ {m['pfad']} (im Repository gelöscht)")
        if not DRY:
            curl(["-X", "DELETE", BASE + "datei?" + urllib.parse.urlencode({"quelle": "claude", "id": m["id"]})])
    print(f"Fertig: {neu} hochgeladen, {gleich} unverändert, {len(weg)} entfernt{' (Probelauf)' if DRY else ''}.")


if __name__ == "__main__":
    main()
