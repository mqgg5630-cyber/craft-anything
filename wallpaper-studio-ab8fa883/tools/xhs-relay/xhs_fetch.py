#!/usr/bin/env python3
"""
xhs_fetch.py — 在 GitHub Actions runner 里跑（runner 出网不受限）。

读取 tools/xhs-relay/queue.json，对每条小红书笔记：
  1. 带浏览器请求头拉笔记页，解析 __INITIAL_STATE__ / 正则，取标题、正文、作者、
     话题、imageList（urlDefault / urlPre / 宽高）。
  2. 对每张图按「原文件 → 强制 PNG → 强制 JPEG → 页面上的签名 webp」四个变体逐个
     下载，用 Pillow 校验后保留像素最多的那个（同像素优先原文件）。
     token 提取与直链拼法与 JoeanAmier/XHS-Downloader 一致：
        token = "/".join(url.split("/")[5:]).split("!")[0]
        原文件  https://sns-img-bd.xhscdn.com/{token}
        定格式  https://ci.xiaohongshu.com/{token}?imageView2/format/png
  3. 写 note.json（机器可读）+ note.md（人读）+ 图片到 out_dir。

退出码恒为 0：一条失败不影响其它条；失败原因写进 note.md。
队列格式（queue.json）：
{
  "jobs": [
    {"note_url": "https://www.xiaohongshu.com/discovery/item/<id>?xsec_token=...",
     "out_dir": "相对仓库根目录的输出目录",
     "image_urls": ["可选：页面抓不到 imageList 时的兜底图片直链", "..."],
     "max_total_mb": 80}
  ]
}
"""
import hashlib
import json
import os
import re
import sys
import time
from io import BytesIO

import requests
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
QUEUE = os.path.join(ROOT, "tools", "xhs-relay", "queue.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
PAGE_H = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}
IMG_H = {"User-Agent": UA, "Referer": "https://www.xiaohongshu.com/",
         "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"}


def log(*a):
    print(*a, flush=True)


def note_id_of(url):
    m = re.search(r"/(?:item|explore|discovery/item)/([0-9a-f]{24})", url)
    return m.group(1) if m else re.sub(r"\W+", "_", url)[-24:]


def token_of(url):
    """XHS-Downloader 同款：去掉域名/时间戳/签名，保留 spectrum/xxx 或 xxx。"""
    return "/".join(url.split("/")[5:]).split("!")[0]


def unescape_js(s):
    return (s.replace("\\u002F", "/").replace("\\/", "/")
             .replace("\\n", "\n").replace('\\"', '"'))


# ---------------------------------------------------------------- 笔记页
def fetch_note(url, cookie=""):
    h = dict(PAGE_H)
    if cookie:
        h["Cookie"] = cookie
    r = requests.get(url, headers=h, timeout=45, allow_redirects=True)
    html = r.text
    info = {"http_status": r.status_code, "final_url": r.url, "html_bytes": len(html)}
    nid = note_id_of(url)

    # A. 完整 JSON（最可靠）
    data = None
    m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>", html, re.S)
    if m:
        # rednote 页面吐的是 JS 字面量，不是严格 JSON：undefined / new Set([]) / new Map([]) 都要先规整
        raw = re.sub(r"\bundefined\b", "null", m.group(1))
        raw = re.sub(r"new\s+(?:Set|Map)\(\s*(\[.*?\])\s*\)", r"\1", raw, flags=re.S)
        try:
            data = json.loads(raw)
        except Exception as e:  # noqa: BLE001
            info["json_error"] = f"{type(e).__name__}: {str(e)[:80]}"
    note = None
    if data:
        try:
            nd = data["note"]["noteDetailMap"]
            key = nid if nid in nd else next(iter(nd))
            note = nd[key]["note"]
        except Exception:  # noqa: BLE001
            note = None

    out = {"note_id": nid, "title": "", "desc": "", "nickname": "", "user_id": "",
           "tags": [], "time": None, "ip_location": "", "interact": {}, "images": [],
           "parse": "json" if note else "regex", "fetch": info}
    if note:
        out["title"] = note.get("title") or ""
        out["desc"] = note.get("desc") or ""
        u = note.get("user") or {}
        out["nickname"] = u.get("nickname") or u.get("nickName") or ""
        out["user_id"] = u.get("userId") or ""
        out["tags"] = [t.get("name") for t in (note.get("tagList") or []) if t.get("name")]
        out["time"] = note.get("time")
        out["ip_location"] = note.get("ipLocation") or ""
        ii = note.get("interactInfo") or {}
        out["interact"] = {k: ii.get(k) for k in ("likedCount", "collectedCount", "commentCount", "shareCount") if k in ii}
        for i, im in enumerate(note.get("imageList") or []):
            out["images"].append({
                "index": i + 1,
                "url_default": im.get("urlDefault") or "",
                "url_pre": im.get("urlPre") or "",
                "width": im.get("width"), "height": im.get("height"),
                "live_photo": bool(im.get("livePhoto")),
            })
        out["type"] = note.get("type") or ("video" if note.get("video") else "normal")
        if note.get("video"):
            out["video"] = video_info(note["video"])
    else:
        # B. 正则兜底
        flat = unescape_js(html)
        t = re.search(r'<meta name="og:title" content="([^"]*)"', flat) or re.search(r"<title>([^<]*)</title>", flat)
        out["title"] = (t.group(1) if t else "").replace(" - 小红书", "").replace(" - rednote", "").strip()
        d = re.search(r'<meta name="description" content="([^"]*)"', flat)
        out["desc"] = d.group(1) if d else ""
        n = re.search(r'"nickname":"([^"]+)"', flat)
        out["nickname"] = n.group(1) if n else ""
        urls = []
        for key in ("urlDefault", "urlPre"):
            urls += re.findall(rf'"{key}":"(https?:[^"]+)"', flat)
        seen = set()
        for u in urls:
            tk = token_of(u)
            if tk and tk not in seen and ("xhscdn" in u or "rednotecdn" in u or "xiaohongshu" in u):
                seen.add(tk)
                out["images"].append({"index": len(out["images"]) + 1, "url_default": u,
                                      "url_pre": "", "width": None, "height": None, "live_photo": False})
        out["tags"] = re.findall(r"#([^#\s\[\]]{1,30})\[话题\]#", out["desc"])
        # 视频兜底：originVideoKey / masterUrl 直接从页面文本里抓
        vk = re.search(r'"originVideoKey":"([^"]+)"', flat)
        murls = re.findall(r'"masterUrl":"(https?:[^"]+)"', flat)
        if vk or murls:
            out["type"] = "video"
            out["video"] = {"origin_key": vk.group(1) if vk else "", "duration": None,
                            "streams": [{"codec": "?", "height": None, "width": None, "size": None,
                                         "bitrate": None, "url": u} for u in dict.fromkeys(murls)]}
        else:
            out["type"] = "normal"
    return out, html


def video_info(v):
    """note.video → 原片 key + 各码流（XHS-Downloader 同款字段）。"""
    mv = ((v.get("media") or {}).get("video") or {})
    info = {"origin_key": ((v.get("consumer") or {}).get("originVideoKey")) or "",
            "duration": ((v.get("capa") or {}).get("duration")) or mv.get("duration"),
            "origin_md5": mv.get("md5") or "",          # 作者上传原片的 md5，可用来校验直传 Drive 的文件
            "hdr_type": mv.get("hdrType"), "video_id": mv.get("videoId") or (v.get("media") or {}).get("videoId"),
            "streams": []}
    stream = ((v.get("media") or {}).get("stream")) or {}
    for codec, items in stream.items():
        for it in items or []:
            urls = [it.get("masterUrl")] + list(it.get("backupUrls") or [])
            info["streams"].append({"codec": codec, "height": it.get("height"), "width": it.get("width"),
                                    "size": it.get("size"), "bitrate": it.get("videoBitrate"),
                                    "url": next((u for u in urls if u), "")})
    info["streams"].sort(key=lambda x: (x["height"] or 0, x["size"] or 0), reverse=True)
    return info


# ---------------------------------------------------------------- 图片
def variants(token, signed_url=""):
    v = [("original", f"https://sns-img-bd.xhscdn.com/{token}"),
         ("png", f"https://ci.xiaohongshu.com/{token}?imageView2/format/png"),
         ("jpeg", f"https://ci.xiaohongshu.com/{token}?imageView2/format/jpeg")]
    if signed_url:
        v.append(("display", signed_url))
    return v


def get_image(url, tries=3):
    last = ""
    for k in range(tries):
        try:
            r = requests.get(url, headers=IMG_H, timeout=60)
            if r.status_code == 200 and len(r.content) > 5000:
                im = Image.open(BytesIO(r.content))
                im.load()
                return r.content, im.format, im.size, ""
            last = f"HTTP {r.status_code} {len(r.content)}B"
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {str(e)[:60]}"
        time.sleep(1.5 * (k + 1))
    return None, None, None, last


RANK = {"original": 0, "png": 1, "jpeg": 2, "display": 3}
EXT = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp", "HEIF": "heic", "AVIF": "avif", "GIF": "gif"}


def download_all(images, out_dir, max_total_mb):
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for im in images:
        token = token_of(im["url_default"]) if im.get("url_default") else im.get("token", "")
        rec = {"index": im["index"], "token": token, "tried": [], "file": None}
        best = None
        for name, u in variants(token, im.get("url_default", "")):
            b, fmt, size, err = get_image(u)
            rec["tried"].append({"variant": name, "url": u, "ok": b is not None,
                                 "bytes": len(b) if b else 0, "format": fmt,
                                 "size": list(size) if size else None, "err": err})
            log(f"  [{im['index']:02d}] {name:8s} -> {'OK' if b else 'x '} {fmt or ''} {size or ''} {len(b) if b else 0}B {err}")
            if b is None:
                continue
            cand = (size[0] * size[1], -RANK[name], name, b, fmt, size)
            if best is None or cand[:2] > best[:2]:
                best = cand
            time.sleep(0.4)
        if best:
            _, _, name, b, fmt, size = best
            fn = f"{im['index']:02d}.{EXT.get(fmt, (fmt or 'bin').lower())}"
            with open(os.path.join(out_dir, fn), "wb") as f:
                f.write(b)
            rec.update({"file": fn, "variant": name, "bytes": len(b), "format": fmt, "size": list(size)})
        results.append(rec)

    # 体积预算：超了就把最大的几张换成 display 版
    total = sum(r.get("bytes", 0) for r in results if r.get("file"))
    budget = max_total_mb * 1024 * 1024
    if total > budget:
        log(f"  total {total/1e6:.1f}MB > budget {max_total_mb}MB, downgrading largest files to display")
        for r in sorted(results, key=lambda r: -r.get("bytes", 0)):
            if total <= budget:
                break
            disp = next((t for t in r["tried"] if t["variant"] == "display" and t["ok"]), None)
            if not disp or r.get("variant") == "display":
                continue
            b, fmt, size, _ = get_image(disp["url"])
            if b:
                os.remove(os.path.join(out_dir, r["file"]))
                fn = f"{r['index']:02d}.{EXT.get(fmt, 'bin')}"
                open(os.path.join(out_dir, fn), "wb").write(b)
                total -= r["bytes"] - len(b)
                r.update({"file": fn, "variant": "display(downgraded)", "bytes": len(b), "format": fmt, "size": list(size)})
    return results


# ---------------------------------------------------------------- 视频
VID_H = {"User-Agent": PAGE_H["User-Agent"], "Referer": "https://www.xiaohongshu.com/",
         "Accept": "video/mp4,video/*;q=0.9,*/*;q=0.8"}


def get_video(url, dest, max_mb, tries=2):
    """流式下载到 dest；返回 (bytes, err)。超过 max_mb 直接放弃，避免把仓库撑爆。"""
    last = ""
    for k in range(tries):
        try:
            with requests.get(url, headers=VID_H, timeout=120, stream=True) as r:
                if r.status_code != 200:
                    last = f"HTTP {r.status_code}"
                    time.sleep(2)
                    continue
                clen = int(r.headers.get("Content-Length") or 0)
                if clen and clen > max_mb * 1024 * 1024:
                    return 0, f"too large: {clen/1e6:.1f}MB > {max_mb}MB"
                n = 0
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
                        n += len(chunk)
                        if n > max_mb * 1024 * 1024:
                            f.close()
                            os.remove(dest)
                            return 0, f"too large (>{max_mb}MB while streaming)"
                if n < 20000:
                    last = f"too small {n}B"
                    continue
                return n, ""
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {str(e)[:60]}"
            time.sleep(2)
    return 0, last


def download_video(video, out_dir, max_mb):
    """先试无水印原片 sns-video-bd/<originVideoKey>，再退到最高分辨率码流。"""
    os.makedirs(out_dir, exist_ok=True)
    cands = []
    if video.get("origin_key"):
        cands.append(("origin", f"https://sns-video-bd.xhscdn.com/{video['origin_key']}"))
    for st in video.get("streams") or []:
        if st.get("url"):
            cands.append((f"stream-{st.get('codec')}-{st.get('height')}p", st["url"]))
    rec = {"tried": [], "file": None}
    for name, u in cands:
        dest = os.path.join(out_dir, "video.mp4")
        n, err = get_video(u, dest, max_mb)
        rec["tried"].append({"variant": name, "url": u, "ok": bool(n), "bytes": n, "err": err})
        log(f"  [video] {name:22s} -> {'OK' if n else 'x '} {n/1e6:.1f}MB {err}")
        if n:
            rec.update({"file": "video.mp4", "variant": name, "bytes": n})
            break
    return rec


# ---------------------------------------------------------------- 大文件直传 Google Drive
def drive_resumable_put(uri, path, chunk=8 * 1024 * 1024):
    """把本地文件按块 PUT 到一次性的 Drive resumable 会话地址（由沙箱里的 Drive 连接器
    initiate_resumable_upload 生成，7 天有效、只能用一次）。块大小必须是 256KiB 的倍数。
    标准 Content-Range 协议（中间块回 308，最后一块回 200/201 + 文件元数据）；首块就 4xx 时再试 X-Goog-Upload-* 协议。"""
    total = os.path.getsize(path)
    rec = {"bytes": total, "protocol": None, "ok": False, "status": None, "response": None, "err": ""}
    h5 = hashlib.md5()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h5.update(blk)
    rec["md5"] = h5.hexdigest()
    for proto in ("content-range", "x-goog"):   # Drive v3 resumable 端点：标准 Content-Range 协议优先
        off, ok, err, last_resp = 0, False, "", None
        with open(path, "rb") as f:
            while off < total:
                data = f.read(chunk)
                last = off + len(data) >= total
                if proto == "x-goog":
                    h = {"X-Goog-Upload-Command": "upload, finalize" if last else "upload",
                         "X-Goog-Upload-Offset": str(off), "X-Goog-Upload-Total-Size": str(total),
                         "Content-Length": str(len(data))}
                else:
                    h = {"Content-Range": f"bytes {off}-{off + len(data) - 1}/{total}",
                         "Content-Length": str(len(data))}
                try:
                    r = requests.put(uri, headers=h, data=data, timeout=600)
                except Exception as e:  # noqa: BLE001
                    err = f"{type(e).__name__}: {str(e)[:80]}"
                    break
                last_resp = r
                st = r.headers.get("X-Goog-Upload-Status", "")
                if r.status_code >= 400:
                    err = f"HTTP {r.status_code} {r.text[:200]}"
                    break
                off += len(data)
                if off % (64 * 1024 * 1024) < chunk or last:
                    log(f"  [drive] {proto} {off/1e6:.0f}/{total/1e6:.0f} MB  http={r.status_code} status={st or '-'}")
                if last:
                    ok = (st == "final") or r.status_code in (200, 201)
        rec.update({"protocol": proto, "ok": ok, "err": err,
                    "status": last_resp.status_code if last_resp is not None else None})
        if last_resp is not None:
            try:
                rec["response"] = last_resp.json()
            except Exception:  # noqa: BLE001
                rec["response"] = last_resp.text[:300]
        if ok:
            break
        if off > 0 and not ok:
            break  # 会话已经被部分写入，不能换协议重来
        log(f"  [drive] {proto} failed at offset 0: {err}; trying next protocol")
    return rec


def push_origin_to_drive(note, uri, tmp="/tmp/xhs-origin.mp4"):
    v = note.get("video") or {}
    if not v.get("origin_key"):
        return {"ok": False, "err": "no originVideoKey"}
    url = f"https://sns-video-bd.xhscdn.com/{v['origin_key']}"
    n, err = get_video(url, tmp, max_mb=4096, tries=3)
    log(f"  [drive] origin download -> {n/1e6:.1f}MB {err}")
    if not n:
        return {"ok": False, "err": f"download failed: {err}", "url": url}
    rec = drive_resumable_put(uri, tmp)
    rec["url"] = url
    if v.get("origin_md5"):
        rec["origin_md5"] = v["origin_md5"]
        rec["md5_match"] = (rec.get("md5") == v["origin_md5"])
    try:
        os.remove(tmp)
    except OSError:
        pass
    return rec


# ---------------------------------------------------------------- 主流程
def run_job(job, cookie):
    url = job["note_url"]
    out_dir = os.path.join(ROOT, job["out_dir"])
    log(f"== {url}\n   -> {job['out_dir']}")
    nid8 = note_id_of(url)[:8]
    drive_uri = os.environ.get(f"DRIVE_UPLOAD_URI__{nid8}", "").strip() or os.environ.get("DRIVE_UPLOAD_URI", "").strip()
    force = job.get("force") or os.environ.get("FORCE", "").lower() in ("1", "true", "yes") or bool(drive_uri)
    if os.path.exists(os.path.join(out_dir, "note.json")) and not force:
        log("   note.json already present -> skip (set \"force\": true in queue.json to refetch)")
        return
    try:
        note, html = fetch_note(url, cookie)
    except Exception as e:  # noqa: BLE001
        note = {"note_id": note_id_of(url), "title": "", "desc": "", "nickname": "", "tags": [],
                "images": [], "parse": "failed", "fetch": {"error": f"{type(e).__name__}: {e}"}}
        html = ""
    log(f"   page: {note.get('fetch')} parse={note['parse']} title={note['title']!r} images={len(note['images'])}")

    images = note["images"]
    fallback = job.get("image_urls") or []
    if len(images) < len(fallback):
        log(f"   page gave {len(images)} images < {len(fallback)} fallback urls; using fallback list")
        images = [{"index": i + 1, "url_default": u, "url_pre": "", "width": None, "height": None}
                  for i, u in enumerate(fallback)]
        note["images_source"] = "fallback(image_urls)"
    else:
        note["images_source"] = "page"
    note["images"] = images

    is_video = note.get("type") == "video" and note.get("video")
    if is_video:
        images = images[:1]  # 视频笔记的 imageList 只有封面
        note["images"] = images
    results = download_all(images, out_dir, job.get("max_total_mb", 80)) if images else []
    note["downloads"] = results
    if is_video:
        note["video_download"] = download_video(note["video"], out_dir, job.get("max_video_mb", 60))
        if drive_uri:
            log("  [drive] upload URI present -> pushing origin video straight to Google Drive")
            rec = push_origin_to_drive(note, drive_uri)
            rec["at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, "drive_upload.json"), "w", encoding="utf-8") as f:
                json.dump(rec, f, ensure_ascii=False, indent=1)
            log(f"  [drive] result ok={rec.get('ok')} protocol={rec.get('protocol')} err={rec.get('err')}")
            enc = os.path.join(ROOT, "tools", "xhs-relay", "secrets", f"DRIVE_UPLOAD_URI__{nid8}.enc")
            if os.path.exists(enc):   # 一次性会话用过就作废，让 workflow 把密文删掉
                open(enc + ".used", "w").write(rec.get("err") or "ok")
        if results and results[0].get("file"):
            cov = results[0]["file"]
            os.replace(os.path.join(out_dir, cov), os.path.join(out_dir, "cover." + cov.split(".")[-1]))
            results[0]["file"] = "cover." + cov.split(".")[-1]
    note["source_url"] = url
    note["fetched_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "note.json"), "w", encoding="utf-8") as f:
        json.dump(note, f, ensure_ascii=False, indent=1)
    if html and job.get("keep_html"):
        open(os.path.join(out_dir, "page.html"), "w", encoding="utf-8").write(html)

    ok = [r for r in results if r.get("file")]
    lines = [f"# {note['title'] or note['note_id']}", "",
             f"- 来源：{url}", f"- 作者：{note.get('nickname') or '?'}",
             f"- 抓取时间（UTC）：{note['fetched_at_utc']}",
             f"- 解析方式：{note['parse']}；图片列表来源：{note['images_source']}",
             f"- 图片：{len(ok)}/{len(images)} 张下载成功", ""]
    if note.get("desc"):
        lines += ["## 正文", "", note["desc"], ""]
    if note.get("tags"):
        lines += ["## 话题", "", " ".join(f"#{t}" for t in note["tags"]), ""]
    if is_video:
        vd = note["video_download"]
        v = note["video"]
        lines += ["## 视频", "",
                  f"- 文件：{vd.get('file') or '❌ 下载失败'}（{vd.get('variant', '')}，{vd.get('bytes', 0)/1e6:.1f} MB）",
                  f"- 时长：{v.get('duration') or '?'} s；原片 key：`{v.get('origin_key') or '-'}`"
                  + (f"；原片 md5：`{v['origin_md5']}`" if v.get('origin_md5') else ""),
                  "- 码流：" + ("；".join(
                      f"{st.get('codec')} {st.get('width') or '?'}×{st.get('height') or '?'}"
                      + (f" {st['size']/1e6:.1f}MB" if st.get('size') else "")
                      for st in (v.get('streams') or [])[:4]) or "（页面未给出码流参数）"),
                  ""]
    lines += ["## 图片", "", "| # | 文件 | 变体 | 尺寸 | 体积 |", "|---|---|---|---|---|"]
    for r in results:
        if r.get("file"):
            lines.append(f"| {r['index']} | {r['file']} | {r['variant']} | {r['size'][0]}×{r['size'][1]} | {r['bytes']/1024:.0f} KB |")
        else:
            errs = "; ".join(f"{t['variant']}:{t['err']}" for t in r["tried"])
            lines.append(f"| {r['index']} | ❌ | — | — | {errs} |")
    with open(os.path.join(out_dir, "note.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    log(f"   saved {len(ok)}/{len(images)} images to {job['out_dir']}")
    return len(ok), len(images)


def main():
    qpath = sys.argv[sys.argv.index("--queue") + 1] if "--queue" in sys.argv else QUEUE
    with open(qpath, encoding="utf-8") as f:
        queue = json.load(f)
    cookie = os.environ.get("COOKIES_XHS", "").strip()
    log(f"queue: {len(queue.get('jobs', []))} job(s); cookie: {'yes' if cookie else 'no'}")
    only = os.environ.get("ONLY_NOTE", "").strip()
    summary = []
    for job in queue.get("jobs", []):
        if only and only not in job["note_url"]:
            log(f"== skip (ONLY_NOTE={only}): {job['note_url'][:80]}")
            continue
        try:
            ok, n = run_job(job, cookie)
        except Exception as e:  # noqa: BLE001
            log(f"   JOB FAILED: {type(e).__name__}: {e}")
            ok, n = 0, 0
        summary.append((job["note_url"], ok, n))
    log("\n== summary ==")
    for u, ok, n in summary:
        log(f"  {ok}/{n}  {u[:90]}")


if __name__ == "__main__":
    main()
