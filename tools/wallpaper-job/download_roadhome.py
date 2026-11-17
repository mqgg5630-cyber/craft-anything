"""Public CDN download for 「回家的路，可以走很久」 (note 6afafb4d0000000026012791).

The note publishes eleven slides (page shows 1/11). Each request carries the
(md5, token) pair taken from the note page; several path variants are tried.
"""
import hashlib
import json
from pathlib import Path

from download import fetch

ROOT = Path('deliveries/road-home-9fm9nrxkjxi')
CDN = 'https://sns-web-i10.rednotecdn.com/202611171044'
# (md5, token) in slide order as published.
IMAGES = [
    ('f800b90c49ceb449c6d954d87406c7a7', '1040g34o327kpbsfn6c505nb0qud08bbbh4v63pg'),
    ('db1c5e3305306dcd2a1054a954394ac5', '1040g34o327kpbsfn6c405nb0qud08bbb3ls9vf8'),
    ('f15e5cff9a538e33fd9c60973bb8856f', '1040g34o327kpbsfn6c3g5nb0qud08bbb5lp3kd8'),
    ('3c58779be1251e75330dfdc76df5312d', '1040g34o327kpbsfn6c005nb0qud08bbbtir2ueg'),
    ('e01089d89851d9c5da55b7a167843521', '1040g34o327kpbsfn6c0g5nb0qud08bbb301u1ag'),
    ('614ae7f0b45788200eaa11d230f33ed7', '1040g34o327kpbsfn6c105nb0qud08bbbf4pii7g'),
    ('adc2a13ff05ae9cfd81b16e557211b19', '1040g34o327kpbsfn6c1g5nb0qud08bbb3gml3ho'),
    ('bdc1046bcf3da2a0942ff1116b35379f', '1040g34o327kpbsfn6c4g5nb0qud08bbb5mft2i8'),
    ('1c88b3c0d551b3ee492a8d205d6ef11c', '1040g34o327kpbsfn6c305nb0qud08bbb9ii2rko'),
    ('44073818992b4786213ca1545cbde0a9', '1040g34o327kpbsfn6c205nb0qud08bbbomohk4o'),
    ('2e0f747112e976942b381332d70e5501', '1040g34o327kpbsfn6c2g5nb0qud08bbb4l8hfq8'),
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
        'note_id': '6afafb4d0000000026012791',
        'title': '回家的路，可以走很久',
        'author': '渐入佳境',
        'share_url': 'https://xhslink.cn/o/9fm9nrxkJxi',
        'source_caveat': (
            'Public CDN responses, not independently verified as author master files. '
            'Note publishes 11 slides; the ten-slide replica set is generated separately.'
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
