# healing-video-dub · 3D 治愈动画模板换文案克隆配音与多场景动态合成技能

> 一个 [`SKILL.md`](SKILL.md) + 四个脚本（`probe_template.py` / `clone_and_dub_a1.py` / `expand_30s_template.py` / `render_10scenes_30s.py`）：既支持固定 1080×1920 24fps 3D 动画底片无损换文案克隆配音，也支持走出卧室的 **10 大真实全身形象 3D 场景 + `Depth-Anything-V2` 神经 3D 视差运镜 + 音节联动毛绒角色律动 + 10 镜环境粒子光影** 动态成片合成。
> 延续本仓库 [`leanrea/`](../leanrea/) 与 [`healing-comic/`](../healing-comic/) 的设计哲学：零 MCP、零付费 API、带硬门禁自动验收。

---

## 实测样片三（30.00s 走出卧室全天 10 场景动态版）：《走过你的朝朝暮暮 · 全天十景》

- **30s 10 场景动态成品视频**：[`examples/output/zhaozhaomumu_10scenes_30s.mp4`](examples/output/zhaozhaomumu_10scenes_30s.mp4)（`1080×1920 @ 24.0fps`，`720 帧`，**冻结帧 `0.00%`**，10 大非躺床场景 × 3s：晨光厨房 → 林荫花径 → 街角奶茶 → 草坪野餐 → 太阳雨巷 → 海滨兜风 → 橘子海落日 → 暖灯集市 → 客厅热可可 → 繁星烟花露台）
- **10 镜关键帧 + 克隆音轨波形 + 帧间运动连续性核验图**：[`examples/output/zhaozhaomumu_10scenes_timeline_qa.png`](examples/output/zhaozhaomumu_10scenes_timeline_qa.png)
- **配置与克隆干声**：[`examples/spec-zhaozhaomumu-10scenes-30s.json`](examples/spec-zhaozhaomumu-10scenes-30s.json) · [`examples/clips-zhaozhaomumu-10scenes/`](examples/clips-zhaozhaomumu-10scenes/)（Colab Tesla T4 即用即停实测：`Depth-Anything-V2-Large` 10 镜深度图 + `F5-TTS + Seed-VC` 克隆 + 双声纹核验共 **`237.87s`**，完成后立即释放会话归零）

---

## 实测样片二（30.04s 三幕长片）：《走过你的朝朝暮暮》（Colab T4 即用即停实测）

- **30s 成品视频**：[`examples/output/zhaozhaomumu_a1_30s.mp4`](examples/output/zhaozhaomumu_a1_30s.mp4)（`1080×1920 @ 24.0fps`，`721 帧`，冻结帧 `0.00%`，三次亲脸颊音效禁区人声泄漏 `0.000000`）
- **12 句波形与 3 处亲吻禁区核验图**：[`examples/output/zhaozhaomumu_30s_timeline_qa.png`](examples/output/zhaozhaomumu_30s_timeline_qa.png)
- **三幕光影递进预览（朝·晨光 → 暮·晚霞 → 星夜微推镜）**：[`examples/output/zhaozhaomumu_3acts_lighting_qa.png`](examples/output/zhaozhaomumu_3acts_lighting_qa.png)
- **台词配置源文件**：[`examples/spec-zhaozhaomumu-30s.json`](examples/spec-zhaozhaomumu-30s.json)
- **Colab T4 冷启动（即用即停）实测耗时**：GPU 活跃总耗时 **`225.05s`（`3 分 45 秒`）**（含环境安装 `53.7s` + 36 条 F5-TTS `47.9s` + 24 条 Seed-VC `74.7s` + 双声纹模型核验 `9.4s`，推理完立即 `colab stop` 释放会话归零）。

---

## 实测样片一（10.08s 单幕短片）：《周末赖床篇：偷亲一下小懒猪》（A1 架构）

- **成品视频**：[`examples/output/weekend_snuggle_a1_10s.mp4`](examples/output/weekend_snuggle_a1_10s.mp4)（`1080×1920 @ 24.0fps`，冻结帧 `0.00%`，`3.50s` 亲吻禁区人声泄漏 `0.000000`）
- **波形与槽位对齐验收图**：[`examples/output/weekend_snuggle_timeline_qa.png`](examples/output/weekend_snuggle_timeline_qa.png)
- **自动门禁报告**：[`examples/output/weekend_snuggle_qa.json`](examples/output/weekend_snuggle_qa.json)
- **台词配置源文件**：[`examples/spec-weekend-snuggle.json`](examples/spec-weekend-snuggle.json)

### 替换后的新四拍台词（严格贴合 24fps 角色嘴型与亲吻动作）

| 槽位 | 时间窗 | 角色 | 新台词 | 声纹相似度 / 倍速比 |
| :--- | :---: | :---: | :--- | :---: |
| `slot1` | `1.57s – 2.92s` | **撸妹** (`lumei`) | **「偷亲一下小懒猪！」** | `CAMPPlus 0.562` · `1.0x` 原速 |
| *(禁区)* | `3.32s – 4.12s` | *(原版音效)* | *（凑近亲脸颊 `mua~` 音效，0 人声侵入）* | `泄漏 = 0.000000` |
| `slot2` | `4.24s – 5.79s` | **噜噜** (`lulu`) | **「唔，谁偷亲我呀？」** | `WavLM-SV 0.961` · `1.16x` 保调 |
| `slot3` | `6.17s – 7.43s` | **撸妹** (`lumei`) | **「周末再抱五分钟嘛！」** | `CAMPPlus 0.521` · `1.0x` 原速 |
| `slot4` | `7.82s – 9.49s` | **噜噜** (`lulu`) | **「好啦，今天陪你赖到底！」** | `WavLM-SV 0.957` · `1.0x` 原速 |

---

## 30 秒复现 / 换任意新文案

```sh
cd healing-video-dub
python3 -m pip install numpy scipy soundfile Pillow opencv-python-headless imageio-ffmpeg matplotlib

# 1. 直接复现《周末赖床篇》10s A1 成片（0.4 秒完成混音、无损封装与门禁验收）
python3 scripts/clone_and_dub_a1.py examples/spec-weekend-snuggle.json \
  --out examples/output/weekend_snuggle_a1_10s.mp4 \
  --qa-json examples/output/weekend_snuggle_qa.json \
  --qa-plot examples/output/weekend_snuggle_timeline_qa.png

# 2. 本地 GPU 改完 spec.json 台词现场跑 F5-TTS + Seed-VC 克隆并合成新成片
python3 scripts/clone_and_dub_a1.py examples/spec-weekend-snuggle.json \
  --clone-on-the-fly --engine hybrid --seed-vc-dir /path/to/seed-vc \
  --out examples/output/custom_10s.mp4

# 3. 扩展为 30 秒三幕长视频（校验 12 句台词门禁 + 生成 30s 零卡顿底片）
python3 scripts/expand_30s_template.py --mode estimate --spec-30s examples/spec-milk-tea-30s.json
```

---

## 10 秒 vs 30 秒生成耗时速查

- **本地 GPU 热启动（模型常驻显存）**：10 秒（4 句）约 **`15 秒`**；**30 秒（12 句）仅需 `40 ~ 55 秒`（不到 1 分钟）**。
- **云端 Colab T4 冷启动（含即用即停自动销毁）**：10 秒实测 **`3 分 01 秒`**；**30 秒约 `3.8 ~ 4.5 分钟`**（固定冷启动拉环境占约 2.5 分钟，多 8 句台词推理仅增加约 35 秒）。
- **纯 CPU 模式**：10 秒约 `1 分钟`；**30 秒约 `2.5 ~ 4 分钟`**。

---

## 目录结构

```
SKILL.md                                        核心技能文档（方法论、卡点表、踩坑铁律、30s 扩容方案）
scripts/
  probe_template.py                             底片帧率/冻结帧检测 + 开口槽位勘测 + 嘴部特写条带图导出
  clone_and_dub_a1.py                           文案门禁 + F5-TTS/Seed-VC 克隆 + 零漂移混音 + H.264 零损封装 + QA
  expand_30s_template.py                        10s -> 30s 零卡顿画面与伴奏扩容工具（multi_clip / pingpong）
templates/capybara_morning_10s/
  template_manifest.json                        4 槽位嘴型时间窗 + 3.50s 亲脸颊音效禁区定义
  speaker_profiles.json                         撸妹 & 噜噜角色声纹参数
  video_1080p24_muted.mp4                       1080×1920 24fps H.264 纯净无声 3D 模板底片
  stems/bgm_and_kiss_sfx.flac                   44.1kHz 立体声晨间吉他 BGM + 3.50s 亲吻音效轨
  refs/ref_*.flac                               提纯双角色干净参考声纹
examples/
  spec-weekend-snuggle.json                     10s 换文案实测配置：《周末赖床篇》
  spec-milk-tea-30s.json                        30s 三幕 12 句扩展配置范例：《热奶茶篇》
  clips-weekend-snuggle/                        GPU (F5-TTS + Seed-VC) 实测克隆干声与相似度报告
  output/                                       10s A1 成片 MP4 + QA 验收 JSON + 波形核验图 PNG
```
