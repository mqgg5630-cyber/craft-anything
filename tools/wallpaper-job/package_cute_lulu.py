"""Offline title typesetting, UI rendering and audited packaging of cute Lulu.

Default invocation rebuilds UI and previews from the ten saved clean wallpapers.
--typeset consumes the temporary AI art once, without editing source downloads.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path('deliveries/lulu-cute-10')
RAW = Path('.local/lulu-cute/raw')
CJK = Path('assets/fonts/cjk/NotoSansCJKsc-Regular.otf')
DIGITS = Path('assets/fonts/DMSans-Medium.ttf')
SCENES = ['比心贴贴', '捏脸偏爱', '公主茶会', '超能爱你', '可爱躲猫猫',
          '草莓抱抱', '奶油烘焙', '雨天同行', '书页晚安', '给你小花']
QUOTES = ['今天也要和你贴贴', '偏爱都给你', '你是我的小公主', '我的超能力\n就是超级爱你',
          '这么可爱怎么办', '把甜甜的爱给你', '和你烤出小幸福', '下雨也要一起走',
          '晚安也想抱抱你', '把花和偏爱都给你']
REFERENCES = [[1], [2], [3], [4], [5], [1, 2], [2, 3], [1, 2], [2, 5], [1, 3]]
TITLE_Y = [.225, .180, .205, .200, .250, .240, .235, .240, .235, .235]
COLORS = ['#9c5c68', '#9c5c68', '#a5744d', '#664932', '#765a9f',
          '#a45e74', '#967246', '#51778b', '#775b99', '#527968']


def font(size, digits=False):
    return ImageFont.truetype(str(DIGITS if digits else CJK), size)


def record(path):
    data = path.read_bytes()
    with Image.open(path) as im:
        im.verify()
    with Image.open(path) as im:
        im.load()
        w, h = im.size
    return {'file': path.relative_to(ROOT).as_posix(), 'width': w, 'height': h,
            'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'md5': hashlib.md5(data).hexdigest()}


def title_image(original, number):
    image = original.convert('RGB')
    w, h = image.size
    d = ImageDraw.Draw(image)
    size = round(w * ({3: .078, 4: .075}.get(number, .060)))
    lines = QUOTES[number].splitlines()
    for offset, line in enumerate(lines):
        d.text((w*.5, h*TITLE_Y[number] + offset*size*1.42), line, anchor='mt',
               font=font(size), fill=COLORS[number], stroke_width=max(2, round(w*.006)),
               stroke_fill='#fffdf8')
    return image


def overlay(original, number):
    """Dark, legible simulated lockscreen UI on these light pastel wallpapers."""
    image = original.convert('RGBA')
    w, h = image.size
    layer = Image.new('RGBA', image.size)
    d = ImageDraw.Draw(layer)
    ink = COLORS[number]
    def box(a, b, c, e):
        return (round(a*w), round(b*h), round(c*w), round(e*h))
    d.text((w*.5,h*.043), '11月22日  星期日', font=font(round(w*.027)), fill=ink, anchor='mt')
    d.text((w*.5,h*.073), '09:41', font=font(round(w*.145), True), fill=ink, anchor='mt')
    # Small lock glyph, status bars and battery. No hardware/device border.
    line = max(1, round(w*.0025))
    d.arc(box(.493,.023,.507,.036),180,360,fill=ink,width=line)
    d.rounded_rectangle(box(.489,.029,.511,.040),radius=w*.003,fill=ink)
    for i in range(4):
        x=.80+i*.009
        d.rounded_rectangle(box(x,.030+(3-i)*.002,x+.005,.040),radius=1,fill=ink)
    d.rounded_rectangle(box(.855,.028,.901,.041),radius=w*.004,outline=ink,width=line)
    d.rounded_rectangle(box(.86,.031,.892,.038),radius=1,fill=ink)
    d.rectangle(box(.904,.032,.908,.037),fill=ink)
    # Bottom quick actions are unobtrusive and do not alter the clean wallpaper.
    for fx, kind in [(.16,'light'),(.84,'camera')]:
        x,y,r=w*fx,h*.935,w*.042
        d.ellipse((x-r,y-r,x+r,y+r),fill=(255,255,255,155),outline=(255,255,255,210),width=line)
        if kind == 'camera':
            d.rounded_rectangle((x-r*.5,y-r*.28,x+r*.5,y+r*.35),radius=w*.004,outline=ink,width=line)
            d.ellipse((x-r*.19,y-r*.14,x+r*.19,y+r*.21),outline=ink,width=line)
            d.rectangle((x-r*.27,y-r*.42,x+r*.17,y-r*.27),fill=ink)
        else:
            d.polygon([(x-r*.30,y-r*.43),(x+r*.30,y-r*.43),(x+r*.13,y-r*.1),
                       (x+r*.10,y+r*.4),(x-r*.10,y+r*.4),(x-r*.13,y-r*.1)],fill=ink)
    d.rounded_rectangle(box(.35,.978,.65,.982),radius=w*.003,fill=ink)
    return Image.alpha_composite(image,layer).convert('RGB')


def fit(canvas, path, box):
    x,y,w,h=box
    with Image.open(path) as im:
        thumb=ImageOps.contain(im.convert('RGB'),(w,h),Image.Resampling.LANCZOS)
    canvas.paste(thumb,(x+(w-thumb.width)//2,y+(h-thumb.height)//2))


def sheet(files, title, dest):
    canvas=Image.new('RGB',(1570,1250),'#fff7f1')
    d=ImageDraw.Draw(canvas)
    d.text((30,22),title,font=font(36),fill='#76596a')
    d.text((32,78),'01—05 参考重绘  /  06—10 新场景延展  ·  中文采用字体精确排版',font=font(19),fill='#a28692')
    for i,path in enumerate(files):
        x,y=30+(i%5)*308,130+(i//5)*550
        fit(canvas,path,(x,y,278,498))
        d.text((x,y+510),f'{i+1:02d}  {SCENES[i]}',font=font(20),fill='#76596a')
    canvas.save(dest,quality=94)


def total_sheet(clean,ui,sources):
    canvas=Image.new('RGB',(2000,1390),'#fff8f4')
    d=ImageDraw.Draw(canvas)
    d.text((40,22),'今天是谁家的可爱噜啊',font=font(52),fill='#8f5c75')
    d.text((42,91),'10 张独立重绘与延展  ·  每组左：无 UI / 右：模拟锁屏 UI  ·  下方：5 张下载原片',font=font(24),fill='#a48696')
    for i,(c,u) in enumerate(zip(clean,ui)):
        x,y=32+(i%5)*394,155+(i//5)*414
        d.rounded_rectangle((x-8,y-5,x+374,y+396),radius=12,fill='#f5e9ed')
        d.text((x+8,y+3),f'{i+1:02d}  {SCENES[i]}',font=font(24),fill='#76596a')
        fit(canvas,c,(x,y+46,175,313));fit(canvas,u,(x+187,y+46,175,313))
        d.text((x+45,y+365),'无 UI',font=font(18),fill='#a28692')
        d.text((x+222,y+365),'模拟 UI',font=font(18),fill='#a28692')
    d.line((40,1000,1960,1000),fill='#e2cbd5',width=2)
    d.text((42,1018),'下载原片 / 公开 CDN 文件',font=font(27),fill='#76596a')
    d.text((42,1065),'5 张 · 941×1672\n保留下载字节与标识\n不保证为作者母版\n\n01—05 对应参考重绘\n06—10 为新场景延展',font=font(20),fill='#a28692',spacing=7)
    for i,p in enumerate(sources):
        x=420+i*300
        fit(canvas,p,(x,1040,150,267))
        d.text((x+25,1313),f'原片 {i+1:02d}',font=font(20),fill='#a28692')
    d.text((42,1352),'AI 参考重绘 ≠ 原片；锁屏界面为设计模拟，非真实设备截图。每张 PNG 独立保存，无放大。',font=font(20),fill='#a28692')
    canvas.save(ROOT/'00-总预览.jpg',quality=94)


def main(typeset=False):
    manifest=json.loads((ROOT/'source-manifest.json').read_text())
    sources=[ROOT/r['file'] for r in manifest['images']]
    if len(sources)!=5:
        raise ValueError('Expected five observed source images')
    for row,path in zip(manifest['images'],sources):
        actual=record(path)
        if any(actual[k]!=row[k] for k in ('width','height','bytes','sha256','md5')):
            raise ValueError('Source bytes or dimensions changed')
    clean_dir,ui_dir=ROOT/'02-复刻无UI',ROOT/'03-复刻模拟UI'
    clean_dir.mkdir(exist_ok=True);ui_dir.mkdir(exist_ok=True)
    if typeset:
        raw=sorted(RAW.glob('*.png'))
        if len(raw)!=10:
            raise ValueError('Require ten independently generated temporary artworks')
        for i,p in enumerate(raw):
            out=clean_dir/p.name
            if out.exists():
                raise ValueError('Refusing to overwrite an existing clean wallpaper')
            with Image.open(p) as im:
                title_image(im,i).save(out,optimize=True)
    clean=sorted(clean_dir.glob('*.png'))
    if len(clean)!=10:
        raise ValueError('Require ten clean wallpapers')
    ui,pairs=[],[]
    for i,p in enumerate(clean):
        before=record(p)
        with Image.open(p) as im:
            if not .53<im.width/im.height<.59:
                raise ValueError('Wrong phone wallpaper aspect ratio')
            out=overlay(im,i)
        dest=ui_dir/p.name;out.save(dest,optimize=True)
        if record(p)!=before:
            raise ValueError('Clean image was mutated')
        ui.append(dest)
        pairs.append({'number':i+1,'scene':SCENES[i],'quote':QUOTES[i],
                      'quote_position_y_fraction':TITLE_Y[i], 'references':REFERENCES[i],
                      'kind':'reference_redraw' if i<5 else 'new_scene_same_series',
                      'clean':before,'simulated_ui':record(dest)})
    if len(list(ui_dir.glob('*.png')))!=10 or len({r['clean']['sha256'] for r in pairs})!=10:
        raise ValueError('Unexpected result count or duplicate clean images')
    sheet(clean,'无 UI 壁纸 · 十张总览',ROOT/'04-无UI总览.jpg')
    sheet(ui,'模拟锁屏 UI · 十张总览',ROOT/'05-模拟UI总览.jpg')
    total_sheet(clean,ui,sources)
    result={'schema_version':1,'source_count':5,'clean_count':10,'simulated_ui_count':10,
            'source_download_run':'https://github.com/mqgg5630-cyber/craft-anything/actions/runs/45018698377',
            'source_return_commit':'6c206b7','source_original_bytes_preserved':True,
            'generation':'Ten independent image-conditioned AI artworks; first five reference redraws, last five new scenes. Titles deterministically typeset. No upscaling.',
            'ui':'Deterministic illustrative lockscreen, not real device screenshots. 2026-11-22, 09:41.',
            'sources':[record(p) for p in sources],'pairs':pairs,
            'previews':[record(ROOT/p) for p in ['00-总预览.jpg','04-无UI总览.jpg','05-模拟UI总览.jpg','原片总预览.jpg']],
            'cloud_status':'See storage-verification.json if present; packaging itself does not upload.'}
    (ROOT/'output-manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'sources':5,'clean':10,'ui':10,'native_sizes':sorted({(p['clean']['width'],p['clean']['height']) for p in pairs})}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--typeset',action='store_true')
    main(parser.parse_args().typeset)
