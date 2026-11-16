# P66 · v66 W3 COMBO 观测 + W4 最小三处境分流交付

日期：2026-11-15 15:50 · 状态：**已编译部署，未实机** · 部署 md5 `5f520ba5d0d8d6f7278df2b88a37e0cc`

## 0 · 先回答怪种问题

**记得，而且已复核**：上一场（v63 首场，14:54 日志）主怪 `mon=0C130510` 的 V 行 `sp=0020` **14/14**，查 `monster-slot-map-137.json` 得 `emid 32 / 轰龙 Tigrex / em032_00,em032_04`。同场 `sp=101A / 102D / 100F` 的 20 条 V 行属于其它 `mon`（`0C430060 / 0C450060 / 0C460060`），是小怪或环境对象，不是主怪。

**下一场换不同怪种正好是最需要的一步**：它同时给 ① W2 档位加权的跨怪通用性（P60 离线表 137 怪，实机目前只有轰龙一场）、② W4 12 Hub 的跨怪「攻击类/非攻击类」语义映射（P36 §3.5 / 阶段 E）、③ W1 三态在另一只怪上的复现，提供第二个数据点。因此 v66 的 `COMBO` 行**带上 `sp` 字段**，判读脚本会直接输出 `sp` 分布并提示是否出现新怪种。

## 1 · 本轮更正（承接 P64 §5.3）

P64 §5.1 原写「`+0x73E0` 语义证伪」是过度结论。被证伪的只是 `AE` 的「`forge_onUpdate` 每帧扫描」采样方式：字段在动作 hook 点仍是 `act/sub/prev_act/prev_sub`（P36 199/199；本场 A 行 `a/s/pa/ps` 吻合、`pa/ps` 非零 74/88；QX 的 `w0/w1` 在 1198/1236 次 `h_unify` 内被游戏改写，action-end 请求里 537/538）。

P36 §3.5 的 S2 离线配对（现有日志）结果是「信号齐、密度不够」：动作间隔 p50 233 帧、`2↔7` 转换 3 次，但 `act=6` / `6/12→7/21` 序列 0 次、END→下一动作 p50 158 帧、`sel` ±30 帧配对仅 19/156 —— 因为 A 行每 `A_EVERY` 个动作才 1 条、Q 行有配额、BEAT 每 300 帧 1 条。**修法是加密观测，不是加实机轮次。**

## 2 · W3：COMBO 观测行（闭合 P36 S2 ③④⑤）

| 行 | 触发点 | 字段 |
|---|---|---|
| `COMBO ev=1` | `h_start_40 @0xAFF40` **每个动作**（不再受 `A_EVERY` 抽样限制） | `f/mon/sp/a/s/pa/ps/sel/an/gap/st` |
| `COMBO ev=2` | `h_unify @0x76154` 的 action-end 请求 `(a3==2 && a1==0)`，独立于 QX 配额 | 同上 + `kind` |

- `a/s/pa/ps` 来自 `rd(a0+0x73E0)` 四字节；`sp=rd16(a0+0xB5F0)`（V 行同来源）；`gap` 为距上次动作开始帧数；`sel` 用于同帧配对。
- `MAX_COMBO=1600`/epoch，按 `COMBO_LOG` 配额并随 epoch 重置。
- 离线按 `f` 排序即可重建连段序列、验证 `act=6` 与 `6/12→7/21` 是否恒 10 帧、`2↔7` 计数、`sel` 同帧配对、END→提交帧差，以及暂停期帧漂移。
- **零新增 hook、零写入、不改任何返回值**；`A`/`Y`/`Q`/`QX`/`AE` 行原样保留。

## 3 · W4：最小三处境分流（不是 12 Hub）

**信号与缓存**：`h_unify` 的 QX 分支里按双信号算 `stance`：

```
kind == 2 || t505 >= 2   → 2 疲惫   （P64 实机 kind=2 的 20 条 100% 落疲惫态）
t518 == 1                → 1 发怒   （MEMORY 定案：可靠只读标志）
其它                     → 0 正常
```

按 `slot_of(mon)` 写入 `STANCE_CUR[8]/STANCE_F[8]`，另有 `STANCE_ANY` 全局兜底；`STANCE_TTL=300` 帧。`kind=3`（实机 142 条）**不参与判定**，仅保留在 QX 行里，因为其与发怒的相关性尚无跨怪证据。

**作用方式**：`rise_weight_pick()` 新增 `stance` 入参，计算 `eff = stance`（有效时）否则 `st3`；`eff` 同时决定 ① `BAND_SHAPE` 的 state 维、② band 无效时 v60 三状态形状、③ `wm` 统计。stance 无效 / 超时 / `W4_STANCE_ENABLE=0` ⇒ 完全按 `st3` 原样，即 v65 行为。

**留痕**：S 行新增 `sc`（处境修正生效次数）与 `sk`（当前 stance）；`STANCE_FB` 记录降级次数。

**明确不做**：P34 的 12 `attack_stance_*` Hub、按「攻击类/非攻击类」筛 case、异常状态不进攻击抽选 —— 这些都需要跨怪语义映射与 1 场零干预基线对照（P36 §3.5 / 阶段 E），下一场换怪才是开始采集的正确时机。

## 4 · 与 v65 的差异 / 不变项

| | 内容 |
|---|---|
| 新增 | `COMBO` 行（ev=1/2，带 `sp`）、`COMBO_LOG/LAST_COMBO_F`、`STANCE_*` 静态、`stance_get()`、`rise_weight_pick` 的 `stance` 入参与 `eff` 状态索引、S 行 `sc/sk` |
| 不变 | `BAND_SHAPE` 15 张形状、`band_sense`/`band_get`、`W2_BAND_ENABLE`/`BAND_TTL`、`B2` 行、`DRAIN_ENABLE=0`、`PROFILE_RELEASE=1`、`W1_ALL=1`、6 个 hook、零游戏内存写入、Z/ZP/ZS/ZT/AE/QX 行为、`6_`/`load_order` |
| 编译期开关 | `W4_STANCE_ENABLE=0` 回 v65；`W2_PROBE=0`/`MAX_B2=0`/`MAX_COMBO=0` 可逐步成品化 |

**假设**：① `kind=2` ⇒ 疲惫在轰龙单场 20/20 成立，跨怪待验；② `t518==1` 发怒为既有定案；③ stance 300 帧时效沿用 band；④ 槽溢出时全局兜底可能混入他怪处境；⑤ `eff` 会让 `w3/w4/wt` 统计口径相对 v65 略有变化（处境修正时），判读已用 `sc/sk` 标注。

## 5 · 验证与部署

| 项 | 结果 |
|---|---|
| 产物 | `out/rai_w3w4_v66.nro` **65536 B**，md5 **`5f520ba5d0d8d6f7278df2b88a37e0cc`** |
| 部署 | `mods/RiseAI_EntryProbe/.../rai_entrylocator_probe.nro` 同 md5（覆盖前 `NO_GAME_PROCESS`） |
| 特征串 | `RAI v66` / `COMBO f=`×2 / `B2 f=` / `Z f=` / `AE f=` / `QX f=` / `DRAIN_ENABLE=0` 各存在；`DG f=` / `ZD f=` / `J f=` 均 0；detour **6** |
| 冒烟 | `analyze_v66_w3w4.py` **PASS=54 / FAIL=0 / SKIP=1**；COMBO ev1=80 / ev2=20、END→动作 p50=2 帧、pa/ps 非零 80/80、stance 覆盖 2 类、sp=0020 |
| 降级回归 | v66 判读跑 v65/v64 冒烟 + v56 雷狼龙实机 + 轰龙实机：四路 `6/0/2` 全通 |
| 向后兼容 | v65 判读跑 v66 冒烟 `46/0/1` 全通（v66 只增行，不破坏既有判据） |
| 脚本 | `analyze_v66_w3w4.py` / `make_v66_smoke.py`；`8_`/`7_` STEP 66、CRLF 127/212、bareLF 0、concat 0 |
| 守卫 | `6_` md5 `7361445f…` 未动；回退 `v65 4d04b95d…`（`rai_w2_band_weight_v65.nro`） |

## 6 · 下一场（换怪）验收清单

双击 `8_lite_check.bat`，**用与轰龙不同的怪**正常打一场（建议 8–10 分钟，含发怒与自然疲惫），正常关游戏。第二份报告一次给：

1. **跨怪（本轮新增重点）**：`COMBO.sp` 与 V 行 `sp` 是否出现 `≠0020` 的新值；按 `sp` 分组对比 W2 `wb/bf` 占比、B2 档位覆盖、W1 `wall/wnok`，确认档位加权与形状表不是轰龙特例。
2. **W3（P36 S2 闭合）**：COMBO `ev1/ev2` 密度、`pa/ps` 重建率、`act=6` 与 `6/12→7/21` 帧差是否恒 10、`2↔7` 计数、`sel` 同帧配对率、END→提交 p50 帧差（对照 v17 的 162/162「恒 1 帧」）。这直接决定 `_IsActionEnd` 门控能否灰度。
3. **W4**：`sc`（处境修正次数）、`sk` 覆盖 0/1/2 三类、`kind=2` 在新怪上是否仍 100% 落疲惫态；若成立，12 Hub 的跨怪语义映射可以开始建表。
4. **回归**：W1 `wall/wnok`、`w3/w4/wt`、疲惫窗时长与窗内探针、零 FATAL / `c0000005` / `fail=0` / `live=1`。

异常时：`W4_STANCE_ENABLE=0` 回 v65、`W2_BAND_ENABLE=0` 回 v64，均为编译期开关，不需改架构。

## 7 · 未完成项

W3 `_IsActionEnd` 门控实现（等本场 COMBO 结果）、W4 完整 12 Hub 与「攻击类/非攻击类」语义映射 + 零干预基线、领地争夺/双怪互打（用户已暂缓）、成品化（`W2_PROBE=0`、`MAX_B2=0`、`MAX_COMBO=0`、移除诊断行）、**v66 未实机**。
