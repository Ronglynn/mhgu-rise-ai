# P82 · L0 装配层静态资产全量交付 + GitHub 发布完成（2026-11-15 21:30）

## 0 · 结论

**GitHub 发布已完成**：新密钥生效，13/13 文件上传成功，仓库 `https://github.com/Ronglynn/mhgu-rise-ai`（公开，head `4fc586d7`，tree 17 条目 = 13 文件 + 4 目录）。

**L0 静态侧本轮把能做的做完了**：12 个处境 Hub → 15 个外部分件 → 8 个例程主 → 120 条 15 池路径 → 555 个池文件全量，并产出 15 张精确权重形状表（Rust 草案）。**GU 侧 L0 仍不可落地**，缺口已精确化为一份清单（§4）；本轮未改插件、未重新编译部署。

## 1 · GitHub 发布结果

| 项 | 值 |
|---|---|
| 仓库 | `Ronglynn/mhgu-rise-ai`（公开） |
| 文件 | **13/13**，含成品 NRO、README、SHA256SUMS、`plugin/` 源码与编译配置、`tools/elf2nro.py` |
| 校验 | 远程 tree 13 blobs；每个文件 blob sha 与本地一致（脚本用 `blob_sha` 比对，已存在则跳过，不产生重复 commit） |
| 过程 | 首次新密钥 11/13 成功，`Cargo.lock`(504) 与 `src/lib.rs`(502) 为 GitHub 瞬时网关错误；脚本加入 5xx 重试 + blob sha 跳过后续传补全 |
| 发布脚本 | `tools/publish_github.py`（令牌从 `C:/Users/RongLynn/.workbuddy/gh_pat.txt` 读，不打印） |

README 已含：安装路径与 IPS32 变体前置、6 hook 与零写入说明、版本校验和、回退链、L7 无需做的边界、`DRAIN_ENABLE` 原生疲惫触发说明、仓库结构、从源码编译命令、发布范围声明。

## 2 · L0 装配层本轮完成的四件事

### 2.1 12 个处境 Hub → 15 个外部分件

从 12 个 `attack_stance_*` Hub 的 userdata info 表解出、去重得到 15 条外部分件路径（`out/P81_hub_external_parts.json`）：4 个 action、3 个 combo、8 个 `*_main.user`（例程主）。每个 Hub 引用 1–2 个外部分件，`out/P82_L0_assembly_map.json` 保存完整逐 Hub 映射。

### 2.2 8 个例程主 → 120 条 15 池路径

主 pak + patch 补抽 15 个外部分件后，**8 个 `*_main.user.2` 用 v2 全部 `parseOK`、0 非法引用、`tail=0`**；每个恰挂 15 个 `AngerRange1..5Check` / `NormalRange1..5Check` / `TiredRange1..5Check` userdataPath ⇒ **3 状态 × 5 距离档、每格 8 次、120 条路径无缺格**。

### 2.3 555 个池文件全量

补抽 em001 全部 `*range[1-5]check.user.2` 得 555 个文件，**120/120 目标路径覆盖、555/555 `parseOK`、`_TransitionRate` 率和 555/555 恒 100**；15 格每格 37 池。

### 2.4 15 张精确权重形状表（新增）

`tools/make_555_shapes.py` 对每格取各池 `_TransitionRate` 降序前 4 项均值、归一化到和 100，生成：

- `out/rise_15pool_shapes_555.json`（形状 + 每格池数/候选数/首项权重 + 与现有表 L1 差异）
- `out/band_shape_555.rs`（可直接编译的 `BAND_SHAPE_555: [[u32;4];15]` 草案）

| 状态 | range1 | range2 | range3 | range4 | range5 |
|---|---|---|---|---|---|
| anger | [46,28,19,7] | [46,24,18,12] | [43,27,18,12] | [46,30,16,8] | [64,24,9,3] |
| normal | [45,29,18,8] | [45,28,17,10] | [44,29,19,8] | [46,30,17,7] | [61,25,11,3] |
| tired | [60,20,14,6] | [56,20,14,10] | [55,22,14,9] | [57,23,13,7] | [72,17,8,3] |

tired 首项 55~72 明显高于 anger/normal 的 43~46，range5 各状态首项 61~72 ⇒ 与 P81「疲惫更低熵、远距出招更单一」一致。

**与成品现有 `BAND_SHAPE` 的 L1 总差异 = 378**（15 格平均 25.2），最大三格：`normal_range5` 52、`tired_range2` 50、`tired_range3` 46。⇒ 当前 W2 形状来自 P61 的 89 池子集，与 555 池全量有系统偏差。这是**可落地的编译期升级点**，但改变权重需实机复验，本轮未编译进插件（§5）。

## 3 · 12 个 Hub 自身的解析边界（诚实）

12 个 `attack_stance_*` Hub 在 v2 下仍为 `parseOK=False`（模板缺类 `typeId=0df87250`，`fieldsComplete=false`，tail=±4，7~9 个非法引用）。本轮额外做了「未知类实例统一占 S 字节」的复刻实验（S ∈ 0..96 共 16 个候选）：**12/12 均未修好**（best S=0，bad=8~9、badc=3、tail=−20），因为 Hub 同时含 userdata 实例与未知类实例，两类偏移叠加。

⇒ 与 parser-ref §8.7 的判定一致：**补模板 / 扩 v2 容错本轮不做**。Hub 的**结构层**（类集合、userdataPath、文件名语义、装配边）可靠；Hub 内的 `_IsActionEnd` / `_NextStateID` 等标量**含失步污染，不作定量依据**。

## 4 · GU 侧 L0 落地缺口（精确清单）

Rise 侧 L0 已完整描述到池文件名级，但要在 GU 侧落地仍缺：

1. **可切换的目标表**：GU 只有一张 `*_cmdtbl` + `mode/sub` 轨道，没有 15 张独立池表或 12 个处境例程文件。
2. **装配注入点**：Rise 由引擎按 `userdataPath` 加载外部分件；GU 的 EMC 解释器 `0x82F80` 直接读 `em+0x2588` 表指针，没有"按处境换表"的加载时机。
3. **写入权限**：复刻需改 `em+0x2588`（写内存），违反零写入纪律；P48 实证直接写 `+0x505/+0x508` 会在 149 帧内被游戏覆盖。
4. **运行时距离分派**：`_RangeDistance` 4 阈值 → 选第 N 个 `*RangeNCheck` 池的逻辑没有静态中间表，需 Rise 实机/反汇编。

⇒ 当前 mod 的 W1+W2+W4 是"在同一抽选层按状态×距离取不同形状"的**机制级等价物**；数据表级 L0 装配在现有纪律下无挂载点。

## 5 · 为什么未改插件

- 本轮产物全在 Rise 静态参照侧；GU 侧 6 hook / 抽选层 / 零写入边界未变。
- `BAND_SHAPE_555` 与现有表 L1=378，直接替换会改变 AI 行为，而成品 v2 已通过 P79 实机验收；任何权重变更都需一场新实机验证，用户已明确不希望多打实机。
- ⇒ 形状表以 Rust 草案交付，作为**未来放宽纪律或安排验证场时可直接落地的编译期资产**；部署点仍是 v2 `c174b191…`。

## 6 · 产物

| 类别 | 路径 |
|---|---|
| 完整装配拓扑 | `out/P82_L0_assembly_map.json` |
| 15 池形状表 | `out/rise_15pool_shapes_555.json`、`out/band_shape_555.rs` |
| 生成工具 | `tools/make_555_shapes.py`、`tools/publish_github.py` |
| 原始资产 | `refs/_p81_extract/`（555 池 + 15 外部分件 + 3 motlist） |
| 本报告 | `out/P82_L0_assets_and_github_release.md` |

**约束**：全程离线静态复核 + 本地文件与 GitHub 发布；未改 `plug/`、未编译 NRO、未动 mods / 游戏目录 / `load_order`；零实机。
