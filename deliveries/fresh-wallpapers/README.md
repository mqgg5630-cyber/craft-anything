# 简单清新 × 锦鲤｜统一尺寸十张

- 公开参考：[简单清新壁纸](https://xhslink.cn/o/24CQFIRp9Er)，作者「齐齐」；第二组参考为先前的[锦鲤入梦](https://xhslink.cn/o/3qz2uQpojFp)，作者 Nihility。九张公开轮播图片通过 [GitHub Actions](https://github.com/mqgg5630-cyber/craft-anything/actions/runs/45523102531) 下载、解码、计算哈希并目视确认；不宣称是作者无损母版。
- 9 张参考图的宽均为 884 px，高为 1837–1920 px，各图大小并不完全相同。为满足统一规格，选择第 01 张公开图的 **884 × 1851 px** 为全部成品和模拟 UI 的尺寸依据。PNG 像素尺寸经过逐张检查。
- 制作：先生成各自不同尺寸的 AI 图，再等比裁切及重采样至目标尺寸，不拉伸。第 05 张为保留整排动物，在等比缩放后上下扩展背景留白；扩展处可能有轻微色差。文字以字体后期叠加，详情见 render.py。AI 生成图经重采样，并非原生 884×1851 或原片。
- `generated/` 是生成中间图；`images/` 是 10 张最终无设备 UI 壁纸（仍包含设计上的祝福文字）；`ui/` 是对应 10 张添加静态时钟和图标的模拟锁屏，不是真实设备截图。图像主题结合了两篇笔记，非对原片的逐像素复制，模型可能带来细节差异。
- Drive：[总文件夹](https://drive.google.com/drive/folders/1CmnoKdN8CXz32Xzi_ZBBOsvDkEOSei5s)，公开原片、无 UI 和模拟 UI 分开，各有 ZIP 和总览。各 ZIP 条目数量、CRC，以及 Drive 目录重列与 MD5 校验通过。
