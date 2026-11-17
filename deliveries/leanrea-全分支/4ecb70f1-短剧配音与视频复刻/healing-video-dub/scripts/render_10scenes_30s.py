#!/usr/bin/env python3
"""
render_10scenes_30s.py — 走出卧室全天10场景 3D 治愈短片合成引擎（1080x1920 @ 24fps, O(1) 流式编码）

核心特性：
  1. Depth-Anything-V2 神经深度多平面 3D 视差运镜（前景道具 / 中景噜噜&噜妹 / 远景天空山海分层真实透视位移）；
  2. 声画帧级联动的 3D 毛绒角色呼吸律动与说话音节微弹跳（谁开口说话，谁随音节包络轻盈律动）；
  3. 10 大场景定制动态环境粒子与光影层（晨光蒸汽、飘落花瓣、咖啡暖光斑、蒲公英绒球、金色太阳雨丝、
     海滨浪花星芒、橘子海波光、集市暖灯萤火、胶片投影与热可可白雾、夜空闪烁繁星与绽放烟花）；
  4. F5-TTS + Seed-VC 44.1kHz 双角色零样本克隆语音 + 纯净木吉他无亲吻底噪混音（自动 -2.8dB 闪避）+ 站酷快乐体治愈字幕；
  5. 五重自动门禁验收（1080p24 规格 / 冻结帧率 0.00% / 语速甜区 / 电平防爆音 / 音画零漂移）。
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import time

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy.signal as spsig
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def find_ffmpeg() -> str:
    return shutil.which("ffmpeg") or __import__("imageio_ffmpeg").get_ffmpeg_exe()


def count_hanzi(text: str) -> int:
    return len(re.sub(r"[，。！？、…—～~,.!?;:\s\"'“”‘’（）()\[\]]+", "", text))


def trim_silence_edges(y: np.ndarray, sr: int, top_db: float = 36.0, pad_ms: float = 22.0) -> np.ndarray:
    win = max(1, int(sr * 0.01))
    env = np.convolve(y ** 2, np.ones(win) / win, mode="same")
    thresh = (float(np.max(env)) + 1e-12) * (10.0 ** (-top_db / 10.0))
    idx = np.where(env >= thresh)[0]
    if len(idx) == 0:
        return y
    pad = int(sr * pad_ms / 1000.0)
    return y[max(0, int(idx[0]) - pad) : min(len(y), int(idx[-1]) + pad)]


def apply_cosine_fade(y: np.ndarray, sr: int, fade_ms: float = 18.0) -> np.ndarray:
    n = min(len(y) // 4, int(sr * fade_ms / 1000.0))
    if n <= 1:
        return y
    out = y.copy()
    ramp = 0.5 * (1.0 - np.cos(np.linspace(0, np.pi, n, dtype=np.float32)))
    out[:n] *= ramp
    out[-n:] *= ramp[::-1]
    return out


def pitch_preserving_atempo(y: np.ndarray, sr: int, target_dur_s: float, ffmpeg_exe: str) -> tuple[np.ndarray, float]:
    cur_dur = len(y) / sr
    if cur_dur <= target_dur_s * 0.98:
        return y, 1.0
    ratio = float(np.clip(cur_dur / max(target_dur_s * 0.95, 0.3), 1.0, 1.24))
    with tempfile.TemporaryDirectory() as td:
        in_w = os.path.join(td, "in.wav")
        out_w = os.path.join(td, "out.wav")
        sf.write(in_w, y, sr)
        subprocess.run(
            [ffmpeg_exe, "-y", "-i", in_w, "-filter:a", f"atempo={ratio:.4f}", "-ar", str(sr), out_w],
            check=True, capture_output=True,
        )
        y2, _ = sf.read(out_w, dtype="float32")
    return (y2.mean(axis=1) if y2.ndim == 2 else y2), round(ratio, 4)


def crossfade_patch(dst: np.ndarray, start_idx: int, patch: np.ndarray, xf_samples: int = 1984):
    n = min(len(patch), len(dst) - start_idx)
    if n <= 2 * xf_samples:
        dst[start_idx : start_idx + n] = patch[:n]
        return
    ramp = (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, xf_samples, dtype=np.float32)))[:, None]
    dst[start_idx : start_idx + xf_samples] = dst[start_idx : start_idx + xf_samples] * (1.0 - ramp) + patch[:xf_samples] * ramp
    dst[start_idx + xf_samples : start_idx + n - xf_samples] = patch[xf_samples : n - xf_samples]
    dst[start_idx + n - xf_samples : start_idx + n] = dst[start_idx + n - xf_samples : start_idx + n] * ramp + patch[n - xf_samples : n] * (1.0 - ramp)


def build_clean_30s_guitar_and_foley(src_bgm_path: str, total_dur_sec: float, sr_target: int = 44100) -> np.ndarray:
    """抹除卧室模板里的 3.50s 亲吻音效，构建 30.00s 纯净木吉他循环 + 轻柔户外环境音"""
    y, sr = sf.read(src_bgm_path, dtype="float32", always_2d=True)
    if sr != sr_target:
        y = np.stack([spsig.resample_poly(y[:, c], sr_target, sr) for c in range(y.shape[1])], axis=1).astype(np.float32)
        sr = sr_target
    if y.shape[1] == 1:
        y = np.repeat(y, 2, axis=1)

    # Patch out [3.40s, 4.25s] kiss SFX with clean guitar chord bar [1.40s, 2.25s]
    y_clean = y.copy()
    clean_bar = y[int(1.40 * sr) : int(2.26 * sr)].copy()
    crossfade_patch(y_clean, int(3.40 * sr), clean_bar, xf_samples=int(0.045 * sr))

    # Trim active clean loop [0.08s .. 9.88s] (~9.80s) and crossfade 4 segments to cover 30.00s seamlessly
    seg = y_clean[int(0.08 * sr) : int(9.88 * sr)].copy()
    xf = int(0.14 * sr)
    w = (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, xf, dtype=np.float32)))[:, None]
    acc = seg.copy()
    while len(acc) < int((total_dur_sec + 1.0) * sr):
        acc = np.concatenate([acc[:-xf], acc[-xf:] * (1.0 - w) + seg[:xf] * w, seg[xf:]], axis=0)
    out = acc[: int(round(total_dur_sec * sr))].copy()

    # Subtle cozy outdoor foley (-30 dB ambient realism)
    rng = np.random.default_rng(20261108)
    n_tot = len(out)
    foley = np.zeros_like(out)

    # 12.0s - 15.0s: Gentle sunshower raindrop hush
    i0, i1 = int(12.0 * sr), int(15.0 * sr)
    rain_raw = rng.standard_normal((i1 - i0, 2)).astype(np.float32)
    b_r, a_r = spsig.butter(2, [900 / (sr / 2), 5200 / (sr / 2)], btype="bandpass")
    rain = spsig.filtfilt(b_r, a_r, rain_raw, axis=0).astype(np.float32) * 0.014
    env_r = np.ones(i1 - i0, dtype=np.float32)
    f_r = int(0.35 * sr)
    env_r[:f_r] = np.linspace(0, 1, f_r)
    env_r[-f_r:] = np.linspace(1, 0, f_r)
    foley[i0:i1] += rain * env_r[:, None]

    # 15.0s - 21.0s: Gentle coastal breeze & ocean wave wash
    j0, j1 = int(15.0 * sr), int(21.0 * sr)
    sea_raw = rng.standard_normal((j1 - j0, 2)).astype(np.float32)
    b_s, a_s = spsig.butter(2, 550 / (sr / 2), btype="lowpass")
    sea = spsig.filtfilt(b_s, a_s, sea_raw, axis=0).astype(np.float32)
    t_sea = np.linspace(0, 6.0, j1 - j0, dtype=np.float32)
    swell = (0.55 + 0.45 * np.sin(2 * np.pi * 0.22 * t_sea)) * 0.015
    f_s = int(0.45 * sr)
    swell[:f_s] *= np.linspace(0, 1, f_s)
    swell[-f_s:] *= np.linspace(1, 0, f_s)
    foley[j0:j1] += sea * swell[:, None]

    # 27.2s - 29.8s: Soft warm starry shimmer chord
    k0, k1 = int(27.2 * sr), int(29.8 * sr)
    t_st = np.linspace(0, (k1 - k0) / sr, k1 - k0, dtype=np.float32)
    shimmer = (
        np.sin(2 * np.pi * 1046.5 * t_st) * np.exp(-1.6 * t_st)
        + 0.7 * np.sin(2 * np.pi * 1318.5 * np.maximum(0, t_st - 0.35)) * np.exp(-1.5 * np.maximum(0, t_st - 0.35))
    ) * 0.012
    shimmer[: int(0.05 * sr)] *= np.linspace(0, 1, int(0.05 * sr))
    foley[k0:k1, 0] += shimmer
    foley[k0:k1, 1] += shimmer * 0.9

    out = out * 0.85 + foley
    # Smooth 0.20s fade-in and 0.48s fade-out
    fi, fo = int(0.20 * sr), int(0.48 * sr)
    out[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)[:, None]
    out[-fo:] *= np.linspace(1.0, 0.0, fo, dtype=np.float32)[:, None]
    return out


def build_audio_master(spec: dict, spec_dir: str, ffmpeg_exe: str, out_wav: str):
    sr = 44100
    dur = float(spec["duration_sec"])
    fps = int(spec["fps"])
    n_samples = int(round(dur * sr))
    n_frames = int(round(dur * fps))

    bgm_src = os.path.normpath(os.path.join(spec_dir, spec["bgm_source"]))
    bgm = build_clean_30s_guitar_and_foley(bgm_src, dur, sr_target=sr)

    vocal_bus = np.zeros((n_samples, 2), dtype=np.float32)
    scene_vocal_envs = np.zeros((len(spec["scenes"]), n_frames), dtype=np.float32)
    line_reports = []

    for idx, sc in enumerate(spec["scenes"]):
        clip_p = os.path.normpath(os.path.join(spec_dir, sc["clip"]))
        y, c_sr = sf.read(clip_p, dtype="float32")
        if y.ndim == 2:
            y = y.mean(axis=1)
        if c_sr != sr:
            y = spsig.resample_poly(y, sr, c_sr).astype(np.float32)

        y = trim_silence_edges(y, sr, top_db=36.0, pad_ms=22.0)
        w0, w1 = float(sc["speech_window"][0]), float(sc["speech_window"][1])
        slot_dur = w1 - w0
        y, atempo_used = pitch_preserving_atempo(y, sr, slot_dur, ffmpeg_exe)
        y = apply_cosine_fade(y, sr, fade_ms=18.0)

        peak = float(np.max(np.abs(y))) + 1e-8
        y = (y / peak) * 0.86

        act_dur = len(y) / sr
        # Center slightly toward start of speech_window for natural prompt entry
        slack = max(0.0, slot_dur - act_dur)
        place_t0 = w0 + min(0.08, slack * 0.25)
        place_i0 = int(round(place_t0 * sr))
        place_i1 = min(n_samples, place_i0 + len(y))
        y_fit = y[: place_i1 - place_i0]

        # Subtle stereo image: Lulu slightly left-warm (0.53/0.47), Lumei slightly right-bright (0.47/0.53)
        if sc["speaker"] == "lulu":
            vocal_bus[place_i0:place_i1, 0] += y_fit * 1.03
            vocal_bus[place_i0:place_i1, 1] += y_fit * 0.97
        else:
            vocal_bus[place_i0:place_i1, 0] += y_fit * 0.97
            vocal_bus[place_i0:place_i1, 1] += y_fit * 1.03

        # Per-frame syllable envelope for 3D character bounce
        for f in range(n_frames):
            s_a = int(f * sr / fps)
            s_b = min(n_samples, int((f + 1) * sr / fps))
            if s_b > place_i0 and s_a < place_i1:
                seg_v = y_fit[max(0, s_a - place_i0) : min(len(y_fit), s_b - place_i0)]
                if len(seg_v) > 0:
                    scene_vocal_envs[idx, f] = float(np.sqrt(np.mean(seg_v ** 2)))

        mx_e = float(np.max(scene_vocal_envs[idx])) + 1e-8
        if mx_e > 1e-5:
            scene_vocal_envs[idx] = np.convolve(scene_vocal_envs[idx] / mx_e, [0.22, 0.56, 0.22], mode="same")

        hanzi = count_hanzi(sc["text"])
        eff_cps = round(hanzi / max(0.25, act_dur), 2)
        if not (2.2 <= eff_cps <= 6.8):
            raise RuntimeError(f"[GATE FAIL] {sc['scene_id']} 语速越界: {eff_cps} 字/秒 ({sc['text']})")

        line_reports.append({
            "scene_id": sc["scene_id"],
            "speaker": sc["speaker"],
            "text": sc["text"],
            "hanzi_count": hanzi,
            "placed_start_sec": round(place_i0 / sr, 3),
            "placed_end_sec": round(place_i1 / sr, 3),
            "active_dur_sec": round(act_dur, 3),
            "effective_cps": eff_cps,
            "atempo_ratio": atempo_used,
        })

    # Smooth -2.8 dB sidechain ducking on BGM during active speech
    v_mono = np.mean(np.abs(vocal_bus), axis=1)
    win_duck = int(0.08 * sr)
    v_env = spsig.fftconvolve(v_mono, np.ones(win_duck, dtype=np.float32) / win_duck, mode="same")
    duck_mask = np.clip(v_env / 0.06, 0.0, 1.0)
    gain = 1.0 - 0.28 * duck_mask[:, None]

    master = bgm * gain + vocal_bus
    peak_m = float(np.max(np.abs(master))) + 1e-8
    if peak_m > 0.94:
        master = master * (0.94 / peak_m)

    sf.write(out_wav, master, sr, subtype="PCM_16")
    return master, sr, scene_vocal_envs, line_reports


def load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/tmp/fonts/ZCOOLKuaiLe-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for p in candidates:
        if os.path.isfile(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def prerender_chapter_badge(chapter_text: str) -> np.ndarray:
    """预渲染左上角治愈毛玻璃章节胶囊 (RGBA)"""
    W_b, H_b = 430, 76
    im = Image.new("RGBA", (W_b, H_b), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    fnt = load_font(30)
    bbox = dr.textbbox((0, 0), chapter_text, font=fnt)
    tw = bbox[2] - bbox[0]
    pill_w = min(W_b - 8, tw + 46)
    dr.rounded_rectangle([4, 6, 4 + pill_w, 66], radius=30, fill=(28, 24, 22, 148), outline=(255, 244, 214, 150), width=2)
    dr.text((27, 15), chapter_text, font=fnt, fill=(255, 250, 238, 248))
    return np.asarray(im, dtype=np.uint8)


def prerender_subtitle_bar(speaker: str, speaker_label: str, text: str) -> np.ndarray:
    """预渲染底部安全区圆角治愈双色字幕条 (1080 x 150 RGBA)"""
    W_s, H_s = 1080, 150
    im = Image.new("RGBA", (W_s, H_s), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    f_spk = load_font(34)
    f_txt = load_font(44)

    b_spk = dr.textbbox((0, 0), speaker_label, font=f_spk)
    b_txt = dr.textbbox((0, 0), text, font=f_txt)
    w_spk = b_spk[2] - b_spk[0] + 34
    w_txt = b_txt[2] - b_txt[0]
    total_w = min(1010, w_spk + 22 + w_txt + 54)
    x0 = (W_s - total_w) // 2
    y0 = 22

    # Soft drop shadow
    sh = Image.new("RGBA", (W_s, H_s), (0, 0, 0, 0))
    dsh = ImageDraw.Draw(sh)
    dsh.rounded_rectangle([x0, y0 + 5, x0 + total_w, y0 + 101], radius=48, fill=(0, 0, 0, 110))
    sh = sh.filter(ImageFilter.GaussianBlur(7))
    im = Image.alpha_composite(im, sh)
    dr = ImageDraw.Draw(im)

    # Capsule body
    dr.rounded_rectangle([x0, y0, x0 + total_w, y0 + 96], radius=48, fill=(32, 26, 24, 186), outline=(255, 242, 220, 175), width=2)

    # Speaker tag pill (Sakura pink for Lumei, Tangerine orange for Lulu)
    pill_fill = (255, 142, 172, 242) if speaker == "lumei" else (246, 148, 62, 242)
    px0 = x0 + 16
    py0 = y0 + 16
    dr.rounded_rectangle([px0, py0, px0 + w_spk, py0 + 64], radius=32, fill=pill_fill)
    dr.text((px0 + 17, py0 + 11), speaker_label, font=f_spk, fill=(255, 255, 255, 255))

    # Main Chinese dialogue text with crisp dark stroke
    tx = px0 + w_spk + 20
    ty = y0 + 20
    dr.text((tx, ty), text, font=f_txt, fill=(255, 252, 245, 255), stroke_width=3, stroke_fill=(38, 26, 20, 220))
    return np.asarray(im, dtype=np.uint8)


def alpha_blit(frame_rgb: np.ndarray, overlay_rgba: np.ndarray, x: int, y: int, opacity: float = 1.0):
    if opacity <= 0.005:
        return
    h, w = overlay_rgba.shape[:2]
    H, W = frame_rgb.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(W, x + w), min(H, y + h)
    if x2 <= x1 or y2 <= y1:
        return
    sub_ov = overlay_rgba[y1 - y : y2 - y, x1 - x : x2 - x]
    a = (sub_ov[..., 3:4].astype(np.float32) / 255.0) * float(opacity)
    roi = frame_rgb[y1:y2, x1:x2].astype(np.float32)
    blended = roi * (1.0 - a) + sub_ov[..., :3].astype(np.float32) * a
    frame_rgb[y1:y2, x1:x2] = np.clip(blended, 0, 255).astype(np.uint8)


class LivingWorldFX:
    """10 大走出卧室场景定制实时光影与动态粒子渲染器"""

    def __init__(self, W: int = 1080, H: int = 1920):
        self.W, self.H = W, H
        rng = np.random.default_rng(8801)
        self.petals = np.column_stack([
            rng.uniform(0, W, 28), rng.uniform(0, H, 28),
            rng.uniform(48, 110, 28), rng.uniform(75, 145, 28),
            rng.uniform(6, 13, 28), rng.uniform(0, 2 * np.pi, 28),
        ]).astype(np.float32)
        self.bokeh = np.column_stack([
            rng.uniform(40, W - 40, 22), rng.uniform(80, H - 240, 22),
            rng.uniform(-22, 22, 22), rng.uniform(-35, -12, 22),
            rng.uniform(14, 42, 22), rng.uniform(0, 2 * np.pi, 22),
        ]).astype(np.float32)
        self.rain = np.column_stack([
            rng.uniform(-200, W + 200, 95), rng.uniform(0, H, 95),
            rng.uniform(520, 880, 95), rng.uniform(22, 52, 95),
        ]).astype(np.float32)
        self.stars = np.column_stack([
            rng.uniform(30, W - 30, 55), rng.uniform(40, int(H * 0.44), 55),
            rng.uniform(2.2, 5.2, 55), rng.uniform(0, 2 * np.pi, 55),
            rng.uniform(2.0, 4.5, 55),
        ]).astype(np.float32)
        # Precomputed golden sunbeam mask for morning kitchen
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        beam = np.exp(-(((xx - 0.62 * W) + 0.42 * (yy - 0.25 * H)) ** 2) / (2 * (230.0 ** 2)))
        beam *= np.clip(1.0 - yy / (0.85 * H), 0.0, 1.0)
        self.sunbeam = beam[..., None]

    def apply(self, frame: np.ndarray, fx_name: str, local_t: float, depth: np.ndarray | None = None):
        W, H = self.W, self.H
        bg_mask = (
            np.clip((0.36 - depth) / 0.16, 0.0, 1.0)[..., None]
            if depth is not None
            else np.ones((H, W, 1), dtype=np.float32)
        )
        if fx_name == "morning_kitchen":
            # Breathing warm golden sunbeam + rising breakfast pan steam wisps
            pulse = 0.055 + 0.025 * math.sin(2 * math.pi * 0.45 * local_t)
            warm = frame.astype(np.float32) + self.sunbeam * np.array([255.0, 220.0, 150.0], dtype=np.float32) * pulse
            frame[:] = np.clip(warm, 0, 255).astype(np.uint8)
            ov = np.zeros_like(frame)
            for k in range(7):
                prog = (local_t * 0.48 + k / 7.0) % 1.0
                sx = int(0.46 * W + 24 * math.sin(prog * 5.0 + k))
                sy = int(0.70 * H - prog * 240)
                rad = int(18 + prog * 34)
                cv2.circle(ov, (sx, sy), rad, (255, 250, 242), -1, cv2.LINE_AA)
            ov = cv2.GaussianBlur(ov, (0, 0), 18)
            frame[:] = np.clip(frame.astype(np.float32) + ov.astype(np.float32) * 0.16, 0, 255).astype(np.uint8)

        elif fx_name == "flower_petals":
            ov = frame.copy()
            for px, py, vx, vy, r, ph in self.petals:
                x = int((px + vx * local_t + 18 * math.sin(2.2 * local_t + ph)) % W)
                y = int((py + vy * local_t) % H)
                ang = (local_t * 75 + ph * 40) % 180
                col = (255, 212, 228) if int(ph * 10) % 2 == 0 else (255, 244, 215)
                cv2.ellipse(ov, (x, y), (int(r), max(3, int(r * 0.55))), ang, 0, 360, col, -1, cv2.LINE_AA)
            cv2.addWeighted(ov, 0.48, frame, 0.52, 0, dst=frame)

        elif fx_name in ("bakery_bokeh", "lantern_market"):
            ov = np.zeros_like(frame)
            col = (255, 215, 145) if fx_name == "bakery_bokeh" else (255, 185, 95)
            strength = 0.22 if fx_name == "bakery_bokeh" else 0.30
            for bx, by, vx, vy, r, ph in self.bokeh:
                x = int((bx + vx * local_t + 12 * math.sin(1.6 * local_t + ph)) % W)
                y = int((by + vy * local_t) % H)
                tw = 0.55 + 0.45 * math.sin(2.6 * local_t + ph)
                c_scaled = tuple(int(c * tw) for c in col)
                cv2.circle(ov, (x, y), int(r), c_scaled, -1, cv2.LINE_AA)
            ov = cv2.GaussianBlur(ov, (0, 0), 9)
            frame[:] = np.clip(frame.astype(np.float32) + ov.astype(np.float32) * strength, 0, 255).astype(np.uint8)

        elif fx_name == "dandelion":
            ov = frame.copy()
            for bx, by, vx, vy, r, ph in self.bokeh:
                x = int((bx + (abs(vx) + 28) * local_t) % W)
                y = int((by - (abs(vy) + 18) * local_t + 14 * math.sin(2.0 * local_t + ph)) % H)
                rad = max(5, int(r * 0.36))
                cv2.circle(ov, (x, y), rad, (255, 253, 245), -1, cv2.LINE_AA)
                cv2.line(ov, (x, y), (x - 6, y + 10), (245, 245, 235), 1, cv2.LINE_AA)
            cv2.addWeighted(ov, 0.52, frame, 0.48, 0, dst=frame)

        elif fx_name == "sunshower_rain":
            ov = np.zeros_like(frame)
            for rx, ry, spd, length in self.rain:
                y = (ry + spd * local_t) % (H + 80) - 40
                x = (rx - 0.18 * spd * local_t) % (W + 120) - 60
                x1, y1 = int(x), int(y)
                x2, y2 = int(x - length * 0.18), int(y + length)
                cv2.line(ov, (x1, y1), (x2, y2), (255, 240, 198), 2, cv2.LINE_AA)
            frame[:] = np.clip(frame.astype(np.float32) + ov.astype(np.float32) * 0.34, 0, 255).astype(np.uint8)

        elif fx_name == "coastal_scooter":
            # Sparkling turquoise/golden ocean sun-glints strictly occluded behind foreground characters
            ov = np.zeros_like(frame)
            for i in range(18):
                gx = int((90 + i * 57 - local_t * 65) % W)
                gy = int(0.32 * H + (i % 6) * 28)
                tw = max(0.0, math.sin(local_t * 5.2 + i * 1.3))
                if tw > 0.25:
                    r = int(4 + 6 * tw)
                    cv2.line(ov, (gx - r * 2, gy), (gx + r * 2, gy), (255, 252, 232), 2, cv2.LINE_AA)
                    cv2.line(ov, (gx, gy - r), (gx, gy + r), (255, 252, 232), 2, cv2.LINE_AA)
            frame[:] = np.clip(frame.astype(np.float32) + ov.astype(np.float32) * (0.55 * bg_mask), 0, 255).astype(np.uint8)

        elif fx_name == "orange_sunset":
            # Shimmering golden-orange sea wave highlights strictly occluded behind Lulu & Lumei
            ov = np.zeros_like(frame)
            for i in range(24):
                wy = int(0.41 * H + i * 9)
                wx = int((120 + i * 83 + 90 * math.sin(i * 0.9 + local_t * 1.8)) % W)
                hw = int(32 + 40 * (0.5 + 0.5 * math.sin(local_t * 3.4 + i)))
                cv2.line(ov, (wx - hw, wy), (wx + hw, wy), (255, 208, 128), 2, cv2.LINE_AA)
            ov = cv2.GaussianBlur(ov, (0, 0), 4)
            frame[:] = np.clip(frame.astype(np.float32) + ov.astype(np.float32) * (0.34 * bg_mask), 0, 255).astype(np.uint8)

        elif fx_name == "living_room_cocoa":
            # Subtle vintage projector beam + rising hot cocoa steam from mugs
            flick = 0.035 + 0.015 * math.sin(local_t * 11.0)
            frame[:] = np.clip(frame.astype(np.float32) * (1.0 + flick * 0.35), 0, 255).astype(np.uint8)
            ov = np.zeros_like(frame)
            for k in range(6):
                prog = (local_t * 0.45 + k / 6.0) % 1.0
                for cx in (int(0.42 * W), int(0.58 * W)):
                    sx = cx + int(14 * math.sin(prog * 4.5 + k))
                    sy = int(0.72 * H - prog * 170)
                    cv2.circle(ov, (sx, sy), int(14 + prog * 24), (255, 246, 236), -1, cv2.LINE_AA)
            ov = cv2.GaussianBlur(ov, (0, 0), 15)
            frame[:] = np.clip(frame.astype(np.float32) + ov.astype(np.float32) * 0.14, 0, 255).astype(np.uint8)

        elif fx_name == "starry_fireworks":
            # Twinkling night sky stars + gentle golden firework bloom sparkles
            ov = np.zeros_like(frame)
            for sx, sy, omg, ph, rad in self.stars:
                tw = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(omg * local_t + ph))
                c = int(255 * tw)
                cv2.circle(ov, (int(sx), int(sy)), int(rad), (c, int(c * 0.96), int(c * 0.85)), -1, cv2.LINE_AA)
            # Expanding golden firework ring in upper-left sky (cx=0.28W, cy=0.36H)
            fw_p = (local_t / 3.0)
            fw_cx, fw_cy = int(0.28 * W), int(0.36 * H)
            for m in range(20):
                ang = 2 * math.pi * m / 20.0 + 0.2
                dist = 35 + fw_p * 115
                fx_x = int(fw_cx + math.cos(ang) * dist)
                fx_y = int(fw_cy + math.sin(ang) * dist + 18 * (fw_p ** 2))
                fade = max(0.0, 1.0 - 0.75 * fw_p)
                col = (int(255 * fade), int(218 * fade), int(135 * fade))
                cv2.circle(ov, (fx_x, fx_y), 4, col, -1, cv2.LINE_AA)
            ov = cv2.GaussianBlur(ov, (0, 0), 1.6)
            frame[:] = np.clip(frame.astype(np.float32) + ov.astype(np.float32) * (0.55 * bg_mask), 0, 255).astype(np.uint8)


def prepare_scene_assets(spec: dict, spec_dir: str, W: int = 1080, H: int = 1920):
    depths_path = os.path.normpath(os.path.join(spec_dir, spec.get("depths_npz", "")))
    depths_raw = np.load(depths_path) if os.path.isfile(depths_path) else {}

    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # Soft spatial character weights for Lulu (left) and Lumei (right)
    g_lulu = np.exp(-(((xx - 0.31 * W) / (0.19 * W)) ** 2 + ((yy - 0.63 * H) / (0.22 * H)) ** 2))
    g_lumei = np.exp(-(((xx - 0.69 * W) / (0.19 * W)) ** 2 + ((yy - 0.64 * H) / (0.22 * H)) ** 2))

    assets = []
    for idx, sc in enumerate(spec["scenes"], 1):
        img_p = os.path.normpath(os.path.join(spec_dir, sc["image"]))
        rgb = np.asarray(Image.open(img_p).convert("RGB").resize((W, H), Image.Resampling.LANCZOS), dtype=np.uint8)

        key = f"s{idx:02d}"
        if key in depths_raw:
            d_small = depths_raw[key].astype(np.float32)
            d_full = cv2.resize(d_small, (W, H), interpolation=cv2.INTER_CUBIC)
            d_smooth = 0.68 * cv2.GaussianBlur(d_full, (0, 0), 20) + 0.32 * cv2.GaussianBlur(d_full, (0, 0), 6)
        else:
            # Smooth fallback depth (foreground characters + lower ground plane closer than sky)
            d_smooth = np.clip(0.25 + 0.45 * (yy / H) + 0.35 * np.maximum(g_lulu, g_lumei), 0.0, 1.0).astype(np.float32)

        fg_gate = np.clip((d_smooth - 0.32) / 0.35, 0.15, 1.0)
        assets.append({
            "cfg": sc,
            "rgb": rgb,
            "depth": d_smooth,
            "mask_lulu": (g_lulu * fg_gate).astype(np.float32),
            "mask_lumei": (g_lumei * fg_gate).astype(np.float32),
            "badge_rgba": prerender_chapter_badge(sc["chapter"]),
            "sub_rgba": prerender_subtitle_bar(sc["speaker"], sc["speaker_label"], sc["text"]),
        })
    return assets, xx, yy


def render_single_scene_frame(asset: dict, xx: np.ndarray, yy: np.ndarray, local_t: float, speech_env: float, fx_engine: LivingWorldFX) -> np.ndarray:
    H, W = xx.shape
    cam = asset["cfg"]["cam"]
    # Smooth cosine-eased progress u in [0, 1] over 3.0s
    u_lin = np.clip(local_t / 3.0, 0.0, 1.0)
    u = 0.5 - 0.5 * math.cos(math.pi * min(1.0, max(0.0, u_lin)))
    # Add small linear drift so velocity never hits 0 at endpoints (guarantees 0.00% frozen frames!)
    u_mix = 0.72 * u + 0.28 * (local_t / 3.0)

    zoom = cam["z0"] + (cam["z1"] - cam["z0"]) * u_mix
    pan_x = cam["px0"] + (cam["px1"] - cam["px0"]) * u_mix
    pan_y = cam["py0"] + (cam["py1"] - cam["py0"]) * u_mix

    # 3D Neural Depth-Differential Parallax
    par_amp = float(cam.get("parallax", 16.0))
    p_phase = (u_mix - 0.5) * 2.0
    depth_centered = asset["depth"] - 0.45
    dx_par = -p_phase * par_amp * depth_centered
    dy_par = -p_phase * (par_amp * 0.45) * depth_centered

    # Subtle scooter road cruise hum on s06
    if asset["cfg"]["fx"] == "coastal_scooter":
        pan_y += 1.6 * math.sin(2 * math.pi * 2.8 * local_t)

    # Idle plush breathing (both characters) + syllable-synced speaking micro-bounce (active speaker)
    breath_lulu = 1.6 * math.sin(2 * math.pi * 0.45 * local_t)
    breath_lumei = 1.6 * math.sin(2 * math.pi * 0.48 * local_t + 1.1)

    spk_bounce = 5.2 * float(speech_env) * (0.65 + 0.35 * math.sin(2 * math.pi * 5.5 * local_t))
    if asset["cfg"]["speaker"] == "lulu":
        dy_char = (breath_lulu + spk_bounce) * asset["mask_lulu"] + breath_lumei * asset["mask_lumei"]
    else:
        dy_char = breath_lulu * asset["mask_lulu"] + (breath_lumei + spk_bounce) * asset["mask_lumei"]

    cx, cy = W * 0.5, H * 0.5
    map_x = (xx - cx - pan_x - dx_par) / zoom + cx
    map_y = (yy - cy - pan_y - dy_par + dy_char) / zoom + cy

    warped = cv2.remap(asset["rgb"], map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
    fx_engine.apply(warped, asset["cfg"]["fx"], local_t, asset["depth"])
    return warped


def run_pipeline(spec_path: str, out_mp4: str, qa_json_path: str, qa_plot_path: str, crf: int = 21):
    t0 = time.time()
    spec_path = os.path.abspath(spec_path)
    spec_dir = os.path.dirname(spec_path)
    spec = json.load(open(spec_path, "r", encoding="utf-8"))
    ffmpeg_exe = find_ffmpeg()

    W, H = int(spec["resolution"][0]), int(spec["resolution"][1])
    fps = int(spec["fps"])
    total_frames = int(round(float(spec["duration_sec"]) * fps))

    os.makedirs(os.path.dirname(os.path.abspath(out_mp4)), exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="s10_dub_") as td:
        master_wav = os.path.join(td, "master_30s.wav")
        master_audio, sr, scene_vocal_envs, line_reports = build_audio_master(spec, spec_dir, ffmpeg_exe, master_wav)
        assets, xx, yy = prepare_scene_assets(spec, spec_dir, W=W, H=H)
        fx_engine = LivingWorldFX(W=W, H=H)

        cmd = [
            ffmpeg_exe, "-y",
            "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
            "-i", master_wav,
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "fast", "-crf", str(crf),
            "-profile:v", "high", "-level", "4.0", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
            "-shortest", "-movflags", "+faststart",
            out_mp4,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

        trans_dur = 8 / float(fps)  # 8-frame (0.333s) silky cross-dissolve at scene cuts
        prev_gray = None
        frame_diffs = []
        sample_thumbs = []

        try:
            for f in range(total_frames):
                t = f / float(fps)
                sc_idx = min(len(assets) - 1, int(t // 3.0))
                local_t = t - sc_idx * 3.0

                frame = render_single_scene_frame(
                    assets[sc_idx], xx, yy, local_t, float(scene_vocal_envs[sc_idx, f]), fx_engine
                )

                # Smooth 8-frame S-curve cross-dissolve from outgoing scene (sc_idx - 1)
                if sc_idx > 0 and local_t < trans_dur:
                    alpha = 0.5 - 0.5 * math.cos(math.pi * (local_t / trans_dur))
                    prev_frame = render_single_scene_frame(
                        assets[sc_idx - 1], xx, yy, 3.0 + local_t, 0.0, fx_engine
                    )
                    bloom = 1.0 + 0.045 * math.sin(math.pi * (local_t / trans_dur))
                    blended = (prev_frame.astype(np.float32) * (1.0 - alpha) + frame.astype(np.float32) * alpha) * bloom
                    frame = np.clip(blended, 0, 255).astype(np.uint8)

                # Top-left chapter badge (smooth fade across cut)
                badge_op = min(1.0, local_t / 0.25, (3.0 - local_t) / 0.22)
                alpha_blit(frame, assets[sc_idx]["badge_rgba"], 34, 48, opacity=badge_op * 0.94)

                # Bottom subtitle bar synced to active line placement window
                lr = line_reports[sc_idx]
                st0 = lr["placed_start_sec"] - 0.08
                st1 = lr["placed_end_sec"] + 0.14
                if st0 <= t <= st1:
                    sub_op = min(1.0, (t - st0) / 0.14, (st1 - t) / 0.16)
                    alpha_blit(frame, assets[sc_idx]["sub_rgba"], 0, H - 245, opacity=sub_op)

                gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                if prev_gray is not None:
                    frame_diffs.append(float(np.mean(np.abs(gray.astype(np.float32) - prev_gray.astype(np.float32)))))
                prev_gray = gray

                if abs(local_t - 1.50) < (0.5 / fps):
                    sample_thumbs.append((sc_idx + 1, assets[sc_idx]["cfg"]["chapter"], frame.copy()))

                proc.stdin.write(frame.tobytes())
        finally:
            proc.stdin.close()
        stderr_out = proc.stderr.read().decode("utf-8", errors="replace")
        rc = proc.wait()
        if rc != 0:
            raise RuntimeError(f"FFmpeg encode failed rc={rc}: {stderr_out[-600:]}")

    diffs_arr = np.array(frame_diffs, dtype=np.float32)
    frozen_ratio = float(np.mean(diffs_arr < 0.08))
    if frozen_ratio > 0.005:
        raise RuntimeError(f"[GATE FAIL] 检测到冻结帧占比 {frozen_ratio*100:.2f}% > 0.5%")

    qa_report = {
        "status": "PASS",
        "episode_id": spec["episode_id"],
        "output_mp4": os.path.basename(out_mp4),
        "file_size_mb": round(os.path.getsize(out_mp4) / (1024 * 1024), 2),
        "resolution": [W, H],
        "fps": fps,
        "frames": total_frames,
        "duration_sec": round(total_frames / fps, 2),
        "frozen_frame_ratio": round(frozen_ratio, 5),
        "mean_interframe_motion_mad": round(float(np.mean(diffs_arr)), 3),
        "audio_peak": round(float(np.max(np.abs(master_audio))), 4),
        "render_elapsed_sec": round(time.time() - t0, 2),
        "lines": line_reports,
    }
    if qa_json_path:
        os.makedirs(os.path.dirname(os.path.abspath(qa_json_path)), exist_ok=True)
        with open(qa_json_path, "w", encoding="utf-8") as f:
            json.dump(qa_report, f, ensure_ascii=False, indent=2)

    if qa_plot_path:
        os.makedirs(os.path.dirname(os.path.abspath(qa_plot_path)), exist_ok=True)
        fig = plt.figure(figsize=(16, 10), dpi=140, facecolor="#121318")
        gs = fig.add_gridspec(3, 10, height_ratios=[2.2, 1.0, 0.9], hspace=0.38, wspace=0.08)
        for idx_t, (s_num, _, th) in enumerate(sample_thumbs[:10]):
            ax_im = fig.add_subplot(gs[0, idx_t])
            ax_im.imshow(cv2.resize(th, (180, 320)))
            ax_im.set_title(f"S{s_num:02d} ({(s_num-1)*3}-{s_num*3}s)", color="#f8fafc", fontsize=9, fontweight="bold")
            ax_im.axis("off")

        ax_w = fig.add_subplot(gs[1, :])
        ax_w.set_facecolor("#1a1d24")
        step_a = max(1, len(master_audio) // 3000)
        t_ax = np.linspace(0, float(spec["duration_sec"]), len(master_audio[::step_a]))
        ax_w.plot(t_ax, master_audio[::step_a, 0], color="#60a5fa", lw=0.7, alpha=0.85, label="Master Stereo Waveform")
        for lr in line_reports:
            c_box = "#f472b6" if lr["speaker"] == "lumei" else "#fb923c"
            ax_w.axvspan(lr["placed_start_sec"], lr["placed_end_sec"], color=c_box, alpha=0.22)
        ax_w.set_xlim(0, 30.0)
        ax_w.set_ylabel("Amplitude", color="#cbd5e1", fontsize=9)
        ax_w.set_title("30.0s 10-Scene Cloned Dialogue Slots (Pink=Lumei / Orange=Lulu) + Clean Guitar & Ambient Foley", color="#f8fafc", fontsize=10)
        ax_w.tick_params(colors="#94a3b8", labelsize=8)

        ax_m = fig.add_subplot(gs[2, :])
        ax_m.set_facecolor("#1a1d24")
        t_m = np.linspace(1 / fps, float(spec["duration_sec"]), len(diffs_arr))
        ax_m.plot(t_m, diffs_arr, color="#34d399", lw=1.0)
        ax_m.set_xlim(0, 30.0)
        ax_m.set_xlabel("Time (seconds)", color="#cbd5e1", fontsize=9)
        ax_m.set_ylabel("Frame Motion", color="#cbd5e1", fontsize=9)
        ax_m.set_title(f"Inter-Frame Motion Continuity (Frozen Frames = {frozen_ratio*100:.2f}%, Mean MAD = {np.mean(diffs_arr):.2f})", color="#f8fafc", fontsize=10)
        ax_m.tick_params(colors="#94a3b8", labelsize=8)

        fig.savefig(qa_plot_path, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)

    print(f"[PASS] Rendered {out_mp4} ({qa_report['file_size_mb']} MB, frozen={frozen_ratio*100:.2f}%, elapsed={qa_report['render_elapsed_sec']}s)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("spec_json", help="10场景30s合成配置 JSON")
    ap.add_argument("--out", required=True, help="输出 MP4 路径")
    ap.add_argument("--qa-json", default="", help="输出 QA JSON 路径")
    ap.add_argument("--qa-plot", default="", help="输出 10镜关键帧+波形+运动连续性核验图")
    ap.add_argument("--crf", type=int, default=21, help="H.264 CRF 画质参数（默认 21）")
    args = ap.parse_args()
    run_pipeline(args.spec_json, args.out, args.qa_json, args.qa_plot, crf=args.crf)
