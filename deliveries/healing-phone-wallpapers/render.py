from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
import hashlib,json
R=Path(__file__).parent
W,H=1080,2347
brush='assets/fonts/mashanzheng/MaShanZheng-Regular.ttf'
latin='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
# Values are relative positions on the final image; brush font and small seal evoke the reference without reproducing its text.
config=[('日子顺遂',.30,.60,'vertical'),('喜乐常伴',.55,.56,'vertical'),('好事将至',.71,.54,'vertical'),('万事从容',.58,.57,'vertical'),('花开有时',.50,.68,'horizontal'),('心向暖阳',.29,.62,'vertical'),('慢慢生活',.53,.53,'horizontal'),('岁岁安然',.58,.58,'vertical'),('自有花期',.30,.60,'vertical'),('温柔以待',.40,.61,'vertical')]
for folder in ('images','ui'): (R/folder).mkdir(exist_ok=True)
records=[]
for i,(words,x,y,layout) in enumerate(config,1):
 f=R/f'generated/{i:02}.png'; im=Image.open(f).convert('RGB'); centering=(.35,.5) if i in (3,8) else ((.65,.5) if i==4 else (.5,.5))
 im=ImageOps.fit(im,(W,H),Image.Resampling.LANCZOS,centering=centering)
 d=ImageDraw.Draw(im); size=91 if layout=='vertical' else 99; font=ImageFont.truetype(brush,size)
 if layout=='vertical':
  for n,c in enumerate(words): d.text((int(W*x),int(H*y)+n*103),c,font=font,fill='#292a26',anchor='mm')
  sx=int(W*x)+53; sy=int(H*y)+385
 else:
  d.text((int(W*x),int(H*y)),words,font=font,fill='#292a26',anchor='mm');sx=int(W*x)+158; sy=int(H*y)+65
 d.rectangle((sx,sy,sx+25,sy+28),fill='#aa5444'); d.text((sx+12,sy+13),'福',font=ImageFont.truetype(brush,19),fill='#f7eee1',anchor='mm')
 p=R/f'images/{i:02}.png';im.save(p,optimize=True)
 ui=im.copy();d=ImageDraw.Draw(ui);d.text((W//2,100),'Monday, August 18',font=ImageFont.truetype(latin,37),fill='#4c4943',anchor='mt');d.text((W//2,150),'9:41',font=ImageFont.truetype(latin,150),fill='#4c4943',anchor='mt')
 for cx in (125,W-125): d.ellipse((cx-46,H-165,cx+46,H-73),fill='#817c74')
 d.polygon([(113,H-141),(137,H-141),(132,H-121),(132,H-100),(118,H-100),(118,H-121)],fill='white')
 d.rounded_rectangle((W-147,H-133,W-103,H-106),radius=4,fill='white');d.ellipse((W-133,H-130,W-117,H-114),fill='#817c74')
 ui.save(R/f'ui/{i:02}.png',optimize=True)
 files=[]
 for folder in ('generated','images','ui'):
  p=R/f'{folder}/{i:02}.png'; b=p.read_bytes()
  with Image.open(p) as check: check.load(); dims=check.size
  if folder!='generated': assert dims==(W,H)
  files.append({'path':str(p.relative_to(R)),'dimensions':dims,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'md5':hashlib.md5(b).hexdigest()})
 records.append({'index':i,'words':words,'crop_center':centering,'files':files})
assert len({x['files'][1]['sha256'] for x in records})==10
(R/'output-manifest.json').write_text(json.dumps({'target_size':[W,H],'size_basis':'All nine public reference images are 1080 × 2347','method':'Proportional fill crop and resize; added Chinese typography and simulated lock screen UI','images':records},ensure_ascii=False,indent=2)+'\n')
font=ImageFont.truetype(latin,24)
for folder,name in [('images','00-无UI总览.jpg'),('ui','00-模拟UI总览.jpg'),('source','00-原片总览.jpg')]:
 fs=sorted((R/folder).glob('*')); out=Image.new('RGB',(1500,1100),'#f5f1e9'); d=ImageDraw.Draw(out)
 for n,f in enumerate(fs):
  img=Image.open(f).convert('RGB');img.thumbnail((260,465),Image.Resampling.LANCZOS); x=20+n%5*296+(260-img.width)//2;y=20+n//5*540;out.paste(img,(x,y));d.text((150+n%5*296,y+478),f.stem,font=font,anchor='mt',fill='#665d58')
 out.save(R/name,quality=92,subsampling=0)
