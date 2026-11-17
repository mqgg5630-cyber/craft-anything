# 待机实验 · 24h 心跳 watchdog（会话分支 arena/241ceae6-leanrea）

- 启动命令：`python3 -u heartbeat.py`（已由 start_process 后台运行）
- 每 60 秒向 `heartbeat.log` 追加一行：墙钟时间、epoch、/proc/uptime、loadavg、leanrea 仓库未提交变更数。
- 每次心跳同时刷新 `status.json`（当前 tick / 已运行小时数）。
- 跑满 24h（或收到 SIGTERM）自动生成 `standby-summary.md`，给出判读结论。

## 怎么判读"待机成功"
1. 墙钟间隔 ≈ 60s 连续不断 → 沙箱一直在运行，没有触发 idle 超时。
2. 出现大间隔（墙钟跳变，而 /proc/uptime 不同步跳）→ 沙箱被 **pause** 过；最大间隔 ≈ 实测的 idle 待机上限；pause 保全了进程，恢复后继续跑。
3. 日志戛然而止、没有 summary、进程不存在 → 沙箱到期被 **kill**，进程未幸存。

过一会儿再在 Arena 里发任意消息，agent 会读取本目录日志并汇报存活情况。
