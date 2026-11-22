from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance
import json, hashlib, math, subprocess, base64, mimetypes, io
import imageio_ffmpeg
R=Path(__file__).resolve().parents[1]
OUT=R/'sets'; OUT.mkdir(exist_ok=True)
NAMES=['湖阶心锁','樱花列车','浮光书庭','旋木暮歌','纸舟花河','月下秋千','星伞喷泉','草莓小憩','湖畔弦音','海风缎带']
FACES=[(.49,.575,.66,.575),(.48,.61,.66,.57),(.48,.59,.67,.59),(.48,.43,.62,.42),(.52,.60,.70,.58),(.39,.56,.67,.54),(.42,.55,.64,.55),(.32,.50,.70,.50),(.48,.53,.66,.51),(.49,.57,.70,.55)]
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def txt(d,xy,t,size=30,fill='#ffffff'):d.text(xy,t,font=ImageFont.truetype(FONT,size),fill=fill)
def save(im,p):
 if p.suffix=='.png':im.save(p)
 else:im.convert('RGB').save(p,quality=95,subsampling=0)
def layout(src,size,mode='contain',side='center'):
 w,h=size
 # Portrait: edge-to-edge contain via tightly bounded aspect crop, keeping top sky.
 if w/h <= .80:
  return ImageOps.fit(src,size,Image.Resampling.LANCZOS,centering=(.5,.30))
 # Wide/square: intentional editorial layout, never stretch figures or invent scenery.
 sky=src.crop((0,0,src.width,max(1,src.height//8))).resize((1,1)).getpixel((0,0))
 bg=Image.new('RGB',size,sky);d=ImageDraw.Draw(bg)
 for yy in range(h):
  t=yy/h; c=tuple(round(sky[j]*(1-t*.25)+(239,221,237)[j]*t*.25) for j in range(3));d.line((0,yy,w,yy),fill=c)
 fit=ImageOps.contain(src,(w,h),Image.Resampling.LANCZOS)
 x=w-fit.width if side=='right' or w/h>1.2 else (w-fit.width)//2
 bg.paste(fit,(x,0))
 # Restrained geometric botanical motif in the clear icon zone, not fake outpainting.
 if w/h>1.2:
  for k in range(7):
   xx=int(w*(.06+.035*k));yy=int(h*(.74+.025*(k%3)));rr=max(3,w//250)
   d.ellipse((xx-rr,yy-rr,xx+rr,yy+rr),fill='#edd8ed')
 return bg

def ui(im,kind):
 a=im.copy();w,h=a.size;d=ImageDraw.Draw(a,'RGBA');s=w/1080
 def text(x,y,t,z=35):txt(d,(int(x*w),int(y*h)),t,max(12,int(z*s)))
 def rect(box,fill,r=24):d.rounded_rectangle(tuple(int(v*(w if j%2==0 else h)) for j,v in enumerate(box)),radius=max(4,int(r*s)),fill=fill)
 if kind=='lock':
  text(.08,.04,'9:41',32);text(.2,.13,'09:41',140);text(.28,.23,'MONDAY, NOVEMBER 16',27)
  rect((.07,.78,.93,.86),(255,255,255,80));text(.12,.8,'A quiet moment, just for you.',30)
 elif kind=='desktop':
  rect((0,0,1,.045),(36,29,52,190),0);text(.03,.009,'Desktop     File     View',23)
  rect((.32,.90,.68,.98),(255,255,255,150))
  for k in range(6):rect((.34+k*.052,.918,.373+k*.052,.967),(135+k*12,120,177,230),9)
 elif kind=='home':
  text(.08,.045,'09:41',32)
  for j in range(3):
   for k in range(4):
    x=.09+k*.23;y=.16+j*.13;rect((x,y,x+.12,y+.067),(222,213,239,210),26)
  rect((.06,.90,.94,.98),(255,255,255,130))
 elif kind=='watch':text(.16,.1,'09:41',130);text(.23,.29,'MON 16',45)
 elif kind=='chat':
  rect((0,0,1,.09),(245,242,249,245),0);txt(d,(int(w*.06),int(h*.035)),'<    Together',int(40*s),'#473650')
  for box,t in [((.08,.23,.65,.30),'Look at the evening sky.'),((.40,.36,.94,.43),'It is beautiful with you.')]:
   rect(box,(255,255,255,232));txt(d,(int((box[0]+.02)*w),int((box[1]+.025)*h)),t,int(27*s),'#493b58')
  rect((0,.93,1,1),(250,248,252,245),0)
 elif kind in ('wechat','qq'):
  rect((0,.61,1,1),(250,248,253,250),0);text(.06,.035,'<    '+('Moments' if kind=='wechat' else 'QQ Profile'),35)
  rect((.75,.52,.94,.65),(241,225,245,255));txt(d,(int(w*.08),int(h*.70)),'Sakura & Syaoran',int(48*s),'#493851');txt(d,(int(w*.08),int(h*.78)),'A little magic in everyday life.',int(28*s),'#83718d')
 return a

manifest=[]
for i,name in enumerate(NAMES,1):
 src=Image.open(R/'masters'/f'{i:02}.png').convert('RGB');folder=OUT/f'{i:02}-{name}';folder.mkdir(exist_ok=True);records=[]
 def emit(im,filename,category):
  p=folder/filename;save(im,p);records.append({'file':filename,'category':category,'size':list(im.size),'md5':hashlib.md5(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
 phone=layout(src,(1440,2560));emit(phone,'01-手机-无UI.jpg','phone');emit(ui(phone,'lock'),'02-手机-锁屏UI模拟.jpg','phone');emit(ui(phone,'home'),'03-手机-桌面UI模拟.jpg','phone')
 for prefix,size,kind in [('04-电脑',(3840,2160),'desktop'),('06-iPad横屏',(2732,2048),'home'),('08-iPad竖屏',(2048,2732),'home'),('10-手表方形',(1024,1024),'watch'),('12-手表竖屏',(396,484),'watch')]:
  im=layout(src,size,side='right' if kind=='desktop' else 'center');emit(im,prefix+'-无UI.jpg',kind);emit(ui(im,kind),prefix+'-UI模拟.jpg',kind)
 cover=layout(src,(2400,1200),side='right');emit(cover,'14-朋友圈封面-无UI.jpg','social')
 emit(ui(layout(src,(1080,1440)),'wechat'),'15-微信朋友圈-UI模拟.jpg','social')
 qq=layout(src,(2400,1350),side='right');emit(qq,'16-QQ主页背景-无UI.jpg','social');emit(ui(layout(src,(1080,1440)),'qq'),'17-QQ主页-UI模拟.jpg','social')
 chat=Image.blend(phone,Image.new('RGB',phone.size,'#eee7f5'),.80);emit(chat,'18-微信聊天背景-无UI.jpg','chat');emit(ui(chat,'chat'),'19-微信聊天-UI模拟.jpg','chat')
 emit(ImageOps.mirror(chat),'20-QQ聊天背景-无UI.jpg','chat');emit(ui(ImageOps.mirror(chat),'chat'),'21-QQ聊天-UI模拟.jpg','chat')
 face=FACES[i-1];avatars=[]
 for k,who in enumerate(['A-小樱','B-小狼']):
  cx,cy=face[k*2:k*2+2];side=int(src.width*.28);x=max(0,min(src.width-side,int(cx*src.width-side/2)));y=max(0,min(src.height-side,int(cy*src.height-side*.60)))
  crop=src.crop((x,y,x+side,y+side));avatar=crop.resize((1024,1024),Image.Resampling.LANCZOS);avatars.append(avatar)
  emit(avatar,'22-情侣头像-'+who+'-无UI.png','avatar');records[-1]['source_crop_pixels']=[side,side]
  preview=Image.new('RGB',(1200,1200),'#e6dced');mask=Image.new('L',(900,900));ImageDraw.Draw(mask).ellipse((0,0,899,899),fill=255);preview.paste(avatar.resize((900,900)),(150,110),mask);txt(ImageDraw.Draw(preview),(300,1060),'AVATAR PREVIEW',48,'#674c78');emit(preview,'23-情侣头像-'+who+'-UI模拟.jpg','avatar')
  # Full original preserved at restrained scale with matching portrait inset: no face-only wallpaper stretch.
  couple=phone.copy();small=avatar.resize((360,360));couple.paste(small,(90 if k==0 else 990,2050));emit(couple,'24-情侣壁纸-'+who+'-无UI.jpg','couple');emit(ui(couple,'lock'),'25-情侣壁纸-'+who+'-锁屏UI模拟.jpg','couple')
 # Clean binary originals remain independent, not screenshots.
 emit(src,'00-原生主图.png','master')
 board=Image.new('RGB',(2000,1250),'#eee6f5');d=ImageDraw.Draw(board);txt(d,(60,28),f'{i:02} / SAKURA TWILIGHT COLLECTION',48,'#513d68')
 for fn,box in [('04-电脑-UI模拟.jpg',(60,180,1000,710)),('06-iPad横屏-UI模拟.jpg',(1040,180,1600,600)),('02-手机-锁屏UI模拟.jpg',(1630,180,1950,750)),('14-朋友圈封面-无UI.jpg',(60,800,1000,1270)),('23-情侣头像-A-小樱-UI模拟.jpg',(1070,770,1460,1160)),('23-情侣头像-B-小狼-UI模拟.jpg',(1520,770,1910,1160))]:
  im=Image.open(folder/fn);im.thumbnail((box[2]-box[0],min(1200,box[3])-box[1]));board.paste(im,(box[0],box[1]))
 emit(board,'26-多设备搭配效果展示.jpg','showcase')
 # 4s exactly periodic subtle light-particle motion, not character AI animation.
 mp4=folder/'27-手机动态-无UI-1080p.mp4';ff=imageio_ffmpeg.get_ffmpeg_exe();proc=subprocess.Popen([ff,'-y','-f','rawvideo','-vcodec','rawvideo','-s','1080x1920','-pix_fmt','rgb24','-r','16','-i','-','-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(mp4)],stdin=subprocess.PIPE,stderr=subprocess.DEVNULL)
 base=phone.resize((1080,1920),Image.Resampling.LANCZOS);gif=[]
 for frame in range(64):
  a=base.copy();layer=Image.new('RGBA',a.size);dd=ImageDraw.Draw(layer)
  for k in range(22):
   x=int((k*.618%1)*1080);y=int(((k*.381+frame/64)%1)*1920);alpha=int(50+45*math.sin(frame/64*math.tau+k));dd.ellipse((x-2,y-2,x+2,y+2),fill=(255,244,255,alpha))
  a=Image.alpha_composite(a.convert('RGBA'),layer).convert('RGB');proc.stdin.write(a.tobytes())
  if frame%2==0:gif.append(a.resize((270,480)))
 proc.stdin.close();assert proc.wait()==0
 records.append({'file':mp4.name,'category':'animation','size':[1080,1920],'duration':4,'frames':64,'fps':16,'md5':hashlib.md5(mp4.read_bytes()).hexdigest(),'bytes':mp4.stat().st_size})
 gp=folder/'28-动态预览-非高清.gif';gif[0].save(gp,save_all=True,append_images=gif[1:],duration=125,loop=0)
 records.append({'file':gp.name,'category':'animation_preview','size':[270,480],'md5':hashlib.md5(gp.read_bytes()).hexdigest(),'bytes':gp.stat().st_size})
 info={'theme':name,'native_size':list(src.size),'rule':'竖屏等比裁切铺满；横屏为原画+取色留白非扩图；Lanczos插值非原生4K；头像裁片放大非新增细节；UI通用模拟非实机；动态光点非人物动画；GIF仅低清预览','files':records}
 (folder/'素材清单.json').write_text(json.dumps(info,ensure_ascii=False,indent=2));manifest.append(info)

(R/'清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
