#!/usr/bin/env python3
"""Build clean phone wallpapers and separate iOS lock-screen previews from ten artworks."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

SUPPORTED = {".png", ".jpg", ".jpeg", ".webp", ".avif"}
CANVAS = (1440, 3200)


def natural_key(path: Path) -> tuple[object, ...]:
    return tuple(int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name))


def font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    paths = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    )
    for path in paths:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def centered_text(draw: ImageDraw.ImageDraw, y: int, text: str, selected_font: ImageFont.ImageFont,
                  *, fill: tuple[int, int, int, int], stroke_width: int = 0) -> None:
    bounds = draw.textbbox((0, 0), text, font=selected_font, stroke_width=stroke_width)
    x = (CANVAS[0] - (bounds[2] - bounds[0])) // 2
    draw.text((x, y), text, font=selected_font, fill=fill, stroke_width=stroke_width,
              stroke_fill=(0, 0, 0, 90))


def make_ios_preview(wallpaper: Image.Image, date: str, time_text: str) -> Image.Image:
    image = wallpaper.convert("RGBA")
    overlay = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    white = (255, 255, 255, 242)

    # A very soft top veil keeps the clock legible while leaving the art visible.
    for y in range(0, 1120):
        alpha = max(0, 50 - int(50 * y / 1120))
        if alpha:
            draw.line((0, y, CANVAS[0], y), fill=(8, 16, 38, alpha))

    # Status row and date/time are vector text, not generated into the wallpaper.
    draw.text((112, 94), "9:41", font=font(48, bold=True), fill=white)
    # Signal, Wi-Fi and battery glyphs drawn with simple geometric primitives.
    for level in range(4):
        x = 1136 + level * 24
        draw.rounded_rectangle((x, 144 - (level + 1) * 15, x + 13, 145), radius=5, fill=white)
    draw.arc((1236, 92, 1298, 148), 205, 335, fill=white, width=8)
    draw.arc((1248, 105, 1286, 145), 205, 335, fill=white, width=7)
    draw.ellipse((1264, 132, 1272, 140), fill=white)
    draw.rounded_rectangle((1320, 104, 1384, 140), radius=9, outline=white, width=5)
    draw.rounded_rectangle((1327, 111, 1370, 133), radius=5, fill=white)
    draw.rectangle((1387, 115, 1394, 129), fill=white)

    centered_text(draw, 298, date, font(66, bold=True), fill=white, stroke_width=1)
    centered_text(draw, 390, time_text, font(288, bold=True), fill=white, stroke_width=2)

    # Lock-screen actions and home indicator.
    for cx in (226, 1214):
        draw.ellipse((cx - 94, 2834 - 94, cx + 94, 2834 + 94), fill=(15, 22, 38, 112),
                     outline=(255, 255, 255, 72), width=3)
    # Flashlight icon
    draw.rounded_rectangle((205, 2782, 247, 2850), radius=10, outline=white, width=8)
    draw.polygon(((216, 2771), (236, 2771), (243, 2782), (209, 2782)), fill=white)
    # Camera icon
    draw.rounded_rectangle((1171, 2804, 1257, 2860), radius=13, outline=white, width=7)
    draw.rounded_rectangle((1190, 2793, 1222, 2807), radius=5, fill=white)
    draw.ellipse((1201, 2817, 1228, 2844), outline=white, width=6)
    draw.rounded_rectangle((468, 3110, 972, 3130), radius=10, fill=(255, 255, 255, 242))
    return Image.alpha_composite(image, overlay).convert("RGB")


def build_set(art_dir: Path, output_dir: Path, date: str, time_text: str) -> dict[str, object]:
    inputs = sorted((item for item in art_dir.iterdir() if item.is_file() and item.suffix.lower() in SUPPORTED), key=natural_key)
    if len(inputs) != 10:
        raise ValueError(f"expected exactly 10 source artworks; found {len(inputs)}")
    clean_dir = output_dir / "无手机UI"
    preview_dir = output_dir / "手机UI预览"
    clean_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    for index, source in enumerate(inputs, 1):
        with Image.open(source) as opened:
            clean = ImageOps.fit(opened.convert("RGB"), CANVAS, method=Image.Resampling.LANCZOS,
                                 centering=(0.5, 0.5))
        filename = f"{index:02d}.png"
        clean.save(clean_dir / filename, format="PNG", optimize=True)
        preview = make_ios_preview(clean, date, time_text)
        preview.save(preview_dir / f"{index:02d}.jpg", format="JPEG", quality=94, optimize=True)
        records.append({
            "index": index, "source": source.name,
            "clean": f"无手机UI/{filename}",
            "preview": f"手机UI预览/{index:02d}.jpg",
            "width": CANVAS[0], "height": CANVAS[1],
        })
    manifest = {
        "schema_version": 1,
        "canvas": list(CANVAS),
        "count": 10,
        "ui_preview": {"date": date, "time": time_text, "type": "ios-lock-screen-overlay"},
        "images": records,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("art_dir", type=Path, help="folder containing exactly 10 generated artworks")
    parser.add_argument("output_dir", type=Path, help="folder for separate clean and UI-preview outputs")
    parser.add_argument("--date", default="Monday, November 16")
    parser.add_argument("--time", dest="time_text", default="9:41")
    args = parser.parse_args()
    manifest = build_set(args.art_dir, args.output_dir, args.date, args.time_text)
    print(f"rendered {manifest['count']} clean wallpapers and {manifest['count']} UI previews")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
