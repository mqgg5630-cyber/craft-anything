"""Retrieve and validate public character research images in Actions."""
from pathlib import Path
from urllib.request import Request, urlopen
from PIL import Image
import io, json, hashlib
R=Path('deliveries/lazy-sheep-ten-scenes')
seed=json.loads((R/'research-seed.json').read_text())
out=R/'research'; out.mkdir(exist_ok=True)
records=[]; errors=[]
for i,k in enumerate(('character_reference','official_crossover_reference'),1):
 try:
  request=Request(seed[k],headers={'User-Agent':'Mozilla/5.0','Referer':seed['reference_page' if i==1 else 'official_crossover_page']})
  with urlopen(request,timeout=25) as resp: data=resp.read(12*1024*1024+1)
  if len(data)>12*1024*1024: raise ValueError('Size exceeds cap')
  with Image.open(io.BytesIO(data)) as img: img.verify()
  with Image.open(io.BytesIO(data)) as img: w,h=img.size; fmt=img.format.lower()
  if min(w,h)<100: raise ValueError('Unexpectedly small reference')
  p=out/f'{i:02d}.{fmt}'; p.write_bytes(data)
  records.append({'path':str(p.relative_to(R)),'url':seed[k],'size':[w,h],'bytes':len(data),'md5':hashlib.md5(data).hexdigest(),'sha256':hashlib.sha256(data).hexdigest()});print(i,w,h,fmt,len(data),flush=True)
 except Exception as e:
  errors.append({'source':k,'type':type(e).__name__,'message':str(e)[:300]});print(errors[-1],flush=True)
(R/'research-manifest.json').write_text(json.dumps({'sources':records,'errors':errors,'status':'downloaded_pending_visual_review' if records else 'blocked'},ensure_ascii=False,indent=2)+'\n')
if not records: raise RuntimeError('All research downloads failed')
