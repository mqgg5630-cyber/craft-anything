"""Offline exact-size adaptation and deterministic vertical Chinese typography."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageOps,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
BRUSH=REPO/'assets/fonts/cjk/MaShanZheng-Regular.ttf'
CJK=REPO/'assets/fonts/cjk/NotoSansCJKsc-Regular.otf'
PHRASES=['平安喜乐','万事胜意','日日欢喜','心有暖阳','顺遂无忧','好事发生','慢慢变好','一切如愿','喜乐常在','自在安然']
SCENES=['垂枝桑果与木盘陶碗','双层枝叶与圆罐','竹篮桑果与米色陶罐','斜枝桑果与双碗','浅盘桑果与高罐','陶杯果碟与长柄木勺','竹盘果碗与布盖罐','枝下果碗与散落桑果','淡墨桑叶与木盘果碗','长穗桑果与木盘果碗']

def details(path):
 data=path.read_bytes()
 with Image.open(path) as im:im.verify()
 with Image.open(path) as im:im.load();w,h=im.size;fmt=im.format.lower()
 return dict(file=str(path.relative_to(ROOT)),format=fmt,width=w,height=h,bytes=len(data),md5=hashlib.md5(data).hexdigest(),sha256=hashlib.sha256(data).hexdigest())

def sized_art(im,size):
 # Uniform scaling then tiny symmetric crop: never anisotropically stretch.
 return ImageOps.fit(im.convert('RGB'),size,method=Image.Resampling.LANCZOS,centering=(.5,.5))

def letter(im,phrase):
 out=im.copy();w,h=im.size;d=ImageDraw.Draw(out);font=ImageFont.truetype(str(BRUSH),76)
 layout=[]
 for i,char in enumerate(phrase):
  center=(round(w*.12),round(h*.49)+i*87)
  d.text(center,char,font=font,fill='#39372e',anchor='mm')
  layout.append(dict(character=char,center=list(center)))
 # One tiny plain cinnabar accent, deliberately not a forged artist stamp.
 x=round(w*.12);y=round(h*.49)+len(phrase)*87+7
 d.rectangle((x-7,y-7,x+7,y+7),fill='#a43936')
 return out,layout

def board(paths,labels,target,title,cols=5):
 cw,ch=220,461;gap=18;top=88;foot=42;rows=-(-len(paths)//cols)
 out=Image.new('RGB',(cols*cw+(cols+1)*gap,top+rows*(ch+foot+gap)),'#ede9dc');d=ImageDraw.Draw(out)
 d.text((gap,22),title,font=ImageFont.truetype(str(CJK),25),fill='#4c5f54')
 for i,p in enumerate(paths):
  x=gap+(i%cols)*(cw+gap);y=top+(i//cols)*(ch+foot+gap)
  with Image.open(p) as im:
   thumb=ImageOps.contain(im.convert('RGB'),(cw,ch),Image.Resampling.LANCZOS)
   out.paste(thumb,(x+(cw-thumb.width)//2,y+(ch-thumb.height)//2))
  d.text((x,y+ch+9),labels[i],font=ImageFont.truetype(str(CJK),18),fill='#4c5f54')
 out.save(target,quality=94)

def main():
 source=json.loads((ROOT/'source-manifest.json').read_text());assert len(source['images'])==1
 first=source['images'][0];target=(first['width'],first['height']);assert target==(884,1851)
 actual=details(ROOT/first['file'])
 for key in ['width','height','bytes','md5','sha256','format']:assert actual[key]==first[key]
 paths=sorted((ROOT/'artwork').glob('*.png'));assert [p.name for p in paths]==[f'{i:02}.png' for i in range(1,11)]
 assert len({details(p)['sha256'] for p in paths})==10
 (ROOT/'images').mkdir(exist_ok=True);records=[]
 for i,path in enumerate(paths):
  native=details(path)
  with Image.open(path) as im:
   base=sized_art(im,target);final,layout=letter(base,PHRASES[i]);final.save(ROOT/'images'/path.name)
  scale=max(target[0]/native['width'],target[1]/native['height'])
  records.append(dict(details(ROOT/'images'/path.name),phrase=PHRASES[i],scene=SCENES[i],references=['source/01.webp'],native_artwork=native,adaptation=dict(method='Uniform Lanczos scale then symmetric crop to EXACT first-reference size; no anisotropic stretch',uniform_scale=scale,continuous_scaled_size=[native['width']*scale,native['height']*scale],target_size=list(target),not_native_resolution=True),typography=dict(method='Locally typeset true Chinese glyphs, not model-generated lettering',font='MaShanZheng-Regular.ttf',font_size=76,fill='#39372e',layout=layout)))
 old_path=ROOT/'output-manifest.json';old=json.loads(old_path.read_text()) if old_path.exists() else {}
 old_path.write_text(json.dumps(dict(generated_count=10,final_count=10,reference_count=1,reference_image_index=1,all_final_size=list(target),other_note_images_used=False,koi_references_used=False,ui_generated=False,visual_review=old.get('visual_review','pending'),files=records),ensure_ascii=False,indent=2)+'\n')
 finals=sorted((ROOT/'images').glob('*.png'))
 board(finals,[f'{i+1:02} · {s}' for i,s in enumerate(PHRASES)],ROOT/'00-10张成品总预览.jpg','简单清新 · 仅参考第一张 · 884 × 1851')
 board([ROOT/first['file']]+finals,['原片01 · 884×1851']+[f'{i+1:02} · {s}' for i,s in enumerate(PHRASES)],ROOT/'00-原片与成品总预览.jpg','桑葚清韵 · 原片01与10张祝福壁纸')
 (ROOT/'local-verification.json').write_text(json.dumps(dict(source_count=1,generated_count=10,final_count=10,all_final_size=list(target),all_21_images_decoded=True,all_output_hashes_unique=True,source_hash_matches=True,all_phrases_four_characters=all(len(p)==4 for p in PHRASES),font_glyphs_locally_typeset=True,artwork_native_sizes=sorted({(r['native_artwork']['width'],r['native_artwork']['height']) for r in records}),adaptation='Resized with uniform scaling/cropping; final exact size not represented as native model size'),ensure_ascii=False,indent=2)+'\n')
 print('PASS: first reference only; 10 distinct artworks + 10 typeset PNGs, all finals 884x1851')
if __name__=='__main__':main()
