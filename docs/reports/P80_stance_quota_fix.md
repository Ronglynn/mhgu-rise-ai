# P80 · 发现并修复成品版 W4 处境维静默失效（配额审计 → 源码修复 → 重编译部署）

## 0 · 一句话

P80 的 30 分钟日志配额审计**顺带查出一个真实缺陷**：成品版 `MAX_QX=400`，而 `STANCE_CUR/F` 更新原本写在 QX 日志配额分支内；实测每 epoch 有 1237 次 QX 事件 ⇒ 前 400 次（约 32%）之后 W4 处境维停更，`STANCE_TTL=300` 帧后静默退回 `st3`。已把状态更新移出日志分支（等价改造、零新增 hook、零写入），重编译并部署成品 v2。

## 1 · 审计数据（`out/P80_30min_quota_audit.md` / `.json`）

用 v71 实机日志 `game_p54_lite.txt` 的实测密度 + `lib.rs.v71bak` 的配额常量演算：

- 最忙 epoch = 0（f=0..29999），[rai] 行 **4780**；全部 `MAX_*` 配额常量之和 **34184**。
- 单 epoch 打满 / 接近打满的行：`Q 60/60`、`M 40/40`、`X 20/20`、`ZS 2/2`、`E 38/40`、`COMBO 1049/1600`(65.6%)、`AR 490/800`(61.3%)、`QX 1237/2400`(51.5%)。
- 这些是 v53 起的**老诊断配额**，在第一个 epoch 内就会打满 ⇒ 该 epoch 后半段这些行停止输出。它们**不 gate 任何 AI 状态更新**（Q/M/X/E/ZS/COMBO/AR 都只是日志），所以不影响 P79 的 6 项验收（关键行 S/S2/HB/BEAT 有余量、无 epoch 盲区）。
- **`QX` 是唯一例外**：`MAX_QX=400`（成品）而实测 1237 次/epoch ⇒ 32% 后打满，且 stance 更新就在这个分支里。

时长外推（按最忙 epoch 密度、60 fps）：

| 时长 | 帧数 | epoch 数 | 预计 [rai] 行 | MAXLOG 占用 | 是否触顶 |
|---|---:|---:|---:|---:|---|
| 10.5min（P79 实测） | 37,800 | 1.26 | 6,023 | 0.60% | 否 |
| 30min | 108,000 | 3.60 | 17,208 | 1.72% | 否 |
| 60min | 216,000 | 7.20 | 34,416 | 3.44% | 否 |
| 120min | 432,000 | 14.40 | 68,832 | 6.88% | 否 |

MAXLOG=1M 理论可撑 **29.1 小时**。**结构性结论**：配额每 30000 帧重置 ⇒ 任务时长本身不会造成整场停写，唯一随任务时长增长的是总 log 序号；本项由此从「仅算术外推」升级为「实测密度 + 源码常量的静态审计」。这不是 30 分钟实机日志，边界见 §5。

## 2 · 缺陷定位

`lib.rs.v71bak:2337-2361`（成品 `lib.rs` 同结构）：

```rust
if QX_LOG < MAX_QX && LOGN < MAXLOG && heap_ok(a0) && a0 + 0x7400 < HEAP_HI {
    ...  // 计算 kind / t505 / t518，输出 QX 行
    let st_now = ...;                       // ← W4 处境状态
    STANCE_CUR[ssi] = st_now; STANCE_F[ssi] = f;
    STANCE_ANY = st_now; STANCE_ANY_F = f;  // ← 全在日志配额门内
    ...
}
```

`STANCE_CUR/F` 是 `rise_weight_pick()` 的 `stance` 入参来源（`stance_get()`），`W4_STANCE_ENABLE=1`。一旦 QX 配额耗尽：
1. 本 epoch 剩余 68% 时间内 stance 不再刷新；
2. `STANCE_TTL=300` 帧后 `stance_get()` 判为无效，退回 `st3`；
3. W4 的 12 处境分流仍在（hub 维 `END_F/ABN_F/ZONE_F` 在日志块之外），但**处境状态维静默失效**。

P75 已标注「`MAX_QX` 不得置 0，因为 `STANCE_CUR/F` 在 QX 分支内」，但**没有量化**成品 400 配额是否够用；本轮实证：不够。

## 3 · 修复（等价改造）

在 QX 日志 `if` **之前**插入独立只读块，用完全相同的 `ident(a0)` / `a3==2 && a1==0` / `t505` / `t518` 计算 `st_now` 并写 `STANCE_CUR/F/STANCE_ANY*`，然后删除 QX 块内的重复更新。

差异仅在于：**状态更新不再受 `QX_LOG < MAX_QX` 与 `LOGN < MAXLOG` 门控**。其余计算逐字一致，`kind/t505/t518` 仍供 QX 日志与 COMBO ev2 使用。零新增 hook、零内存写入、不改 W1/W2/W3/W4 任何权重或抽选逻辑。

| 项 | 值 |
|---|---|
| 修改文件 | `plug/context_probe/src/lib.rs`（主线）、`plug/context_probe/src/lib.rs.release`（同步） |
| 改后源码 md5 | `28e74de67e8b75e1807644b41041ef89`（两文件一致） |
| `MAX_QX` | **保持 400**（不改日志策略，减少变量）；但 P80 起可置 0 而不影响 W4 |
| 编译 | 复制整目录到 `plug/_release_build/`、删 `target/` 全新编译，1m28s，Exit 0，仅已知 `-z norelro ignored` 警告 |
| 产物 | `out/rai_release_v2.nro`，61,440 B，md5 `c174b191549cc734806ef67b99298520` |

## 4 · 静态校验与部署

- NRO 头：`NRO0`、声明/实际 61440 一致、seg0 `0..40960` / seg1 `40960..57344` / seg2 `57344..61440`、bss 4096，与 v1 同构。
- **6 detour 不变**：`h_matcher / h_emc / h_unify / h_exh / h_stamina / h_start_`。
- 特征串：`RAI v71` / `S2 f=` / `HB f=` 各 1；`Z/AE/COMBO/AR/J/B2 f=` 全 0（探针仍被编译期消除）；`QX f=` 1（保留低频诊断）。
- build_id `6521b255…` ≠ v1 `a9424444…` ⇒ 全新编译，未复用旧 ELF（规避 NOTES.md:199/221 的坑）。
- **已部署**：`mods/RiseAI_EntryProbe/.../rai_entrylocator_probe.nro` ← v2，md5 校验一致。备份 v1 `out/deployed_release_v1_dfab157d.nro`（`dfab157d…`）、v71 探针 `out/deployed_v71_1d513ec3.nro`、`lib.rs.v71bak`。

回退链：v2 → v1（覆盖 `deployed_release_v1_dfab157d.nro`）→ v71 全量探针（覆盖 `deployed_v71_1d513ec3.nro` + `lib.rs.v71bak`），重启游戏生效。

## 5 · 诚实边界

- 修复是**源码级等价改造 + 静态校验**，**没有实机验证 v2 加载与 stance 行为**；成品版关掉了 QX 之外的大部分诊断行，也无法从日志观察 stance。若要实证，需回退探针版、把同一改造编译进探针 NRO、再打一场任务（本轮不安排，用户已明确不希望为验证多打实机）。
- 30 分钟任务仍是静态审计，不是实跑；P79 实机场 10.5 分钟。
- Q/M/X/E/ZS 的老诊断配额仍会在每 epoch 内打满，属**已知且无害**的局部停写；若要彻底干净，可在下一版把这些配额一并调整或置 0（不影响 AI 行为）。
- P75「`MAX_QX` 不得置 0」是修复前的定案，**P80 起已作废**：stance 更新已移出，MAX_QX 现在可以置 0。当前保留 400 仅为低频诊断。

## 6 · 产物

`tools/audit_p80_30min_quota.py`、`out/P80_30min_quota_audit.md` / `.json`、`out/P80_stance_quota_fix.md`（本文）、`out/rai_release_v2.nro`、`out/deployed_release_v1_dfab157d.nro`、`plug/context_probe/src/lib.rs{,.release,.v71bak}`。
