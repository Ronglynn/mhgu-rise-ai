# P65 · v65 W2 高保真「状态 × 距离档」加权交付

日期：2026-11-15 15:25 · 状态：**已编译部署，未实机** · 部署 md5 `4d04b95d9c445bf687c9353e8df6436b`

## 0 · 结论

用户「做」⇒ 按 P64 §2.1–2.3 的离线定案，把 **W2 高保真档位加权**真正写进 W1，并撤掉已完成使命的 DG/ZD 诊断行。全过程零实机、零新增 hook、零游戏内存写入。

`BAND_SHAPE`（Rise 15 池实测形状）按 `(st3, band)` 驱动 `rise_weight_pick()`；`band` 由新增的轻量 `band_sense()` 从距离 matcher 的命中 case 操作数读取，**独立于 Z 行日志探针** —— 因此成品可直接 `W2_PROBE=0` / `MAX_B2=0` 编译，加权仍工作。

## 1 · 为什么不再需要实机前置

| P64 原「待下一场诊断」 | 离线定案 | 处置 |
|---|---|---|
| `J/G=0` 原因 | `N` 行：`LOW` f=5700→21600 连续 15900 帧为 1，疲惫前置 f=21778 距 EXIT-LOW 仅 178 帧 | **DG 行删除**；`h_stamina` 门控的 `LOW==0` 是唯一原因，编译期可改 |
| `ZT=0` 卡点 | 运行时 `hit/ts` 本就是 GU 按 `distance<=threshold` 判定的档位；不需要 `a0+0x75ec` 对象链 | **ZD 行删除**；P61 运行时表链路线放弃 |
| 疲惫态样本 | 本场已有 4626 帧窗 / `wt=6` / `st3=2` 的 Z 12 条、QX 113 条 | 已够，不需补 |

数据齐备：`out/dist_bands_all.json`（137 怪 / 8488 距离块 / 119 怪 4 档 f32 阈值）、`out/rise_band_shapes.json`（15 张 `(state,band)` 形状 + Rust `BAND_SHAPE` 常量）。

## 2 · 实现（全部在既有 W1 结构内）

**① `BAND_SHAPE: [[u32;4];15]`** —— 直接采用 P61 生成的 Rise 15 池降序均值，索引 `[state*5 + band]`，`state 0=anger / 1=normal / 2=tired`。例如 anger range1 `[40,30,30]`、range5 `[70,20,10]`；tired range1 `[65,25,10]`、range5 `[70,20,10]`。每张和恒 100，`k=3` 或 `4` 由第 4 项是否非 0 决定。

**② `band_sense(f, mon, ip, op, md, ret)`** —— 新增、纯只读、极轻量：
- 只在 TABLE 型距离 mode（4/14/21/22）执行；从 `guess = ip + ret` 附近扫 6 字节找 `op, sub=1, w`，`w` 即命中 case 的阈值操作数。
- `w<=3 → band=w`（实机 md=4 的 `ts` 值域 0/1/2/3，与 `hit` 一一对应）；`4<=w<0x80 → band=4`（default / 最远档）；否则跳过。
- 按 `slot_of(mon)` 写入 `BAND_CUR[8]` / `BAND_F[8]`，另存全局兜底 `BAND_ANY`（应对 >8 个 mon 实例，P64 实机有 8–9 个）。
- **不依赖 `dist_probe()` / Z 行配额**，所以 `W2_PROBE=0` 成品版仍能分档。

**③ `band_get(mon, f)`** —— W1 抽选时读档位；`0xFF`（开关关闭 / 未注册 / 超 `BAND_TTL=300` 帧）⇒ 逐级降级。

**④ `rise_weight_pick()` 新增 `band` 入参**：
```
band <= 4  → shape = BAND_SHAPE[state*5 + band]，k 由第 4 项决定
band = 0xFF → 原样退回 v60 三状态形状（SHAPE_A3/A4/N3/N4/T3 + 按状态 k3:k4 混合）
```
既有 `kk` 截断归一化、`p5n%100` 轮盘、`prev` 表检查、`w3/w4/wt` 统计、`n>=3` 护栏全部逐字节不变。`W2_BAND_ENABLE=0` 可编译回 v64 行为。

**⑤ 验收留痕**：`S` 行新增 `wb`（按 `(st3,band)` 形状应用次数）与 `bf`（降级 v60 次数）；新增 `B2` 低频行（每 300 帧 1 条）记录 `ts/bd/si/md`。

**⑥ 撤除**：`DG`、`ZD` 两类行及其常量/静态；`dist_table_probe()` 失败恢复静默跳过（ZT 探针本身保留，换怪时若表链可读仍会输出）。

**不变**：6 个 hook、`DRAIN_ENABLE=0`、`PROFILE_RELEASE=1`、`W1_ALL=1`、零游戏内存写入、Z/ZP/ZS/ZT/AE/QX 行为、`6_启动并抓日志.bat`、`load_order.txt`。

## 3 · 关键差异与假设

| 项 | 说明 |
|---|---|
| 与 Rise 的结构差异 | GU 无 15 张独立「状态×距离」池表；本版按**机制级**复刻：用 GU 自己判定的档位索引去查 Rise 的形状表 |
| 档位来源假设 ① | TABLE 型 case 操作数 0..3 直接对应档位 0..3，`>=4` 归第 5 档；实机 Z 行 `ts`/`hit` 支持，但非代码级确证 |
| 档位来源假设 ② | 仅 TABLE 型 mode 更新 band；SCALE100 型（如 md=6 的 `case*100`，实机 `ts=8/10`）不参与，避免错误映射 |
| 档位来源假设 ③ | 多怪同场按 mon 槽隔离，槽溢出时用全局兜底，可能混入他怪档位（P64 实机 8–9 个 mon 实例） |
| 时效假设 ④ | `BAND_TTL=300` 帧沿用 P61 设计；距离调用稀疏时会退回 v60 形状（安全降级，不会用过期档位） |
| 形状表 k | 由 Rise 池 rates 长度（3/4）决定，不是 GU 池 case 数；`m<k` 时沿用 v60 截断归一化 |

## 4 · 未完成项

- **v65 未实机验收**（本轮全部是离线编码）。
- W3 `_IsActionEnd` 门控实现：P64 已证伪 `+0x73E0` 是稳定动作类字段，需另找语义字段；AE 现仅作变化采样。
- W4 12 处境 Hub 与分流实现：`kind=2` 是已实测的疲惫强信号，`kind=3` 语义待跨怪确认。
- 领地争夺 / 双怪互打（用户已暂缓）。
- 最终成品化：设 `W2_PROBE=0`、`MAX_B2=0` 编译；移除 AE/QX/ZT 等诊断行；`W2_BAND_ENABLE` 保持 1。
- `slot` 来源 / `0x71164` 反汇编 / Rise `range_data` 单位对齐 / 18 只怪无 dttune 阈值行（这些对当前实现已非阻塞）。

## 5 · 验证与部署

| 项 | 结果 |
|---|---|
| 产物 | `out/rai_w2_band_weight_v65.nro` **61440 B**，md5 **`4d04b95d9c445bf687c9353e8df6436b`** |
| 部署 | `mods/RiseAI_EntryProbe/.../rai_entrylocator_probe.nro` 同 md5（覆盖前 `NO_GAME_PROCESS`） |
| 特征串 | `RAI v65` / `B2 f=` / `wb=` / `bf=` / `ZT f=` / `Z f=` / `AE f=` / `QX f=` / `DRAIN_ENABLE=0` 各 1；`DG f=` / `ZD f=` / `J f=` / `W f=` 均 0；detour **6** |
| 冒烟 | `analyze_v65_band.py` **PASS=46 / FAIL=0 / SKIP=1**；B2 覆盖 5 档、`wb=40 / bf=10`、疲惫窗 4626 帧 |
| 降级回归 | v65 判读跑 v64/v63 冒烟 + v56 雷狼龙实机 + v63 本场实机：四路 `6/0/2` 全通 |
| 版本切换证据 | v64 判读跑 v65 冒烟 → 2 个 FAIL（期望 DG/ZD 存在），确认诊断行已撤除 |
| 脚本 | 新增 `analyze_v65_band.py` / `make_v65_smoke.py`；`8_`/`7_` STEP 65、`TOOL2` 切 v65；CRLF 120/206、bareLF 0、concat 0 |
| 守卫 | `6_` md5 `7361445f…` 未动；回退 `v64 add1af51…`（`rai_p64_fix_v64.nro`） |

## 6 · 下一场（唯一需要的一场 = 整体验收）

双击 `8_lite_check.bat` 正常打一场（建议 8–10 分钟，含发怒与自然疲惫），正常关游戏。第二份报告一次给四条结论：

1. **W2 加权是否生效**：`B2` 的 `bd` 覆盖档数、`S` 行 `wb>0` 与 `wb/(wb+bf)` 占比、`bf` 降级是否如预期出现在距离调用稀疏段。
2. **W1 是否仍健康**：`wall/wnok`（v63 场 111/102）、`w3/w4/wt`、V 行映射零违例、动作多样性与连段完整性。
3. **疲惫窗数据**：窗长、`st3=2` 样本、窗内 Z/ZP/AE/QX/B2 是否都有数据。
4. **零异常**：FATAL / `c0000005` / `fail` / `live` / `hub`。

若 `wb` 占比过低（<20%）或连段异常，编译期把 `W2_BAND_ENABLE=0` 即回到 v64 行为，无需改架构。验收通过后按 §4 做成品编译即可发布。
