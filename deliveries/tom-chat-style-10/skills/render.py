from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1];ROOT=R.parents[1];OUT=R/'images';OUT.mkdir(exist_ok=True)
CJK=ROOT/'assets/fonts/cjk/NotoSansCJKsc-Regular.otf';LAT=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
NAMES=['蜂蜜奶油格纹','蜜桃情书','焦糖咖啡馆','奶黄雏菊','玫瑰奶昔蝴蝶结','杏色落日窗','奶油复古手账','燕麦鼠尾草','可可晚安灯串','香草草莓野餐']
SHIFTS=[.11,.09,.09,.12,.12,.14,.12,.14,.12,.16]
COLORS=['#876046','#9a5b51','#795337','#8c6e32','#9d5d68','#88552f','#8c694d','#716a49','#fff0d3','#975b42']
def font(n,cjk=True):return ImageFont.truetype(str(CJK if cjk else LAT),n)
def center(d,y,t,f,fill,w):
 box=d.textbbox((0,0),t,font=f);d.text(((w-(box[2]-box[0]))/2,y-box[1]),t,font=f,fill=fill)
records=[];previews=[]
for i,(name,shift,color) in enumerate(zip(NAMES,SHIFTS,COLORS),1):
 src=Image.open(R/'masters'/f'{i:02}.png').convert('RGB');w,h=src.size;dy=round(h*shift)
 # Shift intact subject upward; remove ONLY top blank/decorative margin, never crop faces.
 im=src.copy();im.paste(src.crop((0,dy,w,h)),(0,0))
 # Continue the existing low-contrast bottom texture below the main illustration.
 strip=src.crop((0,h-100,w,h))
 for y in range(h-dy,h,100):im.paste(strip.crop((0,0,w,min(100,h-y))),(0,y))
 d=ImageDraw.Draw(im)
 if i==10:
  d.rounded_rectangle((w*.18,h*.035,w*.82,h*.10),radius=18,fill='#fff2de')
 center(d,round(h*.055),'走过你的朝朝暮暮',font(33),color,w)
 center(d,round(h*.59),'tom❤jerry',font(29,False),'#79583f' if i==9 else color,w)
 p=OUT/f'{i:02}-{name}.png';im.save(p)
 records.append(dict(file=p.name,native_size=[w,h],output_size=[w,h],shift_up_pixels=dy,quote='走过你的朝朝暮暮',names='tom❤jerry',keyboard_preview_starts_at=.64,md5=hashlib.md5(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
 # Keyboard simulation is preview only, never burned into delivered background.
 preview=im.copy().convert('RGBA');layer=Image.new('RGBA',im.size);dd=ImageDraw.Draw(layer);ky=round(h*.64);dd.rectangle((0,ky,w,h),fill=(244,235,222,250));center(dd,ky+22,'输入法遮挡区域 · 示意',font(23),'#8c7863',w)
 for row,line in enumerate(['QWERTYUIOP','ASDFGHJKL','ZXCVBNM']):
  kw=round(w*.082);gap=round(w*.012);start=(w-(len(line)*kw+(len(line)-1)*gap))//2;y=ky+90+row*70
  for k,c in enumerate(line):
   x=start+k*(kw+gap);dd.rounded_rectangle((x,y,x+kw,y+55),radius=9,fill=(255,252,247,255));dd.text((x+kw*.3,y+13),c,font=font(23,False),fill='#7c6a58')
 dd.rounded_rectangle((w*.2,ky+310,w*.8,ky+360),radius=10,fill=(255,252,247,255));previews.append(Image.alpha_composite(preview,layer).convert('RGB'))
board=Image.new('RGB',(2000,1700),'#ede1cf');d=ImageDraw.Draw(board);center(d,28,'Tom & Jerry｜10款暖色聊天背景',font(44),'#6d513b',2000);center(d,91,'人物上移 · 浪漫文案 · 下方输入法遮挡示意',font(25),'#8b7158',2000)
for i,(im,name) in enumerate(zip(previews,NAMES)):
 x=30+(i%5)*395;y=155+(i//5)*765;im.thumbnail((365,650));board.paste(im,(x+(365-im.width)//2,y));d.text((x+8,y+670),f'{i+1:02}  {name}',font=font(25),fill='#674d39')
board.save(R/'00-10款风格选择总览.jpg',quality=95)
(R/'素材清单.json').write_text(json.dumps(dict(status='awaiting_user_style_selection',selected_style=None,generation_calls=10,files=records,warning='Keyboard position is approximate; no chosen default until user selects. Source blank margin shifted, no face crop enlargement. Text added with Noto CJK and DejaVu.'),ensure_ascii=False,indent=2))
for rec in records:
 p=OUT/rec['file']
 with Image.open(p) as im:im.load();assert list(im.size)==rec['output_size']
 assert hashlib.md5(p.read_bytes()).hexdigest()==rec['md5']
print('PASS ten PNGs decoded/hash/size; 10 distinct native sources; style not selected')
