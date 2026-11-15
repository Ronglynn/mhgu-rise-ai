# RiseAI EntryProbe · MHGU 怪物 AI 成品 mod

面向 `Monster Hunter Generations Ultimate Recomp` 的怪物 AI mod，按 MHRise 的「状态 × 距离池 → 加权抽选」结构，对 GU 的决策层做机制级复刻。

> 本仓库只发布**可游玩的成品 NRO**。开发过程、逆向报告与判读工具不在本仓库内。

## 这是什么

- 6 个只读 hook 挂在 GU 的 EMC 抽选层（`0x8E144` / `0x82F80` / `0x76154` / `0xAFF40` / `0xA30E4` / `0xBD260`），**零内存写入**、不改游戏资源、不按单怪 action_id 硬编码，跨怪通用。
- W1：按 Rise 15 池（3 状态 × 5 距离档）的权重形状重加权全部主轨抽选。
- W2：按 `(状态, 运行时距离档 hit/ts)` 取对应池形状。
- W4：3 状态 × 4 处境（常规 / 远距 / 异常 / 换区）分流，换区处境退回原版权重。
- W3 已关闭：三次实机证明 GU 原生没有 `_IsActionEnd` 可拦的 IN_ACTION 窗口。

**定位**：这是「当前纪律下的最大机制级复刻」，不是 MHRise AI 的完整移植。Rise 的 L0/L1 引擎层状态机、L7 动作执行层、疲惫喘息、领地争夺、12 个 `attack_stance_*` Hub 的数据表级 1:1 均未实现。

## 安装

1. 环境：`MHGU Recomp 0.15.3` + `Forge 1.5.1`。
2. **必要前置**：`0x76154` 必须处于 native 状态。本项目使用 MH4U Port IPS32 变体（删除 `0x76254` 的一条 IPS32 记录）实现这一点；若该变体未启用，hook 会落在解释器跳板上，AI mod 不生效。
3. 把 `rai_entrylocator_probe.nro` 放到：

   ```
   <游戏目录>/mods/RiseAI_EntryProbe/romfs/nativeNX/plugins/rai_entrylocator_probe.nro
   ```

4. 启动游戏即生效。不需要 `Show HP Bar`，不需要改 `load_order.txt` 既有行。

## 版本与校验

| 项 | 值 |
|---|---|
| 文件 | `rai_entrylocator_probe.nro` |
| 大小 | 61,440 B |
| MD5 | `c174b191549cc734806ef67b99298520` |
| SHA-256 | 见 `SHA256SUMS.txt` |
| Hook 数 | 6 detour |
| 编译配置 | `PROFILE_RELEASE=1`，关闭高频探针日志 |

实机验收基于同源码的 v71 全量探针版：单场 10.5 分钟任务、泡狐龙，`PASS=64 / FAIL=0 / SKIP=4`，无闪退、正常结算回城，日志完整性自检 OK，W4 特殊处境分流 26.2%。**本成品 NRO 自身未做实机加载复验**，只做了静态校验（NRO 头、6 detour、特征串、build_id）。

## 回退

把备份 NRO 覆盖回同一路径并重启游戏：

- v1 成品：`dfab157dea8e9448780e6ecdbd82aafd`
- v71 全量探针版（带完整日志，用于排查）：`1d513ec3364f4f270929fd24193ff74b`

成品版关闭了大部分日志；若需要新增判据，须回退到探针版重新编译。

## 已知边界

- 只改抽选权重形状，不改动作持续时间、间隔或提交节奏 ⇒ 不会产生「疲惫后输出窗口放大」。
- 不支持 Rise 的领地争夺、12 Hub 数据表级 1:1、招式名映射。
- 跨怪实机已验证 3 种（轰龙 / 斩龙 / 泡狐龙），非 137 怪全覆盖。
- 依赖 06 线 IPS32 变体；回滚该变体会使本 mod 失效。
- L7 动作执行不做：GU 自身拥有完整动画与动作资源，直接沿用 GU 动画即可。

## 仓库结构

```
rai_entrylocator_probe.nro      成品插件
README.md                       本说明
SHA256SUMS.txt                  成品校验和
plugin/                         插件源码与编译配置（Rust no_std ARM32 NRO）
  Cargo.toml / Cargo.lock / build.rs / rust-toolchain.toml
  armv7a-none-eabi.json         自定义 target spec
  link/switch32.ld, exported.txt
  src/lib.rs                    当前发布版源码
  src/lib.rs.release            同上（发布配置副本）
tools/elf2nro.py                ELF → NRO 转换脚本
```

## 从源码编译

需要 Rust nightly（含 `rust-src` 组件）、arm-none-eabi GCC 链接器，以及本仓库的 `tools/elf2nro.py`。

```bash
cd plugin
CARGO_TARGET_ARMV7A_NONE_EABI_LINKER="<path>/arm-none-eabi-gcc.exe" \
  cargo build --release -Zjson-target-spec -Zbuild-std=core,alloc \
  --target armv7a-none-eabi.json
python ../tools/elf2nro.py target/armv7a-none-eabi/release/librai_context_probe.so \
  ../rai_entrylocator_probe.nro
```

编译期开关集中在 `src/lib.rs` 顶部常量区：`W1_ALL`、`W2_BAND_ENABLE`、`W4_STANCE_ENABLE`、`W4_HUB_ENABLE` 为行为开关；`W2_PROBE`、`MAX_AE`、`MAX_AR`、`MAX_B2`、`MAX_COMBO`、`MAX_QX` 控制诊断日志；`W3_GATE_ENABLE=0`（GU 无可拦窗口）、`DRAIN_ENABLE=0`（禁用强制疲惫）。

注意：`MAX_QX` 可以置 0，W4 处境状态更新已独立于 QX 日志配额分支。

`DRAIN_ENABLE` 默认是 0（关闭）。置 1 会启用 v55/v56 验证过的原生疲惫触发：在 `0xBD260` hook 中放大入参 delta，让游戏自己走完疲惫链 I（`+0x508 → +0x505 → Stamina_low_Start`），**零游戏内存写入、跨怪通用**。它只用于调试与验证，会破坏自然疲惫节奏，不建议日常游玩开启。

## 发布范围

本仓库只发布成品 NRO、可编译源码与必要说明。逆向过程报告、实机日志、Rise 静态资产（pak 抽取物）不含在内。
