#!/usr/bin/env python3
"""Fetch a public Xiaohongshu note on a GitHub-hosted runner and encrypt its images."""
from __future__ import annotations

import base64
import hashlib
import html
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from PIL import Image, UnidentifiedImageError
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parents[2]
REQUEST = ROOT / "tools/xhs-wallpaper/request.enc"
RUNNER_PUBLIC = ROOT / "tools/xhs-wallpaper/runner-public.pem"
RESULT_PUBLIC = ROOT / "tools/xhs-wallpaper/result-public.pem"
MAX_IMAGE_BYTES = 35 * 1024 * 1024
MAX_NOTE_BYTES = 12 * 1024 * 1024
CURRENT_PHASE = "startup"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def safe_note_id(url: str) -> str:
    match = re.search(r"(?:item|explore)/([0-9a-f]{24})", url, re.I)
    return match.group(1) if match else "note"


def unescape_js_string(value: str) -> str:
    value = value.replace("\\u002F", "/").replace("\\u0026", "&").replace("\\/", "/")
    try:
        return json.loads('"' + value.replace('"', '\\"') + '"')
    except (json.JSONDecodeError, ValueError):
        return html.unescape(value)


def image_urls_from_html(page: str) -> list[str]:
    """Extract only note-image fields, not avatars or unrelated page assets."""
    normalized = page.replace("\\u002F", "/").replace("\\/", "/").replace("\\u0026", "&")
    state_start = normalized.find("window.__INITIAL_STATE__")
    state = normalized[state_start:] if state_start >= 0 else normalized
    # urlDefault/urlPre live in imageList entries in the note detail state. Repeated
    # occurrences are deduplicated by the content token below.
    candidates: list[str] = []
    for match in re.finditer(r'"(?:urlDefault|urlPre)"\s*:\s*"((?:\\.|[^"\\])+)"', state):
        value = unescape_js_string(match.group(1))
        if value.startswith("//"):
            value = "https:" + value
        if value.startswith("https://") and any(host in value for host in (
            "rednotecdn.com", "xhscdn.com", "xiaohongshu.com"
        )):
            candidates.append(value)
    seen: set[str] = set()
    result: list[str] = []
    for value in candidates:
        token = image_token(value)
        if token and token not in seen:
            seen.add(token)
            result.append(value)
    return result


def image_token(url: str) -> str:
    path = unquote(urlparse(url).path).strip("/")
    path = path.split("!", 1)[0]
    parts = [part for part in path.split("/") if part]
    for marker in ("spectrum", "notes_pre_post"):
        if marker in parts:
            return "/".join(parts[parts.index(marker):])
    return parts[-1] if parts else ""


def image_candidates(display_url: str) -> list[str]:
    token = image_token(display_url)
    if not token:
        return [display_url]
    candidates = [display_url]
    raw_tokens = [token]
    if "/" not in token:
        raw_tokens.extend((f"spectrum/{token}", f"notes_pre_post/{token}"))
    for item in dict.fromkeys(raw_tokens):
        candidates.extend((
            f"https://sns-img-bd.xhscdn.com/{item}",
            f"https://sns-img-hw.xhscdn.com/{item}",
            f"https://ci.xiaohongshu.com/{item}?imageView2/format/png",
            f"https://ci.xiaohongshu.com/{item}?imageView2/format/jpeg",
        ))
    return list(dict.fromkeys(candidates))


def read_limited(response: requests.Response, limit: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    for block in response.iter_content(128 * 1024):
        if not block:
            continue
        size += len(block)
        if size > limit:
            raise ValueError("response exceeds configured size limit")
        chunks.append(block)
    return b"".join(chunks)


def valid_image(data: bytes) -> tuple[int, int, str] | None:
    try:
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            if width <= 0 or height <= 0 or width * height > 100_000_000:
                return None
            image.verify()
            return width, height, (image.format or "JPEG").lower()
    except (UnidentifiedImageError, OSError, ValueError):
        return None


def get_note_html(url: str) -> tuple[str, str, int]:
    response = requests.get(
        url,
        headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7"},
        timeout=(15, 45),
        allow_redirects=True,
    )
    response.raise_for_status()
    if len(response.content) > MAX_NOTE_BYTES:
        raise ValueError("note page exceeds configured size limit")
    return response.text, response.url, response.status_code


def fetch_image(url: str, session: requests.Session) -> tuple[bytes, tuple[int, int, str], str] | None:
    headers = {"User-Agent": UA, "Referer": "https://www.xiaohongshu.com/"}
    for candidate in image_candidates(url):
        try:
            response = session.get(candidate, headers=headers, timeout=(15, 50), stream=True)
            if response.status_code != 200:
                response.close()
                continue
            data = read_limited(response, MAX_IMAGE_BYTES)
            response.close()
            shape = valid_image(data)
            if shape:
                return data, shape, candidate.split("?", 1)[0].split("/")[2]
        except (requests.RequestException, ValueError):
            continue
    return None


def safe_title(page: str) -> str:
    patterns = (
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title',
    )
    for pattern in patterns:
        match = re.search(pattern, page, re.I)
        if match:
            return html.unescape(match.group(1)).strip()[:180]
    return "小红书笔记"


def fetch_bundle(note_url: str, output: Path) -> int:
    global CURRENT_PHASE
    if not note_url.startswith(("https://www.xiaohongshu.com/", "https://xhslink.com/", "https://xhslink.cn/")):
        raise ValueError("unsupported Xiaohongshu URL host")
    CURRENT_PHASE = "fetch-note-page"
    page, final_url, status = get_note_html(note_url)
    CURRENT_PHASE = "parse-note-images"
    urls = image_urls_from_html(page)
    if not urls:
        raise RuntimeError("note page did not expose an imageList")
    output.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    CURRENT_PHASE = "download-source-images"
    with requests.Session() as session:
        for index, source in enumerate(urls, 1):
            saved = fetch_image(source, session)
            if not saved:
                records.append({"index": index, "downloaded": False})
                continue
            data, (width, height, fmt), host = saved
            extension = {"jpeg": "jpg", "png": "png", "webp": "webp", "gif": "gif", "avif": "avif"}.get(fmt, "img")
            name = f"{index:02d}.{extension}"
            (output / name).write_bytes(data)
            records.append({
                "index": index, "file": name, "downloaded": True,
                "bytes": len(data), "width": width, "height": height,
                "sha256": hashlib.sha256(data).hexdigest(), "source_host": host,
            })
    success = sum(1 for record in records if record.get("downloaded"))
    if success == 0:
        raise RuntimeError("no source image could be validated")
    metadata = {
        "schema_version": 1, "note_id": safe_note_id(final_url),
        "title": safe_title(page), "source_image_count": len(urls),
        "downloaded_count": success, "images": records,
    }
    (output / "note.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "README.txt").write_text(
        "Source images retrieved from the public note for personal reference. "
        "Keep originals separate from generated derivatives.\n", encoding="utf-8"
    )
    return success


def decrypt_request() -> str:
    private_path = Path(os.environ.get("XHS_RELAY_PRIVATE_KEY", ".relay/runner-private.pem"))
    if not REQUEST.is_file() or not private_path.is_file():
        raise RuntimeError("relay is not bootstrapped or request is absent")
    private = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
    plaintext = private.decrypt(
        REQUEST.read_bytes(),
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
    )
    note_url = plaintext.decode("utf-8").strip()
    if len(note_url) > 1200 or not note_url.startswith(("https://www.xiaohongshu.com/", "https://xhslink.com/", "https://xhslink.cn/")):
        raise ValueError("encrypted request did not contain a supported link")
    return note_url


def encrypt_bundle(output_dir: Path, destination: Path) -> None:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for item in sorted(output_dir.iterdir()):
            if item.is_file():
                bundle.write(item, arcname=item.name)
    key = os.urandom(32)
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, archive.getvalue(), b"xhs-wallpaper-relay-v1")
    public = serialization.load_pem_public_key(RESULT_PUBLIC.read_bytes())
    wrapped_key = public.encrypt(
        key,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
    )
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "bundle.aesgcm").write_bytes(nonce + ciphertext)
    (destination / "bundle.key.rsa").write_bytes(wrapped_key)


def main() -> int:
    global CURRENT_PHASE
    mode = sys.argv[1] if len(sys.argv) > 1 else "fetch"
    if mode == "fetch":
        CURRENT_PHASE = "decrypt-request"
        note_url = decrypt_request()
        temp = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "xhs-wallpaper-source"
        if temp.exists():
            for item in temp.iterdir():
                if item.is_file():
                    item.unlink()
        count = fetch_bundle(note_url, temp)
        metadata = json.loads((temp / "note.json").read_text(encoding="utf-8"))
        expected = int(metadata.get("source_image_count", count))
        run_id = os.environ.get("GITHUB_RUN_ID", "local")
        CURRENT_PHASE = "encrypt-source-bundle"
        encrypt_bundle(temp, ROOT / "tools/xhs-wallpaper/relay-output" / run_id)
        print(f"relay complete: {count} of {expected} source images encrypted")
        return 0
    if mode == "decrypt-local":
        if len(sys.argv) != 5:
            raise SystemExit("decrypt-local <bundle.aesgcm> <bundle.key.rsa> <private.pem> <output-dir>")
        cipher_path, wrapped_path, private_path, output_dir = map(Path, sys.argv[1:])
        private = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
        key = private.decrypt(
            wrapped_path.read_bytes(),
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
        )
        packed = cipher_path.read_bytes()
        archive = AESGCM(key).decrypt(packed[:12], packed[12:], b"xhs-wallpaper-relay-v1")
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            for item in bundle.infolist():
                if Path(item.filename).name != item.filename:
                    raise ValueError("unsafe archive path")
            bundle.extractall(output_dir)
        print("decryption complete")
        return 0
    raise SystemExit("mode must be fetch or decrypt-local")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:  # noqa: BLE001
        # Strip URLs and share tokens before writing any diagnostics to Actions or Git.
        detail = str(error)
        detail = re.sub(r"https?://\S+", "<url>", detail)
        detail = re.sub(r"xsec_token=[^&\s]+", "xsec_token=<redacted>", detail)
        if len(detail) > 180:
            detail = detail[:180]
        message = detail or type(error).__name__
        if sys.argv[1:2] == ["fetch"] and os.environ.get("GITHUB_ACTIONS") == "true":
            report = {
                "schema_version": 1,
                "phase": CURRENT_PHASE,
                "error_type": type(error).__name__,
                "detail": message,
            }
            (ROOT / "tools/xhs-wallpaper/relay-failure.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        print(f"relay failed during {CURRENT_PHASE}: {message}", file=sys.stderr)
        raise SystemExit(1)
