import json,re,urllib.request,hashlib
from pathlib import Path
from download import fetch
R=Path('deliveries/yier-bubu-comics/01-参考原片');R.mkdir(parents=True,exist_ok=True)
url='https://www.xiaohongshu.com/explore/6aea9153000000000300512f?xsec_token=CBUQ6bixdDbmt3azmTLpvFUcluztlPkDXCHFxXqUfEzFM=&xsec_source=app_share'
html=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=45).read().decode()
(R/'source.html').write_text(html)
m=re.search(r'window\.__INITIAL_STATE__\s*=\s*(.*)</script>',html)
state=json.loads(m.group(1).replace(':undefined',':null')) if m else {}
notes=state.get('note',{}).get('noteDetailMap',{})
images=[]
for v in notes.values():
 images=v.get('note',{}).get('imageList',[])
 if images:break
if not images:images=[{'urlDefault':'https://sns-web-i10.rednotecdn.com/202611191023/a0c9411f9ab19ce014208ddf4c98cce0/spectrum/1040g0k03274oc1at6i005o9jfl9gkfja6590c98!nd_dft_wlteh_webp_3'}]
record=[]
for i,item in enumerate(images,1):
 urls=[item.get('urlDefault','')]+[x.get('url','') for x in item.get('infoList',[])];err=[]
 for u in urls:
  try:
   data,w,h,fmt=fetch(u);p=R/f'{i:02}.{fmt}';p.write_bytes(data);record.append({'file':p.name,'width':w,'height':h,'sha256':hashlib.sha256(data).hexdigest(),'url':u});break
  except Exception as e:err.append(str(e))
 else:raise RuntimeError(err)
(R/'下载记录.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
print('downloaded',len(record))
