#!/usr/bin/env python3
"""video-clone-lite 流水线：extract / balance / estimate / gen / assemble。

只用 Python 标准库 + ffmpeg。生成类命令默认干跑（只报价），
--yes 才真正花钱——这条纪律在 SKILL.md 里不可协商。
"""
import base64
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

# 生成/余额/上传/对齐/TTS 全部走官方 apiz CLI（--wait 自动等任务完成）。
# 纪律：gen 默认干跑报价，--yes 才真正花钱。
RATES = {"480p": 43, "720p": 97, "1080p": 273}
YUAN_PER_POINT = 0.01


def die(msg: str):
    print(f"[error] {msg}", file=sys.stderr)
    sys.exit(1)


def load_plan(path: str) -> dict:
    p = Path(path)
    if not p.is_file():
        die(f"plan 不存在：{p}")
    return json.loads(p.read_text(encoding="utf-8"))


def plan_dir(plan_path: str) -> Path:
    return Path(plan_path).resolve().parent


def shot_seconds(plan: dict) -> float:
    return sum(float(s.get("duration", 0)) for s in plan["shots"])


def rate_of(plan: dict) -> int:
    if plan["meta"].get("points_per_second"):
        return int(plan["meta"]["points_per_second"])
    return RATES.get(plan["meta"].get("resolution", "480p"), 43)


def _ffmpeg_bin() -> str:
    return shutil.which("ffmpeg") or __import__("imageio_ffmpeg").get_ffmpeg_exe()


def ffmpeg(args: list[str], cwd: Path | None = None) -> None:
    r = subprocess.run([_ffmpeg_bin(), "-y", "-v", "error", *args], cwd=cwd)
    if r.returncode != 0:
        die("ffmpeg 失败（见上方输出）")


# ---------------------------------------------------------------- 命令

def cmd_extract(argv: list[str]):
    if len(argv) < 2:
        die("用法: build.py extract <视频> <refs目录>")
    src, out = Path(argv[0]), Path(argv[1])
    out.mkdir(parents=True, exist_ok=True)
    fp = shutil.which("ffprobe")
    if fp:
        info = subprocess.run(
            [fp, "-v", "error", "-show_entries", "format=duration,size",
             "-show_entries", "stream=codec_type,width,height,r_frame_rate",
             "-of", "default=noprint_wrappers=1", str(src)],
            capture_output=True, text=True).stdout
    else:
        info = subprocess.run([_ffmpeg_bin(), "-i", str(src)],
                              capture_output=True, text=True).stderr
    (out / "info.txt").write_text(info, encoding="utf-8")
    print(info.strip())

    dur = 0.0
    for line in info.splitlines():
        if line.startswith("duration="):
            try:
                dur = float(line.split("=")[1])
            except ValueError:
                pass
        elif "Duration:" in line:
            import re as _re
            m = _re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", line)
            if m:
                dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    # 一张 4x4 网格概览：>16s 的片自动降低采样密度，保证单图可读
    fps = 1.0 if dur <= 16 else round(15.0 / max(dur, 1), 3)
    ffmpeg(["-i", str(src), "-vf",
            f"fps={fps},scale=270:-1,tile=4x4:padding=4:color=black",
            "-frames:v", "1", str(out / "overview.jpg")])
    if "codec_type=audio" in info or "Audio:" in info:
        ffmpeg(["-i", str(src), "-vn", "-ac", "1", "-ar", "16000",
                "-b:a", "48k", str(out / "audio.mp3")])
    print(f"[ok] {out}/overview.jpg（用 Read 读图做分镜）+ info.txt")


def cmd_balance(_: list[str]):
    print(_apiz("account", "balance"), end="")


def cmd_estimate(argv: list[str]):
    plan = load_plan(argv[0])
    secs, rate = shot_seconds(plan), rate_of(plan)
    min_dur = int(plan["meta"].get("min_duration", 4))
    gen_secs = sum(max(min_dur, float(s.get("duration", 0)))
                   for s in plan["shots"])
    print(f"镜头数 {len(plan['shots'])}  成片时长 {secs:.1f}s  "
          f"生成时长 {gen_secs:.1f}s（短镜头按模型下限 {min_dur}s 生成后裁剪）  "
          f"分辨率 {plan['meta'].get('resolution', '480p')}")
    if plan["meta"].get("token_billing"):
        print("该模型按 token 计费：总额以每次生成返回的 price 为准，"
              "建议先用 --only 单镜头校准单价")
    else:
        points = int(gen_secs * rate + 0.999)
        print(f"预计费用 ≈ {points} 积分 = {points * YUAN_PER_POINT:.2f} 元"
              f"（不含失败重试）")


def _image_arg(val: str, root: Path | None = None) -> str:
    """本地路径 → 先免费上传拿公网 URL（data URL 会撑爆 Windows 命令行长度）。
    URL/空 原样返回。相对路径基于项目目录（plan.json 所在目录）。"""
    if not val:
        return val
    p = Path(val)
    if not p.is_file() and root:
        p = root / val
    if p.is_file():
        out = _apiz("upload", str(p.resolve()))
        try:
            return json.loads(out)["public_url"]
        except (json.JSONDecodeError, KeyError):
            die(f"图片上传失败：{out[:200]}")
    return val


def _generate_shot(shot: dict, meta: dict, dest: Path, root: Path | None = None):
    model = meta.get("model", "bytedance/seedance-2.0/fast/image-to-video")
    prompt = shot.get("prompt", "")
    if shot.get("dialogue") and meta.get("native_dialogue", True):
        prompt += f"\n角色说这句话（口型同步）：「{shot['dialogue']}」"
    args = ["generate", prompt, "--model", model,
            "--wait", "--json", "--wait-timeout", "15m"]
    if shot.get("image_url"):
        args += ["--image-url", _image_arg(shot["image_url"], root)]
    is_video = any(k in model for k in
                   ("video", "seedance", "kling", "wan", "veo", "sora",
                    "hailuo", "vidu"))
    if is_video:
        # Seedance 等模型有时长下限（实测 4s）；短镜头按 4s 生成，assemble 裁剪
        gen_dur = max(int(meta.get("min_duration", 4)),
                      int(shot.get("duration", 5)))
        args += ["--duration", str(gen_dur)]
        if meta.get("aspect_ratio"):
            args += ["--aspect-ratio", meta["aspect_ratio"]]
        options = dict(meta.get("options", {}))
        options.setdefault("resolution", meta.get("resolution", "480p"))
        if options:
            args += ["--params", json.dumps(options, ensure_ascii=False)]
    # 提交失败（如参数错/无账号）重试 1 次；--wait 成功受理后不再重试，
    # 避免同一镜头重复计费。
    out = _apiz(*args, attempts=2)
    url = _media_url(out)
    if not url:
        raise RuntimeError(f"未拿到媒体地址，原始返回：\n{out[:600]}")
    _download(url, dest)
    print(f"  [ok] {dest}")


def _media_url(text: str) -> str | None:
    """从 generate 的 JSON 返回里取产物 URL（output.media[0].url 或兜底正则）。"""
    try:
        d = json.loads(text)
        stack = [d]
        best = None
        while stack:
            o = stack.pop()
            if isinstance(o, dict):
                if "url" in o and isinstance(o["url"], str):
                    best = best or o["url"]
                    if str(o.get("type", "")).startswith("video"):
                        return o["url"]
                stack.extend(o.values())
            elif isinstance(o, list):
                stack.extend(o)
        return best
    except json.JSONDecodeError:
        pass
    import re
    m = re.search(r"https?://\S+\.(?:mp4|mov|webm|jpg|jpeg|png)", text)
    return m.group(0) if m else None


def _download(url: str, dest: Path):
    import urllib.request
    urllib.request.urlretrieve(url, dest)


def cmd_gen(argv: list[str]):
    plan_path, yes = argv[0], "--yes" in argv
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    plan = load_plan(plan_path)
    root = plan_dir(plan_path)
    rate = rate_of(plan)
    min_dur = int(plan["meta"].get("min_duration", 4))
    shots = plan["shots"]
    if only:
        shots = [s for s in shots if s["id"] == only]
        if not shots:
            die(f"--only {only}：plan 里没有这个镜头 id")

    todo = [s for s in shots
            if not (root / s.get("file", f"shots/{s['id']}.mp4")).is_file()]
    done = len(shots) - len(todo)
    todo_secs = sum(max(min_dur, float(s.get("duration", 0))) for s in todo)
    todo_points = int(todo_secs * rate + 0.999) if rate else 0
    billing = ("token 计费，实际价格以返回的 price 为准"
               if plan["meta"].get("token_billing") else
               f"≈{todo_points}积分 = {todo_points * YUAN_PER_POINT:.2f}元")
    print(f"共 {len(shots)} 镜，已完成 {done}，待生成 {len(todo)} "
          f"（生成 {todo_secs:.1f}s，{billing}）")
    if not todo:
        print("[ok] 全部镜头已就绪，直接 assemble")
        return
    if not yes:
        print("[dry-run] 加 --yes 才会真正生成（先向用户报价确认）")
        return

    print(_apiz("account", "balance"), end="")
    for shot in todo:
        dest = root / shot.get("file", f"shots/{shot['id']}.mp4")
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"生成镜头 {shot['id']}（{shot.get('duration')}s → {dest.name}）")
        for attempt in range(1, 4):
            try:
                _generate_shot(shot, plan["meta"], dest, root)
                break
            except Exception as e:  # noqa: BLE001
                print(f"  第 {attempt} 次失败：{e}")
                if attempt == 3:
                    die(f"镜头 {shot['id']} 连续 3 次失败；"
                        f"换模型或改提示词后重跑 gen --yes 会跳过已完成镜头")
                time.sleep(5)
    print("[ok] 全部镜头生成完毕，运行 assemble 合成")


def cmd_assemble(argv: list[str]):
    plan = load_plan(argv[0])
    root = plan_dir(argv[0])
    meta = plan["meta"]
    w, h = meta.get("width", 720), meta.get("height", 1280)
    entries = [(s, root / s.get("file", f"shots/{s['id']}.mp4"))
               for s in plan["shots"]]
    missing = [str(p) for _, p in entries if not p.is_file()]
    if missing:
        die(f"缺镜头素材（先 gen）：{missing}")

    # 单条 filter_complex：逐镜 scale/pad + 按分镜时长裁剪 + concat，
    # 保证短于模型下限的镜头被剪到 plan 时长（成片节奏与参考一致）
    ins, chains, seg_labels = [], [], []
    for i, (s, p) in enumerate(entries):
        ins += ["-i", str(p.resolve())]
        dur = float(s.get("duration", 0))
        chains.append(
            f"[{i}:v]fps={meta.get('fps', 24)},"
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,format=yuv420p,"
            f"trim=duration={dur},setpts=PTS-STARTPTS[v{i}];"
            f"[{i}:a]aresample=48000,atrim=duration={dur},"
            f"asetpts=PTS-STARTPTS[a{i}]")
        # concat 的输入按“段”交错：每段先视频后音频
        seg_labels.append(f"[v{i}][a{i}]")
    graph = ";".join(chains) + ";" + \
        "".join(seg_labels) + \
        f"concat=n={len(entries)}:v=1:a=1[v][a]"
    v_final, a_final = "[v]", "[a]"
    srt_burn_pil = None
    if plan.get("captions", {}).get("srt"):
        srt_raw = Path(plan["captions"]["srt"])
        srt = srt_raw if srt_raw.is_file() else (root / srt_raw)
        if srt.is_file():
            chk = subprocess.run([_ffmpeg_bin(), "-filters"], capture_output=True, text=True)
            if " subtitles " in (chk.stdout or ""):
                esc_srt = srt.resolve().as_posix().replace(":", r"\:")
                font_opt = ""
                fdir = str(root / "fonts")
                if (root / "fonts").is_dir():
                    esc_fd = Path(fdir).resolve().as_posix().replace(":", r"\:")
                    font_opt = f":fontsdir='{esc_fd}':force_style='FontName=ZCOOL KuaiLe,FontSize=15,PrimaryColour=&H00F5FCFF,OutlineColour=&H00161A22,BorderStyle=1,Outline=2,Shadow=1,MarginV=34'"
                graph += f";[v]subtitles='{esc_srt}'{font_opt}[vout]"
                v_final = "[vout]"
            else:
                srt_burn_pil = srt
    extra_inputs, a_map = [], a_final
    bgm_cfg = plan.get("bgm", {}).get("file")
    if bgm_cfg:
        bgm_p = Path(bgm_cfg) if Path(bgm_cfg).is_file() else (root / bgm_cfg)
        if bgm_p.is_file():
            gain = float(plan["bgm"].get("gain_db", -12))
            extra_inputs = ["-i", str(bgm_p.resolve())]
            graph += (f";[{len(entries)}:a]volume={gain}dB[b];"
                      f"[a][b]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[aout]")
            a_map = "[aout]"
    out_mp4 = root / "out" / "final.mp4"
    tmp_mp4 = root / "out" / "_assembled_nosub.mp4" if srt_burn_pil else out_mp4
    args = [*ins, *extra_inputs, "-filter_complex", graph,
             "-map", v_final, "-map", a_map,
             "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(tmp_mp4)]
    root.joinpath("out").mkdir(parents=True, exist_ok=True)
    ffmpeg(args, cwd=root)
    if srt_burn_pil is not None:
        _burn_srt_pil(tmp_mp4, srt_burn_pil, out_mp4, root)
        tmp_mp4.unlink(missing_ok=True)
    out = out_mp4
    size = out.stat().st_size / 1e6
    print(f"[ok] {out}（{size:.1f} MB）——用 Read 抽帧自查一遍再交付")


# ---------------------------------------------------------------- 语音/上传（官方 apiz CLI）

def _apiz(*args: str, attempts: int = 3) -> str:
    """调用官方 apiz CLI，返回 stdout（JSON 或文本）。
    网关偶发 520/525/5xx（Cloudflare 抖动），自动重试。
    失败抛 RuntimeError（调用方决定是否重试/退出）。"""
    last = ""
    for i in range(1, attempts + 1):
        r = subprocess.run(["apiz", *args], capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout
        last = (r.stderr or r.stdout).strip()
        if "HTTP 5" not in last or i == attempts:
            break
        time.sleep(3 * i)
    raise RuntimeError(f"apiz {' '.join(args[:2])} 失败：{last[:300]}")


def _ms_to_srt(ms: int) -> str:
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def cmd_upload(argv: list[str]):
    if not argv:
        die("用法: build.py upload <文件>  （本地文件 → 公网 URL，免费）")
    out = _apiz("upload", str(Path(argv[0]).resolve()))
    try:
        print(json.loads(out)["public_url"])
    except (json.JSONDecodeError, KeyError):
        print(out)


def cmd_srt(argv: list[str]):
    """已知台词 → 字级打轴 → srt。用法: build.py srt <视频/音频> "台词1|台词2" <out.srt>
    台词未知时无自动打轴——手写 srt 后交给 assemble 烧录。"""
    if len(argv) < 3:
        die('用法: build.py srt <视频或音频> "台词1|台词2" <out.srt>')
    src, text_spec, out_path = argv[0], argv[1], Path(argv[2])
    p = Path(src)
    audio = p
    if p.suffix.lower() in {".mp4", ".mov", ".webm", ".mkv"}:
        audio = p.with_suffix(".tmp-audio.mp3")
        ffmpeg(["-i", str(p), "-vn", "-ac", "1", "-ar", "16000",
                "-b:a", "48k", str(audio)])
    url = json.loads(_apiz("upload", str(audio.resolve())))["public_url"]
    joined = json.loads(_apiz("align", text_spec.replace("|", " "),
                              "--audio", url))
    lines = []
    for u in joined.get("utterances", []):
        text = u.get("text", "").strip()
        if not text:
            continue
        i = len(lines) // 4 + 1
        lines += [str(i),
                  f"{_ms_to_srt(u['start_time'])} --> {_ms_to_srt(u['end_time'])}",
                  text, ""]
    out_path.write_text("\n".join(lines), encoding="utf-8")
    if audio != p:
        audio.unlink(missing_ok=True)
    print(f"[ok] {out_path}（{len(lines) // 4} 条字幕）")


def cmd_tts(argv: list[str]):
    """用法: build.py tts "<文本>" <out.mp3> [--voice <voice_id>]
    音色列表: apiz voices list；克隆/设计音色走 MCP speak 的 clone_voice/design_voice。"""
    if len(argv) < 2:
        die('用法: build.py tts "<文本>" <out.mp3> [--voice <id>]')
    text, out_path, voice = argv[0], Path(argv[1]), None
    if "--voice" in argv:
        i = argv.index("--voice")
        voice = argv[i + 1]
    args = ["speak", text, "--output-file", str(out_path.resolve())]
    if voice:
        args += ["--voice", voice]
    out = _apiz(*args)
    print(f"[ok] {out_path} {out.strip().splitlines()[-1] if out.strip() else ''}")


def cmd_understand(argv: list[str]):
    """GLM 直传整段视频做镜头级理解（≤40MB 且 ≤120s）。
    用法: build.py understand <视频> <out.json>
    模型看连续运动，产出分镜卡+动作时序+全局分析；抽帧只作兜底。"""
    if len(argv) < 2:
        die("用法: build.py understand <视频> <out.json>")
    src, out = Path(argv[0]), Path(argv[1])
    mb = src.stat().st_size / 1e6
    if mb > 40:
        die(f"视频 {mb:.1f}MB 超 40MB 直传上限，先转码瘦身")
    sys.path.insert(0, str(Path(__file__).parent))
    import glm_client
    from pathlib import Path as _P
    vc = glm_client.GLMClient()
    data = _P(str(src)).read_bytes()
    import base64
    b64 = base64.b64encode(data).decode()
    blocks = [{"type": "text", "text": "分析这条竖屏短视频"}]
    blocks.append({"type": "video_url",
                   "video_url": {"url": f"data:video/mp4;base64,{b64}"}})
    system = (
        "你是视频拆解引擎。只输出 JSON，不要多余文字。结构："
        '{"duration_sec": 数字, "shots": [{"id","start_sec","end_sec",'
        '"duration_sec","shot_type"景别,"angle"视角,"camera_move"运镜,'
        '"scene"场景三层,"subject"主体外貌与衣着,"action_steps":["时序动作步骤"],'
        '"props"物品,"dialogue"台词原文(无则空串),"audio_cues"声音,'
        '"lighting","color_tone","purpose"钩子/展示/使用/推荐}], '
        '"overall": {"structure","rhythm","hook","cta","tone",'
        '"lighting","color_tone","person_setting","product_judgment"}}')
    print(f"直传 {mb:.1f}MB 给 GLM 分析中（约 30-60 秒）…")
    text, finish = vc.chat(blocks, system=system, effort="high",
                           max_tokens=16384, timeout=600)
    parsed = glm_client.parse_json_lenient(text)
    out.write_text(json.dumps(parsed, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    shots = parsed.get("shots", [])
    print(f"[ok] {out}（{len(shots)} 个镜头, finish={finish}）")


# ---------------------------------------------------------------- Pippit 通道（默认视频生成）

def _pippit_cli() -> str:
    cli = shutil.which("pippit-tool-cli")
    if not cli:
        die("找不到 pippit-tool-cli；先安装：npx @pippit-dev/cli@latest install，"
            "再 pippit-tool-cli login 登录")
    return cli


def cmd_balance_pippit(_: list[str]):
    print(subprocess.run([_pippit_cli(), "get-credit-balance"],
                         capture_output=True, text=True).stdout)


def cmd_pgen(argv: list[str]):
    """Pippit 参考生成/首尾帧生成（默认视频通道）。
    用法: build.py pgen <plan.json> [--yes] [--only 镜id]
    plan 要点: meta.platform="pippit"，meta.generate_type（0=参考生成换内容，
    1=首尾帧高保真），每镜 refs=[参考图列表] + gen_duration（≥4）。
    无 --yes 只打印计划；提交间隔 65 秒（平台限频 1/分钟），自动轮询下载。"""
    plan_path, yes = argv[0], "--yes" in argv
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    plan = load_plan(plan_path)
    root = plan_dir(plan_path)
    meta = plan["meta"]
    shots = [s for s in plan["shots"] if not only or s["id"] == only]
    todo = [s for s in shots
            if not (root / s.get("file", f"shots/{s['id']}.mp4")).is_file()]
    pps = int(meta.get("points_per_second", 20))
    todo_secs = sum(int(s.get("gen_duration", 4)) for s in todo)
    print(f"待生成 {len(todo)} 镜 / {todo_secs}s ≈ {todo_secs * pps} 积分"
          f"（Pippit 余额：", end="")
    print(subprocess.run([_pippit_cli(), "get-credit-balance"],
                         capture_output=True, text=True).stdout.strip(), ")")
    if not todo:
        print("[ok] 全部镜头已就绪")
        return
    if not yes:
        print("[dry-run] 加 --yes 才真正生成（先向用户报价确认）")
        return

    cli = _pippit_cli()
    manifest_p = root / "shots" / "manifest.json"
    manifest = (json.loads(manifest_p.read_text(encoding="utf-8"))
                if manifest_p.is_file() else {})
    for n, s in enumerate(todo):
        sid = s["id"]
        args = [cli, "generate-video", "--prompt", s["prompt"],
                "--model", meta.get("model", "Seedance_2.5")]
        gt = meta.get("generate_type", 0)
        if gt:
            args += ["--generate-type", str(gt)]
        for ref in s.get("refs", []):
            rp = Path(ref)
            if not rp.is_file():
                rp = root / ref
            args += ["--image", str(rp.resolve())]
        args += ["--duration", str(int(s.get("gen_duration", 4))),
                 "--resolution", meta.get("resolution", "720p"),
                 "--ratio", meta.get("aspect_ratio", "9:16")]
        print(f"提交 {sid}（{s.get('gen_duration')}s）…", flush=True)
        rid = None
        for attempt in (1, 2):
            r = subprocess.run(args, capture_output=True, text=True)
            out = (r.stdout or "") + (r.stderr or "")
            try:
                d = json.loads(out.strip().splitlines()[-1])
                rid = {"thread_id": d["thread_id"], "run_id": d["run_id"]}
                break
            except Exception:
                print(f"  第{attempt}次失败：{out[:160]}", flush=True)
                if attempt == 1:
                    time.sleep(65)  # 平台限频 1 次/分钟
        if rid:
            manifest[sid] = rid
            print(f"  [ok] {rid['run_id']}", flush=True)
        else:
            print(f"  [dead] {sid} 连续失败，跳过（其余镜头继续）", flush=True)
        if n < len(todo) - 1:
            time.sleep(65)
    manifest_p.parent.mkdir(parents=True, exist_ok=True)
    manifest_p.write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    if not manifest:
        die("没有任何镜头提交成功")
    print("全部受理，进入轮询（每 60s，最长 30 分钟）…", flush=True)
    pending = dict(manifest)
    deadline = time.time() + 30 * 60
    while pending and time.time() < deadline:
        time.sleep(60)
        for sid in list(pending):
            m = pending[sid]
            r = subprocess.run([cli, "query-result", "--thread-id", m["thread_id"],
                                "--run-id", m["run_id"], "--download-dir",
                                str(root / "out")], capture_output=True, text=True)
            raw = r.stdout
            try:
                for line in raw.splitlines():
                    if line.startswith("data: "):
                        raw = line[6:]; break
                d = json.loads(raw)
            except Exception:
                continue
            if d.get("completed"):
                vids = d.get("videos") or []
                p = (vids[0].get("output_path", "") if vids else "")
                dest = root / s_file(sid, plan)
                if p and Path(p).is_file():
                    Path(p).replace(dest)
                    print(f"[{sid}] DONE -> {dest.name}", flush=True)
                else:
                    print(f"[{sid}] 完成但无文件：{str(d)[:160]}", flush=True)
                del pending[sid]
            else:
                err = (d.get("error_message") or "").strip()
                print(f"[{sid}] 渲染中 {err}", flush=True)
                if err:
                    del pending[sid]
    print("REMAIN:", list(pending), flush=True)


def s_file(sid: str, plan: dict) -> str:
    for s in plan["shots"]:
        if s["id"] == sid:
            return s.get("file", f"shots/{sid}.mp4")
    return f"shots/{sid}.mp4"


def _burn_srt_pil(in_mp4: Path, srt_path: Path, out_mp4: Path, root: Path):
    """当 ffmpeg 未编译 libass 时，使用 Pillow 渲染高清圆角中文字幕"""
    import re as _re
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    raw = srt_path.read_text(encoding="utf-8").strip()
    cues = []
    for blk in _re.split(r"\n\s*\n", raw):
        lns = [x.strip() for x in blk.splitlines() if x.strip()]
        if len(lns) >= 3 and "-->" in lns[1]:
            t_a, t_b = [s.strip() for s in lns[1].split("-->")]
            def _p(ts):
                hh, mm, rest = ts.replace(",", ".").split(":")
                return int(hh) * 3600 + int(mm) * 60 + float(rest)
            cues.append((_p(t_a), _p(t_b), " ".join(lns[2:])))

    f_cands = [str(root / "fonts" / "ZCOOLKuaiLe-Regular.ttf"), "/tmp/fonts/ZCOOLKuaiLe-Regular.ttf"]
    fnt = next((ImageFont.truetype(fp, 42) for fp in f_cands if Path(fp).is_file()), ImageFont.load_default())

    cap = cv2.VideoCapture(str(in_mp4))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    overlays = {}
    for _, _, txt in cues:
        im = Image.new("RGBA", (W, 130), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        bb = dr.textbbox((0, 0), txt, font=fnt)
        tw = bb[2] - bb[0] + 56
        x0 = max(20, (W - tw) // 2)
        dr.rounded_rectangle([x0, 18, min(W - 20, x0 + tw), 106], radius=44, fill=(28, 24, 22, 185), outline=(255, 240, 215, 175), width=2)
        dr.text((x0 + 28, 36), txt, font=fnt, fill=(255, 252, 245, 255), stroke_width=2, stroke_fill=(32, 22, 18, 220))
        overlays[txt] = np.asarray(im, dtype=np.uint8)

    p_enc = subprocess.Popen([
        _ffmpeg_bin(), "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
        "-i", str(in_mp4), "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-movflags", "+faststart", str(out_mp4),
    ], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    f_idx = 0
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        t = f_idx / fps
        for t0, t1, txt in cues:
            if t0 <= t <= t1:
                ov = overlays[txt]
                a = ov[..., 3:4].astype(np.float32) / 255.0
                y_pos = H - 220
                roi = rgb[y_pos : y_pos + 130].astype(np.float32)
                rgb[y_pos : y_pos + 130] = np.clip(roi * (1.0 - a) + ov[..., :3].astype(np.float32) * a, 0, 255).astype(np.uint8)
                break
        p_enc.stdin.write(rgb.tobytes())
        f_idx += 1
    cap.release()
    p_enc.stdin.close()
    if p_enc.wait() != 0:
        die("PIL 字幕合成失败")


def cmd_kgen(argv: list[str]):
    """开源 Kaggle/本地 GPU 视频生成通道（Lightricks/LTX-Video 双卡并行，0 元免费复刻）"""
    if not argv:
        die("用法: build.py kgen <plan.json> [--yes] [--only <镜id>]")
    sys.path.insert(0, str(Path(__file__).parent))
    import kgen_ltx
    yes = "--yes" in argv
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    kgen_ltx.run_kgen(argv[0], yes=yes, only=only)


COMMANDS = {"extract": cmd_extract, "balance": cmd_balance,
            "estimate": cmd_estimate, "gen": cmd_gen, "assemble": cmd_assemble,
            "upload": cmd_upload, "srt": cmd_srt, "tts": cmd_tts,
            "understand": cmd_understand, "pgen": cmd_pgen,
            "pbalance": cmd_balance_pippit, "kgen": cmd_kgen}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        die(f"用法: build.py <{'|'.join(COMMANDS)}> …（gen 加 --yes 才真正花钱）")
    try:
        COMMANDS[sys.argv[1]](sys.argv[2:])
    except RuntimeError as e:
        die(str(e))
