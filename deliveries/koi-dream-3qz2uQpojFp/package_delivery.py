"""Offline packaging: preserve clean PNGs, render transparent lockscreen layer and boards."""
import hashlib,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
CJK=REPO/'assets/fonts/cjk/NotoSansCJKsc-Regular.otf'
SERIF=Path('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf')
if not SERIF.exists():SERIF=REPO/'assets/fonts/DMSans-Regular.ttf'
PLAN=[('右岸流金',['01'],'右侧S形流水，金鲤上红鲤下'),('左岸清游',['01'],'左侧流水留白，两鲤相向'),('双鲤同行',['01','03'],'下方双鲤同游，上部大留白'),('三鲤回湾',['01'],'右侧与下缘回流，生成变体为一红两金三条锦鲤'),('斜流入梦',['01'],'左上红鲤与右下金鲤，斜向水路'),('双鲤回游',['03'],'下部圆形回游，金鲤左红鲤右'),('椭圆漪澜',['03'],'椭圆流水，红鲤左金鲤右'),('阴阳清漩',['03'],'开放双鲤回旋构图'),('顺水生辉',['03'],'下部顺时针环流'),('金玉相逢',['03'],'开放环流中的双鲤S形动线')]

def info(p):
 data=p.read_bytes()
 with Image.open(p) as im:im.verify()
 with Image.open(p) as im:im.load();w,h=im.size;fmt=im.format.lower()
 return dict(file=str(p.relative_to(ROOT)),format=fmt,width=w,height=h,bytes=len(data),md5=hashlib.md5(data).hexdigest(),sha256=hashlib.sha256(data).hexdigest())

def ui_layer(size,index=0):
 w,h=size;layer=Image.new('RGBA',size,(0,0,0,0));d=ImageDraw.Draw(layer)
 ink=(115,80,24,255);soft=(115,80,24,90)
 tx=w*(.69 if index==4 else .5)
 # Like the reference's airy serif clock, not a screenshot or installable theme.
 d.text((tx,h*.105),'Sun 22 Nov',font=ImageFont.truetype(str(SERIF),round(w*.041)),anchor='mm',fill=ink)
 d.text((tx,h*.177),'9:41',font=ImageFont.truetype(str(SERIF),round(w*.185)),anchor='mm',fill=ink)
 lx,ly=tx,h*.052
 d.arc((lx-w*.010,ly-w*.009,lx+w*.010,ly+w*.011),180,360,fill=ink,width=2)
 d.rounded_rectangle((lx-w*.015,ly,lx+w*.015,ly+w*.024),3,fill=ink)
 # Bottom translucent circles and flashlight/camera glyphs.
 cy=h*.93;r=w*.046
 for cx in [w*.15,w*.85]:d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=soft)
 white=(255,252,242,255)
 cx=w*.15
 d.polygon([(cx-w*.014,cy-w*.02),(cx+w*.014,cy-w*.02),(cx+w*.008,cy-w*.004),(cx-w*.008,cy-w*.004)],fill=white)
 d.rounded_rectangle((cx-w*.007,cy-w*.004,cx+w*.007,cy+w*.021),2,fill=white)
 cx=w*.85
 d.rounded_rectangle((cx-w*.022,cy-w*.014,cx+w*.022,cy+w*.015),3,outline=white,width=2)
 d.ellipse((cx-w*.008,cy-w*.008,cx+w*.008,cy+w*.009),outline=white,width=2)
 d.rounded_rectangle((w*.35,h*.978,w*.65,h*.978+4),2,fill=ink)
 return layer

def sheet(paths,target,title,labels):
 cols=5 if len(paths)>3 else 3;cw,ch=240,520;gap=16;top=88;bottom=44
 rows=-(-len(paths)//cols);out=Image.new('RGB',(cols*cw+(cols+1)*gap,top+rows*(ch+bottom+gap)),'#f4f0e5');d=ImageDraw.Draw(out)
 d.text((gap,22),title,font=ImageFont.truetype(str(CJK),25),fill='#725a34')
 for i,p in enumerate(paths):
  x=gap+(i%cols)*(cw+gap);y=top+(i//cols)*(ch+bottom+gap)
  with Image.open(p) as im:
   pic=ImageOps.contain(im.convert('RGB'),(cw,ch),Image.Resampling.LANCZOS);out.paste(pic,(x+(cw-pic.width)//2,y+(ch-pic.height)//2))
  d.text((x,y+ch+9),labels[i],font=ImageFont.truetype(str(CJK),16),fill='#725a34')
 out.save(target,quality=94)

def main():
 source=json.loads((ROOT/'source-manifest.json').read_text());assert len(source['images'])==3
 for item in source['images']:
  actual=info(ROOT/item['file'])
  for k in ['width','height','bytes','md5','sha256','format']:assert actual[k]==item[k],(item['file'],k)
 clean=sorted((ROOT/'images').glob('*.png'));assert [p.name for p in clean]==[f'{i:02d}.png' for i in range(1,11)]
 before=[info(p) for p in clean];assert len({i['sha256'] for i in before})==10
 (ROOT/'ui').mkdir(exist_ok=True);records=[]
 for i,p in enumerate(clean):
  with Image.open(p) as im:Image.alpha_composite(im.convert('RGBA'),ui_layer(im.size,i)).convert('RGB').save(ROOT/'ui'/p.name)
  title,refs,change=PLAN[i]
  for kind,q in [('no_ui',p),('simulated_ui',ROOT/'ui'/p.name)]:
   records.append(dict(info(q),kind=kind,title=title,references=[f'source/{r}.webp' for r in refs],change=change))
 assert before==[info(p) for p in clean]
 sheet([ROOT/i['file'] for i in source['images']],ROOT/'00-原片总预览.jpg','锦鲤入梦 · 实际下载原片3张',['01 · 边缘流水壁纸','02 · 原帖锁屏主屏展示','03 · 双鲤回游壁纸'])
 labels=[f'{i+1:02} · {PLAN[i][0]}' for i in range(10)]
 sheet(clean,ROOT/'00-无UI总预览.jpg','锦鲤入梦 · 10张参考复刻 · 无UI',labels)
 sheet(sorted((ROOT/'ui').glob('*.png')),ROOT/'00-有UI总预览.jpg','锦鲤入梦 · 10张模拟锁屏 · 有UI',labels)
 paths=[ROOT/'00-原片总预览.jpg',ROOT/'00-无UI总预览.jpg',ROOT/'00-有UI总预览.jpg'];sizes=[]
 for p in paths:
  with Image.open(p) as im:sizes.append(im.size)
 w=max(s[0] for s in sizes);h=sum(s[1] for s in sizes)+32;board=Image.new('RGB',(w,h),'#f4f0e5');y=0
 for p in paths:
  with Image.open(p) as im:board.paste(im,((w-im.width)//2,y));y+=im.height+16
 board.save(ROOT/'00-总预览.jpg',quality=94)
 manifest=ROOT/'output-manifest.json';previous=json.loads(manifest.read_text()) if manifest.exists() else {}
 manifest.write_text(json.dumps(dict(generated_count=10,ui_count=10,reference_count=3,art_reference_count=2,quality='Model-native PNG, no upscaling; source02 is presentation only',ui_note='Simulated lock screen overlay, not real device screenshot or installable theme',visual_review=previous.get('visual_review','pending'),files=records),ensure_ascii=False,indent=2)+'\n')
 (ROOT/'local-verification.json').write_text(json.dumps(dict(source_count=3,clean_count=10,ui_count=10,preview_count=4,all_23_decoded=True,source_hashes_match=True,clean_files_unchanged_by_ui=True,clean_unique=True,native_sizes=sorted({(i['width'],i['height']) for i in before})),indent=2)+'\n')
 print('Verified 3 sources, 10 clean + 10 UI; wrote 4 boards. Clean PNGs unmodified.')
if __name__=='__main__':main()
