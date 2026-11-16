"""Public CDN download for the butterfly-hill cat house note; same bounded validator as before."""
import hashlib
import json
from pathlib import Path
from download import fetch

ROOT = Path('deliveries/garden-cats')
HOST = 'https://sns-web-i10.rednotecdn.com/202611161712'
# (path hash, token) exactly as the note page serves them.
ITEMS = [
    ('5c44af708054c779f4229dfd25b6abad', '1040g3k8327kj09s0ngag4a367e5fgep72dbph1g'),
    ('d7cbb255090e2bb2c20f314c888cae3e', '1040g3k8327kj09s0ng904a367e5fgep769qpveo'),
    ('ccc3e040a91a31683c84008f89e0bc99', '1040g3k8327kj09s0ng9g4a367e5fgep7h4al0og'),
    ('bd77323aa412ec8763b047c3f8057ac6', '1040g3k8327kj09s0nga04a367e5fgep7so7at8o'),
]


def candidates(digest, token):
    yield f'{HOST}/{digest}/notes_pre_post/{token}'
    for view in ('imageView2/2/w/2400/format/png', 'imageView2/2/w/2400/format/jpg',
                 'imageView2/format/png'):
        yield f'{HOST}/{digest}/notes_pre_post/{token}?{view}'
    yield f'{HOST}/{digest}/notes_pre_post/{token}!nd_dft_wlteh_webp_3'
    for base in ('https://sns-img-bd.xhscdn.com/notes_pre_post/',
                 'https://ci.xiaohongshu.com/notes_pre_post/'):
        yield base + token


def main():
    folder = ROOT / '01-下载原图'
    folder.mkdir(parents=True, exist_ok=True)
    record = {'schema_version': 1, 'note_id': '6afac7bc000000002a03b9b3',
              'title': '✨蝴蝶山的猫猫屋🐱', 'author': '年糕和他的蝴蝶结🎀',
              'share_url': 'https://xhslink.cn/o/1zMCJCEvezY',
              'source_caveat': 'Public CDN response, not independently verified as author master.',
              'images': []}
    total = 0
    failures = []
    for i, (digest, token) in enumerate(ITEMS, 1):
        found = []
        for url in candidates(digest, token):
            try:
                data, w, h, fmt = fetch(url)
            except Exception as exc:  # noqa: BLE001 - report every candidate, keep going
                print(f'Image {i}: {type(exc).__name__} {url}', flush=True)
                continue
            print(f'Image {i}: ok {w}x{h} {len(data)}B {url}', flush=True)
            found.append((w * h, len(data), data, w, h, fmt, url))
        if not found:
            failures.append(i)
            print(f'Image {i}: NO CANDIDATE WORKED', flush=True)
            continue
        _, _, data, w, h, fmt, url = max(found, key=lambda v: (v[0], v[1]))
        total += len(data)
        if total > 75 * 1024 * 1024:
            raise ValueError('Job size cap reached')
        filename = f'{i:02d}.{fmt}'
        (folder / filename).write_bytes(data)
        record['images'].append({'file': filename, 'width': w, 'height': h, 'bytes': len(data),
                                 'sha256': hashlib.sha256(data).hexdigest(), 'source_url': url})
    record['missing'] = failures
    (folder / '下载记录.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{len(record["images"])}/{len(ITEMS)} downloaded; missing {failures}', flush=True)


if __name__ == '__main__':
    main()
