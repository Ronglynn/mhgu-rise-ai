# P83 · L0 舍弃判定、GitHub 冻结、历史产出清理盘点（2026-11-15 21:40，全离线 / 零实机 / 远端零操作）

## 0 · 结论

1. **L0 在 GU 侧可以舍弃，建议正式定案舍弃**。L0 是 Rise 的「决策数据表装配层」，不是行为层；其可观测效果已由 W1+W2+W4 在同一抽选层覆盖并通过 P79 实机验收。GU 侧结构性无挂载点（P82 §4 四项缺口），补齐 Rise 静态资料不会改变这一点。
2. **「已有替代方案已部署」需澄清**：部署的是 v2 成品 NRO（机制级等价物 W1/W2/W4），**不是 L0 装配层的等价实现**；P82 的 L0 静态资产未编译进插件。准确措辞是「L0 舍弃 + 效果由已部署机制级方案覆盖 + 数据表级 1:1 明确放弃」。
3. **GitHub 远端零操作**：`Ronglynn/mhgu-rise-ai` 不推送、不改设置、不建仓、不删除、不撤销令牌。本地发布快照与发布脚本原样保留、标记冻结。
4. **历史产出先只读盘点、后按用户确认的 C 档清理**：候选清单 `out/P83_cleanup_manifest.txt`（251 行逐文件）；21:45 已从工作区移走约 528.8 MiB（全部进系统回收站、可恢复），不可再生的 64 个实机日志与 77 个探针 NRO 已先打包备份。详见 §6。

---

## 1 · L0 的作用

### 1.1 定义（NOTES.md §完整链 L0–L7 / P82 §2）

```
L0 EnemyUserDataParam 装配 → L1 EnemyThinkData._StateList/ThinkState
→ L2 12 处境 Hub → L3 ThinkCondition 门控 → L4 状态×距离档索引 15 池
→ L5 ConditionInfo → L6 _TransitionRate 百分制轮盘 → L7 ActionTableData._TableNo
```

L0 是**引擎装配层**：Rise 引擎按 RSZ 的 `userdataPath` 把分散的外部分件加载并组装成一棵 AI 决策树。P81/P82 已把静态拓扑重建到池文件名级：

| 环节 | 实证 |
|---|---|
| 12 个 `attack_stance_*` Hub | 每个引用 1–2 个外部分件（`P82_L0_assembly_map.json`） |
| 15 个外部分件 | 4 action + 3 combo + 8 个 `*_main.user`（例程主） |
| 8 个例程主 | 各挂 15 个 `Anger/Normal/TiredRange1..5Check` userdataPath，`parseOK` 8/8、`tail=0` |
| 120 条池路径 | 3 状态 × 5 距离档，每格 8 次，无缺格 |
| 555 个池文件 | 120/120 路径覆盖、555/555 `parseOK`、`_TransitionRate` 率和恒 100 |

### 1.2 三项作用

1. **决策数据的容器与切换机制**：决定「当前处境下用哪一组池表做抽选」——3 状态 × 5 距离 = 15 张池，每个 Hub 有自己的例程主。
2. **跨怪复用骨架**：52 怪共用同一装配结构，数值按怪变化（P80 全量 468 文件）；外部分件可按怪种覆写。
3. **L1–L6 的挂载前提**：没有装配层，后面的 FSM 状态、Hub、门控、池、轮盘都无处加载。

**关键定性**：L0 本身**不产生可观测行为**。行为由 L4 的池形状与 L6 的 `rand%100` 轮盘产生；L0 只决定「用哪张表」。因此它是 Rise 的**实现组织方式**，而不是 AI 行为目标。

---

## 2 · GU 侧能否舍弃：可以，且应当舍弃

### 2.1 结构性不可落地（P82 §4，四项缺口）

| # | 缺口 | 证据 |
|---|---|---|
| 1 | 无可切换目标表 | GU 只有一张 `*_cmdtbl` + `mode/sub` 轨道，没有 15 张独立池表或 12 个处境例程文件 |
| 2 | 无装配注入点 | EMC 解释器 `0x82F80` 直接读 `em+0x2588` 表指针，没有「按处境换表」的加载时机 |
| 3 | 无写入权限 | 复刻需改 `em+0x2588`（写内存），违反零写入纪律；P48 直接写 `+0x505/+0x508` 在 149 帧内被游戏覆盖 |
| 4 | 无运行时距离分派 | `_RangeDistance` 4 阈值 → 选第 N 个 `*RangeNCheck` 池的逻辑**没有静态中间表**（P81 §2.3：结构性不存在），需 Rise 实机/反汇编 |

⇒ 缺的是 **GU 侧挂载点**，不是 Rise 静态资料。P82 把 12 Hub → 555 池的拓扑补全后，这四项缺口一项都没减少。

### 2.2 行为效果已被覆盖（P79 唯一验收场）

| 机制 | 对应 Rise 层 | 实机证据（`02_Workspace/game_p54_lite.txt`，13,518 行 / 10.5 min） |
|---|---|---|
| W1 15 池形状重加权 | L4/L6 | `wall=116 / wnok=63`（54.3%） |
| W2 状态×距离档加权 | L4 | `wb=59 / bf=25`（70.2% 走档位形状） |
| W4 3 状态×4 处境 | L2 | `h0=62 h2=8 h3=14 hd=14`，特殊处境 **26.2%** 首次有效分流 |
| 总判读 | — | **PASS=64 / FAIL=0 / SKIP=4**，FATAL=0、无闪退、正常回城 |

成品 v2：`c174b191549cc734806ef67b99298520`（61,440 B / 6 detour），部署于 `mods/RiseAI_EntryProbe/romfs/nativeNX/plugins/rai_entrylocator_probe.nro`，**本轮已复核 md5 一致**。

### 2.3 成本收益

强行落地需同时满足：放宽「零写入」纪律、新增引擎层 hook（且 IPS32 首字需实机核对）、Rise 运行时反汇编取得距离分派逻辑 —— 属另一条技术路线，且会推翻 P79 已验收的成品。而 L0 舍弃**不改变任何已部署行为**。

### 2.4 与 L7 一致的处置

用户 21:07 已定案 **L7 无需做**（GU 自身有完整动画与动作资源）。L0 同属「Rise 特有的数据组织方式、GU 无对应结构」，应同样从缺口列表移除，措辞为「**GU 侧不适用 / 定案舍弃**」，而不是「已完成」或「无限期搁置」。

### 2.5 舍弃代价（需明确记录）

- 放弃数据表级 1:1：P82 的 `BAND_SHAPE_555` 与成品现有 `BAND_SHAPE` L1 总差异 378（15 格平均 25.2），555 池全量精确权重不进插件。
- 放弃 12 Hub 内标量：本来已判定 `parseOK=False`、含失步污染，不作定量依据，无实际损失。
- 放弃 Rise 运行时距离分派证据：本来静态资产中不存在。
- **不改变**成品行为、P79 验收结论、部署点 v2。

### 2.6 「替代方案已部署」的准确含义（纠正易混淆点）

| 项 | 状态 |
|---|---|
| v2 成品 NRO（W1+W2+W4 机制级等价物） | **已部署**，md5 已复核 |
| L0 装配层等价实现 | **未实现、本次定案舍弃** |
| P82 L0 静态资产（装配拓扑、555 池形状表、`band_shape_555.rs`） | **已交付但未编译进插件**，定位为参照 / 未来编译期资产 |
| L1 状态触发层（v55/v56/v63 改 `0xBD260` 入参 delta） | **已实现并实机 PASS**，成品 `DRAIN_ENABLE=0` 关闭；未做的是 Rise FSM 结构与 `_tiredSec`/`_motRate` 数值复刻（P81 §7） |

⇒ 一句话：**「L0 舍弃；效果由已部署的机制级方案覆盖；数据表级 1:1 明确放弃」**，不可表述为「L0 已被替代完成」。

### 2.7 达成度口径更新（仅分母口径，交付范围不变）

原 P80：7 层里 1 达成（L6）/ 3 近似（L2/L4/L5）/ 1 证伪（L3）/ 2 空白（L0+L1、L7）。
本次把 **L0、L7 判为「GU 侧不适用」**移出分母；L1 按 P81 §7 修正为「触发层已实现（成品关闭）/ FSM 结构未做」。
⇒ 适用 5 层内：**1 达成 / 3 近似 / 1 证伪**，外加 L1 部分实现。**这不代表达成度提高**，只是把不适用的维度从分母剔除；「机制级最大复刻已交付，非原目标完全实现」的总结论不变。

---

## 3 · GitHub 冻结（用户 21:34 / 21:38 两次指令）

| 范围 | 处置 |
|---|---|
| 远端仓库 `Ronglynn/mhgu-rise-ai` | **零操作**：不推送、不改设置、不建仓、不 archive、不删除、不 API 调用 |
| 令牌 `gh_pat.txt` | 不读取、不修改、不删除；如需撤销由用户自行在 GitHub 网页端处理 |
| 本地 `out/github_release/` | 原样保留（含 `.git` 快照、README、SHA256SUMS、`plugin/` 源码、`tools/elf2nro.py`），标记为**冻结归档** |
| `tools/publish_github.py` | 原样保留，**不再运行** |
| 待办列表 | 移除任何「上传 / 同步 / 更新 GitHub」条目；P82 §1 与 NOTES.md 21:10 ③ 作为历史记录保留不改 |

---

## 4 · 历史产出清理盘点（21:40 只读快照；执行结果见 §6）

### 4.1 目录体积

| 目录 | 体积 | 说明 |
|---|---|---|
| `plug/` | 391 MiB | 其中 5 个 `target/` 构建缓存约 385 MiB，可再生 |
| `refs/` | 180 MiB | `rszmhrise.json` 67 MiB（模板）/ `guide` 43 MiB / `re` 41 MiB / `hpbar` 21 MiB |
| `out/` | 93 MiB | 390 个顶层文件 + 8 个子目录 |
| `_discarded/` | 78 MiB | 已废弃探针工程 |
| `tools/` | 3.9 MiB | 全部分析脚本，保留 |
| `_retired_probes/` | 144 KiB | 保留 |
| `analysis/` | 24 KiB | 保留 |

### 4.2 分档候选（完整逐文件路径见 `out/P83_cleanup_manifest.txt`）

| 档 | 内容 | 文件/目录数 | 体积 | 性质 |
|---|---|---|---|---|
| **A 保守** | T1 五个 `plug/*/target` + T2 `_discarded/` + T3 工程根 31 个命令误重定向碎片 | 5 目录 / 258 文件 / 31 文件 | **458.0 MiB** | 全部可再生或已废弃，风险最低 |
| **B 标准** | A + T4 `sim_*.txt`(34) + T5 历史探针 NRO(77，保留 6 个成品/回退版) + T6 v1 版 `rsz_json`/`rsz_main_json`/`rsz_bulk_json`(587 文件) | +698 文件 | **496.3 MiB** | 结论已提炼进 Pxx 报告；源码 `lib.rs.vNNbak` 与 v2 解析结果保留，可重编译/重解析 |
| **C 彻底** | B + T7 `out/game_p54*.txt` 64 个历史实机日志（32.5 MiB） | +64 文件 | **528.8 MiB** | **不可再生证据**；`02_Workspace/game_p54_lite.txt`（P79 唯一验收场）永不删 |

### 4.3 明确保留（不动）

`NOTES.md`（唯一记忆）、`DESIGN_*.md` / `STATUS.md` / `CRASH_*.md`、`out/P*.md`（77 份报告与定案）；
成品与回退 6 个 NRO（`rai_release_v2.nro`、`rai_release_candidate.nro`、`deployed_release_v1_dfab157d.nro`、`deployed_v71_1d513ec3.nro`、`rai_log_integrity_v71.nro`、`rai_w1all_release_v57.nro`）；
`plug/_release_build/src/` 全部 70+ 份 `lib.rs.*bak` 与编译配置；`out/github_release/`（冻结）、`tools/`（全部）、`refs/rszmhrise.json`、`refs/_p81_extract/`、`refs/_bulk_extract/`、`out/rsz_main_json_v2/`、`out/rsz_bulk_json_v2/`、全部 `out/*.json` 定案数据、`out/band_shape_555.rs`；
`02_Workspace/game_p54_lite.txt`、各线 `.bat` / `load_order` / `mods` / 音频线 `game_p15.txt`。

**不列入删除**：`refs/guide/MHGU-Modding-main`、`refs/re/MHGU-master`（跨线共享逆向库副本，需另行确认是否重复）、`refs/hpbar/`（HP 条线资料）。

### 4.4 删除执行前置条件（21:45 已满足并执行，结果见 §6）

按数据安全纪律，删除前必须：① 对 T5/T7 等不可再生数据先打包备份（zip 校验）；② 全部走系统回收站（可恢复），不做 `rm -rf`；③ 小批次执行并逐批核验；④ 不动任何保留清单内的路径、不动 mods / 游戏目录 / `load_order`。

---

## 5 · 本轮产物

| 文件 | 用途 |
|---|---|
| `out/P83_L0_retire_github_freeze_cleanup.md` | 本报告（L0 定案 + GitHub 冻结 + 清理盘点） |
| `out/P83_cleanup_manifest.txt` | 251 行逐文件候选清单与分档合计 |

**盘点阶段约束**：只读盘点 + 新增两份报告；未编译 NRO、未改 `plug/` 源码、未动 GitHub 远端、未动 mods / 游戏目录 / `load_order`；零实机。执行阶段见 §6。

---

## 6 · 执行结果（21:45，用户选 C 档 +「日志可以做备份或保留」）

**处置**：对 64 个历史实机日志与 77 个历史探针 NRO 采取「**先打包备份、再进回收站**」双保险；`02_Workspace/game_p54_lite.txt`（P79 唯一验收场）原件保留不动。

| 步骤 | 结果 |
|---|---|
| 备份 | `04_RiseAI/_archive_backup_20261115.zip`（3.89 MiB / 144 条目 / `testzip=None`），含 64 日志 + 77 NRO + 两份 P83 文档 + `out/P83_backup_sha256.txt`（逐文件 sha256 / 字节数） |
| 批 1 | 31 个根目录命令碎片 → 系统回收站，`SHFileOperationW rc=0`，残留 0 |
| 批 2 | 175 个文件（34 个 sim 日志 + 77 个探针 NRO + 64 个实机日志）→ 回收站，`rc=0`，残留 0 |
| 批 3 | 9 个目录（5 个 `target` + `_discarded` + 3 个 v1 RSZ 目录）→ 回收站，`rc=0`，残留 0 |
| 方式 | Windows 原生 `SHFileOperationW` + `FOF_ALLOWUNDO`（`FOF_SILENT/NOCONFIRMATION/NOERRORUI`），**可恢复**；未使用 `rm -rf` / 强制删除 |
| 工作区变化 | `out/` 93 → 21 MiB、`plug/` 391 → 7.9 MiB，连同 `_discarded` 共从工作区移走约 **528.8 MiB**；**回收站内容需用户自行清空才真正释放磁盘空间** |

**核验（全部通过）**

- 部署成品 `mods/RiseAI_EntryProbe/.../rai_entrylocator_probe.nro` md5 `c174b191549cc734806ef67b99298520` **未变**；
- 成品与回退 6 个 NRO 全部在位；`plug/_release_build/src/lib.rs` md5 `28e74de67e8b75e1807644b41041ef89` **未变**；
- `NOTES.md`（491,437 B）、70 份 `P*.md` 报告、`refs/rszmhrise.json`、`refs/_p81_extract/`（573 文件）、`out/github_release/`（41 文件）、`02_Workspace/game_p54_lite.txt`（1,472,935 B）、`tools/`、各线 `.bat` 全部完好；
- 备份 zip 可正常打开，`zipfile.testzip()` 返回 `None`。

**未动**：GitHub 远端零操作；本地发布快照与发布脚本冻结保留；`mods/` / 游戏目录 / `load_order` / 音频线日志未动；未编译 NRO、未改 `plug/` 源码、零实机。

**遗留审计文件**：`out/P83_delete_batch{1,2,3}.txt`（三批逐路径执行清单）、`out/P83_backup_sha256.txt`（备份摘要）、`04_RiseAI/_archive_backup_20261115.zip`（备份本体）。三者均为本次清理的恢复依据，建议与 `P83_cleanup_manifest.txt` 一并保留。
