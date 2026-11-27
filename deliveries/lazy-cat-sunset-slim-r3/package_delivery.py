"""Folder-only partial delivery. Never count a failed generation or a preview as artwork."""
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
import hashlib,json,math
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
SIZE=(852,1848)
TITLES={1:'海边拾贝',2:'田间单车',3:'花园秋千',4:'果园采摘',5:'老城电车（待补）',6:'荷塘纸船',7:'风车山坡',8:'阳台晚茶',9:'草地风筝',10:'书店小院'}
FONT=REPO/'assets/fonts/cjk/NotoSansCJKsc-Regular.otf'
def savejson(name,data): (ROOT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def info(p):
 data=p.read_bytes()
 with Image.open(p) as im:im.load();size=list(im.size)
 return dict(file=str(p.relative_to(ROOT)),size=size,bytes=len(data),md5=hashlib.md5(data).hexdigest(),sha256=hashlib.sha256(data).hexdigest())
def sheet(entries,name,title,subtitle):
 cols=min(5,len(entries));cw,ch=280,665;top=100
 b=Image.new('RGB',(max(560,cw*cols),top+math.ceil(len(entries)/cols)*ch+20),'#f7eedf');d=ImageDraw.Draw(b)
 f=ImageFont.truetype(str(FONT),25);s=ImageFont.truetype(str(FONT),17)
 d.text((18,15),title,font=f,fill='#5b4436');d.text((18,57),subtitle,font=s,fill='#80634d')
 for j,(p,label) in enumerate(entries):
  x=(j%cols)*cw;y=top+(j//cols)*ch
  if p is None:
   d.rounded_rectangle((x+10,y+15,x+cw-10,y+ch-60),radius=12,outline='#beac96',width=2)
   d.text((x+32,y+230),'05 生成失败，待补',font=s,fill='#80634d');d.text((x+32,y+265),'未用旧图或裁切图充数',font=s,fill='#80634d')
  else:
   with Image.open(p) as im:t=ImageOps.contain(im.convert('RGB'),(cw-16,ch-56),Image.Resampling.LANCZOS)
   b.paste(t,(x+(cw-t.width)//2,y))
  d.text((x+8,y+ch-40),label,font=s,fill='#5b4436')
 b.save(ROOT/name,quality=92,subsampling=0)
def main():
 source=ROOT/'reference/source-original.jpg';assert info(source)['sha256']=='7e6f54509d875ce81d811be3b710558c77be82ae5984226bcd2b53a22d55d04a'
 paths=sorted((ROOT/'artwork').glob('*.png'));expected=[1,2,3,4,6,7,8,9,10];assert [int(p.stem) for p in paths]==expected
 previous=json.loads((REPO/'deliveries/lazy-cat-sunset-corrected-r2/output-manifest.json').read_text());oldhash={r['native']['sha256'] for r in previous['files']}
 (ROOT/'images').mkdir(exist_ok=True);rows=[]
 for p in paths:
  i=int(p.stem);n=info(p);assert n['sha256'] not in oldhash
  with Image.open(p) as im:final=ImageOps.fit(im.convert('RGB'),SIZE,method=Image.Resampling.LANCZOS,centering=(.5,.5))
  out=ROOT/f'images/{i:02}.png'
  if not out.exists():final.save(out)
  else:
   with Image.open(out) as current:assert current.convert('RGB').tobytes()==final.tobytes()
  row=info(out);assert row['size']==list(SIZE);row.update(number=i,title=TITLES[i],native=n,new_generation=True,references=['reference/face-only.png','reference/classic-original.png'],adaptation='Uniform Lanczos upscale, minimal centered crop only; not native high resolution; no body warping')
  rows.append(row)
 assert len({r['native']['sha256'] for r in rows})==9 and len({r['sha256'] for r in rows})==9
 savejson('source-manifest.json',dict(share_url='https://xhslink.cn/o/6bdoxc66Ezp',acquisition='Reuse exact original downloaded in GitHub Actions45970566753, commit90f0348; no new CDN request',source=info(source),classic_source='https://xyy.huijiwiki.com/wiki/%E6%87%92%E7%BE%8A%E7%BE%8A',classic_status='Public fan-wiki, not independently certified official model sheet',classic=info(ROOT/'reference/classic-original.png'),visual_review_before_generation=True,role_policy='Face crop defines face and painterly style. Unmodified full classic reference defines bib and bare limbs. No rejected generated image reused as input. Body-only crop kept for provenance but not supplied to this round.',face_crop=[40,1000,620,1360]))
 savejson('output-manifest.json',dict(status='partial_9_of_10_pending_05',requested_count=10,result_count=9,complete=False,new_generation_calls_attempted=10,successful_new_generations=9,missing_numbers=[5],failures=[{'number':5,'initial_error':'Image generation failed. Try again.','retry_error':'Image generation limit of 10 reached for this turn.','replacement_or_old_result_used':False}],old_results_reused=False,delivery='Folders only; no ZIP requested or produced',final_size=list(SIZE),native_size=[704,1520],body_change='Prompts request narrow petite body, less wool volume, slender bare limbs; do not warp old images. Numerical proportions were generation guidance, not measured guarantees.',visual_review={'all9_reviewed':True,'notes':'Narrower bodies and less wool than rejected round; degree varies.07 has especially smooth lower wool contour and longer legs. Face, horn and limb proportions still show AI variation; user approval not assumed.'},files=rows))
 available={r['number']:r for r in rows};entries=[(ROOT/available[i]['file'] if i in available else None,f'{i:02} · {TITLES[i]}') for i in range(1,11)]
 sheet(entries,'00-成品总预览-9张已完成1张待补.jpg','轻巧身形重做 · 已完成9张／计划10张','05生成失败并触发本轮次数上限 · 占位框不计入成品')
 sheet([(source,'新参考原片 · 原字节保留')]+[(ROOT/r['file'],f'{r["number"]:02} · {r["title"]}') for r in rows],'00-原片与成品对照.jpg','原片 ＋ 本轮实际完成的9张','收窄身体与羊毛体积 · 成品852×1848 · 不含弃用版本')
 sheet([(source,'原片 · 853×1844'),(ROOT/'reference/classic-original.png','经典角色参考 · 500×590')],'00-原片与角色参考.jpg','参考资料 · 原始文件保持不变','原片参考可爱脸与绘本质感 · 经典参考围兜与裸露手脚')
 savejson('local-verification.json',dict(status='partial_delivery_integrity_passed',task_complete=False,requested=10,actual_final_count=9,missing=[5],unique_new_native=9,unique_final=9,final_size=list(SIZE),source_unchanged=True,previews=3,previews_not_counted_as_results=True,old_results_reused=False,zip_created=False))
 print('PASS partial integrity: nine genuinely new unique artworks, nine852x1848 finals, no05, noZIP. Task NOT complete10.')
if __name__=='__main__':main()
