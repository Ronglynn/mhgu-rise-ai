# P80 · 52 怪 Rise AI 静态资产全量抽取与三问定案（bulk-assets，v2 定稿）

**结论先行**：本报告为 **v2 重解析定稿版**（覆盖 v1 版）。补上 P77/P78「其它 52 怪未抽」缺口后，三条定案 **两条作废、一条作废/改判**：

- **P73「Rise 无几何阈值阶梯」作废**：`_RangeDistance` 255/255 是 4 元素严格递增的**几何距离阈值**，4 阈值切 5 区间（对应 `range1..5`），Rise 确有几何阈值阶梯；`[8,5,3,1]` 只是 `_range_hate_add_data` 仇恨参数（312/312 非单调）。
- **P78 ①「W2 路线 B 对错了层」作废/改判**：层没错；原判基于 em131 单怪 + 误把仇恨参数当阈值候选。
- **P78 ④「疲惫数据表级复刻否定」作废**：`_tiredSec` 61/78 非零（30~120 秒）、`_motRate` 60/78 非 1.0（0.8~1.0），em131 的 `0.0/1.0` 是特例。
- **③ 跨怪通用性**：结构/字段跨怪通用（支持通用规则），数值按怪配置（须参数化，不可硬编码单一常量）。

全程只读 + 新增文件；零实机、零部署、零插件源码改动。

---

## 1 · 抽取覆盖数与 v2 重解析

### 1.1 覆盖

| 项 | 值 |
|---|---|
| 主 pak | `re_chunk_000.pak`（32.2 GB）STEP1 EXIT=0 |
| patch pak | `re_chunk_000.pak.patch_001.pak`（4.4 GB）STEP2 `--override` EXIT=0（**未跳过**） |
| `--test` 预检 | EXIT=0；本地对同一 filelist 应用同一正则命中 **468** = 目标清单 468，EXTRA=0 / MISS=0 / 不含 em131 |
| patch 覆盖实证 | 日志 `out/bulk_main_unpack.log` / `out/bulk_patch_unpack.log`；文件 mtime 两簇（`20:13:47–51` 与 `20:13:53–54`，约 134 个落在 STEP2 时间窗） |
| 输出目录 | `refs/_bulk_extract/`（**新建**，未覆盖 `refs/_main_extract/`） |
| 正则 | 稳健版 `out/bulk_filter_regex.txt`：364 段、17 261 字符、段内不含 `|`（规避 `-f` 的「单正则 alternation / 多 pattern 分隔符」语义歧义）；枚举 52 个 id 精确排除 em131 |
| 实际文件 | **468** = `main` 78 + `combat_main` 78 + `range_data` 78 + `stamina_data` 78 + `act` 105 + `combo` 51 |
| 覆盖 | 52 怪，468/468，`missing=0`、`extra=0`、`em131=0`；核心 4 类全 variant 全量，act/combo 每怪 ≤3 样本（≤600 约束满足） |
| 禁改目录核对 | `refs/_main_extract/` 12 files、`out/rsz_main_json/` 12 JSON 保持原样；`plug/`、mods/、游戏目录未动 |

### 1.2 v2 重解析（本轮质量修正，替代 v1 结论）

parser-ref / team-lead 确认 v1 `out/rsz_bulk_json/` 的 468 JSON **252/468 含越界 ref、1899/24371 非法引用**，不作定论。故：

- 用新增 `tools/bulk_parse_v2.py`（import `tools/rsz_parse_v2.py` 的 `parse()`，不改任何工具源码）重解析全部 468 个原始文件 → **`out/rsz_bulk_json_v2/`**（468 JSON + `_diag_summary.json`）。
- **430/468 `diagnostics.parseOK=True`**；对象引用 `total=23844 / valid=23270 / invalid=574`（v1 为 1899/24371，v2 大幅修复）；`arrayCounts total=9078 / implausible=145`。
- 按类别 parseOK：`range_data 78/78`、`stamina_data 78/78`、`main 78/78`、`combat_main 78/78`、`act 79/105`、`combo 39/51`。
- **交叉验证**：main 的 `out/P80_v2_crosscheck_52monsters.json` 对 156 个 range+stamina 严格复核 `156/156 parseOK、tail=0`；`_tiredSec`/`_motRate` 分布与本报告 v1/v2 逐项一致。
- **parser-ref 全量背书**（`out/P80_object_ref_resolution.md` §8、`out/_v2_full_468.py`）：其在内存中用 v2 重跑全部 468 文件，得 `430/468 parseOK、438/468 tail=0`；`range_data`/`stamina_data`/`main`/`combat_main` 四类 **78/78 全 parseOK、0 非法引用**，且 range/stamina 的 v1↔v2 ref 序列逐项一致 ⇒ Q(a)/Q(c) **不受解析器选择影响**。

### 1.3 标量来源声明（哪些来自 v2 / 哪些不作定量依据）

| 结论 | 标量来源 | parseOK 状态 |
|---|---|---|
| (a) `_RangeDistance` / 仇恨参数 | `out/rsz_bulk_json_v2/` 的 **78 个 range_data** | **78/78 parseOK** |
| (b) `_TableNo` / `_ActionNo` | `out/rsz_bulk_json_v2/` 的 **act 79 + combo 39 = 118 个 parseOK 文件** | 118 个全 parseOK |
| (c) `_tiredSec` / `_motRate` | `out/rsz_bulk_json_v2/` 的 **78 个 stamina_data** | **78/78 parseOK** |
| em131 特例对照 | `out/rsz_main_json/`（只读，v1，仅作对照） | 不并入 52 怪定量 |

**不作定量依据**（仅用于结构/字段名统计，team-lead 要求的排除清单）：
- **38 个 `not parseOK`**：act 26 + combo 12（`out/rsz_bulk_json_v2/_diag_summary.json` 的 `not_parseOK_files`）。根因分解（parser-ref §8.2 修正）：**37 个模板缺类**（`fieldsComplete=false`，9 个未收录 typeId，主要 `0df87250`×25）+ **1 个 String 变长串模式**（`em007_act_001`，`fieldsComplete=true` 但 tail=332 / 14 非法 ref，根因是 RE Engine `String` 为内联 UTF-16 变长串而非 4 字节 ref，v1/v2 均误当 4 B）。
- **37 个 `fieldsComplete=false`**：act 25 + combo 12，完整路径在 `fieldsComplete_false_files`。
- **严谨口径**（parser-ref 提醒）：v1「`userdataCount=0` 即解析完全正确」只适用于 `range_data` / `stamina_data` 两类（即 Q(a)/Q(c) 实际数据源）；act/combo 另有模板缺类失步，且 `em007_act_001` / `em072_act_002` 出现「v1 非法 ref=0 却 partial 提前 break 丢字段」⇒ **不能把「非法 ref=0」当完整判据，一律按 `diagnostics.parseOK` 过滤**。
- v1 产物 `out/rsz_bulk_json/` **已弃用**（仅作对照）；`out/rise_bulk_facts.json` **已覆盖为 v2 定稿版**。

未改 `tools/rsz_parse.py`、`tools/rsz_parse_v2.py`、未覆盖 `out/rsz_main_json/`。

---

## 2 · 三问结论（v2 定稿）

证据总表 `out/rise_bulk_facts.json`（`quantitative_basis` / `questions` / `verdicts`），逐文件 JSON 在 `out/rsz_bulk_json_v2/`。

### (a) `range_data` 的 5 元素递增阈值数组 / `_RangeDistance` 是不是几何阈值 —— **Rise 有几何阈值阶梯，4 阈值切 5 区间**

- **`_RangeDistance`（78/78 parseOK 的 range_data）**：共 **255 处，全部 `len=4`，255/255 严格递增**（与 main v2 复核一致）。
  - 样例：`em001 [6,12,17,22]`、`em003 [5,10,18,25]`、`em004 [4.5,8,16,24]`、`em007 [8,13,19,26]`、`em020 [5,8,15,25]`…
  - **52 怪全部有 4 元素 `_RangeDistance`，49/52 数值元组不同**（按怪配置），但结构一律 4 元素严格递增。
  - 语义：4 个严格递增阈值 → 切出 **5 个距离区间**（对应 15 池 `range1..5`）⇒ **这就是几何阈值阶梯**。
- **原误判来源**：P78 仅看 em131 的 `[1,2,3,4]` / `[27,2,3,4]`（看似占位/非单调），并把 `[8,5,3,1]` 仇恨参数误当成阈值候选，得出「4 元素数组非单调 ⇒ 不是阈值阶梯 ⇒ Rise 无 5 档几何阈值」。全怪 v2 数据推翻。
- **`_range_hate_add_data`**：312 处（`len4` 309 / `len5` 3），**312/312 非单调**，样例 `[8,5,3,1]`、`[1,0,0,-2]`、`[0,0,-1,-2]`、`[3,2,1,0]` ⇒ 仇恨/气息**增量参数**，不是几何阈值。
- **`_RangeKehaiAdd`**：78 处全 `len4`，76 非单调、2 非降但非严格递增 ⇒ 气息参数。
- 全 parseOK 文件数值数组长度分布：`1:48, 2:2, 3:9, 4:649, 5:7, 6:2, 7:5`；`len=5` 数值数组仅 `_range_hate_add_data`(3) + `_EmTypes`(4)，**`len==5 且单调 = 0`**（阈值是 4 元素而非 5 元素，不代表没有阈值阶梯）。
- 证据：`out/rise_bulk_facts.json` → `questions.a._RangeDistance` / `_range_hate_add_data` / `range_data_per_file`；原始文件例 `refs/_bulk_extract/natives/stm/enemy/em001/00/user_data/em001_00_range_data.user.2`。

### (b) `_TableNo → _actionNo → 招式名` 中间映射能否建立 —— **不能完整建立，断点基于 v2 精确化**

- 基于 **118 个 parseOK 的 act/combo**：`_TableNo` = 文件自身编号 **118/118 全验证**；`_ActionNo` 在 90 个文件、值域 **1~5075**。
- v2 结构化 ref 字段计数：`_ActionTableInfo 236`、`_ActionList 502`、`_ConditionList 944`、`_StateList 833`、`_ReferenceThinkData 833` ⇒ 全是**文件内 instance index**，RSZ 无跨文件引用槽（parser-ref `P80_object_ref_resolution.md` §4①）。
- `_TableNo`（`EnemyBTAActionTableSet.RegistActionTableInfo`）与 `_ActionNo`（`EmXXXActionSetAttack/Normal/Move`）分属不同类/实例，**无标量外键逐行对应**，靠对象引用串联但对象图不含跨文件指针。
- **招式名文本层**：filelist 180 405 行里 enemy 目录 `.msg` = **0**、招式名文本候选 = **0**；enemy `motlist` 638 个全是 `emNNN_NN_XX.motlist.528` **编号文件**；全库 `message`(757 行) / `data/define/player/skill/*.msg` 均为 GUI / 玩家技能文本；v2 唯一 name 类字段 `_partsNames`(2，部位名)。
- ⇒ 完整映射**不能建立**，可建仅「表号 = 文件号」一跳。P78 §7 该待办**维持未关闭**，断点由「未抽取」精确化为「文本层缺失 + RSZ 无跨文件引用 + 两类字段无标量外键」。
- 证据：`out/rise_bulk_facts.json` → `questions.b`（`structured_ref_field_counts`、`filelist_evidence`、`sample_TableNo_ActionNo`）。

### (c) `_tiredSec` / `_motRate` 是否跨怪恒 0.0/1.0 —— **否，P78 ④ 作废（翻案）**

78 个 `stamina_data`（78/78 parseOK）：

- `_tiredSec`：**`0.0` 仅 17/78**，非零 **61/78**，12 种值 **30~120 秒**（`60×29, 90×9, 80×7, 45×4, 40×3, 50×2, 70×2, 120×2, 30/75/100 各 1`）。
- `_motRate`：**`1.0` 仅 18/78**，其余 **60/78** 为 **0.8~0.98**（7 种值 `0.9×28, 0.92×15, 0.95×9, 0.85×5, 0.98×2, 0.8×1`）。
- `tired|fatigue|rest` 命名字段（v2 全文件）：`_tiredSec`(78) + `_hyakuryuTiredSec`(78) + `isTiredDisable`(1)。后者在 `em025_combo_001` 的 `snow.wwise.fsm.action.WwiseSituationVoiceEvent`、**`parseOK=False` 不作定量依据**、且为语音事件开关非招式名；**parseOK 的 act/combo AI 字段仍无 tired 命名**（P78 §3(d) 在定量集内成立）。
- em131 只读对照（`out/rsz_main_json/`，未改动）：`_tiredSec=0.0 / _motRate=1.0 / _hyakuryuTiredSec=0.0` ⇒ **17/78 的默认值特例，不是跨怪常量**。
- 证据路径：`refs/_bulk_extract/natives/stm/enemy/em001/00/user_data/em001_00_stamina_data.user.2` → `_tiredSec=60.0, _motRate=0.92`；`.../em002/00/user_data/em002_00_stamina_data.user.2` → `80.0 / 0.92`。
- 证据：`out/rise_bulk_facts.json` → `questions.c`；`out/P80_v2_crosscheck_52monsters.json`（v2 逐项一致）。
- ⇒ **P78「疲惫数据表级复刻否定」作废**：Rise 侧疲惫表真实存在且按怪配置；GU 侧「四条纪律 / 落盘层无 1:1 复刻通道」的结构性结论另论、不受本次数据影响。

---

## 3 · 对三条定案的影响（v2 定稿）

### ①「W2 路线 B 对错了层」（P73 §6 / P78 §3、§7①）—— **作废 / 改判**

- 原判依据：Rise `range_data` 只有 4 元素仇恨/气息参数、无 5 档递增几何阈值 ⇒ 「编译 137 张 dttune 表对齐 Rise 5 档」对错了层、结构性不值得、从待办移除。
- v2 全怪推翻：`_RangeDistance` **255/255 严格递增 4 阈值 = 几何阈值阶梯**（4 阈值切 5 区间，正好对 15 池 `range1..5`）；`[8,5,3,1]` 只是 `_range_hate_add_data` 仇恨参数（312/312 非单调）被误当阈值候选；em131 `[1,2,3,4]`/`[27,2,3,4]` 是单怪特例。
- ⇒ **层没错**：**P73「Rise 无几何阈值阶梯」作废**、**P78 ①「对错了层」作废/改判**。
- **边界（不过度外推）**：路线 B 的其它障碍仍在 —— P77 §3.5 斩龙 `em080_00/04` `rangeRows=0`、18/137 怪无阈值行、GU 侧四条纪律、零实机验证。**改判 ≠ 立刻恢复路线 B 待办**，是否重启须另行评估。

### ②「疲惫数据表级复刻否定」（P77 §2(c) / P78 §7④）—— **作废**

- 原定案用 em131 `_tiredSec=0 / _motRate=1` 断言「Rise 疲惫时长运行时动态累加、非静态可复刻、无需表级复刻」。
- Q(c) 证伪：Rise 侧疲惫表**真实存在且按怪配置**（30~120 秒、0.8~1.0），61/78 非零、60/78 非 1.0；em131 是 17/78 的默认值特例。是 em131 单样本外推到全怪的错误泛化。
- ⇒ 「Rise 侧无静态疲惫表 / 数值恒定占位」的断言**作废**，定案改写为「**Rise 侧疲惫表存在且跨怪可变；GU 侧四条纪律 / 落盘层无 1:1 复刻通道（原结构性结论维持）**」。

### ③「跨怪通用性」（硬约束：通用规则、不硬编码 action_id / 怪种数值）—— **结构通用强支持，数值按怪参数化**

- **支持**：52 怪 `_RangeDistance` 全部 4 元素严格递增（255/255）、字段名一致（`_tiredSec`/`_motRate`/`_hyakuryuTiredSec`）、`_TableNo`=文件号 118/118 ⇒ Rise 侧 AI 数据表**结构跨怪通用**，与「用通用规则而非按怪硬编码」方向一致。
- **边界**：52 怪中 49/52 `_RangeDistance` 元组不同、`_tiredSec` 12 种值、`_motRate` 7 种值 ⇒ 通用性应落在**结构/规则层**，须按怪参数化，不能把单一数值常量当通用。
- 注意：本报告是 **Rise 静态资产参照侧**证据；GU 插件干预点的跨怪通用性仍以实机（P79 `sp=0052` 泡狐龙等）为准，不直接外推。

---

## 4 · 附带关闭 / 推进的待办

- ✅ P77 §4 / P78 §5 / `P80_object_ref_resolution.md` §6 的「其它 52 怪未做全量」缺口**关闭**。
- ✅ P73「Rise 无几何阈值阶梯」、P78 ①、P78 ④ 按 §3 作废/改判。
- ✅ Q(b) 把 P78 §7「中间映射仍缺」断点精确化（v2 结构化 ref 仍是文件内 index + 文本层 0 命中）。
- ✅ v1 失步数据弃用，全怪定量结论改由 v2 `parseOK` 文件支撑。
- 与 parser-ref 分工：对象引用修复（`tools/rsz_parse_v2.py` / `P80_object_ref_resolution.md`）不在本报告范围；其 §4 结构性结论与本报告标量结论互补。

---

## 5 · 诚实边界

1. v2 仍有 **38 个 `not parseOK` / 37 个 `fieldsComplete=false`**（集中 act/combo）：根因 **37 个模板缺类 + 1 个 String 变长串模式（`em007_act_001`）**，均**不作定量依据**；定量结论只取 430 个 `parseOK` 文件，其中 (a)(c) 的 range/stamina 全部 78/78 干净。
2. `isTiredDisable`(1) 来自 `parseOK=False` 的 Wwise 语音事件文件，不作定量、非招式名。
3. `motlist` / `message` 只查 filelist **文件名层面**：enemy 目录连 `.msg` / 招式名文本表文件都不存在；若招式名藏在 `.motlist.528` 二进制内容里按编号索引，需另抽解析（本轮未做），但「文本层文件名 0 命中」已足以判定映射链缺最后一跳。
4. 全部为**静态资产复核，无 Rise 实机 / 反汇编**（沿用 P32:201 证据等级）。
5. 未改插件源码、未编译 NRO、未部署、未动 `plug/`、mods/、游戏目录、`refs/_main_extract/`、`out/rsz_main_json/`、`tools/rsz_parse.py`、`tools/rsz_parse_v2.py`。
6. **为什么不修复这 37 个排除文件**（parser-ref `out/P80_object_ref_resolution.md` §8.7、`out/_probe_unknown_skip.py`）：「未知类实例统一占 S 字节」容错实验仅 **11/37（29.7%）** 能达 parseOK 且 tail=0，26 个仍修不好（多未知类实例使统一 S 假设失效，叠加 §8.6 String 变长字段）⇒ 本轮**不补 `refs/rszmhrise.json`**（9 类缺完整字段布局：二进制只能反推字节长度、推不出字段名/类型；改 66 MB 共享模板会动所有人解析基线；且这些文件已排除，收益为零）、**不扩展 v2 缺类容错**（会让已定稿的 468 份产物与工具版本不一致，且不改变任何定案）。保持按 `parseOK=false` 排除口径。未来线索：最佳 S=**28** 在 10 个文件重复出现，暗示 `0df87250` 类数据长约 28 B，可供将来拿到类型库时补模板。

---

## 6 · 产物清单

| 类别 | 路径 |
|---|---|
| 原始 `.user.2`（468） | `refs/_bulk_extract/` |
| **v2 解析 JSON（468）+ 诊断** | `out/rsz_bulk_json_v2/`、`out/rsz_bulk_json_v2/_diag_summary.json` |
| v1 解析 JSON（468，弃用/对照） | `out/rsz_bulk_json/` |
| **三问汇总（v2 定稿）** | `out/rise_bulk_facts.json` |
| 规划 / 正则 / 统计 | `out/bulk_target_paths.txt`、`out/bulk_filter_regex.txt`、`out/bulk_plan_stats.json` |
| 抽取日志 | `out/bulk_test.log`、`out/bulk_main_unpack.log`、`out/bulk_patch_unpack.log`、`out/bulk_unpack_summary.txt` |
| 可复现脚本 | `tools/bulk_extract_plan.py`、`tools/bulk_parse_and_facts.py`（v1）、**`tools/bulk_parse_v2.py`、`tools/bulk_facts_v2.py`（v2 定稿）** |
| 本报告 | `out/P80_bulk_monster_assets.md` |

复现：
```bat
python tools\bulk_extract_plan.py
ree-pak-cli.exe unpack -p <MHR_STM_Release.list> -i <主 pak>   -o refs\_bulk_extract -f <bulk_filter_regex.txt> --backend mmap --override --skip-unknown
ree-pak-cli.exe unpack -p <MHR_STM_Release.list> -i <patch pak> -o refs\_bulk_extract -f <bulk_filter_regex.txt> --backend mmap --override --skip-unknown
python tools\bulk_parse_v2.py
python tools\bulk_facts_v2.py
```
