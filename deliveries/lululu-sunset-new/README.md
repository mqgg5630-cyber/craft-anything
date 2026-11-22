# 和你一起奔夕阳 · 参考与复刻

来源：[小红书笔记](https://xhslink.cn/o/5thkO8Kd6jg)，作者等噜噜，笔记 ID 6ad212fc000000001802d6be。

- `source/`：5 张 1080×1920 WebP 公开 CDN 图，保留下载字节；未证实是作者无损母版。按要求通过 [GitHub Actions](https://github.com/mqgg5630-cyber/craft-anything/actions/runs/45015091113) 下载、解码校验后写回当前分支，`source-manifest.json` 记录哈希和来源。
- `images/`：参照五张原片分别生成两张，共 10 张独立 AI 复刻；是再创作而非作者原片。没有插值放大，原生尺寸记在 `output-manifest.json`：其中 02 为 848×1264、06 为 768×1365，其余 768×1376。
- `ui/`：每张无 UI 图片对应一张模拟锁屏叠加图；日期、时间和按钮为静态示意，不是实机截图或可安装主题。
- `contact.jpg`：十张无 UI 成品总览。

本地验证五张来源的 SHA-256、图片解码、十张独立图的唯一 MD5、十张 UI 解码。已查看原片、总览与 UI 示例。云端三个文件夹重新列出并逐项对比 MD5，分别为 5、10、10 张，见 `cloud-verification.json`。

[Google Drive 文件夹](https://drive.google.com/drive/folders/1VvrfUhrWURjPBxRx9bgfip8SzZXCuTe6)。
