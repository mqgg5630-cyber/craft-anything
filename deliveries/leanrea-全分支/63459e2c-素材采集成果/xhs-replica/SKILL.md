# xhs-replica

把一份小红书图文素材，复刻成 N 张「同角色、同设计语言、换内容」的成品图。
角色（一二／布布）一个像素都不能改，改的只有场景和内容。

## 硬性指标

| 项 | 值 |
|---|---|
| 输出尺寸 | **1080 × 2280** |
| 比例 | **9:19**（0.4737） |
| 格式 | PNG（成品）／JPG（下载的原片） |
| 模型原生输出 | 704 × 1504 —— **必须**裁到 9:19 再重采样，不能直接拉伸 |

每一轮出图后先 `python3 -c "from PIL import Image; print(Image.open(f).size)"` 抽查，
不是 `1080, 2280` 就不要进云盘。

## 身体比例（最容易翻车的地方）

模型默认会把熊画成**拟人化**——拉长躯干、加腰身、拉长四肢。
这跟原片的大头小身 chibi 比例完全是两回事。
光写「identical body proportions」压不住，必须在提示词里把比例描述死：

```
CRITICAL BODY-PROPORTION LOCK: copy the chibi proportions of the
reference images exactly — a large round head sitting directly on a
small compact low-slung rounded body, short stubby arms and legs,
essentially no neck. Do NOT elongate the torso, do NOT lengthen or
slim the limbs, do NOT add a waist or shoulders, do NOT make them
human-like or anthropomorphic. The head must stay clearly larger than
the torso. Both bears share these same proportions.
```

**真正起作用的是「不要什么」那几条**——正面描述模型会自己发挥，
负面约束才能压住拟人化倾向。这段要放在提示词靠前的位置，
别埋在场景描述后面。

⚠️ 代理人看不到图，无法自查比例是否走形。
**每轮出图后必须让用户抽查**，走形的编号记下来，下轮针对性加强。

## 角色锁定（比身体比例更致命）

**第 14 轮整轮翻车**：提示词写成 `two identical plush teddy bears, one cream-oatmeal, one cocoa-brown`，
且一张参考图都没挂。结果 10 张全是两只普通泰迪熊——**一二被画成了另一只布布**。

两个错叠在一起才崩，单点不会翻车，但两个都犯必翻：

1. **写错角色卡**：写「two bears」，模型默认两只一样。一二不是熊。
2. **没挂参考图**：纯文生图时模型没有任何角色来源，只能自由发挥。

### 角色卡（每个提示词第一段，一字不差照抄）

- **一二**：白色小熊猫——纯白圆身、实心黑圆耳、黑色熊猫眼罩、小眼睛、
  **黑蝴蝶领结**、白色短手、黑色小脚。
- **布布**：奶茶棕小熊——略大一圈、圆耳、奶白口鼻、黑点眼、小鼻子、
  短粗四肢；**原作不戴围巾，别加**。

提示词里用这段英文（`healing-comic/SKILL.md` 同款，已验证）：

```
Use the two characters and the exact art style from the reference images.
CHARACTER 1 (white panda cub): small chubby pure-white round body, two solid
black round ears, two black oval panda eye patches, small simple eyes, a small
black bow tie, short white stubby arms, little black feet.
CHARACTER 2 (brown bear cub): slightly bigger chubby milk-tea-brown round
body, small round ears, pale cream muzzle, small black dot eyes, tiny nose,
short stubby limbs, no scarf.
```

### 三条铁律

- **每次 generate_image 必须挂 2–3 张原图作参考**（`images: [refs_original/r1.jpg, r3.jpg]`）。
  纯文生图不准出成品。
- **工作区重置会把 `refs_original/` 清空**，开工前先确认参考图还在。
  参考图永久存在云盘 `01_小红书素材 → 一二和布布_小红书原图（沿用已有参考图）`，
  用 `download_file` 取回**只返回路径、不返回 base64**，不占上下文；
  但它会写进 `leanrea/google_drive/`，**取完立刻 mv 出仓库并删掉该目录**。
- 提示词里**禁止**出现 `two identical bears` / `two teddy bears` / `same bear`——
  一说 identical，两只就会长成一样。
- 出图后**先让用户看角色对不对**，再谈配色构图。角色不对，后面全都白做。

⚠️ 代理人看不到图，自查不了角色有没有跑偏。
**每轮出图后必须让用户确认角色**，这比确认身体比例更优先。

## 尺寸比例（第二容易翻车的地方）

成品必须 1080×2280，但**原始稿的比例是模型自己定的**，
不写死就会乱：第 16 轮 10 张里混进了 `1376×768`（横的）和 `896×1200`（偏宽）。
横图硬裁成 9:19 = 只切中间一条，跟其他张的景别完全对不上，
用户一眼就看出「有的尺寸比例不一样」。

**提示词里必须写这句**（实测有效）：

```
COMPOSITION: vertical 9:19 portrait, TALL and NARROW.
```

写上之后第 17 轮 10 张原始稿**全是 704×1504（比值 0.468）**，
跟目标 0.4737 几乎一致，裁切量一致 → 十张景别对齐。

出图后先量一遍再进后期：

```sh
python3 -c "
from PIL import Image; import glob,os
for f in sorted(glob.glob('raw/*.png')):
    w,h=Image.open(f).size
    print(os.path.basename(f), f'{w}x{h}', round(w/h,3), '❌横图' if w>h else ('⚠️偏宽' if w/h>0.75 else '✅'))"
```

比值 > 0.75 或横图 → 重出，别硬裁。

## 让模型写字（中文写不出来，英文单词能写）

用户要求「对话直接通过图片生成」。试了，10 张全失败：
提示词里写了 `TEXT TO RENDER — 必须烤进画面`，并指定上/下留白带位置、简体中文字形、
「no invented or broken glyphs」。**模型一个字都没写。**

验证方法（看不到图也能判）：量留白带的**行间差分密度**，跟「同样留白但没要求写字」的一轮比。

| | 上留白带密度均值 |
|---|---|
| 第15轮（没要求写字） | 2.56 |
| 第17轮（要求烤字） | 2.47 |

几乎相同 → 没写。下留白带那点差异是场景本身繁简不同造成的，不算证据。

**结论：中文字仍然只能后期合成**（`dialogue.py`）。
要让字看起来是画面的一部分，就把出图的留白带留够，气泡画进去。

---

### 英文单词：模型能自己画（第21轮实测 10/10 ✅）

第21轮用户要求「字必须是图片生成的，不是后期加的」。试了，**英文单词全部画出来了**：

| 检查项 | 结果 |
|---|---|
| MOON / CLOUDS / GLOW / OCEAN / STARS / SNOW / WISH / AURORA / SWING / DAWN | OCR 全部读出，置信度 0.88–0.99 |
| 拼写 | 10/10 正确 |
| 位置 | 横向居中（≈50%），纵向 81%–90%，整轮基本对齐 |

**关键差异：中文对话画不出来，英文单词能画。**
中文字形笔画多，模型会直接放弃或画成乱码；4–6 个大写英文短词容错高。

照抄就能用的写法：
```
TEXT TO RENDER (this is essential): the English word DAWN appears in the lower part
of the image, below the characters, written in large simple bold capital letters,
spelled exactly D-A-W-N, clean even letterforms, cream-white colour, like a printed
poster title. The letters must be perfectly legible and correctly spelled.
No other text anywhere.
```
要点：**逐字母拼写**（D-A-W-N）、说 `large simple bold capitals`、
说 `no other text anywhere`、场景要留空（字周围有干净区域）。

**怎么验证（不用眼睛看）** —— 装 OCR 客观读字：
```
pip install --break-system-packages rapidocr-onnxruntime opencv-python-headless
```
少了 `opencv-python-headless` 会报 `libGL.so.1`，cv2 起不来，别漏。
```python
from rapidocr_onnxruntime import RapidOCR
r, _ = RapidOCR()(np.array(Image.open(f).convert('RGB')))
print([(t, round(c, 2)) for _, t, c in (r or [])])
```
先拿一张写着 HELLO 的白纸自检，读得出来再去验图。

**结论（更新版）**
- 英文单词 → 让模型自己画，比后期叠更自然（字跟画面吃同一个光），也不需要底板
- 中文对话 → 仍然只能后期合成（`dialogue.py`）
- 要让模型写字时，后期**只做裁切/放大/USM/分级**，spec 里**不给 `word` 键**，`finish.py` 就不会再叠一层


## 字不要有底（第18轮定下来的规矩）

对话文字的三种做法，按好看程度排：

| 做法 | 实测 | 用户评价 |
|---|---|---|
| **无底排版**（默认） | 画面改动像素 1.1%–2.4%，只有字本身 | ✅ 要的就是这个 |
| 毛玻璃（底取自画面） | 牌子与相邻画面 Δ 60~97 | ❌「还是一块板」 |
| 外来白纸气泡 | Δ 60~120 | ❌「字的背景和图片的背景不一样」 |

**结论：字直接坐在画面上，一个像素的底都不要加。**
出图时把留白带留够（上 16% / 下 22%，提示词里写明"plain calm area"），
后期只画字，靠一层半透明柔光描边（`stroke_width` + 低 alpha）保可读性。

两个坑：
1. **字色别用固定阈值切明暗**——底色正好卡在临界点时字色会选错。
   改成「墨色和奶油白谁离底色更远就选谁」，永远选对比更大的那个。
2. **描边强度要跟着对比度走**：对比 < 80 就把 alpha 提到 200，别硬压或动画面底色。

验证：跟「同一张图但不加字」逐像素比，改动像素应 < 4%；
字芯（改动最大的前 15% 像素）与底色的亮度差应 > 90。

## 原始稿必须进云盘

工作区会重置，`/home/user` 下除 `leanrea` 外全部清空。
第17轮的原始稿（没叠字的底图）没存云盘，重置后**整轮 10 张要重生**。

每轮出完片，**把原始稿一起传进 `_原始稿（未加字）/`**——
下次要改排版、改字体、改文案，直接拿原始稿重跑，不用重生图。

## 流程

```
1 取素材   抓笔记页 → 提 CDN 图链 → 下载 → webp 转 png
2 量设计   对原片跑 OCR + 分带取色 + 边缘密度，得到设计语言
3 生成     必挂原图作参考（2–3 张）+ 角色卡照抄 + 身体比例硬锁；不挂参考图不准出图
4 后期     finish.py：裁切 → 放大 → USM → 胶片分级 → 叠文字元素
5 出总图   每轮必出一张 总图.jpg（全部成品的拼版），随成品一起上传
6 归档     云盘「每轮一个子文件夹」+ 档案 Doc（含来源链接与文案）
7 文案     标题三选一 + 正文 + 短版 + 话题标签
8 拆文案   每轮的文案**单独一份文档，放进该轮自己的文件夹**，不是只堆在一个全集里
```

**第 8 步是硬要求**（第19轮起）：文案全集 Doc 只是总索引，
真正发的时候要看的是「第 X 轮 · 小红书文案」——它必须躺在那一轮的文件夹里，
跟 10 张图和总图在一起。做法：`文案全集.md` 按 `══` 段拆成单份 → 转 Google Doc → 上传进对应轮次文件夹。
上传 .md 转 Doc 时**必须带 `content_mime_type: text/markdown`**，否则转换会丢正文，只剩标题。

**第 5 步是硬要求**：只要一轮出了多张，就必须有一张总图，并且**上传到该轮子文件夹**，
不能只留在本地。选首图、跟人讨论都靠它。

### 1. 取素材

**详见 [`下载小红书原图.md`](下载小红书原图.md)。** 一句话：别自己解析小红书页面，
用 GitHub 上的 `JoeanAmier/XHS-Downloader`（curl_cffi 做 TLS 指纹伪装，无需 cookie），
通过 GitHub Actions 中转跑到 `media-out` 分支再取回。

- 机房 IP 裸请求只有「游客壳」（页面 0 个图链，接口回 `-101 无登录信息`），
  yt-dlp / gallery-dl / jina / wayback / playwright 全都不行。
- 笔记页的 CDN 链接带时间戳签名，会过期 —— **让 runner 现抓页面现提链接**，
  不要复用旧链接。
- 落地前按内容 sha256 去重、按文件头确认是真图片（页脚的备案 PDF 会被误捞）。
- **抓完立刻把图和 workflow 从仓库删掉**，别把二进制留在 git 历史里。

### 2. 量设计（别靠猜）

看不到图的时候，用脚本把原片量出来：

- `tesseract -l chi_sim+eng --psm 11 tsv` → 有没有文字、在哪、多大
- 分 10 带取主色 → 配色是糖果色还是低饱和胶片调
- 边缘密度图 → 满幅出血还是有留白、有没有标题栏

本项目原片实测结论（写死在提示词里）：

- 满幅出血，无白边、无留白、**无中文标题栏**
- 低饱和胶片调：石板蓝灰 `#525f6d` ／ 暖褐 `#b38671` ／ 奶油白 `#f2ede5`
- 顶部与四角压暗（电影暗角），中段暖高光
- 全画面密集纹理道具，无空场
- 物件上印**英文小字**（实测到 `BLANKET`、`COFFEE`）

### 3. 生成

参考图给 4–6 张原片缩略图（720×1520 足够），提示词结构：

```
Reference-locked: reproduce the EXACT same two cartoon bear characters ...
absolutely no redesign. Full-bleed vertical illustration, 1080x2280 (9:19
phone wallpaper), no borders or margins ...
Muted low-saturation film palette of slate blue-grey, warm taupe, cream and
soft cocoa brown, with restrained <节日> accents ... used sparingly.
Cinematic soft directional light, gentle vignette, richly textured ...
Layered depth: soft foreground props, the two bears in the mid-ground,
atmospheric background.
IMPORTANT: absolutely no letters, words, numbers or writing anywhere in the
artwork, and keep one calm uncluttered flat surface in the lower third.
Scene: <具体场景，两只在做什么、前景中景背景各有什么>
```

最后两句是关键：

- **中文禁止模型写字**（不出或拼错）；英文单词可以让模型自己画，见「让模型写字」一章，出完用 OCR 验。
- **留一块平整面** —— 给后期叠字留位置。

### 4. 后期

```sh
pip install --break-system-packages pillow numpy
python3 scripts/finish.py spec.json
```

`finish.py` 依次做：

1. 居中裁到 9:19 → `LANCZOS` 重采样到 1080×2280
2. `UnsharpMask(radius=2, percent=60, threshold=3)`
3. 胶片分级：降饱和 0.8 → 冷暖分离（暗部暖褐／亮部石板蓝）→ S 曲线 → 暗角 → 颗粒
4. `stamp_word()`：在**下半部最平整的区块**叠加一个词 —— 这是画面里唯一的文字元素，
   要做得像设计元素而不是小贴图：默认 `scale=1.35`（约 0.46W 宽）、字距 0.16em、
   下方一条细规线、透明度 0.72、轻微旋转 ±2°，颜色取该区块底色
   （亮底压暗、暗底提亮）

只是补字、不想重新调色时，单独调 `stamp_word()` 即可，**不要**重复跑分级。

**用英文，不要用中文**，三个理由：

1. 原片实测只有英文（`BLANKET`、`COFFEE`），用中文等于改设计
2. 模型画汉字必崩，英文短词容错高
3. 英文能确定性叠；中文要装 CJK 字体（`pip install mplfonts`，
   自带 Noto Sans CJK SC / 思源宋体），`lang="zh"` 才可用 —— 留作备选，不默认用

### 5. 归档

云盘按轮次分子文件夹，不要平铺：

```
原始素材/
└─ 素材 02/
   ├─ 第1轮-原片9张（小红书下载）
   ├─ 第2轮-常规复刻10张
   ├─ 第3轮-圣诞特辑10张
   ├─ 第4轮-跨年特辑10张
   └─ 素材02-档案与小红书文案        ← 来源链接、每轮清单、设计语言、文案
```

档案 Doc 里要记：生成会话链接、原笔记链接、云盘路径、每轮文件清单、
设计语言、当轮文案。

### 6. 文案

固定结构：标题三选一 + 正文（前 3 行必须在折叠前露完）+ 短版（单图用）
+ 话题标签 + 发布提示（勾「含 AI 生成内容」、首图建议）。

## 坑

- **模型输出不是 9:19**：704×1504 是 0.4681，差一点点，直接拉伸会变形，必须先裁。
- **小字/中文漏字**：中文、长句、字号太小模型不可靠，必须后期叠；4–6 个大写英文单词可以放心交给模型（出完用 OCR 验）。
- **重复调色**：补字时重跑 `finish.py` 会二次降饱和、二次暗角，画面会发灰。
- **参考图漂移**：别拿上一轮生成的图当参考，会累积漂移，永远用原片。
- **二进制进 git**：抓图用过的 workflow 和图片必须清掉，否则分支会被重置/膨胀。
- **看不到图**：没有视觉能力时，所有判断都要落到数据上（OCR、取色、边缘密度），
  别靠「感觉」。
