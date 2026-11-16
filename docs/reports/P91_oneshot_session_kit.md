# P91 · 一场多目标实机执行包（2026-11-16 19:2x，纯离线准备）

**一句话**：当前部署的就是 P90 合并探针版，**只需正常玩一场约 30 分钟、打两只不同的新大型怪**，即可同时推进剩余待办。执行包已就绪，双击 `9_P91_oneshot.bat` 即可。

> **⚠ P94 更新（2026-11-16 21:0x，权威 `out/P94_log_loss_rootcause_and_hardening.md`）—— 先看这条**
> 20:30 与 20:53 两场日志**都没有 `[rai]` 行**，根因不是插件/版本/配额，而是 `mods/forge/romfs/nativeNX/forge/config.ini` 里 `[log] level = error` 把插件全部 INFO 日志过滤了。已改为 `level = info`（原文件备份在 `out/P94_forge_config_backup_20261116.ini`）。
> 执行包已加固：开打前自动校验并修正该配置、日志按时间戳保留（不再删旧日志）、启动后 150 秒若无 `[rai]` 横幅会**弹窗告警**、退出后立即自检。判读脚本也已能区分「日志通道故障」与「版本不对」。
> **用户口径**：30 分钟 ≈ 一场正常游玩时长，不是额外负担；目标 D 重定义为「一场正常游玩全程日志连续无盲区」。
> 本场及 20:30 场一律**不计入验收**；P92/P93 定案不受影响。

> **✅ P95 更新（2026-11-16 21:2x，权威 `out/P95_postfix_verification_and_failed_quest_session.md`）—— 修复已实机验证**
> P94 修复后的第一场有效日志已拿到：`[rai]`=2162 行 / `[forge] INFO`=3459 / 双横幅 / 6 hook / FATAL=0 / 完整性 OK。**「日志没有记录」的根因确已解决**，下一场不必再担心白打。
> 该场死亡三次、任务失败，但 BEAT 帧序列 `f=300…48300` 严格单调、零盲区 ⇒ **失败不影响日志连续性**；仅时长 13.4 分钟、未进自然疲惫（A/B 已收口，不阻塞）。C 在 `sp=0047` 再次 15/0/0。
> **下一场唯一待办**：正常打一场约 30 分钟 + 两只不同的新大型怪（避开 `0020/0050/0052/0051/0047`）；不必跟疲惫 / 换区 / 进食。

---

## 1 · 前置（bat 会自动做，这里是可核对的口径）

| 项 | 值 | 核对 |
|---|---|---|
| 插件位 NRO | `<游戏>/mods/RiseAI_EntryProbe/romfs/nativeNX/plugins/rai_entrylocator_probe.nro` | md5 `0ab6cbec301b4336fbbd50dcb71f9008`（65,536 B） |
| 参照产物 | `04_RiseAI/out/rai_p90_probe.nro` | md5 同上，`fc /b` 逐字节一致 |
| 开关 | `P90_TIRED_COVERAGE=1` / `P90_F0_PROBE=1` / `P90_MIN_CAND=2` / `MAX_F0=600` | 全开；`DRAIN_ENABLE=0`、`W3_GATE_ENABLE=0` 保持 |
| 日志落点 | `02_Workspace/game_p91_oneshot.txt`（新建，不轮转别人的日志） | **P94**：旧日志改名为 `.<时间戳>.prev`，永不删除 |
| Forge 日志级别 | `<游戏>/mods/forge/romfs/nativeNX/forge/config.ini` 的 `[log] level` | **P94 新增**：必须为 `info`；前置脚本自动校验并修正，否则 `[rai]` 行全丢 |
| 后台监视 | `tools/watch_p91_log.py` → `out/P91_watch_status.txt` | **P94 新增**：150 秒无 `P90 PROBE` 横幅即置顶弹窗 |
| Python | `C:\Users\RongLynn\.workbuddy\binaries\python\versions\3.13.12\python.exe` | 已实测可用 |

**不要用 `8_lite_check.bat` 打这一场**：它输出到 `game_p54_lite.txt`，会覆盖 P79 唯一验收场日志；且它跑的 `analyze_v71_limits.py` 是 v71 全量探针口径，成品已关掉 Z/ZP/AR/COMBO/AE 等行，会大量误报 FAIL。
**也可以用 `7_P54_启动并抓日志.bat`**（输出到 `game_p54.txt`，自带 prev 轮转），但那样游戏结束后要手动跑 §5 的判读命令。

**双击 `9_P91_oneshot.bat` 后的流程（P94）**：`prepare_p91_env.py` 前置校验（NRO md5 + Forge level 修正 + 时间戳轮转）→ 显示打法说明 → `pause` 等按键 → 启动后台监视器 + 游戏并抓日志 → 你正常退出游戏 → 立即自检 `[rai]` 横幅 → 自动跑判读输出 4 份报告。前后各一次 `pause`，中间不需要任何手动操作；**150 秒内若弹出警告窗口请立刻退出，不要白打一场**。

---

## 2 · 这一场怎么打（关键设计）

> **P93 更新（2026-11-16 20:25，权威 `out/P93_baseline_lock_coverage_review_and_gap_closure.md`）**：目标 A / P87② 已由 P92 定案**否决立项**，疲惫窗口数据已取完。若这是「补场」而非首次执行，**本节中「疲惫出现时跟住换区+进食」「两只都要打到疲惫」等要求已作废**，§3 的 A/B 行判据仅作历史对照。补场唯一要求：**连续 ≥30 分钟 + 两只不同的新大型怪（避开 `0020/0050/0052/0051`），正常打猎、正常退出即可**。批处理 `9_P91_oneshot.bat` 的屏显提示已同步更新。

| 时间 | 做什么 | 为什么 |
|---|---|---|
| 0:00 起 | 启动游戏后**不要退出**，连续保持 30 分钟以上 | 目标 D：30 分钟长时日志；末 BEAT 需 `f>=108000`（60 fps） |
| 0~15 min | **任务 A**：选一只大型怪，**避开已打过的 3 种**：轰龙 `0020` / 斩龙 `0050` / 泡狐龙 `0052` | 目标 E：跨怪种类 3→5，并满足 P90 §7.3「跨 ≥2 怪 A/B」 |
| 疲惫出现时 | **别立刻击杀或捕获**，跟住它走完换区 + 进食，至少再观察 1~2 分钟 | 目标 A：F0/F1 需要 `d>=300` 帧的低动作段；P79 的教训是「窗后主怪动作归零 ⇒ 不可判」 |
| 15~30 min | **任务 B**：换**第二只不同的**大型怪，同样尽量触发一次自然疲惫 | 目标 E 的第 2 只；同时给 A/B 多一份样本 |
| 全程 | 不按 F9、不用「任务立即完成」、不长时间停在暂停菜单、不改任何 mod / `load_order` | 避免污染动作计数与日志密度 |
| 结束 | **正常退出游戏**（日志在退出时 flush），然后让 bat 自动分析 | 目标 C/F：日志末尾完整性 |

自然疲惫约 5~6 分钟可达（P64），P79 实测自然疲惫窗 74.5 秒；**这两只怪都要打到疲惫**，否则目标 A、B 会退化为「数据不足」。

**请顺手用肉眼记 4 件事**（脚本判不了，判读时要用来交叉）：
1. 两只怪分别是什么、各自大约第几分钟发怒 / 流口水；
2. 疲惫后是否真的换区并进食，持续大概多久；
3. 有没有出现连续 3 次同招、站住不动、动画错位、卡顿或闪退；
4. 疲惫时是否明显「招式变单一 / 攻击空档变长」。

---

## 3 · 这一场同时推进的 6 个目标与判据

| # | 目标 | 看哪个数字 | 判据 | 不达标时 |
|---|---|---|---|---|
| **A** | P87① FNV0 空档（决定 P87② 让位是否立项） | `F1.d` 疲惫态 p50 / max / `>=300` 段数；`F0` 的 `pct/dc/t505/area/req` | p50 仅 1~5 帧 ⇒ **放弃让位**；`d>=300` 且与 `pct<=30`/`dc=1`/`req!=0` 重合 ⇒ **候选原生进食窗口**，需排除赶路/离场 | 无自然疲惫 ⇒ 数据不足，需补一场 |
| **B** | P89① 覆盖率改进是否生效 | `S.wt` / `F9.wt` 峰值 | 对照 P79 `wt=1`、P70 `wt=7`；`>=8` 明显改善、`2~7` 部分、`<=1` 未改善 | 未改善 ⇒ 考虑 `P90_TIRED_COVERAGE=0` 编回 v2 |
| **C** | v2 实机复验（P80 stance 修复后未跑） | 15 条成品口径判据（6 hook、FATAL=0、`live=1/hub=15`、`wall/wnok`、`wb/bf`、HB 特殊占比、`gs=0/ge>0`、`gdone=0`、关闭行全 0、`V.st3` 覆盖等） | 全 PASS = 0 FAIL | 有 FAIL ⇒ 按明细定位，不宣布通过 |
| **D** | 30 分钟长时日志 | 末 BEAT `f`、epoch 分布、末尾 gap、`log` 峰值 | ≥30 分钟 + 完整性 `OK` + 无 epoch 盲区 + 末尾 gap ≤3000 + `log` 远低于 1M | 时长不足 ⇒ 本目标不闭环 |
| **E** | 跨怪 A/B | `V`/`F0`/`F1` 行的 `sp` | 出现 ≥2 只 `sp<0x1000` 且非 0020/0050/0052 | 只打了 1 只 ⇒ 不满足 P90 §7.3 |
| **F** | P90 自身配额风险（新增） | 每 epoch `F0+F1+F9` 行数、`F9` 末条位置 | 峰值 <590/600 且 F9 覆盖到末段 | 打满 ⇒ F9 后半场停写，逐行 F0/F1 仍可判读、`wt` 改从 S 行读 |

**A 的两条新增严谨性判据**（本包新加，旧 `analyze_p90_f0.py` 没有）：
- `F1.mon != F0.mon` 的比例：F0/F1 是**单一全局段**，不是按怪分槽。跨怪结段 >20% 时，`d` 可能被别的怪的动作结段污染，必须先按 `mon` 过滤再判。
- `F1` 的 `pct/t505/dc/area/req` 是**结段时**读数，`F0` 是**段起点**读数，两者不可混用。

---

## 4 · 跑完自动产出

| 文件 | 内容 |
|---|---|
| `02_Workspace/game_p91_oneshot.txt` | 原始日志（**请勿删除 / 改名**） |
| `04_RiseAI/out/P91_session_report.md` | **主报告**：6 目标总表 + A 帧差分布/最长 10 段 + C 15 条判据 + D/E/F 明细 |
| `04_RiseAI/out/P91_session_report.json` | 结构化结果（便于二次分析） |
| `04_RiseAI/out/P91_session_report.console.txt` | 控制台摘要 |
| `04_RiseAI/out/P91_f0_detail.txt` | 旧 `analyze_p90_f0.py` 的独立留档（口径对照用） |
| `04_RiseAI/out/P91_log_integrity.md` | `check_log_integrity.py` 独立留档 |

报告里的结论是**自动初判**，最终判读仍由 agent 结合第 2 节的 4 条肉眼记录做交叉；把原始日志路径发回来即可。

---

## 5 · 若分析阶段没跑起来（手动命令）

```
cd /d "D:\MHGU mod maker"
"C:\Users\RongLynn\.workbuddy\binaries\python\versions\3.13.12\python.exe" 04_RiseAI\tools\analyze_p91_session.py "D:\MHGU mod maker\02_Workspace\game_p91_oneshot.txt" --md 04_RiseAI\out\P91_session_report.md --json 04_RiseAI\out\P91_session_report.json
```

用 `7_P54_启动并抓日志.bat` 打的话，把上面日志路径换成 `02_Workspace\game_p54.txt` 即可。

---

## 6 · 异常与回退

**中途闪退 / 冻结 / 动画错位 / 明显出招异常**：立刻停止，不要硬打满 30 分钟，正常退出后把日志与现象发回来。脚本会以 `FATAL` / `c0000005` / 完整性 `ERROR` 标出。

**回退到 v2 成品**（覆盖 + 重启即生效）：
```
copy /y "D:\MHGU mod maker\04_RiseAI\out\deployed_v2_pre_p90_c174b191.nro" "D:\Monster Hunter Generations Ultimate Recomp\mods\RiseAI_EntryProbe\romfs\nativeNX\plugins\rai_entrylocator_probe.nro"
copy /y "D:\MHGU mod maker\04_RiseAI\plug\_release_build\src\lib.rs.p90bak" "D:\MHGU mod maker\04_RiseAI\plug\_release_build\src\lib.rs"
```
更早回退链：v1 `out/deployed_release_v1_dfab157d.nro`；v71 `out/deployed_v71_1d513ec3.nro` + `plug/context_probe/src/lib.rs.v71bak`。

---

## 7 · 边界（勿夸大）

1. **P79 验收不再自动适用于 P90**；本场是给 P90 版建立新基线，不是替 v2 追加验收。
2. 目标 D 达标只证明「**当前 P90 成品密度**下连续 30 分钟不停写」。P80 的 30 分钟静态配额审计基于 v71 全量探针版的高密度日志，v71 探针版 30 分钟实跑仍未做，且已裁定不单独安排（P80 §边界）。
3. 目标 A 即使出现 `d>=300` 的低动作段，也**不等于**复刻了 Rise 的输出窗口；GU 无 `dE` 阶段，须先排除赶路 / 主怪离场，且让位只能「不打断」原生进食、不能强制触发（P86/P87）。
4. **P87② 让位权重槽仍未实现**，参数与护栏必须等本场 F0/F1 帧差分布；本执行包不含任何行为改动。
5. Rise 运行时 `_RangeDistance` 分派、`_ActionNo→招式名` 属硬断点，不因本场改变。

---

## 8 · 本轮新增文件（全部只读准备，零实机）

| 文件 | 作用 |
|---|---|
| `9_P91_oneshot.bat` | 启动前版本校验 → 独立日志轮转 → 抓日志 → 自动出报告；不碰 `6_` / `7_` / `8_` 与既有日志 |
| `tools/analyze_p91_session.py` | 一场 6 目标汇总判读，含 A 的跨怪结段与字段口径修正、C 的成品口径判据、F 的配额风险 |
| `out/P91_oneshot_session_kit.md` | 本文 |

**纪律**：未启动游戏、未编译 NRO、未改源码 / 成品 / mods / `load_order` / 游戏资源 / 音频线；GitHub 远端零操作。新增判读脚本已在 P79 旧日志上冒烟（预期正确报「非 P90 版」）。
