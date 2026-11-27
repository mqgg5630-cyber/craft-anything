# 秋天和秋千 · 十张复刻全流程

**1张原片 + 10张独立PNG成品 + 4张总览/对照图 + 制作与校验记录**。全部文件夹交付，不生成或上传ZIP。

## 网盘入口
总文件夹：https://drive.google.com/drive/folders/1RFR9xjGPoFI2DJ0t419MJq18YBOxin2W

- `01-下载原片`：1张Actions验证的原片，原字节未修改。https://drive.google.com/drive/folders/1nC361673YorneIqZCG0qfmvJhCvj5IJF
- `02-十张复刻壁纸`：10张可直接保存的最终PNG，全部 **852 × 1848像素**。https://drive.google.com/drive/folders/1t4SF5mFqrnpw07foNRitnbOXNV5uFKQx
- `03-制作底图`：10张实际AI生成底图（704×1520），供制作备份，非最终尺寸壁纸。https://drive.google.com/drive/folders/13pJvOh7MPGhf9E0pFA4HQCij-m59ugrN
- `04-全流程与总览`：原片总览、十张总览、十组原片成品对照、流程记录。https://drive.google.com/drive/folders/1jKlHGWd7uJctIV7Bqj8v3d3b6KC5-No_
- 总目录 `00-全流程总预览.jpg`：一图查看参考、制作步骤和全部10张结果。

## 1. 下载原片
分享：https://xhslink.cn/o/C5WkFiFa1r

笔记：“秋天和秋千很配哦～”，ID `6abdb5a9000000001802f193`。只有1张公开参考图，**852×1848像素**。下载仅在GitHub Actions执行，本地未请求小红书/CDN；逐张解码和哈希验证后才返回同一分支。

运行：https://github.com/mqgg5630-cyber/craft-anything/actions/runs/45967565012

原片返回提交：`546656b`。SHA256：`eb4d525baab9308a18681b1c8bda6fb05b9ea8c2cb3890a4b5b6bb0d391c5d8b`。

下载文件保留原来的平台标识；属于公开笔记可获得的最高候选版本，不保证是作者母版。原片版权归原权利人，不附带商业授权。

## 2. 风格分析
核心：温暖绘本/动画质感、橙金夕阳、大树下的双绳木秋千、白色卷毛小羊和黄围巾。层次包括前景花草/虚化叶片、中景秋千与金色草地、远山/河湖和开阔晚霞。

## 3. 十张分别重绘
每张只参考这篇的同一张原片，不使用以前其他笔记的画面。分别变化树的位置和树种、小羊神情与姿态、夕阳位置、河湖牧场背景与落叶。不是同图滤镜换色或原图水印修补。

|编号|场景|主要变化|
|---|---|---|
|01|金风轻荡|左侧橡树、牧场、交叠小脚|
|02|银杏溪光|右侧银杏、花海、蜿蜒溪流|
|03|枫林晚照|枫树、梯田远景、侧坐小羊|
|04|湖畔小憩|湖面与远山、闭眼微笑|
|05|落叶来信|右侧大树、飘叶、远山小路|
|06|牧野余晖|栅栏牧场、倾斜摆动的秋千|
|07|秋河漫漫|山谷与弯曲河流|
|08|白桦听风|右侧白桦、云团、小花草地|
|09|麦野暮色|落日、远山、稻草卷|
|10|云湖晚安|右侧树干、湖泊、大朵晚云|

AI风格衍生创作，不冒充原作者作品，不是逐像素复制。成品不添加文字、手机UI、署名或平台标识；场景名称仅用于文件名/总览标签，不画在壁纸内。

## 4. 后期尺寸适配
十张底图原生704×1520，使用单一比例Lanczos放大至足够覆盖原图画布，再极少量居中裁切到 **852×1848**。不分别拉伸横纵轴，不声称原生生成就是最终像素。原片完全不修改。

## 5. 校验与总览
检查原片字节不变、10份成品互异、文件能解码、所有成品尺寸相同、字节数与SHA256/MD5正确。人工查看全部10张及总预览。完整清单与适配参数见`output-manifest.json`，流程见`full-process.json`，上传后记录见`storage-verification.json`。

四张展示图：全流程总预览、原片总览、十张成品总览、原片成品对照。对照图中的十个左图均为同一张原片，不表示有10张原片。

## 6. 以后默认规则
用户本次明确要求用本篇原片尺寸作为以后尺寸，因此最新默认由1080×2343更新为 **852×1848**，除非以后另行指定。历史交付不反向缩放。下载原片保留原生尺寸和字节，成品按最新默认等比适配；原片与结果分文件夹，不打ZIP，附全流程与总览。

规则保存于`tools/wallpaper-job/delivery-defaults.json`；本目录`delivery-defaults.json`为本批生效规则的固定快照，未来更改不覆盖它。

## 离线复现（不重新生成AI图片、不打ZIP）
将网盘“03-制作底图”中的01.png至10.png下载到本地`deliveries/autumn-swing-10/03-制作底图/`，然后在仓库根目录运行：

```sh
python -m pip install Pillow==11.3.0
python tools/wallpaper-job/package_autumn_swing.py --raw deliveries/autumn-swing-10/03-制作底图
python -m unittest discover -s tools/wallpaper-job -p test_autumn_swing_package.py -v
```

排版总览使用仓库已附SIL OFL许可的Noto Sans CJK SC；最终壁纸无字体叠加。实际AI底图保存在网盘而非大型Git对象中，哈希和文件ID留在版本化校验表；生成模型本身不保证可重复，所以保留真实底图。
