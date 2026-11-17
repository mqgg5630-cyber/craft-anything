# 配图：10 张铜版画原图 → 20 个单墨版本

## 为什么推翻重来

v1 是\"四种材料拼贴\"：写实实验室照片、3D 分子渲染、水彩细胞、风景照（山、隧道、学生）。v2 用 duotone 把它们压成两色，风格是勉强统一了，但**题材还是不像生物学**——风景照讲活化能、教室照当收句，怎么调色都不对。

v3 的做法是**从生成端就只出一种材料**：十九世纪铜版／木刻版画。全部 10 张共用同一段风格约束，所以它们**天生是一套图版**，duotone 只负责把纸色对齐到页面。

```
assets/deck-images/src/<name>.jpg      原图（1408×768，图内零文字）
assets/deck-images/<name>-light.jpg    浅版：纸底、墨线，嵌进浅色页
assets/deck-images/<name>-ink.jpg      深版：墨底、收窄高光，整版图 / 深色页
```

## 共用风格约束（每张都带）

> authentic 19th-century scientific engraving, copperplate / wood-engraving, a single dark ink printed on warm off-white rag paper, tone built from fine cross-hatching and stipple, crisp contour lines, visible paper grain, monochrome only, **no text, no letters, no numbers, no labels, no arrows, no border, no frame**, subject centred with generous margins. Avoid: photograph, 3D render, watercolour, gouache, glow, neon, bokeh, gradient mesh, cartoon.

## 十张图

| 文件 | 画面 | 用在哪 |
|---|---|---|
| `tubes` | 木架上三支试管，中间那支剧烈冒细密气泡，左清右微浊，侧光 | 酶封面；第4章「自由扩散」 |
| `splint` | 戴布手套的手用镊子夹带火星木条靠近试管口，一缕细烟 | 酶的「复燃」现象页；第4章断电实验 |
| `flask` | 锥形瓶里液体翻涌成密集气泡柱，无塞，逆光 | 「几微克 / 一整瓶」双大数字页 |
| `enzyme` | 折叠的蛋白托住一枚底物，凹槽处相接（铜版式分子图） | 本课唯一的问题 / 换催化剂 |
| `cell` | 植物细胞剖面：双层细胞壁、大液泡、叶绿体（含基粒）、细胞核、胞间连丝 | 定义页；第4章「植物细胞多了一样东西」 |
| `onion` | 洋葱表皮细胞质壁分离：细胞壁不动，原生质体缩走，四角留出空隙 | 质壁分离实验页；第4章第3课时分隔 |
| `membrane` | 磷脂双分子层截面：两排头部 + 成对尾部，一枚桶状蛋白贯穿 | 协助扩散 / 载体 / 大分子运输 |
| `root` | 根尖纵剖：根冠、分生区、伸长区、成熟区与密生根毛 | 第4章第一问 / 钩子 / 收句 |
| `stomata` | 叶表皮气孔：两个肾形保卫细胞围着孔，周围表皮细胞拼图状 | 课时二分隔页 |
| `saltfield` | 盐霜龟裂的地面上，一株抽穗的水稻；天空只用横排线 | 第4章封面 / 回到稻子 |

图的**信息量为零**：不标结构名、不画箭头、不写数字。要读的关系（曲线两端、平台、原生质层位置）一律由 `build_deck.py` 的 `diagram` / `chart` / `table` 原生绘制——图只负责\"这是生物学的东西\"。

## 上色曲线

构建时 `scripts/build_deck.py` 直接调用 `duotone.make_pair()`，按当前主题取纸色／墨色，**纸色与页面完全一致**，于是图片可以 `meet` 放进版面而不露边框。

| 版本 | 曲线 |
|---|---|
| `-light` | 灰度 → 自动对比（cutoff 1）→ 对比度 1.15 → gamma 0.58 → 墨（暗）↔ 纸（亮） |
| `-ink` | 灰度 → 自动对比 → 对比度 1.10 → 深墨（暗）↔ 墨混纸 44%（亮），压住高光给白字让位 |

gamma 是关键：只调对比度会把中间调压成死黑（首版均值 90，像复印坏了）。0.58 让纸白透出来，均值回到 131 左右。

## 重新派生

```sh
# 单墨基准（仓库里存的就是这一套，供 SVG 预览用）
python3 scripts/duotone.py assets/deck-images/src assets/deck-images --theme plate --width 1400

# 某个主题（构建时自动跑，不必手动）
python3 scripts/duotone.py assets/deck-images/src /tmp/tone-textbook --theme textbook
```

原图由 Arena 内置图像模型生成（2026-11-03）。**只承担氛围与形态，不承担任何事实标注**。
