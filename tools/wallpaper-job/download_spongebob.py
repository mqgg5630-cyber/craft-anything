"""Public CDN download for 「海绵宝宝 & 派大星四季治愈壁纸」 (note 6a8d375100000000240268e9).

The note publishes six slides (page shows 1/6). Each request carries the
(md5, token) pair taken from the note page, in slide order; several path
variants are tried per slide and the largest valid response wins. No cookies
and no credentials are used — these are the same public files a browser loads.
"""
import hashlib
import json
from pathlib import Path

from download import fetch

ROOT = Path('deliveries/spongebob-patrick-5ciq9ne8i38')
CDN = 'https://sns-web-i10.rednotecdn.com/202611200907'
# (md5, token) in slide order as published.
IMAGES = [
    ('d79a6a8e623ca0e013be816d880244d9', '1040g34o3249b9opin27g5nv5h3o0bmq9579ln98'),
    ('d231d850f16b58dac567957e727b29d0', '1040g34o3249b9opin2805nv5h3o0bmq9l2vbpqo'),
    ('3e3be14514b23204522fdf2bf95b58af', '1040g34o3249b9opin2705nv5h3o0bmq9hfvloe8'),
    ('dfc37b1ed3db14af4e52b7cd9b66bea9', '1040g34o3249b9opin28g5nv5h3o0bmq9ti5e0tg'),
    ('8d151e3704f18ad5c56bdcca5c8ae556', '1040g34o3249b9opin2605nv5h3o0bmq97mdsr08'),
    ('56c4702e34b9a3006c1879b85adbea4f', '1040g34o3249b9opin26g5nv5h3o0bmq9p7j19r0'),
]


def variants(md5, token):
    """Every plausible public path for this slide; a bare token is not enough."""
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
        'note_id': '6a8d375100000000240268e9',
        'title': '海绵宝宝 & 派大星四季治愈壁纸✨',
        'author': '申小兮-AI视觉',
        'share_url': 'https://xhslink.cn/o/5CIq9nE8i38',
        'source_caveat': (
            'Public CDN responses, not independently verified as author master files. '
            'Note publishes 6 slides (spring / summer / autumn / winter set, oil-painting '
            'and clay texture); the ten-slide replica set is generated separately.'
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
                # Do not print signed URLs, response bodies or request headers.
                print(f'Slide {index}: one candidate unavailable', flush=True)
                continue
            candidates.append((w * h, len(data), data, w, h, fmt, url))
        if not candidates:
            raise RuntimeError(f'No valid image for slide {index}; download incomplete')
        _, _, data, w, h, fmt, url = max(candidates, key=lambda v: (v[0], v[1]))
        total += len(data)
        if total > 90 * 1024 * 1024:
            raise ValueError('Job exceeds 90 MiB cap')
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
        json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    print(f'wrote {len(record["images"])} slides, {total} bytes total')


if __name__ == '__main__':
    main()
