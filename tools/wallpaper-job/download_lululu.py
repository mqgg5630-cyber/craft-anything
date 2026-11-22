"""Public Xiaohongshu note downloader for the '和你一起奔夕阳 噜噜噜妹壁纸' note.

Runs only on the GitHub Actions runner (never locally). No credentials/cookies:
it resolves the share URL and reads ``window.__INITIAL_STATE__`` from the public
note page. If the share link lands on a login wall (common on rednote.com for
anonymous runners), it recovers the note id and xsec share token from the login
redirect and retries the canonical xiaohongshu.com explore/discovery URLs, which
usually serve anonymous viewers when the share token is supplied. Every image URL
in the note's ``imageList`` is passed through the bounded ``fetch`` validator from
``download.py``; the largest valid file wins and is written byte-for-byte.

A ``download-debug.json`` is always written describing exactly what the runner
observed (final URL, page size, whether ``__INITIAL_STATE__`` was found, recovered
note id / xsec token, per-candidate image-list lengths), so a failed run can be
diagnosed from the committed file without touching the images locally.
"""
import hashlib
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from PIL import Image
from download import fetch

ROOT = Path('deliveries/lululu-sunset')
SHARE_URL = 'https://xhslink.cn/o/5thkO8Kd6jg'
NOTE_TITLE = '和你一起奔夕阳 噜噜噜妹壁纸'
JOB_CAP = 75 * 1024 * 1024
HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/124.0 Safari/537.36'),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://www.xiaohongshu.com/',
}


def _decode(text):
    out = text or ''
    for _ in range(3):
        new = urllib.parse.unquote(out)
        if new == out:
            break
        out = new
    return out


def parse_initial_state(html):
    match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(.*?)</script>', html, re.S)
    if not match:
        return None
    raw = match.group(1).strip().rstrip(';')
    raw = re.sub(r'\bundefined\b', 'null', raw)
    try:
        return json.loads(raw)
    except ValueError:
        return None


def iter_image_lists(node, found):
    """Recursively collect every non-empty 'imageList' list found in the state."""
    if isinstance(node, dict):
        value = node.get('imageList')
        if isinstance(value, list) and value:
            found.append(value)
        for child in node.values():
            iter_image_lists(child, found)
    elif isinstance(node, list):
        for child in node:
            iter_image_lists(child, found)


def extract_note_id(value):
    value = _decode(value)
    for pattern in (r'/(?:explore|discovery/item|item)/([0-9a-zA-Z]+)',
                   r'[?&]note_id=([0-9a-zA-Z]+)'):
        match = re.search(pattern, value)
        if match:
            return match.group(1)
    return None


def extract_xsec_token(value):
    value = _decode(value)
    match = re.search(r'[?&]xsec_token=([^&]+)', value)
    if match:
        return _decode(match.group(1))
    return None


def fetch_page(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=35) as response:
        return response.read(8 * 1024 * 1024).decode('utf-8', 'replace'), response.geturl()


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


def write_debug(debug):
    (ROOT / 'download-debug.json').write_text(
        json.dumps(debug, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    folder = ROOT / '01-下载原片'
    folder.mkdir(parents=True, exist_ok=True)
    debug = {'share_url': SHARE_URL, 'status': 'start'}

    html = None
    final_url = None
    try:
        html, final_url = fetch_page(SHARE_URL)
    except (OSError, ValueError) as exc:
        debug.update(status='page_fetch_failed', error=f'{type(exc).__name__}: {exc}')
        write_debug(debug)
        raise RuntimeError(f'Public page fetch failed: {exc}')

    debug['final_url'] = final_url
    debug['page_bytes'] = len(html)
    debug['has_initial_state'] = 'window.__INITIAL_STATE__' in html

    state = parse_initial_state(html)
    image_lists = []
    if state is not None:
        iter_image_lists(state, image_lists)
    debug['initial_state_parsed'] = state is not None
    debug['image_list_count'] = len(image_lists)
    try:
        note_ids = list((state or {}).get('note', {}).get('noteDetailMap', {}).keys())
    except (AttributeError, TypeError):
        note_ids = []
    debug['note_ids'] = note_ids
    attempts = [{'url': SHARE_URL, 'final_url': final_url, 'image_list_count': len(image_lists)}]

    # Recover from a login wall. xhslink sometimes bounces anonymous runners to
    # rednote.com/login; the note id and xsec share token survive in that
    # redirect (often URL-encoded), so retry the canonical xiaohongshu.com pages
    # which usually serve anonymous viewers when the share token is supplied.
    if not image_lists:
        note_id = extract_note_id(final_url) or extract_note_id(SHARE_URL) or extract_note_id(html)
        xsec = extract_xsec_token(final_url) or extract_xsec_token(html)
        debug['recovered_note_id'] = note_id
        debug['recovered_xsec_token'] = bool(xsec)
        candidates = []
        if note_id:
            for host in ('www.xiaohongshu.com', 'www.rednote.com'):
                for path in (f'explore/{note_id}', f'discovery/item/{note_id}'):
                    base = f'https://{host}/{path}'
                    if xsec:
                        candidates.append(
                            f'{base}?xsec_token={urllib.parse.quote(xsec, safe="")}&xsec_source=app_share')
                    candidates.append(base)
        for candidate in candidates:
            try:
                page, furl = fetch_page(candidate)
                st = parse_initial_state(page)
                found = []
                if st is not None:
                    iter_image_lists(st, found)
                attempts.append({'url': candidate, 'final_url': furl,
                                 'has_initial_state': st is not None,
                                 'image_list_count': len(found)})
                if found:
                    html, final_url, state, image_lists = page, furl, st, found
                    break
            except (OSError, ValueError) as exc:
                attempts.append({'url': candidate, 'error': f'{type(exc).__name__}: {exc}'})
    debug['attempts'] = attempts
    write_debug(debug)

    images = image_lists[0] if image_lists else None
    if not images:
        # Fallback: a previously committed source-manifest.json of candidate URLs.
        manifest_path = ROOT / 'source-manifest.json'
        if manifest_path.exists():
            urls = json.loads(manifest_path.read_text()).get('image_urls', [])
            images = [{'urlDefault': u} for u in urls]
        if not images:
            debug['status'] = 'no_image_list'
            write_debug(debug)
            raise RuntimeError('Could not read note imageList and no committed source-manifest.json fallback')

    note_id = (debug.get('note_ids') or [debug.get('recovered_note_id') or ''])[0]
    print(f'Note {note_id or "?"}: {len(images)} images', flush=True)

    records = []
    total = 0
    for index, image in enumerate(images, 1):
        candidates = candidate_urls(image)
        valid = []
        for url in candidates:
            try:
                data, width, height, fmt = fetch(url)
                valid.append((width * height, len(data), data, width, height, fmt, url))
            except (OSError, ValueError, Image.DecompressionBombError):
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
        'title': NOTE_TITLE,
        'author': '',
        'source_caveat': 'Public CDN files; not independently verified as author master files.',
        'download_method': 'GitHub Actions runner, bounded fetch validator, no cookies',
        'image_count': len(records),
        'images': records,
    }
    (folder / '下载记录.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    debug.update(status='downloaded', image_count=len(records))
    write_debug(debug)
    print(f'Wrote {len(records)} verified images and manifest to {folder}', flush=True)


if __name__ == '__main__':
    main()
