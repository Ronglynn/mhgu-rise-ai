# P77 · Rise 静态资产真实抽取（翻案）：12 个文件、4 类实证、5 条旧定案修正

用户 18:20「把你能做的全做了」→ 18:24 要求并行推进。本文件记录 **main 亲自执行的真实抽取**（与并行子任务的产物互补）。

## 0 · 最大翻案：pak 就在本机

之前子代理报「全盘 0 命中、`re_chunk_000.pak` 不在本机」，据此把 P32 §7 的最高价值缺口判为「外部依赖」。**实测漏查**：

```
D:\Steam\steamapps\common\MonsterHunterRise\re_chunk_000.pak              32,237,404,351 B
D:\Steam\steamapps\common\MonsterHunterRise\re_chunk_000.pak.patch_001.pak  4,388,488,186 B
```

工具链齐全：`00_Tools/06_REEngine_Pak/ree-pak-cli.exe` + `assets/filelist/MHR_STM_Release.list`（180,404 行）+ `04_RiseAI/tools/rsz_parse.py` + `04_RiseAI/refs/rszmhrise.json`（66 MB）。⇒ **P0 缺口不是外部依赖，是没找对目录**。

## 1 · 抽取与解析（已实际执行）

```bat
ree-pak-cli.exe unpack -p MHR_STM_Release.list -i <主 pak> -o refs/_main_extract ^
  -f "natives/stm/enemy/em131/(00/ai_fsm_user_data/(hub|think)/.*main|00/user_data/em131_00_(range|stamina)_data|common/act_tbl_user_data/(action|combo)/.*)\.user\.2" --skip-unknown
ree-pak-cli.exe unpack ... -i <patch pak> ... --override   :: patch 覆盖同名
```

- 路径表中命中 12 个目标（行号 58066/58068/58235/58237/58243–58250），主 pak 与 patch 均抽取成功。
- 原始文件：`04_RiseAI/refs/_main_extract/`，共 12 个，720 ~ 11,200 B。
- 解析：`04_RiseAI/tools/extract_rise_facts.py` 直接 import `rsz_parse.parse()`（绕开其 CLI bug：`args` 过滤只排除 `--` 开头参数，会把 `--json-out` 的**值**当成输入文件）。输出 `out/rsz_main_json/*.json` 12 个 + `out/rise_extracted_facts.json`。
- 解析质量：12/12 出 JSON，`class_ok` 普遍接近 `instanceCount`，但 `bytesConsumed` 常小于 `fileSize`（如 main 224/940、stamina 196/388）⇒ 部分实例未消费；`ThinkState._ActionList` 出现 `ref:0x4BCCF5F2` 垃圾值，**印证 P32:36 对象引用失步，标量才可信**。

## 2 · 四类实证

### (a) `*_main.user.2` 主例程：P32 §7 第 1 条缺口已补上
`em131_00_main.user.2` / `em131_00_combat_main.user.2` 都能解析：
- `EnemyCheckThinkMain {_CheckType: 3 / 17, v2_Condition: True}`
- `ThinkCondition {_Condition: ref, _IsUnderLayerEnd: False/True, _IsActionEnd: False, _NextStateID: 1 / 2}`
- `EnemyBTAActionTableSet.RegistActionTableInfo {_Category: 4, _TableNo: 65535, _Regist: True}`

⇒ **主例程里 `_IsActionEnd` 全为 False**；门控 True 只在 12 个 `attack_stance_*` Hub 里（P32:48），与「L3 门控在 Hub 层」一致。但 `_ActionList` 失步，**Hub→15 池的对象引用因果链仍不能定案**，只能确认主例程结构存在。

### (b) `em131_00_range_data.user.2`：Rise 距离档是 **4 档**，不是 5 档
- `EnemyRange.RangeInfo._RangeDistance` = `[1.0, 2.0, 3.0, 4.0]`（实例 1）、`[27.0, 2.0, 3.0, 4.0]`（实例 2/3）；`_UpHeight = _DownHeight = 20.0`
- `KehaiData._RangeKehaiAdd = [8, 5, 3, 1]`；`HateData._range_hate_add_data = [8, 5, 3, 1]`
- `HateBlockCorrectionData`：`_BlockMainRate 1.2 / _FixedHeightRate 0.8 / _BlockMainOutRate 0.6 / _BlockOutRate 0.4 / _SafeZoneRate 0.0`
- `HateData._attackHateRate 10.0 / 40.0`、`_damageHateRate 20.0 / 10.0 / 0.0`、`_targetHate -30 / -50 / -100`

⇒ **4 元素数组与 GU `dttune` 的 4 档 f32 阈值表同构**；15 池的 `range1..5` 是「状态×距离池索引」，另一套概念。**文件里没有 5 档递增几何阈值** ⇒ P34「Rise 5 档几何阈值未抽取」即使抽到 range_data 也未补上；但反过来说，把 137 怪 dttune 表编译进插件去「对齐 Rise 5 档」是**对错了层**（详见 P73）。

### (c) `em131_00_stamina_data.user.2`：疲惫时长不是静态配置
- `EnemyStaminaData {_motRate: 1.0, _tiredSec: 0.0, _hyakuryuTiredSec: 0.0, _mapNikuEatSec: 20.0, _MouthToNullDistance: 4.0, _SetMeatEatSec: 10.0, _SetMeatConditionSec: 5.0}`
- 4 组 `PointData {_percent: 100, _point: 1000}` + `SeparateData {_recovStartPoint: 0.0, _recovEndPoint: 100.0}`
- **`PredatorData {_IsPredator: 0, _ActionStance: 0, _EnableRadius: 400.0, _EmTypes: [0]}`**

⇒ `_tiredSec = 0.0` 说明 Rise 疲惫时长由运行时 `_AddTiredTime` 动态累加（P32 记 60 处），**不是静态可复刻的数值**；`_motRate=1.0` 也未下调动作速度。这解释了「按 Rise 抽选层逻辑做不出喘息」（P72 §6）：连引擎层实例数值都不是静态表。
⇒ `PredatorData` 是**领地争夺机制在 Rise 侧的首个代码级实证**（`_IsPredator` 开关 / `_EnableRadius` 半径 / `_EmTypes` 目标怪种 / `_ActionStance` 处境），详见 P74。

### (d) action / combo：`TableNo` 可部分落地
- `em131_act_004/005`：`_Category: 0`（action）、`_TableNo: 4 / 5`
- `em131_combo_001/003/005/006/007/008`：`_Category: 1`（combo）、`_TableNo: 1 / 3 / 5 / 6 / 7 / 8`
- `combo_005` 有 450 个实例；各文件 `ThinkCondition._NextStateID` 实测 2 / 14 / 4 / 8 等

⇒ `TableNo → 具体动作表文件` 的**文件名级映射可建立**（这次抽的 12 个就是），但 `_TableNo(U16) → _actionNo(U16) → 招式名` 的中间映射仍缺（P32 §7 第 3 条）。

## 2.5 · 107 个已解包 JSON 的标量对拍（补充实证）

工具 `tools/audit_rise_107_main.py` → `out/rise_107_hub_pool_main.json`（只读，与并行子任务的 `rise_hub_pool_scalars.json` 互补）：

| 指标 | 实测 |
|---|---|
| 文件 | 107 = 12 Hub + 89 池/routine + 6 其它 |
| Hub `ThinkCondition` | 44 个，其中 **`_IsActionEnd = True` 恰 12 个**（与 P32:48「12 True / 32 False，每文件恰 1」一致） |
| `_NextStateID` 值域 | 主要为 4/5（各 12 次），另有 0/9/34/49/80/87/93/128/147/237/242/254 等离散值 |
| 池 `_TransitionRate` | **89/89 文件率和恒 100**（与 `_TransitionRate` 百分制轮盘同构） |
| Hub `_TableNo` 集合 | 仅 `{0}`（其余为 65535 未注册） |
| 池 `_TableNo` 集合 | 100+ 个（0,1,2,…,902） |
| 共享 TableNo | 仅 `{0}`（占位） |

⇒ **Hub 与 15 池之间没有共享的有效 TableNo；`_NextStateID` 是状态 ID 不是池索引；对象引用失步** ⇒ 即使把主例程抽出来，**标量层面仍建不出 Hub→池因果链**。这为「W4 12 Hub 数据表级 1:1 不可做」补上了基于标量对拍的实证，而不再只是「未解包」的推断。

## 3 · 需要修正的旧定案

| 旧定案 | 修正 |
|---|---|
| P32 §7：`*_main.user` 主例程 0 个，最高价值缺口 | 已抽到 2 个（em131）并可解析；结构存在，但对象引用失步 ⇒ 标量可信、因果链仍未闭合 |
| P34 / P57：`em131_00_range_data.user.2` 未抽取 → 无 5 档几何阈值 | 文件已抽，**内容是 4 档仇恨/气息参数，没有 5 档递增阈值**；「5 档」是池索引不是几何阈值 |
| P32 M3 / P72 §6：`_tiredSec` 实例数值未解包 | 已解包：**em131 为 0.0**，`_motRate 1.0` ⇒ 疲惫时长运行时动态，非静态复刻对象 |
| P36 / P72：领地争夺「Rise 侧无专属机制」的推断 | `PredatorData` 实证存在（em131 关闭），属耐力/掠食者参数层 ⇒ 机制确有其事，问题是 GU 侧有无等价结构 |
| P72 §0 / P76 §3：pak 不在本机 ⇒ P0 需外部数据源 | **翻案**：pak 就在 `D:\Steam\steamapps\common\MonsterHunterRise\`，抽取已实际完成 |

## 3.5 · 顺带核实：编译期阈值表对已实机主怪的覆盖

`out/dist_bands_all.json`（P60 全量 137 怪）：

| 怪 | label | distBlocks | 4 档阈值行 | 首行 |
|---|---|---|---|---|
| 轰龙 `sp=0020` | `em032_00` / `em032_04` | 188 / 188 | **2 / 2** | `[450,1000,2700,5000]` / `[500,1000,1500,2500]` |
| 斩龙 `sp=0050` | `em080_00` / `em080_04` | 71 / 75 | **0 / 0** | — |
| 雌火龙 | `em001_00` | 235 | 3 | `[600,1100,2500,5000]` |

⇒ 「按怪种编译 137 张 dttune 表」的路线 B 对 **v66/v69 两场实机的主怪斩龙直接无效**（必须降级到 case 索引分档）；P60 另有 18/137 怪无阈值行。结合 §2(b)「Rise `range_data` 没有 5 档递增几何阈值」，路线 B 的收益被两处实证同时下调，详见 `P73`。

## 4 · 仍未补上的（诚实边界）

- 只抽了 **em131** 一只怪的 12 个文件；其它 52 个 emNNN 的 `_main` / `stamina_data` / action / combo 未抽（路径表可查，工程未做全量）。
- 15 池 `range1..5` 的**物理阈值数值**仍无来源（不在 range_data 里）。
- `ThinkState._ActionList` / `_ConditionList` 对象引用失步，Hub→池因果链仍不能定案。
- `_TableNo → _actionNo → 招式名` 中间映射表仍缺；`actiontune/motion/message` 类文件未抽。
- **本轮全部为静态资产复核，没有 Rise 实机或反汇编**（沿用 P32:201 的证据等级声明）。

## 5 · 产物

| 类别 | 路径 |
|---|---|
| 抽取的原始 `.user.2` | `04_RiseAI/refs/_main_extract/`（12 个） |
| 解析 JSON | `04_RiseAI/out/rsz_main_json/`（12 个） |
| 字段汇总 | `04_RiseAI/out/rise_extracted_facts.json` |
| 工具 | `04_RiseAI/tools/extract_rise_facts.py`；可重复抽取脚本见 `tools/extract_rise_targets.cmd`（子任务维护） |
| 关联报告 | `P73` 纪律重评 / `P74` 领地争夺 / `P75` 成品候选 / `P76` 目标对齐矩阵 |

本轮未改插件源码、未编译 NRO、未部署、未动 `6_` / load_order / 游戏资源。
