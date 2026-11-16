# 「猫之弱者呼唤」核查 + GU 疲惫状态定位 + 方案 B 落地（2026-11-10 21:17）

用户问：GU 猫饭技能「猫之弱者呼唤 / 猫的弱小招来术」作用
「任务中出现的大型怪物更容易陷入虚弱」，**这个「虚弱」是不是怪物进入疲劳？**
并已同意方案 B（只读状态/距离标注探针）。

---

## 1 · 结论：**不是疲劳**

「虚弱」指的是**任务生成时怪物的个体强度（HP 档位）**，不是战斗中的
疲惫（疲れ / Tired / Exhausted）状态。中文 wiki 的「更易陷入虚弱」是意译偏差。

### 证据链

| 来源 | 原文 / 结论 |
|---|---|
| MHGU Fandom `MHGU: Canteen` | "**Felyne Weakener** — Increases the likelihood of large monsters **encountered in Quests being weak**." |
| MHW Kiranico `catskills` | "Felyne Weakener — Large monsters encountered on quests have an increased chance of being **weaker than normal**." |
| Gaming StackExchange 高票答案（MH4U/Gen 系，与 GU 同源） | 怪物刷新时 HP 有 **5 档**：very weak / weak / standard / durable / very durable；**该技能让 durable 与 very durable 两档不出现**；多人不叠加；**固定血量的任务不受影响**。 |
| MH Rise 团子「猫的弱小招来」实测（巴哈姆特，日本玩家验证） | 限制 HP 浮动倍率到 ≤0（原本 -0.2~+0.2 五档），**排除高血量个体**；弱小个体比例并未提高 ⇒ 被戏称「强者不来」。 |
| 本地资料库 `mechanics/systems.md:448` / `wiki/farm-trade-canteen.md:567` | 「猫之弱者呼唤 \| 2 \| ○ \| - \| 任务中的大型怪物更易陷入虚弱」—— 技能等级 2、每日抽奖池、食材「心跳不己酱汁（辛辣）」。 |

### 名称辨析

- **MHGU / MHXX**：猫饭技能 **Felyne Weakener**（ネコの弱者よびこみ），中文常译
  「猫之弱者呼唤」。
- **MH Rise**：团子技能 **Dango Weakener**（猫的弱小招来 / 弱小招来术）。
- 两者同源同机制（排除高 HP 个体），但**不同作品**，用户提到的两个名字不要混用。

### 为什么可以确定不是疲劳

1. 作用时机是**任务开始 / 怪物刷新时一次性**决定 HP 倍率；疲惫是**战斗中**
   由减气蓄积触发的临时状态，两者生命周期完全不同。
2. 技能对**固定血量任务无效** —— 若改的是战斗状态机，不会有这个限制。
3. GU 的疲惫有独立、完整的一套数据与代码（见 §2），与猫饭技能无任何交集。

⇒ **这条线索不能直接给出疲劳字段**，但顺着它找到了下面这套现成资料，
方案 B 的难点反而被解决了。

---

## 2 · 意外收获：GU 疲惫状态的完整逆向资料

本地资料库 `wiki/monster-rage-tired.md`（愤怒/疲惫专页）：

- **疲惫（疲れ / Tired）**：减气（Exhaust）蓄积触发，流口水喘气、动作变慢、
  期间倒地硬直、之后去进食恢复；陷阱/闪光在疲时延长（例：轰龙落穴 16s→20s）。
- **逐怪触发表**在 `arc/enemy/emNNN_00.arc :: emNNN_00_dttune` 的 Exhaust 记录：
  **迅龙 em37 = initial 180 / increase 75 / max 480 [C 已对拍]**；
  迅龙属「即时型」`durF=0`，不靠固定秒数结束，维持到进食/规定行为完成
  ⇒ 这解释了 P10 「任务结束前进入疲劳」但 A 行抽样没抓到稳定状态段。
- **状态机**：`0x1068dd8` 分发器 `r1=1` 怒 / `r1=2` 疲；
  `tired_Change`@0x1585293、`tired_Change/Loop` 动作名；
  怒标志 `[this+0xCBF1]`；参数槽 21（怒）/ 33,34,36（疲）。
- **怒时倍率数组**（dttune 内每怪 30 个 f32）：`AttackRate` /
  `MotionSpeedRate` / `MotionSpeedRateLimit` 已绑定 [B]。
  ⇒ **GU 原版本来就有怒时动作加速**，与 Rise 的
  `_angerMotSpeedUpperValue` / `_tiredMotSpeedLowerLimitValue` 同构。
  这补上了 21:03 报告的缺口：P10 用户说的「不够快」**不能归因 v38**
  （v38 从不动这些倍率），而是 GU 原版倍率本身或抽样观感。

### 2.1 离线反汇编确证疲惫状态字（本轮新增 [C words]）

数据源 `refs/hpbar/main_text_decomp.bin`（文件偏移 = `main+0x...`），capstone：

```
1068DE4  mov  r5, r1              ; r1 = kind
1068DF0  cmp  r5, #2
1068DF4  beq  0x1068e24           ; kind==2 ⇒ 疲惫分支
1068DF8  cmp  r5, #1
1068DFC  bne  0x1068e38           ; 其它 ⇒ 返回
1068E00  movw r0, #0xcac4
1068E04  mov  r7, r4
1068E08  ldr  r0, [r7, r0]!       ; r0 = *(u32*)(mon+0xCAC4)，r7 写回
1068E0C  cmp  r0, #1              ; ==1 ⇒ 怒
1068E14  movw r0, #0xcbf1
1068E1C  strb r1, [r4, r0]        ; 写 [mon+0xCBF1] = 1（怒标志）
1068E24  movw r0, #0xcac4
1068E2C  ldr  r0, [r7, r0]!       ; 同一字段
1068E30  cmp  r0, #2              ; ==2 ⇒ 疲
```

⇒ **`*(u32*)(mon+0xCAC4)` 是怒/疲状态字，1=怒、2=疲**（至少在状态切换分发时）。
`0x1068784` 调用点 `bl 0x3a8d68; cmp r0,#4; movgt r1,#2 / movle r1,#1`
也确证 r1=1/2 的语义。这比 P10 用的 `act+0x518==2`（原本只标「疑似」，
且本场 0 次）**强得多**，且 `0xAFF40` 的 `a0` 就是 mon，无需新增 hook。

---

## 3 · 方案 B 已落地：v39 只读状态探针（规则零改动）

- 产物 `out/rai_state_v39.nro`（`c54d6a05…`，36864 B，**无游戏进程时已部署**）。
- **规则与 v38 逐字节相同**：prev 表 2 项 + 剩余权重归一化重抽，
  只干预 `mode==1 && sub==0`。**游戏行为不变**。
- 只在 `0xAFF40` 的 A 行追加 5 个**纯内存读取**字段：

| 字段 | 读取路径 | 依据 |
|---|---|---|
| `c4` | `*(u32*)(mon+0xCAC4)` | 离线反汇编确证 1=怒 / 2=疲（首选） |
| `cf` | `*(u8*)(mon+0xCBF1)` | 怒标志，`0x1068E1C` 写 1 |
| `e1` | `*(u8*)(mon+0x73E1)` | 动作/状态号（110..114 分支） |
| `dc` | `*(u8*)(mon+0x73DC)` | 长周期状态候选 |
| `h1` | `*(u8*)(act+0x1A1)` | Hub 状态候选（0/1/2） |
| `st` | `*(u8*)(act+0x518)` | 旧字段，保留对照 |

- 判读脚本 `tools/analyze_v39_state.py`：字段分布、`st × c4` 交叉表、
  `c4` 状态段（含 `c4==2` 段与时长）、V 行按状态分组、自动结论。
  旧日志冒烟 SKIP 通过，模拟 v39 日志判读 PASS（能正确识别 c4==2 段）。
- `8_lite_check.bat` 已追加状态分析并自动输出两份报告；
  `7_` 提示改 STEP 37（执行逻辑 / 输出路径 / 轮转**未动**）。
- 回退链：`v38.nro`(`12f1a74d…`) / `v37.nro`(`b968c3f8…`) / `v31.nro` 纯只读。
  `6_` md5 `7361445f…` 未动；`load_order`、变体 IPS、游戏资源未动。

### 一轮实机即可定案（最低负担）

双击 `8_lite_check.bat` → 进任意任务 → 锁定 → **站着不动约 60 秒** → 正常关游戏。
脚本自动跑两份分析。用户只需额外说一句「怪物大概在任务结束前多久变得疲劳」，
把该时刻与 `c4==2` 的状态段对照，即可确认 `mon+0xCAC4` 是否就是真正的疲惫字段。
若 `c4` 全程不为 2，则用 `cf/e1/dc/h1` 与 BEAT 全量计数复核，再决定扩字段。

---

## 4 · 边界

1. `+0xCAC4` 是**离线代码级**确证，尚未经实机值域验证；必须用一轮实机确认
   它在战斗中确实取 1/2、且与玩家看到的怒/疲同步。
2. 猫饭技能机制结论来自 wiki / 社区实测，**未在本机 romfs 逐字节对拍**
   （资料库 `felyne_skills.json` 本身是空表 `[]`，只能以 wiki 为源）。
3. 迅龙疲惫阈值 180/75/480 来自 dttune [C]，但**疲惫状态字节**与
   **减气蓄积值**是两个东西，不要混淆。
4. 本轮未实现任何状态权重层（3 状态分支 / 距离档）；
   v39 只取数，不干预。Rise 12 处境 Hub、`_IsActionEnd` 门控仍未实现。
