"""Deterministic phone overlays and a validated folder archive for this delivery."""
import hashlib
import json
from pathlib import Path
from PIL import ImageStat
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
FONT = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')


def font(size):
    return ImageFont.truetype(str(FONT), size)


def overlay(image):
    """Return a new image; never draw into the clean wallpaper."""
    image = image.convert('RGBA')
    w, h = image.size
    layer = Image.new('RGBA', image.size)
    d = ImageDraw.Draw(layer)
    bright = ImageStat.Stat(image.convert('L').crop((0,int(h*.05),w,int(h*.25)))).mean[0]
    ink = (255, 249, 231, 255) if bright < 140 else (65, 58, 51, 255)
    def box(values):
        return tuple(round(v * w) for v in values)
    # Lock icon and date, followed by an intentionally legible dark blue clock.
    cx, y = w // 2, round(h * .063)
    d.rounded_rectangle((cx-9, y, cx+9, y+16), radius=4, fill=ink)
    d.arc((cx-6, y-11, cx+6, y+5), 180, 360, fill=ink, width=3)
    d.text((w / 2, h * .093), 'Monday, November 16', font=font(round(w * .039)), fill=ink, anchor='mt')
    d.text((w / 2, h * .123), '09:41', font=font(round(w * .19)), fill=ink, anchor='mt', stroke_width=0)
    # Top-right battery and reception: vector shapes, no external image assets.
    sx, sy = round(w * .83), round(h * .031)
    for i in range(4):
        d.rounded_rectangle((sx+i*6, sy+10-i*3, sx+i*6+3, sy+13), radius=1, fill=ink)
    d.rounded_rectangle((sx+33, sy, sx+62, sy+14), radius=3, outline=ink, width=2)
    d.rectangle((sx+36, sy+3, sx+56, sy+11), fill=ink)
    d.rectangle((sx+63, sy+5, sx+65, sy+9), fill=ink)
    # Flashlight and camera quick actions over translucent circular buttons.
    for x, kind in [(w*.15, 'light'), (w*.85, 'camera')]:
        x, y, r = round(x), round(h*.933), round(w*.042)
        d.ellipse((x-r,y-r,x+r,y+r), fill=(193,209,227,170), outline=(255,255,255,145), width=1)
        if kind == 'camera':
            d.rounded_rectangle((x-13,y-8,x+13,y+10), radius=4, outline=ink, width=2)
            d.ellipse((x-5,y-4,x+5,y+6), outline=ink, width=2)
            d.rectangle((x-7,y-12,x+5,y-8), fill=ink)
        else:
            d.polygon([(x-10,y-11),(x+10,y-11),(x+6,y-2),(x+4,y+12),(x-4,y+12),(x-6,y-2)], fill=ink)
            d.line((x-7,y-4,x+7,y-4), fill=(222,231,242,255), width=2)
    d.rounded_rectangle((w*.34,h*.977,w*.66,h*.981), radius=3, fill=ink)
    return Image.alpha_composite(image, layer).convert('RGB')


def record(path):
    data = path.read_bytes()
    with Image.open(path) as im:
        im.verify()
    with Image.open(path) as im:
        size = list(im.size)
    return {'file': str(path.relative_to(ROOT)), 'dimensions': size,
            'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def sheet(files, target):
    cols = 5
    rows = (len(files) + cols - 1) // cols
    result = Image.new('RGB', (cols*230+20, rows*540+20), '#e9edf3')
    d = ImageDraw.Draw(result)
    for i, path in enumerate(files):
        x, y = 20 + (i % cols)*230, 20 + (i // cols)*540
        with Image.open(path) as im:
            thumb = ImageOps.contain(im.convert('RGB'), (210, 490))
        d.text((x, y), path.name[:2], font=font(16), fill='#435367')
        result.paste(thumb, (x, y+26))
    result.save(target, quality=92)


def main():
    clean = sorted((ROOT/'02-复刻无手机UI').glob('*.png'))
    if len(clean) != 10: raise ValueError('Require ten clean images')
    ui=ROOT/'03-复刻有手机UI';ui.mkdir(exist_ok=True)
    records=[]
    for p in clean:
        before=hashlib.md5(p.read_bytes()).hexdigest()
        with Image.open(p) as im: overlay(im).save(ui/p.name)
        if hashlib.md5(p.read_bytes()).hexdigest()!=before: raise ValueError('Source changed')
        for f in [p,ui/p.name]:
            row=record(f);row['md5']=hashlib.md5(f.read_bytes()).hexdigest();records.append(row)
    for folder,label in [('02-复刻无手机UI','无UI'),('03-复刻有手机UI','有UI')]:
        p=ROOT/folder/'总预览.jpg';sheet(sorted((ROOT/folder).glob('*.png')),p)
        row=record(p);row['md5']=hashlib.md5(p.read_bytes()).hexdigest();records.append(row)
    (ROOT/'05-Skills/验收记录.json').write_text(json.dumps({'status':'local_complete_drive_separate','clean_count':10,'ui_count':10,'same_folder_previews':2,'ui':'illustrative not actual phone screenshot','files':records},ensure_ascii=False,indent=2))
    print('10 clean + 10 UI + 2 same-folder previews validated')
if __name__=='__main__': main()
