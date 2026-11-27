"""Actions-only public note carousel downloader for autumn-swing (C5WkFiFa1r).

Uses exact public carousel URL(s) parsed from the public note page, with optional
public initial-state refresh on the Actions runner. Never uses cookies, login
sessions, credentials, guessed tokens, or forged signatures. Fully decodes every
downloaded image before writing to source/.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.request
from urllib.parse import urlparse

from PIL import Image
from download import fetch

ROOT = Path('deliveries/autumn-swing-C5WkFiFa1r')
SHARE_URL = 'https://xhslink.cn/o/C5WkFiFa1r'
NOTE_ID = '6abdb5a9000000001802f193'
ALLOWED_DOMAINS = ('rednotecdn.com', 'xhscdn.com', 'xiaohongshu.com')
PAGE_CAP = 8 * 1024 * 1024
TOTAL_CAP = 60 * 1024 * 1024


def is_allowed_public_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.username or parsed.password or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    return any(host == d or host.endswith('.' + d) for d in ALLOWED_DOMAINS)


def full_decode_metadata(data: bytes, expected_w: int, expected_h: int, expected_fmt: str) -> dict:
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        width, height = image.size
        fmt = (image.format or '').lower()
    if (width, height) != (expected_w, expected_h) or fmt != expected_fmt:
        raise ValueError('Decoded image metadata mismatch')
    if min(width, height) < 300 or fmt not in ('webp', 'png', 'jpeg'):
        raise ValueError('Unexpected image dimensions or format')
    return {
        'width': width,
        'height': height,
        'format': fmt,
        'bytes': len(data),
        'md5': hashlib.md5(data).hexdigest(),
        'sha256': hashlib.sha256(data).hexdigest(),
    }


def try_public_page_refresh() -> tuple[list[list[str]] | None, str]:
    try:
        req = urllib.request.Request(
            SHARE_URL,
            headers={'User-Agent': 'CraftAnything-dev', 'Referer': 'https://www.xiaohongshu.com/'},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read(PAGE_CAP + 1)
        if len(raw) > PAGE_CAP:
            return None, 'page_exceeded_cap_used_seed_urls'
        html = raw.decode('utf-8', errors='replace')
        match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(.*?)</script>', html, re.S)
        if not match:
            return None, 'no_public_initial_state_used_seed_urls'
        state = json.loads(re.sub(r'\bundefined\b', 'null', match.group(1).strip().rstrip(';')))
        details = state.get('note', {}).get('noteDetailMap', {})
        for entry in details.values():
            note = entry.get('note', {})
            if note.get('noteId') != NOTE_ID:
                continue
            image_list = note.get('imageList') or []
            if not image_list:
                continue
            grouped: list[list[str]] = []
            for item in image_list:
                cands = [item.get('urlDefault', '')] + [
                    info.get('url', '') for info in (item.get('infoList') or [])
                ]
                cleaned = list(dict.fromkeys(u for u in cands if is_allowed_public_url(u)))
                if cleaned:
                    grouped.append(cleaned)
            if grouped:
                return grouped, 'refreshed_from_public_initial_state'
        return None, 'note_not_in_public_state_used_seed_urls'
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return None, f'refresh_unavailable_{type(exc).__name__}_used_seed_urls'


def main() -> None:
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('Public CDN download is allowed only on GitHub Actions')
    seed = json.loads((ROOT / 'source-seed.json').read_text(encoding='utf-8'))
    if seed.get('share_url') != SHARE_URL or seed.get('note_id') != NOTE_ID:
        raise ValueError('Seed share_url or note_id mismatch')
    seed_urls = seed.get('carousel_urls') or []
    if not seed_urls or not all(is_allowed_public_url(u) for u in seed_urls):
        raise ValueError('Seed carousel_urls missing or invalid')

    refreshed_groups, refresh_status = try_public_page_refresh()
    if refreshed_groups is not None and len(refreshed_groups) == len(seed_urls):
        candidate_groups = [
            list(dict.fromkeys(group + [seed_u]))
            for group, seed_u in zip(refreshed_groups, seed_urls)
        ]
    else:
        candidate_groups = [[u] for u in seed_urls]

    records = []
    seen_hashes: set[str] = set()
    total_bytes = 0

    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp)
        for index, candidates in enumerate(candidate_groups, 1):
            valid = []
            for url in candidates:
                if not is_allowed_public_url(url):
                    raise ValueError('Disallowed candidate URL')
                try:
                    data, w, h, fmt = fetch(url)
                    meta = full_decode_metadata(data, w, h, fmt)
                    valid.append((w * h, len(data), data, meta, url))
                except (OSError, ValueError) as exc:
                    print(f'Item {index}: one public candidate unavailable ({type(exc).__name__})', flush=True)
            if not valid:
                raise RuntimeError(f'No decodable public image for carousel item {index}')
            _, _, data, meta, chosen_url = max(valid, key=lambda item: (item[0], item[1]))
            if meta['sha256'] in seen_hashes:
                continue
            seen_hashes.add(meta['sha256'])
            total_bytes += len(data)
            if total_bytes > TOTAL_CAP:
                raise ValueError('Combined source files exceed 60 MiB cap')
            ext = 'jpg' if meta['format'] == 'jpeg' else meta['format']
            filename = f'{len(records) + 1:02d}.{ext}'
            (stage / filename).write_bytes(data)
            records.append({
                'index': len(records) + 1,
                'file': f'source/{filename}',
                'source_url': chosen_url,
                **meta,
            })
            print(f'{filename}: {meta["width"]}x{meta["height"]} {meta["format"]} ({meta["bytes"]} bytes)', flush=True)

        if not records:
            raise RuntimeError('Zero verified source images staged')

        dest = ROOT / 'source'
        for staged_file in stage.iterdir():
            target = dest / staged_file.name
            if target.exists() and target.read_bytes() != staged_file.read_bytes():
                raise RuntimeError(f'Refusing to overwrite different existing source file: {staged_file.name}')
        if dest.exists():
            extra = {p.name for p in dest.iterdir()} - {p.name for p in stage.iterdir()}
            if extra:
                raise RuntimeError('Unexpected extra files in destination source/')
        dest.mkdir(parents=True, exist_ok=True)
        for staged_file in sorted(stage.iterdir()):
            (dest / staged_file.name).write_bytes(staged_file.read_bytes())

    manifest = {
        'schema_version': 2,
        'share_url': SHARE_URL,
        'resolved_note_url': seed.get('resolved_note_url'),
        'note_id': NOTE_ID,
        'title': seed.get('title'),
        'author': seed.get('author'),
        'tags': seed.get('tags', []),
        'carousel_dedup_note': seed.get('carousel_dedup_note'),
        'status': 'downloaded_pending_visual_review',
        'run_id': os.environ.get('GITHUB_RUN_ID'),
        'branch': os.environ.get('GITHUB_REF_NAME'),
        'page_refresh': refresh_status,
        'download_method': 'GitHub Actions runner; verified public CDN URLs with bounded full Pillow decode',
        'source_quality': 'Public web CDN display image; not independently verified as author master file',
        'reference_count_downloaded': len(records),
        'images': records,
    }
    (ROOT / 'source-manifest.json').write_bytes(
        (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    )
    (ROOT / 'download-status.json').write_bytes(
        (json.dumps({
            'status': 'downloaded_pending_visual_review',
            'run_id': os.environ.get('GITHUB_RUN_ID'),
            'branch': os.environ.get('GITHUB_REF_NAME'),
            'images_verified': True,
            'count': len(records),
        }, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    )


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            ROOT.mkdir(parents=True, exist_ok=True)
            (ROOT / 'download-status.json').write_bytes(
                (json.dumps({
                    'status': 'blocked_source_download',
                    'error_type': type(exc).__name__,
                    'error': str(exc),
                    'run_id': os.environ.get('GITHUB_RUN_ID'),
                    'share_url': SHARE_URL,
                    'images_verified': False,
                }, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
            )
        raise
