#!/usr/bin/env bash
# 安装 PPT Master（MIT，hugohe3/ppt-master）作为本模块的课件导出通道。
# 为什么需要它：PowerPoint 的"好看"来自版式，不是文本框加粗。
# 它把 1280×720 的 SVG 页转成**原生** DrawingML：文字仍可编辑、图片是原生图片、曲线/表格是原生形状。
#
# 用法：bash scripts/install_ppt_master.sh [安装目录，默认 ~/ppt-master]
set -euo pipefail
DEST="${1:-$HOME/ppt-master}"

if [ ! -d "$DEST/skills/ppt-master" ]; then
  echo "→ clone PPT Master 到 $DEST"
  git clone --depth 1 https://github.com/hugohe3/ppt-master.git "$DEST"
fi

echo "→ 安装 python 依赖（python-pptx / skia-pathops / uharfbuzz / Pillow / XlsxWriter）"
python3 -m pip install --break-system-packages -q \
  python-pptx Pillow numpy XlsxWriter skia-pathops uharfbuzz

echo "→ 完整性校验（PPT Master 的 attribution guard，返回非 0 就说明技能包不完整）"
python3 "$DEST/skills/ppt-master/scripts/attribution_guard.py"
echo "✓ 安装完成。导出课件："
echo "  python3 scripts/build_deck.py --md <课件.md> --plan <plan.json> \\"
echo "      --out <输出目录> --images assets/deck-images --skill $DEST/skills/ppt-master"
