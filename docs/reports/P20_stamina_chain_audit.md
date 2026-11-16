# P20 · 怪物耐力链路核查（MHGU 本地 × Rise）

用户线索：「怪物的攻击动作（可能也不只是攻击动作）会降低其耐力，耐力到一定数值就会触发流口水」。
结论：**线索成立，且这确实是我此前漏掉的一条链路。** 本地 MHGU 与 Rise 两侧都能闭合。

---

## 1 · Rise 侧：完整链路（本地 RSZ 反射数据 + 已解包参数）

数据源：`04_RiseAI/refs/rszmhrise.json`（69 MB，250,700 条类定义）、`04_RiseAI/out/rsz_json/em001~003_action_param_data.user.2.json`、`04_RiseAI/refs/rise_enemy_ai_paths.txt`。

| 环节 | 类 / 字段 | 证据 |
|---|---|---|
| **每动作扣耐力** | `snow.enemy.EnemyActionParamData.ActionInfo._subStaminaPoint` (S32) | RSZ 字段存在；解包实例实测 |
| 玩家减气输入 | `EnemyConditionPresetData.PresetStaminaData._SubStamina` (F32)、`_AddTiredTime` (F32) | RSZ 字段 |
| 状态异常输入 | `EnemyConditionDamageData.StaminaDamageData._SubStamina`、`_AddTiredTime` | RSZ 字段 |
| 耐力数据资源 | `natives/STM/enemy/emNNN/00/user_data/emNNN_00_stamina_data.user.2` | `rise_enemy_ai_paths.txt:326` |
| 疲惫参数 | `EnemyStaminaData._tiredSec` (F32)、`_motRate` (F32)、`_SetMeatRecovStartPoint / _SetMeatRecovEndPoint` (F32) | RSZ，16 成员类 |
| 耐力状态机 | `EnemyStaminaParam`（`State` / `RecoveryType` / `Attr` 枚举）、`EnemyStaminaManager` | RSZ |
| **运行时当前值** | 网络包 `EnemyActionPacket._Stamina` (U16)、`EnemyBossLateJoinSyncPacket._Stamina` (F32)、`EnemyDamagePacket._StaminaDamage` (F32) | RSZ —— 随每个动作包同步，说明是持续值而非一次性事件 |
| 疲惫标志 | `em102.Em102_00Character._IsTired` (Bool)、`SystemDifficultyRateData.OtherRateTableData._TiredRate / _TiredFirstRate` | RSZ |
| 疲惫时衰减 | `EnemyDataTune.UniqueEnergyData._DecRateTired` (F32) | RSZ |

**量化（`_subStaminaPoint` 实测值）**：

| 怪 | 动作实例 | 非零 | 值域 | 高频值 |
|---|---|---|---|---|
| em001 | 296 | 46 (15.5%) | 7~100 | 15×15、10×13、12×8、7×5、20×3、100×2 |
| em002 | 393 | 98 (24.9%) | 5~50 | 15×24、10×21、5×14、40×9、7×8、35×7 |
| em003 | 167 | 29 (17.4%) | 5~20 | 7×11、15×11、10×5 |

⇒ **并非所有动作都扣耐力**（约 15~25%），与用户「可能也不只是攻击动作」一致：只有带该参数的动作扣点。这正是「打一段时间自己就流口水」的机制来源。

---

## 2 · MHGU 本地：同一条链路的证据（此前未串起来）

| 层 | 证据 | 位置 |
|---|---|---|
| 状态名 | **`Stamina_low_Start` / `Stamina_low_End`**（怪物 FSM 状态） | `stringxref.tsv` 引用点 `0xf8d384`；`functions-retile.csv.gz` 中 `0xf8b178` 标签 `Angry_Start\|Angry_End\|Stamina_low_Start` |
| 疲劳动作链 | `tired_start / tired_Loop / tired_end`（`0x10a1814`）、`tired_Change / tired_End`（`0x10383a0`） | `functions-retile.csv.gz` |
| 运行时参数名 | `mParam.stamina_point`、`mParam.stamina_dmg_point`（EMC 脚本参数） | `monster-ai-params.md:72/78`；`stringxref.tsv` 引用点 `0x1eb8d0` |
| 耐力参数类 | `cEmStaminaData::cStaminaLev`（耐力等级） | `mon-class-map.md` §D @`0x1556955` |
| 每动作/时间倍率 | `StaminaSubRate`、`StaminaTimeVal`、`IkariRate`、`EatRateChange` | `cEmDouMouKaData` 成员 34/37（`member-offsets.tsv`）；`em002_00_doumouka` XFS 字符串表逐字节确认存在 |
| 耐力表号 | `mStaminaTblNo_N`（任务怪物槽）、`QuestData.Monsters[5].StaminaTbl` | `mon-ai-entry.md:210`、`romfs-tables.md:114` |
| 状态机 | `0xf8d384`：读 `*(mon+0xCAC0)` 指针 → `+0x3F` 状态字节（switch 0..3）→ `+0x5C` 浮点计时器 → 写回状态 | 本轮反汇编（见 §5） |

`docs/spec-crossgame/monster-gu.md:228` 已把 `stamina_point / stamina_dmg_point` 标为 **「运行期减气阈值字段名，GU-unconfirmed」**，并写 Rise 侧「absent from RSZ dump」——后半句现已被本次 RSZ 检索推翻（Rise 有 `_subStaminaPoint / _SubStamina / _Stamina`）。

---

## 3 · 我漏掉的具体是什么

- `04_RiseAI/NOTES.md:375`（v13 阶段）已经记录 `ActionInfo` 的 8 个字段，其中就有 **`_subStaminaPoint`**，但当时的分析目标是「动作冷却 CD」，把它当普通字段略过，没有串到疲劳链路。
- MHGU 侧的 **`Stamina_low_Start` / `Stamina_low_End`** 状态名与 `mParam.stamina_point` 从未纳入任何探针或判据。
- 因此前 7 轮一直在追「状态字 / 疲惫时长 / 函数入口」，而没有追**「当前耐力值」这个轮询量**。

---

## 4 · 为什么前 7 轮强制疲劳全部失败

| 失败尝试 | 通道 | 根因 |
|---|---|---|
| v40/v42 写 `act+0x5D82=1000` | **累加通道** | 判定在游戏自己的 `+=` 路径里；写值不跑该路径（v42 还写错对象）。P19 已证明该字段本身是活的蓄积（5→150） |
| v44/v45 调/hook `0x1068DD8` | 静态函数 | 实机整场不被调用（T=0） |
| v46 写 `act+0x518=2` | 判定标志 | 落地但无疲劳动画 |
| 数据层改 `@0x390` | 减气瞬时判定 | 无固定时长，改 `durF` 无效 |

共同问题：**都在改「触发的输入」或「结果的标志」，没有改「被轮询的当前耐力值」**。
Rise 的网络包每个动作都同步 `_Stamina`（U16/F32），MHGU 的 `0x816D0`（状态更新）有 315 个调用者、`0x8172C`（is_enraged）有 415 个 —— 均支持**每帧/每动作轮询当前值**的模型。若判定是 `if (stamina <= low_threshold) → Stamina_low_Start`，直接写当前值应能触发，这与所有失败尝试本质不同。

---

## 5 · 关键新线索：`mon+0xCAC0` 是指针，不是状态枚举

反汇编 `0xf8d384`（`Stamina_low_*` 状态机）：

```
movw r1, #0xcac0
ldr  r1, [r6, r1]!        ; r1 = *(r6+0xCAC0)  —— 取出来的是指针
ldrb r2, [r1, #0x3f]      ; 状态字节 0..3
cmp  r2, #3 ; bhi ...     ; 4 路 switch
...
vldr s2, [r0, #0x5c]      ; 浮点计时器
vcmpe.f32 s2, s0          ; 与阈值比较
...
strb r0, #2 / #3 / #0, [r1, #0x3f]   ; 写回状态
```

这解释了 P12 的误判：日志里 `c0 = rd(mon+0xCAC0)` 出现 `0x0C4xxxxx` 指针或 `0`，因为它们**本来就是指针**（或空指针），不是 1/2/3 枚举。真正的状态字节在 `*(mon+0xCAC0)+0x3F`，浮点计时器在子对象 `+0x5C`。
**注意 [U]**：`0xf8d384` 无直接 BL 调用者（虚表间接），其 `r6` 是否等于我们 hook 里的 `mon` 尚未实机验证。

---

## 6 · 与 P19 实机场的吻合

- 用户太刀/大锤两场、P19 跳狗龙 **3.35 分钟**自然流口水：怪物自己出招按 `_subStaminaPoint` / `StaminaSubRate` 扣耐力，不需要玩家减气攻击 ⇒ 不需要 15 分钟。
- P19 `ex`（`act+0x5D82`）从 5 递增到 150 后不再出招：与「累计消耗 / 减气蓄积达到阈值」一致，但**它不是当前耐力值**。
- `monster-status.md` 的「减气是瞬时判定、疲劳无固定时长」：结束条件是**进食恢复 / 耐力回升**（Rise: `_SetMeatRecovStartPoint/EndPoint`、`_mapNikuEatSec`），不是计时器 —— 与链路自洽。
- 暂停菜单不冻结 `forge_onUpdate`（P19 已证）：下一轮仍须「看到流口水立即关游戏」。

---

## 7 · 下一步两条路线（等用户确认，本轮未改任何插件/参数）

**A · 纯只读定位当前耐力值（推荐）**
在 v47 的 R 行定时快照里增加（零写入）：
- `p = rd(mon+0xCAC0)`；若 `heap_ok(p+0x60)` 则输出 `s3f = rd8(p+0x3F)`、`f5c = rd(p+0x5C)`（浮点位模式）、`s41 = rd8(p+0x41)`；
- 继续观测 `act+0x5D82 / 0x5D88 / 0x3CA / 0x3BE / 0x408 / 0x518`；
- 用 P19 的 3~4 分钟可复现短场，判读脚本自动列出「窗口内出现新值」的字段。
定位到「当前耐力」并确认是轮询判定后，才做一次性、有界、可回退的写入。

**B · 临时放大每动作耐力消耗（数据层）**
用户最初设想的路径。现在有了 Rise `_subStaminaPoint` 的语义背书与 MHGU `doumouka` 字段名一一对应，比之前盲改 `@0x390` 有依据得多：优先调 `StaminaSubRate` / `StaminaTimeVal`，或对应 `dtbase / attackdata` 的动作参数。
**风险**：XFS 里字段名已定位但**数值区语义未验证 [U]**，且 `StaminaSubRate` 是比率不是每动作点数；盲目改参可能重演 P17。建议先做 A。

---

## 8 · 边界

- 本轮全部为**离线核查**：本地文档、RSZ 反射数据、已解包 Rise 参数、`main_text_decomp.bin` 反汇编。游戏进程仍在运行，**未编译、未部署、未改任何插件 / 参数 / load_order**。
- `mon+0xCAC0 → +0x3F` 的对象归属、`mParam.stamina_point` 的具体运行时偏移、`doumouka` 数值区，三者均**未经实机验证**，标注 [U]。
- Rise 是不同引擎（RE Engine / RSZ），字段名语义可作为强线索，但 MHGU（ARM32 / EMC）的字段偏移必须实机定案，不能照搬。
