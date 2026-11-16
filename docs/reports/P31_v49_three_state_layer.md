# P31 · v49 三状态权重层：设计、实现与离线闭环（2026-11-12 19:48）

承接 P30（`out/P30_v48_real_machine_closed_loop.md`）：减气/疲惫触发链已字节级 + 实机
闭环，`PASS=11/FAIL=0`，数据已足 ⇒ **回 AI 主线**，实现 3 状态权重层。
本轮完成设计 → 源码 → 编译 → 离线判读 → 部署，**未实机**。

---

## 1 · 目标与结构性对标的边界

Rise 侧（`em001_main_out1_{anger,normal,tired}range{1..5}check.user.2`，NOTES §330/§504）：
3 状态 × 5 距离档 = 15 个候选池，`ConditionInfo._TransitionRate` 权重和恒 100；
怒池 6 表 / 熵 **1.67**（更多样），疲劳池 4 表 / 熵 **1.30**（更低威胁、更集中）。

**GU 侧没有对应表结构**（NOTES §932 已定案：不能照搬 15 池）。因此 v49 只做
**结构性近似**：在已定案的 EMC 加权抽选层（`0x8E144`，`op02 / mode==1 / sub==0`）
按状态调「prev 表否决严格度」，从而改变实际执行序列的分布熵。

| | Rise | GU v49 |
|---|---|---|
| 状态输入 | 引擎状态枚举 | 怒 `st==1`（内存只读）/ 疲惫触发事件 + 行为窗口 / 其余 |
| 权重载体 | 15 张 `_TransitionRate` 表 | 无表可改，只能改变「否决 + 归一化重抽」的严格度 |
| 距离档 | 5 档 | **未实现**（距离档未定位） |

⇒ 这是**近似，不是等价复刻**。不得对外宣称「已复刻 Rise 15 池」。

## 2 · 三态判据（全部只读，跨怪通用）

| 态 | 判据 | 依据 | 优先级 |
|---|---|---|---|
| 怒 `ST_ANGER=1` | `*(u8*)(act+0x518)==1`，`act=*(mon+0x1428)` | P14 / P25 截图「発怒し」/ P30 `st=1` 于 `f=8400..12150` | 最高 |
| 疲 `ST_TIRED=2` | `0xA30E4 EXH add` 返回 **1**（游戏自己判定 `counter>=thr`）或 `proc=*(u8*)(act+0x5D8C)` 递增 ⇒ 进入疲惫窗口 | P29 链路 / P30 实机 `proc 0→1→2→3`、`thr 142→190→237→285` | 次 |
| 常 `ST_NORMAL=0` | 其余 | v38 基线 | — |

**疲惫窗口为什么用「该怪自己的动作数」计时（关键设计）**：
P19/P22/P28/P30 反复证实「暂停菜单冻结游戏逻辑，但 `forge_onUpdate` 帧继续涨」，
任何以 forge 帧为时钟的疲惫窗口都会被暂停错误耗尽。v49 在 `0xAFF40`（动作开始）
按 `reg_mon()` 槽递增 `ST_AN[i]`，窗口 = `ST_AN[i] - ST_TA0[i] >= 40` 个动作，
或绝对帧上限 `108000` 兜底。⇒ 暂停不进入、不退出、不消耗窗口。
`proc` 轮询（每 30 帧）在游戏逻辑冻结时 `proc` 不变，同样不误触发。

**双通道触发**：`h_exh` 若因运行时首字非 push 家族而 SKIP（IPS32 跳板），
`forge_onUpdate` 的 `proc` 递增轮询独立接管，功能不丢。

**日志字段消歧**：`T` 行 `tir=` 是疲惫窗口标志（0/1），与 `V` 行 `st3=` 三态枚举
（0 常 / 1 怒 / 2 疲）不同名不同义；`T.an` 在 ENTER 时是该怪累计动作数、
在 EXIT 时是窗口内动作增量（判据据此要求 `an>=40`）。

## 3 · 权重映射

```
veto_depth: 怒 = 3  /  常 = 2  /  疲 = 1
```

- 怒 `depth=3`：prev 表扩到 3 项并全参与否决 ⇒ 更强地打破复读，动作分布更均匀（对标熵 1.67）。
- 常 `depth=2`：**只查 prev 表前 2 项，与 v38 行为逐项等价**（`P_CNT` 存储扩到 3 不影响判定）。
- 疲 `depth=1` + `TIRED_KEEP_PCT=50`：只否决最近一次，且 50% 概率直接保留原版抽选结果
  （`pskip = (a4 + f*11 + VETO_N*5) % 100`）⇒ 更接近原版权重分布（对标熵 1.30）。

硬约束全部保持：**零内存写入、不写参数表、不碰 action_id、不硬编码怪种数值、
`original!` 恒调用且参数不变、v38 自保护/`GATE_LIVE` 熔断/回退链不变**。

## 4 · v48 强制触发的处理

`v48` 的「一次性把 `amount` 放大到 `thr+16`」是**探针**，不是最终 AI 行为，且 P30
已指出它与用户可见疲惫不是同一次事件（强制在任务内约 42 秒，流口水在 3 分钟）。
v49 **移除强制**：`h_exh(a0, a1)` 原样透传 `a1`，只读 `original!` 返回值，
`ret==1` 时出 `U` 行并登记疲惫事件。⇒ 本版是**纯只读**插件。
`U` 行 `force=0`；NRO 内已确认不存在 `force=1` 串。

## 5 · 源码改动清单（`plug/context_probe/src/lib.rs`，备份 `lib.rs.v48bak`）

| 位置 | 改动 |
|---|---|
| 头部 doc | v49 设计说明（Rise 对标 / 三态 / 权重 / 回退） |
| 常量 | `ST_*`、`TIRED_ACT_WINDOW=40`、`TIRED_MAX_F=108000`、`TIRED_KEEP_PCT=50`、`PROC_POLL=30`、`MAX_T=120` |
| 静态 | `ST_AN/ST_TIR/ST_TA0/ST_TF0/ST_PROC/ST_SEEN`（8 槽）、`S_N/S_V`（3 态）、`S_SKIP/D3_N/T_LOG`、`P_SIG3` |
| `prev_hit_d()` | 带 `depth` 参数的命中检查；`push_prev()` 环形长度 2→3 |
| 新增 | `mon_state()` / `veto_depth()` / `tlog()` / `enter_tired()` |
| `h_matcher` | 取 `st3/vd`、三态计数 `S_N`、疲惫态 50% 放弃否决、重抽改用 `prev_hit_d`、`V` 行加 `st3/vd`、成功否决计 `S_V` |
| `h_exh` | 去强制、改纯只读触发观测（`ret==1` → `enter_tired`） |
| `h_start_40` | 按槽递增 `ST_AN`（逻辑时钟） |
| `forge_onUpdate` | 每 30 帧 proc 轮询 + 疲惫窗口进出；`S` 行加 `s0/s1/s2/sv*/d3/skip` |
| `main()` | v49 横幅、只读 hook 文案、v48 Rule 行标注 FORCE REMOVED |

## 6 · 编译与校验

- 命令：nightly cargo + `-Zbuild-std=core,alloc --target armv7a-none-eabi.json`，
  `elf2nro.py` 转 NRO。仅 `-z norelro ignored` 无害警告。
- 产物：`out/rai_tristate_v49.nro`，**40960 B，md5 `ec4fcd058a514605abbd01c304041a43`**。
- 特征串：`RAI v49` / `THREE-STATE WEIGHT LAYER` / `veto depth 3/2/1` /
  `FORCE amount=thr+16 REMOVED` / `T f=` / `st3=` / `force=0` 各命中；
  **`force=1` 不存在**；`arm-none-eabi-nm` 确认 `h_exh::___detour` 与 `h_matcher::___detour` 存在。
- 源码回退 `plug/context_probe/src/lib.rs.v48bak`；二进制回退 `out/rai_exhaust_chain_v48.nro`
  （`f4c6d2b7…`）。

## 7 · 离线判读（`tools/analyze_v49_states.py`）

`tools/make_v49_smoke.py` 生成 378 行合成日志（含 9 字段全同的「暂停冻结」R 段），
判读结果 `out/v49_sim_report.txt`：

```
PASS=20 / FAIL=0
V=60（普通30/怒12/疲18） st3->vd 违例=0
T ENTER=2 EXIT=2  reason=[1,2,3]  reason=3 且 an>=40 计数=2
U=3（ret=1 force=0）  S: s0/s1/s2=120/48/64, d3=48==s1, skip=22
live=1  hub=15  FATAL=0  5 hook INSTALL
```

降级测试：用 P30 的 v48 真实日志
`out/game_p54_lite_20261111_2254_v48_FULL.txt` 跑 v49 判读脚本 →
输出「旧日志（v48 及以前）」且无 traceback（PASS=6/FAIL=14 属预期缺失字段）。

## 8 · 部署与纪律守卫

- 已确认**无 `mhgurecomp.exe` 进程**后覆盖部署：
  `mods/RiseAI_EntryProbe/romfs/nativeNX/plugins/rai_entrylocator_probe.nro`
  md5 与产物一致（`ec4fcd05…`）。`load_order.txt` 第 38 行 `RiseAI_EntryProbe` 保持启用，**未追加任何行**。
- `6_启动并抓日志.bat` md5 `7361445f989b21fde050be83b347db70` **未动**；
  游戏资源 / `em085` / `em002` arc 未动；临时 mod 早在 P29 已全部回退。
- `8_lite_check.bat` / `7_P54_启动并抓日志.bat` 提示改 STEP 49，
  `TOOL2` → `analyze_v49_states.py`；执行逻辑、输出路径、日志轮转、
  Python 绝对路径、CRLF（`bareLF=0`）全部保持。旧版备份在
  `out/8_lite_check.bat.v48bak` / `out/7_P54_启动并抓日志.bat.v48bak`，
  更新脚本 `tools/update_step49_prompts.py`（自带守卫断言）。

## 9 · 实机验证（下一步，用户操作）

双击 `8_lite_check.bat` → 任意任务（跳狗龙王是已验证短场，自然疲惫约任务内 3 分钟）
→ 正常打，覆盖**发怒段**与**一次流口水疲惫段** → **立即正常关游戏**
（别久留任务状况菜单）→ 自动出两份报告，第二份是 v49 三态判据。

需回报：怪种、大致任务内几分钟发怒 / 流口水、三阶段体感是否有差异、有无异常。
判据：`INSTALL h_exh (v49 read-only)` / `T` 行 ENTER+EXIT 且 `reason∈{1,2,3}` /
`V` 行三态齐全且 `st3→vd` 无违例 / `S` 行 `s1>0 && d3==s1 && skip>0` /
零 FATAL / `live=1` / `hub=15`。

## 10 · 风险与已知边界（不掩盖）

1. **结构性近似**，不是 Rise 15 池等价实现；距离档（5 档）完全未实现。
2. `depth=3`、`TIRED_KEEP_PCT=50`、`TIRED_ACT_WINDOW=40` 均为**自定保守参数**，
   无 Rise 数值依据；实机后按体感调整。
3. 疲惫窗口起点是 `EXH add ret=1` / `proc` 递增（游戏状态机通知），
   **不等于玩家可见的流口水**（P30 强制那次即反例）；窗口可能与可见疲惫有偏差。
4. `st==1`（怒）跨怪一致性未系统验证（P25 标注）；疲惫判据的跨怪一致性同样待实机。
5. 暂停菜单仍会产生「R 行 9 字段全同」段，但它只影响观测样本，
   **不影响疲惫窗口计时**（这是本版专门修掉的陷阱）。
6. 若实机闪退 / 冻结 / 动画错位：立即退出并覆盖回 `out/rai_exhaust_chain_v48.nro`。

---

**本轮收尾**：未实机、未改游戏资源、未动 `6_`、未追加 `load_order`；
插件 v49 已部署待实机验证。
