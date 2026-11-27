# 新岁花笺 · 十张全新祝福壁纸

本次交付**全部为文件夹内的独立文件，不创建或上传 ZIP**。

## 网盘文件夹
总目录：https://drive.google.com/drive/folders/1b_Sb3exIW1-hkK4zPFKuWtZ5ETgu_Kwr

- `01-下载原片`：4张原片，保留下载字节。https://drive.google.com/drive/folders/1_rwVbJ8OJQX-E6OnlbpFvVcFbqQfpVjW
- `02-十张新文案壁纸`：10张可直接使用的独立PNG，**1080 × 2343像素**，与本篇四张原图相同。https://drive.google.com/drive/folders/1F9W1OLdDbnT1kVR5jrPspUgImIA2rFBJ
- `03-制作底图备份`：10张实际AI底图，仅供制作留档，不是最终壁纸。大型底图按仓库外部存储惯例保存在网盘。https://drive.google.com/drive/folders/1100ZonIJEmsp_Ok_iYtB4IuXwhLI4cdD
- `00-十张总预览.jpg`：全部成品总览。
- `04-全流程与总览`：全流程总预览、原片总览、十组原片/成品对照、流程说明与文案尺寸表。https://drive.google.com/drive/folders/1SFYy-T_k4YCSOLTajWyeI3oWyEsNkzcn

## 最新补充与以后默认规则

本次沿用这篇笔记上一轮已完成的10张成品，补齐全流程与总览；没有重新生成另一批10张。4张原片与10张成品均保持原有字节、像素及分文件夹结构。

用户本次确认：**以后成品默认1080 × 2343像素，除非另行指定；原片保持下载尺寸与字节，不改动；原片与结果分开，全部文件夹交付，不打ZIP，附总览和全流程资料。** 该默认规则已保存为 `tools/wallpaper-job/delivery-defaults.json`。

`04-全流程与总览/full-process.json`记录本次补充文件及哈希；`process-storage-verification.json`记录补充资料云端校验。原有`storage-verification.json`继续保留上一轮14张图片与制作底图的上传校验，不重写历史记录。

## 风格与文案
保留仿古绢纸、植物花枝、浅米色纸条、错落竖排墨字的风格语汇，但重新生成十份花材绘画与拼贴，所有主文案均重新选择，不复制原图书法字形、署名和作者印章。

|编号|右列|左列|
|---|---|---|
|01|春来有信|花开有期|
|02|岁序更新|心有暖阳|
|03|长安常乐|好梦皆圆|
|04|心纳吉庆|日有小欢|
|05|福随春至|喜伴风来|
|06|灯火可亲|所遇皆暖|
|07|山河锦绣|前路生花|
|08|且听春语|静待花开|
|09|朝朝舒意|暮暮安然|
|10|良辰如约|新岁长宁|

原图文字经人工识读，原句如“欢喜由心、自在如风、爱财爱己、风生水起、安康如意、顺遂福来”等均未用于成品；第4张原句的繁体/异体识读项也列入非复用检查。二十句新短语互不重复，为常见祝福表达的重新搭配，不声称独占短语版权。

## 下载与制作记录
- 分享：https://xhslink.cn/o/3kQq76Fee2O
- 笔记ID：`6af66414000000002203bdb3`，标题“祝福文字 新年壁纸 |”。
- 原片下载只在 GitHub Actions 执行，本地无小红书/CDN下载请求。
- 下载运行：https://github.com/mqgg5630-cyber/craft-anything/actions/runs/45526335316
- 已解码验证四张原图，返回同一分支，提交 `9e864b6`。
- 十张底图原生704×1520，后期单一比例Lanczos放大并轻微居中裁切到1080×2343，**无横纵轴分别拉伸，不声称原生生成即达到最终像素**。
- 第8张额外绘制纹理纸条；第9张底图底边出现非预期平台样式标记，裁切底边2.5%后再等比适配。下载原片均未编辑。
- 字体：Ma Shan Zheng Regular（SIL OFL），两列四字确定性排版，逐字轻微偏移及旋转；总览用Noto Sans CJK SC（SIL OFL）。共享字体及许可证位于仓库 `deliveries/simple-fresh-first-10/03-复现资源/`。上方装饰为新绘抽象花形圆纹，非照搬作者印章。
- 不加手机UI；本批是AI风格衍生创作，不是原作者作品或逐像素复制，原图版权归原权利人。

## 离线复现与测试（不生成压缩包）
先将网盘“03-制作底图备份”的10张PNG保存到本地 `deliveries/new-year-blessings-10/03-制作资源/底图/`，文件名为01.png至10.png。保留实际底图是因为AI生成本身不保证可重复。

```sh
python -m pip install Pillow==11.3.0
python tools/wallpaper-job/package_new_year_blessings.py
python -m unittest discover -s tools/wallpaper-job -p test_new_year_blessings_package.py -v
```

`output-manifest.json`记录全部原片、底图、成品尺寸、字节数、SHA256、MD5和排版位置。`storage-verification.json`为上传后核验状态；云端通过文件大小和MD5与本地核对，不声称重新下载核验。
