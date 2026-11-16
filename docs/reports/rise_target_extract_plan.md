# MHRise 静态 AI 资产定向抽取 — 已完成真实抽取与实证结论

> 状态：**pak 已在本机找到，真实定向抽取与解析已完成**。此前「全盘 0 命中 / 必须等 pak」
> 的判断源于漏查，已作废。本文记录数据源、抽取链、实测数值、可重复脚本，以及仍属推断的部分。
> 配套产物：`tools/extract_rise_targets.cmd`、`out/rise_hub_pool_scalars.json`、
> `tools/audit_rise_scalars.py`。

---

## 1. 结论速览

- **数据源更正**：`re_chunk_000.pak`（主包 32.2 GB）与 RE Engine patch 包都在本机
  `D:\Steam\steamapps\common\MonsterHunterRise\`，无需再等任何外部数据。
- **已完成真实抽取**：主包 + patch 包两步抽取（patch 用 `--override` 覆盖同名，RE Engine
  patch 优先），共取得 **12 个 em131 `.user.2`** → **12 个解析 JSON**。
- **实证数值已拿到**：`range_data` 的 4 档距离/仇恨数组、`stamina_data` 的 `_tiredSec`/
  `_motRate` 等标量、action/combo 的 `_TableNo`/`_Category`/实例数（见第 5 节）。
- **因果链 (a) 仍为 NO**：`*_main.user.2` 里的 `_StateList`/`_ActionList` 是原始 4 字节
  对象引用，解析器未解析对象表，**无法补全 Hub→15 池因果链**；标量才可信。
- **疲惫专属动作 (d) 未能由静态字段证实**：action/combo 中没有任何 tired/fatigue 命名的
  字段或类；唯一含 "Breath" 的 `Em131_SetBreathTargetPos` 是吐息攻击瞄准，不是「疲惫喘息」。
- **现在能补多少**：静态资产层面已全部补齐；剩下无法定论的（运行时疲惫机制、动作 ID 语义、
  15 池索引对应关系等）见第 7 节，属推断，不是「等 pak」能解决的。

---

## 2. 数据源与抽取链（实测）

| 项 | 实测结果 |
|---|---|
| 主包 | `D:\Steam\steamapps\common\MonsterHunterRise\re_chunk_000.pak` = 32,237,404,351 B（32.2 GB） |
| patch 包 | `D:\Steam\steamapps\common\MonsterHunterRise\re_chunk_000.pak.patch_001.pak` = 4,388,488,186 B（4.39 GB） |
| 路径表 | `00_Tools/06_REEngine_Pak/assets/filelist/MHR_STM_Release.list`，180404 行，前缀 `natives/stm`（**小写**） |
| 442 清单 | `04_RiseAI/refs/rise_enemy_ai_paths.txt`，442 行，前缀 `natives/STM`（**大写**） |
| 抽取工具 | `00_Tools/06_REEngine_Pak/ree-pak-cli.exe`（`unpack -p -i -o -f`，支持 `--test` / `--backend mmap`） |
| RSZ 解析器 | `04_RiseAI/tools/rsz_parse.py` + `04_RiseAI/refs/rszmhrise.json`（69,287,210 B ≈ 66 MiB） |

**大小写坑**：清单是 `natives/STM`，而 `-p` 读取的路径表是 `natives/stm`。`-f` 故意使用
**不含 `natives` 前缀的片段正则**（`em131/...`），对小写路径表稳定命中，不受 `STM/stm` 影响。
实际抽出的 12 个文件落在 `natives/stm/enemy/em131/...`（小写），印证了这一点。

**main 已完成的真实抽取产物**（本 teammate 直接核验存在）：
- 原始 12 个 `.user.2`：`04_RiseAI/refs/_main_extract/natives/stm/enemy/em131/...`
- 解析 12 个 JSON：`04_RiseAI/out/rsz_main_json/*.user.2.json`（**全部 `partial=False`**）
- 字段汇总：`04_RiseAI/out/rise_extracted_facts.json`（204,220 B），工具
  `04_RiseAI/tools/extract_rise_facts.py`
- 另有 `out/rise_107_hub_pool_main.json`（main 对 107 个旧 JSON 的汇总）

本文第 5 节的数值，除采用 main 报告外，本 teammate 亦直接读取
`out/rsz_main_json/` 12 个 JSON 逐项复核，与 main 报告一致；标注「直接复核补充」的
额外字段同样来自该 JSON，非推断、非编造。

---

## 3. 4 类目标在 442 清单中的确切行号与路径

`refs/rise_enemy_ai_paths.txt`（`natives/STM`，行号 = `grep -n`，1 起算）：

### 类别 A — `em131/00/ai_fsm_user_data/(hub|think)/.*_main.user.2`（2 条）
| 行号 | 路径 |
|---|---|
| 219 | `natives/STM/enemy/em131/00/ai_fsm_user_data/hub/em131_00_combat_main.user.2` |
| 221 | `natives/STM/enemy/em131/00/ai_fsm_user_data/think/em131_00_main.user.2` |

### 类别 B — `em131/00/user_data/em131_00_(range|stamina)_data.user.2`（2 条）
| 行号 | 路径 |
|---|---|
| 324 | `natives/STM/enemy/em131/00/user_data/em131_00_range_data.user.2` |
| 326 | `natives/STM/enemy/em131/00/user_data/em131_00_stamina_data.user.2` |

### 类别 C — `em131/common/act_tbl_user_data/(action|combo)/.*\.user\.2`（8 条）
| 行号 | 路径 |
|---|---|
| 331 | `.../act_tbl_user_data/action/em131_act_004.user.2` |
| 332 | `.../act_tbl_user_data/action/em131_act_005.user.2` |
| 333 | `.../act_tbl_user_data/combo/em131_combo_001.user.2` |
| 334 | `.../act_tbl_user_data/combo/em131_combo_003.user.2` |
| 335 | `.../act_tbl_user_data/combo/em131_combo_005.user.2` |
| 336 | `.../act_tbl_user_data/combo/em131_combo_006.user.2` |
| 337 | `.../act_tbl_user_data/combo/em131_combo_007.user.2` |
| 338 | `.../act_tbl_user_data/combo/em131_combo_008.user.2` |

> 合计 **12** 条。未放宽到其它怪种的 `*_main.user.2`，以控制单次抽取规模。

### 路径表命中（`MHR_STM_Release.list`，小写）
| 类别 | 行号 | 命中数 |
|---|---|---|
| A hub / think main | 58066 / 58068 | 2 |
| B range / stamina data | 58235 / 58237 | 2 |
| C action | 58243 / 58244 | 2 |
| C combo | 58245–58250 | 6 |
| **合计** | | **12** |

组合正则对路径表 `grep -Ec` 恰命中 12 行，无多抽漏抽；主包 + patch 抽取后
`refs/_main_extract/` 正好 12 个文件，与清单一致。

---

## 4. 一键脚本 `04_RiseAI/tools/extract_rise_targets.cmd`（已更新为真实抽取版）

- **默认 pak 写死为两个绝对路径**（主包 + patch 包），双击即可跑，无需手动拷 32 GB；
  保留 `%1` 传参覆盖主包路径的能力。
- **双跑 + patch 优先**：STEP 1 抽主包到 `04_RiseAI/refs/rise_target_unpack`，STEP 2 用
  **同一正则**抽 patch 包到同一目录并 `--override`，同名文件以后者（patch）为准。
- **PRECHECK**：先用 `--test`（只解内存不写盘）验证正则命中数；`set DO_TEST=0` 可跳过。
  全部 unpack 使用 `--backend mmap` 处理 32 GB 包。
- **检查提示保留、硬退出移除**：对 pak / 工具 / 路径表只打印 `HINT`，不再因缺主包直接
  `exit`；真失败由 `errorlevel` 转到 `:unpackfail` / `:parsefail` 干净报错。
- **格式**：纯 ASCII（0 非 ASCII 字节）、CRLF（77 行、0 孤立 LF）、所有 `echo` 及
  `if ... echo` 行里的 `| & < >` 均用 `^` 转义（程序化校验 0 漏网）。
- `-f` 用展开成 6 段、不含括号的分支，命令行里每个 `|` 写成 `^|`，规避本工程 cmd 管道坑；
  与第 3 节的 3 段正则语义等价（同为 12 命中）。

**STEP 3 解析与已知 CLI bug**：字面形式
`python 04_RiseAI/tools/rsz_parse.py <files> --json-out 04_RiseAI/out/rsz_target_json`
有 bug —— `rsz_parse.py:163` 把 `--json-out` 的**值**也收进 `args`，会把输出目录当
`.user.2` 去 `read_bytes()` 崩溃（实测确认；`extract_rise_facts.py` docstring 亦记录）。
脚本改用 `python -c` 直接 `import rsz_parse` 的 `parse()` 并自行写 JSON（与
`extract_rise_facts.py` 同套路），输出仍落在 `04_RiseAI/out/rsz_target_json`。

> 说明：本脚本是**可重复的一键工具**，其输出目录（`refs/rise_target_unpack/`、
> `out/rsz_target_json/`）与 main 本次实测产物目录（`refs/_main_extract/`、
> `out/rsz_main_json/`）不同名但内容等价；两者不冲突。

---

## 5. 实证结论（本次真实抽取的核心）

### (b) `range_data` — 距离阈值：**4 档，不是 5 档**，「5 档几何阈值」未出现

`em131_00_range_data.user.2.json` 实测：

| 类 | 字段 | 实测值 |
|---|---|---|
| `EnemyRange.RangeInfo`（3 个实例） | `_RangeDistance` | `[1.0, 2.0, 3.0, 4.0]`（1 个）；`[27.0, 2.0, 3.0, 4.0]`（2 个） |
| 同上 | `_UpHeight` / `_DownHeight` | `20.0` / `20.0` |
| `EnemyRange.KehaiData` | `_RangeKehaiAdd` | `[8, 5, 3, 1]` |
| `EnemyRange.HateData`（4 个实例） | `_range_hate_add_data` | `[8, 5, 3, 1]`；`[-1,-1,-1,-1]`×2；`[3, 2, 1, 0]` |
| `EnemyRange.HateBlockCorrectionData` | 5 个 rate | `_BlockMainRate:1.2, _FixedHeightRate:0.8, _BlockMainOutRate:0.6, _BlockOutRate:0.4, _SafeZoneRate:0.0` |

> 直接复核补充：另有 3 组 `HateBlockCorrectionData`，分别为
> `{1.0, 0.0, 0.5, 0.0, 0.0}`×2 与 `{1.0, 0.3, 0.5, 0.1, 0.0}`；以及
> `_attackHateRate` / `_damageHateRate` = 10/20、40/0、40/0、40/10。

**结论**：所有距离/气息/仇恨数组都是 **4 元素**，Rise 仇恨与气息距离档是 **4 档**。
15 个 `main_out1_*range*check` 池的 `range1..5` 是**另一套索引**，不能与这 4 档直接对齐。
本文件里**没有出现「5 档几何阈值」**，如实标注：该预期数值不存在，不是「没找到」而是
数据结构本身为 4 档。

### (c) `stamina_data` — `_tiredSec` / `_motRate` / `_IsTired`：**疲惫时长不是静态配置**

`em131_00_stamina_data.user.2.json` 实测：

| 类 | 字段 → 值 |
|---|---|
| `EnemyStaminaData` | `_motRate: 1.0`、`_tiredSec: 0.0`、`_hyakuryuTiredSec: 0.0`、`_mapNikuEatSec: 20.0`、`_MouthToNullDistance: 4.0`、`_SetMeatEatSec: 10.0`、`_SetMeatConditionSec: 5.0` |
| `PointData`（4 组） | `_percent: 100`、`_point: 1000` |
| `SeparateData`（4 组） | `_recovStartPoint: 0.0`、`_recovEndPoint: 100.0` |
| `PredatorData` | `_IsPredator: 0`、`_ActionStance: 0`、`_EnableRadius: 400.0`、`_EmTypes: [0]` |

> 直接复核补充（同一 JSON 实测）：`_InCombatMapMeatEatFlag: False`、
> `_IsEnableSetMeatEat: False`、`_SetMeatRecovStartPoint: 20.0`、
> `_SetMeatRecovEndPoint: 80.0`。

**`_IsTired` 在 12 个 JSON 中不存在** —— 全量字段名里只有 `_tiredSec`、
`_hyakuryuTiredSec` 含 "tired"，且都在 `stamina_data`。即疲惫状态不是静态布尔配置，
而是运行时标志。**结论**：em131 静态 `_tiredSec = 0.0`，疲惫时长并非静态配置，
而是运行时 `_AddTiredTime` 动态累加（该运行机制属推断，见第 7 节）。

### (a) `*_main.user.2` 能否补上 Hub→15 池因果链：**NO（仍不可由标量建立）**

`em131_00_main.user.2.json` / `em131_00_combat_main.user.2.json` 实测（标量部分可信）：

| 文件 | 实测标量 |
|---|---|
| main | `EnemyCheckThinkMain._CheckType = 3 / 17`；`ThinkCondition {_IsActionEnd: False, _IsUnderLayerEnd: False, _NextStateID: 1}` 与 `{...False, _NextStateID: 2}` |
| combat_main | `ThinkCondition {_IsActionEnd: False, _IsUnderLayerEnd: False, _NextStateID: 2}`、`{_IsActionEnd: False, _IsUnderLayerEnd: True, _NextStateID: 1}`；`RegistActionTableInfo {_Category: 4, _TableNo: 65535}` |

主例程里 `_IsActionEnd` **全为 False**；`_NextStateID` 只有 1/2；`_TableNo` 只有 65535
（哨兵）。

对象引用部分（**不可信**）：
- `EnemyThinkData._StateList` = `[]` 或 `['ref:0x00000000']`；
- `ThinkState._ActionList` 含 `ref:0x4BCCF5F2`（main）、`ref:0x277CF536`（combat_main）
  等非索引值，与 `ref:0x00000001/00000002/...` 混杂。

**结论**：这 12 个新 JSON 全部 `partial=False`，但解析器只把对象引用 dump 成原始
4 字节 `ref:0x...`，**并未解析对象表**，因此 `_StateList` / `_ActionList` 无法还原成
「Hub → 具体池」的边。可信标量只有 `_NextStateID=1/2`、`_TableNo=65535`、
`_Category=4`、`_CheckType=3/17`、`_IsActionEnd=False`，它们不构成 15 池路由键。
⇒ **Hub→池因果链不可由静态标量建立**，P32:36「对象引用会失步、标量才可信」在此
得到印证；需依赖实机探针（v69 W4 12-hub routing 等）重建，而非继续抽静态文件。

### (d) action/combo 是否有疲惫专属待机 / 低威胁动作，能否支撑「疲惫喘息」：**未能证实**

8 个 action/combo JSON 实测：

- 字段名共 34 种：`_ActionNo`、`_ActionSpecify`、`_ActionList`、`_Condition`、
  `_ConditionList`、`_StateList`、`_TableNo`、`_Category`、`_NextStateID`、
  `_IsActionEnd`、`_IsUnderLayerEnd`、`_Ailments`、`_MotSeqUniqueFilter00/01/02`、
  `_motSeqFilterHashKey` 等 —— **没有任何 tired / fatigue / exhaust / pant / rest 命名**。
- em131 专属类：`Em131_00ActionSetAttack`、`Em131_00ActionSetMove`、
  `Em131_00ActionSetNormal`、`Em131_CheckActionAilment`、`Em131_CheckActionSpecify`、
  `Em131_CheckHeadPosSpecify`、`Em131_CheckHeadPosStatus`、`Em131_CheckSearchType`、
  `Em131_SetBreathTargetPos` —— 同样无疲惫语义类。
- `_TableNo` 实测 `0/1/3/4/5/6/7/8`；`_Category` 实测 `0`（action）/ `1`（combo）/
  `4`（注册表，main 标注）；`em131_combo_005.user.2.json` 有 **450** 个实例。
- 唯一含 "Breath" 的 `Em131_SetBreathTargetPos`（`em131_combo_005` 中 2 处，字段
  `v0_Enabled` / `v1_ID`）是**吐息攻击瞄准**（对应 em131 的 waterbreath / fire / ice /
  poison / web / sleep 等 shell 资产），**不是「疲惫喘息」**。

**结论**：这批 action/combo 文件里**没有可直接指认的疲惫专属待机或低威胁动作字段**，
静态证据不足以支撑「疲惫喘息」。要定性必须把 `_ActionNo` / `_Category` 映射到具体
动画 ID（不在这些 JSON 中）或靠实机观察。此项属**待定/推断**（第 7 节）。

---

## 6. 解析质量

| 数据集 | `partial` 情况 |
|---|---|
| 本次 12 个新 JSON（`out/rsz_main_json/`） | **0/12**（全部 `partial=False`），直接复核 |
| 此前 107 个旧 JSON（`out/rsz_json/`） | **60/107**（P32:36），直接复核 |

注意：即使新 12 个文件未触发 bad-count 中止，`ThinkState._ActionList` 仍出现
`ref:0x4BCCF5F2` 这类非索引值 —— 更准确的解释是「解析器只 dump 原始 4 字节引用、
未解析对象表」，**不能据此断言文件损坏**。P32:36 的实用结论不变：**只有标量可信，
对象引用不可作因果链定论**。`rise_hub_pool_scalars.json` 的 `causal_chain` 判定
（verdict = NO）针对 107 个旧 JSON，仍然成立。

---

## 7. 哪些结论仍是推断 (e)

以下为**推断或未证实**，不是本轮静态抽取能定论的，不要当实测数值使用：

1. 「疲惫时长运行时 `_AddTiredTime` 动态累加」——静态 `_tiredSec: 0.0` 是实测，
   运行机制来自实机探针推断。
2. `ref:0x4BCCF5F2` 等判为「失步/垃圾值」是对解析器输出的解释；新 12 个 JSON 实为
   `partial=False`，对象引用不可解读更可能源于「未解析对象表」，非文件损坏。
3. 15 池 `range1..5` 索引与 4 档 `_RangeDistance` / `_RangeKehaiAdd` 的对应关系未经证实。
4. `_Category` 0=action / 1=combo / 4=注册表 的语义是标注，非文件内自证。
5. `Em131_SetBreathTargetPos` 判为吐息攻击而非喘息，基于命名与同类 shell 资产的推断。
6. 具体 `_ActionNo` → 动画（是否低威胁 / 待机）未验证，故 (d) 无法证实或证伪。
7. 数值均来自 em131 单一怪种，跨怪种泛化未验证。

---

## 8. 产物清单与「现在能补多少」

| 产物 | 内容 | 状态 |
|---|---|---|
| `tools/extract_rise_targets.cmd` | 默认双绝对路径 + patch 双跑 + `--test` + mmap 的一键脚本 | 已更新（本 teammate） |
| `out/rise_target_extract_plan.md` | 本文：已完成真实抽取 + 实证结论 | 已更新（本 teammate） |
| `out/rise_hub_pool_scalars.json` | 107 个旧 JSON 的 12 Hub + 15 池 = 272 条标量观测 + 因果链结论 | 已产出（本 teammate） |
| `tools/audit_rise_scalars.py` | 生成上一行的可重复工具（两次运行字节一致） | 已产出（本 teammate） |
| `refs/_main_extract/` + `out/rsz_main_json/` + `out/rise_extracted_facts.json` | main 的真实抽取与解析结果（12 个） | 已完成（main） |
| `out/rise_107_hub_pool_main.json` | main 对 107 个旧 JSON 的汇总 | 已完成（main，与上行互补不冲突） |

**现在能补多少**：静态资产层面已补齐 —— 12 个 em131 二进制、12 个解析 JSON、
`range_data` 4 档数组、`stamina_data` 全部疲惫相关标量、action/combo 的表号与规模，
以及 107 个旧 JSON 的标量汇总。仍不能定论的只有第 7 节所列推断项（运行时疲惫机制、
对象引用语义、动作 ID → 动画映射、15 池索引对应关系、跨怪种泛化），这些**不是
「等 pak」能解决的**，需要对象表解析、动画 ID 映射或实机探针。

**重跑**：直接双击 `04_RiseAI/tools/extract_rise_targets.cmd`（或传主包完整路径作 `%1`），
即可从本机两个 pak 重新抽 12 个文件到 `refs/rise_target_unpack/` 并解析到
`out/rsz_target_json/`；`python 04_RiseAI/tools/audit_rise_scalars.py` 可随时重建
107 个旧 JSON 的标量汇总。
