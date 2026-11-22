"""Fetch only public note images on GitHub Actions; never needs cookies."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.request
from urllib.parse import urlparse
from PIL import Image
from download import fetch

ROOT = Path('deliveries/lululu-sunset-b7')
SHARE_URL = 'https://xhslink.cn/o/5thkO8Kd6jg'


def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('Download is allowed only on GitHub Actions')
    request = urllib.request.Request(SHARE_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(request, timeout=35) as response:
        body = response.read(8 * 1024 * 1024 + 1)
        final_url = response.url
    if len(body) > 8 * 1024 * 1024:
        raise ValueError('Page exceeds size limit')
    html = body.decode('utf-8')
    match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(.*?)</script>', html, re.S)
    if not match:
        raise RuntimeError('Public note state unavailable; stop without bypassing access restrictions')
    state = json.loads(re.sub(r'\bundefined\b', 'null', match.group(1).strip().rstrip(';')))
    details = state.get('note', {}).get('noteDetailMap', {})
    notes = [detail.get('note', {}) for detail in details.values()]
    notes = [note for note in notes if note.get('imageList')]
    if len(notes) != 1:
        def shape(value, depth=0):
            if depth > 3:
                return type(value).__name__
            if isinstance(value, dict):
                return {key: shape(child, depth + 1) for key, child in value.items()}
            if isinstance(value, list):
                return [shape(value[0], depth + 1)] if value else []
            return type(value).__name__
        raise RuntimeError(f'Expected one unambiguous public note, found {len(notes)}; '
                           f'page_path={urlparse(final_url).path}; state_shape={json.dumps(shape(state))}')
    note = notes[0]
    note_id = note.get('noteId', '')
    if not note_id or note_id not in final_url:
        raise RuntimeError('Resolved note identity does not match page state')
    images = note['imageList']
    if not 1 <= len(images) <= 30:
        raise RuntimeError('Unexpected carousel count')
    manifest = {
        'schema_version': 1, 'share_url': SHARE_URL, 'final_url': final_url,
        'note_id': note_id, 'title': note.get('title'), 'description': note.get('desc'),
        'author': note.get('user', {}).get('nickname'),
        'download_method': 'GitHub Actions public page and bounded image fetch',
        'run_id': os.environ.get('GITHUB_RUN_ID'),
        'branch': os.environ.get('GITHUB_REF_NAME'),
        'source_quality': 'Public CDN display files, not independently verified author master files',
        'status': 'downloaded_pending_visual_review', 'images': [],
    }
    total = 0
    seen = set()
    with tempfile.TemporaryDirectory() as temp:
        stage = Path(temp)
        for item in images:
            identity = item.get('fileId') or item.get('urlDefault')
            if identity in seen:
                continue
            seen.add(identity)
            candidates = [item.get('urlDefault', ''), item.get('urlPre', '')]
            candidates += [entry.get('url', '') for entry in item.get('infoList', [])]
            best = None
            for url in dict.fromkeys(candidates):
                host = urlparse(url).hostname or ''
                if not url.startswith('https://') or not any(host.endswith('.' + domain) for domain in ('xhscdn.com', 'rednotecdn.com', 'xiaohongshu.com')):
                    continue
                try:
                    data, width, height, fmt = fetch(url)
                    with Image.open(io.BytesIO(data)) as decoded:
                        decoded.load()
                    candidate = (width * height, len(data), data, width, height, fmt, url)
                    if best is None or candidate[:2] > best[:2]:
                        best = candidate
                except (OSError, ValueError, Image.DecompressionBombError) as exc:
                    print('Candidate unavailable:', type(exc).__name__, flush=True)
            if best is None:
                raise RuntimeError(f'No verified image for item {len(manifest["images"]) + 1}')
            _, _, data, width, height, fmt, url = best
            total += len(data)
            if total > 75 * 1024 * 1024:
                raise ValueError('Job exceeds 75 MiB')
            filename = f'{len(manifest["images"]) + 1:02d}.{fmt}'
            (stage / filename).write_bytes(data)
            manifest['images'].append({'file': f'source/{filename}', 'source_url': url,
                'width': width, 'height': height, 'format': fmt, 'bytes': len(data),
                'md5': hashlib.md5(data).hexdigest(), 'sha256': hashlib.sha256(data).hexdigest()})
            print(f'{filename}: {width}x{height}, {len(data)} bytes', flush=True)
        if not manifest['images']:
            raise RuntimeError('No verified sources')
        # No deliverable is written until the entire carousel passed validation.
        folder = ROOT / 'source'
        folder.mkdir(parents=True, exist_ok=True)
        for path in stage.iterdir():
            target = folder / path.name
            if target.exists() and target.read_bytes() != path.read_bytes():
                raise RuntimeError('Refusing to overwrite different source')
        for path in stage.iterdir():
            (folder / path.name).write_bytes(path.read_bytes())
    manifest['reference_count_downloaded'] = len(manifest['images'])
    (ROOT / 'source-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')


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
