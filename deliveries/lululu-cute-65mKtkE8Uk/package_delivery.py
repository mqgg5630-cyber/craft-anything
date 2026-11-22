"""Offline decode/hash verification and previews; never downloads content."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
FONT = ROOT.parents[1] / 'assets/fonts/cjk/NotoSansCJKsc-Regular.otf'
PLAN = [
    ('害羞可爱噜', ['01'], '淡紫手账，捂眼大笑主角'),
    ('可爱满分', ['01'], '淡紫手账，捧脸歪头主角'),
    ('一起比心', ['02','03'], '奶油桃色，贴脸共同比心'),
    ('送你一颗心', ['02','03'], '奶油桃色，递送爱心'),
    ('捏捏脸颊', ['03'], '奶油桃色，轻捏脸颊'),
    ('一起读故事', ['03','02'], '奶油桃色，坐垫上一起读书'),
    ('大王驾到', ['04'], '公主茶会，王座与爱心蛋糕'),
    ('甜蜜下午茶', ['04','03'], '公主茶会，双人喝茶分享饼干'),
    ('超级爱你', ['05'], '奶油黄手账，捧心主角'),
    ('今天也开心', ['05','01'], '奶油黄手账，眨眼点赞主角'),
]


def details(path):
    data = path.read_bytes()
    with Image.open(path) as im:
        im.verify()
    with Image.open(path) as im:
        im.load()
        w,h = im.size
        fmt = im.format.lower()
    return {'file':str(path.relative_to(ROOT)), 'width':w, 'height':h, 'format':fmt,
            'bytes':len(data), 'md5':hashlib.md5(data).hexdigest(), 'sha256':hashlib.sha256(data).hexdigest()}


def sheet(paths, target, title, cell=(260,466)):
    cols = 5; rows = -(-len(paths)//cols); gap = 16; top = 100; label = 42
    w,h = cell
    board = Image.new('RGB', (cols*w+(cols+1)*gap, top+rows*(h+label+gap)+gap), '#fff9ed')
    d=ImageDraw.Draw(board)
    font=ImageFont.truetype(str(FONT),28); small=ImageFont.truetype(str(FONT),17)
    d.text((gap,22),title,font=font,fill='#645079')
    for i,path in enumerate(paths):
        x=gap+(i%cols)*(w+gap);y=top+(i//cols)*(h+label+gap)
        with Image.open(path) as im:
            board.paste(ImageOps.contain(im.convert('RGB'),cell,Image.Resampling.LANCZOS),(x,y))
        text = f'{i+1:02d} · '+(PLAN[i][0] if len(paths)==10 else '原片')
        d.text((x,y+h+8),text,font=small,fill='#645079')
    board.save(target,quality=93)


def main():
    manifest=json.loads((ROOT/'source-manifest.json').read_text())
    sources=[ROOT/item['file'] for item in manifest['images']]
    assert len(sources)==5
    for path,item in zip(sources,manifest['images']):
        actual=details(path)
        for k in ('width','height','format','bytes','md5','sha256'):
            assert actual[k]==item[k],(path.name,k)
    paths=sorted((ROOT/'images').glob('*.png'))
    assert [p.name for p in paths]==[f'{i:02d}.png' for i in range(1,11)]
    records=[]
    for i,path in enumerate(paths):
        title,refs,change=PLAN[i]
        records.append(dict(details(path),title=title,references=[f'source/{r}.webp' for r in refs],
                            change=change,generation='Independent reference-based AI recreation; no UI'))
    assert len({r['sha256'] for r in records})==10
    (ROOT/'output-manifest.json').write_text(json.dumps({'generated_count':10,'reference_count':5,
        'route':'xhs-link-recreate-10','status':'decoded_pending_visual_review',
        'quality_note':'Model-native PNG outputs; no upscaling; not author originals',
        'files':records},ensure_ascii=False,indent=2)+'\n')
    sheet(sources,ROOT/'00-原片总预览.jpg','今天是谁家的可爱噜啊 · 5张下载原片')
    sheet(paths,ROOT/'00-10张复刻总预览.jpg','今天是谁家的可爱噜啊 · 10张独立复刻')
    with Image.open(ROOT/'00-原片总预览.jpg') as a, Image.open(ROOT/'00-10张复刻总预览.jpg') as b:
        board=Image.new('RGB',(max(a.width,b.width),a.height+b.height+24),'#fff9ed')
        board.paste(a,(0,0));board.paste(b,(0,a.height+24));board.save(ROOT/'00-总预览.jpg',quality=93)
    (ROOT/'local-verification.json').write_text(json.dumps({'source_count':5,'output_count':10,
        'all_15_decoded':True,'source_hashes_match':True,'outputs_unique':True,
        'output_sizes':sorted({(r['width'],r['height']) for r in records})},indent=2)+'\n')
    print('Validated 5 sources and 10 unique outputs; wrote three previews')


if __name__=='__main__':
    main()
