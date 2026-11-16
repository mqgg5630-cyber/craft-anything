"""Public CDN download for the 3D pop-out animals note; same bounded validator as before."""
import hashlib
import json
from pathlib import Path
from download import fetch

ROOT = Path('deliveries/sticker3d-animals')
TOKENS = [
    '1040g2sg326p6ijcakqfg5p1303kkicij6n0pj7o',
    '1040g2sg326p6ijcakqe05p1303kkicijlll77m8',
    '1040g2sg326p6ijcakqeg5p1303kkicijtk952kg',
    '1040g2sg326p6ijcakqf05p1303kkicijubgp5k0',
]


def main():
    folder = ROOT / '01-下载原图'
    folder.mkdir(parents=True, exist_ok=True)
    record = {'schema_version': 1, 'note_id': '6adebb71000000001800854e',
              'title': '谁懂啊！！这几张3D立体壁纸也太有感觉了吧', 'author': '蜡笔小心',
              'share_url': 'https://xhslink.cn/o/3yBZRAgYSxH',
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
