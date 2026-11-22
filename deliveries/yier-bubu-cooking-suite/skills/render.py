from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
import json,hashlib,subprocess,math
import imageio_ffmpeg
R=Path(__file__).resolve().parents[1];O=R/'images';O.mkdir(exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def txt(d,xy,t,size=30,fill='#ffffff'):d.text(xy,t,font=ImageFont.truetype(FONT,max(10,size)),fill=fill)
def ui(im,kind):
 a=im.copy();w,h=a.size;d=ImageDraw.Draw(a,'RGBA');s=w/1080
 def text(x,y,t,z=35):txt(d,(int(x*w),int(y*h)),t,max(12,int(z*s)))
 def rect(box,fill,r=24):d.rounded_rectangle(tuple(int(v*(w if j%2==0 else h)) for j,v in enumerate(box)),radius=max(4,int(r*s)),fill=fill)
 if kind=='lock':
  text(.08,.04,'9:41',32);text(.2,.13,'09:41',140);text(.28,.23,'MONDAY, NOVEMBER 16',27)
  rect((.07,.35,.93,.42),(255,255,255,80));text(.12,.37,'A quiet moment, just for you.',30)
 elif kind=='desktop':
  rect((0,0,1,.045),(36,29,52,190),0);text(.03,.009,'Desktop     File     View',23)
  rect((.32,.90,.68,.98),(255,255,255,150))
  for k in range(6):rect((.34+k*.052,.918,.373+k*.052,.967),(151+k*10,128,95,230),9)
 elif kind=='home':
  text(.08,.045,'09:41',32)
  for j in range(3):
   for k in range(4):
    x=.09+k*.23;y=.16+j*.13;rect((x,y,x+.12,y+.067),(231,216,190,210),26)
  rect((.06,.90,.94,.98),(255,247,226,130))
 elif kind=='watch':text(.16,.1,'09:41',130);text(.23,.29,'MON 16',45)
 elif kind=='chat':
  rect((0,0,1,.09),(245,242,249,245),0);txt(d,(int(w*.06),int(h*.035)),'<    Together',int(40*s),'#473650')
  for box,t in [((.08,.23,.65,.30),'Look at the evening sky.'),((.40,.36,.94,.43),'It is beautiful with you.')]:
   rect(box,(255,255,255,232));txt(d,(int((box[0]+.02)*w),int((box[1]+.025)*h)),t,int(27*s),'#493b58')
  rect((0,.93,1,1),(250,248,252,245),0)
 elif kind in ('wechat','qq'):
  rect((0,.61,1,1),(250,248,253,250),0);text(.06,.035,'<    '+('Moments' if kind=='wechat' else 'QQ Profile'),35)
  rect((.75,.52,.94,.65),(241,225,245,255));txt(d,(int(w*.08),int(h*.70)),'Yier & Bubu',int(48*s),'#493851');txt(d,(int(w*.08),int(h*.78)),'A little magic in everyday life.',int(28*s),'#83718d')
 return a

records=[]
def emit(im,name,source,process):
 p=O/name;im.convert('RGB').save(p,quality=96,subsampling=0) if p.suffix=='.jpg' else im.save(p)
 records.append(dict(file=name,source=source,size=list(im.size),process=process,md5=hashlib.md5(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
keys=['01-phone','02-desktop','03-ipad-landscape','04-ipad-portrait','05-watch','06-avatar-a','07-avatar-b','08-moments','09-qq-profile','10-chat']
labels=['01-手机','02-电脑','03-iPad横屏','04-iPad竖屏','05-手表方形','06-情头A白熊','07-情头B棕熊','08-朋友圈横幅','09-QQ主页横幅','10-聊天背景']
ims={k:Image.open(R/'masters'/f'{k}.png').convert('RGB') for k in keys}
CJK=R.parents[1]/'assets/fonts/cjk/NotoSansCJKsc-Regular.otf'
def centered(d,y,text,size,color,w):
 f=ImageFont.truetype(str(CJK),size);box=d.textbbox((0,0),text,font=f);d.text(((w-box[2]+box[0])/2,y-box[1]),text,font=f,fill=color)
chat=ims['10-chat'];w,h=chat.size;d=ImageDraw.Draw(chat)
centered(d,int(h*.15),'走过你的朝朝暮暮',32,'#fff1d7',w)
# Heart drawn with DejaVu glyph; CJK font does not contain every symbol.
f=ImageFont.truetype(str(CJK),30);heart=ImageFont.truetype(FONT,29)
parts=[('一二',f),('❤',heart),('布布',f)];widths=[d.textlength(t,font=ff) for t,ff in parts];xx=(w-sum(widths)-16)/2
for (t,ff),ww in zip(parts,widths):
 d.text((xx,int(h*.595)),t,font=ff,fill='#79543d');xx+=ww+8

for k,label in zip(keys,labels):
 im=ims[k];emit(im,label+'-无UI-原生.png',k,'native_with_typeset_no_crop' if k=='10-chat' else 'native_full_canvas_no_crop')
 kind='lock' if k.startswith('01') else 'desktop' if k.startswith('02') else 'home' if k.startswith(('03','04')) else 'watch' if k.startswith('05') else 'chat' if k.startswith('10') else None
 if kind:
  overlay=ui(im,kind)
  if k=='10-chat':
   overlay=im.copy();d=ImageDraw.Draw(overlay,'RGBA');w,h=im.size;ky=int(h*.64)
   d.rectangle((0,0,w,int(h*.07)),fill=(251,241,224,245));centered(d,int(h*.018),'〈  一二和布布',24,'#72543d',w)
   d.rectangle((0,ky,w,h),fill=(239,226,209,252));centered(d,ky+18,'输入法遮挡示意',23,'#86664c',w)
   for row,line in enumerate(['QWERTYUIOP','ASDFGHJKL','ZXCVBNM']):
    kw=int(w*.08);gap=int(w*.012);start=(w-(len(line)*kw+(len(line)-1)*gap))//2;yy=ky+80+row*64
    for num,c in enumerate(line):
     x=start+num*(kw+gap);d.rounded_rectangle((x,yy,x+kw,yy+50),radius=8,fill=(255,250,241,255));txt(d,(x+kw//3,yy+13),c,21,'#795b43')
  if k=='03-ipad-landscape':
   overlay=im.copy();d=ImageDraw.Draw(overlay,'RGBA');w,h=im.size
   txt(d,(35,22),'09:41',28)
   for yy in range(3):
    for xx in range(3):
     x=int(w*(.045+xx*.13));y=int(h*(.16+yy*.16));d.rounded_rectangle((x,y,x+60,y+60),radius=16,fill=(241,229,208,185))
  emit(overlay,label+'-UI模拟.jpg',k,'overlay_only_no_crop')
# Square avatars: retain ALL native pixels; circular mask appears in demonstration only.
for k,label in zip(keys[5:7],labels[5:7]):
 im=ims[k];canvas=Image.new('RGB',(1200,1320),'#ede1cd');thumb=im.resize((980,980),Image.Resampling.LANCZOS);mask=Image.new('L',thumb.size);ImageDraw.Draw(mask).ellipse((0,0,979,979),fill=255);canvas.paste(thumb,(110,70),mask);txt(ImageDraw.Draw(canvas),(290,1130),'PROFILE PREVIEW',42,'#796049');emit(canvas,label+'-圆形UI展示.jpg',k,'full_avatar_scaled_down_circle_mask_preview_only')
# Header clean art and profile screenshot intentionally DIFFERENT aspect ratios.
for k,label,title in [('08-moments','08-朋友圈','Moments'),('09-qq-profile','09-QQ主页','QQ Profile')]:
 im=ims[k];canvas=Image.new('RGB',(1080,1440),'#faf4e9');fit=ImageOps.contain(im,(1080,650),Image.Resampling.LANCZOS);canvas.paste(fit,((1080-fit.width)//2,80));d=ImageDraw.Draw(canvas);d.rectangle((0,0,1080,80),fill='#e4d1b7');txt(d,(35,22),'<     '+title,32,'#4c3b61');avatar=ims['06-avatar-a'].resize((160,160),Image.Resampling.LANCZOS);canvas.paste(avatar,(870,590));txt(d,(65,820),'Yier & Bubu',46,'#544065');txt(d,(65,910),'A little magic, every day.',28,'#84718e');emit(canvas,label+'-主页UI模拟.jpg',k,'whole_header_contain_no_scene_crop')
emit(ui(ims['01-phone'],'home'),'11-手机桌面-UI模拟.jpg','01-phone','overlay_only_no_crop')
watch=Image.new('RGB',(396,484),'#dbc4a6');watch.paste(ims['05-watch'].resize((396,396),Image.Resampling.LANCZOS),(0,88));emit(watch,'12-手表竖屏-无UI.png','05-watch','whole_square_scaled_down_plus_top_clock_safe_matte');emit(ui(watch,'watch'),'12-手表竖屏-UI模拟.jpg','05-watch','whole_square_plus_matte_and_overlay')
for k,label in [('06-avatar-a','A白熊'),('07-avatar-b','B棕熊')]:
 im=ims['01-phone'].copy();portrait=ims[k].resize((180,180),Image.Resampling.LANCZOS);im.paste(portrait,(55 if label.startswith('A') else im.width-235,430));emit(im,'13-情侣壁纸-'+label+'-无UI.png',k+' + 01-phone','full_avatar_badge_scaled_down_over_phone_scene_no_face_crop');emit(ui(im,'lock'),'13-情侣壁纸-'+label+'-UI模拟.jpg',k+' + 01-phone','full_avatar_composite_with_clock')
# Optional standard-resolution exports, from corresponding dedicated canvas, no crop.
for k,size,label in [('01-phone',(1440,2560),'14-手机1440p'),('02-desktop',(3840,2160),'15-电脑4K导出'),('03-ipad-landscape',(2732,2048),'16-iPad横屏导出'),('04-ipad-portrait',(2048,2732),'17-iPad竖屏导出')]:
 src=ims[k];im=ImageOps.pad(src,size,Image.Resampling.LANCZOS,color=src.getpixel((0,0)));emit(im,label+'-无UI.png',k,'full_canvas_contain_tiny_ratio_padding_interpolation_not_native_4k')
# Animation references phone native composition. No figure motion claimed.
base=ims['01-phone'].resize((720,1280),Image.Resampling.LANCZOS);mp=O/'18-动态光点-720p.mp4';ff=imageio_ffmpeg.get_ffmpeg_exe();p=subprocess.Popen([ff,'-y','-f','rawvideo','-vcodec','rawvideo','-s','720x1280','-pix_fmt','rgb24','-r','16','-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(mp)],stdin=subprocess.PIPE,stderr=subprocess.DEVNULL);frames=[]
for j in range(64):
 im=base.copy();d=ImageDraw.Draw(im,'RGBA')
 for t in range(18):
  x=int((t*.618%1)*720);y=int((t*.381+j/64)%1*1280);d.ellipse((x-2,y-2,x+2,y+2),fill=(255,245,255,90))
 p.stdin.write(im.tobytes())
 if j%2==0:frames.append(im.resize((270,480)))
p.stdin.close();assert p.wait()==0
frames[0].save(O/'18-动态预览-低清.gif',save_all=True,append_images=frames[1:],duration=125,loop=0)
for name,size in [('18-动态光点-720p.mp4',[720,1280]),('18-动态预览-低清.gif',[270,480])]:
 p=O/name;records.append(dict(file=name,source='01-phone',size=size,process='periodic_particles_no_character_animation',md5=hashlib.md5(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
(R/'素材清单.json').write_text(json.dumps(dict(generation_calls=10,theme_count=1,native_dimensions={k:list(v.size) for k,v in ims.items()},rules='No face crop enlargement. Dedicated source per use. Native images retained. UI generic simulation. 4K exports are interpolation, not native 4K.',files=records),ensure_ascii=False,indent=2))
print('DONE',len(records),'independent assets')

# Regenerable overview. Individual files above remain the actual deliverables.
board=Image.new('RGB',(2200,1550),'#f0e5d4');d=ImageDraw.Draw(board)
txt(d,(60,35),'YIER & BUBU / COOKING TOGETHER',44,'#594b3c')
names=['02-电脑-UI模拟.jpg','03-iPad横屏-UI模拟.jpg','04-iPad竖屏-UI模拟.jpg','01-手机-UI模拟.jpg','05-手表方形-UI模拟.jpg','06-情头A白熊-无UI-原生.png','07-情头B棕熊-无UI-原生.png','08-朋友圈横幅-无UI-原生.png','09-QQ主页横幅-无UI-原生.png','10-聊天背景-UI模拟.jpg']
for i,n in enumerate(names):
 x=45+i%5*430;y=150+i//5*680;im=Image.open(O/n);im.thumbnail((395,590));board.paste(im,(x+(395-im.width)//2,y));txt(d,(x,y+605),n.split('-')[0]+' / '+n.split('-')[1].encode('ascii','ignore').decode(),22,'#76614b')
board.save(R/'02-全套UI效果总览.jpg',quality=95)
