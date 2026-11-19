# 一二和布布 · 治愈系壁纸复刻 Skills

> 可复用的图片生成工作流，用于批量生成保持角色形象一致的治愈系壁纸。

---

## 📌 基本信息

| 项目 | 内容 |
|------|------|
| 角色 | 一二（奶油色小熊）+ 布布（棕色小熊） |
| 画风 | 治愈系、可爱、kawaii、柔和色彩 |
| 尺寸 | 1080×2280 竖版手机壁纸/聊天背景 |
| 比例 | 1080/2280 = 0.4737 |
| 素材来源 | 小红书 @有间Aigc绘图笔记【bzyy】 |
| 原创素材文件夹 | Google Drive: `一二和布布 - 原始素材\素材 01\` |

---

## 🔧 工作流程

### 1. 准备参考图
- 下载 9 张原始素材图到本地
- 作为 `images` 参数传入 `generate_image`，保持角色形象一致

### 2. 生成图片
- 每次生成 1 张，描述新场景
- 必须包含关键词：`Two cute chubby bears (one cream-colored, one brown)`
- 必须包含：`Keep the bear characters exactly as in the reference image - same appearance, colors, facial features, body shape`
- 每次调用传入 2 张原始素材作为参考图

### 3. 裁剪到目标比例
- 目标尺寸：1080×2280
- 使用 Pillow：先 resize 到目标高度，再居中 crop 宽度

### 4. 上传到 Google Drive
- 每轮结果放入对应子文件夹：`第一轮-日常系列` / `第二轮-圣诞节系列` / 后续轮次

### 5. 记录文案
- 生成小红书文案（标题+正文+标签）
- 记录 Arena Agent 链接

---

## 📐 尺寸裁剪脚本

```python
from PIL import Image

def crop_to_ratio(img_path, out_path, target_w=1080, target_h=2280):
    img = Image.open(img_path)
    target_ratio = target_w / target_h
    src_ratio = img.size[0] / img.size[1]
    if src_ratio > target_ratio:
        new_h = target_h
        new_w = int(new_h * src_ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - target_w) // 2
        img = img.crop((left, 0, left + target_w, new_h))
    else:
        new_w = target_w
        new_h = int(new_w / src_ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        top = (new_h - target_h) // 2
        img = img.crop((0, top, new_w, top + target_h))
    img.save(out_path, 'PNG')
```

---

## 🎨 提示词模板

```
Two cute chubby bears (one cream-colored, one brown) [场景描述]. Keep the bear characters exactly as in the reference image - same appearance, colors, facial features, body shape. [风格关键词], vertical phone wallpaper composition, soft pastel colors, clean lines, warm lighting, high quality illustration
```

### 风格关键词库
- 日常系列：`cozy healing kawaii style`
- 圣诞节：`festive Christmas design, cute healing kawaii style`
- 通用：`soft pastel colors, clean lines, warm cozy lighting, high quality children's picture book illustration`

---

## 📁 文件夹结构

```
一二和布布 - 原始素材/
└── 素材 01/
    ├── 今日份熊图请查收💒_1~9.jpg   (原始素材)
    ├── 第一轮-日常系列/             (10张日常场景)
    ├── 第二轮-圣诞节系列/           (10张圣诞场景)
    └── 第N轮-xxx系列/              (后续轮次)
```

---

## 📋 已完成轮次

| 轮次 | 主题 | 数量 | 日期 | 文件夹 | 文字元素 |
|------|------|------|------|--------|----------|
| 第一轮 | 日常系列 | 10张+1总图 | 2026-11-05 | 第一轮-日常系列 | 无 |
| 第二轮 | 圣诞节系列 | 10张+1总图 | 2026-11-05 | 第二轮-圣诞节系列 | 无 |
| 第三轮 | 跨年系列 | 10张+1总图 | 2026-11-05 | 第三轮-跨年系列 | 无 |
| 第四轮 | 元旦系列 | 10张+1总图 | 2026-11-05 | 第四轮-元旦系列 | 2027/元旦快乐/新年快乐 |
| 第五轮 | 冬至系列 | 10张+1总图 | 2026-11-05 | 第五轮-冬至系列 | Winter Solstice (英文) |

> **重要更新**：
> - 第三轮起，所有图片提示词必须包含 `NO TEXT, NO LETTERS, NO WORDS anywhere in the image`，确保画面干净无文字。
> - **第四轮（元旦系列）起改为包含文字元素**：提示词必须明确要求文字内容（如"2027"、"元旦快乐"等），且文字必须清晰可见。
> - **第五轮（冬至系列）起文字元素统一使用英文**（用户反馈英文更好看），如 "Winter Solstice"。
> - **每轮生成 10 张 + 1 张总预览图**：总预览图用 Pillow 拼图（2行5列），所有图片需先裁剪到 1080×2280 再拼。
> - **第五轮起加入节日特色元素**：如冬至的饺子、圣诞节的圣诞树等，让主题更鲜明。

> **重要更新**：
> - 第三轮起，所有图片提示词必须包含 `NO TEXT, NO LETTERS, NO WORDS anywhere in the image`，确保画面干净无文字。
> - **第四轮（元旦系列）起改为包含文字元素**：提示词必须明确要求文字内容（如"2027"、"元旦快乐"等），且文字必须清晰可见。
> - **每轮生成 10 张 + 1 张总预览图**：总预览图用 Pillow 拼图（2行5列），所有图片需先裁剪到 1080×2280 再拼。

---

## 🔗 创作记录

- Arena Agent: https://arena.ai/agent/01a1aa7f-3c52-78b3-b486-f4986467c7b2
- 素材来源: 小红书 @有间Aigc绘图笔记【bzyy】
- 生成时间: 2026-11-05

---

## ⚠️ 注意事项

1. **角色一致性**：每次生成必须传入原图作为参考，确保熊的形象一致
2. **原创性**：场景必须全新设计，不抄袭原图内容
3. **比例**：生成后必须裁剪到 1080×2280，不能直接使用生成尺寸
4. **上传规范**：每轮结果放入独立子文件夹，命名格式：`第N轮-主题系列`
5. **文案记录**：每轮生成小红书文案，包含标题、正文、标签
