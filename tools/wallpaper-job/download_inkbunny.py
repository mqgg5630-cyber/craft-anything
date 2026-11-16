"""Public CDN download for the glowing ink-wash rabbit/fox note; same bounded validator as before."""
import hashlib
import json
from pathlib import Path
from download import fetch

ROOT = Path('deliveries/ink-bunny-fox-127')
TOKENS = [
    '1040g3k831pkk15qs4a9g5p57q7v7omp2168vueo',
    '1040g3k831pkk15qs4a705p57q7v7omp2300899o',
    '1040g3k831pkk15qs4a7g5p57q7v7omp254opd3o',
    '1040g3k831pkk15qs4a805p57q7v7omp25gt6c3o',
    '1040g3k831pkk15qs4a8g5p57q7v7omp2l0fc0j0',
    '1040g3k831pkk15qs4a905p57q7v7omp24puhf6g',
]


def main():
    folder = ROOT / '01-下载原图'
    folder.mkdir(parents=True, exist_ok=True)
    record = {'schema_version': 1, 'note_id': '69301044000000001b0318ed',
              'title': '会发光的水墨兔狐｜动态壁纸｜127', 'author': '粉心心 wallpaper',
              'share_url': 'https://xhslink.cn/o/9dToOG6BFKA',
              'source_caveat': 'Public CDN response, not independently verified as author master. '
                               'Items 02 and 03 are marked LIVE in the note; only the cover frame is downloadable.',
              'images': []}
    total = 0
    for i, token in enumerate(TOKENS, 1):
        candidates = []
        for base in ['https://sns-img-bd.xhscdn.com/notes_pre_post/',
                     'https://ci.xiaohongshu.com/notes_pre_post/',
                     'https://sns-img-bd.xhscdn.com/']:
            url = base + token
            try:
                data, w, h, fmt = fetch(url)
                candidates.append((w * h, len(data), data, w, h, fmt, url))
            except (OSError, ValueError):
                print(f'Image {i}: candidate unavailable', flush=True)
        if not candidates:
            raise RuntimeError(f'No validated image for {i}')
        _, _, data, w, h, fmt, url = max(candidates, key=lambda v: (v[0], v[1]))
        total += len(data)
        if total > 75 * 1024 * 1024:
            raise ValueError('Job size cap reached')
        filename = f'{i:02d}.{fmt}'
        (folder / filename).write_bytes(data)
        record['images'].append({'file': filename, 'width': w, 'height': h, 'bytes': len(data),
                                 'sha256': hashlib.sha256(data).hexdigest(), 'source_url': url})
        print(f'{filename}: {w}x{h}, {len(data)} bytes', flush=True)
    (folder / '下载记录.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
