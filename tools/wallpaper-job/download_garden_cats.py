"""Public CDN download for the butterfly-hill cat house note; same bounded validator as before."""
import hashlib
import json
from pathlib import Path
from download import fetch

ROOT = Path('deliveries/garden-cats')
TOKENS = [
    '1040g3k8327kj09s0ngag4a367e5fgep72dbph1g',
    '1040g3k8327kj09s0ng904a367e5fgep769qpveo',
    '1040g3k8327kj09s0ng9g4a367e5fgep7h4al0og',
    '1040g3k8327kj09s0nga04a367e5fgep7so7at8o',
]


def main():
    folder = ROOT / '01-下载原图'
    folder.mkdir(parents=True, exist_ok=True)
    record = {'schema_version': 1, 'note_id': '6afac7bc000000002a03b9b3',
              'title': '✨蝴蝶山的猫猫屋🐱', 'author': '年糕和他的蝴蝶结🎀',
              'share_url': 'https://xhslink.cn/o/1zMCJCEvezY',
              'source_caveat': 'Public CDN response, not independently verified as author master.',
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
