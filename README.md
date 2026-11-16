# RiseAI EntryProbe · MHGU 怪物 AI mod

面向 `Monster Hunter Generations Ultimate Recomp` 的怪物 AI mod。按 MHRise 的「状态 × 距离池 → 加权抽选」结构，对 GU 决策层做机制级复刻。

> **当前部署 = P90 合并探针版**（2026-11-16）。本仓库同时归档成品 NRO、可编译源码、逆向/实机报告与全部开发记忆。

## 当前成品

| 项 | 值 |
|---|---|
| 文件 | `rai_entrylocator_probe.nro` |
| MD5 | `0ab6cbec301b4336fbbd50dcb71f9008` |
| 大小 | 65,536 B |
| Hook | 6 detour，零游戏内存写入、不改游戏资源 |
| 源码 | `plugin/src/lib.rs`（P90 版） |
| 编译开关 | `P90_TIRED_COVERAGE=1` / `P90_F0_PROBE=1` / `P90_MIN_CAND=2` / `MAX_F0=600`；前两项置 0 = v2 行为 + 关探针 |
| 校验 | `SHA256SUMS.txt` |

历史成品 v2（md5 `c174b191549cc734806ef67b99298520`）保留在 `releases/rai_release_v2.nro`，其源码在 `plugin/src/lib.rs.v2bak`。

## 机制

- 6 个只读 hook 位于 `0x8E144` / `0x82F80` / `0x76154` / `0xAFF40` / `0xA30E4` / `0xBD260`，只改抽选权重形状，不按单怪 `action_id` 硬编码，跨怪通用。
- W1：按 Rise 15 池（3 状态 × 5 距离档）权重形状重加权；W2：按 `(状态, 距离档 hit/ts)` 取形状；W4：3 状态 × 4 处境 12 槽分流。
- W3 已关闭：三次实机证明 GU 原生没有可拦的 `_IsActionEnd` IN_ACTION 窗口。
- 疲惫态使用 GU 原生独立动作块（id +486），P79 实机中位时长 ×1.11 ⇒ 倍率 0.901，等于 Rise `_motRate` 最常见值 0.90；持续 74.5s 落在 Rise 30~120s 区间。
- 相邻同招率 9.0%（P79 168 条 AE），`prev_hit_d` 排除最近 1~3 步同签名候选；Rise 的 `_CheckPrevTableInfoList` + Think Timer 为短窗抑制，非永久禁用。

## 验收与边界

- P90 成品口径：**PASS 15 / FAIL 0 / SKIP 0**（22.2 min 实机）；唯一完整验收仍属 v2/P79 的 64/0/4，v2 单独复验未做。
- 实机跨怪覆盖 5 只：`0020` 轰龙 / `0050` 斩龙 / `0052` 泡狐龙 / `0051` / `0047`。
- 7 层分解：抽选层达成，处境/池/条件三层机制级近似，门控层结构性证伪，引擎层（L0/L1）与执行层（L7）空白。
- 不可做：Rise `_RangeDistance` 运行时分派、`_ActionNo→招式名`、12 Hub 数据表级 1:1、领地争夺、每怪 `_motRate` 可调字段。
- 「战斗内两招空档 `dE`」不是 Rise 侧已证实机制，是本项目日志侧的观测量，不能作为复刻目标（见 `docs/reports/P97_tired_slowdown_feasibility_verdict.md`）。

## 安装

1. 环境：`MHGU Recomp` + `Forge`。
2. **必要前置**：`0x76154` 必须处于 native 状态。使用 MH4U Port IPS32 变体（删除 `0x76254` 的一条 IPS32 记录）；否则 hook 落在解释器跳板上，mod 不生效。
3. 把 `rai_entrylocator_probe.nro` 放到：

   ```
   <游戏目录>/mods/RiseAI_EntryProbe/romfs/nativeNX/plugins/rai_entrylocator_probe.nro
   ```

4. 启动游戏即生效。不需要 `Show HP Bar`，不需要改 `load_order.txt` 既有行。

## 回退

覆盖同一路径后重启：v2 `releases/rai_release_v2.nro`（md5 `c174b191…`）；v1 `dfab157dea8e9448780e6ecdbd82aafd`；v71 全量探针 `1d513ec3364f4f270929fd24193ff74b`。

## 仓库结构

```
rai_entrylocator_probe.nro      当前成品（P90）
SHA256SUMS.txt                  成品校验和
plugin/                         插件源码与编译配置（Rust no_std ARM32 NRO）
  src/lib.rs                    P90 当前源码
  src/lib.rs.v2bak              v2 源码备份
  src/lib.rs.release            发布配置旧副本
releases/rai_release_v2.nro     历史成品 v2
tools/                          判读/分析脚本、elf2nro、实机一键脚本
docs/reports/                   全部逆向与实机报告（Pxx_*.md）
docs/NOTES.md                   开发主线日志
docs/memory/                    本任务全部记忆（日报 + MEMORY.md）
docs/MHGU_modmaker_ROOT_README.md  工程根说明
```

## 从源码编译

需要 Rust nightly（含 `rust-src`）、arm-none-eabi GCC 链接器：

```bash
cd plugin
CARGO_TARGET_ARMV7A_NONE_EABI_LINKER="<path>/arm-none-eabi-gcc.exe" \
  cargo build --release -Zjson-target-spec -Zbuild-std=core,alloc \
  --target armv7a-none-eabi.json
python ../tools/elf2nro.py target/armv7a-none-eabi/release/librai_context_probe.so \
  ../rai_entrylocator_probe.nro
```

编译期开关集中在 `src/lib.rs` 顶部常量区。`W3_GATE_ENABLE=0`、`DRAIN_ENABLE=0` 保持关闭；`P90_TIRED_COVERAGE` / `P90_F0_PROBE` 置 0 可回到 v2 行为。
