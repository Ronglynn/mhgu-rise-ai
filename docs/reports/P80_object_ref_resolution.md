# P80 · Rise `.user.2` 对象引用解析修复与 Hub→15 池因果链复核

**结论先行**：对象引用失步已被**完全修复**（12/12 文件、1038 个引用 100% 合法、consumed 精确等于 data 段长度）。但**修复后仍无法由对象引用重建 Hub→15 池因果链** —— 卡点是结构性的：RSZ 引用是文件内 instance index、Hub 文件内不含池轮盘、Hub 唯一出口指向未抽取的外部分件、且标量侧无共享 TableNo。因此 **P78「W4 12 Hub 1:1 不可做」定案不推翻，反而由「标量对拍」升级为「标量 + 对象引用 + 结构归属」三重实证**。

本轮全部为**静态资产复核**，零实机、零部署、零插件源码改动。

---

## 0 · 任务范围与约束核对

| 项 | 状态 |
|---|---|
| 只读 + 新增文件 | ✅ 未改 `plug/`、未改 mods/游戏目录、未改 `tools/rsz_parse.py`、未改 `out/rsz_main_json/`（12 份时间戳仍 18:34） |
| 新工具 | ✅ `tools/rsz_parse_v2.py`（不改既有 `rsz_parse.py` 行为） |
| 新产物目录 | ✅ `out/rsz_main_json_v2/`（12 JSON + `_summary.json`） |
| 主样本 | `refs/_main_extract/` 的 12 个 em131 `.user.2`（P77 抽取） |
| 补充查证（只读） | `refs/rise_unpack/` 的 107 个 `.user.2`（P78 标量对拍所用的 107 JSON 的原始二进制），在**内存中**用 v2 重解析，不落盘新 JSON |

---

## 1 · 失步起点定位（任务 1）

### 1.1 现象回顾（P77 §1 / P78 §2）

v1 解析器 `tools/rsz_parse.py` 对 `Object`/`String`/`Resource`/`UserData` 字段一律返回 `"ref:0x%08X"`；样本里出现 `ThinkState._ActionList = ref:0x4BCCF5F2` 之类垃圾值，且 `bytesConsumed` 与文件长对不上。

### 1.2 真实 RSZ 布局（二进制实证）

以 `em131_00_main.user.2`（940 B）为例，dump 结果：

```
USER 头 @0..39   : magic USR\0 | resourceCount=0 | userdataCount=2 | InfoCount=0
                   u64@16=48  u64@24=48  u64@32=330 (→ RSZ 段绝对偏移)
USER @48         : root typeId = 0x1839AAB4 (snow.enemy.EnemyThinkData)
RSZ 段 @330      : magic RSZ\0 | version=16 | objectCount=1 | instanceCount=12
                   | userdataCount=2 | reserved=0
RSZ u64 @pos+24  : instanceOffset=52 (→abs 382) | dataOffset=438 (→abs 768)
                   | userdataOffset=150 (→abs 480)   ← 注意：在 data 之前
RSZ @378         : objectTable[1] = 11
RSZ @382..478    : instanceInfo[12] × {u32 typeId, u32 crc}
RSZ @480..       : userdata info 表 + UTF-16 外部分件路径
RSZ @768..940    : 实例 data 段（172 B）
```

**关键纠正**：RSZ header 第 3 个 u64（`userdataOffset`）指向的**不是 data 段之后的 userdata 数据区，而是 data 段之前的 userdata info 表**。v1 读出了它但从未使用，也没有据此识别 userdata 实例。

userdata info 表条目结构（实测 16 B/条）：

| 偏移 | 字段 | main 条目 0 | main 条目 1 | combat_main 条目 0 |
|---|---|---|---|---|
| +0 | `u32 instanceId` | 7 | 9 | 11 |
| +4 | `u32 typeId` | `1839aab4` | `1839aab4` | `1839aab4` |
| +8 | `u32 pathOffset`（相对 RSZ 段起点） | 182→abs 512 | 318→abs 648 | 182→abs 384 |
| +12 | `u32 reserved` | 0 | 0 | 0 |

`pathOffset` 指向 UTF-16 路径，实测解出：
- main idx7 → `enemy/em131/00/ai_fsm_user_data/think/em131_00_think_interrupt.user`
- main idx9 → `.../think/em131_00_mode.user`
- combat_main idx11 → `.../flow/em131_00_ActionSpecRoutine.user`

### 1.3 失步根因（定案）

**userdata 实例的数据存放在外部分件里，在主 data 流中占 0 字节。** v1 却对它们也按 `fields` 内联解析（`EnemyThinkData._StateList` 是 1 个数组：4 B count + N×4 B 元素，典型吃掉 8 B），导致其后所有实例整体错位。

佐证（完全自洽）：

1. **失步恰好从 userdata 实例的下一个实例开始**：
   - main：userdata = idx7/9，v1 垃圾 ref 从 **idx8** 开始
   - combat_main：userdata = idx11，v1 垃圾 ref 从 **idx12** 开始
   - combo_007：userdataCount=4，v1 有 7 个非法 ref
2. **12 个文件里只有 3 个含 userdata，也只有这 3 个在 v1 下失步**（见 §3 表），其余 9 个 `userdataCount=0` 的文件 v1 本来就解析正确。
3. **垃圾值不是随机噪声，而是被错位的真实 U32 字段**：`0x4BCCF5F2`=1271723506、`0x4FCD4D95`=1338854805、`0x277CF536`=662500662 在修复后分别归位为 main idx8 / idx10 / combat idx12 的 **`_TreeNodeID`**（行为树节点哈希，合法 U32）。v1 把它们误读成了 `_ActionList` 的 Object 数组元素。
4. `bytesConsumed` 对 3 个失步文件分别为 224 / 224 / 640，而真实 data 段长 172 / 192 / 560 —— 各溢出 52 / 32 / 80 B，正是多解析 userdata 实例字段所致。P77「bytesConsumed 常小于 fileSize」是拿 `off-data` 与**整文件长**比的误导性对比；正确判据是 `off-data` 与 **data 段长**比，修好后二者精确相等。

> 结论：**二进制是干净的**，失步是解析器缺陷，不是 patch 覆盖、不是模板缺字段、不是格式异常。P78 §7「对象引用解析需干净二进制」这条前提作废。

---

## 2 · 新工具 `tools/rsz_parse_v2.py`（任务 2）

相对 v1 的四点改进：

1. **识别 userdata 实例**：读 `userdataOffset` 指向的 16 B/条 info 表，解出 `instanceId` 集合与 UTF-16 外部分件路径；解析 data 流时**跳过这些实例（占 0 字节）**，并保留 `isUserdata`/`userdataPath` 标记。
2. **Object/UserData 引用按 instance index 解析**：输出结构化 `{ref, targetClass, valid}`，校验 `0 ≤ ref ≤ instanceCount`（`ref=0` 为 null）。数组元素同样处理。
3. **判据驱动的对齐搜索**：默认策略 `(skip=0, alignUserdata=False)`；若不满足判据，在 `skip ∈ {0,1,2,4,8,16} × align ∈ {False,True}` 共 12 组候选中搜索，记录每个候选的评分与选择理由（写进每份 JSON 的 `diagnostics.alignmentSearch`）。
4. **完整诊断**：`objectRefs{total,valid,invalid}`、`arrayCounts{total,plausible,implausible}`、`bytesConsumed/dataRegionLen/tail`、`fieldsComplete`、`parseOK`、`alignmentSearch`。

判据（评分函数，按优先级）：① 全部引用落在 `[0, instanceCount]`；② 数组 count ≤ 4096 且 `count×size ≤ 剩余字节`；③ 除 index 0 外所有实例类可解析；④ `|tail|` 最小；⑤ `skip` 最小、不对齐优先。

### 2.1 对齐搜索实证（离线阶段 `out/_probe_strategy.py`）

| 策略 | main（ic=12, data=172 B） | combat_main（ic=14, data=192 B） |
|---|---|---|
| **skip=0, align=F** | consumed **172/172**, tail=0, bad_ref **0/11**, bad_cnt **0/7** ✅ | consumed **192/192**, tail=0, bad_ref **0/14**, bad_cnt **0/7** ✅ |
| skip=0, align=T | 同上（main 尾部恰可吸收） | consumed 228/192, tail=−36, bad_ref **8/22** ❌ |
| skip=1, align=F | 通过（尾部 padding 吸收 1 B） | consumed 228/192, tail=−36, bad_ref **8/22** ❌ |
| skip=4 / 8 / 16 | tail=−12/−44/−52，出现非法 ref 与异常 count ❌ | 全部 ❌ |

**只有 `skip=0, align=False` 同时让 12/12 文件满足判据且 `tail=0`**。combat_main 是决定性反例：`skip=1` 时 tail=−36、8 个引用越界，排除「userdata 占 1 字节」；main 因尾部对齐恰好能吸收 1 B 而出现 `skip=0/1` 双解，按「skip 最小」取 0。

正式 v2 运行时，12 个文件**默认策略即 `parseOK=True`，均未触发自动搜索**（`alignmentSearch.triggered=false`）；搜索能力保留用于对未来含缺类文件的容错。

---

## 3 · 12 文件重解析统计（任务 3）

输出 `out/rsz_main_json_v2/*.json` + `_summary.json`（556 条关键表记录）。

### 3.1 v1 → v2 对比

| 文件 | ic | ud | v1 refs | v1 非法 | v1 consumed / data | v2 refs | v2 非法 | v2 consumed / data | tail | OK |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| em131_00_combat_main | 14 | 1 | 15 | **1** | 224 / 192 | 14 | 0 | 192 / 192 | 0 | YES |
| em131_00_main | 12 | 2 | 16 | **2** | 224 / 172 | 11 | 0 | 172 / 172 | 0 | YES |
| em131_00_range_data | 66 | 0 | 64 | 0 | 1112 / 1112 | 64 | 0 | 1112 / 1112 | 0 | YES |
| em131_00_stamina_data | 11 | 0 | 9 | 0 | 196 / 196 | 9 | 0 | 196 / 196 | 0 | YES |
| em131_act_004 | 29 | 0 | 32 | 0 | 452 / 452 | 32 | 0 | 452 / 452 | 0 | YES |
| em131_act_005 | 116 | 0 | 130 | 0 | 1936 / 1936 | 130 | 0 | 1936 / 1936 | 0 | YES |
| em131_combo_001 | 39 | 0 | 44 | 0 | 652 / 652 | 44 | 0 | 652 / 652 | 0 | YES |
| em131_combo_003 | 104 | 0 | 116 | 0 | 1728 / 1728 | 116 | 0 | 1728 / 1728 | 0 | YES |
| em131_combo_005 | 450 | 0 | 512 | 0 | 7488 / 7488 | 512 | 0 | 7488 / 7488 | 0 | YES |
| em131_combo_006 | 29 | 0 | 32 | 0 | 452 / 452 | 32 | 0 | 452 / 452 | 0 | YES |
| em131_combo_007 | 35 | 4 | 46 | **7** | 640 / 560 | 36 | 0 | 560 / 560 | 0 | YES |
| em131_combo_008 | 34 | 0 | 38 | 0 | 552 / 552 | 38 | 0 | 552 / 552 | 0 | YES |
| **合计** | | | **1054** | **10** | | **1038** | **0** | | | **12/12** |

- **解析成功率 12/12**（`parseOK`），其中含 450 实例 / 7488 B 的 `combo_005` 也精确吻合。
- **Object/UserData 引用合法率 1038/1038 = 100%**（v1 为 1044/1054，3 个文件共 10 个非法）。
- **数组 count 合理率 293/293 = 100%**。
- **`bytesConsumed == dataRegionLen` 12/12，tail = 0**：解析结束后剩余字节恰为 0，data 段被完整消费，userdata info 表与字符串表都在 data 段之前（已由头部偏移解释），无需再对应尾部区块。
- **字段定义完整性**：12 文件中除 index 0（null 占位）外所有实例类型均可在 `rszmhrise.json` 命中（`fieldsComplete=true`）。⇒ 任务背景提到的「files_partial=60/107、字段定义可能不全」**在这 12 个文件上不是失步原因**（但在 §4 的补充查证里确实生效，见 §5 诚实边界）。

### 3.2 关键表指向（`_summary.json` 556 行）

| 字段 | 条数 / 文件数 | 指向的实例类名（次数） |
|---|---|---|
| `_ActionList` | 97 / 10 | `Em131_00ActionSetAttack`(52)、`EnemyBTAActionTableSet`(18)、`Em131_00ActionSetNormal`(15)、`Em131_00ActionSetMove`(9)、`Em131_SetBreathTargetPos`(2)、`EnemyThinkStart`(1) |
| `_ConditionList` | 181 / 10 | `snow.enemy.ThinkCondition`(181) |
| `_TransitionActTbl` | **0 / 0** | （12 个文件内不存在此字段实例） |
| `_StateList` | 130 / 10 | `snow.enemy.ThinkState`(130) |
| `_ActionTableInfo` | 18 / 9 | `EnemyBTAActionTableSet.RegistActionTableInfo`(18) |
| `_ReferenceThinkData` | 130 / 10 | null/`ref=0`(123)、`EnemyThinkData` userdata 实例(7) |

**`_TransitionActTbl` 在这 12 个 em131 文件里是 0 条** —— 池轮盘结构（`EnemyRoutineLotSet.ConditionInfo` / `ActionTableData`）不在本次抽取范围内。

### 3.3 修复后的两个主例程对象图（此前是垃圾）

`em131_00_main`（think 主例程，root `EnemyThinkData`，ic=12，ud=2）：
```
[11] EnemyThinkData._StateList = [6, 8, 10]        ← 3 个 ThinkState
 [6] ThinkState  _ID=0  Action=[1 →EnemyThinkStart]  Condition=[3,5 →ThinkCondition]  Ref=null
 [8] ThinkState  _ID=1  Action=[]  Condition=[]  Ref=[7 →userdata em131_00_think_interrupt.user]
 [10]ThinkState  _ID=2  Action=[]  Condition=[]  Ref=[9 →userdata em131_00_mode.user]
 [3]/[5] ThinkCondition: _IsActionEnd=False, _NextStateID=1/2
```

`em131_00_combat_main`（hub 主例程，ic=14，ud=1）：
```
[13] EnemyThinkData._StateList = [5, 8, 12]
 [5] ThinkState  _ID=0  Action=[2 →EnemyBTAActionTableSet(set_type=0)]  Condition=[4]  Ref=null
 [8] ThinkState  _ID=1  Action=[7 →EnemyBTAActionTableSet(set_type=1)]  Condition=[]   Ref=null
 [12]ThinkState  _ID=2  Action=[]  Condition=[10]  Ref=[11 →userdata em131_00_ActionSpecRoutine.user]
 [1]/[6] RegistActionTableInfo: _Category=4, _TableNo=65535, _Regist=True
```

所有 `_TreeNodeID` 为合法 U32 哈希（如 4084313016 / 662500662），不再是 ref 垃圾。

---

## 4 · Hub→15 池因果链判定（任务 4）：**不能重建**

为让判定建立在**修复后的引用**上，额外用 v2 在内存中重解析了 `refs/rise_unpack/` 的 **107 个原始 `.user.2`**（P78 标量对拍所用 107 JSON 的原始二进制，一一对应）。分类实测：12 个 `attack_stance_*` Hub + 89 个 `range*check` 池（`angerrange1..5` / `normalrange1..5` / `tiredrange1..5`，即项目术语「15 池」的 3 处境 × 5 距离变体）+ 3 个 action 表 + 3 个其它。

### 四条独立硬证据

**① 格式层面：RSZ 对象引用是文件内 instance index，没有跨文件引用槽。**
Hub 与池是不同文件（且分属 em001 / em131 不同怪种）。修复后（em131 12 文件）全部 1038 个引用都落在本文件 `[0, instanceCount]` 内；107 批次里 12 个 Hub 出现的 92 个越界引用全部是 v2 未完全修复的失步残留（见 §5），不是合法跨文件指针。RSZ 数据格式不提供「指向另一个文件某实例」的字段。

**② Hub 文件内根本没有池轮盘结构。**
12 个 `attack_stance_*` Hub 的类集合只有 `ThinkState`(72)、`ThinkCondition`(72)、`EnemyAiFsmCondition`(60)、`EnemyBTAActionTableSet`(24)、`RegistActionTableInfo`(24)、`EnemyThinkData`(32)：
- `_TransitionActTbl` = **0**
- `_TransitionRate` = **0**
- `EnemyRoutineLotSet.ConditionInfo` = **0**
- `ActionTableData` = **0**

而池轮盘全部在 83 个池文件内部：376 条 `_TransitionActTbl` → **376/376 指向 `snow.enemy.ActionTableData`**，配 376 条 `_TransitionRate`、`ActionTableData._TableNo` 110 个唯一值、`_Category ∈ {0:224, 1:151, 4:1}`。这是**池文件内部的对象图**，没有一条从 Hub 出发。

> 类名来自 instanceInfo 表、字段有无来自类定义，二者都不依赖 data 流对齐 ⇒ 该结论不受 v2 在 12 个 Hub 上未完全修复的影响。

**③ Hub 唯一的对象引用「出口」是外部分件，且全部未被抽取。**
`_ReferenceThinkData` 指向 userdata 实例，其 path 在 12 个 Hub 里共指向 **15 个唯一外部分件**（`em001_act_019.user`、`em001_combo_902.user`、`em001_mode001/003/011/013/014/030_main.user`、`em001_main_out1/2_main.user` 等），实测 **15/15 均不在 107 个已解包文件内**。这是硬断点；且这些是动作表 / 连招表 / 例程主文件，**不是** `range*check` 池文件。即便补抽，也仍是另一文件内的对象图，不构成跨文件引用链。

**④ 标量连接不受引用修复影响，仍无有效共享值。**
修复对象引用**不改变任何标量字段值**，故 P78 §2.5 的标量对拍结论原样成立。本次 12 个 em131 文件复测：

| 侧 | `_TableNo` 值域 | 有效值（0<x<65535） |
|---|---|---|
| Hub（2 个 main） | `{65535: 2}` | ∅ |
| 池/其它（10 个） | `{0,1,3,4,5,6,7,8}` | `{1,3,4,5,6,7,8}` |
| **共享有效 TableNo** | | **∅（空集）** |

`_NextStateID` 是状态 ID（0/4/5/9/34/49/80/87/128/147/237/242/254…），不是池索引；P78 已判定 `_NextStateID=80 ↔ 池 _TableNo=80` 是语义错配的巧合。

### 卡点归类（对照任务 4 的四个候选）

| 候选卡点 | 是否成立 |
|---|---|
| 模板缺字段 | **主样本不成立**（em131 12 文件 `fieldsComplete=true`）；补充查证的 12 个 `attack_stance_*` Hub 成立（缺类 `0df87250`），但**不是因果链卡点**，只是解析瑕疵 |
| 引用指向未解析实例 | 否，引用全部指向本文件已解析实例 |
| 文件被 patch 覆盖 | 否，二进制干净，失步已由解析器修复证明 |
| **格式本身不支持** | ✅ **主卡点**：RSZ 无跨文件引用 + Hub 无池轮盘 + 出口外部分件未抽取 + 标量无共享值 |

---

## 5 · 对「W4 12 Hub 1:1 不可做」定案的影响（任务 5）

| 维度 | 变化 |
|---|---|
| **定案本身** | **不推翻，加强**：由「标量对拍无共享 TableNo」升级为「标量 + 对象引用 + 结构归属」三重实证。Hub 与池之间连「可由对象引用表达的连接」都不存在。 |
| **旧表述修正** | P77 §2(a)/§4、P78 §2/§5、§7 把「`_ActionList` 对象引用失步 ⇒ 因果链不能定案，需干净二进制或实机探针」列为待办。本轮证明**二进制干净、失步是解析器 bug 且已修复**，该前提作废；em131 12 文件对象引用 100% 可信。 |
| **卡点精确化** | 从「解析失败」精确化为「**结构性不可由静态对象引用重建**」。继续推进需要的是 L0/L1 运行时 FSM 装配证据（实机 / 反汇编）或补抽 15 个外部分件，而不是再修解析器。 |
| **新增正面产物** | Hub 内部对象图现在完全可信（3 ThinkState / 2 个 `EnemyBTAActionTableSet` set_type 0,1 / 门控 `_IsActionEnd` 全 False / 12 个外部分件路径清单 / `Em131_00ActionSet*` 动作集指向）。这些可用于**结构描述与后续资产抽取定位**，但仍不足以做数据表级 1:1 复刻。 |
| **待办关闭** | ✅ 「对象引用解析（需干净二进制）」关闭；「Hub→池因果链」改判为结构性不可由静态对象引用重建（不移除，但不再挂在解析缺陷上）。 |

---

## 6 · 诚实边界

1. **主交付限于 em131 的 12 个文件**：v2 在这 12 个上 100% 修复（§3）。其它 52 只怪的 `_main`/`stamina_data`/action/combo 未做全量。
2. **补充查证（rise_unpack 107 文件）v2 为 95/107 `parseOK`**：12 个 `attack_stance_*` Hub 每文件含 **1 个模板未收录类实例 `typeId=0df87250`**（index 19 或 20），v2 无法确定其字段长度 ⇒ `fieldsComplete=false`、tail=±4、仍有 7~9 个非法 ref。这**印证任务背景的 `files_partial=60/107`**。因此：
   - 这 12 个 Hub 的**标量数值（如 `Hub _TableNo={65535:12, 18684:8, 17:4}`、`_IsActionEnd={False:64,True:8}`）含失步污染，本报告不将其作定量依据**；标量对拍仍以 P77 §2.5 / P78 的既有定案为准。
   - 但 §4 的**结构结论**（类集合、字段有无、池轮盘归属、外部分件路径、文件名分类）来自 instanceInfo 表 / 类定义 / userdata info 表 / 文件名，**不依赖 data 流对齐**，可靠。
3. 107 批次 v2 共 5684 个引用，92 个非法全部集中在这 12 个 Hub；其余 95 个文件（含全部 83 个池文件）引用 100% 合法。
4. 未抽 15 个 Hub 外部分件；未做 `_TableNo → _actionNo → 招式名` 中间映射；未做 Rise 实机 / 反汇编（沿用 P32:201 证据等级声明）。
5. 未改插件源码、未编译 NRO、未部署、未动 `load_order` / 游戏资源 / 既有 `out/rsz_main_json/`。

---

## 7 · 产物清单

| 类别 | 路径 |
|---|---|
| 新解析工具 | `tools/rsz_parse_v2.py` |
| 重解析 JSON（12） | `out/rsz_main_json_v2/*.json` |
| 关键表汇总（556 行） | `out/rsz_main_json_v2/_summary.json` |
| 本报告 | `out/P80_object_ref_resolution.md` |
| 诊断 / 实证脚本（新增，可复现） | `out/_diag_rsz.py`（二进制 dump + 字段偏移追踪）、`out/_probe_strategy.py`（12 组对齐策略搜索）、`out/_probe_all.py`（12 文件策略验证）、`out/_stat_v1_v2.py`（v1/v2 对比 + 关键表统计）、`out/_chain_verdict.py`（107 文件因果链决定性判定） |

复现命令：

```bat
python tools\rsz_parse_v2.py --all --json-out out\rsz_main_json_v2 --summary out\rsz_main_json_v2\_summary.json
python out\_diag_rsz.py <某个 .user.2>
python out\_probe_strategy.py
python out\_stat_v1_v2.py
python out\_chain_verdict.py
python out\_v2_full_468.py
```

---

## 8 · 补充：52 怪全量交叉验证（bulk-assets 协作后追加）

bulk-assets 完成 52 怪 / 468 个 `.user.2` 全量抽取（`refs/_bulk_extract/`）后邀请用 v2 做全量对象引用验证。本节用 `tools/rsz_parse_v2.py` 在**内存中**解析全部 468 个文件（只读，不落盘新 JSON），检验 §1~§4 的结论能否泛化，并核对 bulk-assets `P80_bulk_monster_assets.md` §1.1 的数据可信度前提。复现脚本 `out/_v2_full_468.py`。

### 8.1 总览

| 指标 | v1（`out/rsz_bulk_json/`） | v2（全量重解析） |
|---|---|---|
| 含非法引用的文件数 | **252 / 468** | **37 / 468**（−85%） |
| 非法引用数 | **1899 / 24371** | **574 / 23844**（−69.8%） |
| `parseOK` | — | **430 / 468（91.9%）** |
| 数组 count 异常 | — | 145 / 9078 |
| `tail=0` 的文件 | — | 438 / 468 |

> v1 与 v2 的「引用总数」不可直接相减比较：v1 失步后会读出垃圾 count 并造出大量伪 ref，v2 不含这些。可比的是**非法引用数与受影响文件数**。

### 8.2 按类别（决定性）

| 类别 | 文件数 | ud=0 / ud>0 | v2 parseOK | 非法引用 | 异常 count |
|---|---:|---:|---:|---:|---:|
| `main` | 78 | 0 / 78 | **78/78** | **0** | 0 |
| `combat_main` | 78 | 0 / 78 | **78/78** | **0** | 0 |
| `range_data` | 78 | 78 / 0 | **78/78** | **0** | 0 |
| `stamina_data` | 78 | 78 / 0 | **78/78** | **0** | 0 |
| `act` | 105 | 67 / 38 | 79/105 | 301 | 67 |
| `combo` | 51 | 2 / 49 | 39/51 | 273 | 78 |

- **含 userdata 的 `main` / `combat_main` 共 156 个文件 100% 修复、0 非法引用** ⇒ §1 的 userdata 根因与 §2 的 v2 修复**泛化到全部 52 怪**，不是 em131 特例。
- **38 个残余不 OK 文件全部集中在 `act` / `combo`**，与 userdata 无关，分**两种**根因：
  - **37 个 = 模板缺类**（`fieldsComplete=false`）：共 9 个未收录 `typeId`（完整清单见 §8.5），主要是 `0df87250`(25 次)、`077a9e93`(7)、`026f597b`(6)、`0a84b65f`(4)。这与 §6 诚实边界里 rise_unpack 107 批次的现象一致，印证任务背景的 `files_partial=60/107`。
  - **1 个 = 第三种失步模式（String 字段编码）**：`em007_act_001` 是 38 个里唯一 `fieldsComplete=true` 却不 OK 的（`tail=332`、14 个非法 ref、3 个异常 count）。详见 §8.6。

### 8.3 对 bulk-assets 报告的两点交叉反馈

**① 背书（结论不变）**：`range_data` 78/78 与 `stamina_data` 78/78 在 v2 下 `parseOK`、0 非法引用，且 **v1 与 v2 的 ref 序列逐项一致**（未出现在不一致清单里）。⇒ `P80_bulk_monster_assets.md` 的 **Q(a) 坐实 / Q(c) 翻案**所依赖的标量数据完全可信，不受解析器选择影响；§1.1 的 v2 crosscheck 双重确认由本次 468 文件全量验证进一步加固。

**② 需要精化一处措辞（不改变结论）**：§1.1 第 40 行「Q(a)/Q(c) 的全部数据在 `ud=0` 文件上，**v1 解析完全正确**」若作为**一般命题**不严格成立 —— 实测有 **12 个 `userdataCount=0` 但 `fieldsComplete=false`** 的文件（全为 `act` 类，如 `em001_act_002`、`em072_act_002`、`em081_act_001`），其中 **4 个** v1 与 v2 的 ref 序列不一致，且 `em007_act_001`(21→37)、`em072_act_002`(31→102) 两例 v1 **非法引用数为 0 却是 `partial` 提前 break 丢字段**，并非「没有非法 ref 就完整」。
⇒ 建议把该句限定为「**`range_data` / `stamina_data` 这两类 `ud=0` 文件 v1 解析完全正确**」（这才是 Q(a)/Q(c) 实际用到的数据源），或补一句「`act`/`combo` 另有**模板缺类**导致的失步，与 userdata 无关」。这与该报告 §5 第 120 行「Q(b) 的 act/combo 标量仅作结构佐证」的谨慎口径一致，并由本次 v2 全量数字给出量化支撑；**Q(a)/Q(c)/Q(b) 三条结论均不受影响**。

### 8.4 对既有定案的影响

无新增改动：§4 的「Hub→15 池因果链不能由对象引用重建」与 §5 的「W4 12 Hub 1:1 不可做不推翻」在 52 怪全量下依旧成立（对象引用仍全部为文件内 instance index）。本节只把「对象引用修复」的适用范围从 em131 12 文件扩展到 52 怪 468 文件，并给出**可信文件判据**：以 `diagnostics.parseOK` / `fieldsComplete` 为准，`act`/`combo` 的 38 个不 OK 文件其标量值不作定量依据。

### 8.5 468 文件完整缺类清单（供 bulk-assets #13 对照）

468 个文件中未收录 `typeId` 共 **9 类 / 52 个实例**，全部落在 `act`/`combo`：

| typeId | 实例数 | typeId | 实例数 | typeId | 实例数 |
|---|---:|---|---:|---|---:|
| `0df87250` | 25 | `077a9e93` | 7 | `026f597b` | 6 |
| `0a84b65f` | 4 | `07e5ee43` | 3 | `04db4de2` | 3 |
| `02da62cf` | 2 | `041c55aa` | 1 | `0a59bcb6` | 1 |

⇒ **超出 107 批次见过的 `0df87250` 共有 8 类**。38 个不 OK 文件里 37 个由这些缺类导致；逐文件缺类映射可用 `out/_v2_full_468.py` 复现（该文件已打印 38 个文件的 `tail` / 非法 ref / 异常 count / `fieldsComplete` / 缺类集合）。

### 8.6 第三种失步模式：String 字段是内联 UTF-16，不是 4 字节 ref

`em007_act_001`（ic=34、ud=0、`fieldsComplete=true`）是 38 个里唯一**不因缺类**而失步的文件，说明存在独立于 userdata 与缺类的第三种模式。字段偏移追踪（`out/_diag_rsz.py` 同款方法）定位到 index 21 `snow.enemy.aifsm.EnemyCheckPartsBroken`：

```
idx20 ThinkState          正常结束 @708
idx21 EnemyCheckPartsBroken 起始 @708
  v0_ID@708 U32 / v1_GUID@712 Guid(16B) / v2_Condition@728 Bool
  _selectPartsName@732  String  → u32 = 9
  _partsNames@736      String[] → count 读到 0x00610064  ← 垃圾，break
idx22 ThinkCondition._Condition@740 = 0x0061006d  ← 也是 UTF-16 字节
```

二进制实证（abs 728..）：

```
728: 01 00 00 00 | 09 00 00 00 | 64 00 61 00 6d 00 61 00
744: 67 00 65 00 | 5f 00 2d 98 | 00 00 ...   → UTF-16 "damage_頭"
```

⇒ **RE Engine 的 `String` 字段格式是 `u32 字符数 + UTF-16 字符 + u16 NUL` 的内联变长字符串**（此处 9 字符 → 4+18+2=24 B），**不是** 4 字节 instance index。v1 与 v2 的 `REF_TYPES` 都把 `String` 当作 4 字节 ref，只消费 4 B，导致其后所有实例整体错位；`String[]` 更严重（每个元素都是变长串）。垃圾值 `0x0060FA44` / `0x0061006d` 实为 UTF-16 字符对，与 §1 里 `_TreeNodeID` 被误读同理，均为错位产物而非噪声。

**影响范围（实测）**：模板中 1742 个类含 `String` 字段，但 468 个 AI 资产里**仅 3 个实例**（全部为 `EnemyCheckPartsBroken`），分布在 3 个文件 `em007_act_001` / `em025_combo_001` / `em136_act_001`，且都在已标注「不作定量依据」的 `act`/`combo` 中。⇒ 该缺陷**不改变任何既有结论**，`main`/`combat_main`/`range_data`/`stamina_data` 四类都不含 String 字段。

**未修原因（诚实边界）**：正确支持 `String` 需改 `scalar_value()` 与数组元素解析（变长 + 对齐），而 bulk-assets 的 #13 正在基于当前 v2 产物定稿，此时改共享工具会使其产物与工具版本不一致；且该模式只影响 3 个已排除文件。故本轮**不改 `tools/rsz_parse_v2.py`**，把这 3 个文件按 `diagnostics.parseOK=false` 排除即可。若后续需要解析含 String 字段的其它资产，再单独补该类型支持。

### 8.7 对「补模板 / 扩展 v2 缺类容错」的判断（回应 bulk-assets 征询）

bulk-assets 同步 9 类缺类后征询是否值得补 `refs/rszmhrise.json` 或扩展 v2 容错。为让判断有依据，做了 `out/_probe_unknown_skip.py`（只读、内存、未改任何工具/产物）：对 37 个 `fieldsComplete=false` 文件，假设未知类实例**统一占 S 字节**（S ∈ {0,4,8,…,96} 共 16 个候选），按「引用全合法 + 数组 count 合理 + `|tail|` 最小」选最佳。

| 结果 | 数字 |
|---|---|
| 能达到「引用全合法 + 数组合理 + `tail=0`」 | **11 / 37（29.7%）** |
| 仍无法修复 | **26 / 37** |
| 最佳 S 分布 | `28`×10、`0`×9、`56`×3、`12`×3、`20/64/4/8`×2、`48/80/36/16`×1 |
| 典型失败 | 多未知类实例文件：`em086_combo_050`(6)、`em097_combo_000`/`em019_combo_001`/`em072_act_002`(各 3)；另有 5 个文件 `badRef=0` 但 `badCnt>0`（叠加 §8.6 String 变长字段） |

**判断：本轮两项都不做。**
1. **补 `rszmhrise.json` 不可行**：9 个类缺的是完整字段布局（`name`/`type`/`size`/`align`/`array`），二进制只能反推字节长度、推不出字段名与类型；改 66 MB 共享参考资产会改变所有人的解析基线；且这 37 个文件已按 `parseOK=false` 排除，**收益为零**。真要补只能依赖更完整的类型库或反汇编，属另一类数据来源任务。
2. **扩展 v2 缺类容错性价比低**：统一 S 只覆盖 29.7%，剩余 26 个需逐实例独立搜索（组合爆炸）或真实字段定义；部分还叠加 String 变长编码；且会让 bulk-assets 已定稿的 `out/rsz_bulk_json_v2/` 468 份产物与工具版本不一致。即便全修好，这 37 个 `act`/`combo` 文件也只是 Q(b) 的「结构佐证」，**不改变任何定案**。
3. 保持 `diagnostics.parseOK=false` 排除口径即可。**留给未来的线索**：`S=28` 在 10 个文件上重复出现，强烈暗示 `0df87250` 类的数据长度约为 28 B；`out/_probe_unknown_skip.py` 可复现。

本轮未改 `tools/rsz_parse_v2.py`、`refs/rszmhrise.json`、`out/rsz_bulk_json_v2/`。
