# P78 · 「把能做的全做了」离线总交付（目标对齐后的最大推进）

用户 18:20 要求「把你能做的全做了」，18:24 要求并行推进。本文件汇总本轮**全部离线产出**：4 个并行子任务 + main 亲自执行的真实抽取。**零实机轮次、零部署变更**。

## 0 · 一句话

**找到了此前被判定「不在本机」的 32 GB Rise pak，把 P32 §7 列为最高价值的静态资产真实抽出并解析，由此改写 5 条旧定案；同时编译出成品候选 NRO（未部署）、完成纪律重评、领地争夺目标层定位、目标对齐矩阵。** 下一场实机仍是唯一一场，待验项没有增加。

## 1 · 并行执行（回应用户「不派多个子 agent 同时进行吗」）

| 子任务 | 产物 | 状态 |
|---|---|---|
| `asset-prep` | `tools/extract_rise_targets.cmd`（绝对路径双 pak）、`out/rise_target_extract_plan.md`、`out/rise_hub_pool_scalars.json`（272 标量）、`tools/audit_rise_scalars.py` | ✅ |
| `discipline` | `out/P73_discipline_review.md`（26 KB）、`out/dist_bands_rust.rs`（41 KB 草案）、`tools/make_dist_bands_rust.py` | ✅ |
| `territory` | `out/P74_territory_target_layer.md`（20 KB）、`tools/audit_p74_target_layer.py` | ✅ |
| `release` | `out/rai_release_candidate.nro`、`out/P75_release_candidate.md` | ✅ |
| **main 亲自** | `refs/_main_extract/`（12 个原始 `.user.2`）、`out/rsz_main_json/`（12 JSON）、`out/rise_extracted_facts.json`、`tools/extract_rise_facts.py`、`out/rise_107_hub_pool_main.json`、`tools/audit_rise_107_main.py`、`out/P76_goal_alignment_matrix.md`、`out/P77_rise_extracted_facts.md` | ✅ |

## 2 · 五条被改写的旧定案（本轮最核心成果）

| # | 旧定案 | 实证修正 |
|---|---|---|
| 1 | `re_chunk_000.pak` 不在本机 ⇒ P32 §7 缺口需外部数据源 | **翻案**：`D:\Steam\steamapps\common\MonsterHunterRise\re_chunk_000.pak`（32.2 GB）+ patch（4.4 GB）就在本机；工具链齐全，已真实抽取 12 个 em131 资产 |
| 2 | `*_main.user` 主例程 0 个，Hub→15 池因果链无字段证据 | 抽到 `em131_00_main` / `em131_00_combat_main` 并可解析；`ThinkCondition._IsActionEnd` 全 False、`_NextStateID` 1/2/14/8 等。但 `_ActionList` 对象引用失步（`ref:0x4BCCF5F2` 垃圾值）；对拍 107 JSON 得 **Hub 与池仅共享 `TableNo=0`** ⇒ 标量仍建不出因果链，「W4 12 Hub 1:1 不可做」从推断升级为实证 |
| 3 | `range_data` 未抽取 ⇒ 无 Rise 5 档几何阈值 | 抽到后实测：距离档是 **4 档**（`_RangeKehaiAdd=[8,5,3,1]`、`_range_hate_add_data=[8,5,3,1]`、`_RangeDistance=[1,2,3,4]/[27,2,3,4]`），**没有 5 档递增阈值**；15 池 `range1..5` 是另一套池索引 ⇒ W2 路线 B「编译 137 表对齐 Rise 5 档」**对错了层**（P73 §6） |
| 4 | `_tiredSec` / `_motRate` 实例数值未解包 | 实测 **`_tiredSec=0.0`、`_motRate=1.0`** ⇒ 疲惫时长运行时动态累加、非静态可复刻；4 组 `PointData{100,1000}` 实证 |
| 5 | 领地争夺「Rise 侧无专属机制」只是推断 | `EnemyStaminaData.PredatorData {_IsPredator:0, _EnableRadius:400.0, _EmTypes:[0], _ActionStance:0}` **代码级实证**：Rise 有掠食者参数层；GU 侧全库检索**无等价 `PredatorData`/`_EmTypes` 类或 137 槽怪种枚举**（`spec-crossgame/monster-gu.md:398,459`）⇒ P74 二次修订把结论升级为 **「结构性不可复刻」[C] 定案**，独立于且不再挂在「目标点身份未定案」上 |

## 3 · 四个子任务的最终判断

- **纪律（P73，已按实证定稿）**：三条自定纪律（禁按怪种编译表 / 禁查表 / 只在抽选层）**可以放宽且不违反零写入、不整包重封 arc**；但 W2 路线 B 从「当前证据下不值得」**下调为「结构性不值得 / 对错了层」，建议从待办移除、不再安排实机**。硬证据：全文件数组长度扫描显示 `range_data` **没有任何 5 元素数值阈值数组**（唯一 5 长度是 `fields` 元数据），4 元素数组 `[27,2,3,4]`/`[8,5,3,1]`/`[3,2,1,0]` 非单调 ⇒ 不是阈值阶梯；GU dttune 4 档（距离 matcher）与 Rise `EnemyRange` 仇恨/气息参数是两个不同数据源，不能互替；斩龙 `em080_00/04` `rangeRows=0` 且 `candidateCount=0`；v71 探针版 `.rodata` 仅余 1608 B / `.text` 88 B。产物 `dist_bands_rust.rs`（bits 5758 B / int 3118 B、119 怪、330 行、1320 单元）保留为未来资料。
- **领地争夺（P74，二次修订）**：**主结论 = 结构性不可复刻 [C] 定案**（Rise 有 `PredatorData` 参数层、GU 无等价类/表且无 137 槽怪种枚举），不再依赖 P36 §2.4 第③步。「目标点是否只指向猎人」作为**独立支线保留为 [I]/[U] 未定案**：v69 单场仅 1 只大怪，`+0x30` 组是全场 3 个固定静态锚点、`+0x40` 组逐条变化、距离单峰无两簇、`COMBO.sp` 是自身怪种不承载目标信息。最小只读探针可在 6 hook 内加行，但**更不值得并进下一场**（主问题已定案 + 需两只大怪同区任务 + 需重编译）。
- **成品（P75）**：`out/rai_release_candidate.nro`，md5 `dfab157dea8e9448780e6ecdbd82aafd`，61440 B，6 detour；`Z/AE/COMBO/AR/J/B2` 特征串全 0、`S2/HB` 保留；`W2_PROBE=0`、`MAX_QX=400`（关键：`STANCE_CUR/F` 在 QX 分支内，置 0 会让 W4 处境维静默失效）。**未部署**，部署点仍 v71 `1d513ec3364f4f270929fd24193ff74b`。
- **抽取就绪（asset-prep）**：一键脚本把 pak 路径写死为本机 Rise 安装目录、主包 + patch 包两步 `--override`、含 `--test` 预检与 mmap；标量汇总覆盖 107 个已解包 JSON 的 **272 条观测**，结论「Hub→池因果链不可由标量建立」（Hub `_TableNo` 仅 `{0,65535}` 哨兵，池交集也只有哨兵；`_NextStateID=80 ↔ 池 _TableNo=80` 是状态 ID/表号语义错配的巧合）。计划文档已改为「已完成真实抽取」，`(a)~(e)` 五问全部作答：`(d)` action/combo 34 种字段**无任何 tired/fatigue/rest 命名**，`Em131_SetBreathTargetPos` 是吐息攻击瞄准而非疲惫喘息 ⇒ 静态证据不足以支撑「疲惫喘息」。

## 4 · 目标对齐的最终状态（P76）

| Rise 层 | 现状 | 本轮变化 |
|---|---|---|
| L0 装配 / L1 FSM | 空白 | 无变化（GU 引擎层，够不到） |
| L2 处境 Hub | W4 机制级 3×4 | **「1:1 不可做」升级为实证**（主例程抽到 + 标量对拍无共享 TableNo）；**领地争夺升级为结构性不可复刻 [C] 定案** |
| L3 门控 | W3 已关闭 | 主例程 `_IsActionEnd` 全 False，门控 True 只在 12 Hub；GU 无可拦窗口未变 |
| L4 状态×距离池 | W1+W2 机制级 | **路线 B 结构性不值得、从待办移除**：Rise `range_data` 实测 4 档仇恨/气息参数、全文件无 5 元素阈值数组、斩龙 `rangeRows=0` |
| L5 条件检查 | prev 表近似 | 无变化 |
| L6 加权抽选 | **高（同构）** | 107 JSON 对拍确认 89/89 池率和恒 100、44 TC 中 12 True |
| L7 执行 | 空白 | 抽到 action/combo 的 `_TableNo` 0/1/3/4/5/6/7/8，文件名级映射可建，`TableNo→_actionNo→招式名` 中间表仍缺 |

## 5 · 诚实边界（仍未补上的）

- 只抽了 **em131 一只怪**的 12 个文件；其它 52 个 emNNN 的 `_main` / `stamina_data` / action / combo 未做全量（路径表可查）。
- 15 池 `range1..5` 的物理阈值数值仍无来源（不在 `range_data` 里）。
- `ThinkState._ActionList` / `_ConditionList` 对象引用失步 ⇒ Hub→池因果链仍不能定案。
- `actiontune / motion / message` 类文件未抽；`_TableNo → _actionNo → 招式名` 中间映射仍缺。
- 全部为**静态资产复核，无 Rise 实机 / 反汇编**（沿用 P32:201 的证据等级声明）。
- 疲惫喘息 / 输出窗口放大：现有四条纪律下仍不可定量复刻，但按 P72 §6 已更正为「不作无期限排除」。

## 6 · 不变的边界与下一场

- 未改插件源码（`lib.rs` 仍 v71）、未部署、未动 `6_启动并抓日志.bat`（md5 `7361445f…`）、`load_order.txt`、音频 mod、游戏资源。
- **下一场仍是唯一一场**：双击 `run_v66.cmd` 用 v71 探针版验收 W4 分流、日志完整性、跨怪 `sp`、W1/W2 回归、零异常；**待验项没有增加**。
- 验收通过后，按 `out/P75_release_candidate.md` / `out/release_profile.md` 部署成品版；异常则编译期开关回退，无需另打验证。

## 7 · 最终关闭状态（19:00）

四个子任务全部完成并二次修订到位，过时结论已清理（残留「未抽取 / 必须等 pak」字样均为**引用旧定案并注明已失效**的对照句，非自相矛盾）：

- ✅ P73 纪律重评定稿（§4.5 实证 + §6 导航注）、P74 领地争夺二次修订（§5.5/§5.6 + 主结论升级）、P75 成品候选编译校验、asset-prep 一键脚本与标量汇总收尾。
- ✅ P76 目标对齐矩阵、P77 抽取实证、P78 本汇总；`refs/_main_extract/` 12 原始文件、`out/rsz_main_json/` 12 JSON 齐全。
- ✅ 部署点仍 v71 `1d513ec3364f4f270929fd24193ff74b`；`lib.rs` 未被任何子任务修改（release 用临时目录 `_release_build` 编译）；`6_` md5 `7361445f…` 未变。
- ✅ 全程零实机轮次、零部署、零游戏资源改动。

**由本轮实证新关闭的待办**：① W2 路线 B（结构性不值得，移除）；② 领地争夺（结构性不可复刻，定案）；③ 「pak 需外部数据源」（翻案，已抽完）；④ 「疲惫喘息数据表级可复刻」（`_tiredSec=0` + action/combo 无疲惫命名 ⇒ 否定）。
**仍未关闭**：15 池 `range1..5` 背后的几何阈值定义、`TableNo→_actionNo→招式名` 中间映射、对象引用解析（需干净二进制或实机探针）、其它 52 只怪的全量资产、Rise 实机/反汇编。
