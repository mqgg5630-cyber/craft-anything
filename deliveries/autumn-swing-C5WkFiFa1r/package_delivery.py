"""Package ten newly generated sheep-swing wallpapers, exact verified source size."""
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont,ImageChops
import hashlib,json,math
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
SIZE=(852,1848)
FONT=REPO/'assets/fonts/cjk/NotoSansCJKsc-Regular.otf'
SCENES=['含笑轻荡','仰望落叶','眯眼迎风','侧望夕阳','笑迎金光','困倦小憩','低头看花','秋千微晃','歪头浅笑','开怀秋日']
DETAILS=['微笑，双脚错落，轻缓摆动','抬头看金色落叶，天空由淡金到暖橙','闭眼笑，双脚向前，秋千略偏','侧脸看夕阳，远处田间弯路与高积云','张嘴欢笑，树冠间斜射光束','半闭眼困倦表情，远山光谷与淡粉云','低头圆嘴，草地小白花、更多顶端叶片','迎着镜头轻笑，座板略微偏斜，夕阳光芒','歪头闭眼浅笑，较近取景，额前卷毛变化','闭眼大笑，宽阔斜向云带与远处小飞鸟']
def info(path):
 data=path.read_bytes()
 with Image.open(path) as im:im.load();w,h=im.size;fmt=im.format
 return dict(file=str(path.relative_to(ROOT)),width=w,height=h,format=fmt,bytes=len(data),md5=hashlib.md5(data).hexdigest(),sha256=hashlib.sha256(data).hexdigest())
def adapt(im):return ImageOps.fit(im.convert('RGB'),SIZE,method=Image.Resampling.LANCZOS,centering=(.5,.5))
def sheet(entries,path,title):
 cols=min(5,len(entries));cw=272;ch=650;top=104
 im=Image.new('RGB',(max(520,cols*cw),top+math.ceil(len(entries)/cols)*ch+20),'#fff0d6');d=ImageDraw.Draw(im);f=ImageFont.truetype(str(FONT),26);s=ImageFont.truetype(str(FONT),17)
 d.text((20,15),title,font=f,fill='#6b3e19');d.text((20,57),'原片1张 · 新生成10张 · 成品852×1848 · 原片与结果独立保存',font=s,fill='#875e36')
 for j,(path_,label) in enumerate(entries):
  x=(j%cols)*cw;y=top+(j//cols)*ch
  with Image.open(path_) as a:t=ImageOps.contain(a.convert('RGB'),(cw-16,ch-55),Image.Resampling.LANCZOS)
  im.paste(t,(x+(cw-t.width)//2,y));d.text((x+9,y+ch-42),label,font=s,fill='#6b3e19')
 im.save(path,quality=92,subsampling=0)
def main():
 source=json.loads((ROOT/'source-manifest.json').read_text());assert len(source['images'])==1
 a=info(ROOT/'source/01.jpg');expected=source['images'][0]
 for k in ['width','height','bytes','md5','sha256']:assert a[k]==expected[k]
 assert (a['width'],a['height'])==SIZE
 paths=sorted((ROOT/'artwork').glob('*.png'));assert [p.name for p in paths]==[f'{i:02}.png' for i in range(1,11)]
 (ROOT/'images').mkdir(exist_ok=True);rows=[];old=REPO/'deliveries/newyear-blessings-3kQq76Fee2O'
 oldhash={hashlib.sha256(p.read_bytes()).hexdigest() for p in (old/'images').glob('*.png')}
 for i,path in enumerate(paths):
  native=info(path)
  with Image.open(path) as im:out=adapt(im)
  dest=ROOT/f'images/{i+1:02}.png';out.save(dest,optimize=True);r=info(dest);scale=max(SIZE[0]/native['width'],SIZE[1]/native['height'])
  assert r['sha256'] not in oldhash
  r.update(title=SCENES[i],variation=DETAILS[i],references=['source/01.jpg'],new_generation=True,native_artwork=native,adaptation=dict(method='One uniform Lanczos upscale and minimal centered crop; no anisotropic stretch; final pixels are not model-native',uniform_scale=scale,scaled_dimensions=[native['width']*scale,native['height']*scale],final_dimensions=list(SIZE)),ui=False,added_text=False)
  rows.append(r)
 assert len({r['sha256'] for r in rows})==10 and len({r['native_artwork']['sha256'] for r in rows})==10
 m=dict(share_url='https://xhslink.cn/o/C5WkFiFa1r',note_id='6abdb5a9000000001802f193',source_count=1,result_count=10,new_generation_calls=10,old_results_reused=False,source_dimensions=list(SIZE),default_future_dimensions=list(SIZE),medium='Detailed golden-orange cinematic anime landscape with softly rounded chibi white-wool sheep, yellow bib, brown horns, rope swing; no unrelated watercolor/paper-craft change',status='packaged_pending_final_visual_review',files=rows)
 p=ROOT/'output-manifest.json'
 if p.exists():
  oldm=json.loads(p.read_text())
  if 'visual_review' in oldm:m['visual_review']=oldm['visual_review'];m['status']=oldm['status']
 p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
 entries=[(ROOT/r['file'],f'{i+1:02} · {SCENES[i]}') for i,r in enumerate(rows)]
 sheet(entries,ROOT/'00-10张成品总预览.jpg','秋天和秋千很配哦 · 10张新生成')
 sheet([(ROOT/'source/01.jpg','原片 · 852×1848')]+entries,ROOT/'00-原片与成品对照.jpg','原片1张 ＋ 新生成10张 · 对照预览')
 sheet([(ROOT/'source/01.jpg','原片 · 网页CDN文件，保留原字节')],ROOT/'00-原片总预览.jpg','参考原片 · 1张')
 verification=dict(status='passed',new_generation_calls=10,old_results_reused=False,source_count=1,decoded_source_native_final_images=21,final_count=10,final_dimensions=list(SIZE),unique_native_artworks=10,unique_final_images=10,native_dimensions=[[r['native_artwork']['width'],r['native_artwork']['height']] for r in rows],all_final_png=True,all_reference_only_original=True,adaptation='Uniform Lanczos upscale, minimal center crop; not native 852x1848',previews=3)
 (ROOT/'local-verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2)+'\n');print('PASS: 10 NEW independent generations, 10 unique 852x1848 PNGs, 3 previews')
if __name__=='__main__':main()
