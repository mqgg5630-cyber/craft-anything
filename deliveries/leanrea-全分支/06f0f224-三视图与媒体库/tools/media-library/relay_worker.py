#!/usr/bin/env python3
"""
relay_worker.py — runs INSIDE the GitHub Actions runner (unrestricted egress).

For every URL in .mediaqueue/urls.txt it tries, in order:
  1. yt-dlp          (video-first: YouTube / B站 / 抖音 / 快手 / TikTok / IG)
  2. gallery-dl      (album-first: Instagram / Pinterest / 微博 / TikTok)
  3. xhs-dump        (小红书: yt-dlp --dump-single-json 取原图列表)
  4. html-scrape     (last resort: pull every CDN image URL out of the page)

Results land in media-raw/<云盘目录名>/<slug>/ with a meta.json; a summary is
written to media-raw/_LAST_RUN.md

Exit code is always 0 — one platform failing must not cancel the others.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "media-raw")
QUEUE = os.path.join(ROOT, ".mediaqueue", "urls.txt")

PLATFORM_OF = [
    ("01_小红书素材", ["xiaohongshu.com", "xhscdn.com"]),
    ("02_抖音素材", ["douyin.com", "iesdouyin.com", "douyinpic.com", "douyinvod.com"]),
    ("03_YouTube素材", ["youtube.com", "youtu.be"]),
    ("05_B站素材", ["bilibili.com"]),
    ("06_快手素材", ["kuaishou.com", "chenzhongtech.com"]),
    ("07_TikTok素材", ["tiktok.com"]),
    ("08_Instagram素材", ["instagram.com", "cdninstagram.com"]),
    ("04_其他平台素材", []),
]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

IMG_CDN = re.compile(
    r"https?://[^\s\"'\\<>]+?\.(?:jpg|jpeg|png|webp)(?:\?[^\s\"'\\<>]*)?", re.I)

# 完整浏览器请求头：B站那层 WAF 认的是 sec-ch-ua / sec-fetch-* 这套，
# 光有 User-Agent 会被判成脚本直接 412
BROWSER_H = {
    "User-Agent": UA,
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,image/apng,*/*;q=0.8"),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


def platform_of(url):
    low = url.lower()
    for folder, keys in PLATFORM_OF:
        if any(k in low for k in keys):
            return folder
    return "04_其他平台素材"


def slug_of(url):
    m = re.search(r"/(?:video|explore|p|reel|status|note)/([A-Za-z0-9_-]+)", url)
    return m.group(1) if m else hashlib.sha1(url.encode()).hexdigest()[:12]


def run(cmd, timeout=300):
    """返回 (rc, stdout, stderr)。"""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout or "", p.stderr or ""
    except Exception as e:
        return 99, "", f"{type(e).__name__}: {e}"


MEDIA_EXT = {".mp4", ".m4v", ".webm", ".mov", ".mkv", ".flv", ".avi",
             ".m4a", ".mp3", ".aac", ".opus", ".flac"}


def is_media(name):
    return os.path.splitext(name)[1].lower() in MEDIA_EXT


# cookie 注入：内容走 GitHub Actions Secrets，按域名挂给 yt-dlp / gallery-dl
COOKIE_ENV = {
    "douyin.com": "COOKIES_DOUYIN",
    "youtube.com": "COOKIES_YOUTUBE",
    "youtu.be": "COOKIES_YOUTUBE",
    "bilibili.com": "COOKIES_BILIBILI",
    "xiaohongshu.com": "COOKIES_XHS",
    "instagram.com": "COOKIES_INSTAGRAM",
    "weibo.com": "COOKIES_WEIBO",
    "kuaishou.com": "COOKIES_KUAISHOU",
}


def write_cookies_file(domain, pairs, out):
    """pairs: dict|list[tuple] -> Netscape 格式。"""
    if not pairs:
        return None
    items = pairs.items() if isinstance(pairs, dict) else pairs
    path = os.path.join(out, "_cookies.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Netscape HTTP Cookie File\n")
        for k, v in items:
            f.write(f".{domain.lstrip('.')}\tTRUE\t/\tFALSE\t0\t{k}\t{v}\n")
    return path


def cookies_for(url, out):
    """按 URL 域名取 cookie 文件（Secrets 优先，其次官方指纹自举）。"""
    low = url.lower()
    for dom, envname in COOKIE_ENV.items():
        if dom in low:
            raw = os.environ.get(envname, "").strip()
            if raw:
                pairs = []
                for part in raw.replace("\n", ";").split(";"):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        pairs.append((k.strip(), v.strip()))
                p = write_cookies_file(dom, pairs, out)
                if p:
                    return p
    if "bilibili.com" in low:
        # B站对机房 IP 返回 412；带上官方接口发的 buvid3/buvid4 指纹可解
        try:
            r = requests.get("https://api.bilibili.com/x/frontend/finger/spi",
                             headers={"User-Agent": UA,
                                      "Referer": "https://www.bilibili.com/"}, timeout=30)
            d = r.json().get("data") or {}
            if d.get("b_3"):
                return write_cookies_file("bilibili.com",
                                          [("buvid3", d["b_3"]),
                                           ("buvid4", d.get("b_4", "")),
                                           ("b_nut", "100")], out)
        except Exception:
            pass
    return None


def list_files_recursive(root):
    out = []
    for d, _, fs in os.walk(root):
        for f in fs:
            if f.endswith((".part", ".ytdl", ".json")) and f != "meta.json":
                continue
            out.append(os.path.relpath(os.path.join(d, f), root))
    return sorted(set(out))


# --------------------------------------------------------------------------
# 0. cookie 自举：抖音/微博这类只要「新鲜匿名 cookie」，不一定要登录态
# --------------------------------------------------------------------------
def bootstrap_cookies(url, out):
    try:
        s = requests.Session()
        s.headers.update({"User-Agent": UA})
        host = re.match(r"https?://([^/]+)", url).group(1)
        r = s.get(url, timeout=30)
        cookies = s.cookies.get_dict()
        # 从 Set-Cookie 里再捞一遍（session 有时不收 http-only 之外的）
        for m in re.finditer(r"([^=;\s]+)=([^;]*);", "\n".join(r.headers.get_all("set-cookie", []))):
            cookies.setdefault(m.group(1), m.group(2))
        if not cookies:
            return None
        path = os.path.join(out, "_cookies.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Netscape HTTP Cookie File\n")
            for k, v in cookies.items():
                f.write(f"{host}\tTRUE\t/\tFALSE\t0\t{k}\t{v}\n")
        return path
    except Exception:
        return None


# --------------------------------------------------------------------------
# 1. yt-dlp
# --------------------------------------------------------------------------
# 优先用 nightly：YouTube 的 extractor 每周都在被修，正式版经常跟不上
YT_BIN = shutil.which("yt-dlp-nightly") or shutil.which("yt-dlp") or "yt-dlp"

YT_BASE = [YT_BIN, "--no-warnings", "--no-playlist", "--ignore-errors",
           "--no-color", "--user-agent", UA, "--referer", "https://www.google.com/",
           "--write-info-json", "--write-thumbnail", "--convert-thumbnails", "jpg",
           "--retries", "5", "--socket-timeout", "30"]

FORMATS = [
    "bv*[height<=480]+ba/b[height<=480]",   # 首选：480p 音视频分离后合并
    "18/22/43/b",                            # YouTube 传统渐进式单文件（最抗风控）
    "b",                                     # 退一步：最好的单文件
    "bv*+ba/b",                              # 再退：不管分辨率
    "worst",                                 # 保底
]


def try_ytdlp(url, out):
    logs = []
    cookie_file = cookies_for(url, out)
    if not cookie_file and any(k in url for k in ("douyin.com", "weibo.com")):
        cookie_file = bootstrap_cookies(url, out)
    logs.append(f"cookies: {cookie_file or 'none'}")

    for i, fmt in enumerate(FORMATS):
        cmd = list(YT_BASE) + ["-f", fmt, "--merge-output-format", "mp4",
                               "-o", os.path.join(out, "%(title).50s_%(id)s.%(ext)s"), url]
        if cookie_file:
            cmd += ["--cookies", cookie_file]
        if "youtube.com" in url or "youtu.be" in url:
            # 轮换 player client，绕过「Requested format is not available」
            clients = ["android_vr", "web_safari,mweb", "ios,mweb",
                       "tv,web_embedded", "default,-web_safari"]
            extra = f"youtube:player_client={clients[i % len(clients)]}"
            if i >= len(clients):
                # 再退一步：接受缺 PO token 的格式，有时候能直接下下来
                extra += ";formats=missing_pot"
            cmd += ["--extractor-args", extra]
        rc, so, se = run(cmd, timeout=1200)
        logs.append(f"-f {fmt} -> rc={rc} {se.strip()[-200:]}")
        files = [f for f in list_files_recursive(out)
                 if not f.startswith("_") and f != "meta.json"]
        # 缩略图不算成功：--write-thumbnail 总会写，会把失败伪装成成功
        if [f for f in files if is_media(f)]:
            return True, "\n".join(logs), files
    return False, "\n".join(logs), []


# --------------------------------------------------------------------------
# 2. gallery-dl
# --------------------------------------------------------------------------
def try_gallerydl(url, out):
    rc, so, se = run(["gallery-dl", "--no-colors", "--dest", out, url], timeout=1200)
    files = [f for f in list_files_recursive(out) if not f.startswith("_") and f != "meta.json"]
    return (rc == 0 and bool(files)), f"rc={rc} {se.strip()[-300:]}", files


# --------------------------------------------------------------------------
# 3. 小红书专用：yt-dlp 能解析页面，只是图片笔记没有 video format
# --------------------------------------------------------------------------
def try_xhs_dump(url, out):
    urls = []

    # A. yt-dlp dump（视频笔记能 dump 出来；图片笔记它会直接报错）
    rc, so, se = run([YT_BIN, "--no-warnings", "--no-playlist", "--user-agent", UA,
                      "--dump-single-json", url], timeout=180)
    if rc == 0 and so.strip():
        try:
            data = json.loads(so)
            for t in data.get("thumbnails") or []:
                u = t.get("url") if isinstance(t, dict) else t
                if u:
                    urls.append(u)
            if not urls and data.get("thumbnail"):
                urls.append(data["thumbnail"])
        except Exception:
            pass

    # B. 直接解页面里的 __INITIAL_STATE__，拿 imageList（图片笔记走这条）
    if not urls:
        try:
            r = requests.get(url, headers={"User-Agent": UA,
                                           "Accept-Language": "zh-CN,zh;q=0.9"}, timeout=45)
            html = r.text.replace("\\u002F", "/").replace("\\/", "/")
            for key in ("urlDefault", "urlPre", "url"):
                urls += re.findall(rf'"{key}"\s*:\s*"(https?:[^"]+?)"', html)
            urls = [u for u in urls if "xhscdn" in u or "xiaohongshu" in u] or urls
        except Exception as e:
            if not urls:
                return False, f"dump rc={rc} {se.strip()[-160:]} | page: {type(e).__name__}", []

    if not urls:
        return False, f"dump rc={rc} {se.strip()[-160:]} | no image urls in page", []

    cleaned, seen = [], set()
    for u in urls:
        # 去掉小红书的降质后缀，拿原始大图
        u = re.sub(r"!nd_dft_\w+", "", u)
        u = re.sub(r"\?imageView2/.*$", "", u).replace("\\/", "/")
        if u not in seen:
            seen.add(u)
            cleaned.append(u)

    got = []
    for i, u in enumerate(cleaned[:30]):
        try:
            r = requests.get(u, headers={"User-Agent": UA, "Referer": "https://www.xiaohongshu.com/"},
                             timeout=60)
            if r.status_code == 200 and len(r.content) > 10000:
                ext = ".jpg" if "jpeg" in u.lower() or "jpg" in u.lower() else (
                    ".png" if "png" in u.lower() else ".webp")
                p = os.path.join(out, f"xhs_{i+1:02d}{ext}")
                open(p, "wb").write(r.content)
                got.append(os.path.basename(p))
        except Exception:
            continue
        time.sleep(0.3)
    return bool(got), f"dumped {len(cleaned)} urls, saved {len(got)}", got


# --------------------------------------------------------------------------
# 3.5 B站专用：网页端 412（WAF），改走官方 web-interface / playurl 接口
# --------------------------------------------------------------------------
def try_bilibili_api(url, out):
    bv = re.search(r"(BV[0-9A-Za-z]+)", url)
    if not bv:
        return False, "no bvid", []
    bvid = bv.group(1)
    h = dict(BROWSER_H, Referer="https://www.bilibili.com/",
             Origin="https://www.bilibili.com")
    # 多入口轮试：web 接口 / app 接口 / wbi 前的老接口
    endpoints = [
        f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
        f"https://app.bilibili.com/x/v2/view?bvid={bvid}&build=7240300&mobi_app=android",
        f"https://api.bilibili.com/view?type=bvid&bvid={bvid}",
    ]
    v = None
    diag = []
    for ep in endpoints:
        try:
            r = requests.get(ep, headers=h, timeout=30)
            try:
                j = r.json()
            except Exception:
                diag.append(f"{ep.split('/')[2]}: HTTP {r.status_code} non-json")
                continue
            if j.get("code") == 0 and (j.get("data") or {}).get("cid"):
                v = j
                break
            diag.append(f"{ep.split('/')[2]}: code={j.get('code')}")
        except Exception as e:
            diag.append(f"{ep.split('/')[2]}: {type(e).__name__}")
    if not v:
        return False, " | ".join(diag) or "all endpoints blocked", []
    try:
        cid = v["data"]["cid"]
        title = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", v["data"]["title"])[:40]
    except Exception as e:
        return False, f"parse: {e}", []

    logs = [f"bvid={bvid} cid={cid}"]
    for qn, plat in ((32, "html5"), (16, "html5"), (64, "pc")):
        try:
            p = requests.get(
                "https://api.bilibili.com/x/player/playurl",
                params={"bvid": bvid, "cid": cid, "qn": qn, "otype": "json",
                        "fnver": 0, "fnval": 16, "fourk": 1, "platform": plat},
                headers=h, timeout=30).json()
            if p.get("code") != 0:
                logs.append(f"qn{qn}/{plat}: code={p.get('code')}")
                continue
            d = p["data"]
            srcs = []
            if d.get("dash"):
                srcs.append(("v.m4s", [x["baseUrl"] for x in d["dash"]["video"]]))
                srcs.append(("a.m4s", [x["baseUrl"] for x in d["dash"].get("audio", [])]))
            elif d.get("durl"):
                srcs.append(("v.flv", [d["durl"][0]["url"]]))
            if not srcs:
                logs.append(f"qn{qn}/{plat}: no stream")
                continue

            saved = []
            for fname, urls in srcs:
                if not urls:
                    continue
                r = requests.get(urls[0], headers={**h, "Range": "bytes=0-"}, timeout=180, stream=True)
                if r.status_code in (200, 206):
                    pth = os.path.join(out, fname)
                    with open(pth, "wb") as f:
                        for chunk in r.iter_content(1 << 20):
                            f.write(chunk)
                    saved.append(pth)

            final = os.path.join(out, f"{title}_{bvid}.mp4")
            if len(saved) == 2:
                run(["ffmpeg", "-y", "-loglevel", "error", "-i", saved[0], "-i", saved[1],
                     "-c", "copy", final], timeout=600)
            elif saved:
                run(["ffmpeg", "-y", "-loglevel", "error", "-i", saved[0], "-c", "copy", final],
                    timeout=600)
            if os.path.exists(final) and os.path.getsize(final) > 50000:
                for s in saved:
                    try:
                        os.remove(s)
                    except OSError:
                        pass
                return True, "; ".join(logs), [os.path.basename(final)]
            logs.append(f"qn{qn}/{plat}: mux produced nothing")
        except Exception as e:
            logs.append(f"qn{qn}/{plat}: {type(e).__name__}: {e}")
    return False, "; ".join(logs), []


# --------------------------------------------------------------------------
# 3.6 抖音专用：yt-dlp 要 cookie，这里走公开的 iteminfo 接口拿无水印地址
# --------------------------------------------------------------------------
def try_douyin_api(url, out):
    vid = re.search(r"/video/(\d+)", url) or re.search(r"(\d{15,})", url)
    if not vid:
        return False, "no video id", []
    vid = vid.group(1)
    h = {"User-Agent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
                        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"),
         "Referer": "https://www.douyin.com/"}
    apis = [
        f"https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids={vid}",
        f"https://www.iesdouyin.com/share/video/{vid}/?region=CN&mid=0",
    ]
    data, diag = None, []
    for a in apis:
        try:
            r = requests.get(a, headers=h, timeout=30)
            try:
                j = r.json()
            except Exception:
                diag.append(f"{a.split('/')[2]}: HTTP {r.status_code} non-json {r.text[:100]!r}")
                continue
            if j.get("item_list"):
                data = j
                break
            diag.append(f"{a.split('/')[2]}: keys={list(j)[:5]} status_code={j.get('status_code')}")
        except Exception as e:
            diag.append(f"{a.split('/')[2]}: {type(e).__name__}: {e}")
    if not data:
        return False, " | ".join(diag) or "no item_list", []

    item = data["item_list"][0]
    got = []
    # 图文
    for i, im in enumerate(item.get("images") or []):
        for u in im.get("url_list", [])[:1]:
            try:
                rr = requests.get(u, headers=h, timeout=60)
                if rr.status_code == 200 and len(rr.content) > 10000:
                    p = os.path.join(out, f"douyin_{i+1:02d}.jpg")
                    open(p, "wb").write(rr.content)
                    got.append(os.path.basename(p))
            except Exception:
                continue
    # 视频：playwm -> play 去掉水印
    if not got:
        for u in item.get("video", {}).get("play_addr", {}).get("url_list", []):
            u = u.replace("/playwm/", "/play/").replace("/play/", "/play/")
            try:
                rr = requests.get(u, headers={**h, "Range": "bytes=0-"}, timeout=180, stream=True)
                if rr.status_code in (200, 206):
                    p = os.path.join(out, f"douyin_{vid}.mp4")
                    with open(p, "wb") as f:
                        for c in rr.iter_content(1 << 20):
                            f.write(c)
                    if os.path.getsize(p) > 50000:
                        got.append(os.path.basename(p))
                        break
            except Exception:
                continue
    return bool(got), f"iteminfo ok (images={len(item.get('images') or [])})", got


# --------------------------------------------------------------------------
# 3.6b 抖音图文笔记专用：yt-dlp/gallery-dl 都不认 /note/ 链接，桌面页 HTML 里
#      也没有图（图片靠 JS 渲染）。这里按「移动端分享页 → RENDER_DATA /
#      _ROUTER_DATA → 第三方解析 API」三级兜底，专门啃图文笔记。
# --------------------------------------------------------------------------
MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 "
             "Mobile/15E148 Safari/604.1")


def _json_blobs(html):
    """把页面里 RENDER_DATA / _ROUTER_DATA / __INITIAL_STATE__ 抠成 dict。"""
    from urllib.parse import unquote
    blobs = []
    pats = [
        r'<script[^>]*id="RENDER_DATA"[^>]*>(.*?)</script>',
        r'window\._ROUTER_DATA\s*=\s*(\{.*?\})\s*;?\s*</script>',
        r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;?\s*</script>',
        r'window\._SSR_DATA\s*=\s*(\{.*?\})\s*;?\s*</script>',
    ]
    for pat in pats:
        for m in re.findall(pat, html, re.S):
            for cand in (m, unquote(m)):
                cand = cand.strip()
                if not cand.startswith("{"):
                    continue
                try:
                    blobs.append(json.loads(cand))
                    break
                except Exception:
                    continue
    return blobs


def _walk_image_urls(node, acc):
    """深度遍历 JSON，收集所有 douyinpic 图片地址（去水印原图优先）。"""
    if isinstance(node, dict):
        for v in node.values():
            _walk_image_urls(v, acc)
    elif isinstance(node, list):
        for v in node:
            _walk_image_urls(v, acc)
    elif isinstance(node, str):
        if "douyinpic.com" in node and re.search(r"~noop|aweme-images|\.(jpg|jpeg|webp|png)", node, re.I):
            acc.append(node)


def _canon(u):
    """同一张图的多种 tplv 变体归一到同一 key。"""
    m = re.search(r"/tos-cn-[^/]+/([^~?]+)", u)
    return m.group(1) if m else u.split("?")[0]


def _variants(u):
    """优先要无水印原图：~noop.jpeg / ~tplv-...:q75.webp 都试一遍。"""
    base = re.sub(r"~[^/?#]+$", "", u.split("?")[0])
    base = base.split("~")[0]
    out = []
    for suffix in ("~noop.jpeg", "~noop.webp", "~tplv-dy-aweme-images:q75.webp"):
        out.append(base + suffix + "?from=327834062")
    return out


def _download_images(urls, out, referer="https://www.douyin.com/"):
    h = {"User-Agent": MOBILE_UA, "Referer": referer,
         "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"}
    got = []
    for i, u in enumerate(urls[:20]):
        for cand in _variants(u):
            try:
                rr = requests.get(cand, headers=h, timeout=45)
                if rr.status_code == 200 and len(rr.content) > 8000:
                    ext = ".jpg"
                    if cand.endswith(".webp") or b"WEBP" in rr.content[:16]:
                        ext = ".webp"
                    p = os.path.join(out, f"douyin_{i+1:02d}{ext}")
                    open(p, "wb").write(rr.content)
                    got.append(os.path.basename(p))
                    break
            except Exception:
                continue
        time.sleep(0.25)
    return got


def try_direct_media(url, out):
    """直链视频（douyinvod / amemv / 任意带 mime_type=video_mp4 的地址）。
    验证：>200KB 且头部含 ftyp / EBML 魔数。"""
    aid = re.search(r"item_id=(\d{15,})", url)
    name = f"douyin_{aid.group(1)}.mp4" if aid else "douyin_video.mp4"
    try:
        rr = requests.get(url, headers={"User-Agent": MOBILE_UA,
                                        "Referer": "https://www.douyin.com/"},
                          timeout=300, stream=True, allow_redirects=True)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}", []
    ctype = (rr.headers.get("Content-Type") or "").lower()
    if rr.status_code not in (200, 206) or "text" in ctype or "json" in ctype:
        return False, f"HTTP {rr.status_code} {ctype[:24]}", []
    p = os.path.join(out, name)
    with open(p, "wb") as f:
        for c in rr.iter_content(1 << 20):
            f.write(c)
    size = os.path.getsize(p)
    head = open(p, "rb").read(32)
    if size > 200_000 and (b"ftyp" in head[:16] or head[:4] == b"\x1aE\xdf\xa3"):
        return True, f"saved {size/1048576:.2f} MB ({ctype})", [name]
    os.remove(p)
    return False, f"not a video ({size}B {ctype[:24]})", []


def try_direct_image(url, out):
    """队列里直接给 CDN 图片直链时用（抖音签名直链有效期约 1 个月）。
    只认「下下来真的是图片」——按魔数判断，不看扩展名。"""
    if not re.search(r"\.(?:jpg|jpeg|png|webp)(?:\?|$)", url, re.I):
        return False, "not an image url", []
    got = []
    # 签名直链必须原样请求（去掉 x-signature 就 403），原图变体只作补充
    for i, cand in enumerate([url] + (_variants(url) or [])):
        try:
            rr = requests.get(cand, headers={"User-Agent": MOBILE_UA,
                                             "Referer": "https://www.douyin.com/",
                                             "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"},
                              timeout=60)
        except Exception as e:
            if i == 0:
                return False, f"{type(e).__name__}: {e}", []
            continue
        head = rr.content[:16]
        if rr.status_code == 200 and len(rr.content) > 8000 and (
                head[:3] == b"\xff\xd8\xff" or head[:4] == b"\x89PNG"
                or (head[:4] == b"RIFF" and rr.content[8:12] == b"WEBP")):
            ext = ".jpg" if head[:3] == b"\xff\xd8\xff" else (
                ".png" if head[:4] == b"\x89PNG" else ".webp")
            slug = re.sub(r"[^A-Za-z0-9]+", "", _canon(url))[:14] or "img"
            p = os.path.join(out, f"frame_{slug}{ext}")
            open(p, "wb").write(rr.content)
            got.append(os.path.basename(p))
            break
    return bool(got), f"saved {len(got)} direct image(s)", got


def _douyin_play_candidates(html):
    """从任何抖音页面 HTML 里刮播放地址：og:video / url_list / douyinvod / uri。"""
    html = (html.replace("\\u002F", "/").replace("\\/", "/")
                .replace("\\u0026", "&").replace("&amp;", "&"))
    out = []
    # 1) 任意 CDN 视频直链
    out += re.findall(r'https?://[^"\s\\<>]*?(?:douyinvod|zjcdn|snssdk|amemv|bytecdn|ixigua|\\.mp4)[^"\s\\<>]*', html)
    # 2) og:video / content 顺序任意
    for tag in re.findall(r'<meta[^>]*og:video[^>]*>', html):
        out += re.findall(r'content="([^"]+)"', tag)
    # 3) play_addr 之后 1500 字内的所有 http 地址
    for mt in re.finditer(r'"(?:play_addr|play_addr_h264|download_addr|playApi)"', html):
        seg = html[mt.end(): mt.end() + 1500]
        out += re.findall(r'https?://[^"\s\\<>]+', seg)
    # 4) uri -> 官方 play 接口
    for uri in set(re.findall(r'"uri"\s*:\s*"(v[0-9a-zA-Z]{10,})"', html)) | \
               set(re.findall(r'video_id=(v[0-9a-zA-Z]{10,})', html)):
        for ratio in ("1080p", "720p"):
            out.append(f"https://aweme.snssdk.com/aweme/v1/play/?video_id={uri}&ratio={ratio}&line=0")
    seen, uniq = set(), []
    for u in out:
        u = u.strip().strip('"')
        if u.startswith("http") and u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def try_douyin_video(url, out):
    """/video/ 专用：分享页/详情页刮播放地址 -> Range 拉 mp4（ftyp 魔数校验）。"""
    m = re.search(r"/(?:video|note)/(\d{15,})", url) or re.search(r"(\d{15,})", url)
    if not m:
        return False, "no aweme id", []
    aid = m.group(1)
    h_html = {"User-Agent": MOBILE_UA, "Accept-Language": "zh-CN,zh;q=0.9",
              "Referer": "https://www.douyin.com/"}
    cands, diag, seen_pages = [], [], set()
    for pg in (f"https://www.iesdouyin.com/share/video/{aid}/?region=CN&mid=0",
               f"https://www.douyin.com/video/{aid}",
               f"https://m.douyin.com/share/video/{aid}"):
        try:
            r = requests.get(pg, headers=h_html, timeout=45)
        except Exception as e:
            diag.append(f"{pg.split('/')[2]}: {type(e).__name__}")
            continue
        found = _douyin_play_candidates(r.text or "")
        diag.append(f"{pg.split('/')[2]}: HTTP {r.status_code} len={len(r.text or '')} urls={len(found)}")
        for u in found:
            if u not in seen_pages:
                seen_pages.add(u)
                cands.append(u)

    for u in cands[:10]:
        try:
            rr = requests.get(u, headers={"User-Agent": MOBILE_UA,
                                          "Referer": "https://www.douyin.com/"},
                              timeout=240, stream=True, allow_redirects=True)
        except Exception as e:
            diag.append(f"dl {u[:40]}: {type(e).__name__}")
            continue
        ctype = (rr.headers.get("Content-Type") or "").lower()
        if rr.status_code not in (200, 206) or "text" in ctype or "json" in ctype:
            diag.append(f"dl {u[:40]}: HTTP {rr.status_code} {ctype[:18]}")
            continue
        p = os.path.join(out, f"douyin_{aid}.mp4")
        with open(p, "wb") as f:
            for c in rr.iter_content(1 << 20):
                f.write(c)
        size = os.path.getsize(p)
        head = open(p, "rb").read(32)
        if size > 200_000 and (b"ftyp" in head[:16] or head[:4] == b"\x1aE\xdf\xa3"):
            return True, f"saved {size/1048576:.2f} MB; " + "; ".join(diag), [os.path.basename(p)]
        os.remove(p)
        diag.append(f"dl {u[:40]}: not video ({size}B {ctype[:18]})")
    return False, "; ".join(diag) or "no play url", []


PUBLIC_PARSERS = [
    "https://api.xingzhige.com/API/douyin/?url={}",
    "https://api.kxzjoker.cn/api/dy?url={}",
    "https://api.52vmy.cn/api/video/dy?url={}",
    "https://api.pearktrue.cn/api/video/douyin/?url={}",
    "https://api.suyanw.cn/api/dy.php?url={}",
    "https://api.douyin.wtf/api/hybrid/video_data?url={}&minimal=false",
]


def try_public_parsers(url, out):
    """公共解析站兜底：它们大多走 app 签名接口，能绕开数据中心 IP 的 SSR 500。"""
    from urllib.parse import quote
    diag, cands = [], []
    for tpl in PUBLIC_PARSERS:
        host = tpl.split("/")[2]
        try:
            r = requests.get(tpl.format(quote(url, safe="")),
                             headers={"User-Agent": UA, "Accept": "application/json, */*"},
                             timeout=45)
        except Exception as e:
            diag.append(f"{host}: {type(e).__name__}")
            continue
        txt = r.text or ""
        if r.status_code != 200:
            diag.append(f"{host}: HTTP {r.status_code}")
            continue
        found = re.findall(r'https?://[^"\s\\]+(?:douyinvod|zjcdn|\.mp4)[^"\s\\]*', txt)
        found = [f.replace("\\u0026", "&").replace("\\/", "/") for f in found]
        if not found:
            diag.append(f"{host}: 200 但无直链 ({txt[:60]!r})")
            continue
        diag.append(f"{host}: {len(found)} 直链")
        cands += found

    aid = re.search(r"(\d{15,})", url)
    for u in cands[:6]:
        try:
            rr = requests.get(u, headers={"User-Agent": MOBILE_UA,
                                          "Referer": "https://www.douyin.com/"},
                              timeout=240, stream=True)
        except Exception as e:
            diag.append(f"dl: {type(e).__name__}")
            continue
        ctype = (rr.headers.get("Content-Type") or "").lower()
        if rr.status_code not in (200, 206) or "text" in ctype or "json" in ctype:
            diag.append(f"dl: HTTP {rr.status_code} {ctype[:16]}")
            continue
        p = os.path.join(out, f"douyin_{aid.group(1) if aid else 'video'}.mp4")
        with open(p, "wb") as f:
            for c in rr.iter_content(1 << 20):
                f.write(c)
        size = os.path.getsize(p)
        head = open(p, "rb").read(32)
        if size > 200_000 and (b"ftyp" in head[:16] or head[:4] == b"\x1aE\xdf\xa3"):
            return True, f"saved {size/1048576:.2f} MB; " + "; ".join(diag), [os.path.basename(p)]
        os.remove(p)
        diag.append(f"dl: not video ({size}B)")
    return False, "; ".join(diag) or "no parser worked", []


def try_douyin_note(url, out):
    m = re.search(r"(?:/note/|/video/|item_ids=|/slides/)(\d{15,})", url)
    if not m:
        return False, "no aweme id in url", []
    aid = m.group(1)
    h_html = {"User-Agent": MOBILE_UA, "Accept-Language": "zh-CN,zh;q=0.9",
              "Referer": "https://www.douyin.com/"}
    pages = [
        f"https://www.iesdouyin.com/share/slides/{aid}/",
        f"https://www.iesdouyin.com/share/video/{aid}/",
        f"https://m.douyin.com/share/note/{aid}",
        f"https://www.douyin.com/note/{aid}",
    ]
    diag, urls = [], []
    for pg in pages:
        try:
            r = requests.get(pg, headers=h_html, timeout=45)
        except Exception as e:
            diag.append(f"{pg.split('/')[2]}{pg.split(aid)[0][-8:]}: {type(e).__name__}")
            continue
        html = (r.text or "").replace("\\u002F", "/").replace("\\/", "/")
        found = []
        for blob in _json_blobs(html):
            _walk_image_urls(blob, found)
        if not found:
            found = [u.replace("\\u002F", "/") for u in
                     re.findall(r"https?://[^\s\"'\\<>]*douyinpic\.com[^\s\"'\\<>]*", html)]
        # 同图去重，保留最先出现（通常是原图）
        seen, uniq = set(), []
        for u in found:
            k = _canon(u)
            if k not in seen:
                seen.add(k)
                uniq.append(u)
        diag.append(f"{pg.split('/')[2]}: HTTP {r.status_code} len={len(html)} imgs={len(uniq)}")
        if uniq:
            urls = uniq
            break

    if urls:
        got = _download_images(urls, out)
        if got:
            return True, f"share-page ok: {len(got)} imgs; " + "; ".join(diag), got

    # 第三方解析 API（公共实例，可能 502，多试几家）
    from urllib.parse import quote
    apis = [
        "https://api.douyin.wtf/api/hybrid/video_data?url={}&minimal=false",
        "https://www.tikwm.com/api/?url={}",
        "https://api.douyin.wtf/api/douyin/web/fetch_one_video?aweme_id=" + aid,
    ]
    for tpl in apis:
        target = tpl.format(quote(url, safe="")) if "{}" in tpl else tpl
        try:
            r = requests.get(target, headers={"User-Agent": UA}, timeout=45)
            j = r.json()
        except Exception as e:
            diag.append(f"api {target.split('/')[2]}: {type(e).__name__}")
            continue
        acc = []
        _walk_image_urls(j, acc)
        seen, uniq = set(), []
        for u in acc:
            k = _canon(u)
            if k not in seen:
                seen.add(k)
                uniq.append(u)
        if uniq:
            got = _download_images(uniq, out)
            if got:
                return True, f"third-party api {target.split('/')[2]}: {len(got)} imgs", got
        diag.append(f"api {target.split('/')[2]}: HTTP {r.status_code} imgs=0")

    return False, "; ".join(diag) or "no strategy worked", []


# --------------------------------------------------------------------------
# 3.7 YouTube 专用：Invidious 公共实例 —— 换一条完全不在数据中心 IP 上的路
#     Invidious 是开源 YouTube 前端，它自己的服务器去取流，我们只跟它要结果
# --------------------------------------------------------------------------
INVIDIOUS = [
    "https://inv.nadeko.net",
    "https://invidious.nerdvpn.de",
    "https://yewtu.be",
    "https://iv.melmac.space",
    "https://invidious.privacyredirect.com",
    "https://invidious.f5.si",
]


def _h(res):
    m = re.search(r"(\d+)", str(res or ""))
    return int(m.group(1)) if m else 0


def try_invidious(url, out):
    vid = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url)
    if not vid:
        return False, "no 11-char video id", []
    vid = vid.group(1)
    diag = []
    for inst in INVIDIOUS:
        host = inst.split("//")[1]
        try:
            r = requests.get(f"{inst}/api/v1/videos/{vid}",
                             headers={"User-Agent": UA}, timeout=35)
            if r.status_code != 200:
                diag.append(f"{host}: HTTP {r.status_code}")
                continue
            j = r.json()
        except Exception as e:
            diag.append(f"{host}: {type(e).__name__}")
            continue

        prog = [(f.get("resolution"), f.get("url"))
                for f in (j.get("formatStreams") or []) if f.get("url")]
        prog = [p for p in prog if 0 < _h(p[0]) <= 480] or prog
        prog.sort(key=lambda p: -_h(p[0]))

        vids = [(f.get("qualityLabel") or f.get("resolution"), f.get("url"))
                for f in (j.get("adaptiveFormats") or [])
                if f.get("url") and "audio" not in (f.get("type") or "")]
        vids = [v for v in vids if 0 < _h(v[0]) <= 720] or vids
        vids.sort(key=lambda v: -_h(v[0]))

        auds = [(f.get("audioQuality") or f.get("bitrate") or "0", f.get("url"))
                for f in (j.get("adaptiveFormats") or [])
                if f.get("url") and "audio" in (f.get("type") or "")]
        auds.sort(key=lambda a: -int(re.sub(r"\D", "", str(a[0])) or 0))

        title = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", j.get("title") or "yt")[:40]
        final = os.path.join(out, f"{title}_{vid}.mp4")

        def grab(u, dst):
            rr = requests.get(u, headers={"User-Agent": UA, "Referer": inst},
                              timeout=300, stream=True)
            if rr.status_code not in (200, 206):
                return False
            with open(dst, "wb") as f:
                for c in rr.iter_content(1 << 20):
                    f.write(c)
            return os.path.getsize(dst) > 50000

        if prog:
            if grab(prog[0][1], final):
                return True, f"{host}: progressive {prog[0][0]}", [os.path.basename(final)]
            diag.append(f"{host}: progressive download failed")
        if vids:
            vp = os.path.join(out, "v.tmp")
            ap = os.path.join(out, "a.tmp")
            if grab(vids[0][1], vp):
                if auds and grab(auds[0][1], ap):
                    run(["ffmpeg", "-y", "-loglevel", "error", "-i", vp, "-i", ap,
                         "-c", "copy", final], timeout=600)
                else:
                    run(["ffmpeg", "-y", "-loglevel", "error", "-i", vp,
                         "-c", "copy", final], timeout=600)
                for p in (vp, ap):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
                if os.path.exists(final) and os.path.getsize(final) > 50000:
                    return True, f"{host}: adaptive+mux {vids[0][0]}", [os.path.basename(final)]
            diag.append(f"{host}: adaptive download failed")
    return False, " | ".join(diag) or "no invidious instance reachable", []


# --------------------------------------------------------------------------
# 3.8 公共代理中继：B站/抖音对机房 IP 硬拒绝，借第三方代理换个出口 IP 试试
# --------------------------------------------------------------------------
PROXY_TPL = [
    "https://api.codetabs.com/v1/proxy?quest=",
    "https://api.allorigins.win/raw?url=",
    "https://corsproxy.io/?url=",
]


def try_proxy_relay(url, out):
    """只用于拿元数据 JSON（B站 view / playurl、抖音 iteminfo）。"""
    diag = []
    for tpl in PROXY_TPL:
        host = tpl.split("//")[1].split("/")[0]
        try:
            from urllib.parse import quote
            r = requests.get(tpl + quote(url, safe=""),
                             headers={"User-Agent": UA}, timeout=45)
            if r.status_code != 200:
                diag.append(f"{host}: HTTP {r.status_code}")
                continue
            txt = r.text.strip()
            if not txt or txt[0] not in "{[":
                diag.append(f"{host}: non-json {txt[:60]!r}")
                continue
            try:
                j = json.loads(txt)
            except Exception:
                diag.append(f"{host}: json parse failed")
                continue
            json.dump(j, open(os.path.join(out, f"_proxy_{host}.json"), "w",
                              encoding="utf-8"), ensure_ascii=False, indent=2)
            return True, f"{host}: got JSON", []
        except Exception as e:
            diag.append(f"{host}: {type(e).__name__}")
    return False, " | ".join(diag) or "no proxy worked", []


# --------------------------------------------------------------------------
# 4. 兜底：直接扒页面里的 CDN 图片
# --------------------------------------------------------------------------
def try_scrape(url, out):
    try:
        r = requests.get(url, headers={"User-Agent": UA,
                                       "Accept-Language": "zh-CN,zh;q=0.9"}, timeout=45)
        html = r.text
    except Exception as e:
        return False, f"fetch failed: {type(e).__name__}: {e}", []

    html = html.replace("\\u002F", "/").replace("\\/", "/")
    cands = []
    for pat in (r"https?:[^\s\"'\\<>]*?xhscdn\.com[^\s\"'\\<>]*?\.(?:jpg|jpeg|png|webp)[^\s\"'\\<>]*",
                r"https?:[^\s\"'\\<>]*?sinaimg\.cn[^\s\"'\\<>]*?\.(?:jpg|jpeg|png|webp)[^\s\"'\\<>]*",
                IMG_CDN.pattern):
        cands += re.findall(pat, html, re.I)

    seen, urls = set(), []
    for u in cands:
        u = u.replace("&amp;", "&")
        if u.split("?")[0] not in seen:
            seen.add(u.split("?")[0])
            urls.append(u)

    got = []
    for i, u in enumerate(urls[:30]):
        try:
            rr = requests.get(u, headers={"User-Agent": UA, "Referer": url}, timeout=45)
            if rr.status_code == 200 and len(rr.content) > 8000:
                ext = ".jpg" if "jp" in u.lower()[-12:] else (".png" if "png" in u.lower()[-12:] else ".webp")
                p = os.path.join(out, f"img_{i+1:02d}{ext}")
                open(p, "wb").write(rr.content)
                got.append(os.path.basename(p))
        except Exception:
            continue
        time.sleep(0.3)
    return bool(got), f"found {len(urls)} candidate urls, saved {len(got)}", got


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def handle(url):
    url = url.strip()
    if not url or url.startswith("#"):
        return None
    folder = platform_of(url)
    is_dy_cdn = re.search(r"douyin(?:pic|vod)\.com", url, re.I) is not None
    is_video = ("mime_type=video_mp4" in url or re.search(r"\.mp4(?:\?|$)", url, re.I) is not None
                or "douyinvod.com" in url)
    if is_dy_cdn and is_video:
        out = os.path.join(RAW, folder, "direct_media")
        os.makedirs(out, exist_ok=True)
        good, log, _ = try_direct_media(url, out)
        real = []
        for rel in list_files_recursive(out):
            if rel == "meta.json":
                continue
            pp = os.path.join(out, rel)
            if os.path.isfile(pp):
                real.append({"name": rel, "bytes": os.path.getsize(pp), "sha256": sha256(pp)})
        json.dump({"source_url": url, "platform_folder": folder,
                   "status": "ok" if good else "failed",
                   "tool_used": "direct-media" if good else None,
                   "steps": [{"tool": "direct-media", "ok": bool(good), "log": log}],
                   "files": real,
                   "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "note": "素材仅供研究/参考/二次创作底稿，勿直接搬运发布"},
                  open(os.path.join(out, "meta.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        return json.load(open(os.path.join(out, "meta.json"), encoding="utf-8"))

    if "douyinpic.com" in url and re.search(r"\.(?:jpg|jpeg|png|webp)", url, re.I):
        out = os.path.join(RAW, folder, "direct_images")
        os.makedirs(out, exist_ok=True)
        good, log, _ = try_direct_image(url, out)
        real = []
        for rel in list_files_recursive(out):
            if rel == "meta.json":
                continue
            pp = os.path.join(out, rel)
            if os.path.isfile(pp):
                real.append({"name": rel, "bytes": os.path.getsize(pp), "sha256": sha256(pp)})
        json.dump({"source_url": url, "platform_folder": folder,
                   "status": "ok" if good else "failed",
                   "tool_used": "direct-image" if good else None,
                   "steps": [{"tool": "direct-image", "ok": bool(good), "log": log}],
                   "files": real,
                   "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "note": "素材仅供研究/参考/二次创作底稿，勿直接搬运发布"},
                  open(os.path.join(out, "meta.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        return json.load(open(os.path.join(out, "meta.json"), encoding="utf-8"))
    out = os.path.join(RAW, folder, slug_of(url))
    os.makedirs(out, exist_ok=True)

    chain = [("yt-dlp", try_ytdlp), ("gallery-dl", try_gallerydl), ("scrape", try_scrape)]
    # 视频优先的平台，先换条不在机房 IP 上的路
    if folder == "03_YouTube素材":
        chain.insert(1, ("invidious", try_invidious))
    if folder in ("05_B站素材", "02_抖音素材"):
        chain.append(("proxy-relay", try_proxy_relay))
    if folder == "01_小红书素材":
        # 图片笔记没有 video format，先走 dump-json 拿原图列表
        chain.insert(0, ("xhs-dump", try_xhs_dump))
    if folder == "05_B站素材":
        chain.insert(1, ("bilibili-api", try_bilibili_api))
    if folder == "02_抖音素材":
        chain.insert(2, ("public-parsers", try_public_parsers))
        chain.insert(0, ("douyin-video", try_douyin_video))
        chain.insert(0, ("douyin-note", try_douyin_note))
        chain.insert(1, ("douyin-api", try_douyin_api))

    steps, ok = [], False
    for name, fn in chain:
        try:
            good, log, _ = fn(url, out)
        except Exception as e:
            good, log = False, f"{type(e).__name__}: {e}"
        steps.append({"tool": name, "ok": bool(good), "log": log})
        if good:
            ok = True
            break

    real = []
    for rel in list_files_recursive(out):
        if rel == "meta.json":
            continue
        p = os.path.join(out, rel)
        if os.path.isfile(p):
            real.append({"name": rel, "bytes": os.path.getsize(p), "sha256": sha256(p)})

    if not real:
        ok = False

    json.dump({
        "source_url": url, "platform_folder": folder,
        "status": "ok" if ok else "failed",
        "tool_used": next((s["tool"] for s in steps if s["ok"]), None),
        "steps": steps, "files": real,
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "note": "素材仅供研究/参考/二次创作底稿，勿直接搬运发布",
    }, open(os.path.join(out, "meta.json"), "w", encoding="utf-8"),
        ensure_ascii=False, indent=2)
    return json.load(open(os.path.join(out, "meta.json"), encoding="utf-8"))


def main():
    if not os.path.exists(QUEUE):
        print("no queue file")
        return
    urls = [l for l in open(QUEUE, encoding="utf-8").read().splitlines() if l.strip()]
    os.makedirs(RAW, exist_ok=True)
    results = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        for m in ex.map(handle, urls):
            if m:
                results.append(m)
                print(f"[{'OK  ' if m['status'] == 'ok' else 'FAIL'}] "
                      f"{m['platform_folder']:<16} {m['source_url'][:60]} "
                      f"-> {len(m['files'])} files "
                      f"({sum(f['bytes'] for f in m['files'])/1048576:.2f} MB)")

    lines = ["# 最近一次中继下载", "",
             f"时间：{time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}  ",
             f"任务：{len(results)} 条，成功：{sum(1 for m in results if m['status'] == 'ok')} 条", "",
             "| 平台 | 结果 | 命中工具 | 文件数 | 体积 | 链接 |",
             "|---|---|---|---|---|---|"]
    for m in results:
        size = sum(f["bytes"] for f in m["files"])
        lines.append(f"| {m['platform_folder']} | {'✅' if m['status'] == 'ok' else '❌'} | "
                     f"{m['tool_used'] or '-'} | {len(m['files'])} | {size/1048576:.2f} MB | "
                     f"{m['source_url'][:55]} |")
    lines += ["", "## 逐条明细", ""]
    for m in results:
        lines += [f"### {m['source_url']}", "",
                  f"- 平台目录：`{m['platform_folder']}`",
                  f"- 状态：{m['status']}，命中工具：{m['tool_used'] or '无'}"]
        for f in m["files"]:
            lines.append(f"- `{f['name']}` — {f['bytes']:,} 字节")
        for s in m["steps"]:
            if not s["ok"]:
                lines.append(f"- ❌ {s['tool']}：`{s['log'][:300]}`")
        lines.append("")
    open(os.path.join(RAW, "_LAST_RUN.md"), "w", encoding="utf-8").write("\n".join(lines))
    json.dump(results, open(os.path.join(RAW, "_last_run.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("\n".join(lines[:16]))


if __name__ == "__main__":
    sys.exit(main())
