"""Offline integrity verification and contact sheet; no network requests."""
from pathlib import Path
import json, hashlib
from PIL import Image, ImageOps, ImageDraw, ImageFont
R=Path(__file__).resolve().parent
NAMES=['草地野餐','一起烘焙','雨天共伞','花园秋千','海边沙堡','阳台观星','温室浇花','泡泡浴','旋转木马','雪地伙伴']
def inspect(p):
 data=p.read_bytes()
 with Image.open(p) as im: im.verify()
 with Image.open(p) as im: im.load();w,h=im.size;fmt=im.format.lower()
 return dict(file=str(p.relative_to(R)),width=w,height=h,format=fmt,bytes=len(data),md5=hashlib.md5(data).hexdigest(),sha256=hashlib.sha256(data).hexdigest())
def verify():
 m=json.loads((R/'source-manifest.json').read_text())
 assert len(m['images'])==5
 for item in m['images']:
  a=inspect(R/item['file'])
  for key in ['width','height','format','bytes','md5','sha256']:assert a[key]==item[key],(item['file'],key)
 paths=sorted((R/'images').glob('*.png'));assert [p.name for p in paths]==[f'{i:02}.png' for i in range(1,11)]
 records=[dict(inspect(p),scene=NAMES[i],references=['source/02.webp','source/03.webp'],text_policy='No lettering, slogans, watermark or UI') for i,p in enumerate(paths)]
 assert len({i['sha256'] for i in records})==10
 old=json.loads((R.parent/'lululu-cute-65mKtkE8Uk/output-manifest.json').read_text())
 assert not {i['sha256'] for i in records}&{i['sha256'] for i in old['files']}
 for item in records:assert item['height']>item['width'] and item['format']=='png'
 return records
if __name__=='__main__':
 records=verify()
 manifest=R/'output-manifest.json'
 previous=json.loads(manifest.read_text()) if manifest.exists() else {}
 manifest.write_text(json.dumps(dict(generated_count=10,original_source_count=5,used_reference_count=2,independent_generation=True,quality='AI reference-based new scenes; model native PNG, no upscaling; not author originals',visual_review=previous.get('visual_review','pending'),files=records),ensure_ascii=False,indent=2)+'\n')
 fontpath=R.parents[1]/'assets/fonts/cjk/NotoSansCJKsc-Regular.otf'
 font=ImageFont.truetype(str(fontpath),28);small=ImageFont.truetype(str(fontpath),19)
 board=Image.new('RGB',(1396,1160),'#fff8ee');d=ImageDraw.Draw(board)
 d.text((16,24),'噜噜和噜妹 · 第二轮10个新场景 · 无字版',font=font,fill='#735765')
 for i,item in enumerate(records):
  x=16+(i%5)*276;y=96+(i//5)*528
  with Image.open(R/item['file']) as im:board.paste(ImageOps.contain(im.convert('RGB'),(260,466),Image.Resampling.LANCZOS),(x,y))
  d.text((x,y+476),f'{i+1:02} · {NAMES[i]}',font=small,fill='#735765')
 board.save(R/'00-10张新场景总预览.jpg',quality=94)
 (R/'local-verification.json').write_text(json.dumps(dict(source_count=5,used_reference_count=2,output_count=10,all_decoded=True,source_hashes_match=True,outputs_unique=True,no_previous_output_reused=True,sizes=sorted({(i['width'],i['height']) for i in records})),indent=2)+'\n')
 print('PASS: 5 intact sources; 10 decoded unique new outputs; all hashes recorded')
