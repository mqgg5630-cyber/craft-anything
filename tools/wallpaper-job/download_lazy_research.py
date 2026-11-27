"""Retrieve public character reference images on GitHub Actions."""
from pathlib import Path
from download import fetch
import json,hashlib
R=Path('deliveries/lazy-sheep-ten-scenes')
seed=json.loads((R/'research-seed.json').read_text())
out=R/'research'; out.mkdir(exist_ok=True)
records=[]
for i,k in enumerate(('character_reference','official_crossover_reference'),1):
 data,w,h,fmt=fetch(seed[k]); p=out/f'{i:02d}.{fmt}'
 if p.exists(): raise RuntimeError('Refusing overwrite')
 p.write_bytes(data);records.append({'path':str(p.relative_to(R)),'url':seed[k],'size':[w,h],'bytes':len(data),'md5':hashlib.md5(data).hexdigest(),'sha256':hashlib.sha256(data).hexdigest()});print(i,w,h,fmt,len(data))
(R/'research-manifest.json').write_text(json.dumps({'sources':records,'status':'downloaded_pending_visual_review'},ensure_ascii=False,indent=2)+'\n')
