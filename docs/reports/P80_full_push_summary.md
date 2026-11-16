# P80 · 「继续完成未完成的任务」总汇总（2026-11-15 20:45 定稿，全离线、零实机）

## 0 · 一句话

**本轮把「未闭环」里能离线推进的全部推进了，并且翻案了两条由「只抽 em131 一只怪」导致的错误定案、修掉一个成品版真实缺陷、部署了成品 v2。但原目标仍未完全实现**：Rise 侧静态证据比之前认为的丰富，GU 侧的结构性限制（引擎层 / 执行层 / 6 hook / 零写入）没有改变，成品 mod 仍是「机制级最大复刻」。

## 1 · 回答前两问

- **模型**：腾讯混元 Hy（Tencent Hunyuan Hy）。
- **是否实现本 mod 任务目标**：**没有完全实现**。准确说法 = 在当前四条纪律（零写入 / 跨怪通用 / 不硬编码 action_id / 6 hook 全在抽选层）+ 无 Rise 实机反汇编下，**可交付的最大机制级复刻已做完、验收通过并部署**。按 Rise L0–L7 分层：L6 加权抽选达成；L2/L4/L5 机制级近似；L3 结构性证伪；L0/L1 与 L7 空白 ⇒ 7 层里 **1 达成 / 3 近似 / 1 证伪 / 2 空白**。详见 `out/P80_goal_achievement_assessment.md`。

## 2 · main 亲自完成（三项）

| # | 工作 | 结论 | 产物 |
|---|---|---|---|
| 1 | 30 分钟日志配额静态审计 | 最忙 epoch 4780 行；30/60/120 分钟预计 17,208/34,416/68,832 行，MAXLOG 1M 占用 1.72/3.44/6.88%，理论 29.1 小时。**配额每 30000 帧重置 ⇒ 任务时长本身不会造成整场停写**，唯一线性增长的是总 log 序号。仍非 30 分钟实跑。 | `tools/audit_p80_30min_quota.py`、`out/P80_30min_quota_audit.md/.json` |
| 2 | **查出并修复成品真实缺陷 → 部署 v2** | 成品 `MAX_QX=400`、实测每 epoch 1237 次 QX 事件，`STANCE_CUR/F` 原在 QX 日志分支内 ⇒ 前 32% 后 W4 处境维静默停更。已把 stance 更新移出日志分支（等价改造 / 零新增 hook / 零写入），重编译部署 **v2 `c174b191…`**（61,440 B / 6 detour / 特征串全 0 / NRO 头同构 / build_id 全新）。**P75「`MAX_QX` 不得置 0」定案作废**。v2 未实机复验。 | `out/P80_stance_quota_fix.md`、`out/rai_release_v2.nro`、`out/deployed_release_v1_dfab157d.nro`、`out/release_profile.md` |
| 3 | 工具回归 | 修正口径后的判读：模拟 68/0/2、P79 实机 64/0/4；完整性自检 OK。 | `out/P79_v71_acceptance_judgement.txt` |

顺带发现 Q/M/X/ZS/E 老诊断配额在单 epoch 内就打满（60/60、40/40、20/20、2/2、38/40），只影响诊断行、不 gate 任何 AI 状态 ⇒ 判为**已知无害**，不为此再改插件。

## 3 · 子任务 A：对象引用解析（已交付）

`out/P80_object_ref_resolution.md`（§1–§8，约 330 行）、`tools/rsz_parse_v2.py`、`out/rsz_main_json_v2/`（12 JSON + 556 行 `_summary.json`）、`out/_v2_full_468.py`。

- **修复成功**：12/12 文件 `parseOK`、Object 引用 **1038/1038 合法**（v1 有 10 个非法）、数组 count 293/293 合理、`bytesConsumed == dataRegionLen` 且 `tail=0`。main 自己也独立复跑过（12/12 全 OK）。
- **根因**：RSZ 的 `userdataOffset` 指向 data 段**之前**的 userdata info 表；userdata 实例数据在外部分件、主 data 流占 0 字节，v1 却按 fields 内联解析导致其后整体错位。垃圾 ref `0x4BCCF5F2` 等其实是合法的 `_TreeNodeID` U32 哈希。**二进制干净，P78「需干净二进制」前提作废**。
- **Hub→15 池因果链仍不能重建**，但卡点从「解析失败」精确化为**结构性**：① RSZ 引用是文件内 instance index，无跨文件引用槽；② 12 个 `attack_stance_*` Hub 内 `_TransitionActTbl`/`_TransitionRate`/`ConditionInfo`/`ActionTableData` 全 0，池轮盘 376 条全在 83 个池文件内部；③ Hub 唯一引用出口 `_ReferenceThinkData` 指向 15 个外部分件，15/15 未被抽取且都不是池文件；④ 标量无共享有效 TableNo（Hub `{65535}` vs 池 `{0,1,3,4,5,6,7,8}`）。
- ⇒ **「W4 12 Hub 数据表级 1:1 不可做」定案不推翻，反而加强**（标量 + 对象引用 + 结构归属三重实证）；「对象引用解析」待办关闭。新增正面结果：Hub 内部对象图 100% 可信，可用于后续资产抽取定位。
- 边界：补充查证的 107 个 `rise_unpack` 文件里 12 个 Hub 因模板缺类 `0df87250` 仍失步（95/107 parseOK），其标量数值不作定量依据；结构结论来自 instanceInfo/类定义，不受影响。

## 4 · 子任务 B：52 只怪全量资产（v2 定稿）

`refs/_bulk_extract/`（468 文件 / 52 个 emNNN）、`out/rsz_bulk_json_v2/`（468 v2 JSON + `_diag_summary.json`）、`out/rise_bulk_facts.json`（20:29 已更新为 v2 定稿）、`tools/bulk_*.py`、`out/P80_bulk_monster_assets.md`（v2 定稿）、`out/bulk_*` 日志。抽取主 pak + patch 两步 `--override` 均 EXIT=0，命中 468 = 目标 468、EXTRA=0/MISS=0、不含 em131。

> **质量演进（三方一致）**：B 首批 `out/rsz_bulk_json/` 是 v1 产物，252/468 含越界引用、1899/24371 非法引用。**B 已按 main 要求全部改用 v2 重解析定稿**，v1 产物弃用。v2 全量 **430/468 `parseOK`、574/23844 非法（−69.8%）**；38 个失败全在 act/combo（**37 个模板缺类** 9 类 / 52 实例 + **1 个 String 内联 UTF-16 变长串模式** `em007_act_001`，第三种独立失步；全库仅 3 个 String 实例且都在已排除的 act/combo，见 A 报告 §8.5/8.6）。`main`/`combat_main`/`range_data`/`stamina_data` 各 78/78 全 OK、0 非法；**main 与 parser-ref 各自独立跑出同一组数字**（parser-ref 全量背书另有 **438/468 tail=0**；`range_data`/`stamina_data`/`main`/`combat_main` 四类各 78/78 全 `parseOK`、0 非法引用，range/stamina 的 v1↔v2 ref 序列逐项一致 ⇒ Q(a)/Q(c) 不受解析器选择影响）。措辞精化：「ud=0 ⇒ v1 完全正确」**只适用于 range_data / stamina_data 两类**；act/combo 另有模板缺类失步，`em007_act_001`/`em072_act_002` 出现「非法 ref=0 却 `partial` 提前 break 丢字段」⇒ **一律按 `diagnostics.parseOK` 过滤，不能把「非法 ref=0」当完整判据**。

**main 独立复核 1（严格）**：78 个 `range_data` + 78 个 `stamina_data` ⇒ **156/156 `parseOK`、`tail=0`**（`out/P80_v2_crosscheck_52monsters.json`）⇒ (a)(c) 牢固。

**main 独立复核 2（全量）**：468 个原始文件 ⇒ **430/468 `parseOK`**（`out/P80_v2_full_bulk_crosscheck.json`）；(b) 的定量结论只适用于 v2 解析成功的 **118 个 act/combo 文件**，其余不作定量依据。

> **后续补做的实验判定（parser-ref §8.7，本轮不做）**：对 37 个模板缺类文件试「未知类实例统一占 S 字节」16 个候选，仅 **11/37（29.7%）** 能修到 `parseOK + tail=0`，26 个修不好（多未知类实例叠加 String 变长字段）。补 66 MB `rszmhrise.json` 模板需要完整字段布局（name/type/size/align/array，二进制推不出字段名）且会改动所有人基线；扩 v2 容错会让已定稿的 468 份 v2 产物与工具版本不一致，且修好也不改变任何定案（那 37 个只是 Q(b) 结构佐证）⇒ **补模板与扩容错两项本轮都不做**。保留线索：最佳 S=28 在 10 个文件重复，暗示 `0df87250` 数据长约 28 B。

> **排除口径有效性佐证（parser-ref 关闭前补充）**：过滤前 `TableNo == 文件号` **156/156**，按 `diagnostics.parseOK` 排除 38 个不 OK 文件后 **118/118**，两者一致性都是 100%（156 − 38 = 118，数字自洽）⇒ 按 `parseOK` 排除**没有误伤有效样本**，Q(b) 的「表号 = 文件号」一跳在可信集内完整成立，不只是单方面声明「不作定量依据」。

### 4.1 三问结论（v2 定稿口径）

| 问 | 结论 |
|---|---|
| (a) 全怪 range_data 是否有 5 元素递增几何阈值 | **没有 5 元素递增阈值数组**：0/78 文件、唯一有效 len5 数组 2 个且非单调。但 **`_RangeDistance` 255 处全部 4 元素、255/255 严格递增、95 种、49/52 怪数值不同**（如 `[6,12,17,22]`/`[10,20,35,50]`/`[12,25,40,60]`）⇒ 4 阈值切 5 区间，与 Rise 15 池 `range1..5` 及 GU dttune 4 档 f32 **同构**。另 312 个 `_range_hate_add_data`（309 个 len4 + 3 个 len5）**312/312 非单调** ⇒ 纯仇恨参数、不是几何阈值（v2 定稿最强证据）。 |
| (b) `TableNo → _actionNo → 招式名` | **不能完整建立**：v2 可信子集 118/118 `parseOK`、0 非法引用、tail 全 0；**118/118 文件 `_TableNo` = 自身文件号**（文件名级映射可建）、90 个文件有 `_ActionNo` 值域 **1..5075**（v1 的 0..30594 是失步污染，已作废）；RSZ 唯一 name 字段是 `_partsNames`/`_selectPartsName`（部位名）。filelist 180,405 行里 enemy `.msg`=**0**、招式名文本候选=**0**、638 个 enemy `motlist` 全是编号文件；全库 `message` 是 GUI/玩家技能文本 ⇒ 最后一跳「→招式名」**无文本源可挂接**，且 RSZ 无跨文件引用、两类字段无标量外键。 |
| (c) `_tiredSec`/`_motRate` 是否跨怪恒 0/1 | **否**。78 个 stamina_data：`_tiredSec` 12 种值（30~120 秒，61/78 非 0）、`_motRate` 7 种值（0.8~1.0，60/78 非 1.0）。**em131 的 0.0/1.0 是 17/78 默认特例**。tired/fatigue/rest 命名字段 156 处，全在 stamina_data 的 `_tiredSec`/`_hyakuryuTiredSec`；action/combo 全怪无（P78 这部分观察成立；另有 1 处 `isTiredDisable` 在 parseOK=False 的语音事件文件，不作定量依据）。 |

### 4.2 由此改写两条 P78 定案（本轮最重要的证据修正）

| 旧定案（P78，仅基于 em131） | 全怪实证 | 修订 |
|---|---|---|
| ① W2 路线 B「结构性不值得 / 对错了层」：Rise `range_data` 是 4 档仇恨/气息参数、无 5 元素阈值数组、非单调 ⇒ 不是阈值阶梯 | 255 个 `_RangeDistance` 全 4 元素严格递增、95 种、49/52 怪数值不同；312 个非单调数组全是 `_range_hate_add_data` ⇒ 两类字段被 P73 混为一谈 | **定案 ① 作废 / 改判（B 的 v2 定稿已同步）**：Rise 距离档层是几何阈值，4 阈值→5 区间，与 GU dttune 同构。**但 W2 机制级实现裁定不变**：路线 A 按 `(st3, hit/ts)` 已实机通过（`wb=59/bf=25`）、`ZT=0` 读不到运行时链、Rise 世界单位不可套 GU、v71 rodata 仅 1608 B ⇒「层是对的，但按怪种编译 137 表不值得」，**不恢复路线 B 待办**。 |
| ④ 「疲惫数据表级复刻否定」：`_tiredSec=0.0`/`_motRate=1.0` ⇒ 疲惫时长运行时动态、非静态可复刻 | 61/78 怪有非零静态疲惫时长、60/78 怪有 <1.0 的动作速度倍率 | **定案推翻**。Rise 疲惫时长与动作速度是**静态可复刻数值**。但 **GU 侧行为结论维持**：6 hook 全在抽选层、`Stamina_low_Start/tired_start/tired_Loop` FSM 与 `+0x50C` 倒计时在引擎层 ⇒「疲惫喘息 / 输出窗口放大做不到」的理由从「Rise 侧无静态数值」改为「GU 侧执行层不可达」，且现在有了可对标的具体目标值。P72 §6 相应论据同步作废。 |

另：全怪 `_EmTypes` 数组长度 1–7（77 处）进一步印证 Rise 侧 `PredatorData` 有怪种枚举；**P74 领地争夺 [C] 定案不变**（GU 侧无等价类/表这一半未变）。③ Hub→池因果链由 A **加强**，不变。

### 4.3 「W2 路线 B」判读裁定（main 裁定，B 报告 v2 定稿后已同步改判）

B 首版 §3① 曾主张「对错了层」维持，依据是「Rise 侧无 5 元素递增阈值数组、15 池 `range1..5` 是池索引」。main 不采纳该判读；B 用 v2 重解析定稿后**已把 ① 改为作废/改判**。理由：

- 5 个距离区间（`range1..5`）**由 4 个阈值切分**，本就不该找 5 元素数组；`_RangeDistance` 255/255 是 4 元素严格递增 f32 ⇒ 正好切出 5 区间，与 GU `dttune` 4 档 f32 **同构**（P61 最初的结构判断其实成立）。
- P73 把 `_range_hate_add_data` 的 `[8,5,3,1]`（非单调仇恨参数）当成距离阈值，才得出「4 元素数组非单调 ⇒ 不是阈值阶梯 ⇒ 对错了层」。v2 定稿把两类字段分开（仇恨参数 312/312 非单调 vs 几何阈值 255/255 严格递增）后，该论据彻底作废。
- ⇒ **裁定**：P73/P78 ① 的**理由作废**，措辞改为「层是对的，但按怪种编译 137 张表仍不值得」；**结论维持**（路线 A 已实机通过、`ZT=0`、Rise 世界单位不可套 GU、rodata 仅 1608 B）。B 的「无 5 元素递增数组」命题本身仍成立，只是推不出「无几何阈值层」。**改判 ≠ 恢复路线 B 待办**。

### 4.4 跨怪通用性（B 报告 §3③）

52 怪字段结构一致（同一套 `EnemyStaminaData` / `EnemyRangeData` / `ThinkState` 类），但数值按怪变化：疲惫时长 12 种、动作速度倍率 7 种、`_RangeDistance` 95 种数组且 **49/52 怪数值不同**。⇒ **通用性在结构与规则层，不能硬编码单一常量** —— 这是现有 mod「跨怪通用 / 不按怪种编译表 / 只走抽选层」纪律的静态证据支持；若将来放宽纪律按怪种建表，也必须「按怪取值」，且 W2 机制级实现仍是更稳妥的裁定。

## 5 · 更新后的「未闭环」清单

**已关闭（本轮）**：对象引用解析；其它 52 只怪资产抽取（含 v2 全量重解析）；30 分钟配额静态审计；成品 `MAX_QX` 饿死 W4 处境维缺陷；P78 ①④ 两条证据错误；Q(b) 断点精确化。

**仍未闭环（真做不了 / 需外部条件）**：
1. 30 分钟**实跑**日志（只有静态审计；成品版关了大部分日志，要验需回退探针版打一场，用户已明确不想多打实机）。
2. Hub→池因果链：结构性不可由静态对象引用重建，需 L0/L1 运行时证据（Rise 实机/反汇编）或补抽 15 个外部分件。
3. `_TableNo → _actionNo → 招式名` 完整中间表：**已定位为结构性断点**（enemy `.msg`=0、招式名文本候选=0、638 个 motlist 全是编号文件、RSZ 无跨文件引用）；除非另抽并解析 `.motlist.528` 二进制按编号索引，否则不能建。
4. 15 池 `range1..5` ↔ 95 种 `_RangeDistance` 数组的索引对应中间表。
5. GU 侧执行层（L0/L1/L7）：疲惫喘息、动作速度、12 Hub 1:1、领地争夺 —— 均需放宽纪律或新增 hook，属另一条技术路线。
6. 跨怪实机仅 3 种（轰龙 / 斩龙 / 泡狐龙）；137 怪全覆盖需多场实机。
7. 成品 v2 未实机加载复验（只做了静态校验）。

## 6 · 交付物与状态

- 部署：`mods/RiseAI_EntryProbe/.../rai_entrylocator_probe.nro` = **v2 `c174b191549cc734806ef67b99298520`**（61,440 B / 6 detour），下次启动生效。
- 回退链：v1 `out/deployed_release_v1_dfab157d.nro` → v71 探针 `out/deployed_v71_1d513ec3.nro` + `lib.rs.v71bak`；两份覆盖回去 + 重启。
- 源码主线 `plug/context_probe/src/lib.rs` = `lib.rs.release`（md5 `28e74de6…`），只改 stance 更新位置。
- 未动 `6_` / `7_` / `run_v66.cmd` / `load_order.txt` / 音频 mod / 游戏资源；全程零实机、零游戏写入。
- 报告索引：`P80_goal_achievement_assessment.md`（目标达成度）、`P80_30min_quota_audit.md`、`P80_stance_quota_fix.md`、`P80_object_ref_resolution.md`（含 §8 全量验证与 String 模式）、`P80_bulk_monster_assets.md`（v2 定稿）、`P80_full_push_summary.md`（本文）。
