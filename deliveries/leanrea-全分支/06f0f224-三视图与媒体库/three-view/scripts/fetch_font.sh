#!/usr/bin/env bash
# 取一个中文字体（霞鹜文楷 Lite，SIL OFL 1.1）。
#
# 为什么不用 raw.githubusercontent.com：多数沙箱只放行 github.com / codeload.github.com /
# api.github.com，raw 域名会直接 TLS 重置（curl: (35) SSL_ERROR_SYSCALL）。
# 所以这里走 codeload 的 tar.gz。
set -euo pipefail

DEST="${1:-$HOME/.fonts/LXGWWenKaiLite-Regular.ttf}"
URL="https://codeload.github.com/lxgw/LxgwWenKai-Lite/tar.gz/refs/heads/main"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$(dirname "$DEST")"
echo "下载 $URL"
curl -fL --retry 2 -o "$TMP/font.tar.gz" "$URL"

tar -xzf "$TMP/font.tar.gz" -C "$TMP" \
  --strip-components=3 "LxgwWenKai-Lite-main/fonts/TTF/LXGWWenKaiLite-Regular.ttf"
mv "$TMP/LXGWWenKaiLite-Regular.ttf" "$DEST"

echo "完成：$DEST"
echo "用法：SHEET_FONT=$DEST python3 scripts/contact_sheet.py preview ..."
