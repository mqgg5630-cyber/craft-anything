"""Download public note images with bounded validation; no login/cookies."""
import re,json,hashlib,urllib.request
from pathlib import Path
from download import fetch
ROOT=Path('deliveries/doraemon-dream-world/01-下载原图')
URL='https://www.rednote.com/discovery/item/6aedc91f0000000023004ff2?xsec_token=CBISbJnVDWPV9wo-NpRox3vlAiuJMLTnOqfIxdKkYl3ak=&xsec_source=app_share'
def main():
 ROOT.mkdir(parents=True,exist_ok=True)
 images=[{'urlDefault':f'https://sns-web-i10.rednotecdn.com/202611181652/{h}/spectrum/{t}!nd_dft_wlteh_webp_3'} for h,t in [
 ('e24ba896e28e143fa1416a1aa743c1cf','1040g34o3277svrit6a0g5p6u518g8mchqoa9prg'),
 ('e96762b50c44e6c8408e0861a9d8aea7','1040g34o3277svrit6a1g5p6u518g8mchi256gvo'),
 ('f54df2fcc472b131ebe98410b5cca236','1040g34o3277svrit6a005p6u518g8mchq24cob0'),
 ('a901e2757daddaaee898559db27461d0','1040g34o3277svrit6a105p6u518g8mchlsf30pg')]]
 record={'note_id':'6aedc91f0000000023004ff2','title':'✨哆啦A梦的奇妙世界','author':'一名努力向上的舞蹈老师','share_url':'https://xhslink.cn/o/4pNl4VJBJjX','source_caveat':'Public CDN derivatives, not author masters','images':[]}
 if len(images)!=4:raise ValueError(f'Expected four references, got {len(images)}')
 total=0
 for i,item in enumerate(images,1):
  urls=[x['url'] for x in item.get('infoList',[]) if x.get('url')]+[item.get('urlDefault',''),item.get('urlPre','')]
  good=[]
  for url in dict.fromkeys(urls):
   if not url:continue
   try:
    data,w,h,fmt=fetch(url);good.append((w*h,len(data),data,w,h,fmt,url))
   except (ValueError,OSError) as exc:
    with (ROOT/'download-errors.txt').open('a') as f:f.write(f'{i}: {url}: {exc}\n')
  if not good:raise RuntimeError(f'No image downloaded: {i}')
  _,_,data,w,h,fmt,url=max(good,key=lambda v:(v[0],v[1]));total+=len(data)
  if total>75*1024*1024:raise ValueError('Size cap')
  name=f'{i:02d}.{fmt}';(ROOT/name).write_bytes(data)
  record['images'].append({'file':name,'width':w,'height':h,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'source_url':url})
  (ROOT/'下载记录.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
  print(name,w,h,len(data),flush=True)
if __name__=='__main__':
 try:main()
 except Exception as exc:
  ROOT.mkdir(parents=True,exist_ok=True)
  (ROOT/'failure.txt').write_text(f'{type(exc).__name__}: {exc}')
  raise
