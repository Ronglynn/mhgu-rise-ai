# P42 · v52 每动作 stamina 观测探针（已编译、离线验收、已部署，未实机）

日期：2026-11-12 22:40 UTC+8 ｜ 任务线 `04_RiseAI`
前置：P41 更正（`0xA30E4` 不是每动作扣 stamina 的通道）｜ 回退 `out/rai_exhaust_probe_v51.nro`

---

## 1 · 离线定位结论：**GU 没有独立的「当前耐力值」字段**

先纠正一个基址口径：`refs/hpbar/main_text_decomp.bin` 里 P29 用的地址是**文件偏移（base=0）**，
P33 崩溃用的 `0x49BD3C` 才是 guest VA（base=0x200000）。二者不可混用。

按 base=0 反汇编，`0x9DBE4` 与 `0x9A470` 字节级确认 P29 §2.2：

| 地址 | 指令 | 含义 |
|---|---|---|
| `0x9DB6C` | `movw r1,#0x1428` / `ldr` | 取 `act = *(mon+0x1428)` |
| `0x9DBE4` | `movw r1,#0x4D8` | 目标偏移 `act+0x4D8` |
| `0x9DBE8` | `ldrh r1,[r0,r1]` | 读当前 amount |
| `0x9DBEC` | `add r1,r1,r3` | **加上本动作的减气点 r3** |
| `0x9DBF0` | `strh` | 写回 `act+0x4D8` |
| `0x9A454` | `movw r0,#0x4D8` / `ldrh r1,[r7,r0]` | 读出 amount |
| `0x9A470` | `bl 0xA30E4` | 交给 EXH add 累加 counter |
| `0x9A48C` | `movw r0,#0x4DA` | 下一个状态块 |

另有 `0x9DB94: movw r0,#0x4D2` 的同构累加（气绝块，可作对照）。

⇒ **GU 的模型是「每动作 amount → 累计 counter(`act+0x5D82`) vs 阈值(`act+0x5D84`)」**，
不是 Rise 侧「被轮询的当前耐力值」。P20 的「该追当前耐力值」是 Rise 侧 RSZ 推断；
`cEmStaminaData::cStaminaLev` 在 `mon-class-map.md §D` 只有孤立类名、**无成员表**
（文档第 409 行自述为「本批最大覆盖缺口」），`member-offsets.tsv` 只有参数类的
`StaminaSubRate @+0x14` / `StaminaTimeVal @+0x20`，都不是运行时当前值。
`mon+0xCAC0 → +0x3F/+0x5C` 已由 P38 实机否定。

因此 v52 不再假设能离线定案某个「当前耐力」偏移，而是：
**① 直接观测每动作 amount（`act+0x4D8`）；② 让实机数据自己指出候选字段。**

## 2 · v52 三层纯只读观测

| 层 | 载体 | 内容 |
|---|---|---|
| **Y 行** | 已装 `h_start_40`(`0xAFF40`) | 每 2 个动作 1 条，配额 200：`am=act+0x4D8`（每动作减气点瞬时值）、`d2=+0x4D2`（气绝对照）、`ex/thr/proc/d5/st`、动作号 `a/s`、`amx`（该槽每帧峰值） |
| **每帧统计** | `forge_onUpdate` | 每帧读 8 槽 `act+0x4D8`，累计 `AM_MAX/AM_NZ/AM_RISE`，S 行输出 `amx/anf/anr`。R 行 150/30 帧快照两场 `amt` 恒 0，是因为该值同帧内被 `0x9A470` 消费后清零 |
| **候选耐力扫描** | R 行 | 从 `p=*(mon+0xCAC0)` 读 `+0x40,+0x44,+0x48,+0x4C,+0x50,+0x54,+0x58,+0x60` 共 8 个 u32（`q40..q60`），判读脚本自动列出 `uniq>1` 的字段 |

**全部不变项**：5 个 hook 点位/数量（`nm` 实测 detour=5）、`original!` 参数透传、
零游戏内存写入、W1 权重形状、W0 门控、v51 的 H/ac/gac 探针、GATE_LIVE 熔断。
跨怪通用、不硬编码 action_id / 怪种数值。

## 3 · 验证数据

| 项 | 结果 |
|---|---|
| 编译 | `cargo build --release` PASS（仅 ld `-z norelro` 惯用警告） |
| 产物 | `out/rai_per_action_stamina_v52.nro`，45056 B，md5 **`0d1d97c6d120e5fd84b224dfdc1c24d7`** |
| 特征串 | `RAI v52` / `PER-ACTION STAMINA` / `Y f=` / `q40=` / `q60=` / `amx/anf/anr` / `ROLLBACK v51.nro` 齐全；`force=1`=0；v51/v50 历史横幅保留 |
| 冒烟 | `make_v52_smoke.py` + `analyze_v52_stamina.py` → **PASS=26 / FAIL=0 / SKIP=0**，Y=20、`am` 值域 [10,15]、`amx=15 anf=430 anr=198`、判据「已捕获每动作减气 amount」 |
| 降级 1 | v51 暂停中真实快照 → **PASS=16/0/SKIP=1**，判据 N，v52 段正确跳过 |
| 降级 2 | v50 雄火龙真实日志 → **PASS=14/0/SKIP=1**，不崩溃、不误报 |
| 实机脚本 | `8_` / `7_` 改 STEP 52、`TOOL2`→`analyze_v52_stamina.py`；CRLF 77/156、bareLF **0**；旧版备份 `out/*.v51bak` |
| 守卫 | `6_` md5 `7361445f…` 未动；`load_order.txt` 仍只第 38 行 `RiseAI_EntryProbe`；游戏资源/其它 mod 未动 |

## 4 · 部署

- 部署前确认 `NO GAME PROCESS`
- `mods/RiseAI_EntryProbe/romfs/nativeNX/plugins/rai_entrylocator_probe.nro` 已覆盖，
  md5 与产物一致 **`0d1d97c6…`**
- 回退链：`v51 5cd6f1a0…` → `v50 cc48483a…` → `v49 ec4fcd05…` → `v48 f4c6d2b7…`

**本版仍是纯只读诊断探针，不是 AI 改进版**：W1 权重层、W0 门控、疲惫窗口逐字节保留。

## 5 · 实机判据（第二份报告直接打印）

| 判定 | 条件 | 结论 |
|---|---|---|
| **捕获** | `Y.am>0` | 每动作减气点已抓到，可统计「动作 → 减气点」分布 |
| **存在但错过** | `Y.am=0` 且 `S.amx>0` | amount 真实存在，同帧被消费清零，Y 行时机需前移 |
| **通道未走** | 两者皆 0 | `0x9DBE4` 本场不走；下一步才需要 hook `0x9DB54/0x9DBE4` 抓 `r3`（须先核对 IPS32 运行时首字） |

辅助：`R` 行 `q40..q60` 的 `uniq` 列 —— 随动作下降 / 随时间恢复且 `uniq>1` 的字段才是
「当前耐力」候选；`s3f/f5c` 已由 P38 否定，保留仅为兼容。

## 6 · 建议跑法

1. 任一场任务均可，**让怪多出招**（跳狗龙王短场还能顺带验收 W1 疲惫形状 `wm=3/wt>0`；
   雄火龙场则继续积累跨怪对照）。打不打怪都有效（P41）。
2. 正常关游戏，别停在暂停菜单，别按 F9 / 即时完成。
3. 看第二份报告的「v52 每动作 stamina」段 `判定` 行与 `Y.am` / `S.amx`。

## 7 · 边界

- **尚未实机**；所有结论止于离线反汇编 + 编译 + 冒烟 + 两代真实日志降级。
- `act+0x4D8` 是**每动作 amount 缓冲**，不是「剩余耐力」；`ex` 是累计 counter，
  两者都不是当前耐力值。真正回答「GU 有没有当前耐力」要靠 `q40..q60` 的实机扫描。
- `q40..q60` 只是**候选区间**（依据 P20 §5 的 `p+0x3F` 状态字 / `p+0x5C` 计时器位置外推），
  若实机全 0 说明 `p` 无效或字段不在该区，需换扫描区间，不能当成定案。
- Y 行是等距采样（每 2 个动作 1 条、配额 200），不是全量；`S.amx/anf/anr` 是 8 槽汇总，
  不等于单槽值。
- 每帧 8 次 `rd16` 属新增只读开销（约 480 次/秒 @60fps），未改任何写入/调用面；
  P33 的 `c0000005` 仍未归因，本版同样不能宣称与之无关。
- 若三种判定都指向「通道未走」，下一步新增 hook `0x9DB54` 会突破「5 hook / 零新增」
  纪律，须先实机核对运行时首字（`E28FFxxx` 不可 hook）并单独评估。
