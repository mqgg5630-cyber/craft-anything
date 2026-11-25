# 简单清新 · 十张四字祝福壁纸

只参考新笔记的**第一张图片**。原片及全部十张成品均为 **884 × 1845 像素**，竖屏 PNG 成品无手机 UI。

## 文件
- `00-十张总预览.jpg`：十张成品总览。
- `01-下载原片/01.jpg`：通过 GitHub Actions 下载、解码校验并返回同一分支的第一张原片，保持原字节。
- `02-同尺寸四字祝福/`：十张独立 PNG 壁纸。
- `03-复现资源/`：十张 AI 底图、排版脚本、离线测试、字体与许可证。
- `source-manifest.json`、`output-manifest.json`：来源、尺寸、哈希、排版及等比适配记录。
- `storage-verification.json`（包外后续生成）：网盘上传后校验记录。压缩包是上传前快照，不含其自身校验报告或后续云端状态。

## 本次设计
浅灰米白留白、水彩果枝、下方果篮与茶盏、偏右竖排四字祝福。苹果、柿子、橘子、石榴、桃、梨、葡萄、枇杷等主题。十句依次为：平安喜乐、岁岁平安、喜乐安康、事事顺遂、大吉大利、福满人间、平安顺遂、万事胜意、好事成双、顺遂无忧。

## 来源与边界
- 分享链接：https://xhslink.cn/o/24CQFIRp9Er
- 笔记：简单清新壁纸；ID `69af7ccc000000001a02eba0`。
- Actions：https://github.com/mqgg5630-cyber/craft-anything/actions/runs/45524307533
- 原片返回提交：`5927d55`；只下载并参考索引 1，虽观察到共 9 张，但其他 8 张未下载、未用于生成，也未使用以前其他笔记的图片。
- 原图 SHA-256：`312d1ffbcbf63aa7690706f0c6c9af2f3a521ef619a6fcdff350b6460e7f3ea7`。
- 十张为 AI 风格衍生创作，不声称是原作者作品或逐像素复印。未仿制作者水印、印章。下载原片仍包含原有署名，版权归原权利人；本交付不授予原图商业使用许可。
- AI 底图原生为 704 × 1488；后期以**单一比例 Lanczos 放大并轻微居中裁切**至 884 × 1845，不横纵向分别拉伸，不声称原生生成即为最终像素。桃、梨底图额外离线清理了杂色背景。
- 中文不是 AI 画字，而是使用 SIL OFL 许可的 Ma Shan Zheng Regular（马善政毛笔字）确定性排版；总览用 Noto Sans CJK SC，许可证均附。

## 离线复现
在仓库根目录运行：

```sh
python -m pip install -r deliveries/simple-fresh-first-10/03-复现资源/requirements.txt
python tools/wallpaper-job/package_simple_fresh.py --root deliveries/simple-fresh-first-10 --raw deliveries/simple-fresh-first-10/03-复现资源/底图
python -m unittest discover -s tools/wallpaper-job -p 'test_simple_fresh_package.py' -v
```

在完整 ZIP 解压后的 `简单清新壁纸` 目录中运行：

```sh
python -m pip install -r 03-复现资源/requirements.txt
python 03-复现资源/package_simple_fresh.py --root . --raw 03-复现资源/底图
FRESH_DELIVERY_ROOT=. python -m unittest discover -s 03-复现资源 -p 'test_simple_fresh_package.py' -v
```

脚本为纯离线操作，不重新请求图片源。`--raw` 必须是这十张已保存的 AI 底图；图片生成本身不保证可重复，因此完整保留实际底图。
