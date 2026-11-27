"""Offline full-process overviews for an existing verified ten-image delivery.

Does not regenerate, resize or modify originals/final wallpapers. No network/ZIP.
"""
from functools import lru_cache
import hashlib,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps

ROOT=Path('deliveries/new-year-blessings-10')
EXTRAS=ROOT/'04-全流程与总览'
DEFAULTS=Path(__file__).with_name('delivery-defaults.json')

@lru_cache(maxsize=16)
def font(size):
    return ImageFont.truetype('assets/fonts/cjk/NotoSansCJKsc-Regular.otf',size)

def text(d,xy,value,size=24,color='#645640'):
    d.text(xy,value,font=font(size),fill=color)

def thumb(canvas,path,box):
    x,y,w,h=box
    with Image.open(path) as im:im=ImageOps.contain(im.convert('RGB'),(w,h),Image.Resampling.LANCZOS)
    canvas.paste(im,(round(x+(w-im.width)/2),round(y+(h-im.height)/2)))

def verify(row):
    data=(ROOT/row['file']).read_bytes()
    if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Input changed: '+row['file'])
    with Image.open(ROOT/row['file']) as im:im.load();size=im.size
    if list(size)!=[row['width'],row['height']]:raise ValueError('Image size mismatch')

def record(path):
    data=path.read_bytes();row={'file':path.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'md5':hashlib.md5(data).hexdigest()}
    if path.suffix=='.jpg':
        with Image.open(path) as im:im.verify()
        with Image.open(path) as im:row.update(width=im.width,height=im.height)
    return row

def main():
    EXTRAS.mkdir(exist_ok=True)
    m=json.loads((ROOT/'output-manifest.json').read_text());policy=json.loads(DEFAULTS.read_text())
    sources=m['sources'];outputs=m['outputs']
    if len(sources)!=4 or len(outputs)!=10 or policy['wallpaper_size']!=[1080,2343]:raise ValueError('Delivery contract mismatch')
    rows=sources+[r['result'] for r in outputs]
    for row in rows:
        verify(row)
        if [row['width'],row['height']]!=policy['wallpaper_size']:raise ValueError('Final/source dimensions differ')
    sheet=Image.new('RGB',(1500,1070),'#f0e9d9');d=ImageDraw.Draw(sheet)
    text(d,(40,25),'原片总览 · 本篇 4 张公开参考图',40)
    text(d,(42,88),'全部 1080 × 2343 像素  /  Actions 下载并验证  /  原文件未修改',22)
    for i,row in enumerate(sources):
        thumb(sheet,ROOT/row['file'],(40+i*365,145,325,835))
        text(d,(75+i*365,990),f'原片 {i+1:02d} · 1080 × 2343',20)
    text(d,(42,1035),'原片保留原有文字及平台标识；仅用于风格参考，不是作者母版或商用授权。',18)
    sheet.save(EXTRAS/'01-原片总览.jpg',quality=94)

    sheet=Image.new('RGB',(2200,1220),'#eee7d6');d=ImageDraw.Draw(sheet)
    text(d,(40,20),'原片 → 成品 · 十张参考对应与文案替换',42)
    text(d,(42,88),'每格左为参考原片，右为新成品；风格衍生，不是逐像素复印。成品均为 1080 × 2343。',23)
    for i,row in enumerate(outputs):
        x=30+i%5*438;y=145+i//5*520;source=sources[row['source_reference_index']-1]
        thumb(sheet,ROOT/source['file'],(x,y,195,430));thumb(sheet,ROOT/row['result']['file'],(x+216,y,195,430))
        text(d,(x,y+438),f'原片 {row["source_reference_index"]:02d}  →  成品 {i+1:02d}',20)
        text(d,(x,y+470),row['right_phrase']+' · '+row['left_phrase'],19)
    sheet.save(EXTRAS/'02-原片与十张成品对照.jpg',quality=94)

    sheet=Image.new('RGB',(2000,2460),'#efe8d6');d=ImageDraw.Draw(sheet)
    text(d,(42,25),'新岁花笺 · 十张复刻全流程总预览',49)
    text(d,(44,99),'1080 × 2343 像素  /  20 句文案全部替换  /  原片与结果分开  /  文件夹交付，不打 ZIP',24)
    text(d,(45,153),'01  原片参考 · 4 张',28)
    for i,row in enumerate(sources):thumb(sheet,ROOT/row['file'],(45+i*220,205,195,410))
    for y,line in zip((220,280,340,400,460,520),(
        '02  提炼风格：仿古绢纸、花枝、错落纸条',
        '03  重绘变化：10 份花材与拼贴各不相同',
        '04  替换文案：每张两列，共 20 句新祝福',
        '05  后期排版：毛笔字、等比适配、原图同尺寸',
        '06  校验交付：4 张原片 + 10 张独立 PNG',
        '以后默认尺寸：1080 × 2343，除非另行指定')):text(d,(980,y),line,25)
    text(d,(45,648),'成品总览 · 10 张（沿用上一轮已完成作品，本次补齐流程资料）',28)
    for i,row in enumerate(outputs):
        x=32+i%5*396;y=705+i//5*800
        thumb(sheet,ROOT/row['result']['file'],(x,y,365,740))
        text(d,(x+10,y+753),f'{i+1:02d}  {row["right_phrase"]} · {row["left_phrase"]}',21)
    text(d,(45,2335),'原片下载 → 风格分析 → 花材拼贴重绘 → 全文案替换 → 精确尺寸排版 → 校验并分文件夹上传',24)
    text(d,(45,2395),'底图原生 704 × 1520，经等比放大及轻微裁切适配；不声称最终尺寸为原生生成，不拉伸变形。',21)
    sheet.save(EXTRAS/'00-全流程总预览.jpg',quality=94)

    table='编号,右列文案,左列文案,参考原片,宽,高\n'+''.join(f'{r["number"]:02d},{r["right_phrase"]},{r["left_phrase"]},{r["source_reference_index"]:02d},1080,2343\n' for r in outputs)
    (EXTRAS/'十张文案与尺寸表.csv').write_text(table,encoding='utf-8-sig')
    (EXTRAS/'全流程说明.md').write_text('''# 新岁花笺 · 完整制作与交付说明

本次沿用上一轮完成的10张成品，补齐总览、对照、流程资料，没有假称重新生成另一批10张。

## 1. 下载与验证原片
原链接：https://xhslink.cn/o/3kQq76Fee2O 。已通过 GitHub Actions 下载4张公开参考图，每张1080×2343像素；原文件字节未修改。未在本地重新请求小红书或CDN。
运行：https://github.com/mqgg5630-cyber/craft-anything/actions/runs/45526335316 ，原片返回提交9e864b6。

## 2. 风格分析与变化
提取仿古绢纸、浅米色错落纸条、花枝拼贴、竖排毛笔字。重新生成10份花材和纸张拼贴：梅、茶花、玉兰、竹与南天竹、海棠、水仙、桃、兰、花枝、腊梅。不是原图逐像素复制，也不冒充原作者作品。

## 3. 全部替换文案
每张两列四字短语，共20句新文案，均不复用参考图主文案。完整清单见同目录CSV；上一轮成品已完成该替换，本次未修改成品。

## 4. 后期排版与尺寸
底图原生704×1520，通过单一比例Lanczos放大及轻微居中裁切到1080×2343，不横纵轴分别拉伸。第8张加纹理纸条，第9张裁去底边非预期平台样式标记。中文用SIL OFL许可的Ma Shan Zheng毛笔字确定性排版；不粘贴原作者字形、署名或印章。

## 5. 校验
解码检查4张原片和10张成品；检查像素、字节数、SHA256、MD5、10份成品互异、20句文案互异、原片不变。上一轮离线重建校验证明10张及总览字节一致。本次再次校验现有文件，不假称重新下载或重跑AI生成。

## 6. 文件夹交付
- 01-下载原片：4张原片，未修改。
- 02-十张新文案壁纸：10张最终PNG，不掺原片。
- 03-制作底图备份：实际AI生成底图，非最终壁纸。
- 04-全流程与总览：本说明、原片总览、原片/成品对照、全流程总预览及CSV。
- 总目录另有10张成品总览。
不创建ZIP。云端文件大小和MD5与本地核对，校验记录在JSON；不声称重新下载云端文件。

## 以后默认规则（用户本次明确指定）
成品统一1080×2343像素，除非用户明确更改；新参考原图如尺寸不同，仍原样保存，不为匹配成品而改动原片。原片与结果分文件夹，不打ZIP，附总览和流程。机器可读规则保存在tools/wallpaper-job/delivery-defaults.json。

原片版权归原权利人；本交付不赋予原图商业使用权。AI风格衍生作品不声称是原作者作品。
''',encoding='utf-8')
    generated=[record(p) for p in sorted(EXTRAS.iterdir()) if p.suffix in ('.jpg','.csv','.md')]
    report={'schema_version':1,'existing_artwork_reused':True,'new_ai_generations_this_followup':0,'original_count':4,'result_count':10,'standard_dimensions':policy['wallpaper_size'],'originals_and_results_separate':True,'zip_created':False,'originals_and_final_images_unchanged':True,'source_run':m['source_download_run'],'previous_rebuild_verification':json.loads((ROOT/'rebuild-verification.json').read_text()),'generated_supplements':generated,'cloud_status':'See process-storage-verification.json after upload; existing image verification remains storage-verification.json.'}
    (EXTRAS/'full-process.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'validated_originals':4,'validated_results':10,'new_supplements':len(generated)+1,'standard_size':policy['wallpaper_size'],'existing_art_unchanged':True}))

if __name__=='__main__':main()
