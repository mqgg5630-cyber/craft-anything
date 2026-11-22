"""Download the public images of one Xiaohongshu note on a GitHub runner.

Usage: python tools/wallpaper-job/download_xhs_note.py SHARE_URL OUT_DIR
No cookies, login or credentials. The short link's redirect is read without
following it, so the note ID and share token are kept even when the final hop
is a login page; the public note page is then requested on a few public hosts.
Each image goes through the existing bounded fetch() validator; unsigned CDN
variants are tried and the largest valid decode (pixels, then bytes) is kept.
"""
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from download import fetch

DESKTOP = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
MOBILE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'
JOB_CAP = 80 * 1024 * 1024
DIAG = {}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def redirect_chain(url, limit=6):
    opener = urllib.request.build_opener(NoRedirect)
    chain = [url]
    for _ in range(limit):
        req = urllib.request.Request(url, headers={'User-Agent': DESKTOP})
        try:
            with opener.open(req, timeout=30):
                break
        except urllib.error.HTTPError as exc:
            loc = exc.headers.get('Location')
            if exc.code not in (301, 302, 303, 307, 308) or not loc:
                break
            url = urllib.parse.urljoin(url, loc)
            chain.append(url)
    return chain


def note_ref(chain):
    for url in chain:
        for candidate in [url] + [urllib.parse.unquote(v) for v in re.findall(r'=([^&]+)', url)]:
            m = re.search(r'/(?:explore|discovery/item|item)/([0-9a-f]{24})', candidate)
            if m:
                q = urllib.parse.parse_qs(urllib.parse.urlparse(candidate).query)
                return m.group(1), q.get('xsec_token', [''])[0]
    return None, ''


def token_of(url):
    path = url.split('://', 1)[-1].split('?', 1)[0].split('!', 1)[0]
    parts = path.split('/')[1:]
    for i, part in enumerate(parts):
        if part.startswith(('1040g', 'spectrum', 'notes_')):
            return '/'.join(parts[i:])
    return ''


def variants(token):
    return [f'https://sns-img-bd.xhscdn.com/{token}',
            f'https://ci.xiaohongshu.com/{token}?imageView2/format/png',
            f'https://sns-webpic-qc.xhscdn.com/{token}?imageView2/2/w/2560/format/png']


def parse_page(html, note_id):
    meta, lists = {}, []
    m = re.search(r'window\.__INITIAL_STATE__\s*=\s*(.*?)</script>', html, re.S)
    if m:
        state = json.loads(re.sub(r'\bundefined\b', 'null', m.group(1).strip().rstrip(';')))
        details = state.get('note', {}).get('noteDetailMap', {})
        for detail in details.values():
            note = detail.get('note') or {}
            if note_id and note.get('noteId') not in (None, note_id):
                continue
            images = note.get('imageList') or []
            if images:
                meta = {'title': note.get('title'), 'desc': note.get('desc'),
                        'author': (note.get('user') or {}).get('nickname'), 'type': note.get('type')}
                for item in images:
                    urls = [item.get('urlDefault') or '', item.get('urlPre') or '']
                    urls += [v.get('url') or '' for v in item.get('infoList') or []]
                    lists.append([u.replace('http://', 'https://', 1) for u in urls if u])
                return meta, lists
    og = re.findall(r'<meta[^>]+(?:name|property)="og:image"[^>]+content="([^"]+)"', html)
    return meta, [[u.replace('http://', 'https://', 1)] for u in dict.fromkeys(og)]


def main(share_url, out_dir):
    root = Path(out_dir)
    source = root / '原片'
    chain = redirect_chain(share_url)
    note_id, xsec = note_ref(chain)
    DIAG.update(redirect_hosts=[urllib.parse.urlparse(u).netloc + urllib.parse.urlparse(u).path for u in chain],
                note_id=note_id, token_found=bool(xsec))
    print('redirect hops:', len(chain), 'note id found:', bool(note_id), 'token found:', bool(xsec), flush=True)
    meta, lists, tried = {}, [], []
    pages = []
    if note_id:
        qs = f'?xsec_token={urllib.parse.quote(xsec)}&xsec_source=app_share' if xsec else ''
        for host in ('www.xiaohongshu.com', 'www.rednote.com'):
            for path in ('explore', 'discovery/item'):
                pages.append(f'https://{host}/{path}/{note_id}{qs}')
    pages.append(share_url)
    for page in pages:
        for ua in ('Mozilla/5.0', DESKTOP, MOBILE):
            try:
                req = urllib.request.Request(page, headers={'User-Agent': ua, 'Accept-Language': 'zh-CN,zh;q=0.9'})
                with urllib.request.urlopen(req, timeout=35) as resp:
                    final = resp.geturl()
                    html = resp.read(8 * 1024 * 1024).decode('utf-8', 'replace')
                login = '/login' in final
                meta, lists = ({}, []) if login else parse_page(html, note_id)
                tried.append({'host': urllib.parse.urlparse(page).netloc,
                              'path': urllib.parse.urlparse(page).path.split('/')[1],
                              'ua': 'plain' if ua == 'Mozilla/5.0' else ('mobile' if ua == MOBILE else 'desktop'),
                              'final_host': urllib.parse.urlparse(final).netloc,
                              'login_redirect': login, 'images': len(lists)})
                print(tried[-1], flush=True)
                if lists:
                    break
            except (OSError, ValueError) as exc:
                tried.append({'host': urllib.parse.urlparse(page).netloc, 'error': type(exc).__name__})
                print(tried[-1], flush=True)
        if lists:
            break
    DIAG.update(page_attempts=tried, meta=meta, image_lists=len(lists))
    if not lists:
        raise RuntimeError('No public image list available from the note page')
    source.mkdir(parents=True, exist_ok=True)
    records, total = [], 0
    for index, urls in enumerate(lists, 1):
        token = next((token_of(u) for u in urls if token_of(u)), '')
        candidates = list(dict.fromkeys(urls + (variants(token) if token else [])))
        valid = []
        for url in candidates:
            try:
                data, width, height, fmt = fetch(url)
                valid.append((width * height, len(data), data, width, height, fmt, url))
            except Exception as exc:  # noqa: BLE001 - skip this candidate only
                DIAG.setdefault('candidate_errors', []).append(f'{index}:{type(exc).__name__}')
                print(f'Image {index}: candidate unavailable ({type(exc).__name__})', flush=True)
        if not valid:
            raise RuntimeError(f'No validated public image for item {index}')
        _, _, data, width, height, fmt, url = max(valid, key=lambda item: item[:2])
        total += len(data)
        if total > JOB_CAP:
            raise ValueError('Combined source files exceed job cap')
        name = f'{index:02d}.{fmt}'
        (source / name).write_bytes(data)
        records.append({'file': f'原片/{name}', 'format': fmt, 'width': width, 'height': height,
                        'bytes': len(data), 'md5': hashlib.md5(data).hexdigest(),
                        'sha256': hashlib.sha256(data).hexdigest(), 'token': token, 'source_url': url})
        print(f'Image {index}: {width}x{height} {fmt}, {len(data)} bytes', flush=True)
    manifest = dict(meta, share_url=share_url, note_id=note_id, page_attempts=tried,
                    status='downloaded_pending_visual_review', image_count=len(records),
                    source_quality='Validated public CDN files; not independently verified author master files.',
                    download_method='GitHub Actions runner, tools/wallpaper-job/download_xhs_note.py',
                    images=records)
    (root / 'source-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print('downloaded', len(records), flush=True)


if __name__ == '__main__':
    out = Path(sys.argv[2])
    try:
        main(sys.argv[1], sys.argv[2])
        DIAG['result'] = 'ok'
    except Exception as exc:
        DIAG['result'] = f'failed: {type(exc).__name__}: {exc}'[:300]
        raise
    finally:
        out.mkdir(parents=True, exist_ok=True)
        (out / 'download-log.json').write_text(json.dumps(DIAG, ensure_ascii=False, indent=2) + '\n')
