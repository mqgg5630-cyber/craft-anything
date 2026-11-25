from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont,ImageFilter
import hashlib,json
R=Path(__file__).parent; W,H=1080,2343
BRUSH='assets/fonts/mashanzheng/MaShanZheng-Regular.ttf'; LATIN='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
blessings=[('岁岁安宁','事事从容'),('福满人间','喜上眉梢'),('心怀热爱','日有清欢'),('财运渐丰','福气盈门'),('安然向暖','四季皆欢'),('愿得所愿','行有坦途'),('平安常伴','幸福相随'),('诸事和顺','喜乐长留'),('繁花有期','好梦成真'),('万事欣然','福泽绵长')]
for f in ('images','ui'): (R/f).mkdir(exist_ok=True)
records=[]
for i,(right,left) in enumerate(blessings,1):
 f=R/f'generated/{i:02}.png'; img=Image.open(f).convert('RGB'); img=ImageOps.fit(img,(W,H),Image.Resampling.LANCZOS,centering=(.5,.5)).convert('RGBA')
 # Both translucent paper slips preserve the source paper texture instead of flat opaque rectangles.
 shadow=Image.new('RGBA',(W,H));d=ImageDraw.Draw(shadow)
 dx=(-12,0,10,-7,6,-8,8,-4,5,0)[i-1]
 slips=[(int(W*.66)+dx,int(H*.345),int(W*.66)+dx+188,int(H*.88)),(int(W*.25)-dx,int(H*.49),int(W*.25)-dx+188,int(H*.985))]
 for x0,y0,x1,y1 in slips: d.rectangle((x0+8,y0+5,x1+8,y1+7),fill=(87,64,39,31))
 img=Image.alpha_composite(img,shadow.filter(ImageFilter.GaussianBlur(8)))
 layer=Image.new('RGBA',(W,H));d=ImageDraw.Draw(layer)
 for x0,y0,x1,y1 in slips: d.rectangle((x0,y0,x1,y1),fill=(255,236,209,155))
 img=Image.alpha_composite(img,layer);d=ImageDraw.Draw(img)
 font=ImageFont.truetype(BRUSH,137); sealfont=ImageFont.truetype(BRUSH,38)
 for (x0,y0,x1,y1),phrase in zip(slips,(right,left)):
  cx=(x0+x1)//2
  for j,c in enumerate(phrase):
   d.text((cx,y0+132+j*177),c,font=font,fill=(38,32,27,255),anchor='mm')
  # A small red seal printed onto each strip, with newly typeset 福 rather than source marks.
  sx,sy=cx-31,y1-115
  d.rectangle((sx,sy,sx+62,sy+62),outline=(156,66,48,165),width=3)
  d.text((cx,sy+31),'福',font=sealfont,fill=(156,66,48,165),anchor='mm')
 # Small circular red seal in open upper paper.
 cx,cy=W//2,int(H*.20);red=(163,80,57,125)
 d.ellipse((cx-36,cy-36,cx+36,cy+36),outline=red,width=3)
 d.text((cx,cy),'喜',font=ImageFont.truetype(BRUSH,37),fill=red,anchor='mm')
 img=img.convert('RGB');img.save(R/f'images/{i:02}.png',optimize=True)
 ui=img.copy();d=ImageDraw.Draw(ui);dark='#4d4639'
 d.text((W//2,95),'Monday, August 18',font=ImageFont.truetype(LATIN,36),fill=dark,anchor='mt')
 d.text((W//2,145),'9:41',font=ImageFont.truetype(LATIN,150),fill=dark,anchor='mt')
 for cx in (112,W-112):d.ellipse((cx-43,H-155,cx+43,H-69),fill='#8d806b')
 d.polygon([(100,H-134),(124,H-134),(120,H-116),(120,H-96),(104,H-96),(104,H-116)],fill='#fff8e9')
 d.rounded_rectangle((W-132,H-126,W-92,H-102),radius=3,fill='#fff8e9');d.ellipse((W-119,H-123,W-105,H-109),fill='#8d806b')
 ui.save(R/f'ui/{i:02}.png',optimize=True)
 files=[]
 for folder in ('generated','images','ui'):
  p=R/f'{folder}/{i:02}.png';b=p.read_bytes()
  with Image.open(p) as im:im.load();size=list(im.size)
  if folder!='generated': assert size==[W,H]
  files.append({'path':str(p.relative_to(R)),'size':size,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'md5':hashlib.md5(b).hexdigest()})
 records.append({'index':i,'right_column':right,'left_column':left,'files':files})
assert len({r['files'][1]['sha256'] for r in records})==10
(R/'output-manifest.json').write_text(json.dumps({'target_size':[W,H],'target_basis':'all four public reference images are 1080 x 2343','method':'AI backgrounds proportionally cropped and resampled, paper slips, new blessing text and seals overlaid; lockscreen UI is a static mockup','images':records},ensure_ascii=False,indent=2)+'\n')
font=ImageFont.truetype(LATIN,24)
for folder,name in [('images','00-无UI总览.jpg'),('ui','00-模拟UI总览.jpg'),('source','00-原片总览.jpg')]:
 fs=sorted((R/folder).iterdir());out=Image.new('RGB',(1500,1100),'#f5f1e9');d=ImageDraw.Draw(out)
 for n,f in enumerate(fs):
  im=Image.open(f).convert('RGB'); im.thumbnail((260,465),Image.Resampling.LANCZOS);x=20+n%5*296+(260-im.width)//2;y=20+n//5*540;out.paste(im,(x,y));d.text((150+n%5*296,y+478),f.stem,font=font,anchor='mt',fill='#665d58')
 out.save(R/name,quality=92,subsampling=0)
