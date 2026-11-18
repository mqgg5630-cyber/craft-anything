"""Retrieve the nine public slides of the user-supplied white-veil note.

Runs on the user's existing GitHub branch because the local sandbox does not
have direct access to the image CDN.  No cookies, login, or paid media are used.
Each downloaded response is verified as a decodable image and recorded with a
hash. Public CDN renditions are not necessarily the creator's master files.
"""

import hashlib
import html
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image

NOTE = 'https://xhslink.cn/o/AUULQrW380N'
NOTE_ID = '6ad8a6ba00000000310375b1'
TOKENS = [
    '1040g3k8326j8isnml0b05p34u8pahcqa5p9ipl8',
    '1040g3k8326j8isnml0705p34u8pahcqa5hslv18',
    '1040g3k8326j8isnml07g5p34u8pahcqajgs7368',
    '1040g3k8326j8isnml0805p34u8pahcqa5410nto',
    '1040g3k8326j8isnml08g5p34u8pahcqag7blvbo',
    '1040g3k8326j8isnml0905p34u8pahcqa5ou2rug',
    '1040g3k8326j8isnml09g5p34u8pahcqae4bbqg8',
    '1040g3k8326j8isnml0a05p34u8pahcqaelrb2qo',
    '1040g3k8326j8isnml0ag5p34u8pahcqaqmotsqo',
]
OUT = Path('deliveries/white-veil/01-下载原图')
MAX_IMAGE = 12 * 1024 * 1024
MAX_TOTAL = 75 * 1024 * 1024
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Referer': 'https://www.xiaohongshu.com/',
    'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
}


def page_urls(page):
    """Find fresh, public rendition URLs, but only for the nine known slide IDs."""
    text = html.unescape(page.replace('\\/', '/').replace('\\u002F', '/'))
    matches = re.findall(r'https://sns-web-i10\.(?:rednotecdn|xhscdn)\.com/'
                         r'[^\s"\'<>\\]+', text)
    result = {}
    for token in TOKENS:
        for url in matches:
            if re.search(r'/' + re.escape(token) + r'(?:!|\?|$)', url):
                result[token] = url
                break
    return result


def render_public_page():
    """Load the same public share URL in a normal, disposable headless browser."""
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        print('No headless browser is installed on the runner.', flush=True)
        return ''
    with tempfile.TemporaryDirectory(prefix='white-veil-browser-') as directory:
        output = Path(directory) / 'page.html'
        try:
            with output.open('wb') as stream:
                result = subprocess.run(
                    [chrome, '--headless=new', '--disable-gpu', '--no-sandbox',
                     '--disable-dev-shm-usage', '--virtual-time-budget=10000',
                     '--user-data-dir=' + str(Path(directory) / 'profile'),
                     '--dump-dom', NOTE],
                    stdout=stream, stderr=subprocess.DEVNULL, timeout=45, check=False)
            if result.returncode:
                print(f'Browser exited with status {result.returncode}.', flush=True)
                return ''
            with output.open('rb') as stream:
                return stream.read(4 * 1024 * 1024).decode('utf-8', 'replace')
        except (OSError, subprocess.TimeoutExpired):
            print('Browser was unavailable or timed out.', flush=True)
            return ''


def fetch_image(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=20) as response:
        data = response.read(MAX_IMAGE + 1)
    if len(data) > MAX_IMAGE:
        raise ValueError('image exceeds byte cap')
    with Image.open(io.BytesIO(data)) as image:
        image.verify()
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        width, height, fmt = image.width, image.height, image.format.lower()
    if min(width, height) < 300 or fmt not in ('png', 'jpeg', 'webp'):
        raise ValueError('unexpected size or image format')
    return data, width, height, fmt


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(NOTE, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=25) as response:
            page = response.read(4 * 1024 * 1024).decode('utf-8', 'replace')
            final = urllib.parse.urlsplit(response.geturl() if hasattr(response, 'geturl') else NOTE)
        signed = page_urls(page)
        print(f'Public page host/path: {final.netloc}{final.path}; '
              f'{len(page)} chars, {sum(t in page for t in TOKENS)} known image IDs, '
              f'{len(signed)} signed URLs.', flush=True)
        if not signed:
            rendered = render_public_page()
            signed = page_urls(rendered)
            print(f'Rendered public page: {len(rendered)} chars, '
                  f'{sum(t in rendered for t in TOKENS)} known image IDs, '
                  f'{len(signed)} signed URLs.', flush=True)
            if not signed and ('<title>安全限制</title>' in rendered or
                               'Sorry, This Page Isn\'t Available Right Now.' in rendered):
                raise RuntimeError('The note returned a security restriction; stopped')
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise RuntimeError('The public note rate-limited the request; stopped') from exc
        signed = {}
        print(f'The note page returned HTTP {exc.code}; trying the known public image IDs.', flush=True)
    except (OSError, ValueError):
        signed = {}
        print('Could not read the note page; trying the known public image IDs.', flush=True)

    record = {'schema_version': 1, 'note_id': NOTE_ID, 'note_url': NOTE,
              'title': '以白纱誓约的方式打开魔卡少女樱', 'author': '云野原',
              'caveat': 'Public CDN renditions, not verified creator masters. '
                        'The note has nine slides; a tenth design must be labelled as an addition.',
              'images': []}
    total = 0
    for index, token in enumerate(TOKENS, 1):
        urls = [signed.get(token),
                f'https://sns-img-bd.xhscdn.com/notes_pre_post/{token}',
                f'https://ci.xiaohongshu.com/notes_pre_post/{token}',
                f'https://sns-webpic-qc.xhscdn.com/notes_pre_post/{token}?imageView2/2/w/2560/format/png']
        candidates = []
        for url in filter(None, urls):
            try:
                data, width, height, fmt = fetch_image(url)
                candidates.append((width * height, len(data), data, width, height, fmt, url))
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    raise RuntimeError('CDN rate-limited the request; stopped without retrying') from exc
                print(f'Slide {index}: a rendition returned HTTP {exc.code}', flush=True)
            except (OSError, ValueError, Image.DecompressionBombError):
                print(f'Slide {index}: a rendition was unavailable or invalid', flush=True)
        if not candidates:
            raise RuntimeError(f'No valid rendition for slide {index}; results incomplete')
        _, _, data, width, height, fmt, url = max(candidates, key=lambda row: (row[0], row[1]))
        total += len(data)
        if total > MAX_TOTAL:
            raise ValueError('total download byte cap reached')
        name = f'{index:02d}.{fmt}'
        (OUT / name).write_bytes(data)
        record['images'].append({'file': name, 'width': width, 'height': height,
                                 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                                 'public_image_id': token, 'source_host': urllib.parse.urlsplit(url).netloc})
        (OUT / 'download-record.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'{name}: {width}x{height}, {len(data)} bytes, verified', flush=True)
    print(f'Complete: {len(record["images"])} public slides, {total} bytes', flush=True)


if __name__ == '__main__':
    main()
