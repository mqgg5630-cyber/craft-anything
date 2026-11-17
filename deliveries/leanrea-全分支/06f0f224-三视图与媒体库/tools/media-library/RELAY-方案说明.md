# GitHub Actions 中继下载方案

日期：2026-11-05 ｜ 适用：本沙箱（Arena）内采集任意平台素材

---

## 一、真正的病根

之前那份《下载工具箱·安装与测试报告》的判断是：

> 本沙箱出口只放行 github.com / pypi.org / registry.npmjs.org，
> 抖音/小红书/YouTube 全部 HTTP 000，所以抓不到，换台能出网的机器再补。

**前半句对，结论可以再往前走一步。**

沙箱出网确实被限制，但 **GitHub Actions 的 runner 出网不受限**。
所以不需要"换台机器"——把下载任务搬到 runner 上跑，结果 commit 回分支，
本地 `git pull` 就能拿到。本机一行命令即可完成，全程不出沙箱。

链路：

```
本沙箱                        GitHub                        本沙箱
写 .mediaqueue/urls.txt  →  Actions runner 跑 yt-dlp   →  git pull
git push                     /gallery-dl/直连            media-raw/ 里就是素材
                             结果 commit 回分支
```

---

## 二、怎么用

仓库里已经备好，开箱即用：

```bash
tools/media-library/gh-relay "https://www.douyin.com/video/xxxx"
tools/media-library/gh-relay "url1" "url2" "url3"
tools/media-library/gh-relay --from links.txt
tools/media-library/gh-relay --status     # 看上一次跑的结果
```

脚本会自己：写队列 → push → 轮询 workflow → 跑完 `git pull` → 打印结果表。
通常 1–3 分钟。

产物落在 `media-raw/<云盘目录名>/<作品ID>/`，跟云盘 8 个平台文件夹一一对应，
每条带 `meta.json`（来源链接、命中工具、逐文件 sha256、字节数）可直接拖拽同步。

文件：

| 文件 | 作用 |
|---|---|
| `tools/media-library/gh-relay` | 本地入口：排队、推送、轮询、拉回 |
| `tools/media-library/relay_worker.py` | runner 上跑的下载器，四级降级 |
| `.github/workflows/media-relay.yml` | 触发器：队列或工具变更就跑，结果 commit 回来 |
| `.mediaqueue/urls.txt` | 待抓链接，一行一条 |

---

## 三、降级策略（worker 内部）

每条链接依次试，命中即停：

1. **yt-dlp** —— 视频优先，格式阶梯 `bv*[h<=480]+ba/b` → `18/22/43/b` → `b` → `bv*+ba/b` → `worst`
2. **平台专用通道** —— 小红书 `xhs-dump`、B站 `bilibili-api`、抖音 `douyin-api`
3. **gallery-dl** —— 相册优先（TikTok / Instagram / Pinterest / 微博）
4. **html-scrape** —— 兜底，直接扒页面里的 CDN 图片链接

两个坑已经填掉，别再踩：

* `--write-thumbnail` 一定会写缩略图，**不能把"有文件"当成功**，
  否则失败会被伪装成成功。只认 mp4/m4a/webm 等真媒体扩展名。
* 命令拼装时 URL 必须真的进 argv，漏了会得到
  `You must provide at least one URL` 这种看起来像平台风控的假错误。

---

## 四、实测结果（2026-11-05，Actions 数据中心 IP）

| 平台 | 结果 | 命中 | 拿到什么 |
|---|---|---|---|
| **TikTok** | ✅ | yt-dlp | 真视频 3.26 MB |
| **小红书** | ✅ | xhs-dump | 12 个文件，0.40 MB |
| **YouTube** | ⚠️ | scrape | 25 个缩略图/封面，**视频没拿到** |
| **B站** | ❌ | — | 全链路 **HTTP 412** |
| **抖音** | ❌ | — | yt-dlp 要 cookie；iesdouyin 公开接口已失效 |

### 逐条说清楚

**TikTok —— 通了。** 第一个格式失败，阶梯往下走到 `b` 就拿到了完整 mp4。
这是"沙箱里也能抓 TikTok"的完整证据。

**小红书 —— 通了，从 4 个涨到 12 个。** 关键是别指望 yt-dlp
（图片笔记它会直接报 `No video formats found`），
走 `xhs-dump`：先试 `--dump-single-json`，失败就直接解页面里的
`window.__INITIAL_STATE__` 拿 `imageList` 的 `urlDefault`，
再把 `!nd_dft_xxx` 降质后缀去掉，就是原图。

**YouTube —— 半通。** 缩略图、封面图能拿到（25 个），视频拿不到。
轮换五种 player_client（android_vr / web_safari / ios / tv / default）
外加传统渐进式格式 `18/22/43`，三种报错轮换出现：
`Requested format is not available` / `HTTP 403 Forbidden` /
`The page needs to be reloaded`。这是 YouTube 对数据中心 IP 的常规风控。

**B站 —— 确认是 IP 级封禁，不是指纹问题。**
试过的路子（全部 412 Precondition Failed）：

* 网页端 + 浏览器 UA + Referer
* `api.bilibili.com/x/web-interface/view` 直连
* 官方指纹接口 `x/frontend/finger/spi` 取 buvid3/buvid4 再带 cookie 重试
* yt-dlp 全格式阶梯

B站对机房 IP 是硬拒绝，**只能换 runner 地区，没有别的办法**。

**抖音 —— 卡在 cookie。** yt-dlp 明确要求
`Fresh cookies (not necessarily logged in) are needed`；
自举匿名 cookie 拿不到（抖音对机房 IP 不返回 Set-Cookie）。
老的 `www.iesdouyin.com/web/api/v2/aweme/iteminfo` 无水印接口**已经失效**，
现在返回 HTML 不是 JSON。

---

## 五、剩下的三个怎么破（按性价比排序）

**1. 导出 cookie（能一次解决抖音 + YouTube，大概率也能解 B站）**

浏览器装 *Get cookies.txt LOCALLY* 扩展，分别在 douyin.com / youtube.com /
bilibili.com 登录状态下导出 Netscape 格式，存成：

```
.config/cookies/douyin.txt
.config/cookies/youtube.txt
.config/cookies/bilibili.txt
```

然后在 `relay_worker.py` 的 `try_ytdlp()` 里按域名挂上去：

```python
COOKIE_FILES = {
    "douyin.com":   os.environ.get("COOKIES_DOUYIN"),
    "youtube.com":  os.environ.get("COOKIES_YOUTUBE"),
    "bilibili.com": os.environ.get("COOKIES_BILIBILI"),
}
```

cookie 内容走 **GitHub Actions Secrets** 注入（`env:` 段），
不要直接写进仓库。

**2. 换 runner 地区（专治 B站）**

B站的 412 是地区 + 机房双判定。GitHub 托管 runner 只有美西/欧洲，
可以挂 self-hosted runner 在国内机器或香港节点的机器上，B站/抖音/快手基本就通了。
仓库里的工作流改一行即可：`runs-on: self-hosted`。

**3. 小红书补全 9 张**

现在拿 4 张，是因为**未登录**状态下笔记页只暴露部分图。
带上 xhs 的 cookie 再跑一次 `xhs-dump` 应该就是全套 9 张。

---

## 五之二、GitHub 上现成的工具，哪些真能救

你问"GitHub 肯定有能成功的工具"——有，但要分清楚**哪些卡的是工具、哪些卡的是环境**。
工具解决不了 IP 封禁，这点必须说在前面。

**yt-dlp 插件生态（yt-dlp 会自动加载，装完就生效）**

| 工具 | 治什么 | 装法 | 实测结果 |
|---|---|---|---|
| `bgutil-ytdlp-pot-provider` | YouTube 的 PO token / 403 | `pip install bgutil-ytdlp-pot-provider` | ❌ 已装，仍 403 |
| `yt-dlp-nightly` | 每日构建，extractor 修得比正式版快 | `pip install -U --pre yt-dlp-nightly` | ❌ 已装并优先调用，仍 403 |
| `formats=missing_pot` | 接受缺 PO token 的格式 | `--extractor-args "youtube:formats=missing_pot"` | ❌ 仍 403 |
| `player_client` 轮换 | 换播放器身份绕过风控 | `android_vr / web_safari / ios / tv / default` | ❌ 五种全试，仍 403 |

**YouTube 无 cookie 这条路，我已经试到底了。**
三招叠满（nightly + PO 插件 + missing_pot + 五种 client 轮换），
稳定复现 `HTTP 403 Forbidden` / `Requested format is not available` /
`The page needs to be reloaded` 三种报错轮换。

**还试过两条"绕开 IP"的路，也都堵死了：**

| 路子 | 做法 | 实测 |
|---|---|---|
| Invidious 公共实例 | 开源 YouTube 前端代取，换一条非机房 IP | ❌ 6 个实例全挂：inv.nadeko.net 403、nerdvpn.de 401、yewtu.be 403、melmac.space 连不上、privacyredirect 404、f5.si 530 |
| 公共 CORS 代理 | codetabs / allorigins / corsproxy 转发 B站、抖音接口 | ❌ 522 / 522 / 401 全部拒绝 |

**结论：YouTube 视频必须给 cookie，没有第二条路。**
（缩略图、封面、info.json 这些不需要 cookie，已经能拿。）

**平台专用下载器（都要 cookie，或者要能出网的地区）**

| 平台 | 工具 | 说明 |
|---|---|---|
| B站 | `yutto-dev/yutto`、`bilibili-API-collect` | 工具都成熟，但**IP 被封，换工具没用**，得换 runner 地区 |
| 抖音 | `JoeanAmier/TikTokDownloader`、`Evil0ctal/DouYinCommandLine` | 功能最全，但**必须给 cookie**，且要定期更新 |
| 快手 / 微博 / Instagram | `gallery-dl` 直接支持 | 后两家基本必须给 cookie |
| 全平台爬虫 | `MediaCrawler`（小红书/抖音/B站/微博） | 关键词级批量采集，重、要部署，适合大量采 |

**结论**：剩下三家卡的是**环境（数据中心 IP + 缺 cookie）**，不是工具。
工具箱里已经装了 yt-dlp + gallery-dl，这两个覆盖了 90% 的场景；
真要补齐，性价比排序是：

1. **换 self-hosted runner 到国内/香港节点** —— 一次性解决 B站、抖音、快手
2. **导出 cookie 塞进 Actions Secrets** —— 解决抖音、YouTube、微博、Instagram
3. **换 `yt-dlp-nightly`** —— 最省事，可能直接解决 YouTube

---

## 六、结论

"沙箱内抓不了国内平台"这个结论**已经不成立**——
TikTok 和小红书是实测跑通的证据，整条链路（排队→runner→commit→pull）是可用的。

剩下 B站、抖音、YouTube 视频三家的拦路石**不是网络出口，是平台风控**，
需要的是 cookie 或换 runner 地区，跟工具箱装得对不对没关系。
