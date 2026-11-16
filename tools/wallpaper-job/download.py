"""Bounded, auditable download of the seven public note images. No cookies needed."""
import hashlib
import io
import json
from pathlib import Path
import urllib.error
import urllib.request
from PIL import Image

TOKENS = [
    '1040g2sg326grq9sckqh05nqoser0bki2bre5sm8',
    '1040g2sg326grq9sckqe05nqoser0bki2tmq0oo0',
    '1040g2sg326grq9sckqeg5nqoser0bki2peegos0',
    '1040g2sg326grq9sckqf05nqoser0bki26fgh3r0',
    '1040g2sg326grq9sckqfg5nqoser0bki2lm7o5sg',
    '1040g2sg326grq9sckqg05nqoser0bki200ublqg',
    '1040g2sg326grq9sckqgg5nqoser0bki2i78i8g0',
]
ROOT = Path('deliveries/blue-kitty')
LIMIT = 12 * 1024 * 1024


def fetch(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'CraftAnything-dev',
        'Referer': 'https://www.xiaohongshu.com/',
    })
    with urllib.request.urlopen(req, timeout=35) as response:
        data = response.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError('Image exceeds 12 MiB cap')
    with Image.open(io.BytesIO(data)) as image:
        image.verify()
    with Image.open(io.BytesIO(data)) as image:
        w, h = image.size
        fmt = image.format.lower()
    if min(w, h) < 300:
        raise ValueError('Unexpectedly small image')
    return data, w, h, fmt


def main():
    original = ROOT / '01-下载原图'
    original.mkdir(parents=True, exist_ok=True)
    manifest = {'schema_version': 1, 'note_id': '6ad631d1000000002803bf27',
                'title': '奶fufu淡蓝手绘｜氛围感手机壁纸',
                'share_url': 'https://xhslink.cn/o/AgiCwSCgdwL',
                'source_caveat': 'Public CDN files; not independently verified as author master files.',
                'images': []}
    total = 0
    for index, token in enumerate(TOKENS, 1):
        candidates = []
        for url in [f'https://sns-img-bd.xhscdn.com/{token}',
                    f'https://ci.xiaohongshu.com/{token}?imageView2/format/png',
                    f'https://sns-webpic-qc.xhscdn.com/{token}?imageView2/2/w/2560/format/png']:
            try:
                data, w, h, fmt = fetch(url)
                candidates.append((w * h, len(data), data, w, h, fmt, url))
            except (OSError, ValueError, Image.DecompressionBombError):
                # Do not print signed URLs, response bodies or request headers.
                print(f'Image {index}: one candidate unavailable', flush=True)
        if not candidates:
            raise RuntimeError(f'No valid image for item {index}; download incomplete')
        _, _, data, w, h, fmt, url = max(candidates, key=lambda x: (x[0], x[1]))
        total += len(data)
        if total > 75 * 1024 * 1024:
            raise ValueError('Job exceeds 75 MiB cap')
        name = f'{index:02d}.{fmt}'
        (original / name).write_bytes(data)
        manifest['images'].append({'file': name, 'width': w, 'height': h,
                                   'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                                   'source_url': url})
        print(f'Image {index}: {w}x{h}, {len(data)} bytes', flush=True)
    (original / '下载记录.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
