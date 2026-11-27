"""Actions-only download and verification of the public lazy-sheep-with-kitten note.

No login, cookies, token invention, access-control changes, or fetching in the sandbox.
Every file must fully decode and match verified metadata before publication.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlparse

from PIL import Image
from download import fetch

ROOT = Path('deliveries/lazy-sheep-6bdoxc66Ezp')
SHARE_URL = 'https://xhslink.cn/o/6bdoxc66Ezp'
NOTE_ID = '6afc0e24000000002b005031'


def validate_expected(data, width, height, fmt, expected):
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        if image.size != (width, height) or image.format.lower() != fmt:
            raise ValueError('Decoded metadata mismatch')
    actual = {
        'width': width,
        'height': height,
        'format': fmt,
        'bytes': len(data),
        'md5': hashlib.md5(data).hexdigest(),
        'sha256': hashlib.sha256(data).hexdigest(),
    }
    for key, value in actual.items():
        if expected[key] != value:
            raise ValueError(f'Historical source mismatch: {key}')
    return actual


def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('Download is allowed only on GitHub Actions')
    seed = json.loads((ROOT / 'source-seed.json').read_text(encoding='utf-8'))
    if seed['share_url'] != SHARE_URL or seed['note_id'] != NOTE_ID or len(seed['images']) != 1:
        raise ValueError('Seed identity or carousel count mismatch')
    manifest = {key: seed[key] for key in ('share_url', 'note_id', 'title', 'author', 'provenance')}
    manifest.update(
        schema_version=2,
        images=[],
        status='downloaded_pending_visual_review',
        run_id=os.environ.get('GITHUB_RUN_ID'),
        branch=os.environ.get('GITHUB_REF_NAME'),
        download_method='GitHub Actions; declared public CDN URL; full decode and MD5/SHA-256 verification',
        source_quality='Public CDN display file; not independently verified as author lossless master file',
    )
    total = 0
    with tempfile.TemporaryDirectory() as temp:
        stage = Path(temp)
        for index, expected in enumerate(seed['images'], 1):
            url = expected['source_url']
            parsed = urlparse(url)
            if (
                parsed.scheme != 'https'
                or parsed.hostname != 'sns-web-i10.rednotecdn.com'
                or parsed.username
                or parsed.password
            ):
                raise ValueError('Unexpected public CDN URL')
            data, width, height, fmt = fetch(url)
            actual = validate_expected(data, width, height, fmt, expected)
            total += len(data)
            if total > 60 * 1024 * 1024:
                raise ValueError('Combined sources exceed size cap')
            filename = f'{index:02d}.{fmt}'
            (stage / filename).write_bytes(data)
            manifest['images'].append(
                dict(actual, file=f'source/{filename}', source_url=url, historical_hash_match=True)
            )
            print(f'{filename}: {width}x{height}, {len(data)} bytes, hashes MATCH', flush=True)
        folder = ROOT / 'source'
        for path in stage.iterdir():
            target = folder / path.name
            if target.exists() and target.read_bytes() != path.read_bytes():
                raise RuntimeError('Refusing to overwrite different source')
        if folder.exists() and set(p.name for p in folder.iterdir()) - set(p.name for p in stage.iterdir()):
            raise RuntimeError('Unexpected extra source files')
        folder.mkdir(parents=True, exist_ok=True)
        for path in stage.iterdir():
            (folder / path.name).write_bytes(path.read_bytes())
    manifest['reference_count_downloaded'] = len(manifest['images'])
    (ROOT / 'source-manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    (ROOT / 'download-status.json').write_text(
        json.dumps(
            {
                'status': 'downloaded_pending_visual_review',
                'run_id': os.environ.get('GITHUB_RUN_ID'),
                'images_verified': True,
                'historical_hashes_matched': True,
                'count': len(manifest['images']),
            },
            indent=2,
        )
        + '\n',
        encoding='utf-8',
    )


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        ROOT.mkdir(parents=True, exist_ok=True)
        (ROOT / 'download-status.json').write_text(
            json.dumps(
                {
                    'status': 'blocked_source_download',
                    'error_type': type(exc).__name__,
                    'error': str(exc)[:180],
                    'run_id': os.environ.get('GITHUB_RUN_ID'),
                    'share_url': SHARE_URL,
                    'images_verified': False,
                },
                ensure_ascii=False,
                indent=2,
            )
            + '\n',
            encoding='utf-8',
        )
        raise
