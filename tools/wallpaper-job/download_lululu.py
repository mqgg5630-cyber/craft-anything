"""Public Xiaohongshu note downloader for the '和你一起奔夕阳 噜噜噜妹壁纸' note.

Runs only on the GitHub Actions runner (never locally). No credentials/cookies:
it resolves the share URL, reads ``window.__INITIAL_STATE__`` from the public note
page, lists every image in the note's ``imageList``, and for each image tries every
public CDN candidate URL (``urlDefault`` + ``infoList`` variants). Each candidate is
passed through the bounded ``fetch`` validator from ``download.py`` (decodes, checks
dimensions, caps size). The largest valid file wins and is written byte-for-byte, with
dimensions, byte size and hashes recorded.

This mirrors the proven little-prince / blue-kitty downloaders: it reuses the shared
validator, refuses to overwrite a different file, and never claims success when no
validated image is available for an item.
"""
import hashlib
import json
import re
import urllib.request
from pathlib import Path
from download import fetch

ROOT = Path('deliveries/lululu-sunset')
SHARE_URL = 'https://xhslink.cn/o/5thkO8Kd6jg'
NOTE_TITLE = '和你一起奔夕阳 噜噜噜妹壁纸'
JOB_CAP = 75 * 1024 * 1024


def parse_initial_state(html):
    match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(.*?)</script>', html, re.S)
    if not match:
        raise RuntimeError('window.__INITIAL_STATE__ not found in public note page')
    raw = match.group(1).strip().rstrip(';')
    raw = re.sub(r'\bundefined\b', 'null', raw)
    return json.loads(raw)


def candidate_urls(image):
    urls = []
    for key in ('urlDefault', 'urlPre', 'urlMiddle', 'url'):
        value = image.get(key)
        if isinstance(value, str) and value.startswith('https://'):
            urls.append(value)
    for info in image.get('infoList', []) or []:
        url = info.get('url')
        if isinstance(url, str) and url.startswith('https://'):
            urls.append(url)
    seen = set()
    ordered = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            ordered.append(url)
    return ordered


def first_note_with_images(state):
    details = state.get('note', {}).get('noteDetailMap', {}) or {}
    for detail in details.values():
        note = detail.get('note', {}) or {}
        if note.get('imageList'):
            return note
    return None


def main():
    folder = ROOT / '01-下载原片'
    folder.mkdir(parents=True, exist_ok=True)
    # Resolve the short link to the note page on the runner (full internet access).
    # A transient page-read failure must not hard-fail the job: fall back to a
    # previously committed source-manifest.json of candidate URLs when present.
    images = None
    try:
        req = urllib.request.Request(SHARE_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=35) as response:
            html = response.read(8 * 1024 * 1024).decode('utf-8', 'replace')
        note = first_note_with_images(parse_initial_state(html))
        if note is not None:
            images = note.get('imageList', [])
    except (OSError, ValueError) as exc:
        print('Public page read unavailable:', type(exc).__name__, flush=True)
    if not images:
        manifest_path = ROOT / 'source-manifest.json'
        if manifest_path.exists():
            images = [{'urlDefault': url} for url in
                      json.loads(manifest_path.read_text()).get('image_urls', [])]
    if not images:
        raise RuntimeError('Could not read note imageList and no committed source-manifest.json fallback')
    note_id = note.get('noteId', '')
    title = note.get('title') or NOTE_TITLE
    author = (note.get('user') or {}).get('nickname', '')
    print(f'Note {note_id}: {len(images)} images, author={author!r}, title={title!r}', flush=True)

    records = []
    total = 0
    for index, image in enumerate(images, 1):
        candidates = candidate_urls(image)
        valid = []
        for url in candidates:
            try:
                data, width, height, fmt = fetch(url)
                valid.append((width * height, len(data), data, width, height, fmt, url))
            except (OSError, ValueError):
                print(f'Image {index}: one candidate unavailable', flush=True)
        if not valid:
            raise RuntimeError(f'No validated public image for item {index}')
        _, _, data, width, height, fmt, url = max(valid, key=lambda item: (item[0], item[1]))
        total += len(data)
        if total > JOB_CAP:
            raise ValueError('Combined source files exceed 75 MiB cap')
        name = f'{index:02d}.{fmt}'
        path = folder / name
        if path.exists() and path.read_bytes() != data:
            raise RuntimeError(f'Refusing to overwrite different source: {name}')
        path.write_bytes(data)
        records.append({'file': name, 'width': width, 'height': height, 'bytes': len(data),
                        'md5': hashlib.md5(data).hexdigest(),
                        'sha256': hashlib.sha256(data).hexdigest(), 'source_url': url})
        print(f'Image {index}: {width}x{height}, {len(data)} bytes', flush=True)

    manifest = {
        'schema_version': 1,
        'status': 'downloaded_pending_visual_review',
        'share_url': SHARE_URL,
        'note_id': note_id,
        'title': title,
        'author': author,
        'source_caveat': 'Public CDN files; not independently verified as author master files.',
        'download_method': 'GitHub Actions runner, bounded fetch validator, no cookies',
        'image_count': len(records),
        'images': records,
    }
    (folder / '下载记录.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {len(records)} verified images and manifest to {folder}', flush=True)


if __name__ == '__main__':
    main()
