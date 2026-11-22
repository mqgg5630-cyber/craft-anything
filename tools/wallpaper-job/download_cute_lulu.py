"""Actions-only public source download for https://xhslink.cn/o/65mKtkE8Uk.
No cookies, login, proxies, or invented image URLs. Publish only a fully
validated carousel. Optional historical exact-URL seeds must match this share.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.parse
import urllib.request
from PIL import Image
from download import fetch

ROOT = Path('deliveries/lululu-cute-65mKtkE8Uk')
SHARE_URL = 'https://xhslink.cn/o/65mKtkE8Uk'
PAGE_CAP = 8 * 1024 * 1024
TOTAL_CAP = 60 * 1024 * 1024


def parse_note(html):
    match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(.*?)</script>', html, re.S)
    if not match:
        raise ValueError('Public page has no note state')
    raw = re.sub(r'\bundefined\b', 'null', match.group(1).strip().rstrip(';'))
    state = json.loads(raw)
    details = state.get('note', {}).get('noteDetailMap', {})
    notes = [v.get('note', {}) for v in details.values() if isinstance(v, dict)]
    notes = [v for v in notes if v.get('imageList')]
    if len(notes) != 1:
        raise ValueError('Public page has no unambiguous carousel')
    note = notes[0]
    title = note.get('title', '')
    if not ('可爱噜' in title or '谁家' in title):
        raise ValueError('Public title does not match requested note')
    if not note.get('noteId') or not 1 <= len(note['imageList']) <= 30:
        raise ValueError('Missing identity or unexpected carousel count')
    return note


def allowed_image(url):
    p = urllib.parse.urlparse(url)
    return (p.scheme == 'https' and not p.username and not p.password
            and p.port in (None, 443) and any((p.hostname or '').endswith('.' + domain)
                for domain in ('xhscdn.com', 'rednotecdn.com', 'xiaohongshu.com')))


def candidates(item):
    values = [item.get('urlDefault', ''), item.get('urlPre', '')]
    values += [v.get('url', '') for v in item.get('infoList', [])]
    values = [u.replace('http://', 'https://', 1) for u in values if isinstance(u, str)]
    return list(dict.fromkeys(u for u in values if allowed_image(u)))


def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('Only GitHub Actions may download this note')
    ROOT.mkdir(parents=True, exist_ok=True)
    diagnostic = {'share_url': SHARE_URL, 'run_id': os.environ.get('GITHUB_RUN_ID'),
                  'branch': os.environ.get('GITHUB_REF_NAME'), 'status': 'starting'}
    try:
        req = urllib.request.Request(SHARE_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=35) as response:
            body = response.read(PAGE_CAP + 1)
            final_url = response.url
        if len(body) > PAGE_CAP:
            raise ValueError('Page exceeds size cap')
        p = urllib.parse.urlparse(final_url)
        diagnostic.update(resolved_page=p.scheme + '://' + p.netloc + p.path,
                          page_bytes=len(body), login_redirect='/login' in p.path)
        # Identify the requested note from any public redirect path, never retry a login wall.
        decoded = urllib.parse.unquote(urllib.parse.unquote(final_url))
        ids = re.findall(r'/(?:explore|discovery/item)/([0-9a-f]{24})', decoded)
        if ids:
            diagnostic['redirect_note_ids'] = list(dict.fromkeys(ids))
        note = parse_note(body.decode('utf-8', 'replace'))
        if ids and note['noteId'] not in ids:
            raise ValueError('Resolved note identity mismatch')
        lists = []
        seen = set()
        for item in note['imageList']:
            urls = candidates(item)
            if not urls:
                raise ValueError('Carousel item has no public image URL')
            identity = item.get('fileId') or urls[0].split('!', 1)[0]
            if identity not in seen:
                lists.append(urls); seen.add(identity)
        total, records = 0, []
        with tempfile.TemporaryDirectory() as temporary:
            stage = Path(temporary)
            for i, urls in enumerate(lists, 1):
                best = None
                for url in urls:
                    try:
                        data, w, h, fmt = fetch(url)
                        with Image.open(io.BytesIO(data)) as image:
                            image.load()
                        choice = (w*h, len(data), data, w, h, fmt, url)
                        if best is None or choice[:2] > best[:2]:
                            best = choice
                    except (OSError, ValueError, Image.DecompressionBombError):
                        print(f'Image {i}: candidate unavailable', flush=True)
                if best is None:
                    raise RuntimeError(f'No validated public image for item {i}')
                _, _, data, w, h, fmt, url = best
                total += len(data)
                if total > TOTAL_CAP:
                    raise ValueError('Job exceeds combined cap')
                name = f'{i:02d}.{fmt}'
                (stage/name).write_bytes(data)
                records.append({'file':f'source/{name}', 'source_url':url, 'format':fmt,
                    'width':w, 'height':h, 'bytes':len(data),
                    'md5':hashlib.md5(data).hexdigest(), 'sha256':hashlib.sha256(data).hexdigest()})
                print(f'{name}: {w}x{h}, {len(data)} bytes', flush=True)
            folder = ROOT/'source'
            if folder.exists() and any(folder.iterdir()):
                raise RuntimeError('Refusing to overwrite existing source delivery')
            folder.mkdir(exist_ok=True)
            for path in stage.iterdir():
                (folder/path.name).write_bytes(path.read_bytes())
        manifest = {'share_url':SHARE_URL, 'note_id':note['noteId'], 'title':note.get('title'),
                    'author':note.get('user', {}).get('nickname'), 'description':note.get('desc'),
                    'resolved_page':diagnostic['resolved_page'], 'reference_count_downloaded':len(records),
                    'download_method':'GitHub Actions, public declared image URLs only; bounded fetch and full decode',
                    'source_quality':'Public CDN display files; not independently verified author master files',
                    'status':'downloaded_pending_visual_review','run_id':os.environ.get('GITHUB_RUN_ID'),
                    'images':records}
        (ROOT/'source-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        diagnostic.update(status='downloaded_pending_visual_review',count=len(records),images_verified=True)
    except Exception as exc:
        diagnostic.update(status='blocked_source_download',error_type=type(exc).__name__,
                          error=str(exc),images_verified=False)
        raise
    finally:
        (ROOT/'download-status.json').write_text(json.dumps(diagnostic,ensure_ascii=False,indent=2)+'\n')


if __name__ == '__main__':
    main()
