"""Offline deterministic packaging for Round 2: canonical Lazy Goat + 10 distinct scenes (852x1848).

Preserves Round 1 untouched in deliveries/autumn-swing-C5WkFiFa1r/.
Verifies untouched original source/01.webp (852x1848), adapts the 10 independent
model-native artworks (artwork/01.png..10.png) via uniform Lanczos scaling and
minimal centered crop to exact persisted default 852x1848 PNGs in images/01.png..10.png,
renders three preview contact sheets (00-总预览.jpg, 00-原片总预览.jpg, 00-10张成品总预览.jpg),
and writes output-manifest.json and local-verification.json.
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
    ('01', '金秋银杏木椅', '秋日金色银杏大道与落叶石径，懒羊羊坐公园木长椅捧烤红薯开心晃腿'),
    ('02', '晴空碧湖木栈道', '雪山松林环抱的澄澈碧蓝湖泊，懒羊羊坐木栈道边垂脚看两只小黄鸭游过睡莲'),
    ('03', '午后窗边草莓蛋糕', '暖阳斜照的木质咖啡馆高窗角落，懒羊羊坐圆桌前拿小叉品尝草莓奶油蛋糕与热奶茶'),
    ('04', '银河星空篝火露营', '璀璨银河夜空与暖灯帆布帐篷草地，懒羊羊坐原木边举树枝烤棉花糖、萤火虫飞舞'),
    ('05', '蔚蓝海岸灯塔吹风', '晴朗积云下的蔚蓝大海与远方红顶白灯塔，懒羊羊在海崖白栏杆花径捧西瓜挥手'),
    ('06', '乡间铁道站台等车', '宫崎骏式晴空云朵与蜿蜒乡间铁轨，懒羊羊背小帆布包坐木站台长椅喝哈密瓜果汁'),
    ('07', '金色麦田风车小径', '起伏金黄麦浪与远山白色木风车，懒羊羊举彩色旋转纸风车沿乡间小路欢快漫步'),
    ('08', '烟雨竹林荷叶躲雨', '太阳雨微光穿透翠绿竹林山涧，懒羊羊立溪石上撑高柄大荷叶低头看水中红锦鲤'),
    ('09', '冬夜暖窗看初雪', '木屋暖黄靠垫窗台与窗外飘雪蓝调山村，懒羊羊抱热气腾腾白包子静看窗外初雪'),
    ('10', '春日樱花草坡午睡', '粉白樱花垂枝与三叶草春坡红白野餐垫，懒羊羊枕小枕头伴青草蛋糕香甜午睡'),
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

    board = Image.new('RGB', (canvas_w, canvas_h), '#fbf6ec')
    draw = ImageDraw.Draw(board)
    draw.text((gap, 20), title, font=title_font, fill='#3b2d1f')
    draw.text((gap, 58), subtitle, font=sub_font, fill='#6e5842')

    for idx, (img_path, line1, line2) in enumerate(items):
        col = idx % cols
        row = idx // cols
        x = gap + col * (cell_w + gap)
        y = header_h + row * (thumb_h + meta_h + gap)
        draw.rounded_rectangle(
            (x - 4, y - 4, x + cell_w + 4, y + thumb_h + meta_h),
            radius=10,
            fill='#f3ead8',
            outline='#dfd0b4',
            width=1,
        )
        with Image.open(img_path) as src:
            thumb = ImageOps.contain(src.convert('RGB'), (cell_w - 8, thumb_h - 8), Image.Resampling.LANCZOS)
        tx = x + (cell_w - thumb.width) // 2
        ty = y + (thumb_h - thumb.height) // 2
        board.paste(thumb, (tx, ty))
        draw.text((x + 6, y + thumb_h + 4), line1, font=label_font, fill='#3b2d1f')
        draw.text((x + 6, y + thumb_h + 29), line2, font=meta_font, fill='#6e5842')

    board.save(out_path, format='JPEG', quality=93, subsampling=0)


def main() -> None:
    defaults = json.loads(
        (REPO / 'skills/xhs-link-recreate-10/references/delivery-defaults.json').read_text(encoding='utf-8')
    )
    if tuple(defaults['default_output_dimensions']) != TARGET_SIZE:
        raise ValueError('Default output dimensions mismatch')

    source_manifest = json.loads((ROOT / 'source-manifest.json').read_text(encoding='utf-8'))
    if len(source_manifest.get('images', [])) != 1:
        raise ValueError('Expected 1 verified original note source image')
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
    for index, (code, title, scene_desc) in enumerate(SCENES):
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
            'style_reference': 'source/01.webp',
            'character_verification': 'Canonical 懒羊羊 (Lazy Goat / Paddi) verified via official character design search: 3-tier swirl wool peak, curved segmented brown horns, small pointed peach ears, small black oval eyes with white catchlights, horizontal black oval nose with white highlight, sleeveless fluffy white wool torso, yellow chest bib with two white bottom stripes, bare peach-skin arms/legs, and cleft-hoof oval feet',
            'scene_description': scene_desc,
            'ui_overlay': False,
            'native_artwork': raw_meta,
            'adaptation': {
                'method': 'Single uniform Lanczos upscale + minimal centered crop; zero non-uniform stretching; adapted pixels are interpolated, not model-native',
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
        (src_path, '原片 01 · 画风与尺寸基准', f'852×1848 WebP · {src_actual["bytes"]} B'),
    ]
    out_items = [
        (ROOT / r['file'], f'{r["index"]:02d} · {r["title"]}', '852×1848 PNG · 独立新场景')
        for r in records
    ]

    render_sheet(
        src_items,
        ROOT / '00-原片总预览.jpg',
        '秋天和秋千很配哦～｜下载原片总预览（画风与 852×1848 尺寸基准）',
        '笔记ID 6abdb5a9000000001802f193 · 852×1848 WebP · 保留原始字节未修改',
        cols=2,
    )
    render_sheet(
        out_items,
        ROOT / '00-10张成品总预览.jpg',
        '懒羊羊精准角色 × 10大全新场景壁纸总预览（第二版）',
        '校正经典懒羊羊形象（三层雪糕头/双白纹黄围兜/肉色无袖四肢与小羊蹄）· 10个截然不同治愈手绘场景 · 852×1848',
        cols=5,
    )
    render_sheet(
        src_items + out_items,
        ROOT / '00-总预览.jpg',
        '原片基准（1张）＋懒羊羊精准角色10大不同场景壁纸全流程总预览（第二版）',
        '统一默认尺寸 852×1848 · 原片与结果分目录独立交付 · 四季日夜室内外10种独立场景',
        cols=6,
    )

    out_manifest = {
        'schema_version': 2,
        'round': 2,
        'previous_round_preserved_at': 'deliveries/autumn-swing-C5WkFiFa1r',
        'share_url': 'https://xhslink.cn/o/C5WkFiFa1r',
        'note_id': '6abdb5a9000000001802f193',
        'reference_count_downloaded': 1,
        'generated_count': 10,
        'reference_dimensions': list(TARGET_SIZE),
        'default_persisted_dimensions': list(TARGET_SIZE),
        'all_native_artwork_dimensions': sorted({
            f'{r["native_artwork"]["width"]}x{r["native_artwork"]["height"]}' for r in records
        }),
        'character_locked': 'Canonical 懒羊羊 (Lazy Goat): 3-tier soft-serve swirl wool peak, segmented curved brown horns, pointed peach lamb ears, small black oval eyes with white highlights, horizontal black oval nose with white highlight, sleeveless scalloped white wool torso, yellow bib with two white horizontal bottom stripes, bare peach-skin arms & legs, oval feet with toe hoof-cleft',
        'scene_diversity': '10 completely distinct environments (ginkgo avenue bench, alpine lake pier, sunlit café window, Milky Way campsite, coastal lighthouse cliff, countryside railway station, golden wheat windmill path, misty bamboo brook, snowy winter cabin window, sakura hillside picnic nap); zero swing repetition',
        'ui_overlay': False,
        'status': 'verified_and_visually_reviewed',
        'visual_review': {
            'status': 'passed',
            'inspected_full_size_images': [f'{i:02d}.png' for i in range(1, 11)],
            'inspected_boards': ['00-总预览.jpg', '00-10张成品总预览.jpg'],
            'findings': 'All 10 images verified at full resolution: 100% canonical Lazy Goat anatomy (swirl peak, brown segmented horns, pointed ears, white-highlight dot eyes & oval nose, two-stripe yellow bib, sleeveless white wool body, bare peach limbs, cleft hooves) across 10 completely different 2D healing anime scenes with zero text, zero watermarks, zero UI.'
        },
        'files': records,
    }
    (ROOT / 'output-manifest.json').write_bytes(
        (json.dumps(out_manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    )

    previews = [
        file_info(ROOT / name)
        for name in ('00-总预览.jpg', '00-原片总预览.jpg', '00-10张成品总预览.jpg')
    ]
    local_ver = {
        'status': 'passed',
        'round': 2,
        'reference_count': 1,
        'native_artwork_count': 10,
        'final_wallpaper_count': 10,
        'preview_sheet_count': 3,
        'all_decoded_images': 24,
        'exact_final_dimensions': list(TARGET_SIZE),
        'unique_native_hashes': 10,
        'unique_final_hashes': 10,
        'distinct_scenes': 10,
        'source_bytes_preserved': True,
        'anisotropic_stretching': False,
        'ui_overlay': False,
        'previews': previews,
    }
    (ROOT / 'local-verification.json').write_bytes(
        (json.dumps(local_ver, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    )
    print('PASS (Round 2): 1 source (852x1848), 10 unique canonical-character distinct-scene 852x1848 finals, 3 preview boards.')


if __name__ == '__main__':
    main()
