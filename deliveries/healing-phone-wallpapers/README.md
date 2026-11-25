# 花墙治愈｜手机壁纸十张

- 参考：[手机壁纸](https://xhslink.cn/o/3vhEnAitnnf)，公开轮播 9 张，由 [GitHub Actions](https://github.com/mqgg5630-cyber/craft-anything/actions/runs/45524599707) 下载并验证后回写当前分支；这些是公开页面图，不宣称为作者无损母版。
- 参考图 9 张均为 1080 × 2347；十张 AI 再创作壁纸与各自静态 UI 版均经比例裁切和缩放至相同像素大小，非原生生成尺寸。构图、花色、祝福语各有变化；部分画面边缘的装饰灯被裁切。
- `generated/` 为生成底图，`images/` 是无设备 UI 的成品（包含后期祝福文字），`ui/` 是后期叠加的静态锁屏效果，非真实手机截图。部分模拟时钟与上方花枝重叠，实际锁屏适配取决于设备。
- 祝福文字使用 [Ma Shan Zheng](https://github.com/google/fonts/tree/main/ofl/mashanzheng) 字体（SIL Open Font License，许可文本见 `assets/fonts/mashanzheng/OFL.txt`），由 `render.py` 叠加。图片检查与逐张哈希见 `output-manifest.json`。
- [Google Drive 总文件夹](https://drive.google.com/drive/folders/1SfPSBh1r4vyhXqTNaxeh9bdG5Iy0ZUj2) 中参考、无 UI、模拟 UI 分开放置；每组各有 ZIP 及总览。本地检查了 ZIP 条目数、CRC、图片解码、尺寸，上传后重列并比对云端 MD5。
