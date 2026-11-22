"""Download the public images of note 6ad212fc000000001802d6be on a GitHub runner.

"和你一起奔夕阳 噜噜噜妹壁纸" (share link https://xhslink.cn/o/5thkO8Kd6jg).
No cookies, login or credentials. The share link is resolved live on the runner so
signed CDN URLs are fresh; unsigned CDN token variants are tried as well and the
largest valid decode (pixels, then bytes) is kept. Every file goes through the
existing bounded fetch() validator (12 MiB cap, full decode, minimum size).
"""
import hashlib
import json
import re
import urllib.request
from pathlib import Path

from download import fetch

ROOT = Path('deliveries/lululu-sunset-ui-10')
SOURCE = ROOT / '原片'
NOTE_ID = '6ad212fc000000001802d6be'
SHARE_URL = 'https://xhslink.cn/o/5thkO8Kd6jg'
# Carousel tokens observed for this note; used only if the live page gives no list.
KNOWN_TOKENS = [
    'notes_pre_post/1040g3k8326cqvueoka905qlghp0l1h01fu7131o',
    'notes_pre_post/1040g3k8326cqvueoka705qlghp0l1h01pro2cso',
    'notes_pre_post/1040g3k8326cqvueoka7g5qlghp0l1h01cjj2jlg',
    'notes_pre_post/1040g3k8326cqvueoka805qlghp0l1h01pb66us8',
    'notes_pre_post/1040g3k8326cqvueoka8g5qlghp0l1h01pt7kqn0',
]
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/126.0 Safari/537.36'}
JOB_CAP = 60 * 1024 * 1024


def token_of(url):
    """'https://host/<ts>/<sig>/notes_pre_post/1040g...!nd_x' -> 'notes_pre_post/1040g...'."""
    path = url.split('://', 1)[-1].split('?', 1)[0].split('!', 1)[0]
    parts = path.split('/')[1:]
    for i, part in enumerate(parts):
        if part.startswith('1040g') or part.startswith('spectrum') or part.startswith('notes_'):
            return '/'.join(parts[i:])
    return ''


def variants(token):
    return [f'https://sns-img-bd.xhscdn.com/{token}',
            f'https://ci.xiaohongshu.com/{token}?imageView2/format/png',
            f'https://sns-webpic-qc.xhscdn.com/{token}?imageView2/2/w/2560/format/png']


def read_note():
    meta = {'share_url': SHARE_URL, 'note_id': NOTE_ID}
    req = urllib.request.Request(SHARE_URL, headers=UA)
    with urllib.request.urlopen(req, timeout=35) as response:
        meta['resolved_url'] = response.geturl().split('?', 1)[0]
        html = response.read(8 * 1024 * 1024).decode('utf-8', 'replace')
    match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(.*?)</script>', html, re.S)
    if not match:
        return meta, []
    state = json.loads(re.sub(r'\bundefined\b', 'null', match.group(1).strip().rstrip(';')))
    for detail in state.get('note', {}).get('noteDetailMap', {}).values():
        note = detail.get('note') or {}
        if note.get('noteId') not in (None, NOTE_ID):
            continue
        images = note.get('imageList') or []
        if not images:
            continue
        meta.update(title=note.get('title'), desc=note.get('desc'),
                    author=(note.get('user') or {}).get('nickname'),
                    tags=[t.get('name') for t in note.get('tagList') or []])
        lists = []
        for item in images:
            urls = [item.get('urlDefault') or '', item.get('urlPre') or '']
            urls += [v.get('url') or '' for v in item.get('infoList') or []]
            lists.append([u.replace('http://', 'https://', 1) for u in urls if u])
        return meta, lists
    return meta, []


def main():
    try:
        meta, lists = read_note()
        print(f'Live note page: {len(lists)} images', flush=True)
    except (OSError, ValueError) as exc:
        print('Live note page unavailable:', type(exc).__name__, flush=True)
        meta, lists = {'share_url': SHARE_URL, 'note_id': NOTE_ID}, []
    if not lists:
        lists = [[] for _ in KNOWN_TOKENS]
        tokens = KNOWN_TOKENS
        meta['image_list_source'] = 'previously observed carousel tokens'
    else:
        tokens = [next((token_of(u) for u in urls if token_of(u)), '') for urls in lists]
        meta['image_list_source'] = 'live note page on GitHub runner'
    SOURCE.mkdir(parents=True, exist_ok=True)
    records, total = [], 0
    for index, (urls, token) in enumerate(zip(lists, tokens), 1):
        candidates = list(dict.fromkeys(urls + (variants(token) if token else [])))
        valid = []
        for url in candidates:
            try:
                data, width, height, fmt = fetch(url)
                valid.append((width * height, len(data), data, width, height, fmt, url))
            except Exception as exc:  # noqa: BLE001 - any failure just skips this candidate
                print(f'Image {index}: candidate unavailable ({type(exc).__name__})', flush=True)
        if not valid:
            raise RuntimeError(f'No validated public image for item {index}')
        _, _, data, width, height, fmt, url = max(valid, key=lambda item: item[:2])
        total += len(data)
        if total > JOB_CAP:
            raise ValueError('Combined source files exceed job cap')
        name = f'{index:02d}.{fmt}'
        (SOURCE / name).write_bytes(data)
        records.append({'file': f'原片/{name}', 'format': fmt, 'width': width, 'height': height,
                        'bytes': len(data), 'md5': hashlib.md5(data).hexdigest(),
                        'sha256': hashlib.sha256(data).hexdigest(), 'token': token,
                        'candidates_valid': len(valid), 'source_url': url})
        print(f'Image {index}: {width}x{height} {fmt}, {len(data)} bytes, '
              f'{len(valid)}/{len(candidates)} candidates valid', flush=True)
    manifest = dict(meta, status='downloaded_pending_visual_review',
                    reference_count_downloaded=len(records),
                    source_quality='Validated public CDN files; not independently verified author master files.',
                    download_method='GitHub Actions runner, tools/wallpaper-job/download_lululu_ui.py',
                    images=records)
    (ROOT / 'source-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print('downloaded', len(records), flush=True)


if __name__ == '__main__':
    main()
