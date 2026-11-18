"""Spiegelt den Ordner 3d-druck/ in den Admin-Bereich „3D-Dateien → Von Claude“.

Lädt neue/geänderte Dateien hoch (Vergleich per MD5). Quellskripte (src/) werden
nicht übertragen.

Standardmäßig wird im Admin NICHTS gelöscht: Parallel arbeitende Sitzungen auf
anderen Branches laden Dateien hoch, die im lokalen Checkout fehlen – ein reiner
Spiegel würde sie wieder entfernen. Löschen nur mit --loeschen, und dann nur
Dateien, die
  1. im lokalen Checkout fehlen,
  2. laut Git-Historie (git log --diff-filter=D) im aktuellen Branch gelöscht wurden und
  3. in keinem bekannten Branch (lokal oder origin/*) aktuell existieren.
Admin-Dateien, die nur fehlen, aber nie gelöscht wurden, werden bloß aufgelistet.

Aufruf:  python3 3d-druck/src/dateien_abgleich.py [--trocken] [--loeschen]

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
LOESCHEN = "--loeschen" in sys.argv


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


def git(*args):
    r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def repo_prefix():
    """Pfad von 3d-druck/ relativ zur Repository-Wurzel, z. B. '3d-druck/'."""
    return git("rev-parse", "--show-prefix").strip()


def in_historie_geloescht():
    """Pfade (relativ zu 3d-druck/), die in der Historie von HEAD gelöscht wurden."""
    pre = repo_prefix()
    out = git("log", "--diff-filter=D", "--name-only", "--pretty=format:", "HEAD", "--", ".")
    return {l[len(pre):] for l in out.splitlines() if l.startswith(pre)}


def in_branches_vorhanden():
    """Pfade (relativ zu 3d-druck/), die an der Spitze irgendeines bekannten Branches existieren."""
    pre = repo_prefix()
    vorhanden = set()
    for ref in git("for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes").split():
        if ref.endswith("/HEAD"):
            continue
        out = git("ls-tree", "-r", "--name-only", ref, "--", pre or ".")
        vorhanden |= {l[len(pre):] for l in out.splitlines() if l.startswith(pre)}
    return vorhanden


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
    fehlend = [m for pfad, m in remote.items() if pfad not in local]
    weg = []
    if LOESCHEN and fehlend:
        geloescht = in_historie_geloescht()
        vorhanden = in_branches_vorhanden()
        for m in fehlend:
            if m["pfad"] in geloescht and m["pfad"] not in vorhanden:
                weg.append(m)
    behalten = [m for m in fehlend if m not in weg]
    if behalten:
        grund = "nicht in der Git-Historie gelöscht oder in anderem Branch vorhanden" if LOESCHEN \
            else "Löschen nur mit --loeschen"
        print(f"· {len(behalten)} Admin-Datei(en) fehlen lokal und bleiben erhalten ({grund}):")
        for m in behalten:
            print(f"    {m['pfad']}")
    for m in weg:
        print(f"✕ {m['pfad']} (im Repository gelöscht)")
        if not DRY:
            curl(["-X", "DELETE", BASE + "datei?" + urllib.parse.urlencode({"quelle": "claude", "id": m["id"]})])
    print(f"Fertig: {neu} hochgeladen, {gleich} unverändert, {len(weg)} entfernt, "
          f"{len(behalten)} behalten{' (Probelauf)' if DRY else ''}.")


if __name__ == "__main__":
    main()
