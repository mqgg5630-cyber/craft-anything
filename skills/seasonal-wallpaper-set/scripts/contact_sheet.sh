#!/usr/bin/env bash
# 把一整套壁纸拼成一张总览图，一次性检查比例、角色和季节元素。
#
# 用法：
#   ./contact_sheet.sh <目录> [每行列数] [缩略图宽度]
# 例：
#   ./contact_sheet.sh ./winter 5 300
#
# 依赖：ImageMagick（montage / identify）。没有的话：apt-get install -y imagemagick
set -euo pipefail

dir="${1:?用法: contact_sheet.sh <目录> [每行列数] [缩略图宽度]}"
cols="${2:-5}"
thumb="${3:-300}"

cd "$dir"

# 收集图片（含 00- 前缀的参考图/旧拼图之外的成品），按文件名排序
imgs=()
while IFS= read -r f; do
  [ "$f" = "00-contact-sheet.jpg" ] && continue
  imgs+=("$f")
done < <(ls -1 *.jpg *.jpeg *.png 2>/dev/null | sort)

if [ ${#imgs[@]} -eq 0 ]; then
  echo "目录里没有图片: $dir" >&2
  exit 1
fi


# 9:16 归一：比例不对的图居中裁切（不拉伸，人物居中不会走样）
# 传入 --fix 才会真正改写文件；默认只报告。
fix="${FIX_RATIO:-0}"
for f in "${imgs[@]}"; do
  read -r w h < <(identify -format '%w %h\n' "$f")
  # 目标宽 = h*9/16；偏差超过 4% 才处理
  want=$(python3 -c "print(round($h*9/16))")
  diff=$(python3 -c "print(round(abs($w-$want)/$want*100))")
  if [ "$diff" -gt 4 ]; then
    if [ "$fix" = "1" ]; then
      convert "$f" -gravity center -crop "${want}x${h}+0+0" +repage -quality 93 "$f.tmp.jpg"
      mv "$f.tmp.jpg" "$f"
      echo "已裁切 $f -> ${want}x${h}（原 ${w}x${h}）"
    else
      echo "比例偏离 ${diff}%: $f（${w}x${h}，9:16 应为 ${want}x${h}）—— 设 FIX_RATIO=1 再跑可自动裁切"
    fi
  fi
done

montage -tile "${cols}x" -geometry "${thumb}x+10+10" \
  -background '#141416' "${imgs[@]}" 00-contact-sheet.jpg

echo "已生成: $dir/00-contact-sheet.jpg（${#imgs[@]} 张）"
identify -format '%f %wx%h\n' "${imgs[@]}"
