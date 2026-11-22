"""Resolve and fetch the note's public carousel on a GitHub Actions runner.

No login, cookies, or bypassing access restrictions. All image bytes are
validated before anything is written to source/. A safe diagnostic is written
on failure so the triggering branch records the blocker without page secrets.
"""
import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from download import fetch

ROOT = Path('deliveries/lululu-cute-note')
SHARE = 'https://xhslink.cn/o/65mKtkE8Uk'
MAX_PAGE = 8 * 1024 * 1024
MAX_TOTAL = 75 * 1024 * 1024


def main():
    req = urllib.request.Request(SHARE, headers={'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'zh-CN,zh;q=0.9'})
    with urllib.request.urlopen(req, timeout=35) as resp:
        final = resp.geturl()
        html = resp.read(MAX_PAGE + 1)
    parsed = urllib.parse.urlparse(final)
    if len(html) > MAX_PAGE:
        raise RuntimeError('public note page exceeded size limit')
    if 'login' in parsed.path.lower():
        raise RuntimeError('public note link redirected to a login page')
    note_id_match = re.search(r'/(?:explore|discovery/item)/([0-9a-f]{24})', parsed.path)
    note_id = note_id_match.group(1) if note_id_match else None
    m = re.search(r'window\.__INITIAL_STATE__\s*=\s*(.*?)</script>', html.decode('utf-8', 'replace'), re.S)
    if not m:
        raise RuntimeError('public page does not contain a note state')
    state = json.loads(re.sub(r'\bundefined\b', 'null', m.group(1).strip().rstrip(';')))
    details = state.get('note', {}).get('noteDetailMap', {})
    notes = [d.get('note', {}) for d in details.values() if isinstance(d, dict)]
    if note_id:
        notes = [n for n in notes if n.get('noteId') == note_id]
    notes = [n for n in notes if n.get('imageList')]
    if len(notes) != 1:
        raise RuntimeError(f'expected one public note with imageList, got {len(notes)}')
    note = notes[0]
    note_id = note.get('noteId') or note_id
    if not note_id:
        raise RuntimeError('public note id could not be confirmed')
    image_list = note['imageList']
    if not 1 <= len(image_list) <= 30:
        raise RuntimeError(f'unexpected image count: {len(image_list)}')
    results = []
    total = 0
    for i, item in enumerate(image_list, 1):
        urls = [item.get('urlDefault', ''), item.get('urlPre', '')] + [entry.get('url', '') for entry in item.get('infoList', [])]
        valid = []
        for url in dict.fromkeys(u for u in urls if isinstance(u, str) and u.startswith('https://')):
            try:
                data, w, h, fmt = fetch(url)
                valid.append((w*h, len(data), data, w, h, fmt, url))
            except (OSError, ValueError) as exc:
                print('candidate unavailable:', i, type(exc).__name__, flush=True)
        if not valid:
            raise RuntimeError(f'no valid public image for carousel item {i}')
        _, _, data, w, h, fmt, url = max(valid, key=lambda row: row[:2])
        total += len(data)
        if total > MAX_TOTAL:
            raise RuntimeError('total image size exceeded limit')
        results.append((data, {'file': f'source/{i:02d}.{fmt}', 'width':w,'height':h,'format':fmt,'bytes':len(data),
                               'md5':hashlib.md5(data).hexdigest(), 'sha256':hashlib.sha256(data).hexdigest(), 'source_url':url}))
        print(f'validated image {i}: {w}x{h} {fmt} {len(data)} bytes', flush=True)
    if len({r['sha256'] for _,r in results}) != len(results):
        raise RuntimeError('duplicate carousel images; requires manual review')
    dest = ROOT / 'source'
    if dest.exists() and any(dest.iterdir()):
        raise RuntimeError('refusing to overwrite existing source images')
    dest.mkdir(parents=True, exist_ok=True)
    for data, rec in results:
        (ROOT / rec['file']).write_bytes(data)
    manifest = {'share_url': SHARE, 'note_id': note_id, 'title': note.get('title'), 'description': note.get('desc'),
                'author': (note.get('user') or {}).get('nickname'), 'status': 'downloaded_pending_visual_review',
                'source_quality': 'Public CDN files, not confirmed author master files.', 'images': [r for _,r in results]}
    (ROOT / 'source-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {'status':'success','note_id':note_id,'image_count':len(results)}


if __name__ == '__main__':
    ROOT.mkdir(parents=True,exist_ok=True)
    try:
        status = main()
    except Exception as exc:
        status = {'status':'blocked_source_download','error_type':type(exc).__name__, 'message':str(exc)[:300]}
        print(json.dumps(status,ensure_ascii=False),flush=True)
        (ROOT / 'download-status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        raise
    (ROOT / 'download-status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
