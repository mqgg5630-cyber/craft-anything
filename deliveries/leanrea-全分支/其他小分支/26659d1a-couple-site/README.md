# 我们的小时光 · 情侣记录网站

一个可以白嫖部署、零依赖、数据留在自己手里的情侣记录站。做成了手绘纸张的质感——蜡笔涂鸦、贴纸、胶带、手写体日期，全部用 CSS 画出来，不加载任何外部字体或图床。

> 风格来自你自己的 Google Drive：`SKILL · 情侣复刻技能文件（scribble-couple）` 里那套「白纸 + 黑蜡笔双线 + 方宽脸 + 腮红 + 小红心」。插画按这套风格重新生成，界面把同一套语言搬到了排版上。

```
couple-site/
├── index.html              # 页面结构（不用改）
├── data/content.js         # ★ 只改这一个文件就能换成你们的故事
├── assets/
│   ├── style.css           # 样式
│   ├── app.js              # 交互（日期计算 / 灯箱 / 清单 / 小纸条 / 设置）
│   ├── art/                # 首页插画 + 相册示例图
│   └── photos/             # 放你们自己的照片
└── .nojekyll               # GitHub Pages 用
```

## 它有什么

- **首页**：在一起第几天（实时）、几年几个月零几天、今天的时钟、最近的一个纪念日倒计时
- **时光轴**：按时间排的故事卡，可配图，左右交替
- **相册**：拍照贴纸墙 + 灯箱，键盘 ← → 翻页，Esc 关闭
- **画风样张**：相册下面是 Drive 里 scribble-couple 的 6 张测试图，横滑查看（`samples` 数组，可删）
- **纪念日**：每年循环，自动算「还有几天」，当天会亮起来
- **一起做的事**：带进度条的清单，勾选状态存本地
- **小纸条**：贴在冰箱上的便利贴，可写可撕
- **改一改**：右上角抽屉里直接改名字 / 纪念日 / 城市 / 文案，立刻生效；还能一键导出 `content.js`
- 手机 / 平板自适应，支持「减少动态效果」偏好，可打印成 PDF

## 本地看效果

```sh
cd couple-site
python3 -m http.server 8080
# 打开 http://localhost:8080
```

直接双击 `index.html` 也能看，但建议用上面的方式（有些浏览器对 `file://` 有限制）。

## 三步改成你们的

1. 打开 `data/content.js`，把 `couple` 里的名字、`startDate`（在一起第一天）、城市、一句话改掉。
2. 把照片放进 `assets/photos/`，在 `photos` 数组里加一条：
   ```js
   { src: "assets/photos/2024-hokkaido.jpg", title: "北海道", date: "2024-12-30", note: "冷到手机关机" }
   ```
3. 改 `timeline`（时光轴）、`anniversaries`（纪念日）、`wishes`（清单）、`notes`（初始小纸条）。

改完刷新即可。**不想碰代码**也行：网页右上角「改一改」→ 保存到本机 → 「导出 content.js」→ 用它替换 `data/content.js`。

## 免费部署（都支持自定义域名、HTTPS）

### 1. GitHub Pages（最省事，推荐）

**网页两步（最稳）**：仓库 → **Settings → Pages** → Source 选 **Deploy from a branch** → Branch 选 `main`、目录选 **`/couple-site`** → Save。
一两分钟后地址就是 `https://<用户名>.github.io/<仓库名>/`。

或者用你自己的 `gh` 登录跑：

```sh
gh api -X POST repos/hukeying85-ux/leanrea/pages --input - <<'JSON'
{"source":{"branch":"main","path":"/couple-site"}}
JSON
```

> 注意：现在站点在功能分支 `arena/26659d1a-leanrea` 上，先把这个分支 PR 合进 `main`，Pages 才指向得到。也可以临时把 Branch 选成 `arena/26659d1a-leanrea`。
> 仓库里已经放了 `.nojekyll`，避免 Jekyll 处理静态文件。

默认加了 `robots.txt`（禁止收录），因为这是私人页面；想让搜索引擎抓到就删掉它。

> 私有仓库也能用 Pages（免费账号的私有仓库 Pages 需要 Pro；公开仓库免费）。如果只想自己看，见下面的「只在本地」。

### 2. Cloudflare Pages（国内访问通常比 GitHub 快）

1. Cloudflare Dashboard → Workers & Pages → Create → Pages → Connect to Git
2. 选仓库，**Build command 留空**，**Build output directory 填 `couple-site`**
3. Deploy。之后每次 push 自动更新，免费额度够用。

### 3. Vercel / Netlify

- Vercel：New Project → 选仓库 → Framework 选 **Other** → Root Directory 填 `couple-site` → Deploy
- Netlify：直接把 `couple-site` 文件夹拖到 https://app.netlify.com/drop

### 4. 只想自己看（最私密）

不上传任何地方：本地跑 `python3 -m http.server`，或者把文件夹放进 iCloud / 坚果云同步。所有「改一改」的内容、清单勾选、小纸条都只存在你自己的浏览器里。

## 隐私

- 没有后端、没有统计脚本、没有第三方请求（字体用系统字体，图标是内联 SVG）。
- 用户输入（小纸条、清单勾选、设置）只写进浏览器的 `localStorage`，换设备不会同步。
- 部署到公开链接时，页面本身是公开的。介意的话：仓库设为私有 + Cloudflare Pages，或者加一层简单的密码保护（Cloudflare Access 免费档即可）。

## 参考的开源方案

看过这些项目，思路和取舍如下——本站只借了「该有什么」，代码是从零写的零依赖静态站：

| 项目 | 许可 | 借了什么 |
|---|---|---|
| [CoderSJ418/our-valley](https://github.com/CoderSJ418/our-valley) | MIT | 星露谷风格、零依赖 HTML/CSS/JS 模板的「一个文件夹就能部署」思路 |
| [VV0611/Couple-Anniversary-DIY](https://github.com/VV0611/Couple-Anniversary-DIY) | MIT | 纪念日倒计时的交互与无需写代码的定位 |
| [liupeng-zhangju/love-station](https://github.com/liupeng-zhangju/love-station) | MIT | 前后端分离的完整功能清单（本站故意去掉后端） |
| [NoEggEgg/love-memorial-website](https://github.com/NoEggEgg/love-memorial-website) | — | 纯前端 + 浏览器本地存储的隐私取舍 |
| [Baoziiii1228/couple-space](https://github.com/Baoziiii1228/couple-space) | — | 功能分区（相册 / 日记 / 纪念日 / 清单 / 留言）的参考 |
| [sun626609827/photo-next](https://github.com/sun626609827/photo-next) | — | 相册优先的产品结构 |

没有引入它们的代码或依赖，所以本站不存在许可证传染问题；上面的许可是各自仓库的，使用前请自行核对。

## 素材

- 5 张插画由 AI 按 `scribble-couple` 风格生成（蜡笔双线 / 方宽脸 / 黑色圆角眼 / 腮红 / 小红心 / 右下签名），放在 `assets/art/`，可直接替换。
- 界面的纸纹是内联 SVG `feTurbulence`，没有外部图片。

## 改样式

配色在 `assets/style.css` 顶部 `:root`：

```css
--paper: #fbf7f0;   /* 纸 */
--ink:   #211c18;   /* 墨 */
--red:   #e4573d;   /* 蜡笔红 */
--sun:   #f2c14e;   /* 暖黄 */
--sky:   #a9c3d9;   /* 淡蓝 */
```

想更「干净现代」，把 `--radius-hand*` 改成 `12px`、去掉卡片旋转（`transform: rotate(...)`）就是另一套气质。

## License

代码 MIT。`assets/art/` 里的插画可随站点一起使用，替换成你们的照片时请自行确认肖像权。
