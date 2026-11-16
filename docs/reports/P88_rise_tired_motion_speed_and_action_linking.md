# P88 · Rise 疲惫是否降低攻击动作速度 / 疲惫时两招如何衔接（2026-11-15 22:55）

用户两问：① Rise 侧怪物疲劳是否会降低攻击动作速度？② Rise 侧疲劳时两个攻击动作之间是如何衔接的？
**本轮纯只读静态复核**，补做一次逐动作参数重解析，得到一处对 P72/P86 暗示的修正。

---

## 0 · 结论先行

| 问 | 答 |
|---|---|
| ① 是否降低攻击动作速度 | **是，但只有「按怪全局倍率」一层有静态数值证据**：`EnemyStaminaData._motRate` 0.8~0.98（60/78 = 76.9% 怪 <1.0，降幅 2%~20%；18/78 恒 1.0）。逐动作字段 `_tiredMotSpeedLowerLimitValue` **不是降速倍率**，而是下限保护值，856 个动作中 814 个禁用、42 个为 1.0、**无任何 <1 值**。该倍率只拉伸动作时长 `dS`，不改变两招之间空档 `dE`（P85 维持）。 |
| ② 两招如何衔接 | **疲惫前后衔接机制同构，静态侧没有「招间间隔 / 冷却」字段**：`_IsActionEnd` 门控（动作结束才允许重抽）→ L5 条件检查（prev 表 / Think 计时器 / 计数器）→ L6 百分制轮盘（555/555 率和恒 100，每次必命中一个动作）→ L7 载入 `action/` 或 `combo/` 资源。疲惫时唯一变化是 **L4 换到 tired 五池**；玩家感觉「两招变久」来自动作变慢与引擎层插入待机/发呆/进食，不在 L3–L7 数据表里。 |

---

## 1 · 问①：疲惫降速的两层证据

### 1.1 按怪全局倍率 `_motRate`（78/78 `parseOK`）

本轮全量复核 `out/rsz_bulk_json_v2/*stamina_data*.json`：

| `_motRate` | 怪数 | 相对原速 |
|---|---|---|
| 0.80 | 1 | −20% |
| 0.85 | 5 | −15% |
| 0.90 | 28 | −10% |
| 0.92 | 15 | −8% |
| 0.95 | 9 | −5% |
| 0.98 | 2 | −2% |
| **1.00** | **18** | 不降速 |

⇒ **60/78 = 76.9% 的怪疲惫时动作播放速度被下调 2%~20%**；同文件 `_tiredSec` 30~120 s（61/78 非零）决定该状态持续多久。em001 = 60.0 s / 0.92，em002 = 80.0 s / 0.92。
证据等级：字段名 `mot` = motion 的语义推断 + 静态实例数值；**无 Rise 反汇编 / 实机绑定**。是否只作用于「攻击动作」无法区分（P20 原文「可能也不只是攻击动作」）。

### 1.2 逐动作层：本轮修正（重解析 3 个 `action_param_data`）

用 `tools/rsz_parse_v2.py` 重解析 `refs/rise_unpack/.../em00{1,2,3}_action_param_data.user.2`（三文件全部 `parseOK`、`bytesConsumed == dataRegionLen`、零非法引用），统计 `snow.enemy.EnemyActionParamData.ActionInfo`：

| 怪 | ActionInfo | `_tiredMotSpeedLowerLimitValue = -1.0`（禁用） | `= 1.0` | 其它值 | `_angerMotSpeedUpperValue` |
|---|---|---|---|---|---|
| em001 | 296 | 280 | 16 | 0 | −1.0×274 / 1.0×22 |
| em002 | 393 | 377 | 16 | 0 | −1.0×342 / 1.0×51 |
| em003 | 167 | 157 | 10 | 0 | −1.0×146 / 1.0×20 / **1.1×1** |
| **合计** | **856** | **814 (95.1%)** | **42 (4.9%)** | **0** | 唯一非 1.0 显式值为 1.1 |

**修正 P72 §6 / P86 的暗示**：`_tiredMotSpeedLowerLimitValue` 字段确实存在，但在这 3 只怪里**没有任何 <1 的值** ⇒ 它不是「逐动作降速倍率」，而是**疲惫时动作速度的下限钳制**：启用值 1.0 表示「该动作不允许被全局 `_motRate` 压到低于原速」，用于保护个别动作；−1.0 = 该动作不启用此保护。对照 `_angerMotSpeedUpperValue`（怒时上限，em003 有 1.1）说明「上限可 >1（加速）」，两者是 Clamp 语义而非 Scale 语义。
⇒ Rise 疲惫降速**主要由按怪的 `_motRate` 承担**，逐动作层只做例外保护。引擎是否把两者相乘、下限是否真的生效，无代码级证据。

### 1.3 效果落在 `dS`，不产生输出窗口

`_motRate` 拉伸动作播放（判定帧、后摇同比变慢），但两招之间空档 `dE` 不变；P85「Rise 无间隔倍率字段」定案维持。这也解释了为什么把它搬进 GU 也做不出用户定义的「输出窗口」。

---

## 2 · 问②：两招之间的衔接链

### 2.1 通用链（疲惫 / 非疲惫同构）

| 步 | 层 | 字段 / 载体 | 实证强度 |
|---|---|---|---|
| 1 | **L3 门控** | `ThinkCondition._IsActionEnd`：12 个 `attack_stance_*` Hub 共 44 个 TC 中 **12 True / 32 False，每文件恰 1 True**；主例程与 15 池内 TC **全 False** | 实证（P32 §2 / P77 / P80_object_ref） |
| 2 | **L5 条件检查** | `ConditionInfo._CheckPrevTableInfoList` 每条件恰 1 项（防复读）；`EnemyThinkTimerData._Timer` 0~300 s、17 档共 44 个值（0/3/5/10/15/20/30/40/45/50/60/70/90/120/150/180/300，em001 口径）；`EnemyThinkCounterData._UniqueId` 1..6 | 标量实证，因果推断 |
| 3 | **L6 轮盘** | `_TransitionRate` 百分制，**555/555 池率和恒 100** ⇒ 每次抽选必定命中一个动作，**没有「空过 / 等待」选项** | 实证（555 池全量） |
| 4 | **L7 执行** | `ActionTableData(_Category, _TableNo)` → `action/emNNN_act_NNN.user` 或 `combo/emNNN_combo_NNN.user`；`ActionInfo` 固定 8 字段，**无 combo / link / next / CD**，`explicit_cooldown_field_found = false` | 部分（映射链断） |
| 5 | 连段内部 | `combo/` 是预编排动作序列，段内按资源推进、不回抽选层（mhvuze modding wiki + `_Category` 与 combo 路径强相关） | 高置信推断，非实证 |

**关键定性**：门控是「动作没结束不重抽」，不是「动作结束后等 N 秒」。`_Timer` 是**思考 / 重复抑制计时器**（P32:120 明确「不是疲惫时长，勿混用」），`_CheckPrevTableInfoList` 决定「不能连着抽同一张表」，二者都不构成招间强制间隔。**静态全库 `explicit_cooldown_field_found = false`**。

### 2.2 疲惫时变的是什么

- **L4 换池**：`{anger|normal|tired}range1..5`，疲惫走 `tiredRange1..5`。555 池全量：每格 37 池，`mean_candidates` 3.35~3.57、最大权重 52.0~72.0（`tired_range5` 72）、平均熵 **1.2984**（怒 1.6740 / 常 1.6669）。em001 原始顺序：tired 五档**恒含表 1、该项权重恒 10**，表号并集 `{1,15,20,51}`（P32:85-90）。
  - **口径澄清**：P32「首项恒 10」指池内第一项（表 1）；555 形状「首项 55~72%」指按 `_TransitionRate` **降序**归一后的最大权重项。两者不矛盾，勿混用。
- **连段变少**：em001 15 池 `_Category` 分布 `{0:64, 1:36}`，`tiredrange1` 的 cat1 = 0 ⇒ combo 路径 0，其余 14 池 cat1 > 0 均有 combo 路径（P36:120-121）。属单怪实证，不外推全库。
- **没有「疲惫专属衔接层」**：12 Hub / 15 池 / 107 个 RSZ JSON 搜 `tired / drool / rest / fatigue` **0 命中**（除文件名）；无「疲惫时把 Think 计时器调长」的字段或绑定证据（P86 §1）。

### 2.3 玩家感觉「两招之间变久」的三处真实来源（都不在 L3–L7）

1. **`_motRate` 拉长 `dS`**（§1.1，静态可定量）。
2. **L1 引擎状态层**：`_IsTired` 持续布尔 + `_AddTiredTime` 动态累加 + `EnemyStaminaManager`，插入流口水 / 发呆 / 滑倒；动画资源层 442 条清单 437 条 0 覆盖，工程内无法定量。
3. **脱战换区进食**（P87）：`_mapNikuEatSec` 20 s(74) / 10 s(4)、`_SetMeatRecovStartPoint` 20/30 → `EndPoint` 80/70、**`_InCombatMapMeatEatFlag = False`(78/78)** ⇒ 战斗中不吃、换区才吃。

⇒ **准确说法**：Rise 疲惫 = 换一批更单一的候选 + 状态持续 + 动作变慢 + 引擎层插入待机/进食；**不是「抽选器变慢」或「决策层插入间隔」**。

### 2.4 仍不能定案

- 「表 1」是否为待机 / 非攻击表：`TableNo → _actionNo → 招式名` 文本源硬断点，语义未知。
- `combo/` 资源未解包：段数 / 是否线性 / 条件分支 / 帧数无证据。
- `_IsActionEnd`「仅在动作结束帧求值」、Timer / Counter 与具体 `ConditionInfo` 的绑定因果：**推断级**（P32:202、P36 §3.1 已自述降级）。
- 全部 Rise 侧结论均为**静态资产复核，无 Rise 实机或反汇编**（P32:201）。

---

## 3 · 与本项目 v2 的关系

- v2 的 W1/W2/W4 只复刻 **L4 池选择 + L6 权重形状**；速度层 `_motRate` 与衔接层 `_IsActionEnd`(W3) 均未实现，W3 经 P70/P79 三次实机证明 GU 原生无 IN_ACTION 窗口已关闭。
- **P84 / P85 结论不受影响**：那两条讲的是 **GU dttune** 只有怒时专用倍率、无疲惫专属速度字段；本轮讲的是 **Rise** 侧「全局倍率降速 + 逐动作下限保护」两层，两者是不同游戏。GU 侧执行层不可达的判定维持。
- **P87 的 FNV0 让位方案不受影响**：它对应「引擎层原生待机 / 进食」，既不是速度也不是间隔，是 §2.3 三处来源中的第 2/3 项。
- v2 成品行为、P79 验收、P80/P83/P85/P86/P87 达成度口径**全部不变**。

---

## 4 · 边界与产物

本轮纯只读：重解析 3 个 `action_param_data` 到 `%TEMP%/p88_actionparam/`（新增 3 个临时 JSON，未写入工程目录），复核 78 个 `stamina_data` 与 555 池形状 JSON；**未启动游戏、未编译 NRO、未改 `plug/` 源码 / 成品与回退 NRO / mods / `load_order` / 音频线，GitHub 远端零操作**。Rise 侧无实机、无反汇编。

数据源：`out/rsz_bulk_json_v2/*stamina_data*.json`、`out/rise_15pool_shapes_555.json`、`out/rise_ai_rules.json`、`out/P32/P36/P72/P80/P84/P85/P86/P87_*.md`、`refs/rise_unpack/.../em00{1,2,3}_action_param_data.user.2`。
