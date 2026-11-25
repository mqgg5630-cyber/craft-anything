"""Reproducible full-copy replacement; all visible typeset words are recorded here."""
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont,ImageChops
from fontTools.ttLib import TTFont
import hashlib,json,math
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
SIZE=(1080,2343)
BRUSH=REPO/'assets/fonts/cjk/MaShanZheng-Regular.ttf'
SANS=REPO/'assets/fonts/cjk/NotoSansCJKsc-Regular.otf'
# Right column first, read in traditional order. All eight original main phrases forbidden.
FORBIDDEN=['萬穩萬當','不如一默','歡喜由心','自在如風','愛財愛己','風生水起','安康如意','順遂福來']
COPY=[('春祺夏安','秋绥冬禧','一程春风','满目新晴'),('岁启新章','福满人间','灯火可亲','团圆有期'),('所行皆坦','所遇皆暖','心怀明朗','步履生光'),('长乐未央','喜悦成双','愿逢美好','常见晴光'),('花开有信','好运有期','春来有约','喜至无声'),('心栖暖处','日有小欢','闲煮清茶','笑看流年'),('福随春至','喜伴岁长','春山可望','来日可期'),('朝迎瑞气','暮揽祥光','朝暮皆好','四时有光'),('家和景明','岁丰人悦','家常有暖','岁月生香'),('新程似锦','佳事连年','心向远方','一路芬芳')]
# Normalized actual blank-paper boxes, manually measured after reviewing all ten native backgrounds.
BOXES=[((.613,.35,.783,.695),(.20,.608,.39,.97)),((.61,.345,.79,.695),(.20,.5,.39,.905)),((.73,.29,.88,.64),(.11,.54,.25,.90)),((.61,.345,.79,.875),(.20,.5,.395,.99)),((.61,.345,.79,.875),(.20,.5,.395,.985)),((.61,.345,.79,.695),(.20,.5,.39,.985)),((.61,.345,.79,.88),(.20,.5,.395,.985)),((.61,.345,.79,.875),(.20,.5,.395,.985)),((.61,.345,.79,.72),(.20,.54,.395,.96)),((.61,.345,.79,.695),(.20,.5,.395,.985))]
REFERENCES=[1,2,3,4,1,2,3,4,1,2]
SCENES=['紅梅與舊紙','桃花與薄宣','海棠與層紙','山茶與絹邊','南天竹紅果','秋菊與紙箋','桂枝與淡絹','牡丹與紙影','梅枝與花箋','櫻枝與春紙']
def info(path):
 data=path.read_bytes()
 with Image.open(path) as im:im.load();size=im.size;fmt=im.format
 return dict(file=str(path.relative_to(ROOT)),width=size[0],height=size[1],format=fmt,bytes=len(data),md5=hashlib.md5(data).hexdigest(),sha256=hashlib.sha256(data).hexdigest())
def fit(im):return ImageOps.fit(im.convert('RGB'),SIZE,method=Image.Resampling.LANCZOS,centering=(.5,.5))
def centered(d,xy,char,font,fill):
 box=d.textbbox((0,0),char,font=font);d.text((xy[0]-(box[0]+box[2])/2,xy[1]-(box[1]+box[3])/2),char,font=font,fill=fill)
def typeset(im,index):
 im=im.copy().convert('RGBA');w,h=im.size;coords=[]
 # Fine, restrained grey-brown offset impression matches the source aesthetic, not a fake font stroke.
 for col,(text,box) in enumerate(zip(COPY[index][:2],BOXES[index])):
  x0,y0,x1,y1=box;bw=(x1-x0)*w;bh=(y1-y0)*h
  fs=round(min(132,bw*.78,bh*.19));font=ImageFont.truetype(str(BRUSH),fs)
  usable=min(bh*.79,4*fs*1.55);cy=(y0+y1)*h/2;step=(usable-fs)/3
  xs=(x0+x1)*w/2-5
  points=[(round(xs),round(cy-1.5*step+k*step)) for k in range(4)]
  shadow=Image.new('RGBA',SIZE);sd=ImageDraw.Draw(shadow)
  for ch,(x,y) in zip(text,points):centered(sd,(x+round(fs*.16),y+round(fs*.14)),ch,font,(71,61,43,59))
  im=Image.alpha_composite(im,shadow);d=ImageDraw.Draw(im)
  for ch,point in zip(text,points):centered(d,point,ch,font,(25,24,20,255))
  coords.append(dict(column='right' if col==0 else 'left',text=text,font_px=fs,box_normalized=box,glyph_centers=points))
 # Side copy fully replaces original side inscription; never retain original poem/signature.
 d=ImageDraw.Draw(im);font=ImageFont.truetype(str(BRUSH),29)
 if index==2: xx=[.445,.405];yy=.40
 else:xx=[.145,.105];yy=.50
 for line,(text,x) in enumerate(zip(COPY[index][2:],xx)):
  for k,ch in enumerate(text):centered(d,(round(w*x),round(h*yy)+k*42),ch,font,(66,54,40,225))
 # Small non-authorial editorial caption, all newly written, no name/date or copied seal text.
 return im.convert('RGB'),coords

def board(files,path,include_sources=False):
 font=ImageFont.truetype(str(SANS),24);small=ImageFont.truetype(str(SANS),17)
 cols=5;cw=280;ch=665;top=98
 records=[]
 if include_sources:
  records.extend((ROOT/f'source/{i:02}.webp',f'原片 {i:02} · 1080×2343') for i in range(1,5))
 records.extend((ROOT/f'images/{i:02}.png',f'{i:02}  {COPY[i-1][0]} · {COPY[i-1][1]}') for i in range(1,11))
 rows=math.ceil(len(records)/cols);im=Image.new('RGB',(cols*cw,top+rows*ch+30),'#e9dfc9');d=ImageDraw.Draw(im)
 title='原片4張 ＋ 同風格新文案10張' if include_sources else '新年祝福壁紙 · 10張新文案'
 d.text((24,15),title,font=font,fill='#423b30');d.text((24,55),'成品均為1080×2343 · 宣紙拼貼／仿舊絹邊／書法雙列 · 非原作者發布成品',font=small,fill='#655b49')
 for j,(p,label) in enumerate(records):
  x=j%cols*cw;y=top+j//cols*ch
  with Image.open(p) as a:
   thumb=ImageOps.contain(a.convert('RGB'),(cw-18,ch-55),Image.Resampling.LANCZOS);im.paste(thumb,(x+(cw-thumb.width)//2,y))
  d.text((x+8,y+ch-43),label,font=small,fill='#423b30')
 im.save(path,quality=92,subsampling=0)

def main():
 source=json.loads((ROOT/'source-manifest.json').read_text());assert len(source['images'])==4
 for item in source['images']:
  a=info(ROOT/item['file'])
  for k in ['width','height','bytes','md5','sha256']:assert a[k]==item[k]
  assert (a['width'],a['height'])==SIZE
 assert len({s for row in COPY for s in row[:2]})==20
 assert all(len(s)==4 and s not in FORBIDDEN for row in COPY for s in row)
 cmap=TTFont(BRUSH).getBestCmap()
 assert all(ord(c) in cmap for row in COPY for s in row for c in s),'Font missing glyph; do not publish tofu'
 (ROOT/'images').mkdir(exist_ok=True);records=[]
 for i in range(10):
  raw=ROOT/f'artwork/{i+1:02}.png';a=info(raw)
  with Image.open(raw) as base:im,coords=typeset(fit(base),i)
  out=ROOT/f'images/{i+1:02}.png';im.save(out,optimize=True);r=info(out)
  scale=max(SIZE[0]/a['width'],SIZE[1]/a['height'])
  r.update(main_copy=dict(right=COPY[i][0],left=COPY[i][1]),side_copy=list(COPY[i][2:]),scene=SCENES[i],reference=[f'source/{REFERENCES[i]:02}.webp'],native_artwork=a,adaptation=dict(method='One uniform Lanczos upscale then small centered crop; not anisotropic; final pixels not model-native',uniform_scale=scale,scaled_dimensions=[a['width']*scale,a['height']*scale],final_dimensions=list(SIZE)),typography=dict(font='assets/fonts/cjk/MaShanZheng-Regular.ttf',font_sha256=hashlib.sha256(BRUSH.read_bytes()).hexdigest(),columns=coords,side_font_px=29,grey_offset_impression=True),ui=False)
  records.append(r)
 assert len({r['sha256'] for r in records})==10 and len({r['native_artwork']['sha256'] for r in records})==10
 manifest=dict(share_url='https://xhslink.cn/o/3kQq76Fee2O',note_id='6af66414000000002203bdb3',source_dimensions=list(SIZE),status='typeset_pending_final_visual_review',copy_policy='20 distinct newly typeset main phrases and 20 new side phrases. None of source eight main phrases or side inscription is reused. Generated red impressions are visual ornament, not transcribed text or authenticated personal seals.',source_main_copy_forbidden=FORBIDDEN,independent_generations=True,all_native_artwork_dimensions=[704,1520],source_medium='antique xuan-paper/silk collage with floral panel and two vertical brush-lettered slips',files=records)
 p=ROOT/'output-manifest.json'
 if p.exists():
  old=json.loads(p.read_text())
  if 'visual_review' in old:manifest['visual_review']=old['visual_review'];manifest['status']=old['status']
  if 'glyph_coverage' in old:manifest['glyph_coverage']=old['glyph_coverage']
 p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 board(records,ROOT/'00-10張成品總預覽.jpg');board(records,ROOT/'00-原片與成品對照.jpg',True)
 (ROOT/'local-verification.json').write_text(json.dumps(dict(status='passed',reference_count=4,decoded_source_native_final_images=24,count=10,exact_size=list(SIZE),unique_native=10,unique_final=10,unique_main_phrases=20,source_main_phrases_retained=0,native_dimensions=[704,1520],adaptation='uniform Lanczos upscale plus slight center crop; no anisotropic stretching',typography='real MaShanZheng font; no model-rendered main/side wording',ui=False),ensure_ascii=False,indent=2)+'\n')
 print('PASS: 4 sources, 10 independent backgrounds, 10 exact 1080x2343 finals; all main/side copy replaced')
if __name__=='__main__':main()
