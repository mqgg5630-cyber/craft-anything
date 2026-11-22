# 噜噜噜妹 · 和你一起奔夕阳 · 10张复刻（无UI / 有UI）

来源：https://xhslink.cn/o/5thkO8Kd6jg ，笔记 `6ad212fc000000001802d6be`，作者 等噜噜，标题「和你一起奔夕阳 噜噜噜妹壁纸」。

## 1. 原片下载（GitHub Actions，不在当前环境直接下载）
- 工作流 `.github/workflows/lululu-ui-download.yml` → `tools/wallpaper-job/download_lululu_ui.py`，复用 `download.py` 的 fetch 校验（12 MiB上限、完整解码、最小尺寸）。
- 运行：https://github.com/mqgg5630-cyber/craft-anything/actions/runs/45013798803 ，成功，机器人提交 `b3283db` 写回本分支。
- runner 上短链被重定向到登录页，所以图片列表用的是之前对同一笔记读到的5个公开轮播token；每个token尝试签名WebP以外的无签名CDN变体，取像素最大、字节最大的有效文件。
- 结果：`原片/01–05.png`，均为 1080×1920 PNG，约2.2–2.4 MB（比网页WebP约75–100 KB清晰得多）。MD5/SHA-256见 `source-manifest.json`。属公开CDN文件，未确认是作者无损母版。
- 本地重新校验MD5并解码，5张逐张看过后才生成。

## 2. 复刻结果
- `复刻结果/无UI/`：10张独立AI参考复刻，模型原生 768×1376，未放大。每张只附1张对应原片作参考（映射见 `output-manifest.json`），保留毛绒质感、黄金时刻逆光、桃橙色调，变化姿态、互动和场景。
- `复刻结果/有UI/`：同名10张，由 `render_ui.py` 叠加通用锁屏模拟（状态栏、日期、18:30时钟、手电筒/相机按钮、Home条）。仅为效果预览，不是真机截图或可安装主题。渲染前后校验无UI原图未被改动。
- `00-总览-原片.jpg / 00-总览-无UI.jpg / 00-总览-有UI.jpg` 仅为预览，不替代单张。

## 3. 已知缺陷（看图检查发现）
- **03-草地看云、06-晚霞飞鸟**：妹妹的脸被画成人类娃娃脸（带头发），原片是黄色毛绒猪脸。本轮生图次数已用满（10次），需下一轮以原片04为身份参考返工这2张（无UI+有UI同步替换）。

## 4. Google Drive 交付
根文件夹「噜噜噜妹·和你一起奔夕阳·复刻10张(有无UI)-20261122」：
- `01-原片/` 5张
- `02-复刻结果/无UI/` 10张
- `02-复刻结果/有UI/` 10张

重新列目录核对：25/25，名称与MD5全部匹配（`cloud-verification.json`）。

## 验收
`.venv/bin/python deliveries/lululu-sunset-ui-10/test_delivery.py`
