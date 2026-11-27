"""Offline deterministic packaging for autumn-swing (C5WkFiFa1r).

Verifies untouched original source/01.webp (852x1848), adapts the 10 independent
model-native backgrounds (artwork/01.png..10.png) via uniform Lanczos scaling and
minimal centered crop (~2px horizontal edge trim, zero non-uniform stretching) to
exact 852x1848 PNGs in images/01.png..10.png, builds three preview contact sheets
(00-总预览.jpg, 00-原片总预览.jpg, 00-10张成品总预览.jpg), and writes
output-manifest.json and local-verification.json.
"""
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
TARGET_SIZE = (852, 1848)
FONT_CJK = REPO / 'assets/fonts/cjk/NotoSansCJKsc-Regular.otf'

SCENES = [
    ('01', '树下轻荡', '左侧大树与麻绳木板秋千，懒羊羊坐秋千微呆萌望向前方，金橙夕阳与前景白雏菊景深'),
    ('02', '仰望流云', '低机位四分之三视角，懒羊羊在秋千上抬头微笑看飘落秋叶与流云，暖金草坡辽阔'),
    ('03', '红枫秋千', '右侧红金枫树镜像平衡构图，懒羊羊一手扶绳一手举起红枫叶端详，远山落日余晖'),
    ('04', '晃脚欢笑', '秋千迎着晚风轻轻前荡，懒羊羊弯眼欢笑，逆光金色斜阳洒满雏菊草地'),
    ('05', '银杏金雨', '金黄银杏树冠垂枝，懒羊羊在秋千上闭眼打盹小憩，扇形银杏叶随风飘落草甸'),
    ('06', '背影看夕阳', '诗意后侧视角，懒羊羊坐在秋千上面向层叠秋山与蜿蜒金溪落日，白绒卷发轮廓镀金光'),
    ('07', '秋千野餐篮', '秋日橡树下挂起木秋千，树根草丛放藤编苹果篮，懒羊羊双手抱红苹果开心晃腿（苹果遮挡胸前围兜）'),
    ('08', '蒲公英晚风', '高空长绳秋千取景（上方树枝位于画幅顶边之外），金色蒲公英绒球与秋叶掠过暖橘天空，懒羊羊手握发光蒲公英'),
    ('09', '暮色初星', '晚霞渐入柔暖暮色，上空浮现纤细新月，懒羊羊困倦倚靠秋千绳享受静谧余晖'),
    ('10', '站上秋千望远', '右侧秋树下懒羊羊稳稳站在秋千木板上双手高握麻绳，越过金色芦苇雏菊草甸眺望落日'),
]


def file_info(path: Path) -> dict:
    data = path.read_bytes()
    with Image.open(path) as im:
        im.verify()
    with Image.open(path) as im:
        im.load()
        width, height = im.size
        fmt = (im.format or '').lower()
    return {
        'file': str(path.relative_to(ROOT)).replace('\\', '/'),
        'format': fmt,
        'width': width,
        'height': height,
        'bytes': len(data),
        'md5': hashlib.md5(data).hexdigest(),
        'sha256': hashlib.sha256(data).hexdigest(),
    }


def adapt_to_target(im: Image.Image) -> Image.Image:
    return ImageOps.fit(
        im.convert('RGB'),
        TARGET_SIZE,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def render_sheet(
    items: list[tuple[Path, str, str]],
    out_path: Path,
    title: str,
    subtitle: str,
    cols: int,
) -> None:
    title_font = ImageFont.truetype(str(FONT_CJK), 26)
    sub_font = ImageFont.truetype(str(FONT_CJK), 16)
    label_font = ImageFont.truetype(str(FONT_CJK), 16)
    meta_font = ImageFont.truetype(str(FONT_CJK), 13)

    cell_w, thumb_h, meta_h, gap = 256, 536, 58, 20
    header_h = 98
    rows = math.ceil(len(items) / cols)
    canvas_w = cols * cell_w + (cols + 1) * gap
    canvas_h = header_h + rows * (thumb_h + meta_h + gap) + 12

    board = Image.new('RGB', (canvas_w, canvas_h), '#fbf4e6')
    draw = ImageDraw.Draw(board)
    draw.text((gap, 20), title, font=title_font, fill='#4a2f18')
    draw.text((gap, 58), subtitle, font=sub_font, fill='#7c5836')

    for idx, (img_path, line1, line2) in enumerate(items):
        col = idx % cols
        row = idx // cols
        x = gap + col * (cell_w + gap)
        y = header_h + row * (thumb_h + meta_h + gap)
        draw.rounded_rectangle(
            (x - 4, y - 4, x + cell_w + 4, y + thumb_h + meta_h),
            radius=10,
            fill='#f3e5cb',
            outline='#dfcaa4',
            width=1,
        )
        with Image.open(img_path) as src:
            thumb = ImageOps.contain(src.convert('RGB'), (cell_w - 8, thumb_h - 8), Image.Resampling.LANCZOS)
        tx = x + (cell_w - thumb.width) // 2
        ty = y + (thumb_h - thumb.height) // 2
        board.paste(thumb, (tx, ty))
        draw.text((x + 6, y + thumb_h + 4), line1, font=label_font, fill='#4a2f18')
        draw.text((x + 6, y + thumb_h + 29), line2, font=meta_font, fill='#7c5836')

    board.save(out_path, format='JPEG', quality=93, subsampling=0)


def main() -> None:
    source_manifest = json.loads((ROOT / 'source-manifest.json').read_text(encoding='utf-8'))
    if len(source_manifest.get('images', [])) != 1:
        raise ValueError('Expected exactly 1 verified carousel source image')
    src_entry = source_manifest['images'][0]
    src_path = ROOT / src_entry['file']
    src_actual = file_info(src_path)
    for key in ('width', 'height', 'format', 'bytes', 'md5', 'sha256'):
        if src_actual[key] != src_entry[key]:
            raise ValueError(f'Source verification mismatch on {key}')
    if (src_actual['width'], src_actual['height']) != TARGET_SIZE:
        raise ValueError('Source dimensions do not match 852x1848')

    images_dir = ROOT / 'images'
    images_dir.mkdir(exist_ok=True)

    records = []
    for index, (code, title, change_desc) in enumerate(SCENES):
        raw_path = ROOT / f'artwork/{code}.png'
        raw_meta = file_info(raw_path)
        with Image.open(raw_path) as raw_im:
            adapted = adapt_to_target(raw_im)
        out_path = images_dir / f'{code}.png'
        adapted.save(out_path, format='PNG', optimize=True)
        out_meta = file_info(out_path)
        scale = max(TARGET_SIZE[0] / raw_meta['width'], TARGET_SIZE[1] / raw_meta['height'])
        records.append({
            **out_meta,
            'index': index + 1,
            'title': title,
            'cloud_filename': f'{code}-{title}.png',
            'references': ['source/01.webp'],
            'allowed_variation': change_desc,
            'ui_overlay': False,
            'native_artwork': raw_meta,
            'adaptation': {
                'method': 'Single uniform Lanczos upscale + minimal centered horizontal crop (~1.9px/side); zero non-uniform stretching; adapted pixels are interpolated, not model-native',
                'uniform_scale': round(scale, 6),
                'scaled_dimensions': [round(raw_meta['width'] * scale, 2), round(raw_meta['height'] * scale, 2)],
                'final_dimensions': list(TARGET_SIZE),
            },
        })

    if len({r['sha256'] for r in records}) != 10:
        raise ValueError('Final 10 images are not all unique')
    if len({r['native_artwork']['sha256'] for r in records}) != 10:
        raise ValueError('Native 10 artworks are not all unique')

    src_items = [
        (src_path, '原片 01 · 笔记唯一下载图', f'852×1848 WebP · {src_actual["bytes"]} B'),
    ]
    out_items = [
        (ROOT / r['file'], f'{r["index"]:02d} · {r["title"]}', '852×1848 PNG · 无系统UI')
        for r in records
    ]

    render_sheet(
        src_items,
        ROOT / '00-原片总预览.jpg',
        '秋天和秋千很配哦～｜下载原片总预览（实际1张）',
        '笔记ID 6abdb5a9000000001802f193 · 852×1848 WebP · 保留原始字节未修改',
        cols=2,
    )
    render_sheet(
        out_items,
        ROOT / '00-10张成品总预览.jpg',
        '秋天和秋千很配哦～｜10张同系列独立复刻总预览',
        '全部参考原片 852×1848 等比适配输出 · 2D暖秋夕阳手绘动画风 · 无UI独立壁纸（非原作者新增原片）',
        cols=5,
    )
    render_sheet(
        src_items + out_items,
        ROOT / '00-总预览.jpg',
        '秋天和秋千很配哦～｜原片（1张）＋同系列复刻（10张）全流程总预览',
        '统一原片尺寸 852×1848 · 原片与复刻结果分目录存储 · 每次独立附原片生成',
        cols=6,
    )

    out_manifest_path = ROOT / 'output-manifest.json'
    prev = json.loads(out_manifest_path.read_text(encoding='utf-8')) if out_manifest_path.exists() else {}
    out_manifest = {
        'schema_version': 2,
        'share_url': 'https://xhslink.cn/o/C5WkFiFa1r',
        'note_id': '6abdb5a9000000001802f193',
        'reference_count_downloaded': 1,
        'generated_count': 10,
        'reference_dimensions': list(TARGET_SIZE),
        'default_persisted_dimensions': list(TARGET_SIZE),
        'all_native_artwork_dimensions': sorted({
            f'{r["native_artwork"]["width"]}x{r["native_artwork"]["height"]}' for r in records
        }),
        'style_summary': '2D warm golden-hour anime illustration with clean dark-brown character linework, painted sunset clouds, autumn foliage, rope swing, and soft bokeh foreground wildflowers (not 3D CGI)',
        'generation_method': '10 separate image-conditioned generations each directly referencing source/01.webp; never chained across generated outputs, never sliced from a grid',
        'ui_overlay': False,
        'status': prev.get('status', 'packaged_pending_visual_review'),
        'visual_review': prev.get('visual_review', {'status': 'pending'}),
        'files': records,
    }
    out_manifest_path.write_bytes(
        (json.dumps(out_manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    )

    previews = [
        file_info(ROOT / name)
        for name in ('00-总预览.jpg', '00-原片总预览.jpg', '00-10张成品总预览.jpg')
    ]
    local_ver = {
        'status': 'passed',
        'reference_count': 1,
        'native_artwork_count': 10,
        'final_wallpaper_count': 10,
        'preview_sheet_count': 3,
        'all_decoded_images': 24,
        'exact_final_dimensions': list(TARGET_SIZE),
        'unique_native_hashes': 10,
        'unique_final_hashes': 10,
        'source_bytes_preserved': True,
        'anisotropic_stretching': False,
        'ui_overlay': False,
        'previews': previews,
    }
    (ROOT / 'local-verification.json').write_bytes(
        (json.dumps(local_ver, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    )
    print('PASS: 1 verified source (852x1848), 10 unique 852x1848 finals, 3 preview boards written.')


if __name__ == '__main__':
    main()
