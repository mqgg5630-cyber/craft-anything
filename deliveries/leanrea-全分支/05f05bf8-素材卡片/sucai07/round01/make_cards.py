# -*- coding: utf-8 -*-
"""
素材07 Round01 — 复刻图卡生成器 v2
主题：Claude Code 免费用（接入 DeepSeek/Kimi 等免费模型）
输出：10 张 1080x1920 资讯图卡 + 1 张总预览图
v2 修复：符号豆腐块(矢量绘制)、代码窗口中英文混排、第3张溢出
"""
import os, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
OUT = os.path.dirname(os.path.abspath(__file__))
FD = "/tmp/fonts"

def F(name, size):
    return ImageFont.truetype(os.path.join(FD, name), size)

BG_TOP = (11, 16, 32)
BG_BOT = (22, 27, 54)
ACCENT = (255, 122, 69)
CYAN = (54, 207, 201)
VIOLET = (149, 128, 255)
WHITE = (245, 247, 255)
GREY = (150, 158, 186)
PANEL = (255, 255, 255, 14)
PANEL_LINE = (255, 255, 255, 36)
GREEN = (82, 196, 126)
RED = (255, 95, 95)
YELLOW = (255, 200, 80)

def gradient_bg():
    img = Image.new("RGB", (W, H), BG_TOP)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        c = tuple(int(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOT))
        d.line([(0, y), (W, y)], fill=c)
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([W-520, -260, W+260, 520], fill=(40, 22, 10))
    gd.ellipse([-300, H-560, 420, H+220], fill=(8, 36, 40))
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    img = Image.blend(img, Image.blend(img, glow, 0.9), 0.55)
    d = ImageDraw.Draw(img)
    for yy in range(80, H, 72):
        for xx in range(60, W, 72):
            d.ellipse([xx, yy, xx+3, yy+3], fill=(34, 40, 66))
    return img

def overlay(img):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return ov, ImageDraw.Draw(ov)

def rr(d, box, r, fill=None, outline=None, width=2):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)

def wrap_cjk(text, font, maxw):
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur); cur = ""; continue
        if font.getlength(cur + ch) > maxw:
            lines.append(cur); cur = ch
        else:
            cur += ch
    if cur: lines.append(cur)
    return lines

# ---------- 矢量图标（替代缺字形符号） ----------
def icon_x(d, cx, cy, r, color, w=8):
    d.line([cx-r, cy-r, cx+r, cy+r], fill=color, width=w)
    d.line([cx-r, cy+r, cx+r, cy-r], fill=color, width=w)

def icon_check(d, cx, cy, r, color, w=9):
    d.line([cx-r, cy+r*0.1, cx-r*0.15, cy+r*0.85], fill=color, width=w)
    d.line([cx-r*0.15-3, cy+r*0.85, cx+r*1.05, cy-r*0.75], fill=color, width=w)

def icon_refresh(d, cx, cy, r, color, w=8):
    d.arc([cx-r, cy-r, cx+r, cy+r], start=-50, end=210, fill=color, width=w)
    ax, ay = cx + r*math.cos(math.radians(-50)), cy + r*math.sin(math.radians(-50))
    d.polygon([(ax-14, ay-16), (ax+18, ay-4), (ax-8, ay+16)], fill=color)

def icon_star(d, cx, cy, r, color):
    pts = []
    for i in range(10):
        ang = -math.pi/2 + i*math.pi/5
        rad = r if i % 2 == 0 else r*0.45
        pts.append((cx+rad*math.cos(ang), cy+rad*math.sin(ang)))
    d.polygon(pts, fill=color)

def icon_arrow_down(d, cx, cy, r, color, w=8):
    d.line([cx, cy-r, cx, cy+r*0.5], fill=color, width=w)
    d.polygon([(cx-r*0.6, cy+r*0.3), (cx+r*0.6, cy+r*0.3), (cx, cy+r)], fill=color)

# ---------- 中英文混排（代码窗口用） ----------
def draw_mixed(d, xy, text, fill, size=36, mono="JBMono-400.ttf", cjk="NotoSC-500.ttf"):
    x, y = xy
    fm, fc = F(mono, size), F(cjk, size)
    def is_cjk(ch): return ord(ch) > 0x2E7F
    run, runcjk = "", None
    def flush(x, run, runcjk):
        if not run: return x
        f = fc if runcjk else fm
        d.text((x, y + (2 if not runcjk else 0)), run, font=f, fill=fill)
        return x + f.getlength(run)
    for ch in text:
        c = is_cjk(ch)
        if runcjk is None or c == runcjk:
            run += ch; runcjk = c
        else:
            x = flush(x, run, runcjk); run, runcjk = ch, c
    flush(x, run, runcjk)

def header(d, idx, tag="白嫖 AI 编程系列"):
    rr(d, [60, 70, 310, 146], 38, fill=(255, 122, 69, 255))
    d.text((85, 88), f"第 {idx:02d} / 10 张", font=F("NotoSC-700.ttf", 38), fill=(20, 14, 10))
    tw = F("NotoSC-500.ttf", 34).getlength(tag) + 56
    rr(d, [W-60-tw, 74, W-60, 142], 34, outline=(54, 207, 201, 200), width=3)
    d.text((W-60-tw+28, 90), tag, font=F("NotoSC-500.ttf", 34), fill=CYAN)

def footer(d, idx):
    d.line([(60, H-150), (W-60, H-150)], fill=(255, 255, 255, 40), width=2)
    d.text((60, H-118), "一二和布布 · AI 工具分享", font=F("NotoSC-500.ttf", 36), fill=GREY)
    t = "#ClaudeCode  #免费AI"
    f = F("NotoSC-500.ttf", 34)
    d.text((W-60-f.getlength(t), H-116), t, font=f, fill=(255, 122, 69, 220))

def dots(d, x, y):
    for i, c in enumerate([RED, YELLOW, GREEN]):
        d.ellipse([x+i*44, y, x+i*44+24, y+24], fill=c)

def code_window(d, box, title, lines, fsize=34, lh=None):
    x0, y0, x1, y1 = box
    rr(d, box, 28, fill=(12, 15, 28, 240), outline=(255, 255, 255, 46), width=2)
    rr(d, [x0, y0, x1, y0+78], 28, fill=(26, 31, 52, 255))
    d.rectangle([x0, y0+50, x1, y0+78], fill=(26, 31, 52, 255))
    dots(d, x0+28, y0+27)
    draw_mixed(d, (x0+180, y0+22), title, GREY, size=30)
    yy = y0 + 110
    lh = lh or int(fsize*1.6)
    for color, txt in lines:
        draw_mixed(d, (x0+36, yy), txt, color, size=fsize)
        yy += lh

def big_title(d, y, lines, size=104, color=WHITE, accent_idx=None, accent_color=None):
    f = F("NotoSC-900.ttf", size)
    for i, ln in enumerate(lines):
        c = accent_color if (accent_idx is not None and i == accent_idx) else color
        d.text((60, y), ln, font=f, fill=c)
        y += int(size * 1.28)
    return y

def chip(d, x, y, text, fg, line, fsize=36):
    f = F("NotoSC-700.ttf", fsize)
    w = f.getlength(text) + 56
    rr(d, [x, y, x+w, y+fsize+36], (fsize+36)//2, outline=line, width=3)
    d.text((x+28, y+16), text, font=f, fill=fg)
    return x + w + 24

def bullet_panel(d, y, items, title=None, icon_color=ACCENT):
    x0, x1 = 60, W-60
    top_pad = 44
    yy_probe = top_pad + (90 if title else 0)
    f_item = F("NotoSC-500.ttf", 40)
    rows_h = 0
    wrapped = []
    for it in items:
        lns = wrap_cjk(it, f_item, x1-x0-160)
        wrapped.append(lns)
        rows_h += len(lns)*58 + 36
    h = yy_probe + rows_h + 16
    rr(d, [x0, y, x1, y+h], 32, fill=PANEL, outline=PANEL_LINE, width=2)
    yy = y + 44
    if title:
        d.text((x0+44, yy), title, font=F("NotoSC-700.ttf", 44), fill=CYAN)
        yy += 90
    for lns in wrapped:
        d.ellipse([x0+48, yy+16, x0+66, yy+34], fill=icon_color)
        for ln in lns:
            d.text((x0+96, yy), ln, font=f_item, fill=WHITE)
            yy += 58
        yy += 36
    return y + h

def save(img, ov, name):
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    img.save(os.path.join(OUT, name), quality=95)
    print("saved", name)

# ---------------- 卡片 01 封面 ----------------
def card01():
    img = gradient_bg(); ov, d = overlay(img)
    header(d, 1)
    y = 300
    x = chip(d, 60, y, "GitHub 开源神器", CYAN, (54,207,201,200))
    chip(d, x, y, "亲测有效", ACCENT, (255,122,69,200))
    y = big_title(d, y+120, ["Claude Code", "现在能永久", "「白嫖」了？"], size=128, accent_idx=2, accent_color=ACCENT)
    yy = y + 40
    rr(d, [60, yy, W-60, yy+330], 36, fill=(255,122,69,26), outline=(255,122,69,140), width=3)
    d.text((100, yy+48), "每月免费 Token 总额度", font=F("NotoSC-500.ttf", 44), fill=GREY)
    d.text((100, yy+124), "1,300,000,000+", font=F("JBMono-800.ttf", 110), fill=WHITE)
    d.text((100, yy+262), "约 13 亿 / 月（多平台免费额度合计）", font=F("NotoSC-500.ttf", 38), fill=CYAN)
    d.text((60, yy+410), "DeepSeek · Kimi · GLM · Qwen 全接入", font=F("NotoSC-700.ttf", 48), fill=WHITE)
    d.text((60, yy+490), "划到最后，手把手教你配置", font=F("NotoSC-500.ttf", 40), fill=GREY)
    icon_arrow_down(d, 60 + F("NotoSC-500.ttf", 40).getlength("划到最后，手把手教你配置") + 46, yy+516, 22, ACCENT)
    footer(d, 1); save(img, ov, "card_01_封面.png")

# ---------------- 卡片 02 痛点 ----------------
def card02():
    img = gradient_bg(); ov, d = overlay(img)
    header(d, 2)
    big_title(d, 260, ["先说痛点：", "AI 编程太烧钱"], size=110, accent_idx=1, accent_color=ACCENT)
    y = 600
    items = [
        ("Claude 官方订阅", "$20 ~ $200 / 月，重度使用照样限流"),
        ("按量付费 API", "跑一个项目，账单比咖啡还贵"),
        ("额度焦虑", "写到一半被掐断，思路全没了"),
    ]
    for t, s in items:
        rr(d, [60, y, W-60, y+200], 32, fill=PANEL, outline=PANEL_LINE, width=2)
        icon_x(d, 134, y+100, 26, RED)
        d.text((210, y+34), t, font=F("NotoSC-700.ttf", 48), fill=WHITE)
        d.text((210, y+110), s, font=F("NotoSC-500.ttf", 38), fill=GREY)
        y += 236
    y += 30
    rr(d, [60, y, W-60, y+170], 32, fill=(54,207,201,26), outline=(54,207,201,160), width=3)
    d.text((104, y+34), "但 Claude Code 本身是免费开源的", font=F("NotoSC-700.ttf", 44), fill=CYAN)
    d.text((104, y+104), "烧钱的只是背后的模型 —— 那就换模型！", font=F("NotoSC-500.ttf", 38), fill=WHITE)
    footer(d, 2); save(img, ov, "card_02_痛点.png")

# ---------------- 卡片 03 核心思路 ----------------
def card03():
    img = gradient_bg(); ov, d = overlay(img)
    header(d, 3)
    big_title(d, 250, ["核心思路", "一个公式讲明白"], size=96, accent_idx=0, accent_color=CYAN)
    y = 545
    blocks = [("免费大模型", "DeepSeek / Kimi / GLM…", CYAN), ("+",), ("Claude Code", "最强 CLI 编程智能体", ACCENT), ("=",), ("零成本 AI 编程", "体验不打折，账单归零", VIOLET)]
    for b in blocks:
        if len(b) == 1:
            f = F("NotoSC-900.ttf", 80)
            d.text(((W-f.getlength(b[0]))//2, y-6), b[0], font=f, fill=GREY)
            y += 96
            continue
        t, s, c = b
        rr(d, [100, y, W-100, y+150], 30, fill=(c[0], c[1], c[2], 28), outline=(c[0], c[1], c[2], 170), width=3)
        f = F("NotoSC-900.ttf", 54)
        d.text(((W-f.getlength(t))//2, y+22), t, font=f, fill=WHITE)
        f2 = F("NotoSC-500.ttf", 34)
        d.text(((W-f2.getlength(s))//2, y+94), s, font=f2, fill=GREY)
        y += 166
    y += 18
    bullet_panel(d, y, [
        "各大平台注册就送免费 Token 额度",
        "用「路由器」把请求转发给免费模型",
        "Claude Code 的工作流一点不变",
    ], title="为什么可行？")
    footer(d, 3); save(img, ov, "card_03_核心思路.png")

# ---------------- 卡片 04 工具 ----------------
def card04():
    img = gradient_bg(); ov, d = overlay(img)
    header(d, 4)
    big_title(d, 250, ["主角登场", "claude-code-router"], size=92, accent_idx=1, accent_color=ACCENT)
    y = 530
    rr(d, [60, y, W-60, y+430], 36, fill=(12,15,28,240), outline=(255,255,255,60), width=2)
    d.ellipse([100, y+44, 180, y+124], outline=WHITE, width=5)
    d.ellipse([118, y+62, 162, y+106], fill=WHITE)
    d.text((210, y+46), "musistudio /", font=F("JBMono-400.ttf", 40), fill=GREY)
    d.text((210, y+100), "claude-code-router", font=F("JBMono-700.ttf", 52), fill=WHITE)
    icon_star(d, 124, y+216, 26, YELLOW)
    d.text((170, y+190), "38k+ Stars", font=F("JBMono-700.ttf", 44), fill=YELLOW)
    d.text((470, y+194), "开源免费 · 持续更新", font=F("NotoSC-500.ttf", 40), fill=GREY)
    for i, ln in enumerate(["一个本地「模型路由器」：把 Claude Code 的", "请求转发到任意模型供应商，想用谁就用谁"]):
        d.text((100, y+280+i*58), ln, font=F("NotoSC-500.ttf", 38), fill=WHITE)
    y += 480
    bullet_panel(d, y, [
        "支持 DeepSeek / Kimi / GLM / Qwen 等",
        "按任务路由：默认·后台·思考·长上下文",
        "对话中 /model 一句话热切换模型",
    ], title="它能干什么？")
    footer(d, 4); save(img, ov, "card_04_工具.png")

# ---------------- 卡片 05 免费模型盘点 ----------------
def card05():
    img = gradient_bg(); ov, d = overlay(img)
    header(d, 5)
    big_title(d, 250, ["免费模型去哪薅？", "4 大平台盘点"], size=96, accent_idx=1, accent_color=CYAN)
    y = 540
    rows = [
        ("DeepSeek V3.2", "官方 API 白菜价，新户送免费额度", CYAN),
        ("Kimi K2", "月之暗面开放平台，注册送体验金", ACCENT),
        ("GLM-4.6", "智谱 BigModel，长期有免费模型位", VIOLET),
        ("Qwen3-Coder", "阿里百炼，新户大额免费 Token", GREEN),
    ]
    for name, desc, c in rows:
        rr(d, [60, y, W-60, y+210], 32, fill=PANEL, outline=PANEL_LINE, width=2)
        d.rectangle([60, y+24, 74, y+186], fill=c)
        d.text((120, y+34), name, font=F("JBMono-700.ttf", 48), fill=WHITE)
        d.text((120, y+118), desc, font=F("NotoSC-500.ttf", 38), fill=GREY)
        y += 246
    y += 24
    d.text((60, y), "＊免费额度以各平台最新政策为准，拿到 API Key 即可", font=F("NotoSC-500.ttf", 34), fill=GREY)
    footer(d, 5); save(img, ov, "card_05_免费模型.png")

# ---------------- 卡片 06 安装 ----------------
def card06():
    img = gradient_bg(); ov, d = overlay(img)
    header(d, 6)
    big_title(d, 250, ["上手第一步", "两行命令装好"], size=100, accent_idx=1, accent_color=ACCENT)
    code_window(d, [60, 560, W-60, 1185], "terminal - zsh", [
        (GREY,  "# 1. 安装 Claude Code"),
        (GREEN, "$ npm install -g \\"),
        (GREEN, "    @anthropic-ai/claude-code"),
        (WHITE, ""),
        (GREY,  "# 2. 安装路由器"),
        (CYAN,  "$ npm install -g \\"),
        (CYAN,  "    @musistudio/claude-code-router"),
        (WHITE, ""),
        (GREY,  "# 3. 用 ccr 启动，替代 claude"),
        (ACCENT,"$ ccr code"),
    ], fsize=36, lh=50)
    bullet_panel(d, 1225, [
        "需要 Node.js 18+ 环境",
        "ccr 是 claude-code-router 的命令入口",
        "以后写代码都用 ccr code 启动即可",
    ], title="注意事项")
    footer(d, 6); save(img, ov, "card_06_安装.png")

# ---------------- 卡片 07 配置 ----------------
def card07():
    img = gradient_bg(); ov, d = overlay(img)
    header(d, 7)
    big_title(d, 250, ["填上 API Key", "配置一次就好"], size=100, accent_idx=0, accent_color=CYAN)
    code_window(d, [60, 560, W-60, 1400], "~/.claude-code-router/config.json", [
        (WHITE, '{'),
        (CYAN,  '  "Providers": [{'),
        (WHITE, '    "name": "deepseek",'),
        (WHITE, '    "api_key": "sk-你的Key",'),
        (WHITE, '    "models": ["deepseek-chat"]'),
        (CYAN,  '  }, {'),
        (WHITE, '    "name": "kimi",'),
        (WHITE, '    "api_key": "sk-你的Key",'),
        (WHITE, '    "models": ["kimi-k2"]'),
        (CYAN,  '  }],'),
        (ACCENT,'  "Router": {'),
        (WHITE, '    "default": "deepseek,deepseek-chat",'),
        (WHITE, '    "longContext": "kimi,kimi-k2"'),
        (ACCENT,'  }'),
        (WHITE, '}'),
    ], fsize=34, lh=46)
    d.text((60, 1450), "把各平台领到的 Key 填进来，按场景分配模型", font=F("NotoSC-500.ttf", 40), fill=WHITE)
    d.text((60, 1520), "也可以运行 ccr ui 在网页里可视化配置", font=F("NotoSC-500.ttf", 40), fill=GREY)
    footer(d, 7); save(img, ov, "card_07_配置.png")

# ---------------- 卡片 08 备用切换 ----------------
def card08():
    img = gradient_bg(); ov, d = overlay(img)
    header(d, 8)
    big_title(d, 250, ["杀手级功能", "失败自动切换"], size=100, accent_idx=1, accent_color=ACCENT)
    y = 560
    steps = [
        ("模型 A：DeepSeek", "额度用光 / 请求失败", RED, "x"),
        ("自动切换", "路由器秒切备用线路", YELLOW, "r"),
        ("模型 B：Kimi 接管", "续上上下文，继续写码", GREEN, "v"),
    ]
    for t, s, c, icon in steps:
        rr(d, [60, y, W-60, y+200], 32, fill=PANEL, outline=(c[0], c[1], c[2], 170), width=3)
        d.ellipse([100, y+58, 184, y+142], fill=(c[0], c[1], c[2], 50), outline=c, width=4)
        cx, cy = 142, y+100
        if icon == "x": icon_x(d, cx, cy, 20, c)
        elif icon == "r": icon_refresh(d, cx, cy, 20, c)
        else: icon_check(d, cx, cy, 20, c)
        d.text((230, y+38), t, font=F("NotoSC-700.ttf", 48), fill=WHITE)
        d.text((230, y+114), s, font=F("NotoSC-500.ttf", 38), fill=GREY)
        y += 226
        if icon != "v":
            icon_arrow_down(d, W//2, y-12, 26, GREY)
            y += 46
    y += 30
    rr(d, [60, y, W-60, y+170], 32, fill=(149,128,255,28), outline=(149,128,255,170), width=3)
    d.text((104, y+32), "编程全程不中断", font=F("NotoSC-700.ttf", 46), fill=VIOLET)
    d.text((104, y+102), "多平台免费额度无缝接力，越用越香", font=F("NotoSC-500.ttf", 38), fill=WHITE)
    footer(d, 8); save(img, ov, "card_08_自动切换.png")

# ---------------- 卡片 09 实测 ----------------
def card09():
    img = gradient_bg(); ov, d = overlay(img)
    header(d, 9)
    big_title(d, 250, ["实测体验", "和官方一样顺手"], size=100, accent_idx=0, accent_color=CYAN)
    code_window(d, [60, 560, W-60, 1180], "ccr code — 会话中", [
        (ACCENT, "> 帮我写一个贪吃蛇小游戏"),
        (WHITE,  ""),
        (GREY,   "* 正在使用 deepseek-chat ..."),
        (GREEN,  "+ 创建 snake.html"),
        (GREEN,  "+ 创建 game.js (214 行)"),
        (GREEN,  "+ 本地预览已启动"),
        (WHITE,  ""),
        (GREY,   "本次消耗: 0 元 (免费额度)"),
        (CYAN,   "/model kimi,kimi-k2 · 随时换模型"),
    ], fsize=36, lh=52)
    bullet_panel(d, 1240, [
        "读写文件、跑命令、改 bug 全都能干",
        "日常任务免费模型完全够用",
        "复杂任务再切强模型，灵活省钱",
    ], title="体验结论")
    footer(d, 9); save(img, ov, "card_09_实测.png")

# ---------------- 卡片 10 总结 CTA ----------------
def card10():
    img = gradient_bg(); ov, d = overlay(img)
    header(d, 10)
    big_title(d, 250, ["三步总结", "现在就能用上"], size=100, accent_idx=1, accent_color=ACCENT)
    y = 560
    steps = [
        ("01", "各平台注册，领免费 API Key", CYAN),
        ("02", "装好 claude-code-router 填配置", ACCENT),
        ("03", "ccr code 启动，开写！", VIOLET),
    ]
    for n, t, c in steps:
        rr(d, [60, y, W-60, y+170], 32, fill=PANEL, outline=PANEL_LINE, width=2)
        d.text((104, y+36), n, font=F("JBMono-800.ttf", 84), fill=c)
        d.text((250, y+56), t, font=F("NotoSC-700.ttf", 46), fill=WHITE)
        y += 200
    y += 36
    rr(d, [60, y, W-60, y+320], 36, fill=(255,122,69,30), outline=(255,122,69,180), width=3)
    f = F("NotoSC-900.ttf", 64)
    t = "免费模型 + Claude Code"
    d.text(((W-f.getlength(t))//2, y+52), t, font=f, fill=WHITE)
    f2 = F("NotoSC-700.ttf", 52)
    t2 = "= 这波真的能白嫖"
    d.text(((W-f2.getlength(t2))//2, y+150), t2, font=f2, fill=ACCENT)
    f3 = F("NotoSC-500.ttf", 38)
    t3 = "关注我，下期拆解更多 AI 神器"
    d.text(((W-f3.getlength(t3))//2, y+240), t3, font=f3, fill=GREY)
    footer(d, 10); save(img, ov, "card_10_总结.png")

# ---------------- 总预览图 ----------------
def preview():
    cols, rows = 5, 2
    tw, th = 360, 640
    gap = 24
    pw = cols*tw + (cols+1)*gap
    ph = rows*th + (rows+1)*gap + 160
    pv = Image.new("RGB", (pw, ph), BG_TOP)
    d = ImageDraw.Draw(pv)
    d.text((gap, 36), "素材07 · Round01 预览 — Claude Code 免费用（10 张图卡）", font=F("NotoSC-700.ttf", 52), fill=WHITE)
    names = sorted(f for f in os.listdir(OUT) if f.startswith("card_") and f.endswith(".png"))
    for i, n in enumerate(names):
        im = Image.open(os.path.join(OUT, n)).resize((tw, th), Image.LANCZOS)
        x = gap + (i % cols) * (tw + gap)
        y = 160 + gap + (i // cols) * (th + gap)
        pv.paste(im, (x, y))
        d.rectangle([x, y, x+tw, y+th], outline=(255, 255, 255), width=2)
    pv.save(os.path.join(OUT, "preview_总预览图.png"), quality=92)
    print("saved preview")

if __name__ == "__main__":
    for fn in [card01, card02, card03, card04, card05, card06, card07, card08, card09, card10]:
        fn()
    preview()
    print("ALL DONE")
