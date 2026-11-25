"""Offline Koi Dream UI, preview and integrity manifest renderer.

No network calls or AI generation. Clean art and downloaded sources are immutable.
Extracted bundles can run this script with --root .; fonts are bundled separately.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(os.environ.get('KOI_DELIVERY_ROOT', 'deliveries/koi-dream-10'))
SCENES = ['双鲤成环', '碧波游梦', '金鳞照水', '朱鲤映月', '逐浪生辉',
          '荷间三愿', '月汀相逢', '花影听澜', '流金长梦', '莲开有期']
REFERENCES = [[2], [3], [2,3], [2], [2,3], [2,3], [2], [3], [2,3], [2,3]]
WISHES = ['时来运转', '锦鲤入梦', '金鳞纳福', '心愿成真', '好运将至',
          '三愿皆安', '所愿皆圆', '花开见喜', '福运绵长', '渐入佳境']


def font(size, digits=False):
    filename = 'DMSans-Regular.ttf' if digits else 'NotoSansCJKsc-Regular.otf'
    repo = Path('assets/fonts') / (filename if digits else 'cjk/'+filename)
    path = repo if repo.is_file() else ROOT/'04-复现资源'/filename
    return ImageFont.truetype(str(path), size)


def record(path):
    data=path.read_bytes()
    with Image.open(path) as im:
        im.verify()
    with Image.open(path) as im:
        im.load();w,h=im.size
    return {'file':path.relative_to(ROOT).as_posix(),'width':w,'height':h,
            'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
            'md5':hashlib.md5(data).hexdigest()}


def overlay(original, number):
    """Illustrative gold lockscreen only; input pixels are never modified."""
    image=original.convert('RGBA')
    w,h=image.size
    layer=Image.new('RGBA',image.size)
    d=ImageDraw.Draw(layer)
    ink='#765e34';soft='#9b8559'
    # The second reference composition keeps a fish in the top-right corner.
    cx=w*(.37 if number==1 else .5)
    d.text((cx,h*.066),'11月22日  星期日',font=font(round(w*.027)),fill=ink,anchor='mt')
    d.text((cx,h*.094),'9:41',font=font(round(w*.18),True),fill=ink,anchor='mt')
    d.text((cx,h*.218),WISHES[number],font=font(round(w*.032)),fill=soft,anchor='mt')
    def box(a,b,c,e):
        return (round(a*w),round(b*h),round(c*w),round(e*h))
    line=max(1,round(w*.002))
    # Lock, battery and reception are intentionally small; no device chassis.
    d.arc((cx-w*.008,h*.038,cx+w*.008,h*.051),180,360,fill=ink,width=line)
    d.rounded_rectangle((cx-w*.010,h*.044,cx+w*.010,h*.055),radius=w*.003,fill=ink)
    for i in range(4):
        x=.807+i*.009
        d.rounded_rectangle(box(x,.026+(3-i)*.002,x+.005,.036),radius=1,fill=ink)
    d.rounded_rectangle(box(.860,.024,.904,.037),radius=w*.003,outline=ink,width=line)
    d.rounded_rectangle(box(.865,.027,.896,.034),radius=1,fill=ink)
    d.rectangle(box(.907,.028,.911,.033),fill=ink)
    for fx,kind in [(.16,'light'),(.84,'camera')]:
        x,y,r=w*fx,h*.938,w*.043
        d.ellipse((x-r,y-r,x+r,y+r),fill=(255,252,241,165),outline=(208,190,145,120),width=line)
        if kind=='camera':
            d.rounded_rectangle((x-r*.48,y-r*.29,x+r*.48,y+r*.35),radius=w*.004,outline=ink,width=line)
            d.ellipse((x-r*.18,y-r*.14,x+r*.18,y+r*.21),outline=ink,width=line)
            d.rectangle((x-r*.25,y-r*.42,x+r*.17,y-r*.29),fill=ink)
        else:
            d.polygon([(x-r*.28,y-r*.42),(x+r*.28,y-r*.42),(x+r*.12,y-r*.09),
                       (x+r*.10,y+r*.41),(x-r*.10,y+r*.41),(x-r*.12,y-r*.09)],fill=ink)
    d.rounded_rectangle(box(.36,.978,.64,.981),radius=w*.003,fill=ink)
    return Image.alpha_composite(image,layer).convert('RGB')


def fit(canvas,path,box):
    x,y,w,h=box
    with Image.open(path) as im:
        thumb=ImageOps.contain(im.convert('RGB'),(w,h),Image.Resampling.LANCZOS)
    canvas.paste(thumb,(x+(w-thumb.width)//2,y+(h-thumb.height)//2))


def sheet(files,title,dest):
    canvas=Image.new('RGB',(1570,1250),'#f6f2e8')
    d=ImageDraw.Draw(canvas)
    d.text((30,22),title,font=font(36),fill='#3c625d')
    d.text((32,78),'01—02 对应参考重绘  /  03—10 同系列新构图  ·  独立原生 PNG，无放大',font=font(19),fill='#8c7c57')
    for i,p in enumerate(files):
        x,y=30+(i%5)*308,130+(i//5)*550
        fit(canvas,p,(x,y,278,498))
        d.text((x,y+510),f'{i+1:02d}  {SCENES[i]}',font=font(20),fill='#3c625d')
    canvas.save(dest,quality=94)


def total_sheet(clean,ui,sources):
    canvas=Image.new('RGB',(2000,1390),'#f7f3e9')
    d=ImageDraw.Draw(canvas)
    d.text((40,20),'锦鲤入梦',font=font(56),fill='#375f58')
    d.text((42,91),'10 张独立原画  ·  每组左：无 UI / 右：模拟锁屏 UI  ·  米白纸纹 / 青碧水色 / 朱金长尾',font=font(24),fill='#927b4a')
    for i,(c,u) in enumerate(zip(clean,ui)):
        x,y=32+(i%5)*394,155+(i//5)*414
        d.rounded_rectangle((x-8,y-5,x+374,y+396),radius=12,fill='#e7ece4')
        d.text((x+8,y+3),f'{i+1:02d}  {SCENES[i]}',font=font(24),fill='#42665e')
        fit(canvas,c,(x,y+46,175,313));fit(canvas,u,(x+187,y+46,175,313))
        d.text((x+45,y+365),'无 UI',font=font(18),fill='#897955')
        d.text((x+222,y+365),'模拟 UI',font=font(18),fill='#897955')
    d.line((40,1000,1960,1000),fill='#c9bc98',width=2)
    d.text((42,1018),'实际下载原片 / 3 个文件',font=font(27),fill='#42665e')
    d.text((42,1065),'01 为展示封面\n02、03 为独立壁纸\n保留下载字节与来源标识\n不保证为作者母版\n\n新作：2 张重绘＋8 张延展',font=font(20),fill='#897955',spacing=7)
    captions=['01 展示封面 · 1080×1440','02 壁纸 · 853×1844','03 壁纸 · 853×1844']
    for i,p in enumerate(sources):
        x=500+i*450
        fit(canvas,p,(x,1030,270,280))
        d.text((x-5,1316),captions[i],font=font(20),fill='#897955')
    d.text((42,1352),'AI 参考重绘 ≠ 原片；模拟锁屏非真实设备截图。无 UI 版不含时钟、短句、图标或人为水印。',font=font(20),fill='#897955')
    canvas.save(ROOT/'00-总预览.jpg',quality=94)


def main():
    manifest=json.loads((ROOT/'source-manifest.json').read_text())
    sources=[ROOT/r['file'] for r in manifest['images']]
    if manifest.get('note_id')!='6acb2a3800000000120390ba' or len(sources)!=3:
        raise ValueError('Wrong Koi Dream source note or carousel count')
    for row,path in zip(manifest['images'],sources):
        actual=record(path)
        if any(actual[k]!=row[k] for k in ('width','height','bytes','sha256','md5')):
            raise ValueError('Source bytes or dimensions changed')
    clean=sorted((ROOT/'02-复刻无UI').glob('*.png'))
    if len(clean)!=10 or len({record(p)['sha256'] for p in clean})!=10:
        raise ValueError('Need ten distinct original clean art files')
    folder=ROOT/'03-复刻模拟UI';folder.mkdir(exist_ok=True)
    pairs,ui=[],[]
    for i,p in enumerate(clean):
        before=record(p)
        with Image.open(p) as im:
            if not .53<im.width/im.height<.59:
                raise ValueError('Wrong phone wallpaper aspect ratio')
            result=overlay(im,i)
        dest=folder/p.name;result.save(dest,optimize=True)
        if record(p)!=before:
            raise ValueError('Clean artwork was modified')
        ui.append(dest)
        pairs.append({'number':i+1,'scene':SCENES[i],'reference_files':REFERENCES[i],
                      'kind':'reference_redraw' if i<2 else 'new_scene_same_series',
                      'ui_wish':WISHES[i],'clean':before,'simulated_ui':record(dest)})
    if len(list(folder.glob('*.png')))!=10:
        raise ValueError('Unexpected UI file count')
    sheet(clean,'锦鲤入梦 · 十张无 UI 总览',ROOT/'04-无UI总览.jpg')
    sheet(ui,'锦鲤入梦 · 十张模拟锁屏总览',ROOT/'05-模拟UI总览.jpg')
    total_sheet(clean,ui,sources)
    result={'schema_version':1,'source_count':3,'source_cover_count':1,'source_artwork_count':2,
            'clean_count':10,'simulated_ui_count':10,'source_original_bytes_preserved':True,
            'source_download_run':'https://github.com/mqgg5630-cyber/craft-anything/actions/runs/45522544591',
            'source_return_commit':'d2d19a5','source_roles':{'01.jpg':'presentation_cover','02.jpg':'wallpaper','03.jpg':'wallpaper'},
            'generation':'Ten independent image-conditioned AI artworks: two reference redraws and eight new compositions. No upscaling. Cover not used as artwork reference.',
            'clean':'No added clock, caption, icons, branding or watermark.',
            'ui':'Deterministic simulated lockscreen: 11月22日 星期日, 9:41, small wish and vector icons. Not device screenshots.',
            'sources':[record(p) for p in sources],'pairs':pairs,
            'previews':[record(ROOT/p) for p in ['00-总预览.jpg','04-无UI总览.jpg','05-模拟UI总览.jpg','原片总预览.jpg']],
            'cloud_status':'Consult storage-verification.json if present; this renderer does not upload.'}
    (ROOT/'output-manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'sources':3,'clean':10,'ui':10,'native_sizes':sorted({(p['clean']['width'],p['clean']['height']) for p in pairs})}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    ROOT=parser.parse_args().root
    main()
