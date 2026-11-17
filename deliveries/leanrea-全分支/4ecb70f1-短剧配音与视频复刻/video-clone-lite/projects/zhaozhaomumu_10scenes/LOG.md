# video-clone-lite 施工记录（LOG.md）— Kaggle GPU 实测复刻版

- **上游项目**：`liangdabiao/video-clone-lite` (`925a61f`) + `kgen` 开源 GPU 扩展通道
- **复刻主题**：《走过你的朝朝暮暮》（噜噜 & 噜妹 · 走出卧室 10 场景全动态 AI 视频复刻）
- **算力平台**：Kaggle Batch Kernel (`is_private=true`, 即用即停自动销毁)
- **实测 GPU**：`2 × Tesla T4` (29.1 GB 总显存)
- **视频生成模型**：`video-clone-lite/kgen (Lightricks/LTX-Video-0.9.5)` (`512×896 × 73帧 @ 24fps` 时空扩散 → `1080×1920` 竖屏合成)
- **商业接口费用**：`0.00 元`（纯开源模型 + Kaggle 免费 GPU 配额）
- **10 镜扩散总耗时**：`853.76s`（Kernel 全流程 `961.83s`）

## 逐镜生成与动态检验指标

| 镜头 | 分配显卡 | 扩散帧数 | 帧间动态均值 (MAD) | 静止帧占比 | 推理耗时 | 单镜体积 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| S01 | GPU-0 | 73 帧 | `0.7` | `0.0%` | `118.74s` | `737.6 KB` |
| S02 | GPU-1 | 73 帧 | `3.984` | `0.0%` | `119.5s` | `2137.3 KB` |
| S03 | GPU-0 | 73 帧 | `1.399` | `0.0%` | `112.92s` | `1046.2 KB` |
| S04 | GPU-1 | 73 帧 | `1.849` | `0.0%` | `117.29s` | `2161.2 KB` |
| S05 | GPU-0 | 73 帧 | `0.622` | `0.0%` | `112.5s` | `1061.9 KB` |
| S06 | GPU-1 | 73 帧 | `2.817` | `0.0%` | `116.83s` | `2605.1 KB` |
| S07 | GPU-0 | 73 帧 | `1.533` | `0.0%` | `113.38s` | `1406.2 KB` |
| S08 | GPU-1 | 73 帧 | `1.463` | `0.0%` | `115.68s` | `1223.6 KB` |
| S09 | GPU-0 | 73 帧 | `0.235` | `0.0%` | `111.32s` | `507.1 KB` |
| S10 | GPU-1 | 73 帧 | `1.838` | `0.0%` | `114.04s` | `2048.5 KB` |

## 执行流水线核验
1. `python scripts/build.py extract` → 生成 `refs/overview.jpg` + `refs/audio.mp3` + `refs/info.txt`
2. `python scripts/build.py kgen plan.json --yes` → FP32 T5-XXL 预编码英文 S-A-C-S-C 分镜 + Kaggle 双卡并行 LTX-Video I2V 生成 + 封装 F5-TTS/Seed-VC 克隆角色干声
3. `python scripts/build.py assemble plan.json` → 逐镜精确裁剪 3.00s + 烧录站酷快乐体对白字幕 + `-12dB` 混入纯音乐 BGM → `out/final.mp4` (`12.13 MB`)
