"""Public Xiaohongshu note downloader for the '和你一起奔夕阳 噜噜噜妹壁纸' note.

Runs only on the GitHub Actions runner (never locally). No credentials/cookies:
it resolves the share URL, reads ``window.__INITIAL_STATE__`` from the public note
page, lists every image in the note's ``imageList`` (searching recursively so
alternate JSON shapes are tolerated), and for each image tries every public CDN
candidate URL (``urlDefault`` + ``infoList`` variants). Each candidate is passed
through the bounded ``fetch`` validator from ``download.py`` (decodes, checks
dimensions, caps size). The largest valid file wins and is written byte-for-byte,
with dimensions, byte size and hashes recorded.

A ``download-debug.json`` is always written to the delivery root describing exactly
what the runner observed (final URL, page size, whether ``__INITIAL_STATE__`` was
found, note ids, per-note imageList lengths). This lets a failed run be diagnosed
from the committed file without touching the images locally.
"""
import hashlib
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from download import fetch

ROOT = Path('deliveries/lululu-sunset')
SHARE_URL = 'https://xhslink.cn/o/5thkO8Kd6jg'
NOTE_TITLE = '和你一起奔夕阳 噜噜噜妹壁纸'
JOB_CAP = 75 * 1024 * 1024
HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/124.0 Safari/537.36'),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://www.xiaohongshu.com/',
}


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


def extract_note_id(url):
    match = re.search(r'/(?:explore|discovery/item|item)/([0-9a-zA-Z]+)', url or '')
    return match.group(1) if match else None


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
    debug['html_head'] = html[:400]

    state = parse_initial_state(html)
    image_lists = []
    if state is not None:
        iter_image_lists(state, image_lists)
    debug['initial_state_parsed'] = state is not None
    debug['image_list_count'] = len(image_lists)
    note_ids = []
    try:
        note_ids = list((state or {}).get('note', {}).get('noteDetailMap', {}).keys())
    except (AttributeError, TypeError):
        pass
    debug['note_ids'] = note_ids
    attempts = [{'url': SHARE_URL, 'final_url': final_url, 'image_list_count': len(image_lists)}]

    # If the share link hit a login wall (common on the international rednote.com
    # domain) or returned no images, retry the CN xiaohongshu.com explore/discovery
    # URLs directly. Still fully cookie-less; this just tries the canonical public
    # page that often serves anonymous viewers.
    if not image_lists and 'login' in (final_url or '').lower():
        # The note id lives in a URL-encoded redirectPath query parameter.
        parsed = urllib.parse.urlparse(final_url)
        redirect = urllib.parse.unquote(urllib.parse.parse_qs(parsed.query).get('redirectPath', [''])[0])
        note_id = extract_note_id(redirect) or extract_note_id(urllib.parse.unquote(SHARE_URL))
        xsec = ''
        m = re.search(r'xsec_token=([^&]+)', redirect)
        if m:
            xsec = urllib.parse.unquote(m.group(1))
        candidates = []
        if note_id:
            explore = f'https://www.xiaohongshu.com/explore/{note_id}'
            if xsec:
                explore += f'?xsec_token={urllib.parse.quote(xsec, safe="")}&xsec_source=app_share'
            candidates.append(explore)
            candidates.append(f'https://www.xiaohongshu.com/discovery/item/{note_id}')
        for candidate in candidates:
            try:
                page, furl = fetch_page(candidate)
                st = parse_initial_state(page)
                found = []
                if st is not None:
                    iter_image_lists(st, found)
                attempts.append({'url': candidate, 'final_url': furl, 'image_list_count': len(found)})
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

    note_id = (debug.get('note_ids') or [''])[0]
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
