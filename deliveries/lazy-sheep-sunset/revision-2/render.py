from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
import hashlib,json,zipfile
R=Path(__file__).parent; W,H=852,1848
for d in ('images','ui'): (R/d).mkdir(exist_ok=True)
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'; items=[]
scenes=['海边灯塔','苹果园','山间露营','湖畔','樱花公园','乡间车站','花园','河畔单车','风车山坡','小镇庭院']
for i,scene in enumerate(scenes,1):
 im=Image.open(R/f'generated/{i:02}.png').convert('RGB')
 im=ImageOps.fit(im,(W,H),Image.Resampling.LANCZOS,centering=(.5,.5))
 im.save(R/f'images/{i:02}.png',optimize=True)
 mock=im.copy();d=ImageDraw.Draw(mock)
 d.text((W//2,86),'Monday, August 18',font=ImageFont.truetype(font,28),fill='#fff9e7',stroke_width=1,stroke_fill='#5d4433',anchor='mt')
 d.text((W//2,120),'9:41',font=ImageFont.truetype(font,118),fill='#fff9e7',stroke_width=2,stroke_fill='#60442b',anchor='mt')
 for cx in (94,W-94): d.ellipse((cx-35,H-132,cx+35,H-62),fill='#7a6b4e')
 d.polygon([(84,H-117),(104,H-117),(100,H-102),(100,H-83),(88,H-83),(88,H-102)],fill='white')
 d.rounded_rectangle((W-110,H-112,W-78,H-92),radius=3,fill='white'); d.ellipse((W-100,H-109,W-88,H-97),fill='#7a6b4e')
 mock.save(R/f'ui/{i:02}.png',optimize=True)
 files=[]
 for folder in ('generated','images','ui'):
  p=R/f'{folder}/{i:02}.png'; b=p.read_bytes()
  with Image.open(p) as ck: ck.load(); size=ck.size
  if folder!='generated': assert size==(W,H)
  files.append({'path':str(p.relative_to(R)),'size':list(size),'bytes':len(b),'md5':hashlib.md5(b).hexdigest(),'sha256':hashlib.sha256(b).hexdigest()})
 items.append({'index':i,'scene':scene,'references':['../source/01.webp','../../lazy-sheep-ten-scenes/research/01.jpeg'],'files':files})
assert len({x['files'][1]['sha256'] for x in items})==10
(R/'output-manifest.json').write_text(json.dumps({'target_size':[W,H],'method':'AI outputs proportionally cropped and resampled to target; simulated UI added separately','images':items},ensure_ascii=False,indent=2)+'\n')
lab=ImageFont.truetype(font,24)
for folder,name in [('images','00-无UI总预览.jpg'),('ui','00-模拟UI总预览.jpg')]:
 fs=sorted((R/folder).glob('*.png')); canvas=Image.new('RGB',(1500,1100),'#f5f1e9');d=ImageDraw.Draw(canvas)
 for n,f in enumerate(fs):
  m=Image.open(f).convert('RGB');m.thumbnail((260,465),Image.Resampling.LANCZOS); x=20+n%5*296+(260-m.width)//2;y=20+n//5*540;canvas.paste(m,(x,y));d.text((150+n%5*296,y+478),f.stem,font=lab,anchor='mt',fill='#665d58')
 canvas.save(R/name,quality=92,subsampling=0)
 Path('.cache/lazy-sheep-sunset').mkdir(parents=True,exist_ok=True)
 archive=Path('.cache/lazy-sheep-sunset')/f'{folder}.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for f in fs: z.write(f,f.name)
 with zipfile.ZipFile(archive) as z: assert len(z.namelist())==10 and z.testzip() is None
m=json.loads((R.parent/'source-manifest.json').read_text());m['status']='downloaded_and_visually_reviewed';(R.parent/'source-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
