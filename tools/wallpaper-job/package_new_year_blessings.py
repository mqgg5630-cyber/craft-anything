"""Offline folder-only New Year collage delivery. No ZIP and no network."""
import argparse
from functools import lru_cache
import hashlib,json,math,random
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps,ImageChops

ROOT=Path('deliveries/new-year-blessings-10')
PAIRS=[('春来有信','花开有期'),('岁序更新','心有暖阳'),('长安常乐','好梦皆圆'),('心纳吉庆','日有小欢'),('福随春至','喜伴风来'),('灯火可亲','所遇皆暖'),('山河锦绣','前路生花'),('且听春语','静待花开'),('朝朝舒意','暮暮安然'),('良辰如约','新岁长宁')]
SOURCE_PHRASES=['欢喜由心','自在如风','爱财爱己','风生水起','安康如意','顺遂福来','萬穩萬當','不如一默','万稳万当','不如一黙']
SCENES=['梅信','茶暖','玉兰','竹喜','海棠','水仙','桃锦','兰语','花朝','腊梅']
# Positions track each independently generated blank paper slip.
POSITIONS=[(.70,.43,.30,.57),(.69,.31,.30,.66),(.70,.32,.29,.55),(.69,.38,.30,.55),(.70,.43,.30,.56),(.70,.38,.30,.58),(.70,.40,.30,.57),(.70,.37,.30,.57),(.70,.38,.30,.56),(.70,.38,.30,.55)]
RES=Path('03-制作资源')

@lru_cache(maxsize=12)
def font(size,brush=False):
    name='MaShanZheng-Regular.ttf' if brush else 'NotoSansCJKsc-Regular.otf'
    candidates=[ROOT/RES/name,Path('deliveries/simple-fresh-first-10/03-复现资源')/name]
    for p in candidates:
        if p.is_file():return ImageFont.truetype(str(p),size)
    raise ValueError('Missing bundled font '+name)

def record(path):
    data=path.read_bytes()
    with Image.open(path) as im:im.verify()
    with Image.open(path) as im:im.load();w,h=im.size
    return {'file':path.relative_to(ROOT).as_posix(),'width':w,'height':h,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'md5':hashlib.md5(data).hexdigest()}

def glyph(canvas,char,cx,cy,index,number):
    size=round(canvas.width*.108)
    tile=Image.new('RGBA',(size*2,size*2));d=ImageDraw.Draw(tile)
    rng=random.Random(number*71+index)
    d.text((size,size),char,font=font(size,True),fill=(31,29,24,246),anchor='mm')
    tile=tile.rotate(rng.uniform(-2.5,2.5),Image.Resampling.BICUBIC)
    canvas.paste(tile,(round(cx-tile.width/2+rng.uniform(-4,4)),round(cy-tile.height/2)),tile)

def flower_mark(canvas,number):
    """Original geometric floral ornament, not a copied signature or text seal."""
    d=ImageDraw.Draw(canvas,'RGBA');w,h=canvas.size;x=w*(.49+((number%3)-1)*.012);y=h*.20
    color=(157,74,52,105);radius=w*.037
    d.ellipse((x-radius,y-radius,x+radius,y+radius),outline=color,width=2)
    for j in range(5):
        a=2*math.pi*j/5-math.pi/2;px=x+math.cos(a)*radius*.40;py=y+math.sin(a)*radius*.40;r=radius*.25
        d.ellipse((px-r,py-r,px+r,py+r),outline=color,width=2)
    d.ellipse((x-3,y-3,x+3,y+3),fill=color)

def add_paper(canvas,x,y,height):
    w,h=canvas.size;box=(round(w*(x-.085)),round(h*y),round(w*(x+.085)),round(h*(y+height)))
    paper=canvas.crop((round(w*.42),round(h*.08),round(w*.56),round(h*.28))).convert('L')
    paper=ImageOps.colorize(paper,'#ded0ae','#f8f0d9').resize((box[2]-box[0],box[3]-box[1]))
    canvas.paste(paper,box[:2])

def render(raw,number,target):
    with Image.open(raw) as im:
        native=im.size;art=im.convert('RGB')
    crop=None
    if number==8:
        # Discard an unwanted AI-generated platform-like mark at the bottom.
        # Original downloaded references are never edited.
        crop=[0,0,art.width,round(art.height*.975)];art=art.crop(crop)
    art=ImageOps.fit(art,target,Image.Resampling.LANCZOS,centering=(.5,.5))
    if number==7:
        add_paper(art,.70,.345,.32);add_paper(art,.30,.535,.39)
    rx,ry,lx,ly=POSITIONS[number];w,h=target
    for col,(phrase,x,y) in enumerate(zip(PAIRS[number],(rx,lx),(ry,ly))):
        for j,char in enumerate(phrase):glyph(art,char,x*w,y*h+j*w*.143,j+col*4,number)
    flower_mark(art,number)
    return art,{'native_dimensions':list(native),'pre_fit_crop':crop,'method':'single isotropic Lanczos scale with centered crop; no axis stretching','target':list(target)}

def overview(files,target):
    sheet=Image.new('RGB',(1640,1550),'#eee7d6');d=ImageDraw.Draw(sheet)
    d.text((35,20),'新岁花笺 · 十张全新祝福',font=font(43),fill='#554c36')
    d.text((38,85),f'仿古绢纸 · 花枝拼贴 · 错落竖排  /  {target[0]} × {target[1]} 像素  /  文件夹交付，不打包 ZIP',font=font(20),fill='#887b60')
    for i,p in enumerate(files):
        x=30+i%5*324;y=140+i//5*680
        with Image.open(p) as im:thumb=ImageOps.contain(im.convert('RGB'),(296,615),Image.Resampling.LANCZOS)
        sheet.paste(thumb,(x+(296-thumb.width)//2,y))
        d.text((x,y+625),f'{i+1:02d} {PAIRS[i][0]} · {PAIRS[i][1]}',font=font(17),fill='#64553d')
    d.text((38,1515),'10 张独立 PNG；所有主文案已替换，花材与拼贴重新设计。原片、成品分文件夹保存。',font=font(19),fill='#887b60')
    sheet.save(ROOT/'00-十张总预览.jpg',quality=94)

def main():
    source=json.loads((ROOT/'source-manifest.json').read_text());sources=[]
    for row in source['images']:
        actual=record(ROOT/row['file'])
        if any(actual[k]!=row[k] for k in ('sha256','bytes','width','height')):raise ValueError('Source changed')
        sources.append(actual)
    target=(1080,2343)
    if any((s['width'],s['height'])!=target for s in sources):raise ValueError('Source-size contract changed')
    phrases=[p for pair in PAIRS for p in pair]
    if len(set(phrases))!=20 or any(len(p)!=4 or p in SOURCE_PHRASES for p in phrases):raise ValueError('All twenty phrases must be distinct and replaced')
    folder=ROOT/'02-十张新文案壁纸';folder.mkdir(exist_ok=True)
    rows=[];files=[]
    for i,pair in enumerate(PAIRS):
        raw=ROOT/RES/'底图'/f'{i+1:02d}.png';art,sizing=render(raw,i,target)
        out=folder/f'{i+1:02d}-{pair[0]}-{pair[1]}.png';art.save(out,optimize=True)
        files.append(out);rows.append({'number':i+1,'scene':SCENES[i],'right_phrase':pair[0],'left_phrase':pair[1],
            'source_reference_index':i%4+1,'raw':record(raw),'sizing':sizing,'result':record(out),'positions':list(POSITIONS[i])})
    if len(list(folder.glob('*.png')))!=10 or len({r['result']['sha256'] for r in rows})!=10:raise ValueError('Require ten distinct outputs')
    overview(files,target)
    manifest={'schema_version':1,'share_url':source['share_url'],'note_id':source['note_id'],'source_download_run':'https://github.com/mqgg5630-cyber/craft-anything/actions/runs/45526335316','source_return_commit':'9e864b6',
        'sources':sources,'output_count':10,'required_dimensions':list(target),'source_phrases_transcribed_for_nonreuse_check':SOURCE_PHRASES,'all_twenty_phrases_replaced':True,
        'generation':'Ten independent image-conditioned botanical paper collages. Native AI assets are 704x1520, proportionally enlarged and lightly cropped; final size is not claimed native generation.',
        'text':'Two four-character columns, Ma Shan Zheng Regular (SIL OFL), deterministic typesetting. No original calligraphy glyphs pasted.',
        'decoration':'New abstract floral roundels, not source author seals. No added mobile UI. Generated asset 09 has a bottom-edge crop to exclude an unwanted generated platform-like mark.',
        'delivery_format':'folders with individual images; no ZIP created or uploaded','outputs':rows,'previews':[record(ROOT/'00-十张总预览.jpg'),record(ROOT/'原片总预览.jpg')]}
    (ROOT/'output-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print(json.dumps({'outputs':10,'size':target,'new_phrases':20,'zip_created':False}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT);args=parser.parse_args();ROOT=args.root;main()
