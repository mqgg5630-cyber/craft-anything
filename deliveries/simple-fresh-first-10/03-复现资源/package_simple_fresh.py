"""First-reference-only watercolor series: exact source size and vertical wishes.

Offline only. Reads ten independent temporary AI images (also bundled as rebuild
resources), fits proportionally to the first downloaded source size, typesets
Chinese text with a licensed brush font, and verifies each output immediately.
"""
import argparse
from collections import deque
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageStat

ROOT=Path(os.environ.get('FRESH_DELIVERY_ROOT','deliveries/simple-fresh-first-10'))
RAW=Path('.local/simple-fresh/raw')
SCENES=['红果平安','青红相伴','粉果清欢','柿柿顺心','橘暖生喜','榴实纳福','桃枝安然','梨香如意','葡萄成双','枇杷无忧']
WISHES=['平安喜乐','岁岁平安','喜乐安康','事事顺遂','大吉大利','福满人间','平安顺遂','万事胜意','好事成双','顺遂无忧']
RES=Path('03-复现资源')


@lru_cache(maxsize=32)
def font(size,brush=False):
    if brush:
        candidates=[Path('.local/simple-fresh/fonts/MaShanZheng-Regular.ttf'),ROOT/RES/'MaShanZheng-Regular.ttf']
    else:
        candidates=[Path('assets/fonts/cjk/NotoSansCJKsc-Regular.otf'),ROOT/RES/'NotoSansCJKsc-Regular.otf']
    for p in candidates:
        if p.is_file():return ImageFont.truetype(str(p),size)
    raise ValueError('Required licensed font missing; use bundled reproduction resources')


def record(path):
    data=path.read_bytes()
    with Image.open(path) as im:im.verify()
    with Image.open(path) as im:im.load();w,h=im.size
    return {'file':path.relative_to(ROOT).as_posix(),'width':w,'height':h,'bytes':len(data),
            'sha256':hashlib.sha256(data).hexdigest(),'md5':hashlib.md5(data).hexdigest()}


def largest_components(mask,count):
    """Bounded 8-connected mask components; remove detached paper-grunge marks."""
    w,h=mask.size
    if w*h>4_000_000:raise ValueError('Cleanup mask exceeds pixel budget')
    data=bytearray(1 if v>127 else 0 for v in mask.getdata())
    components=[]
    for start in range(len(data)):
        if not data[start]:continue
        data[start]=0;queue=deque([start]);members=[]
        while queue:
            p=queue.popleft();members.append(p);x=p%w;y=p//w
            for dy in (-1,0,1):
                ny=y+dy
                if not 0<=ny<h:continue
                for dx in (-1,0,1):
                    nx=x+dx
                    if not 0<=nx<w:continue
                    q=ny*w+nx
                    if data[q]:data[q]=0;queue.append(q)
        components.append(members)
    result=bytearray(w*h)
    for component in sorted(components,key=len,reverse=True)[:count]:
        for p in component:result[p]=255
    return Image.frombytes('L',(w,h),bytes(result))


def clean_background(image,bg):
    """Keep the watercolor branch and still life; clear accidental background stains.

Used on generated peach/pear assets only. This is not applied to downloaded art.
"""
    image=image.convert('RGB');w,h=image.size;r,g,b=image.split()
    chroma=ImageChops.subtract(ImageChops.lighter(r,ImageChops.lighter(g,b)),ImageChops.darker(r,ImageChops.darker(g,b)))
    light=image.convert('L')
    seed=ImageChops.lighter(
        ImageChops.multiply(chroma.point(lambda v:255 if v>=26 else 0),light.point(lambda v:255 if v<218 else 0)),
        ImageChops.multiply(chroma.point(lambda v:255 if v>=15 else 0),light.point(lambda v:255 if v<190 else 0)))
    # Separate top branch and bottom still life. No painted objects are needed in
    # the central text/negative-space region. Joining tiny gaps retains leaf edges.
    regions=[]
    for y0,y1,count in [(0,round(h*.325),1),(round(h*.75),h,3)]:
        zone=Image.new('L',(w,h));d=ImageDraw.Draw(zone)
        d.rectangle((0,y0,w,y1),fill=255)
        candidate=ImageChops.multiply(seed,zone).filter(ImageFilter.MaxFilter(5))
        regions.append(largest_components(candidate,count))
    mask=ImageChops.lighter(*regions).filter(ImageFilter.GaussianBlur(1.0))
    return Image.composite(image,Image.new('RGB',image.size,bg),mask)


def add_wish(image,index):
    result=image.convert('RGB');w,h=result.size;d=ImageDraw.Draw(result)
    size=round(w*.09);step=round(size*1.31);x=round(w*.80);y=round(h*.45)
    for i,char in enumerate(WISHES[index]):
        d.text((x,y+i*step),char,font=font(size,True),fill='#9c5147',anchor='mt')
    return result


def fit_thumbnail(canvas,path,box):
    x,y,w,h=box
    with Image.open(path) as im:thumb=ImageOps.contain(im.convert('RGB'),(w,h),Image.Resampling.LANCZOS)
    canvas.paste(thumb,(x+(w-thumb.width)//2,y+(h-thumb.height)//2))


def preview(files,target_size):
    w,h=target_size
    canvas=Image.new('RGB',(1630,1420),'#f2efe8');d=ImageDraw.Draw(canvas)
    d.text((34,20),'简单清新 · 十张四字祝福',font=font(43),fill='#80534a')
    d.text((36,85),f'只参考第一张  /  全部 {w} × {h} 像素  /  等比适配，不拉伸  /  竖排毛笔字，无手机 UI',font=font(21),fill='#8d8578')
    for i,p in enumerate(files):
        x,y=28+(i%5)*320,140+(i//5)*625
        d.rounded_rectangle((x-5,y-7,x+303,y+592),radius=9,fill='#e6e4da')
        fit_thumbnail(canvas,p,(x,y,292,558))
        d.text((x+5,y+566),f'{i+1:02d}  {WISHES[i]}',font=font(22),fill='#80534a')
    d.text((36,1390),'每张 PNG 独立保存；原片与成品分开。9 张轮播只取第一张，其余未下载、未用于生成。',font=font(18),fill='#8d8578')
    canvas.save(ROOT/'00-十张总预览.jpg',quality=94)


def main():
    source_manifest=json.loads((ROOT/'source-manifest.json').read_text())
    if source_manifest['source_count']!=1 or source_manifest.get('reference_image_index')!=1:
        raise ValueError('Exactly the first source image must be selected')
    row=source_manifest['images'][0];source=ROOT/row['file'];original=record(source)
    if any(original[k]!=row[k] for k in ('width','height','bytes','sha256','md5')):
        raise ValueError('Downloaded first source changed')
    target=(row['width'],row['height'])
    if target!=(884,1845):raise ValueError('Observed source-size contract changed unexpectedly')
    folder=RAW if RAW.is_dir() else ROOT/RES/'底图'
    raw=sorted(folder.glob('*.png'))
    if len(raw)!=10:raise ValueError('Require exactly ten independently generated art inputs')
    output=ROOT/'02-同尺寸四字祝福';output.mkdir(exist_ok=True)
    with Image.open(source) as im:
        sw,sh=im.size
        bg=tuple(int(v) for v in ImageStat.Stat(im.convert('RGB').crop((int(sw*.06),int(sh*.45),int(sw*.45),int(sh*.68)))).median)
    rows=[];files=[]
    for i,path in enumerate(raw):
        data=path.read_bytes()
        with Image.open(path) as im:
            im.load();native=im.size
            art=clean_background(im,bg) if i in (6,7) else im.convert('RGB')
            if i==7:
                # Clear two isolated grunge remnants outside the pear/cup/basket
                # silhouettes; these lie in otherwise empty background areas.
                d=ImageDraw.Draw(art);rw,rh=art.size
                d.rectangle((rw*.16,rh*.95,rw*.285,rh),fill=bg)
                d.rectangle((rw*.89,rh*.80,rw,rh*.88),fill=bg)
            scale=max(target[0]/native[0],target[1]/native[1])
            # ImageOps.fit uses a single isotropic scale followed by a centered
            # crop. It never stretches x and y independently.
            aligned=ImageOps.fit(art,target,Image.Resampling.LANCZOS,centering=(.5,.5))
            rendered=add_wish(aligned,i)
        dest=output/f'{i+1:02d}-{SCENES[i]}-{WISHES[i]}.png'
        rendered.save(dest,optimize=True)
        actual=record(dest)
        if (actual['width'],actual['height'])!=target:raise ValueError('Output must equal exact first-image pixels')
        files.append(dest)
        rows.append({'number':i+1,'scene':SCENES[i],'wish':WISHES[i],
                     'reference_image_index':1,'reference_sha256':row['sha256'],
                     'raw_file':path.name,'raw_dimensions':list(native),'raw_sha256':hashlib.sha256(data).hexdigest(),
                     'sizing':{'method':'single isotropic scale + centered crop, no axis stretch','scale':scale,
                               'crop_in_raw_pixels':[(native[0]-target[0]/scale)/2,(native[1]-target[1]/scale)/2],
                               'target_dimensions':list(target),'resampling':'Lanczos'},
                     'background_cleanup':i in (6,7),'text':{'layout':'four vertical characters','font':'Ma Shan Zheng Regular (SIL OFL)',
                                                            'color':'#9c5147','x_fraction':.8,'y_fraction':.45,'font_px':round(target[0]*.09)},
                     'result':actual})
    if len(list(output.glob('*.png')))!=10 or len({r['result']['sha256'] for r in rows})!=10:
        raise ValueError('Expected ten distinct final images')
    preview(files,target)
    manifest={'schema_version':1,'share_url':source_manifest['share_url'],'note_id':source_manifest['note_id'],
              'source_download_run':'https://github.com/mqgg5630-cyber/craft-anything/actions/runs/45524307533',
              'source_return_commit':'5927d55','only_first_reference':True,'other_carousel_images_downloaded_or_used':False,
              'previous_koi_or_other_note_art_used':False,'observed_carousel_count':source_manifest['observed_carousel_count'],
              'source':original,'output_count':10,'required_dimensions':list(target),
              'all_output_dimensions_identical_to_source':True,
              'generation':'Ten independent image-conditioned artworks. Native generated inputs are proportionally fitted to the first source exact pixel dimensions, then Chinese text is typeset. Not claimed native generation at final size.',
              'mobile_ui_added':False,'lettering':'Exactly one four-character wish per final image, deterministic licensed brush-font typesetting; no imitation author seals.',
              'outputs':rows,'previews':[record(ROOT/'00-十张总预览.jpg'),record(ROOT/'原片总预览.jpg')],
              'cloud_status':'Consult storage-verification.json if present.'}
    (ROOT/'output-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'source_dimensions':target,'final_count':10,'all_final_dimensions':sorted({(r['result']['width'],r['result']['height']) for r in rows}),'other_reference_images_used':0}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--raw',type=Path,default=RAW)
    args=parser.parse_args();ROOT=args.root;RAW=args.raw;main()
