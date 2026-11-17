#!/usr/bin/env python3
"""
clone_and_dub_a1.py — A1 丝滑模板换文案配音核心引擎（门禁校验 + F5-TTS/Seed-VC 语音克隆 + 零漂移卡点混音 + H.264 零重编封装 + 自动 QA）

支持两种工作模式：
  1. 端到端本地/云端 GPU 克隆 + 合成（传入 --clone-on-the-fly，自动调用开源 F5-TTS + Seed-VC 44.1kHz）：
     python3 scripts/clone_and_dub_a1.py examples/spec-weekend-snuggle.json \
       --clone-on-the-fly --engine hybrid --out examples/output/weekend_snuggle_a1_10s.mp4
  2. 直接使用已克隆干声极速卡点合成（0.4 秒出片，适合微调混音电平或批量验收）：
     python3 scripts/clone_and_dub_a1.py examples/spec-weekend-snuggle.json \
       --out examples/output/weekend_snuggle_a1_10s.mp4 --qa-plot examples/output/weekend_snuggle_timeline_qa.png
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from argparse import Namespace

import numpy as np
import scipy.signal as spsig
import soundfile as sf


def find_ffmpeg() -> str:
    sys_ff = shutil.which("ffmpeg")
    if sys_ff:
        return sys_ff
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def count_hanzi_and_words(text: str) -> int:
    cleaned = re.sub(r"[，。！？、…—～~,.!?;:\s\"'“”‘’（）()\[\]]+", "", text)
    return len(cleaned)


def trim_silence_edges(y: np.ndarray, sr: int, top_db: float = 36.0, pad_ms: float = 20.0) -> np.ndarray:
    """温和裁除首尾静音（保留字头呼吸气口），避免台词过早或拖尾侵入亲吻音效区"""
    win = max(1, int(sr * 0.01))
    env = np.convolve(y ** 2, np.ones(win) / win, mode="same")
    peak_e = float(np.max(env)) + 1e-12
    thresh = peak_e * (10.0 ** (-top_db / 10.0))
    idx = np.where(env >= thresh)[0]
    if len(idx) == 0:
        return y
    pad = int(sr * pad_ms / 1000.0)
    i0 = max(0, int(idx[0]) - pad)
    i1 = min(len(y), int(idx[-1]) + pad)
    return y[i0:i1]


def pitch_preserving_atempo(y: np.ndarray, sr: int, target_dur_s: float, ffmpeg_exe: str) -> tuple[np.ndarray, float]:
    """当有效语音略超槽位时，调用 FFmpeg WSOLA atempo 保调微缩（严控在 0.85x ~ 1.22x 安全区间）"""
    cur_dur = len(y) / sr
    if cur_dur <= target_dur_s * 0.99:
        return y, 1.0
    ratio = cur_dur / max(target_dur_s * 0.96, 0.25)
    ratio = float(np.clip(ratio, 1.0, 1.25))
    with tempfile.TemporaryDirectory() as td:
        in_w = os.path.join(td, "in.wav")
        out_w = os.path.join(td, "out.wav")
        sf.write(in_w, y, sr)
        subprocess.run(
            [ffmpeg_exe, "-y", "-i", in_w, "-filter:a", f"atempo={ratio:.4f}", "-ar", str(sr), out_w],
            check=True, capture_output=True,
        )
        y2, _ = sf.read(out_w, dtype="float32")
    if y2.ndim == 2:
        y2 = y2.mean(axis=1)
    return y2, round(ratio, 4)


def apply_cosine_fade(y: np.ndarray, sr: int, fade_ms: float = 16.0) -> np.ndarray:
    n = min(len(y) // 4, int(sr * fade_ms / 1000.0))
    if n <= 1:
        return y
    out = y.copy()
    ramp = 0.5 * (1.0 - np.cos(np.linspace(0, np.pi, n, dtype=np.float32)))
    out[:n] *= ramp
    out[-n:] *= ramp[::-1]
    return out


def synthesize_line_gpu_or_cpu(ref_audio: str, ref_text: str, gen_text: str, target_dur: float, out_flac: str, engine: str = "hybrid", seed_vc_dir: str = ""):
    """调用本地开源 F5-TTS (+ 可选 Seed-VC 44.1kHz) 零样本生成新台词"""
    import torch
    import torchaudio

    def _load(uri, frame_offset=0, num_frames=-1, normalize=True, channels_first=True, **kw):
        data, sr = sf.read(str(uri), dtype="float32", always_2d=True)
        data = data[frame_offset : (frame_offset + num_frames if num_frames > 0 else None)]
        return torch.from_numpy(data.T.copy() if channels_first else data.copy()), sr

    def _save(uri, src, sample_rate, channels_first=True, **kw):
        arr = src.detach().cpu().numpy()
        sf.write(str(uri), arr.T if (arr.ndim == 2 and channels_first) else arr, sample_rate)

    torchaudio.load, torchaudio.save = _load, _save
    device = "cuda" if torch.cuda.is_available() else "cpu"
    ref_y, ref_sr = sf.read(ref_audio, dtype="float32")
    ref_dur = len(ref_y) / ref_sr

    from f5_tts.api import F5TTS
    tts = F5TTS(model="F5TTS_v1_Base", device=device)
    tmp_f5 = out_flac + ".f5.wav"
    wav, sr, _ = tts.infer(
        ref_file=ref_audio,
        ref_text=ref_text,
        gen_text=gen_text,
        file_wave=tmp_f5,
        fix_duration=ref_dur + target_dur,
        nfe_step=32 if device == "cuda" else 16,
        cfg_strength=2.0,
        remove_silence=False,
        seed=42,
    )
    if engine == "f5tts" or not seed_vc_dir or not os.path.isdir(seed_vc_dir):
        sf.write(out_flac, wav, sr, format="FLAC")
        if os.path.exists(tmp_f5):
            os.remove(tmp_f5)
        return

    old_cwd = os.getcwd()
    sys.path.insert(0, os.path.abspath(seed_vc_dir))
    tmp_sv_dir = tempfile.mkdtemp(prefix="sv_")
    try:
        os.chdir(seed_vc_dir)
        import inference as sv_inf
        a = Namespace(
            source=os.path.abspath(tmp_f5), target=os.path.abspath(ref_audio), output=tmp_sv_dir,
            diffusion_steps=35 if device == "cuda" else 15, length_adjust=1.0, inference_cfg_rate=0.7,
            f0_condition=False, auto_f0_adjust=True, semi_tone_shift=0, checkpoint=None, config=None,
            fp16=(device == "cuda"),
        )
        sv_inf.main(a)
        emitted = glob.glob(os.path.join(tmp_sv_dir, "*.wav"))
        y_sv, sr_sv = sf.read(emitted[0], dtype="float32")
        sf.write(out_flac, y_sv, sr_sv, format="FLAC")
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(tmp_sv_dir, ignore_errors=True)
        if os.path.exists(tmp_f5):
            os.remove(tmp_f5)


def gate_validate(spec: dict, tpl: dict, profiles: dict) -> list[dict]:
    """门禁 1：在合成前校验字数语速、说话人存在性与动作音效禁区冲突"""
    slot_map = {s["slot_id"]: s for s in tpl["dialogue_slots"]}
    guards = tpl.get("sfx_guard_zones", [])
    resolved = []

    for item in spec["lines"]:
        sid = item["slot_id"]
        if sid not in slot_map:
            raise ValueError(f"[GATE FAIL] 未知 slot_id={sid}，可用槽位: {list(slot_map)}")
        slot = slot_map[sid]
        spk = item.get("speaker", slot["speaker"])
        if spk not in profiles:
            raise ValueError(f"[GATE FAIL] 未知 speaker={spk}，可用角色: {list(profiles)}")

        t0 = float(item.get("start_sec", slot["start_sec"]))
        t1 = float(item.get("end_sec", slot["end_sec"]))
        dur = t1 - t0
        n_chars = count_hanzi_and_words(item["text"])
        cps = n_chars / max(dur, 0.1)
        if cps > 6.8 or cps < 2.2:
            raise ValueError(
                f"[GATE FAIL] {sid} 台词「{item['text']}」({n_chars}字 / {dur:.2f}s = {cps:.2f}字/秒) 超出自然语速区间 [2.2, 6.8] 字/秒！"
            )
        for gz in guards:
            overlap = min(t1, gz["end_sec"]) - max(t0, gz["start_sec"])
            if overlap > 0.01:
                raise ValueError(
                    f"[GATE FAIL] {sid} [{t0:.2f}s..{t1:.2f}s] 侵入动作音效禁区 {gz['id']} [{gz['start_sec']}s..{gz['end_sec']}s]！"
                )
        resolved.append({
            "slot_id": sid,
            "speaker": spk,
            "text": item["text"],
            "start_sec": t0,
            "end_sec": t1,
            "slot_dur_sec": round(dur, 3),
            "char_count": n_chars,
            "chars_per_sec": round(cps, 2),
            "clip": item.get("clip", ""),
        })
    return resolved


def main():
    ap = argparse.ArgumentParser(description="A1 丝滑 3D 模板换文案零漂移克隆配音与自动验收引擎")
    ap.add_argument("spec_json", help="分句台词配置文件 (如 examples/spec-weekend-snuggle.json)")
    ap.add_argument("--out", default="", help="输出 MP4 路径")
    ap.add_argument("--qa-json", default="", help="输出 QA 验收报告 JSON 路径")
    ap.add_argument("--qa-plot", default="", help="输出时间轴波形与音效禁区核验图 PNG 路径")
    ap.add_argument("--clone-on-the-fly", action="store_true", help="调用本地 F5-TTS (+ Seed-VC) 现场生成克隆干声")
    ap.add_argument("--engine", choices=["hybrid", "f5tts"], default="hybrid")
    ap.add_argument("--seed-vc-dir", default="", help="本地 seed-vc 仓库目录（hybrid 模式可选）")
    ap.add_argument("--vocal-gain-db", type=float, default=0.0, help="人声相对标准电平增益微调 (dB)")
    ap.add_argument("--bgm-gain-db", type=float, default=-1.5, help="伴奏与亲吻音效轨增益微调 (dB)")
    args = ap.parse_args()

    spec_abs = os.path.abspath(args.spec_json)
    spec_dir = os.path.dirname(spec_abs)
    spec = json.load(open(spec_abs, "r", encoding="utf-8"))

    tpl_path = os.path.normpath(os.path.join(spec_dir, spec["template"]))
    tpl_dir = os.path.dirname(tpl_path)
    tpl = json.load(open(tpl_path, "r", encoding="utf-8"))
    profiles = json.load(open(os.path.join(tpl_dir, tpl["speaker_profiles_file"]), "r", encoding="utf-8"))

    resolved_lines = gate_validate(spec, tpl, profiles)
    ffmpeg_exe = find_ffmpeg()

    bgm_path = os.path.join(tpl_dir, tpl["bgm_sfx_file"])
    bgm_stereo, target_sr = sf.read(bgm_path, dtype="float32", always_2d=True)
    if bgm_stereo.shape[1] == 1:
        bgm_stereo = np.repeat(bgm_stereo, 2, axis=1)
    total_samples = len(bgm_stereo)
    vocal_bus = np.zeros(total_samples, dtype=np.float32)

    placement_report = []
    for item in resolved_lines:
        clip_rel = item["clip"]
        clip_path = os.path.normpath(os.path.join(spec_dir, clip_rel)) if clip_rel else os.path.join(spec_dir, f"_gen_{item['slot_id']}.flac")
        if args.clone_on_the_fly or not os.path.isfile(clip_path):
            prof = profiles[item["speaker"]]
            ref_audio = os.path.join(tpl_dir, prof["ref_audio"])
            os.makedirs(os.path.dirname(clip_path), exist_ok=True)
            synthesize_line_gpu_or_cpu(
                ref_audio, prof["ref_text"], item["text"], item["slot_dur_sec"],
                clip_path, engine=args.engine, seed_vc_dir=args.seed_vc_dir,
            )

        y_raw, sr_in = sf.read(clip_path, dtype="float32")
        if y_raw.ndim == 2:
            y_raw = y_raw.mean(axis=1)
        if sr_in != target_sr:
            g = np.gcd(sr_in, target_sr)
            y_raw = spsig.resample_poly(y_raw, target_sr // g, sr_in // g).astype(np.float32)

        y_trim = trim_silence_edges(y_raw, target_sr, top_db=36.0, pad_ms=22.0)
        y_fit, atempo_used = pitch_preserving_atempo(y_trim, target_sr, item["slot_dur_sec"], ffmpeg_exe)
        y_fit = apply_cosine_fade(y_fit, target_sr, fade_ms=16.0)

        # Normalize per-line active RMS to -15.5 dBFS (0.168) for consistent intimate dialogue clarity
        rms = float(np.sqrt(np.mean(y_fit ** 2))) + 1e-8
        target_rms = 0.168 * (10.0 ** (args.vocal_gain_db / 20.0))
        y_norm = y_fit * (target_rms / rms)
        peak = float(np.max(np.abs(y_norm)))
        if peak > 0.92:
            y_norm *= 0.92 / peak

        # Center slightly toward slot start (+30ms natural reaction offset) while strictly clamping before slot end
        s_idx = int(round((item["start_sec"] + 0.02) * target_sr))
        max_e_idx = min(total_samples, int(round(item["end_sec"] * target_sr)))
        avail = max(0, max_e_idx - s_idx)
        y_placed = y_norm[:avail]
        if len(y_placed) < len(y_norm):
            y_placed = apply_cosine_fade(y_placed, target_sr, fade_ms=18.0)

        vocal_bus[s_idx : s_idx + len(y_placed)] += y_placed
        actual_s = round(s_idx / target_sr, 3)
        actual_e = round((s_idx + len(y_placed)) / target_sr, 3)
        placement_report.append({
            **item,
            "placed_start_sec": actual_s,
            "placed_end_sec": actual_e,
            "placed_dur_sec": round(actual_e - actual_s, 3),
            "atempo_ratio": atempo_used,
            "slot_fill_pct": round((actual_e - actual_s) / item["slot_dur_sec"] * 100.0, 1),
        })

    # Subtle sidechain ducking (-2.5 dB) on BGM ONLY while characters are actively speaking, keeping 3.50s kiss SFX at 100%!
    win_sc = int(target_sr * 0.04)
    v_env = np.sqrt(np.convolve(vocal_bus ** 2, np.ones(win_sc) / win_sc, mode="same"))
    duck = np.where(v_env > 0.02, 0.76, 1.0).astype(np.float32)
    smooth_win = int(target_sr * 0.06)
    duck = np.convolve(duck, np.ones(smooth_win) / smooth_win, mode="same").astype(np.float32)

    bgm_scale = float(10.0 ** (args.bgm_gain_db / 20.0))
    mix_stereo = bgm_stereo * (bgm_scale * duck[:, None]) + vocal_bus[:, None]
    # Soft limiter ceiling at -0.8 dBFS (0.912)
    mix_peak = float(np.max(np.abs(mix_stereo))) + 1e-9
    if mix_peak > 0.912:
        mix_stereo = np.tanh(mix_stereo / mix_peak * 1.15) / np.tanh(1.15) * 0.912

    out_mp4 = os.path.abspath(args.out or os.path.join(spec_dir, "output", f"{spec['episode_id']}_a1.mp4"))
    os.makedirs(os.path.dirname(out_mp4), exist_ok=True)
    master_wav = out_mp4[:-4] + "_master_44k.wav"
    sf.write(master_wav, mix_stereo, target_sr, subtype="PCM_16")

    video_tpl_path = os.path.join(tpl_dir, tpl["video_file"])
    subprocess.run([
        ffmpeg_exe, "-y",
        "-i", video_tpl_path,
        "-i", master_wav,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "256k", "-ar", str(target_sr), "-ac", "2",
        "-shortest", "-movflags", "+faststart",
        out_mp4,
    ], check=True, capture_output=True)

    # Gate 2: Post-mux Automated QA Verification
    guard_leak_max = 0.0
    for gz in tpl.get("sfx_guard_zones", []):
        g0, g1 = int(gz["start_sec"] * target_sr), int(gz["end_sec"] * target_sr)
        leak = float(np.max(np.abs(vocal_bus[g0:g1]))) if g1 > g0 else 0.0
        guard_leak_max = max(guard_leak_max, leak)

    import cv2
    cap = cv2.VideoCapture(out_mp4)
    out_fps = round(float(cap.get(cv2.CAP_PROP_FPS)), 2)
    out_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    out_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    qa_status = "PASS" if (guard_leak_max < 1e-4 and out_w == 1080 and out_h == 1920 and abs(out_fps - 24.0) < 0.2) else "FAIL"
    qa_data = {
        "status": qa_status,
        "episode_id": spec["episode_id"],
        "title": spec["title"],
        "output_mp4": out_mp4,
        "file_size_bytes": os.path.getsize(out_mp4),
        "video_spec": f"{out_w}x{out_h} @ {out_fps}fps ({out_frames} frames)",
        "audio_spec": f"{target_sr}Hz stereo AAC 256kbps (master WAV saved)",
        "sfx_guard_zone_vocal_leak": round(guard_leak_max, 6),
        "lines": placement_report,
    }

    qa_json_path = args.qa_json or (out_mp4[:-4] + "_qa.json")
    with open(qa_json_path, "w", encoding="utf-8") as f:
        json.dump(qa_data, f, ensure_ascii=False, indent=2)

    if args.qa_plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        t_ax = np.arange(total_samples) / target_sr
        fig_w = 16.5 if len(placement_report) > 6 else 13.0
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(fig_w, 6.0), sharex=True, dpi=145)
        fig.patch.set_facecolor("#14161d")
        for ax in (ax1, ax2):
            ax.set_facecolor("#1c1f29")
            ax.tick_params(colors="#dce1eb")
            for sp in ax.spines.values():
                sp.set_color("#3a4052")

        step = 40
        ax1.plot(t_ax[::step], vocal_bus[::step], color="#06d6a0", lw=0.8, label="Cloned Dialogue Bus (F5-TTS + Seed-VC 44.1kHz)")
        for idx_p, p in enumerate(placement_report):
            ax1.axvspan(p["start_sec"], p["end_sec"], color="#4cc9f0", alpha=0.14)
            y_lbl = 0.88 if (idx_p % 2 == 0 or len(placement_report) <= 6) else 0.66
            fs_lbl = 7.2 if len(placement_report) > 6 else 8.5
            ax1.text((p["start_sec"] + p["end_sec"]) / 2, y_lbl, f"{p['slot_id']}\n{p['speaker']} ({p['atempo_ratio']}x)",
                     ha="center", va="top", color="#e8f1f8", fontsize=fs_lbl, fontweight="bold")
        for idx_g, gz in enumerate(tpl.get("sfx_guard_zones", [])):
            lbl_g = "SFX Guard Zones (Cheek Kiss SFX - 0% Vocal Leak)" if idx_g == 0 else None
            ax1.axvspan(gz["start_sec"], gz["end_sec"], color="#ef476f", alpha=0.26, label=lbl_g)
        ax1.set_ylim(-0.95, 0.95)
        ax1.set_ylabel("Cloned Vocals", color="white")
        ax1.set_title(f"A1 New-Copy Dubbing QA Timeline [{qa_status}] — {spec['episode_id']} (1080x1920 @ 24fps)", color="white", fontsize=11.5, fontweight="bold")
        ax1.legend(loc="lower right", facecolor="#252a36", edgecolor="#3a4052", labelcolor="white", fontsize=8.5)

        bgm_m = bgm_stereo.mean(axis=1)
        ax2.plot(t_ax[::step], bgm_m[::step], color="#ffd166", lw=0.75, alpha=0.9, label="Original BGM + 3.50s Cheek Kiss SFX Stem")
        ax2.plot(t_ax[::step], mix_stereo.mean(axis=1)[::step], color="#4cc9f0", lw=0.55, alpha=0.55, label="Final Stereo Master Mix")
        ax2.set_ylim(-0.95, 0.95)
        ax2.set_xlabel("Time (seconds)", color="white")
        ax2.set_ylabel("BGM & Master", color="white")
        ax2.legend(loc="lower right", facecolor="#252a36", edgecolor="#3a4052", labelcolor="white", fontsize=8.5)

        plt.tight_layout()
        plt.savefig(args.qa_plot, facecolor=fig.get_facecolor())
        plt.close(fig)

    print(f"[{qa_status}] Generated A1 {total_samples/target_sr:.2f}s video: {out_mp4} ({os.path.getsize(out_mp4):,} B)")
    for p in placement_report:
        print(f"  - {p['slot_id']} [{p['placed_start_sec']:.2f}s..{p['placed_end_sec']:.2f}s] ({p['speaker']}): {p['text']} (fill={p['slot_fill_pct']}%, atempo={p['atempo_ratio']}x)")


if __name__ == "__main__":
    main()
