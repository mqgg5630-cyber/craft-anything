#!/usr/bin/env python3
"""
kgen_ltx.py — video-clone-lite 开源 Kaggle/本地 GPU 视频生成后端（替代付费 Pippit / apiz 通道）

基于 Lightricks/LTX-Video-0.9.5 (LTXConditionPipeline / LTXImageToVideoPipeline, 2B DiT 真实时空视频扩散模型)：
  1. 自动检测单卡 (1x T4/P100) 或 Kaggle 双卡 (2x Tesla T4 = 32GB VRAM) 多进程并行分片加速；
  2. 先以 FP32 预编码全部 S-A-C-S-C 分镜提示词（彻底规避 T5-XXL 在 Turing FP16 下的溢出问题），随后完全卸载释放显存；
  3. 逐镜以真实角色场景锚定图 (refs/S01..S10) 驱动生成 73 帧 @ 24fps (3.04s) 连续 AI 动态镜头；
  4. 自动封装对应镜头的克隆角色对白音轨 (48kHz 立体声)，无缝对接 `build.py assemble plan.json`。
"""
import gc
import inspect
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np


def find_ffmpeg() -> str:
    sys_ff = shutil.which("ffmpeg")
    if sys_ff:
        return sys_ff
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def trim_and_place_dialogue(audio_path: str | None, total_dur: float, ffmpeg_exe: str, sr: int = 48000) -> np.ndarray:
    """将单镜角色克隆干声裁切静音并居中安放在 [0.34s, total_dur-0.28s] 安全口播窗内"""
    import soundfile as sf
    import scipy.signal as spsig

    n_tot = int(round(total_dur * sr))
    track = np.zeros((n_tot, 2), dtype=np.float32)
    if not audio_path or not os.path.isfile(audio_path):
        return track

    y, c_sr = sf.read(audio_path, dtype="float32")
    if y.ndim == 2:
        y = y.mean(axis=1)
    if c_sr != sr:
        y = spsig.resample_poly(y, sr, c_sr).astype(np.float32)

    win = max(1, int(sr * 0.01))
    env = np.convolve(y ** 2, np.ones(win) / win, mode="same")
    thresh = (float(np.max(env)) + 1e-12) * (10.0 ** (-36.0 / 10.0))
    idx = np.where(env >= thresh)[0]
    if len(idx) > 0:
        pad = int(0.02 * sr)
        y = y[max(0, int(idx[0]) - pad) : min(len(y), int(idx[-1]) + pad)]

    slot_dur = max(0.8, min(3.0, total_dur) - 0.62)
    cur_dur = len(y) / sr
    if cur_dur > slot_dur * 0.98:
        ratio = float(np.clip(cur_dur / (slot_dur * 0.95), 1.0, 1.24))
        with tempfile.TemporaryDirectory() as td:
            iw, ow = os.path.join(td, "in.wav"), os.path.join(td, "out.wav")
            sf.write(iw, y, sr)
            subprocess.run([ffmpeg_exe, "-y", "-i", iw, "-filter:a", f"atempo={ratio:.4f}", "-ar", str(sr), ow],
                           check=True, capture_output=True)
            y, _ = sf.read(ow, dtype="float32")
            if y.ndim == 2:
                y = y.mean(axis=1)

    nf = min(len(y) // 4, int(0.018 * sr))
    if nf > 1:
        ramp = 0.5 * (1.0 - np.cos(np.linspace(0, np.pi, nf, dtype=np.float32)))
        y[:nf] *= ramp
        y[-nf:] *= ramp[::-1]

    peak = float(np.max(np.abs(y))) + 1e-8
    y = (y / peak) * 0.88

    i0 = int(round(0.34 * sr))
    i1 = min(n_tot, i0 + len(y))
    track[i0:i1, 0] = y[: i1 - i0]
    track[i0:i1, 1] = y[: i1 - i0]
    return track


def resolve_ltx_repo(preferred: str) -> tuple[str, str]:
    """自动探测具备完整 diffusers model_index.json + 2B safetensors 的最优 LTX-Video 仓库"""
    from huggingface_hub import HfApi
    import diffusers

    api = HfApi()
    cands = []
    for c in [preferred, "Lightricks/LTX-Video-0.9.5", "Lightricks/LTX-Video"]:
        if c and c not in cands:
            cands.append(c)
    for cand in cands:
        try:
            info = api.model_info(cand)
            rfiles = [f.rfilename for f in (info.siblings or [])]
            has_idx = "model_index.json" in rfiles
            has_te = any(fn.startswith("text_encoder/") and fn.endswith(".safetensors") for fn in rfiles)
            has_tr = any(fn.startswith("transformer/") and fn.endswith(".safetensors") for fn in rfiles)
            if has_idx and has_te and has_tr:
                mode = "condition" if ("0.9.5" in cand and hasattr(diffusers, "LTXConditionPipeline")) else "i2v"
                return cand, mode
        except Exception as e:
            print(f"[kgen] probe {cand} skipped: {e}", flush=True)
    return "Lightricks/LTX-Video", "i2v"


def precompute_t5_embeddings(shots: list[dict], model_repo: str, out_pt: str):
    import torch
    from transformers import T5EncoderModel, T5TokenizerFast
    from diffusers import LTXImageToVideoPipeline

    t0 = time.time()
    n_gpu = torch.cuda.device_count()
    print(f"[kgen] Pre-encoding {len(shots)} S-A-C-S-C prompts with FP32 T5-XXL from {model_repo} (GPUs={n_gpu})...", flush=True)

    tokenizer = T5TokenizerFast.from_pretrained(model_repo, subfolder="tokenizer")
    if n_gpu >= 2:
        max_mem = {0: "11GiB", 1: "11GiB", "cpu": "24GiB"}
        dmap = "auto"
    elif n_gpu == 1:
        max_mem = {0: "10GiB", "cpu": "24GiB"}
        dmap = "auto"
    else:
        max_mem = None
        dmap = None

    text_encoder = T5EncoderModel.from_pretrained(
        model_repo,
        subfolder="text_encoder",
        torch_dtype=torch.float32,
        low_cpu_mem_usage=True,
        device_map=dmap,
        max_memory=max_mem,
    ).eval()

    pipe_enc = LTXImageToVideoPipeline(
        scheduler=None, vae=None, text_encoder=text_encoder, tokenizer=tokenizer, transformer=None
    )
    first_dev = next(text_encoder.parameters()).device
    neg_prompt = (
        "worst quality, low quality, blurry, inconsistent motion, deformed face, distorted snout, "
        "extra limbs, mutated hands, morphing clothes, flickering, jittery, watermark, text, subtitle, logo"
    )

    embeds = {}
    with torch.no_grad():
        for s in shots:
            sid = s["id"]
            p_txt = s.get("prompt_en") or s.get("prompt", "")
            pe, pam, npe, npam = pipe_enc.encode_prompt(
                prompt=p_txt,
                negative_prompt=neg_prompt,
                do_classifier_free_guidance=True,
                num_videos_per_prompt=1,
                max_sequence_length=160,
                device=first_dev,
                dtype=torch.float32,
            )
            assert not torch.isnan(pe).any(), f"NaN in T5 prompt_embeds for {sid}"
            embeds[sid] = {
                "pe": pe.to(torch.float16).cpu(),
                "pam": pam.cpu(),
                "npe": npe.to(torch.float16).cpu(),
                "npam": npam.cpu(),
            }

    torch.save(embeds, out_pt)
    del pipe_enc, text_encoder, tokenizer
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print(f"[kgen] T5-XXL prompt embeddings saved in {time.time() - t0:.1f}s (VRAM freed)", flush=True)


def gpu_worker_process(gpu_id: int, worker_shots: list[dict], root_dir: str, meta: dict, model_repo: str, pipe_mode: str, embeds_pt: str, result_json: str):
    """独立进程绑定单张 GPU 跑 LTX-Video 3D 时空扩散推理"""
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
    import torch
    import soundfile as sf
    import diffusers
    from PIL import Image

    dev = "cuda:0" if torch.cuda.is_available() else "cpu"
    gen_w = int(meta.get("gen_width", 512))
    gen_h = int(meta.get("gen_height", 896))
    out_w = int(meta.get("width", 1080))
    out_h = int(meta.get("height", 1920))
    fps = int(meta.get("fps", 24))
    steps = int(meta.get("num_inference_steps", 32))
    cfg_scale = float(meta.get("guidance_scale", 4.5))

    t_load0 = time.time()
    use_dtype = torch.float16
    if torch.cuda.is_available() and torch.cuda.get_device_capability(0)[0] >= 8:
        use_dtype = torch.bfloat16

    pipe_cls = diffusers.LTXConditionPipeline if pipe_mode == "condition" else diffusers.LTXImageToVideoPipeline
    pipe = pipe_cls.from_pretrained(
        model_repo,
        text_encoder=None,
        tokenizer=None,
        torch_dtype=use_dtype,
    ).to(dev)
    if hasattr(pipe.vae, "enable_tiling"):
        pipe.vae.enable_tiling()

    ts_aware = bool(getattr(pipe.vae.config, "timestep_conditioning", False))
    call_params = set(inspect.signature(pipe.__call__).parameters.keys())

    embeds = torch.load(embeds_pt, map_location="cpu", weights_only=False)
    ffmpeg_exe = find_ffmpeg()
    root = Path(root_dir)
    stats = []
    print(f"[GPU-{gpu_id}] Loaded {pipe_cls.__name__} ({model_repo}, dtype={use_dtype}, ts_vae={ts_aware}) in {time.time()-t_load0:.1f}s, assigned {len(worker_shots)} shots", flush=True)

    for idx, s in enumerate(worker_shots):
        sid = s["id"]
        t_s0 = time.time()
        dest = root / s.get("file", f"shots/{sid}.mp4")
        dest.parent.mkdir(parents=True, exist_ok=True)

        ref_rel = s["refs"][0]
        ref_p = Path(ref_rel) if Path(ref_rel).is_file() else (root / ref_rel)
        init_img = Image.open(ref_p).convert("RGB").resize((gen_w, gen_h), Image.Resampling.LANCZOS)

        dur_req = float(s.get("gen_duration", s.get("duration", 3.0)))
        k8 = max(4, int(math.ceil((dur_req * fps - 1) / 8.0)))
        num_frames = 8 * k8 + 1

        em = embeds[sid]
        gen = torch.Generator(device=dev).manual_seed(int(s.get("seed", 2026 + idx * 17 + gpu_id * 101)))

        kw = dict(
            image=init_img,
            prompt=None,
            negative_prompt=None,
            prompt_embeds=em["pe"].to(device=dev, dtype=use_dtype),
            prompt_attention_mask=em["pam"].to(device=dev),
            negative_prompt_embeds=em["npe"].to(device=dev, dtype=use_dtype),
            negative_prompt_attention_mask=em["npam"].to(device=dev),
            width=gen_w,
            height=gen_h,
            num_frames=num_frames,
            frame_rate=fps,
            num_inference_steps=steps,
            guidance_scale=cfg_scale,
            decode_timestep=0.05 if ts_aware else 0.0,
            decode_noise_scale=0.025 if ts_aware else None,
            generator=gen,
            output_type="pil",
        )
        if "guidance_rescale" in call_params:
            kw["guidance_rescale"] = 0.7
        if "image_cond_noise_scale" in call_params and ts_aware:
            kw["image_cond_noise_scale"] = 0.025

        with torch.no_grad():
            out = pipe(**kw)
        frames = out.frames[0]

        arrs = [np.asarray(fr, dtype=np.float32) for fr in frames]
        diffs = [float(np.mean(np.abs(arrs[k] - arrs[k - 1]))) for k in range(1, len(arrs))]
        mean_mad = round(float(np.mean(diffs)), 3)
        frozen_pct = round(float(np.mean(np.array(diffs) < 0.05)) * 100.0, 2)
        std_val = float(np.std(arrs[len(arrs) // 2]))
        if np.isnan(std_val) or std_val < 5.0:
            raise RuntimeError(f"[GPU-{gpu_id}] Degenerate/NaN frame output (std={std_val}) on {sid}")

        with tempfile.TemporaryDirectory(prefix=f"shot_{sid}_") as td:
            wav_p = os.path.join(td, "dial.wav")
            aud_rel = s.get("dialogue_audio", "")
            aud_p = str(root / aud_rel) if aud_rel else ""
            aud_arr = trim_and_place_dialogue(aud_p, len(frames) / float(fps), ffmpeg_exe, sr=48000)
            sf.write(wav_p, aud_arr, 48000, subtype="PCM_16")

            p_enc = subprocess.Popen([
                ffmpeg_exe, "-y",
                "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{gen_w}x{gen_h}", "-r", str(fps), "-i", "-",
                "-i", wav_p,
                "-vf", f"scale={out_w}:{out_h}:flags=lanczos,unsharp=3:3:0.45:3:3:0.0,format=yuv420p",
                "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-profile:v", "high", "-level", "4.0",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-shortest", "-movflags", "+faststart", str(dest),
            ], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            for fr in frames:
                p_enc.stdin.write(fr.tobytes())
            p_enc.stdin.close()
            err_b = p_enc.stderr.read()
            if p_enc.wait() != 0:
                raise RuntimeError(f"FFmpeg shot mux failed on {sid}: {err_b.decode('utf-8', 'replace')[-400:]}")

        dt = round(time.time() - t_s0, 2)
        stat = {
            "id": sid,
            "gpu_id": gpu_id,
            "frames": len(frames),
            "gen_res": [gen_w, gen_h],
            "out_res": [out_w, out_h],
            "elapsed_sec": dt,
            "mean_motion_mad": mean_mad,
            "frozen_pct": frozen_pct,
            "file_kb": round(dest.stat().st_size / 1024, 1),
        }
        stats.append(stat)
        print(f"[GPU-{gpu_id}] DONE {sid} -> {dest.name} ({len(frames)}f, motion_mad={mean_mad}, frozen={frozen_pct}%, {dt}s)", flush=True)

    Path(result_json).write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")


def run_kgen(plan_path: str, yes: bool = False, only: str | None = None) -> dict:
    p = Path(plan_path).resolve()
    root = p.parent
    plan = json.loads(p.read_text(encoding="utf-8"))
    meta = plan["meta"]
    shots = [s for s in plan["shots"] if not only or s["id"] == only]
    todo = [s for s in shots if not (root / s.get("file", f"shots/{s['id']}.mp4")).is_file()]

    tot_s = sum(float(s.get("duration", 3.0)) for s in todo)
    pref_repo = meta.get("hf_model", "Lightricks/LTX-Video-0.9.5")
    print(f"[video-clone-lite · kgen] 共 {len(shots)} 镜，待生成 {len(todo)} 镜（{tot_s:.1f}s）| 模型: {pref_repo} | 预计费用: 0.00 元（开源 Kaggle GPU 免费算力）", flush=True)
    if not todo:
        print("[ok] 全部镜头已就绪，可直接运行 build.py assemble", flush=True)
        return {"shots": [], "total_elapsed_sec": 0.0}
    if not yes:
        print("[dry-run] 加 --yes 启动 Kaggle/本地 GPU 真实视频扩散生成", flush=True)
        return {"dry_run": True}

    import torch
    import multiprocessing as mp

    t0 = time.time()
    n_gpu = torch.cuda.device_count()
    gpu_names = [torch.cuda.get_device_name(i) for i in range(n_gpu)] if n_gpu > 0 else ["cpu"]
    model_repo, pipe_mode = resolve_ltx_repo(pref_repo)
    print(f"[kgen] Hardware detected: {n_gpu} GPU(s): {gpu_names} | Resolved repo: {model_repo} ({pipe_mode})", flush=True)

    # Pre-download transformer/vae/scheduler once in main process so 2 workers don't race on HF cache!
    from huggingface_hub import snapshot_download
    print(f"[kgen] Pre-caching {model_repo} weights (shared across GPUs)...", flush=True)
    snapshot_download(repo_id=model_repo, ignore_patterns=["*.ckpt", "*.pt", "*.bin"])

    with tempfile.TemporaryDirectory(prefix="kgen_ltx_") as td:
        embeds_pt = os.path.join(td, "t5_embeds.pt")
        precompute_t5_embeddings(todo, model_repo, embeds_pt)

        if n_gpu >= 2 and len(todo) >= 2:
            ctx = mp.get_context("spawn")
            procs = []
            res_files = []
            for gid in range(min(n_gpu, 2)):
                shard = todo[gid::2]
                rj = os.path.join(td, f"stats_gpu{gid}.json")
                res_files.append(rj)
                pr = ctx.Process(
                    target=gpu_worker_process,
                    args=(gid, shard, str(root), meta, model_repo, pipe_mode, embeds_pt, rj),
                )
                pr.start()
                procs.append(pr)
            for pr in procs:
                pr.join()
                if pr.exitcode != 0:
                    raise RuntimeError(f"Multi-GPU worker exited with code {pr.exitcode}")
            all_stats = []
            for rj in res_files:
                all_stats.extend(json.loads(Path(rj).read_text(encoding="utf-8")))
            all_stats.sort(key=lambda x: x["id"])
        else:
            rj = os.path.join(td, "stats_gpu0.json")
            gpu_worker_process(0, todo, str(root), meta, model_repo, pipe_mode, embeds_pt, rj)
            all_stats = json.loads(Path(rj).read_text(encoding="utf-8"))

    report = {
        "engine": f"video-clone-lite/kgen ({model_repo})",
        "pipe_mode": pipe_mode,
        "gpu_count": n_gpu,
        "gpu_names": gpu_names,
        "total_elapsed_sec": round(time.time() - t0, 2),
        "shots": all_stats,
    }
    rep_path = root / "shots" / "kgen_report.json"
    rep_path.parent.mkdir(parents=True, exist_ok=True)
    rep_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] 全部 {len(all_stats)} 镜真实 AI 动态视频生成完毕（总耗时 {report['total_elapsed_sec']}s），运行 build.py assemble 合成最终成片", flush=True)
    return report


if __name__ == "__main__":
    yes_flag = "--yes" in sys.argv
    only_id = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    run_kgen(sys.argv[1], yes=yes_flag, only=only_id)
