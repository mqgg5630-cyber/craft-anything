"""Public CDN download for the second note; uses the same bounded image validator."""
import hashlib
import json
from pathlib import Path
from download import fetch

ROOT = Path('deliveries/sakura-white-veil')
TOKENS = ['1040g3k8326j8isnml0b05p34u8pahcqa5p9ipl8', '1040g3k8326j8isnml0705p34u8pahcqa5hslv18', '1040g3k8326j8isnml07g5p34u8pahcqajgs7368', '1040g3k8326j8isnml0805p34u8pahcqa5410nto', '1040g3k8326j8isnml08g5p34u8pahcqag7blvbo', '1040g3k8326j8isnml0905p34u8pahcqa5ou2rug', '1040g3k8326j8isnml09g5p34u8pahcqae4bbqg8', '1040g3k8326j8isnml0a05p34u8pahcqaelrb2qo', '1040g3k8326j8isnml0ag5p34u8pahcqaqmotsqo']


def main():
    folder = ROOT / '01-下载原图'
    folder.mkdir(parents=True, exist_ok=True)
    record = {'schema_version':1, 'note_id':'6ad8a6ba00000000310375b1',
              'title':'以白纱誓约的方式打开魔卡少女樱', 'author':'云野原',
              'share_url':'https://xhslink.cn/o/AUULQrW380N',
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
