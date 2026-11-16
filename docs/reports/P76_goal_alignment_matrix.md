# P76 · 目标对齐矩阵：以「最大程度复刻 MHRise 怪物 AI 设计」逐层核对

用户 2026-11-15 18:17 重申目标、18:20 要求「把你能做的全做了」。本文件是**主线对齐表**（子任务产物见 §6 索引）。

## 1 · 目标与层次

原始目标（P34 开篇）：「本任务要尽可能复刻 Rise 的怪物 AI，所以还原度高」。
Rise 侧静态全链（P32 §L0–L7）：L0 装配 / L1 FSM 状态 / L2 处境 Hub / L3 `_IsActionEnd` 门控 / L4 状态×距离池选择 / L5 条件检查 / L6 加权抽选 / L7 执行（动作表→动作参数）。

| Rise 层 | 本项目对应 | 现状 | 保真度 | 缺口 |
|---|---|---|---|---|
| L0 装配 | 无 | 未碰 | 0 | `EnemyUserDataParam` 58 字段未对位 |
| L1 FSM | 无（GU 疲惫 FSM 够不到） | 只观测 `+0x505` 状态字 | 低 | `Stamina_low_Start/tired_start/tired_Loop` 属状态机层 |
| **L2 处境 Hub** | **W4** | v66 三处境 → v69 3 状态×4 处境 = 12 槽 | **机制级** | 自创结构，不是 Rise 12 `attack_stance_*`；`_ActionList` 绑定未落地；Hub→池主例程未抽取 |
| **L3 门控** | **W3** | v68 重抽门控实机 `gs=0` 失效 → v70 关闭 | **0** | GU 原生 END→动作 p50=0 帧，无可拦窗口；未找 GU 等价门控 |
| **L4 状态×距离池** | **W1 + W2** | W1 三状态形状（v60）、W2 5 档 case 索引（v65） | **机制级** | GU 无 15 张独立池表；Rise 5 档几何阈值 `range_data` 未抽取；4 档 f32 表已离线拿到但未编译使用 |
| L5 条件检查 | prev 表近似 | `_CheckPrevTableInfoList` 用 3 项 prev 表近似 | 低 | `_Timer`/`_UniqueId` 因果存疑（P32） |
| **L6 加权抽选** | **W1 核心** | `op02` `rand%100` 轮盘 + top-k Rise 形状重分配 | **高（同构）** | 结构和恒 100 与 `_TransitionRate` 同构，已实证 |
| L7 执行 | 无 | 未碰 | 0 | `TableNo→_actionNo→招式名` 链断；动作资源层未解包 |

⇒ **四层里真正高保真的只有 L6；L2/L4 是机制级近似；L3 归零；L0/L1/L5/L7 空白。** 这就是「最大程度」当前的实际落点。

## 2 · 量化：投入都去哪了

| 指标 | 值 |
|---|---|
| 插件源码 | 3058 行；AI 行为主函数 ≈918 行、探针函数 ≈296 行 |
| 日志输出点 `info!` | 107 个 |
| hook | 6 个（全程未增） |
| NRO / 报告 / 判读脚本 | 79 / 53 / 45 |
| 真正改变 AI 行为的版本 | W1(v50/v57/v60)、W2(v65)、W3(v68→关闭)、W4(v66/v69) |
| 跨怪实机样本 | 2 种（轰龙 `sp=0020`、斩龙 `sp=0050`；P34 阶段 E 要求 2–3 只） |
| 成品 mod | **尚未交付**：部署仍是全量探针 v71，`lib.rs.release` 未编译未部署 |

## 3 · 偏离优先级（复盘定案）

| 级别 | 偏离 | 可恢复性 |
|---|---|---|
| **P0** | P32 §7 列为最高价值的 `*_main.user` 主例程、`range_data`、`stamina_data`、`action/combo` 一直未定向抽取 ⇒ 多个「不可行」建立在「未解包」上 | **18:25 翻案**：`re_chunk_000.pak`（32.2 GB）与 patch（4.4 GB）实测就在 `D://Steam//steamapps//common//MonsterHunterRise//`，此前「全盘 0 命中」是漏查。抽取器 + 路径表 + RSZ 解析器齐全 ⇒ **已启动真实定向抽取**，不再是外部依赖 |
| **P0** | 自定纪律「只走抽选层/权重、禁止按单怪 action_id 硬编码」把 L0–L7 压到 L4/L6 | 可放宽：P60 已有 137 怪 4 档阈值表，编译期按怪种表不违反零写入 |
| **P1** | 领地争夺（Rise AI 组成部分）判不可行后暂缓，关键判据「目标点是否只指向猎人」从未执行 | 可做只读定位，不增实机轮次 |
| **P1** | W3 证伪后直接关闭，未找 GU 等价门控 | 需静态定位 FSM/动作提交层 |
| **P1** | 至今无成品 mod | 本轮编译候选（不部署，保留 v71 供验收） |
| **P2** | v49–v64 大量强制疲惫 / 诊断行 / bat / 日志修复属验证辅助，非 AI 复刻 | 已完成，沉没成本，不再追加 |
| — | GU 无 15 张独立池表、GU 疲惫瞬时事件 + FSM、零写入与不整包重封 arc、无 Rise 实机/反汇编 | **客观天花板，不算偏离** |

## 4 · 本轮「能做的全做了」的执行范围（全部离线，不增实机轮次）

1. **P0 抽取（升级为真实执行）**：pak 已找到 ⇒ 直接定向抽取 `*_main.user.2` / `range_data` / `stamina_data` / `action` / `combo`，用 `rsz_parse.py` 解析，并给出 5 档距离阈值、`_tiredSec`/`_motRate`、Hub→池因果链、疲惫专属动作的**实证数值或明确失败原因**；同时产出可重复的一键脚本与已解包 107 JSON 的标量汇总。
2. **P0 纪律**：产出逐条纪律审计、W2 路线 B 放宽后的实现路径、137 怪阈值表的 Rust 编译期草案与体积评估。
3. **P1 领地争夺**：只读定位目标层，把推断升级为结论或明确证据缺口，给出可并进下一场的最小探针。
4. **P1 成品**：编译成品候选 NRO（**不部署**），静态校验 6 hook / 零写入 / 探针已关，并给验收后部署与回退步骤。
5. **主线**：下一场仍用 v71 探针版验收（W4 分流、日志完整性、跨怪、零异常），待验项不增加。

## 5 · 不变的边界

- 零游戏内存写入；6 hook 不变；不整包重封被多 mod 共享的大 arc（P50 教训）。
- `6_启动并抓日志.bat`、`load_order.txt`、音频 mod、游戏资源不动。
- 成品候选**不覆盖**当前部署点，避免下一场拿不到验收数据。

## 6 · 子任务产物索引（19:00 最终版）

| 任务 | 产物 |
|---|---|
| **Rise 资产真实抽取** | `tools/extract_rise_targets.cmd`（本机双 pak 绝对路径 + patch --override + --test）、`out/rise_target_extract_plan.md`（已完成真实抽取、(a)~(e) 五问）、`out/rise_hub_pool_scalars.json`（272 标量，verdict NO）、`tools/audit_rise_scalars.py`、`refs/_main_extract/`（12 原始 `.user.2`）、`out/rsz_main_json/`（12 JSON）、`out/rise_extracted_facts.json`、`tools/extract_rise_facts.py` |
| 纪律重评与编译表 | `out/P73_discipline_review.md`（35 KB，§4.5 实证定稿）、`out/dist_bands_rust.rs`（41 KB 草案）、`tools/make_dist_bands_rust.py` |
| 领地争夺目标层 | `out/P74_territory_target_layer.md`（28 KB，二次修订：结构性不可复刻 [C] 定案）、`tools/audit_p74_target_layer.py` |
| 成品候选 | `out/rai_release_candidate.nro`（md5 `dfab157dea8e9448780e6ecdbd82aafd`，61440 B，6 detour，高频探针串全 0，**未部署**）、`out/P75_release_candidate.md` |
| main 亲自实证 | `out/P77_rise_extracted_facts.md`（12 文件抽取 + 5 条定案修正 + §2.5 标量对拍 + §3.5 阈值表覆盖）、`out/rise_107_hub_pool_main.json`、`tools/audit_rise_107_main.py` |
| **总汇总** | **`out/P78_full_offline_push_summary.md`**（本轮唯一入口：4 子任务 + main 实证 + 最终关闭状态） |

