# P75 成品版 NRO 候选：编译与静态校验（**未部署**）

> 本轮只产出「可直接使用的成品 mod NRO 候选」并做静态校验，**没有部署任何文件**。
> 当前部署点仍是 v71 全量探针版 `1d513ec3364f4f270929fd24193ff74b`，
> 下一场实机验收继续用它采数据，因此游戏目录里的 NRO 一个字节都没有动。

## 1. 产物

| 项 | 值 |
|---|---|
| 路径 | `04_RiseAI/out/rai_release_candidate.nro` |
| md5 | `dfab157dea8e9448780e6ecdbd82aafd` |
| 字节数 | **61440**（60 KiB，= 15 × 0x1000 页） |
| 版本串 | `RAI v71` |
| build_id（NRO header） | `910a95b1c8007196dde555c7d54f626da94…`（全 0 补齐 0x20） |
| 源 | `04_RiseAI/plug/context_probe/src/lib.rs.release`（md5 `1113133915416f52e2b05e6fe6e6db76`） |

## 2. 构建方式（全程不触碰原 `lib.rs`）

采用「复制整目录到临时目录再编译」的方案，**没有**走「备份 → 覆盖 → 恢复」，
因此原 `lib.rs` 从未被写入，不存在恢复动作，一致性天然成立。

1. 复制 `04_RiseAI/plug/context_probe/` → `04_RiseAI/plug/_release_build/`（副本）。
2. 删除副本的 `target/`：**保证全新编译**。既规避 NOTES.md:199/221 记录的
   「编译失败时 elf2nro 复用旧 ELF、产出同 md5 文件」坑，也避免 build.rs 的
   linker script 路径缓存串到原目录。
3. 用副本内的 `lib.rs.release` 覆盖副本的 `src/lib.rs`
   （复核副本 `src/lib.rs` md5 = `1113133915416f52e2b05e6fe6e6db76`）。
4. 在 `_release_build/` 下编译；产物 `.so` 只存在于副本的 `target/`。
5. 用工程根 `bin/elf2nro.py` 把副本 `.so` 转成 `out/rai_release_candidate.nro`。

编译命令（cwd = `04_RiseAI/plug/_release_build`）：

```
CARGO_TARGET_ARMV7A_NONE_EABI_LINKER="D:/MHGU mod maker/00_Tools/forge_toolchain/xpack-arm-none-eabi-gcc-14.2.1-1.1/bin/arm-none-eabi-gcc.exe" "C:/Users/RongLynn/.cargo/bin/cargo.exe" build --release -Zjson-target-spec -Zbuild-std=core,alloc --target armv7a-none-eabi.json
```

结果：`Finished 'release' profile [optimized] target(s) in 41.33s`，Exit 0；
仅 `-z norelro ignored` 一条无害链接器警告（NOTES.md:1201 已注明）。

转换命令：

```
python bin/elf2nro.py 04_RiseAI/plug/_release_build/target/armv7a-none-eabi/release/librai_context_probe.so 04_RiseAI/out/rai_release_candidate.nro
```

### 2.1 编译前后原文件一致性复核

| 项 | 编译前 | 编译后 |
|---|---|---|
| 原 `src/lib.rs` md5 | `68a96f9826d64069e344bb116f68235e` | `68a96f9826d64069e344bb116f68235e` |
| 大小 | 172830 B | 172830 B |
| mtime | 2026-11-15 17:39:25 | 2026-11-15 17:39:25 |
| 原目录 `target/.../librai_context_probe.so` | 108584 B / 17:42（v71） | 108584 B / 17:42（v71，未变） |

**结论：原 `lib.rs` 与编译前完全一致（且从未被修改过）。**

## 3. 开关清单（编译前对 `lib.rs.release` 逐项复核）

W1 / W2 / W4 行为开关全部保留；只把诊断日志配额与探针关掉，靠编译期消除。
`MAX_QX` 必须 >= 1（`STANCE_CUR/F` 在 QX 分支内更新，W4 处境分流依赖它）。

| 常量 | 成品值 | 类别 | 说明 |
|---|---|---|---|
| `PROFILE_RELEASE` | 1 | 行为保留 | 发布配置 |
| `W1_ALL` | 1 | 行为保留 | W1 主轨全抽选 |
| `W2_BAND_ENABLE` | 1 | 行为保留 | W2 状态×档位加权（`band_sense` 独立于 `W2_PROBE`） |
| `W4_HUB_ENABLE` | 1 | 行为保留 | W4 12 处境分流 |
| `W4_STANCE_ENABLE` | 1 | 行为保留 | W4 处境状态维 |
| `W2_PROBE` | 0 | 探针关闭 | 编译期消除 Z/ZP/ZS/ZT 探针；W2 加权仍生效 |
| `MAX_B2` | 0 | 诊断关闭 | B2 低频诊断行 |
| `MAX_AE` | 0 | 诊断关闭 | AE 动作边沿行 |
| `MAX_COMBO` | 0 | 诊断关闭 | COMBO 连段观测行 |
| `MAX_AR` | 0 | 诊断关闭 | AR 换区状态行（`ZONE_F` 在 AR 块之外，W4 不受影响） |
| `MAX_HB` | 200 | 保留 | HB 行（W4 分流统计） |
| `MAX_QX` | 400 | 行为依赖 | **必须 >= 1**，承载 `STANCE_CUR/F` 更新 |
| `MAXLOG` | 1000000 | 保留 | 全局灾难熔断上限；原 24000 会截断半小时任务 |
| `DRAIN_ENABLE` | 0 | 行为保留 | 纯只读，关闭强制疲惫放大 |
| `W3_GATE_ENABLE` | 0 | 行为保留 | P70 实机证明 GU 无可拦窗口，撤回无效门控 |

## 4. 校验结果

### 4.1 特征串（`grep -a -o -F` 逐串计数）

| 串 | 期望 | 实测命中 | 判定 |
|---|---|---|---|
| `RAI v71` | 含 | 1 | 通过 |
| `S2 f=` | 含 | 1 | 通过 |
| `HB f=` | 含 | 1 | 通过 |
| `Z f=` | 不含 | 0 | 通过（`W2_PROBE=0` 编译期消除生效） |
| `AE f=` | 不含 | 0 | 通过（`MAX_AE=0`） |
| `COMBO f=` | 不含 | 0 | 通过（`MAX_COMBO=0`） |
| `J f=` | 不含 | 0 | 通过 |

> 注意：`Z f=` / `AE f=` / `COMBO f=` / `J f=` 的字面量在源码里仍存在
> （位于 `W2_PROBE==1` 或 `MAX_*>0` 分支内），NRO 中 0 命中证明 LTO 已把
> 不可达分支连同字符串一起消除，不是漏编。

### 4.2 detour 数量

```
grep -a -o 'INSTALL h_[a-z]*' out/rai_release_candidate.nro | sort -u | wc -l  ->  6
```

去重列表：`h_emc`、`h_exh`、`h_matcher`、`h_stamina`、`h_start`、`h_unify`。
与源码「6 hook / 零新增 detour」约定一致，通过。

### 4.3 NRO 头部结构（静态解析）

| 字段 | 值 |
|---|---|
| magic（0x10） | `NRO0` |
| size（header 声明 / 实际文件） | 61440 / 61440（一致） |
| seg0 | off `0x0`, size 40960, end `0xA000` |
| seg1 | off `0xA000`, size 16384, end `0xE000` |
| seg2 | off `0xE000`, size 4096, end `0xF000` |
| bss | 4096 |
| 三段 | 连续、无重叠、全部 `end <= 文件大小` |

参照已实机成功加载的 v71 NRO（65536 B：seg0 45056 / seg1 16384 / seg2 4096 / bss 4096），
两者由同一 `elf2nro.py` 生成、结构同构；成品仅 seg0 小 4096 B（一页），
正是编译期消除探针代码所致。build_id 与 v71 的 `0604cbca…` 完全不同，
证明这是**全新编译产物**，没有复用旧 ELF。

### 4.4 体积量级

**61440 B = 60 KiB，仍在 64 KiB 量级**（v71 为 65536 B = 64 KiB，差 4096 B = 1 页）。
落在历史成功加载过的 NRO 体积区间（20–64 KiB）内，未因裁剪日志而异常膨胀或塌缩。

### 4.5 是否可正常加载（仅静态校验，未启动游戏）

静态层面判定为**结构合法、可加载**，依据：

1. `NRO0` 魔数正确，header 声明 size 与实际文件大小一致；
2. 3 个 PT_LOAD 段偏移连续、全部落在文件范围内，bss 与已成功加载的 v71 一致；
3. 与同一转换脚本产出、已实机加载成功的 v71 NRO 结构同构；
4. cargo 编译 / 链接 Exit 0，无错误，build_id 为全新值；
5. 60 KiB 处于历史成功加载体积区间。

**边界声明**：以上全部是静态校验，**没有启动游戏、没有实机加载验证**，
不对运行时行为（W4 分流、日志完整性、零异常、连段正常）作任何保证；
这些必须等下一场 v71 验收场判读通过后再决定。

## 5. 未部署声明

- **未向游戏目录写入任何文件**，未修改或删除任何已部署的 NRO。
- 当前部署点仍是 v71 全量探针版 `1d513ec3364f4f270929fd24193ff74b`；
  下一场实机验收继续用 v71 采数据。
- 本轮实际写入范围（严格受限）：
  - `04_RiseAI/plug/_release_build/`（临时构建目录，含新生成的 `target/`）
  - `04_RiseAI/out/rai_release_candidate.nro`（新建）
  - `04_RiseAI/out/P75_release_candidate.md`（本文档，新建）
- **未改动**：游戏目录任何文件、记忆文件、`04_RiseAI/NOTES.md`、任何 `.bat/.cmd`、
  `out/` 下已有的 `P*.md`、任何现有 NRO（含 `rai_log_integrity_v71.nro`）。

## 6. 验收通过后如何部署

前置条件：下一场 v71 实机验收场判读通过（W4 分流正确、日志完整性、零异常、连段正常）。

```
cp 04_RiseAI/out/rai_release_candidate.nro "<游戏目录>/mods/RiseAI_EntryProbe/romfs/nativeNX/plugins/rai_entrylocator_probe.nro"
```

- 文件名不变，`load_order` 无需改动。
- 部署后用 `md5sum` 复核部署点应为 `dfab157dea8e9448780e6ecdbd82aafd`（61440 B）。
- 建议覆盖前先把当前部署点 NRO 另存一份备份（out/ 里已有 v71 副本可回退）。
- 部署后首次启动仍建议先跑一场短任务确认日志里 `S2 f=` / `HB f=` 正常、
  且 `Z f=` / `AE f=` / `COMBO f=` / `J f=` 不出现。

## 7. 回退

```
cp 04_RiseAI/out/rai_log_integrity_v71.nro "<游戏目录>/mods/RiseAI_EntryProbe/romfs/nativeNX/plugins/rai_entrylocator_probe.nro"
```

- 回退目标：`04_RiseAI/out/rai_log_integrity_v71.nro`，
  md5 `1d513ec3364f4f270929fd24193ff74b`（本轮已复核），65536 B。
- 源码侧回退：原 `lib.rs` 本就是 v71 且未被改动，无需任何恢复动作；
  若要重新编译 v71，直接在原 `context_probe/` 目录按常规命令重编即可。
