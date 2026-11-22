"""Offline sunset delivery packaging: preserve sources, overlay UI, audit and preview."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

ROOT = Path('deliveries/lulumei-sunset-10')
CJK = Path('assets/fonts/cjk/NotoSansCJKsc-Regular.otf')
DIGITS = Path('assets/fonts/DMSans-Medium.ttf')
SCENES = ['草坡奔赴', '并肩躺平', '溪石牵手', '山路同行', '码头日落',
          '花坡拥抱', '湖畔野餐', '芦苇晚风', '山坡风筝', '肩靠余晖']
REFERENCES = [[1], [2], [3], [4], [5], [1, 3], [2, 5], [3, 4], [1, 4], [5, 2]]


def font(size, digits=False):
    return ImageFont.truetype(str(DIGITS if digits else CJK), size)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(path):
    with Image.open(path) as im:
        im.verify()
    with Image.open(path) as im:
        im.load()
        w, h = im.size
    data = path.read_bytes()
    return {'file': path.relative_to(ROOT).as_posix(), 'width': w, 'height': h,
            'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'md5': hashlib.md5(data).hexdigest()}


def overlay(original):
    """Illustrative lock-screen overlay. Does not modify the input image."""
    image = original.convert('RGBA')
    w, h = image.size
    layer = Image.new('RGBA', image.size)
    d = ImageDraw.Draw(layer)
    scale = w / 768
    def p(x, y):
        return (round(w*x), round(h*y))
    def rect(box, **kw):
        d.rounded_rectangle((round(box[0]*w), round(box[1]*h), round(box[2]*w), round(box[3]*h)), **kw)
    ink = (255, 249, 235, 250)
    # Very subtle brown shadow, not a large opaque top bar over the sunset sky.
    text = Image.new('RGBA', image.size)
    td = ImageDraw.Draw(text)
    td.text(p(.5, .086), '11月22日  星期日', font=font(round(w*.033)), anchor='mt', fill=ink)
    td.text(p(.5, .112), '17:20', font=font(round(w*.185), True), anchor='mt', fill=ink)
    shadow = Image.new('RGBA', image.size)
    sd = ImageDraw.Draw(shadow)
    sd.text(p(.5, .086+2/h), '11月22日  星期日', font=font(round(w*.033)), anchor='mt', fill=(83, 54, 26, 100))
    sd.text(p(.5, .112+3/h), '17:20', font=font(round(w*.185), True), anchor='mt', fill=(83, 54, 26, 100))
    layer = Image.alpha_composite(layer, shadow.filter(ImageFilter.GaussianBlur(3*scale)))
    layer = Image.alpha_composite(layer, text)
    d = ImageDraw.Draw(layer)
    # Reception bars and battery, all proportional to the output size.
    sx, sy = w*.81, h*.027
    for i in range(4):
        x = sx+i*w*.009
        d.rounded_rectangle((x, sy+w*(.019-.005*i), x+w*.005, sy+w*.025), radius=1, fill=ink)
    rect((.868, .027, .916, .040), radius=round(w*.005), outline=ink, width=max(1, round(2*scale)))
    rect((.873, .030, .906, .037), radius=1, fill=ink)
    rect((.918, .031, .922, .036), radius=1, fill=ink)
    # Lock glyph centered above the date.
    cx, cy = p(.5, .058)
    r = w*.011
    d.arc((cx-r*.7, cy-r*1.5, cx+r*.7, cy+r*.2), 180, 360, fill=ink, width=max(1, round(2*scale)))
    d.rounded_rectangle((cx-r, cy-r*.3, cx+r, cy+r*1.1), radius=2*scale, fill=ink)
    # Flashlight and camera quick actions; these are simulations, not screenshots.
    for fx, kind in [(.16, 'light'), (.84, 'camera')]:
        x, y = p(fx, .928)
        r = w*.047
        d.ellipse((x-r, y-r, x+r, y+r), fill=(83, 57, 33, 75), outline=(255, 248, 229, 80), width=1)
        if kind == 'camera':
            d.rounded_rectangle((x-r*.48, y-r*.30, x+r*.48, y+r*.34), radius=4*scale, outline=ink, width=max(1, round(2*scale)))
            d.ellipse((x-r*.18, y-r*.16, x+r*.18, y+r*.20), outline=ink, width=max(1, round(2*scale)))
            d.rectangle((x-r*.28, y-r*.43, x+r*.15, y-r*.30), fill=ink)
        else:
            d.polygon([(x-r*.32,y-r*.42),(x+r*.32,y-r*.42),(x+r*.17,y-r*.1),
                       (x+r*.13,y+r*.43),(x-r*.13,y+r*.43),(x-r*.17,y-r*.1)], fill=ink)
            d.line((x-r*.24,y-r*.13,x+r*.24,y-r*.13),fill=(134,106,73,255),width=max(1,round(2*scale)))
    rect((.35, .976, .65, .980), radius=round(w*.003), fill=ink)
    return Image.alpha_composite(image, layer).convert('RGB')


def paste_fit(canvas, path, box):
    x, y, w, h = box
    with Image.open(path) as im:
        thumb = ImageOps.contain(im.convert('RGB'), (w, h), Image.Resampling.LANCZOS)
    canvas.paste(thumb, (x+(w-thumb.width)//2, y+(h-thumb.height)//2))


def result_sheet(files, title, dest):
    result = Image.new('RGB', (1570, 1250), '#f7efe4')
    d = ImageDraw.Draw(result)
    d.text((32, 22), title, font=font(36), fill='#664b34')
    d.text((32, 78), '01—05 参考重绘   /   06—10 同系列新场景', font=font(19), fill='#96765b')
    for i, path in enumerate(files):
        x, y = 30+(i%5)*308, 130+(i//5)*550
        paste_fit(result, path, (x, y, 278, 498))
        d.text((x, y+510), f'{i+1:02d}  {SCENES[i]}', font=font(20), fill='#664b34')
    result.save(dest, quality=93)


def total_sheet(clean, ui, sources):
    result = Image.new('RGB', (2000, 1390), '#f7efe4')
    d = ImageDraw.Draw(result)
    d.text((40, 22), '和你一起奔夕阳', font=font(52), fill='#62462f')
    d.text((42, 91), '10 张独立重绘与延展  ·  每组左：无 UI / 右：模拟锁屏 UI  ·  下方：5 张下载原片', font=font(24), fill='#96765b')
    for i, (c, u) in enumerate(zip(clean, ui)):
        x, y = 32+(i%5)*394, 155+(i//5)*414
        d.rounded_rectangle((x-8,y-5,x+374,y+396), radius=12, fill='#eee1d0')
        d.text((x+8, y+3), f'{i+1:02d}  {SCENES[i]}', font=font(24), fill='#62462f')
        paste_fit(result, c, (x, y+46, 175, 313))
        paste_fit(result, u, (x+187, y+46, 175, 313))
        d.text((x+45, y+365), '无 UI', font=font(18), fill='#96765b')
        d.text((x+222, y+365), '模拟 UI', font=font(18), fill='#96765b')
    d.line((40, 1000, 1960, 1000), fill='#d9c4a9', width=2)
    d.text((42, 1018), '下载原片 / 公开 CDN 文件', font=font(27), fill='#62462f')
    d.text((42, 1065), '5 张 · 1080×1920\n保留下载字节与标识\n不保证为作者母版\n\n01—05 对应参考重绘\n06—10 为新场景延展', font=font(20), fill='#96765b', spacing=7)
    for i, path in enumerate(sources):
        x = 420+i*300
        paste_fit(result, path, (x, 1040, 150, 267))
        d.text((x+25, 1313), f'原片 {i+1:02d}', font=font(20), fill='#96765b')
    d.text((42, 1352), 'AI 参考重绘 ≠ 原片；锁屏界面为设计模拟，非真实设备截图。单张文件与预览图分开交付。', font=font(20), fill='#96765b')
    result.save(ROOT / '00-总预览.jpg', quality=94)


def main():
    source_manifest = json.loads((ROOT/'source-manifest.json').read_text())
    sources = [ROOT / row['file'] for row in source_manifest['images']]
    if len(sources) != 5:
        raise ValueError('Expected five observed source images')
    for path, row in zip(sources, source_manifest['images']):
        if sha(path) != row['sha256']:
            raise ValueError('Source hash changed')
        actual = record(path)
        if [actual['width'], actual['height']] != [row['width'], row['height']]:
            raise ValueError('Source dimensions changed')
    clean = sorted((ROOT/'02-复刻无UI').glob('*.png'))
    if len(clean) != 10 or len({sha(p) for p in clean}) != 10:
        raise ValueError('Need ten distinct clean PNGs')
    folder = ROOT/'03-复刻模拟UI'
    folder.mkdir(exist_ok=True)
    pairs, ui = [], []
    for i, path in enumerate(clean):
        before = sha(path)
        with Image.open(path) as im:
            if im.height < im.width or not .53 < im.width/im.height < .59:
                raise ValueError('Result is not a portrait phone wallpaper')
            out = overlay(im)
        dest = folder/path.name
        out.save(dest, optimize=True)
        if sha(path) != before:
            raise ValueError('Clean image was mutated')
        ui.append(dest)
        pairs.append({'number': i+1, 'scene': SCENES[i], 'references': REFERENCES[i],
                      'kind': 'reference_redraw' if i < 5 else 'new_scene_same_series',
                      'clean': record(path), 'simulated_ui': record(dest)})
    if len(list(folder.glob('*.png'))) != 10:
        raise ValueError('Unexpected UI file count')
    result_sheet(clean, '无 UI 壁纸 · 十张总览', ROOT/'04-无UI总览.jpg')
    result_sheet(ui, '模拟锁屏 UI · 十张总览', ROOT/'05-模拟UI总览.jpg')
    total_sheet(clean, ui, sources)
    manifest = {'schema_version': 1, 'source_count': 5, 'clean_count': 10, 'simulated_ui_count': 10,
                'source_download_run': 'https://github.com/mqgg5630-cyber/craft-anything/actions/runs/45017817674',
                'source_return_commit': '213238f',
                'source_original_bytes_preserved': True,
                'generation': 'Ten independent image-conditioned AI outputs; first five reference redraws, last five new scenes. No upscaling.',
                'ui': 'Deterministic illustrative lock-screen overlay, not a real device screenshot.',
                'sources': [record(p) for p in sources], 'pairs': pairs,
                'previews': [record(ROOT/p) for p in ['00-总预览.jpg','04-无UI总览.jpg','05-模拟UI总览.jpg','原片总预览.jpg']],
                'cloud_status': 'not_uploaded'}
    (ROOT/'output-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'sources':5,'clean':10,'ui':10,'native_sizes':sorted({(p['clean']['width'],p['clean']['height']) for p in pairs})}))


if __name__ == '__main__':
    main()
