from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont
import hashlib, json
ROOT=Path(__file__).parent
TARGET=(884,1851)
FONT=Path('assets/fonts/cjk/NotoSansCJKsc-Regular.otf')
REFS={1:1,2:2,3:3,4:4,5:5,6:6,7:7,8:8,9:9,10:1}
for folder in ('images','ui'): (ROOT/folder).mkdir(exist_ok=True)
for i in range(1,11):
 f=ROOT/f'generated/{i:02}.png'
 with Image.open(f) as src:
  src=src.convert('RGB')
  if i==5:
   # Keep every animal on the ledge: scale to width, extend matching cream above and below.
   h=round(src.height*TARGET[0]/src.width); src=src.resize((TARGET[0],h),Image.Resampling.LANCZOS)
   sample=src.getpixel((10,10)); im=Image.new('RGB',TARGET,sample); im.paste(src,(0,(TARGET[1]-h)//2))
  else: im=ImageOps.fit(src,TARGET,method=Image.Resampling.LANCZOS,centering=(.5,.5))
 d=ImageDraw.Draw(im)
 def text(x,y,value,size,color,anchor='mm'):
  d.text((int(TARGET[0]*x),int(TARGET[1]*y)),value,font=ImageFont.truetype(str(FONT),size),fill=color,anchor=anchor,stroke_width=0)
 def vertical(x,y,value,size,color,step=.047):
  for n,c in enumerate(value): text(x,y+step*n,c,size,color)
 if i==1: vertical(.19,.49,'万事善意',51,'#37352f'); text(.26,.68,'福',30,'#b63d35')
 if i==2: vertical(.79,.47,'平安喜乐',53,'#a6453b'); text(.70,.65,'福',30,'#bf5547')
 if i==3:
  text(.5,.49,'发财被爱',55,'#fff7e9'); text(.5,.55,'好运常在',55,'#fff7e9')
 if i==4:
  text(.27,.66,'生活就要',39,'#f4bfbe');text(.32,.70,'开心快乐',39,'#f4bfbe');text(.36,.74,'好运就来啦',37,'#f4bfbe')
 if i==5:
  text(.5,.38,'希望你快乐',51,'#714e3e');text(.5,.43,'今天 明天 每天',45,'#714e3e')
 if i==6:
  text(.5,.67,'揣着热爱 奔赴山海',38,'#fff9ff');text(.5,.72,'美好如期而至',44,'#fff9ff')
 if i==7: text(.5,.72,'少说话 多挣钱',49,'#a36a36')
 if i==8:
  text(.5,.65,'多喜乐  长安宁',51,'#342723');text(.5,.72,'凡事发生皆有益',31,'#9d4c35')
 if i==9: text(.5,.40,'马到成功',80,'#ad271e')
 if i==10: vertical(.24,.46,'福运绵长',49,'#6e5a3b')
 p=ROOT/f'images/{i:02}.png';im.save(p)
 ui=im.copy(); d=ImageDraw.Draw(ui); color='#fdf8f3' if i==4 else '#634e44'
 font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
 d.text((442,105),'Monday, August 18',font=ImageFont.truetype(font,28),fill=color,anchor='mt')
 d.text((442,150),'9:41',font=ImageFont.truetype(font,116),fill=color,anchor='mt')
 for x in (112,772):
  y=1720;r=39;d.ellipse((x-r,y-r,x+r,y+r),fill='#77706d')
 d.polygon([(102,1705),(122,1705),(117,1720),(117,1735),(107,1735),(107,1720)],fill='white')
 d.rounded_rectangle((754,1711,790,1733),radius=4,fill='white');d.ellipse((766,1714,778,1726),fill='#77706d')
 ui.save(ROOT/f'ui/{i:02}.png')
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',24)
for folder,name in [('images','00-无UI总览.jpg'),('ui','00-模拟UI总览.jpg'),('source','00-原片总览.jpg')]:
 fs=sorted((ROOT/folder).glob('*'));rows=(len(fs)+4)//5; sheet=Image.new('RGB',(1500,rows*550+20),'#f5f1e9');d=ImageDraw.Draw(sheet)
 for n,f in enumerate(fs):
  im=Image.open(f).convert('RGB');im.thumbnail((260,455),Image.Resampling.LANCZOS);x=20+n%5*296+(260-im.width)//2;y=20+n//5*550;sheet.paste(im,(x,y));d.text((150+n%5*296,y+466),f.stem,font=font,anchor='mt',fill='#665d58')
 sheet.save(ROOT/name,quality=92,subsampling=0)
records=[]
for i in range(1,11):
 paths=[ROOT/f'{folder}/{i:02}.png' for folder in ('generated','images','ui')]; vals=[]
 for p in paths:
  b=p.read_bytes()
  with Image.open(p) as im: im.load(); size=list(im.size)
  vals.append({'path':str(p.relative_to(ROOT)),'size':size,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'md5':hashlib.md5(b).hexdigest()})
 assert vals[1]['size']==list(TARGET) and vals[2]['size']==list(TARGET)
 records.append({'index':i,'fresh_reference':f'source/{REFS[i]:02}.webp','koi_reference':'../koi-dream/source/01.webp' if i in (1,3) else '../koi-dream/source/03.webp','files':vals,'fit_method':'proportional scale and top/bottom extension' if i==5 else 'proportional center-crop and resize'})
assert len({r['files'][1]['sha256'] for r in records})==10
(ROOT/'output-manifest.json').write_text(json.dumps({'target_size':TARGET,'target_basis':'fresh source 01 public CDN size; sources differ','images':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
