# P84 · Titanbreak 难度 mod「出招速度」实现剖析（离线静态，2026-11-15 22:05）

## 0 · 一句话结论

**Titanbreak 不写 hook、不改代码、不改运行时内存。** 它给每只怪生成一个只含少量条目的「补丁 arc」，把 `enemy/dt_tune/emNNN_SS_dttune` 里 **30 个 f32 的怒时倍率数组前 3 项按难度系数缩放**，第一项即官方说明的 `Enraged Speed`。Hard 及以上才把速度项从 ×1.0 提到 ×1.1 / ×1.2 / ×1.35；Standard 及以下保持原值。这是**纯数据层、任务加载时生效的静态倍率**，不是运行时按状态驱动的出招频率/间隔控制。

来源包：`D:\Baidunetdiskdownload\titanbreak_difficulties_6b631.7z`（12 MiB → 解包 82 MiB / 1950 文件 / 167 目录）。GameBanana 官方页：`https://gamebanana.com/mods/595757`（作者 Handburger）。

## 1 · 实现载体：单条目补丁 arc

包内 20 个难度档：`VeryEasy / Easy / Standard / Hard / VeryHard / Master / Veteran / Ashenveil`，各档再分 `+HP`、`+Loot`、`+Loot+HP` 变体。每档 94~96 个怪物 arc。

每个 `romfs/nativeNX/arc/enemy/emNNN_SS.arc` **只含 1 或 5 个条目**（`arc_tool.py extract` 实测，em001_00）：

| 条目 | 大小 | 出现档位 | 作用 |
|---|---|---|---|
| `enemy\dt_tune\em001_00_dttune` | 1594 B (zlib) | 全部 | HP / 部位硬直 / 怒时倍率数组 |
| `enemy\hagi\hagi_s{0,1,2,4}_em001_00` | 各 346 B | 仅 `+Loot` 变体 | 剥取掉落表（80 条 drop 记录） |
| `romfs/nativeNX/loc/arc/result.arc` | 313 条目 | 仅 `+Loot` 变体 | 全部怪的 hagi 掉落表副本；实测与 `em001_00.arc` 内 4 个条目**逐字节一致** |
| `romfs/nativeNX/eng/arc/title_eng.arc` | 2 个标题贴图 | 全部 | 难度标题图，与行为无关 |

即：由 mod loader 把补丁 arc 与原版 arc **按条目合并**，而不是整包替换。与本项目 ARC 纪律（禁止整包重封共享大 arc、一律 `bin/arc_tool.py pack --orig`）完全同构。包内**没有任何** `.nro` / IPS / 代码补丁 / `*_cmdtbl` 条目 ⇒ 出招速度不是从 AI 抽选层改的。

## 2 · 出招速度改在哪：dttune 怒时倍率数组前 3 项

本项目既有 RE 文档 `00_Tools/92_MHGU-master/.../docs/wiki/monster-rage-tired.md` §3bis 已定位：每怪 `*_dttune` 内含 **30 个 f32 倍率数组**（120 B，前 ~13 项随怪变化、其余 1.0），由装载器 `0x57740` 整块读入（`0x5811c..0x58170`），在怪初始化时喂给 `cAngryParam` 参数节点，**主程序内无数值副本**。`em001_00` 数组起点 `0x1B2`，原版前 14 项：

```
1.15, 1.25, 1.0, 1.15, 1.1, 1.05, 1.0, 1.0, 1.5, 3.0, 0.5, 1.5, 2.0, 1.0
```

em001 跨 20 档逐字节对比：**全文件仅 21 字节有差异** = HP 低 2 字节(0x38) + 部位硬直块(0x3C..0x82) + `0x1B2/0x1B6/0x1BA` 三个 f32。数组起点**逐怪浮动**（实测 0x154 / 0x17E / 0x17F / 0x19A / 0x1B2 / 0x1DA / 0x202…，含奇数偏移，必须逐字节扫描），作者脚本按怪定位后统一乘系数。

### em001_00 三字段逐档实测（原版 1.15 / 1.25 / 1.00）

| 档位 | idx0 @0x1B2 | idx1 @0x1B6 | idx2 @0x1BA | 相对原版系数 |
|---|---|---|---|---|
| 原版 / VeryEasy / Easy | 1.1500 | 1.2500 | 1.0000 | 1.0 / 1.0 / 1.0 |
| Standard | 1.1500 | **1.3750** | 1.0000 | 1.0 / **1.1** / 1.0 |
| Hard | **1.2650** | 1.8750 | 0.9000 | **1.1** / 1.5 / 0.9 |
| VeryHard | **1.3800** | 2.1875 | 0.8500 | **1.2** / 1.75 / 0.85 |
| Master | **1.5525** | 2.5000 | 0.8000 | **1.35** / 2.0 / 0.8 |
| Veteran | **1.2650** | 1.2500 | 0.8000 | **1.1** / 1.0 / 0.8 |
| Ashenveil | **1.7500** | 4.8125 | 0.7000 | **1.5217** / 3.85 / 0.7 |

与官方难度文案逐档精确吻合（Hard `Speed 1.1x / Damage 1.5x / Defence up 10%`；VeryHard `1.2x / 1.75x / 15%`；Master `1.35x / 2x / 20%`；Veteran `1.10x / 1.0x / 20%`；Standard 只有 `Enraged Damage 1.1x`）。**「Hard 及以上才改出招速度」属实**：Standard 及以下 idx0 恒为原值。

全怪复核：`Hard+Loot` 94 个 arc 与 `Easy+loot` 逐字节比对，**93/94 只怪**三项系数严格为 `1.1 / 1.5 / 0.9`，无一例外；唯一例外 `em087_00` 只改部位硬直、无倍率改动（与 `dttune.md` 记「em087 是唯一无 status block 的 arc」一致）。轰龙 `em020_00` 数组在 0x198，原版 `1.2/1.3/1.0` → Hard `1.32/1.95/0.9`，同样 ×1.1/×1.5/×0.9。

其余改动（同属 dttune，与速度无关）：`+HP` 变体改 `0x38` 基础 HP（em001 4500 → Hard+HP 4950 = ×1.1、VeryEasy+HP 2700 = ×0.6、Veteran 9000 = ×2.0）；各档改部位硬直 `0x3C..0x82`（em001 140 → Hard 165 / Master 200 / Ashenveil 240）；`+Loot` 变体改 hagi 掉落概率/数量。

## 3 · 字段语义：一处需要标注的分歧

| 来源 | idx0 | idx1 | idx2 | 证据等级 |
|---|---|---|---|---|
| Titanbreak 010 模板 `dttune_mhgu.bt` + 官方说明 | `SpeedMult` | `AttackMult` | `DefenseMult` | 作者脚本命名 + 社区说明 + 本包数值 |
| 本项目 RE `monster-rage-tired.md` §3bis | `AttackRate` | `MotionSpeedRate` | `MotionSpeedRateLimit` | [C bytes / **语义 B**]，代码链推断 |

两边顺序相反，且都**不是代码级 [C]**。支持 Titanbreak 命名的强证据：**Standard 档只宣称改 Damage 1.1x，而字节上只有 idx1 变了 ×1.1，idx0 未动** ⇒ idx1 = Damage，idx0 = Speed。wiki 侧把「参数槽 36 → 动作速度 s16 字段 `[x+0x1428]+177`、下限钳制 ≥1.0（`0x10690ac`）」绑到 idx1；若该绑定成立，则 idx2 的 `1.0→0.9` 会被 ≥1.0 钳制吃掉、官方宣称的 `Defence up 10%` 反而不生效。

**处置建议**：把 wiki §3bis 的 idx0/idx1/idx2 具名绑定降为「存疑，需参数槽 dump 或实机 A/B」，但**不影响本轮实现方式结论**——三项都出自同一个 30-f32 数组、按难度系数缩放、由 arc 数据层下发。本项目不为此改既有 RE 文档。

## 4 · 对本项目的意义（修正上一轮措辞，不改交付结论）

上一轮答复「v2 没有输出窗口，因为节奏在 GU 引擎层、6 个 hook 够不到」需要**细化而非推翻**：

1. **运行时 hook 层确实够不到，但静态数据层可达。** dttune 数组由装载器整块读入、主程序无副本 ⇒ 改 arc 即改运行时倍率，**零 hook、零写入、零新增 detour**。本项目已有 `bin/arc_tool.py pack --orig` 工具链与 P48/P61 单条目 arc 实机经验，路径是通的。此前定案把「够不到」说成绝对，应改为「hook 层够不到；静态倍率可由数据层改」。
2. **仍不能复刻「疲惫喘息 / 输出窗口」**，三条硬约束：
   - 这三个倍率属 `cAngryParam` 族，**怒时专用**，不是按疲惫状态触发；
   - 静态、任务加载时一次性生效，**不随状态动态切换**；
   - GU 的 30 数组后 16 项全 1.0，静态侧**未定位疲惫专属动作速度下限字段**（Rise 侧对应 `ActionInfo._tiredMotSpeedLowerLimitValue`）⇒ GU 只有「怒加速」没有「疲减速」的数据字段，这正好解释 P80「疲惫喘息不可复刻」的根因。
3. **三条可选路径评估**（均不在当前交付范围）：
   - **静态改怒时速度**（arc 数据层）：可落地，但需逐怪改 94 个 arc、影响所有怪的怒时手感、与 v2 抽选层正交、必须实机复验；方向是「加速」，**不能给疲惫开窗**。
   - **运行时按疲惫状态缩放动作速度**：写参数槽 36 / `[x+0x1428]+177`（wiki 已给出钳制点 `0x10690ac`）= 写内存 + 新 hook，违反零写入与「6 hook 固定」纪律，属另一条技术路线。Titanbreak 反向证明该字段是真实生效点，可作未来锚点。
   - **维持现状**：v2 成品 `c174b191…` 行为与 P79 验收不变。

另：本轮把「Rise `_angerMotSpeedUpperValue` 有 GU 对应物、`_tiredMotSpeedLowerLimitValue` 无」从推测升级为有第三方实证支撑，**P80/P83 达成度结论（L1 部分、L0 舍弃、适用 5 层内 1 达成/3 近似/1 证伪）维持不变**。

## 5 · 边界与未做的事

- 全程**离线静态**：未启动游戏、未部署/启用该 mod、未编译 NRO、未改 `plug/` 源码、未动成品与回退 NRO、`mods/`、`load_order`、音频线、**GitHub 远端零操作**。
- 官方难度文案来自 GameBanana 页面（外部资料）；数值全部来自本包字节复核，二者逐档吻合。未做实机 A/B，故「改 idx0 是否真的让动作变快」仍是作者说明 + 数值一致性，**非本项目实机验证**。
- 字段语义分歧（§3）未解决；`em087_00` 例外已记录。
- 解包副本仅在系统临时目录 `%TEMP%/titanbreak_analysis`，原始 7z 原样保留在用户下载目录；未向工程写入大体积样本。

## 6 · 复现命令

```bash
# 解包（工程内工具）
"/c/Program Files/7-Zip/7z.exe" x titanbreak_difficulties_6b631.7z -o<tmp> -y
python bin/arc_tool.py extract \
  "<tmp>/Titanbreak/Hard+Loot/romfs/nativeNX/arc/enemy/em001_00.arc" <outdir>
# 逐档读 30-f32 数组前 3 项（起点按怪浮动，须逐字节扫描，不能只走 u16 网格）
python - <<'PY'
import struct
v = open("<outdir>/enemy/dt_tune/em001_00_dttune","rb").read()
print([struct.unpack_from("<f", v, o)[0] for o in (0x1B2,0x1B6,0x1BA)])
# 原版 1.15 / 1.25 / 1.0；Hard 1.265 / 1.875 / 0.9
PY
```

关联定案：`out/P80_goal_achievement_assessment.md`、`out/P83_L0_retire_github_freeze_cleanup.md`、`out/P72_struct_bias_and_release_profile.md`（疲惫喘息）、`out/P79_v71_real_quest_acceptance.md`（v2 验收）。
