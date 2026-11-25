"""Actions-only public source job for the user's New Year Blessings note.

Reuses the existing bounded public-note validator; never requests the note or
images in the agent sandbox. Other deliveries remain immutable and separate.
"""
from pathlib import Path
import urllib.error
import download_sunset as engine

SHARE_URL = 'https://xhslink.cn/o/3kQq76Fee2O'
ROOT = Path('deliveries/new-year-blessings-10')
_parse_note = engine.parse_note


def parse_note(html, final_url):
    return _parse_note(html, final_url, title_hint='新年')


def main():
    previous = (engine.ROOT, engine.SHARE_URL, engine.parse_note, engine.PUBLIC_NOTE_URLS[:])
    try:
        engine.ROOT = ROOT
        engine.SHARE_URL = SHARE_URL
        engine.PUBLIC_NOTE_URLS.clear()
        engine.parse_note = parse_note
        engine.main()
    finally:
        engine.ROOT, engine.SHARE_URL, engine.parse_note = previous[:3]
        engine.PUBLIC_NOTE_URLS[:] = previous[3]


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        if isinstance(exc, urllib.error.HTTPError):
            message = f'Public endpoint returned HTTP {exc.code}'
        elif isinstance(exc, ValueError):
            message = str(exc)[:180].replace('\n', ' ')
        else:
            message = type(exc).__name__
        print(f'::error title=New Year Blessings public download blocked::{message}', flush=True)
        raise SystemExit(1)
