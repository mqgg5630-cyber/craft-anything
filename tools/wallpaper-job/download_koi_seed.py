"""Fetch three carousel URLs observed on the public note page; run on Actions."""
import hashlib
import json
from pathlib import Path
from download import fetch

ROOT = Path('deliveries/koi-dream')

def main():
    seed=json.loads((ROOT/'source-seed.json').read_text(encoding='utf-8'))
    if len(seed['image_urls']) != 3 or len(set(seed['image_urls'])) != 3:
        raise ValueError('Expected three distinct public note carousel URLs')
    results=[]; total=0
    for i,url in enumerate(seed['image_urls'],1):
        data,w,h,fmt=fetch(url)
        total+=len(data)
        if total>60*1024*1024: raise ValueError('Total exceeds 60 MiB')
        rec={'file':f'source/{i:02d}.{fmt}','format':fmt,'width':w,'height':h,'bytes':len(data),'md5':hashlib.md5(data).hexdigest(),'sha256':hashlib.sha256(data).hexdigest(),'source_url':url}
        results.append((data,rec)); print(f'Validated {i}: {w}x{h} {fmt} {len(data)} bytes',flush=True)
    if len({rec['sha256'] for _,rec in results}) != 3: raise ValueError('Duplicate image bytes')
    folder=ROOT/'source'
    if folder.exists() and any(folder.iterdir()): raise RuntimeError('Refusing to overwrite sources')
    folder.mkdir(exist_ok=True)
    for data,rec in results: (ROOT/rec['file']).write_bytes(data)
    manifest={k:v for k,v in seed.items() if k!='image_urls'}
    manifest.update({'status':'downloaded_pending_visual_review','download_method':'GitHub Actions; public page carousel URLs; bounded decode','images':[r for _,r in results]})
    (ROOT/'source-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {'status':'success','image_count':len(results)}

if __name__=='__main__':
    try:
        result=main()
    except Exception as exc:
        result={'status':'blocked_source_download','error_type':type(exc).__name__,'message':str(exc)[:300]}
        (ROOT/'download-status.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        raise
    (ROOT/'download-status.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
