"""Public CDN download for the second note; uses the same bounded image validator."""
import hashlib
import json
from pathlib import Path
from download import fetch

ROOT = Path('deliveries/bears-261127')
TOKENS = [
 '1040g3k0327jao89a7g2g5pjd5dehotguk1o5u7g',
 '1040g3k0327jao89a7g005pjd5dehotgu5j97mi8',
 '1040g3k0327jao89a7g0g5pjd5dehotgur1k5n6o',
 '1040g3k0327jao89a7g105pjd5dehotgursc2ha8',
 '1040g3k0327jao89a7g1g5pjd5dehotgu5pp6ab0',
 '1040g3k0327jao89a7g205pjd5dehotgug4c4apg',
]


def main():
    folder = ROOT / '01-下载原图'
    folder.mkdir(parents=True, exist_ok=True)
    record = {'schema_version':1, 'note_id':'6af97d2600000000240306f9',
              'title':'261127', 'author':'Cppp壁纸',
              'share_url':'https://xhslink.cn/o/gdCTkloAC6',
              'source_caveat':'Public CDN response, not independently verified as author master.',
              'images':[]}
    total = 0
    for i, token in enumerate(TOKENS, 1):
        candidates = []
        for base in ['https://sns-img-bd.xhscdn.com/notes_pre_post/',
                     'https://ci.xiaohongshu.com/notes_pre_post/',
                     'https://sns-img-bd.xhscdn.com/']:
            url = base + token
            try:
                data, w, h, fmt = fetch(url)
                candidates.append((w*h,len(data),data,w,h,fmt,url))
            except (OSError, ValueError):
                print(f'Image {i}: candidate unavailable', flush=True)
        if not candidates:
            raise RuntimeError(f'No validated image for {i}')
        _,_,data,w,h,fmt,url = max(candidates,key=lambda v:(v[0],v[1]))
        total += len(data)
        if total > 75*1024*1024:
            raise ValueError('Job size cap reached')
        filename = f'{i:02d}.{fmt}'
        (folder/filename).write_bytes(data)
        record['images'].append({'file':filename,'width':w,'height':h,'bytes':len(data),
                                 'sha256':hashlib.sha256(data).hexdigest(),'source_url':url})
        print(f'{filename}: {w}x{h}, {len(data)} bytes',flush=True)
    (folder/'下载记录.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__ == '__main__':
    main()
