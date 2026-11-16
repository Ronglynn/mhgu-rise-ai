# P94 · 「日志没有记录」根因定案与执行包加固

**日期**：2026-11-16 21:0x（纯离线排查，未启动游戏）
**触发**：用户完成第二场任务；补充「30 分钟日志是因为我一场游玩就在这个时间左右，之前多次出现日志没有记录的情况让我很烦躁」。

---

## 0 · 结论先行

**本场（20:53 日志）与上一份 `.prev`（20:30）都不是「实机失败」，而是「日志通道故障」**：插件已加载并很可能正常运行，但 Forge 把全部插件 `INFO` 级日志静默过滤了，所以 `[rai]` 行 = 0。根因是单一配置行，不是插件、不是 NRO、不是配额、不是用户游玩时长。

| 判定 | 结论 |
|---|---|
| 插件是否加载 | **是**：`loaded rai_entrylocator_probe.nro at 03580000 size 00011000 syms 15` + `relocated (5 imports bound)` + `[forge] plugin ...` |
| 是否为版本错误 | **否**。自动报告原写「非 P90 编译版」是判读 bug，已修正 |
| 是否为配额耗尽 | **否**。P90 `MAX_F0=600`、v71 `MAXLOG=1M` 均未触及（无 `[rai]` 行可计） |
| 是否为插件功能失败 | **无法判定，且不应据此判定**。C 表的 9 个 FAIL 是「无数据」，不是回归 |
| 真实根因 | `mods/forge/romfs/nativeNX/forge/config.ini` 的 `[log] level = error` |
| 本场六目标 | A–F **全部无数据**；P92/P93 定案不受影响（基于第一场有效日志） |

---

## 1 · 证据链

### 1.1 宿主在 19:21 自动升级

`update/updater.log` 末段：

```
this build 0.15.3, latest release 0.17.5
downloading .../Windows-MHGURecomp.0.17.5.zip (44116675 bytes)
installing 27 files
updated to 0.17.5
starting ...\mhgurecomp.exe
```

P79 验收日志首行 `MHGU Recomp 0.15.3`；新日志与 `.prev` 首行均为 `MHGU Recomp 0.17.5`。Forge loader 版本两者同为 **1.5.1**，故差异来自宿主主程序而非 Forge 版本。`mhgurecomp.exe` mtime = 19:21。

### 1.2 日志级别分布是决定性证据

| 指标 | P79（0.15.3，有效） | 20:53 场（0.17.5） | 20:30 场（0.17.5） |
|---|---:|---:|---:|
| `[forge] [INFO]` | **6873** | **0** | **0** |
| `[forge] [DEBUG]` | 621 | 2 | 2 |
| `[forge] [ERROR]` | 4 | 1393 | 497 |
| `[forge] [WARN]` | 12 | 0 | 0 |
| `Loading plugin` | 19 | 0 | 0 |
| `Initializing plugin` | 16 | 0 | 0 |
| `[rai]` 行 | 大量 | **0** | **0** |

`[rai]` 行的实际前缀是 `[forge] [INFO] [rai] ...`（见下），因此 `level = error` 会把它整批丢掉。残留的 1393 行 ERROR 来自其它插件（主要是 `[action_ext]` 的诊断输出），说明日志系统本身工作，只是级别被过滤。

### 1.3 插件与 NRO 均正常

- 新日志第 109–111 行：`loaded rai_entrylocator_probe.nro` / `relocated ... (5 imports bound)` / `[forge] plugin rai_entrylocator_probe.nro (mods/RiseAI_EntryProbe/romfs/nativeNX/plugins/...)`。
- 部署 NRO 仍为 `0ab6cbec301b4336fbbd50dcb71f9008`，与 `out/rai_p90_probe.nro` **逐字节一致**。
- 游戏目录 `log.txt`（19:22 由 updater 启动的那次短会话）中有 **`[rai]` 70 行、`P90 PROBE` 横幅、`RAI v71` 横幅、6 个 `INSTALL`、`[forge] [INFO]` 184 行**，即升级后首次启动时 INFO 通道仍开着。该文件 BEAT 只到 `f=300`，是启动冒烟，不含实机数据。
- 宿主二进制内可定位 `forge_config_load` / `level` / `font_size` / `log_level_of` / `MHGU_FORGE_LOG` / `DEBUG|INFO|WARN|ERROR` 等字符串，与 `config.ini` 的键一一对应。

### 1.4 配置文件内容（修复前，已备份）

`mods/forge/romfs/nativeNX/forge/config.ini`：

```ini
[log]
level = error

[menu]
key = 73
font_size = 12.0
```

备份：`out/P94_forge_config_backup_20261116.ini`（md5 `8425f5d79656b39dd0943446ac589473`）。目录 mtime 20:27 提示该项在 20:14~20:30 之间被写入，正好落在「第一场有效日志」与「两份空日志」之间。

### 1.5 为什么此前多次「没有记录」

用户报告的现象与本次证据一致：**只要 `level` 被设为 `error`（或同类静默过滤），日志里就只剩宿主行，看起来像「没记录」**。它与「30 分钟配额耗尽」是两回事——v71 起 `MAXLOG=1M`、每 30000 帧重置各独立配额，P92 已实测第一场 22.2 分钟配额 PASS 134/600，无截断。

---

## 2 · 用户补充的口径修正（重要）

> 「30 分钟日志的原因是我一场游玩时长就在这个时间左右」

据此重新定义目标 D：

- **旧口径**（P80/P91）：需要专门打满 ≥30 分钟来验证长时日志配额。
- **新口径（本裁定）**：**D = 一次正常游玩（约 30 分钟）全程日志连续、无盲区**，不要求用户额外延长时长，也不要求重复打。判据是 BEAT 覆盖到结束、无 epoch 盲区、行长/完整性 OK，而不是「凑够 30 分钟」。
- 因此用户真正需要解决的是**「这一场有没有被完整记下来」**，而非「打得更久」。本次加固（前置校验 + 150 秒横幅监视 + 退出后自检）正是针对这一点。

---

## 3 · 已执行的修复（全部离线）

### 3.1 根因

`mods/forge/romfs/nativeNX/forge/config.ini`：`level = error` → **`level = info`**。原文件已备份，回退只需覆盖回去。这是本轮**唯一**改动游戏侧文件的动作；其它 mod、`load_order`、游戏资源、音频线均未动。

> 说明：`level = info` 会恢复所有插件的 INFO 输出，日志体积回到 P79 量级（约 1.5 MB / 1.3 万行），可接受。若用户后续为减日志把它改回 `error`/`warn`，本任务的判读数据会再次消失，执行包前置会自动改回 `info`。

### 3.2 执行包加固

| 文件 | 变更 |
|---|---|
| `9_P91_oneshot.bat` | 新增 P94 前置（NRO md5 + Forge level 自动修正 + 时间戳轮转 + 清监视状态）；启动后台监视器；游戏退出后立即检查 `P90 PROBE` 横幅；CRLF 已规范（80 行） |
| `tools/prepare_p91_env.py`（新） | 前置校验：NRO 与参照逐字节一致且 md5 为 `0ab6cbec…`；`level` 非 `info` 自动改（首次先备份）；旧日志改名为 `game_p91_oneshot.txt.<时间戳>.prev`，**不再删除任何历史日志**；失败返回 1 并阻止开打 |
| `tools/watch_p91_log.py`（新） | 后台每 5 秒轮询日志；出现 `P90 PROBE` + `[rai]` 即写 `out/P91_watch_status.txt=OK` 并退出；**150 秒仍无横幅则弹出置顶 Windows 警告框**，用户可立刻停手，不必白打一场 |
| `tools/analyze_p91_session.py` | 新增宿主日志通道诊断（`[forge] INFO/ERROR`、插件是否已 loaded、宿主版本）；`level=error` 时 A–F 统一标为「无数据（日志通道）」，不再误报「非 P90 版本」或把空数据当 9 个功能 FAIL |
| `tools/analyze_p90_f0.py` | 无 F0/F1 时区分「日志级别过滤」与「版本/脚本问题」，给出对应修复指引 |

四份本场报告已按新口径重出：`P91_session_report.md` / `.console.txt` / `.json`、`P91_f0_detail.txt`、`P91_log_integrity.md`。修前的错误报告保留为 `P91_session_report_preP94.md`。

### 3.3 顺带发现的数据损失

旧 bat 的轮转逻辑是「若 `.prev` 存在则先删除，再把当前日志改名为 `.prev`」。用户连续开了两场，导致 **P92 判读所用的第一场有效日志（27,498 行 / 22.2 分钟 / PASS 15/0/0）被第二次轮转删除**。现存 `.txt.prev` 是 20:30 的空日志。

- 影响：原始日志不可再复核，但 `P92_p91_session_review.md`、`P93_*.md`、`P91_session_report_auto_v0.md`、`P91_f0_detail_auto_v0.txt` 已固化全部结论，**定案不丢**。
- 已修：新 bat 用时间戳命名且永不删除旧文件。

---

## 4 · 本场判读结论（20:53 日志）

`02_Workspace/game_p91_oneshot.txt`：7130 行 / 601,704 B / 宿主 0.17.5 / 6 hook 加载齐（无 INFO 行故看不到 INSTALL）/ FATAL=0 / `[rai]` 行 **0**。

| 目标 | 结论 |
|---|---|
| A · P87① FNV0 空档 | 无数据（日志通道）—— P92 已否决 P87②，**不受影响** |
| B · P89① 覆盖率 | 无数据（日志通道）—— P93 已定案「机制通路通过、改动效果未验证、不再改源码」，**不受影响** |
| C · 成品复验 | 无数据（日志通道）—— 第一场 P90 的 PASS 15/0/0 仍是当前基线依据 |
| D · 30 分钟长时日志 | 无数据（日志通道）；按 §2 新口径待下一场有效日志闭环 |
| E · 跨 2 只新大型怪 | 无数据（日志通道） |
| F · P90 配额 | 无数据（日志通道）；第一场已 PASS 134/600 |

**结论：本场不计入任何验收，也不需要为它补做功能修复。P79 唯一完整验收（64/0/4）、P90 当前部署基线（15/0/0）、P87② 否决、P93 收口全部维持不变。**

---

## 5 · 下一场（唯一待办，且只需正常打一场）

1. 双击 `9_P91_oneshot.bat`。屏显 `[ok] Forge log level = info` + `[ok] deployed NRO = P90 probe build` + `[ok] PREFLIGHT PASSED` 才按任意键开打。
2. 正常玩**一场约 30 分钟**，中途不退出游戏；两个任务、两只**不同**的新大型怪，避开 `0020 / 0050 / 0052 / 0051`。不必刻意跟疲惫、换区或进食（P93 已关闭目标 A）。不按 F9、不用即时完成、正常退出。
3. 启动后 150 秒内**若没有弹出警告窗口**，就说明 `[rai]` 横幅已出现、日志正常；若弹窗，立即退出并把消息发来，不必浪费这一场。
4. 退出后脚本自动出 4 份报告并发 `game_p91_oneshot.txt` 路径。

**边界**：本轮未启动游戏、未编译 NRO、未改插件源码 / 部署 NRO / 其它 mod / `load_order` / 游戏资源 / 音频线 / `game_p54_lite.txt`；GitHub 远端零操作。唯一游戏侧改动是 Forge 自身 `config.ini` 的日志级别，已备份可回滚。
