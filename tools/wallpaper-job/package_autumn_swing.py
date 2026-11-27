"""Offline ten-image autumn swing delivery: exact original pixels, folders, no ZIP."""
import argparse
from functools import lru_cache
import hashlib,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps

ROOT=Path('deliveries/autumn-swing-10')
RAW=Path('.local/autumn-swing/raw')
SCENES=['金风轻荡','银杏溪光','枫林晚照','湖畔小憩','落叶来信','牧野余晖','秋河漫漫','白桦听风','麦野暮色','云湖晚安']
DESCRIPTIONS=['橡树与金色牧场，交叠小脚轻轻荡秋千','右侧银杏树、花海与蜿蜒小溪','左侧枫树、梯田晚霞与侧坐小羊','湖面余晖、远山与闭眼微笑的小羊','右侧大树、落叶与伸向远山的小路','木栅栏、金色牧场与轻轻后仰的秋千','弯曲的河流与傍晚的山谷','右侧白桦树、柔软云团和满地小花','落日、远山与稻草卷点缀的牧场','右侧树干、湖泊与绵软的大朵晚云']
EXTRA=Path('04-全流程与总览')

@lru_cache(maxsize=20)
def font(size):return ImageFont.truetype('assets/fonts/cjk/NotoSansCJKsc-Regular.otf',size)

def text(d,xy,value,size=24,fill='#705638'):d.text(xy,value,font=font(size),fill=fill)

def record(path):
    data=path.read_bytes();row={'file':path.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'md5':hashlib.md5(data).hexdigest()}
    if path.suffix.lower() in ('.jpg','.png'):
        with Image.open(path) as im:im.verify()
        with Image.open(path) as im:im.load();row.update(width=im.width,height=im.height)
    return row

def check(row):
    actual=record(ROOT/row['file'])
    if any(actual[k]!=row[k] for k in ('bytes','sha256','width','height')):raise ValueError('Image changed: '+row['file'])

def thumb(canvas,path,box):
    x,y,w,h=box
    with Image.open(path) as im:t=ImageOps.contain(im.convert('RGB'),(w,h),Image.Resampling.LANCZOS)
    canvas.paste(t,(round(x+(w-t.width)/2),round(y+(h-t.height)/2)))

def previews(source,outputs,target):
    extra=ROOT/EXTRA;extra.mkdir(exist_ok=True)
    sheet=Image.new('RGB',(1100,1180),'#f4ead5');d=ImageDraw.Draw(sheet)
    text(d,(40,25),'原片参考 · 秋天和秋千很配哦～',37)
    text(d,(42,88),f'1 张原片 / {target[0]} × {target[1]} 像素 / 原文件未修改',22)
    thumb(sheet,ROOT/source['file'],(100,145,440,955))
    for y,line in zip((220,285,350,415,480,570,635,700),('画风：温暖绘本与动画质感','色彩：橙金夕阳、暖黄草地','主体：黄围巾小羊与秋千','层次：树冠、远山、花草','留白：上半部宽阔晚霞天空','Actions 下载并解码校验','原片保留原有平台标识','只作参考，不是商用授权')):text(d,(580,y),line,22)
    sheet.save(extra/'01-原片总览.jpg',quality=94)

    sheet=Image.new('RGB',(1660,1690),'#f4ead5');d=ImageDraw.Draw(sheet)
    text(d,(35,25),'秋日轻荡 · 十张成品总览',44)
    text(d,(38,88),f'全部 {target[0]} × {target[1]} 像素 / 无字无手机 UI / 构图与景色各有变化',23)
    for i,row in enumerate(outputs):
        x=25+i%5*330;y=150+i//5*750
        thumb(sheet,ROOT/row['result']['file'],(x,y,308,670));text(d,(x+12,y+682),f'{i+1:02d}  {SCENES[i]}',23)
    text(d,(38,1650),'10 张独立 PNG；原片与结果分开保存，文件夹交付，不打 ZIP。',22)
    sheet.save(extra/'02-十张成品总览.jpg',quality=94)

    sheet=Image.new('RGB',(2200,1230),'#f4ead5');d=ImageDraw.Draw(sheet)
    text(d,(38,25),'原片 → 成品 · 十组风格与构图对照',42)
    text(d,(40,90),'每格左为同一张参考原片，右为新绘成品；不是十张不同原片，也不是简单滤镜换色。',23)
    for i,row in enumerate(outputs):
        x=25+i%5*438;y=150+i//5*525
        thumb(sheet,ROOT/source['file'],(x,y,193,420));thumb(sheet,ROOT/row['result']['file'],(x+214,y,193,420))
        text(d,(x,y+435),f'原片 01  →  成品 {i+1:02d}',21);text(d,(x,y+470),SCENES[i],22)
    sheet.save(extra/'03-原片成品对照.jpg',quality=94)

    sheet=Image.new('RGB',(2000,2480),'#f4ead5');d=ImageDraw.Draw(sheet)
    text(d,(45,25),'秋天和秋千 · 十张复刻全流程总预览',49)
    text(d,(47,100),f'{target[0]} × {target[1]} 像素 / 原片、结果分开 / 10 张独立 PNG / 不打 ZIP',25)
    text(d,(48,155),'原片参考 · 1 张',27);thumb(sheet,ROOT/source['file'],(45,205,320,435))
    lines=['01  Actions 下载原片 → 解码、尺寸与哈希校验','02  画风分析 → 橙金晚霞、树下秋千、黄围巾小羊','03  十张分别重绘 → 动作、树形、山谷、湖泊与光线变化',f'04  后期等比适配 → 精确到原片 {target[0]} × {target[1]} 像素','05  复核与交付 → 原片总览、十张总览、对照图、流程说明',f'以后默认成品尺寸：{target[0]} × {target[1]}（除非你另行指定）']
    for y,line in zip((220,290,360,430,500,570),lines):text(d,(440,y),line,27)
    text(d,(45,675),'成品总览 · 10 张全新绘制',29)
    for i,row in enumerate(outputs):
        x=32+i%5*396;y=735+i//5*790
        thumb(sheet,ROOT/row['result']['file'],(x,y,365,728));text(d,(x+12,y+740),f'{i+1:02d}  {SCENES[i]}',24)
    text(d,(45,2340),'制作说明：底图原生 704 × 1520，经单一比例 Lanczos 放大与轻微居中裁切，不拉伸变形。',23)
    text(d,(45,2400),'本批不加文字、手机 UI、作者署名或平台标识；原片保持原始下载字节。',23)
    sheet.save(ROOT/'00-全流程总预览.jpg',quality=94)
    return [record(ROOT/'00-全流程总预览.jpg')]+[record(p) for p in sorted(extra.glob('*.jpg'))]

def main():
    m=json.loads((ROOT/'source-manifest.json').read_text())
    if m['source_count']!=1:raise ValueError('Expected one reference from this note')
    source=m['images'][0];check(source);target=(source['width'],source['height'])
    if target!=(852,1848):raise ValueError('Verified original size changed')
    rawfolder=RAW if RAW.is_dir() else ROOT/'03-制作底图'
    raw=sorted(rawfolder.glob('*.png'))
    if len(raw)!=10:raise ValueError('Exactly ten preserved generation inputs required')
    out=ROOT/'02-十张复刻壁纸';out.mkdir(exist_ok=True);rows=[]
    for i,path in enumerate(raw):
        data=path.read_bytes()
        with Image.open(path) as im:
            im.load();native=im.size
            art=ImageOps.fit(im.convert('RGB'),target,Image.Resampling.LANCZOS,centering=(.5,.5))
        p=out/f'{i+1:02d}-{SCENES[i]}.png';art.save(p,optimize=True)
        r=record(p)
        if (r['width'],r['height'])!=target:raise ValueError('Output size mismatch')
        scale=max(target[0]/native[0],target[1]/native[1])
        rows.append({'number':i+1,'scene':SCENES[i],'description':DESCRIPTIONS[i],'reference_index':1,'reference_sha256':source['sha256'],
            'raw':{'file':'03-制作底图/'+path.name,'width':native[0],'height':native[1],'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'md5':hashlib.md5(data).hexdigest()},
            'sizing':{'method':'single isotropic scale and centered crop; no independent axis stretching','scale':scale,'target':list(target),'raw_crop_each_side':[(native[0]-target[0]/scale)/2,(native[1]-target[1]/scale)/2]},'result':r})
    if len(list(out.glob('*.png')))!=10 or len({r['result']['sha256'] for r in rows})!=10:raise ValueError('Require ten distinct final images')
    preview=previews(source,rows,target)
    report={'schema_version':1,'share_url':m['share_url'],'note_id':m['note_id'],'title':m['title'],'source_download_run':'https://github.com/mqgg5630-cyber/craft-anything/actions/runs/45967565012','source_return_commit':'546656b','sources':[source],'output_count':10,'required_dimensions':list(target),'all_output_dimensions_identical_to_source':True,'generation':'Ten independent reference-conditioned redraws, native 704x1520; proportionally enlarged and minimally centered-cropped. Not native generation at final size. No previous-note artwork used.','added_text':False,'mobile_ui_added':False,'source_watermark_copied':False,'delivery_format':'folders containing individual files; no ZIP','outputs':rows,'previews':preview}
    (ROOT/'output-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    process={'schema_version':1,'steps':['Actions-only public-note image download','Decode/dimension/SHA256 verification before same-branch publication','Visual style review','Ten independent reference-conditioned image generations','Isotropic resize plus centered crop to source exact pixel size','Visual review and integrity/count/dimension tests','Separate originals/results folders and Drive MD5/size verification'],'source_count':1,'independent_generations':10,'final_count':10,'dimensions':list(target),'source_unchanged':True,'zip_created':False,'status':'Local packaging complete; consult storage-verification.json for cloud state.'}
    (ROOT/'full-process.json').write_text(json.dumps(process,ensure_ascii=False,indent=2))
    print(json.dumps({'source_size':target,'outputs':10,'previews':len(preview),'zip_created':False}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--raw',type=Path,default=RAW);args=parser.parse_args();ROOT=args.root;RAW=args.raw;main()
