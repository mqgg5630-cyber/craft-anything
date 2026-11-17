#!/usr/bin/env python3
"""24h standby watchdog for Arena session arena/241ceae6-leanrea.

Logs one heartbeat line every INTERVAL seconds for up to BUDGET hours.
- wall clock (date) jumps across an e2b pause/resume; /proc/uptime freezes during pause.
  => a big wall-clock gap between ticks == the sandbox was paused (idle timeout hit).
  => log stopping entirely with no summary == sandbox was killed on timeout.
On finish (24h budget or SIGTERM) writes standby-summary-7d.md with the verdict.
"""
import json
import os
import signal
import subprocess
import time
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "heartbeat2.log")
SUMMARY = os.path.join(BASE, "standby-summary-7d.md")
STATUS = os.path.join(BASE, "status2.json")
BUDGET_S = 7 * 24 * 3600
INTERVAL = 60
TZ = timezone(timedelta(hours=8))  # Asia/Shanghai
REPO = "/home/user/leanrea"

start = time.time()
ticks = []  # (wall_epoch, uptime_s)
stop = False


def now_str():
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")


def get_branch():
    try:
        return subprocess.run(
            ["git", "-C", REPO, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return "?"


BRANCH = get_branch()


def handle(signum, frame):
    global stop
    stop = True


signal.signal(signal.SIGTERM, handle)
signal.signal(signal.SIGINT, handle)


def write_summary(reason):
    end = time.time()
    gaps = [ticks[i][0] - ticks[i - 1][0] for i in range(1, len(ticks))]
    max_gap = max(gaps) if gaps else 0.0
    big = [g for g in gaps if g > INTERVAL * 2]
    uptime_gap = 0.0
    if len(ticks) >= 2:
        uptime_gap = ticks[-1][1] - ticks[0][1]
    lines = [
        "# 待机实验总结（watchdog 自动生成）",
        f"- 结束原因: {reason}",
        f"- 分支: {BRANCH}",
        f"- 开始(墙钟): {datetime.fromtimestamp(start, TZ).strftime('%Y-%m-%d %H:%M:%S')} (Asia/Shanghai)",
        f"- 结束(墙钟): {datetime.fromtimestamp(end, TZ).strftime('%Y-%m-%d %H:%M:%S')} (Asia/Shanghai)",
        f"- 墙钟总时长: {(end - start) / 3600:.2f} h（预算 7d）",
        f"- /proc/uptime 跨度: {uptime_gap / 3600:.2f} h（pause 期间冻结，所以通常 < 墙钟时长）",
        f"- 心跳次数: {len(ticks)}（间隔 {INTERVAL}s）",
        f"- 最大墙钟间隔: {max_gap:.0f}s；超过 {INTERVAL * 2}s 的大间隔次数: {len(big)}",
        "- 判读: 间隔≈60s 说明沙箱一直在跑；出现大间隔说明沙箱被 pause 过（墙钟跳变）→ 实测 idle 待机上限≈最大间隔；若日志戛然而止且无本总结，说明到期被 kill。",
        "",
    ]
    with open(SUMMARY, "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines), flush=True)


with open(LOG, "a") as f:
    f.write(f"# watchdog start {now_str()} branch={BRANCH} budget=7d interval={INTERVAL}s\n")

while not stop and (time.time() - start) < BUDGET_S:
    w = time.time()
    try:
        up = float(open("/proc/uptime").read().split()[0])
    except Exception:
        up = -1.0
    load = open("/proc/loadavg").read().strip()
    try:
        gs = subprocess.run(["git", "-C", REPO, "status", "--porcelain"],
                            capture_output=True, text=True, timeout=10).stdout
        n_changes = len([l for l in gs.splitlines() if l.strip()])
    except Exception:
        n_changes = -1
    ticks.append((w, up))
    line = (f"{now_str()} | epoch={w:.0f} | uptime={up:.0f}s | load={load} "
            f"| repo_changes={n_changes} | tick={len(ticks)}")
    with open(LOG, "a") as f:
        f.write(line + "\n")
    with open(STATUS, "w") as f:
        json.dump({"alive": True, "tick": len(ticks), "wall": now_str(),
                   "uptime_s": up, "elapsed_h": round((w - start) / 3600, 3)}, f)
    print(line, flush=True)
    for _ in range(INTERVAL):
        if stop:
            break
        time.sleep(1)

write_summary("收到停止信号" if stop else "24h 预算到达")
with open(STATUS, "w") as f:
    json.dump({"alive": False, "finished": now_str()}, f)
print("watchdog finished", flush=True)
