"""Actions-only replay of previously verified public CDN files for the new cute Lululu note.

Provenance and expected hashes are committed in source-seed.json. No login,
cookies, token invention, access-control changes, or fetching in the sandbox.
The public share page's login wall does not invalidate our existing source list.
All five files must fully decode and match historical hashes before publication.
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

ROOT = Path('deliveries/lululu-cute-65mKtkE8Uk')
SHARE_URL = 'https://xhslink.cn/o/65mKtkE8Uk'
NOTE_ID = '6a6195240000000001030e32'


def validate_expected(data, width, height, fmt, expected):
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        if image.size != (width, height) or image.format.lower() != fmt:
            raise ValueError('Decoded metadata mismatch')
    actual = {'width': width, 'height': height, 'format': fmt, 'bytes': len(data),
              'md5': hashlib.md5(data).hexdigest(), 'sha256': hashlib.sha256(data).hexdigest()}
    for key, value in actual.items():
        if expected[key] != value:
            raise ValueError(f'Historical source mismatch: {key}')
    return actual


def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('Download is allowed only on GitHub Actions')
    seed = json.loads((ROOT / 'source-seed.json').read_text(encoding='utf-8'))
    if seed['share_url'] != SHARE_URL or seed['note_id'] != NOTE_ID or len(seed['images']) != 5:
        raise ValueError('Seed identity or carousel count mismatch')
    manifest = {key: seed[key] for key in ('share_url', 'note_id', 'title', 'author', 'provenance')}
    manifest.update(schema_version=2, images=[],
        status='downloaded_pending_visual_review',
        run_id=os.environ.get('GITHUB_RUN_ID'), branch=os.environ.get('GITHUB_REF_NAME'),
        download_method='GitHub Actions; exact historical public CDN URLs; full decode and historical MD5/SHA-256 match',
        source_quality='Public CDN files; not independently verified author master files',
        page_refresh='Not retried: previous runner confirmed /login; replay existing verified public asset list only')
    total = 0
    with tempfile.TemporaryDirectory() as temp:
        stage = Path(temp)
        for index, expected in enumerate(seed['images'], 1):
            url = expected['source_url']
            parsed = urlparse(url)
            if parsed.scheme != 'https' or parsed.hostname != 'sns-web-i10.rednotecdn.com' or parsed.username or parsed.password:
                raise ValueError('Unexpected historical CDN URL')
            data, width, height, fmt = fetch(url)
            actual = validate_expected(data, width, height, fmt, expected)
            total += len(data)
            if total > 60 * 1024 * 1024:
                raise ValueError('Combined sources exceed size cap')
            filename = f'{index:02d}.{fmt}'
            (stage / filename).write_bytes(data)
            manifest['images'].append(dict(actual, file=f'source/{filename}', source_url=url,
                                           historical_hash_match=True))
            print(f'{filename}: {width}x{height}, {len(data)} bytes, historical hashes MATCH', flush=True)
        folder = ROOT / 'source'
        # Validate all pre-existing destinations before writing anything.
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
    (ROOT / 'source-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (ROOT / 'download-status.json').write_text(json.dumps({
        'status': 'downloaded_pending_visual_review', 'run_id': os.environ.get('GITHUB_RUN_ID'),
        'images_verified': True, 'historical_hashes_matched': True, 'count': 5,
    }, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        ROOT.mkdir(parents=True, exist_ok=True)
        (ROOT / 'download-status.json').write_text(json.dumps({
            'status': 'blocked_source_download', 'error_type': type(exc).__name__,
            'error': str(exc), 'run_id': os.environ.get('GITHUB_RUN_ID'),
            'share_url': SHARE_URL, 'images_verified': False,
        }, ensure_ascii=False, indent=2), encoding='utf-8')
        raise
