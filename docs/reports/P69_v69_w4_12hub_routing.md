# P69 · v69 = W4 机制级 12 处境分流（已部署，未实机）

用户 2026-11-15 16:59：「w4能做完吗？」；持续约束「仅最大可能减少实机次数」。

## 0 · 结论（先答）

| 层次 | 能否做完 | 说明 |
|---|---|---|
| **机制级 W4 处境分流** | ✅ **本轮做完并部署** | 3 状态 × 4 处境 = 12 槽，特殊处境退回 v38 原版权重，编译期开关 + 熔断 |
| **Rise 12 `attack_stance_*` Hub 数据表级 1:1** | ❌ **做不完（结构性天花板）** | `*_main.user` 主例程 0 个、Hub→15 池因果链断、GU 无闪光/倒地/无目标专用字段、`kind=3` 不跨怪、零干预基线属旧 IPS32 口径不可混算 |
| **额外实机轮次** | ✅ **零** | v69 = v68 + W4，完整保留 W3 门控与 AR 换区探针；下一场本来就要为换区链打 ⇒ 同场验 W3 + W4 + 换区 |

## 1 · 必须先修的实机问题

v66/v67 的「最小三处境分流」在斩龙场 `sc=1`。原因：`stance` 由 `kind==2 || t505>=2`（疲惫）、`t518==1`（发怒）推出，与既有 `st3` 几乎恒等 ⇒ `eff = stance` **没有产生新行为**。W4 名义实现了，实质是重复 W1 的状态维。本轮把 W4 升级为独立的**处境维度**。

## 2 · Rise 侧静态证据与断点

- `out/rsz_json/em001_00_attack_stance_*.user.2.json` 共 **12 个**：`flash` / `flash_hyakuryu` / `no_target_routine` / `out_main_zone` / `return_blockcenter_routine` / `same_main` / `same_main_down_floor` / `same_main_down_wall` / `same_main_high` / `same_main_master` / `same_main_up_floor` / `same_main_up_wall`。
- P32 §M5 / §L2：12 Hub 差异在 `ThinkCondition._NextStateID`(12 值) + `_ActionList` hash + userdata 绑定；**`*_main.user` 主例程 0 个被抽取**，Hub→15 池因果链无字段证据；`attack_stance=0` 无字段级证据把 Hub 与 15 池直连。
- P34 阶段 D：W4 需「跨怪通用的攻击类/非攻击类语义映射」+「异常状态不进攻击抽选」+ 零干预基线；禁止事后写 `+0x73E1`（v13-b/c 已证伪）。
- GU 侧实机（斩龙 v66 场）：`t5e08` 全 0；`kind` 值域 `{0,1,2,255}`，**`kind=3` 为 0**（轰龙 v63 场为 142 条）⇒ 不跨怪稳定，只能作「有则算」的弱信号；`dc=1` 占 265/743 太频繁；`e1` 值域丰富但语义未定案。⇒ **倒地/闪光/无目标没有可靠只读信号**。
- 零干预基线：`log.txt` 与 `20261111_2158` 归档的 v38/v39/v47 是「rule = v38, ZERO writes」，但属旧 IPS32 口径，按工作记忆纪律**不可与变体口径混算做严格 A/B**。

## 3 · v69 设计：3 状态 × 4 处境 = 12 槽

`state` = anger / normal / tired（沿用 `eff = stance`，W4_STANCE_ENABLE 不变）
`hub` 由纯只读时间戳按优先级 `3 > 2 > 1 > 0` 组合，`HUB_TTL=300`，按 mon 槽 + 全局兜底：

| hub | 语义（对标 Rise） | GU 只读信号 | 行为 |
|---|---|---|---|
| 0 | 常规同区 `same_main*` | 无特殊信号 | **与 v68 逐字节一致**：`BAND_SHAPE[state*5+band]`，W1/W2 不变 |
| 1 | 远距/无目标 `no_target_routine` / `out_main_zone` | `band==4`（TABLE 命中 default case） | 改取 `HUB_SHAPE[state*4+1]`（Rise range5 形状） |
| 2 | 异常状态 `flash` / `down_*` | `kind==3` 或 `act+0x5E08 != 0` | 改取 `HUB_SHAPE[state*4+2]`（Rise range2 形状）；**不按 action_id 硬编码** |
| 3 | 换区/离开主区域 `out_main_zone` / `return_blockcenter` | AR 的 `req=+0x73f3` / `f0=+0x73f0` / `f4=+0x73f4` 非零 | **退回 v38 原版权重轮盘**（`return (-1,0,0)`），对应「异常状态不进攻击抽选」 |

- `HUB_SHAPE: [[u32;4];12]` 来自 `out/rise_band_shapes.json`，映射表 `out/rise_hub_shapes.json`（hub0←range3 / hub1←range5 / hub2←range2 / hub3←range1 占位）。和恒 100，k 由第 4 项决定 3/4，沿用既有截断归一化。
- **护栏**：`W4_HUB_ENABLE=0` 编译期回 v68；自适应熔断 `HUB_DEFER > h0*2+50` ⇒ 之后全按常规；hub3 只退回原版权重、不中断抽选；所有读取带 `heap_ok` 与上界检查。
- **统计**：S 行加 `h0/h1/h2/h3`（各处境命中）+ `hd`（特殊处境退回次数），累计不随 epoch 重置。
- **不变**：6 hook、零游戏内存写入、W3 `_IsActionEnd` 门控（ge/gs/ek）、AR 换区探针、B2、COMBO、BAND_SHAPE、`DRAIN_ENABLE=0` / `PROFILE_RELEASE=1` / `W1_ALL=1`、`6_` / load_order。

## 4 · 与 Rise 的关键差异 / 假设 / 未完成项

**关键差异**
1. Rise 是 12 个独立 `attack_stance_*` 文件（各自 `_NextStateID` + `_ActionList`）；GU 无对应表 ⇒ 本版是 **3 状态 × 4 处境的重新组合**，不是 1:1。
2. Hub→15 池主例程链断（`*_main.user` 0 个），本版按「处境覆盖 band 形状」实现，无 Rise 字段级因果依据。
3. 闪光、倒地、上下墙/地板落差在 GU 无可靠只读信号 ⇒ 未做；GU 的高度差只在 ZP 日志里、运行时未缓存。
4. 「攻击类/非攻击类筛选」未做（会引入按动作 id 硬编码，违反跨怪纪律）；用「退回原版权重」近似。
5. 零干预 A/B 缺（旧 IPS32 口径不可混算）；用 `h0..h3/hd` 自身量化 + 编译期开关承担对照。

**假设（明确标注）**
- `band==4` ≈ 远距/无目标；`req/f0/f4 != 0` ≈ 换区进行中；`kind==3 / +0x5E08!=0` ≈ 异常。
- TTL 300 帧沿用 P61 设计；优先级 3>2>1>0 为设计选择，无 Rise 实证。
- hub1/2 形状取 Rise range5/range2 属语义拟合（远距更集中、异常更保守），非数据表映射。

**未完成项**：v69 实机验收；W3 `_IsUnderLayerEnd`；12 Hub 1:1；跨怪攻击类语义映射；领地争夺（暂缓）；原生疲惫→换区需 AR 确证；成品化（`W2_PROBE=0` / `MAX_B2=0` / 移除诊断行）。

## 5 · 产物与验证

- `out/rai_w4_hub_v69.nro` 65536 B，md5 **`1f3e15d2ae325f7677df07bec70627ec`**，部署点同 md5（覆盖前 `NO_GAME_PROCESS`）。
- 特征串：`RAI v69` / `HUB_SHAPE` / `h0=` / `AR f=` / `B2 f=` / `COMBO f=` 齐全，`J f=0`，detour=6。
- 冒烟 **65/0/1**（h0=120 / h1=18 / h2=9 / h3=6 / hd=6，特殊处境 21.6%，wall=48 wnok=41）。
- 四路旧日志降级 `6/0/2` 全通；v68 判读跑 v69 冒烟 `61/0/1` 全通（只增 S 行字段，向后兼容）。
- `8_`/`7_` STEP 69、CRLF 147/228、bareLF 0、echo 元字符未转义 0 处、concat 0；`run_v66.cmd`（文件名沿用）TOOL2 切 `analyze_v69_hub.py`。
- `6_启动并抓日志.bat` md5 `7361445f…` 未动；回退 `v68 c8466a44…`。
- 新增 `tools/analyze_v69_hub.py`、`tools/make_v69_smoke.py`、`out/rise_hub_shapes.json`。

## 6 · 下一场（唯一需要的一场，不增轮次）

双击 `run_v66.cmd` → 按键 → 游戏自动启动 → 正常打一场（建议换第三种怪，含发怒 + 自然疲惫）→ 正常关游戏。

判读一次给四条结论：
1. **W4**：`h0..h3/hd`，至少一个特殊处境命中（否则标 SKIP，属数据结论，不需重打）；特殊占比 <60%；`wall/wnok` 未下降、连段未切碎。
2. **W3**：`ek/ge/gs` 与拦下占比 <90%（v68 门控同场首验）。
3. **换区链**：AR 的 `area` 变化边沿 + `req/f0/f4` 命中 + 疲惫窗内命中。
4. **回归**：W1/W2 `wb/bf`、B2 档位覆盖、COMBO 连段、零 FATAL/异常。

判定分支：W4 正常 ⇒ 进成品候选；特殊处境占比过高或连段异常 ⇒ `W4_HUB_ENABLE=0` 编译回 v68（无需另打验证）；W3 不合适 ⇒ `W3_GATE_ENABLE=0`。

> 备注：v68 与 v69 都是首次实机（两个新机制同场首验），靠编译期开关分别回退；这是「不增加实机轮次」约束下的取舍，已在报告如实标注。
