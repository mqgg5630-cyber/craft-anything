"""Fetch the five public carousel files on Actions, validating before writing."""
import hashlib
import json
import re
import urllib.request
from pathlib import Path
from download import fetch

ROOT = Path('deliveries/lululu-sunset-new')

def main():
    seed = json.loads((ROOT / 'source-seed.json').read_text(encoding='utf-8'))
    candidates = [[url] for url in seed['image_urls']]
    try:
        req = urllib.request.Request(seed['share_url'], headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=35) as response:
            page = response.read(8 * 1024 * 1024).decode('utf-8')
        match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(.*?)</script>', page, re.S)
        if match:
            state = json.loads(re.sub(r'\bundefined\b', 'null', match.group(1).strip().rstrip(';')))
            for detail in state.get('note', {}).get('noteDetailMap', {}).values():
                note = detail.get('note', {})
                if note.get('noteId') == seed['note_id'] and len(note.get('imageList', [])) == 5:
                    for existing, item in zip(candidates, note['imageList']):
                        existing[:0] = [item.get('urlDefault', '')] + [v.get('url', '') for v in item.get('infoList', [])]
                    break
    except (OSError, ValueError) as exc:
        print('Page refresh unavailable:', type(exc).__name__, flush=True)
    if len(candidates) != 5:
        raise ValueError('Expected five reference images')
    images, records, total = [], [], 0
    for index, urls in enumerate(candidates, 1):
        valid = []
        for url in dict.fromkeys(u for u in urls if u.startswith('https://')):
            try:
                data, width, height, fmt = fetch(url)
                valid.append((width * height, len(data), data, width, height, fmt, url))
            except (OSError, ValueError) as exc:
                print(f'Image {index}: unavailable: {type(exc).__name__}', flush=True)
        if not valid:
            raise RuntimeError(f'No validated public image for item {index}; nothing written')
        _, _, data, width, height, fmt, url = max(valid, key=lambda item: item[:2])
        total += len(data)
        if total > 36 * 1024 * 1024:
            raise ValueError('Combined images exceed 36 MiB')
        name = f'{index:02d}.{fmt}'
        images.append((name, data))
        records.append({'file': f'source/{name}', 'format': fmt, 'width': width, 'height': height,
                        'bytes': len(data), 'md5': hashlib.md5(data).hexdigest(),
                        'sha256': hashlib.sha256(data).hexdigest(), 'source_url': url})
        print(f'Image {index}: {width}x{height}, {len(data)} bytes', flush=True)
    target = ROOT / 'source'
    if target.exists() and any(target.iterdir()):
        raise RuntimeError('Refusing to overwrite existing source files')
    target.mkdir(exist_ok=True)
    for name, data in images:
        (target / name).write_bytes(data)
    manifest = {key: seed[key] for key in ('share_url', 'note_id', 'title', 'author')}
    manifest.update(status='downloaded_pending_visual_review', images=records,
                    source_quality='Public CDN files; not independently verified author master files.',
                    download_method='GitHub Actions; bounded image validation')
    (ROOT / 'source-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

if __name__ == '__main__':
    main()
