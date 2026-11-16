# P39 · v51 上游减气 amount 观测探针（已部署，未实机）

> ⚠ **判据 A 与「0xA30E4 = 每动作扣 stamina 通道」的前提已被 `P41_add_channel_correction.md`
> 撤回**（2026-11-12 22:23）。本文的部署/验证数据仍有效；判据以 P41 的 N/B/C/D/X 为准。

日期：2026-11-12 22:05 UTC+8 ｜ 任务线：`04_RiseAI`（Rise 式怪物 AI）
前置：P37 首场 v50 实机、P38 两问复核 ｜ 回退：`out/rai_risepool_weight_v50.nro`

---

## 0 · 直接回答用户两问

**1）GU 的怪攻击会扣自身 stamina，且不需要玩家攻击。**
- P20（`out/P20_stamina_chain_audit.md`）离线确证：怪物动作按 Rise `ActionInfo._subStaminaPoint` 扣自身耐力，em002 的 393 个动作里 98 个非零（5~50 点）；GU 同构名词 `mParam.stamina_point @0x1eb8d0`、`doumouka` 的 `StaminaSubRate / StaminaTimeVal`。
- P19 实机：跳狗龙王 + 当前打法在任务内 **3.35 分钟**自然流口水（BEAT dA 10→2/3/1 @f=15300，qstart=3247），这条链不需要玩家减气输入。
- 因此「不打怪、让怪自己动」是**有效对照实验**：把玩家侧任何可能的减气/伤害输入隔离掉，只留怪物自身出招消耗。本轮已把它写进 `8_lite_check.bat` / `7_P54_启动并抓日志.bat` 的首选跑法。

**2）探针此前没有部署，本轮已实现并部署。**
P38 只给了「在 `0x9A470` / `0x9DB54` 加 hook」的建议，未落地。本轮用**更优解**：不新增任何 hook —— 现有 `h_exh(a0, a1)` 的 `a1` 就是 amount（v48 实机把 `a1` 放大到 `thr+16` 成功强制触发，已实证该参数语义），只需在已装的 hook 里加纯计数。

---

## 1 · 要区分的两种根因

P38 用三场实机把「雄火龙不疲劳」收敛到「整块 Exhaust 运行期区从未被写入」：
`ex / proc / d5 / t5c` 在雄火龙两场全恒 0，而 P30 跳狗龙场 `ex` 0→237、`d5` 有 35 个不同值。
按 P29，`amount>=1` 才重置 `d5`，所以断点是「从未产生有效减气量」。但 `U` 行只在 `ret==1` 时输出，
`U=0` 只能证明没触发，**无法区分**下面两件事：

| 情形 | 含义 | 后续动作 |
|---|---|---|
| `add` 从未被调用 | ~~跨怪路径差异~~ → **P41 更正：自然静默态，不能定案** | 换层探每动作 stamina 扣减 |
| `add` 被调用但 `amount` 恒 0 | 数据层（动作参数不带减气点 / `StaminaSubRate`） | 离线解 em001 动作参数对比 em085 |

v51 就是为把这两种情形分开而做的纯观测探针。

---

## 2 · v51 改动清单（8 处，全部在 `plug/context_probe/src/lib.rs`）

| 位置 | 改动 | 性质 |
|---|---|---|
| 文件头 | v51 设计（原 A/B/C/D 判据，现以 P41 的 N/B/C/D/X 为准） | 注释 |
| 常量 | `MAX_H = 40` | 配额 |
| 静态区 | `ADD_CALL / ADD_SUM / ADD_MAX / ADD_NZ`（每槽 8 个）+ 全局 `ADD_*_G` + `H_LOG` | 纯计数 |
| `slot_of()` | 新增**只读**槽查找，不注册、不改 `CMON` | 避免 `h_exh` 挤占 R 行 4 槽配额 |
| `h_exh` | 每次调用累计 `a1`；每 10 次输出 1 条 H 行（配额 40） | 纯只读 + 有界日志 |
| R 行 | 增加 `ac / asum / amax / anz` | 每槽上游统计 |
| S 行 | 增加 `gac / gsum / gmax / gnz` | 全局上游统计 |
| `main()` | v51 横幅 + Rule 行 | 版本标识 |

**关键不变项**：`original!(a0, a1)` 参数原样透传；5 个 hook 点位/数量不变；
零游戏内存写入；W1 权重形状与 W0 门控逐字节不变；GATE_LIVE 熔断、自保护不变。
H 行同时记录调用瞬间的 `cnt / thr / proc / d5`，可直接看「通道在跑但 counter 不动」。

---

## 3 · 验证数据

| 项 | 结果 |
|---|---|
| 编译 | `cargo build --release` PASS（仅 ld `-z norelro` 惯用警告） |
| 产物 | `out/rai_exhaust_probe_v51.nro`，45056 B，md5 **`5cd6f1a0820440742ae86080a5994c41`** |
| 特征串 | `RAI v51` / `UPSTREAM EXHAUST-AMOUNT` / `H f=` / `ac/asum/amax/anz` / `gac/gsum/gmax/gnz` 齐全；`force=1` 计数 0；`h_exh` detour 符号在 |
| 冒烟判读 | `tools/make_v51_smoke.py` + `tools/analyze_v51_exhaust.py` → **PASS=22 / FAIL=0 / SKIP=0**，H=10、S 末行 `gac=200 gsum=2000`、根因判据 D |
| 降级测试 | 用 P37 的 v50 雄火龙真实日志跑 v51 脚本 → **PASS=14 / FAIL=0 / SKIP=1**，不崩溃、不误报 |
| 实机脚本 | `8_` / `7_` 改 STEP 51、`TOOL2` → `analyze_v51_exhaust.py`；CRLF `76 / 152`、bareLF **0**；执行逻辑/输出路径/Python 路径/轮转全保持；旧版备份 `out/*.v50bak` |
| 基线守卫 | `6_启动并抓日志.bat` md5 `7361445f…` 未动；`load_order.txt` 仍只有第 38 行 `RiseAI_EntryProbe`，无追加 |

---

## 4 · 部署状态

- 部署点 `mods/RiseAI_EntryProbe/romfs/nativeNX/plugins/rai_entrylocator_probe.nro` 已覆盖，md5 与产物一致 **`5cd6f1a0…`**
- 部署前已确认 `NO GAME PROCESS`
- 回退链：`rai_risepool_weight_v50.nro`（`cc48483a…`）→ `rai_tristate_v49.nro`（`ec4fcd05…`）→ `rai_exhaust_chain_v48.nro`（`f4c6d2b7…`）
- 未动游戏资源、其它 mod、`load_order`、`6_`

**本版仍是纯只读诊断探针，不是 AI 改进版**：W1 权重层、W0 门控、疲惫窗口全部原样保留。

---

## 5 · 实机判据（`lite_state_result.txt` 第二份报告会直接打印）

| 判定 | 条件 | 结论 |
|---|---|---|
| **X** | `h_exh` 未 INSTALL | 运行时首字是 IPS32 跳板，`gac=0` 不可解读，先核对 `SITE +0A30E4` |
| ~~**A**~~ | ~~`gac=0` ⇒ 跨怪路径差异~~ | **已由 P41 撤回**：v48 强制触发前 28 次动作也是 `add=0/ex=0`；`gac=0` 是自然静默态 |
| **N** | `gac=0` | **正常静默态，不能定案任何根因**（`0xA30E4` 是减气蓄积 counter 的累加入口，不是每动作 stamina 扣减） |
| **B** | `gac>0` 且 `gsum=0` | 通道在跑但 amount 恒 0 ⇒ 数据层（动作参数/ `StaminaSubRate`） |
| **C** | `gac>0` 且 `gsum>0` 且 R 行 `ex` 恒 0 | 有效 amount 被别处吞掉 ⇒ 新根因，继续追累加路径 |
| **D** | 其余 | 减气链正常，本场只是没到阈值 |

辅助字段：H 行 `a1` 值域与 `a1>0` 计数；R 行按 mon 分组的 `ac/asum/amax/anz`；S 末行 `gmax/gnz`。

---

## 6 · 建议跑法

1. 双击 `8_lite_check.bat`，选**雄火龙任务，全程不攻击怪**，让怪自己出招；
   或选跳狗龙王短场到自然流口水（约任务内 3 分钟，顺带验收 W1 疲惫形状 `wm=3 / wt>0`）。
2. 正常关游戏（别停在暂停菜单 / 任务状况菜单），别按 F9、别用即时完成。
3. 自动出两份报告，第二份是 v51 判读，看 `PASS/FAIL` 与「根因判据」那一行。

---

## 7 · 边界与风险（必须说清）

- **P33 闪退仍未归因**：v51 不新增 hook、不新增写入、不新增游戏函数调用，不引入新的写入/调用类崩溃面，但不能宣称与那次 `c0000005 accessing 0x10` 无关。
- `H` 行是**等距采样**（每 10 次调用 1 条，配额 40），不是全量；总量以 S 行的 `gac/gsum/gmax/gnz` 为准。若全场调用数 <10 且首调用未落在 `% 10 == 1`，H 可能只有 1 条。
- 每槽 `ac/asum/...` 只覆盖**已注册进 `CMON` 的 8 个槽**；全局 `gac/...` 覆盖所有调用。两者不可混算。
- `a1` 以 u32 原样累计，若游戏传入的是负数补码，`gsum/gmax` 会出现大数 —— 这本身是诊断信息，不是插件错误。
- 若 `h_exh` 因 IPS32 跳板 SKIP，`gac=0` 是「探针没装」而不是「add 没调用」，判据 X 已覆盖。
- v51 **尚未实机**；本轮所有结论止于编译 + 离线对拍 + 冒烟 + 旧日志降级。
