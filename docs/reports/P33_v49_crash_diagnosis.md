# P33 · v49 首场实机闪退诊断（2026-11-12 20:28）

用户反馈：v49 实机任务中闪退。本轮**只读诊断**，未改动插件、部署、bat、游戏资源、load_order。

日志现场已归档：`out/game_p54_lite_20261112_2028_v49_CRASH.txt`（647,686 B / 6291 行）。
修正后的判读：`out/P33_v49_real_machine_report.txt`（原 `lite_state_result.txt` 保留不覆盖）。

---

## 1 · 崩溃现场（逐字）

```
6248 | *** exception c0000005 accessing 0x10
6249 |     host pc 7ff6dd45ed49 (?+0)
6250 |     host lr 0 (?)
6287 | guest: sp=efffdab0 lr=00000000 (?+0) pc=0049bd3c
6288 |   r0  00000000  r1  0000000f  r2  3f80256a  r3  00000000
6290 |   r8  0c163940  r9  00000000  r10 0c165e00  r11 00000000
```

- `c0000005 accessing 0x10` = **宿主侧空指针 +0x10 读取**（`ldr rX,[r0,#0x10]`，r0=0）。
- host backtrace 34 帧，#13 起为 guest 函数帧：`f_49b8e8+1edc` / `f_49b65c+194` /
  `f_e07640+31e` / `f_5da8fc+62b` / `f_d8692c+130` / `f_a6538c+8c` / `f_3a82e8+e8` /
  `f_2478d80+13b`。
- `text_addr=0x00200000`（NOTES §110/§212）⇒ guest pc 偏移 `0x29BD3C`。
  反查 `refs/hpbar/main_text_decomp.bin`：`0x49bd3c = E3500001` = `cmp r0,#1`；
  其前 `0x49bd34 = E5900000` = `ldr r0,[r0]`、`0x49bd38 = EB099153` = `BL`。
  崩溃函数 `0x49b8e8` prologue 为 `E92D4FF0` push 家族，第二现场读 `[r4+0x1470]`。
- `lr=0` 与历史 v20 崩溃（`FATAL: no function at 0`，`pc=0`、`lr` 有效）**形态不同**，
  不是同一种 guest 间接跳空指针。

## 2 · 崩溃前的路径线索（关键）

末 10 条非 `[rai]` 行全部是**玩家侧**探针，且对象恒为 `0C163900`（玩家对象，不是怪物）：

```
[guest] MHGU_FIX40_FX_TEST25: native_combo_state / terrain_entry_reset /
        action_committed / motion_bound / native_combo_seen ...
```

全文计数：`FIX40_FX_TEST25` **1326** 条、`gogport: dmg special path` **117** 条、
玩家对象 `0C163900` **1497** 条。guest 崩溃寄存器 `r8=0C163940`、`r10=0C165E00`
也落在同一玩家对象区间。⇒ **崩溃发生在玩家动作/连招/伤害结算路径，不是怪物 AI 抽选路径**。
（`MHGU_FIX40_FX_TEST25` 属音频任务插件，NOTES §278 已定性；本任务不碰。）

其它现场：
- 末 `[rai] R f=37950`；末 `BEAT f=37800`，`live=1`、`hub=15`、`fail=0`、`ok=141`。
- `N f=34800 ENTER-LOW dA=1`，`low=1` 持续 3150 帧（≈52 s）到崩溃 ⇒ 长时间低活动，
  符合「停在任务状况/暂停菜单」的已知陷阱（P19/P22/P28/P30），但不等于崩溃原因。
- `[fs] mounted host directory .../save/save_0` 出现在 `f=37800` 附近。
- `[forge] [INFO] [KatSmithy]` GUI 日志持续到崩溃前 4 行。

## 3 · v49 侧健康检查（全部正常）

| 项 | 实机值 |
|---|---|
| 5 个 hook | **全部 INSTALL**：`h_matcher/h_emc/h_unify/h_exh/h_start_40`；`SITE +0A30E4=E92D41F0` 校验通过 |
| `FATAL` / `live` / `hub` | `0` / `1` / `15`（`GATE_LIVE` 未熔断，自保护未触发） |
| 主规则 | `sel=254 act=254 beg=254 begf=0 rep=34 v=34 noalt=0 fail=0`，35 条 V 行 `rd=1`、`sw=100` 全合法 |
| 三态映射 | 35/35 条 `st3→vd` 零违例，`d3=34 == s1=34` |
| 强制残留 | `U` 行 `force=1` 计数 0（v48 强制确已移除） |

**代码面因果判断**：v49 是**纯只读**，零游戏内存写入、零游戏函数调用、
5 个 hook 与 v48 同点位（v48 已实机 PASS=11/0 且零崩溃）。v49 新增的游戏内存读取
（`act+0x518`、`act+0x5D8C`、`act+0x5D84`）都是 v48 的 C/R 行**已经读过的字段**。
⇒ **不存在「v49 把某对象写成 0」的路径**，与 `CRASH_20261108_death.md §4` 的判定逻辑一致。

## 4 · 归因裁定（分层，不夸大）

| 层 | 判定 |
|---|---|
| **基本可排除** | v49 直接写出空指针 / hook 栈帧破坏 / 中段 hook（历史 v3/v5 根因）。5 hook 全在入口、首字校验通过、零 FATAL、v38 主规则全程正常 |
| **基本可排除** | 怪物抽选层本身。崩溃 guest 帧与寄存器指向玩家对象 `0C163900`；末条 `[rai]` 是正常的 `R` 行快照 |
| **不能排除** | **时长/时序诱发**：这是 `c0000005` 在归档日志中**首次出现**（`04_RiseAI/out/game_p54_lite_*.txt` 全部计数 0）；本场 `37950` 帧 > v48 最长 `27750` 帧；且处于 3150 帧低活动窗口。v48 未在同等时长/场景跑过，不能据此证明「与版本无关」 |
| **不能排除** | 其它 mod 的玩家侧路径：`FIX40_FX_TEST25`（音频线）、`gogport: dmg special path`、`KatSmithy` GUI、`MH4U Port` 的 IPS32 解释器变体 |
| **未定案** | 因此**不建议**在未归因前改插件参数或推进高还原度重构（见 P34 阶段 A） |

## 5 · A/B 隔离（按 `CRASH_20261108_death.md §6` 的成熟做法）

按成本递增，任一步得出「仍崩」即可停止并把探针排除：

1. **可复现性**：保持 v49 不动，同一任务、同样操作/时长复跑一次 ⇒ 判断是否偶发。
2. **版本对照**：用 `out/rai_exhaust_chain_v48.nro`（`f4c6d2b7…`，P30 实机稳定）覆盖部署，
   同场景复跑。
   - 仍崩 ⇒ 与 v49 无关，转第 3 步；
   - 不崩 ⇒ v49 新增面相关，回退 v48 并单独定位（优先查「长时间低活动窗口」下的 `forge_onUpdate` 频率）。
3. **彻底排除探针**：备份 `load_order.txt`，把 `RiseAI_EntryProbe` 改为
   `# off: RiseAI_EntryProbe`，同场景复跑。仍崩 ⇒ 探针彻底排除，转向其它 mod
   （顺序：`FIX40` 音频线 → `MH4U Port` → `gogport`）。
4. 纪律：**不动** `6_启动并抓日志.bat`、音频 mod 工作流、`Show HP Bar`、
   游戏资源；改 `load_order` 必须先备份。

> 每一步只需用户回报「是否闪退 + 大概任务内时间」，日志由 `8_lite_check.bat` 自动落盘。

## 6 · 本轮发现的两个确凿缺陷（与闪退无关，但影响 AI 正确性）

### 6.1 判读脚本假 FAIL —— **已修**
`analyze_v49_states.py` 用 `l.strip().startswith("[rai] INSTALL")` 检测安装行，
但实机行带宿主前缀 `[forge] [INFO] [rai] INSTALL ...` ⇒ 报 `INSTALL=0`（假 FAIL）。
已改为 `"[rai] INSTALL h_" in l`，并新增「零 host 异常」判据与 `proc>30` 告警。
修正后：**PASS=14 / FAIL=7**（原 12/8，两个假 FAIL 消除，新增 1 条真实崩溃 FAIL）。

### 6.2 v49 的 proc 误判 —— **待修，本轮不动插件**
唯一 T 行：

```
T f=20970 kind=1 reason=2 i=1 mon=0C430060 tir=1 proc=211 an=5
```

`proc=211` 远超 `grow` 上限（P29 定案 cap 30、实机 0→1→2→3）⇒ 把**非目标槽**
`act+0x5D8C` 的无关字节当成 proc 递增，制造了**假疲惫窗口**（且落在 i=1 而非主怪 i=0）。
佐证：`U=0` ⇒ 本场 `h_exh` 一次都没返回 1，**根本没有真实减气触发**；
`V` 行 `st3` 集合只有 `{0,1}`、`s2=0`、`skip=0`、`T EXIT=0`，全部由此解释。

修正口径（留待 v50，不在归因前改部署）：
- proc 合法性 `0 < proc <= 30`，且 `thr` 合法（`0 < thr < 0x4000`，排除 `65535` 免疫哨兵）；
- `h_exh` 已 INSTALL 时，**只信 `ret==1`**，proc 轮询降级为纯观测，不再触发窗口；
- 疲惫窗口只对「有减气块的主怪槽」生效（按 `thr` 有效值筛选），不扫小怪槽。

## 7 · 本场对 v49 三态结论的影响

**本场不能作为三态层的实机验收**：闪退中断 + 未出现自然疲惫（`U=0`）+ 只有一条假疲惫事件。
有效的正向证据只有：5 hook 全装、零 FATAL、live=1、hub=15、`st3→vd` 35/35 零违例、
怒态 `depth=3` 生效（`s1=d3=34`）、v48 强制已移除。
`P31` 的「待实机」状态**保持不变**。

---

**本轮收尾**：只读诊断 + 判读脚本修正 + 日志归档；插件仍 `ec4fcd05…`，
`6_`、load_order、游戏资源、其它 mod 均未改动。
