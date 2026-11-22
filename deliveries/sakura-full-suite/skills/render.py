from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance
import json, hashlib, math, subprocess, base64, mimetypes, io
import imageio_ffmpeg
R=Path(__file__).resolve().parents[1]
OUT=R/'sets'; BUNDLES=R/'albums'; OUT.mkdir(exist_ok=True); BUNDLES.mkdir(exist_ok=True)
NAMES=['星灯约定','樱桥花语','暮色观星','花亭乐盒','玫瑰来信','天鹅晚风','古堡钥匙','莓果茶会','温室蝶影','纸鹤月光']
FACES=[(.33,.57,.69,.55),(.31,.46,.71,.46),(.55,.53,.73,.53),(.36,.57,.68,.57),(.42,.53,.66,.50),(.42,.59,.61,.59),(.40,.425,.65,.405),(.36,.52,.68,.53),(.42,.57,.65,.58),(.30,.43,.72,.43)]
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def txt(d,xy,t,size=30,fill='#ffffff'):d.text(xy,t,font=ImageFont.truetype(FONT,size),fill=fill)
def save(im,p):
 if p.suffix=='.png':im.save(p)
 else:im.convert('RGB').save(p,quality=95,subsampling=0)
def layout(src,size,mode='contain',side='center'):
 w,h=size; bg=Image.new('RGB',size,'#e7def1');d=ImageDraw.Draw(bg)
 # Native-resolution geometric matte, not stretched or blurred invented scenery.
 for k in range(12):
  c=(217+k,202+k,230+k//2);y=int(h*k/12);d.rectangle((0,y,w,int(h*(k+1)/12)),fill=c)
 for k in range(14):
  x=int((k*.173%1)*w);y=int((k*.317%1)*h);rr=max(3,int(w*.004));d.ellipse((x-rr,y-rr,x+rr,y+rr),outline='#f8f1fa',width=max(1,w//800))
 fit=ImageOps.contain(src,(int(w*.94),int(h*.94)),Image.Resampling.LANCZOS)
 x=(w-fit.width)//2
 if side=='right':x=w-fit.width-int(w*.07)
 bg.paste(fit,(x,(h-fit.height)//2));d=ImageDraw.Draw(bg);d.rectangle((x-2,(h-fit.height)//2-2,x+fit.width+2,(h+fit.height)//2+2),outline='#fff6fd',width=2)
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
  cx,cy=face[k*2:k*2+2];side=int(src.width*.42);x=max(0,min(src.width-side,int(cx*src.width-side/2)));y=max(0,min(src.height-side,int(cy*src.height-side*.40)))
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
 gp=folder/'28-动态预览.gif';gif[0].save(gp,save_all=True,append_images=gif[1:],duration=125,loop=0)
 records.append({'file':gp.name,'category':'animation_preview','size':[270,480],'md5':hashlib.md5(gp.read_bytes()).hexdigest(),'bytes':gp.stat().st_size})
 info={'theme':name,'native_size':list(src.size),'rule':'原图完整保留；不同设备为等比适配+设计留白，不是AI扩图；Lanczos插值非原生4K；头像小裁片放大非新增细节；UI为通用模拟非实机；动态为光点叠加非人物动画','files':records}
 (folder/'素材清单.json').write_text(json.dumps(info,ensure_ascii=False,indent=2));manifest.append(info)
 # Offline self-contained album holds ACTUAL asset bytes with per-file download, no ZIP, no external dependencies.
 payload=[]
 for p in sorted(folder.iterdir()):payload.append({'name':p.name,'type':mimetypes.guess_type(p.name)[0] or 'application/octet-stream','data':base64.b64encode(p.read_bytes()).decode()})
 page='''<!doctype html><html lang="zh"><meta charset="utf-8"><title>配套素材下载</title><style>body{background:#f4eef8;color:#49365c;font:16px system-ui;margin:40px}h1{font-size:32px}section{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:22px}article{background:white;padding:16px;border-radius:16px}img,video{width:100%;height:290px;object-fit:contain;background:#eee8f4}a,button{display:inline-block;background:#705486;color:white;border:0;padding:12px;border-radius:9px;text-decoration:none;cursor:pointer}small{display:block;margin:12px 0}</style><h1>THEME_TITLE · 全套素材</h1><p>每个条目都内嵌实际文件，可独立下载。无需联网，无需解压。UI是模拟展示，不是实机截图；4K指输出尺寸，不是原生生成细节。</p><p>Chrome/Edge：可点击“保存全套到文件夹”；其他浏览器请逐项下载。若从Drive打开，请先下载此HTML到电脑再用浏览器打开。</p><button onclick="saveAll()">保存全套到文件夹</button><p id="status"></p><section id="grid"></section><script>const assets=PAYLOAD;function blob(a){let b=atob(a.data),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);return new Blob([u],{type:a.type})}for(let a of assets){let url=URL.createObjectURL(blob(a)),card=document.createElement('article');if(a.type.startsWith('image/')){let im=new Image();im.src=url;im.loading='lazy';card.append(im)}else if(a.type.startsWith('video/')){let v=document.createElement('video');v.src=url;v.controls=true;v.preload='none';card.append(v)}let name=document.createElement('small');name.textContent=a.name;card.append(name);let link=document.createElement('a');link.href=url;link.download=a.name;link.textContent='下载原文件';card.append(link);grid.append(card)}async function saveAll(){try{if(!window.showDirectoryPicker)throw Error('此浏览器不支持文件夹保存，请使用各项下载按钮');let dir=await showDirectoryPicker();for(let [i,a] of assets.entries()){let f=await dir.getFileHandle(a.name,{create:true}),w=await f.createWritable();await w.write(blob(a));await w.close();document.getElementById('status').textContent=`已保存 ${i+1}/${assets.length}`} }catch(e){document.getElementById('status').textContent=e.message}}</script></html>'''
 page=page.replace('THEME_TITLE',f'{i:02}-{name}').replace('PAYLOAD',json.dumps(payload,ensure_ascii=False));bp=BUNDLES/f'{i:02}-{name}-全套素材.html';bp.write_text(page);print(i,name,len(records),bp.stat().st_size,flush=True)
(R/'清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
