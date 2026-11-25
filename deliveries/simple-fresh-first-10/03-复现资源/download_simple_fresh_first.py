"""Actions-only download of ONLY the first image of the user's fresh-style note."""
import json
from pathlib import Path
import urllib.error
import download_sunset as engine

SHARE_URL='https://xhslink.cn/o/24CQFIRp9Er'
ROOT=Path('deliveries/simple-fresh-first-10')
_parse_note=engine.parse_note
_selection={}


def parse_note(html,final_url):
    note=_parse_note(html,final_url,title_hint='清新')
    _selection['observed_carousel_count']=len(note['imageList'])
    selected=dict(note)
    selected['imageList']=note['imageList'][:1]
    return selected


def main():
    previous=(engine.ROOT,engine.SHARE_URL,engine.parse_note,engine.PUBLIC_NOTE_URLS[:])
    _selection.clear()
    try:
        engine.ROOT=ROOT;engine.SHARE_URL=SHARE_URL
        engine.PUBLIC_NOTE_URLS.clear();engine.parse_note=parse_note
        engine.main()
        path=ROOT/'source-manifest.json'
        m=json.loads(path.read_text())
        m.update(reference_image_index=1,selection='First carousel image only; other images not downloaded or used.',
                 observed_carousel_count=_selection.get('observed_carousel_count'),
                 other_carousel_images_downloaded=False)
        path.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        engine.ROOT,engine.SHARE_URL,engine.parse_note=previous[:3]
        engine.PUBLIC_NOTE_URLS[:]=previous[3]


if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        if isinstance(exc,urllib.error.HTTPError):
            message=f'Public endpoint returned HTTP {exc.code}'
        elif isinstance(exc,ValueError):
            message=str(exc)[:180].replace('\n',' ')
        else:
            message=type(exc).__name__
        print(f'::error title=Fresh first-image download blocked::{message}',flush=True)
        raise SystemExit(1)
