# P32 · Rise 侧完整 AI 链系统复核（2026-11-12 20:35）

用户去跑 v49 实机，要求「先检查 Rise 侧的完整 AI 链，文件太多可以分多个子 agent」。
本轮用 **4 路只读子代理并行**（A 池与权重 / B FSM 与门控 / C 动作与耐力 / D 资产与差距），
再由主代理做**独立交叉核验**（现算熵、表号、路径口径、RSZ 字段字节计数）。

**本轮全程只读**：未改动插件、部署、bat 脚本、游戏资源、load_order；未运行游戏。

---

## 0 · 先看结论：5 条修正既有定案的发现

| # | 发现 | 性质 | 影响 |
|---|---|---|---|
| **M1** | NOTES §504「`tired·档5 [10,20,70]→[1,20,51]`」的箭头**不能逐项配对**：`[1,20,51]` 是 `action_table_nos` 的**升序集合**，与 `rates` 位置 0/15 池吻合。真实配对 `10→表1、20→表51、70→表20` | 修正误读 | 「疲惫池偏向低威胁表」缺 TableNo→威胁度映射支撑；表 51 在 normal 档3/4/5 也以 50/45/35 高权重出现 |
| **M2** | 15 池香农熵：**anger 1.6740 / normal 1.6669 / tired 1.2984**。怒与常仅差 **+0.43%**，疲惫比非疲惫低 **22%** | 修正 P31 叙事 | Rise 实际只区分「疲惫 vs 非疲惫」。P31 §1「怒池熵 1.67 更多样」不成立，**v49 的怒 `depth=3` 缺 Rise 数值依据** |
| **M3** | Rise RSZ 中实证存在 `_tiredSec`(1)、`_IsTired`(2)、`_AddTiredTime`(60)；而 `Stamina_low_Start` / `tired_start` 在 Rise 侧 **0 命中**（是 GU 的 EMC/rodata 状态名） | 修正对标前提 | GU「疲惫是瞬时事件、无持续状态字」是 **GU 特有**，不是 Rise 对标；P20「Rise 不是计时器」存疑 |
| **M4** | NOTES §932「GU 无对应结构，不能照搬」的**推理前提已被 NOTES:1968/2278 推翻**：GU 有 EMC `0x82f80` 抽选层，`op02` = `rand%100` 与 `_TransitionRate` 同构 | 降级 + 改写 | 字面禁令（不照搬 15 张表）仍成立；建议改述为「有同构抽选骨架，无 (状态×距离) 索引的独立池表 ⇒ 照搬表不可行、结构性近似可行」 |
| **M5** | 「12 处境 Hub」= em001/00 的 12 个 `attack_stance_*` **处境变体**，非全局 12 个独立 FSM；且 442 条路径清单与 107 个解包文件 **basename 重叠 0** | 收窄口径 | Hub 是目录级概念（em131 另有 flow/think/hub/damage/stand）；`*_main.user` 主例程 0 个 ⇒ **链在 L2→L4 断开** |

> 术语警示：GU 侧 `hub=15`（hook 掩码）与 Rise 的 `attack_stance_*` Hub **同名异物**，不可互证。
> 另：`EnemyAIFSM` 类名在 RSZ 模板中 **0 命中**，实际载体是 `EnemyThinkData` / `ThinkState` / `ThinkCondition` + `snow.enemy.aifsm.*` 命名空间。

---

## 1 · 资产实况与口径（交叉核验数值）

| 资产 | 数量 | 说明 |
|---|---|---|
| `refs/rise_enemy_ai_paths.txt` | **442** 条唯一路径 | 主类 `user_data` 325 / `shell` 68 / `map_data` 26 / `act_tbl` 12 / `ai_fsm` 11；涉及 53 个 emNNN，em131 占 137 |
| `refs/rise_unpack/` | **107** 个 `.user.2` | `common/act_tbl_user_data/routine` **89**、`00/ai_fsm_user_data/hub` **12**、`common/user_data` **6**；em001 57 / em002 34 / em003 16 |
| `out/rsz_json/` | **107** 个 JSON | 与解包 **一一对应**（交集 107、双差集 0）；`files_partial=60` |
| 与 442 清单的关系 | **basename 重叠 = 0** | 清单是**待抽取索引**（集中 em131），解包是**另一轮针对 15 池的定向抽取**。二者不是「清单→解包」关系 |
| routine 文件口径 | 全库 **89** / em001 **43**（22 子目录） | A 的 43 与 D 的 89 不矛盾：前者只数 em001，后者数三怪全库 |

**解析质量**：`files_partial=60/107`，`ThinkState._ConditionList` 固定失步（垃圾值 `67174401` / `2206645383`）。
⇒ `_TransitionRate` / `_TableNo` / `_subStaminaPoint` 等**标量可信**；`_ConditionList` / `_ActionList` / `_TransitionActTbl` 等**对象引用不可作定论**。这解释了为何「15 池矩阵」可定案而「Hub→池因果链」不能。

---

## 2 · Rise 完整 AI 链（L0–L7）

| 层 | 环节 | 数据载体 / 字段 | 证据强度 |
|---|---|---|---|
| **L0** | 装配 | `EnemyUserDataParam`（58 字段）：`_useThinkData` / `_actTblGroupData` / `_thinkUseFreeData` / `_targetRangeData` / `_angerData` / `_staminaData` | 类型定义 |
| **L1** | FSM 状态 | root `snow.enemy.EnemyThinkData._StateList → List<ThinkState>`；`ThinkState` = `_ID:U8` / `_ActionList` / `_ConditionList` / `_ReferenceThinkData` / `_TreeNodeID` | 类型 + 实例 |
| **L2** | 处境 Hub 分流 | 12 个 `attack_stance_*`，差异 = `ThinkCondition._NextStateID`(12 值) + `_ActionList` hash + userdata 绑定：`down_*`→`act_600`、`up_*`→`combo_033/034`、`flash`→`mode030`、`same_main`→`mode001/003`、`out_main_zone`→`main_out1_main` | 实证（UTF-16 userdata 路径） |
| **L3** | 门控 | `ThinkCondition`（typeId `8b6e48e0`）= `_Condition` / `_IsUnderLayerEnd` / **`_IsActionEnd`** / `_NextStateID:U8`。12 Hub 共 44 个 TC：**12 True / 32 False，每文件恰 1 True**；15 池内 TC **全 False** | 实证 |
| **L4** | 池选择 | **状态 × 距离档共同索引** → `main_out1_{anger|normal|tired}range{1..5}check.user.2`（3×5=15） | 实证 |
| **L5** | 条件检查 | `EnemyRoutineLotSet._ConditionInfoList → ConditionInfo`：`_TransitionActTbl:Object→ActionTableData`、`_TransitionRate:S32`、**`_CheckPrevTableInfoList:List<ActionTableData>`（50/50 长度恰 1）**；计时器 `_Timer:F32` 0~300s、计数器 `_UniqueId` 1..6 | 实证（计时器因果存疑） |
| **L6** | 加权抽选 | 按 `_TransitionRate` 百分制轮盘赌，15/15 组**和恒 100**；`EnemyRoutineLotCase._TransitionValue` 为池内 0..n−1 索引 | 实证 |
| **L7** | 执行 | 命中项 → `ActionTableData(_Category:S32, _TableNo:U16)` → `action/em001_act_NNN.user` / `combo/em001_combo_NNN.user` → `EnemyActionParamData.ActionInfo(_actionNo:U16, _subStaminaPoint:S32, …)` | 部分（见 §6 断点） |

**`_IsActionEnd` 生效点 = L3 第 ⑧ 步**：它决定「何时允许离开当前动作状态、进入下一次抽选」，
**不在** L5 否决、不在 L6 抽选、不在 L7 执行。「连段内部不重新抽选」的字段证据有 5 条
（TC 唯一宿主、Hub 层 12 True、池内全 False、否决字段挂 ConditionInfo 而非 TC 等），
但「仅在动作结束帧求值」仍是**字段语义推断**，无反汇编佐证。

**关键链断点**：Hub（L2）→ 15 池（L4）之间的 `*_main.user` 主例程本次 **0 个**被抽取
（`main_out1_main.user` 仅被 `out_main_zone` 引用 1 次）。全库 UTF-16 路径扫描 `rangecheck`=0、
`attack_stance`=0 ⇒ 目前**没有字段级证据**把 Hub 与 15 池直接连起来。

---

## 3 · 15 池权重 / 表号 / 熵（完整矩阵）

`rates` 按 ConditionInfo 顺序；`真实表号` 由 `_TransitionActTbl` ref 还原，与 `action_table_nos`（升序集合）**位置不对应**。

| state | 档 | `_TransitionRate` | n | H (bit) | 真实按权重顺序 `_TableNo` |
|---|---|---|---|---|---|
| anger | 1 | [30, 40, 30] | 3 | 1.5710 | [80, 14, 19] |
| anger | 2 | [15, 25, 25, 35] | 4 | 1.9406 | [61, 80, 14, 19] |
| anger | 3 | [20, 20, 25, 35] | 4 | 1.9589 | [61, 80, 14, 19] |
| anger | 4 | [25, 15, 50, 10] | 4 | 1.7427 | [62, 80, 19, 20] |
| anger | 5 | [10, 70, 20] | 3 | 1.1568 | [80, 19, 20] |
| normal | 1 | [45, 30, 25] | 3 | 1.5395 | [79, 13, 19] |
| normal | 2 | [30, 25, 45] | 3 | 1.5395 | [79, 13, 19] |
| normal | 3 | [25, 25, 50] | 3 | 1.5000 | [79, 51, 19] |
| normal | 4 | [20, 25, 45, 10] | 4 | 1.8150 | [79, 51, 19, 20] |
| normal | 5 | [15, 25, 35, 25] | 4 | 1.9406 | [79, 51, 19, 20] |
| tired | 1 | [10, 65, 25] | 3 | 1.2362 | [1, 51, 15] |
| tired | 2 | [10, 45, 45] | 3 | 1.3690 | [1, 51, 20] |
| tired | 3 | [10, 45, 45] | 3 | 1.3690 | [1, 51, 20] |
| tired | 4 | [10, 50, 40] | 3 | 1.3610 | [1, 51, 20] |
| tired | 5 | [10, 20, 70] | 3 | 1.1568 | **[1, 51, 20]** |

| 状态 | 平均 n | 平均 H | 平均 H/Hmax | 平均最大权重 | 表号并集 |
|---|---|---|---|---|---|
| anger | 3.60 | **1.6740** | 0.9084 | 46.0 | {14,19,20,61,62,80} |
| normal | 3.40 | **1.6669** | 0.9534 | 44.0 | {13,19,20,51,79} |
| tired | 3.00 | **1.2984** | 0.8192 | 55.0 | {1,15,20,51} |

**判定**：Rise 的低熵只出现在**疲惫态**；怒态与常态在熵维度几乎不可区分，
差异体现在**招式数**（3.6 vs 3.4）与**表号集合**（怒独有 14/61/62/80，常独有 13/79）。
tired 池 5 档首项权重恒 10 且恒含表 1，是唯一稳定的结构性特征。

**extra 网格**：`routine/` 全库 89 个文件中，`main_out1` 只占 15；其余 74 个是
`main_out2/301/302` 与 22 个 `modeNNN` 子目录（em001）下的**稀疏 state×range 覆写**，
仍沿用 `{anger|normal|tired}range{1..5}` 命名体系，但每个 group 只覆盖部分格。
例如 `mode001_normalrange1check` 有 7 项权重 `[10,10,20,10,25,15,10]`、表号 60/66/67/19/7/9/13。
⇒ 15 池是**主网格**，不是全部池；「mode」语义（战斗模式/处境）目前仅为命名推断。

---

## 4 · 耐力 / 疲惫链：Rise 与 GU 的关键不等价

| 环节 | Rise | GU（P29/P30 实证） | 判定 |
|---|---|---|---|
| 每动作扣点 | `ActionInfo._subStaminaPoint:S32`；em001 46/296、em002 98/393、em003 29/167 非零，值 5~100 | `act+0x4D8:s16 amount` → `0xA30E4 add` 累加 | **对应** |
| 当前量 | `EnemyActionPacket._Stamina:U16`（同步当前值） | `act+0x5D82` counter + `act+0x5D84` thr，且 ex 会衰减 | 部分对应 |
| 阈值递推 | 本地未见对应字段 | `0xA3198 grow: thr=min(initial+increase*proc,max)`，实机 142→190→237→285 | Rise 侧证据不足 |
| 触发 | `EnemyStaminaParam.State` 枚举 + **`_IsTired:Bool`** | `counter>=thr ⇒ return 1` **瞬时事件**，`flg` 不占位 | **不等价** |
| 时长 | **`_tiredSec` / `_hyakuryuTiredSec` / `_AddTiredTime`** | `durF` 对减气无效；疲惫不占状态位 | **不等价** |
| 恢复 | `_SetMeatRecovStartPoint/EndPoint`、`SetMeatInfo._StaminaRate/_Distance` | 进食/耐力回升，非计时器 | 部分对应（都指向进食） |
| 状态名 | RSZ **0 命中** `Stamina_low_Start` / `tired_start` / `tired_Loop` | GU EMC/rodata 的状态名（`0xf8d384`、`0x10a1814`） | **不同引擎层** |
| 池切换 | **状态 + 距离档共同索引** 15 池 | 无表结构；v49 只按状态调 veto 严格度 | **不等价** |

⇒ **「疲惫是瞬时事件、无持续状态字」是 GU 的实测结论，不能反向当作 Rise 机制**。
`Stamina_low_Start/tired_start` 是 GU 侧名称，P20/P29 的「同构」属推断性类比。
另：`EnemyThinkTimerData._Timer`(0~300s) 是**思考/重复抑制计时器**，不是疲惫时长，勿混用。

`_subStaminaPoint` 复核（本地现算 em001）：296 个 `ActionInfo`，直方图
`0×250 / 15×15 / 10×13 / 12×8 / 7×5 / 20×3 / 100×2`，与 P20 逐值一致。

---

## 5 · 对 v49 的直接影响（不改本轮部署）

1. **怒 `depth=3` 的 Rise 依据不成立**。M2 显示怒/常熵无差异 ⇒ 若保留 depth=3，
   应改称「自定增强多样性」，不能说「对标怒池高熵」。更贴 Rise 数据的结构是
   **两档**：非疲惫（怒/常同 depth=2）vs 疲惫（depth=1 + keep）。**待用户拍板，本轮不动**。
2. **疲惫窗口不是 Rise 对标**。M3 表明 Rise 有 `_IsTired` / `_tiredSec`；v49 用
   EXH ret=1 + 该怪动作数是 **GU 侧因「无状态字」而必需的近似**，P31 已如此表述，本轮加固。
3. **§504 的「疲惫偏低威胁表」叙事需降级**。真实配对 70% 落在表 20，表 51 在常态也高权重。
   这不改 v49 实现（v49 不读表号），但影响后续「按档调权重」的设计动机。
4. **§932 建议改写**（M4），避免后续继续基于「GU 无抽选器」这一已作废前提做判断：
   > GU **有**与 `_TransitionRate` 同构的 EMC 加权抽选骨架（`op02` / `rand%100`，全怪共用），
   > 但**没有**按 (状态 × 距离) 索引的 15 张独立池表（怒/常复用同一批 op02 块）；
   > 因此「照搬数据表不可行」，「结构性近似可行」——v49 已落地 3 状态维度，5 距离档仍缺。
5. **5 距离档仍是唯一硬的未实现维度**，且 Rise 侧确认为「状态 + 距离共同索引」（C 定案），
   v49 只覆盖前者。距离阈值数值在 Rise 侧也**未解出**（`em131_00_range_data.user.2` 未抽取），
   文件名 `range1..5` 是唯一线索。

---

## 6 · 差距矩阵（精简）

| Rise 环节 | GU 现状 | v49 | 证据 | GU 结构性可实现 |
|---|---|---|---|---|
| FSM 顶层 `think/flow/hub` | EMC `0x82f80` + `em+0x2588` 恒 21 段（段语义 [U]） | ✗ | 中 | 可（按段号门控） |
| 12 处境 Hub | `0x75224` 选 kind 0/1/2 → `0x76154`，17 调用者 | ✗（仅观测 hub=15） | 高 | 可（调用者层按 kind 分流） |
| `_IsActionEnd` 门控 | v17 实机 action-end 后 1 帧提交；`act+0x1A0` | ✗ | 高 | 可（收敛点门控，不写字段） |
| 3 状态 | 怒 `st==1`、疲 EXH/proc 事件、其余 | ✅ **唯一新增** | 怒高 / 疲中高 | 可（纯只读） |
| 5 距离档 | 静态阈值 case×100，运行时档位未定位 | ✗ **明确未实现** | 低 | 可但需前置（matcher 层） |
| 加权池 `_TransitionRate` | `op02/mode==1` = `rand%100` 同构，但怒/常复用同批块 | ⚠️ 间接改熵 | 高 | 可（归一化重抽），不可照搬表 |
| prev 表检查 | `+0x73E0` 自带 prev（197/198 吻合） | ✅（v35 起，v49 扩 depth） | 高 | 可 |
| 计时器/计数器 | 自创全局 CD 已证伪 | ✗ 有意不覆盖 | Rise 侧存疑 | 暂不建议 |
| 动作表 / `_subStaminaPoint` | cmdtbl 21 段、102 表读全量 | ✗ 不写表 | 高 | 次要路线（离线 arc） |
| 耐力疲惫 | `0xA30E4` 链字节级 + 实机闭环 | ✅ 三态输入源 | 高 | 可（纯只读） |

---

## 7 · 链断点与未抽取资产（按价值排序）

1. **`*_main.user` 主例程 0 个** ⇒ Hub→15 池因果链无字段证据（最高价值，定向抽取即可补）。
2. `em131_00_range_data.user.2`（距离阈值）、`emNNN_00_stamina_data.user.2`（`_tiredSec` 实例数值）
   仅存在于路径清单，未解包 ⇒ Rise 侧「5 档阈值」与「疲惫时长」都还无数值。
3. `TableNo → _actionNo → 招式名` 映射链断：107 个 JSON 中无 `actiontune / motion / message` 类文件；
   `_TableNo`(U16) 与 `_actionNo`(U16) 是不同编号空间，中间映射表缺失。
4. 442 条清单中 **437 条 0 覆盖**：`user_data` 标准 314、`shell` 68、`map_data` 26、
   `common/user_data` 11、`ai_fsm/think` 5、`ai_fsm/flow` 1、`act_tbl/action+combo+damage` 12。
5. `files_partial=60/107` 的解析失步 ⇒ 深层条件链、`_ConditionList`、对象引用不可定论。
6. `modeNNN` 语义、Timer/Counter 与具体 ConditionInfo 的绑定、Hub `_NextStateID` 大数值含义，
   均只有类型/命名级证据。

---

## 8 · v49 之后的优先级（结合本轮修正）

**P0（零前置，用户正在做）**：v49 实机三态判据闭环 + **换第 2 只怪复跑**验跨怪一致性。
理由：v49 目前只有合成日志 `PASS=20/0`，`depth=3 / 50% / 40 动作` 全是自定参数；
没有这份基线，后续任何结构性改动都无可归因对照。

**P0'（零成本，文档）**：按 M1/M2/M3/M4 修正 NOTES §504、§932 与 P31 §1 的对标叙事，
避免后续基于错误前提继续投入。本轮已在报告中给出改写文本。

**P1（补 15 池唯一硬缺口）**：在 `0x8E144` matcher 层做**纯只读**探针，记录每个 op02 块的
`s16` / 阈值 case 序列 / 命中 case 索引 / `st3`，跨 2 只怪建立运行时档位输入，
再在 v49 的 depth 映射上叠加「按档调严格度」（仍是结构近似，不照搬表、不写内存）。
前置：P0 通过 + 复核 `0x8E144` 运行时首字。

**P2（对齐 12 处境 Hub，NOTES §1867 的 P1 建议）**：在 `0x75224` 干净调用者层
（17 个中 11 个可 hook）只读补齐 `kind` 分布、`act+0x1A1` 语义、`st=2` 样本，
再做「异常状态不进攻击抽选」分流。纪律：`0x76154` 被 IPS32 切成解释器函数**不可直接 hook**；
不得事后写 `+0x73E1`（v13-b/c 已证伪）。前置：需先建立跨怪通用的「攻击类/非攻击类」语义映射。

---

## 9 · 边界

- 本轮 4 路结论均为**静态资产复核**，不含 Rise 实机运行或反汇编；
  `_IsActionEnd` 求值时语义、Timer/Counter 因果、mode 语义、`range`=距离档命名，仍是推断。
- 15 池矩阵 / 熵 / 标量字段可信；所有 `Object` / `List<Struct>` 引用与深层条件链不可作定论。
- 「疲惫偏低威胁表」「Rise 疲惫不是计时器」「状态名同构」三条既有说法均已被本轮降级或存疑。
- **本轮未改任何插件 / 部署 / 脚本 / 游戏资源 / load_order**；v49 保持 `ec4fcd05…` 待实机。
