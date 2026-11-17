"""Public CDN download for 「手机壁纸｜被窝外正在下雨」 (note 6adf6496000000000803f71a).

Nine shared slides. Bare-token URLs 404 on this note, so every request carries the
(md5, token) pair taken from the note page and several path variants are tried.
"""
import hashlib
import json
from pathlib import Path

from download import fetch

ROOT = Path('deliveries/rainy-note')
CDN = 'https://sns-web-i10.rednotecdn.com/202611170925'
# (md5, token) in slide order as published.
IMAGES = [
    ('947beb7277c05afab69c475691c359ea', '1040g0k0326pr2h93k62g5p008j052cht4hsnhg0'),
    ('d93fe198fadf1d11a53545060ea4723b', '1040g0k0326pr2h93k6305p008j052chttu7kpd8'),
    ('15143e3dc12d008f248e1c2425298bce', '1040g0k0326pr2h93k6005p008j052cht2ck3bd0'),
    ('6ab2520422728ade5ed807fe8601b8bf', '1040g0k0326pr2h93k60g5p008j052chtcn9h5n8'),
    ('55ba2ae73e16d95d48fedfc4381f5939', '1040g0k0326pr2h93k6405p008j052chtarhuacg'),
    ('f0cfcb2372aedf927225a638c6355bfb', '1040g0k0326pr2h93k6105p008j052chtulvd6dg'),
    ('3dc3b7a29a4e9ce35ce80630e2286d83', '1040g0k0326pr2h93k61g5p008j052chthtrh7f0'),
    ('6cbfabcc233367dfc793fe102888979f', '1040g0k0326pr2h93k6205p008j052chtv1kbno8'),
    ('5f968d821f6c07d9c8880831baded3dc', '1040g0k0326pr2h93k63g5p008j052chtkghfvdg'),
]


def variants(md5, token):
    """Every plausible public path for this note; bare tokens are not enough."""
    return [
        f'{CDN}/{md5}/spectrum/{token}!nd_dft_wlteh_webp_3',
        f'{CDN}/{md5}/spectrum/{token}',
        f'{CDN}/{md5}/notes_pre_post/{token}',
        f'{CDN}/{md5}/{token}',
        f'https://sns-img-bd.xhscdn.com/notes_pre_post/{token}',
        f'https://ci.xiaohongshu.com/notes_pre_post/{token}',
    ]


def main():
    folder = ROOT / '01-下载原图'
    folder.mkdir(parents=True, exist_ok=True)
    record = {
        'schema_version': 1,
        'note_id': '6adf6496000000000803f71a',
        'title': '手机壁纸｜被窝外正在下雨 ☔️',
        'author': '椿几许壁纸',
        'share_url': 'https://xhslink.cn/o/2HY8xv0DdQ1',
        'source_caveat': (
            'Public CDN responses, not independently verified as author master files. '
            'Note publishes 9 slides; the author states the paid set has 11.'
        ),
        'images': [],
    }
    total = 0
    for index, (md5, token) in enumerate(IMAGES, 1):
        candidates = []
        for url in variants(md5, token):
            try:
                data, w, h, fmt = fetch(url)
            except (OSError, ValueError):
                print(f'Image {index}: one candidate unavailable', flush=True)
                continue
            candidates.append((w * h, len(data), data, w, h, fmt, url))
        if not candidates:
            raise RuntimeError(f'No valid image for slide {index}; download incomplete')
        _, _, data, w, h, fmt, url = max(candidates, key=lambda v: (v[0], v[1]))
        total += len(data)
        if total > 75 * 1024 * 1024:
            raise ValueError('Job exceeds 75 MiB cap')
        name = f'{index:02d}.{fmt}'
        (folder / name).write_bytes(data)
        record['images'].append({
            'file': name, 'width': w, 'height': h, 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(), 'source_url': url,
        })
        print(f'{name}: {w}x{h}, {len(data)} bytes', flush=True)
    if len(record['images']) != len(IMAGES):
        raise RuntimeError('Slide count mismatch')
    (folder / '下载记录.json').write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Done: {len(record["images"])} slides, {total} bytes', flush=True)


if __name__ == '__main__':
    main()
