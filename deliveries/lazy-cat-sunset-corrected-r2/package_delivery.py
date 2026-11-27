"""Package ten independently generated body-corrected wallpapers; no new network acquisition."""
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont
import hashlib,json,math,zipfile
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
SIZE=(852,1848)
TITLES=['溪桥晚风','海边站台','山丘野餐','湖畔栈桥','花店门廊','稻田车站','温室花园','山间露营','灯塔海岸','书店露台']
FONT=REPO/'assets/fonts/cjk/NotoSansCJKsc-Regular.otf'
def savejson(name,data): (ROOT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def info(p):
 data=p.read_bytes()
 with Image.open(p) as im: im.load(); size=list(im.size)
 return dict(file=str(p.relative_to(ROOT)),size=size,bytes=len(data),md5=hashlib.md5(data).hexdigest(),sha256=hashlib.sha256(data).hexdigest())
def sheet(entries,name,title,subtitle):
 cols=min(5,len(entries)); cw,ch=280,665;top=100
 b=Image.new('RGB',(max(560,cw*cols),top+math.ceil(len(entries)/cols)*ch+20),'#f7eedf');d=ImageDraw.Draw(b)
 f=ImageFont.truetype(str(FONT),25);s=ImageFont.truetype(str(FONT),17)
 d.text((18,15),title,font=f,fill='#5b4436');d.text((18,57),subtitle,font=s,fill='#80634d')
 for j,(p,label) in enumerate(entries):
  with Image.open(p) as im:t=ImageOps.contain(im.convert('RGB'),(cw-16,ch-56),Image.Resampling.LANCZOS)
  x=(j%cols)*cw;y=top+(j//cols)*ch;b.paste(t,(x+(cw-t.width)//2,y));d.text((x+8,y+ch-40),label,font=s,fill='#5b4436')
 b.save(ROOT/name,quality=92,subsampling=0)
def main():
 source=ROOT/'reference/source-original.jpg';assert info(source)['sha256']=='7e6f54509d875ce81d811be3b710558c77be82ae5984226bcd2b53a22d55d04a'
 native=sorted((ROOT/'artwork').glob('*.png'));assert len(native)==10
 old=REPO/'deliveries/lazy-cat-sunset-6bdoxc66Ezp/artwork';oldhash={hashlib.sha256(p.read_bytes()).hexdigest() for p in old.glob('*.png')}
 (ROOT/'images').mkdir(exist_ok=True);rows=[]
 for i,p in enumerate(native):
  n=info(p);assert n['sha256'] not in oldhash
  use=ROOT/'corrected/10.png' if i==9 else p
  with Image.open(use) as im:final=ImageOps.fit(im.convert('RGB'),SIZE,method=Image.Resampling.LANCZOS,centering=(.5,.5))
  out=ROOT/f'images/{i+1:02}.png'
  if not out.exists(): final.save(out,optimize=True)
  else:
   with Image.open(out) as existing: assert existing.convert('RGB').tobytes()==final.tobytes()
  row=info(out);assert row['size']==list(SIZE)
  row.update(title=TITLES[i],native=n,input_to_resize=str(use.relative_to(ROOT)),new_generation=True,references=['reference/face-only.png','reference/body-only.png'],postprocess='Sky replacement logged in postprocess-log.json' if i==9 else 'Uniform Lanczos upscale and minimal center crop only')
  rows.append(row)
 assert len({r['native']['sha256'] for r in rows})==10 and len({r['sha256'] for r in rows})==10
 savejson('source-manifest.json',dict(share_url='https://xhslink.cn/o/6bdoxc66Ezp',note_title='带着小猫看晚霞的懒羊羊～',note_id='6afc0e24000000002b005031',acquisition='Original downloaded by GitHub Actions run45970566753, commit90f0348; exact bytes reused, no new CDN request',source=info(source),classic_source='https://xyy.huijiwiki.com/wiki/%E6%87%92%E7%BE%8A%E7%BE%8A',classic_status='Public fan-wiki reference, not independently certified official model sheet',classic=info(ROOT/'reference/classic-original.png'),visual_review_before_generation=True,reference_roles={'face-only.png':'Crop [40,1000,620,1360] of unchanged user source; face only, excludes misleading yellow limbs and platform mark','body-only.png':'Crop [110,363,370,590] of classic reference; white wool torso, yellow double-white-stripe bib, bare limbs'},user_decision='All non-face parts to be consistent; complete hidden body using classic animation'))
 savejson('output-manifest.json',dict(result_count=10,new_generation_calls=10,old_results_reused=False,final_size=list(SIZE),native_size=[704,1520],resolution_note='Lanczos upscaled and minimally center cropped, not native high resolution',reference_policy='Every generation independently attached the same face and classic body crops; no previous generated artwork used as input',files=rows,visual_review={'overview_reviewed':True,'notes':'All figures show bib and bare limbs without yellow sleeves or shoes; expressions, proportions and stripe rendering still have AI variation. 10 background duplicate repaired, full log included. Not a pixel-identical production model sheet.'}))
 entries=[(ROOT/r['file'],f'{i+1:02} · {r["title"]}') for i,r in enumerate(rows)]
 sheet(entries,'00-10张成品总预览.jpg','懒羊羊与小猫 · 身体重做版10场景','新参考可爱脸＋经典围兜与裸露手脚 · 852×1848')
 sheet([(source,'原片 · 原字节保留')]+entries,'00-原片与成品对照.jpg','新参考原片 ＋ 本轮10张新生成','原片与结果分开 · 不含弃用的黄袖子版本')
 sheet([(source,'新参考原片 · 853×1844'),(ROOT/'reference/classic-original.png','经典身体参考 · 500×590')],'00-原片与角色参考.jpg','参考资料 · 分工说明','第一张参考脸与绘本质感 · 第二张参考围兜、身体与裸露手脚')
 savejson('local-verification.json',dict(status='passed',final_count=10,unique_native=10,unique_final=10,final_size=list(SIZE),source_unchanged=True,previews=3,old_results_reused=False))
 mapping=[(source,'01-原片/01.jpg'),(ROOT/'reference/classic-original.png','01-角色参考/classic-original.png')]
 mapping += [(ROOT/r['file'],f'02-成品-852x1848/{i+1:02}-{r["title"]}.png') for i,r in enumerate(rows)]
 mapping += [(p,'03-预览/'+p.name) for p in sorted(ROOT.glob('00-*.jpg'))]
 mapping += [(ROOT/n,'04-说明与清单/'+n) for n in ['README.md','source-manifest.json','output-manifest.json','postprocess-log.json','local-verification.json']]
 out=REPO/'.local/delivery-bundles/懒羊羊与小猫-身体重做10场景-852x1848.zip';out.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p,n in mapping:z.writestr(n,p.read_bytes())
 with zipfile.ZipFile(out) as z:
  assert z.testzip() is None
  for p,n in mapping:assert z.read(n)==p.read_bytes()
 data=out.read_bytes();savejson('bundle-verification.json',dict(status='passed',file=str(out.relative_to(REPO)),bytes=len(data),md5=hashlib.md5(data).hexdigest(),sha256=hashlib.sha256(data).hexdigest(),member_count=len(mapping),all_members_exact_bytes=True,crc_passed=True))
 print(f'PASS: ten new unique artworks, ten {SIZE} finals, three previews, {len(mapping)} exact-byte ZIP members; ZIP {len(data)} bytes')
if __name__=='__main__':main()
