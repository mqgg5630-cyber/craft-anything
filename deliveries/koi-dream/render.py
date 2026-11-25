from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json, hashlib
root=Path(__file__).parent
if (root/'output-manifest.json').exists():
 raise SystemExit('Already rendered: refusing to re-crop or overwrite finished images')
cn='assets/fonts/cjk/NotoSansCJKsc-Regular.otf'
serif='/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
# Independent generated image 02 has a stray synthetic credit; remove just the bottom strip.
p=root/'images/02.png'
im=Image.open(p); im.crop((0,0,im.width,im.height-24)).save(p)
# Add the same four-character blessing as the source's circular-koi design.
for i in range(6,11):
 p=root/f'images/{i:02}.png'; im=Image.open(p).convert('RGB'); d=ImageDraw.Draw(im); w,h=im.size
 font=ImageFont.truetype(cn,round(w*.038)); chars='时来运转'; gap=round(w*.045); center=w//2
 for n,c in enumerate(chars): d.text((center+(n-1.5)*gap,int(h*.91)),c,font=font,anchor='mm',fill='#815b24')
 d.line((int(w*.38),int(h*.939),int(w*.62),int(h*.939)),fill='#ac874c',width=max(1,w//500))
 im.save(p)
(root/'ui').mkdir(exist_ok=True)
records=[]
for i in range(1,11):
 p=root/f'images/{i:02}.png'; im=Image.open(p).convert('RGB'); w,h=im.size; d=ImageDraw.Draw(im)
 font=ImageFont.truetype(serif,int(w*.155)); small=ImageFont.truetype(serif,int(w*.032)); color=(115,77,32)
 d.text((w//2,int(h*.064)),'Sun 11 Oct',font=small,fill=color,anchor='mt')
 d.text((w//2,int(h*.09)),'9:41',font=font,fill=color,anchor='mt')
 for x in (.13,.87):
  cx,cy=int(w*x),int(h*.942);r=int(w*.043);d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(179,173,160))
 cx,cy=int(w*.13),int(h*.942);r=int(w*.043)
 d.polygon([(cx-r*.25,cy-r*.35),(cx+r*.25,cy-r*.35),(cx+r*.12,cy),(cx+r*.12,cy+r*.36),(cx-r*.12,cy+r*.36),(cx-r*.12,cy)],fill='white')
 cx=int(w*.87);d.rounded_rectangle((cx-r*.42,cy-r*.23,cx+r*.42,cy+r*.30),radius=3,fill='white');d.ellipse((cx-r*.15,cy-r*.12,cx+r*.15,cy+r*.18),fill=(160,153,140))
 ui=root/f'ui/{i:02}.png'; im.save(ui,optimize=True)
 def info(f):
  b=f.read_bytes(); return {'bytes':len(b),'md5':hashlib.md5(b).hexdigest(),'sha256':hashlib.sha256(b).hexdigest()}
 records.append({'file':str(p.relative_to(root)),'reference':'source/01.webp' if i<=5 else 'source/03.webp','width':w,'height':h,**info(p),'ui_file':str(ui.relative_to(root)),'ui':info(ui)})
for folder,title in [('images','00-无UI总览.jpg'),('ui','00-模拟UI总览.jpg'),('source','00-原片总览.jpg')]:
 files=sorted((root/folder).glob('*')); rows=(len(files)+4)//5
 sheet=Image.new('RGB',(1500,rows*550+20),'#f3f0e8');d=ImageDraw.Draw(sheet);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',24)
 for i,f in enumerate(files):
  im=Image.open(f).convert('RGB');im.thumbnail((260,455),Image.Resampling.LANCZOS);x=20+(i%5)*296+(260-im.width)//2;y=20+(i//5)*550;sheet.paste(im,(x,y));d.text((150+(i%5)*296,y+466),f.stem,font=font,fill='#7e6b4a',anchor='mt')
 sheet.save(root/title,quality=92,subsampling=0)
(root/'output-manifest.json').write_text(json.dumps({'images':records,'count':len(records),'note':'02 cropped 24 bottom pixels to remove a generated stray credit; 06–10 have post-added Chinese blessing; UI is a static mockup'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
