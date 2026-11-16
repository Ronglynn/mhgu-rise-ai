# P55 · v58 = v57 全抽选 + W2 距离档只读探针（2026-11-14 23:45，已部署未实机）

## 0 · 用户要求与结论

用户：「把探针一起做了吧，我一场验证 W1 和距离档探针两个」。

**已做到**：v58 在**不新增 hook、零写入、W1 行为逐字节不变**的前提下，把 W2 距离档只读探针挂进已有的 `h_matcher @0x8E144`。下一场双击 `8_lite_check.bat` 正常打一场，第二份报告同时给出 **W1 验收结论** 与 **W2 数据充足度结论**。

- 6 个 hook 不变（源码 `#[forge::hook]` 计数 = 6），`DRAIN_ENABLE=0` / `PROFILE_RELEASE=1` / `W1_ALL=1` 不变。
- 新增 `W2_PROBE=1` 编译期开关；置 0 即编译回 v57 纯发布版（探针代码被编译器消除）。
- 部署点 md5 与产物一致；游戏进程已确认关闭后才覆盖。

---

## 1 · 为什么这样设计（静态 + 实机双重依据）

`00_Tools/92_MHGU-master/.../docs/reference/formats/emc.md`：

- §3：`0x8E144(ctx, ip, op, mode, value)` 是 EMC **block matcher**，遍历同 op 的 `case` 返回「到选中分支的字节距离」。
- §4：距离/几何 op = `0x0b`(mode 4/14)、`0x17`(mode 6)、`0x57`(mode 14)、`0x5c`(mode 16)、`0x7c`(mode 24)；坐标来自 `sub=*(ctx+0x1428)` 的 `+0x30..0x38`、`+0x40..0x48`、`+0x2e8..0x304`，朝向 `+0x54`。
- §5：mode 5,6,7,15,16,19,20,23,24,25 的阈值 = `case*100`（例 8/10/15 → 800/1000/1500）；mode 4,14,21,22 的阈值来自 float 表；`distance <= threshold` 时命中该 case。

**实机证据**（`out/game_p54_lite_20261114_2301_v56_ZINOGRE.txt`，v56 雷狼龙场）：
80 条 `M` 行里已有 `op=17/md=6`×4、`op=0B/md=4`×2、`op=57/md=14`×1、`op=6A/md=26`×3 —— 距离块确实走 `0x8E144`，但 `MAX_M=40` 被 mode0 状态 switch 吃光，全场几乎没有距离样本。同时 `V` 行 `p5` 值域 0..98（主轨 rand%100），而距离调用的 `p5` 几乎恒 0 ⇒ **a4 不是可直接用的距离值**（value 走 VFP），必须从 `sub` 几何字段取。

⇒ v58 用**独立配额**的 `Z`/`ZP` 两类行专门记录距离调用，不抢 M 行配额。

---

## 2 · 实现

在 `h_matcher` 的 `f==0 / GATE_LIVE` 早返回之后、主轨判断之前插入：

```rust
if W2_PROBE == 1 && dist_mode(mode) {
    dist_probe(f, a0, a1, op, mode, a4, r);
}
```

`dist_mode()` 只放行 §5 的几何 mode `{4,5,6,7,14,15,16,19,20,21,22,23,24,25,26}`，显式排除 mode 0/1（状态/加权轮盘赌）与 11/18（bitmask）。距离 mode 与 `main_track(mode==1)` 互斥 ⇒ **不触碰 W1 抽选主干**。

**Z 行**（每次距离调用，独立配额 `MAX_Z=1200`/epoch）：

```
Z f op md val ip blk nc t0 t1 t2 t3 hit ret st3 log
```

- `val` = a4 原始位（实机多为 0，仅留证）；`ip`/`blk` = 脚本地址 / 块起点
- `t0..t3` = 复用 v35 的 `find_begin()` + `scan_cases()` 读到的 case 阈值序列；begin 定位失败时向前 64B 回退找 `op,sub=0`，且必须扫出 ≥2 个 case 才采信
- `hit` = 由 `ret`（到选中 case 的字节距离）反推的**命中档位索引**，`bestd>MATCH_TOL` 记 −1
- `st3` = 复用 `mon_state()` 的三态只读判定

**ZP 行**（每 4 次 Z 行一条，`MAX_ZP=300`/epoch）：`sub` 的 `a30/a34/a38/a40/a44/a48`（3D/XZ 两组坐标 f32 原始位）、`e0/e2/e4`（`+0x2E8..` 六 float 代表）、`hd`（`+0x54` heading）、`cmd=*(mon+0x2588)`、`ent=*(cmd+0x78)`（脚本 entry 基址，用于 `ip-ent` 离线对齐）。判读端用 `struct.unpack('<f')` 解 float 算 3D/XZ 距离。

**安全**：`mon_ok = heap_ok(mon) && mon+0x2600 < HEAP_HI`、`sub+0x310 < HEAP_HI` 双重越界保护；所有读取都是 `read_volatile`；不调用游戏函数、不改 `r`/参数/内存。`Z_LOG/ZP_LOG` 随 30000 帧 epoch 重置，`Z_N` 累计不重置。`W2_PROBE=0` 时整段被编译期消除。

---

## 3 · 验证与部署

| 项 | 结果 |
|---|---|
| 产物 | `out/rai_w1all_w2probe_v58.nro`，**53248 B**，md5 **`12a0d422ed555eba57139fb628c0ee4c`** |
| 部署 | `mods/RiseAI_EntryProbe/romfs/nativeNX/plugins/rai_entrylocator_probe.nro`，md5 一致；部署前 `NO_GAME_PROCESS` |
| 编译 | PASS（仅 ld `-z norelro` 常规警告）；`RAI v58` / `W2 Z line` / `Z f=` / `ZP f=` 齐全；`J f=` / `W f=` 计数 0；detour=6 |
| 冒烟 | **PASS=30 / FAIL=0 / SKIP=0**（`Z=600 ZP=150`、6 种距离 mode、case 解析 100%、命中 100%、几何 f32 100% 可解、`wall=48/wnok=41`） |
| 兼容 | `analyze_v57_release.py` 跑 v58 冒烟 **20/0/0**；v58 判读脚本跑 v57/v56/v55 冒烟 + 3 份实机日志，**6 路降级 6/0/2 全通、零误报零崩溃** |
| 判读 | 新增 `tools/analyze_v58_release.py`（30 项：基础 6 + 发布配置 5 + W1 9 + W2 10 含诊断）、`tools/make_v58_smoke.py` |
| 脚本 | `8_lite_check.bat` → v58 标题 / `TOOL2=analyze_v58_release.py` / 双结论提示；`7_P54_启动并抓日志.bat` → STEP 58 + v58 说明 + 回退改 v57；CRLF **80 / 171**、bareLF **0** |
| 守卫 | `6_启动并抓日志.bat` md5 `7361445f989b…` 未动；`mods/load_order.txt` 未动；游戏资源/其它 mod 未动 |
| 回退 | `v57 1aed8640a4bc592c7f1169c375e81710` → v56 `63f37b8e…` → v55 → v54 → v50 |

---

## 4 · 这一场怎么验（用户操作）

双击 `8_lite_check.bat`，**正常打一场**（不会自动疲惫），正常关游戏后看第二份报告：

- **W1 验收**：`wall>0 / wnok>0 / wnok<=wall`、`w3/w4/wt` 形状占比、无 `R/W/J/G`、`gdone=0`、V 行 `st3→vd` / `wm→wk` 零违例、零 FATAL、`live=1`/`hub=15`。
- **W2 数据**：`Z`/`ZP` 行数、距离 mode 覆盖、`nc>=2`（case 阈值解析率）、`hit>=0`（档位可定位率）、t 序列非全 0、ZP 几何 f32 可解、`ent!=0`、3D/XZ 距离分位数、`ip-ent` 脚本内偏移、按 md/st3 的档位分布。
- 判读脚本会直接打印「**W2 数据充足，可进入档位映射**」或「需补一轮探针」。
- **体感**：动作多样性、连段完整性、有无卡动作（v57 的 A 改动仍在本版里，是首次实机）。

---

## 5 · 边界（如实说明）

1. **v58 只是探针，不实现 W2 档位加权**。这一场的目标是采数据，不是把 W1 升级成「状态×距离档」。对齐后（用离线 `target_dist_rot` 4 档 + ZP 几何阈值）才做 W1 的档位扩展。
2. **未实机**。Z 行的 `find_begin/scan_cases` 复用 op02 的解析路径，对距离块成功率未知（新增 64B 回退 + `nc>=2` 校验兜底）；若实机 `nc>=2` 比例低，下一轮补距离块专用 begin 定位。
3. `a4` 在距离调用几乎恒 0 ⇒ **档位判定必须靠 `hit` + ZP 几何 + 离线表**，不能靠 value。
4. `ent=*(cmd+0x78)` 是否等于当前 entry 基址未定案；`ip-ent` 只是诊断量，对齐时需复核。
5. Rise 侧 5 档几何阈值（`em131_00_range_data.user.2`）仍未抽取，GU 只能做 4 档相对映射；`_IsActionEnd` 门控、12 处境 Hub、领地争夺仍未实现。
6. 发布前把 `W2_PROBE=0` 编译回纯发布版（v59）：探针日志会让单场日志从发布级涨到约 0.2 MB，属临时诊断开销。
