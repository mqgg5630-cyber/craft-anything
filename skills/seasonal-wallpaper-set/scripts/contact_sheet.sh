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

montage -tile "${cols}x" -geometry "${thumb}x+10+10" \
  -background '#141416' "${imgs[@]}" 00-contact-sheet.jpg

echo "已生成: $dir/00-contact-sheet.jpg（${#imgs[@]} 张）"
identify -format '%f %wx%h\n' "${imgs[@]}"
