# P74 · 领地争夺「目标层」定位报告：距离档目标点是否只指向猎人

日期：2026-11-15 · 只读分析，未改插件源码 / 未编译 NRO / 未部署 / 未改任何 .bat/.cmd / 未改 NOTES.md / 未改 out 下已有 P*.md。
本轮新增文件仅两份：`out/P74_territory_target_layer.md`（本文）与 `tools/audit_p74_target_layer.py`（离线统计脚本，只读日志、不写文件）。

任务来源：`P36 §2.4` 第③步「W2 matcher 探针判定距离档的『目标点』是另一只大怪还是猎人 —— 若只指向猎人，则引导部分正式判不可行」**从未执行**；`P76 §3 P1 / §4 第 3 点 / §6` 把「把推断升级为结论或明确证据缺口」列为本轮子任务。

---

## 0 · 结论摘要（18:45 二次修订：纳入 Rise PredatorData 实证并升级结论框架）

1. **领地争夺「不可复刻」已由一条独立的结构性证据定案（[C]）**：Rise `em131_00_stamina_data.user.2` 实测解析出 `snow.enemy.EnemyStaminaData.PredatorData`（`_IsPredator` 开关 / `_EnableRadius: 400.0` / `_EmTypes[]` 目标怪种表 / `_ActionStance` 处境，挂在 `EnemyStaminaData._PredatorDataInfo` 下）⇒ **Rise 侧「双怪互打」确有其机制参数层**（此前只有公开资料推断）；而 GU 逆向库**全库检索无等价类/表**（详见 §5.6）⇒ **Rise 有、GU 无 ⇒ 领地争夺属结构性不可复刻**。该定案**独立于、且不再挂在**「距离档目标点身份未定案」上。
2. **「距离档目标点是否只指向猎人」仍为推断、未定案**（P36 §2.4 第③步从未执行；本轮离线统计仍无法定案）。它现在降为一条**独立支线**：只影响「纯只读引导互攻」这一分支是否还有讨论空间，**不影响第 1 条的定案**；其证据等级判定完整保留于 §2(a)(c)(d) 与 §5。
3. **本轮离线统计给出的是「否定性/间接」证据，而且其中一条反而不利于朴素假设**：现有 v69 日志已采到 matcher 用的两组几何坐标（`sub+0x30..0x38` / `sub+0x40..0x48`），实测 `+0x30` 组是**每实体固定的静态锚点**（全场 67 条仅 3 个唯一值），`+0x40` 组逐条变化；全场只有 **1 只可识别大怪**，几何距离**单峰无两簇**、**跨 mon 无目标点对应**。`COMBO.sp` 是动作实体自身怪种字、**不承载目标信息**。
4. **最小探针可在现有 6 hook 内追加只读观测行完成（零新增 hook、零写入），但当前更不值得并进下一场**：主问题已由第 1 条定案，探针只剩支线学术价值；下一场是 v71 单大怪验收场（P76 §4 第 5 点「待验项不增加」），且需先做静态定位（玩家坐标 / `target_*` offset）+ 一场「两只大怪同区」任务才有定案数据。

---

## 1 · 证据分级口径

沿用 `re-guide-gu.md:41` 的标记法，并映射到本任务要求的三档：

| 档 | 标记 | 含义 |
|---|---|---|
| **有代码级证据** | [C] | 反汇编/字节级确证，或 `W4-REFERENCE.md` 复算 CONFIRMED 的锚点 |
| **有实机证据** | [实机] | 本轮只读日志统计 / 历轮实机日志可复算数字 |
| **仅为推断** | [I] / [U] | [I] 推断、[U] 未证/未定案（含「字段名存在但语义未验证」） |

凡 [C] 只证明「代码读了什么」，不自动证明「读到的实体是谁」；本报告严格区分这两层。
补充：Rise 侧 RSZ 资源**类结构 + 字段数值**（如 `PredatorData`）同属 [C] 代码级实证，高于 P36 §2.1 的「公开资料中等可信」。

---

## 2 · 分问回答 (a)~(e)

### (a) `0x8E144` 的 target 点来自哪；`sub+0x30..0x38` / `+0x40..0x48` 各自实体归属有没有定案

**[C] 代码级（已定案的部分）**

- matcher 签名 `0x8e144(ctx, ip, op, mode, value)`；`ctx` = 解释器 `0x82f80` 第 1 参（r8），`sub = [ctx+0x1428]`。锚点经 `W4-REFERENCE.md:71,150,320,372-373` 字节级复算 CONFIRMED；`re-guide-gu.md:27,50` 亦把 `+0x1428` 记为敌人 act 子对象（HP 在 `X+0x370`）。
- 距离类 block op（`emc.md:42-48`）：`0x0b`(mode4) / `0x17`(mode6，3D 距离 `[sub+0x30..0x38]` vs `[sub+0x40..0x48]` @`0x8e394`) / `0x57`(mode14) / `0x5c`(mode16，XZ 距离 @`0x8e434`) / `0x7c`(mode24，六 float 最小)。
- 比较逻辑（`emc.md:54-58`）：mode 5/6/7/15/16/… 阈值 = case 操作数 ×100，按 `distance <= threshold` 顺序命中；mode 4/14/21/22 阈值来自 `0x71164(ctx, slot)` 的 dttune float 表（**在另一个文件、不在 EMC 表内**），距离是「自身 + heading 旋转偏移的点」。
- 插件侧确证：`lib.rs:2060-2078` 中 `h_matcher(a0..a4)` 把 `a0` 当 `mon/ctx`，`lib.rs:1960-1980` 在 `dist_probe()` 里读 `sub=rd(mon+0x1428)` 并快照 `a30/a34/a38 = sub+0x30/34/38`、`a40/a44/a48 = sub+0x40/44/48`、`hd = sub+0x54`、`cmd = mon+0x2588`。即 **ZP 探针已经采到了判定所需的那两块内存**。

**[U] 未定案的部分（核心）**

- `emc.md:51` 原文：「Which entity `sub+0x30` and `sub+0x40` belong to (enemy vs hunter) **is not proven [U]**; the pattern fits target position and own position **[I]**」。
- `emc.md:63`：「no opcode found that reads them; the geometric switch ops above test distance only … modes 4..25 read positions and `[sub+0x2e8..0x304]` only」——即 matcher 内**没有**任何「目标实体 ID / 枚举另一只怪」的读取。
- `emc.md:18` §2「section index → AI state 映射 [U]」、`mon-ai-entry.md:253`「**AI 决策层（选招、目标选择、距离/朝向判定）尚未定位**」。

**结论 (a)**：两组偏移被读取并参与距离比较是 [C]；**哪组是「自身」、哪组是「目标」、目标属于哪个实体，全部 [U] 未定案**。本轮实测（见 §3）还发现 `+0x30` 组是静态锚点，进一步说明不能简单套用「一组=猎人实时位置」的 [I] 假设。

### (b) 有没有「枚举另一只怪 / 选另一只怪作目标」的 opcode 或字段

| 面 | 结论 | 等级 |
|---|---|---|
| EMC opcode 集 | `emc.md:38-50` 全部 block op 是「状态字节 / 距离 / 六距最小」switch；`emc.md:63` 明确未发现读取视锥/听觉/角度锥的 op。**已知 opcode 集里没有「枚举/选另一只怪」op** | [C]（但这是「本次逆向覆盖范围内未发现」，非全镜像穷尽证明；`emc.md §6` 自列 Open items） |
| 动作名闭集 | `mon-ai-entry.md:233` 13 类（FwMove/MoveMove/AttackMove/…/DemoMove），**无 versus / turf 类**（P36 §2.2 引用） | [C] |
| 反射字段名 | `monster-ai-params.md:50-67,116-129` 列有 `mParam.target_selID[i]`、`target_type[i]`、`target_sel[i]`、`target_id`、`sysSendData.q_target_type`、`tar_param[i].id/.num/.max` —— **名字存在**（rodata 字符串，`W3-MEMBERS` 复算 131 个 `mParam.`，`monster-ai-params.md:26`） | [C]（仅「存在」） |
| 字段名 → 语义 | `monster-ai-params.md:3-5` 自述「**不含 offset/size**；offset 需通过注册函数反推」；`mon-ai-entry.md:253` 决策层未定位 | [U] |
| Rise 本地资源（**已翻案**） | P36 §2.1 曾记 `TurfWar/turf/Turf/Turfbattle` 0 命中 ⇒ 当时判「本地 Rise 资料不足以实证复刻」；**本轮追加实证**（P76 §3 P0：pak 已定位并抽出）`em131_00_stamina_data.user.2` 含 `EnemyStaminaData.PredatorData`（`_IsPredator/_EnableRadius/_EmTypes/_ActionStance`，见 §5.5、§5.6）⇒ **Rise 侧双怪互打机制确有其参数层**。旧「0 命中」只是关键词不对（真名 `Predator/掠食者`，藏在 `stamina_data` 里），不是机制不存在 | [C] 代码级实证（RSZ 类+数值） |

**结论 (b)**：**GU 侧仍没有定案**（既没有确证「存在可用字段/语义」，也没有「穷尽证明不存在」；`target_*[i]` 名字存在 ≠ 能选另一只怪作目标，仍是 [U]）。**Rise 侧则已 [C] 实证存在** `PredatorData` 参数层（含 `_EmTypes` 目标怪种表与 `_EnableRadius` 半径）——两侧合起来正是 §5.6「Rise 有、GU 无」的结构性差异。

### (c) 反射字段 `mParam.target_type` / `sysSendData.q_target_type` 的语义是否已验证

**[C]**：字段存在，`monster-ai-params.md:61,64-66,126` 给出 vaddr（`0x1559922` / `0x1559c37` / `0x1559db4` / `0x1559dc7`）。

**[U]**：语义**完全没有验证** —— 取值范围、各值代表什么、是否区分「猎人 / 另一只怪」、是否就是距离档目标点，均无运行时取值或反汇编绑定。本轮对 `04_RiseAI/NOTES.md`（474 KB）全文检索 `target_type|q_target_type|target_selID|target_id|目标点|目标层` **0 命中** ⇒ 工程从未读过这些字段的运行时值。`monster-ai-params.md:3-5` 明说名字表不含 offset/size，故连「在结构哪个偏移」都未定。

**结论 (c)**：**仅字段名存在，语义未验证**。

### (d) 现有实机日志能否间接判断目标点身份

**数据源盘点 [实机]**：只有 `02_Workspace/game_p54_lite.txt`（v69，11368 行）含 Z/ZP/AR/QX/COMBO；**28 个 `04_RiseAI/out/game_p54_lite_*.txt` 归档 + 旧 `02_Workspace/game_p54.txt` 系列日志 ZP=0**（ZP 探针自 v58 才加入，归档都更早），几何分析只能用 v69 单场。旧 `game_p54.txt`(v38) V 行 sp = `{0025, 100D, 1022, 1023, 1027}`，也是 1 个低位怪种 + 多个 `0x10xx`。

**逐项回答 team-lead 的举例**：

- 「`COMBO.sp` 是否随目标切换」→ **否，且不能用**。`lib.rs:2367-2368, 2580-2582, 2607-2611` 中 `sp = rd16(a0+0xB5F0)`，`a0` 是**发动作的实体自身**；`sp` 是「自身怪种/类型字」，**不是目标标识**。主日志 V/COMBO/AR 的低位(<0x1000)大怪怪种 sp 值域 = **仅 `{0050}`（斩龙）**，其余 `1008/101B/102F` 是「其它对象」（`P70:5,75`、`NOTES:6168` 定性）。⇒ **`COMBO.sp` 完全不承载目标信息，不能用来判定目标身份**。
- 「多怪同场时 ZP 几何距离是否出现两个不同簇」→ 本场 **没有两簇**：67 条 `|a40-a30|` 3D 距离 42.4~5861.4（p50 1623），最大间隙切分 `gap_ratio=0.086`，直方图连续单峰。但**这是单大怪场的真空证据**（没有另一只怪可切，距离本来就不会分两簇），不能反推「只指向猎人」。
- 「ZP 几何距离跨 mon 对应」→ `a40(A)~a30(B)` / `a30(A)~a40(B)` / `a40(A)~a40(B)` **全部 0 命中**（tol=1.0），仅 `a30(A)~a30(B)` 命中 6 对（共享固定锚点）。即**没有「某实体目标点 = 另一实体自身位置」的证据**——但同样受限于单大怪样本。

**结论 (d)**：**不能定案**。现有日志能给的只有否定性/间接证据，且缺三样决定性真值：① 猎人/玩家坐标；② `target_type/target_id/target_selID` 运行时值；③ 两只大怪同区同时间窗样本。另外 `a30` 是静态固定点这一实测，**反而不支持**「两组之一是猎人实时位置」的朴素图景（见 §3）。

### (e) 最小只读探针一锤定音需要采哪些字段、能否并进下一场

**判据（一锤定音）**：在**两只大怪同区**时，判定「距离 matcher 的目标点」是 (α) 恒等于猎人坐标、还是 (β) 曾等于另一只大怪的坐标/自身锚点。α ⇒ 「只指向猎人」成立、(a) 的引导部分正式判不可行；β ⇒ 目标层不封死。

**必需字段（全部纯只读，可在现有 6 hook 回调里追加观测行/字段）**：

| # | 字段 | 用途 | 前置 |
|---|---|---|---|
| 1 | `mParam.target_type` / `target_id` / `target_selID[i]` / `sysSendData.q_target_type` 运行时值 | 直接给出目标实体身份/类型 | **需静态定位 offset**（`monster-ai-params.md:3-5` 未定），非新增 hook |
| 2 | 玩家/猎人坐标真值（3×f32，每条 ZP 时刻或每帧） | 把 `a30`/`a40` 任一组绑定到「猎人」 | **需静态定位玩家对象基址 + pos 偏移** |
| 3 | 两组几何 `a30/a34/a38`、`a40/a44/a48` + `hd`（**ZP 已有**，`lib.rs:1978`） | 目标点 / 自身点候选 | 已有，保留即可 |
| 4 | `mon → sp(怪种)` 映射 + `area`（**AR 已有**，`lib.rs:2611`）、`f` 帧号 | 确认 ≥2 个不同低位 sp 大怪、同 area、共现窗口 ≤120 帧（P36 §2.4 验收门槛） | 已有 |
| 5 | 每 mon 的自身位置真值（另采一个已知 transform/pos 锚点） | 区分 `a30`/`a40` 里哪个是「自身」，从而定位哪个是「目标」 | 需静态定位 |

**降级方案（无需猎人坐标真值）**：只采 ① 两只大怪同区 + ② 现有 ZP 两组坐标，做「跨 mon 坐标对应」检验 —— 若出现 `a40(A)~a40(B)` 或 `目标点(A)~自身点(B)` 命中 ⇒ 目标点指向另一只怪；若两只大怪的「目标点」始终等于同一个值 ⇒ 强支持「共同单一目标（猎人）」。这条**甚至可以不改插件、不重编译**（见 §5）。

**零新增 hook / 零写入论证**：以上字段可全部追加在已有 `h_matcher @0x8E144` 的 `dist_probe()`（`lib.rs:1867-2010`，ZP 行）与 `h_start_40`（AR/COMBO 行）内，只多输出观测行、不改 `r`/参数、不写游戏内存、不增 detour。符合 `P76 §5` 边界。

---

## 3 · 离线统计（只读，可复现）

脚本：`04_RiseAI/tools/audit_p74_target_layer.py`（`python audit_p74_target_layer.py`）；只读 `02_Workspace/game_p54_lite.txt` 与 `04_RiseAI/out/game_p54_lite_*.txt`，不写任何文件。

**数据来源**
- 主日志：v69 斩龙场，11368 行；`Z=270 / ZP=67 / AR=338 / COMBO=701 / QX=815 / V=21`；零 FATAL、`live=1`。
- 归档：28 个 `game_p54_lite_*.txt`（v42~v56）**ZP 全为 0**；旧 `game_p54.txt`(v38)/`.prev`(v37) 亦 ZP=0。

**实体口径**
- V 行 sp=`{0050, 101B}`，COMBO/AR sp=`{0050, 1008, 101B, 102F}`；低位(<0x1000)大怪怪种 sp 值域 = **仅 `{0050}`**。⇒ **全场 1 只可识别大怪，无两只大怪同区样本**（`P70:5` 亦记「本场未换到第三种怪，101B 是其它对象」）。

**ZP 几何（67 条全部可解为有限 f32，6 个不同 mon）**

| 指标 | `sub+0x30..0x38` | `sub+0x40..0x48` |
|---|---|---|
| 唯一值（全体 67 条） | **3** | **67** |
| 同一 mon 内 | 完全恒定（主怪 44 条、其它 mon 各 1 值） | 逐条不同 |
| 明细 | `(1170.0,171.0,-325.0)`→主怪 `0C1F15F0`；`(3423.9,230.1,567.0)`→4 个 mon 共享；`(-1615.7,-141.7,-1105.4)`→`0C14D240` | x∈[-3012,3604]、z∈[-1652,4842]、y∈[-144,251]（跨度 6616 / 6494 / **395**） |
| 相邻帧位移 | 0（恒定） | p50≈790，p100≈4106 |

- 3D 距离 `|a40-a30|`：min 42.4 / p25 733 / p50 1623 / p75 2805 / max 5861；**最大间隙切分 gap_ratio=0.086 → 未见两个不同簇**，12 桶直方图连续单峰。
- `e2=e4=BF800000(-1.0f)` 67/67 恒定（哨兵），`e0` 逐条变；Z 行 mode 分布 `{4:117, 26:71, 6:54, 5:28}`，`val` 恒 0（case 操作数），**不含身份字段**。
- 跨 mon 坐标对应（tol=1.0）：`a40~a30`、`a30~a40`、`a40~a40` **0 命中**；`a30~a30` 命中 6 对（共享固定锚点）。

**这些数字能说明什么、不能说明什么**
- 能：`+0x30` 组是**每实体固定的静态锚点**（甚至 4 个 mon 共享一个），`+0x40` 组是随帧变化的水平面坐标；两者都不是「随猎人实时移动而变」的简单图景。
- 不能：无法把任一组绑定到「猎人」或「另一只大怪」——没有猎人坐标真值、没有 `target_*` 运行时值、没有两只大怪样本。

---

## 4 · 最小探针设计与「并进下一场」判断

**硬前提（两个，都不是「并进下一场」能自动解决的）**
1. **静态定位**：玩家对象基址+pos 偏移、`target_*` 字段 offset、`mon→怪种` 映射。这是离线反汇编工作（零实机轮次、零编译），`monster-ai-params.md:3-5` / `mon-ai-entry.md:253` 已指明该层未定位。
2. **一场「两只大怪同区」实机**：P36 §2.4 前置「≥2 轮两只大怪同区 + 1 轮单怪对照」；本轮统计证实历轮日志从未出现两只大怪同区。`P76 §4 第 5 点` 明确「下一场仍用 v71 探针版验收（W4 分流、日志完整性、跨怪、零异常），**待验项不增加**」。

**判断**
- **当前更不值得并进下一场**：领地争夺可行性已由 §0 第 1 条 / §5.6 的 [C] 结构性证据定案，探针现在只剩「GU 目标层支线是否也封死」的学术价值；下一场又是单大怪的 v71 验收场。追加字段需要重新编译 NRO（本任务禁止编译，且会挤占/覆盖验收探针），而单大怪场连支线数据都拿不到 ⇒ 白费一次编译与部署，且与 `P76 §4 第 5 点`「待验项不增加」冲突。
- **满足条件时值得并入**：先完成静态定位，并确认用户愿意在下一场跑一个「两只大怪同区」任务；届时把上表字段追加进现有 ZP/AR 行，随该场一次采齐，零新增 hook、零写入、不增实机轮次上的额外负担（同一场顺带）。
- **零编译的替代（推荐先做）**：**不改插件、不重编译**，仅把下一场换成双大怪任务，沿用现有 ZP 行做「跨 mon 坐标对应 + 距离簇」检验。它给不出 `target_type` 语义，但能直接证伪/支持「目标点是否指向另一只怪」，成本最低，且不触碰 v71 验收探针。

**最小必需数据清单（若仍无法定案时的明确缺口）**
① 两只大怪同区、同时间窗（≤120 帧）的一场；② 猎人坐标真值或 `target_type/target_id` 运行时值（二选一即可定案）；③ `mon→怪种` 映射确认这两只都是大怪；④ 保留现有 ZP 两组几何 + hd + area + f。

---

## 5 · 三档结论汇总

| 档 | 条目 |
|---|---|
| **有代码级证据 [C]** | matcher `0x8e144(ctx,ip,op,mode,value)`、`sub=[ctx+0x1428]`、距离 op `0x0b/0x17/0x57/0x5c/0x7c`、两组偏移 `+0x30..0x38`/`+0x40..0x48` 被读取并比较（`emc.md:33,42-58` + `W4-REFERENCE.md:71,150,320,372-373` 复算 CONFIRMED）；插件 ZP 已快照这两块（`lib.rs:1960-1980`）；已知 EMC opcode 集无「枚举/选另一只怪」op、动作名闭集 13 类无 versus/turf（`mon-ai-entry.md:233`）；反射字段名 `target_type/q_target_type/target_selID/target_id` 存在（`monster-ai-params.md:50-67`）；`COMBO/AR.sp = rd16(a0+0xB5F0)` 是自身怪种字（`lib.rs:2367,2580,2607`）；**Rise `EnemyStaminaData.PredatorData` 类 + `_IsPredator/_EnableRadius:400/_EmTypes[]/_ActionStance` 数值实证**（`em131_00_stamina_data.user.2.json`，§5.5）；**GU 逆向库全库检索无等价 `PredatorData`/`_EmTypes` 类或对象表**（§5.6、`spec-crossgame/monster-gu.md:230,365,398,459`） |
| **有实机证据 [实机]** | 仅 v69 单场含 ZP（归档 28 个 + 旧 `game_p54.txt` 系列 ZP=0）；全场仅 1 只大怪 `sp=0050`；ZP 67 条：`+0x30` 组全场 3 个固定值、`+0x40` 组 67 个唯一值；3D 距离单峰无两簇（gap_ratio 0.086）；跨 mon 目标点对应 0 命中；`COMBO.sp` 不随目标切换（是自身怪种） |
| **仅为推断 / 仍未定案 [I][U]** | **「目标点只指向猎人」= 推断**（P36 §2.4 第③步从未执行，本轮离线统计**仍无法定案**）；`sub+0x30`/`+0x40` 实体归属 [U]（`emc.md:51`）；`target_type/q_target_type` 语义 [U]；AI 决策层目标选择入口 [U]（`mon-ai-entry.md:253`）；「已知 opcode 里没有」不等于「全镜像不存在」；`0x10xx` sp 是否绝对排除大怪属工程惯例 [I]。**注意：本档的「目标点身份未定案」已不再是领地争夺可行性的依据**（见下方定案）。 |

**核心定案**：**Rise 有 `PredatorData` 参数层、GU 无等价类/表 ⇒ 领地争夺属结构性不可复刻** = [C]，**不依赖「目标点是否只指向猎人」**（§5.6）。

**对 P36 §2.3 / §2.4 的影响**：「纯只读做不到让两怪主动互攻」结论成立，且现在由一条**独立的 [C] 结构性证据**支撑（§0 第 1 条 / §5.6），**不再依赖** P36 §2.4 第③步那个从未执行的目标点判据。P36 §2.3 原推理（[U]「归属未证」+ 公开资料旁证）降为次要佐证；§2.4 第③步即使永远不跑，也不影响本结论。目标点身份判据**完整保留**为独立支线，证据等级仍为 [I]/[U]（见 §2(a)(c)(d) 与本表第三档）。`P76 §3` 把它列为「从未执行、可做只读定位」依旧成立，但优先级已下降。

---

## 5.5 · 追加（18:35，main 补入）：Rise 侧掠食者参数的代码级实证

本报告主体完成时，main 已从本机 `D:\Steam\steamapps\common\MonsterHunterRise\re_chunk_000.pak` 定向抽出并解析 `em131_00_stamina_data.user.2`（JSON：`04_RiseAI/out/rsz_main_json/em131_00_stamina_data.user.2.json`，实证总表 `out/P77_rise_extracted_facts.md`）。其中有：

```
snow.enemy.EnemyStaminaData.PredatorData
  {_IsPredator: 0, _ActionStance: 0, _EnableRadius: 400.0, _EmTypes: [0]}
```

**这是 Rise 侧「双怪互打 / 领地争夺」机制存在的首个 [C] 代码级实证**（此前工程里只有推断或资料旁证）：由耐力参数层的 `PredatorData` 驱动，含 `_IsPredator` 开关、`_EnableRadius` 生效半径、`_EmTypes` 目标怪种表、`_ActionStance` 处境；em131 该开关为 0（此怪不参与），但结构确实存在。同一文件另有 `_mapNikuEatSec: 20.0`、`_SetMeatEatSec: 10.0`、`_MouthToNullDistance: 4.0`。

**对本文结论的影响**：
1. 原 §5 的判断「Rise 侧是否有专属机制不明」应升级为「**Rise 有，且属耐力/掠食者参数层，不在抽选层**」。
2. 但 GU 侧在逆向库里**未找到**等价的 `PredatorData` / `_EmTypes` 类字段或对象表（`monster-ai-params.md` 只有 `target_type/target_selID` 等名字，语义 [U]）⇒ 即使把目标层定案，GU 也缺少「按怪种表挑对手 + 半径判定」的数据结构。**完整逐条对照见 §5.6**：⇒ **Rise 有、GU 无 ⇒ 领地争夺属结构性不可复刻**，这是 [C] 定案，**独立于、且不再挂在**「目标点身份未定案」上；目标点判据降为独立支线（证据等级保留于 §2、§5）。
3. 这不改变 §0 第 4 条「当前不值得并进下一场」（主结论已定案后优先级更低）：下一场仍是 v71 单大怪验收（待验项不增加），且需要两只大怪同区任务才有定案数据。

---

## 5.6 · GU 侧等价结构对照与结构性定案（本轮全库检索）

对 `00_Tools/92_MHGU-master/MHGU-master/docs/` 全库做大小写不敏感检索，关键词：
`Predator|predator|_EmTypes|IsPredator|掠食|捕食|领地|turf|territory|ZakoCombat|rival|hosyoku|fight_point|gekitai|EmTypes`。本轮检索回答 `P77:85` 留下的开放问题「GU 侧有无等价结构」。

### Rise 侧（[C] 实证，来自 §5.5 / `em131_00_stamina_data.user.2.json`）

- 类 `snow.enemy.EnemyStaminaData.PredatorData`（typeId `ea9c61fa`，crc `0x451278F1`），4 字段：`_IsPredator`(S32，枚举 `PredatorData.PredatorExec`)=0、`_ActionStance`(S32，`EnemyDef.PredatorActionStance`)=0、`_EnableRadius`(F32)=400.0、`_EmTypes`(`EnemyDef.EmTypes[]`)=`[0]`。
- 由 `snow.enemy.EnemyStaminaData._PredatorDataInfo`（Object）引用（instance 10 → ref instance 9）；同文件另有 `_mapNikuEatSec:20.0` / `_SetMeatEatSec:10.0` / `_MouthToNullDistance:4.0` / `_tiredSec` / `_motRate` 等耐力/进食参数。
- **限定（避免过度解读）**：em131 该实例 `_IsPredator=0`、`_EmTypes=[0]`，即此怪不启用、目标表为空默认值；**实证的是「类结构与字段语义」**，不是「em131 实际参与领地争夺」，也不是「已拿到多怪组合表」。这仍比 P36 §2.1 的公开资料推断高一档（资源级 [C]），与 `P77:53,85` 一致。
- 机制定位：**耐力/掠食者参数层**，不是 EMC 抽选层（W1/W2 那套），也不在 `combo/`。

### GU 侧逐条对照（全库检索结果）

| 检索命中 | 所在 | 判定 |
|---|---|---|
| `PredatorData` / `_IsPredator` / `_EnableRadius` / `_ActionStance` / `PredatorExec` | **0 命中**（`Predator` 的全部命中是武器名 `Apex Predator 5`） | 无等价类 |
| `_EmTypes` / `EmTypes[]` 目标怪种表 | GU 侧 0 命中；`spec-crossgame/monster-gu.md:398,459` 明确 **RS 用 `snow.enemy.EnemyDef.EmTypes` 枚举做键，GU 无 137 槽概念、无该枚举键** | 连「按怪种枚举目标」的数据基础都不同 |
| `mParam.fight_point`（`monster-ai-params.md:82`） | `spec-crossgame/monster-gu.md:230` 标 **GU-unconfirmed (-)**，「none: runtime parameters, absent from RSZ dump」 | 仅字段名，语义未知、无资源类 |
| `mParam.hosyoku_em_set_id`（`monster-ai-params.md:136`） | `spec-crossgame/monster-gu.md:365` 标 **GU-unconfirmed (-)**，「none (runtime; not in RSZ)」；释义「补食组 id」 | 仅字段名，非目标怪种表 |
| `mParam.gekitai_st`（`:197`）、`EatRateChange`（`mon-class-map.md:246`「比率（捕食）」）、`mGekitaiBias` / `mGekitaiHp` | 击退 / 进食类运行期字段 | 非领地争夺结构 |
| `mParam.target_selID[i]` / `target_type[i]` / `target_id` / `tar_param[i].id`（`monster-ai-params.md:60-66,114,193-194`） | 语义相近字段名；`monster-ai-params.md:3-5`「不含 offset/size」，本报告 §2(c) 已判语义 [U] | 名字存在 ≠ 可用目标表 |
| 类 `sEnemyHosyoku`（`class-inventory.tsv:2132` size 9648、`mon-class-map.md:135,197`、`batchA-classname-xref.md:55`） | GU 的「捕食/进食」per-monster 工作区结构，10 个之一 | 无 `_EmTypes[]`、无 `_EnableRadius`、无 `_ActionStance`；语义是进食而非双怪领地争夺 |
| `Tuff Turf` / `Clash of Rivals` / `Astalos Territory`（`quests.md:171`、`quests-village-hub.md`） | **任务名**，非机制（P36 §2.2 已指出） | 无关 |
| `mon-ai-entry.md:233,253` | 动作名闭集 13 类无 versus/turf；**AI 决策层（选招、目标选择、距离/朝向判定）尚未定位** | 无对应调度层 |

### 结论：结构性不可复刻（[C] 定案）

**GU 侧无等价 `PredatorData` / `_EmTypes` 类或对象表**：只有若干 `GU-unconfirmed` 的运行期字段名，加上一个语义为「进食」的 `sEnemyHosyoku` 工作区，且 GU 与 Rise 的怪种键空间根本不同（137 槽 vs `EmTypes` 枚举）。⇒ **Rise 有、GU 无 ⇒ 领地争夺属结构性不可复刻**：Rise 的领地争夺由「耐力参数层的掠食者类 + 按怪种的目标表 + 半径/处境判定」驱动，GU 连该数据结构的等价物都没有，因此不是「插件参数 / 抽选层调一调」能补的，也不是「目标点身份定案后」就能补的。这条定案**不依赖、也不再挂在**「目标点是否只指向猎人」上。

**(4) 保留目标点身份的证据等级判定**：本定案**不推翻也不替代** §2(a)(c)(d) 与 §5 第三档 ——「距离档目标点是否只指向猎人」**仍为 [I] 推断 / [U] 未定案**，P36 §2.4 第③步从未执行、本轮离线统计仍无法定案。它现在是**独立支线**，只决定「纯只读引导互攻」这一分支是否还有讨论空间，不影响上面的结构性定案；最小只读探针设计（§2(e)、§4）与「当前不值得并进下一场」的判断亦按此定位保留。

---

## 6 · 边界与未做

- 严格遵守：未改插件源码、未编译 NRO、未部署、未改任何 .bat/.cmd、未改记忆文件、未改 `04_RiseAI/NOTES.md`、未改 out 下已有 `P*.md`；只新增本文与 `tools/audit_p74_target_layer.py`。Rise `em131_00_stamina_data.user.2.json` 与 `P77_rise_extracted_facts.md` 为 main/team-lead 产出，本轮**只读引用、未修改**；§5.5 为 main 补入的记录，本轮仅升级其第 2/3 点结论措辞并补入 §5.6 对照。
- 未做：静态定位玩家坐标 / `target_*` offset（超出「只读定位方案」范围，属前置反汇编工作）；未跑实机；未读取/修改任何游戏资源。
- 复现：`python 04_RiseAI/tools/audit_p74_target_layer.py`，输出即 §3 全部数字。
