#!/usr/bin/env python3
"""
Download the ORIGINAL wallpaper images from the Xiaohongshu/rednote post
"✨小王子系列壁纸 🌌深蓝夜空款" and verify them.

This is meant to run inside a GitHub Actions runner (which has real outbound
internet). It cannot run in the craft-anything sandbox because that environment
blocks external CDNs.

Strategy:
  1. Discover current (freshly signed) image URLs by fetching the public note
     page HTML and scraping rednotecdn / xhscdn `notes_pre_post` URLs.
  2. Fall back to a few known URLs captured from the post.
  3. Download each candidate, skip non-images / tiny files, verify it is a real
     image with sane dimensions, and save into ./original.
  4. Write a manifest.json and exit non-zero if nothing valid was downloaded
     (so the workflow will NOT push garbage).
"""
import os
import sys
import re
import json
import html
import urllib.request
import urllib.error

OUT_DIR = "original"
MIN_BYTES = 20000  # ignore placeholders / error pages

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.rednote.com/",
    "Accept": "image/avif,image/webp,image/apng,image/png,image/*,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# Public share note for the post (deep-blue night-sky Little Prince wallpapers).
NOTE_URL = (
    "https://www.rednote.com/discovery/item/6ae4c02f000000001b01ef9b"
    "?share_from_user_hidden=true&xsec_source=app_share&type=normal"
    "&xsec_token=CBIGZMm-B9V_VnP1EsAsglq-DNwRAzgylsDMilorirbco="
    "&author_share=1&shareRedId=ODc1MzpJOTw2NzUyOTgwNjY1OTk3SjxK"
    "&apptime=1795332028&track_code=8AL0Drxsydk"
)
XHSLINK_URL = "https://xhslink.cn/o/8AL0Drxsydk"

# Known image URLs captured from the post (used as fallback only).
KNOWN_URLS = [
    "https://sns-web-i10.rednotecdn.com/202611221549/7e088999dcc90b2f484241f7e8fb97c0/notes_pre_post/1040g3k8326v1e3nfma905plljionc98jba6ikgg!nd_dft_wlteh_webp_3",
    "https://sns-web-i10.rednotecdn.com/202611221549/08de45d6d3454eca16a6c9bf8848b299/notes_pre_post/1040g3k8326v1e3nfma805plljionc98j70sso6g!nd_dft_wlteh_webp_3",
    "https://sns-web-i10.rednotecdn.com/202611221549/b1112cd2b03ad842543cc9a2ba2c1e11/notes_pre_post/1040g3k8326v1e3nfma8g5plljionc98j61jvfv8!nd_dft_wlteh_webp_3",
]


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def discover_urls():
    found = []
    for page_url in (NOTE_URL, XHSLINK_URL):
        try:
            raw = fetch(page_url).decode("utf-8", "ignore")
        except Exception as e:  # noqa: BLE001
            print(f"[discover] could not fetch {page_url}: {e}")
            continue
        raw = html.unescape(raw).replace("\\/", "/")
        pats = [
            r"https://[^\s\"'\\]+rednotecdn\.com/[^\s\"'\\]*notes_pre_post[^\s\"'\\]*",
            r"https://[^\s\"'\\]+xhscdn\.com/[^\s\"'\\]*notes_pre_post[^\s\"'\\]*",
        ]
        for pat in pats:
            for m in re.findall(pat, raw):
                m = m.rstrip(")")
                if m not in found:
                    found.append(m)
    return found


def ext_for(data):
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None


def verify(path):
    """Return (width, height) if valid, else raise."""
    try:
        from PIL import Image
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"Pillow unavailable: {e}")
    with Image.open(path) as im:
        im.verify()  # raises if corrupt
    with Image.open(path) as im:
        return im.size


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    urls = []
    for u in discover_urls() + list(KNOWN_URLS):
        if u not in urls:
            urls.append(u)
    print(f"[info] candidate image URLs: {len(urls)}")
    for u in urls:
        print("  -", u)

    ok = 0
    saved = []
    for i, url in enumerate(urls, 1):
        try:
            data = fetch(url)
        except urllib.error.HTTPError as e:
            print(f"[{i}] HTTP {e.code} for {url}")
            continue
        except Exception as e:  # noqa: BLE001
            print(f"[{i}] download error {url}: {e}")
            continue
        if len(data) < MIN_BYTES:
            print(f"[{i}] skip too small ({len(data)} bytes): {url}")
            continue
        ext = ext_for(data)
        if ext is None:
            print(f"[{i}] skip unknown magic ({len(data)} bytes): {url}")
            continue
        fname = os.path.join(OUT_DIR, f"original_{i:02d}{ext}")
        with open(fname, "wb") as f:
            f.write(data)
        try:
            w, h = verify(fname)
        except Exception as e:  # noqa: BLE001
            print(f"[{i}] verify FAILED {fname}: {e}")
            os.remove(fname)
            continue
        print(f"[{i}] OK  {fname}  {w}x{h}  {len(data)} bytes")
        ok += 1
        saved.append(fname)

    manifest = {
        "count": ok,
        "files": saved,
        "source_note": NOTE_URL,
    }
    with open(os.path.join(OUT_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    if ok == 0:
        print("\n[result] No valid original images were downloaded. "
              "Not committing anything.")
        sys.exit(1)
    print(f"\n[result] Downloaded and verified {ok} original image(s).")
    sys.exit(0)


if __name__ == "__main__":
    main()
