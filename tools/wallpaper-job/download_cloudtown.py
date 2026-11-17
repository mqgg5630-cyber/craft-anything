"""Public CDN download for 「✨治愈系壁纸 | 梦幻小镇、星空下的钟楼」 (note 6afb0441000000002203bea5).

The note publishes four slides (page shows 1/4). Every request carries the
(md5, token) pair taken from the note page; several path variants are tried
because bare-token URLs 404 on this note.
"""
import hashlib
import json
from pathlib import Path

from download import fetch

ROOT = Path('deliveries/cloud-town-2n522qk8gxn')
CDN = 'https://sns-web-i10.rednotecdn.com/202611171026'
# (md5, token) in slide order as published.
IMAGES = [
    ('a76b00abe91aad55300c0de4b58b1e12', '1040g34o327kqebaa6c105p6fcusjkgdej2mfss0'),
    ('d8a1f3d3411afdff89e24a9db54cbbd6', '1040g34o327kqflpfma805p6fcusjkgde91a4i3o'),
    ('cbf510cfeb44d3a22c502db1f5229214', '1040g34o327kqffhn6g205p6fcusjkgdemln8hsg'),
    ('c2714f11f30e5650e1bf02a5c4675849', '1040g34o327kqffhn6g2g5p6fcusjkgdepcb7dq8'),
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
        'note_id': '6afb0441000000002203bea5',
        'title': '✨治愈系壁纸 | 梦幻小镇、星空下的钟楼',
        'author': '一只小猫喵喵喵',
        'share_url': 'https://xhslink.cn/o/2N522Qk8Gxn',
        'source_caveat': (
            'Public CDN responses, not independently verified as author master files. '
            'Note publishes 4 slides; the ten-slide delivery is completed by replica work.'
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
        json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    print(f'wrote {len(record["images"])} slides, {total} bytes total')


if __name__ == '__main__':
    main()
