# GitHub 上「抖音取图 + 三视图」相关工具调研

调研时间：2026-11-07。方法：`gh search repos` / `api.github.com/repos/...` 取实时 star，逐个看 README 与代码路径，不只看标题。
star 数均为当日 GitHub API 返回值（沙箱只放行 GitHub / PyPI / npm，抖音 CDN 直接 TLS 被重置，所以「能不能抓」和「工具好不好」是两件事，分开记）。

## 结论先说

1. **取图这一步没有「装上就能用」的银弹**。抖音 `/note/` 图文链接：`yt-dlp` 报 `Unsupported URL`，`gallery-dl` 报
   `Unsupported URL`，桌面页 HTML 里一张图都没有（靠 JS 渲染），老的 `iesdouyin.com/web/api/v2/aweme/iteminfo` 已失效
   （返回 HTML 而非 JSON）。这三个坑都是本仓库在 Actions 上实测出来的，见 `tools/media-library/` 的 `_LAST_RUN.md`。
2. 真正能出图的路子只有三类：**带 cookie 的成品下载器** / **自建签名接口** / **移动端分享页 JSON + 第三方解析 API**。
   本仓库选了第三条（不需要账号，`three-view` 技能里的 `douyin-note` 通道就是它），把它写进 relay worker 里跑在 GitHub Actions 上。
3. 「三视图」这件事 GitHub 上没有现成 skill，只有**方法论 + 少量设定图模板库**。可抄的是 ai-chan-sheets 的「拆成本视图 / 表情 / 服装 / 道具
   独立素材，再 1:1 拼回横版」的组织方式，而不是它的画风。

## 一、抖音取图 / 取视频

| 仓库 | ★ | 做什么 | 判断 |
|---|---|---|---|
| [Evil0ctal/Douyin_TikTok_Download_API](https://github.com/Evil0ctal/Douyin_TikTok_Download_API) | 21234 | 自托管异步解析 API（抖音 / TikTok / B 站），FastAPI + PyWebIO，Docker 一键部署，**支持图文图集**，也提供 MCP 接入 | ⭐⭐ 想要「稳定、可批量、能拿图文原图」就上它。代价是要自己部署 + 维护 cookie；公共实例常年打不通 |
| [jiji262/douyin-downloader](https://github.com/jiji262/douyin-downloader) | 12556 | 单条 / 主页批量下载，视频 + 图集 + 合集 + 音乐，SQLite 去重、断点续传、验证码弹浏览器人工过 | ⭐⭐ 本机批量搬号的实用款。**必须要 cookie**；图集是按作品目录归档的，命名干净 |
| [Johnserf-Seed/f2](https://github.com/Johnserf-Seed/f2) | 2724 | 多平台高速下载（抖音 / TikTok / 快手 / B 站…），Python 包 + CLI，更新频率高 | ⭐ 适合写进脚本当库用；同样卡 cookie |
| [yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp) | 205860 | 万金油下载器 | 抖音只认 `/video/` 与部分分享链，`/note/` 图文直接 unsupported（实测）；作为 relay 的第一级降级通道仍然值得留 |
| [mikf/gallery-dl](https://github.com/mikf/gallery-dl) | 20403 | 图集专用下载器（几百个站点） | 抖音不在支持列表；TikTok / 微博 / Pinterest / IG 反而好用，图文类站点优先选它 |
| 本仓库 `tools/media-library/` | — | GitHub Actions 中继：沙箱写 `.mediaqueue/urls.txt` → runner 出网抓 → 结果 commit 回 `media-out` 分支 | ⭐⭐ 沙箱出口只放行 GitHub/PyPI/npm 时唯一能跑通的路；`douyin-note` 通道专治 `/note/` 图文 |

## 二、三视图 / 角色设定图

| 仓库 | ★ | 做什么 | 可借鉴 |
|---|---|---|---|
| [lmy414/ai-chan-sheets](https://github.com/lmy414/ai-chan-sheets) | 483 | 把一张立绘补成**横版完整设定图**：拆成三视图 / 表情 / 服装 / 道具独立素材，「推定补全侧背面」，原生像素 1:1 拼接 | ⭐⭐ 目录结构直接照抄：`三视图/正面`、`表情/`、`服装/`、`道具/`；「侧背面靠推定」这点和本技能一致——AI 不会凭空知道背面，得用同一张基线图当参考 |
| [PicoTrex/Awesome-Nano-Banana-images](https://github.com/PicoTrex/Awesome-Nano-Banana-images) | 24021 | Nano Banana 生图案例合集（含大量「角色多视图 / 表情九宫格」提示词） | ⭐ 找提示词句式用；三视图提示词的关键词（`character turnaround sheet`、`front / side / back view`、`same character, consistent proportions`）就是从这类案例里归纳的 |

没有找到的：**任何把「一条抖音三视图笔记」直接变成「10 张可商用素材包 + 预览图 + 文案」的现成 skill**。
所以本仓库自己写了一个（`three-view/SKILL.md`），只依赖 Pillow 和 `generate_image`。

## 三、为什么不用它们，而用自建 relay

| 方案 | 能不能拿到这条笔记的 6 张图 | 代价 |
|---|---|---|
| 本机跑 `douyin-downloader` / `f2` | ✅（导 cookie 后） | 需要 Windows 上装 Python、导 Netscape cookie、手动同步到 G 盘 |
| 公共在线解析站 | ⚠️ 时好时坏 | 广告、限速、链接容易失效 |
| yt-dlp / gallery-dl 裸跑 | ❌ 实测 unsupported | — |
| 本仓库 Actions relay（`douyin-note` 通道） | ✅ 无需账号（分享页 JSON / 第三方 API） | 需要 push 触发，1–3 分钟一轮；结果走 `media-out` 分支 |

命令（沙箱内即可）：

```sh
printf 'https://www.douyin.com/note/7645624036777334882\n' > .mediaqueue/urls.txt
git add .mediaqueue/urls.txt && git commit -m "queue: douyin note" && git push
# 1–3 分钟后
git fetch origin +refs/heads/media-out:refs/remotes/origin/media-out
git show origin/media-out:media-raw/_LAST_RUN.md      # 逐条结果 + 命中工具 + 失败原因
```

产物落在 `media-raw/02_抖音素材/<aweme_id>/`，带 `meta.json`（来源链接、命中工具、逐文件 sha256、字节数）。
