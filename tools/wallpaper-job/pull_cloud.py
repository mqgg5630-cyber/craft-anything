#!/usr/bin/env python3
"""Pull cloud-delivered bundles onto the repository disk.

Reads a JSON manifest of one-time download URLs (Dropbox temporary links,
Google Drive alt-media links, ...) and materialises each bundle as a browsable
folder under `deliveries/`. Zip bundles are extracted, never kept as the only
copy, because the delivery policy is "every result must be a navigable folder".

Manifest shape:

    [
      {"url": "https://...", "dest": "deliveries/rainy-note/02-复刻无手机UI",
       "unzip": true, "flatten": false},
      {"url": "https://...", "dest": "deliveries/x/说明.md", "unzip": false}
    ]

`flatten` strips the archive's top-level directory so files land directly in
`dest` (useful when the zip wraps everything in one folder whose name we do not
want). The manifest is passed via env var CLOUD_MANIFEST_JSON so the URLs never
live in the repository.
"""

from __future__ import annotations

import io
import json
import os
import pathlib
import shutil
import sys
import tempfile
import urllib.request
import zipfile

REPO = pathlib.Path(__file__).resolve().parents[2]
UA = "Mozilla/5.0 (X11; Linux x86_64) craft-anything-delivery/1.0"


def download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as resp:  # noqa: S310
        return resp.read()


def safe_extract(archive: zipfile.ZipFile, target: pathlib.Path, flatten: bool) -> int:
    target.mkdir(parents=True, exist_ok=True)
    names = [n for n in archive.namelist() if not n.endswith("/")]
    prefix = ""
    if flatten and names:
        tops = {n.split("/", 1)[0] for n in names}
        if len(tops) == 1 and all("/" in n for n in names):
            prefix = tops.pop() + "/"
    written = 0
    for name in names:
        rel = name[len(prefix):] if prefix and name.startswith(prefix) else name
        if not rel:
            continue
        dest = (target / rel).resolve()
        if not str(dest).startswith(str(target.resolve())):
            raise RuntimeError(f"unsafe path in archive: {name}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(name) as src, dest.open("wb") as out:
            shutil.copyfileobj(src, out)
        written += 1
    return written


def handle(entry: dict) -> str:
    url = entry["url"]
    dest = (REPO / entry["dest"]).resolve()
    if not str(dest).startswith(str(REPO)):
        raise RuntimeError(f"dest escapes repo: {entry['dest']}")
    blob = download(url)
    if entry.get("unzip"):
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            count = safe_extract(archive, dest, bool(entry.get("flatten")))
        return f"{entry['dest']}: {len(blob)} bytes -> {count} files"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(blob)
    return f"{entry['dest']}: {len(blob)} bytes -> 1 file"


def main() -> int:
    raw = os.environ.get("CLOUD_MANIFEST_JSON", "").strip()
    if not raw:
        print("CLOUD_MANIFEST_JSON is empty", file=sys.stderr)
        return 2
    manifest = json.loads(raw)
    failed = 0
    for entry in manifest:
        try:
            print(handle(entry))
        except Exception as exc:  # noqa: BLE001 - report every bundle, keep going
            failed += 1
            print(f"FAILED {entry['dest']}: {exc}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
