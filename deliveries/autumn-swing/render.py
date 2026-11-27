from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
import hashlib,json
R=Path(__file__).parent; W,H=852,1848
for d in ('images','ui'): (R/d).mkdir(exist_ok=True)
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'; items=[]
for i in range(1,11):
 im=Image.open(R/f'generated/{i:02}.png').convert('RGB')
 # Center crop maintains proportions. Landscape-like 04/05/10 are shifted left to keep the lamb comfortably in frame.
 centering=(.05,.5) if i==4 else ((.38,.5) if i in (5,10) else (.5,.5))
 im=ImageOps.fit(im,(W,H),Image.Resampling.LANCZOS,centering=centering)
 im.save(R/f'images/{i:02}.png',optimize=True)
 mock=im.copy();d=ImageDraw.Draw(mock);d.text((W//2,86),'Monday, August 18',font=ImageFont.truetype(font,28),fill='#fff9e7',stroke_width=1,stroke_fill='#5d4433',anchor='mt');d.text((W//2,120),'9:41',font=ImageFont.truetype(font,118),fill='#fff9e7',stroke_width=2,stroke_fill='#60442b',anchor='mt')
 for cx in (94,W-94):d.ellipse((cx-35,H-132,cx+35,H-62),fill='#7a6b4e')
 d.polygon([(84,H-117),(104,H-117),(100,H-102),(100,H-83),(88,H-83),(88,H-102)],fill='white')
 d.rounded_rectangle((W-110,H-112,W-78,H-92),radius=3,fill='white');d.ellipse((W-100,H-109,W-88,H-97),fill='#7a6b4e')
 mock.save(R/f'ui/{i:02}.png',optimize=True)
 files=[]
 for folder in ('generated','images','ui'):
  p=R/f'{folder}/{i:02}.png';b=p.read_bytes()
  with Image.open(p) as check:check.load();size=check.size
  if folder!='generated':assert size==(W,H)
  files.append({'path':str(p.relative_to(R)),'size':list(size),'bytes':len(b),'md5':hashlib.md5(b).hexdigest(),'sha256':hashlib.sha256(b).hexdigest()})
 items.append({'index':i,'reference':'source/01.webp','crop_center':centering,'files':files})
assert len({x['files'][1]['sha256'] for x in items})==10
(R/'output-manifest.json').write_text(json.dumps({'target_size':[W,H],'target_basis':'public reference image 01, 852x1848','method':'AI variations proportionally cropped and resampled to target; static UI added separately','images':items},ensure_ascii=False,indent=2)+'\n')
lab=ImageFont.truetype(font,24)
for folder,name in [('images','00-无UI总预览.jpg'),('ui','00-模拟UI总预览.jpg'),('source','00-参考原图预览.jpg')]:
 fs=sorted((R/folder).iterdir()); rows=(len(fs)+4)//5; canvas=Image.new('RGB',(1500,rows*540+20),'#f5f1e9');d=ImageDraw.Draw(canvas)
 for n,f in enumerate(fs):
  m=Image.open(f).convert('RGB');m.thumbnail((260,465),Image.Resampling.LANCZOS); x=20+n%5*296+(260-m.width)//2;y=20+n//5*540;canvas.paste(m,(x,y));d.text((150+n%5*296,y+478),f.stem,font=lab,anchor='mt',fill='#665d58')
 canvas.save(R/name,quality=92,subsampling=0)
p=R/'source-manifest.json';m=json.loads(p.read_text());m['status']='downloaded_and_visually_reviewed';p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
