# 噜噜噜妹 · 和你一起奔夕阳 — 壁纸交付

来源笔记（小红书分享链接）：https://xhslink.cn/o/5thkO8Kd6jg
主题：和你一起奔夕阳 噜噜噜妹壁纸

## 流水线（按仓库既定约定）

1. **下载原片**：`tools/wallpaper-job/download_lululu.py` 仅在 GitHub Actions runner 上运行
   （不在本机直接下载）。它解析分享链接、读取笔记公开 `imageList`，逐张经 `download.py`
   的有界 `fetch` 校验器（解码、尺寸、大小上限）后原样落盘，并写入 `下载记录.json`。
   登录墙会自动回退到 `xiaohongshu.com` 的 explore/discovery 公开页（带 xsec 分享令牌）。
   `download-debug.json` 始终记录 runner 实际观测，便于失败归因。
2. **校验后写回同一分支**：`.github/workflows/lululu-download.yml` 在会话分支上触发，
   下载完成后把 `deliveries/lululu-sunset/` 提交回同一分支。
3. **复刻 10 张**：参考下载原片，用图像生成工具产出 10 张同风格壁纸，落入 `02-复刻无手机UI/`。
4. **有无 UI 版**：`tools/wallpaper-job/package_lululu.py` 为每张干净壁纸渲染确定性锁屏示意
   （非设备截图），落入 `03-复刻有手机UI/`；并生成 `总预览图.jpg` 及各分卷总览。
5. **推送谷歌硬盘**：原片（`01-下载原片`）与结果（`02-复刻无手机UI` + `03-复刻有手机UI`）
   分两个文件夹上传 Google Drive，并写入验收回执。

## 目录

- `01-下载原片/` 公开 CDN 原片 + `下载记录.json`（尺寸/字节/哈希/来源 URL）
- `02-复刻无手机UI/` 10 张干净复刻（无锁屏 UI）
- `03-复刻有手机UI/` 对应的 10 张锁屏示意
- `04-说明与验收/` 验收记录 + 分卷总览
- `总预览图.jpg` 原片 + 无 UI + 有 UI 总览
- `download-debug.json` runner 诊断（含失败归因）

## 说明

公开 CDN 文件不能保证为作者母版；复刻为同风格新生成，非作者原图的精确复制。
原生生成图未放大伪称高清母版。
