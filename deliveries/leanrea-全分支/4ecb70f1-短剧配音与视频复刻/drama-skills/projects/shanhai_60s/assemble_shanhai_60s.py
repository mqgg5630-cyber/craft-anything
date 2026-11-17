#!/usr/bin/env python3
"""
assemble_shanhai_60s.py — 《山海寻光记：赴一场四季星河》（v2 正版形象与音画同步精制版 · 60.000s / 1440f @ 24fps）
"""
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import scipy.signal as spsig
import soundfile as sf


def ass_ts(sec: float) -> str:
    sec = max(0.0, sec)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def synth_note(freq: float, dur: float, sr: int, timbre: str = "piano") -> np.ndarray:
    t = np.arange(int(dur * sr), dtype=np.float32) / sr
    if timbre == "piano":
        env = np.exp(-2.6 * t) * (1.0 - np.exp(-90.0 * t))
        sig = (
            1.00 * np.sin(2 * np.pi * freq * t)
            + 0.34 * np.sin(2 * np.pi * 2 * freq * t) * np.exp(-1.5 * t)
            + 0.13 * np.sin(2 * np.pi * 3 * freq * t) * np.exp(-2.8 * t)
            + 0.04 * np.sin(2 * np.pi * 4 * freq * t) * np.exp(-4.0 * t)
        )
        return (sig * env).astype(np.float32)
    elif timbre == "celesta":
        env = np.exp(-3.8 * t) * (1.0 - np.exp(-140.0 * t))
        sig = np.sin(2 * np.pi * freq * t) + 0.22 * np.sin(2 * np.pi * 2 * freq * t) + 0.08 * np.sin(2 * np.pi * 5.02 * freq * t) * np.exp(-6.0 * t)
        return (sig * env).astype(np.float32)
    else:
        att = np.clip(t / min(0.55, dur * 0.35), 0.0, 1.0)
        rel = np.clip((dur - t) / min(0.65, dur * 0.40), 0.0, 1.0)
        env = np.sin(0.5 * np.pi * att) * np.sin(0.5 * np.pi * rel)
        vib = 1.0 + 0.0020 * np.sin(2 * np.pi * 5.0 * t)
        ph = 2 * np.pi * np.cumsum(freq * vib) / sr
        sig = 0.74 * np.sin(ph) + 0.26 * np.sin(2 * ph + 0.3) + 0.10 * np.sin(3 * ph + 0.7)
        return (sig * env).astype(np.float32)


def synthesize_5chapter_score_and_foley(sr: int = 48000, total_s: float = 60.0) -> tuple[np.ndarray, dict[int, np.ndarray], np.ndarray]:
    n = int(round(total_s * sr))
    score = np.zeros((n, 2), dtype=np.float32)
    rng = np.random.default_rng(20261108)

    chords = [
        ([174.61, 220.00, 261.63, 329.63, 392.00], [523.25, 659.25, 783.99, 659.25], "piano"),
        ([196.00, 246.94, 293.66, 329.63, 392.00], [587.33, 659.25, 783.99, 880.00], "piano"),
        ([164.81, 246.94, 293.66, 392.00],         [659.25, 587.33, 493.88, 587.33], "piano"),
        ([220.00, 261.63, 329.63, 392.00, 493.88], [523.25, 659.25, 783.99, 987.77], "piano"),
        ([130.81, 196.00, 246.94, 293.66, 329.63], [523.25, 659.25, 783.99, 1046.5], "celesta"),
        ([174.61, 220.00, 261.63, 329.63, 440.00], [698.46, 659.25, 523.25, 659.25], "celesta"),
        ([146.83, 220.00, 261.63, 329.63, 440.00], [587.33, 659.25, 783.99, 659.25], "celesta"),
        ([196.00, 293.66, 349.23, 440.00, 493.88], [587.33, 698.46, 783.99, 987.77], "piano"),
        ([130.81, 196.00, 261.63, 329.63, 392.00], [659.25, 783.99, 1046.5, 783.99], "piano"),
        ([110.00, 220.00, 261.63, 329.63, 493.88], [523.25, 493.88, 440.00, 523.25], "piano"),
        ([174.61, 261.63, 329.63, 392.00, 440.00], [523.25, 659.25, 783.99, 659.25], "piano"),
        ([196.00, 261.63, 293.66, 392.00, 493.88], [587.33, 659.25, 783.99, 587.33], "piano"),
        ([174.61, 220.00, 261.63, 329.63, 392.00], [659.25, 783.99, 1046.5, 783.99], "celesta"),
        ([164.81, 246.94, 329.63, 392.00, 493.88], [783.99, 659.25, 587.33, 659.25], "celesta"),
        ([130.81, 196.00, 246.94, 293.66, 329.63, 523.25], [1046.5, 783.99, 659.25, 523.25], "piano"),
    ]

    bar_s = 4.00
    for b_idx, (pad_freqs, arp_freqs, lead_timbre) in enumerate(chords):
        t0 = b_idx * bar_s
        i0 = int(t0 * sr)
        for k, pf in enumerate(pad_freqs):
            pad = synth_note(pf, min(bar_s + 0.55, total_s - t0), sr, "pad") * 0.032
            pan = 0.35 + 0.30 * ((k % 3) / 2.0)
            i1 = min(n, i0 + len(pad))
            score[i0:i1, 0] += pad[: i1 - i0] * math.sqrt(1.0 - pan)
            score[i0:i1, 1] += pad[: i1 - i0] * math.sqrt(pan)

        step_s = bar_s / len(arp_freqs)
        for m_i, mf in enumerate(arp_freqs):
            nt0 = t0 + m_i * step_s
            ni0 = int(nt0 * sr)
            if ni0 >= n:
                break
            note = synth_note(mf, min(2.1, total_s - nt0), sr, lead_timbre) * (0.052 if lead_timbre == "piano" else 0.042)
            pan = 0.30 + 0.40 * ((m_i + b_idx) % 2)
            ni1 = min(n, ni0 + len(note))
            score[ni0:ni1, 0] += note[: ni1 - ni0] * math.sqrt(1.0 - pan)
            score[ni0:ni1, 1] += note[: ni1 - ni0] * math.sqrt(pan)

    for d_ms, g in [(115, 0.20), (235, 0.11)]:
        ds = int(d_ms * sr / 1000)
        score[ds:, 0] += score[:-ds, 1] * g
        score[ds:, 1] += score[:-ds, 0] * g

    amb_len = int(12.0 * sr)
    amb_acts: dict[int, np.ndarray] = {}
    t_amb = np.arange(amb_len, dtype=np.float32) / sr

    w1 = rng.standard_normal((amb_len, 2)).astype(np.float32)
    amb_acts[1] = spsig.lfilter(*spsig.butter(2, [140 / (sr / 2), 780 / (sr / 2)], btype="band"), w1, axis=0).astype(np.float32) * 0.008

    w2 = rng.standard_normal((amb_len, 2)).astype(np.float32)
    bed2 = spsig.lfilter(*spsig.butter(2, [220 / (sr / 2), 1100 / (sr / 2)], btype="band"), w2, axis=0).astype(np.float32) * 0.008
    for bt in [0.9, 3.2, 8.6]:
        bi, bl = int(bt * sr), int(0.16 * sr)
        tt = np.arange(bl, dtype=np.float32) / sr
        bed2[bi : bi + bl, int(bt * 3) % 2] += np.sin(2 * np.pi * (2500 + 550 * np.sin(2 * np.pi * 13 * tt)) * tt) * np.hanning(bl) * 0.010
    amb_acts[2] = bed2

    w3 = rng.standard_normal((amb_len, 2)).astype(np.float32)
    rain_env = np.clip(1.0 - (t_amb - 7.5) / 5.0, 0.32, 1.0)
    amb_acts[3] = spsig.lfilter(*spsig.butter(2, [450 / (sr / 2), 3600 / (sr / 2)], btype="band"), w3, axis=0).astype(np.float32) * (0.009 * rain_env[:, None])

    w4 = rng.standard_normal((amb_len, 2)).astype(np.float32)
    surf = 0.45 + 0.55 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.18 * t_amb - 0.5))
    amb_acts[4] = spsig.lfilter(*spsig.butter(2, [120 / (sr / 2), 1450 / (sr / 2)], btype="band"), w4, axis=0).astype(np.float32) * (0.011 * surf[:, None])

    w5 = rng.standard_normal((amb_len, 2)).astype(np.float32)
    amb_acts[5] = spsig.lfilter(*spsig.butter(2, [150 / (sr / 2), 980 / (sr / 2)], btype="band"), w5, axis=0).astype(np.float32) * 0.007

    foley = np.zeros((n, 2), dtype=np.float32)
    i_dand, l_dand = int(17.67 * sr), int(1.15 * sr)
    td = np.arange(l_dand, dtype=np.float32) / sr
    wind_sw = spsig.lfilter(*spsig.butter(2, [600 / (sr / 2), 2900 / (sr / 2)], btype="band"), rng.standard_normal((l_dand, 2)).astype(np.float32), axis=0)
    env_d = np.sin(np.pi * np.clip(td / 1.15, 0, 1)) ** 1.4
    sparkle_d = (np.sin(2 * np.pi * 1318.5 * td) + 0.6 * np.sin(2 * np.pi * 1760.0 * td)) * np.exp(-4.5 * td) * 0.012
    foley[i_dand : i_dand + l_dand] += wind_sw * (0.012 * env_d[:, None]) + sparkle_d[:, None]

    i_clink, l_clink = int(54.85 * sr), int(0.32 * sr)
    tc = np.arange(l_clink, dtype=np.float32) / sr
    ceramic = (np.sin(2 * np.pi * 1480.0 * tc) * np.exp(-26.0 * tc) + 0.55 * np.sin(2 * np.pi * 2890.0 * tc) * np.exp(-38.0 * tc) + 0.25 * np.sin(2 * np.pi * 4150.0 * tc) * np.exp(-55.0 * tc)) * (1.0 - np.exp(-400.0 * tc)) * 0.032
    foley[i_clink : i_clink + l_clink, 0] += ceramic
    foley[i_clink : i_clink + l_clink, 1] += ceramic * 0.92

    s15_start_s = 1332 / 24.0
    for dt_fw in (0.35, 1.55, 2.65):
        fi, fl = int((s15_start_s + dt_fw) * sr), int(1.0 * sr)
        if fi + fl < n:
            tt = np.arange(fl, dtype=np.float32) / sr
            fw = rng.standard_normal((fl, 2)).astype(np.float32)
            sh = spsig.lfilter(*spsig.butter(2, [110 / (sr / 2), 2400 / (sr / 2)], btype="band"), fw, axis=0).astype(np.float32) * (np.exp(-3.4 * tt) * (1.0 - np.exp(-38.0 * tt)))[:, None] * 0.018
            foley[fi : fi + fl] += sh

    return score, amb_acts, foley


def prepare_pure_studio_voice(flac_path: Path, sr: int = 48000) -> np.ndarray:
    y, c_sr = sf.read(str(flac_path), dtype="float32")
    if y.ndim == 2:
        y = y.mean(axis=1)
    if c_sr != sr:
        g = math.gcd(sr, c_sr)
        y = spsig.resample_poly(y, sr // g, c_sr // g).astype(np.float32)

    sos_hp = spsig.butter(2, 75.0 / (sr * 0.5), btype="highpass", output="sos")
    y = spsig.sosfiltfilt(sos_hp, y).astype(np.float32)

    nf = min(len(y) // 8, int(0.008 * sr))
    if nf > 1:
        ramp = 0.5 * (1.0 - np.cos(np.linspace(0, np.pi, nf, dtype=np.float32)))
        y[:nf] *= ramp
        y[-nf:] *= ramp[::-1]

    rms = float(np.sqrt(np.mean(y[np.abs(y) > 0.015] ** 2) + 1e-8)) if np.any(np.abs(y) > 0.015) else 0.12
    y = y * (0.21 / rms)
    y = np.tanh(y * 1.12) / np.tanh(1.12) * 0.88
    return np.column_stack([y, y]).astype(np.float32)


def write_ass_subtitles(ass_path: Path, placements: list[dict]):
    header = """[Script Info]
Title: 山海寻光记：赴一场四季星河（正版形象还原精制版）
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Dialogue,ZCOOL KuaiLe,52,&H00F8FAFF,&H0000FFFF,&H001B2230,&H78000000,0,0,0,0,100,100,1.5,0,1,4.2,2.0,2,64,64,155,1
Style: NarrationVO,ZCOOL KuaiLe,48,&H00D4F5FF,&H0000FFFF,&H00202838,&H80000000,0,0,0,0,100,100,2.0,0,1,4.0,2.0,2,72,72,165,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev_lines = []
    for p in placements:
        st_name = "NarrationVO" if p["voice_mode"] == "VO" else "Dialogue"
        txt = "{\\fad(120,140)}" + p["sub_display"]
        ev_lines.append(f"Dialogue: 0,{ass_ts(p['sub_in'])},{ass_ts(p['sub_out'])},{st_name},{p['speaker']},0,0,0,,{txt}")
    ass_path.write_text(header + "\n".join(ev_lines) + "\n", encoding="utf-8")


def write_drama_skills_cutlist(ep_dir: Path, shots: list[dict], windows: list[dict], voice_files: dict[int, str]):
    lines = [
        "# EP001 剪辑单\n",
        "- 成片目标时长：60.00 秒",
        "- 画幅与帧率：9:16 · 1080×1920 · 24fps",
        "- 交付响度：-16 LUFS",
        "- 字幕：硬字幕，台词逐字取自《剧本.md》，底部安全区内\n",
    ]
    for s, w in zip(shots, windows):
        idx = int(s["idx"])
        cid = f"CUT-EP001-{idx:03d}"
        vid_rel = f"制作成果/videos/{s['id']}.mp4"
        v_rel = f"制作成果/配音/{voice_files[idx]}"
        dur_s = round(w["flen"] / 24.0, 2)
        v_off = round(w["local_voice_s"], 2)
        ch_no = int(s["chapter"])
        lines.append(f"## {cid} · {s['title']}\n")
        lines.append(f"- 来源：{s['motion_id']} · {vid_rel}")
        lines.append("- 入点：0.00")
        lines.append(f"- 出点：{dur_s:.2f}")
        lines.append(f"- 时长：{dur_s:.2f}")
        lines.append(f"- 取舍：入点=首帧清晰切入{s['title']}；出点=台词与角色互动自然完成后叠化接下一镜")
        lines.append(f"- 声音：融合 44.1kHz Seed-VC 优选干声与第{ch_no}章自然环境声及治愈配乐")
        lines.append("- 画面：无")
        lines.append(f"- 字幕：{s['line']}")
        lines.append(f"- 配音：{v_off:.2f} {v_rel}")
        if idx in (1, 4, 7, 10, 13):
            lines.append(f"- 环境声：0.00 制作成果/环境声/act{ch_no}_ambience.flac（增益：-6）")
        lines.append("")
    (ep_dir / "剪辑单.md").write_text("\n".join(lines), encoding="utf-8")


def run_master_assembly(proj_dir: Path, raw_vid_dir: Path, ff_exe: str, fonts_dir: str) -> dict:
    ep_dir = proj_dir / "剧集" / "EP001"
    prod_dir = ep_dir / "制作成果"
    vid_dir, voc_dir, amb_dir, out_dir = prod_dir / "videos", prod_dir / "配音", prod_dir / "环境声", prod_dir / "成片"
    for d in (vid_dir, amb_dir, out_dir):
        d.mkdir(parents=True, exist_ok=True)

    staged_links = []
    for src_mp4 in sorted(raw_vid_dir.glob("SHOT-EP001-*.mp4")):
        dst_mp4 = vid_dir / src_mp4.name
        if dst_mp4.exists() or dst_mp4.is_symlink():
            dst_mp4.unlink()
        os.symlink(src_mp4.resolve(), dst_mp4)
        staged_links.append(dst_mp4)

    manifest = json.loads((proj_dir / "episode_manifest_60s.json").read_text(encoding="utf-8"))
    shots = manifest["shots"]
    windows = json.loads((proj_dir / "timeline_sync_v2.json").read_text(encoding="utf-8"))

    sr = 48000
    total_samples = 60 * sr
    score, amb_acts, foley = synthesize_5chapter_score_and_foley(sr=sr, total_s=60.0)

    amb_master = np.zeros((total_samples, 2), dtype=np.float32)
    for old_f in amb_dir.glob("*.flac"):
        old_f.unlink()
    for ch_no in range(1, 6):
        aw = amb_acts[ch_no]
        sf.write(str(amb_dir / f"act{ch_no}_ambience.flac"), aw, sr)
        s0 = (ch_no - 1) * 12 * sr
        amb_master[s0 : s0 + len(aw)] += aw

    voice_master = np.zeros((total_samples, 2), dtype=np.float32)
    speech_env = np.zeros(total_samples, dtype=np.float32)
    placements, voice_files = [], {}

    for s, w in zip(shots, windows):
        idx = int(s["idx"])
        v_path = sorted(voc_dir.glob(f"v{idx:02d}_*.flac"))[0]
        voice_files[idx] = v_path.name
        v_st = prepare_pure_studio_voice(v_path, sr=sr)
        v_in_s = float(w["global_voice_s"])
        i0 = int(round(v_in_s * sr))
        i1 = min(total_samples, i0 + len(v_st))
        voice_master[i0:i1] += v_st[: i1 - i0]
        speech_env[i0:i1] = 1.0
        placements.append({
            "idx": idx, "id": s["id"], "speaker": s["speaker"], "voice_mode": s["voice_mode"],
            "line": s["line"], "sub_display": s["sub_display"],
            "voice_in": round(v_in_s, 3), "voice_out": round(i1 / sr, 3),
            "sub_in": round(max(w["solo_in_s"] + 0.02, v_in_s - 0.05), 3),
            "sub_out": round(min(w["solo_out_s"] - 0.02, i1 / sr + 0.16), 3),
        })

    write_drama_skills_cutlist(ep_dir, shots, windows, voice_files)

    k_atk = int(0.16 * sr)
    duck_curve = np.convolve(speech_env, np.hanning(k_atk) / np.sum(np.hanning(k_atk)), mode="same")
    duck_gain = 1.0 - 0.49 * np.clip(duck_curve, 0.0, 1.0)
    mix = voice_master * 0.96 + score * duck_gain[:, None] + amb_master + foley

    fi_n, fo_n = int(0.35 * sr), int(0.85 * sr)
    mix[:fi_n] *= np.linspace(0.0, 1.0, fi_n, dtype=np.float32)[:, None]
    mix[-fo_n:] *= np.linspace(1.0, 0.0, fo_n, dtype=np.float32)[:, None]
    mix = np.tanh(mix * 1.06) / np.tanh(1.06)
    pk = float(np.max(np.abs(mix))) + 1e-8
    mix = (mix / pk) * (10.0 ** (-0.9 / 20.0))

    with tempfile.TemporaryDirectory(prefix="shanhai60_v2_") as td:
        td_p = Path(td)
        wav_p, ass_p, xfade_mp4 = td_p / "master_60s_v2.wav", td_p / "subs_60s_v2.ass", td_p / "xfade_60s_nosub.mp4"
        sf.write(str(wav_p), mix, sr, subtype="PCM_16")
        write_ass_subtitles(ass_p, placements)

        inputs, fc_parts = [], []
        for w, s in zip(windows, shots):
            inputs += ["-i", str(vid_dir / f"{s['id']}.mp4")]
            fc_parts.append(f"[{w['idx']-1}:v]trim=start_frame=0:end_frame={w['flen']},setpts=PTS-STARTPTS,fps=24,format=yuv420p[v{w['idx']}]")

        prev_lbl = "v1"
        for k in range(1, 15):
            nxt_w, cur_w = windows[k], windows[k - 1]
            out_lbl = f"x{k}"
            fc_parts.append(f"[{prev_lbl}][v{k+1}]xfade=transition=fade:duration={cur_w['out_xfade_s']:.6f}:offset={nxt_w['start_s']:.6f}[{out_lbl}]")
            prev_lbl = out_lbl
        fc_parts.append(f"[{prev_lbl}]fade=t=in:st=0:d=0.40,fade=t=out:st=59.25:d=0.75,format=yuv420p[vout]")

        r1 = subprocess.run([ff_exe, "-y", *inputs, "-filter_complex", ";".join(fc_parts), "-map", "[vout]", "-c:v", "libx264", "-preset", "fast", "-crf", "18.5", "-r", "24", "-frames:v", "1440", str(xfade_mp4)], capture_output=True, text=True)
        if r1.returncode != 0:
            raise RuntimeError(f"xfade pass failed:\n{r1.stderr[-1200:]}")

        final_mp4 = out_dir / "shanhai_xunguang_60s_final.mp4"
        esc_ass = str(ass_p).replace("\\", "/").replace(":", "\\:")
        esc_fd = str(fonts_dir).replace("\\", "/").replace(":", "\\:")
        r2 = subprocess.run([
            ff_exe, "-y", "-i", str(xfade_mp4), "-i", str(wav_p),
            "-vf", f"ass=filename='{esc_ass}':fontsdir='{esc_fd}',format=yuv420p",
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-c:v", "libx264", "-preset", "medium", "-crf", "22.5", "-profile:v", "high", "-level", "4.1",
            "-r", "24", "-frames:v", "1440", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-shortest", "-movflags", "+faststart", str(final_mp4),
        ], capture_output=True, text=True)
        if r2.returncode != 0:
            raise RuntimeError(f"Subtitle/audio mux failed:\n{r2.stderr[-1200:]}")

    return {"final_mp4": str(final_mp4), "placements": placements}


if __name__ == "__main__":
    p_dir = Path(sys.argv[1]).resolve()
    r_dir = Path(sys.argv[2]).resolve()
    ff = sys.argv[3] if len(sys.argv) > 3 else shutil.which("ffmpeg")
    fdir = sys.argv[4] if len(sys.argv) > 4 else "/tmp/fonts"
    res = run_master_assembly(p_dir, r_dir, ff, fdir)
    print(f"[OK] Master v2 60.000s AI Comic-Drama rendered -> {res['final_mp4']}")
