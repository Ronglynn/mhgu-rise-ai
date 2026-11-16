# 成品版编译配置（P80 修订 · 已部署 v2）

生成物：v2 源码权威备份 `04_RiseAI/plug/_release_build/src/lib.rs.p90bak`（md5 `28e74de67e8b75e1807644b41041ef89`）；v2 NRO = `out/rai_release_v2.nro`（md5 `c174b191549cc734806ef67b99298520`）。**2026-11-15 23:20 修正**：上文原写「`plug/context_probe/src/lib.rs.release` 与主线同步、md5 `28e74de6…`」已过时 —— 实测 `lib.rs.release` md5 为 `11131339…`，是 P80 之前的旧快照。**当前部署已切换为 P90 合并探针版，见文末 §P90**。

## 开关清单

| 常量 | 成品值 | 作用 |
|---|---|---|
| `DRAIN_ENABLE` | 0 | 强制疲惫放大，必须关闭 |
| `MAX_AE` | 0 | 关 AE 动作类边沿行 |
| `MAX_AR` | 0 | 关 AR 换区状态行；`ZONE_F` 状态更新在 AR 块之外，W4 hub3 仍生效 |
| `MAX_B2` | 0 | 关 B2 诊断行 |
| `MAX_COMBO` | 0 | 关 COMBO 连段观测行 |
| `MAX_HB` | 200 | HB 行（W4 分流统计）；`--silent` 时置 0 |
| `MAX_QX` | 400 | 低频 QX 诊断行；**P80 起可置 0**，`STANCE_CUR/F` 已移出 QX 分支 |
| `PROFILE_RELEASE` | 1 | 发布配置，保持开启 |
| `W1_ALL` | 1 | 主轨全抽选，保持开启 |
| `W2_BAND_ENABLE` | 1 | W2 状态×档位加权，保持开启 |
| `W2_PROBE` | 0 | 关 Z/ZP/ZS/ZT 探针；`band_sense` 独立，W2 加权仍生效 |
| `W3_GATE_ENABLE` | 0 | P70 实机证明 GU 无可拦窗口，保持关闭 |
| `W4_HUB_ENABLE` | 1 | W4 12 处境分流，保持开启 |
| `W4_STANCE_ENABLE` | 1 | W4 处境状态维，保持开启 |

## 依赖说明（P80 修订）

- `band_sense()` 独立于 `W2_PROBE`，所以关掉 Z 系日志后 W2 加权仍工作。
- `ZONE_F`（换区 hub3）状态更新在 AR 日志块**之外**，关 `MAX_AR` 不影响 W4。
- `END_F` / `ABN_F`（W3/W4 异常）更新在 `h_unify` 独立块，不依赖 QX 日志。
- ~~只有 `STANCE_CUR/F` 在 QX 分支内 ⇒ `MAX_QX` 不得置 0~~ **已作废**：P80 配额审计发现成品 `MAX_QX=400` 而实测每 epoch 1237 次 QX 事件，前 32% 后 W4 处境维会静默停更。已把 `STANCE_CUR/F` 更新移到 QX 日志配额分支**之外**（等价改造、零新增 hook、零写入），现在 `MAX_QX` 可置 0 而不影响 W4。当前保留 400 仅作低频诊断。详见 `out/P80_stance_quota_fix.md`。

## 编译方式（P75 起沿用，避免复用旧 ELF）

复制整目录到 `04_RiseAI/plug/_release_build/`，删除副本 `target/`，用副本内 `lib.rs` 编译：

```
cd 04_RiseAI/plug/_release_build
CARGO_TARGET_ARMV7A_NONE_EABI_LINKER="D:/MHGU mod maker/00_Tools/forge_toolchain/xpack-arm-none-eabi-gcc-14.2.1-1.1/bin/arm-none-eabi-gcc.exe" "C:/Users/RongLynn/.cargo/bin/cargo.exe" build --release -Zjson-target-spec -Zbuild-std=core,alloc --target armv7a-none-eabi.json
cd "D:/MHGU mod maker" && python bin/elf2nro.py 04_RiseAI/plug/_release_build/target/armv7a-none-eabi/release/librai_context_probe.so 04_RiseAI/out/<产物>.nro
```

静态校验：NRO0 头、6 detour、`Z/AE/COMBO/AR/J/B2` 特征串 0、`RAI v71/S2/HB` 各 1、build_id 与上一版不同。

## 状态（P80 · 2026-11-15 20:12 更新）

**已部署成品 v2** `c174b191549cc734806ef67b99298520`（61,440 B / 6 detour），下次启动游戏生效。
备份链：v1 成品 `out/deployed_release_v1_dfab157d.nro`、v71 探针 NRO `out/deployed_v71_1d513ec3.nro`、v71 源码 `plug/context_probe/src/lib.rs.v71bak`。回退 = 对应备份覆盖回去 + 重启。
验收证据 `out/P79_v71_real_quest_acceptance.md`（v71 探针版 PASS=64 / FAIL=0 / SKIP=4）；v2 只改 stance 更新的位置，未实机复验，见 `out/P80_stance_quota_fix.md §5`。

---

## P90 合并探针版（2026-11-15 23:20 · **当前部署**）

**当前插件位已切换为 P90 探针版，不再是 v2 成品**：

| 项 | 值 |
|---|---|
| 产物 | `out/rai_p90_probe.nro` · 65,536 B · md5 `0ab6cbec301b4336fbbd50dcb71f9008` · 6 detour · `NRO0`@0x10 |
| 源码 | `plug/_release_build/src/lib.rs`（P90 版）；v2 备份 `lib.rs.p90bak`（`28e74de6…`） |
| 新增开关 | `P90_TIRED_COVERAGE=1`、`P90_F0_PROBE=1`、`P90_MIN_CAND=2`、`MAX_F0=600` |
| 既有开关 | 与上表**完全一致**（`DRAIN_ENABLE=0` / `W3_GATE_ENABLE=0` / `W1_ALL=1` / `W4_HUB_ENABLE=1` / `PROFILE_RELEASE=1` 等） |
| 新增日志行 | `F0`（空签名段起点）/ `F1`（段→下一动作帧差）/ `F9`（每 600 帧汇总）；行长上界 157 / 172 / 146 < 265 |
| 静态校验 | 6 detour；`F0/F1/F9/P90 PROBE/RAI v71/S2/HB` 各 1；`Z/AE/COMBO/AR/J/B2` 全 0 |
| 实机状态 | **P92（11-16 20:10）22.2 min / `sp=0051`：成品口径 PASS 15/0/0；P95（11-16 21:2x）13.4 min / `sp=0047`：再次 PASS 15/0/0、FATAL=0、日志完整性 OK，并完成 P94 日志通道修复（`level=info`）的实机验证。两次均为 P90 版；P79 验收（v71/v2 探针口径 64/0/4）不自动适用，仍是唯一完整验收** |

**做了什么**：① P89① 疲惫形状覆盖率改进（疲惫态 `m<3→2`、`n>=3→2`、`hub==3` 不再无条件 defer，改套 `HUB_SHAPE[tired][3]`）；② P87① 纯只读 FNV0 探针。零新增 hook、零写入、跨怪通用。详见 `out/P90_capability_inventory_and_now_doable.md §7`。

**判读**：`python tools/analyze_p90_f0.py [日志路径]` 与 `python tools/analyze_p91_session.py [日志路径]`（两脚本已按 P92 修正口径：疲惫分组用 `F1.t505>=2`、行长只数 `[rai]` 行）；取数指引见 P90 报告 §8。

**回退到 v2**：`out/deployed_v2_pre_p90_c174b191.nro`（`c174b191…`）覆盖插件位 + `lib.rs.p90bak` 覆盖 `lib.rs` + 重启。更早回退链见上节。

---

## P93 基线定案（2026-11-16 20:25 · 权威 `out/P93_baseline_lock_coverage_review_and_gap_closure.md`）

- **当前部署基线 = P90**（`0ab6cbec…`）：成品口径 15/0/0 全绿、探针数据已取完、零新增 hook / 零写入。**建议保持现状不动**，不重编译、不回退。
- **唯一完整验收仍属 v2 / P79**（64/0/4，探针口径），与 P91 的 15 条成品判据**不可互相替代**。
- **覆盖率改动复核**：P91 疲惫窗口 `S.s2` 0→5、`wt` 0→5 ⇒ 疲惫形状命中率 **5/5 = 100%**，未被 W1/W4 门槛丢弃；但 `hub==3` 全场仅 1 次且不在疲惫窗口、疲惫态合格候选 `m>=3` ⇒ **P90 的两处放宽本场均未被触发**。`wt=5` 不能归因于改动，`P79=1 / P70=7 / P91=5` 跨场不可比。准确措辞是「机制通路验证通过、改动效果未验证」，**不是**「部分改善」。
- **不再改插件源码**：`wt` 上限由引擎疲惫态进入抽选层的次数决定（本场 5 次），非插件门槛；`P90_F0_PROBE` 留着不影响行为（配额峰值 134/600），关它需重编译 + 实机 A/B，不做。
- **功能开发收口**：剩余仅 3 个可合并为一场的验证项（30 分钟长时日志 / 第 2 只新大型怪 / v2 单独复验）+ 永久硬断点（Rise 运行时 `_RangeDistance` 分派、`_ActionNo→招式名`、L0/L1/L7、12 Hub 1:1）。GitHub 远端零操作。
