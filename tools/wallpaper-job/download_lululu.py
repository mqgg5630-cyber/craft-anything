"""Reuse the previously successful public-note GitHub runner download path.
No credentials/cookies. Only public note images, bounded by existing fetch().
Targets the "和你一起奔夕阳 噜噜噜妹壁纸" post (note 6ad212fc000000001802d6be).
"""
import hashlib
import json
import re
import urllib.request
from pathlib import Path
from download import fetch

ROOT = Path('deliveries/lululu-sunset-10')
NOTE_ID = '6ad212fc000000001802d6be'
SHARE_URL = 'https://xhslink.cn/o/5thkO8Kd6jg'


def main():
    manifest_path = ROOT / 'source-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    urls = [[u] for u in manifest['image_urls']]
    # Resolve again on runner: signed CDN URLs in earlier page reads may expire.
    try:
        req = urllib.request.Request(SHARE_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=35) as response:
            html = response.read(8 * 1024 * 1024).decode('utf-8')
        match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(.*?)</script>', html, re.S)
        if match:
            state = json.loads(re.sub(r'\bundefined\b', 'null', match.group(1).strip().rstrip(';')))
            details = state.get('note', {}).get('noteDetailMap', {})
            for detail in details.values():
                note = detail.get('note', {})
                if note.get('noteId', NOTE_ID) != NOTE_ID:
                    continue
                images = note.get('imageList', [])
                if images:
                    urls = [[item.get('urlDefault', '')] + [v.get('url', '') for v in item.get('infoList', [])] for item in images]
                    break
    except (OSError, ValueError) as exc:
        print('Public page refresh unavailable:', type(exc).__name__, flush=True)
    if len(urls) != 5:
        raise RuntimeError(f'Expected the 5 observed carousel images, got {len(urls)}')
    folder = ROOT / 'source'
    folder.mkdir(exist_ok=True)
    records = []
    total = 0
    for index, candidates in enumerate(urls, 1):
        valid = []
        for url in dict.fromkeys(u for u in candidates if u.startswith('https://')):
            try:
                data, width, height, fmt = fetch(url)
                valid.append((width * height, len(data), data, width, height, fmt, url))
            except (OSError, ValueError) as exc:
                print(f'Image {index}: candidate unavailable: {type(exc).__name__}', flush=True)
        if not valid:
            raise RuntimeError(f'No validated public image for item {index}')
        _, _, data, width, height, fmt, url = max(valid, key=lambda item: item[:2])
        total += len(data)
        if total > 36 * 1024 * 1024:
            raise ValueError('Combined source files exceed 36 MiB')
        name = f'{index:02d}.{fmt}'
        path = folder / name
        if path.exists() and path.read_bytes() != data:
            raise RuntimeError(f'Refusing to overwrite different source: {name}')
        path.write_bytes(data)
        records.append({'file': f'source/{name}', 'width': width, 'height': height,
                        'bytes': len(data), 'md5': hashlib.md5(data).hexdigest(),
                        'sha256': hashlib.sha256(data).hexdigest(), 'source_url': url})
        print(f'Image {index}: {width}x{height}, {len(data)} bytes', flush=True)
    manifest.update(status='downloaded_pending_visual_review', reference_count_downloaded=len(records),
                    source_quality='Validated public CDN files; not independently verified author master files.',
                    download_method='GitHub Actions runner, existing bounded fetch validator', images=records)
    manifest.pop('blocker', None)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
