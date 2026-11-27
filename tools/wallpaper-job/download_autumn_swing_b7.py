"""Download this public sunset note on GitHub Actions, never in the agent sandbox.

No login/cookies or access-control bypass. Preserve decoded-valid CDN bytes.
Stage the whole delivery before publishing; failures never commit partial images.
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
import warnings

from PIL import Image, ImageDraw, ImageOps

SHARE_URL = 'https://xhslink.cn/o/C5WkFiFa1r'
ROOT = Path('deliveries/autumn-swing-C5WkFiFa1r')
IMAGE_LIMIT = 12 * 1024 * 1024
TOTAL_LIMIT = 65 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 24_000_000
warnings.simplefilter('error', Image.DecompressionBombWarning)
PUBLIC_NOTE_URLS = []


def check_url(url):
    p = urllib.parse.urlsplit(url)
    allowed = ('xhslink.cn', 'xhslink.com', 'xiaohongshu.com', 'rednote.com', 'xhscdn.com', 'rednotecdn.com')
    if (p.scheme != 'https' or p.username or p.password or p.port not in (None, 443)
            or not any(p.hostname == d or (p.hostname or '').endswith('.' + d) for d in allowed)):
        raise ValueError(f'Unexpected public-note host: {p.scheme}://{p.hostname}')
    return url


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Some public short links declare an HTTP target; request HTTPS instead.
        if newurl.startswith('http://'):
            newurl = 'https://' + newurl[7:]
        check_url(newurl)
        parsed = urllib.parse.urlsplit(newurl)
        if re.search(r'/(?:explore|discovery/item)/[a-f0-9]{24}', parsed.path):
            PUBLIC_NOTE_URLS.append(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def read_url(url, limit):
    req = urllib.request.Request(check_url(url), headers={
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        'Referer': 'https://www.xiaohongshu.com/', 'Accept-Language': 'zh-CN,zh;q=0.9'})
    with urllib.request.build_opener(SafeRedirect()).open(req, timeout=25) as response:
        check_url(response.url)
        data = response.read(limit + 1)
        final = response.url
    if len(data) > limit:
        raise ValueError('Response exceeds byte cap')
    return data, final


def parse_note(html, final_url, title_hint='秋'):
    match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(.*?)</script>', html, re.S)
    if not match:
        raise ValueError('Public note state unavailable; may require app/login')
    # Undefined is emitted as a JS literal by this public page. Do not eval JS.
    raw = match.group(1).strip().rstrip(';')
    raw = re.sub(r'(?<=[,:\[])\s*undefined\s*(?=[,}\]])', 'null', raw)
    state = json.loads(raw)
    details = state.get('note', {}).get('noteDetailMap', {})
    note_id_match = re.search(r'/(?:explore|discovery/item)/([a-f0-9]{24})', final_url)
    notes = [v.get('note', {}) for v in details.values() if isinstance(v, dict)]
    if note_id_match:
        notes = [n for n in notes if n.get('noteId', note_id_match.group(1)) == note_id_match.group(1)]
    if not notes:
        # The official international web page uses a different state layout.
        # Inspect data only, with bounded traversal; never execute page scripts.
        stack, visited = [(state, 0)], 0
        while stack:
            value, depth = stack.pop()
            visited += 1
            if visited > 100_000 or depth > 30:
                raise ValueError('Public note state exceeds traversal cap')
            if isinstance(value, dict):
                if (isinstance(value.get('imageList'), list)
                        and title_hint in str(value.get('title', ''))
                        and (not note_id_match or value.get('noteId', note_id_match.group(1)) == note_id_match.group(1))):
                    if value not in notes:
                        notes.append(value)
                stack.extend((v, depth + 1) for v in value.values() if isinstance(v, (dict, list)))
            elif isinstance(value, list):
                stack.extend((v, depth + 1) for v in value if isinstance(v, (dict, list)))
    if len(notes) != 1:
        keys = ','.join(str(k) for k in state)[:90]
        note_keys = ','.join(str(k) for k in state.get('note', {}))[:90]
        raise ValueError(f'Cannot identify note: count={len(notes)}; state={keys}; note={note_keys}')
    note = notes[0]
    if note_id_match:
        note.setdefault('noteId', note_id_match.group(1))
    if title_hint not in note.get('title', ''):
        raise ValueError('Resolved note title does not match requested note')
    images = note.get('imageList', [])
    if not 1 <= len(images) <= 20:
        raise ValueError('Unexpected carousel image count')
    return note


def candidates(item):
    urls = [item.get('urlDefault', ''), item.get('urlPre', '')]
    urls += [v.get('url', '') for v in item.get('infoList', [])]
    # Only use publicly declared CDN URLs. Do not invent asset tokens or signatures.
    result = []
    for url in dict.fromkeys(urls):
        if not url:
            continue
        if url.startswith('http://'):
            url = 'https://' + url[7:]
        check_url(url)
        result.append(url)
    return result


def validate(data):
    if len(data) > IMAGE_LIMIT:
        raise ValueError('Image exceeds byte cap')
    with Image.open(io.BytesIO(data)) as im:
        im.verify()
    with Image.open(io.BytesIO(data)) as im:
        im.load()
        w, h = im.size
        fmt = {'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp'}.get(im.format)
        if not fmt or min(w, h) < 300 or w * h > 24_000_000 or getattr(im, 'n_frames', 1) != 1:
            raise ValueError('Unsupported, animated, small or oversized image')
    return w, h, fmt


def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('Network download is restricted to GitHub Actions')
    html, final = read_url(SHARE_URL, 8 * 1024 * 1024)
    try:
        note = parse_note(html.decode('utf-8'), final)
    except ValueError:
        parsed = urllib.parse.urlsplit(final)
        print(f'::notice title=Public share redirect::{parsed.hostname}{parsed.path}', flush=True)
        # Use only a note URL actually declared by the public short-link redirect,
        # not the final /login path. One official public frontend retry, no cookies.
        if not PUBLIC_NOTE_URLS:
            raise ValueError('Share redirected to login without exposing a public note URL')
        declared = urllib.parse.urlsplit(PUBLIC_NOTE_URLS[0])
        domestic = urllib.parse.urlunsplit(('https', 'www.xiaohongshu.com', declared.path, declared.query, ''))
        html, final = read_url(domestic, 8 * 1024 * 1024)
        if '/login' in urllib.parse.urlsplit(final).path:
            raise ValueError('Official public note redirects to login; no authentication attempted')
        note = parse_note(html.decode('utf-8'), final)
    ROOT.parent.mkdir(parents=True, exist_ok=True)
    if (ROOT / 'source').exists():
        raise ValueError('Sources already exist; refusing to overwrite')
    if note.get('noteId') != '6abdb5a9000000001802f193':
        raise ValueError('Resolved note identity mismatch')
    with tempfile.TemporaryDirectory(dir=ROOT.parent, prefix='.sunset-') as tmp:
        stage = Path(tmp) / 'delivery'
        source = stage / 'source'
        source.mkdir(parents=True)
        rows, hashes, total = [], set(), 0
        for index, item in enumerate(note['imageList'], 1):
            best = None
            for url in candidates(item):
                try:
                    data, _ = read_url(url, IMAGE_LIMIT)
                    w, h, fmt = validate(data)
                    candidate = (w * h, len(data), data, w, h, fmt, url)
                    if best is None or candidate[:2] > best[:2]:
                        best = candidate
                except (OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
                    print(f'Image {index}: a declared candidate unavailable', flush=True)
            if best is None:
                raise ValueError(f'No validated public image at position {index}')
            _, _, data, w, h, fmt, chosen_url = best
            total += len(data)
            if total > TOTAL_LIMIT:
                raise ValueError('Source set exceeds 65 MiB cap')
            digest = hashlib.sha256(data).hexdigest()
            if digest in hashes:
                raise ValueError('Duplicate source image in carousel')
            hashes.add(digest)
            name = f'{index:02d}.{fmt}'
            (source / name).write_bytes(data)
            rows.append({'file': 'source/' + name, 'width': w, 'height': h,
                         'bytes': len(data), 'sha256': digest, 'md5': hashlib.md5(data).hexdigest(), 'format': fmt, 'source_url': chosen_url})
            print(f'Validated image {index}: {w}x{h}, {len(data)} bytes', flush=True)
        # Re-read every staged file before publishing anything to the repository.
        for row in rows:
            data = (stage / row['file']).read_bytes()
            validate(data)
            if hashlib.sha256(data).hexdigest() != row['sha256']:
                raise ValueError('Staged file hash mismatch')
        cols = min(5, len(rows))
        sheet = Image.new('RGB', (cols * 240 + 20, ((len(rows)+cols-1)//cols)*550 + 55), '#f5ebdb')
        draw = ImageDraw.Draw(sheet)
        draw.text((20, 14), 'PUBLIC NOTE SOURCES / NOT AUTHOR MASTER FILES', fill='#72523c')
        for i, row in enumerate(rows):
            x, y = 20 + i % cols * 240, 50 + i // cols * 550
            with Image.open(stage / row['file']) as im:
                thumb = ImageOps.contain(im.convert('RGB'), (220, 505))
            sheet.paste(thumb, (x, y+25))
            draw.text((x, y), f'{i+1:02d} / {row["width"]} x {row["height"]}', fill='#72523c')
        sheet.save(stage / '原片总预览.jpg', quality=92)
        manifest = {'schema_version': 1, 'status': 'downloaded_pending_visual_review',
                    'share_url': SHARE_URL, 'note_id': note.get('noteId'), 'title': note.get('title'),
                    'author': note.get('user', {}).get('nickname'),
                    'download_method': 'GitHub Actions only; public declared CDN URLs; no cookies',
                    'source_quality': '公开笔记的最高可得候选文件，未经重编码；不保证为作者母版。',
                    'source_count': len(rows), 'requested_result_count': 10,
                    'runner_commit': os.environ.get('GITHUB_SHA'), 'run_id':os.environ.get('GITHUB_RUN_ID'),
                    'images': rows}
        (stage / 'source-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        (stage / 'download-status.json').write_text(json.dumps({'status':'downloaded_pending_visual_review','run_id':os.environ.get('GITHUB_RUN_ID'),'count':len(rows),'all_decoded':True})+'\n')
        ROOT.mkdir(parents=True,exist_ok=True)
        for entry in stage.iterdir():
            entry.replace(ROOT / entry.name)
    print(f'Published {len(rows)} verified public source images', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Expose only a short diagnostic in the Checks API, not signed URLs/bodies.
        import urllib.error
        if isinstance(exc, urllib.error.HTTPError):
            message = f'Public endpoint returned HTTP {exc.code}'
        elif isinstance(exc, ValueError):
            message = str(exc)[:180].replace('\n', ' ')
        else:
            message = type(exc).__name__
        print(f'::error title=Public note download blocked::{message}', flush=True)
        raise SystemExit(1)
