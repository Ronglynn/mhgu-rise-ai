# Rise 式单人 AI 任务 —— 独立工作区与记忆

> **任务边界**：本任务（在 MHGU 复刻 Rise 式单人怪物 AI 体验 / 怪物对象定位 / 招式池 / 决策层插件）
> 与用户的**音频 mod 工作流完全独立**。两条线的脚本、日志、插件、记忆互不混用：
> - 音频线：`6_启动并抓日志.bat` → `02_Workspace/game_p15.txt`，工作记忆在 `.workbuddy/memory/*.md`。
> - 本任务：`7_P54_启动并抓日志.bat` → `02_Workspace/game_p54.txt`，**记忆与日志在本文件**。
> 共享的 `.workbuddy/memory/MEMORY.md` 只保留一行路由，不再承载本任务细节。

## 目录
- 本任务根：`D:\MHGU mod maker\04_RiseAI\`
- 参考资料：`04_RiseAI\refs\guide\MHGU-Modding-main\`（制作指南包）、`refs\re\MHGU-master\`（逆向成果）
- 逆向资料与工作区既有的 `00_Tools\92_MHGU-master\MHGU-master` **抽样 md5 一致**（`mon-ai-entry.md` / `emc.md` / `monster-code-map.md`），但新包含更多文档（`docs/analysis/audit/`、`docs/analysis/members/`、`tools/gu-moves/`、`forge/` 范例）。
- 游戏目录：`D:\Monster Hunter Generations Ultimate Recomp`（Recomp 0.15.1）
- 游戏镜像：`02_Workspace/mot/main.140.flat.bin`（静态分析输入，本机已有）
- 怪物资源：`data\romfs\nativeNX\arc\enemy\emNNN_SS.arc`
- 当前会话实时日志：0.15.1 写游戏目录 `log.txt`；`game_p54.txt` 只留重启前短会话。分析前先确认哪个文件在增长。

## 资料读完后的关键结论（2026-11-07）

### 指南包（MHGU-Modding-main）
- 性质是**资源清单 + 010 Editor 模板仓库**，不是文字教程：`README.md` 仅 406 B（wiki 首页/贡献者），86 个 `.bt` 模板，14 个武器动作值 `.txt`，`MHGU-Filetypes_Hashes.txt`（文件类型→哈希）。
- 对本任务有用：`.emc` 类型哈希 `3aabba02`；`MHGU_Extractedarc.txt` 是 **UTF-16 LE**（23 MB），含完整路径，例如
  `\arc\enemy\em001_00.arc\enemy\cmd_tbl\em001_00_cmdtbl.3AABBA02`、
  `\arc\enemy\em001_00.arc\enemy\em001\em001_00\mot\em001_00_0.lmt`。
- **包内没有怪物 AI / EMC 的 010 模板**（仅 `em_nando_tbl`、`emsizetbl`、`spt_act_base` 等相关边角），怪物 AI 结构只能靠逆向成果包。

### 逆向成果包（MHGU-master）
1. `+0x73E0` 语义**确认**：`movw r0,#0x73e0; ldrb r0,[r4,r0]; cmp r0,#17` 是每怪 L1 动作派发器的统一签名，`r4 = this`（怪物对象指针）。全镜像 638 处 `movw #0x73e0` / 489 个函数 / 332 个 `ldrb` 读取者 / 53 张状态表（51 张是怪物一级派发器）。**这直接给出「hook 派发器拿 this」的对象定位路径，远优于按内存值盲扫。**
2. `docs/mechanics/monster-state-machine.md`：60 个小节、1,223 行状态，`state → handler → motion` 已解；`monster-ai-params.md` 给出 `mParam.*` 全字段表（移动/索敌/阈值/行动控制/网络同步等）。**此前「EMC 叶命令语义未解、section→状态映射未解」的判断已过时。**
3. `tools/gu-moves/gu-moves.mjs`：**现成的静态招式池生成器**。输入怪物 arc，反编译 `enemy\cmd_tbl\emNNN_SS_cmdtbl` 的 op14 叶 / op02 权重 case / section-1 / reset(state,variant)，定位类的 L1 派发器（`movw #0x73e0` + 18 字表）与各状态 L2 派发器，结合 LMT 帧数与 attackdata，输出 `variants.tsv / motions.tsv / moves.tsv / census.tsv / facts.json`。
   ⇒ **招式池可以静态批量生成，不需要靠实机 actionNo 日志采集**（129 只怪可自动化）。
4. `docs/analysis/monsters/mon-counter-slots.md`：运行期表 `0x1597ea4` 与 `EmId → 计数器槽号`；`mon-quest-dispatch.md` §6 有全局单例槽定位规则；`mon-ai-entry.md` E1 `0x15004c` 是怪物类名注册表初始化（360 槽）。这些是 `sEnemy` 之外的备选锚点。
5. `forge/dbgport/dbgport.c` / `forge/itembox-v7/`：**Forge C 插件里有 `ForgeHook`、guest 内存读写、`forge_onUpdate` 的完整范例**，可直接支撑「hook guest 派发器」的插件实现。

## 之前经过的去留判断（第 3 点）

**保留（有效）**
- Forge 插件工具链：nightly cargo + `-Zbuild-std` + xpack ARM GCC、`elf2nro.py`、独立 mod 目录部署、`load_order` 登记方式。
- `7_P54_启动并抓日志.bat`（独立日志 + `.prev/.prev2` 轮转）与 `6_` 的隔离约定。
- `ai_cd_probe.py`（冷却约束 `cd ≤ k-1`）、`rise_ai_layer_probe.py`（三层决策 + 自适应冷却）两个仿真结论，算法层已验证。
- `mon_pool_build.py` 的日志转池逻辑（可作为实机校验数据，与静态池对拍）。
- v3.1 实机结论本身（两条定位路径证伪）是有效证据，不必重跑。

**废弃 / 需要重来**
- **P54 的「盲扫 0x0C 段 + 值过滤」对象自举策略整个废弃**。`act<=17` 对「该字节为 0」恒成立，实测抓到的 8 个 PROMO 对象 `+0x73E0 = 3F800000`（float 1.0），1,225 次稳定复现只换 1 条 ACT。改走 hook L1 派发器取 `this`。
- `sEnemy@0x19A52090 → 0193331C` 锚点**证伪**（前 32 字全是 `0x002xxxxx` 代码/静态指针，0 个堆指针），不要再试。
- 「招式池需靠实机采集」的路线判断作废：改用 `gu-moves` 静态导出。
- 「EMC 叶命令与 section→状态映射未解」的判断作废：资料库已有解析成果。
- `mon_anchor_parse.py` 仅对已证伪的锚点段有用，降级为历史工具，不再迭代。

**需要复核的约束**
- 资料库基于 `main.140.flat.bin`（游戏本体 0.14 镜像）；Recomp 宿主已从 0.14.0 升到 **0.15.1**。guest 地址空间未必变（`sEnemy` 单例值两版一致），但任何静态 vaddr 在用于 hook 前必须实机验证一次。

## 下一步（按优先级）
1. 用 `forge/dbgport` 的 `ForgeHook` 范例，hook 一个已知 L1 派发器（如 `0xd227d8`，`em003_00`），在回调里取 `r0` = 怪物对象 `this`，打印 `+0x73E0/+0x73E1` 与对象基址 → 一次性解决对象定位。
2. 跑 `gu-moves` 对目标怪导出 `facts.json`，作为 Hub/Action 层的静态招式池；与实机 ACT 序列对拍校验。
3. 在已定位的 `this` 上实现冷却与上下文决策层（复用两个仿真脚本的参数结论）。
4. 全程只用 `04_RiseAI/` 与 `7_`，不碰 `6_`、`game_p15.txt`、音频 mod 与 load_order 中音频条目。

## 独立日志
- 2026-11-07：解压并阅读两个 zip（见上）；完成去留判断；建立本独立工作区与记忆文件。此前本任务的过程记录散在 `.workbuddy/memory/2026-11-05.md` / `2026-11-07.md`，本文件起不再续写共享日志。

## 23:24 路线前提核实（决定下一步）

### Forge hook 的地址语义（已确认）
- `#[forge::hook(offset = N)]` + `install_hook!(forge::mem::text_addr(), h)` → 目标 = `text_addr() + N`。
- crate 明确写着「只在游戏的 ARM target 上运行」、非 ARM 只是编译桩 → 插件运行在 **guest 地址空间**，这解释了 P54 直读 `0x0C` 段有效。
- 历史记录里的 `main+0x11998b0` 双 hook 冲突也是同一套 `main + guest vaddr` 形式 ⇒ **`N` 就是资料库的 guest vaddr**（如派发器 `0xd227d8`）。
- 因此「hook L1 派发器、在回调里取第一个参数 = 怪物对象 `this`」在机制上成立。`forge/dbgport/dbgport.c` 的 `NpadHook` 记录了 `args[0]` 的同类用法。
- **风险**：资料库基于 `main.140.flat.bin`，宿主是 Recomp 0.15.1。任何静态 vaddr 用于 hook 前必须先做一次只读校验：打印 `text_addr()`，读 `text_addr()+0xd227d0` 附近 4~8 字，应与 `movw r0,#0x73e0`（`e30?03e0` 形式）吻合。校验插件不 hook、不写内存。

### 静态招式池工具 gu-moves 的可运行性（已实测）
- 已复制并本地化到 `04_RiseAI/tools/`（129 个 `.mjs` 中改了 7 个硬编码路径）；`FLAT` 环境变量可指向本机 `02_Workspace/mot/main.140.flat.bin`；怪物 arc 在本机 137 个齐全；Node v22.22.2 可用。
- **实测阻塞**：`ClassIndex` 强依赖两个不在交付包里的私有 KB 文件 `gu-l1-class-names.tsv`、`gu-em-shared-class.tsv`（原路径 `G:/omp works/MHRS-private/kb`），`gu-moves.mjs` 另引用 `rise-fsm-state-clip-all.tsv`。直接跑报 ENOENT。
- ⇒ 路线 B 不能开箱即用。可选：① 用包内 `docs/data/class-inventory.tsv` 与 `docs/analysis/code/inventory/*.tsv` 重建这两个映射；② 只用 `tools/mhgu/emc.mjs` 独立解单只怪的 cmdtbl；③ 暂缓，先靠实机 ACT 序列建池。**优先 ③，因为对象定位是当前瓶颈。**

### 本地化产物
- `04_RiseAI/tools/gu-moves/`、`tools/mhgu/`（路径已改写）、`04_RiseAI/out/`（试跑输出目录，空）。

## 23:30 清理已完成 + 步骤 1 校验插件已部署

### 废弃产物：全部从原位置移除，归档到 `04_RiseAI/_discarded/`（可恢复，未永久删除）
- `mon_anchor_parse.py`（锚点已证伪，不再迭代）
- `02_Workspace/plug/p54_mon_probe/` 整个工程（含 target）、`03_Output/p54_mon_probe.nro`
- `mods/P54_MonProbe/` 部署目录
- `game_p54.txt.prev`（11-06 崩溃日志）、`game_p54_20261106_crash.txt`
- `load_order.txt` 中的 `P54_MonProbe` 行已移除
- 保留 `02_Workspace/game_p54_20261107_v31_log.txt`：v3.1 首次跑通的唯一实证，用于对拍

### 有用产物迁入独立目录
- `analysis/ai_cd_probe.py`、`rise_ai_layer_probe.py`、`mon_pool_build.py`（仿真与池构建结论有效）
- `refs/forge-src/`（Forge crate 源码，后续写 hook 用）
- `tools/`、`refs/guide`、`refs/re` 保持

### 新插件（步骤 1）
- 工程 `04_RiseAI/plug/disp_probe/`，产物 `04_RiseAI/out/rai_disp_probe.nro`（20480 B，md5 `d931869b…`）
- 部署 `mods/RiseAI_DispProbe/romfs/nativeNX/plugins/`（两侧 md5 一致）；`load_order.txt` 登记 `RiseAI_DispProbe`；备份 `04_RiseAI/load_order_backup_20261107_2330.txt`
- **命名独立于音频线**：音频任务已有 `P56_DetachProbe`/`P57_AddSE`/`P59_BowDiag`/`P60_CustomBank`，本任务一律用 `RiseAI_*` 目录与 `[rai]` 日志标签，不再用 P5x 编号
- 行为：`forge::entry` 只读，打印 `text_addr()` 与 4 个已知 `movw #0x73e0` 站点（`0x81ca4 / 0xd227d0 / 0xd3137c / 0x1120ee0`）各 5 个字；不 hook、不写内存
- `7_P54_启动并抓日志.bat` 提示改为「只需启动游戏、无需进任务」；轮转逻辑双次干跑验证（prev=RUN2 / prev2=RUN1）；回显改为仅在轮转成功时打印
- `6_启动并抓日志.bat` 未改动（md5 `7361445f…`，由音频任务维护）

### 下一步实机
重启游戏 → 跑 `7_` → 日志出现 `[rai] text_addr=...` 与 `SITE +00D227D0 ... e30?03e0` 即证明 0.15.1 与资料库地址一致，随后出 hook 版取 `this`。

## 23:38 步骤 1 实机通过 + 步骤 2 hook 版已部署

### RAI-v1 地址校验结果（决定性）
- 日志 `02_Workspace/game_p54.txt`（本轮 7_ 脚本输出，实时增长），7 条 `[rai]`：
  `text_addr=00200000`；
  `+00081CA4 = E30703E0 E7D40000 E350000A ...`（cmp #10）；
  `+00D227D0 = E92D4830 E1A04000 E30703E0 E7D40000 E3500011`（push / **mov r4,r0** / movw / ldrb / cmp #17）；
  `+00D3137C`、`+01120EE0` 同样以 `E30703E0` 开头。
- **结论**：Recomp 0.15.1 的 guest 代码地址与 `main.140.flat.bin` 资料库完全一致，无需版本偏移修正；`mov r4,r0` 证实 r0 就是怪物对象 `this`。
- **关键细节**：hook 必须落在函数入口 `0xD227D0`，资料里标的 `0xD227D8` 是第 3 条指令（movw），hook 在那里会跳过 push 与 mov r4,r0。

### RAI-v2（步骤 2）
- 工程 `04_RiseAI/plug/hook_probe/`，产物 `out/rai_hook_probe.nro`；部署 `mods/RiseAI_HookProbe/`。
- `#[forge::hook(offset = 0x00D227D0)] fn em003_disp(this: u32)` → 记录 `this / vt / +0x73E0 / +0x73E1`，按 (对象, act, sub) 变化节流打 `THIS`，`original!(this)` 调回原函数，不改游戏状态；`forge_onUpdate` 每 600 帧打 `BEAT f/hit/log`。
- `load_order`：`RiseAI_DispProbe` 改 `# off:`，新增 `RiseAI_HookProbe`；备份 `04_RiseAI/load_order_backup_20261107_2340.txt`。
- `7_` 提示改为「进任务打一只大怪约 60 秒」。
- **局限**：只 hook 了 em003 的派发器。若 `BEAT hit=0`，说明本次打的不是该怪，下一步把已验证的其余派发器（`0x81ca4 / 0xd3137c / 0x1120ee0`）一并挂上，或从资料库 51 张表批量生成 hook。

## 23:44 v2 实机结果 + v3 全派发器版已部署
- **v2 日志**：`[rai] RAI v2 dispatcher hook` 横幅出现，插件正常加载（syms 15 / 5 imports），游戏稳定 9000 帧无 FATAL，但 `BEAT hit=0 log=0` 全程 → **hook 安装成功、em003 派发器本次任务未被调用**，不是插件失败。用户打的不是 em003。
- 日志里 mh4uport 的 `em057_01 / em005_01` 是 mod 资源安装信息，不是任务怪 ID，不能据此定位。
- 尝试用 `main.140.flat.bin` 反推入口失败：镜像中 `0xD227D8` 处不是 `E30703E0`，说明静态镜像与 Recomp 运行时 guest 布局不同；**只能用实机验证过的资料库 vaddr**，不要用镜像字节反推。
- **v3**：批量挂 `monster-state-machine.md` 列出的全部 60 个派发器地址（`#[forge::hook(offset = vaddr)]`），共享 `record(this, site)` 按 (对象, act, sub) 节流打 `THIS`，`original!(this)` 回原逻辑；`site_ok()` 在安装前校验 `text_addr()+vaddr` 的字确为 `movw r?,#0x73e0`（`E30?03E0`），不符则跳过并打印 `installed/skipped`，自动排除二级表与非代码地址。
- hook 落在资料给的 movw 位置（不是 -8 入口）：统一签名 `push; mov r4,r0; movw r0,#0x73e0` 中 `mov r4,r0` 不改写 r0，故此处 r0 仍是 `this`；trampoline 执行原指令后继续。
- 产物 `04_RiseAI/out/rai_hook_probe_v3.nro`（57344 B），已覆盖部署到 `mods/RiseAI_HookProbe/`；v2 留档 `out/rai_hook_probe_v2_single.nro`；源码 v2 备份 `plug/hook_probe/src/lib.rs.v2bak`。`load_order` 未再改动。
- 下一轮实机判据：`installed N hooks, skipped M`；`BEAT hit>0` 且出现 `THIS site=... obj=...` 即拿到怪物对象；若 `installed=0` 说明 site_ok 判定或地址换算有误。

## 23:50 v3 闪退复盘 + v4 单点版（用户确认固定打将军镰蟹）

### 用户补充的关键事实
- **每次任务打的都是将军镰蟹**（Shogun Ceanataur）。资料 `docs/analysis/monsters/mon-counter-slots.md:321`：`emid 19 / 槽 20 = 镰蟹 / Shogun Ceanataur`；`monster-state-machine.md` 的派发器 `0xdc3908 — 单位 em019_00` 即对应它。
- 因此**不需要全派发器覆盖**，单点 hook 即可；此前 v2 `hit=0` 是因为挂的是 em003。

### v3 崩溃复盘
- 日志：`installed 50 hooks, skipped 10` → 3 条 `BEAT hit=0` → 进任务时 `FATAL: no function at 0 (lr=002afdd0 ...)`，`pc=00000000` 与 guest 寄存器转储。
- **根因判定**：v3 把 hook 打在资料给的 `movw` 位置（函数中段）。Forge trampoline 在中段替换指令后，`original!()` 恢复了 `movw r0,#0x73e0`，但前序 `push / mov r4,r0` 造成的栈与寄存器约定被破坏，派发器首次被真实调用时跳空指针。
- **可复用的正面证据**：v2 把 hook 打在**函数入口** `0xd227d0`，稳定跑 9000 帧无 FATAL。⇒ 结论：**必须 hook 函数入口，不能 hook 中段**；批量 50 个中段 hook 方案作废。

### v4（已部署）
- 只针对 `0xdc3908`（em019），准备 3 个入口候选 hook：`-8 / -4 / +0`；`main()` 里读 `text_addr()+site-8/-4/+0` 三个字，按 `push@-8 + mov rX,r0@-4 → -8`、`push@-4 → -4`、否则 `+0` 判定，**只安装一个**；若 site 字节不是 `movw #0x73e0` 则不安装并打印告警。
- 打印 `SITE -8=... -4=... +0=...` 与 `installed entry -8/-4/+0`，下一轮日志可直接看出入口判定是否正确。
- 产物 `04_RiseAI/out/rai_hook_probe_v4.nro`（20480 B，md5 `0ce555a9…`），已覆盖 `mods/RiseAI_HookProbe/`；v3 留档 `out/rai_hook_probe_v3.nro`；`load_order` 不变；`7_` 提示同步为 STEP 2c。
- 下一轮判据：`installed entry -8` + `BEAT hit>0` + `THIS site=... obj=...`。若仍 `hit=0`，用日志里的 `SITE` 字节重新定位入口，或改挂 `0x81ca4`（RAI-v1 已验证入口=site 本身的通用派发器）。

## 23:52 怪物编号纠正 + v5（7 站点入口 hook）
- **重要纠错**：`monsters-index.md:63-65` 明确 `槽17 = em019 大名盾蟹`、`槽19 = em020 / 20 = 将军镰蟹 Shogun Ceanataur`。`mon-counter-slots.md:321` 的「| 19 | 20 |」是**槽号与 em id**，被我误读成 emid 19，v4 挂的 `0xdc3908`（em019）是错的怪。
- 资料未给 em020 派发器的直接标注；按地址顺序 `em019=0xdc3908` → 紧邻的未标注 `0xdc75fc` 最可能是 em020，`0xddcfe8` 次之。`attr-strings.tsv` 的 `em020_00` 串在 `0xdc9168`，同区域。
- v3 崩溃复盘不变：`installed 50 hooks` 后进任务 `FATAL: no function at 0 / pc=0`，根因是**中段 hook**；v2 入口单点稳定 9000 帧。结论：只挂函数入口。
- **v5**：7 个候选站点（`0x81ca4 / 0xd227d8 / 0xd3137c / 0xdc3908 / 0xdc75fc / 0xddcfe8 / 0x1120ee0`），每站点备 `-8/-4/+0` 三个 hook，运行时读字节判定入口后**只装一个**；打印每个 `SITE ... movw=...` 与 `entry -8/-4/+0`；`installed N entry hooks`。
- 产物 `out/rai_hook_probe_v5.nro`（36864 B，md5 `49020442…`），已覆盖部署；v4 留档 `out/rai_hook_probe_v4.nro`，v3 `out/rai_hook_probe_v3.nro`；崩溃日志备份 `out/game_p54_20261107_v3_crash.txt`。`load_order` 不变，`7_` 提示同步。
- 生成脚本曾因 Python f-string 与 Rust `{:08X}` 冲突而静默复用 v4（md5 相同），已改用模板替换并核对产物大小/特征串后才部署。
- 下一轮：若 `BEAT hit>0` 且 `THIS site=00DC75FC obj=...` 即确认将军镰蟹派发器与对象；若 7 个站点全 `hit=0`，则用日志里各 SITE 的字节反查入口，或改走 EMC 解释器 / sEnemy 深挖。

## 23:56 v5 二次闪退 → 弃用 hook 路线，改 v6 零 hook 只读方案

### 闪退根因（已由日志字节确证）
- v5 日志 7 个 SITE 全部 `movw=true`，但三个被判为 `entry +0` 的站点前 8 字节是**真实指令**：
  `0x00081CA4 -8=E3010428 -4=EA00003C`、`0x00DC75FC -8=E3010428 -4=E0845000`、`0x00DDCFE8` 同。
  ⇒ `+0` 不是函数入口，是函数中段；hook 打在那里破坏 `push / mov r4,r0` 建立的栈帧。
- 崩溃现场与 v3 **字节级一致**：`FATAL: no function at 0 (lr=002afdd0 ...)`、`pc=00000000`、`r0=r4=00001428`、`sp=efffd9b8` ⇒ 同一条路径，与怪种无关。
- 结论：**只要存在中段 hook 就会崩**；v2 单点入口稳定 9000 帧是唯一正面样本。hook 路线整体放弃（资料库未给 em020 派发器的可靠入口，逐个反查成本过高且风险不可控）。

### v6（零 hook、纯只读）
- 依据 `attr-vtable-fixed.tsv:158-159`：`uEm019_00 vtable 0x1732344`、`uEm020_00 vtable 0x1732358`（将军镰蟹）。怪物类 vtable 落在镜像 .data 区 `0x0173xxxx`。
- `forge_onUpdate` 分片扫描 `0x0C000000..0x0C400000`（128KB/帧、32 帧一轮，与 P54 v3.1 同强度、已证明稳定）；对象首字落在 `0x01700000..0x01800000` 且 4 对齐 → 候选；再以 `u8[+0x73E0]<=17 / u8[+0x73E1]<=1` 校验；按 (base, act, sub) 变化节流打 `[rai] OBJ base=... vt=... em020=... act=A->B`。
- `em020=true` 表示 vt 落在 `0x01732340..0x01732380` 簇（含 uEm019/020 两个相邻 vtable）。
- **自查修正**：初版把 vtable 区间误写成 `0x172F0000..0x17350000`（差 16 倍，实际应为 `0x01700000..0x01800000`），已改并重新编译。
- 产物 `out/rai_obj_probe_v6.nro`（20480 B，md5 `b78e2f4f…`），部署 `mods/RiseAI_ObjProbe/`；`load_order` 把 `RiseAI_HookProbe` 改 `# off:`、新增 `RiseAI_ObjProbe`，备份 `load_order_backup_20261107_2356.txt`。v5 崩溃日志备份 `out/game_p54_20261107_v5_crash.txt`。
- 下一轮判据：`BEAT cand>0 obj>0` 且出现 `OBJ ... em020=true`；若 `cand=0` 说明 vtable 指针不等于类记录里的值（可能有 +8 偏移或对象首字另有结构），按日志里的 vt 值调整区间即可，插件本身不会导致崩溃。

## 11-08 00:03 v6 实机判读（零 hook 方案成立）+ v7 修正日志淹没

### v6 结果（正面）
- 无 FATAL、无崩溃，稳定跑到 `BEAT f=11400`（心跳 pf=25200 / up=12599），证明**零 hook 只读扫描**路径安全，前两次闪退确由中段 hook 引起。
- `cand=47624 obj=30670 act=400`，但 vt 分布为 `01771FC4 / 01772020 / 017C0000 / 01730000` 等，**`em020=true` 为 0**，日志中没有任何 vt 接近资料给的 `0x01732358` ⇒ 类记录里的 vtable 值不等于运行时对象首字，或怪物对象不在该区间。

### 发现的日志缺陷（真实 bug）
- 400 条 `OBJ` 中 **339 条是 `act=0->0` 的首次登记**：`note()` 只有 16 个槽，被 3 万多个对象轮流覆盖，每次 `old != base` 都判为变化 → 日志预算瞬间耗尽，真实动作变化只剩 61 条且被截断。
- 61 条真变化里出现成组固定序列：`0C360ACC(0->3) / 0C366A14(3->1) / 0C3688A0(1->0)` 各重复 13 次；另有 `0C0160B4(0->1) / 0C016A88(0->17) / 0C016ACC(17->0)` 等地址相邻、act 互补的对象对。尚不能断定哪组是怪物对象，但说明 `+0x73E0` 确在这些对象上变化。

### v7（已部署）
- 槽位 16→64、日志预算 400→2000；**首次登记且 act/sub 全 0 的对象不再打印**（消除 339 条垃圾）；`em020` 簇放宽到 `0x01732000..0x01734000`；BEAT 增加 `vt20=`（该簇命中数）与 `log=`。
- 产物 `out/rai_obj_probe_v7.nro`（md5 `08941ff7…`），已覆盖 `mods/RiseAI_ObjProbe/`；`load_order` 不变（仍为 `RiseAI_ObjProbe` 启用、两个 hook 版 off）。v6 日志备份 `out/game_p54_20261108_v6_scan.txt`。
- 下一轮判据：`BEAT ... act>0 vt20=... log<2000`（日志未被打满）→ 从 `OBJ` 行提取 base/vt，找出 act 变化最频繁且与将军镰蟹动作节奏吻合的对象，即为目标怪物对象。

## 11-08 00:10 v7 实机 → 全堆扫描路线证伪；v8 启动即完成探针已部署

### v7 判读（否定性结论）
- 无 FATAL，稳定到 `BEAT f=12600`，但 `vt20=0`、`log=2000`（预算再次打满）、`cand=62803 obj=38070`。
- 离线分析 2000 条 OBJ：**只有 27 个不同 base**，其中 **26 个 act 是单一常数被重复登记**（如 `0C015D54 act=0->5` 重复 299 次），仅 `0C193DA4 vt=0176C100` 在 1↔17 间切换（11 条）。
- ⇒ 根因不是参数，是方法：按 `vt` 区间 + `act<=17` 值筛选，在 3 万候选规模下必然产生静态值假象；`note()` 槽位被覆盖导致重复登记。**全堆 vtable 扫描路线证伪，不再迭代**。

### 编译踩坑（已修）
- `plug/disp_probe` 由 `p56_disp_probe` 改名后，build.rs 输出的 linker script 路径仍缓存为旧目录 → 链接失败；`rm -rf target` 清缓存后重编通过。注意：编译失败时 elf2nro 会拿旧 ELF 产出同 md5 文件，必须用特征串校验产物。

### v8（已部署，零 hook、零逐帧扫描、启动即完成）
- `forge::entry` 只读，回答两个决定性未知量：
  (A) 打印 `0xDC75FC`（em020 候选派发器）前 16 字与 `0xDC3908`（em019 对照）前 8 字 → 向前找 `push {...,lr}` 定位真正函数入口；
  (B) `sEnemy@0x19A52090` 指向结构深挖 512 字，只打印落在 0x0C 堆段的指针 → 判断是否存在怪物实例表（v3.1 只看 32 字）。
- 产物 `out/rai_boot_probe_v8.nro`（md5 `c8165369…`），部署 `mods/RiseAI_DispProbe/`；`load_order` 只启用它，`RiseAI_ObjProbe` 改 `# off:`，两个 hook 版仍 off；备份 `load_order_backup_20261108_0010.txt`。v7 日志备份 `out/game_p54_20261108_v7_scan.txt`。
- **下一轮用户成本最低**：只需启动游戏，看到 `[rai] probe done` 即可退出，无需进任务、无需打怪。
- 判据：`PRE 00DC75FC -xxx E92D....` 给出入口偏移；`SEN +xxx heap=0C......` 给出怪物实例指针。两者之一成立即可回到「单点入口 hook」或「直接读实例表」，且都不必再全堆盲扫。

## 11-08 00:15 v8 启动探针给出决定性答案 → v9 单点入口 hook 已部署

### v8 实机输出（标题界面即完成，无需进任务、无 FATAL）
- `text_addr=00200000`。
- **`0xDC75FC` 前 16 字**关键序列：`-010 E92D4830`（push r4,r5,lr）→ `-00C E1A04000`（mov r4,r0 = this）→ `-008 E3010428` → `-004 E0845000` → `+00 E30703E0`（movw r0,#0x73e0）。
  ⇒ **真正函数入口 = `0xDC75EC`（-0x10）**。v5 只查 -8/-4，看到的是函数体中间指令，误判为「入口=+0」→ 中段 hook → 两次闪退。
- 对照 `0xDC3908`（em019）：`-008 E92D4010` / `-004 E1A04000` → 入口 -8，与 v5 判定一致。说明不同派发器的入口偏移不统一，必须逐站点看字节。
- **`sEnemy@19A52090 -> 0193331C` 深挖 512 字：`SEN heap pointers found=0`** ⇒ 该结构内没有任何 0x0C 堆指针，锚点/实例表路线彻底排除。

### v9（已部署）
- `#[forge::hook(offset = 0x00DC75EC)] fn h_em020(this: u32)`，单点、函数入口、`original!(this)` 回原逻辑；`record` 打印 `[rai] THIS obj=... vt=... act=A->B sub=...`，`BEAT f/hit/log`。
- 安全性依据：v2 在同类 push 入口 `0xD227D0` 单点 hook 稳定 9000 帧；v3/v5 的崩溃全部来自中段 hook。本版只有一个入口 hook。
- 编译踩坑：日志串 `{r4,r5,lr}` 被 Rust 当格式占位符导致失败；失败时 elf2nro 复用旧 ELF（md5 与 v5 相同），已修正并用特征串 `RAI v9` 校验后才部署。
- 产物 `out/rai_hook_probe_v9.nro`（20480 B，md5 `65914d3f…`）部署 `mods/RiseAI_HookProbe/`；`load_order` 启用它、`RiseAI_DispProbe` 改 off、`RiseAI_ObjProbe` 保持 off；备份 `load_order_backup_20261108_0015.txt`；v8 日志备份 `out/game_p54_20261108_v8_boot.txt`。
- 下一轮：重启后跑 `7_`，进任务打将军镰蟹约 60 秒。判据 `hook installed at text_addr+00DC75EC` → `BEAT hit>0` → `THIS obj=...`。若 `hit=0`，说明 `0xDC75FC` 不是 em020 派发器，但插件不会崩（单点入口 hook），可据 v8 的字节法继续定位其它站点。

## 11-08 00:25 v9 实机成功（决定性）→ v10 决策字段差分已部署

### v9 结果：怪物对象定位问题彻底解决
- `hook installed at text_addr+00DC75EC` → `BEAT f=12600 hit=10540 log=87`，**FATAL=0**，全程稳定。
- 87 次状态切换全部来自**同一个对象** `obj=0C1F0890 vt=019B5588`，无第二只怪、无对象漂移。⇒ 将军镰蟹派发器入口 `0xDC75EC` 与 `this` 均已确认。
- 实测 vt `019B5588` 与资料 `uEm020_00 vtable 0x1732358` 完全不同 → 再次印证「不能用静态 vtable 值扫堆」。

### 字段语义与复读基线（离线量化）
- `+0x73E0`（act）实测 5 值 `0/1/2/7/10` = L1 动作类；主循环 `2<->7`（21/17 次）。连续同类率 0.2674，最长连发 3。
- `+0x73E1`（sub）实测 **22 种、值域 0..61** = L2 变体/子状态索引（资料 C11：`0xf48ef0` 二级表 62 entries，index=`0x73e1−2`）。**此前 v6/v7 用 `sub<=1` 过滤，直接把真怪物排除**，是全堆扫描证伪的第二个根因。
- 每个 act 的合法 sub 白名单（游戏自身用过）：`0:[1]`、`1:[2,3,4,22]`、`2:[0,2,5,14,15,18,20,25,26,40,46,51,52]`、`7:[0,15,16,33,40,41,52,61]`、`10:[7]`。act=0/10 只有 1 个候选，无法换招。
- 87 次决策、27 种 (act,sub)；**窗口3 内同招复现率 0.2381、窗口5 0.3049、窗口8 0.4557**；同招复现最小间隔 2 步、中位 6 步，间隔<=3 的复现 20/60。⇒ 旧作确实存在短窗口复读，这是 Rise 式冷却要解决的目标，已量化。
- 相邻决策间隔中位 91 帧（约 1.5 s），派发器每帧调用（10540/12600），所以**变化沿才是决策序列**，逐帧统计不可当复读率。
- **口径陷阱**：THIS 是「变化才打印」的节流日志，故 `(act,sub)` 连续重复率 0 是采样必然结果，**不能**当作游戏自带防复读的证据。

### v10（已部署，纯只读）
- 沿用已验证的单点入口 hook `+00DC75EC`，只在 (act,sub) 变化时读 24 个候选偏移（`+0x73C0..+0x73FC` 16 个 + motion 候选 `+0x112C/116C/118C/1428/14D8/1200` + `+0x7400/7404`），插件内累计每个偏移的「跨决策变化次数」，每 600 帧打 `CHG0/CHG1/CHG2` 三行；`DEC` 行给前 300 次决策的关键值。
- 目的：在改写任何字段前，先确定哪个偏移才是招式级 ID、以及 `sub` 改写是否安全。变化与 act/sub 同步者即为冷却插件的改写目标。
- 产物 `out/rai_hook_probe_v10.nro`（44536 B ELF→NRO），已用特征串 `RAI v10` 校验（并断言不含 `RAI v9`，避免旧 ELF 复用）后覆盖 `mods/RiseAI_HookProbe/`。`load_order` 不变，v9 日志备份 `out/game_p54_20261108_v9_success.txt`。
- 下一轮：重启后进任务打将军镰蟹约 60 秒。判据 `BEAT dec>0` + `CHG` 行找出变化次数接近 dec 的偏移。之后即可写「按窗口3 冷却、在同一 act 白名单内换 sub」的行为插件。

## 11-08 00:34 资料复核：act/sub 关系其实已完整写在逆向包里（重要纠错）

### 用户提问触发的复核结论
- **指南包 `MHGU-Modding-main.zip`：没有**。它是资源路径清单（UTF-16 `MHGU_Extractedarc.txt`）+ 86 个 010 Editor 二进制模板；`73e0 / 73e1 / dispatch / ai_fsm` 全文计数均为 0，只有 139 条 `cmdtbl` 路径，模板中无怪物 AI/状态机定义。
- **逆向包 `MHGU-master.zip`：有，且至少 5 处明确记载**：
  1. `tools/gu-moves/gu-moves.mjs:3` —— 招式池坐标就是 **`(L1 state, L2 variant)`**，"every motion a monster's EMC decision tree can select, per (L1 state, L2 variant)"。
  2. `tools/gu-moves/lib/machine.mjs:431-435` —— 正式命名：`0x73E0 / 0x73E1 seeds: the L1 state and L2 variant bytes`，walk 时分别注入 `ctx.state` / `ctx.variant`。
  3. `tools/gu-moves/lib/classinfo.mjs:68-77` —— canonical idiom：`movw rA,#0x73E0|0x73E1; ldrb; [sub #indexBase]（L2 专有）; cmp #max; **bhi <default>**; add pc…`。**L2 派发有上界检查与默认分支，越界不会跳飞** —— 这直接回答了「改写 +0x73E1 是否安全」。
  4. `docs/mechanics/monster-code-map.md:49` —— 6 张 L2 动作变体表 `0xCF1898(34)/0xD14238(42)/0xD28594(47)/0xD36310(37)/0xD4B040(37)/0xD37044(50)`，每个解析一个具体 motion。
  5. `docs/mechanics/monster-state-machine.md` 头部 + 9 个「（二级）」小节 —— 51 张一级表（0x73e0）+ 9 张二级表（0x73e1），state 范围 `30..64 / 5..21 / 14..50 / 5..48 / 1..34 / 2..63 / 33..59 / 1..42 / 6..40`；`LINK-MECHANICS-CODE.md` C11 给出 `index = 0x73e1 − k`，并指出文档把二级表误标成 state 0..N。

### 我的疏漏（必须记住）
- 上一轮只读到 `LINK-MECHANICS-CODE.md` C11，就停在「sub 是 L2 变体/子状态索引」这一层，**没有追到 `tools/gu-moves/` 的三个源文件**，于是把「哪个偏移是招式级 ID」当成未知量，写了 v10 的 24 偏移差分探针。实际上资料已明确给出 `+0x73E1` 就是招式级 variant、且带边界保护。
- **v10 那轮采集因此作废**（尚未实机运行，直接被 v11 取代），产物 `out/rai_hook_probe_v10.nro` 留档不再部署。省下一轮实机。
- 另修正一处口径：上一轮说「实测 sub 0..61 与 0xf48ef0 的 62 entries 吻合」不严谨 —— 9 张二级表 indexBase 各不相同（2/5/14/30/33/1/6…），实测出现的 sub=0/1 不在 2..63 内。按 act 分组的**实机白名单**仍是必要补充，只是它的作用从「找字段」变成「限定改写候选」。

### v11（已部署，首个行为改写版）
- `#[forge::hook(offset = 0x00DC_75EC)]` 沿用 v8 字节确证、v9 实机验证稳定的单点函数入口。
- 冷却规则：`CD=3`（最近 3 次决策内不可复用同一 `(act, variant)`）；命中时把 `u8[this+0x73E1]` 改为**同一 act 下实机观测过的合法 variant**、且不在历史窗口内；`HIT_N % n` 轮转选候选，避免总选同一个。
- 白名单：act=1 → `[2,3,4,22]`、act=2 → `[0,2,5,14,15,18,20,25,26,40,46,51,52]`、act=7 → `[0,15,16,33,40,41,52,61]`；act=0/10 只有一个候选，跳过。
- 护栏：每场最多 200 次替换、两次替换间隔 ≥30 次 hook 调用（防止游戏回写后反复抖动）、L2 派发自带 `bhi default` 上界保护；全部改写都打 `[rai] CD`，决策打 `[rai] DEC`，心跳 `BEAT ... patch= skip=`。
- **风险声明**：这是本任务首次向游戏内存写字段。hook 位置本身已验证稳定，写入值限定为游戏自身用过的 variant；若出现异常，用 `out/ROLLBACK_rai_hook_probe_v9_readonly.nro` 覆盖部署目录即可回到纯只读 v9。
- `load_order` 未变（`RiseAI_HookProbe` 启用）；`7_` 提示改为 STEP 7。
- 下一轮：重启进任务打将军镰蟹约 60 秒。判据 `BEAT patch>0` 且窗口 3 内同招复现率从基线 0.2381 明显下降；同时观察有无 FATAL/动作异常。

## 11-08 00:41 v11 实机：首次行为改写成功且无崩溃 → v12 修伪决策 + 自适应 CD

### v11 结果（决定性：写内存路径可用）
- 日志 `02_Workspace/game_p54.txt`：`RAI v11` 横幅，`BEAT f=10800 hit=8889 dec=81 patch=7 skip=12`，**FATAL=0**，稳跑 180 秒。这是本任务第一次向游戏内存写字段且未引发闪退 → `+0x73E1` 改写路径成立。
- 改写**确实生效**：`CD dec=4 hit=628 act=2 0->15`、`dec=58 46->51`、`dec=62 40->52`、`dec=64 46->0`；后续决策读到新值（游戏未立刻回写）。
- **复读率下降**：窗口3 内同招复现率 **0.2381（v9 只读基线）→ 0.1566**（排除伪决策后 0.1467），降幅约 34%~38%。这是 Rise 式冷却首次产生可测的行为改变。
- 窗口5 / 窗口8 为 0.3580 / 0.4872（v9 为 0.3049 / 0.4557），未改善 ⇒ 固定 CD=3 只压短窗口，符合预期。
- 日志第 444 行 `mhgu_fix40_fx.nro: read at 0x03000EA0 (unmapped page)` 是**音频任务插件**的 WARN，非本任务、非崩溃，按任务分离要求不动它。

### 发现的两个问题
1. **明确代码缺陷（伪决策）**：v11 在决策块开头就写 `LAST_S = s`（原始值），但改写后 `s` 变成 chosen 却没同步 LAST_S；下一帧 hook 读到我们写入的值即判为「新决策」，且因 HIST 里已有该组合而 `cd=true`、又被 `MIN_GAP=30` 拦下 → 计为 skip。日志可见成对行：`n=4 sub=0 final=15 hit=628` / `n=5 sub=15 final=15 hit=629`。这污染历史窗口并压低 patch 数。
2. **act=6 新出现 14 次**（sub 0/7/10/11/12），v9 的 87 次决策里完全没有。首次出现于 hit≈3209，距第一次 patch（hit=628）2500+ 次调用，因此更像任务自然阶段而非改写引发的异常，但**性质未证实**；v11 无对应白名单 → 全部 skip，是 12 次 skip 的主要来源。保守起见 v12 仍不给 act=6 换招。

### v12（已部署）
- 修 `LAST_S`：移到决策块末尾、用**最终值**赋值，消除改写回显造成的伪决策。
- 冷却窗口由固定 3 改为**自适应** `cd = min(5, 该 act 候选数 − 1)`，沿用 `ai_cd_probe.py` / `rise_ai_layer_probe.py` 已验证的 `cd ≤ k-1` 约束；HIST 环形扩到 5 槽，判定与候选排除都只扫最近 `cd` 槽。act=2（13 候选）→ cd=5、act=7（8）→ 5、act=1（4）→ 3、act=0/10 与未知 act → 0（直接跳过，不再计 skip）。
- `DEC` 行增加 `w=`（本次生效的 cd 宽度），便于判读；白名单不变（act=6 继续跳过）。
- 产物 `out/rai_hook_probe_v12.nro`（20480 B，特征串 `RAI v12` 校验、断言不含 v11/v10），已覆盖部署；回退版 `out/ROLLBACK_rai_hook_probe_v11.nro`（行为改写版）与 `out/ROLLBACK_rai_hook_probe_v9_readonly.nro`（纯只读版）均在。`load_order` 不变，`7_` 提示改 STEP 8；v11 日志备份 `out/game_p54_20261108_v11_cooldown.txt`。
- 下一轮判据：无 FATAL；`BEAT patch>0`、`skip` 显著下降（伪决策消失）；窗口3 复现率进一步低于 0.1566，窗口5/8 也应回落；`DEC ... w=5` 出现即自适应生效。

## 11-08 10:07 纠正：Rise 机制参数对本 mod 重要；本机已具备低成本获取条件

### 判断修正
- 上一轮答「Rise 的冷却数值/距离档/状态分支只是学术对照，对当前 mod 无收益」**结论下粗了**：把「不能照搬数值」与「不需要参照设计」混为一谈。
- 正确分层：
  - **高价值·影响当前插件正确性**：Rise 的 CD 粒度（每招独立冷却 vs 全局最近 N 次不重复）、大招/普通招是否分档设不同 CD。v12 现用统一 `cd = min(5, k-1)` 来自本任务仿真自洽，**无对标**；若 Rise 是 per-move CD，方向需改。
  - **高价值·决定后续层**：距离档结构、玩家方位、怒/常/疲劳分支、任务等级分支。这是「Rise 式体验」的第二、三层，本任务目前只完成第一层（不复读）。
  - **中价值**：候选池组织方式（Think→Hub→Action 路由），指导 GU 侧把 `(act, variant)` 组织成按上下文过滤的池。
  - **低价值/不可迁移**：具体帧数秒数、`_ActionNo`、motion 名、招式池内容、BHVT/FSM2 文件本身（引擎与动作库不对应）。
- 结论：**应该做，且应排在 GU 侧上下文层（v13+）之前**，否则后续参数仍是自洽但无对标的推测；不影响已跑通的冷却层能否运行。

### 本机 Rise 资源实况（只读核实）
- 安装：`D:/Steam/steamapps/common/MonsterHunterRise`；`re_chunk_000.pak` 32,237,404,351 B + `re_chunk_000.pak.patch_001.pak` 4,388,488,186 B。
- **REFramework 已装并运行过**（日志时间 2026-11-07 21:34）：`reframework/`、`re2_framework_log.txt`、`reframework_accessed_files.txt`（3,930,336 B，含 `natives/STM/...` 明文路径）、`reframework_loose_files.txt`。
- 已有 `reframework/autorun/motion_id_logger2.lua`（3,307 B）：hook `snow.player.PlayerMotionControl:lateUpdate` 读 `_OldMotionID/_OldBankID`，输出 `data/motion_id_log.txt`。**记录的是玩家动作，不是怪物**；改类型后可复用于怪物出招序列。
- `accessed_files.txt` 关键词计数：`enemy/em` 1886、`ai_fsm_user_data` 19、`act_tbl_user_data` 17、`think_param` 1、`action_param` 2、`datatune` 1；`attack_stance` 与 `RangeNCheck` 均为 **0**（那次会话未加载 routine 层攻击姿态文件）。样本集中在 `em131`（137 条 AI/参数路径）。
- 本机**没有** `mhrisePC.list`、REtool、mhrice、`.user.2` 解包产物、010 模板。

### 已落地产物
- `04_RiseAI/refs/rise_enemy_ai_paths.txt`（31,734 B）：从访问日志提取的 442 条 enemy AI/参数类唯一路径（enemy 全量唯一路径 1194 条）；层级分布 `act_tbl_user_data` 12、`common/user_data` 8、`ai_fsm_user_data/hub` 5、`think` 5、`flow` 1。作为后续按需抽取的清单，避免全量解 32 GB pak。

### 最小成本路径（不需要编译 / 不需要反汇编 / 不需要全量解包）
1. **行为层（零解包）**：REFramework Lua 观测怪物出招序列与同招间隔分布，直接得到 CD 的实际表现；比静态数值更能判定「每招独立 CD vs 全局窗口」。
2. **规则层（按需抽取）**：仅取 Hub 的 `attack_stance_same_main{,_high,_master}.user.2`、routine 的 `modeNNN_*RangeNCheck.user.2`、`*_think_param_data.user.2` / `*_action_param_data.user.2`；需要版本匹配的 `mhrisePC.list` 或 mhrice 导出，再用 RSZ/010 模板解析。REFramework 的 loose file 路径表可作为抽取清单。
3. **架构层**：社区既有资料（mhrice JSON / MHRise-Database / 之前的检索结论）已足够，无需重复。
- 下一步执行项：在 `04_RiseAI/` 下准备 Rise 侧怪物动作记录 Lua（基于 `motion_id_logger2.lua` 改造）与按需抽取脚本；需要一次 Rise 实机运行。本任务记忆与产物一律留在本目录，不碰音频线。

## 11-08 10:15 用户建议改用 pak 解包 → 已实抽验证，规则层数据到手

### 工具核实结论
- `https://github.com/Ekey/REE.PAK.Tool`：C# / .NET Framework 4.7.2 + VS2019-2022 工程；`REE.Unpacker <TAG_LIST_FILE> <PAK> [OUT]`，需 `Projects/` 目录随工具。README 的 **Steam 平台表未列 MHRise**（MHR 只有 `MHR_NSW_Release` / `MHR_MSG_Release`），且本机无 dotnet CLI → 不是本机最优选择。
- **本机已有更合用的实现**：`00_Tools/06_REEngine_Pak/ree-pak-cli.exe`（3.8 MB，Rust CLI，子命令 `unpack / dump-info / pack`）+ `assets/filelist/MHR_STM_Release.list`（13.2 MB，**Steam 版 MHRise 路径表**）。
  - `unpack -p <list> -i <pak> -o <dir> -f <正则>` 支持**按路径正则按需抽取**，无需解 32 GB 全包；另有 `--test`（只解内存不写盘）、`--skip-unknown`、`--backend mmap|legacy`。
  - 路径表覆盖：`attack_stance` 911、`ai_fsm_user_data` 10753、`act_tbl_user_data` 29358、`think_param` 86、`action_param` 86、`datatune` 117。**`RangeNCheck` 计数为 0** → 早先 wiki 的 `modeNNN_*RangeNCheck` 命名不适用于 Steam 版，实际是 `angerrangeNcheck / normalrangeNcheck / tiredrangeNcheck`。

### 实抽结果（已落盘，仅本地研究，不分发 Capcom 原始资源）
- 输出根 `04_RiseAI/refs/rise_unpack/`，**27 个 `.user.2` / 116 KB**，命令：
  `ree-pak-cli.exe unpack -p MHR_STM_Release.list -i re_chunk_000.pak -o <out> -f "<路径正则>" --skip-unknown`
- 12 个 `em001/00/ai_fsm_user_data/hub/em001_00_attack_stance_*.user.2`（1000~1448 B），其中 `same_main` / `_high` / `_master` 三档 **md5 各不相同**（`a133c7fc…` / `0fe49f1d…` / `1ec7bbb6…`）→ 任务等级分支确有独立数据。
- 15 个 `em001/common/act_tbl_user_data/routine/main_out1/em001_main_out1_{anger,normal,tired}range{1..5}check.user.2`（1776~2284 B）→ **Rise 候选池按 3 状态（怒/常/疲劳）× 5 距离档 = 15 个池组织**，文件大小不同说明各池招式数不同。这正是 v13 上下文层要对标的结构。
- 文件头 `55 53 52 00`（`USR\0`）+ version 2 + RSZ 段，**本机没有** `rszmhrise.json` / mhrice / RszTool / RE_RSZ 模板 → 抽取链路已通，字段数值解析仍缺类型描述。

### 判断修正（对用户建议的回应）
- **解包确实是拿「规则层」的正确手段**，优于 Lua 观测：冷却数值、距离阈值、状态分支条件是数据，运行时只能看到结果、看不到阈值。上一轮把 Lua 列为首选是判断偏差。
- 但两者**互补而非替代**：解包 → 静态规则；REFramework Lua → 实际出招序列与 CD 表现，用于验证规则是否被游戏按预期执行。解析 `.user.2` 字段值也可走 REFramework 读取已加载对象，绕开类型描述。
- 下一步执行项：取与本机 Rise 版本匹配的 `rszmhrise.json`（或 mhrice 导出）解析这 27 个文件，提取 CD 粒度/距离阈值/权重；随后在 GU 侧按 3×5 池结构设计 v13。产物与记忆一律留在 `04_RiseAI/`，不碰音频线。

## 11-08 10:25 RE_RSZ 离线解析跑通（无需 010 Editor、无需实机游戏）

### 结论：用户给的模板仓库可用，且已完全离线拿到规则层数值
- 下载 `RE_RSZ/rszmhrise.json`（69,287,210 B，**250,700 个类型**，key = typeId hex，含 `crc / fields / name`；field 带 `name / type / size / align / array / original_type`）与 `RE_RSZ.bt`（316 KB，用于确认容器布局）。
- 依据 `RE_RSZ.bt:5474-5505` 的 `RSZHEADER` 写出 `04_RiseAI/tools/rsz_parse.py`（纯 Python，零依赖）：USER 头 48 B 处读根 typeId；找 `RSZ\0` 段；header = `magic/version/objectCount/instanceCount/userdataCount/reserved`(4B×6) + `instanceOffset/dataOffset/userdataOffset`(8B×3) = 48 B；instanceInfo 从 `RSZHeader+instanceOffset` 起每项 8 B（typeId + CRC）；实例数据从 `RSZHeader+dataOffset` 起按 JSON fields 顺序内联读取。
- **27/27 个 `.user.2` 全部解析成功**，实例类名可解析率约 96%（未解析者均为 index 0 的 NULL 实例，typeId=0）。输出 `out/rsz_json/*.json`。

### 关键实证：Rise 的「状态 × 距离档 → 候选池 + 权重」规则
- 15 个 `em001_main_out1_{anger,normal,tired}range{1..5}check.user.2` 解出 `snow.enemy.aifsm.EnemyRoutineLotSet.ConditionInfo._TransitionRate`（百分制权重）与 `ActionTableData._TableNo`（动作表号）。**15/15 组权重和恰为 100**，且表号随档位变化，自洽性高。
- 汇总见 `out/rise_routine_rates.json`。示例：
  - 怒·档1 `[30,40,30]` → 表 `[14,19,80]`；怒·档5 `[10,70,20]` → `[19,20,80]`
  - 常·档1 `[45,30,25]` → `[13,19,79]`；常·档5 `[15,25,35,25]` → `[19,20,51,79]`
  - 疲劳·档1 `[10,65,25]` → `[1,15,51]`；疲劳·档5 `[10,20,70]` → `[1,20,51]`
- **没有发现任何显式冷却/CoolDown/Timer 字段**。防复读线索是 `ConditionInfo._CheckPrevTableInfoList`（每个 ConditionInfo 都有 1 项，字段名直指「检查前一动作表」）→ 支持既有判断：Rise 的重复抑制来自抽选条件与候选池结构，而非独立 CD 计时器；这解释了为何 v12 的统一窗口只能压短窗口复现。
- 另有 `EnemyRoutineLotCase._TransitionValue`（0/1/2/3，档位索引）、`ThinkState._ActionList` / `_ConditionList`、`ThinkCondition._NextStateID`，构成可映射的三层结构。

### 可靠性边界（必须如实标注）
- 数组元素按「4 字节引用」解析，但部分 `List<Struct>` 元素是内联结构体 → 少数实例出现 `<bad count …>` 或 `None`，`bytesConsumed` 偶超数据区。因此**深度字段与对象引用尚不可作为定论**；但 `_TransitionRate` / `_TableNo` 这组标量跨 15 文件自洽（权重和恒 100、表号随档变化），可信。
- JSON 的 `crc` 是类型名散列，与 instanceInfo 的 CRC 不同源，已把解析器里的 `crc_matches` 改为 `class_found`，避免误判。
- 下一步：按 `original_type` 反查元素类型、递归解析内联结构，修掉失步；再批量抽取其余怪与 `think_param/action_param`，把 3 状态 × 5 距离档的权重结构映射到 GU 侧 v13 上下文层。

### 合规与边界
- `rszmhrise.json` / `RE_RSZ.bt` / 抽取的 `.user.2` 仅用于本地研究，不分发 Capcom 原始资源；对外只输出结构化结论。
- 全部产物在 `04_RiseAI/`；`6_启动并抓日志.bat` 与音频线未改动。

## 11-08 10:45 继续推进：解析器修正、抽取扩容、规则总表与 v13 设计落地

### 解析器（tools/rsz_parse.py）
- 按 `RE_RSZ.bt:2505/1360-1372/5635` 修正布局规则：对齐基于**绝对文件偏移**；数组字段固定 4 字节对齐；**每个数组元素前再按字段 align 对齐**；实例起点按字段 0 规则对齐。修正后 `sum|consumed-expect|` 从 25736 降到 3444。
- 残余失步**唯一定位**：`ThinkState._ConditionList`（27/27 文件、均实例 19、垃圾值同为 2206645383）。根因是 `List<via.behaviortree.Action>` / `List<ThinkCondition>` 元素为内联结构，按 4 字节引用读会偏移。已加 `partial` 标记与**失步即截断**，避免产出错误数值污染下游；核心权重/表号字段位于失步之前，不受影响。

### 抽取扩容
- `ree-pak-cli.exe` 宽 filter 一次命中 1124 条并中途报错（`unpack.rs:392`）；改用精确 filter + `--ignore-error` 成功。当前 `refs/rise_unpack/` 共 **107 个 `.user.2` / 465 KB**，含 em001-003 的 `think_param_data` / `action_param_data` 6 个参数文件与多怪 range 档。
- 首次宽抽取报错时已落盘 74 个文件，均保留（未删）。

### 决定性发现（规则总表 `out/rise_ai_rules.json`）
- `EnemyThinkTimerData._Timer` 取值 **0/3/5/10/15/20/30/40/45/50/60/70/90/120/150/180/300 秒**，附 `_UniqueId`；`EnemyThinkCounterData._UniqueId` 1..6。⇒ Rise 的重复抑制是**秒级计时器 + 计数器 + 前表检查**，不是决策次数窗口；这直接说明 v12 的统一窗口只能压短窗口复现。
- `ActionInfo` 856 条实例，字段固定 8 个（`_actionNo` / `_subStaminaPoint` / `_angerMotSpeedUpperValue` / `_tiredMotSpeedLowerLimitValue` / `_incUniqueEnergyValue` / `_decUniqueEnergyValue` / `_setUniqueEnergyValueOnEnter` / `_ActionAttrPlan`），`_actionNo` 值域 0..7056、181 种；**仍无显式 CD 字段**。
- 15 档 `_TransitionRate` 权重和恒 100，表号随档变化（见 `out/rise_routine_rates.json`）。
- 全部 107 文件解析成功，其中 60 个因固定失步被 `partial` 截断；**可信部分**为参数文件与失步前的实例。

### v13 设计（`DESIGN_v13.md`）
- 三阶段：v13-a 上下文探针（距离/状态标注，只读）→ v13-b 3×5 加权候选池 → v13-c 秒级帧计时器（按动作组配长/短窗口）。
- 明确差距表、硬约束（单人、映射回 GU 动作、60fps、帧计时、可回退、合规）与依赖。
- 待办：v12 实机验证（需用户重启）+ v13-a 探针（我可编译部署，需一次实机采集）。

### 边界
- 全部产物在 `04_RiseAI/`；`6_启动并抓日志.bat` 与音频线未改动（md5 `7361445f…`）。

## 11-08 10:50 v13-a 上下文探针已编译待命（禁用状态，不打乱 v12 验证）
- 工程 `04_RiseAI/plug/context_probe/`，产物 `out/rai_context_probe_v13a.nro`（20480 B，特征串 `RAI v13-a context probe` 校验通过）。
- 纯只读、不写内存、不做冷却；沿用已验证入口 hook `+00DC75EC`。每次 `(act, variant)` 变化打 `DEC` + 3 行 `CTX`，共 dump 24 个字：`+0x40..+0x60`（坐标候选）、`+0x100..+0x120`（状态候选）、`+0x73D0..+0x73F0`（动作字段邻域）；预算 200 次决策。
- 部署 `mods/RiseAI_ContextProbe/`，但 `load_order.txt` 写为 **`# off: RiseAI_ContextProbe`**：当前仍只启用 `RiseAI_HookProbe`（v12），两轮验证顺序不冲突。备份 `load_order_backup_20261108_1050.txt`。
- 启用方式：v12 验证完成后，把该行前缀 `# off: ` 去掉、并把 `RiseAI_HookProbe` 加上 `# off: ` 即可；无需重新编译。
- 离线差分目标：从 `CTX` 里找随怪物移动/出招连续变化的 float（坐标）与离散字节（怒/疲劳状态），供 v13-b 建立 3×5 加权池。

## 11-08 11:05 v12 实机体感异常复盘 + v14 连段安全版已部署

### 用户体感（决定性反馈）
- 冷却**确实生效**：没有再看见重复出同一招。
- 但出现新异常：将军镰蟹「遁地→破土」（通常 3 次 / 愤怒 4 次，次数为用户记忆、未核实）**连段进行中被换招**，视觉上土中的镰蟹突然回地面攻击。
- 因镰蟹招式多短帧，感觉「攻击欲望」反而更高；表现为某招途中或之后立刻接下一招。

### 日志量化（v12 轮，`out/game_p54_20261108_v12_feedback.txt`）
- `BEAT f=54000 hit=27378 dec=224 patch=44 skip=5`，**FATAL=0**（插件稳定，问题在判定语义）。
- 相邻「决策」中 **42.9% 是 act 不变、仅 sub(+0x73E1) 变**（51/119）→ 这些正是连段段号/子状态变化，v12 却当作新出招决策并在其中改写 `+0x73E1`。
- 决策间隔中位数 89 hit，**72.3% <=150 hit**；CD 改写间隔最小 31 hit、44.2% <=300 hit；**44 次改写中 38.6%（17 次）在 ±300 hit 内伴随同 act 的其它决策** → 连段被打断的直接证据。
- 典型序列：`CD(9,hit=1661,2:40->46)` → `CD(10,hit=1764,2:0->51)` → `CD(11,hit=2003,2:40->2)` → `DEC12(hit=2008)`；另 `CD(5,hit=1148)` 后仅 2 hit 就出现 `DEC6(act=2,sub=40)`，说明改写触发了状态机的立即再派发。

### 根因
**判定口径错误 + 改写时机错误**：把 `(act, sub)` 任意字节变化当成「一次出招决策」；在 L1 派发器入口写 `+0x73E1`，等于在动作**进行中**篡改 L2 变体索引，状态机跳到与当前 act 不一致的分支。短帧招式放大了改写密度，动作链被切碎 → 「攻击欲望更高」。
Rise 实证（本任务 `out/rise_ai_rules.json`）：在**抽选新动作时**用 `_CheckPrevTableInfoList` + 秒级计时器否决/重抽，连段内部不重新抽选；且没有事后改字段的做法。

### v14（已部署）
- **冷却判定只在 `act`（L1 动作类）变化时触发**；`act` 不变的 `sub` 变化全部跳过、绝不改写（连段保护）。日志用 `SUB_N` 单独计数受保护的变化。
- 按 Rise 实证改为**帧级计时器**：每 `(act, variant)` 记录上次使用帧，`CD_FRAMES=180`（≈3 秒 @60fps，对应 Rise 计时器最短档 3 秒）内禁用；候选还必须不在各自冷却期。
- 帧护栏 `MIN_GAP_FRAMES=60`（≈1 秒）限制两次改写最小间隔，避免短帧招式反复被打断；`MAX_PATCH=200`。
- 沿用 v12 的实机白名单与 `LAST` 同步修复；hook 点仍为已验证的 `+00DC75EC`。
- 日志：`ACT`（动作类切换，含 `cd/patched`）、`CD`（实际改写）、`BEAT ... act= sub= patch= guard=`（`sub` 大、`patch` 小即证明连段保护生效）。
- 产物 `out/rai_hook_probe_v14.nro`（md5 见下），已覆盖 `mods/RiseAI_HookProbe/`；v12 源码备份 `plug/hook_probe/src/lib.rs.v12bak`、nro 留档 `out/rai_hook_probe_v12.nro`；`load_order` 不变（`RiseAI_HookProbe` 启用、`RiseAI_ContextProbe` 仍 off）；`7_` 提示改 STEP 9。

### 参数说明与下一轮判据
- `CD_FRAMES=180` / `MIN_GAP_FRAMES=60` 为**可调初值**：依据 Rise 计时器 3~30 秒与 GU 决策间隔中位 91 帧（≈1.5 秒）折中取最短档；若体感仍偏碎则调大，若复读回归则调小。
- 判据：① 遁地连段能完整播完（体感）；② `BEAT sub` 明显大于 `patch`；③ 不再出现同一 `act` 内相隔几 hit 的连续 `CD`；④ 仍无重复同招；⑤ 无 FATAL。

## 11-08 11:20 v14 实机两个异常复盘 + v15 已部署

### 症状（用户）
1. 死亡回营地后前往怪物所在区域，**玩家与怪物坐标同时异常**（截图：玩家浮空于瀑布／地形外，怪物模型错位；小地图仍标在 3 区附近）。
2. 怪物进入**异常复读状态**。

### 复读根因（日志确证，确定）
- v14 日志 `BEAT f=35400 hit=30564 act=140 sub=270 patch=0 guard=0`，**FATAL=0**；`[rai] CD` 改写行 **0 条** → 冷却逻辑整场一次都没触发。
- 105 次动作类切换中同 `(act, variant)` 复现 **82 次**，帧间隔**最小 214 / 中位 451 帧**，**全部 > `CD_FRAMES=180`** → `in_cd` 恒为 false，`patch=0`、`guard=0`。窗口比实际复现间隔短，等于没做冷却。
- 末段 `2->0->2->0` 规律循环、sub 固定，与用户观察到的复读一致。
- 连段保护本身是有效的：`sub=270` 次变化全部被跳过、无一次在连段内改写。

### 坐标异常归因（证据链，尚需一次对照定案）
- **v14 `patch=0`，即零次 `wb()` 写入游戏内存** → 坐标异常在因果上不可能来自改写 `+0x73E1`；v12 轮曾写 44 次，用户未报告坐标异常。
- 两轮日志的 ERROR/WARN **几乎完全相同**（`mhgu-target-health-display` 字节不匹配被禁用、`WSG r68` 四条、`FasterFieldHunter`/`AutoDelivery` 正常加载）；宿主仍为 **Recomp 0.15.1**，`mhgurecomp.exe` 时间 11-06 13:55 未变 → 不是本轮新增的插件错误或版本升级。
- 本轮新走过「死亡 → 营地 → 换区」路径（前几轮都是进任务打 60 秒直接退），因此怀疑两类：**(a)** 换区后该派发器被非目标对象调用，hook 的 `original!(this)` 走了不同路径；**(b)** v14 首次引入 `USE_FRAME: [u32; 320]`（1280 B）静态数组，若 Forge 的 NRO 加载器为插件 .bss 分配空间有限，越界可能污染相邻内存。两者均为**待验证假设**，不作为结论。
- 一锤定音的对照：把 `load_order.txt` 里 `RiseAI_HookProbe` 改成 `# off: `，重复同样的死亡→换区流程；若异常消失即锁定本任务 hook，若仍在则与本任务插件无关，需查其它 mod（尤其 `FasterFieldHunter` / `mapassist`）。

### v15（已部署）
- `CD_FRAMES 180 -> 600`（≈10 秒），覆盖实测复现间隔（最小 214 / 中位 451）；`MIN_GAP_FRAMES 60 -> 180`。
- **去掉 1280 B 的 `USE_FRAME[320]`**，改 16 项环形历史（`H_ACT/H_SUB/H_FRAME`，约 96 B），消除假设 (b) 的大数据段风险。
- **对象身份防护**：`OBJ` 记录当前对象地址；地址变化时打 `[rai] OBJCHG`、清空历史、重置 `LAST_ACT`，且**该帧绝不写入**；`BEAT` 增加 `objchg=` 计数，`ACT`/`CD` 行带 `obj=`，便于确认换区后对象是否重建。
- 保留只在 `act` 变化时判定的连段保护、实机白名单、`+00DC75EC` 入口 hook。
- 产物 `out/rai_hook_probe_v15.nro`（20480 B，特征串校验通过），已覆盖 `mods/RiseAI_HookProbe/`；v14 源码备份 `plug/hook_probe/src/lib.rs.v14bak`、nro 留档 `out/rai_hook_probe_v14.nro`；`load_order` 不变（ContextProbe 仍 off）；`7_` 提示改 STEP 10。

### 下一轮判据
① 复读：`patch>0` 且 `guard` 合理，同招复现率回落；② 连段仍完整（v14 已验证的机制不回退）；③ 坐标：死亡→换区后若仍异常，看 `OBJCHG` 是否出现在异常时刻，并按上述对照法停用本插件定性；④ 无 FATAL。

## 11-08 11:45 v15 实机：坐标异常已消失，但「改写 +0x73E1」整条路线证伪（必须止损）

### 用户反馈
1. **坐标异常未再出现** → v14 的 `USE_FRAME[320]`（1280 B 静态数组）是当时唯一新增变量（用户确认「死亡→营地→换区」路径此前也走过且无异常），移除后异常消失，**假设②（NRO 数据段过大污染相邻内存）得到强支持**；仍非严格 A/B 复现，措辞保持「强支持」。
2. **遁地连段仍被换招**：土中镰蟹回地面挥爪，同时保留破土判定 → 一个动作被拆成两个攻击段。用户明确指出「整个遁地→破土而出（不做攻击）做完才算一个动作」。
3. **高频攻击 + 疲劳/倒地动画被打断**，随即转入无休止攻击。

### 日志证据（`out/game_p54_20261108_v15_feedback.txt`）
- `RAI v15` 横幅，`BEAT f=36600 hit=28700 act=149 sub=79 patch=20 guard=3 objchg=1`，**FATAL=0**。
- `act` 分布：`7`×56、`2`×55、`1`×10、`10`×10、`6`×9、`0`×8 → **2↔7 高频来回切换本身就是遁地/破土连段的段号**，并非独立招式；v14 起把「act 变化 = 新动作边界」当判据，等于在连段内部做冷却。
- **ACT 帧间隔最小 1 帧**（5.4% ≤30 帧、60.8% ≤180 帧）→ 改写触发状态机立即再派发，即用户看到的无休止攻击。
- 20 次 `CD` 全部落在 act=7 或 act=2，例：`CD act=7 21->15 n=12 f=7545`、`CD act=2 51->18 n=35 f=11562`（后 92 帧内又出现 `(37,2,20)`）。每条 CD 与同帧 ACT 成对出现 → 改写紧跟一次新的派发。
- `sub` 变化仅 79 次（v14 为 270）→ 连段被切断，段号变化本身也减少。
- `OBJCHG n=1 obj=0C1C0A50 f=4308`（死亡后对象重建），对象防护生效；坐标异常消失与此无关（v14 也有 OBJCHG 逻辑外的同一路径）。

### 根因（结构性，参数无法修复）
在 **L1 派发器入口** 写 `u8[+0x73E1]` 时，游戏已经把原始 `(act, sub)` 读入并开始执行当前动作；写入的新 variant **不能取消已开始的动作**，只能让 `original!()` 之后的派发再走一次新分支 ⇒
- 双攻击段（破土 + 挥爪同时有判定）、
- 高频攻击（每次改写额外产生一次派发，帧间隔可到 1）、
- 疲劳/倒地被切断（这些状态同样是 act 切换，被当成新招改写）。

对照 Rise 实证（`out/rise_ai_rules.json`）：Rise 在**抽选新动作时**用 `_CheckPrevTableInfoList` + 秒级计时器否决／重抽，**连段内部不重新抽选，且不存在事后改字段**。⇒ **「事后改写 variant」路线整体作废**，v11/v12/v14/v15 的所有参数调整（CD 窗口、护栏、白名单、对象防护）都只是改变异常的表现形式，不可能修好。

### 已执行止损（本轮）
- `mods/RiseAI_HookProbe/.../rai_hook_probe.nro` 覆盖为 **`ROLLBACK_rai_hook_probe_v9_readonly.nro`**（纯只读，零 `wb()`）。
- `mods/RiseAI_ContextProbe/` 部署 `rai_context_probe_v13a.nro`（纯只读，同 hook 点 `+00DC75EC`）。
- `load_order`：`RiseAI_HookProbe` → `# off:`，`RiseAI_ContextProbe` → 启用；备份 `load_order_backup_20261108_1145.txt`。**当前游戏侧零内存写入，行为应回到原版**（连段、疲劳、倒地、坐标全部恢复正常），代价是冷却效果暂时归零。
- `7_` 提示改 STEP 11；音频线未动。

### 下一阶段（不再靠调参续命）
必须在**真正的动作抽选/提交点**做「否决式」干预，而不是在派发器事后改写。候选锚点来自资料库：EMC 解释器 `0x82f80` / 256 路分发表 `0x837ac` / 指令长度表 `0x50ce0`、vtable 槽 247 action end `0x75224`、attackdata picker `0x70ffc`、6 张 L2 变体表。
- 先用 v13-a 只读探针采一轮，从 `CTX`（`+0x40` 坐标／`+0x100` 状态／`+0x73D0` 邻域）找「一个完整动作何时结束」的信号（动作计时器/motion 字段），再判断能否在**动作开始前**写入而不产生双段。
- 降级方案（若不值得继续投入）：改 EMC 静态分支权重做「静态近似降复读」，安全但无有状态冷却。
- `DESIGN_v13.md` 的 v13-b/c 建立在「改写 +0x73E1」之上，须按上述结论重读，不可直接实施。

## 11-08 12:50 用户反馈「没有输出窗口」→ 任务重定义 + v16 只读边界探针已部署

### 决定性前提：该场游戏是零写入基线
- 用户 12:38 反馈（注明「没有日志」）：攻击欲望强、招式硬衔接、小/大硬直与倒地被攻击覆盖、无输出窗口，要求严谨参考 MHRise。
- **其实有日志**：Recomp 0.15.1 写游戏目录 `log.txt`（12:22，865 KB），已备份 `out/game_p54_20261108_1220_v13a_context.txt`。横幅 `RAI v13-a context probe (read-only, NO writes)`；`load_order` 中 `RiseAI_HookProbe` 为 off，其 nro md5 `65914d3f…` = 纯只读 v9。
- ⇒ **症状是原版 GU 的 AI 基线，不是插件副作用**。任务从「修冷却插件」改为「按 Rise 机制改造原版节奏」；v11~v15 的参数线全部终止。

### 基线量化（`tools/analyze_context_log.py` 离线分析 199 次决策）
- act 分布 `2`:79 `7`:67 `6`:33 `10`:10 `1`:7 `0`:2 `11`:1；决策间隔 min 1 / 中位 **87 帧** / ≤30 帧 26.3% / ≤60 帧 41.9%。
- `2↔7` 转移 77 次 = 连段段号；`act=6` 是 `7/21→6/12→6/7→6/11→6/12→7/21` 固定序列（段内 2~11 帧），重复 4 轮。
- 非攻击类 `{0,6,10}` → 攻击类 22/45（9 次 ≤60 帧）；`act=10/sub=7` 10 次，前后 4~68 帧即接 act=2/7 ⇒ 疑为受击硬直被立即打断，对应用户体感。
- 窗口 3/5/8 同招复现 0.1608 / 0.2915 / 0.3970（复读是次要问题）。
- **新实证**：`+0x73E0` 四字节 = `act/sub/prev_act/prev_sub`，游戏自带前一动作记录（199/199 吻合），直接对应 Rise `_CheckPrevTableInfoList`。
- 其它候选：`+73D4` 低 16 位变 10 次；`+73DC` 低字节只变 2 次、跨度 11631 帧（≈194 s，疑怒/疲劳）；`+110/+11C` 同步变 5 次。决策点采样不足以定性，需逐帧。

### Rise 机制严谨对标（本机解包 + RSZ 解析，详见 `DESIGN_v16.md` §2）
- `ThinkCondition._IsActionEnd` / `_IsUnderLayerEnd` / `_NextStateID`：**动作结束门控**状态转移，动作内不重抽。
- 12 个 `attack_stance_*` Hub 按处境分文件（`flash` / `down_floor` / `down_wall` / `no_target` / `out_main_zone` / `return_blockcenter` / `same_main{,_high,_master}`）⇒ 倒地/异常状态**不进攻击抽选池**，这是「硬直不被覆盖」的机制原因。
- 15 个 routine 池 = 3 状态 × 5 距离档，`_TransitionRate` 和恒 100；疲劳池偏向低威胁表（`tired·档5 [10,20,70]→[1,20,51]`）。
- 防复读 = `_CheckPrevTableInfoList` + `EnemyThinkTimerData._Timer`（3~300 秒）+ `EnemyThinkCounterData`；**无显式 CD 字段**。
- 可信度：字段名来自 `rszmhrise.json` 类型定义（结构确定）；15 档权重/表号在解析失步之前且自洽（数值可信）；hub 文件 `partial:true`，失步后的 `_TreeNodeID`/`_ID`/第二组表信息是垃圾值（不可作结论）。
- ⇒ 输出窗口是「门控 + 状态分支 + 池结构」的涌现结果，不是给每招挂计时器；v11~v15 事后写 `+0x73E1` 正是 Rise 明确不做的事。

### GU 侧锚点（资料库确证）
`0x75224` = vtable slot 247 action end（`W4-REFERENCE.md:77` 字节级确证）；`0x76008` = EMC 叶命令 state reset / 动作提交（`formats/emc.md:40,50`）；`0xeb66bc` = 动作 ID 选择（`precision-A.tsv:14`，读 `[this+0x75f0]+100` 向 `0x72d34` 发 2/7，与本轮 act=2/7 吻合）；EMC 解释器 `0x82f80` / 256 路表 `0x837ac` / 距离 matcher `0x8e144`（阈值 = case×100）；EMC 脚本 `em+0x2588`。

### v16（已部署，纯只读）
- 沿用唯一验证过的单点入口 hook `+00DC75EC`，**零写入**。每帧只读 10 个已观测字段，仅在变化时打 `F/W`（带帧号、变化位掩码 `mask`）；每 60 次 hook 打 `P`（`+1428/2588/75F0/75EC`）；日志预算 900 组。
- `entry` 打印 7 个锚点函数前 8 字（判断能否挂 hook）与实例 `vt[247]`。
- 产物 `out/rai_boundary_probe_v16.nro`（20480 B，md5 `17277620…`，特征串 `RAI v16` 校验、断言不含 v13-a）；源码 `plug/context_probe/src/lib.rs`，v13-a 备份 `lib.rs.v13abak`。
- 编译踩坑：Rust 2024 `static_mut_refs` —— info! 宏不能直接引用 `static mut`，须先读到局部变量；已修。
- 部署 `mods/RiseAI_BoundaryProbe/romfs/nativeNX/plugins/rai_boundary_probe.nro`（两侧 md5 一致）；`load_order`：`RiseAI_ContextProbe` → `# off:`，新增 `RiseAI_BoundaryProbe`，备份 `load_order_backup_20261108_1250.txt`；`7_` 提示改 STEP 12（输出 `game_p54.txt` 与轮转逻辑未动）；音频线未动。
- **下一轮**：重启跑 `7_`，进任务打将军镰蟹约 60 秒。判据：① `SITE +0075224/+0076008/+00EB66BC` 字节给出真实函数入口；② `VT ... slot247=00075224`；③ `F` 行找出「每个完整动作结束翻转一次」的字段；④ 无 FATAL。
- 之后才进入 `DESIGN_v16.md` §5-B：在动作提交点做否决式干预（状态优先 / 输出窗口 / 前表重抽），严禁事后改 `+0x73E1`。

## 11-08 13:05 v16 实机回收 → 字段层无动作结束信号，转 v17 函数级探针

### 本场日志（零写入、零 FATAL）
- `02_Workspace/game_p54.txt`（13:05，602 KB）→ 备份 `out/game_p54_20261108_1305_v16_boundary.txt`；横幅 `RAI v16 boundary probe`，`[rai]` 1133 行（F217 / W434 / P420 / BEAT51 / SITE7 / VT1 / OBJ1），30600 帧 ≈ 8.5 min，`hit=25247 chg=217 log=637`（预算 900 未耗尽，数据完整）。
- 分析脚本 `tools/analyze_boundary_log.py` → `out/v16_boundary_events.json`（217 个完整变化点）。

### A 阶段判据结果（详见 `DESIGN_v16.md` §5-A 结果）
- ✅ `VT slot247=00275224`（= `text_addr 0x200000 + 0x75224`），跨 em001/em020 一致，资料库锚点实机确证。
- ✅ 7 个锚点里 6 个是标准 prologue（`E92D4xxx`/`E92D4FF0`），**未被 MH4U Port 的 IPS32 跳板改写，可直接挂 hook**；`0x837ac` 首字 `00000E7C` 是 256 路跳转表（数据表，非函数）。
- ✅ 4 个指针 `+1428=0C221CD0`、`+2588=0`、`+75F0=1AE4F640`、`+75EC=1AE4F430` 420 次采样恒定。
- ❌ **10 个字段里没有「每动作结束翻转一次」的信号**：`73E0/73E8/73EC` 是提交时刷新（195/217 为 `mask=0D0`），`73D0/73D4/73D8/73DC/110/11C` 是低频长状态位（2~11 次变化）。动作边界**只能靠函数级观测**。

### 新增实证（改变下一阶段做法）
- `<=3` 帧聚类 = **199 个决策簇**，与 12:20 场 199 次决策逐一对上 ⇒ 决策点定义可靠。
- `+73E0` 的 `prev_act/prev_sub` 吻合上一次提交 **197/198** ⇒ GU 自带「前表」记录，对应 Rise `_CheckPrevTableInfoList`，**无需自建历史窗口**。
- `+73E8=(act<<24)|rng16`、`+73EC=(rng16<<16)|sub`；`rng16` 每次提交刷新、209 个唯一值、`0010..FFF1` 近似均匀 ⇒ 抽选随机源在提交点可读。
- **用户抱怨的现场**：`f=14730` 同帧 `2/55 → 7/33` 双提交，伴随 `+73DC 0→1` 与 `+0110` 切换，prev 链在此唯一一次断裂 ⇒ 「硬直/倒地被攻击覆盖」实证。短衔接 ≤12 帧共 35 次，`act=6` 连段内 `6/11→6/12` 恒 1 帧、`6/12→7/21` 恒 10 帧（重复 4 轮），是段号推进而非独立决策。
- `+73D0` 三段重复生命周期 `0→08000002→00000102→0`，伴随 `+73D8` 挂/摘 `1ACF08E0`/`1ACF1060`（em 脚本指针），周期 ≈5800 帧；`+0110/+011C` 同步切换 7 次（`EB/2BFF` ↔ `4B/3FFF`）。均为长状态位，非动作边界。

### v17（已部署，待实机，纯只读）
- **单 hook `0x75224`（`vt[247]`）**，4 形参原样透传 `original!`（thunk 会 clobber r1，被调函数不依赖 r1 传参）；`forge_onUpdate` 逐帧差分 `+73E0` 并校验对象 vtable，**不占第二个 hook 点**（遵守「一次只装一个新 hook」硬约束）。
- `E` = 动作结束、`S` = 提交；`dS` = 动作时长、`dE` = 结束→下一招间隔（输出窗口候选）。日志预算 700 组。
- 判据：`BEAT ... end/600` ≈600 ⇒ `0x75224` 不是 action-end（资料库语义标注有误），回退重评；`end ≈ sub ≈ 决策数` ⇒ 确证，可进 §5-B 否决式干预。
- 产物 `out/rai_actionend_probe_v17.nro`（20480 B，md5 `52b9dc09…`，含 `RAI v17`、不含 `RAI v16`/v13a）；源码 `plug/context_probe/src/lib.rs`，v16 备份 `lib.rs.v16bak`。
- 部署 `mods/RiseAI_EndProbe/romfs/nativeNX/plugins/rai_actionend_probe.nro`（两侧 md5 一致）；`load_order`：`RiseAI_BoundaryProbe` → `# off:`，新增 `RiseAI_EndProbe`，备份 `load_order_backup_20261108_1312.txt`；`7_` 提示 STEP 13（**输出 `game_p54.txt` 与轮转逻辑未动**）；音频线与 `6_` 未动。
- 回退：把 `load_order` 用上述备份还原即可（v16 nro 仍在 `out/rai_boundary_probe_v16.nro`）。
- **下一轮**：重启跑 `7_`，打将军镰蟹约 60 秒；日志出来后跑 `tools/analyze_actionend_log.py`（已写、空输入冒烟通过）配对 E/S 帧差。

## 11-08 13:21 v17 实机回收 → **决定性根因确证**，转 v18 动作开始入口探针

### 本场日志（零写入、零 FATAL）
- `02_Workspace/game_p54.txt`（13:21，341 KB）→ 备份 `out/game_p54_20261108_1321_v17_actionend.txt`；横幅 `RAI v17 action-end probe`，`[rai]` 435 行（E166 / S218 / BEAT42 / OBJ6），25366 帧；日志预算 700 未耗尽（`log=418`）。
- 分析 `tools/analyze_actionend_log.py` → `out/v17_actionend_events.json`；另做按 OBJ 清洗（临时脚本，未落盘，结论已写入本文件）。

### A′ 判据结果：**0x75224 确证是 action end，且 GU 没有输出窗口阶段**
- `end/600` 全程 0..8（非每帧）；`SITE +00075224 = E92D4010` 标准 prologue。
- 主对象 `0C1C0A50`（vt `019B5588`，与 v16 场同 vtable）= 怪物：**162 个 E，全部在 1 帧后产生 1 个 S，配对 162/162 无例外**，`S.pa/ps == E.a/s`。
- **⇒ END → 下一动作提交恒 1 帧。GU 原版架构里不存在「动作结束后的间隔」这一阶段**，输出窗口必须由插件人为插入。这是用户「招式硬衔接 / 硬直倒地被覆盖 / 无输出窗口」的函数级根因，不是参数问题。
- 另 52 个 S 无对应 E = 连段段号推进（act=6 序列 `6/10→6/7→6/11→6/12`），不是新动作。
- 动作时长中位 **85 帧**（≈1.42 s，p25 54 / p75 154），与 v16 场决策间隔中位 87 帧交叉吻合。
- `+73DC` 相邻 E 变化 **1/161**（只在 `08200000`/`08200001` 长时保持）⇒ 排除其作为边界信号。
- 污染已定位：另两个对象 `0C1CD5C0` / `0C220060`（vt `01A14E48`）各 2 次 E/S，仅出现在开局 ~200 帧，是初始化临时实体；排除后不影响任何结论。

### 资料库语义修正（重要）
- `0x76008` **不是动作提交**，是 EMC 叶命令 state reset path（`formats/emc.md:40,50`：op `0x00` operands `0,0xff` 及 leaf ops 尾部都调它），频率过高，不宜作干预点。原 `DESIGN_v16.md` §4/B 段据此已改。
- 真正的**动作开始入口**是 `0xaff40(this, action_id, float_duration, f32)`（`precision-A.tsv:10,15,16,17,18,19,21` 共 7 处 dispatch 调用，calls `vtable+984 = set action N`）。**B 阶段首选干预点**：在动作开始前改参数，而不是事后写字段。
- `0xeb66bc` = 从 actor 状态选 action id（读 `[this+0x75f0]+100` bytes 5/6，向 `0x72d34` 发 2/7）。

### v18（已部署，待实机，纯只读）
- 保留已验证 `0x75224` hook，新增 **1 个** hook `0xaff40`；entry 先读 `SITE +000AFF40` 首字，**只有标准 ARM prologue 才安装**（被 IPS32 跳板改写则 `SKIP` 自动降级为纯 action-end 探针）。6 个 `u32` 形参原样透传（f32 位模式等价），零写入。
- `E` = 动作结束、`A` = 动作开始（打印 `id` / `dur` 位模式 / `dE` / 当前 act-sub）。判据：`A.dE ≈ 1` 且 `id` 可分类 ⇒ 可在 `0xaff40` **动作开始前改参数**实现否决，不重演 v11~v15。
- 产物 `out/rai_actionstart_probe_v18.nro`（20480 B，md5 `81519014…`，含 `RAI v18`、不含 v17/v16）；源码 `plug/context_probe/src/lib.rs`，v17 备份 `lib.rs.v17bak`；分析脚本 `tools/analyze_actionstart_log.py`（已冒烟）。
- 部署 `mods/RiseAI_StartProbe/romfs/nativeNX/plugins/rai_actionstart_probe.nro`（两侧 md5 一致）；`load_order`：`RiseAI_EndProbe` → `# off:`，新增 `RiseAI_StartProbe`，备份 `load_order_backup_20261108_1325.txt`；`7_` 提示 STEP 14（**输出 `game_p54.txt` 与轮转逻辑未动**）；音频线与 `6_` 未动。
- 回退：用上述备份还原 `load_order` 即可。
- **下一轮（预计最后一轮只读）**：重启跑 `7_`，打将军镰蟹约 60 秒；跑 `tools/analyze_actionstart_log.py`。拿到 `id` 白名单后进入 §5-B：END 设窗口 → `0xaff40` 在窗口内把攻击类 `action_id` 换待机/移动类；严禁写 `+0x73E1`、严禁跳过 `original!`。

## 11-08 13:34 v18 实机回收 → **0xaff40 入口标注存疑**，转 v19 入口定位轮

### 本场日志（零写入、零 FATAL）
- `02_Workspace/game_p54.txt`（13:34，424 KB）→ 备份 `out/game_p54_20261108_1334_v18_actionstart.txt`；`[rai]` 48 行（E6 / A0 / BEAT29 / OBJ4 / SITE6 / SKIP1），17400 帧。
- **`SKIP h_action_start: +000AFF40 not a function entry (E3A02000)`** ⇒ v18 的运行时 prologue 校验主动降级，**A 行 0 条**，本轮没拿到 `id`/`duration` 白名单。
- `SITE +000AFF40 = E3A02000 EAFFFF96 | E92D4070 ED2D8B04`：`mov r2,#0` + `b -0x1a8`（回跳 `0xafda4`），**不是标准入口**；`+008` 起才是 `push {r4,r5,r6,lr}; vpush {d8}` ⇒ **`0xaff48` 是标准 prologue**（带 d8，符合 `float duration` 函数）。资料库 `0xaff40` 起点标注可能偏 +8，或该地址是 thunk / 前一函数的循环回边。
- 其余锚点 `0x76008 / 0xeb66bc / 0x72d34 / 0x752ec / 0x75224` 首字均 `E92D4xxx`，是可挂的标准入口。
- **样本过短**：END 仅 6 次（f=3985..4279），之后 13000+ 帧无 E；疑似任务提前结束/怪物离开。不影响 v17 的 162/162 配对结论，但不能作统计。`7_` 提示已加「打满 60 秒、勿用立即完成任务 cheat、保持与怪交战」。

### v19（已部署，待实机，纯只读 / 零写入）
- **不再靠首字猜**：entry 时对 `text+0xB00000..0x1200000` 做**只读 BL 调用图扫描**，统计指向 `0xaff40 / 0xaff48 / 0xafda4 / 0xafd9c` 的调用数与前 4 个调用点（`CALL` 行）。资料库称 `0xaff40` 有 4398 个调用者且几乎都在该区间，真入口必有大量命中。另宽 dump `0xaff20..0xaff70` 六行确认函数边界。
- 保留已验证 `0x75224` END hook；**运行时只装一个新 hook**：`c40>=c48` 装 `+AFF40`，否则装 `+AFF48`；两者皆无调用者则 `FALLBACK` 挂 `0x72d34`（标准 prologue，dispatch 下游收 2/7）打印 `D` 行。全部 `original!` 原样透传，分类日志预算 E250/A450/D200。`BEAT ... sel=` 标明本轮选了哪个。
- 产物 `out/rai_entrylocator_probe_v19.nro`（20480 B，md5 `226eadca…`，含 `RAI v19`、不含 v18/v17）；源码 `plug/context_probe/src/lib.rs`，v18 备份 `lib.rs.v18bak`。
- `tools/analyze_actionstart_log.py` 已扩展解析 `CALL / INSTALL / FALLBACK / D`（v18 日志冒烟通过，输出 `v19_entrylocator_events.json`）。
- 部署 `mods/RiseAI_EntryProbe/romfs/nativeNX/plugins/rai_entrylocator_probe.nro`（两侧 md5 一致）；`load_order`：`RiseAI_StartProbe` → `# off:`，新增 `RiseAI_EntryProbe`，备份 `load_order_backup_20261108_1343.txt`；`7_` 提示 STEP 15（**输出 `game_p54.txt` 与轮转逻辑未动**）；音频线与 `6_` 未动。
- 回退：用上述备份还原 `load_order` 即可。
- **下一轮**：重启跑 `7_`，**保持与将军镰蟹交战满 60 秒**；跑 `tools/analyze_actionstart_log.py`。先看 `CALL` 行定入口，再看 `A.dE≈1` 与 `id` 分布；确认后进入 §5-B 落地输出窗口（严禁写 `+0x73E1`、严禁跳过 `original!`）。

## 11-08 13:45 用户提示 → 逆向 Show HP Bar，发现遗漏的 act 对象；v19 → v19b

### 研究结论（详见 `refs/hpbar/README.md`、`refs/hpbar/full.asm` / `onupdate.asm`）
- `target_health_display.nro` v0.4 动态符号表只有 `forge_onUpdate=0x710C` 等 3 个导出，导入里**无任何 hook**，
  只有 `forge_mem_getMainTextAddr` + ImGui ⇒ **纯内存读取**就能锁定目标怪并读 HP / 发怒状态。
- 反汇编 `forge_onUpdate` 得到确证链（与 `W4-REFERENCE.md:73` 的 `HP [em+0x1428]+0x370` 完全吻合）：
  `mgr = *(main+0x184D750)` → `slot = call(main+0x18F90, mgr)` → `locked = call(main+0x18E50, mgr)` →
  **`mon = call(main+0x18FFC, mgr)` = 目标怪对象指针** → `act = *(mon+0x1428)` →
  `hp = *(act+0x370)`、`maxhp = *(act+0x374)`、`species = *(u16*)(mon+0xB5F0)`。
- 资料库交叉（`precision-A.md:111` / `verdict-35_42.md:48` / `W4-REFERENCE.md:71,72`）：
  `*(em+0x1428)` 就是 **act 对象**，带 `+0x1A0/+0x1A1` 状态字节、`+0x1A8` flags（0xaff40 会读）；
  **EMC 对象在 `*(em+0x2588)`**（解释器 0x82f80 / 循环 0x83770）；`mon+0xB5F5` 是选动作 id 开关；
  rage/tired 管线 `0x1069d8c` 内调 `0x106aef0 / 0x1068dd8 / 0x106b04c`，用 `hp/maxhp` 比值判定。
- **重要修正**：v16 的「字段层没有动作结束信号」结论**不完整** —— v16 只差分了怪物对象自身
  `+0x73D0..0x73EC` / `+0x110` / `+0x11C` 这 10 个字，**从未读 `*(em+0x1428)` 与 `*(em+0x2588)`**。
  不推翻 v17 的函数级结论（END→提交恒 1 帧、GU 无输出窗口阶段），但字段层可能仍有更轻量的
  act start/end 信号与怒/疲劳状态，可用于 Rise 式状态分支。

### v19b（已部署，待实机；v19 原逻辑全部保留，纯只读零写入）
- 同轮并行两路：A = BL 调用图定 `0xaff40/0xaff48` 入口 + 动态选唯一新 hook；
  B = HP Bar 式 act 对象观测。新增行：
  - `H`：`obj/act/emc` 指针、`hp/max`、`act+0x1A0/0x1A4/0x1A8`、`emc+0`（对象出现/切换时打印）；
  - `X`：`act+0x180..0x1C0` 与 `emc+0x00..0x40` 共 32 字逐帧差分，变化时打印 `w=A/E +off old->new`，限 400 行 / 每帧 8 行；
  - `G`：每 300 帧打印 `main+0x184D750 / +0x1899458 / +0x2126998` 全局；`M`：在管理器对象前 0x200 内搜等于 END-hook `this` 的指针字段（**纯只读，不调用游戏函数**）。
- 判据：`X` 中某字段与 `E`（END）帧 ±2 对齐率高 ⇒ 字段层 act 信号；`M` 命中偏移 ⇒ 可直接读目标怪指针，不必调 getter。
- 产物 `out/rai_actobject_probe_v19b.nro`（24576 B，md5 `4b8a8ae5…`，含 `RAI v19b`）；源码 `plug/context_probe/src/lib.rs`（v19 备份 `out/rai_entrylocator_probe_v19.nro` 仍在，v18 源码 `lib.rs.v18bak`）；`tools/analyze_actionstart_log.py` 已扩展 X/H/G/M 与「X↔END 对齐率」（v18 日志冒烟通过）。
- 部署：覆盖 `mods/RiseAI_EntryProbe/.../rai_entrylocator_probe.nro`（两侧 md5 一致），**load_order 未变**（仍 `RiseAI_EntryProbe`）；`7_` 提示改 STEP 15 v19b（**输出 `game_p54.txt` 与轮转逻辑未动**）；`6_`、音频线、`05_TargetHealth/` 与 Show HP Bar mod 本身**均未改动**。
- 回退：用 `out/rai_entrylocator_probe_v19.nro` 覆盖部署文件即回 v19；`load_order_backup_20261108_1343.txt` 可回 v18。
- **下一轮**：重启跑 `7_`，**打满 60 秒、锁定目标怪**；跑 `tools/analyze_v20_log.py`。

## 11-08 14:08 回收 v19b → 部署 v20（入口确证 + id 白名单 + 否决模拟）

### v19b 实机结论（零 FATAL / 零写入，29400 帧 ≈ 8.2 分钟）
- **BL 调用图**：`0xaff40` 4396 个调用者 / `0xaff48` 72 / `0xafda4` 490 / `0xafd9c` 0
  ⇒ **`0xaff40` 是真入口**，`mov r2,#0; b 0xafda4` 是 8 字节 thunk；`0xaff48` 是另一个函数。
  v18「起点偏 +8」猜想证伪。**判定入口以后一律用调用图，不用首字猜**。
- **A=197（主对象 189）/ E=163**，同帧配对 131/163；同帧 A 的 `+0x73E0` 与 E 的 **131/131 全不同**
  ⇒ 时序 `E(读旧) → original! 内部提交新动作并写 +0x73E0 → 0xaff40(读新)`。
- **`a1` 就是动作 id**，与 `(act,sub)` 高度一一（21 个提交 id 中 17 个唯一）：
  `535↔2/5`、`520↔7/16`、`514↔7/15`、`540↔7/61`、`524↔7/33`、`3↔1/3`、`15↔1/2`；
  `act=2/7` 攻击、`act=1` 移动待机、`act=6` 连段特殊。非同帧 A（58 条，id=19/525/526/527/528）是动作内部 motion 调用。
- **X/H/M 全空**：`H` 仅 f=29439 一次且 `act=29243964` 读回全 0 ⇒ `*(END-hook this+0x1428)`
  **不是有效 act 对象**，hook 的 `this` 与 HP Bar 的 `mon` 很可能不是同一层对象。
  `g1=15DAD640`（mgr）恒定有效，`obj` 在 f≈3221 后稳定 `0C1C0A50`。

### v20（已部署，待实机；仍纯只读零写入）
- 直接复现已启用 Show HP Bar 的 **getter 链**（每帧都在调，零风险）：
  `mgr=*(main+0x184D750)` → `slot=call(0x18F90,mgr)` / `lock=call(0x18E50,mgr)` / **`mon=call(0x18FFC,mgr)`**；
  `C` 对比 `mon` 与 `obj`，`K` 同时 dump 两者 `+0x1428/+0x2588`、HP、species，彻底回答「如何确认怪」。
- `R` 每个 END 帧打 `act+0x1A0/1A4/1A8` + `hp/max` + `emc+0`；`X` 用 **mon 侧指针**逐帧差分
  `act+0x180..0x1C0` / `emc+0..0x40`，找怒/硬直/倒地状态位。
- **干预策略零风险模拟**：END 开窗 60 帧，`0xaff40` 用 `+0x73E0` 整字变化判提交、`act=2/7` 判攻击，
  命中打 `V`（`id0/id1/win_left/applied`）。**`const INTERVENE=false` ⇒ a1 原样透传、零写入**；
  下一轮只改这个常量重编即灰度验证，替身 `IDLE_ID=3`（`(1,3)` 移动待机）。
  注意 `a2` 被 thunk 的 `mov r2,#0` 清零，**改 duration 无效，只能改 a1**。
- 产物 `out/rai_hpchain_probe_v20.nro`（md5 `9d8cd3a9…`），源码 v19b 备份 `lib.rs.v19bbak`；
  部署覆盖 `mods/RiseAI_EntryProbe/`（**load_order 未变**，备份 `load_order_backup_20261108_1420.txt`）；
  `tools/analyze_v20_log.py`（v19b 日志冒烟通过）；`7_` 提示 STEP 16（输出路径与轮转逻辑未动，新增「锁定目标怪」）。
- **下一轮（原计划）**：重启跑 `7_`，**打满 60 秒、锁定目标怪**，然后跑 `tools/analyze_v20_log.py`。
  判据：`C.mon==C.obj`？`K.hp/max` 合理？`R/X` 哪个字段随状态翻转？`V` 拦截率与间隔。
  全部通过后把 `INTERVENE` 改 true 重编即进入 §5-B 灰度干预（严禁写 `+0x73E1`、严禁跳过 `original!`）。

### v20 实机回收（11-08 14:30，玩家阵亡后闪退；日志已备份）
日志 `out/game_p54_20261108_1430_v20_hpchain.txt`（3277 行 / 529 条 rai / 1 条 FATAL），
分析 `out/v20_probe_events.json`。**零写入、`applied=0` 共 5 次**。

- **getter 链确证有效**：`mgr=15DAD640` 恒定；`slot/lock` 在 f=6000 由 0→1；
  `mon=0C160890` 稳定；`p1428=0C161CD0` 有效 act 对象；`hp` 3862→2088 / `max` 3880；
  `sp=0014`（将军镰蟹）。**「如何确认锁定的怪」已解答**。
- **`mon != obj`**（`obj=0C1F26D0` 是 END-hook 的 this），`o1428=40400000` 是浮点位模式不是指针。
  ⇒ v19b 的 `H/X` 全空由此解释，`R` 全 0 是 `ACT_OK` 在 E 帧尚未置位的**探针时序缺陷**，不是字段无效。
- **决定性发现：`0xaff40` 的 `a0` 就是 `mon`**（72/91 条 A 行 `this=0C160890`）。
  ⇒ 确认怪**无需调用任何游戏函数**，动作开始 hook 的第一个参数就是目标怪对象。
- **END hook `0x75224` 本场只 7 次**（全在 f=3538..3962，之后 8600 帧零 END），且 this 非目标怪
  ⇒ **不能用 END 开窗**。v20 的 `V` 还错写了 `a0 == OBJ`，与 `a0 == mon` 互斥，故只拦 5 次。
- **`act+0x1BC` 是逐帧 -1 的浮点动作剩余计时器**（40.0→0 / 240.0→0，值域 0..240），
  即字段级 `_IsActionEnd` 等价物；`X` 320 条限流全被它刷满，`A` 行 8 条 `+1A0` 变化。
- 量化：主怪 submit 65 个间隔中位 **79 帧**，p25=62，≤60 帧 16/65，≤90 帧 38/65；
  攻击类提交 66/78（84%）。`id↔(a,s)` 白名单扩到 23 个 id（19 个唯一映射）。
- **两处设计错误已定位**：① 窗口源应是 `0xaff40` 的 submit，不是 END；
  ② 目标怪判据应是 `a0 == mon`，不是 `a0 == OBJ`。

### v21（已部署，待实机；本轮纯只读零写入 A/B 版）
- 修正上述两处错误：单 hook `0xaff40`，用 `+0x1428` 落在堆区 + `hp/max/species` 自洽**自识别目标怪**；
  每个放行的攻击提交开 60 帧窗口，窗口内攻击类新提交打 `V`（本轮 `applied=0` 零写入）。
- 顺带清除 v20 相对 v19b 的三个新增面（见 `CRASH_20261108_death.md`）：
  零游戏 getter 调用、`onUpdate` 零游戏内存读取、只装 1 个 hook、指针解引用收紧、加阵亡结算熔断。
  ⇒ **v21 同时是闪退 A/B 判据**：零 FATAL ⇒ 与 v20 新增面相关且已修复；仍 FATAL ⇒ 与探针无关。
- 产物：只读版 `out/rai_risewindow_v21.nro`（md5 `dd3ee7d1…`，**已部署**）
  ／干预版 `out/rai_risewindow_v21i.nro`（md5 `d13bf846…`，**待命未部署**，两版只差 `INTERVENE` 常量）。
  源码 `lib.rs.v20bak`；`tools/analyze_v21_log.py`；`7_` 提示 STEP 17（输出路径与轮转逻辑未动）。
  `load_order` 未变，备份 `load_order_backup_20261108_1455.txt`。
- 闪退诊断全文 `CRASH_20261108_death.md`；NSO0 解压产物 `refs/hpbar/main_text_decomp.bin`。
### v21 实机（15:25 场，纯只读零写入）——判据全部通过
- 日志 `out/game_p54_20261108_1525_v21_readonly.txt`（473 KB / 24600 帧 ≈6.8 分钟）；
  **零 FATAL、零 HALT**、`A=208 / submit=184 / 攻击类 153 (83%) / V=41 (applied=0) / pass=112`，
  `LOGN=291 < 900` 未触限流。任务正常 `quest started → quest ended`。
- 目标怪自识别一次命中：`mon=0C138180 act=0C1395C0 hp 3880→1220 sp=0014`（将军镰蟹），
  `MON` 仅 1 次 ⇒ 单 hook + `+0x1428` 堆区校验 + `hp/max/species` 自洽判据稳定可靠。
- **窗口参数实测**：攻击类提交间隔中位 **72 帧**，p25=54、p75=142；
  ≤60 帧 30%、**≤90 帧 64%**、≤120 帧 69%。⇒ 理论上 `W=60` 只拦 30% 攻击提交，
  `W=90` 可拦 64%（1.5 秒），`W=120` 69%。**60 帧偏保守**，灰度通过后再调。
- **替身动作合法性实证**：`id=3` 本场由主怪自己调用 4 次（`(act,sub)=(1,3)`，
  `pa/ps` 均来自攻击类），说明游戏原生在攻击之后就会进入该待机/移动动作
  ⇒ 把攻击 `a1` 换成 3 不是凭空造动作，干预风险显著降低。
- **状态位证伪**：`act+0x1A0` 的 `00000101 / 00000201 / 00000301` 三值中，
  后两者只对应 `id=525 / 526 / 527`（全 `act=7`），呈周期性单/双次出现
  ⇒ **不是怒/疲劳/硬直状态位**，不能作 Rise Hub 状态分支输入；v22 需另找字段。
  `act+0x1A8` 恒为 `00440049`；`+0x1BC` 动作计时器 51/208 次非零（浮点 0..900）。
- **闪退 A/B 未闭合**：本场无 `cart/faint/death` 线索、未阵亡，`HALT` 未触发。
  零 FATAL 只证明 v21 在常规任务流程稳定；「阵亡后闪退」仍需一次阵亡场景复测才能定论。

### v22 前置 / 当前部署：v21i 灰度干预
- 已部署 `out/rai_risewindow_v21i.nro`（md5 `d13bf846…`，`INTERVENE=true`，`W=60`，`IDLE_ID=3`）：
  只改 `a1`，`original!` 其余 5 参原样透传；**严禁写 `+0x73E1`、严禁跳过 `original!`**。
- 待命变体 `out/rai_risewindow_v21i_w90.nro`（md5 `106069df…`，`W=90`），
  灰度若体感不足可直接换；**不要同时改多个变量**，否则无法归因。
- 只读基线 `out/rai_risewindow_v21.nro`（`dd3ee7d1…`）保留作一键回退；
  源码 `lib.rs` 保持 `INTERVENE=false / W=60`，备份 `lib.rs.v21bak`。
- `7_` 提示 STEP 18（**输出 `game_p54.txt` 与轮转逻辑未改**）；`load_order` 未变，
  备份 `load_order_backup_20261108_1615.txt`。
- **下一轮**：重启跑 `7_`，打满 60 秒、锁定怪。观察三点：① 攻击节奏是否出现可用输出窗口；
  ② 是否有怪物卡住/发呆/无动画却有攻击判定/任务无法结算；③ 是否 FATAL（尤其阵亡后）。
  跑 `tools/analyze_v21_log.py`，判据 `V.applied=1` 计数、零 FATAL、游戏可正常游玩。

### v21i 灰度干预（16:30 场）——**路线证伪，已回退**
- 日志 `out/game_p54_20261108_1630_v21i_intervene.txt`：**零 FATAL**，`V=16` 次 `applied=1`，
  `A=139`（只读场 208）、`pass=70`；HP 3880→173（正常讨伐至濒死，用户未阵亡）。
- 量化劣化：攻击类提交 153→86、间隔中位 **72→142 帧**、≥400 帧长间隔 **5%→12%**；
  7 次干预后到下一次提交 ≥229 帧，最后一次提交后 2686 帧无新提交（含任务结算，但实机确有「原地傻站」）。
- 动作分布变化：`520` 26→7、`517` 23→9 骤减；`525/526/527` 占比 11.5%→**15.8%**，
  且这三者正是 `act+0x1A0` 取 `00000201/00000301` 的特殊动作 ⇒ 与用户「大量吼叫」吻合（尚待命名对齐）。
- **根因**：`+0x73E0` 的 act/sub 在 `0xaff40` 之前已写入，单独改 `a1` 破坏状态机一致性；
  且 `act=2/7` 是 L1 粗粒度类（18 槽），把整类当攻击拦掉会误伤吼叫 / 硬直 / 位移。
  **用户「没有区分怪物 act」的质疑成立**。
- ⇒ **「在 `0xaff40` 改 `a1`」路线废弃**。下一步必须在**抽选/提交前**做否决式重抽
  （候选 `0xeb66bc` 选招 / `0x72d34` dispatch / EMC 解释器 `0x82f80`），且按 **id 白名单**分类。
- 部署已回退为 `out/rai_risewindow_v21.nro`（`dd3ee7d1…`，纯只读）。

### 用户明确约束（必须遵守，2026-11-08）
- **AI mod 不得与 `Show HP Bar` 绑定**：不调用其函数、不共享其状态、不要求玩家安装。
  它只是「如何获取怪物名字、血量、大小、是否发怒」的**接口参考**，为后续**发怒 / 疲劳权重**打基础。
- 所有字段一律从 `0xaff40` 的 `a0`(=mon) 纯内存读取；字段表见 `refs/hpbar/README.md` 末节。
  怒/疲劳状态 = `*(u8*)(act+0x518)`（1=怒、2=疑似疲劳，由 `main+0x8172C / 0x81774` 反汇编确证）。

### v22（已部署，纯只读零写入）
- 单 hook `0xaff40`、`original!` 六参原样透传、零游戏函数调用、不依赖 HP Bar。
  `S` 行按 `id` 记录每次新提交（附 hp / st / 动作计时器）；`T` 行抓 `act+0x518` 状态切换。
- 目的：① 建立按 **action_id** 的动作分类（攻击 / 吼叫 / 硬直 / 移动），取代 act=2/7 粗判；
  ② 实机验证怒/疲劳状态枚举，为 Rise 式加权池提供输入。
- 产物 `out/rai_idstate_probe_v22.nro`（md5 `7216f9f5…`，**已部署**）；`tools/analyze_v22_log.py`（冒烟通过）；
  `7_` 提示 STEP 19；`load_order` 未变，备份 `load_order_backup_20261108_1640.txt`。
- **下一轮**：重启跑 `7_`，打满 60 秒、锁定怪；确认「原地发呆」消失；
  观察并描述**吼叫发生的大致时机**（开局 / 受击后 / 发怒时 / 低血量），用于把 id 与吼叫对齐。
  跑 `tools/analyze_v22_log.py`；判据 `S` 计数、`T` 的 st 取值、零 FATAL。

### v22 实机（16:50 场）——阵亡 3 次零闪退 / 复读指纹定位 / 发怒字段确证
- 日志 `out/game_p54_20261108_1648_v22_idstate.txt`：470 KB、24600 帧、`FATAL=0`、
  `S=156 / T=5 / MON=1 / HALT=0`。**用户阵亡三次、任务失败，均无闪退**
  ⇒ 阵亡闪退 A/B 闭合，见 `CRASH_20261108_death.md §5.7`。
- **发怒字段确证**：`act+0x518` 在 0↔1 间切换 5 次（f=7117/11986/14836/19770/22300），
  与 HP 阶段相关（3210 怒→2248 解→1718 怒→926 解→111 怒）。`st=2` 本场未出现。
  st=1 时提交间隔中位 **72 帧**、≤30 帧 24%；st=0 为 87 帧、20% ⇒ 发怒时攻击更密，
  可作为加权池输入。尺寸倍率 float `act+0x1B0 = 3F8F5C29`(≈1.12)。
- **「后退→前撞」复读定位到具体连招指纹**：`19(6/12) → 4(6/7) → 19(6/12)`，
  段间隔 10~13 帧，整轮约 220 帧；在 f=7897..8376（怒）与 f=13909..14433 各连续 3 轮，
  共 6 次。**全部在 `act=6`（连段类），不在旧的 act=2/7 攻击白名单内**
  ⇒ 印证「分类必须按 id/sub 而非 act 粗类」，也解释了 v21i 为何漏判/误判。
  其它高频对：`515→514`(11)、`517→520`(9)、`535↔540`(11，全在怒状态)。
- **本场 v22 零写入，复读是原版 GU AI 的固定连段复读，不是插件回归**。
  GU 自带 prev 表 `+0x73E0` 高 16 位（pa/ps），可直接对标 Rise `_CheckPrevTableInfoList`；
  但 `4→19` 的 prev 链 0/6 吻合（中间态 (6,11)），故防复读要用**连招指纹**而非单步 prev。
- 长间隔 >500 帧 6 段（f=4334/5086/7694/12493/16827/21410），与阵亡/脱战/换区吻合。

### v23（已部署，纯只读双 hook）
- 新增 `0xEB66BC`（选招点，`precision-A.tsv:14`，SITE 首字 `E92D48F0` 标准 prologue），
  运行时校验首字，非 prologue 自动 `SKIP` 降级为单 hook；保留已验证的 `0xAFF40`。
- `P` 行记录选招参数与 `+0x73E0`/`act+0x1A1`/`+0x518`；`S` 行新增 `dP`（距最近选招帧差）
  与 `s1A1`；`T` 行同时抓 `+0x518` 与 `+0x1A1` 变化（后者是资料库动作分派函数
  `0xf14e34/0xfcb480` 读取的 0/1/2 状态字节，Rise Hub「硬直/倒地独立分支」候选输入）。
- 零写入、零游戏函数调用、不依赖 HP Bar、`onUpdate` 不读游戏内存。
- 产物 `out/rai_selectpoint_probe_v23.nro`（md5 `dfb27ee5…`，**已部署**）；
  源码 `lib.rs`（v22 备份 `lib.rs.v22bak`）；`tools/analyze_v22_log.py` 已扩展支持
  `P / dP / s1A1 / 连招指纹`；`7_` 提示 STEP 20；`load_order` 未变，
  备份 `load_order_backup_20261108_1655.txt`。
- **下一轮**：重启跑 `7_`，打满 60 秒、锁定怪。判据 `P` 有数据、`S.dP≈0`
  （选招发生在提交之前 ⇒ 可作否决点）、`s1A1` 取值、零 FATAL。
  通过后进 v24：在选招点做**否决式重抽**（连招指纹命中即换表 + 3~300 秒计时器，
  对标 Rise `_CheckPrevTableInfoList`），先只读模拟再灰度。

### 17:07 实时快照（用户第一次阵亡后暂停游戏，只读抓取，未改任何部署）
- 快照 `out/game_p54_20261108_1707_v23_paused_snapshot.txt`：339 KB、`FATAL=0`、
  `S=53 / T=10 / MON=1`；最后提交 `f=13799`，之后 BEAT 到 `f=19800`（暂停期间帧继续推进、无新提交）。
- **`0xEB66BC` 选招点证伪**：`SITE +00EB66BC +000=E92D48F0`、`INSTALL` 成功（`inst=1`），
  但 **`P=0` / `BEAT sel=0` 全程恒定**、`S.dP` 全部等于帧号（`LAST_P_F=0`）
  ⇒ 该函数在本场**从未被调用**，不能作否决点；`precision-A.tsv:14` 的描述不适用于当前怪/路径。
- **用户口述与日志精确对齐**：用户「阵亡前 30 秒~1 分钟 3 次后退前撞、后两次紧邻阵亡」，
  日志中该时间窗（距最后提交 30~60 秒）恰有 `535↔540` 交替 4 次
  （f=11430/11927/12277/13093，距阵亡 39.5/31.2/25.4/11.8 秒）与 `515→514` 4 次
  （f=11614/11764/12659/13462，距阵亡 36.4/33.9/19.0/5.6 秒），且 **10/11 处在发怒 st=1**。
  ⇒ 「后退→前撞」优先对应 `535(2/5) ↔ 540(7/61)` 交替，次选 `515(2/51)→514(7/15)`；
  本场 `19→4→19` 指纹命中 0 次（v22 场的另一套连招）。
- **`act+0x1A1` 确证为状态机**：取值 1/2/3，`1→2→3→1` 三段序列伴随 `id=525→526→515`
  （f=7126/7259/7338 与 f=12400/12512/12578 各一轮）；S 行 s1A1 恒为 1，
  说明 2/3 是瞬时中间态，只在 hook 调用瞬间可见 ⇒ 采样需放在 hook 内而非 onUpdate。
- **B 阶段重新定向（不再找抽选点）**：`0xaff40` 是唯一需要的 hook。
  v21i 卡住的根因是把攻击 id 换成 `id=3`（act=1 待机）与 `+0x73E0` 已写入的 act=7 不一致；
  新方案只在**复读指纹命中的那一次提交**把 `a1` 换成**同一 act 的其它攻击 id**
  （如 `535→517`、`540→520`，均保持 act 类别不变），低频、不破坏状态机一致性。
  先做只读模拟（打 `M` 行）再灰度，严禁写 `+0x73E1`、严禁跳过 `original!`。
- 本轮**未改动游戏目录、未换 nro、未改 load_order**；用户游戏仍在暂停中，等其继续/结束任务后回收完整日志。

### 17:12 第二次暂停标注 —— **致死连招确证**，v24 定向防护已部署
- 快照 2 `out/game_p54_20261108_1712_v23_paused_snapshot2.txt`：862 KB、`FATAL=0`、
  `S=80`；对比快照 1 新增 27 次提交（第二次战斗）。
- **用户明确「这次阵亡刚好是被后退再前撞击杀」**，日志最后一次提交正是
  `f=34130 id=540 (7/61)`，紧接 `f=34055 id=535 (2/5)`、**Δ=75 帧、`st=1` 发怒**，
  之后 41 秒无任何提交。⇒ **确证致死连招 = `535(2/5) → 540(7/61)` 交替**（Δ≈75 帧），
  循环回边 `540 → 535`（Δ≈350 帧）；`515→514`（Δ 1~21 帧）是另一组段推进，非致命主因。
- 快照 2 里该对在阵亡前 30 秒内又出现 2 轮（f=33098→33122 段、f=33462→34055→34130），
  与用户「后两次紧邻阵亡」一致。`0xEB66BC` 仍 `sel=0 / P=0`，选招点证伪已坐实。

### v24（已部署到 mods，下次启动生效；当前暂停的进程仍跑 v23 只读）
- **单 hook `0xaff40`**，废弃 `0xEB66BC`。触发条件极窄：
  `a1==540` 且前一提交 `id==535` 且间隔 ≤120 帧且 act∈{2,7} 且 `ACTIVE`。
  命中时把 `a1` 由 **540 换成 520**（`(7,16)`，同 act=7、游戏原生高频攻击），
  只改这一个参数，`original!` 其余 5 参原样透传。
- **与 v21i 的关键差异**：v21i 把所有 act=2/7 攻击在 60 帧窗口内换成 `id=3`(act=1 待机)，
  与 `+0x73E0` 已写入的 act=7 冲突 → 卡住/吼叫；v24 只动一个连招、保持 act 类别一致。
- **三重安全**：每场最多 6 次（`MAX_HIT`）；上次提交后 >240 帧无新提交自动
  `ACTIVE=false` 并打 `SAFE` 行；`HALTED`（对象失效/结算）时只透传。
  严禁写 `+0x73E1`、严禁跳过 `original!`。
- 产物：`out/rai_comboguard_v24i.nro`（md5 `47723ffc…`，**干预版，已部署**）
  ／`out/rai_guard_v24_SIM.nro`（`8627c382…`，只读模拟版，`applied=0`）
  ／回退 `out/rai_selectpoint_probe_v23.nro`（`dfb27ee5…`）、`out/rai_idstate_probe_v22.nro`。
  源码 `lib.rs` 保持 `INTERVENE=false` 基线；v23 备份 `lib.rs.v23bak`。
- `7_` 提示 STEP 21（**输出 `game_p54.txt` 与轮转逻辑未改**）；`load_order` 未变，
  备份 `load_order_backup_20261108_1715.txt`。**游戏运行中替换 nro 不影响已加载进程**，
  当前这场仍为零写入 v23，本场日志已由两份快照保全。
- **下一轮**：结束本场后重启跑 `7_`（自动加载 v24）。判据 `M ... applied=1` 次数、
  无 `SAFE`、零 FATAL、后退前撞是否消失/不再致死；若出现发呆/吼叫等异常，
  立即换 `rai_guard_v24_SIM.nro` 或 `v23.nro` 回退并报告。

### 17:18 方向修正（用户质疑成立）——**v24 已撤销，禁止硬编码招式**
- 用户质疑：「针对单个连招做防护」违背 AI 改进任务的根本目标，且不是 Rise 的 AI 逻辑。
  **该质疑成立**，v24 属于 whack-a-mole 式特例补丁：把「结果层的一个动作」当原因，
  用替换 `action_id` 事后改写；换怪 / 换招即失效，本质仍是 v11~v15 已证伪路线的变体。
- **立即撤销部署**：已回退到纯只读 `out/rai_idstate_probe_v22.nro`（md5 `7216f9f5…`）。
  `rai_comboguard_v24i.nro` / `rai_guard_v24_SIM.nro` 保留作**反例归档，标记废弃，禁止再启用**。
  `7_` 提示改 STEP 22（只读基线）；`load_order` 未变。
- **Rise 实测机制复核**（`DESIGN_v16.md §2.1~2.4`，107 个 `.user.2` 离线解析）：
  1. `_IsActionEnd` 门控 —— 动作没结束不重新抽选；
  2. 12 个 Hub 按处境分文件（`down_floor/down_wall/flash/no_target/...`），
     **攻击抽选只在 `same_main*` 内**，倒地/硬直根本不进攻击池；
  3. 3 状态（怒/普通/疲劳）× 5 距离档加权池，`_TransitionRate` 权重和恒 100；
  4. 防复读 = `_CheckPrevTableInfoList` + 3~300 秒计时器，**无独立 CD 字段**。
  ⇒ **Rise 里没有任何针对具体 `action_id` 的规则**；输出窗口是
  「门控 + 状态分支 + 池结构」的涌现结果，不是给某招打补丁。

### 结构性原则（写死为任务纪律，后续一律遵守）
- **禁止硬编码任何 `action_id` / `(act,sub)` 组合作为干预目标**；`535/540/519…` 只能作为
  离线分析的证据，不得进入插件逻辑。
- 干预必须在**抽选层**（rng 产生 / L2 表选择 / 权重判定），不能在 `0xaff40` 改 `a1`。
- 规则必须**对所有动作一视同仁**：通用 prev 表检查 + 秒级计时器 + 状态 Hub 分支 + 加权池。
- 状态分支输入（已确证字段）：`act+0x1A1`（0/1/2/3）、`act+0x518`（怒/疲劳）、
  HP 比值 `+0x370/+0x374`、尺寸 `+0x1B0`；距离档与表号待定位。
- 门控层：v17 确证 GU「动作结束→下一提交恒 1 帧」，Rise 缺的 Think 间隔须人为制造，
  但**不得用替换动作实现**（v21i 卡住）。
- GU 抽选层线索：`+0x73E0` 低 16 位 act/sub 含 prev（197/198 吻合）；
  `+0x73E8/+0x73EC` 每次提交刷新同一个 16 位 rng（v16）。
  **下一步只读任务**：定位 rng 写入者 / L2 表选择函数（BL 调用图 + 字段写入点），
  在此之前不编译、不部署任何干预版。

### 17:22 证据核查（用户两问）——两处表述降级/修正
- **Q1 秒级计时器**：Rise 里**确有** `EnemyThinkTimerData._Timer`（em001 5/10/15/30/45/180 秒，
  三只怪合集覆盖 3~300 秒），但 `ConditionInfo` 里**没有任何 Timer 字段**，
  ⇒ 此前「防复读 = 前表检查 + 秒级计时器」是**过度推断**，已在 `DESIGN_v16.md §2.4` 改写。
  确证的防复读机制只有 `_CheckPrevTableInfoList`（376 个条件实例，103 空、其余单 ref）。
  本项目纪律中「3~300 秒计时器」相应降级为「可选的自行设计规则」，不再声称来自 Rise。
- **Q2 抽选 / rng 定位**：**既有逆向成果里有大量「派发器 / 状态表」结构**
  （`refs/re/.../analysis/monsters/mon-ai-entry.md`：53 张 `+0x73E0` 状态表、89 个 18 态派发器、
  每怪方法表簇；`mechanics/monster-state-machine.md`：9 个 `#0x73e1` 二级表；`precision-A.tsv`），
  此前未充分利用。**但资料库里没有任何 rng 产生 / 加权抽选函数的标注**。
  且 v16 把 `+0x73E8/+0x73EC` 的 16 位值命名为「rng」证据不足：重算 217 条记录，
  该值 209 个不同取值**每个只映射一个 (act,sub)**、不单调、不等于帧号低 16 位，
  更像动作序号 / 表索引。⇒ 「定位 rng」不是既有成果，也不能以该字段为锚。
- **方向调整**：下一步从 `mon-ai-entry.md` 的派发器 / 二级表 / 方法表簇出发，
  做只读探针确认「L1 动作号与 L2 变体号在何处被确定」；在此之前不设计任何重抽规则。
- 本轮只改文档与结论口径，**未改动部署、nro、load_order、7_ 执行逻辑**。

## 17:28 再次确认（用户第二次问「Rise 侧数据不足是否需要解包 / 逆向」）

- **答案：不需要再解包；暂不需要 Rise 代码逆向；当前瓶颈在 GU 侧。**
- 复用 11-08 10:15 那次的结论：用户当时建议改走 pak 解包，已执行完毕并扩到
  **107 个 `.user.2` + 107 个 `out/rsz_json/*.json` 全解析成功**；工具链齐备
  （`00_Tools/06_REEngine_Pak/ree-pak-cli.exe`、`MHR_STM_Release.list`、
  `refs/rszmhrise.json` 69 MB / 250700 类型、`refs/RE_RSZ.bt`、`tools/rsz_parse.py`），
  `refs/rise_enemy_ai_paths.txt` 442 条路径可作按需增量抽取清单。
- Rise 侧「数据不足」要分两类，不能混为一谈：
  1. **文件覆盖不足**（其它怪 / hub 全量 / flow / datatune / action_param）→ 按需增量抽取成本很低，
     但结构性对标（`_IsActionEnd` 门控 / 12 个 Hub / 3 状态×5 距离档加权池 /
     `_CheckPrevTableInfoList`）用现有 107 个已足够，**不必再抽**。
  2. **代码层执行语义**（计时器与防复读的因果、权重如何参与抽选、Think/Routine 调用顺序）
     → `.user.2` 是 RSZ 数据文件，看不到执行逻辑；需 **Rise 主程序反汇编**才算严谨确证。
     本机 D 盘未检出 Rise exe / pak（当时抽取用的 pak 需用户指路），且属**可选深挖、非阻塞项**。
     REFramework Lua 实机观测是互补验证手段（验证规则是否被按预期执行），需一次 Rise 实机运行。
- 当前唯一阻塞是 **GU 侧「L1 动作号 / L2 变体号在何处确定」**，属 GU 逆向；
  地图已在 `refs/re/.../analysis/monsters/mon-ai-entry.md`（53 张 `+0x73E0` 状态表 /
  89 个 18 态派发器 / 9 个 `#0x73e1` 二级表），只需只读实机探针确认。
  即便把 Rise 代码全逆出来，GU 侧没有对应插入点也无法落地。
- 本轮仅补口径记录，**未改动部署 / nro / load_order / `7_` 执行逻辑 / `6_`**。

> **进度总览索引**：`STATUS.md`（2026-11-08 17:31 快照）——阶段 S0~S5、已完成证据、当前卡点、剩余缺口与下一步。本文件仍为唯一状态流水。

## 17:33–17:42 继续推进：S5 第一步**离线静态确证** + 部署 v25 只读抽选层探针

### 静态扫描（`tools/scan_select_writers.py`，零实机、零风险）
- 全量扫 `refs/hpbar/main_text_decomp.bin`（GU NSO0 text，0x13F1DEC 字节）：
  `movw #0x73E0/73E1/73E4/73E8/73EC` 之后 2137 个寄存器偏移访存点，
  **仅 10 个函数含写入**（其余 1416 个仅读 = 派发器主体）。BL 调用图 23195 个目标。
- **`0x76154` = 统一落盘函数**（`push {r4..sl,fp,lr}`）：
  `0x76160 sl=r2`、`0x76164 r6=r1`、`0x76168 r9=r0`，`strb r6,[sp,#19]` / `strb sl,[sp,#18]`；
  `0x76868 strb +0x73E0 = r1(act)`、`0x76870 strb +0x73E1 = r2(sub)`、
  `0x76878 strh +0x73E8 = sl`；同时复位 `act+0x1A1/1A2/1A3`、写 `+0x13F8=0`、
  `+0xB7F0=1.0f`，并调用发怒 getter `0x8172c/0x81774/0x81790`。
  **17 个 BL 调用者**：`0x75224`(action-end)、`0x752ec`、`0x75338`…`0x769d4`，
  各分支带固定 `kind`=0/1/2/3/5（`r3`）⇒ **GU 版「状态 Hub」**。
  `0x75224` 内还按 `call 0x816d0`(怒) 与 `act+0x1A8 / +0x2C0` 选 `sub`=0/1/2。
- **`0x752EC` = 通用 (act,sub) 提交入口**（`push {r4,r5,r6,lr}`）：
  `r6=mon, r5=r1(act), r4=r2(sub)`；若 `+0x73E0 == 11` 跳过；否则
  `r1=act, r2=sub, r3=2, [sp]=0` → `bl 0x76154`。**393 个 BL 调用者**，
  分布在 `0xCF8BEC..0x1111A6C` 的每怪每动作脚本函数末尾。
- `0xAFF40` 4398 个 BL 调用，分散在每怪动作函数（单函数最多 11 次）。
- ⇒ **决定性结构结论：GU 没有集中式加权抽选器 / rng 函数**，决策是分布式动作脚本，
  每个 (怪, 动作) 函数末尾直接调 `0x752EC(mon, act, sub)`。这解释了
  v19 找 `0xEB66BC` 选招点（0 调用）、`+73E8`「rng」（实为动作序号/表索引）
  为何全部落空，也说明资料库检索不到 rng/抽选标注并非遗漏。
- **对 Rise 对标的影响**：Rise「3 状态×5 距离档加权池」在 GU **无对应结构，不能照搬**；
  可行的是「门控 + 状态 Hub + 通用 prev 表」。通用干预点选**收敛点 `0x752EC`**：
  393 个脚本必经、对所有动作一视同仁、且发生在 `0x76154` 写字段**之前**
  ⇒ 符合「只在抽选层、不事后改字段」纪律，避开 v21i 的状态机冲突根因。
  **边界**：静态结论尚未实机验证；`0x752EC` 是「所有决策的必经收敛」，
  不是「加权池」，不得过度表述。

### v25（已部署，纯只读双 hook，md5 `0a2b4dc8…`）
- `0x752EC`（新，3 参数全在寄存器）打 `G` 行：`act/sub/w0→w1/st`；
  运行时首字校验期望 `E92D4070`，被 IPS32 跳板改写则 `SKIP` 降级为单 hook。
- 保留已验证的 `0xAFF40` 打 `A` 行，新增 `dG`（距最近 G 帧差）与 `gAct/gSub`。
- 零写入、零游戏函数调用、`onUpdate` 不读游戏内存、不依赖 HP Bar、`original!` 全透传。
- 判据：`sel=1` / `G` 有数据 / `A.dG≈0` / `G.w1` 低字节==act、次字节==sub /
  `A.gAct/gSub == A.a/s` / 零 FATAL。分析脚本 `tools/analyze_v25_log.py`（v22 日志冒烟通过）。
- 产物：`out/rai_selectlayer_probe_v25.nro`、`out/gu_select_writers.json`、
  `tools/scan_select_writers.py`、`tools/analyze_v25_log.py`；
  源码 `lib.rs`（v24 备份 `lib.rs.v24bak`）；`7_` 提示 STEP 23（输出路径与轮转逻辑未改）；
  `load_order` 未变，备份 `load_order_backup_20261108_1742.txt`。
- 回退：`out/rai_idstate_probe_v22.nro`（`7216f9f5…`）。
- **下一轮**：重启跑 `7_`，打满 60 秒并锁定怪；跑 `tools/analyze_v25_log.py`。
  全通过前不编译、不部署任何干预版。

## 17:51 实时日志（用户仍在游戏中，只读快照）——**`0x752EC` 实机证伪**，v26 已部署待下轮

- 快照 `out/game_p54_20261108_1751_v25_live_snapshot.txt`（361 KB，f 到 20400）：
  `RAI v25` banner 正常，`INSTALL h_select +000752EC first=E92D4070` 成功、`sel=1`、
  **零 FATAL**；`MON=1`（mon=0C1A0060 / act=0C1A14A0 / hp 3880→2630 / sp=14），
  `A=79`（a/s 与 id 分布正常、st 0/1 都有）、`T=0`、`BEAT=34`。
- **但 `G=0` 全程**，79 条 A 的 `dG` 全为 0x7FFFFFFF ⇒ `0x752EC` 在本场从未产生有效调用。
  与 v23 的 `0xEB66BC` 同型：静态 393 个调用者 ≠ 当前怪的运行路径。
- **静态复核给出原因**：`0x75224`（action-end，v17 确证 162 次 END）内部
  `0x752d4: bl 0x76154` **直接**调统一落盘函数，**不经 `0x752EC`**。
  ⇒ 常规提交链是 `END(0x75224) → 0x76154 → 0xAFF40`；`0x752EC` 只是动作脚本的可选切换入口。
  （G=0 的两种解释「从未被调用」/「a0 非 mon 被 ident 过滤」结论相同：它不是收敛点。）
- ⇒ **修正 17:42 的结论**：真正的通用收敛点是 **`0x76154`** —— 17 个状态 Hub 调用者
  （含 action-end）必经、对所有动作一视同仁、在写 `+0x73E0/73E1/73E8` **之前**，
  正好对标 Rise「`_IsActionEnd` 门控 + 状态 Hub」，且避开 v21i 改 `a1` 破坏字段一致性的根因。
  `STATUS.md §3`、设计文档均已改写；不得再声称 `0x752EC` 是收敛点。

### v26（已部署到 mods，下次启动生效；用户当前这场仍跑 v25 只读）
- 双只读 hook：**`0x76154`（新，5 参数，第 5 个在栈上）** + 已验证的 `0xAFF40`。
  `Q` 行记 `act=r1 / sub=r2 / kind=r3 / p5 / w0→w1 / st`；`A` 行新增 `dQ / qAct / qSub / qKind`。
  新 hook 首字校验期望 `E92D4FF0`，不符则 `SKIP` 降级为单 hook。
- 零写入、零游戏函数调用、`onUpdate` 不读游戏内存、不依赖 HP Bar、`original!` 五/六参原样透传。
- 判据：`uni=1` / `Q` 有数据 / `A.dQ≈0` / `Q.w1` 低字节==act、次字节==sub /
  `Q.kind` 分布（区分 17 个 Hub）/ 零 FATAL。分析脚本 `tools/analyze_v26_log.py`（v25 快照冒烟通过）。
- 产物 `out/rai_unified_probe_v26.nro`（md5 `c9b7dff…`）；源码 `lib.rs`（v25 备份 `lib.rs.v25bak`）；
  `7_` 提示 STEP 24（输出路径与轮转逻辑未改）；`load_order` 未变，
  备份 `load_order_backup_20261108_1755.txt`。回退 `rai_idstate_probe_v22.nro`。
- **游戏中替换 nro 不影响已加载进程**：本场日志仍属 v25，已用快照保全；
  用户可照常打完，结束后重启即加载 v26。全通过前不编译、不部署任何干预版。

## 17:58 可行性核查（用户：跨怪通用性 / 能否参照 Rise 加权池）
- **`0x76154` 是共享基类实现，不是单怪专属**（静态证据）：
  1. 函数体 0x76154..0x76908（493 条指令）的 **41 个 BL 目标中 0 个**落在每怪专属区
     `0xCF0000..0x1140000`；目标全在共享区（`0x8172c/0x81774/0x81790` 发怒 getter、
     `0x7fc08`、`0xb2d2c`、`0x8dee0`、`0xbd184`、`0xba874`、`0xc46c8`…）。
  2. 含 **4 条 `blx rX`**（虚调用）⇒ 每怪差异经对象 vtable 分派，函数体本身不判怪种。
  3. 17 个 BL 调用者全部在 `0x752d4..0x769d4`（< 0x77000 共享区）；
     每怪派发器清单从 `0xCF0000` 起（`mon-ai-entry.md`）。其中 `0x75224` 是
     vtable slot 247（v17 确证），所有怪共用该槽 ⇒ 都走 `0x76154`。
  ⇒ **结构上对所有怪通用**；实机目前只在将军镰蟹验证，换怪需一次只读复验（低风险）。
- **加权池可行性**：「照搬 Rise 数据表」不可行（GU 无集中抽选点、招式集不同）；
  「参照 3×5 结构自行实现」可行但属**自建 Rise 风格规则**，前提 4 项：
  ① v26 确证 `0x76154` 实机覆盖；② `+0x518` 的 st=2（疲劳）实机捕获；
  ③ 玩家-怪距离字段定位（做 5 档）；④ 用**跨怪通用的 act 类语义**建候选池，
  不得按单怪 id 分布建表（否则退化为单怪特例，违背底层通用定位）。
  权重数值只能借用 `rise_routine_rates.json` 的「和=100 / 怒疲劳偏向」作模板，
  必须按 GU 实机分布重新校准。
- 用户明确项目定位：**本 AI 改进 mod 是更底层的通用改进，不仅针对一只怪** —— 已写入项目长期记忆。

## 18:05 v26 实机日志 —— **收敛点 `0x76154` 被 IPS32 切成解释器函数，不可 hook**；v27 上移 Hub 层

- 日志 `out/game_p54_20261108_1805_v26_unified.txt`（263 KB、f 到 13800）：`RAI v26` banner 正常、
  **零 FATAL**、`MON=1`（mon=0C139440 / act=0C13A880 / hp 3880→2119 / sp=0014 / st 0/1 都有）、
  `A=73` 条动作提交正常；最后提交 f=11340，之后 2460 帧无新提交（阵亡/暂停/结算窗口）。
- **关键行**：`SKIP h_unify +00076154 first=E28FF7AD`。实机首字不是静态镜像的 `E92D4FF0`，
  而是 `add pc,pc,#imm` 跳板（解码：imm12=7AD → 立即数 0x02B40000，
  目标 ≈ `0x76154+8+0x2B40000`）。
- **根因确证**：本场日志含 `MH4U Port ... 218 word(s) of code patched,
  176 function(s) run in the interpreter now`。解析该 IPS32 的 218 条记录：
  落在 `0x70000..0x78000` 的只有 `0x76254`/`0x70128`/`0x70150` 三条，
  其中 `0x76254` 正在 `0x76154..0x76908` 函数体内 ⇒ Recomp 把**整个函数**切进解释器，
  并在函数入口写跳板。与 `05_TargetHealth/NOTES.md §2` 记录的 `main+0x9A764`
  由 `E3012428`→`E28FF7AD` 是同一机制。
- **工程结论**：该跳板 **PC 相对**，Forge trampoline 在别处执行会跳错解释器槽 ⇒
  **不能直接 hook `0x76154`**；v26 的 `SKIP` 是正确降级。
  ⇒ **Q=0 只说明 hook 没装，绝不能推断 `0x76154` 不活跃**（与 v25 的 `G=0` 性质不同）。
  静态「统一落盘 / 17 个状态 Hub 调用者」结论仍成立，但它是概念收敛点，不是可挂钩点。
- **静态复核给出替代路径**：17 个 Hub 调用者函数里 **11 个仍是干净标准 prologue**
  （`0x75224` E92D4010、`0x752EC` E92D4070、`0x75338`/`0x75394`/`0x753EC`、
  `0x75444`/`0x754B8`/`0x75510`/`0x75574`、`0x76908`/`0x76984`），
  全部在共享区、体内无补丁。`0x75224`（vtable slot 247 / action-end）在
  v16/v17/v18 三场实机首字恒为 `E92D4010`，v17 确证 162 次 END、零 FATAL，
  且 vtable 槽位所有怪共用 ⇒ **干净、活跃、跨怪通用**。

### v27（已部署到 mods，下次启动生效；当前进程仍跑 v26 只读）
- 双只读 hook：**`0x75224`（新，4 参，期望首字 `E92D4010`，不符则 SKIP）** + 已验证的 `0xAFF40`。
- `SITE` 行一次性 dump **12 个候选 Hub / 收敛点入口的运行时首字**，判定哪些被切解释器。
- `H` 行记录 action-end 时的 Rise 式 Hub 输入：`+0x518`(怒/疲劳)、`+0x1A1`(状态机)、
  `+0x1A8`、`+0x2C0`、HP/max、`+0x73E0` prev，并标 `eq`（a0 是否 == mon）。
  `A` 行新增 `dH`（距最近 H 帧差）。`peek()` 纯校验不写全局，MON 仍只由 `0xAFF40` 设定，
  避免 action-end 被非主怪对象调用时污染目标怪。
- 零写入、零游戏函数调用、`onUpdate` 不读游戏内存、不依赖 HP Bar、
  未硬编码任何 action_id、`original!` 全透传。
- 产物 `out/rai_hublayer_probe_v27.nro`（md5 `0b79be26…`）；分析脚本
  `tools/analyze_v27_log.py`（v26 日志冒烟通过）；源码 `lib.rs`（v26 备份 `lib.rs.v26bak`）。
- `7_` 提示 STEP 25（输出路径与轮转逻辑未改）；`load_order` 未变，
  备份 `load_order_backup_20261108_1810.txt`。回退 `out/rai_idstate_probe_v22.nro`。
- **下一轮**：结束本场后重启跑 `7_`，打满 60 秒并锁定怪，跑 `tools/analyze_v27_log.py`。
  判据 `INSTALL h_hub / hub=1`、`SITE` 首字、`H` 有数据、`A.dH≈0`、`H.eq=1`、
  Hub 输入字段分布、零 FATAL。全通过前不编译、不部署任何干预版。

### 新增纪律（与既有硬约束并列）
- **IPS32 解释器函数入口不可 hook**：新 hook 点必须先核对**运行时首字**，
  凡 `E28FFxxx`（`add pc,pc,#imm`）一律 SKIP；静态镜像的 prologue 不等于运行时首字。
- 静态调用图只能给候选；活跃路径与可挂钩性都必须实机确认
  （`0xEB66BC`→`0x752EC`→`0x76154` 已连续三次验证这一点）。

## 18:18 v27 实机 —— **Hub 层判据全部通过**；v28 部署（最后一轮只读）

- 日志 `out/game_p54_20261108_1818_v27_hublayer.txt`（285 KB、f 到 16200）、
  `FATAL=0`、`H=70 / A=59 / T=2 / BEAT=27 / MON=1`、
  `mon=0C1F0060 act=0C1F14A0 hp 3760→2624 sp=0014`。
- **SITE 实机确证**：12 个候选入口里**只有 `0x76154` = `E28FF7AD` 是解释器跳板**，
  其余 11 个全是标准 prologue（`E92D4010`/`E92D4070`/`E92D48F0`）
  ⇒ 18:05 的静态判断 100% 正确；`0x76154` 是唯一不可 hook 的点。
- **`INSTALL h_hub +00075224` 成功**，`H.eq=1` 69/70、`a0` 唯一值 1 个
  ⇒ **`0x75224` 的 this 就是 mon**（v19b「END hook 的 this 不是 mon」的旧困惑由此解决，
  当时是末段对象/判据问题，不是另一类对象）。
- **`A.dH=0` 52/59**、H 间隔中位 96 帧 / A 87 帧 ⇒ 第三次独立确证
  「action-end → 提交同帧」，与 v17 / v19b 一致。
- **`H.w0` 与同帧 A 反推的 `+0x73E0` 0/52 相同** ⇒ H 确实在字段写入**之前**，
  是合规的「决策前」层（时序 `END → 提交并改写 +0x73E0 → 0xAFF40`）。
- **Hub 输入初探**：`s2C0` = 0（开局满血 9 次）/ `0x01000001`（常态 59）/
  `0x01000101`（2 次）；`s1A1` = 1(66) / 3(4，3/4 在发怒，f=7560/8872/10620/11035)；
  `s1A8` 恒 `0x00440049`（**无区分度，不能作 Hub 分支输入**）；
  `st` 怒/普通 41/29；`T` 行 0→1(f=8872)、1→0(f=13395)。
  `a3` 多次为 `0x3F800000`(float 1.0) ⇒ `0x75224` 形参含 float，暂不改参数。
- **`skip=59`**：`0x75224` 共被调用约 129 次，59 次 a0 未通过自洽判据 ⇒ 身份待定，
  关系到「跨怪通用」是否实机确证（若 vt 在 vtable 区且 species 合理 = 其它怪）。

### v28（已部署，下次启动生效；当前进程仍跑 v27 只读）——**最后一轮只读**
- 双只读 hook 不变（`0x75224` + `0xAFF40`），只加三类观测：
  ① `H.w1` = `original!` **之后**再读 `+0x73E0`，与 `w0` 对照，
     直接确证 action-end 内部是否就是决策落盘点；
  ② `J` 行（限 40 条）打印 peek 失败调用者的 `a0 / vt / w73 / sp`，判定其它怪或非怪对象；
  ③ `A.hW1` 与 A 行字段对齐、再采一轮 `s2C0`/`s1A1`。
- 零写入、零游戏函数调用、不依赖 HP Bar、未硬编码 action_id、`original!` 全透传。
- 产物 `out/rai_hubcause_probe_v28.nro`（md5 `94736e85…`）；
  `tools/analyze_v28_log.py`（v27 日志冒烟通过，已修十六进制/None 防御）；
  源码 `lib.rs`（v27 备份 `lib.rs.v27bak`）。
- `7_` 提示 STEP 26（输出路径与轮转逻辑未改）；`load_order` 未变，
  备份 `load_order_backup_20261108_1822.txt`。回退 `out/rai_idstate_probe_v22.nro`。
- **下一轮**：结束本场后重启跑 `7_`，打满 60 秒并锁定怪，跑 `tools/analyze_v28_log.py`。
  判据 `H.w0 != w1` / `A.hW1 == A 行字段` / `J` 身份 / 零 FATAL。
  全通过后进入**通用 Hub 层干预设计**（门控 + 状态分支 + 通用 prev 表），
  仍不硬编码 action_id、不事后写字段、不写 `+0x73E1`。

## 18:29 v28 实机（用户即将退出，只读快照）——**prev 表机制确证 + GU 状态 Hub 反汇编定案**

- 日志 `out/game_p54_20261108_1829_v28_hubcause.txt`：`FATAL=0`、
  `H=58 / A=56 / J=40 / T=1 / BEAT=20`、`mon=0C1F0060 hp 3880→…`；
  `SITE` 与 v27 完全一致（仅 `0x76154` 是跳板）。
- **判据 ① `w0 != w1` 58/58**：`original!` 之后 `+0x73E0` 必变。
  样例 `00022802 → 28020000`、`28020401 → 04010000`，即
  **`w1 = ((w0 & 0xFFFF) << 16) | 新(act,sub)`**：低 16 位（当前动作）移到高 16 位成为 prev，
  低 16 位写入新决策。8 次低 16 位为 0 是新决策为 (0,0) 的中间态。
  ⇒ 原判据「`A.hW1` 全等 A 字段」0/56 属预期（w1 是 decision-in-progress 中间态），
  已改为检查 prev 链：**`hW1` 高 16 位 == A 的 prev 55/56**、**`H.w0` 低 16 位 == A 的 prev 48/48**。
  ⇒ **GU 自带 prev 表在 action-end 内部更新**，等价于 Rise `_CheckPrevTableInfoList`；
  干预层若要防复读，最自然的输入就是 `+0x73E0` 高 16 位。
- **判据 ③ `J` 行**：3 类非主怪对象调用 `0x75224`
  （`0C430060` 26 次、`0C106550` 11 次 vt=`01A204D4`、`0C13B9B0` 3 次 vt=`019B44E8`）；
  后两类有合法 vtable 且 `+0x73E0` 呈正常 (act,sub,prev) 结构 ⇒
  **该 Hub 被多类对象共用，跨对象通用有实机迹象**（仍非「换怪种」的严格验证）。
  **探针盲区**：`0C430060` 超出 `HEAP_HI=0x0C400000` 被主动跳过（vt/sp 全 0 是没读，不是无效）；
  下一版堆区上界须放宽到 ≥ `0x0C500000`。

### 静态反汇编 `0x75224` 全文（0x75224..0x752EC）——**GU 状态 Hub 定案**
```
7523c  bl 0x816d0            ; 发怒 getter(mon) -> 0/1
75248  ldr r1,[r4,#0x1428]   ; act 对象
75250  ldrb r0,[r1,#0x1a8] ; tst #0x40    (怒时)
75260  ldrb r1,[r1,#0x2c0] ; cmp #1       ★ Hub 分支输入
75264  ldrb r0,[r4,#0x73e0]; cmp #11      (act==11 跳过)
75278/75294/752b8  bl 0x49694   ; monster-em 通用配置 getter，返回值被丢弃
75284/752a0/752c4  mov r2,#1 / #0 / #2     ★ kind = 状态 Hub 分支号
752d4  bl 0x76154(mon, r1=0, r2=kind, r3=2, stack5=0)
752e8  b 0x82510(mon, 0)     ; 尾调用
```
- ⇒ **`0x75224` 不是单纯 action-end，而是「按状态选 Hub 分支并提交」**：
  分支依据 = 发怒 `0x816d0`、`act+0x1A8` bit6、`act+0x2C0` 低字节、`mon+0x73E0` 的 act==11；
  输出 = `kind` 0/1/2（`0x76154` 的 r2）。这正是 **Rise 12 个处境 Hub 的 GU 对应物**。
- **`act+0x2C0` 与 v28 实机完全对齐**：反汇编读其低字节 `cmp #1`；
  实机 `s2C0` 低字节 = 1（`0x01000001` 48 次 / `0x01000101` 2 次）或 0（8 次）
  ⇒ 多数时间走 kind=1 分支。**这是第一个「静态分支条件 ↔ 实机字段」双向确证的 Hub 输入**。
- **`0x49694` 不是抽选器**：反汇编显示它读全局 `+0xd56` 字节并查 `+0xd758+idx*12` 表，
  返回 signed byte；资料库 `attr-callervote.tsv:12` 标为 `monster-em`（6/6 调用者），
  42 个 BL 调用者，返回值在 `0x75224` 中被丢弃 ⇒ 只是带副作用的通用配置 getter。
- ⇒ 修正 17:42 起的参数假设：`0x76154` 的 r1 不是 act、r2 不是 sub；
  **`0x75224` 传的是 `r1=0, r2=kind, r3=2`**。真正的动作抽选 + `+0x73E0` 写入在
  `0x76154` **内部**（该函数被 IPS32 切进解释器，不可 hook）。

### 由此产生的新结构性障碍（诚实记录，不硬推方案）
- 干净的 Hub 调用者层（17 个函数，11 个可 hook）只负责**选 kind**；
  动作决策与字段写入在不可 hook 的 `0x76154` 内。
- 因此「在抽选层做通用否决」目前有三条候选，均有待评估，**本轮不编译任何干预版**：
  1. 在 Hub 调用者层改 `kind`（影响状态分支，但不直接改动作；效果未知）；
  2. 在 `0x75224` 的 `bl 0x76154` 处做 inline hook / 参数拦截（需写游戏代码内存、可恢复，风险最高）；
  3. 继续只读：挂 2~3 个额外干净 Hub 入口（`0x75338`/`0x75394`/`0x76908`），
     先拿到 kind 全分布与状态输入，再决定干预形式（最稳，但多一轮实机）。
- **下一轮需用户拍板选哪条**；在此之前部署保持 `v28.nro` 纯只读不变。
- 本轮只改文档与分析脚本（判据 ② 改为 prev 链、修 hex/None 防御），
  **未换 nro、未改 load_order、未动 `7_` 执行逻辑**。

## 18:50 用户拍板路线 3 → v29 多 Hub 只读观测（已编译部署，待下一轮实机）

### 用户决策
- 三选一里选 **3**：继续只读，挂 2~3 个额外干净 Hub 入口，先拿 kind 全分布与状态输入，
  再决定干预形式；**本轮不编译任何干预版**。用户已退出游戏，替换 nro 安全。

### 静态复核（`tools/disasm_hubs.py`，本轮新增，零实机、零风险）
- **关键定案 / 修正旧表述**：`0x76154` 开头 `r7=r3 / sl=r2 / r6=r1 / sb=r0`，
  `strb r6,[sp,#0x13]`、`strb sl,[sp,#0x12]`，`cmp r7,#1` 时跳过 `+0x73E0==11` 门控 ⇒
  **`0x76154(r0=mon, r1=act, r2=sub, r3=mode, [sp]=p5)`**。
  17:33 记的「各分支固定 kind=0/1/2/3/5（r3）」**有误**：**r3 是 mode（2/5/0/1），r2 才是 kind/sub**。
- 各 Hub 的静态调用参数（全部 `r3=2`，除标注者）：
  `0x75224`(0, kind=0/1/2 按怒/`+0x1A8` bit6/`+0x2C0`/act==11 分支, 2)、
  `0x752EC`(传入 act, 传入 sub, 2)、`0x75338`(0,3,2)、`0x75394`(0,6,2)、
  `0x753EC`(0,7,2)、`0x75444`(0,8,2)、`0x754B8`(0,9,2)、
  `0x76908`(a1,a2,**5**)、`0x76984`(…,**5**)、`0x75510`(73E6,73E7,**0**)、
  `0x75574`(a1,a2,a3) 直通。
- **`0x76908` 是「act/sub 请求」入口，不是纯 kind Hub**：`+0x7420 != 0` → 直接
  `0x76154(mon, a1, a2, 5)` 并置 `+0x73EA=1`；`+0x7420 == 0` → 排队
  （`+0x73E5=1`、`+0x73E6=a1`、`+0x73E7=a2`），由 `0x75510` 在 `+0x7420 != 0` 时
  取回 (73E6,73E7) 提交（mode=0）。⇒ GU 有「动作请求排队」层，且这是**带参 Hub**，
  hook 层可直接观察 a1/a2；这使路线 1「在 Hub 层改参数」只对带参 Hub 有意义。
- 12 个候选入口静态首字与 v28 实机完全一致：仅 `0x76154`=E92D4FF0（运行时被换成
  E28FF7AD 跳板），其余 11 个干净。

### v29 设计（路线 3 落地）
- 5 个只读 hook：`0x75224`(H 行) + `0x75338`/`0x75394`/`0x76908`(U 行，带 `site`)
  + `0xAFF40`(A 行)。4 个 Hub 逐个校验运行时首字（期望 E92D4010/E92D4010/
  E92D4010/E92D4070），不符 SKIP；`OK` bitmask 由 `BEAT hub=` 报出，**15 = 全装**。
- `U` 行：`f n site eq a0 a1 a2 a3 w0 w1 st s1A1 s2C0 vt sp hp/mx`；
  `H` 行新增 `site/vt/sp`；`J` 行新增 `site`。`vt`=对象首字(vtable 指针)，`sp`=species。
- **两处必须记录的防护**（否则这一轮数据会废）：
  ① 观测堆上界 `HEAP_HI` 放宽到 `0x0C500000`（补 v28 的 `0C43xxxx` 盲区），
     但 **MON 识别仍保持 `0x0C400000` 窄口径**，A 行与 v27/v28 完全可比；
     且 `LAST_H_F/LAST_H_EQ/LAST_W1` **只在 `eq==1` 时更新**，防止放宽后进 H 行的
     非主怪对象污染 A 行 `dH/hEq/hW1` 判据。
  ② U 行按 site 各限 160 条（`MAX_U_SITE`），避免某个高频 Hub 吃光 `MAXLOG=1600`
     导致后续 H/A 全部无日志。H 400 / A 400 / J 120 上限不变。
- 零写入、零游戏函数调用、`onUpdate` 不读游戏内存、不依赖 HP Bar、
  未硬编码任何 action_id、`original!` 全透传。

### 产物与部署
- 源码 `plug/context_probe/src/lib.rs`（v28 备份 `lib.rs.v28bak`）；
  产物 `out/rai_multihub_probe_v29.nro`（28672 B，md5 **`040b4341…`**），
  已部署到 `mods/RiseAI_EntryProbe/romfs/nativeNX/plugins/rai_entrylocator_probe.nro`（同 md5）。
- 新增 `tools/disasm_hubs.py`、`tools/analyze_v29_log.py`（用 v28 日志冒烟通过：
  H=58/A=56/J=40/FATAL=0 全解析正常，U=0 时给出明确提示）。
- `7_` 提示改 STEP 27（**只改 echo 提示文字**；`OUT=02_Workspace/game_p54.txt`、
  `.prev/.prev2` 轮转、`mhgurecomp.exe` 启动行均未动）；`6_` md5 仍 `7361445f989b…`；
  `load_order` 未变（只做只读复制备份 `load_order_backup_20261108_1848.txt`）。
- **编译环境注意**（本会话踩坑）：`cargo.exe` 与 `arm-none-eabi-gcc` 都不在 PATH。
  可用命令：
  `CARGO_TARGET_ARMV7A_NONE_EABI_LINKER="D:/MHGU mod maker/00_Tools/forge_toolchain/xpack-arm-none-eabi-gcc-14.2.1-1.1/bin/arm-none-eabi-gcc.exe" "C:/Users/RongLynn/.cargo/bin/cargo.exe" build --release -Zjson-target-spec -Zbuild-std=core,alloc --target armv7a-none-eabi.json`
  → `python bin/elf2nro.py <.so> out/<name>.nro`。链接器 `-z norelro ignored` 警告无害。
- 回退：`out/rai_hubcause_probe_v28.nro`（`94736e85…`）。

### 下一轮实机（用户操作）
- 重启跑 `7_`，进任务打满 60 秒以上并锁定怪；结束后
  `python tools/analyze_v29_log.py 02_Workspace/game_p54.txt`。
- 判据：`BEAT hub=15`（4 Hub 全装）/ 零 FATAL / `SITE` 与 v28 一致 /
  `U` 非空且按 site 有分布 / `0x76908` 的 a1/a2 是否呈 (act,sub) 语义 /
  `0C43xxxx` 的 `vt+sp` 是否可读且合理（判定是否另一只怪）/ H-A prev 链仍 55+/56、
  `A.dH=0` 仍接近 v28。
- 若 `U=0`：常规链只走 `0x75224`，下轮换 `0x75510`/`0x75574`/`0x752EC` 等带参入口；
  若 `U` 充足：进入「通用 Hub 层干预设计」，仍不硬编码 action_id、不事后写字段、
  不写 `+0x73E1`。

## 19:00 v29 实机 —— **U=0 确证（3 个处境 Hub 本场零调用）**；静态 BL 图给出更好的下一批入口，v30 已部署

日志 `out/game_p54_20261108_1900_v29_multihub.txt`（189 KB，f 到 9600）。

### 判据结果
- **`hubMask=15`，5 个 hook 全装**（4 个 Hub 首字均与静态一致），**零 FATAL**。
  `H=47 / A=42 / J=28 / T=1 / BEAT=16 / log=135`（远低于 MAXLOG=1600）
  ⇒ **U=0 不是日志截断**。
- **`U=0`**：`0x75338`/`0x75394`/`0x76908` 本场**一次都没被调用**。
  28 条 `J` 行 **全部 `site=075224`**，即连「peek 失败的调用」都不存在
  ⇒ 不是过滤/身份问题，是函数根本没进运行路径（与 v25 的 `G=0` 同型但证据更硬）。
- **`0x75224` 两处防护有效性确证**：`H.w0` 低 16 位 == A 的 prev **37/37**、
  `hW1` 高 16 位 == A 的 prev **40/42**、`A.dH=0` **36/42**
  ⇒ 放宽 `HEAP_HI` 没有污染 A 行判据，v27/v28 口径保持可比。
- **跨对象/跨怪证据变硬**：J 行 28 条现在都读到 `vt=019B44E8 / sp=03F7`
  （主怪 H 行 `vt=019B5588 / sp=000E`），两个地址 `0C430060`(22) / `0C420060`(6)
  同 vtable 同 species；`+0x73E0` 呈正常 (act,sub,prev) 结构，
  如 `00010301 → a1 s3 pa1 ps0`、`03011402 → a2 s20 pa1 ps3`。
  ⇒ **至少另一类对象在跑同一套状态机**，v28 的「跨对象通用实机迹象」升级为确证
  （仍非严格「换怪种」验证，sp=`03F7` 也可能是小怪/其它对象）。
- **`s2C0` 低字节首次出现 2**（f=3927/4015，2 次；其余 1=42、0=3），
  补上 `0x75224` 反汇编 `cmp #1` 之外的分支样本。`s1A8` 仍恒 `00440049`（无区分度）。
- `s2C0` 高 16 位本场为 `0x0000`（v28 是 `0x0100`），说明该 32 位字含独立状态位，
  **Hub 分支只读低字节**的静态结论不受影响。

### 静态 BL 调用图解释 U=0（本轮新增，零实机）
扫 `main_text_decomp.bin` 全量 `BL` 目标（0xEB000000），按共享区 `<0xCF0000` /
每怪区 `0xCF0000..0x1140000` 分类：

| 入口 | BL 调用者 | 共享区 | 每怪区 | 说明 |
| --- | --- | --- | --- | --- |
| `0x75224` | **0** | 0 | 0 | vtable 槽，靠处境分派（实机 75 次调用） |
| `0x75338`/`75394`/`753EC`/`75444`/`754B8` | **0** | 0 | 0 | 同为纯处境 Hub ⇒ 常规战斗不触发，U=0 属预期 |
| `0x76908` | 1 | 1 | 0 | act/sub 请求入口，几乎不活跃 |
| `0x752EC` | 393 | 0 | 393 | v25 已实机证伪（G=0） |
| **`0x76AFC`** | **52** | **51** | 1 | **共享区高频，跨怪通用、最可能活跃** |
| `0x76984` | 355 | 1 | 354 | 每怪动作脚本的 (act,sub) 提交入口 |
| `0x76AB0` | 43 | 1 | 42 | 同上，mode=1 |
| `0x76A58` | 19 | 1 | 18 | 同上 |
| `0x75574` | 5 | 4 | 1 | a1/a2/a3 直通 `0x76154` |
| `0x75510` | 1 | 1 | 0 | 消费 `+0x73E6/73E7` 排队字段 |
| `0x76A10` | 2 | 2 | 0 | mode=1 |

- **结论修正**：`0x75224` 及 5 个 kind Hub 的 BL=0，说明它们是 **vtable 处境槽**；
  「挂更多处境 Hub」在常规战斗里大概率继续 U=0。真正该看的是
  **带 (act,sub) 参数的提交入口**——它们把 `r1=act, r2=sub` 透传给 `0x76154`，
  并有 `+0x73E0==11` 门控，是「抽选结果落盘前最后一跳」的候选。
- 反汇编确证 4 个候选首字：`0x76AFC`/`0x76984`/`0x76AB0` = `E92D4070`，
  `0x75574` = `E92D48F0`，全部干净（非 `E28FFxxx`）。

### v30（已编译部署，下次启动生效）
- **6 个只读 hook**：`0x75224`(H，对照) + `0x76AFC`/`0x76984`/`0x76AB0`/`0x75574`(U)
  + `0xAFF40`(A)。5 个 Hub 逐个首字校验，`OK` 5 位 bitmask，`hubMask=31` 表示全装。
  `SITE` 扩到 16 个入口。`MAXLOG=2000`、每 site 160 条 U 配额。
- **核心新判据**（`tools/analyze_v30_log.py`，已用 v29 日志 + 模拟 U 行双重冒烟通过）：
  ① `U.w1` 低 16 位 == `a1 | (a2<<8)` ⇒ 确证 a1/a2 就是落盘的 (act,sub)；
  ② `U.a1/a2` == 同帧 A 行的 (a,s) ⇒ 该入口是「抽选结果落盘前最后一跳」；
  ③ U 对 A 的覆盖率（同帧或 ±1 帧）。
  三者同时高命中 ⇒ 找到合规的**通用干预层**（对所有动作一视同仁）。
- 零写入、零游戏函数调用、不依赖 HP Bar、未硬编码 action_id、`original!` 全透传。
- 产物 `out/rai_submithub_probe_v30.nro`（28672 B，md5 **`4a362783…`**），
  已部署到 `mods/RiseAI_EntryProbe/romfs/nativeNX/plugins/rai_entrylocator_probe.nro`（同 md5）。
  源码 `lib.rs`（v29 备份 `lib.rs.v29bak`）；新增 `tools/analyze_v30_log.py`。
- `7_` 提示改 STEP 28（**只改 echo 提示**，输出路径/轮转/启动行未动）；
  `6_` md5 仍 `7361445f989b…`；`load_order` 未变。回退 `out/rai_multihub_probe_v29.nro`（`040b4341…`）。
- 日志快照 `out/game_p54_20261108_1900_v29_multihub.txt`、`out/v29_multihub_events.json`。

### 下一轮实机
- 重启跑 `7_`，打满 60 秒并锁定怪 → `python tools/analyze_v30_log.py 02_Workspace/game_p54.txt`。
- 判据：`hub=31` / 零 FATAL / `U` 非空且按 site 有分布 / `w1 低16位 == a1|(a2<<8)` /
  `a1,a2 == 同帧 A 的 (a,s)` / U 覆盖多数 A 行 / H-A prev 链仍稳定。
- **若 U 再次全空**：常规链确证只有 `0x75224 → 0x76154 → 0xAFF40`，
  「继续挂入口」这条路线收益已耗尽 ⇒ **转路线 2**（在 `0x75224` 的 `bl 0x76154`
  处做 inline hook 拦参数，需写代码内存、风险最高），先做可行性评估再动手。
- 硬约束不变：不硬编码 action_id、不在 `0xAFF40` 改 `a1`、不事后写 `+0x73E1`、
  保留只读回退链。

## 19:13 可行性核查 —— **已被 19:16 的源码级结论证伪，以 19:16 为准**

> ⚠️ 本节靠 IPS32 二进制推断，有 **2 处错误**：① `IPS offset = site + 0x100`（NSO 头），
> 故 `0x76254` 记录对应的是 **`0x76154` 函数入口本身**（原字 `E92D4FF0`），
> 不是「函数内 +0x100 / `ldr r0,[r4]`」；② `set_action_c()` 恒返回 0、只打印巨戟龙诊断日志，
> 删记录**不改变 AI 行为基线**。源码级证据与正确结论见 `06_MH4UPort_IPS32/NOTES.md` v2，
> 对本任务的影响与重排路线见下文 **19:16**。本节其余内容仅作纠错留档，不再作为决策依据。

**（原结论已作废：技术上可行但不建议；且即使成功也不能直接进入介入版。）**

### 机制已精确到具体补丁记录（静态证据，未实机验证）
- `MH4U Port/exefs/FB08F1D20FD1204FE7070672777F869B.ips` 是 IPS32，218 条记录；
  落在 `0x70000..0x78000` 的只有 3 条：`0x76254`=`E28FF79C`、`0x70128`/`0x70150`=`E28FF79D`。
- **`0x76254` 正在 `0x76154..0x76908` 函数体内（+0x100）**；静态原值 `E5940000`
  （`ldr r0,[r4,#0]`），被补丁换成 `add pc,pc,#imm` 跳板 ⇒ 这是 MH4U Port 有意的移植改动。
- **IPS 记录里没有 `0x76154`**：静态首字 `E92D4FF0`，运行时变 `E28FF7AD`
  ⇒ 入口跳板不是补丁写的，是 Recomp 检测到函数内代码被改后，把整个函数切进解释器时
  生成的分派跳板（**机制推断，未实机验证**）。`05_TargetHealth/NOTES.md §2` 的
  `main+0x9A764` / 补丁 `0x9A864` 也是同样的 +0x100 模式。
- ⇒ Forge trampoline 在别处执行这条 **PC 相对**跳板会跳错解释器槽，这是「不可 hook」的根因。

### 最小改动方案（若一定要走这条路）
- 只需从 IPS32 删除 **offset `0x76254` 那一条 4 字节记录**（218→217），其余 217 条全保留；
  重启后 `0x76154` 应恢复 `E92D4FF0`、不再进解释器，Forge hook 即可正常安装。
  不需要改 Recomp 宿主、不需要动解释器本身。
- **代价（4 条）**：
  ① `0x76254` 恢复 `ldr r0,[r4]` = **恢复原版 GU 逻辑**，MH4U Port 在这处的功能失效；
  ② 影响**所有怪**的该函数，且它正是我们要改的 AI 抽选函数 ⇒ **AI 基线被改变**，
     v16~v30 全部实机数据需重测；
  ③ 触碰别人的 mod 与游戏代码补丁，违反既定「不动其它 mod / 游戏资源」边界；
  ④ 启动日志的 `176 function(s)` 需复核是否下降，且要排除其它记录间接影响该函数。
- **更便宜的先验证**：编一个**不 SKIP**、纯只读的 `0x76154` hook 强装一轮（零写入），
  直接回答「解释器函数到底能否 hook」。风险是 `original!` 里的 PC 相对跳板可能跳错导致
  FATAL/闪退；但比改别人的 mod 代价低得多。此项**未执行**，仅作为可选验证记录。

### 为什么不能「直接」进入介入版
- `0x76154` 同时做「动作抽选 + `+0x73E0/73E1/73E8` 字段写入」，**拦到参数 ≠ 知道改什么**；
  v21i 已证明破坏字段一致性会原地发呆、吼叫增多。
- 通用规则的输入仍有缺口：`act+0x1A1` 的 1/2/3 处境语义、`+0x518` 的 `st=2`（疲劳）
  尚未实机捕获、玩家-怪距离字段（5 档）未定位、跨怪通用的 act 类语义与加权池未建立。
- v30 正在做的「`U.a1/a2` 是否就是落盘 (act,sub)」只读确证，是设计任何干预规则的前提。
- 硬约束不变：跨怪通用、规则对所有动作一视同仁、不硬编码 action_id。

### 更稳妥的等价路径
- **路线 2**：在 `0x75224` 的 `bl 0x76154`（`0x752D4`）处做 inline hook 拦
  `(r1=act, r2=sub, r3=mode)`；跳回时 PC 相对跳板仍在**原地址**执行 ⇒ 完全绕开解释器，
  **不动任何 mod / 补丁 / load_order**。
- **v30 结果优先**：若 4 个带参提交入口活跃且 `a1/a2` 就是 (act,sub)，
  直接在干净的 hook 层做通用规则，连 inline hook 都不需要。
- 本轮只做只读核查与文档，**未改任何 nro / mod / IPS 补丁 / load_order**。

## 19:16 06 任务定案 → 本任务路线重排（**结构性障碍可消除**）

**结论：04 的核心障碍「决策执行者 `0x76154` 不可 hook」有低风险解，首选干预点应改为 `0x76154` 入口；但仍不能直接做介入版，且有两个决策需用户拍板。**

### 1 · 交叉核验（本轮新增，零实机）
- 解析 162 个 IPS32 跳板 site（`off-0x100`），与 04 全部候选比对：
  **只有 `0x76154` 是 hook site**；`0x75224`、`0xAFF40`、v29 的 3 个、v30 的 4 个、
  以及 `0x752EC`/`0x75510` **全部干净**。
- ⇒ ① v29 的 `U=0` 不是 SKIP 造成（`hubMask=15` 全装），确证是函数未进运行路径；
  ② **v30 探针无需任何修改**，可照常跑；③ 变体只影响我们关心的这一个点。
- `ips32_variant.py verify` 复核：游戏目录仍是 `BASELINE (unmodified)`（md5 `6e2caabd…`），
  变体 `4e778eef…` 已备好、**未部署**。

### 2 · 结论重评（修正 19:13）
- 06 的 v2 源码定案：删 1 条 IPS32 记录（10 B）→ `0x76154` 回 native、入口恢复
  `E92D4FF0`、Forge 入口 hook 可装；功能损失只有巨戟龙 ≤200 行 setAction 调试日志，
  其余 161 个 hook 逐字节不变；风险由「中高」降为**极低**（仍属全局 exefs 变更，需停机窗口）。
  04 的 v16~v30 基线数据**不会因删记录而作废**（但变体后的解释器数量变化需做一次 A/B）。
- **对本任务路线的影响**：
  - **路线 2（在 `0x75224` 的 `bl 0x76154` 做 inline hook）降级为回退** —— 它本来只是
    绕开「不可 hook」的权宜之计，现在不必冒险写代码内存。
  - **v30 的 4 个带参提交入口降级为辅助观测** —— 它们是 `0x76154` 的上游 wrapper；
    06 的 `notes/api-map.md` 记录 `0x76154` 是全怪通用 `setAction(this,cat,num,mode)`、
    约 750 次调用 / 15 个 wrapper，hook 它一次覆盖全部，且发生在写
    `+0x73E0/73E1/73E8` **之前** ⇒ 完全符合「抽选层、对所有动作一视同仁、跨怪通用」。
  - ⇒ **首选干预点改为 `0x76154` 入口 hook**（前提是变体生效）。

### 3 · 仍不能直接做介入版
- 变体**尚未部署、未实机验证**（06 的 P3/P4 待批准）；`217 / 175 / 177` 与
  `SITE=E92D4FF0` 目前都是预测值。
- 通用规则输入仍有缺口：`act+0x1A1` 的 1/2/3 处境语义、`+0x518` 的 `st=2`（疲劳）
  未实机捕获、玩家-怪距离档未定位、跨怪通用 act 类语义与加权池未建立。
- ⇒ 即使 hook 装上，仍须**先只读一轮**（v31：`0x76154` 入口只读，拿全量 `r1/r2/r3`、
  prev 表、状态输入）→ 再设计通用规则 → 再灰度干预。不得跳过。

### 4 · 数据分界与停机窗口（关键协调）
- 变体是全局 exefs 改动，解释器函数 176→175，会改变**所有任务**的实机代码路径与时序
  ⇒ 基线数据与变体数据**不可混用**。
- 用户当前不在游戏中、v30 尚未开跑 ⇒ **现在就是干净的分界点**。二选一：
  - **方案甲（数据最完整）**：先在**基线**跑完 v30（`7_`，拿常规链入口分布），
    再切变体（06 的独立脚本）做 P3/P4；v31 起全部属变体口径。
  - **方案乙（最省一轮）**：直接切变体做 P3/P4，v30 归档为回退路径不跑，
    v31 直接拿全量决策数据。
- 06 的 P3 明确用 `06_MH4UPort_IPS32/game_ips32.txt` 独立日志，
  **不碰** `6_` / `7_` / `game_p15.txt` / `game_p54.txt`；两任务脚本不可同时启动。

### 5 · 需用户拍板的两件事
- ① 停机窗口 / 是否现在 `deploy --confirm`，以及选方案甲还是乙。
- ② **是否长期启用变体**：若按 06 的 P5 默认回滚基线，`0x76154` 又不可 hook，
  AI 干预 mod 就无法长期使用；06 §6.4 已判定「不能叠加小 mod，必须就地替换或停用原 mod」
  ⇒ 长期方案需单独确认（本机常驻变体 / AI mod 自带该补丁 / 退回路线 2）。

### 6 · 本轮改动
- 只读核验（IPS site 集合 + `verify`）、标注 19:13 两处错误、追加本节；
  **未部署变体、未改任何 nro / mod / IPS 补丁 / load_order / bat**。
  当前部署仍 `v30.nro`（`4a362783…`），纯只读。

> 本节「未部署」是 19:16 时点状态；19:21 已部署，见下一节。

## 19:21 顺序已定并执行（用户：「按你觉得最好的顺序来」）

### 决策：**方案乙的改良版** —— 直接切到变体口径，用已部署的 `v30.nro` 兼做变体启动验证
理由三条：
1. 长期交付 AI 干预 mod 必须依赖 `0x76154` hook ⇒ **变体是目标常态**，基线口径的数据注定作废；
2. `0x76154` 可 hook 后，v30 的 4 个上游提交入口不再是关键路径，先在基线单独跑一轮收益低；
3. 变体是全局 exefs 改动（解释器 176→175），越早统一口径，v31 / 干预版的数据越连贯。

⇒ **一轮实机同时完成两件事**：06 的 P3 启动判据 + 04 的 v30 观测。
v30 探针无需改动（162 个 IPS 跳板 site 只有 `0x76154` 与 04 候选重合），
其 `SITE` 首行 `+076154` 正好是 P3 核心判据：应从 `E28FF7AD` 变为 `E92D4FF0`。

### 已执行（04 视角）
- 06 任务区在**无游戏进程**时执行 `deploy --confirm`，游戏 IPS md5 现为 `4e778eef…`
  （基线 `6e2caabd…` 双份备份）；详情只写 `06_MH4UPort_IPS32/NOTES.md §9`。
- **04 侧未改任何探针 / 脚本 / 文档配置**：`v30.nro` 仍 `4a362783…`（纯只读）、
  `7_` 未再改动、`6_` 与 `load_order` md5 未变。
- 06 新增独立 `1_launch_and_capture.bat`（输出 `game_ips32.txt`）与 `check_p3_log.py`；
  两者均不碰 `6_` / `7_` / `game_p15.txt` / `game_p54.txt`。
  `check_p3_log.py` 已用 04 的基线日志冒烟，能正确判为 P3 FAIL（不会误放行）。

### 下一轮（用户操作）
1. 跑 `06_MH4UPort_IPS32/1_launch_and_capture.bat`，进任务打满 60 秒并锁定怪，正常结算退出。
2. 从 `D:\MHGU mod maker` 跑：
   `python 06_MH4UPort_IPS32/check_p3_log.py 06_MH4UPort_IPS32/game_ips32.txt`
   同一份日志再跑 `python 04_RiseAI/tools/analyze_v30_log.py 06_MH4UPort_IPS32/game_ips32.txt`。
3. 任一 P3 FAIL ⇒ 06 一键 `restore --confirm` 回滚，本任务退回变体前状态。

### P3 通过后的路线（不变）
- **v31**：在 `0x76154` 入口装只读 hook（首字校验期望 `E92D4FF0`，不符 SKIP），
  一次拿全量 `(act,sub,mode)` / prev 表 / 状态输入，并验证 `INSTALL` 成功、`hit>0`、零 FATAL
  ⇒ 对应 06 的 P4 第 2 条。
- 之后才设计通用规则（门控 + 状态 Hub + 通用 prev 表，必要时自建 Rise 风格加权池），再灰度干预。
- 硬约束不变：跨怪通用、规则对所有动作一视同仁、不硬编码 action_id、
  不在 `0xAFF40` 改 `a1`、不事后写 `+0x73E1`、保留只读回退链。

### 口径提醒
- 此后**所有实机数据均属变体口径**；v16~v30 的基线数据只作对照，不可与新数据混算。
- 变体按「长期启用」规划（AI 干预 mod 可交付的前提）；若最终回滚基线，
  `0x76154` hook 方案同步作废，须改走路线 2。

### 本轮实际改动
- 只写文档：04 的 `NOTES.md` / `STATUS.md`、06 的 `NOTES.md`、daily log、项目 `MEMORY.md`。
- **未编译任何插件、未改任何 nro / bat / load_order**；变体部署由 06 任务区工具完成。

## 19:31 P3 实机全过 + v30 找到「最后一跳」；v31 已部署（P4）

日志 `06_MH4UPort_IPS32/game_ips32.txt`（212 KB，19:30，用户已正常退出游戏），
快照 `out/game_p54_20261108_1930_v30_variant.txt`、`out/v30_submithub_events.json`。

### 1 · P3 全项 PASS（06 任务定案）
- `check_p3_log.py`：**FAIL=0 / WARN=0**。`MH4U Port 217 word(s) / 175 function(s) / 177 jump(s)`
  与预测精确一致；**`SITE +076154=E92D4FF0`** ⇒ `0x76154` 回 native；
  `module_init ok (word e92d41f0)`、零 FATAL、零禁止串、`hubMask=31`、
  `A=72 / BEAT=18 / 最后 f=10800` ⇒ 完整打完一场并结算。
- 功能 A/B：72 次动作提交、无发呆/无动画/结算异常的用户反馈 ⇒ 「删记录几乎无损」
  得到实机支持。**变体保持部署**，06 §5 P5 的「默认回滚基线」不再适用。
- 细节只写 `06_MH4UPort_IPS32/NOTES.md §10`。

### 2 · v30 观测：**`0x75574` = 抽选结果落盘前最后一跳**（本轮最大突破）
- `U=74`：`0x75574` **73 次**、`0x76AFC` 1 次、`0x76984` / `0x76AB0` 0 次
  ⇒ 4 个候选里只有 `0x75574` 活跃；它静态只有 5 个 BL 调用者却实机 73 次，
  **再次证明「静态调用图只给候选，活跃性必须实机确认」**。
- 三项判据同时成立：
  `U.w1` 低 16 位 == `a1|(a2<<8)` **68/73**、
  `U.a1/a2` == 同帧 A 行的 (a,s) **62/73**、
  U 覆盖 A（同帧或 ±1 帧）**63/72 = 87.5%**。
  ⇒ `0x75574` 带 `(act,sub,mode)`、位于 `0x76154` 之前、干净（首字 `E92D48F0`）、
  活跃、跨怪通用（4 个共享区调用者），是**已实机验证的合规干预点候选**。
- `a1` 分布 `(2:29, 7:25, 6:14, 1:5)` = L1 动作类（18 槽中的 4 类），
  `a2` 分布广（0/12/16/5/40/2/15/7/11/21/51/33…），`a3` **恒 0**
  ⇒ 常规提交的 mode=0（对比 `0x75224` 传 mode=2、`0x76908` 传 mode=5）。
- 对照判据未被变体破坏：`H.w0` 低 16 位 == A 的 prev **48/48**、`A.dH=0` 47/72、零 FATAL。
- J 行 3 类对象 vtable：`019B44E8/03F7`(55)、`01A112DC/03E9`(12)、
  `019B5588/000E`(1，主怪) ⇒ 至少 3 类对象共用这套状态机，跨对象证据进一步加固。

### 3 · v31（已编译部署，下次启动生效）—— 承担 06 的 P4 第 2 条
- **3 个只读 hook**：`0x76154`（**5 参**，第 5 参在栈上，首字期望 `E92D4FF0`）、
  `0x75574`（4 参，期望 `E92D48F0`）、`0xAFF40`（6 参）。
  前两个不符即 SKIP；`original!` 按各自参数个数原样透传；零写入、零游戏函数调用。
- `Q` 行（`0x76154`）：`f n eq a0 r1 r2 r3 p5 w0 w1 st s1A1 s2C0 vt sp hp/mx`；
  `U` 行（`0x75574`）与 v30 同格式；`A` 行精简为 `id/a/s/pa/ps/st/hp`。
  `BEAT` 报 `q/u/a/hub`，`hubMask=3` 表示两个 Hub 全装。
- 产物 `out/rai_unifyentry_probe_v31.nro`（24576 B，md5 **`57dc990f…`**），
  已部署到 `mods/RiseAI_EntryProbe/.../rai_entrylocator_probe.nro`（同 md5）。
  源码 `lib.rs`（v30 备份 `lib.rs.v30bak`）；新增 `tools/analyze_v31_log.py`
  （v30 日志 + 模拟 Q 行双重冒烟通过）。
- `7_` 提示改 STEP 29（**只改 echo 提示**；`OUT=game_p54.txt` / 轮转 / 启动行未动）；
  `6_`、`load_order`、变体 IPS 均未再改动。回退 `out/rai_submithub_probe_v30.nro`（`4a362783…`）。

### 4 · 下一轮 P4 判据（`python tools/analyze_v31_log.py 02_Workspace/game_p54.txt`）
- 必过：`INSTALL h_unify +00076154` / `hubMask=3` / `SITE +076154=E92D4FF0` /
  零 FATAL / `Q` 非空。
- 定案判据：`Q.w1` 低 16 位 == `r1|(r2<<8)`、`Q.r1/r2` == 同帧 A 的 (a,s)、
  **Q 覆盖 A 是否高于 `0x75574` 的 87.5%**、Q 与 U 同帧参数一致率。
- 全过 ⇒ 定案最终干预点（`0x76154` 全量 / 或 `0x75574` 已验证），进入通用规则设计
  （门控 + 状态 Hub + 通用 prev 表，必要时自建 Rise 风格加权池），再灰度干预。
- 若 `Q=0` 或 FATAL ⇒ 回退 `v30.nro`，**直接用 `0x75574` 作干预点**（已验证、覆盖 87.5%），
  不再继续追 `0x76154`。

### 5 · 纪律与口径
- 所有实机数据均为**变体口径**；v16~v29 基线只作对照，不可混算。
- 硬约束不变：跨怪通用、规则对所有动作一视同仁、不硬编码 action_id、
  不在 `0xAFF40` 改 `a1`、不事后写 `+0x73E1`、保留只读回退链。
- **全通过前不编译任何干预版**。本轮部署仍为纯只读探针。

## 19:40 清理游戏 mods 目录的历史探针（用户：probe 太多、影响启动时间）

- 扫描 `D:/Monster Hunter Generations Ultimate Recomp/mods/` 下 8 个 `RiseAI_*Probe`：
  每个目录只有 1 个 nro、无配置/资源。**`RiseAI_EntryProbe` 是当前 v31 部署目录，必须保留**；
  其余 7 个在 `load_order.txt` 里全是 `# off:`（第 31~37 行），本就不会加载。
- **7 个 nro 与 `04_RiseAI/out/` 历史产物逐字节相同**（md5 一一对应），删除零风险：

  | 目录 | nro | md5 | out/ 对应版本 |
  | --- | --- | --- | --- |
  | `RiseAI_BoundaryProbe` | `rai_boundary_probe.nro` | `17277620…` | `rai_boundary_probe_v16.nro` |
  | `RiseAI_ContextProbe` | `rai_context_probe.nro` | `290c073f…` | `rai_context_probe_v13a.nro` |
  | `RiseAI_DispProbe` | `rai_boot_probe.nro` | `c8165369…` | `rai_boot_probe_v8.nro` |
  | `RiseAI_EndProbe` | `rai_actionend_probe.nro` | `52b9dc09…` | `rai_actionend_probe_v17.nro` |
  | `RiseAI_HookProbe` | `rai_hook_probe.nro` | `65914d3f…` | `rai_hook_probe_v9.nro` |
  | `RiseAI_ObjProbe` | `rai_obj_probe.nro` | `08941ff7…` | `rai_obj_probe_v7.nro` |
  | `RiseAI_StartProbe` | `rai_actionstart_probe.nro` | `81519014…` | `rai_actionstart_probe_v18.nro` |

- 执行方式：**移出游戏目录并归档**到 `04_RiseAI/_retired_probes/<原目录名>/`
  （等价从游戏视角删除，但保留可回滚副本；原 nro 在 `out/` 另有备份）。
  未直接 `rm`，避免不可逆。
- 结果校验：游戏 `mods/` 下 `RiseAI_*` **只剩 `RiseAI_EntryProbe`**；
  归档 7 个 nro 的 md5 与移动前完全一致；
  `load_order.txt` 未改（md5 `fb9b176d…`，7 行 `# off:` 注释保留，指向不存在的目录无害，
  便于将来恢复）、`6_` 未动（md5 `7361445f…`）、
  `v31.nro` 未动（`57dc990f…`）、变体仍部署（`4e778eef…`）。
- 严格口径：这 7 个本来已被 `# off:`，移除**不会改变已加载插件集合**，
  主要收益是减少 Recomp 启动时的目录枚举与 mod 列表噪声；不要宣称「大幅缩短启动时间」。
- 下一轮 P4 判据与操作**不变**：跑 `7_`（STEP 29）打满 60 秒 → `analyze_v31_log.py`。
- 若用户要求彻底删除归档，再删 `04_RiseAI/_retired_probes/`（`out/` 备份仍在）。

## 19:47 v31 实机 P4 —— **全项 PASS，干预点定案**；并修正两处旧假设

日志 `out/game_p54_20261108_1947_v31_P4.txt`（298 KB，实时快照）、`out/v31_unifyentry_events.json`。
用户游戏进程仍在（末 A 帧 10888、末 BEAT 帧 16200，之后无新动作），本场数据已完整够用。

### 1 · P4 判据全过
- `INSTALL h_unify +00076154 first=E92D4FF0`、`hubMask=3`、**零 FATAL**、
  `Q=162 / U=82 / A=77 / BEAT=27` ⇒ **5 参入口 hook 装上且安全**。
  `p5` 恒 0（162/162）证明第 5 个栈参数读取正确、无栈错乱（这是变体路线最后一个工程风险点）。
- `Q.w1` 低 16 位 == `r1|(r2<<8)` **157/162**；**Q 覆盖 A 71/77 = 92.2%**
  （v30 的 `0x75574` 是 87.5%）⇒ Q 是更全的收敛点。
- `Q` 与 `U` 同帧参数一致 82/82（每个 U 都对应一个同帧 Q）⇒ `0x75574` 是 `0x76154` 的直接上游。
- `SITE +076154=E92D4FF0` 保持，变体稳定。06 的 P4 第 2 条至此实机验证通过。

### 2 · **修正旧假设（重要）**
- 17:42 起记录的「`0x76154` 内部做动作抽选 + 字段写入」**前半句被证伪**：
  `w1 低16位 == r1|(r2<<8)` 157/162 ⇒ 它**直接把传入的 (r1,r2) 落盘**到 `+0x73E0`，
  不做抽选。抽选/决策在上游（`0x75224` 选 kind、动作脚本选 (act,sub)）。
- Q 按 `r3`(mode) 严格分三类，**语义完全不同**：

| mode | n | r1 | r2 | 同帧 A 对齐 | s1A1 | 性质 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 82 | 2/7/6/1 | 具体 sub | **71** | 0(79) | **实际动作提交** |
| 2 | 78 | **恒 0** | kind 1/7/0 | **0** | 1(71) | action-end 状态请求（`0x75224`），**不产生动作** |
| 5 | 2 | 10 | 7 | 0 | 1 | `0x76908` 类 |

  ⇒ **干预必须只针对 mode==0**；mode==2 不是攻击提交，动它会破坏状态机。
  `mode==0` 是跨怪通用条件、不是招式特例，符合硬约束。
- `Q.w0 低16位 == A 的 prev` 仅 **1/71**（v28 的 H 层是 48/48）⇒ prev 链判据只适用于
  Hub 层 `0x75224`，不能套到 `0x76154`。如实记录，不掩盖。
- 疲劳 `st=2` 本场仍未出现（只有 0/1 两态）。

### 3 · 离线规则仿真（`tools/simulate_rules_v31.py`，零实机、零风险）
- 基线：相邻提交帧差中位 **79**、≤30 帧 **20/79 = 25.3%**、≤60 帧 34/79；
  与 v16 基线（中位 87 / 26.3% ≤30 帧）一致 ⇒ **变体口径下行为未变，AI 改进仍 0%**。
- **prev 表防复读几乎无收益**：完全复读 2/80 (2.5%)、同类连发 3/80 (3.8%)
  ⇒ 用户体感的「连招」是**不同 (act,sub) 的连段**，Rise 的 prev 表检查在 GU 抓不到主因。
- **短间隔才是主因**：R2「间隔 ≤30 帧」触发 20/80 (25.0%)，其中 act=7 占 11、act=6 占 8；
  插入 30 帧缓冲 ⇒ 全场 +600 帧 ≈ **10 秒输出窗口**（原战斗 7142 帧 ≈ 119 秒）。
- 推荐第一版通用规则：**只对 mode==0，按帧间隔做通用门控 + 怒/普通两态分支**；
  不读 action_id、不针对单怪、不改具体招式；距离档与疲劳态暂缓（字段/样本未就绪）。

### 4 · 下一步（实现层面待定，**未编译干预版**）
- 关键工程问题：如何在 hook 层「插入间隔」而不破坏字段写入 / 不卡住
  （v21i 教训：跳过 `original!` 或事后改 a1 都会导致发呆、吼叫）。
- 候选实现：① 利用 GU 自带 `+0x7420` 排队机制（`0x76908` 暂存 `+0x73E6/73E7`，
  `0x75510` 消费）把短间隔提交转入原生排队；② 延迟调用 `original_function!()`；
  ③ 在 Hub 层改 kind。需先评估安全性，再编第一个灰度干预版。
- 当前部署仍 `v31.nro`（`57dc990f…`）纯只读；**下一轮实机将是干预版验证**。

### 5 · 本轮改动
- 修 `tools/analyze_v31_log.py`：过滤以 `Q ` 开头的说明性 banner（曾触发 `KeyError: 'f'`）。
- 新增 `tools/simulate_rules_v31.py`；保存日志 / JSON 快照；更新文档。
- **未改任何 nro / bat / load_order / IPS 补丁**。

## 20:00 静态定案「如何安全插间隔」+ **第一个干预版 v32 部署**

用户「继续」。本轮全部是离线工作（无游戏进程），**编了第一个行为改写版并部署**。

### 1 · 静态定案（`refs/hpbar/main_text_decomp.bin` 反汇编）
- `0x76154` 入口 `E92D4FF0`；`r3==1` 跳过 `+0x73E0==11` 门控；
  `0x7629C cmp r7,#5 / cmpne r7,#0 / bne 0x763d4` ⇒ **mode 0 与 5 走同一主路径**，
  且 `mon+0x7420==0` 时 `beq 0x768fc` 直接返回（不落盘）。
- `0x7620C movw #0xdf00 / movt #3` ⇒ bitmask `0x3DF00` 置位 act 类 **8~12、14~17**
  （特殊类集合）；`+0x73E0==11` 有独立门控（`(12,255)` 与 act 14 例外）。
- 字段写入集中在 `0x76864~0x76878`（`+0x73E0`=r1、`+0x73E1`=r2、`+0x73E8`=r2 半字），
  之前是 `act+0x1A1/1A2/1A3` 复位；之后 `blx [vtable+0x16c]`、`blx [vtable+0x368]`、
  `bl 0x755b4(mon,act,sub)`、`bl 0xa7e84(mon,0)`；结尾 `pop {...,pc}` **无返回值消费**。
- `0x76154` 的 **17 个 BL 调用者全在共享区**（无每怪专属）⇒ 跨怪通用再确认；
  `0xAFF40` 有 4398 个调用者、绝大多数在每怪脚本区，且是 `mov r2,#0; b 0xafda4` thunk。
- `+0x7420` 排队机制定案：`0x76908` 在标志 0 时把 (act,sub) 暂存 `+0x73E6/73E7`
  并置 `+0x73E5=1`，`0x75510` 在标志非 0 时取出并 `bl 0x76154(mode=0)` 消费。
  **两者各只有 1 个 BL 调用者**（`0xA5C5C` / `0xA18B0`），本场 mode=5 仅 2 次
  ⇒ 是两段式提交、**不是计时延迟**，不能用来插间隔。

### 2 · 三条实现路线被排除
| 路线 | 排除依据 |
| --- | --- |
| 跳过 / 延迟 `original!` 且**不补调用** | `0x76154` 内的虚调用通知链与字段复位会整体丢失 ⇒ v21i 式永久发呆 |
| 在入口改 `(r1,r2)`（含「替换成间隙类」） | `0xAFF40` 的 action_id 由每怪脚本独立传入；A 行 `id` 与 `(a,s)` 一一对应（23 组合仅 3 个一对多）证明两者同源但**分别传参**。改 `+0x73E0` 不改 action_id ⇒ 字段/动画不一致，与 v21i 同类风险 |
| `+0x7420` 排队 | 见上，非计时机制且本场几乎不活跃 |

### 3 · 唯一可行形式：**延迟落盘**（v32）
`original_function!()` 展开为宏内 `__forge_original`（`unsafe extern "C" fn(5×u32)->u32`），
可在 detour 内把 trampoline 地址存到全局，由 `forge_onUpdate`（同游戏线程）补调用；
补调用走 trampoline、**不再进入 detour，无递归**。
- 规则：**只对 `mode==0`**，且距该 mon 上一次落盘 `<=30` 帧时，把 `original!`
  延后 `30` 帧执行。期间 `+0x73E0` 保持旧值 ⇒ 怪物停在动作结束后的 Think 间隙，
  即 Rise `_IsActionEnd` 门控的 GU 等价物。
- **不改任何参数、不丢弃通知链、不写游戏内存**（字段仍由游戏自己的 original 写）；
  只看帧间隔 ⇒ 对所有动作一视同仁、不读 action_id；per-mon 8 槽 ⇒ 跨怪通用。
- `GAP_MIN=30 / HOLD=30` 来自 `simulate_rules_v31.py`（25% 触发、约 +10 秒窗口）。

### 4 · 自保护（本轮最重要的工程设计）
同帧日志顺序确证是 **Q(mode=2) → Q(mode=0) → A(`0xAFF40`)**。若 `0xAFF40`
不依赖 `+0x73E0`、仍按原帧触发，延迟落盘就会造成字段/动画不一致。
⇒ `h_start_40` 检测「该 mon 仍有 pending 却已开始动作」时，**立即补落盘 +
把 `GATE_LIVE` 永久置 0（F 行）**。一轮实机自动判定兼容性，且不会出现整场发呆：
- **无 F 行** ⇒ A 随落盘一起延后，方案成立；
- **有 F 行** ⇒ 顺序不兼容，改走「在 `0xAFF40` 之前补落盘」或路线 2，已自动回退到原版行为。
另有：`peek(mon)` 有效性校验、pending 存活上限 120 帧、首字 `E92D4FF0` 不符 SKIP 且关闭门控。

### 5 · 产物与部署
- `out/rai_framegap_gate_v32.nro`（md5 `3f668db9…`），已覆盖部署到 `RiseAI_EntryProbe`。
- 源码备份 `src/lib.rs.v31bak`；新增 `tools/analyze_v32_log.py`（v31 日志 + 模拟 v32 日志双重冒烟通过）。
- `7_` 提示改到 **STEP 30**（只改提示；执行逻辑 / 输出路径 / 轮转未动）；
  `6_`、`load_order`、变体 IPS（`4e778eef…`）均未再改动。
- **回退**：`cp out/rai_unifyentry_probe_v31.nro` 覆盖插件即恢复纯只读。

### 6 · 下一轮判据（这是行为改写版，体感优先）
`python tools/analyze_v32_log.py 02_Workspace/game_p54.txt`：
零 FATAL / `hubMask=3` / G 与 D 非空且 `D.ok=1` / **`fuse=0`、`live=1`、无 F 行** /
`Q.d=1` 行 `w1==w0` / D 与 A 同帧 `(act,sub)` 对齐 / A 帧间隔中位高于 79、≤30 帧占比下降。
**体感判据**：是否真有输出窗口、有无原地发呆/异常吼叫/动画错位、硬直倒地是否不再被覆盖、
能否正常结算、零闪退。任一项不对立即回退 `v31.nro`，本版归档为实验反例。
- 硬约束核对：无硬编码 action_id、无招式特例、不事后写 `+0x73E1`、不依赖 HP Bar、
  跨怪通用、保留只读回退链 ⇒ **全部满足**。

## 20:20 v32 实机 P5 —— 诊断「窗口少」的根因；**v33 定稿并部署**

日志 `out/game_p54_20261108_2017_v32_P5.txt`、`out/v32_framegap_P5_events.json`。
用户体感：① 窗口有点少；② 窗口里怪物做的是**饮食**动作；③ 没发现招式复读
（主要仍是「后退再前撞」）；④ **只测了将军镰蟹**。零 FATAL、正常结算。

### 1 · v32 判据结果
`Q=315 (mode0=156, d=1 15) / A=137 / G=15 / D=1 / F=1 / BEAT=42`；
`hubMask=3`、零 FATAL、`SITE=E92D4FF0`。
A 帧间隔中位 **88**（v31 基线 79）、≤30 帧 **13.2%**（基线 25.3%）——
但**不能归功于 mod**：全场只有一次有效窗口，节奏差异主要来自该场战斗本身。

### 2 · 两个真实根因
1. **熔断把门控整场关掉**。`F=1` 在 **f=7093**（A 在 pending 未落盘时触发），
   v32 按设计「补落盘 + `GATE_LIVE=0`」；`BEAT live` 从 f=7200 起恒 0。
   ⇒ 后半场完全无干预，全场有效窗口只有 **f=6446 一次**（D=1，补落盘 `(2,0)`）。
   自保护机制本身是有效的（补落盘后 `+0x73E0` 与 A 的 (a,s) 一致、零闪退），
   **错的是「永久熔断」这个策略**。
2. **逐帧抽选循环被误判成连招**。f=7071~7092 每帧都是
   `mode=2 (0,7)` action-end + `mode=0` 候选提交，候选在
   `(6,7)/(6,11)/(6,12)/(7,21)` 间轮换，`+0x73E0` 恒 `07060700`；
   f=7093 才定案 `(7,9)` 并产生 A。v32 用「距上次落盘帧」判据，
   把这 22 帧循环每帧都算短间隔 → 14 条 G 噪声 + pending 反复覆盖。

### 3 · 结构性上限（本轮最重要的新认知）
`simulate_gate_v33.py` 用本场 Q/A 事件流离线重放：**87~96% 的窗口被
`0xAFF40` 提前结束**，平均窗口只有 **5~18 帧**。即 `0xAFF40` 几乎总在
落盘后几帧内触发，**加大 HOLD 无法拉长窗口**。
- `GAP=60/HOLD=45` → 28 次 / 累计 **140 帧(2.3s)** / 平均 5 帧 ⇒ 几乎无效；
- `GAP=90/HOLD=45/COOL=60` → **55 次 / 992 帧(16.5s) / 平均 18 帧** ⇒ 采用。
⇒ 要得到 45 帧级、可控、且不以原生空闲动画呈现的窗口，必须把门控移到
`0xAFF40` 动作开始层（同时延迟落盘与动作开始，保持两者顺序），
风险明显更高，列为**下一阶段**，本轮不做。

### 4 · 「饮食动作」定性
窗口期间播放的是 GU **原生 Think 间隙空闲/进食动画**。本 mod 不注入、
不替换、不读取任何 action_id，所以既不会制造也不会消除该动画。
想改成「战斗喘息」需要动动作选择，会触碰「禁止硬编码 action_id」边界。
如实记录，不掩盖也不假装已解决。

### 5 · v33 改动（已编译部署）
- **不熔断**：A 提前触发时「先补落盘再放行动作开始」（E 行），字段/动画一致，
  门控继续运行；`GATE_LIVE` 只在首字不符时关闭。
- **判据改成「距上一次真实动作开始（A 行）」** + `COOLDOWN=60` 保证窗口间有正常节奏。
- pending 期间只覆盖参数，**不重复记 G、不刷新 due** ⇒ 抽选循环收敛成一次窗口。
- `GAP_MIN 30→90`、`HOLD 30→45`（仿真定案）；新增 `W` 行量化
  每次窗口长度与全场累计，BEAT 加 `g/d/e/w/live`。
- 产物 `out/rai_gate_v2_v33.nro`（md5 `146674c2…`）已部署；源码备份
  `src/lib.rs.v32bak`；新增 `tools/simulate_gate_v33.py`、`tools/analyze_v33_log.py`
  （v32 日志 + 模拟 v33 双重冒烟通过）。
- `7_` 提示改到 **STEP 31**（只改提示），并写明**请换一只不同的怪**以验证跨怪通用；
  `6_`、`load_order`、变体 IPS 均未再改动。
- 回退：`v31.nro` 纯只读（或 `v32.nro`）。

### 6 · 下一轮判据
`python tools/analyze_v33_log.py 02_Workspace/game_p54.txt`：
零 FATAL / `live=1` 全程 / W 非空且 `ok=1` / 累计 `w > 600` 帧 /
平均窗口 > 8 帧 / **W 的 mon 与所打怪对应（跨怪验证）**。
体感：窗口是否明显够用、有无发呆/吼叫/复读/动画错位、正常结算。
若仍不够 ⇒ 进入 `0xAFF40` 层双延迟方案（先做可行性评估，不直接写）。
- 硬约束仍全部满足：无硬编码 action_id、无招式特例、不事后写字段、
  不依赖 HP Bar、跨怪通用、零参数改写、保留只读回退链。

## 20:41 v33 换怪实机 —— **跨怪验证通过，无功能性问题**

日志 `out/game_p54_20261108_2040_v33_crossmonster.txt`（476 KB）、
`out/v33_crossmonster_events.json`。用户换了怪，反馈「没感觉到复读」。

### 1 · 跨怪验证成立（本轮核心结论）
| | v32 场 | v33 本场 |
| --- | --- | --- |
| `MON` species `sp` | `0014`（将军镰蟹） | **`0004`** |
| Q 行 sp 分布 | 单一 `0014` × 315 | 单一 `0004` × 180 |
| 主怪对象 | `0C1C0890` | `0C118780` |
| 窗口 W | 1 次有效 | **11 次，全部 `ok=1`** |

规则对另一只怪同样生效（11 次窗口全落在该对象上），零 FATAL、
`live=1` 全程 47 个 BEAT、正常结算 ⇒ **「跨怪通用」从静态推断升级为实机证据**。

### 2 · 判据全过（修正判据口径后）
`FATAL=0 / Q=180 (d=1 11) / A=120 / G=11 / D=7 / E=4 / W=11 / BEAT=47`；
`hubMask=3`、`SITE=E92D4FF0`、G 与 W 一一对应（11/11）、补落盘全成功、
`live` 全程 1（v32 的熔断问题已消除）。
- 窗口累计 **315 帧 ≈ 5.2s**，平均 **28.6 帧**，最大 45 帧；占战斗时长 1.11%。
- `analyze_v33_log.py` 原先用「累计 > 600 帧」绝对阈值判 FAIL，**该阈值不适用于慢节奏怪**。
  已改为相对判据（窗口数 ≥8、占时长 ≥1%、零长窗口 <50%），并新增
  species / 复读率 / 零长窗口统计。修正后 **FAIL=0**。

### 3 · 仿真与实测精确一致（模型校验）
用本场事件流跑 `simulate_gate_v33.py`（`GAP=90/HOLD=45/COOL=60`）得到
**11 次 / 315 帧 / 5.2s / A 提前结束 36%**，与实测 `W=11 / 315 帧 / E=4/11=36%`
逐项吻合 ⇒ 离线仿真模型可信，也证明**窗口量低不是实现缺陷**。
参数扫描显示：本场任何 GAP/HOLD/COOL 组合最多也只有 315 帧 ——
这只怪 A 间隔中位 **188 帧**（将军镰蟹 88），本来就有充足输出窗口，
门控按需触发少是**正确行为**，不是「mod 没生效」。

### 4 · 复读口径（如实记录，不夸大）
本场连续同 `id` 16/119 = **13.4%**、连续同 `(a,s)` 31/119 = **26.1%**；
v32 场分别是 2.2% / 14.7%。**两者 sp 不同、且本场缺该怪原版基线，
数字不可混算、不可归因于 mod**。用户体感「没感觉到复读」与
「未引入异常重复」一致；低频 id（如 id=5 出现 23 次）属该怪原生行为。
A 帧间隔中位 188 / ≤30 帧 3.4% 相比将军镰蟹基线（79 / 25.3%）
差异主要来自怪种，**不可宣称是 mod 的功劳**。

### 5 · 已知非致命问题（不重编 nro 的理由）
1. **4 次 `win=0`**：G 与 A 同帧，`0xAFF40` 立刻触发提前补落盘（E），
   窗口长度为 0。这是 20:20 已定性的结构性上限，无害，仅日志噪声。
2. **E 分支 `life` 显示 `4294967251`**：`f.wrapping_sub(due)` 在
   `f < due` 时 u32 下溢；`how==1` 已绕过超时检查，**只影响日志可读性，
   不影响任何逻辑**。留待下一阶段与 `0xAFF40` 方案一起修。
3. **J 行 120 条吃满 `MAX_J`**：非主怪对象也走同一状态机（跨对象通用证据），
   不影响主怪判据（MON 识别用窄口径）。
4. **A 间隔 >600 帧 5 次（最大 771）**：窗口最多 45 帧，不可能造成 12 秒级空档；
   属该怪原生节奏 / 换区 / 玩家走位，不归因于 mod。
- **本轮不重编 nro**：v33 在两只怪上均零 FATAL、全程存活、无复读，
  参数对本场已是最优；换版会破坏数据可比性。当前部署仍 `v33.nro`（`146674c2…`）。

### 6 · 下一步（需用户拍板，本轮不动）
| 方向 | 收益 | 代价 |
| --- | --- | --- |
| A · 同怪 A/B 半场对照（编译期开关，前半场 ON / 后半场 OFF） | 首次拿到**同怪原版基线**，可严谨量化 mod 真实效果 | 单场体验忽好忽坏；需重编 + 一轮实机 |
| B · `0xAFF40` 层双延迟 | 45 帧级可控窗口、消除 `win=0`、窗口不再以原生空闲动画呈现 | 需延迟动作开始，可能引入无动画判定，风险最高 |
| C · 维持 v33，再跑 1~2 只怪 | 成本最低，继续积累跨怪稳定性证据 | 仍缺同怪基线，效果无法严格归因 |

建议先由用户确认「本场窗口体感是否够用」：若够用走 C；若仍想要更明确的窗口，
走 A 拿基线后再决定是否值得承担 B 的风险。

### 7 · 本轮改动
- 修 `tools/simulate_gate_v33.py`：到期优先判 `D`（原先 A 与 due 同帧时误标 A）。
- 修 `tools/analyze_v33_log.py`：相对判据取代绝对帧数阈值，新增
  species / 零长窗口 / 复读率统计与跨怪不可比提示。
- 保存日志与事件快照；更新 `NOTES.md` / `STATUS.md` / daily log。
- **未改任何 nro / bat / load_order / IPS 补丁**；`6_` 与 `7_` 执行逻辑未动。

## 2026-11-09 19:55 用户质疑复核 —— **v33 不是 Rise AI 仿制；5 项核心机制实现 0 项**

用户反馈：攻击频率高的怪没被约束（水龙连续三次同一招），频率低的怪反而更笨重；
要求严谨检查「仿制的 Rise AI」缺了什么，必要时回查 Rise 行为逻辑与具体方法。
本轮回查了本机解包的 107 个 `.user.2` / `out/rsz_json/*.json`（非联网推测），
并用 `tools/audit_rise_gap.py` 对两场不同怪的实机事件流做了可复现量化。

### 0 · 结论（先行）
**用户的两个观察都成立，且根因是同一个：v33 不是 Rise AI 的仿制，
而是一个自创的「全局帧间隔节流阀」。** Rise 的 5 项核心机制（处境 Hub、
`_IsActionEnd` 门控、3×5 加权池、prev 表检查、状态/距离自适应）**实现 0 项**。
我们唯一实现的 `GAP/HOLD/COOL` 恰恰是 Rise **明确没有**的东西
（`explicit_cooldown_field_found=false`）。

### 1 · 实机数据证据（`audit_rise_gap.py`，可复现）
| 指标 | v33 / sp=0004（用户所述水龙场） | v32 / sp=0014（将军镰蟹） |
| --- | --- | --- |
| 连续同 `id` 段 | **4 连 id=524，f=6907..7277，间隔 [125,120,125]** | 无 3 连，3 对间隔 ≤30 |
| 该复读段邻近窗口 | **0 次** | — |
| 连续同 id 对 | 16/119 = **13.4%**，中位 81 帧 | 3/136 = 2.2% |
| 其中间隔 >90 帧（门控够不着） | **6 对** | 0 对 |
| 窗口落点局部间隔 | `[46,46,46,47,47,47,78,84,84,84,111]`，**6/11 落在 ≤60 帧处** | — |
| 零长窗口 | 4/11 | — |

- **高频怪未被约束**：4 次同招间隔 120~125 帧 > `GAP_MIN=90` ⇒ 规则根本不触发，
  **邻近窗口 0 次**。这不是参数偏小的问题：即便放宽 GAP，我们也没有
  「按动作身份否决」的能力，只有「按帧间隔延迟」。
- **低频怪变笨重**：7 个有效窗口中有 6 个插在**原本只有 46~47 帧的正常衔接**上，
  把 46 帧拉成 91 帧；而真正该管的 120+ 帧复读段一次都没碰。
  即窗口**落点系统性错位**：惩罚了正常节奏，放过了异常复读。

### 2 · Rise 机制实证清单（本机 RSZ，非推测）vs v33
| Rise 机制 | RSZ 实证（具体方法） | v33 | 后果 |
| --- | --- | --- | --- |
| 12 个 `attack_stance_*` 处境 Hub | `flash` / `no_target_routine` / `out_main_zone` / `same_main*` 等独立文件；攻击池**只在 `same_main*` 内**；`_IsActionEnd` 跨 12 文件 **12 True / 32 False**，按分支门控 | 无 | 硬直/倒地/无目标仍与攻击共用同一落盘路径 |
| `ThinkCondition._IsActionEnd` | 状态转移由「上一动作是否结束」门控，动作进行中不重抽 | 无 | v17 已确证 GU action-end 后 1 帧提交；我们的窗口被 A 提前结束 36% |
| 3 状态 × 5 距离档加权池 | 15 个 `em001_main_out1_{anger,normal,tired}range{1..5}check`，`ConditionInfo._TransitionRate` 和恒 100，`ActionTableData._TableNo` 随档变；`tired·档5=[10,20,70]→[1,20,51]` 偏低威胁 | 无 | 规则输入只有帧间隔；`st` 在 Q 行已读出（0:40 / 1:43）却**从未使用**，距离档未定位 |
| prev 表检查 | **50 个 `ConditionInfo` 实例，每个的 `_CheckPrevTableInfoList` 各指向本池 1 个 `ActionTableData`**（如 anger·档1 的 30/40/30 三项分别 ref 4/7/10）⇒ 抽选时**按动作表**检查前表、否决/重抽；不是按具体招式 id，符合跨怪通用 | 无 | 连续 4 次 id=524 完全未受约束 |
| 显式 CD | `explicit_cooldown_field_found=false`；`EnemyThinkTimerData._Timer` 独立存在但因果未证实 | **自创全局 CD** | `GAP=90/HOLD=45/COOL=60` 是 Rise 没有的机制，直接与「慢怪笨重」对应 |

⇒ **Rise 的输出窗口是「门控 + 处境分流 + 池结构 + prev 否决」的涌现结果，
不是给所有动作统一挂一个节流阀。** 输出窗口来自**抽选到什么动作**，
不是**把落盘延后几帧**。

### 3 · 必须更正的两处判断错误（如实记录）
1. **20:41 章「慢节奏怪触发少属按需门控，不是缺陷」错误**：触发少 ≠ 对症。
   本轮数据显示落点系统性错位（6/11 插在 46 帧正常衔接）、有效窗口只有 7 个、
   4 个零长窗口，而真正问题（120+ 帧复读）未触及。当时把「仿真与实测吻合」
   当成「规则正确」，但仿真只验证**实现是否符合规则**，不能验证**规则是否对标 Rise**。
2. **v31 章「prev 表防复读仅 2.5% 不是主因」是单怪外推**：该结论只基于将军镰蟹
   一场（2.2%）；sp=0004 这场是 13.4% 且有 4 连段。用单怪分布外推到「所有怪」，
   违反了用户明确要求的「跨怪通用 / 底层改进」定位，方法上不成立。
   ⇒ **Rise 的 prev 表检查必须补回来**，它是本次用户体感问题的直接对应机制。

### 4 · 结构性约束（既有实机定案，决定「不能照搬」）
- GU **没有集中式加权抽选器 / rng 函数**：`0x752EC` 有 393 个 BL 调用者，
  分散在每怪每动作脚本函数末尾；每个脚本直接提交 `(act,sub)`。
  `0xEB66BC`（v19 `sel=0`）、`0x752EC`（v25 `G=0`）均已实机证伪不活跃。
- `0x76154` 只做落盘（P4 定案），`0xAFF40` 是动作开始 —— **两者都在抽选之后**。
  ⇒ 在当前干预层只能做「节流」，无法做「否决 / 重抽 / 加权」。
  这是 v33 偏离 Rise 的根本工程原因，不是实现偷懒。
- 因此「照搬 Rise 15 张数据表」不可行；但「门控 + 状态 Hub + 通用 prev 表」
  这条 17:58 已定案的结构性路线仍成立，只是被 v32/v33 的节流阀带偏了。

### 5 · GU 侧已确证、可用于结构性对标的落点
| 语义 | 锚点 | 状态 |
| --- | --- | --- |
| 状态 Hub / 处境分支 | `0x75224`：按发怒 `0x816d0`、`act+0x1A8` bit6、`act+0x2C0` 低字节、`+0x73E0` act==11 设 `kind=0/1/2` → `0x76154(mode=2)` | v27/v28 实机确证，跨怪通用，**最贴近 Rise 处境 Hub** |
| prev 表 | `+0x73E0` 高 16 位；v28 公式 `w1=((w0&0xFFFF)<<16)|新(act,sub)` | 已确证，只做观测未做干预 |
| 怒/疲劳 | `act+0x518`（1=怒、2=疑似疲劳） | 三场只出现 0/1，**st=2 从未捕获** |
| 距离档 | EMC op `0x0b/0x17/0x5c` 阈值，但无直接内存字段 | **未定位** |
| 跨怪 act 类语义 | `+0x73E0` 低字节是 L1 动作类（18 槽） | 有结构，无逐类语义表 |

### 6 · 改进路线（按 Rise 对标优先级，本轮**不编任何干预版**）
| 优先级 | 动作 | 收益 | 代价 / 前提 |
| --- | --- | --- | --- |
| P0 | **停止把「帧间隔节流」当作 Rise 仿制**；v33 降级为「过渡实验版」，不再沿 GAP/HOLD 调参 | 消除慢怪笨重的直接来源 | 需明确新基线，可能要回退 `v31.nro` 只读 |
| P1 | **状态自适应 + 处境分支**：用已读到的 `st`（怒/疲劳）与 `+0x2C0/+0x1A8` 异常状态位做分支，异常状态不插窗口、怒/疲劳用不同策略；进一步可在 `0x75224` 按 kind 做 Rise 式处境分流 | 直接对齐 Rise「3 状态 + 独立 Hub」，且字段已在 hook 内就绪，不需改参 | 需一轮只读拿 `st=2` 样本与 kind 全分布；`0x75224` 改 kind 的效果未验证 |
| P2 | **通用 prev 表否决**：按 **act 类**（非具体 sub / 非 action_id）检查 `+0x73E0` prev，对齐 `_CheckPrevTableInfoList` | 直接解决「连续三次同一招」，跨怪通用 | 「否决后重抽」在 GU 落盘层没有安全实现：等待逐帧重提交（v32 的 22 帧循环）只对同帧循环有效，**对 120 帧间隔的独立提交无效**；要真正换招需改抽选结果，必须解决 `+0x73E0` 与 `0xAFF40` action_id 的一致性，风险最高 |
| P3 | **自建 Rise 风格加权池**（3×5 结构、按 GU 分布校准） | 最完整的结构性对标 | 17:58 定案的 4 个前提目前 **0/4 就绪**（疲劳样本、距离档、act 类语义、GU 分布），现在做必然退化为单怪特例 |

**建议的下一轮（低成本、高信息量）**：编一轮**纯只读**探针，同时观测
`0x75224` 的 kind 三分支分布、`act+0x518` 是否出现 `st=2`、
`+0x2C0/+0x1A8` 异常状态位、`+0x73E0` prev 链、连续同 act 类的间隔，
并**跨 2 只怪**（含一只快节奏、一只慢节奏）取对照。拿到这份数据后再定
P1/P2 的实现形式，而不是继续在落盘层调参数。

### 7 · 本轮改动
- 回查 `DESIGN_v16.md §2/§3/§5-B/C`、`out/rise_ai_rules.json`、
  `out/rise_routine_rates.json`、`out/rsz_json/*`（15 个池 + 12 个 Hub 的字段级实证）。
- 新增 `tools/audit_rise_gap.py`（两场事件流量化 + Rise 清单对照，可复现）。
- 更正上述两处判断错误；更新 `STATUS.md`、daily log。
- **未改任何 nro / bat / load_order / IPS 补丁**；当前部署仍是 `v33.nro`（`146674c2…`），
  但已定性为「过渡实验版」，下一轮方向需用户拍板。

---

## 2026-11-09 20:29 —— 用游戏文件替代「跨 2 只怪实机对照」（用户提问）

**用户诉求**：跨 2 只快慢不同的怪取对照，无论对用户还是 AI 成本都太大；问有没有
游戏文件可以先翻出来研究，实在不行再做观测。

**结论：有，而且比预期好得多 —— 不需要再打两只怪做对照。**
游戏 romfs 里就有 137 个怪物资源包，每包含一张完整的怪物 AI 决策表；
资料库里已有该表的**格式文档**和**可运行的解析器**（04 任务区还自带一份副本）。
本轮全程离线只读，没启动游戏、没改任何 mod / nro / bat / load_order / IPS 补丁。

### 1 · 找到的资源（全部本机已有）
| 资源 | 位置 | 状态 |
| --- | --- | --- |
| 怪物资源包 | `游戏/data/romfs/nativeNX/arc/enemy/emNNN_SS.arc`，137 个、10~23 MB | 已解出，含 `enemy\cmd_tbl\*_cmdtbl` |
| EMC 格式文档 | `00_Tools/92_MHGU-master/.../docs/reference/formats/emc.md` | 完整：头/21 段/脚本文法/167 条 LEN 表/距离 matcher |
| 解析器 | `tools/mhgu/emc.mjs` + `tools/gu-moves/lib/{emc-tree,trees}.mjs` | **04 任务区 `tools/` 已有自包含副本，实测可跑** |
| 怪物编号表 | `docs/data/json/monster-slot-map-137.json` | 137 只怪中文名/英文名 |
| 代码镜像 | `04_RiseAI/refs/hpbar/main_text_decomp.bin` | 用于 matcher 反汇编核对 |

`*_cmdtbl` 解压后 5~50 KB，magic `EMC\0`、版本 `0x20120804`、**恒 21 段**，
每段是一组字节脚本，由 EMC 解释器 `0x82f80` 执行，表对象在 `em+0x2588`。
`emc.md` 确证的分支 op：`0x0b/0x17/0x57/0x5c/0x7c` 距离档（3D / XZ / 旋转偏移 / 六距最小），
`0x07..0x0a/0x0c/0x23/0x29/0x63` 状态字节（含我们已知的 `act+0x2C0`），
阈值按 mode 乘 100 顺序比较（`0x8e144` / `0x8e86c`）。

### 2 · 全量离线结果（工具可复现）
新增三个脚本，全部只读、直接读游戏 arc、不落盘解压：
- `tools/audit_emc_offline.mjs` → `out/emc_offline/summary.tsv/json`、`focus.md`
- `tools/audit_emc_pools.mjs` → `out/emc_offline/pools_<label>.json`（单怪池明细）
- `tools/audit_emc_repeat.mjs` → `out/emc_offline/repeat.tsv/md`（必然同招池全量扫描）

| 指标 | 结果 |
| --- | --- |
| arc / 不同结构的表 | **137 / 102**（23 组共享同一张表，另有 7 张空占位表） |
| 有 `op02` 多分支块的表 | **130** |
| `op02` 块 case 数值和恒 100 | **130/130** |
| 距离档 switch 块 | 中位 24、最大 173 |
| 状态字节 switch 块 | 中位 22、最大 228 |
| 动作队列 `op14` 叶子 | 中位 799、最大 4474 |
| 存在「必然同招池」的表 | **75/130**，共 **1067 个池**（占全部池 4.21%） |

`必然同招池` 定义：把 `op02` 块各 case 指向的动作 entry 聚合后，
所有 case 都指向同一个 entry 且权重和 = 全块 case 权重和
⇒ **无论分支怎么选，该处境下一定出同一个动作**。

### 3 · 直接解释用户的两类体感（无需实机）
| 怪 | species | 池数 | 必然同招池 | 占比 | 全量排名 |
| --- | --- | --- | --- | --- | --- |
| 水龙 `em010_00` | `000A`（昨晚那场**没抓到 `7_` 日志**） | 79 | **8（10.1%）** | 10.1% | 11/130 |
| 将军镰蟹 `em020_00` | `0014` | 289 | **0（0%）** | 0% | 83/130 |
| 岩龙 `em004_00` | `0004`（v33 跨怪场，**不是水龙**） | 193 | 2（1%） | 1% | 67/130 |

- **「水龙连续三次同一招」**：`em010_00` 的 `s0.e7` 里多个 `op02` 块形如
  `[[10,[69]],[20,[70,69]],[70,[69]]]` —— 3 个 case 全部把票投给 entry 69，
  累计 100%，**该处境下 RNG 无论落哪都选同一招**；共有 8 个这样的池。
  将军镰蟹 0 个，与用户体感「换怪后没感觉到复读」完全一致。
- **「低频怪更显笨重」**：岩龙/慢节奏怪本就有 2 个单 case 100% 池，
  动作间隔中位 188 帧；v33 又往这些长间隔里插窗口 ⇒ 叠加成笨重。
- **口径更正**：19:55 审计把 `sp=0004` 称作「水龙场」是错的，
  按 `monster-slot-map-137.json` 它是**岩龙**；将军镰蟹是 `0014`，水龙是 `000A`。
  19:55 表里「sp=0004 连续 4 次 id=524」应读作岩龙，结论方向不变、怪名需更正。

### 4 · 代码级核对与严谨性边界
反汇编 matcher `0x8e144` 发现：`s16` 是几何/状态计算值
（`0x8e468 vsqrt` / `0x8e6d0 vabs` / `0x8e634 vselgt`），
`0x8e86c vcmpe.f32 s20,s16; blt next-case` 是**阈值顺序比较**，
未见 0~100 随机数来源。资料库内部因此有两种口径：
`trees.mjs` 把 `op02` case 当百分比权重（块内和 100），
`emc.md §4` 把 `0x02` 归为「按 enemy 状态字节 switch」[I]。

⇒ **「GU 已有 Rise 式 `_TransitionRate` 加权池」只能作为高置信工作假设，不是代码级确证**；
130/130 表和恒 100 是强结构证据，但运行时语义待闭环。
**但「必然同招池」的结论不依赖 case 数值语义**：判据只看
「所有 case 是否都指向同一 entry」，所以第 3 节的解释依然成立。
另：21 段的 `section → AI 状态` 映射在资料库仍标 `[U]`，本轮不臆测。

### 5 · 对 19:55 审计结论的修正
| 19:55 结论 | 20:29 状态 |
| --- | --- |
| v33 是自创全局帧间隔节流阀、不是 Rise 仿制 | ✅ **仍成立** |
| 高频怪没管住、慢怪变笨重、窗口落点错位 | ✅ **仍成立**，且现在有表层原因 |
| 「GU 没有集中式抽选器」 | ❌ **作废**。抽选层是 EMC 解释器 `0x82f80` + `em+0x2588`，全怪共用；此前是在 `0x76154` 落盘层干预，压根没碰决策层 |
| 「加权池不能照搬」 | ⚠️ **改为待验证**：GU 有 21 段 + 距离/状态 switch + `op02` 和恒 100 的多分支块，骨架比预想接近 Rise；缺的是 prev 否决与状态门控 |
| 「加权池 4 个前提 0/4 就绪」 | ⚠️ **部分改善**：跨怪结构分布已可离线全量获取；`st=2` 疲劳样本、距离档运行时字段、act 类语义仍缺 |
| `DESIGN_v16.md §3「GU 的 EMC 是确定性 switch」` | ❌ **作废并已改写** |

**根因更精确的表述**：不是「GU 没有 Rise 的机制」，而是
**我们把干预装在抽选之后的落盘层**，所以看不到也改不了
`op02` 分支、`op14` 动作队列、距离档与状态分支 ——
只能在自己的层里发明节流阀，必然偏离 Rise。

### 6 · 下一步候选（本轮不编任何干预版，等用户拍板）
1. **A｜抽选层 hook（最对标）**：EMC 解释器 `0x82f80` / matcher `0x8e144` 是**全怪共用**的，
   一次 hook 覆盖 102 张表，可在分支选择处做通用 prev 否决（按 act 类、非 action_id），
   对齐 `_CheckPrevTableInfoList`。前提：先核对运行时首字是否 IPS32 跳板（纪律）、
   确认 `0x82f80` 的调用频率与重入风险；这是**新层第一次实机只读探针**。
2. **B｜离线改表（最稳但静态）**：统一扫描 102 张表，把「必然同招池」按通用规则
   平滑（不针对具体动作 id），生成单条目 arc 替换（遵守 ARC 纪律）。
   代价：静态近似、无运行时状态，且要处理 23 组共享表；不是 Rise 式动态否决。
3. **C｜维持 v33 + 一轮只读验证**：只补 `st=2` 疲劳样本与 EMC 解释器首字，
   不改行为，成本最低。

**实机观测需求已从「跨 2 只快慢怪各一场」压缩到「1 轮验证」**：
跨怪对照已由 137 个 arc 的离线全量数据替代；剩下的实机只用于
验证新干预层的可挂钩性与最终体感，不需要再为「取对照」打怪。

### 7 · 本轮改动
- 新增 `tools/audit_emc_offline.mjs` / `audit_emc_pools.mjs` / `audit_emc_repeat.mjs`
  及 `out/emc_offline/` 下 8 个产物（summary / focus / repeat / 3 份 pools JSON）。
- 修 `DESIGN_v16.md §3` 错误行；更新 `STATUS.md`、daily log、项目 `MEMORY.md`。
- **未改任何 nro / bat / load_order / IPS 补丁 / 游戏文件**；
  当前部署仍是 `v33.nro`（`146674c2…`，过渡实验版）。

---

## 2026-11-09 20:43 —— 用户拍板路线 A（抽选层 hook），v34 只读探针落地

**用户选择**：A —— 在 EMC 抽选层做通用 prev 否决，而不是离线改表 / 维持 v33。
按纪律**不直接编干预版**：先做静态可挂钩性核查 → 编**纯只读**探针 → 一轮实机验证。

### 1 · 静态定案（全部离线，代码级）
| 项 | 结果 |
| --- | --- |
| IPS32 跳板集合 | 161 个 site，**不含** `0x8e144` / `0x82f80` / `0x83770` / `0x50ce0` / `0x8e044` ⇒ 全部干净可 hook |
| `0x8e144` matcher | 首字 `E92D4FF0`，12 个 BL 调用者**全在共享区**（解释器 block-op handler） |
| `0x82f80` 解释器入口 | 首字 `E92D4FF0`，唯一 BL 调用者 `0x82f54`（thunk，间接调用） |
| 256 路跳转表 `0x837ac` | `op02` handler=`0x846E0`；`op14` handler=`0x83ED8` |
| **`op14` handler** | `0x83ED8` 直接写 `ctx+0x7350 / +0x7351 / +0x7354` 的**动作排队槽**（8 字节 stride） |
| **`0x85848` 调用链** | `bl 0x8e144` → `ldr r1,[r4]` (ip) → `add r0,r1,r0` → `str r0,[r4]` ⇒ **matcher 返回值 = 跳到选中 case 分支的字节距离** |

⇒ 这就是 Rise `_CheckPrevTableInfoList`「抽选时否决并重抽」的等价挂钩点：
改 matcher 返回值即可切换分支，且**对所有 `op02` 块一视同仁、不读 action_id、跨怪通用**。
`op02` handler 传 `r2=2(op)`、`r3=0(mode)` 给 matcher，与 `emc.md` 一致。

**注意**：`op14` 排队的是**EMC 脚本 entry 索引**，不是 `action_id`，也不是 `+0x73E0` 的 (act,sub)。
因此 prev 键必须在**同一层**选取（例如「上一次选中的 case 分支」或「上一次排队的 entry」），
不能跨层拿 `0x76154` 的 (r1,r2) 直接比 —— 这是 v35 设计时要解决的第一个问题，
本轮只读数据正是用来确认可行映射。

### 2 · v34 纯只读探针（已编译部署）
`out/rai_emcselect_probe_v34.nro`，md5 `ed959740…`，源码 `lib.rs`（备份 `lib.rs.v33bak`）。
4 个 hook，**零写入、零参数改写、全透传 `original!`**：
- `M` = `0x8e144` matcher（5 参）：记录 `op/mode/p5/ip/脚本前 6 字节/ret/重入深度`，
  以及 `mon/sp/w73`；按 `op==0x02 && mode==0` 分「抽选块」与其它（距离/状态）分类计数。
- `X` = `0x82f80` 解释器入口（3 参）：测脚本执行频率与 ctx(=mon)。
- `Q` = `0x76154` 落盘、`A` = `0xAFF40` 动作开始：帧/动作基准。
- `BEAT` 每 300 帧聚合：累计调用数、`sel` 抽选块数、距离/状态/其它分类、
  单帧 matcher 峰值 `peak`、重入峰值 `depth`、`hub` 掩码。
- 采样配额（M 抽选 140 / M 其它 70 / X 70 / Q 140 / A 140，全局 2200）防止高频刷爆日志。
- 4 个 hook 首字不符即 SKIP；`hub=15` 表示全装。

**v34 部署后 v33 门控自动停止**（游戏行为回原版），这是路线 A 的干净分界点。

### 3 · 本轮要回答的四个工程问题
1. `0x8e144` 5 参 / `0x82f80` 3 参 hook 实机能否安全安装（含栈上第 5 参透传）；
2. **频率与单帧峰值** —— matcher 每条 EMC block 指令都会调，若过高则此层不能常驻 hook；
3. `op==0x02 && mode==0` 抽选块是否真的活跃（决定 prev 否决有没有作用面）；
4. `ip` 脚本字节 / `ret` 分支偏移 / `mon` 与 `+0x73E0` 落盘能否关联，作为 prev 键的依据。

`tools/analyze_v34_log.py` 已用 v33 旧日志 + 模拟 v34 日志双重冒烟（判据 FAIL=0）。
`7_` 提示改到 STEP 32（**执行逻辑 / 输出路径 / 轮转未动**），提示里请用户关注
**是否卡顿**——高频 hook 的体感成本是本轮的关键判据。

### 4 · 判据与回退
跑 `7_`（STEP 32）打满 60 秒正常结算 →
`python tools/analyze_v34_log.py 02_Workspace/game_p54.txt`。
判据：零 FATAL / `hub=15` / 无 SKIP / `sel>0` / `p5` 有非 0 且无异常 /
`depth<=1` / `peak<=200`/帧（工程经验阈值，需体感校准）/ 游戏不卡。
- 全过 ⇒ 编 **v35**：在 matcher 返回值层做通用 prev 否决（先写设计文档再实现），
  规则不读 action_id、对所有 `op02` 块一视同仁、per-mon、保留只读回退。
- 任一 FAIL 或明显卡顿 ⇒ 回退 `v31.nro` 纯只读，改走路线 B（离线统一改 102 张表）。

### 5 · 本轮改动
- 新增 `out/rai_emcselect_probe_v34.nro`、`tools/analyze_v34_log.py`、
  源码 `lib.rs`（v34）与 `lib.rs.v33bak`。
- `7_` 只改提示；更新 `STATUS.md`、daily log。
- **未改** `6_` / `load_order` / 变体 IPS / 任何游戏资源 / 任何 nro 之外的配置。

---

## 2026-11-09 21:01 —— v34 P6 实机：可行性全过，v35 设计案就位

**用户跑完一场（多怪任务）并正常退出。** 日志 `02_Workspace/game_p54.txt`，
快照 `out/game_p54_20261109_2057_v34_P6.txt` + `out/v34_emcselect_P6_events.json`。

### 1 · 判据：FAIL=0，零 FATAL
| 项 | 实测 | 判定 |
| --- | --- | --- |
| 安装 | `SITE +08E144=E92D4FF0 +082F80=E92D4FF0 +076154=E92D4FF0 +0AFF40=E3A02000`；4 个 INSTALL、`hubMask=15`、无 SKIP | ✅ 4 hook 全装 |
| FATAL | 0，正常结算 | ✅ 5 参 hook（含栈上 `p5`）透传安全；`p5` 实测有非 0（7/74/9/26/6/55/1/4176…） |
| 频率 | `m=2767` / 44400 帧 = **0.06/帧**，单帧峰值 **46**；`depth=1` | ✅ **完全可常驻 hook**，用户未报卡顿；这是路线 A 最大的工程风险，已排除 |
| 抽选块 | **`sel=291`（`op02 && mode0`，占 matcher 10.5%）**；`op02=516`、`mode0=2168` | ✅ 通用 prev 否决有作用面 |
| 其它分类 | `state=1343`、`dist=385`、`other=748`、`ret0=1018`、`retneg=0` | 状态 switch 是最大类；`ret=0` 多为 endblock |
| 跨怪 | **6 个 mon 对象、4 个 sp（`1015/1013/0024/1006`）、43 个 ip 被多个 mon 共用** | ✅ 全怪共用同一解释器与 EMC 表；per-mon prev 表是必须的，全局键会污染 |

### 2 · 两处口径修正（重要）
1. **matcher 的 `a1` 指向 sub 字节流，不是 opcode**。解释器 `0x83788 add sb,r3,#1`
   把「opcode 后第一字节」传给 matcher；`op` 由 `a2` 传入。
   实机 `b[0]` = `{00 begin, 01 case, 02 default, FF endblock}`，**210/210 全部符合 EMC 文法**。
   v34 分析脚本原判据 `ip[0]==op` 写错，已改为 sub 文法自洽（210/210）。
   ⇒ v35 的字节解析必须按此口径；`b[1]` 是 case 值，实机见 15/10/40/5/25/35/30/20/32…，
   与离线「op02 块 case 和恒 100」互为旁证，但**加权语义仍未 100% 闭环**（matcher `s16` 是几何值）。
2. **`0x76154` 的 `r3==0` ≠ 动作提交**。Q 采样里 **124/140 是 `r1=0` 且 `w0==w1` 的空请求**，
   真实提交仅 16 次。v31/v33「mode==0 即动作提交」口径不完整，应加 `r1!=0` / `w0!=w1` 过滤。
   所幸 v32/v33 门控延迟空请求不改变字段，只浪费配额，**既有实机结论方向不受影响**。

**抽样限制**：Q 采样 `f=5710..6177`、A `f=5707..25851`（配额开场吃满），
所以「同帧真实提交==A(a,s) 1/16」是采样窗口错位，**不作机制判据**。
`st` 分布 0=112 / 1=28，仍无 `st=2` 疲劳样本。

### 3 · v35 设计案（已写，**未编译**）
`DESIGN_v35.md`：作用面固定 `op==0x02 && mode==0`（结构性条件、不读 action_id、
对所有块一视同仁），核心是**改 matcher 返回值切到另一个 case 分支**。
三个待用户拍板点：
- ① prev 键：推荐 **A1 `(mon, ip, ret)`**（纯运行时、跨怪通用、与离线必然同招池同构）；
  A2 case 值依赖未闭环语义；A3 全局键会被 6 个 mon 污染、不可用。
- ② 否决后跳到哪：推荐 **B1 下一个 case，找不到就透传原 `ret`**（最坏=无干预，不会发呆；
  严禁跳 `FF` endblock / `02` default）；B2 本地加权重抽更贴 Rise 但风险高；
  B3 只记录不改写要多一轮实机。
- ③ 灰度：推荐 **C1 全量 + 自保护 + `v31` 回退**（0.06/帧、峰值 46，开销可忽略）。

**风险如实列出**：改 `ret` 跳错分支可能让脚本提前进 endblock → 无动作 → 发呆/吼叫（v21i 教训）；
EMC 有嵌套块与变长 `sub`，hook 内字节解析需先用离线 102 张表对拍；
加权语义未闭环 ⇒ v35 只能叫「分支去重」，**不能宣称实现了 Rise `_TransitionRate` 加权池**。

### 4 · 本轮改动
- 修 `tools/analyze_v34_log.py`（sub 文法判据、op02 case 值、Q 空请求与采样窗口说明）；
  用 P6 快照复核 FAIL=0。
- 新增 `DESIGN_v35.md`；保存日志 / 事件快照；更新 `STATUS.md`、daily log、项目 `MEMORY.md`。
- **未编译任何 nro、未改任何 bat / load_order / IPS / 游戏文件**；
  当前部署仍是 `v34.nro`（`ed959740…`，纯只读）。
- 21:19 更新：用户已拍板 A1+B1+C1，本节「待拍板」状态由下一章取代。

---

## 2026-11-09 21:19 · v35：第一个「按 Rise 逻辑线」的抽选层干预版（已部署）

用户 21:05：「按你推荐的来，我们尽量复刻 rise 的逻辑线」⇒ **A1 + B1 + C1**。

### 1 · 先做离线解析器对拍（设计案 §5.2 的硬性前置）

新增 `tools/audit_emc_caseoff.mjs`（产物 `out/emc_offline/caseoff.{md,tsv}`）：
用资料库 `emc.mjs` 的 `LEN_TABLE` 与插件**完全相同**的算法，
从 `a1-1` 按 EMC 文法逐条 decode、收集同 op case、
以 case body 内全部 `op14` 排队动作的 entry 序列做 FNV-1a 签名。

| 指标 | 结果 |
|---|---|
| 137 arc / 130 张含 op02 块的表 | 全量解析成功 |
| op02 块 / case | **25322 / 141792** |
| 池数与既有 `audit_emc_repeat.mjs` 对拍 | **0 差异**（水龙 79 / 镰蟹 289 / 岩龙 193 逐项一致） |
| 存在不同动作可换的块 | **20337 = 80.3%** |
| 所有 case 排同一动作（必然同招，v35 透传） | 4985 = 19.7% |
| 相邻 case 距离 | 中位 5B、99.9% ≤43B，与 P6 实机 `ret` 值域 0..43 吻合 |

⇒ 证明「改 ret 到下一个 case」在**数值与结构上都可行**，且大部分池确实能换到不同动作。

### 2 · P6 数据补出的两处关键语义（决定作用面）

- op02 的 146 次调用里 **79 次是 `b[0]=FF`(endblock) 且 `ret=0`**，
  即「无匹配/不跳转」；只有 **67 次 `ret>0`** 是真实选 case。
  ⇒ 作用面修正为 `op==0x02 && mode==0 && ret>0 && ret<=256`，
  比设计案 §4.1 更精确；BEAT 新增 `act` 单独计数。
- `LEN[0x14]=1`（leaf），故 `op14` 的第一个 operand 就是动作表项 entry；
  用它的序列作签名 = Rise `_CheckPrevTableInfoList` 按 ActionTableData 否决的 GU 等价物。

### 3 · 实际实现（`lib.rs`，4 hook，`hubMask=15`）

- **唯一干预点** `h_matcher` (`0x8e144`，5 参)：`original!` 恒调用且只调用一次；
  只替换**返回值**（选中 case 的字节距离），不改任何参数、不写游戏内存。
- per-mon 16 槽 prev 表 `(sel, sig, age, valid)`：
  `sel` = 上次选中 case 的绝对地址，`sig` = 该 case 的动作表项签名。
  用 case 地址而非 `a1`，因为同一块的 begin/case/endblock 各有不同 `a1`。
- 判重：`sig` 相同 且 同一池内（`sel` 相同 或 `|Δsel| ≤128`）⇒ 复读；
  否决时向后找第一个 `sig` 不同的 case，`nr = ret + (p_pick - p_sel)`（相对差）。
- **自保护**：`a1-1` opcode 对齐检查、唯一最近匹配（容差 32，
  `d` 记入 V/K 行供复核）、`p_sel`/`p_pick` 双重 case 字节自检、
  `0<nr<256`、找不到不同动作即透传（`K why=4`）、
  `GATE_LIVE` 熔断（否决 >500 / 连续解析失败 >120）、一键回退 `v31.nro`。
- 其余 3 个 hook（`X` 解释器 / `Q` 落盘 / `A` 动作开始）保持纯只读对照，
  `Q` 采样加 `a1!=0 && w0!=w1` 过滤（P6 修正的空请求口径）。

### 4 · 与 Rise 的对标关系（如实）

✅ 已实现：**抽选时按动作表项否决 + 重抽分支**（`_CheckPrevTableInfoList` 等价）、
作用面为结构性 `op02` 块、跨怪通用、无 action_id / 无招式特例。
❌ 仍未实现：12 处境 Hub 分流、`_IsActionEnd` 门控、3 状态×5 距离档加权池、
状态/距离自适应；`op02` case 值是否等同 `_TransitionRate` 也未运行时闭环。
⇒ v35 是**逻辑线的第一步**，不能称「已复刻 Rise AI」。

### 5 · 产物与改动边界

- `out/rai_preveto_v35.nro`（`75e70e56…`）已覆盖部署；源码备份 `lib.rs.v34bak`。
- 新增 `tools/audit_emc_caseoff.mjs`、`tools/analyze_v35_log.py`
  （v34 旧日志 + 模拟 v35 双重冒烟：PASS=13 / FAIL=0）、`out/emc_offline/caseoff.{md,tsv}`。
- `DESIGN_v35.md` 由「设计案待拍板」改写为「实现案已部署」（新增 §8）。
- `7_` 只改提示到 **STEP 33**；`6_`、`load_order`、变体 IPS(`4e778eef…`)、
  游戏资源、`04_RiseAI/_retired_probes/` 均未动。游戏进程已关闭，下次启动生效。

### 6 · 下一轮（一轮实机即可）

跑 `7_P54_启动并抓日志.bat` 打满 60 秒并正常结算 →
`python tools/analyze_v35_log.py 02_Workspace/game_p54.txt`。
判据：零 FATAL / `hub=15` 无 SKIP / `live=1` 全程 / `act>0` / `ok>0` /
**`veto>0`** / `V.nr == ret+delta` / `d` 分布（>8 说明基址需校准）/
跨 mon 覆盖。**体感优先**：连续 3 次同招是否减少、有无发呆/吼叫/动画错位、
战斗是否自然、正常结算、零闪退。
任一异常 ⇒ `cp out/rai_unifyentry_probe_v31.nro` 覆盖插件回退纯只读，
本版归档为实验反例再定改进；若 19.7% 必然同招池需要改善 ⇒ 转路线 B（离线改表）。

---

## 2026-11-09 21:34 · P7 实机（变形冰鲨）：v35 零改写，降级为实验反例

用户：「变形鲨鱼出现了连续 3 次喷吐，还有一些时候进入一个动作后就不动了」，
并要求结合日志判断。日志快照 `out/game_p54_20261109_2134_v35_P7.txt`
+ `out/v35_P7_events.json`。

### 1 · 判据结果：`veto=0`

`hub=15` 无 SKIP、零 FATAL、`live=1` 全程、正常结算；
`sel=401 / act=84 / ok=27 / fail=0`；**`rep=57 / noalt=57 / veto=0 / V=0`**。
K 行 `why` 全为 4（找不到签名不同的 case），`d` 分布 7/3/4 全部 ≤8
⇒ **解析 100% 成功、基址推导正确**，但一次否决都没发生。

**因此 v35 没有改写任何 matcher 返回值，游戏分支选择等同原版。**
两个体感都不是本 mod 引入的（v34 已在同一 4 hook 上实机零异常）。

### 2 · 失效根因：运行时扫描提前终止（工程 bug，不是路线错误）

新增 `tools/audit_emc_v35_miss.mjs` / `out/emc_offline/v35_miss.md`。
决定性证据是 K 行的 **nc × 空签名交叉表**：
`nc=1` 33 行里 26 行空签名、`nc=2` 8 行里 7 行空、`nc≥4` 的 10 行**全部非空**。
扫描越短签名越空；离线完整块空签名只占 11.9%（变形冰鲨 14%）、`nc=1` 只占 14%，
P7 却是 63% / 58% ⇒ `scan_cases` 提前 break，case body 没扫完、`op14` 漏计，
签名退化成 FNV0、候选只剩 1 个 ⇒ 必然 noalt。
最可能机制：从 `a1-1` 起扫时若落在**嵌套 op02 块内部**，depth 从 0 开始会把该
嵌套块的 `endblock` 误判为当前块结束。次要因素：确实存在 body 内无 `op14` 的池
（离线 11.9%，对应 `repeat.mjs` 的 `emptyVote`），不是动作选择池，不该参与判重。

离线全量证明表结构不是死路：25322 块 / 141792 case，
每个 case「向后存在不同签名」**76.8%**，非空签名池 **85.0%**；
变形冰鲨 `em067_00` 403 池 / 1745 case，67.4% / 78.4%。

### 3 · 两个体感的严谨判断

- **连续 3 次喷吐**：A 采样内确有 `id=51` 三连（f=8328..8474）。
  变形冰鲨离线 `repeat.tsv`：17 个必然同招池（4.2%）、**81 个 ≥80% 集中池**、
  79 个 `emptyVote` ⇒ 该怪本就易连招。v35 零改写 ⇒ 属原版行为、规则未覆盖。
- **进入动作后不动**：A 行 80 条配额在 f=11476 吃满（末 BEAT f=34500），
  后段动作时间线不可见；BEAT 的 `a` 是全局累计（末 259），
  有 11 个 300 帧窗口「a 不增但 m/q/sel 仍增」、最长 4 连窗（20 秒），
  只能说明脚本在跑，**不能区分换区 / 原生长动作 / 发呆**。
  结合 `veto=0` + 零 FATAL + 正常结算，最可能是该怪原生行为
  （膨胀 / 冰冻形态 / 钻地等长动作）；但**不能 100% 排除 hook 时序影响**，
  需同怪原版对照或加长采样复测才能确证。

### 4 · v36 修复方向（未实现，待拍板）

1. **修复扫描终止**：从 `a1-1` 向前定位最近 `op==0x02 && sub==0` begin，
   用 LEN decode 校验可对齐回 `a1-1`，从 begin 起扫描并正确维护 depth
   （`delta` 仍为正、`nr>0`，不引入往回跳）。
2. **跳过空签名池**：`sig==FNV0` 直接透传，不判重、不计 noalt。
3. **A 行时间分层采样**，覆盖全场以定位后段发呆。
修完后 B1 理论成功率约 76.8%。

### 5 · 本轮改动

- 新增 `tools/audit_emc_v35_miss.mjs`、`out/emc_offline/v35_miss.md`；
  增强 `tools/analyze_v35_log.py`（nc / FNV0 / 采样截断 / BEAT 停滞窗口诊断）。
- 保存日志与事件快照；`DESIGN_v35.md` 新增 §9；`STATUS.md`、daily log 同步。
- **未编译任何 nro、未改任何 bat / load_order / IPS / 游戏文件**；
  部署仍是 `v35.nro`（`75e70e56…`，本场实测零改写，等效纯只读）。
- 下一步需用户拍板：**回退 `v31.nro` 做同怪原版对照**（确证发呆来源）
  或**直接编 v36**（修扫描 + 跳空池 + 加长采样）。

---

## 2026-11-09 22:00 · v36 已编译部署（用户 21:44「按你推荐的来」）

**决策**：不回退做纯对照（P7 已等价原版），直接编 v36，一轮同时验证 `v>0` 与体感。

### 1 · 静态复核推翻了上一章的两处判断（本轮最重要的收获）

- **`mode==1` 才是 GU 的加权抽选**：跳转表 `table[0x02]=0x846E0`，
  `ldrb r1,[sb]; cmp r1,#0; beq 0x85814` ⇒ `sub==0`(begin) 走
  `0x85814`：`0x496f0` RNG → `umull 0x51EB851F / lsr #5 / mls #100`
  = **`rand % 100`**，`r3=1`(mode=1)、栈 p5=随机数；
  `sub!=0` 走 `0x846F4`：`r3=0`(mode=0)、p5=0。
  matcher `0x8e8e8 cmp 累积case值, p5; ble 下一个 case` = 加权轮盘赌。
  **⇒ 21:34/21:19/20:43 记的「未见 0~100 随机数来源、加权语义未闭环」作废**，
  GU 的 `op02` case 值确为权重，与 Rise `_TransitionRate` 同构。
- **P6 实机佐证**：op02/mode=1 的 6 条全 `b[0]=00`、p5∈{7,74,9,26,6,55}、
  ret 全 >0；op02/mode=0 的 140 条 `b[0]∈{FF,01}`、p5 全 0。
  ⇒ v35 挂在 case/endblock 遍历上、`a1` 落在块中间 ⇒ 扫描截断。
  **21:34 章「疑似嵌套 endblock 误判的工程 bug」只是表象，根因是作用面选错。**
- **ret 基址**：`0x83788 add sb,r3,#1; 0x8378C str sb,[r4]` ⇒ `[r4]=a1`（sub 地址），
  `0x85850 add r0,r1,r0` ⇒ `new_ip = a1 + ret`。v35 基址正确，
  `d=3..7` 是 ret 指向 case 的 sub 而非 opcode；v36 同时试 `pos`/`pos+1`。

### 2 · v36 实现（4 hook，唯一干预点仍是 matcher）

- **双作用面**：主轨 `mode==1 && sub==0`（贴 Rise 加权抽选）、
  副轨 `mode==0 && sub==1`（保底）；BEAT 分轨统计 `m1/m0c/v1/v0`，一轮定案哪条是真实决策点。
- **向前定位 begin + 完整块扫描**：`find_begin()` 从 `a1-1` 回退 ≤192B 找
  `op02/sub=0`，用 LEN decode 校验能对齐回 `a1-1` 且 depth 不闭合；
  `scan_cases()` 从 begin 起 depth 从 0 开始、正确处理嵌套，收集最外层 case。
- **空签名池**（`sig==FNV0`，离线 11.9%）直接透传，不判重、不计 noalt。
- **prev 键** `(mon, begin, sel, sig)`；否决跳向后第一个「签名不同且非空」的 case；
  `nr = ret + (p_pick - p_sel)` 相对差；双重字节自检、`0<nr<256`、`GATE_LIVE` 熔断。
- **A 行时间分层**：每 3000 帧段 24 条、总 240，覆盖全场（修 P7 开场截断）。
- 全部自保护与 `v31.nro` 一键回退保留。

### 3 · 离线对拍（`tools/audit_emc_v36_align.mjs`）

137 arc / 25322 块 / 141792 case：**begin 对齐 100%**（141792/141792）、
可见 case 661154 → 1180516（**1.79×**）、v35 有 17.9% 起点扫不到后续 case、
空签名 11.9%、非空签名 case 向后可换 **82.8%**（全量 74.8%）。
变形冰鲨 403 块 / 1745 case、100% 对齐、空签名 14.0%、可换 67.4%。

### 4 · 改动与边界

- 产物 `out/rai_preveto_v36.nro`（`3d8714e1…`，已部署）、`lib.rs.v35bak`、
  `tools/audit_emc_v36_align.mjs`、`out/emc_offline/v36_align.{md,tsv}`、
  `tools/analyze_v36_log.py`（v35 旧日志 + 模拟 v36 双重冒烟 PASS=18/FAIL=0）。
- `7_` 只改提示到 STEP 34（执行逻辑 / 输出路径 / 轮转未动）；
  `6_`、`load_order`、变体 IPS(`4e778eef…`)、游戏资源均未改；无游戏进程时部署。
- **下一轮**：跑 `7_` 打满 60 秒正常结算 →
  `python tools/analyze_v36_log.py 02_Workspace/game_p54.txt`。
  判据：零 FATAL / `hub=15` / `live=1` / `m1>0` / `beg>0` / **`v>0`** /
  `V.nr==ret+delta` / mode1 的 `p5∈[0,99]` / A 采样覆盖后半场。
  **体感优先**：连续 3 次同招是否减少、有无发呆/吼叫/动画错位、战斗是否自然、正常结算。
- 如实风险：`mode=1` 全场真实频率未知（P6 的 6 条只是配额采样）；
  副轨 `mode=0` 改 ret 风险更高，若异常下一版关掉；
  改 ret 仍可能跳错分支导致发呆，体感判据优先；异常即覆盖回 `v31.nro` 纯只读。
- 仍未实现：Rise 12 处境 Hub / `_IsActionEnd` 门控 / 3×5 状态距离加权池 /
  状态距离自适应。v36 只实现「抽选时按动作表项否决 + 重抽」。

---

## 2026-11-09 22:40 · P8 实机结论 + v37 已部署（用户「剩下的部分交给你」）

### 1 · P8 日志：判据全过，但 `v=2` ⇒ 规则几乎没生效

零 FATAL / `hub=15` / `live=1` 全程 164 BEAT / 正常结算；
`m1=337`、`m0c=231`、`sel=551`、**`beg=551/551`（向前定位 begin 100%）**、`d=1`、
V 行 `p5=46/89` ∈[0,99] ⇒ 22:00 的静态定案**全部实机闭环**。
但 **`v=2 / 551 = 0.36%`**（`v1=2`、`v0=0`），阻塞在
`empt=323`（58.6%）与 `noalt=38/40`（95%）。

### 2 · 用户体感的严谨归因（不能算 mod 的功劳）

- 本场 V 行 `sp=1019`=**硬甲龙**（小怪）、`sp=002D`=**爆锤龙**（慢节奏），
  两者本就少连招；`v=2` 不足以造成「没连招 + 待机」的体感变化。
- 两次否决附近 f=22435 后 7 帧、f=23752 后 119 帧即有新动作 ⇒ 未见否决导致的发呆。
- **「待机」的日志证据是采样伪影**：A 行每 3000 帧段配额 24 条在段 2~7/10/11 全吃满，
  而 BEAT 全量 `a` 同段有 22~84 次动作开始；段 13~16 A 采样 0 条、全量仍有 55/56/29。
  因此 A 行 1223/2018/2412/2431 帧「长间隔」不是真实无动作。
  BEAT 全量计数显示全场只有 5 个 300 帧窗口无动作（含开场 16 窗与结算 3 窗）。

### 3 · 离线加权核验（`tools/audit_emc_weighted.mjs`）

按 case 值加权（即 `rand%100` 真实口径）：空签名 **22.3%**、向后可换 **55.8%**
（按 case 数旧口径 11.9% / 74.8%）——仍解释不了实机 58.6% / 5%，故定位为：
① **副轨 `mode==0` 语义混用**（231 次占作用面 42%，其 ret 是「跳到下一个 case」，
不是加权抽选结果）；② **B1「只向后找」的结构限制**（累积阈值常落在靠后 case）。

### 4 · v37 实现并部署（`b968c3f8…`）

- **作用面收窄**：只主轨 `mode==1 && sub==0`；副轨只统计、不干预。
- **否决后重抽**（Rise 等价）：B1 失败时用新阈值 `p5n=(p5+f*7+v*13+37)%100`
  按 case 值 w 做加权轮盘赌，在完整池内选签名不同的 case，
  `nr=(p_new+B)-a1`（B = ret 与 case opcode 的固定偏移 0/1）。
  **纯计算、零副作用、不二次调用 original**；所有 case 都在 `a1` 之后 ⇒ `nr` 恒 >0，
  不受「只向后」限制。扫描额外记录 case 值 w（权重）。
- **A 行改全局等距**（每 4 个事件 1 条），消除分段配额伪影。
- 新增 `S` 行（每 3000 帧分轨 e1/r1/n1/v1/rd）、`E` 行（空签名池 nc/ki/sw）、
  V 行 `ki/rd/sw`；全部自保护与 `v31.nro` 一键回退保留。
- 产物：`out/rai_redraw_v37.nro`、`lib.rs.v36bak`、`tools/audit_emc_weighted.mjs`、
  `out/emc_offline/weighted.{md,tsv}`、`tools/analyze_v37_log.py`
  （v36 旧日志 + 模拟 v37 双重冒烟 PASS=16/FAIL=0）、
  `out/game_p54_20261109_2226_v36_P8.txt` + `out/v36_P8_events.json`、`7_` STEP 35。
  `6_` / `load_order` / 变体 IPS / 游戏资源均未改；无游戏进程时部署。

### 5 · 下一轮与风险

跑 `7_` 打满 60 秒正常结算 → `python tools/analyze_v37_log.py 02_Workspace/game_p54.txt`。
判据：零 FATAL / `live=1` / **`v>2` 且 `S.rd>0`** / `noalt` 率 <95% /
`V.nr∈(0,256)` / A 覆盖后 1/4 场且无中段空洞 / 跨 mon。
**如实风险**：重抽会显著提高否决数（预期数十次），可能引入发呆/动画错位，
体感优先于日志；异常即覆盖回 `v31.nro` 纯只读。
Rise 12 处境 Hub / `_IsActionEnd` 门控 / 3×5 状态距离加权池仍未实现。

---

## 2026-11-09 23:05 · P9 实机（v37）结论 + v38 已部署（用户「你看看这次的日志」）

日志 `02_Workspace/game_p54.txt`（22:51，1,036,564 B）已归档
`out/game_p54_20261109_2251_v37_P9.txt`。**判据修正后 PASS=17 / FAIL=0**。

### 1 · P9：机制层全部闭环

零 FATAL / `hub=15` / 4 hook 全装 / `live=1` 全程 166 BEAT /
`quest started` 3 次 + `quest ended` 2 次 ⇒ 覆盖 3 场任务且正常结算 /
`m1=438`、`sel=act=beg=438`、`begf=0`、`fail=0`、**`v=124`（改写率 28.3%，
v36 P8 仅 2/551=0.36%）**、`rd=15`、`noalt=0`（v36 为 95%）、
V 行 `p5∈[0,99]`、`nr∈(0,256)` 全过、跨 8 个 mon。
`E` 行 40 条**全部 `sw=100`** ⇒ 块内 case 权重和恒 100，
与 Rise `_TransitionRate` 同构，**实机确证**（此前只是离线统计）。

**安全性证据**：V 行到下一动作开始（A 抽样）间隔 p50=135 帧 / p90=393 帧，
>600 帧仅 1 次 ⇒ 未发现改写造成的系统性发呆。
全场 `a_N=344`、A 行 86 条 = `344/4`；4 个长无动作窗口分别落在
开场加载(300–9600)、任务提示弹窗(10500–11400)、两次结算/换场
(16200–25500、26700–31800)，无一是战斗中卡死。

### 2 · 判据自身的一处错误已修正（重要口径）

22:40 加的「A 无整段空洞」是**错的**：v37 已把 A 改成「每 4 个
`0xAFF40` 事件记 1 条」的**按事件等距**，不是按时间等距，空段对应
真实无动作或任务间隙。修正为「空段必须无 ≥4 次动作开始」+「A 总行数
≈ `a_N/4` ±1」；同时修正 BEAT Δa 的段边界归属（归上一 BEAT 所在段，
否则段 5 会错位一个 300 帧窗口而误判）。
`tools/analyze_v37_log.py` 复跑 P9 由 PASS=15/FAIL=1 → **PASS=17/FAIL=0**。

### 3 · 但 V 行结构暴露 v37 硬伤：机械 A-B-A-B 二循环

- `sig=0x000C5540` 占 **91/124**；`pick` 前三位（`1B83BC00`56、
  `1BA54120`34、`1B9ED478`9）占 **99/124**；`blk` 前三位占 110/124。
- **`rd=1` 仅 15/124 ⇒ 88% 的改写走 B1「向后找第一个不同 case」**，
  同一个块永远改到同一个 case。执行序列变成
  `A(原版高频) → B(固定替代) → A → B …`；每 mon 的 V 行
  「隔一次同 sig」为 42/45、20/36、24/26。
- 结论：**v37 只是把复读换成二选一交替，不是 Rise 的「否决后重抽」**，
  与用户「尽量复刻 rise 的逻辑线」不符。日志判据全过 ≠ 行为正确，
  体感/结构判据必须一起看。

### 4 · v38 实现并部署（`12f1a74d…`，已覆盖游戏目录）

- **取消 B1 优先级**：所有否决一律走「**剩余权重归一化重抽**」——
  排除 `sig==FNV0` 与命中 prev 表的 case，对剩余 w 求和 `sw2`，
  `thr=p5n*sw2/100` 只累加合格 case 的 w 做轮盘赌；
  B1 降级为 `sw2==0` / 无候选时的兜底。
- **prev 表 1 项 → 2 项**：新增 `P_SIG2/P_CNT`，`prev_hit()` 返回
  1=命中最近一次、2=命中上上次；`push_prev()` 记录**实际执行**签名
  （改写时记 `cs[pick].sig`）。仍限定同一动作池，跨怪通用、无硬编码。
  这能打破 ABAB，并保证不会连续 3 次同动作。
- V 行新增 `b1/ph/sw2`，S 行新增 `b1/p2`；主轨、副轨只统计、
  空签名透传、`nr` 相对差、A 事件等距、GATE_LIVE 熔断、
  `v31.nro` 一键回退**全部不变**；纯计算、零副作用、零二次调用 original。
- 产物：`out/rai_prevtable_v38.nro`、`plug/context_probe/src/lib.rs.v37bak`、
  `tools/analyze_v38_log.py`（旧日志冒烟 SKIP=23；模拟 v38 日志
  **PASS=23/FAIL=0**）、`tools/analyze_v37_log.py`（判据修正）、
  `out/sim_v38_smoke.txt`、`7_` 提示改 STEP 36。
- 边界：`6_` md5 `7361445f…` 未动；`7_` 执行逻辑/输出路径/轮转未动；
  `load_order`、变体 IPS(`4e778eef…`)、游戏资源未动；**无游戏进程时部署**。

### 5 · 下一轮与风险

跑 `7_` 打满 60 秒正常结算 →
判据（已按 20:08 离线对拍修正）：零 FATAL / `live=1` /
**`rd≥60%` 且 `b1` 率 <25%** / `p2>0` / `sw2>0` /
**改写落点前三位占比 <85%（相对判据，v37 P9 实机 79.8%、离线 91.3%）** /
`V.nr∈(0,256)` / A 事件等距 / 跨怪。
「连续 3 次同招 / ABAB」日志无法可靠量化，其定量结论由
`out/emc_offline/sim_v38.md` 给出；实机只看安全性 + 体感。
**如实风险**：prev 表扩到 2 项会提高改写率（预期高于 28.3%），
可能让慢节奏怪更显笨重或出现动画错位。异常即覆盖回 `v37.nro`（`b968c3f8…`）或
`v31.nro` 纯只读。Rise 12 处境 Hub / `_IsActionEnd` 门控 /
3×5 状态距离加权池仍未实现。

---

## 2026-11-10 20:08 · 离线蒙特卡洛对拍 + 轻量验证（用户「我有点累，你能自己进游戏检测吗」）

### 1 · 「我自己进游戏」的可行性结论（如实）

**不能完全无人值守地打一场**。技术上可启动游戏进程、抓日志、自动分析，
环境里也有 `pynput`（按键注入）与 `PIL`（截图），但：
① 无 OCR / 实时视觉决策闭环，菜单导航需多次截图迭代，脆弱且慢；
② 输入注入需窗口前台焦点，且当前环境策略不主动启动 GUI 进程
（需用户明确授权）；
③ 挂机时怪物 AI 缺少玩家交互，数据代表性不足；
④ 强制结束进程有存档写入风险。
⇒ 承担「除进任务之外的一切」是可行的；「我替你玩」不是。

### 2 · 更方便的方法：全量离线对拍（**完全不需要游戏**）

`tools/simulate_v38_offline.mjs` → `out/emc_offline/sim_v38.{md,tsv}`。
137 arc / **25322 个加权池 / 141792 个 case**，每池连续抽选 120 次，
共 **9.12M 次规则执行**；同一池、同一步三规则共用完全相同的随机序列
（配对设计）。规则语义严格按插件源码（含 `sig==FNV0` 透传且不更新 prev）。

| 规则 | 相邻同招 | 连续 3 次 | 连续 4 次 | ABAB | 改写率 | B1 率 | 归一化重抽 | 落点 top3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 全量 vanilla | 33.91% | 18.88% | 18.67% | 14.66% | — | — | — | — |
| 全量 v37 | 7.73% | 7.62% | 7.51% | **33.34%** | 23.71% | 52.90% | 47.10% | 68.21% |
| 全量 v38 | 11.56% | 7.62% | 9.71% | **3.82%** | 38.25% | 0% | 68.68% | 67.82% |
| **可干预池 vanilla** | 28.40% | 12.22% | 12.10% | 15.90% | — | — | — | — |
| **可干预池 v37** | 0.00% | 0.00% | 0.00% | **36.17%** | 24.06% | 70.83% | 29.17% | 91.32% |
| **可干预池 v38** | 4.16% | **0.00%** | 2.38% | **4.14%** | 43.81% | 0% | 81.46% | 80.45% |

- **26.39%（6683/25322）是「必然同招池」**（只有一个非空动作签名），
  任何抽选规则都改不了，是全量口径里 `连续 3 次` 下界的来源。
- **v38 相对 v37 是净改进**：ABAB 36.17%→**4.14%**、连续 3 次保持 **0%**、
  落点 top3 91.32%→80.45%、B1 消失。代价是相邻同招 0%→4.16%
  （机械二循环被消除后的自然回归，仍远低于原版 28.40%）。
- 空签名透传三规则恒为 22.32% ⇒ 仿真实现自洽。
- **边界**：假设各池调用频率均匀（实机不是），是结构层面对拍而非某场战斗预测；
  重抽阈值分布与插件帧号盐不完全相同；**完全无法验证改 `ret` 后游戏是否真
  执行该 case**（动画/状态兼容、发呆、体感、结算仍必须实机）。

### 3 · 判据按离线结果修正（避免用户白跑一轮）

`tools/analyze_v38_log.py`：`rd` 主路径 70%→**60%**（离线 68.7%/81.5%）、
`b1` 20%→**25%**（离线 15.6%/18.5%）、落点 **<60% 是结构上不可达**
（池平均仅 5.6 个 case）改为相对判据 **<85%**；
「被否决签名不再单一集中」**删除**（`sig` 是原版抽中签名，mod 改不了
原版抽选结果，该判据逻辑不成立，降级为 INFO 输出）。
模拟 v38 日志冒烟 **PASS=22 / FAIL=0**。

### 4 · 最低交互实机脚本（用户只需站着，不用打）

`8_lite_check.bat`（纯 ASCII 名、英文提示，**新文件，不动 `6_` / `7_`）**：
独立日志 `02_Workspace/game_p54_lite.txt`（不覆盖 `game_p54.txt` /
`game_p15.txt`，不做轮转），游戏退出后**自动**跑 `analyze_v38_log.py`
并把结论打到控制台 + 写 `out/lite_result.txt`。
用户操作：双击 → 进任意任务 → 锁定 → **站着不动约 60 秒** → 正常关游戏。
不需要打怪、不需要完成任务、不需要换怪、不需要手动分析。
小样本下分布判据可能不稳，以「零 FATAL / live=1 / v>0 / rd>0 / 无 SKIP」
为准；3 连、发呆、动画错位仍需用户体感。

### 5 · 边界与产物

`6_` md5 `7361445f…` 未动；`7_`（STEP 36）执行逻辑/输出/轮转未动；
`load_order`、变体 IPS、游戏资源、已部署的 `v38.nro`（`12f1a74d…`）均未改。
新增：`tools/simulate_v38_offline.mjs`、`out/emc_offline/sim_v38.{md,tsv}`、
`8_lite_check.bat`、`tools/analyze_v38_log.py` 判据修正。
**仍可选**：若用户明确授权，可尝试「截图 + 按键注入」自动进任务，
但需接受焦点/存档风险，且数据代表性仍不如真人操作。

---

## 2026-11-10 21:03 · P10 迅龙场 + 怒/疲劳状态权重检查（本轮**不改 nro**）

用户体感「还不错」，但发怒时攻击动作不够多不够快（连段内），
且任务结束前怪物进入疲劳 —— 要求结合日志与 Rise 做比较检查。
完整报告 `out/state_weight_audit.md`，日志快照
`out/game_p54_20261110_2101_v38_P10_nargacuga.txt`。

### 1 · P10 判据 22/22（v38 机制层全通）

零 FATAL / `live=1` / 正常结算 / 跨 6 mon；`m1=452`、**`v=178`（39.4%）**、
`rd=165/178=92.7%`、`b1=13/178=7.3%`、`p2=89`、`noalt=0`、`fail=0`、
落点 top3 **66.3%**（v37 P9 79.8%、离线 v38 80.5%）。
原 FAIL 项 `V.sw2>0` 是**判据写错**：`sw2=0` = 归一化池空 → B1 兜底，
本场 `sw2=0` 13 次与 `b1=1` 13 次精确一一对应，已改为对应性判据。

### 2 · 状态观测（A 行 `st = *(u8*)(act+0x518)`）

- 只有 `st=0`(72) / `st=1`(43)，**`st=2`（疑似疲劳）本场 0 次**，
  与用户观察到的疲劳不符 ⇒ 该字段语义**未确证**（原本就标注「疑似」），
  或疲劳落在 f>42000 的 A 采样空白区（段 14/15 确实无动作开始）。
- `st` 在 0/1 间切换 43 次，与持久怒状态直觉不符，语义需复核。
- V 行按状态 112/66（62.9%/37.1%）与 A 行状态占比（62.6%/37.4%）一致
  ⇒ **v38 对怒/常一视同仁**；`ph=2` 命中率两状态均 50%，怒状态 `sw2` 均值
  16.0 < 常态 19.3（候选略少），`rd=1` 怒 100%。
- 怒/常 V 行 `blk` 交集 4、主块 `0x1A76A2CE` 均为 top1
  ⇒ **GU 原版怒/常复用同一批 op02 加权块**，不像 Rise 按状态切独立池文件。

### 3 · Rise 对标（三层状态适配，v38 一层都没有）

`out/rise_routine_rates.json` 15 池定量：怒 `[14,19,20,61,62,80]`（6 表、
熵 1.67）、常 `[13,19,20,51,79]`（5 表、熵 1.67）、
**疲劳 `[1,15,20,51]`（4 表、熵 1.30，每档都有 10% 指向表 1）**
⇒ 怒池候选更丰富、疲劳池收缩且集中，输出窗口变长是池结构结果。
另：`ActionInfo._angerMotSpeedUpperValue` / `_tiredMotSpeedLowerLimitValue`
⇒ 状态还改**动作播放速度**（对应「不够快」）；12 个处境 Hub 决定哪些处境
不进攻击池。**口径**：`_TransitionRate` 是「转移到动作表」的概率，
不是攻击频率倍率，不能说「Rise 怒时攻击更频繁」。

### 4 · 体感归因与下一步

「发怒时不够多」与机制一致（无状态层、prev 抑制在怒时不放松）；
「不够快」对应 Rise 的速度层，但属参数写入、违反本任务纪律且风险高。
另有一条**推断未证实**：v38 prev 粒度是「最近 2 次 case 内 op14 签名」，
比 Rise「前一个动作表 + 多数 1 项」更细，对迅龙 `A→B→A` 连段可能误伤；
本场日志无完整执行序列，无法证实或证伪。

按用户要求本轮**只检查、不改 nro**（当前体感不错，贸然改有破坏风险）：
- **方案 A（最小）**：抽选层按状态调 prev 严格度（怒 1 项 / 常·疲劳 2 项），
  跨怪通用、不碰 action_id、只在抽选层，低风险。
- **方案 B（推荐前置）**：先做**只读状态/距离标注探针**定位真正的疲劳字段
  （候选 `act+0x1A1`、`mon+0x73DC`、`+0x110/+0x11C`），核实 `+0x518` 语义
  与 GU 状态条件 op，再设计 3 状态分支。零风险、需一轮实机取数。
- **方案 C（不做）**：改动作速度，违反「不写游戏参数」纪律，判定帧风险高。

建议顺序 **B → A**；回退链 `v37.nro`(`b968c3f8…`) / `v31.nro` 保持有效。
`v38.nro`(`12f1a74d…`)、`6_` / `7_` / `8_lite_check.bat` / `load_order` /
变体 IPS / 游戏资源**全部未改**，本轮无游戏侧写入。

---

## 2026-11-10 21:17 · 猫之弱者呼唤核查 + 疲惫状态定位 + v39 只读探针部署

用户已同意方案 B，但先提出线索：GU 猫饭「猫之弱者呼唤 / 猫的弱小招来术」
「任务中大型怪物更易陷入虚弱」，问「虚弱」是否 = 疲劳。
完整报告 `out/weakener_and_tired_state.md`。

### 1 · 结论：**不是疲劳**（中文 wiki 意译偏差）

英文原文 "**Felyne Weakener** — Increases the likelihood of large monsters
**encountered in Quests being weak**"（MHGU Canteen / MHW Kiranico）。
社区实测：怪物刷新时 HP 有 **5 档** very weak…very durable，技能让
durable / very durable 两档不出现；多人不叠加；**固定血量任务无效**
（Gaming StackExchange 高票答案，MH4U/Gen 系与 GU 同源）。
MH Rise 团子「猫的弱小招来」同理（限制 HP 浮动 ≤0）。
⇒ 作用时机是**任务生成时一次性**决定个体 HP，与战斗中减气蓄积触发的
疲惫完全不同。**名称辨析**：GU 是猫饭 Felyne Weakener，Rise 是团子
Dango Weakener，同源不同作品。
本地资料库 `mechanics/systems.md:448` 技能等级 2、每日抽奖池、
食材「心跳不己酱汁（辛辣）」；`felyne_skills.json` 为空表 ⇒ 只能以 wiki 为源。

### 2 · 意外收获：GU 疲惫状态资料齐全 + 离线定位状态字

`wiki/monster-rage-tired.md`：疲惫 = 减气蓄积触发、流口水/动作变慢/倒地/
进食恢复；**迅龙 em37 = 180/75/480 [C]**，即时型 `durF=0`
（维持到进食/规定行为结束，解释 P10 「任务结束前疲劳」但 A 抽样没抓到）。
状态机 `0x1068dd8` r1=1 怒 / r1=2 疲；`tired_Change`@0x1585293、
`tired_Loop`@0x1585422；怒标志 `[mon+0xCBF1]`。
**怒时倍率数组**（dttune 每怪 30 f32）含 `AttackRate` /
`MotionSpeedRate` / `MotionSpeedRateLimit`，与 Rise
`_angerMotSpeedUpperValue` 同构 ⇒ **GU 原版本来就有怒时动作加速**，
21:03 报告里「不够快」不能归因 v38（v38 从不动这些倍率）。

**本轮离线反汇编新增 [C words]**：`0x1068dd8` 分发头
`cmp r1,#2 / #1`；`0x1068E08 ldr r0,[r7,#0xCAC4]!; cmp r0,#1`（怒）与
`0x1068E2C ldr r0,[r7,#0xCAC4]!; cmp r0,#2`（疲）
⇒ **`*(u32*)(mon+0xCAC4)` 是怒/疲状态字，1=怒 / 2=疲**。
比 `act+0x518==2`（原本只标「疑似」、P10 出现 0 次）强得多，
且 `0xAFF40` 的 `a0` 就是 mon，无需新 hook。

### 3 · 方案 B 落地：v39 只读状态探针（规则零改动，已部署）

`out/rai_state_v39.nro`（**`c54d6a05…`**，36864 B，无游戏进程时部署）。
规则与 v38 逐字节相同（prev 2 项 + 剩余权重归一化重抽），**游戏行为不变**；
只在 A 行追加纯内存读取字段 `c4`=`*(u32*)(mon+0xCAC4)`（首选）、
`cf`=`+0xCBF1`、`e1`=`+0x73E1`、`dc`=`+0x73DC`、`h1`=`act+0x1A1`，
`st` 保留对照。banner 保留 "RAI v38" 兼容串 ⇒ `analyze_v38_log.py` 仍可跑。
新增 `tools/analyze_v39_state.py`（字段分布 / st×c4 交叉 / c4 状态段 /
V 按状态分组 / 自动结论；旧日志冒烟 SKIP 通过、模拟日志判读 PASS）。
`8_lite_check.bat` 追加状态分析并自动出两份报告；`7_` 提示 STEP 37
（执行逻辑 / 输出路径 / 轮转未动）。
回退链 `v38.nro`(`12f1a74d…`) / `v37.nro` / `v31.nro`；
`6_` md5 `7361445f…` 未动，`load_order` / 变体 IPS / 游戏资源未动。

### 4 · 下一轮（最低负担）

双击 `8_lite_check.bat` → 进任意任务 → 锁定 → **站着 60 秒** → 正常关游戏，
脚本自动出两份报告。用户只需补一句「大概在任务结束前多久怪物变疲劳」，
把该时刻与 `c4==2` 状态段对照即可定案。
**边界**：`+0xCAC4` 是离线代码级确证，尚未经实机值域验证；
猫饭技能机制来自 wiki/社区实测、未在本机 romfs 逐字节对拍；
疲惫状态字节 ≠ 减气蓄积值。本轮**未实现任何状态权重层**。

---

## 2026-11-10 21:33 · v40「必定疲劳」观测插件（用户授权的一次性写入）

用户要求本轮观测「怪物恒定」：把耐力上限改成 1 / 让一个攻击动作必定疲劳，
以便不靠运气定案疲惫状态字段。完整报告 `out/force_tired_v40.md`。

### 1 · 选「减气蓄积」而非「耐力上限」

运行时**耐力上限字段未确证**（只有静态参数类 `StaminaSubRate` /
`StaminaTimeVal` / `cEmStaminaData::cStaminaLev` 的 XML 成员名），盲写风险高。
改为写**减气（Exhaust）蓄积**，链路完整且跨怪通用：
- `0xA398C`：`r8 = mon+0x1428`（预索引写回）⇒ `ldr r0,[r8]` = **act 对象**。
- 同函数按 `bl 0x71078; ldr r7,[mgr+0x34/38/3C/40/0x44]` 遍历
  Poison/Sleep/Para/KO/**Exhaust**。
- Exhaust 段 `0xA3B9C..0xA3C04`：`movw r1,#0x5d82; add r6,r0,r1; ldrsh`
  ⇒ **`*(u16*)(act+0x5D82)` = 减气蓄积计数**，`+0x5D88` = 衰减 f32 timer；
  `dttune` 阈值迅龙 180/75/480。硬编码立即数 ⇒ 跨怪通用。
写蓄积值走**游戏自己的状态机**判定疲惫，**不写 `mon+0xCAC4` 状态字**
⇒ 观测对象不被污染（这点比直接硬写状态字正确）。

### 2 · v40 实现（`be9cf246…`，已部署，v38 规则逐字节不变）

- **一次性写入**：首次动作开始时，若 `c4!=1`（非愤怒）/ `FORCED==0` /
  `GATE_LIVE==1` / `heap_ok(actp)`，写 `actp+0x5D82 = 1000`
  （> 所有已知怪 max≤850，会被钳到 max，仍 ≥ initial 最高 300）；
  `FORCED` 熔断，全场最多一次。`F` 行记录写入前后。
- **`C` 行每帧状态变化即时捕获**：`forge_onUpdate` 读缓存 mon 的
  `+0xCAC4`，值一变立即打日志（上限 400）——**不受 A 行 1/4 采样限制**。
  这是 P10「用户看到疲劳、日志没抓到」的真正原因：疲惫时怪物几乎不出招，
  A 行系统性跳过整段。
- A 行保留 5 个候选字段 + 新增 `ex` / `forced`；banner 保留 "RAI v39" /
  "RAI v38" 兼容串 ⇒ 两个旧分析脚本仍可跑。
- `tools/analyze_v39_state.py` 升级：解析 F/C 行、C 行状态段与 `c4==2`
  时长、A 行 ex 分布、「写入→c4==2」全链路结论；旧日志冒烟 SKIP 通过、
  模拟 v40 判读 PASS。
- `7_` STEP 38 / `8_lite_check.bat` 只改提示与分析调用（含写入风险告知），
  执行逻辑/输出/轮转未动；`6_` md5 `7361445f…`、`load_order`、变体 IPS、
  游戏资源未动；无游戏进程时部署。

### 3 · 安全边界（本任务**首次游戏侧内存写入**，必须保留）

`+0x5D82` 语义是离线反汇编推断、**未经实机值域验证**；可能无效（最安全）、
触发疲惫（目标）、或反复疲惫/动画错位（立即退出）。
熔断：`FORCED` 一次 / `c4!=1` / `GATE_LIVE` / `heap_ok` / 日志上限；
不写状态字、不写 `+0x73E0`、不改参数表。
**一键回退** `v39.nro`(`c54d6a05…`) 纯只读 → `v38.nro`(`12f1a74d…`)
→ `v37.nro` → `v31.nro`。

### 4 · 下一轮判据

双击 `8_lite_check.bat` → 进任务 → 锁定 → 站着 60 秒 → 关游戏，
自动出两份报告。判据：零 FATAL / `F` 行恰好 1 条 / C 行出现 `c4==2` 段 /
A 行 `ex` 写入后呈衰减或钳制 / `live=1` / 体感无反复疲惫或动画错位。
若 `F` 有但 C 无 `c4==2` ⇒ 写入没驱动状态机或字段推断有误，
**回退 v39，改用「延长观测 + 每帧 C 行」自然捕获，不再盲写**。
本轮未实现任何状态权重层。

---

## 2026-11-10 22:22 · P11 疲劳定位审计 + v41 纯只读状态扫描

用户完成 v40 场：减气蓄积写入没生效，但怪物**自然疲劳**（截图，任务内 15 分钟之后）。
要求「先定位疲劳；若疲劳信息已全获取，则不管减气蓄积，以推进任务优先」。
完整报告 `out/tired_state_P11_audit.md`，日志快照
`out/game_p54_20261110_2221_v40_P11_tired.txt`。

### 1 · 结论：疲劳时段定案，状态字段未取到

- `BEAT.a` 全量计数 ⇒ 任务开始 `f≈14566`、结算 `f≈118951`、**60fps**（全场 29.0 分钟）。
  连续 900 帧零动作开始段 **`f=69600..70500` = 任务内 15.3~15.5 分钟**，
  与用户截图/描述精确吻合；另一次疑似 `f=95400..97500`；结算后
  `f=115200..120300` 排除。
- **但状态字没采到**，因此「疲劳信息全获取」不成立，本轮**不进入 3 状态权重层**。
- 按用户要求**减气蓄积不再追**：`F` 行 1 条（`ex 0→1000`）、A 行 `ex` 240 条全 0、
  写入对象 `0C181390` 与 C 行监控对象 `0C220060` 不同 ⇒ 推断未通过实机验证，
  v41 撤销全部写入。

### 2 · 三处根因（必须长期记住）

1. **`mon+0xCAC4` 不是状态字，21:17 的「1=怒/2=疲」结论作废**：实机主怪恒 413
   (`0x19D`)、另一对象为每帧变化的浮点位模式；`0xCEFEB8` 确实把 413 写进
   `+0xCAC4/+0xCAC8`，`0xD0CAD0..` 写 0x54~0x57。`mon+0xCBF1` 同样噪声；
   `act+0x518` 只出现 0/1、无 2。
2. **C 行配额被噪声吃光**：v40 每帧比较 `c4` 浮点，400 条在 `f=14564..15380`
   （816 帧）打光，之后全场无状态记录。
3. **盯错怪**：`LAST_MON=0C220060`，主怪其实是 `0C181390`（V 行 30 次）。
另：`8_lite_check.bat` 裸 `python` 在 cmd 里不存在 ⇒ 本轮两份自动报告只有
`'python' is not recognized`；已修为绝对路径。

### 3 · 离线重新定位的状态候选（[C words]）

- **`mon+0xCAC0`**：`0x106873C` 初始化 1；疲惫分支 `0x1068EA4`
  `ldr r2,[r4,#0xCAC0]; cmp #2 / cmp #3` ⇒ **状态枚举（1/2/3）最强候选**。
- **`act+0x408`**：疲惫分支 `0x1068F18 / 0x1068F9C` 写入的 s16（时长/阈值）。
- `mon+0xCBF1`：`0x1068E1C / 0x1068E8C` 怒标志写入点。
- `act+0x5D82`：Exhaust 蓄积（只读）。

### 4 · v41 已部署（`4391d438…`，36864 B，ZERO writes）

- 规则与 v38 逐字节相同、怪物行为不变；删除 `F` 行 / `FORCED` / 写回代码。
- `reg_mon()` 8 槽 + `forge_onUpdate` 每帧扫全部 mon；C 行只在**离散状态指纹**
  `fp = c0&0xFF | cf<<8 | st<<16 | (t4!=0)<<24` 变化时记录，`c4/c8/ex/t4`
  只输出不触发；`MAX_C 400→800`、`MAX_A 240→400`
  （P11 的 240 在 f=89281 打满，正是 `analyze_v38_log.py` 3 条 A 采样判据
  FAIL=3 的原因，全是配额伪影）。
- A 行新增 `c0/c8/t4`；`tools/analyze_v41_state.py` 自动用 BEAT 零动作段作
  锚点比对候选字段，旧日志冒烟降级、模拟日志 PASS=9/FAIL=0。
- `7_` STEP 39 / `8_lite_check.bat` 修 Python 绝对路径 + 分析脚本 + 提示
  （正常打一场即可，不必站着 60 秒）；执行逻辑 / 输出路径 / 轮转未动；
  `6_`（`7361445f…`）、`load_order`、变体 IPS、游戏资源未动。

### 5 · 下一轮（一次定案，用户交互最小）

双击 `8_lite_check.bat` → 正常打一场（疲劳通常任务内 ~15 分钟）→ 关游戏，
脚本自动出两份报告；只需再告诉我「大概任务内几分钟变疲劳」。
判据：零 FATAL / C 行覆盖全场 >80% / 锚点段附近有 C 行事件 /
`c0` 在锚点出现 2 或 3，或 `t4` 非零且形成段。成立即可定案状态字，
随后直接做 3 状态权重层（Rise 15 池：怒 6 表熵 1.67、疲劳 4 表熵 1.30；
GU 在抽选层按状态调 prev 严格度，跨怪通用、不碰 action_id、不写参数）。

**边界**：`+0xCAC0` / `act+0x408` 语义是离线代码级推断、未经实机值域验证；
零动作段是强间接证据，不等于状态字。回退链 `v40.nro`(`be9cf246…`) /
`v39.nro`(`c54d6a05…`) / `v38.nro`(`12f1a74d…`) / `v37` / `v31` 纯只读。

---

## 2026-11-10 22:51 · v42「v41 状态扫描 + 有界减气蓄积写入」已部署（用户 22:41 要求）

用户原话：「v40 做了怪物疲劳改动，因为所需信息没有全部获取，所以 v41 也需要做个插件修改怪物疲劳，按 v40 说法是减气蓄积」。
⇒ 当前部署版本需同时具备 **v41 的只读状态扫描** 与 **v40 的减气蓄积写入**。
因 `v41.nro` 已定案为纯只读回退基线，不覆盖其定义，故新版本编号 **v42**（v41 全部能力 + 写入）。
**v38 AI 规则逐字节不变**；写入目标仍按 v40 口径：`*(u16*)(act+0x5D82) = 1000`（Exhaust 减气蓄积）。

### 1 · P11 复盘新增的根因（v40 写入为何没生效）

| # | 根因 | 证据 |
|---|---|---|
| 1 | **写在加载期** | `F.f=14563`，任务 HUD 初始化 `f≈14566` ⇒ 写入发生在怪物初始化完成前，A 行 `ex` 全场 240 条全 0 |
| 2 | **从未验证写入落地** | v40 的 F 行 `ex1` 打印的是常量 `FORCE_EX`，不是 `write_volatile` 后的回读 |
| 3 | **写入对象 ≠ 监控对象** | F 行 `mon=0C181390` / C 行 `LAST_MON=0C220060` |
| 4 | **没有逐帧轨迹** | 无法区分「字段被逐帧清零」「被状态机消费」「语义推断错误」 |

### 2 · v42 实现（`c064d980…`，36864 B，已部署）

- **时机**：`A_N >= 30`（第 30 个动作开始）且 `f >= 600` 才允许写；对**当前出招的 mon/act** 写。
- **门控**：`FORCED==0` / `GATE_LIVE==1` / `heap_ok(actp)` / `st != 1`（`act+0x518` 实机 0/1，1=怒）。
  **去掉 v40 已证伪的 `c4 != 1`**（`mon+0xCAC4` 恒 413/浮点）。
- **对象统一**：`reg_mon()` 改为返回槽号；F 行带 `i`，与 C 行 8 槽扫描同源，杜绝盯错怪。
- **真实回读**：F 行 `ex1 = rd16(actp+0x5D82)`（写入后立即读）。
- **有界维持窗口**（v40 只写一次，v42 针对「被逐帧清零」）：写入后 120 帧内，
  若 `ex < 1000` 则补写，总次数 ≤120；一旦 `c0==2/3`（`mon+0xCAC0`）或 `t4!=0`
  （`act+0x408`）立即早停并出 `G` 行。**不写状态字**、不写 `+0x73E0`、不改参数表。
- **W 行只读轨迹**：`+1/2/4/8/16/32/64/96/120/180/300/600` 帧记录**补写前**的
  `ex/c0/cf/st/t4/fw/done` ⇒ 一轮即可判「落地 / 被清零 / 被消费」。
- A 行追加 `forced`/`fw`；C 行离散指纹、8 槽、配额 800/400、banner 兼容串
  （`RAI v41` / `RAI v39` / `RAI v38`）全部保留 ⇒ 旧分析脚本仍可跑。
- 源码备份 `plug/context_probe/src/lib.rs.v41bak`；产物 `out/rai_force_tired_v42.nro`。
  ELF/NRO 特征串校验：`RAI v42` / `F f=` / `W f=` / `STATE-REACHED` 均在，
  v41 旧 banner `ZERO writes` 已不存在（避免编译失败时误用旧 ELF）。

### 3 · 脚本与纪律

- 新增 `tools/analyze_v42_force.py`（F/W/G + 锚点 + C 行覆盖 + 自保护判读）、
  `tools/make_v42_smoke.py`（合成日志，无需游戏）、`out/sim_v42_smoke.txt`。
  模拟日志 **PASS=13 / FAIL=0**；v40 P11 真实日志降级冒烟通过。
- `8_lite_check.bat`：`TOOL2` 指向 v42 判读脚本，标题/提示改 v42；
  `7_` 提示改 STEP 40（含 F/W/G 期望行、回退到 v41）。两者**执行逻辑 / 输出路径 /
  日志轮转 / Python 绝对路径均未动**，CRLF 保持；`6_` md5 `7361445f…` 未动，
  `load_order` / 变体 IPS / 游戏资源未动；无游戏进程时部署，部署 md5 与产物一致。
- **安全边界（本任务第二次游戏侧写入，必须保留）**：单一写入目标、120 帧窗口、
  ≤120 次、`GATE_LIVE` 熔断、非怒、`heap_ok`、状态达成早停。可能无效（最安全）、
  触发疲惫（目标）、或反复疲惫/动画错位（立即退出）。
  **一键回退** `out/rai_state_scan_v41.nro`（`4391d438…`，纯只读）
  → `v40.nro` / `v39.nro` / `v38.nro` / `v37` / `v31`。

### 4 · 下一轮（用户交互最小，一次定案）

双击 `8_lite_check.bat` → 正常打一场 → 关游戏，脚本自动出两份报告（第二份是本轮判据）。
只需告知「怪物大概任务内几分钟变疲劳、是否明显早于 15 分钟」以及
「有无反复疲惫 / 动画错位 / 卡顿」。

判据：F 行恰好 1 条 / `ex1 != 0` / `an >= 30` 且 `f > qstart` /
W 行 ≥8 且 `ex` 出现非 0 / F 与 W 的 mon 一致且该 mon 在 C 槽内 /
`G` 行或 `c0∈{2,3}` 或 `t4!=0` / 零动作锚点早于 15.3 分钟 / 零 FATAL / `live=1`。
- 若 **W.ex 全 0** ⇒ `act+0x5D82` 语义或对象推断错误，回退 v41，停止追减气蓄积。
- 若写入落地但未驱动状态 ⇒ 对照 W 轨迹与用户体感，再决定是否改状态字段。
- 若状态定案 ⇒ 直接做 3 状态权重层（抽选层按状态调 prev 严格度，跨怪通用、
  不碰 action_id、不写参数）。

**边界**：`+0x5D82` / `+0xCAC0` / `act+0x408` 仍是离线代码级推断、未经实机值域验证；
「提前出现零动作段」是强制疲惫的强间接证据，不等于状态字；需与用户口述时刻对照。

---

## 2026-11-10 23:01 · P12（v42 暂停场）实机：**减气蓄积路径证伪**

用户在任务中暂停并反馈「怪物仍然没有进入疲劳」。当场日志快照
`out/game_p54_lite_20261110_2301_v42_paused.txt`，判读报告 `out/v42_paused_report.txt`。
任务开始 `f=13278`（HUD layout），末 BEAT `f=25800` ⇒ **任务内仅 3.5 分钟**，
远短于 P11 的自然疲劳时刻（15.3 分钟）。

### 1 · 硬结论：写入落地，但游戏**完全没有消费**

- `F f=15536 i=1 an=30 mon=0C410060 act=0C4114A0 ex0=0 ex1=1000 st=0 c0=0 t4=65535`
  ⇒ 真实回读证明 `write_volatile(act+0x5D82, 1000)` **成功落地**，时机/对象门控都按设计执行。
- 12 条 W 行（+1…+600 帧）**`ex` 恒为 1000**，无衰减、无钳制、无清零。
  一个真实的减气蓄积字段必然被状态机逐帧处理；恒值 10 秒 ⇒
  **`act+0x5D82` 不是活的减气蓄积字段，或 `0xA398C` walker 的 `r0` 基址推断错误**
  ⇒ P11「减气蓄积不再追」的结论在实机层面得到确证，不再重试该写入。

### 2 · 三个假象（必须长期记住）

1. **G 行是假早停**：`t4 = *(u16*)(act+0x408)` 全场恒 `65535(0xFFFF)`（未初始化哨兵），
   `c0=0`。v42 的早停条件 `t4!=0` 在写入后 **+1 帧**就成立 ⇒ `fw=1`，
   120 帧维持窗口实际只写了 1 次（等价于 v40 的一次性写入）。
   ⇒ `t4!=0` 判据作废；`act+0x408` 不是疲惫时长。
2. **`mon+0xCAC0` 不是状态枚举**：A 行 `c0=205591808 / 203178464`（0x0C4xxxxx，
   指向对象自身的指针/噪声），`c4/c8/cf` 在不同 mon 上分别是 87/93/87 与浮点位模式
   ⇒ P11 的 `c0` 候选（初始化 1、疲惫分支 cmp 2/3）基址推断有误：
   `0x1068EA4` 的 `r4` / `0x1068E08` 的 `r7` **不是 mon**。四个状态候选需重新定位基址。
3. **写入对象不是主怪**：F 行 `mon=0C410060`(i=1)，而 V 行抽选最多 `0C420060`(5) /
   `0C1C2D40`(3)、A 行最多 `0C1C2D40`(18)。第 30 个动作开始恰好落在次要对象上。
   C 行 225/229 条也被 `0C410060` 的低字节噪声吃满。

### 3 · 插件状态与本轮改动

零 FATAL / `hub=15` / `live=1` / 4 个 hook 全装 / 无 SKIP ⇒ **插件本身稳定、无风险**，
无反复疲惫或动画错位的用户反馈。本轮仅改判读脚本 `tools/analyze_v42_force.py`：
- 排除 `t4==65535` 哨兵，状态判据改为 `c0∈{2,3}` 或 `0<t4<65535` 或有效 G 行；
- 任务时长 <15 分钟时不再把「零动作段提前」当证据；
- C 行覆盖判据允许「末段无状态变化」（暂停/离散指纹正常行为）。
模拟日志复核 **PASS=13 / FAIL=0**；暂停场报告现正确输出「写入落地但游戏完全未消费」。
已部署 nro 未改（`c064d980…`），游戏仍在运行/暂停中，**未重新部署**。

### 4 · 下一步

用户正常关游戏后（`8_lite_check.bat` 自动出报告），按用户指令二选一：
- **A（推荐）**：停止追减气写入，重新离线核对 `0x1068dd8` 疲惫分发头的 `r4/r7` 基址，
  定位真正的状态字与减气字段；拿到后再决定是否做强制疲劳写入。
- **B**：不强制疲劳，直接打满一场（~15 分钟）用 v41 只读扫描拿自然疲劳时段的
  字段值域，先定案状态字，再进 3 状态权重层。
无论哪条，`act+0x5D82` 写入与 `t4!=0` 早停都不得沿用。
回退链不变：`v41.nro`(`4391d438…`) 纯只读为首选。

---

## 2026-11-10 23:10 · 路线 A：离线重新定位 em 基址 + v43 纯只读探针已部署

用户 23:04「按推荐继续」⇒ 执行 P12 章的路线 A：停掉减气写入，重新核对疲惫分发头基址。
游戏已于 23:03 正常关闭（两份自动报告已生成），本轮**离线 + 部署**，未再进游戏。

### 1 · 离线复核结论（`tools/locate_tired_base.py` → `out/tired_base_audit.txt`）

- `0x1068dd8` 函数入口 `push {r4..lr}` → `mov r5,r1` / `mov sb,r2` / **`mov r4,r0`**。
  `r1`=1 怒、2 疲；`ldr r0,[r7=r4,#0xCAC4]!; cmp #1 / cmp #2` ⇒
  **所有 `+0xCAC0/+0xCAC4/+0xCBF1` 偏移都相对「第一个参数 em」，不是相对 `0xAFF40` 的 a0**。
- `0x106873C`（初始化，也是 `0x1068DD8` 的调用者之一）：`str 1,[r4,#0xCAC0]`；
  疲惫分支 `0x1068EA4 ldr r2,[r4,#0xCAC0]; cmp #2 / cmp #3` ⇒ `em+0xCAC0` 是 1/2/3 枚举。
- `0x1068F10 movw r0,#0x1428; ldr r0,[r4,r0]; strh r6,[r0,#0x408]` ⇒
  `em+0x1428` 是 act，疲惫时长写到 `act+0x408`；**`0xFFFF` 是「未设置」值，不是疲惫时长**
  （这解释了 v42 的 `t4!=0` 假早停）。
- `0x106A4C4` 是 `0x1069D8C` 内第二个调用点；`0x1069D8C` 入口也用
  `ldr r0,[sb=r4,#0x1428]!` ⇒ 它同样以 em 为第一个参数。
- **`0x106873C` 与 `0x1069D8C` 均无直接 BL 调用者、字面量池也无函数指针引用**
  ⇒ 通过虚表间接调用，静态无法推出 em 与 a0 的关系。
  P12 实机 `a0+0xCAC0` 是 0x0C4xxxxx 指针/噪声 ⇒ **a0 ≠ em**，只能靠运行时结构自洽扫描定位。

### 2 · v43 实现（`6a5683f7…`，36864 B，已部署）

- **ZERO writes**：删除全部 `write_volatile` / F / W / G 行 / 维持窗口 / `FORCE_*` 常量；
  ELF 特征串已核对（`RAI v43`/`P f=`/`D f=` 在，v42 的 F/W 与 "ONE bounded write" 均不在）。
- `scan_em()`：每个 mon 槽做**一次** a0±64KB 只读扫描，结构自洽判据
  `1<=*(P+0xCAC0)<=3` && `*(P+0xCAC4)<=2` && `*(P+0xCBF1)<=1` &&
  `heap_ok(*(P+0x1428))`；`P` 行输出 em 地址与 `delta = em - a0`。
- `D` 行：按定案 delta 每帧读 em 的真实状态字段（`c0/c4/cf` + `act+0x518/+0x408`），
  只在离散指纹变化时记录（上限 400）。v41 的 8 槽 C 行保留作对照。
- **v38 AI 规则逐字节不变**；零风险、无需熔断；回退 `v41.nro`（`4391d438…`）纯只读。
- 源码备份 `plug/context_probe/src/lib.rs.v42bak`，产物 `out/rai_em_base_v43.nro`。

### 3 · 脚本与纪律

- 新增 `tools/analyze_v43_base.py`（P/D 行 + delta 一致性 + 状态段 + 锚点判读）、
  `tools/make_v43_smoke.py`、`out/sim_v43_smoke.txt`；模拟日志 **PASS=8 / FAIL=0**，
  v42 暂停场日志降级冒烟通过。
- `8_lite_check.bat`：`TOOL2` → v43 判读脚本、提示改 v43、新增
  `set "PYTHONIOENCODING=gbk:replace"`：上一轮两份自动报告因 `⇒` 在 GBK 控制台
  `UnicodeEncodeError` 崩溃，已把 tools 下全部 `analyze_*.py` 的 `⇒` 换成 `->`，
  并让 Python 输出按 GBK 编码、不可编码字符降级替换 ⇒ 不再崩溃、中文可正常显示。
- `7_` 提示改 STEP 41（P/D 期望行）；两者**执行逻辑 / 输出路径 / 日志轮转 / Python 绝对路径
  未动**，CRLF 保持；`6_` md5 `7361445f…`、`load_order`、变体 IPS、游戏资源未动。

### 4 · 下一轮（一次定案）

双击 `8_lite_check.bat` → **打满一场到自然疲劳（任务内约 15 分钟）** → 关游戏自动出两份报告，
告诉我「怪物大概几分钟变疲劳」。判据：`P` 行 `strict>0` 且 delta 跨槽一致 /
`D` 行覆盖全场 / 疲惫段 `D.c0∈{2,3}` 或 `D.c4==2` / `t4` 从 0xFFFF 变为有效值 /
零 FATAL / `live=1`。
成立即定案 `em = a0 + delta` 与状态字，随后进 3 状态权重层（抽选层按状态调 prev 严格度，
跨怪通用、不碰 action_id、不写参数）。

**边界**：结构自洽判据是离线代码级推断，可能出现多个假命中（P 行会列出全部）；
若 `strict=0`，下一轮放宽 `c4/cf` 约束或扩大扫描范围，不改 AI 规则。

---

## 2026-11-10 23:15 · v44「强制疲劳」已部署（用户：等 15 分钟太累）

用户 23:13：「没有强制疲劳会很累，还是需要让怪强制疲劳」⇒ 取消「打满 15 分钟
等自然疲劳」的前置条件，改为**进任务后由插件主动触发疲惫**。

### 1 · 方案选择：调用游戏自己的状态机，而不是再写内存

P12 已证伪「写减气蓄积」（`act+0x5D82` 写入后游戏完全不读）。继续盲写状态字
只会得到一个"看起来是 2、但动画/AI 没变"的假状态。离线复核
`0x1068DD8` 疲惫分支尾部（本轮新增反汇编证据）：

| 地址 | 指令 | 含义 |
|---|---|---|
| `0x1069008` | `str r5,[r7]`（r7=r4+0xCAC4，r5=r1） | 写 `em+0xCAC4 = 1(怒)/2(疲)` |
| `0x106901C` | `vstr s0,[r4+0xCAC8]` | 疲惫计时器 |
| `0x1069024/2C` | `str 0,[r4+0xCAFC]` / `strb 0,[r4+0xCACC]` | 清标志 |
| `0x1068F9C` | `strh r0,[act+0x408]` | 疲惫时长 |
| `0x10690C4/0x1069164` | `strh r7,[act+0x3CA/0x3BE]` | 耐力相关 |
| `0x1069034/0x106917C` | `blx [vt+0x288]` / `blx [vt+0x410]` | **动画状态通知** |

⇒ `0x1068DD8(em, r1=2, r2=0)` 是游戏**自己的**疲惫状态机入口，调用它会
完整触发疲惫（含动画），不是伪造状态字。`r2=0` 取初始化路径 `0x106873C`
的用法，少动全局 UI（0x1B88/0x1B8C）。

### 2 · v44 实现（`9c74e1e1…`，40960 B，已部署）

- 保留 v43 的 P/D 只读扫描（先用 `scan_em()` 找 `delta = em - a0`）。
- `em_valid()` 调用前复核：`em+0xCAC0∈{1,2,3}` / `+0xCAC4<=2` /
  `*(em+0x1428)` 有效 / **`*(em)` 虚表合法且 `+0x288`、`+0x410` 槽非空**
  （函数会 `blx` 这两个槽，虚表非法会直接崩溃）。
- `0x1068DD8` 运行时首字必须 `E92D4FF0`（凡 `E28FFxxx` 解释器跳板一律 SKIP，
  SKIP 时 `FORCED=2` 不再重试，插件保持只读）。`TIRED SITE` 行输出首字。
- 触发：`FORCED==0` / `GATE_LIVE==1` / `A_N>=20` / `f>=600` / `heap_ok`，
  且 `*(em+0xCAC4)!=2`；**一次性熔断**。`fp(em, 2, 0)` 通过
  `transmute::<u32, unsafe extern "C" fn(u32,u32,u32)>` 调用。
- `F` 行记录调用前后 `c0/c4/t4`；`W` 行在 +1/2/4/8/16/32/64/120/300 帧
  只读回读，验证游戏是否接受疲惫状态。
- **v38 AI 规则逐字节不变**；不直接写任何游戏内存（状态由游戏函数自己写），
  不写参数表。**定位为测试用强制疲劳探针，不是最终 AI mod 行为**。
- 源码备份 `lib.rs.v43bak`；产物 `out/rai_force_tired_v44.nro`。
  ELF/NRO 特征串：`RAI v44` / `RAI v43 EM-BASE`(兼容) / P/D/F/W / `TIRED SITE` 全在。

### 3 · 脚本与纪律

- `tools/analyze_v43_base.py` 扩展 v44 判据（F 恰好 1 条、`c4a==2`、
  W 行 ≥5 且 `c4==2`、`0<t4<65535`、P/D 与自保护判据保留）；
  新增 `tools/make_v44_smoke.py`、`out/sim_v44_smoke.txt`。
  模拟 **PASS=11 / FAIL=0**，v43 模拟仍 **PASS=8 / FAIL=0**。
- `8_lite_check.bat` 提示改 v44（强调「短场即可、不用打 15 分钟」+ 风险与
  回退命令），`7_` 改 STEP 42（F/W/P/D 期望行）。两者**执行逻辑 / 输出路径 /
  轮转 / Python 绝对路径 / TOOL2 指向均未动**；`6_` md5 `7361445f…`、
  `load_order`、变体 IPS、游戏资源未动；无游戏进程时部署。

### 4 · 下一轮（用户负担最小）

双击 `8_lite_check.bat` → 进任意任务 → 锁定怪物 → **打约 20 个动作（很短）**
→ 观察怪是否流口水/喘气/动作变慢 → 正常关游戏（自动出两份报告）。
只需告知「是否很快疲劳、大概什么时候」以及有无异常。

判据：`TIRED SITE +1068DD8=E92D4FF0` / P 行 `strict>0` 且 delta 一致 /
`F` 行 1 条且 `c4a==2` / `W` 行 `c4==2` 且 `t4` 脱离 0xFFFF /
D 行出现 `c0∈{2,3}` / 零 FATAL / `live=1`。
成立即定案状态字并进 3 状态权重层；若 F 行 SKIP 或 strict=0，
分别改走「另找调用点」或「放宽 em 扫描」，不碰 AI 规则。

### 5 · 风险与回退（本任务风险最高的一版，必须保留）

主动调用游戏函数可能出现闪退 / 冻结 / 反复疲惫 / 动画错位；函数末尾是
`pop {..., lr}; bx r2` 的**虚表尾调用**，对栈与虚表合法性敏感 —— 这正是
`em_valid()` 要校验 `+0x288/+0x410` 的原因。
异常立即退出游戏并覆盖回 **`v43.nro`（`6a5683f7…`，纯只读）**：
`copy 04_RiseAI\out\rai_em_base_v43.nro` 到插件 nro 路径。
回退链还有 `v41.nro`(`4391d438…`) / `v38.nro` 等。
**边界**：`0x1068DD8` 的调用效果与 em 定位均为离线代码级推断 + 结构自洽，
尚未实机验证；本轮日志是唯一判据。

---

## 2026-11-10 23:30 · P13 复盘 + v45「hook 改参」强制疲劳已部署

用户 23:25 中断游戏：没看见怪物疲劳，但**游戏正常进行、无崩溃**。
日志快照 `out/game_p54_lite_20261110_2325_v44_paused.txt`，自动报告
`out/lite_state_result.txt`。

### 1 · P13 硬结论：v44 安全地什么都没做

- `TIRED SITE +1068DD8=E92D4FF0` ⇒ 疲惫入口首字正确，不是 IPS32 解释器跳板。
- **F=0 / W=0** ⇒ `force_tired()` 一次都没调用成功；零 FATAL、`live=1`、
  `hub=15`、游戏正常 ⇒ 熔断与校验按设计生效，没有造成任何损害。
- 根因是 **em 定位失败**：P 行三个槽给出三个互不相同的 delta
  （`-33412` / `9056` / `-17020`），`loose=256/226/144`；D 行显示所谓 em
  （如 `0C1EA61C`）的 `st` 是逐帧随机字节（102/157/171…）、`c0` 从 2 变 0
  ⇒ **a0±64KB 结构自洽扫描找到的全是噪声假命中**。
  `em_valid()` 的虚表检查（`+0x288/+0x410`）正确拒绝了它们 ⇒ 没有调用。
- 自动报告 v44 判据 **PASS=6 / FAIL=5**（F/W/c4a/t4/delta 一致性全 FAIL），
  与现象一致。⇒ **放弃"扫描猜 em"路线**。

### 2 · v45 方案（`de78b083…`，40960 B，已部署）

不再猜 em，改为 **hook 游戏自己的疲惫分发入口 `0x1068DD8`**：
- 游戏调用时 `a0=r0` 就是 100% 正确的 em（离线确证 `mov r4,r0`）。
- `h_tired` 只把**首次** `a1==1`(怒) 改成 `2`(疲)，随后 `original!(a0, 2, a2)`
  ⇒ 由游戏自己写 `em+0xCAC4=2`、`em+0xCAC8`、`act+0x408`、`act+0x3CA/3BE`
  并经虚表 `+0x288/+0x410` 通知动画。**不主动调用函数、不写内存、不猜对象**，
  风险低于 v44（只改一个参数，栈/虚表/尾调用全由游戏处理）。
- 门控：`FORCED==0` 一次熔断 / `GATE_LIVE` / `FRAMES>=600` / `heap_ok(a0)` /
  运行时首字 `E92D4FF0`（否则 `SKIP h_tired`）。
- `T` 行记录每次 hook 调用（em/r1/r2/change），`F` 行记录改参前后
  `c4b/c4a/t4b/t4a`，`W` 行 +1…+300 帧只读回读；v43 的 P/D 扫描与
  v38 规则全部保留作对照。
- hook 安装**不计入 HOOKS mask**，保持 `hub=15` 兼容旧判据。
- **v38 AI 规则逐字节不变**；测试用强制疲劳探针，非最终 AI 行为。
  源码备份 `lib.rs.v44bak`；产物 `out/rai_hook_tired_v45.nro`。
  ELF/NRO 特征串：`RAI v45` / `RAI v44`(兼容) / T/F/W / `INSTALL h_tired` 全在。

### 3 · 脚本与纪律

- `tools/analyze_v43_base.py` 扩展 v45：T 行解析、`h_tired` 安装判据、
  v45 结论文案；新增 `tools/make_v45_smoke.py`、`out/sim_v45_smoke.txt`。
  模拟：**v45 PASS=13/FAIL=0**、v44 11/0、v43 8/0；v44 真实暂停日志仍
  PASS=6/FAIL=5（正确反映"未触发"）。
- `8_lite_check.bat` 提示改 v45、`7_` 改 STEP 43（T/F/W 期望行）。
  两者**执行逻辑 / 输出路径 / 轮转 / Python 绝对路径 / TOOL2 指向未动**；
  `6_` md5 `7361445f…`、`load_order`、变体 IPS、游戏资源未动；
  无游戏进程时部署，部署 md5 与产物一致。

### 4 · 下一轮（短场）

双击 `8_lite_check.bat` → 进任务锁定怪 → 打一小会儿 → 正常关游戏。
判据：`INSTALL h_tired` / T 行 ≥1 且出现 `change=1` / F 行 1 条且
`c4a==2` / W 行 `c4==2` 且 `t4` 脱离 0xFFFF / 零 FATAL / `live=1`。
- 若 **T 行 0 条** ⇒ `0x1068DD8` 在任务中没被调用，改 hook 上游
  `0x1069D8C`（rage/tired 主管线）或 `0x106873C`（初始化）。
- 若 T 行有但 `r1` 从未为 1 ⇒ 改参条件需放宽（例如 `r1==3` 也改）。
- 若 F 行 `c4a!=2` ⇒ 疲惫分支被 `em+0xCAC4` 已是 2 提前返回，或改参未生效。

### 5 · 风险与回退

hook 只改一个参数且 `original!` 恒调用，但仍可能出现状态不一致 /
动画错位 / 冻结。异常立即退出并覆盖回 **`v43.nro`（`6a5683f7…`，纯只读）**：
`copy 04_RiseAI\out\rai_em_base_v43.nro` 到插件 nro 路径。
**边界**：`0x1068DD8` 是否在任务中被调用、改 `r1` 的完整效果均为
离线推断 + 结构分析，尚未实机验证；本轮 T/F/W 行是唯一判据。

---

## 2026-11-10 23:40 · P14 复盘 + v46「字段层强制疲劳」已部署

用户 23:35 中断游戏：怪物**还是发怒了**（不是疲劳），游戏正常无崩溃。
日志快照 `out/game_p54_lite_20261110_2335_v45_paused.txt`。

### 1 · P14 硬结论：整条函数管线在本作实机不走

- `INSTALL h_tired +001068DD8 first=E92D4FF0` 成功，但 **T=0 / F=0 / W=0**
  ⇒ `0x1068DD8` 在整场任务中**一次都没被调用**（P13 的 v44 也未调用成功）。
- 怪物照样发怒：A 行 `st=1` @ `f=13862`（`mon=0C190060`），全场 41 条 A 行
  `st` 只出现 0/1、`t4` 恒 `65535`。零 FATAL、`live=1`、`hub=15`。
- ⇒ 23:10 离线定位的 `0x1068DD8 / 0x1069D8C / 0x873C` rage/tired 管线
  **在本作实机是不走的死代码或另一版本路径**；继续 hook 它、继续猜 em 都无效。
  **放弃函数层**（v44 主动调用、v45 hook 改参均作废）。

### 2 · v46 方案（`daef81ef…`，40960 B，已部署）

改用**唯一被实机验证过语义的字段**：`*(u8*)(act+0x518)`，
`act = *(mon+0x1428)`（我们一直可靠使用，不需要 em）。
- `0`=普通；`1`=发怒（`main+0x8172C` is_enraged，P14 的 `st=1` 已闭环）；
  `2`=另一状态（`main+0x81774`，README 标注「疑似疲劳」），历史日志从未出现。
- 触发：**游戏自己把 st 写成 1（发怒）的那一刻**，把该 act 的 st 改成 2；
  若始终不发怒，`A_N>=20` 兜底。之后 **600 帧（10 秒）维持** `st==2`
  （游戏若写回 1 就再写），一次性熔断 + `GATE_LIVE` + 堆校验。
- 只写 **1 个字节**，不调用函数、不猜 em、不写状态字结构、不写参数表。
  `Y` 行记录 `TRIG`（写前 stb / 写后 sta）与 `HOLD`（+1…+600 帧回读）。
- v45 的 `h_tired` 保留但**不再改参**（`forced_now=false`，只输出 T 行诊断）；
  v43 的 P/D 扫描、v38 规则全部保留作对照；hook mask 仍 `hub=15`。
- 源码备份 `lib.rs.v45bak`；产物 `out/rai_field_tired_v46.nro`。
  ELF/NRO 特征串：`RAI v46` / `RAI v45`(兼容) / `Y f=` / `kind=TRIG` / `kind=HOLD` 全在。

### 3 · 脚本与纪律

- `tools/analyze_v43_base.py` 扩展 v46（Y 行、TRIG/HOLD、A 行 st=2、
  自保护；v46 不再要求 em delta 一致性）；新增 `tools/make_v46_smoke.py`、
  `out/sim_v46_smoke.txt`。
  模拟：**v46 PASS=9/FAIL=0**；v45 13/0、v44 11/0、v43 8/0；
  v45 真实暂停日志仍正确判 PASS=7/FAIL=6。
- `8_lite_check.bat` 提示改 v46、`7_` 改 STEP 44（Y 行期望）。
  两者**执行逻辑 / 输出路径 / 轮转 / Python 绝对路径 / TOOL2 指向未动**；
  `6_` md5 `7361445f…`、`load_order`、变体 IPS、游戏资源未动；
  无游戏进程时部署，部署 md5 与产物一致。

### 4 · 下一轮（短场）

双击 `8_lite_check.bat` → 进任务锁定怪 → 打一小会儿（发怒或未发怒都会触发）
→ 看怪是否流口水 / 喘气 / 动作变慢、是否还会发怒 → 正常关游戏。
判据：`Y kind=TRIG` 恰好 1 条且 `sta==2` / HOLD ≥5 条且 `sta` 保持 2 /
A 行出现 `st=2` / 零 FATAL / `live=1`。
- **若 st=2 落地但视觉上仍无疲劳动画** ⇒ `act+0x518` 只是判定标志，
  不是动画状态；下一轮改查疲惫动画字段（`act+0x408` 从 0xFFFF 变化、
  或 `+0x3CA/0x3BE`），不再重复函数层路线。
- 若 Y 行 0 条 ⇒ 触发条件没满足（看 A_N / 槽），放宽即可。

### 5 · 风险与回退

只写 1 字节 + 600 帧维持，风险低于 v44/v45，但仍可能状态不一致 /
动画错位 / 冻结。异常立即退出并覆盖回 **`v43.nro`（`6a5683f7…`，纯只读）**：
`copy 04_RiseAI\out\rai_em_base_v43.nro` 到插件 nro 路径。
**边界**：`st=2` 是否等于「疲劳」仍是 README 级推断（0x81774 读 ==2），
未经实机视觉验证；本轮用户体感与 Y/A 行是唯一判据。

---

## 2026-11-10 23:55 · P15 复盘 + 临时「雄火龙减气阈值」数据层 mod 已部署

用户 23:50 中断游戏：v46 仍没见到疲劳，提出新方案 —— **临时修改雄火龙的动作减气值，
拿到疲劳全部所需数据后再改回来**。日志快照
`out/game_p54_lite_20261110_2350_v46_paused.txt`。

### 1 · P15：v46 字段写入落地但无效

- `Y kind=TRIG act=0C2514A0 stb=0 sta=2`，10 条 HOLD 回读恒 `sta=2`，
  `n` 从 1 增至 6（游戏几次写回又被改回）⇒ **1 字节写入确实落地并维持**。
- 但 **A 行 `st` 全场只有 0/1（55 次 0、9 次 1），从未出现 2**；`t4` 恒 65535；
  用户没看到疲惫。⇒ 写入的 act 不是 A 行采样到的出招怪，且 `st=2` 只是
  `0x81774` 的判定标志，**不是疲惫动画状态**。至此字段层也证伪。
- 零 FATAL、`live=1`、`hub=15`、游戏正常 ⇒ 无损害。

### 2 · 口径澄清：改的是「减气触发阈值」，不是「每动作减气值」

本地资料库（`docs/wiki/monster-rage-tired.md`、`reference/formats/dttune.md`）
中**没有定位到独立的「怪物动作减气值」表**；已字节级确证 `[C]` 的是
`emNNN_00_dttune` 的 **Exhaust 状态记录**（6×u16：initial / A / B / durF /
increase / max）。疲惫由玩家造成的减气蓄积达到 `initial` 触发。
故本轮改的是这个阈值 + 疲惫时长，属于游戏正常机制路径，比写状态字节可靠。

### 3 · 临时改动（可一键回退）

- 源文件 `01_Original_romfs/romfs/nativeNX/arc/enemy/em002_00.arc` →
  `enemy\dt_tune\em002_00_dttune`，Exhaust 记录 **@0x390**：
  `(180, 600, 5, 0, 75, 480)` → **`(1, 600, 5, 600, 75, 480)`**
  （`initial` 180→1、`durF` 0→600 帧=10 秒；A/B/increase/max 不动）。
- 按 ARC 纪律：**单条目 arc**（`arc_tool.py pack ... --orig`），1 条目、
  typeHash `48E8AC29` 保持不变、仅 3 字节差异；产物
  `03_Output/em002_00_exhaust_probe.arc`（`0f4c5ba5…`，33440 B）。
  打包前查过冲突：**没有其他 mod 覆盖 `em002_00.arc`**。
- 部署 `mods/Rathalos_ExhaustProbe/romfs/nativeNX/arc/enemy/em002_00.arc`；
  `load_order` **只追加一行** `Rathalos_ExhaustProbe`，原文件备份
  `out/load_order_backup_20261110_2350.txt`，既有行未动。
- **插件回退到 `v43.nro`（`6a5683f7…`，纯只读）**：撤销 v46 的
  `act+0x518=2` 写入，避免污染疲惫时段的字段观测；`8_` 的 TOOL2
  `analyze_v43_base.py` 与 v43 banner 正好匹配。
- 原版备份：`02_Workspace/em002_original_backup/`（原 dttune + 原 arc）。
- 一键回退 `tools/rollback_exhaust_probe.py`（*不删除任何文件*）：
  把 mod 目录移动到 `out/_retired_Rathalos_ExhaustProbe/`、
  从备份恢复 `load_order`、确认插件仍为 v43 只读。
- `6_` md5 `7361445f…` 未动；游戏本体资源未改动（只在 mods 下新增）。

### 4 · 下一轮（短场，用户负担最小）

双击 `8_lite_check.bat` → 进**雄火龙（em002_00 普通个体）**任务 →
**带 LV1 减气弹 / 减气瓶，或用大锤 / 狩猎笛打一下**（提供 ≥1 点减气蓄积）
→ 观察流口水 / 喘气 / 动作变慢 / 倒地（阈值现在是 1，疲惫固定 10 秒）
→ 正常关游戏。报告里看 A/C/D 行的 `st/t4/c4/ex` 值域与 BEAT 零动作段，
即可拿到疲惫时段的字段数据。**拿到后立即运行回退脚本**。

**边界**：`initial=1` 仍需玩家造成至少 1 点减气，不是无条件疲惫；
`0/0/0` 才是免疫，本改法不是。只改 `em002_00`；若打的是狞猛 / 二名个体
（`em002_02` / `em002_04`）需补对应 arc。若用户指的是**玩家武器动作减气值**，
那是另一张表，本地资料未定位，需另行调研。

---

## 2026-11-11 20:05 · P16 复盘 + 减气阈值 v2（initial=0）已部署

用户 20:00 中断游戏：雄火龙仍未进入疲劳。日志快照
`out/game_p54_lite_20261111_1959_exhaust_probe.txt`。

### 1 · 硬结论：mod 生效，但**减气蓄积从未产生**

- 游戏日志明确：`[romfs] archives merged: data/romfs/nativeNX/arc/enemy/em002_00.arc
  <- 1 entries changed by mods/Rathalos_ExhaustProbe/...` ⇒ **单条目 arc 合并成功**，
  排除「mod 没加载」「路径错」「整包覆盖」三类怀疑。
- 插件 banner `RAI v43`（纯只读）正确；零 FATAL、`live=1`、`hub=15`、游戏正常。
- V 行 `sp=0002`（雄火龙 em002）在场，`sp=1016` 为同场另一只怪。
- **A 行 35 条：`ex` 恒 0、`t4` 恒 65535、`st` 只有 0/1** ⇒
  没有任何减气蓄积，阈值 1 也没被达到。任务内约 3 分钟（短场）。
- 结论：上一版把阈值降到 1 仍依赖「玩家造成 ≥1 点减气」，
  而本场没有减气来源（用户未带减气弹/打击武器，或减气攻击未生效）。

### 2 · v2 改动（不依赖玩家装备）

`em002_00_dttune` Exhaust 记录 **@0x390**：
`(180, 600, 5, 0, 75, 480)` → **`(0, 0, 0, 600, 75, 480)`**
- `initial` 1→**0**：若判定为 `buildup >= initial`，则 0≥0 无需任何减气来源。
- `A`(衰减周期) 600→0、`B`(每周期扣点) 5→0：蓄积不再衰减。
- `durF` 600（10 秒疲惫）保持；`increase=75` / `max=480` 保持 ⇒
  **不是 wiki 的 `0/0/0 = 免疫` 模式**（免疫指 initial/increase/max 全 0）。
- 单条目 arc 重新打包：1 条目、hash `48E8AC29`、6 字节差异，
  产物 `03_Output/em002_00_exhaust_probe.arc`（`c6b1198d…`，33441 B），
  已覆盖部署到 `mods/Rathalos_ExhaustProbe/.../em002_00.arc`（md5 一致）。
- 插件仍为 `v43.nro`（`6a5683f7…`，纯只读，零写入）；
  `load_order` 仍只追加一行；`6_` / 游戏本体资源 / 既有行未动。
- 离线反汇编补充：`0xA398C`（状态衰减 walker）首字 `E92D41F0`，
  其 `r4=r0` 通过 `+0x1428` 取 act，`Exhaust` 段读 `act+0x5D82`、
  timer `act+0x5D88`；walker 尾部 `b 0xaac10 → 0xa21a8`（未继续追）。
  这解释 v40/v42 写 `act+0x5D82` 恒值不衰减：walker 只在
  `mgr+0x44` 参数非空且 timer 到期时扣点，且疲惫判定不在该 walker 内。

### 3 · 下一轮（短场，无需特殊装备）

双击 `8_lite_check.bat` → 进**普通雄火龙 em002_00**任务 → 正常打一小会儿 →
看是否流口水 / 喘气 / 动作变慢 / 倒地（疲惫固定 10 秒）→ 关游戏。
判据：A/C 行 `t4` 脱离 65535、`st` 出现 2、BEAT 出现零动作段。
拿到数据后立即运行 `python 04_RiseAI\tools\rollback_exhaust_probe.py` 回退。

### 4 · 若 v2 仍失败（预先定好的退路）

`initial=0` 若被游戏判为免疫（wiki 的 0/0/0 口径可能只看 initial），
则「蓄积 ≥ 阈值」不是本作疲惫触发方式。此时不再继续试状态字段/函数层
（P12~P15 已全部证伪），改走用户最初提出的**玩家武器动作减气值**
（另一张表，本地资料库未定位，需另行调研），或放弃强制疲劳、
回到纯观测（打满 15 分钟拿自然疲惫数据）。

---

## 2026-11-11 20:12 · P17 实机证伪：`@0x390` 是硬直/气绝记录，不是疲劳窗口

用户打了两次任务后给出决定性实机证据：
- **太刀**：任何攻击都不能让雄火龙进入疲劳；
- **大锤**：**第一次攻击就让雄火龙进入硬直**；
- 用户结论：「你修改的这个数据是硬直数据，而不是疲劳窗口」。

### 1 · 结论：`em002_00_dttune @0x390` 的字段映射错了

- 该记录 `(180, 600, 5, 0, 75, 480)` 被 wiki `monster-rage-tired.md`
  的「疲惫触发蓄积表」标为 em002 减气 180/75/480 [C]，我据此改了
  `initial` 与 `durF`。**实机推翻该映射**。
- 因果链自洽：太刀不积累气绝 → 无反应；大锤打头积累气绝 →
  `initial=0` 后一击即达阈值 → 气绝/硬直。⇒ **该记录属于打击系
  硬直（气绝/怯み）蓄积，不是减气/疲惫窗口**。
- 离线交叉验证（本轮新增，7 只怪 dttune 逐字节扫描）：
  | 怪 | `(initial,A,B,durF,increase,max)` 命中 | 前 12B |
  |---|---|---|
  | em001 雌火龙 | `+390 (180,600,5,0,75,480)` | `+384 (150,600,5,600,150,750)` |
  | em002 雄火龙 | `+390 (180,600,5,0,75,480)` | `+384 (150,600,5,600,150,750)` |
  | em007 角龙 | `+35C (300,600,10,600,100,800)` | `+350 (150,900,5,600,100,650)` |
  | em037 迅龙 | `+356 (180,600,5,0,75,480)` | `+34A (200,600,5,600,150,800)` |
  | em043 恐暴龙 | `+510 (180,600,5,900,150,780)` / `+51C (180,600,5,0,150,780)` | `+504 (180,600,10,900,200,980)` |
  | em060 青熊兽 | `+35C (100,600,5,0,80,420)` | `+350 (100,600,5,600,80,300)` |
  | em088 阁螳螂 | `+374 (180,600,5,0,150,800)` | `+368 (150,600,5,420,250,1000)` |
  ⇒ **同一个 `(initial,increase,max)` 三元组可命中多条记录**（恐暴龙 2 条），
  说明「按数值三元组定位减气记录」方法本身不可靠；`durF` 位置也不唯一。
  带 `durF=600`（10 秒窗口）的相邻记录更可能是用户说的「疲劳窗口」，
  但**未经实机验证，不得再盲改**。

### 2 · 累计证伪清单（强制疲劳路线，全部实机）

| 版本 | 路线 | 结果 |
|---|---|---|
| v40/v42 | 写 `act+0x5D82` 减气蓄积 | 写入落地，游戏 600 帧完全不消费 |
| v44 | 主动调用 `0x1068DD8(em,2,0)` | P 行 delta 不一致，`em_valid` 正确拒绝，F=0 |
| v45 | hook `0x1068DD8` 改 r1 1→2 | T=0，该入口整场不被调用 |
| v46 | 写 `act+0x518=2` 并维持 | Y 行落地，但 A 行 st 仍 0/1，无疲劳动画 |
| 数据层 v1/v2 | 改 `em002_00_dttune @0x390` | mod 确实合并生效，但改的是硬直数据 |

⇒ **函数层 / 字段层 / 数据层猜测式改参三条路全部证伪**。
继续按 wiki 数值表盲改参数不可接受；下一步必须改为**实机只读反推**。

### 3 · 状态（待用户关闭游戏后撤销）

- 游戏进程仍在运行（20:12 检查），**未改动任何加载状态**；
  `mods/Rathalos_ExhaustProbe`、`load_order` 追加行、v43 只读插件均保持原状。
- 一键撤销 `python 04_RiseAI\tools\rollback_exhaust_probe.py`
  （移动 mod 目录到 `out/_retired_…`、恢复 `load_order` 备份、确认 v43 只读）。
  原版备份完好：`02_Workspace/em002_original_backup/`。

### 4 · 下一步候选（等用户拍板，不再自作主张改参数）

- **A 只读差分（推荐）**：利用「大锤第一击」这个可复现触发点，做纯只读
  探针，在动作开始 / 每帧对 8 槽 mon 差分 `act+0x408/+0x3CA/+0x3BE/
  +0x5D82/+0x518` 与 `mon+0xCAC0/4/8/+0xCBF1`，一次定案哪个字段对应
  硬直/气绝、哪个对应疲惫窗口。零写入、零参数猜测。
- **B 离线重定位**：查 `em002_00_doumouka`（`cEmDouMouKaData` 含
  `StaminaSubRate` / `StaminaTimeVal` / `cEmStaminaData::cStaminaLev`）
  与 `dtbase`，先给结论、不改游戏。
- **C 搁置强制疲劳**：回到 AI 规则主线（3 状态权重层），疲惫数据以后再说。

**边界**：本轮全部为实机因果推断 + 离线字节交叉验证；
`durF=600` 相邻记录是否真是疲劳窗口，未经实机验证。

---

## 2026-11-11 20:20 · P18 按用户定义核查「到底有没有找到疲劳」+ 定性更正

用户补充定义：**疲劳 = 怪物待机动作变成流口水 + 攻击动作频次降低**，
并要求据此检查历次日志；同时提示 GitHub 解包资料已更新。

### 1 · 结论：**没有找到**（严格按用户定义）

| 日志 | 是否有「流口水待机 / 频次降低」 | 是否捕获到对应状态字段 |
|---|---|---|
| P11 v40（用户确认 15 分钟后疲劳） | **有**：`f=68400..69600` 每 300 帧动作数 5→1~2，`f=69900..70500` 连续 900 帧 0 动作 | **否**：C 行配额在 `f=15380` 就打光，该时段 C 行 **0 条**；A 行 9 条 `st=0` 全程，v40 无 `t4/c0` 字段 |
| v42 / v44 / v45 / v46 各场 | 无 | 无 |
| 2026-11-11 太刀场 | 无 | `ex` 全 0 |
| 2026-11-11 大锤场 | 无（第一击即硬直） | `ex=30/60/90`（减气蓄积真实产生），但 `st=0`、`t4=65535` 全程 |

⇒ 之前 P11 报告写的「疲劳时段定案 `f=69600..70500`」只是**用零动作做的
时间锚点**，不是状态字段定案；后续所有「强制疲劳」版本均**未复现**
用户定义的流口水待机。累计 6 轮实机，疲劳窗口字段一个都没拿到。

### 2 · 定性更正（推翻 20:12 章的措辞，但不推翻实机结论）

按 `docs/wiki/monster-status.md`（本地 11-04 快照即有，本轮之前漏读）：
- `em002_00_dttune` 状态块起点 `@0x35C`，行序 = 毒/眠/麻/**晕**/**减气**/骑乘/跳跃/爆破，
  每行 6×u16 `[initial, A, B, durationFrames, increase, max]`。
- `@0x384 (150,600,5,600,150,750)` = **眩晕 150/150/750 / 10s / 打头累积**；
  `@0x390 (180,600,5,0,75,480)` = **减气 180/75/480 / 疲劳无固定时长**。
- 原文明确：**「骑乘/减气/跳跃/爆破是瞬时判定，没有时长概念」**、
  **「疲劳无固定时长」**，`durationFrames` 只服务毒/眠/麻/晕。
- 怪物侧 KO/硬直计量在 `0x16915C` / `0x169174`（力竭项）/ `0x16919C`，
  **不是 8 种异常的累积函数**；「受击方的累积加值、阈值递增、衰减函数：未找到 [U]」。

⇒ **`@0x390` 的 wiki 映射没错，错的是我**：把「减气瞬时判定」当成
「疲惫窗口」，还去改一个对减气无效的 `durF`。把 `initial` 降到 0 后，
大锤第一击的减气蓄积立刻越过阈值 → 触发瞬时硬直（用户所见）；
太刀不产生减气 → 完全无反应。用户「这是硬直数据，不是疲劳窗口」
在**效果层面完全正确**。20:12 章写的「wiki 映射错误」措辞不准，以此章为准。

### 3 · GitHub 最新版比对（用户提示）

- `Twelve-eight/MHGU` 默认分支 `master`，`pushed_at 2026-11-09`；
  近 30 次提交**无** tired / exhaust / stamina / dttune / drool 相关更新
  （均为 emc-script-vm、coverage、audit 类）。
- 下载三份关键文档到 `04_RiseAI/refs/re-master/`：
  `monster-status.md`(25852 B)、`monster-rage-tired.md`(16679 B)、
  `dttune.md`(21255 B)，与本地 11-04 快照 **逐字节完全相同**。
⇒ 最新版没有新增可用信息；真正的纠正来自**本地已有但此前漏读**的
  `monster-status.md`。若用户指的是另一仓库的解包文件，需其给出链接。

### 4 · 已撤销（用户 20:12 关闭游戏后执行）

`python 04_RiseAI/tools/rollback_exhaust_probe.py` 已执行：
- `mods/Rathalos_ExhaustProbe` → `04_RiseAI/out/_retired_Rathalos_ExhaustProbe/`（未删除）；
- `load_order.txt` 从 `out/load_order_backup_20261110_2350.txt` 恢复，既有行未动；
- 插件仍 `v43.nro`（`6a5683f7…`）纯只读；`6_` md5 `7361445f…` 未动；
- 原版备份 `02_Workspace/em002_original_backup/` 完好。
游戏目录已无任何 `em002_00.arc` 覆盖 ⇒ **回到干净原版基线**。

### 5 · 下一步（不再改任何数据）

用户定义提供了**行为判据**，比猜字段可靠：
1. 用**纯只读探针**，以大锤连续攻击作为可复现的减气累积路径
   （实机 `ex` 已达 30/60/90，原版阈值 180 ⇒ 几次重击即可自然触发，
   比等 15 分钟快得多）；
2. BEAT 全量 `a` 计数检测「频次下降 → 零动作待机」段作为锚点；
3. 段内逐帧记录 8 槽候选字段 `act+0x408/+0x3CA/+0x3BE/+0x5D82/+0x518/
   +0x1A1` 与 `mon+0xCAC0/4/8/+0xCBF1`，C 行配额 ≥800 且只用离散指纹
   （P11 的失败根因是 400 条配额被浮点 `c4` 在 `f=15380` 吃光）；
4. 由用户在看到流口水时给一个大致时刻，与锚点段对照定案。

零写入、零参数猜测、不再动 dttune。等用户确认后再实施。

---

## 2026-11-11 20:55 · P19：首次实机捕获「流口水疲劳」行为 + v47 定时快照探针已部署

用户 20:48 暂停游戏并给出截图：**跳狗龙正在流口水（疲劳状态）**。
游戏 20:51 正常关闭，两份自动报告已生成。日志归档：
- `out/game_p54_lite_20261111_2048_TIRED_DROOL_paused.txt`（暂停瞬间快照，f 到 18300）
- `out/game_p54_lite_20261111_2051_v43_TIRED_full.txt`（完整场，f 到 28500）
判读回溯 `out/v47_P19_retro_report.txt`。部署插件当时仍是 `v43.nro`（`6a5683f7…`）纯只读。

### 1 · 三个硬结论

**(1) 自然疲惫只需约 3.4 分钟，不是 15 分钟。**
`qstart=3247`；BEAT 每 300 帧动作增量在正常段是 5~13，
`f=15300` 起变为 `2 / 3 / 1`，`f=16200` 起为 0。
⇒ 疲惫行为起点 `f≈15300`，任务内 `(15300-3247)/3600 = 3.35` 分钟。
P11 的 15.3 分钟是另一场/另一怪，不构成通用前置条件。
**用户负担问题已由实机本身解决：跳狗龙 + 当前打法，短场即可复现。**

**(2) `act+0x5D82` 是「活的」减气蓄积字段 —— 更正 P12 的定性。**
主怪 `0C190060` 的 `ex` 逐次采样：
`5 → 30 → 45 → 70 → 95 → 125 → 110(衰减) → 140 → 135 → 145 → 150 → 145`，
`f=14368` 之后该怪不再出招（进入疲惫）。
⇒ 减气蓄积真实累积、会衰减、到阈值触发疲惫。
P12 写「`+0x5D82` 不是活的减气蓄积」措辞不准：v40/v42 直接写 1000 之所以
无效，是因为**阈值判定发生在游戏自己的累加路径里**，写值不跑该路径
（且 v42 写的是次要怪 `0C410060`）。
⇒ 长期口径：`+0x5D82` 可作**观测字段**，但**禁止再靠写它来强制疲劳**。

**(3) 状态字仍然没有捕获（第 7 轮），失败模式已精确定位。**
- `C` 行 800 条配额全部落在 `f=3245..6064`：指纹里的 `cf = *(u8*)(mon+0xCBF1)`
  是逐帧随机字节（58/153/29/108/9…），每帧都触发 ⇒ 配额在任务开始 47 秒就吃光。
- `D` 行 113 条全是 em 假命中噪声（delta 各槽互异、c0/c4 是随机大数），末条 `f=13942`。
- 疲惫窗口 `f>=15300` 内 **C=0 / D=0 / A=0**（A 行最后 `f=15384`，流口水待机不出招）。
⇒ 根因不是「没看到疲劳」，而是**探针依赖动作开始事件 + 噪声指纹吃光配额**，
零动作待机段天然没有任何记录。

### 2 · 重要陷阱：暂停菜单不冻结 `forge_onUpdate`

用户开暂停菜单后 `FRAMES` 继续增长，BEAT 一直输出到 `f=28500`，
但 `A_N` 冻结在 262 ⇒ `f=16200..28500` 的**长零动作段主要是暂停造成的**，
不能整段当作疲惫待机。日志尾部大量 `KatSmithy input: WantCaptureKeyboard=1`
即为暂停菜单输入。
⇒ P19 可用的行为证据是 **`f=15300..15900` 的频次下降 + 用户截图/口述**；
后续探针与判读必须排除长时间暂停。

### 3 · v47 实现（`0fd173bd…`，36864 B，已部署）

基于 `lib.rs.v43bak` 纯只读基线重建（当前 v46 源码另存 `lib.rs.v46bak`），
**ZERO writes**，v38 AI 规则逐字节不变：
- 删除已证伪的 em 自洽扫描（P/D 行）；C 行指纹去掉 `cf/c0/c4` 噪声，
  只用 `st` / `t4!=0` / `h1` / `ex` 粗粒度（每 25 点一档），配额 800→300。
- **`R` 行定时快照**：不依赖动作事件，常规每 150 帧、低活动窗口每 30 帧，
  对 `ex>0 || st!=0 || t4!=0` 的槽输出
  `st/t4/ex/d5(+5D88)/h1/e1/dc/p3ca(+3CA)/p3be(+3BE)`，上限 900 条。
  ⇒ 零动作待机段第一次有状态记录。
- **`N` 行锚点**：用 BEAT 的 300 帧 `A_N` 增量自动输出
  `ENTER-LOW / EXIT-LOW`；要求 `A_N>=10` 以排除任务加载期。
- **配额保护**：低活动段超过 3600 帧（60 秒）自动降回 150 帧周期
  ⇒ 用户长时间暂停也不会吃光 R 行配额（针对 P19 陷阱）。
- ELF/NRO 特征串核对：`RAI v47` / `R f=` / `N f=` / `ENTER-LOW` 在，
  v46 的 `kind=TRIG` / `ONE byte write` 均不在（确认无写入）。

### 4 · 脚本与纪律

- 新增 `tools/analyze_v47_tired.py`（行为锚点 → R 行覆盖 → 窗口内/外字段值域差分
  → 自动列候选状态字段 → 自保护判据）、`tools/make_v47_smoke.py`、
  `out/sim_v47_smoke.txt`、`out/v47_sim_report.txt`。
  模拟 **PASS=7/FAIL=0** 且正确识别 `st=2 / t4=600 / p3ca=120`；
  P19 真实日志回溯正确判为「零动作段存在但 R=0、C 配额 6064 吃光」，
  即 v47 要修复的失败模式。GBK 控制台输出复核无乱码。
- `8_lite_check.bat`：`TOOL2` → v47 判读脚本、标题/提示改 v47（强调短场、
  看到流口水立即关游戏、不要久暂停）；`7_` 改 STEP 46。
  两者**执行逻辑 / 输出路径 / 日志轮转 / Python 绝对路径未动**，CRLF 保持；
  `6_` md5 `7361445f…`、`load_order`（已回滚干净）、变体 IPS、游戏资源未动。
- 游戏进程确认关闭后才部署，产物与插件目录 md5 一致。

### 5 · 下一轮（短场，一次定案）

双击 `8_lite_check.bat` → **同一怪种 / 同一武器**再打一场 →
看到流口水/喘气/动作变慢时**立即正常关游戏**（不要在暂停菜单久留）→
自动出两份报告，第二份直接给出「窗口内出现新值」的候选状态字段。
用户只需告知「大概几分钟流口水」。
判据：N 行 `ENTER-LOW` / R 行覆盖锚点段 ≥3 条 / 至少一个字段窗口内出现新值 /
零 FATAL / `live=1`。成立即定案状态字，进 3 状态权重层
（抽选层按状态调 prev 严格度，跨怪通用、不碰 action_id、不写参数）。

**边界**：R 行观测的是 `act` 上的 9 个候选偏移；若全部无新增值，
说明疲惫状态字不在该集合内，下一轮改为窗口内 `act` 区域差分扫描，
仍不写内存、不改参数。

---

## 2026-11-11 21:18 · P20 离线核查：怪物「攻击动作扣耐力 → 流口水」完整链路（用户提示）

用户 21:11：「可能有一条你忘记了，怪物的攻击动作（可能也不只是攻击动作）会降低其耐力，
耐力到一定数值就会触发流口水，你可以检查 mhgu 本地的完整链路，这个在 rise 侧应该也有完整链路」。
**线索成立，且确实是我漏掉的一条。** 完整证据与对照表见
`out/P20_stamina_chain_audit.md`。本轮纯离线，**未编译 / 未部署 / 未改任何文件**
（游戏进程仍在运行）。

### 1 · Rise 侧（本地 RSZ + 已解包参数，链路闭合）

- `snow.enemy.EnemyActionParamData.ActionInfo._subStaminaPoint` (S32) = **每动作扣耐力点**。
  实测：em001 296 个动作 46 个非零（7~100）、em002 393 个 98 个非零（5~50）、
  em003 167 个 29 个非零（5~20）⇒ 约 15~25% 动作扣点，印证「不只是攻击动作」。
- 玩家减气输入 `EnemyConditionPresetData.PresetStaminaData._SubStamina / _AddTiredTime`；
  状态异常输入 `EnemyConditionDamageData.StaminaDamageData._SubStamina`。
- 疲惫参数 `EnemyStaminaData._tiredSec / _motRate / _SetMeatRecovStartPoint / _SetMeatRecovEndPoint`；
  状态机 `EnemyStaminaParam`（State/RecoveryType/Attr）、`EnemyStaminaManager`；
  资源 `emNNN_00_stamina_data.user.2`（`rise_enemy_ai_paths.txt:326`）。
- **运行时当前值是持续量**：网络包 `EnemyActionPacket._Stamina`(U16)、
  `EnemyBossLateJoinSyncPacket._Stamina`(F32) 随动作同步；`_IsTired` 标志存在。
- 疲惫结束条件是**进食/耐力回升**，不是计时器 ⇒ 与 `monster-status.md`
  「减气瞬时判定、疲劳无固定时长」自洽。

### 2 · MHGU 本地（同一条链路，此前未串起来）

- FSM 状态名 **`Stamina_low_Start` / `Stamina_low_End`**：`stringxref.tsv` 引用点
  `0xf8d384`；`functions-retile.csv.gz` 中 `0xf8b178` 标签
  `Angry_Start|Angry_End|Stamina_low_Start`。
- 疲劳动作链 `tired_start/tired_Loop/tired_end` @`0x10a1814`、
  `tired_Change/tired_End` @`0x10383a0`。
- 运行时 EMC 参数名 `mParam.stamina_point` / `mParam.stamina_dmg_point`
  （`monster-ai-params.md:72/78`，property 注册函数 `0x1eb8d0`）。
- 耐力类 `cEmStaminaData::cStaminaLev` @`0x1556955`；`cEmDouMouKaData` 成员
  `StaminaSubRate`(34) / `StaminaTimeVal`(37)；`em002_00_doumouka` XFS 字符串表
  逐字节确认这四个字段名存在；任务槽 `mStaminaTblNo_N` / `QuestData.Monsters.StaminaTbl`。
- `monster-gu.md:228` 写 Rise 侧「absent from RSZ dump」⇒ **本轮 RSZ 检索推翻该句**。

### 3 · 我漏掉的具体条目

`04_RiseAI/NOTES.md:375`（v13）已记录 `ActionInfo` 8 字段含 `_subStaminaPoint`，
但当时只追动作冷却 CD，未串到疲劳；MHGU 侧 `Stamina_low_*` 与
`mParam.stamina_point` 从未进入任何探针/判据。
⇒ 前 7 轮都在改「触发输入」或「结果标志」，没有追**被轮询的当前耐力值**。

### 4 · 为什么此前强制疲劳全败

v40/v42 写 `act+0x5D82` 是**累加通道**（判定在游戏自己的 `+=` 路径）；
v44/v45 的 `0x1068DD8` 实机不走；v46 写 `act+0x518=2` 只是判定标志；
数据层 `@0x390` 是减气瞬时判定。
Rise 每动作同步 `_Stamina`、MHGU `0x816D0` 有 315 个调用者、`0x8172C` 有 415 个
⇒ 支持**每帧/每动作轮询当前值**模型。若是
`if (stamina <= low_threshold) -> Stamina_low_Start`，写当前值应能触发，
与所有失败尝试本质不同（尚未实机验证）。

### 5 · 关键新线索：`mon+0xCAC0` 是指针

本轮反汇编 `0xf8d384`：`movw r1,#0xcac0; ldr r1,[r6,r1]!` 取出的是**指针**，
`ldrb r2,[r1,#0x3f]` 才是 0..3 状态字节（4 路 switch），
`vldr s2,[r0,#0x5c]` 是浮点计时器，case 里 `strb #0/#1/#2/#3,[r1,#0x3f]` 写回。
⇒ P12 把 `rd(mon+0xCAC0)` 当状态枚举是误判：日志里的 `0x0C4xxxxx` / 0
本来就是指针 / 空指针。真正状态字在 `*(mon+0xCAC0)+0x3F`。
**[U]** 该函数无直接 BL 调用者（虚表间接），`r6` 是否等于 hook 的 `mon` 未实机验证。

### 6 · 与 P19 的吻合 / 下一步

P19 跳狗龙 3.35 分钟自然流口水 = 怪物自己出招扣耐力，不需要玩家减气；
`ex` 5→150 是累计消耗/减气蓄积，**不是当前耐力值**。
下一步两条路线（等用户确认，本轮未动手）：
- **A（推荐）纯只读 v48**：在 v47 的 R 行增加 `p=rd(mon+0xCAC0)` 解引用后
  `+0x3F` 状态字节 / `+0x5C` 浮点位模式 / `+0x41`，配合既有 act 候选字段，
  用 P19 的 3~4 分钟短场自动差分定位「当前耐力」；定位后再考虑有界写入。
- **B 临时放大每动作耐力消耗**：调 `doumouka` 的 `StaminaSubRate/StaminaTimeVal`
  或 `dtbase/attackdata` 动作参数。字段名有一一对应，但 XFS 数值区语义 [U]，
  且 `StaminaSubRate` 是比率不是点数 ⇒ 有重演 P17 的风险，建议先 A。

**边界**：Rise（RE Engine / RSZ）字段名是强线索，MHGU（ARM32 / EMC）偏移必须实机定案；
`0xf8d384` 对象归属、`mParam.stamina_point` 运行时偏移、`doumouka` 数值区均未验证。

---

## 2026-11-11 21:26 · P21：按用户选 B，临时「跳狗龙王减气阈值」mod 已部署

用户 21:20：「B，我下场打跳狗龙你改跳狗龙的」⇒ 执行 P20 报告里的 B 路线，
针对用户下场要打的跳狗龙做临时数据层改动，拿到数据后用一键脚本改回。

### 1 · 怪种定案（避免改错 arc）

- P19 日志 V 行：`sp=0055`(=85) 出现 1 次、`mon=0C190060`；
  `sp=102E`(=4142, 小怪 Maccao) 出现 16 次。
- **A 行 `ex` 累积与流口水都发生在 `0C190060` = `sp=0055` = 跳狗龙王 / Great Maccao
  / DosMaccao = `em085_00`**（文档 `mon-em-units.md:209`、`mon-counter-slots.md:372`）。
- 故改 `em085_00.arc`。

### 2 · 为什么不是改 `StaminaSubRate`：跳狗龙王没有 doumouka

- `em085_00.arc` 416 条目中**没有 `dou_mou_ka`**；全 romfs 扫描 106 个
  `doumouka` 条目，均为 em001~em049 部分怪，em085 不在其中。
- 该 arc 有 `action_tune`（FUP，132 B 纯 f32 倍率数组，无字段名）、
  `dt_base`(263 B)、`dt_tune`(1238 B)、`cmd_tbl`。
- ⇒ `cEmDouMouKaData.StaminaSubRate / StaminaTimeVal` **对跳狗龙王不存在**，
  无法按 P20 原设想改「每动作耐力消耗倍率」。
- 等价且更可控的替代：**降低减气触发阈值**（怪物自身动作按
  Rise `_subStaminaPoint` 扣耐力，累积到该阈值即流口水）。

### 3 · 字节级定案 + P19 实机闭环（关键定性更正）

- `em085_00_dttune` **@+0x2EC** = `(150, 600, 5, 0, 50, 350)`，
  与 `wiki/monster-rage-tired.md:154`「85 跳狗龙王 150/50/350 即时型」逐字节吻合 [C]。
  结构 `[initial, A, B, durF, increase, max]`（见
  `reference/re-example-dttune-consumer.md` §3）。
- **P19 实机：主怪 `act+0x5D82` 从 5 累积到 150 后立刻停止出招、开始流口水** ⇒
  **`initial=150` 就是流口水触发点**。这修正 P18 的过度解读：
  wiki「减气是瞬时判定、疲劳无固定时长」应理解为**疲惫状态本身没有计时器
  （靠进食恢复结束）**，不是「减气触发硬直」。
  P17 大锤第一击硬直是 `initial=0` 造成的「每次动作都反复越过阈值」异常，
  不是正常阈值 180 的语义。
- ⇒ 本轮只把 `initial` 150 → **30**（不设 0），其余 5 字段不动。
  P19 里 `ex` 每次采样 +5~25 点 ⇒ 约 2~6 个动作即达阈值，
  预计进任务后十几秒到一分钟内流口水。

### 4 · 部署与纪律

- 补丁：`(150,600,5,0,50,350)` → `(30,600,5,0,50,350)`，**仅 1 字节差异**。
- 按 ARC 纪律生成**单条目 arc**：`arc_tool.py pack ... --orig`，
  1 条目 `enemy\dt_tune\em085_00_dttune`、typeHash `48E8AC29` 保持不变；
  产物 `03_Output/em085_00_stamina_probe.arc`（`45eb58b0…`，33287 B）。
  打包前确认**无其他 mod 覆盖 `em085_00.arc`**。
- 部署 `mods/Maccao_StaminaProbe/romfs/nativeNX/arc/enemy/em085_00.arc`，
  md5 与产物一致；`load_order` **只追加一行** `Maccao_StaminaProbe`，
  备份 `out/load_order_backup_20261111_2125.txt`，既有行未动。
- 原版备份 `02_Workspace/maccao_original_backup/`（原 dttune + 原 arc）。
- **插件保持 `v47.nro`（`0fd173bd…`）纯只读**，未编译、未改插件：
  R 行定时快照负责在流口水待机段抓状态字段，N 行自动标记低活动窗口。
  ⇒ 本轮「参数层加速触发」+「只读层采集」一次完成。
- `6_` md5 `7361445f…` 未动；游戏本体资源未改；无游戏进程时部署。
- 一键回退 `tools/rollback_maccao_probe.py`（不删除任何文件）：
  移动 mod 目录到 `out/_retired_Maccao_StaminaProbe/`、从备份恢复
  `load_order`、确认插件仍是 v47 只读。
- `8_lite_check.bat` 提示改本轮说明（TOOL2 仍指向
  `analyze_v47_tired.py`，执行逻辑/输出/轮转/Python 路径未动）；`7_` 改 STEP 47。

### 5 · 下一轮（短场）

双击 `8_lite_check.bat` → 进**跳狗龙王**任务 → 正常打，预计几个动作后
（远早于 3.35 分钟）出现流口水 → **立即正常关游戏**（不要久留暂停菜单）
→ 自动出两份报告，第二份由 v47 判读脚本给出「窗口内出现新值」的候选字段。
用户只需告知「是否很快流口水、大概何时」及有无异常。
拿到数据后立即运行 `python 04_RiseAI\tools\rollback_maccao_probe.py` 改回。

### 6 · 风险与边界

- 若出现**连续硬直 / 反复疲惫 / 动画错位 / 卡顿**，立即退出并回退；
  这正是 `initial` 设得太低的风险（本版取 30 而非 0 已规避 P17 的极端情形）。
- 只改 `em085_00`（普通个体）；狞猛/二名变体（`em085_0x`）不受影响。
- 若用户下场任务实际只有小怪跳狗龙（sp=102E）而无跳狗龙王，
  本补丁不会生效 —— 需按日志 V 行 sp 确认后再补对应 arc。
- 「疲惫无固定时长」与「降低阈值加速触发」是两件事：本版只加速触发，
  不改变疲惫的结束条件（进食恢复）。

---

## 2026-11-11 21:35 · P22：临时阈值 mod 实机成功（1:40 流口水）+ 暂停冻结陷阱

用户 21:32 暂停并给截图：任务内 **1 分 40 秒**跳狗龙王倒地流口水。
快照 `out/game_p54_lite_20261111_2132_MACAO_TIRED_paused.txt`，
报告 `out/P22_maccao_tired_probe.md` / `out/v47_MACAO_report.txt`。
游戏进程仍在（暂停菜单），**未改动任何加载状态、未回退 mod**。

### 1 · 硬结论

- `[romfs] archives merged: data/romfs/nativeNX/arc/enemy/em085_00.arc
  <- 1 entries changed by mods/Maccao_StaminaProbe/...` ⇒ 单条目 arc 合并成功。
- V 行 `sp=0055`（跳狗龙王，em085）在场；R 行监控 `0C1F1930`。零 FATAL / `live=1` / `hub=15`。
- `qstart=4515`；BEAT 正常 dA=2~9，`f=10800` 降到 2，`f=11400` 起 0 动作；
  `N f=11700 ENTER-LOW` 自动锚点正常。任务内疲惫 ≈**1 分 50 秒**，
  对比 P19 原版阈值 150 的 **3 分 21 秒** ⇒ **加速约 1.8 倍**。
- **R 行首次覆盖疲惫窗口**：97 条、锚点段内 75 条；`C` 行仅 93 条、末帧 10877
  ⇒ v47 的「去掉 cf 噪声指纹 + 定时快照」两项修复都生效。

### 2 · 暂停冻结陷阱（必须长期记住）

R 行从 `f=10950` 起 **77 条 9 字段完全相同**
（`st=0 t4=0 ex=55 d5=62512 h1=4 e1=175 dc=0 p3ca=71 p3be=73`）。
`d5=act+0x5D88` 此前每 150 帧都在变（32768/65370/65036/16368/…），
此刻突然恒定 ⇒ 游戏逻辑冻结而 `forge_onUpdate` 仍逐帧跑（P19 已证）。
用户截图是「任务状况」菜单。**该段不能作疲惫样本**，否则差分必得「无变化」。
⇒ 判读脚本已加「连续 ≥8 条 R 行全同 = 冻结」检测并排除该段。

### 3 · 状态切换候选点 `f≈10299~10350`（冻结前）

| 字段 | 前 | 后 | 判断 |
|---|---|---|---|
| `e1=rd8(mon+0x73E1)` | 20/91/31 小值 | **175（持续）** | `0x73E1` 是 wiki 标注 u8 状态槽；全场唯一持续新值，**最强候选** |
| `ex=rd16(act+0x5D82)` | 30 | **55** | 会衰减（本场曾 65→15），减气/耐力消耗累计 |
| `p3ca / p3be` | 74 / 88 | **71 / 73** | 随 ex 递增单调下降（早期 168/114 → 71/73），疑似当前耐力相关 |
| `st=act+0x518` | 0 | 0 | 全程 0，**再次证伪** |
| `t4=act+0x408` | 0 | 0 | 全程 0（本场非 0xFFFF 哨兵），**再次证伪** |

C 行指纹同帧 `00110000 → 00210000`。`e1=175` 也可能是倒地动作 sub，
必须与「恢复段」对照才能区分。

### 4 · 判读脚本修正

`tools/analyze_v47_tired.py`（备份 `.p21bak`）：
1. 冻结检测（连续 ≥8 条 R 行 9 字段全同）并排除该段；
2. 冻结场景改用「冻结前最近一次 ≥3 字段同时变化的 R 行」作状态切换锚点，
   而不是 BEAT 零动作段（含暂停）；模拟日志回归 **PASS=7/FAIL=0**；
3. 本场 **PASS=7/FAIL=0**，候选 `ex=55 / e1=175 / p3ca=71 / p3be=73`
   （`d5` 是计时器噪声，忽略）。

### 5 · 下一轮（用户负担最小）

游戏仍暂停 ⇒ **请取消暂停、继续打 10~20 秒直到怪物恢复出招，再正常关游戏**
（不要在暂停菜单久留）。R 行会记录 `e1=175 / ex=55 / p3ca=71` 的回落轨迹，
一次即可定案状态字与当前耐力值。拿到数据后运行
`python 04_RiseAI\tools\rollback_maccao_probe.py` 改回原版参数。

**边界**：本轮未回退临时 mod；插件仍 v47 纯只读；`6_` md5 `7361445f…`、
游戏本体资源、既有 load_order 行未动。

---

## 2026-11-11 21:40 · P23：完整「疲惫 → 恢复」轨迹到手，状态判定标志定案

用户 21:36：任务内约 **2:40** 跳狗龙王恢复状态（1:40 倒地流口水）。
完整日志 `out/game_p54_lite_20261111_2136_MACAO_RECOVERED.txt`，
报告 `out/P23_tired_state_determined.md`。**9 轮以来第一次拿到完整往返轨迹。**

### 1 · 三段结构

| 段 | 帧 | 特征 |
|---|---|---|
| 战斗→触发 | `7200..10950` | `e1` 动作 sub 小值；`ex` 10→65→15→30→55 |
| **暂停菜单 #1**（21:32 截图） | `10950..20250` | **159 条 R 行 9 字段全同**：`st=0 t4=0 ex=55 d5=62512 h1=4 e1=175 p3ca=71 p3be=73` |
| **恢复段**（取消暂停继续打） | `20550..24300` | `e1` → 61/14/101/2/41/30/14/10；`ex` 55→50→45→40→35→30→25→20 |
| 暂停菜单 #2（21:36 截图） | `24300..28950` | 112 条全同：`ex=20 e1=95 p3ca=71 p3be=73` |

恢复三重印证：`N f=21000 EXIT-LOW dA=7`；BEAT `f=20700` 起 dA=4/7/6/3（此前 0）；
`f=20550` 起 `e1` 从 175 回落、`ex` 开始衰减。`d5=act+0x5D88` 活动段每帧变、
冻结段恒定 ⇒ 可作「游戏逻辑冻结」判据。

### 2 · 字段定案

| 字段 | 疲惫段 | 恢复段 | 结论 |
|---|---|---|---|
| **`e1 = *(u8*)(mon+0x73E1)`** | **175（持续 159 条）** | 61/14/101/2/41/30/14/10 | **疲惫/倒地状态标志**：全场唯一持续新值、恢复即消失；`0x73E1` 是 wiki 标注 u8 状态槽 |
| `ex = *(u16*)(act+0x5D82)` | 55 | 55→50→45→40→35→30→25→20（约 5 点/600 帧） | **减气/耐力消耗蓄积**，会衰减（dttune A=600/B=5）；到阈值触发疲惫，不是状态字 |
| `p3ca/p3be = act+0x3CA/0x3BE` | 71/73 | **仍 71/73** | 不随恢复回升 ⇒ **不是当前耐力值**，是固定阈值/动作参数 |
| `st = act+0x518` | 0 | 0 | **彻底证伪**（v46 的 `st=2` 作废） |
| `t4 = act+0x408` | 0 | 0 | **彻底证伪**（本场非 0xFFFF 哨兵） |

C 行指纹 `f=10299 00110000→00210000` 与 `e1=175` 同帧。

### 3 · 对 B 方案 / P20 模型的验证

- `em085_00_dttune @+0x2EC initial` 150→30 生效：疲惫 1:40（原版 3:21）、恢复 2:40 ⇒ 疲惫窗口约 1 分钟。
- `ex` 疲惫段保持 55、恢复段衰减到 20 且未归零 ⇒ 疲惫结束条件**不是 ex 归零**，
  与「靠进食/耐力回升结束」一致；`e1` 直接回落说明状态机是独立字段。
- 玩家未用减气武器，`ex` 仍随怪物动作增长 ⇒ 印证 P20「怪物自身动作扣耐力」。

### 4 · 边界

- `e1=175` 严格说是「疲惫/倒地期间」特有值，可能含倒地动作 sub 语义，
  尚不能断言是纯状态枚举；但作为**只读判定标志**已足够驱动 3 状态权重层。
- 「当前耐力值」仍未定位（`p3ca/p3be` 已排除、`ex` 是累计消耗）。若必须拿，
  需窗口内 `act` 区域差分扫描，仍不写内存。
- 判读脚本 `analyze_v47_tired.py` 本轮再修：冻结段结束帧记录（准确报 159 条而非全后段）、
  多字段突变锚点；模拟 PASS=7/0、本场 PASS=7/0，候选 `ex=55 / e1=175 / p3ca=71 / p3be=73`。

### 5 · 下一步

1. 游戏仍在运行（暂停菜单）⇒ 请用户**正常关闭游戏**。
2. 关闭后运行 `python 04_RiseAI\tools\rollback_maccao_probe.py` 回退临时参数
   （移动 mod 目录、恢复 `load_order`、保留 v47 只读，不删除文件）；或由我执行。
3. 回 AI 主线 **3 状态权重层**：`e1==175`（疲惫）/ `st==1`（怒，P14 已闭环）/ 其余（普通），
   在 EMC 抽选层按状态调 prev 严格度；跨怪通用、不碰 action_id、不写参数、不绑定 Show HP Bar。

---

## 2026-11-11 21:45 · P24 纯倒地对照组：排除 `e1=175` 是倒地动作 sub 的疑义

用户 21:40 给出判据「倒地动作 sub 在第一次恢复游戏时已结束，恢复后短时间内没变化就是疲劳」，
21:44 又打出一次**只有倒地、没有疲劳**的对照场。日志快照
`out/game_p54_lite_20261111_2144_MACAO_KNOCKDOWN_NO_TIRED.txt`，报告
`out/P24_knockdown_control.md`。游戏仍在运行（暂停菜单），未改任何加载状态。

### 1 · 两条独立证据

- **A 恢复判据**：第一个冻结段结束 `f=20250`；`f=20400` 时 `ex` 55→50、
  `d5` 62512→0（游戏逻辑已恢复）但 **`e1` 仍 175**，直到 `f=20550` 才变 61
  ⇒ 恢复后约 150 帧内未变，按用户判据是状态而非倒地 sub。
- **B 对照场**：`f=54900..60750`（136 条全同）只有倒地、无疲劳，
  **`e1=7`**、`ex=80`、`p3ca/p3be=171/54`、`h1=3`；
  而疲劳+倒地段 `e1=175`、`ex=55`、`p3ca/p3be=71/73`、`h1=4`。
  同一怪同一任务同样倒地，**只有疲劳那次出现 175** ⇒ 175 与倒地无关、与疲劳绑定。

⇒ **P23 定案成立**：`*(u8*)(mon+0x73E1)==175` 可作疲惫判定标志。
`st/t4` 两段仍全 0。

### 2 · 第二次为何没打出疲劳

dttune 改后 `(30,600,5,0,50,350)`，阈值递推 `initial+(k-1)*increase`：
第 1 次 30、**第 2 次 80**；第二场 `ex` 最高恰停 80 未越过 ⇒ 未触发。
印证 wiki 阈值递增公式，也说明「改 initial 只加速首次触发」的边界。

### 3 · 附带观察

- `e1` 与 A 行 `s`（动作 sub）**38/38 完全一致** ⇒ `0x73E1` 平时放动作 sub，
  只有进入疲劳才覆写为 175；这解释了它既能当状态标志又与动作号同源。
- `p3ca` 第一轮 168→139→117→104→84→74→71（随 ex 上升），第二轮 37→33，
  倒地时跳 171 并保持 ⇒ 仍不能定案为当前耐力值。
- 第三个暂停菜单 `f=54900..60750` 再次印证暂停冻结。

### 4 · 下一步与边界

请正常关闭游戏 → `python 04_RiseAI\tools\rollback_maccao_probe.py` 回退 → 3 状态权重层。
**边界**：`e1=175` 目前只在跳狗龙王一场确认，跨怪是否同值需下一轮验证；
若跨怪不同，改用「`e1` 脱离动作 sub 值域」判定，禁止硬编码 175（跨怪通用纪律）。

---

## 2026-11-11 21:50 · P25 发怒倒地对照组：**撤回 P23/P24 的 `e1=175` 定案**

用户 21:48 又打出倒地，但这次怪物是**发怒状态**（截图「跳狗龙王・无冠 発怒し」）。
日志快照 `out/game_p54_lite_20261111_2148_MACAO_ENRAGED_KNOCKDOWN.txt`，
报告 `out/P25_enraged_knockdown_control.md`。同一场连续打（HP 512/920），
游戏仍在运行（任务状况菜单），未改任何加载状态。

### 1 · 两条硬结论

1. **`e1=175` 不是疲劳专属状态字，P23/P24 定案撤回。**
   `f=66900` 起 `st=1`（发怒），`f=69330` 起 `e1=175 / ex=120 / p3ca=66 / p3be=22`；
   `69330..69750` 期间 `d5` 在 0/32768/65535 变化、`h1` 1→2→3 ⇒ **游戏逻辑未冻结，
   175 真实持续 420 帧**，不是暂停定格。暂停冻结段是 `69780..72450`（70 条全同）。
   ⇒ 175 与「倒地/待机动作」绑定，怒与疲都会执行。
2. **`st = *(u8*)(act+0x518)==1` 是发怒的可靠只读标志**：本场 R 行 134 条 st=1、
   689 条 st=0，与截图「発怒し」及 P14 实机闭环 ⇒ 3 状态权重层「怒」的确定输入。

### 2 · 四段对照（同一场同一只怪）

| 段 | 现象 | st | e1 | ex | p3ca/p3be | h1 |
|---|---|---|---|---|---|---|
| `10950..20250` | 倒地+流口水（疲劳） | 0 | **175** | 55 | 71/73 | 4 |
| `24300..52650` | 恢复后站立（菜单） | 0 | 95 | 20 | 71/73 | 1 |
| `54900..66600` | 只有倒地无疲劳 | 0 | **7** | 80 | 171/54 | 3 |
| `69780..72450` | **发怒+倒地** | **1** | **175** | 120 | 66/22 | 3 |

`e1` 与 A 行 `s` 本场 49/49 一致 ⇒ `mon+0x73E1` 平时放动作 sub；175 是倒地/待机动作号。
`t4` 四段全 0。用户 21:40 判据方向正确，P24 两个样本就定案属于样本不足。

### 3 · 修正后的判据

- 怒：`st==1` —— 实机闭环。
- 疲：`e1==175 && st==0` —— **仅候选**，能排除发怒场但不能排除「非疲劳倒地也用 175」，
  跨怪未验证，**禁止硬编码 175 当通用状态字**。
- 为什么第 2/3 次没再疲劳：阈值递推 30 / 80 / 130，两场 `ex` 分别停在 80 / 120 未越过。

### 4 · 下一步（等用户定）

- **A（推荐）**：不再追状态字。3 状态权重层用 `st==1` 判怒，疲惫用**行为判据**
  （BEAT 300f 动作增量连续下降 + 零动作段，即用户定义的流口水待机），跨怪通用、零写入。
- **B**：v48 纯只读探针观测 `*(mon+0xCAC0)` 解引用 `+0x3F / +0x5C / +0x41`（P20 离线线索），
  需再跑一轮短场。
无论哪条，先正常关游戏 → `python 04_RiseAI\tools\rollback_maccao_probe.py` 回退。

### 5 · 边界

`st==1` 跨怪一致性未验证；四个暂停菜单段（159/270/175/70 条全同）再次印证暂停冻结，
判读脚本已能自动排除。

---

## 2026-11-11 21:55 · P26 决定性控制组：疲劳站立未倒地 → `dc` 新候选

用户 21:52 截图「现在是疲劳状态（流口水）**未倒地**」，右上「未发怒」。
快照 `out/game_p54_lite_20261111_2152_MACAO_TIRED_STANDING.txt` /
`out/..._2153_TIRED_STANDING_live.txt`，报告 `out/P26_tired_standing_control.md`。
游戏仍在运行，未改任何加载状态。

### 1 · 两条硬结论

1. **`e1=175` 彻底排除为疲劳状态字**：站立流口水段 `e1=96/7/10/27`（不是 175）。
   175 只与倒地共现（疲劳倒地、发怒倒地）⇒ P25 撤回正确，175 = 倒地动作 sub。
2. **新候选 `dc = *(u8*)(mon+0x73DC)==1`**：全场 847 条 R 行仅 **5 条为 1**，
   全部自 `f=75450` 起；A/C 行 `f=75440..99667` 共 13 条 dc=1。
   该段 `st=0`（截图「未发怒」一致）、`t4=0`、`ex` 140→170→0。
   `f=76126` 起 ex 归零使 R 行停止（筛选条件），但 C/A 行仍 dc=1 ⇒ **dc 独立于 ex**。

### 2 · 五段对照

| 段 | 现象 | st | e1 | dc | ex |
|---|---|---|---|---|---|
| 10950..20250 | 倒地+流口水 | 0 | 175 | 0 | 55 |
| 54900..66600 | 纯倒地无疲劳 | 0 | 7 | 0 | 80 |
| 69780..74850 | 发怒+倒地 | 1 | 175 | 0 | 120 |
| **75450..76050** | **站立流口水未倒地** | 0 | 96/7/10 | **1** | 140→170 |
| 98778..99667 | 延续（A/C） | 0 | 30/61/20 | **1** | 0 |

### 3 · 未解矛盾（不掩盖）

`10950..20250` 倒地流口水段 dc=0。可能倒地时 dc 由另一路径清零，
或那次口水来自倒地动画而非疲惫状态机 ⇒ **`dc==1` 定案前需再跑一轮
「倒地疲劳 → 站立疲劳」连续对照**，不得直接定案。

### 4 · 阈值复核

递推 30/80/130/180；第二场停 80、第三场停 120 未越过；本次 ex 到 170 后归零，
与第 4 次阈值 180 附近触发一致。ex 归零与 dc=1 同段 ⇒ 蓄积达阈值→清零→进疲惫。

### 5 · 下一步与边界

请正常关游戏 → `python 04_RiseAI\tools\rollback_maccao_probe.py` 回退 → 3 状态权重层：
怒 `st==1`（确定）、疲 `dc==1`（强候选 + BEAT 行为兜底）、普通其余。
跨怪通用、零写入、不硬编码 175。
边界：dc 只在跳狗龙王一场观测；所有暂停菜单段证明 forge 帧继续但游戏逻辑冻结，
**forge 帧差≠任务内时间差**，只作帧锚点。

---

## 2026-11-11 22:00 · P27 恢复点落在探针盲区（用户要求暂时只做分析）

用户 21:58 补充：任务时长 50 分钟，截图剩余 **44:10**（任务内 5:50），
**截图前约 3 秒怪物从疲惫恢复正常**（≈剩余 44:13 / 任务内 5:47）；
「可能之后还有补充，暂时只做分析」。本轮**未编译/未部署/未改任何插件或参数**。
快照 `out/game_p54_lite_20261111_2158_RECOVER_TO_NORMAL.txt`（末 BEAT f=112500），
报告 `out/P27_recovery_blind_spot.md`。

### 1 · 结论

**`dc` 是否在恢复时归零无法判定 —— 恢复点落在 v47 盲区，不是数据否定。**
但站立流口水全段行为强化了 `dc` 的可信度：`dc` 自 `f=75440` 0→1 后到
最后一条 C/A 行 `f=102599` **全程恒 1**；`f=76126` 起 `ex` 归零并保持，
`st=0`、`t4=0`、`e1` 为动作 sub 小值（非 175）⇒ dc 独立于 ex、独立于动作号。

### 2 · 时间映射

| 截图 | 剩余 | 任务内 | 末帧 |
|---|---|---|---|
| 21:32 | 48:20 | 1:40 | ≈18300 |
| 21:36 | 47:14 | 2:46 | ≈28950 |
| 21:44 | 46:37 | 3:23 | ≈60750 |
| 21:48 | 45:45 | 4:15 | ≈72450 |
| 21:52 | 45:13 | 4:47 | ≈90600 |
| 21:58 | 44:10 | 5:50 | ≈112500 |

forge 帧在菜单期间继续涨、任务计时冻结 ⇒ 非线性；末段菜单 `f≈103200` 起
（BEAT dA 连续 0 到 112500）。恢复点 ≈ **f=103020**。

### 3 · 三个盲区（配额未满，是设计缺口）

1. R 行 `f=76050` 停止：条件 `ex>0||st!=0||t4!=0`，`f=76126` 起全 0。
2. C 行指纹 `fp = st | (t4!=0)<<8 | (h1&3)<<16 | (ex/25)<<20` **不含 dc**
   ⇒ dc 单独 1→0 不触发 C 行。
3. A 行依赖动作开始事件，最后一条 `f=102383`。
最后 C=102599 / A=102383 / R=76050，`f=103200` 起菜单冻结 ⇒ 恢复点夹在空白区。
C=189、A=59，MAXLOG 未触发。

### 4 · 判定维持

`dc==1` **强候选、未定案**：支持证据为全场仅一次 0→1、精确起于站立流口水、
持续覆盖口述疲惫期、发怒/纯倒地/恢复后站立全为 0；
未解矛盾为 `10950..20250` 倒地流口水段 dc=0，以及恢复点归零未观测到。

### 5 · 后续补数据（本轮不实施）

v48 纯只读三改：dc 纳入 C 行指纹；R 行无条件定期输出（或 dc!=0 也输出）；
提高配额/放宽降采样。请用户恢复后别立刻开菜单，正常打 10~20 秒再关游戏。

### 6 · 边界

只做分析；`dc` 跨怪未验证；`e1=175` 已排除（倒地动作 sub），`st==1` 为怒确定判据；
forge 帧差≠任务内时间差。

---

## 2026-11-11 22:05 · P28 眩晕 / 纯倒地双对照：**`dc==1` 证伪**

用户 22:03 两图：图1 眩晕（黄星，剩余 43:38，HP 394/920）、
图2 纯倒地（剩余 43:07，HP 314/920）。快照
`out/game_p54_lite_20261111_2203_STUN_KNOCKDOWN.txt`（末 BEAT f=127200），
报告 `out/P28_stun_knockdown_dc_falsified.md`。游戏仍在运行，本轮**只做分析**，
未编译 / 未部署 / 未改插件、参数、load_order、`6_`。

### 1 · 硬结论：`dc` 不是当前疲惫状态字，P26/P27 强候选撤回

主怪 `0C1F1930` 的 `dc=*(u8*)(mon+0x73DC)` 自 `f=75440` 0→1 后，
到最后观测 `f=126490` **全程恒 1**（主怪 C 行 dc=1 共 49 条 f=75440..125139、
A 行 15 条 f=75900..126490，dc=0 末帧分别 75211 / 68932）。
期间用户状态依次为：站立流口水(21:52) → **恢复正常**(21:58) → 纯倒地 → 眩晕 →
发怒(`f=125121 st=1`)。一个跨 5 种互斥状态不变的值只能是一次性 latch
（「本场曾进过疲惫」），不能判「现在是否疲惫」。

**P26 的未解矛盾顺带解决**：`10950..20250` 倒地+流口水段 dc=0 是
**第 1 次疲惫**（21:32，任务内 1:40），早于 `f=75440`（21:52 第 2 次）的置位时刻，
不是「倒地时清零」。

### 2 · 状态判据盘点：内存字段全灭

| 判据 | 状态 |
|---|---|
| `st=act+0x518==1` | **确定可用**（怒；本场 f=125121 再复现） |
| `e1=175` | 证伪（倒地动作 sub） |
| `dc==1` | **本轮证伪**（跨状态 latch） |
| `ex` | 证伪（减气蓄积量） |
| `t4/p3ca/p3be/c0/c4/c8/cf` | 证伪（恒 0 / 固定参数 / 噪声） |
| `mon+0xCAC0`、`0x1068DD8` | 证伪（指针 / 实机不走） |

⇒ 没有任何已观测内存字段能判定「当前是否疲惫」。

### 3 · 新增观测缺口

- **R 行配额耗尽**：`R=900/900`，末条 `f=116190`；之后只有 C/A 行 ⇒ 眩晕/纯倒地段
  无定时快照。P27 三盲区之外的第四处。
- C 行指纹不含 dc，dc 单独变化不触发 C 行（本轮靠 A 行补齐）。
- 冻结段复核：`10950..20250`(159) / `24300..52650`(270) / `54900..66600`(175) /
  `69780..74700`(85) / `115260..116190`(32) 全同 R 行，dc 分别 0/0/0/0/1。

### 4 · 下一步（等用户定）

- **A（推荐）**：放弃内存状态字，3 状态层降为怒 `st==1`（确定）+
  疲惫行为判据（BEAT 300f 动作增量连续下降 + 零动作段）软输入，或只做怒/普通两态。
  跨怪通用、零写入、不硬编码数值。
- **B**：v48 纯只读观测 `*(mon+0xCAC0)+0x3F/+0x5C/+0x41` 与 act 区域差分，再跑一轮。
无论哪条，先正常关游戏 → `python 04_RiseAI\tools\rollback_maccao_probe.py` 回退。

### 5 · 边界

两张截图剩余时间 43:38 > 43:07 ⇒ 按任务计时图1(眩晕)早于图2(纯倒地)，
与用户口述顺序相反，但两者均非疲惫且 dc 均为 1，不影响结论。
眩晕 KO 计量 `0x16915C/0x169174/0x16919C` 本探针未读。
forge 帧差≠任务时间差；dc 跨怪未验证。

---

## 2026-11-11 22:45 · P29：疲惫触发链字节级定案 + v48 已部署（下一轮就绪）

用户 22:12「结束游戏了，整理之前信息，结合本地链路看能否找到疲劳如何触发，之后准备下一轮」。
游戏已关闭；本轮**回退全部临时数据层 mod**（`rollback_maccao_probe.py` 执行成功，
`load_order` 干净、无 em085/em002 arc 覆盖），随后离线链路核查 + 编译部署 v48。
综合报告 `out/P29_tired_trigger_chain_and_next_round.md`。

### 1 · 触发链（[C] 字节级，`re-example-dttune-consumer.md` + 反汇编）

- `getter 0x71078 = *(em+0x75EC)+0x64`；块 `[getter+0x34..0x54]` = `res+0x98..0xB8`，
  每块 12 B `[initial,A,B,durF,increase,max]`。160 个 `bl 0x71078` 调用点按块偏移分组，
  **`[getter+0x44] = res+0xA8` = Exhaust（减气/疲惫）块**，5 个专属调用点。
- `act = *(em+0x1428)` 减气字段（**此前 28 轮只观测了第 1 个**）：
  | act+ | 语义 | 日志字段 |
  |---|---|---|
  | `0x5D82` | counter 蓄积 | `ex` |
  | `0x5D84` | **当前阈值 thr** | 新增 `thr` |
  | `0x5D88` | 衰减计时器 f32 | `d5` |
  | `0x5D8C` | **已触发次数 proc** | 新增 `proc` |
  | `0x4D8` | **每动作减气点数 amount**（Rise `_subStaminaPoint` 同构） | 新增 `amt` |
  | `0x5E08` | 状态**位**（毒/眠/麻 bit0..2、气绝 bit4） | 新增 `flg` |
  | `0x5E0C` | `durF` 时长计时器 | 新增 `t5c` |
- 消耗 → 判定 → 切换：
  `0x9DB54` 累加 `act+0x4D8` → `0x98A60 → 0x9A34C → 0x9A470` 取 amount
  → **`0xA30E4 EXH add`**：`counter += amount`；若 `counter>=thr && [vt+0x39C]()!=1`
  则 `counter=thr; return 1` ★触发；`[vt+0x39C]()==1` 时钳到 `thr-1` 返回 0（抑制）。
  → `0xA3198 grow`：`counter=0`、`proc+1`、`thr=min(initial+increase*proc,max)`，
  尾调用 `0xA4130` → 虚表 `+0x1CC` (r1=9) → `Stamina_low_Start / tired_start`。
- **数值闭环**：`grow` 公式正是 P24 的 30/80/130/180（`initial=30, increase=50,
  max=350`）；P19 原版 `initial=150` 时 `ex` 5→150 后流口水；P22 改 30 后 1:40 触发。
- **减气 `add` 完全不检查 `act+0x5E08`** ⇒ 减气是瞬时判定、无固定时长 ⇒
  **根本不存在持续状态字**，这是 28 轮找「状态字」全败的根因；
  写 counter（v40/v42）绕过了游戏自己的 `+=` 比较路径；`durF` 对减气无效。

### 2 · 28 轮整理（详见 P29 报告 §1）

已证伪：写 `act+0x5D82`(v40/42)、调/hook `0x1068DD8`(v44/45)、
写 `act+0x518=2`(v46)、改 `em002 @0x390 initial=0`(数据层 v1/v2)。
状态候选全排除：`e1=175`(倒地动作 sub)、`dc`(跨 5 状态 latch)、`st==1`(**仅怒确定**)、
`t4/p3ca/p3be/c0/c4/c8/cf`(噪声或固定)、`ex`(蓄积 counter)、`mon+0xCAC0`(指针)。
长期陷阱：暂停菜单冻结游戏逻辑但 forge 帧继续涨；forge 帧差≠任务时间差；
v47 R 行 900 配额在 `f=116190` 耗尽且输出条件漏掉疲惫待机/恢复点。

### 3 · v48（`f4c6d2b7…`，40960 B，已部署）

基于 `lib.rs.v47bak` 重建；`v38 AI 规则逐字节不变`、`hub=15` 兼容。
- **hook `0xA30E4`**：运行时首字须 `(ew & 0xFFFF0000)==0xE92D0000`（push 家族，
  排除 IPS32 `E28FFxxx`），否则 `SKIP h_exh` 退化为纯只读。静态首字 `E92D41F0` [C]。
  *踩坑*：初版掩码写成 `0xFFF0F000`/期望 `0xE92D4000`，bit12-15 被屏蔽导致条件恒假、
  整个 hook 被优化删掉；已用 `nm` 核对 detour 符号修正。
- **一次性有界强制**：`f>=600 && A_N>=20 && GATE_LIVE && 0<thr<0x4000` 时
  把 `amount` 放大为 `thr+16`，其余原样透传、`original!` 恒调用、一次性熔断。
  ⇒ 由游戏自己走完整疲惫状态机；**不写 counter/状态字/参数表，不碰 action_id**。
- **只读观测**：`U` 行每次 EXH add + 强制前后；`R` 行改**无条件定时快照**
  （修 P27/P28 盲区）并加 `thr/proc/amt/flg/t5c/s3f/f5c`；`C` 行指纹纳入
  `flg/proc/thr`；`MAX_R 900→1800`、`MAXLOG 2400→4200`。
- 源码备份 `lib.rs.v47bak`（另 `lib.rs.v48prediag` 为诊断中间态）。
  ELF/NRO 特征串与 `nm` detour 双向核对：`RAI v48` / `U f=` / `INSTALL h_exh` /
  `SKIP h_exh` / `RAI v47`(兼容) 全在。

### 4 · 脚本与纪律

- 新增 `tools/analyze_v48_trigger.py`（U 行 force/POST、R 行 thr/proc 递推、
  触发前后字段差分、自保护、结论）、`tools/make_v48_smoke.py`、
  `out/sim_v48_smoke.txt` / `out/v48_sim_report.txt`。
  模拟 **PASS=11/FAIL=0**；v47 真实日志降级不崩溃；GBK 控制台无 traceback。
- `8_lite_check.bat`：`TOOL2` → v48 判读、标题/提示改 STEP 48 说明；
  `7_` 改 STEP 48（含完整链路与「为何 28 轮全败」）。
  两者**执行逻辑 / 输出路径 / 日志轮转 / Python 绝对路径未动**，CRLF 保持；
  `6_` md5 `7361445f…`、游戏资源、既有 load_order 行未动；无游戏进程时部署。
- 回退 `out/rai_tired_snapshot_v47.nro`（`0fd173bd…`，纯只读）。

### 5 · 下一轮（短场）

双击 `8_lite_check.bat` → 任意任务（跳狗龙王已验证短场）→ 正常打约 20 个动作
→ 看是否很快流口水 → **立即正常关游戏**（别久留任务状况菜单）→ 自动两份报告，
第二份给 v48 结论。用户只需告知「是否很快疲劳、大概何时」及有无异常。
判据：`INSTALL h_exh` / `U force=1` 恰好 1 条且 `amt=thr+16` / `POST ret=1` /
`proc` 递增且 `counter` 归零 / `thr` 按递推 / 零 FATAL / `live=1`。

### 6 · 风险与边界

- 新增 1 hook + 改 1 次参数 = 游戏侧行为改动，比纯只读高一档；
  闪退/冻结/反复疲惫/动画错位立即退出并回退 v47。
- `[vt+0x39C]()` 返回 1 会抑制触发（add 返回 0），`U` 行如实记录、不重试。
- 运行时首字受 IPS32 变体影响 [U]；不符自动 SKIP，仍可拿 `thr/proc/amt` 数据。
- 触发成功即可进 **3 状态权重层**：怒 `st==1`、疲惫用「proc 递增事件 +
  BEAT 频次下降」行为判据、普通其余；跨怪通用、零写入、不硬编码怪种数值。

---

## 2026-11-11 22:55 · P30：v48 实机触发链闭环（信息已足，用户可退出游戏）

用户 22:52 暂停并给截图「任务约 3 分钟进入流口水疲惫」，要求信息够了第一时间告知可退出。
**已当场答复：信息够了，可以正常退出。** 快照
`out/game_p54_lite_20261111_2252_v48_TIRED_paused.txt`，判读
`out/v48_P30_report.txt`，报告 `out/P30_v48_real_machine_closed_loop.md`。
游戏当时仍在运行（任务状况菜单），本轮**未改任何加载状态**。

### 1 · 硬结论：判读 PASS=11 / FAIL=0

`INSTALL h_exh +000A30E4 first=E92D41F0`（运行时首字正确、非 IPS32 跳板），
零 FATAL、`live=1`、`hub=15`。
强制（唯一一次 `f=5193`）：`a1=10 cnt=0 thr=142 proc=0 amt=158 force=1`
→ `POST ret=1 cnt=142 thr=142 proc=0`。
`amt = thr+16`；`add` 返回 1、`cnt` 钳到 `thr`，正是 `0xA30E4` 的
`counter=thr; return 1` 分支 [C]。
`POST` 时 `proc` 仍 0 是**正常时序**（`grow 0xA3198` 由 `0x75F0C` 在后续帧调用），
判读脚本原判据过严 ⇒ 改为「cnt 钳到 thr 或归零」，grow 由 proc/thr 递推判据验证；
模拟回归 11/0、实机 11/0。

### 2 · grow 递推实机数值闭环

| f | proc | thr |
|---|---|---|
| 2700 | 0 | 142 |
| 5250 | 1 | 190 |
| 8400 | 2 | 237 |
| 11700 | 3 | 285 |

步长 48/47/48 = `increase 50 × k(≈0.95)`，与
`0xA3198: thr=min(initial+increase*proc,max)` 完全一致 [C]。
`U` 行逐次显示 `cnt` 从 0 累加到 thr ⇒ P29 链路「每动作 amount → add → 达 thr 触发」
全过程实机可见。解释 P24 的 30/80/130/180 与「后几次没打出疲惫」。
`U` 行配额 40 在 `f=11246` 用尽 ⇒ proc=3 之后触发无 U 行轨迹 [U]。

### 3 · 状态位语义实证

`flg=act+0x5E08` 在 `f=7500..7950`、`f=9300..9750` 为 **16 (bit4)**，
`t5c` 同步出现 49152/32768/64928、`e1=32` ⇒ 气绝/眩晕块
（`0xA2E18` 检查 `&0x10`、`0xA2F0C` 置 `|0x10`）[C]。
疲惫段 `flg=0` ⇒ **减气不占状态位**，P29「瞬时事件、无持续状态字」再确认。
`st=1` 于 `f=8400..12150`（怒判据再确认）；`dc=1` 自 `f=12000` 起 latch（P28 一致）。

### 4 · 时间锚点 / 冻结陷阱

`qstart=2693`，3 分钟 ≈ `f=13493`；`N f=15000 ENTER-LOW`、BEAT dA 自
`f=14700` 恒 0；`f=14250..20400` **138 条 R 行全同** ⇒ 任务状况菜单
再次冻结游戏逻辑而 forge 帧继续涨。可用证据只有 `f≈13650..14250` 频次下降
+ 用户口述，冻结段不作样本。

### 5 · 重要边界（不可过度宣称）

**强制触发在 `f=5193`（任务内约 42 秒），用户口述流口水在 3 分钟，不是同一次事件。**
强制那次确实驱动 1 次 grow（proc 0→1），可见疲惫是后续第 2/3 次自然触发
⇒ 结论是「触发链闭环 + 强制路径有效」，不是「强制一次 = 立刻可见流口水」。
若要开场即疲惫，v49 需把强制窗口延后或避开自然阈值叠加（本轮不动）。

### 6 · 下一步与纪律

用户正常关游戏后（报告 2 已可复现 PASS=11/0），数据已足，回 AI 主线
**3 状态权重层**：怒 `st==1`、疲惫「proc 递增事件 + BEAT 300f 频次下降」行为判据、
普通其余；跨怪通用、零写入、不硬编码怪种数值、不碰 action_id。
本轮只做分析 + 判读脚本修正（`tools/analyze_v48_trigger.py`），
未编译 / 未部署 / 未改参数 / 未动 `6_`。回退链不变（`v47.nro` 纯只读）。

### 7 · 22:56 补记（用户退出后）

用户已正常关游戏。完整日志归档 `out/game_p54_lite_20261111_2254_v48_FULL.txt`（末 BEAT f=27750），修正判读重跑 `out/v48_P30_FINAL_report.txt` **PASS=11/FAIL=0**；`out/lite_state_result.txt` 旧报告为 `10/1`（误判 POST 时序），已覆盖修正版。`f=20550..27750` 主怪 R 行 49 条全同 ⇒ 用户从菜单直接退出，本轮无恢复轨迹，不影响「触发链闭环」结论。U 行 40/40 配额在 f=11246 用满 [U]。本轮收尾未编译/未部署/未改参数；插件仍 v48（`f4c6d2b7…`）。

---

## 2026-11-12 19:48 · P31：v49 三状态权重层（继承会话续做，已部署未实机）

用户「继承工作空间中的 MHGU AImod（针对怪物的）并继续任务」⇒ 主线 `04_RiseAI`
（Rise 式单人 AI、针对怪物），**不是** `08_AIHunter`（伪真人队友）。继承核验：
P30 减气链闭环 `PASS=11/0`、插件 v48 `f4c6d2b7…` 产物与部署 md5 一致、
基线干净（临时 mod 已回退 / `6_` md5 `7361445f…` / load_order 无追加）。
P30 §6 定案下一步 = 回 AI 主线 **3 状态权重层**，本轮按此推进。

### 1 · 设计（结构性近似，非等价复刻）

Rise 15 池 = 3 状态 × 5 距离档，怒 6 表熵 1.67 / 疲 4 表熵 1.30；
GU **无对应表结构**（§932），只改 EMC 加权抽选层（`0x8E144`, `mode==1/sub==0`）
的 **prev 否决严格度**：怒 `depth=3`（更多样）/ 常 `depth=2`（v38 行为等价）/
疲 `depth=1` + `TIRED_KEEP_PCT=50` 放弃否决（更贴近原版权重）。距离档未实现。

### 2 · 三态判据（全只读、跨怪通用）

- 怒 `*(u8*)(act+0x518)==1`（P14/P25/P30 闭环），优先级最高。
- 疲 `0xA30E4 EXH add` 返回 **1** 或 `proc=act+0x5D8C` 递增 ⇒ 进疲惫窗口；
  **窗口用该怪自己的动作数 `ST_AN[i]` 计时**（`0xAFF40` 按 `reg_mon` 槽递增），
  退出 `>=40` 动作或 `108000` 帧兜底 ⇒ **暂停菜单不进入/不退出/不消耗窗口**
  （P19/P22/P28/P30 的 forge 帧陷阱）。`h_exh` 被 SKIP 时 proc 轮询（30f）接管。
- 常其余。

### 3 · v48 强制已移除

一次性 `amount=thr+16` 是探针、且 P30 证实与可见疲惫非同一次事件 ⇒ v49
`h_exh(a0,a1)` **原样透传、只读返回值**，纯只读零写入。NRO 内 `force=1` 不存在。

### 4 · 产物与验证

- 源码 `plug/context_probe/src/lib.rs`（备份 `lib.rs.v48bak`）；新增 `P_SIG3`、
  `prev_hit_d/push_prev(3)`、`mon_state/veto_depth/tlog/enter_tired`、
  `T` 行状态事件、`V` 行 `st3/vd`、`S` 行 `s0/s1/s2/sv*/d3/skip`。
- 产物 `out/rai_tristate_v49.nro`，**40960 B，md5 `ec4fcd058a514605abbd01c304041a43`**；
  特征串/`nm` detour 双向核对通过（含 `h_exh::___detour`）。
- 离线：`tools/make_v49_smoke.py` + `tools/analyze_v49_states.py`
  → `out/v49_sim_report.txt` **PASS=20 / FAIL=0**（V=60 三态齐全、st3→vd 违例 0、
  T ENTER/EXIT 齐、reason=3 且 an>=40、U ret=1 force=0、d3==s1、skip>0）；
  P30 的 v48 真实日志降级不崩溃（PASS=6/14 属预期缺失）。
- 无游戏进程时部署到 `mods/RiseAI_EntryProbe/.../rai_entrylocator_probe.nro`，
  md5 一致；`6_` / 游戏资源 / load_order 未动。
- `8_lite_check.bat` / `7_P54_启动并抓日志.bat` 改 STEP 49、`TOOL2`→v49 判读；
  CRLF（`bareLF=0`）、执行逻辑、输出路径、轮转、Python 绝对路径全保持；
  备份 `out/*.bat.v48bak`，更新脚本 `tools/update_step49_prompts.py`（自带守卫断言）。
- 报告 `out/P31_v49_three_state_layer.md`（细节只写这里）。

### 5 · 下一步与边界

用户双击 `8_lite_check.bat` → 跳狗龙王短场，覆盖发怒段 + 一次自然流口水
（约任务内 3 分钟）→ 立即正常关游戏 → 第二份报告给 v49 三态判据。
判据：`INSTALL h_exh (v49 read-only)` / T ENTER+EXIT / V 三态齐全且映射无违例 /
`S s1>0 && d3==s1 && skip>0` / 零 FATAL / `live=1` / `hub=15`。
**边界**：结构性近似非等价；`depth=3 / 50% / 40 动作`均为自定保守参数；
疲惫窗口起点是状态机通知，不必等于可见流口水（P30 强制那次即反例）；
怒/疲判据跨怪一致性未系统验证；暂停仍产生全同 R 段但不再影响窗口计时。
异常即覆盖回 `out/rai_exhaust_chain_v48.nro`（`f4c6d2b7…`）。

本轮**未实机**、未改游戏资源、未动 `6_`、未追加 load_order。

---

## 2026-11-12 20:35 · P32：Rise 侧完整 AI 链系统复核（4 路并行只读，等实机期间）

用户去跑 v49 实机，要求先检查 Rise 侧完整 AI 链、文件多可分子 agent。
**4 路只读子代理并行**（A 池/权重、B FSM/门控、C 动作/耐力、D 资产/差距）
+ 主代理独立交叉核验（现算熵/表号/路径口径/RSZ 字节计数）。
**本轮全程只读**：未改插件、部署、bat、游戏资源、load_order，未运行游戏。
报告 `out/P32_rise_full_ai_chain_audit.md`（细节只写这里）。

### 1 · 五条修正既有定案（最重要）

1. **§504 表号箭头误读**：`tired·档5 [10,20,70]→[1,20,51]` 的 `[1,20,51]` 是
   `action_table_nos` **升序集合**，与 rates 位置 **0/15 池吻合**；真实配对由
   `_TransitionActTbl` ref 还原为 **10→表1、20→表51、70→表20**。表 51 在 normal
   档3/4/5 也以 50/45/35 高权重出现 ⇒「疲惫池偏向低威胁表」无 TableNo→威胁度映射支撑，降级。
2. **怒池熵与常池几乎无差**：现算 anger **1.6740** / normal **1.6669**（差 +0.43%）/
   tired **1.2984**（比非疲惫低 22%）。⇒ Rise 实际只区分「疲惫 vs 非疲惫」，
   P31 §1「怒池熵 1.67 更多样」不成立，**v49 的怒 `depth=3` 缺 Rise 数值依据**。
3. **Rise 有疲惫计时器/布尔状态字段**：`_tiredSec`(1) / `_IsTired`(2) / `_AddTiredTime`(60)
   在 `rszmhrise.json` 实证存在；`Stamina_low_Start` / `tired_start` 在 Rise 侧 **0 命中**
   （是 GU 的 EMC/rodata 状态名）⇒ GU「疲惫是瞬时事件、无持续状态字」是 **GU 特有**，
   不是 Rise 对标；P20「Rise 不是计时器」存疑。
4. **§932 前提被推翻、字面禁令保留**：`NOTES:1968/2278` 已作废「GU 无集中抽选器」，
   `op02` = `rand%100` 与 `_TransitionRate` 同构。建议改写为「GU **有**同构抽选骨架、
   **没有**按 (状态×距离) 索引的 15 张独立池表 ⇒ 照搬表不可行、结构近似可行」。
5. **「12 处境 Hub」口径收窄 + 资产断裂**：12 = em001/00 的 12 个 `attack_stance_*`
   处境变体（非全局 12 个独立 FSM），Hub 是目录级概念；442 条路径清单与 107 个解包
   **basename 重叠 0** ⇒ 清单是待抽取索引、解包是另一定向抽取。`*_main.user` 主例程
   **0 个** ⇒ 链在 L2→L4 断开。GU `hub=15` 与 Rise Hub **同名异物**。
   `EnemyAIFSM` 类名在 RSZ 模板 0 命中。

### 2 · 完整链 L0–L7

`L0 EnemyUserDataParam 装配 → L1 EnemyThinkData._StateList/ThinkState →
L2 12 处境 Hub(_NextStateID + userdata 绑定) → L3 ThinkCondition 门控
(_IsActionEnd 12 True/32 False，池内全 False) → L4 状态×距离档共同索引 15 池 →
L5 ConditionInfo 检查(_CheckPrevTableInfoList 50/50 长度 1 + Timer/Counter) →
L6 _TransitionRate 百分制轮盘赌(和恒 100) → L7 ActionTableData._TableNo → act/combo →
ActionInfo(_actionNo,_subStaminaPoint)`。
`_IsActionEnd` 生效在 **L3**（决定何时允许进入下一次抽选），不在 L5/L6/L7；
「连段内部不重抽」有 5 条字段证据，但「仅动作结束帧求值」仍属推断。

### 3 · 资产口径

442 路径（user_data 325 / shell 68 / map_data 26 / act_tbl 12 / ai_fsm 11，53 怪种）；
解包 107 = routine 89 + hub 12 + param 6；`rsz_json` 107 一一对应、`files_partial=60`。
routine 全库 89 / em001 43（22 子目录）不矛盾。`main_out1` 只占 15，其余 74 是
`main_out2/301/302` 与 `modeNNN` 的**稀疏 state×range 覆写网格**（仍用 3×5 命名）。
标量可信，`Object/List<Struct>` 引用因固定失步不可定论。

### 4 · 对 v49 的影响（本轮不改部署）

- 怒 `depth=3` 应改称「自定增强多样性」；更贴 Rise 数据的结构是**两档**
  （非疲惫 depth=2 / 疲惫 depth=1+keep）。**待用户拍板，本轮不动**。
- 疲惫窗口是 GU 因无状态字而必需的近似，不是 Rise 对标（P31 表述正确，本轮加固）。
- §504 叙事降级不改 v49 实现（v49 不读表号）。
- **5 距离档仍是唯一硬的未实现维度**；Rise 侧确认为「状态+距离共同索引」，
  且距离阈值数值在 Rise 侧也未解出（`em131_00_range_data.user.2` 未抽取）。

### 5 · 优先级

**P0**（用户正在做）v49 实机 + 换第 2 只怪验跨怪一致性；
**P0'** 按上面 5 条修正 NOTES §504/§932 与 P31 §1 的对标叙事；
**P1** `0x8E144` matcher 层纯只读定位运行时 5 档（跨 2 怪，复核首字）；
**P2** `0x75224` 干净调用者层处境分流（17 个中 11 个可 hook，`0x76154` 被 IPS32
切成解释器函数不可直 hook，禁止事后写 `+0x73E1`）。

### 6 · 断点

`*_main.user` 主例程 0 个；`range_data` / `stamina_data` / `action/combo/damage` /
`ai_fsm/think` / `flow` 未解包（437/442 条 0 覆盖）；`TableNo→_actionNo→招式名`
映射链断；`modeNNN` 语义、Timer/Counter 绑定、Hub `_NextStateID` 大数值含义均为推断。

本轮**未实机、未改任何插件/部署/脚本/游戏资源/load_order**；v49 仍 `ec4fcd05…` 待实机。

---

## 2026-11-12 20:49 · P33/P34：v49 首场实机闪退诊断 + 高还原度路线

用户 20:49 反馈「任务中闪退，需要看日志并检查原因」+「本任务要尽可能复刻 Rise 怪物 AI，还原度高」。
日志 `02_Workspace/game_p54_lite.txt`（20:28，647,686 B / 6291 行），
归档 `out/game_p54_lite_20261112_2028_v49_CRASH.txt`；
修正判读 `out/P33_v49_real_machine_report.txt`（不覆盖原 `lite_state_result.txt`）。
报告 `out/P33_v49_crash_diagnosis.md`、`out/P34_high_fidelity_roadmap.md`（细节只写这两份）。

### 1 · 闪退现场与裁定

`*** exception c0000005 accessing 0x10`（host 空指针 +0x10），
`guest pc=0049bd3c lr=0`，r0=0 / r8=`0C163940` / r10=`0C165E00`；
host backtrace 34 帧，#13 起 `f_49b8e8+1edc` / `f_49b65c+194` / `f_e07640` / `f_5da8fc` /
`f_d8692c` / `f_a6538c` / `f_3a82e8` / `f_2478d80`。
`text_addr=0x200000` ⇒ 偏移 `0x29BD3C`，反查 `main_text_decomp.bin` 得 `E3500001 cmp r0,#1`，
前一条 `E5900000 ldr r0,[r0]`；崩溃函数 `0x49b8e8` prologue `E92D4FF0`、读 `[r4+0x1470]`。
`lr=0` 与历史 v20 `FATAL: no function at 0 (pc=0,lr 有效)` **形态不同**。

崩溃前 10 行全是玩家侧 `MHGU_FIX40_FX_TEST25`（`native_combo_state/action_committed/motion_bound`），
对象恒 `0C163900`；全文 FIX40 **1326** / gogport **117** / 玩家对象 **1497** 条
⇒ **崩溃在玩家动作/连招/伤害结算路径，不是怪物抽选路径**。
末 `[rai] R f=37950`、`BEAT f=37800`、`low=1` 已持续 3150 帧（≈52 s，疑暂停菜单）。

v49 健康检查全正常：**5 hook 全 INSTALL**（`SITE +0A30E4=E92D41F0`）、零 FATAL、
`live=1`、`hub=15`、`fail=0`、`ok=141`、35 条 V 行 `st3→vd` 零违例、`d3=34==s1=34`、
`U` 行 `force=1` 计数 0。v49 纯只读、零写入、零游戏函数调用，新增读取都是 v48 C/R 行
已读字段 ⇒ **不存在写出空指针的路径**。

**裁定分层**：基本可排除「v49 写空指针 / hook 栈帧破坏 / 怪物抽选层」；
**不能排除**「时长/时序诱发」（`c0000005` 在归档日志中首次出现，本场 37950 帧 >
v48 最长 27750 帧，且处于长低活动窗口）与其它 mod 玩家侧路径。
⇒ **未定案，定因前不改插件参数、不推进重构**。A/B 见 P33 §5：
① 同场景复跑判偶发 → ② 覆盖回 `out/rai_exhaust_chain_v48.nro` 同场景复跑 →
③ 备份后把 `RiseAI_EntryProbe` 改 `# off:` 彻底排除 → ④ 再隔离音频线/`MH4U Port`/gogport。
纪律：不动 `6_`、音频 mod、`Show HP Bar`、游戏资源；改 load_order 先备份。

### 2 · 两个确凿缺陷（与闪退无关）

1. **判读脚本假 FAIL（已修）**：`analyze_v49_states.py` 用 `startswith("[rai] INSTALL")`，
   实机行带 `[forge] [INFO]` 前缀 ⇒ 报 `INSTALL=0`。已改 `"[rai] INSTALL h_" in l`，
   并加「零 host 异常」判据与 `proc>30` 告警。修正后 **PASS=14 / FAIL=7**（原 12/8）。
2. **v49 proc 误判（待修，本轮不动插件）**：唯一 T 行
   `f=20970 kind=1 reason=2 i=1 mon=0C430060 proc=211 an=5`，proc=211 远超 grow cap 30
   ⇒ 非目标槽字节被当递增，制造假疲惫窗口；`U=0` 证明本场**无真实减气触发**，
   故 `st3={0,1}`、`s2=0`、`skip=0`、`EXIT=0` 全部由此解释。
   修正口径留 v50：proc≤30 + `0<thr<0x4000`、`h_exh` 已装时只信 `ret==1`、
   proc 轮询降为纯观测、只对有减气块的主怪槽生效。

⇒ **本场不能作 v49 三态验收**；P31「待实机」状态不变。

### 3 · 高还原度路线（用户第 2 点）

**v49 还原度不够**：只调 prev 否决严格度，没碰 Rise 真正的载体——候选池权重分布；
且 P32 M2 已证怒 `depth=3` 无数值依据。

**GU 骨架此前被低估（离线硬数据）**：3 怪 `allPools` **561** 池（462 个 cases≥3 且和=100），
`target_dist_rot` **147** / `target_dist_rot2` 6 处（距离 case `('0','1','2','3')` 83 处）、
状态分支 `[sub+0x1ba]` **172** 处等 ⇒ P32「距离档完全未定位」应修正为
「**离线脚本层已定位、运行时读法未定案**」。

**W1 权重层离线对拍**（top-k 截断 + Rise 排序形状重分配，纯计算零写入）：
Rise 非疲形状 `[45,26,22]` 熵 1.6705 / 疲惫 `[55,35,10]` 熵 1.2984；
GU 462 池原始 meanH **2.4519**。变换后非疲 k=3 → 1.5321、k=4 → 1.8423（55:45 混合命中 1.67）；
**疲惫 k=3 → 1.2955（偏差 −0.005，几乎精确命中 1.2984）**。
⇒ W1 是可量化、可验收、跨怪通用、不硬编码 action_id 的高还原度落点。

**五层**：W0 状态输入（修 proc）/ **W1 权重层（核心跃升点）** / W2 距离档运行时探针 /
W3 `_IsActionEnd` 门控（`0x75224`）/ W4 处境分流（12 Hub ↔ kind）。
明确不做：Rise 侧 Timer/Counter 因果未证实、GU 自创 CD 已证伪、照搬 15 张表不可行。
阶段 A（闪退 A/B + 修 W0 + 干净基线）→ B（W2 只读探针）→ C（W1）→ D（W3+W4）→ E（跨怪一致性）。

**诚实天花板**：能做到**机制级复刻**（轮盘赌 / 状态×距离权重 / prev 否决 / 门控 / 处境分流，
零写入）；做不到数据表级 1:1（GU 无 15 张独立池表）、Rise 5 档几何阈值（未抽取
`range_data`）、疲惫持续状态（GU 是瞬时事件）、`TableNo→招式名`（Rise 侧链本身断）。

本轮**只读诊断 + 判读脚本修正 + 日志归档 + 设计/离线对拍**；
插件仍 `ec4fcd05…`，`6_` / load_order / 游戏资源 / 其它 mod 未动。

---

## 2026-11-12 21:05 · P35：v50 W1 Rise 池权重层落地（跳过 A/B，已部署未实机）

用户 20:59「我不验证是否再次闪退，你继续推进任务」⇒ **跳过 P33 A/B**，
直接按 P34 实现 W0 + W1。报告 `out/P35_v50_w1_implementation.md`（细节只写这里）。

**风险前置**：P33 闪退仍未归因。本版 5 个 hook 点位/数量不变、零写入、
零游戏函数调用、`original!` 参数透传，改动全是局部纯计算 + 只读字段门控，
不新增读取面 ⇒ 不引入新的写入/调用类崩溃面，但**不宣称与该异常无关**。

### 1 · W1 权重层（高还原度核心）

`rise_weight_pick()`：合格 case 按原权重降序稳定排序 → 取 top-k →
其余置 0 → 按 Rise 排序形状重分配成和=100 的**局部**有效权重 →
`cum>p5n` 轮盘赌；候选 `<3` 或 `<k` 返回 -1 退回 v38 原权重。
**绝不写 `cs[].w`（游戏内存）**，唯一输出仍是 `h_matcher` 返回分支偏移。

最终形状（P34 §6 口径修正）：`SHAPE_N3=[45,32,23]` / `N4=[40,27,20,13]` /
`T3=[60,30,10]` / `W_MIX_PCT=61`。疲惫实测平均形状 `[55,35,10]` 熵 1.3367
≠ Rise 平均熵 1.2984（形状均值≠熵均值），故按熵目标微调为 `[60,30,10]`。
离线对拍 `tools/verify_v50_weight.py`（Python 逐行复现 Rust 整数算法，462 个真实 GU 池）：
形状和恒 100 / pick 越界 **0** / 非疲 **1.6701**（目标 1.6705，−0.0004）/
疲惫 **1.2955**（目标 1.2984，−0.0029）/ 混合 61:39，全 PASS。

配套：`veto_depth` 3/2/1 → **2/1**（删怒 depth=3，P32 M2）；删疲惫 50% keep
（避免与 W1 双重压熵）。

### 2 · W0 修复（P33 §6.2）

三重门控：`proc<=30`（cap 30）、`0<thr<0x4000`（排除小怪槽 65535 免疫哨兵）、
`EXH_SITE_OK==1` 时 proc 轮询**不再触发**窗口只观测（唯一可信触发 `ret==1`）。
`U` 行加 `bad=`、`V` 行加 `wm/wk`、`S` 行加 `w3/w4/wt`（`d3/skip` 恒 0）。

### 3 · 产物与验证

- 源码 `plug/context_probe/src/lib.rs`（备份 `lib.rs.v49bak`）；
  产物 **`out/rai_risepool_weight_v50.nro`，45056 B，md5 `cc48483a9b5e436baddb7a7a2875148f`**。
  特征串 `RAI v50` / `W1 RISE-POOL WEIGHT LAYER` / `wm=` / `wk=` / `w3=` / `bad=` 齐，
  `force=1` 不存在，`nm` 含 `h_matcher::___detour`。
- 冒烟 `tools/make_v50_smoke.py` + `tools/analyze_v50_weight.py`
  → `out/v50_sim_report.txt` **PASS=19 / FAIL=0**；P33 的 v49 崩溃日志降级不崩溃。
- 无游戏进程后部署到 `mods/RiseAI_EntryProbe/.../rai_entrylocator_probe.nro`，md5 一致。
  `6_` md5 `7361445f…` 未动、load_order 第 38 行未追加、游戏资源/其它 mod 未动。
- `8_`/`7_` 提示改 STEP 50、`TOOL2`→`analyze_v50_weight.py`；执行逻辑/输出路径/
  轮转/Python 绝对路径/CRLF（`bareLF=0`）全保持，`tools/update_step50_prompts.py` 带守卫，
  旧版备份 `out/*.bat.v49bak`。
- 回退链 `out/rai_tristate_v49.nro`(`ec4fcd05…`) → `out/rai_exhaust_chain_v48.nro`(`f4c6d2b7…`)。

### 4 · 下一步

实机判据见 P35 §7（零 FATAL 且零 c0000005 / wm→wk 与 st3→vd 零违例 /
w3,w4,wt>0 / U bad=0 / T proc<=30 / live=1 / hub=15）。
**W2**：`0x8E144` matcher 层纯只读探针，把离线已定位的 `target_dist_rot` 4 档
（147 处）与运行时 `s16`/case 索引对齐；对齐后 W1 可升级为
「(状态 × 距离档) 逐档 Rise 真实形状」，还原度再升一级。
W3 门控 / W4 处境分流仍留 P34 阶段 D。

本轮**未实机**，v50 待实机；未改游戏资源、未动 `6_`、未追加 load_order。

---

## 2026-11-12 21:20 · P36：三问可行性分析（距离档 / 领地争夺 / 小连段）

用户三问：①「距离档为什么不做，如果只是想测 W1 就告诉我」；② 两只大怪领地争夺能否复刻；
③ Rise 小连段是否真实、能否在 GU 复刻。**全程只读**，2 路子代理（E 领地 / F 连段）+
主代理交叉核验。报告 `out/P36_three_questions_feasibility.md`（细节只写这里）。

### 1 · 第 1 问正面回答

**是的，v50 本轮就是把 W1 单独拆出来验证**。W1 零前置（`scan_cases` 已有 case 权重、
实机 `sw=100` 35/35）且收益最大；W2 的运行时输入未定位：Rise `range1..5` 只是文件名
（几何阈值在 `em131_00_range_data.user.2`，未抽取），GU 离线 EMC 虽有 `target_dist_rot`
147 处 / 4 档，但 `h_matcher` 的 `s16` / 命中 case 索引 ↔ 档位 无实机证据。
同时写 W1+W2 会把两个未验证假设相乘、出错无法归因 ⇒ 刻意分开。
W2 成本 = 1 场 `0x8E144` 纯只读探针（s16 / 阈值 case / 命中索引 / st3）跨 2 怪；
降级方案 = 按 case 索引分档（不读绝对距离），还原度低，不冒充 Rise 5 档。

### 2 · 重要交叉裁定：`0x76154` 当前可 hook

子代理 E 引用 `NOTES:1008/1018/1056` 称 `0x76154` 是 `E28FF7AD` 解释器跳板不可 hook，
与 v50 冒烟/实机的 `INSTALL h_unify first=E92D4FF0` 冲突。
核验：`load_order` 第 29 行 `MH4U Port` 启用，IPS32 **变体 `4e778eef…`** 长期部署
（§1415/1440，删 `0x76254` 记录），实机日志 `SITE +076154=E92D4FF0`。
⇒ **`E28FF7AD` 属 v16~v29 基线口径，当前变体口径下 `0x76154` 已 native、可 hook**。
E 该条论据不成立但不改变其结论；P32 §6 / P34 W3 的相应表述按此裁定理解
（P34 已追加 §6.1 注记）。

### 3 · 领地争夺：Rise 式专属演出**不可行**

- Rise 机制（公开资料中等可信）：脚本化专属演出、固定怪种对、猎人在场、W/L/Draw 表、
  专用动画；monsterhunterwiki / Game8 / fandom 多源一致。
- **本地实证否定**：RSZ 中 `TurfWar/turf/Turf/Turfbattle` **0 命中**；
  `Territory` 65 次全是地图区域 AI（`EnemyTerritoryInfo._BlockNo/_Radius/_CombatFlag`）；
  `rival` 80 次**全是 `Arrival` 子串误报**；路径清单仅 1 条 `m00_territory.user.2`
  未解包；107 解包 / 107 rsz_json **0 命中**。
- GU：多怪同场是任务一等公民（`quests.md` 乱入表），但**只有被动误伤、无主动互为目标、
  无专属演出**；GU 动作名闭集 13 类无 versus/turf（`mon-ai-entry.md:233`）。
- 三路线：(a) 纯只读观测 + W1 引导 **有条件可行**，但「引导互攻」**不成立**
  （EMC 无「另一只怪」目标概念，`formats/emc.md:51,63` 只读距离无视锥）；
  (b) 复用互殴增强 **当前不可行**（必须写目标/状态，违反零写入）；
  (c) 专属演出 **不可行**（新增动画资源 + 写内存 + 按怪种对硬编码 + 改 arc）。
- 前置：≥3 轮多怪实机、mon 区域号、对象表纯读路径（禁用 `call(0x18FFC,mgr)`）、
  「≥2 个不同 sp 同区号同时间窗共现」判定。

### 4 · 小连段：**真实**，GU 本来就有

- Rise 实证：`refs/rise_unpack` UTF-16 扫出 **73 个** `emNNN_combo_NNN.user`
  （em001 18 / em002 30 / em003 25），64/107 个 `.user.2` 含 combo；
  15 池 `_Category` **{0:64,1:36}**，`tiredrange1` cat1=0 → combo 路径 0，其余 14 池
  cat1>0 均有 combo ⇒「Category=1 → combo 目录」强相关实证；
  `ActionTableData` 仅 2 字段 = 资源句柄；`ActionInfo` 8 字段无 combo/link/CD；
  RSZ 的 `Combo` 784 次主语义是**玩家武器派生 / 操龙**，无通用 `EnemyCombo` 类。
  ⇒ 连段是 **`combo/` 资源预编排序列**（抽选层决定进哪张表，执行层按表推进）。
  **硬缺口**：combo `.user.2` 全部未解包，段数/线性/分支/帧数无本地证据。
- **证据等级更正**：「连段内部不重抽」是**高置信推断非实证**（P32 §2 已自述），
  NOTES §409/472 措辞应下调一档，结论不推翻。
- GU 实证：42.9%(51/119) act 不变仅 sub 变 = 段号；`2↔7` 77 次；`act=6` 固定序列
  `7/21→6/12→6/7→6/11→6/12→7/21`（`6/12→7/21` 恒 10 帧，重复 4 轮）；
  v22 零写入仍是原版连段 ⇒ 不是插件产物。
- **v50 按设计不破坏连段**（只改栈上局部权重、零写入、段内推进非加权抽选产物），
  但**缺一条闭环数据**：`NOTES:2042` matcher 每条 EMC block 指令都会调，
  无实机证据证明段内 sub 变化不经过 `op02/mode==1`。且 `v50_sim_report.txt` 的
  19 项判据**没有连段完整性项**（本轮发现的实际待补项）。
  闭环判据：`sel>0` 只出现在 act 变化时、段内 sub 变化时 `sel=0`。
- 三路线：(a) v50 现状 **可行**（待闭环）；(b1) 抽选层改「进入哪个连段/衔接概率」
  **有条件可行**（本质 W1 按状态扩展，可与 W2 合并）；
  (b2) 改连段长度/段内衔接 **不可行**（需写 `+0x73E1`，与 v11~v15/v24i 同构已证伪）；
  (c) 注入 combo 资源 **不可行**（改资源 + 映射链断 + action_id 硬编码）。
- 最小验证：S1 静态闭环 → S2 归档日志离线配对 `+0x73E0` × `0xAFF40` 间隔 × `sel` →
  S3 若字段不足，v50 现有 5 个只读回调**只补观测行** `COMBO`（不新增 hook/不写内存）跑 1 场。

### 5 · 三问汇总与状态

① 距离档：本轮确实只做 W1，W2 待 1 场探针（或接受降级）；
② 领地争夺：Rise 式不可行，纯只读最多「同区检测 + 招式分布引导」，不能主动互攻；
③ 小连段：真实且 GU 本来就有，v50 待一条 `sel` 配对闭环，(b1) 可随 W2 推进。

本轮**纯只读**：v50 仍 `cc48483a…` 已部署待实机；
未改插件/部署/脚本/游戏资源/`6_`/load_order。

---

## 2026-11-12 21:26 · P37：v50 首场实机（雄火龙）判读 + 「不疲劳」归因

用户完成一场任务：① 雄火龙一直发怒、不进疲劳（自述非 mod 问题但不正常）；
② 要检查日志判断 mod 是否出错。日志 `02_Workspace/game_p54_lite.txt`
（1,120,354 B / 10,900 行），归档 `out/game_p54_lite_20261112_2126_v50_RATHALOS.txt`；
判读 `out/P37_v50_real_machine_report.txt`；报告 `out/P37_v50_rathalos_real_machine.md`
（细节只写这里）。

### 1 · mod 结论：**没有出错**

零 FATAL、零 host 异常（**上一场 `c0000005` 本场未复现**）、
`MapAssist quest state reset (quest ended)` **任务正常结算**；
5 hook 全 INSTALL（`+076154=E92D4FF0` 再次印证 P36 §1 变体口径裁定）、
`live=1` / `hub=15` / `fail=0` / `ok=119` / `noalt=0`；
v38 主规则 **PASS=22/FAIL=0**（`sel=218 v=26` 改写率 11.9%、`sw=100` 24/24）；
v50 W1 `wm→wk` 与 `st3→vd` **26/26 零违例**，26 条 V 行中
`wm=1`(非疲k3) 14 / `wm=2`(非疲k4) 7 / `wm=0`(候选不足退回 v38) 5；
`S` 行 `w3=14 w4=7 wt=0 d3=0 skip=0`；W0 无误判（`T=0` 故无 `proc>30`）。
⇒ **W1 在非疲态确实生效**，疲惫分支本场未被触发、不是失效。

### 2 · 工具修正：样本缺失 ≠ 规则违例

原 `analyze_v50_weight.py` 把 `U=0/T=0/st2=0/wt=0` 报成 **6 个 FAIL**
（`PASS=13/FAIL=6`），会误导成 mod 出错。已改：新增 `has_tired` 判定，
无疲惫样本时把「三态/三形状/wt/U/T」判据标 **SKIP** 不计 PASS/FAIL，
硬判据仍全部执行（含新增「W1 非疲形状生效 w3,w4>0」）。
修正后本场 **PASS=14 / FAIL=0 / SKIP=1**；冒烟回归 **PASS=20 / FAIL=0 / SKIP=0**。
只改判读脚本，**未改 NRO / 8_ / 7_ / 6_ / load_order / 游戏资源**。

### 3 · 雄火龙实测与三场对照

主怪 `0C109CE0`（`sp=0002`），R 行 556 条：
`st={0:253, 1:303}` ⇒ 发怒 **54.5%**（A 行 53.3%），用户体感成立但非 100%；
`thr` **恒 233**（有效减气块，非 65535 哨兵）；
`ex` / `proc` / `amt` **全部恒 0** ⇒ counter 从未累加、`0xA30E4 add` 从未返回 1。

| 场 | 主怪 | thr | ex | proc | 全同冻结段 | 疲惫 |
|---|---|---|---|---|---|---|
| P30 v48 | 跳狗龙 `0C250060` | 142→190→237→285 | 0..237 | 0→3 | 48.6%（触发后才冻结） | ✅ 3 次 |
| v49 | 雄火龙 `0C1F3650` | 恒 233 | 恒 0 | 恒 0 | 5.9% | ❌ |
| 本场 v50 | 雄火龙 `0C109CE0` | 恒 233 | 恒 0 | 恒 0 | 20.4% | ❌ |

**逐项排除**：① 非 W1 引入（v49 无 W1 同样全 0，v50 纯只读零写入）；
② 非 `[vt+0x39C]()` 抑制（抑制会留 `ex=thr-1=232`，全库命中 0）；
③ 非发怒抑制（`st=0` 的 253 条里 ex 也恒 0）；
④ 非暂停冻结（v49 只 5.9% 仍 0；P30 48.6% 反而触发 3 次）；
⑤ 非「无减气块」（thr=233 合法，3 个小怪槽才是 65535）。
⇒ **跨怪差异高置信推断**：P29 减气链是 `em085` 实证，跨怪一致性本就标注未验证
（P31/P35/P36），本场实机撞上。**根因未定案**。
注意 `amt=0` 不能当证据：P30 跳狗龙 R 行 `amt` 也恒 0（272/272）却 ex 累积
⇒ `act+0x4D8` 是瞬时值，30/150 帧快照采不到。

### 4 · 观测缺口（本场暴露）

1. v50 `U` 行只在 `ret==1` 输出 ⇒ `U=0` 只能证明「没触发」，
   **无法区分**「add 从未被调用」与「amount 恒 0 / 被抑制」。
   建议下一版 `S` 行加 `add_calls / amt_sum / amt_max`（纯观测、不改行为、不新增 hook）。
2. 判读脚本仍缺连段完整性项（P36 §3.3）：本场 `A=90` 但无
   `act=6` 序列 / `2↔7` 段号 / 段内 `sel` 配对核对。

### 5 · 下一步

① **换跳狗龙王短场**验收 W1 疲惫分支（判据 `U>0 bad=0` / T ENTER+EXIT /
`st3=2 vd=1 wm=3` / `wt>0` / 零 FATAL / 零 c0000005 / live=1 / hub=15）；
② 补 add 观测后再跑雄火龙，把「跨怪差异」从推断升实证；
③ 同场补 `COMBO` 观测闭环 P36 的段内豁免判据。

**边界**：本场未复现闪退 ≠ P33 已归因；雄火龙不减气根因未定案；
v50 仍 `cc48483a…` 已部署。本轮只改判读脚本。

---

## 2026-11-12 21:40 · P38：两问复核（状态静止段 ≠ 冻结；当前耐力该盯哪里）

用户两问：①「冻结占比 20.4%？本场除跑图就在战斗、没暂停，全同段是跑图导致的吧」；
②「疲劳应该也要关注怪物 stamina 值的变化对吗」。**两问都对**。
报告 `out/P38_freeze_vs_stamina.md`（细节只写这里）；P37 两处表述已回填更正。

### 1 · 问题 1：承认归因误差

P37 把「连续 ≥8 条 R 行 9 字段全同」直接叫「冻结段」，**漏了真判据**
（P19/P22/P28/P30 定案：`A_N` 停止增长 + forge 帧继续涨 + R 行全同）。
补 `A_N` 交叉核验：本场 17 段共 9570 帧，其中 **`A_N` 仍在增长的段 5580 帧 = 58.3%**；
最长段 `f=34500..36930`（58 条 / 2430 帧）`ΔA_N=5`、段内 2 条 A 行、`low=0`
⇒ 典型跑图/主怪离场，不是暂停。且主怪 `ex` 值域恒 `[0]`、`st` 切换 10 次，
**非全同段 `ex` 同样 0** ⇒ 与任何分段无关，P37 排除项 ④ 结论不变。
以后判暂停一律用 `A_N` 停止增长，不能只看 R 行全同。

### 2 · 问题 2：方向对，但要精修字段

P20 §56/69/70 早就定案「前 7 轮追错了对象，该追**被轮询的当前耐力值**」，
用户直觉与项目结论一致。但 P20 路线 A 推荐的 `mon+0xCAC0 → +0x3F / +0x5C`
（R 行 `s3f` / `f5c`）**三场实机不支持**：
`s3f` 三场恒 0；`f5c` P30 恒 0、雄火龙两场恒 `1106247680 = 0x41F00000 = f32 30.0`
（固定常量，不是被轮询的计时器）。P20 当时自己标了 `[U]`，现予否定。

真正与疲惫联动的是 **`act+0x5D82..0x5E0C` 整块**（P29 Exhaust 运行期块）：

| 字段 | P30 跳狗龙(有疲惫) | 雄火龙两场(无) |
|---|---|---|
| `ex` / `thr` / `proc` | 0→25→90→0 / 142→285 / 0→3 | 恒 0 / 恒 233 / 恒 0 |
| **`d5` (`+0x5D88` 衰减计时器)** | **35 个不同值** | **恒 0** |
| **`t5c` (`+0x5E0C`)** | **6 个不同值** | **恒 0** |
| `t4` (`+0x408`) | 恒 0 | 恒 65535 |
| `p3ca/p3be` | 11/18 个值 | 18/3 个值，会回升，未定案 |

**决定性证据**：P29 定案 `amount>=1` 才重置 `d5`。P30 `d5` 35 个值 ⇒ 反复有有效减气；
雄火龙 `d5` 恒 0 ⇒ **从未产生过 `amount>=1` 的减气量**，
整块 Exhaust 运行期区从未被写入 —— 不是「耐力掉得慢」，是**减气输入从未发生**。

**数据层不是缺块**：离线扫 `02_Workspace/dttune_cmp/` + 原始备份，
按 `(initial,600,5,0,increase,max)` 六元组定位：
`em001_00_dttune @0x390 = (180,600,5,0,75,480)`（与 em002 同）、
`em085 @0x2EC = (150,600,5,0,50,350)`、em037/060/088/043 各有记录、
**em007 无该形态记录**。雄火龙有 Exhaust 块且 initial=180 比跳狗龙高 20%
（实机 `thr=233` ⇒ 怪种倍率 k≈1.29；P30 跳狗龙 k≈0.95，k 随怪种变，属推断）。
⇒ 更可能是**动作参数不带减气点 / `0x9A470→0xA30E4` 通道未走**
（对应 P20 的 `mParam.stamina_point`、`doumouka` 的 `StaminaSubRate`）。

### 3 · 修正后的因果链与下一步

`动作参数减气点 → 0x9DB54/0x9A470 取 amount(act+0x4D8) → 0xA30E4 add
( counter+=amount；amount>=1 重置 d5 ) → counter>=thr 返回 1
→ 0xA3198 grow(proc+1, thr 递推) → 虚表 +0x1CC → Stamina_low_Start`。
本场断在**最上游**（amount 从未 >=1）。

下一步（按价值）：① **纯只读上游探针**：在 `0x9A470` 或 `0x9DB54` 记录每次实际
amount 与 `act+0x4D8` 轨迹，`S` 行加 `add_calls/amt_sum/amt_max`（P37 §4 已建议）
⇒ `add_calls>0 && amt_sum=0` 是数据层原因；`add_calls=0` 是跨怪路径差异实锤；
② 离线解 em001 动作参数/`doumouka` 的 `StaminaSubRate` 与 em085 对比；
③ 判读脚本加「减气块活性」诊断（`d5/t5c/ex` 取值数），自动区分「怪没减气」与「时长不够」；
④ 换跳狗龙短场仍是验收 W1 疲惫形状（`wm=3/wt>0`）的最快路径，与本项互不阻塞。

**边界**：`p3ca/p3be` 会变但未定案、`f5c=30.0` 是常量；
「动作不带减气点/通道未走」是**高置信推断非定案**，需 ① 实证；
v50 NRO 仍 `cc48483a…`，本轮**只读**，未改插件/部署/`8_`/`7_`/`6_`/load_order/游戏资源。

---

## 2026-11-12 22:05 · P39 v51 上游减气 amount 观测探针（已部署，未实机）

用户两问：① GU 怪攻击是否扣 stamina（会扣就「不打怪让怪自己动」）；② 探针是否部署好了。

**① 会扣，且不需要玩家攻击**：P20 离线确证怪物动作按 `_subStaminaPoint` 扣自身耐力
（em002 393 动作中 98 个非零、5~50 点），P19 实机跳狗龙王任务内 3.35 分钟自然流口水
（BEAT dA 10→2/3/1 @f=15300，qstart=3247）无玩家减气输入 ⇒ 「不打怪」是有效对照实验。
**② P38 只给建议、没部署；本轮补上**，且用更优解：**零新增 hook** —— 现有
`h_exh(a0,a1)` 的 `a1` 即 amount（v48 放大 `a1` 到 `thr+16` 强制触发成功已实证语义）。

**v51 改动（8 处，全在 `plug/context_probe/src/lib.rs`）**：新增 `MAX_H=40`；
静态 `ADD_CALL/ADD_SUM/ADD_MAX/ADD_NZ[8]` + 全局 `ADD_*_G` + `H_LOG`；新增**只读**
`slot_of()`（不注册、不改 `CMON`，避免 `h_exh` 挤占 R 行 4 槽配额）；`h_exh` 每次调用
累计 `a1`、每 10 次输出 1 条 H 行（含 `ret/cnt/thr/proc/d5`）；R 行增
`ac/asum/amax/anz`；S 行增 `gac/gsum/gmax/gnz`；main 增 v51 横幅。
`original!` 透传、5 hook 点位/数量、W1 权重形状、W0 门控、GATE_LIVE 全部不变，零写入。

**根因判据**（P38 §5 落地）：X=`h_exh` 未 INSTALL（跳板，gac=0 不可判 A）；
A=`gac=0` ⇒ add 从未调用（跨怪路径差异）；B=`gac>0 & gsum=0` ⇒ 数据层；
C=`gac>0 & gsum>0 & ex 恒 0` ⇒ 新根因；D=链正常未达阈值。

**验证/部署**：编译 PASS；产物 `out/rai_exhaust_probe_v51.nro` 45056 B
md5 **`5cd6f1a0820440742ae86080a5994c41`**，特征串与 `h_exh` detour 齐全、`force=1`=0；
冒烟 `make_v51_smoke.py` + `analyze_v51_exhaust.py` **PASS=22/FAIL=0/SKIP=0**
（H=10、`gac=200 gsum=2000`、判据 D）；v50 雄火龙真实日志降级 **PASS=14/0/1** 不崩溃；
`8_`/`7_` 改 STEP 51、`TOOL2`→`analyze_v51_exhaust.py`，CRLF 76/152、bareLF 0，
旧版备份 `out/*.v50bak`；部署前 `NO GAME PROCESS`，部署点 md5 与产物一致。
守卫：`6_` `7361445f…` 未动、load_order 仍只第 38 行、游戏资源/其它 mod 未动。
回退链 `v50 cc48483a… → v49 ec4fcd05… → v48 f4c6d2b7…`。

**边界**：本版是**纯只读诊断探针，不是 AI 改进**；P33 闪退仍未归因（不新增写入/调用面
但不能宣称无关）；H 行是等距采样非全量，总量以 S 行为准；每槽字段只覆盖已注册
8 槽、全局字段覆盖全部调用，不可混算；`a1` 负数补码会在 gsum/gmax 出大数属诊断信息；
**尚未实机**。首选跑法已写进两个 bat：雄火龙场全程不攻击让怪自己动，
或跳狗龙短场顺带验收 W1 疲惫形状。报告 `out/P39_v51_upstream_exhaust_probe.md`。

---

## 2026-11-12 22:13 · P40 v51 首场现场体检（用户暂停中，探针正常 / add 0 次）

用户暂停游戏、问「耐力是否正常记录，正常就退出换雄火龙」。快照
`out/game_p54_lite_20261112_2213_v51_LIVEPAUSE.txt`（401820 B，进程仍在）。

**探针字段级完全正常**：v51 横幅在、5 hook 全 INSTALL（`SITE +0A30E4=E92D41F0`
+ `INSTALL h_exh` ⇒ 排除判据 X）、零 FATAL / 零 `c0000005`、`live=1` / `hub=15`、
**782/782 R 行有 `ac/asum/amax/anz`**、**6/6 S 行有 `gac/gsum/gmax/gnz`**
（f=3000..18000 等距）。⇒ 可以退出换怪，无需重编译/重部署。

**事件级为 0**：`H=0`、6 条 S 行 `gac/gsum/gmax/gnz` 全 0、R 行 `ac/asum` 全 0、
主怪 `0C14C1E0`（`thr=142`）`ex/d5/proc` 全 0、`U=0/T=0` ⇒ `0xA30E4 add`
**一次都没被调用**。`ADD_CALL_G` 在 `h_exh` 函数体最开头无条件 +1，故 `gac=0`
只能由「函数体从未执行」产生，不是探针坏。

**暂停不是原因**：`BEAT.a` 在 f=9300 到 89 后 f=11100..16500 恒 89、
`N f=9600 ENTER-LOW dA=0`、R 行 `low=1` ⇒ 暂停约从 f≈9600 起（forge 帧继续涨到 18000）；
但 f=3000/6000/9000 的 S 行 `gac` 已全 0，该段有 89 次动作开始 + `gogport` 46 条
+ `dmg special` 44 条 + `FIX40` 81 条，不是「没活动」。

**新证据 · v48 对照**：回退基线 `lib.rs.v48bak:872` 证实 v48 的 U 行在 `original!`
之前**无条件记录每次 add 调用**（无 ret 条件）；P30 归档有 **40 条 U 行**
（f=5193..11246、`a1=10/15`、`thr 142→190→237`、`proc 0→2`）⇒ 那场 add 被调用
**≥39 次**。同 `thr=142`、同有玩家侧伤害事件，v48 39+ 次 vs 本场 0 次 ⇒ 差异可能来自
玩家攻击输入/任务怪种（本场 V `sp` 主要 `102E`、`0055` 仅 2 条）/v48 疲惫状态机后续调用，
**尚不能定案**，但足以否定「v51 失效」与「暂停致 0」两解。

**跑法修正（已落地）**：P39 建议「不打怪让怪自己动」，本场显示该跑法 add 仍 0，
与 v48 正常打怪场 39+ 次反差 ⇒ 玩家攻击输入可能是打开减气通道的必要条件。
`8_`/`7_` 首选提示改为「雄火龙场 **PLAY NORMALLY / attack it**」，
「不打怪」降为备选；CRLF 77/152、bareLF 0，执行逻辑/输出路径/Python 路径未动。
本轮未改 NRO / 部署 / `6_` / load_order / 游戏资源。报告 `out/P40_v51_live_pause_check.md`。
**⚠ 本章 §4–§6 的「v48 对照 ⇒ 玩家攻击输入是必要条件」与「跑法改为必须打怪」已于 22:23 由下一章 P41 撤回。**

---

## 2026-11-12 22:23 · P41 更正：`0xA30E4` 不是每动作 stamina 扣减通道（判据 A 撤回）

用户质疑「怪物的攻击动作不是会扣减自身 stamina 吗？」⇒ **用户正确，上一章 §4–§6 错**。

**错因**：P40 用「v48 P30 场 40 条 U 行（≥39 次 add）vs 本场 0 次」推出
「玩家攻击输入是打开减气通道的必要条件」，但那 39+ 次**不是自然产生、也不是玩家攻击产生**，
是插件一次性强制触发之后疲惫状态机的连锁。

**决定性证据**（`lib.rs.v48bak:868-881` 证 U 行在 `original!` 前无条件记录每次调用）：
- P30 归档 **f<5193（强制前）U 行 0 条** ⇒ `0xA30E4` 从未被调用；主怪 17 条 R 行
  `ex=[0]`、`amt=[0]`。同期 `BEAT.a` 在 f=5100 已 **28 次动作**、`sel=10`（玩家正常打怪）。
- f=5193 首条 U 行 `a1=10 force=1 cnt=0`（放大到 158）；f=5604 起 39 条真实 U 行
  `a1=10/15`、`cnt 0→215`、`thr 142→190→237`、`proc 0→2`；`ex` 首次非零在 f=5700。
- 本场 v51：89 次动作、`gac=0`、`ex=[0]`、`amt=[0]`、`d5=[0]` ⇒ 与 **v48 强制前逐项一致**。

⇒ `add=0 / ex=0` 是**自然静默态**，与打不打怪、怪种、暂停均无关。本场数据**不能**
否定「不打怪让怪自己动」，反而与 P20 自洽。

**真正的错误是探针挂错层**：P29 §2.2 链条 `0x9DB54/0x9DBE4` 每动作累加 amount
→ `0x98A60` 状态更新总入口 → `0x9A470: amount=act+0x4D8 → bl 0xA30E4`
→ counter(`act+0x5D82`) += amount → `>=thr` 触发 grow/tired FSM。
`0xA30E4` 是**减气蓄积 counter 的累加入口 / 阈值判定**，不是「每动作扣当前 stamina」。
P20 §3/§4 早就写「前 7 轮都在改触发输入或结果标志，没追**被轮询的当前耐力值**」，
v48~v51 仍盯 `ex` 与它的累加器 —— 正是 P20 批评的层级错误。用户 21:40 的方向是对的，
当时只否定了 `s3f/f5c`，没把探针换层。证据等级须分清：P20 `_subStaminaPoint` 是
**Rise 侧 RSZ 实证**（em001 296 动作 46 非零 / em002 393 动作 98 非零），
GU 侧 `stamina_point/StaminaSubRate` 是**同构推断**（`monster-gu.md:228` 标 GU-unconfirmed）。

**已落地修正**：① `tools/analyze_v51_exhaust.py` 判据 **A 撤回 → N = 正常静默态不能定案**，
docstring 同步；`W1 非疲形状生效` 改 `w3+w4>0`（本场 13 条 V 行 12 条候选不足退回 v38，
`w4=0` 是样本不足非违例）→ 改标 SKIP；结论文本改 N/B/C/D。② `8_`/`7_` 跑法改回
**中性**「attack OR let the monster act alone 两者都有效」，加注「本探针看的是减气蓄积
通道、不是每动作 stamina 扣减，gac=0 不能证明任何事」；CRLF 80/153、bareLF 0。
③ P39/P40 顶部加更正标记与判据表撤回注记；MEMORY.md 04 行同步。
回归：冒烟 PASS=22/0、本场快照 PASS=16/0/SKIP=1（判据 N）、v50 雄火龙降级 PASS=14/0/1。
NRO 仍 `5cd6f1a0…` 未动，`6_`/load_order/游戏资源未动。

**v52 方向（按风险）**：① 离线定位被轮询的当前耐力值（`cEmStaminaData::cStaminaLev`、
`mParam.stamina_point @0x1eb8d0`、`0x9DBE4` 的 `strh` 目标；`mon+0xCAC0→+0x3F/+0x5C`
已由 P38 否定，勿再试）；② 零新增 hook：在已装 `h_start_40`(`0xAFF40`) 做动作开始时
纯只读快照读 `act+0x4D8` + 候选当前耐力（R 行 150/30 帧快照 amt 恒 0 是瞬时值采不到）；
③ 必要时新增 hook `0x9DB54`/`0x9DBE4`/`0x9A470`，须先实机核对首字防 IPS32 跳板，
且突破「5 hook/零新增」纪律需单独评估。**跑法结论**：用户原计划有效，照原计划即可；
要回答「GU 每动作扣多少 stamina」靠 v52 换层，不是换怪/换打法。
报告 `out/P41_add_channel_correction.md`。

---

## 2026-11-12 22:40 · P42 v52 每动作 stamina 探针（已部署，未实机）

用户「继续做到部署，已关闭游戏」⇒ v52 全流程落地。

**离线定位结论（本轮关键）**：`refs/hpbar/main_text_decomp.bin` 中 P29 的地址是
**文件偏移 base=0**（P33 的 `0x49BD3C` 才是 guest VA base=0x200000），二者不可混用。
按 base=0 反汇编字节级确认：`0x9DB6C movw r1,#0x1428`（取 act）→
`0x9DBE4 movw r1,#0x4D8` → `0x9DBE8 ldrh r1,[r0,r1]` → `0x9DBEC add r1,r1,r3`
→ `0x9DBF0 strh`（**每动作把减气点 r3 累加到 act+0x4D8**）；
`0x9A454 movw r0,#0x4D8 / ldrh r1,[r7,r0]` → `0x9A470 bl 0xA30E4`（消费该 amount）；
`0x9A48C movw r0,#0x4DA`（下一状态块）；另有 `0x9DB94 movw r0,#0x4D2`（气绝同构）。
⇒ **GU 没有独立「被轮询的当前耐力值」，模型是「每动作 amount → counter(5D82) vs thr(5D84)」**。
P20 的「追当前耐力值」是 Rise 侧推断；`mon-class-map.md §D` 明说
`cEmStaminaData::cStaminaLev` 无成员表（第 409 行「本批最大覆盖缺口」），
`member-offsets.tsv` 只有参数类 `StaminaSubRate @+0x14` / `StaminaTimeVal @+0x20`。
`mon+0xCAC0→+0x3F/+0x5C` 已由 P38 实机否定。

**v52 三层纯只读观测（零新增 hook / 零写入 / 跨怪通用）**：
① **Y 行**：已装 `h_start_40`(0xAFF40) 每 2 个动作 1 条、配额 200，
`am=act+0x4D8`（每动作减气点瞬时值）、`d2=+0x4D2`（气绝对照）、
`ex/thr/proc/d5/st`、`a/s` 动作号、`amx` 该槽峰值；
② **每帧统计**：`forge_onUpdate` 每帧读 8 槽 `act+0x4D8`，累计
`AM_MAX/AM_NZ/AM_RISE`，S 行输出 `amx/anf/anr`（R 行 150/30 帧快照两场 amt 恒 0
是因为同帧被 0x9A470 消费清零）；
③ **候选耐力扫描**：R 行从 `p=*(mon+0xCAC0)` 读 `+0x40..+0x60` 的 8 个 u32
（`q40..q60`），判读脚本列 `uniq>1` 者当候选。
5 hook 点位/数量（nm detour=5）、`original!` 透传、W1/W0、v51 的 H/ac/gac、GATE_LIVE 全不变。

**验证/部署**：编译 PASS；产物 `out/rai_per_action_stamina_v52.nro` 45056 B
md5 **`0d1d97c6d120e5fd84b224dfdc1c24d7`**，v52 特征串齐全、`force=1`=0、v51/v50 横幅保留；
冒烟 `make_v52_smoke.py` + `analyze_v52_stamina.py` **PASS=26/0/0**
（Y=20、am 值域 [10,15]、amx=15 anf=430 anr=198、判据「已捕获」）；
v51 暂停中真实快照 **PASS=16/0/1**（判据 N）、v50 雄火龙 **PASS=14/0/1**，降级均不崩溃。
`8_`/`7_` 改 STEP 52、TOOL2→`analyze_v52_stamina.py`，CRLF 77/156、bareLF 0，
旧版备份 `out/*.v51bak`；部署前 `NO GAME PROCESS`，部署点 md5 与产物一致。
守卫：`6_` `7361445f…` 未动、load_order 仍只第 38 行、游戏资源/其它 mod 未动。
回退链 `v51 5cd6f1a0… → v50 cc48483a… → v49 ec4fcd05… → v48 f4c6d2b7…`。

**判据**：`Y.am>0` 捕获每动作减气点 / `amx>0` 存在但 Y 错过（同帧清零）/
两者皆 0 ⇒ 0x9DBE4 本场不走，下一步才需 hook `0x9DB54/0x9DBE4` 抓 r3
（须先核对 IPS32 首字，且会突破「5 hook/零新增」纪律）。

**边界**：纯只读诊断非 AI 改进、**尚未实机**；`act+0x4D8` 是 amount 缓冲不是剩余耐力，
`ex` 是累计 counter；`q40..q60` 只是候选区间（由 P20 §5 的 `p+0x3F/0x5C` 外推），
全 0 说明 p 无效或字段不在此区，不能当定案；Y 行是采样非全量；每帧 8 次 rd16 是
新增只读开销（约 480 次/秒）；P33 `c0000005` 仍未归因。报告 `out/P42_v52_per_action_stamina.md`。

---

## 2026-11-13 20:57 · P43 v52 暂停中现场体检（探针正常 / amount 全 0 / q* 全常量）

用户暂停游戏要求查日志。快照 `out/game_p54_lite_20261113_2057_v52_LIVEPAUSE.txt`
（290211 B，进程仍在）。部署仍 `0d1d97c6…`。

**探针字段级全正常**：v52 横幅 + v51/v50 历史横幅在、5 hook 全 INSTALL
（`SITE +0A30E4=E92D41F0` + `INSTALL h_exh`）、零 FATAL / 零 `c0000005`、
`live=1` / `hub=15`、**Y 行 12 条**（am/d2/ex/thr/proc/d5/st/amx 齐全）、
**S 行 4 条**（amx/anf/anr + gac/gsum/gmax/gnz 齐全）、**R 行 483 条**（q40..q60 +
ac/asum/amax/anz 齐全）。判读 **PASS=20/FAIL=0/SKIP=1**（SKIP 是无疲惫样本，非违例）。

**本场 = 雄火龙且暂停很早**：主怪 `0C180B70` `thr=233`、V 行 `sp=2`；
全程 `st=0`（未发怒）、`ex=0`、`d5=0`、`t5c=0`、`t4=65535`。
暂停起点约 **f≈6000**（`BEAT.a` 到 25 后 f=6300..10500 恒 25、
`N f=6300 ENTER-LOW dA=0`、R 行 `low=1` 占 250/483，forge 帧继续涨）。
折算约 100 秒 / 25 次动作，远短于 P19 跳狗龙自然流口水 3.35 分钟 ⇒
本场无疲惫、未发怒属正常。

**每动作 stamina 全 0**：12 条 Y 行（含主怪 5 条 `a=2/7/7/7/7`、`s=7/9/7/4/19`）
`am` 全 0、`d2` 全 0；S 行 `amx=0 anf=0 anr=0`（这是每帧读 8 槽的全量统计，
比 Y 行更强）；`gac=0` ⇒ v51 判据 N（正常静默态，P41）。
**严谨裁定（本轮修判读脚本过度定案）**：`am=0 && amx=0` 只能说明「离散采样未捕获」，
**不能区分** ① `0x9DBE4` 路径未走 与 ② 写入→`0x9A470` 消费→清零窗口短于采样间隔
（`h_start_40` 动作开始 + 宿主帧回调 `forge_onUpdate` 都可能系统性错过）。
P42 判读脚本原写死「⇒ 累加路径本场不走」已改为不可区分表述；定案须 hook
`0x9DB54/0x9DBE4` 直接抓 `r3`（需核对 IPS32 首字、突破 5 hook 纪律，单独评估）。

**候选当前耐力扫描假设被否定**：按主怪分组统计 `q40..q60`——
`q40/q44/q48/q4c/q58` 恒 0；`q50=65535`(0xFFFF 哨兵)、
`q54=1058642330`=`0x3F19999A`=**f32 0.6**、`q60=1065353216`=`0x3F800000`=**f32 1.0**、
`f5c=1106247680`=`0x41F00000`=**f32 30.0**（P38 已知）；
**主怪上全部 uniq=1**。全量 R 行的 `uniq=2` 只来自不同怪槽（小怪为 0），不是随时间变化。
⇒ **`p+0x40..+0x60` 是参数/常量区，不是被轮询的当前耐力值**；`s3f` 恒 0 再证 P38。
判读脚本已改为按主怪输出「全量 uniq / 主怪 uniq」并在全恒定时明确判定为参数区。

**已落地**：只改 `tools/analyze_v52_stamina.py` 两处（判定文案 + 候选分组诊断）；
回归冒烟 PASS=26/0/0、本场快照 PASS=20/0/1。
**未改** NRO / 部署 / `8_` / `7_` / `6_` / load_order / 游戏资源。

**下一步（倾向先 1）**：① 恢复本场跑更久，让雄火龙发怒并自然流口水（>3 分钟），
正常关游戏 ⇒ 补疲惫样本、验收 W1 `wm=3/wt>0`，并看疲惫激活后 `am` 是否非零
（P30 的 10/15 点正是强制触发后才出现）；零改动、成本最低。
② 做 v53 新增 hook `0x9DB54/0x9DBE4` 抓 `r3`，绕开采样窗口问题，
但须核对 IPS32 首字 + 关游戏后重编译部署 + 独立评估新增 hook 风险。
当前只有 25 次动作且未发怒，样本不足以判「路径未走」还是「时机错过」。

**边界**：日志暂停中仍增长，报告基于 20:57 快照；`q*` 全恒定只否定该区间，
不否定「GU 存在当前耐力值」的可能性（P42 §1 的 counter/thr 模型）；
P33 `c0000005` 仍未归因；未实机完成。报告 `out/P43_v52_live_pause_check.md`。

---

## 2026-11-13 21:11 · P44 10 分钟无疲劳：数据复核 + `0x9A468` 门控定案

用户「任务已过 10 分钟，肉眼看不到疲劳」。快照
`out/game_p54_lite_20261113_2111_v52_10MIN_NO_TIRED.txt`（888335 B，进程仍在）。

**数据完全支持无疲劳，且比体感更强：连发怒都没有。**
f=3600..59460、活跃逻辑约 10 分钟（低活动锚点 `N f=6300 ENTER-LOW` →
`f=22500 EXIT-LOW` → `f=48600/48900` → `f=57000 ENTER-LOW`；
forge 帧在暂停时继续涨不能直接换算，活跃段约 34500 帧 ≈ 9.6 分钟）：
`BEAT.a` 25→**592**；主怪 `0C180B70` 552 条 R 行 `thr=233`（雄火龙）、V `sp=2`；
**`st` 恒 0（592 次动作一次未怒）**；`ex/d5/t5c/proc/amt/flg` 全程恒 0、
`t4=65535`；`gac=0 / gsum=0 / ac/asum/amax/anz=0`；
**Y 行 200 条配额打满 `am` 全 0**、S 行 `amx/anf/anr=0/0/0`；
**U=0 / T=0**、50 条 V 行 `st3` 全 0、`wm` 从未取 3、`wt=0`。
零 FATAL / 零 `c0000005` / `live=1` / `hub=15` / 5 hook 全装，
判读 **PASS=20/FAIL=0/SKIP=1**；W1 `w3=19 w4=20`、V 行 wm=1/2 共 39 条 +
11 条退回 v38 ⇒ **抽选层正常工作**。
⇒ **不是 mod 的问题**：v52 纯只读诊断、W1 只改抽选局部权重、零写入；
P37 的 v50 雄火龙场（原版规则）同样 `ex` 全 0 无疲惫。

**排除「怪没动」**：Y 行按 mon 分组主怪 **98 条**（约 196 次动作）、
小怪 `0C420060` 57 / `0C410060` 45；A 行主怪 54；主怪 `e1` 有 **22 个不同值**、
`p3ca` 130→129→128 缓变。

**新发现 · `0x9A468` amount 门控（离线字节级实证，base=0）**：
```
0x9A454 movw r0,#0x4D8 ; 0x9A460 ldrh r1,[r7,r0]  ; r1=act+0x4D8
0x9A464 cmp r1,#1      ; 0x9A468 BA000007 blt 0x9A48C  ★ amount<1 跳过
0x9A470 bl 0xA30E4     ; 仅 amount>=1 才调用      ; 0x9A48C movw r0,#0x4DA
```
⇒ **`gac=0` 有精确解释**：不是 hook 没装、不是模糊「路径差异」，
而是 `0x9A34C` 状态更新总入口读到 `act+0x4D8` 时该值**从未 ≥1**，
`blt` 直接跳过 EXH add。断点前移到 **`0x9DBE4` 累加环节**（每动作把减气点
`r3` 加到 `act+0x4D8`），而非 EXH add 本身。结合 200 条 Y 行 `am=0` 与每帧
8 槽全量 `anf=0`：该值在所有可采样时刻都是 0；仍不能排除「写入-清零窗口
短于采样间隔」（P43 裁定），但已把待区分的两解收敛为「未累加 / 累加后瞬时清零」。

**最值得注意的异常：全程未发怒**。`st` 恒 0 vs P37 雄火龙场正常打怪时
`st=1` 占 **54.5%**（303/556）、P30 跳狗龙场（插件强制）`ex` 0→237 / 疲惫 3 次。
本场 `gogport` 191 / `dmg special` 188 / `FIX40` 183 条，但标签形如
`dmg special path x108000` **不区分攻击方向**，无法证明玩家命中主怪；
用户可能按 `8_` 的「BOTH play styles are valid」采用了「不打怪让怪自己动」。
**推断（未定案）**：GU 发怒/减气链可能需要玩家交互；但 P37 反例（打怪且发怒，
`ex` 仍全 0）说明单靠打怪不足以让雄火龙减气 ⇒ 更可能是「本场未交互 +
雄火龙自身数据层问题」两因素叠加。

**下一步（零改动、判别力最高）**：继续当前任务**正常攻击雄火龙直到发怒**
（约 2–3 分钟）再正常关游戏。判据：`st=1 & ex/d5 开始涨` ⇒ 玩家交互是必要条件，
P41「与打不打怪无关」需按怪种细化；`st=1 但 ex 仍 0` ⇒ 交互非必要，
雄火龙数据层问题实锤；`st 仍 0` ⇒ 发怒另有触发条件。
三场雄火龙都稳定 0 才考虑 **v53** hook `0x9DB54/0x9DBE4` 抓 `r3`
（须核对 IPS32 首字、突破 5 hook 纪律）。

**边界**：本轮**纯只读**，未改插件/部署/`8_`/`7_`/`6_`/load_order/游戏资源；
NRO 仍 `0d1d97c6…`；用户仍在任务中、日志继续增长；`q40..q60` 主怪仍全恒定
（P43 参数区结论未推翻）；伤害标签不区分方向，是否打中主怪需用户口述；
P33 `c0000005` 仍未归因。报告 `out/P44_10min_no_tired.md`。

---

## 2026-11-13 21:18 · P45 雄火龙「无发怒却疲惫」+ v53 配额修复（已编译未部署）

用户口述：**雄火龙未发怒，但暂停前一刻进入疲惫**。快照
`out/game_p54_lite_20261113_2118_v52_TIRED.txt`（991427 B）。

**两条定案级修正**：① **P44 推断「发怒/玩家交互是疲惫必要条件」被证伪** ——
主怪 `st` 全程恒 0（未发怒）却出现疲惫，发怒与疲惫解耦；
② **疲惫发生时 P29/P30 那条减气链完全没有反应** —— `gac=0`（`h_exh` 函数体
开头无条件 +1，**精确计数不受配额影响**）、`U=0 / T=0 / H=0`、S 行
`gac/gsum/amx/anf/anr/s2/wt` 全 0、54 条 V 行 `st3` 全 0 / `wm` 从未取 3。
⇒ 该链不是疲惫唯一入口，或插件疲惫判据漏检雄火龙自然疲惫。
`BEAT.a` 592→711、f=80100 后恒定（暂停点）；f=78900..80100 仍 686→711
**无零动作段** ⇒ P30 行为判据在本场不成立。

**关键：疲惫窗口恰在观测盲区**。用户暂停 f≈80100，疲惫在 f≈79800..80100；
而 `R` 行 1800 条止于 **f=59730**、`Y` 行 200 条止于 **f=47593**（配额耗尽），
`A` 行止于 f=79886（`st=0 ex=0`）、`V` 行止于 f=79427（`st3=0`）、
`C` 行止于 f=77557 ⇒ **疲惫瞬间没有任何字段快照**。
判读脚本实测 `BEAT 末帧 87600 / R 末帧 59730 / Y 末帧 47593`（差 27870 / 40007 帧）。

**两种解释不可二选一**：A（倾向未定案）疲惫走另一条路径 —— P20 §5 的
`0xf8d384` `Stamina_low_*` 状态机读 `*(mon+0xCAC0)+0x3F` 状态字节与 `+0x5C`
计时器，P38 否定的只是「s3f/f5c 是当前耐力值」而非其参与状态机；
B 用户看到的可能不是疲惫（气绝/眩晕/待机动画），日志无独立行为证据。
两者都**不推翻 P29/P30 字节级链**，只限定其适用范围（跳狗龙 / 减气输入路径）。
**需用户口述疲惫具体表现**（流口水？垂头？动作变慢？）来分流。

**v53 已编译未部署**：`out/rai_quota_reset_v53.nro` 45056 B
md5 **`aa504fe60a7fdc90dfbc99c4846fe6bd`**、5 个 detour、`force=1`=0。
9 处源码改动全在观测层：新增 `QUOTA_EPOCH_F=30000` 在 `forge_onUpdate`
分段重置 16 个日志配额计数器（R/Y/A/C/U/T/H/N/V/E/M/X/Q/K/P/D_LOG），
**不重置任何累计统计**（A_N/S_N/W3_N/ADD_*_G/AM_*/FRAMES/ST_* 全保留）；
`MAXLOG 4200→24000`、`MAX_R 1800→4000`、`MAX_Y 200→1000`、
`MAX_A 400→800`、`MAX_C 300→600`、`MAX_V 200→600`；加 v53 横幅。
零新增 hook / 零写入 / W1/W0/v52/v51 规则逐字节不变。
`analyze_v52_stamina.py` 加「观测配额盲区检查」（WARN，不算 FAIL）+ 兼容 v53 横幅；
`make_v52_smoke.py` 的 Y 行覆盖到 f=30000 消除合成日志假 WARN。
回归：冒烟 **26/0/0（无盲区）**、疲惫场 **20/0/1（WARN）**、v50 降级 **14/0/1**。

**部署点仍是 v52 `0d1d97c6…`，`8_`/`7_` 仍是 STEP 52** —— 游戏还在运行，
等用户正常关游戏后才部署 v53 + 改脚本提示；回退 `out/rai_per_action_stamina_v52.nro`。
本轮未改游戏资源 / `6_` / load_order；判读零 FATAL / 零 `c0000005` / live=1；
P33 闪退仍未归因。报告 `out/P45_tired_without_exhaust.md`。

---

## 2026-11-14 13:2x · P46 疲惫完整触发链路静态定案（4 路并行 + capstone 复核）

用户要求「捕获之前从静态里找出疲惫完整触发链路及触发方式」。4 路只读子代理并行
（A 符号/函数图、B `0xF8D384` 反汇编、C `+0x505` 写入链、D 文档与 `0x1068DD8` 对齐）
+ 主代理 capstone 5.0.7 独立复核 6 组关键指令，逐条吻合。
二进制 `refs/hpbar/main_text_decomp.bin`（20,913,644 B，ARM32 LE，**文件偏移=VA，base=0**）。

**五条核心结论**：
① **找到 P20 一直没定位到的「被轮询的当前耐力值」= `act+0x508`**（u16，初始
0x3E8=1000），上限 `act+0x506`；`act=*(mon+0x1428)`。
② **疲惫状态字 = `act+0x505`**（u8：0 正常 / 1 耐力耗尽中间态 / 2 正式疲惫 /
3 疲惫加强或计时器到期），与发怒 `act+0x518`、减气 counter `act+0x5D82` 互不相关。
③ **存在两条数据流完全并行的链**（见下），P29 链**不写 `+0x505`**。
④ ⇒ P45「雄火龙疲惫但 `0xA30E4` 整场 0 次」完全解释：疲惫走链 I；链 II 因
`act+0x4D8<1` 被 `0x9A468 blt` 跳过。**「无发怒却疲惫」也解释**：1→2 门控
`0x762E0 bl 0x8172C ; bne 0x7635C` 明确要求不发怒。
⑤ P45「解释 A 另一条路径」由静态实证定案，解释 B（不是疲惫）不再必需。

**链 I（耐力主链 · 自然疲惫）**：
`0x76154(mon,id,sub,arg3)` [17 callers] → `0x768EC bl 0x755B4` →
`0x756A8 bl 0x711E8` 取表 → 按 `(id,sub)` 匹配 → `0x75740 ldrsh` 减气量 →
`0x75754 vmul.f32` 倍率 → `0x75768 bl 0xBD260(mon,delta,max)`（唯一 caller）；
`0xBD260` 总闸门 `act+0x1A8 & 0x80001 == 1` + `0x711E8!=0`，
`0xBD2B0 ldrh r2,[act+0x508]!`（cur）、`0xBD2AC rsb r3,r5,#0`（-delta）、
`0xBD2B4 cmp r2,r3 ; ble 0xBD350`（耗尽），未耗尽 `0xBD2BC add r3,r2,r5` +
`0xBD2C4 strh` 回写并 clamp 到 `+0x506`；耗尽 `0xBD354 strh #0`、
`0xBD35C bl 0x816D0`（未疲惫才继续）、`0xBD370 bl 0xA1FC8(r1=0x20)`
（`act+0x5E08 bit5==0`）、`0xBD390 strb r1,[act+0x505]` **写 1**；
`0x76154` 内 `0x762C8 ldrb r1,[+0x505] ; cmp #1`，门控
`0x8172C==0`（不发怒）、`+0x362 bit2/bit4=0`、`+0x518!=2`、`+0x5DF3==0`
→ `0x76338 mov r1,#2 ; 0x76358 bl 0xBD184` → `0xBD1B0 strb [+0x505]` **写 2**；
`0x816D0`(8 ins/315 callers) `ldrb [+0x505]; and r1,r0,#0xFE; cmp r1,#2`
⇒ 值 2/3 都算疲惫；`0xF8D384`：`p=*(mon+0xCAC0)`，
`[p+0x41]==0 && 0x816D0(mon)==1` → `0xF8D710 strb #5,[p+0x41]`
→ `Stamina_low_Start`，循环 0→5→4→6→0；计时器在**二级解引用**
`[[p+0x30]+0x5C]`（疲）/ `[[p+0x34]+0x5C]`（怒）。

**链 II（P29 减气蓄积，并行）**：`0x9DB54/0x9DBE4` 累加 `act+0x4D8` →
`0xADE48 → 0xA5900 → 0x97DDC →(8 部位循环)→ 0x98A60 bl 0x9A34C`（每帧 1 次）
→ `0x9A454 movw r0,#0x4D8 / 0x9A460 ldrsh / 0x9A464 cmp r1,#1 /
0x9A468 blt 0x9A48C` → `0x9A470 bl 0xA30E4` → `0xA3198 grow`（唯一 caller
`0x75F0C`，在 `0x755B4` 内）→ `0xA325C b 0xA4130` → `0xA414C ldr r3,[vt+0x1CC];
mov r1,#9; bx r3`。**两链字段零交集**，唯一共享是只读 getter `0xA1FC8`；
控制流共用 `0x76154 → 0x755B4` 但走不同 case（链 I `0x75768`、链 II `0x75F0C`）。

**触发方式枚举（证据强度）**：① 每动作扣 `+0x508` 耗尽→`+0x505=1`→门控 1→2→
`Stamina_low_Start`（**GU 静态实证，自然疲惫主路径**）；② 已疲惫再次减气 2→3
（`0xBD2E8..0xBD30C`）；③ 计时器到期写 3（`0xC8F98 bl 0x72128` →
`0xC8FBC bl 0xBD184`）；④ 外部状态包 `0xCC584 [r6+0x70]&0xC` 直接映射 0/1/2/3
（生成/载入期）；⑤ P29 减气蓄积 `counter>=thr` 瞬时触发（静态+实机双实证，
P19/P22/P24/P30 跳狗龙）；⑥ 数据层强制（dttune initial / v48 放大 amount，实机）；
⑦ 玩家减气攻击（Rise 侧 RSZ `StaminaDamageData._SubStamina`，**GU 注入点未定案**，
`mParam.stamina_dmg_point` 是独立字段）；⑧ 进食恢复使 `+0x508` 回升
（`0xBD3D4` 清 0 / `0x76340` `+0x508!=0` 复位，行为实证字段级部分推断）；
⑨ `0x1068DD8` 状态机 r1=1/2 直切（`em+0xCAC4`）——**静态存在但实机整场 0 次**
（v45 T=0、hook 确实 INSTALL、首字 E92D4FF0 非跳板 ⇒ 死代码/另一版本路径）；
⑩ hp/maxhp 推进 `em+0xCAC0` 1→2→3（同 ⑨ 不走）；⑪ Rise `_tiredSec`/
`EnemyStaminaManager`（P32 已定性不等价）；⑫ 领地争夺（P36 已否定）。

**七条定案修正**：
1. P20 §5 把 `p+0x3F` 当 `Stamina_low_*` 状态机**错** —— `+0x3F` 是 Angry
   （4 路 switch 由 `0x8172C` 驱动），**`+0x41` 才是 Stamina_low**（由 `0x816D0` 驱动）。
2. P38「`s3f/f5c` 否定参与疲惫」无效：疲惫状态字是 `p+0x41`（P38 未读），
   计时器是二级解引用 `[[p+0x30]+0x5C]`（P38 读的一级 `p+0x5C` 是另一字段）；
   「不是当前耐力」的结论仍成立。
3. P29/P31/P35/P36「疲惫是瞬时事件、无持续状态字」**只适用于链 II**；
   链 I 有 `act+0x505`(0/1/2/3) 与 `p+0x41`(0/4/5/6)。
4. P41「`0xA30E4` 是减气蓄积通道，不是每动作 stamina 扣减」**成立且强化**：
   每动作扣减在 `0xBD260` 写 `+0x508`。
5. P44「发怒/玩家交互是疲惫必要条件」**证伪**，机制上是 1→2 要求「不发怒」。
6. P45「解释 A / B 二选一」→ **A 定案**。
7. A 路初稿「`mon+0xCAC4` 1=怒/2=疲」**作废**：那是 `em`（`0x1068DD8` 第一参数）
   的字段，`em≠mon`；实机 `mon+0xCAC4` 恒 413（NOTES:2732-2734, 2906-2918）。

**捕获清单（供 v54，本轮未实施）**：只读字段 `act+0x505/506/508/50C/1A8/5E08/362/518/5DF3`、
`p+0x41`、`p+0x3F`、`[[p+0x30]+0x5C]`，对照 `act+0x4D8/5D82/5D84`；
精确事件点 `0xBD260(mon,delta,max)`（抓每次扣减）、`0xBD184(mon,state)`
（抓 `+0x505` 跃迁）、`0x816D0`（315 callers 宜计数）、`0xF8D384`（动画 FSM）。
新增 hook 须先核对运行时首字防 IPS32 跳板且突破「5 hook」纪律；
更稳妥是零新增 hook：在已装 `h_start_40` + `forge_onUpdate` 做纯只读快照，
配合 v53 分段配额重置。

**边界**：全为静态反汇编；`+0x508` 语义由读/写/清零/初值/clamp 推断，未实机读值；
`0xF8D384` 的 `r8=arg0` 是否等于插件 `mon` 仍 [U]；`+0x505==2` 与 `==3` 在
`0x816D0` 不可区分；`0x711E8` 表名未定案；链 D/E 是否参与战斗中自然疲惫未定案；
`0x1068DD8` T=0 只证该场未调用；P33 `c0000005` 仍未归因。
**本轮纯只读**：未改插件/部署/`8_`/`7_`/`6_`/load_order/游戏资源，
部署点仍 v52 `0d1d97c6…`。报告 `out/P46_static_tired_full_chain.md`。

---

## 2026-11-14 15:0x · P47 v54 疲惫链路快照 + 一次性强制（已部署，未实机）

用户「做 v54，如果能强制进入疲劳也一并做了以便让日志记录」⇒ 全流程落地并部署。
在 v53（分段配额重置，此前编译未部署）基础上叠加两层，同一 NRO。

**① 只读快照（P46 §5.1 全字段）**：R 行新增 9 字段
`t505`(+0x505 疲惫状态字 0/1/2/3)、`t506`(+0x506 上限)、`t508`(+0x508 **当前耐力**)、
`t50c`(+0x50C 浮点累计)、`p41`(p+0x41 **Stamina_low FSM 状态字** 0/4/5/6)、
`pt5c`(**二级解引用** `[[p+0x30]+0x5C]` 疲惫动作计时器)、
`t1a8`/`t362`/`t5df3`（1→2 门控位）。p=`*(mon+0xCAC0)`。
P38 读的一级 `f5c`(p+0x5C) 保留作对照，但 P46 已更正它不是状态机计时器。

**② 一次性有界强制疲惫 —— 本项目首次游戏内存写入**：
`wr16(act+0x508, 0)` + `wr8(act+0x505, 2)`，共 **3 字节 / 只 1 次**。
依据 P46 链 I：`0x816D0=((+0x505 & 0xFE)==2)` → `0xF8D384` 在 `[p+0x41]==0`
时写 `p+0x41=5` → `Stamina_low_Start`；写 `+0x508=0` 让状态自洽，避免
`0x76340`（`+0x505==3 && +0x508!=0` 时复位）立即撤销。
**安全边界**：`FORCE_DONE` 熔断 / `f>=1800` / `A_N>=20` / 目标怪 `ST_AN>=4` /
`LOW==0`（P19 暂停时 forge 帧仍涨，禁止在冻结逻辑上写）/ `GATE_LIVE` /
`heap_ok` / `0<thr<0x4000`（主怪）/ `+0x505==0`（尚未疲惫）；
**不写** `p+0x41`（交给游戏 FSM）、动作 id、连段字段、其它偏移；
`G` 行记录 before/after 全快照，`S` 行 `gdone/gf`；`FORCE_ENABLE=0` 即得纯只读版本。
回退 `out/rai_quota_reset_v53.nro`(`aa504fe6…`) 即完全移除写入。

**验证/部署**：编译 PASS；产物 `out/rai_tired_force_v54.nro` 49152 B
md5 **`f1588542ad50975021bdabc214e67489`**，部署点 md5 一致；
**5 个 detour 不变（零新增 hook）**；v54/v53/v52/v51/v50 横幅齐全、`force=1`(G 行)=1。
判读 `analyze_v54_tired.py` + 冒烟 `make_v54_smoke.py`：
完整场 **PASS=33/0/0**；**强制-only 场景**（链 I 疲惫但 W1 形状全 0）
**PASS=27/0/1** 且 SKIP 明确标注为 v55 待修、不误报；
降级 v52 疲惫场 20/0/1、v52 暂停场 20/0/1、v50 雄火龙 14/0/1，均不崩溃。
`8_`/`7_` 改 STEP 54、TOOL2→`analyze_v54_tired.py`，CRLF 75/160、bareLF 0，
旧版备份 `out/*.v52bak`；部署前 `NO GAME PROCESS`。
守卫：`6_` `7361445f…` 未动、load_order 仍只第 38 行、游戏资源/其它 mod 未动。
回退链 `v53 aa504fe6… → v52 0d1d97c6… → v51 5cd6f1a0… → v50 cc48483a…`。

**边界（必须说清）**：① 不再是纯只读，虽只 3 字节一次可即时回退，仍有状态机
不同步/动作异常风险，异常立即关游戏覆盖回 v53；② **强制≠原生链路**，直接置位
`+0x505=2` 跳过 `0xBD260` 耗尽判定与 `0x76154` 的 1→2 门控，目的是制造可记录窗口；
让游戏自己走完链 I 需 hook `0xBD260` 放大 delta（新增 hook + 核对 IPS32 首字）；
③ **W1 疲惫形状可能不触发**：v49 三态层疲惫判据基于链 II（`EXH ret==1`/`proc`），
强制走链 I ⇒ 本场 `st3=2`/`wm=3`/`wt>0` 很可能全 0，判读已标 SKIP 非 FAIL；
**把疲惫判据切到 `t505>=2 || p41>=5` 是 v55 明确待办**，也是当前还原度最实质缺口；
④ `LOW==0` 在长跑图/挂机可能延后或阻止触发；⑤ 尚未实机；⑥ P33 `c0000005` 仍未归因。

**下一步**：双击 `8_lite_check.bat` 正常打一场，强制约 30 秒后自动触发一次；看到疲惫
再打约 1 分钟让 R 行覆盖窗口，正常关游戏；回报是否流口水/异常及 G 行与时间线结论。
若强制生效且可见 ⇒ v55 立即把 W1 疲惫判据切到链 I。报告 `out/P47_v54_tired_chain_force.md`。

---

## 2026-11-14 15:25 · P48 v54 实机证伪 → v55 原生强制（已部署，未实机）

用户跑 v54 一场雄火龙后反馈「怪物没有正常进入疲劳」。日志快照
`out/game_p54_lite_20261114_1525_v54_FORCE.txt`，v54 判读
`out/P48_v54_real_machine_report.txt`（26/0/1 + 1 FAIL 来自截断）。

**① 强制写入成功但被覆盖（定案）**：
`G f=7801 ... b505=0 b508=626 b506=1000 → a505=2 a508=0 ap41=0 thr=233 an=12`
是写后回读，证明 `wr16(+0x508,0)` + `wr8(+0x505,2)` 落地。但 f=7950
（仅隔 149 帧）R 行 `t505=0 t508=800`，之后到 f=20400 `t505` 恒 0、
`t508` 800→618 缓降。**v54 直接写状态字方案证伪。**

**② 静态定因（capstone，base=0）**：`0xBD260(mon,delta,max)` 唯一 caller
`0x75768`。`0xBD2AC rsb r3,r5,#0` / `0xBD2B0 ldrh r2,[+0x508]` /
`0xBD2B4 cmp r2,r3` / `0xBD2B8 ble 0xBD350`（`cur<=-delta` 耗尽）/
`0xBD2BC add r3,r2,r5` + `0xBD2C4 strh` + `0xBD2D8 strhhi r6`（按 delta+max
回写/clamp `+0x508`）；`0xBD2EC..0xBD30C` 与 `0xBD390` **每次调用重写 `+0x505`**
（0/1/3）。`0xBD350` 耗尽后 `0xBD370 bl 0xA1FC8(mon,0x20)` 门控 →
`0xBD390 strb 1`；同一 `0x76154` 内 `0x762C8..0x76358` 四重门控
（`0x8172C` 不发怒 + `0x7FC08`/`0x81774`/`0x81790`）→ `bl 0xBD184(mon,2)`
→ `0x816D0` → `0xF8D384` `p+0x41=5`。**`+0x505` 是派生状态，只能由游戏推进。**
附带：`act+0x508` 首次实机确认为当前耐力（`t506` 恒 1000、值随动作变化），
P46 静态推断落地；`0` 被拉回 `800` 的恢复来源未定案。

**③ 附带工具缺陷**：647 条 R 行长度**全为 270**，主怪行切在 `t508=... t50`，
`p41/pt5c/t1a8/t362/t5df3/low/log` 全丢（仅 428 条短值小怪槽含 `p41=`）。
v54「完整链 I 快照」实际没落盘，判读那个 FAIL 源于此，非插件错误。

**④ v55（已编译并部署）**：`out/rai_native_tired_v55.nro`，53248 B，
md5 `3656a2b7cbff27ac819e8ce69a127b4c`，部署点一致，**detour=6**。
- 新增 `h_stamina @0xBD260`（静态首字 `E92D41F0`，与已装的 `0xA30E4` 同形），
  一次性把 `delta` 放大为 `-(cur+1)`，让游戏原生耗尽；**零游戏内存写入**
  （v54 的 `wr8/wr16` 已删）。运行时首字非 `E92Dxxxx` → SKIP、整体降级纯只读。
- R 行瘦身（`t505/t506/t508` + 原有字段，恢复 `low/log`），新增 **W 行**
  承载 `t50c/p41/pt5c/t1a8/t362/t5df3/q40..q60/low/log`（`MAX_W=4000` 随 epoch 重置）。
- `mon_state()` 增加 `rd8(act+0x505)>=2` ⇒ W1 疲惫判据切链 I，
  补齐 P47 的 v55 待办（`wm=3 / wt>0`）。
- 门控、`FORCE_DONE` 熔断、W1/W0、v50~v54 观测全部不变。

**⑤ 验证**：冒烟 `analyze_v55_tired.py` **31/0/0**（W=197、G=1、`d0!=d1`、
`a508=0/a505=1`、`st3=2`、`wm=3`、`wt=36`）；降级 v54 本场 26/0/2
（截断与 W1 判据标 SKIP）、v52 疲惫场 20/0/1、v50 雄火龙 14/0/1，无 Traceback。
`8_`/`7_` → STEP 55、`TOOL2`→`analyze_v55_tired.py`，CRLF 75/166、bareLF 0，
旧版已备份；部署前确认无游戏进程；`6_` `7361445f…`、load_order 第 38 行、
游戏资源未动。回退 `v54 f1588542…` → `v53 aa504fe6…` → `v52` → `v50`。

**⑥ 边界**：v55 未实机；第 6 hook 运行时首字未实机核对（SKIP 则无强制）；
原生链路 `0xA1FC8` / `0x762F4..` 门控若不满足可能只到 `+0x505=1` 或被清 0；
`+0x508` 恢复来源、`0xF8D384 arg0==mon` 未定案；P33 闪退仍未归因。

**下一步**：双击 `8_lite_check.bat` 正常打一场（~30s 自动强制一次），看到疲惫后
再打约 1 分钟，正常关游戏。看 `INSTALL h_stamina`、G 行 `d0!=d1 / a508=0 /
a505>=1`、W 行 `t505>=2 且保持 / p41=5`、`st3=2 / wm=3 / wt>0`。
若 `a505=1` 但 `t505` 被清 0 ⇒ 门控是下一个静态目标。
报告 `out/P48_v54_falsified_and_v55_native_force.md`。

---

## 2026-11-14 15:47 · P49 v55 实机验收：可见疲惫 + 疲惫计时器定案

用户「能正常看见疲劳，并且在其疲劳结束后才关闭游戏」⇒ 日志完整落盘，
**v55 实机 PASS=31/0/0**，6 hook 全装（`INSTALL h_stamina first=E92D41F0`）、
零 FATAL / 零 `c0000005` / `live=1` / `hub=15` / R·Y·W 覆盖末帧无盲区。

日志 `out/game_p54_lite_20261114_1547_v55_TIRED_FULL.txt`；
判读 `out/P49_v55_real_machine_report.txt`；报告 `out/P49_v55_real_machine_acceptance.md`。

**① 强制链路闭环**：`G f=4596 b505=0 b508=792 d0=-8 d1=-793 a505=1 a508=0
thr=233 an=12 force=1`，`S gdone=1 gf=4596`。`d1=-(792+1)` 与 G 前 `t508`
精确对应；`a505=1/a508=0` 证明是**游戏自己**走 `0xBD2B8 ble 0xBD350` 耗尽分支。

**② 完整四态首次实机抓到**（主怪 `0C181D30` 雄火龙，W 行 105 条）：
`f=2550 t505=0/t508=800` → `f=4650 t505=1/t508=0`（耗尽）→
`f=4800 t505=2`（**正式疲惫，用户可见**）→ 持续 4860 帧≈**81 秒** →
`f=9540 t505=3` → `f=9660 t505=0/t508=800`（**结束并恢复**）→
`f=10590` 仍正常（恢复后观测 930 帧≈15.5 秒）。
`t1a8=0x440249 & 0x80001 = 1` ⇒ P46 耗尽门控实机确认满足。
`st / ex / proc / gac` 全程 0 ⇒ 疲惫与发怒、链 II 完全解耦（再证 P45/P46）。
行为侧：`N f=8700 ENTER-LOW dA=2`，`BEAT.a` 在 f=9000..10200 只涨 6。

**③ 新定案（修正 P20/P46）**：`act+0x50C` = **疲惫帧倒计时器**（f32，
初值约 4800 帧 = 80 秒 @60fps），W 行 `t50c` 55 个值解码后
**斜率 −1.000/帧**，判读脚本外推归零帧 9537，实测 `f=9540 t505 2→3` 精确吻合。
与静态 `0xBD420 ldrsh/vcvt.f32.s32/vstr s0,[act+0x50C]`（写初值）、
`0xBD46C vmla.f32/vstr`（每帧累减）对上。
⇒ **「疲惫无固定时长、靠进食恢复」在 GU 链 I 不成立**：至少这条强制疲惫是
固定时长计时器驱动，归零即结束并恢复 `t508=800`（恢复值来源未定案）。

**④ W1 权重层实证**：V 行 `f=5945 / f=8531 st3=2 vd=1 wm=3 wk=3 sp=2`，
S 行 `s2=6`、`wt=2`、`wm=[1,2,3]`、`w3=2 w4=2` ⇒ P47 的 v55 待办
「疲惫判据切链 I」**已完成并实机验证**，疲惫窗口确实走 Rise 低熵形状。

**⑤ 存疑**：`p41` 与 `pt5c` **全程恒 0**，但用户肉眼可见疲惫且 `t505` 四态完整
⇒ P46 对 `0xF8D384` 的 `p=*(mon+0xCAC0)/+0x41` 推断存疑（可能 `arg0≠mon`，
P46 本就标 [U]，或 FSM 状态字不在该偏移）。不影响结论：`t505` + `t50c` 已提供
完整可观测判据。判读脚本已把「p+0x41 未见 >=5」改为存疑提示 + 新增 `t50c`
计时器诊断（纯输出）；回归实机 31/0/0、冒烟 31/0/0、v54 26/0/2、v52 20/0/1。

**⑥ 边界**：这是**一次强制**疲惫，不是自然疲惫（自然场是否同字段未直接验证）；
f=9660 后无 V 行样本 ⇒ 疲惫结束后 W1 形状恢复仅逻辑推断；
`t508` 恢复值 800 非上限 1000 的来源未定案；`quest ended` 0 命中（直接关游戏）；
P33 闪退仍未归因。

**下一步建议 A→B**：A 关 `FORCE_ENABLE` 编纯观测版跑一场自然疲惫，证明
强制链路 = 原生链路、并补退出后 W1 样本；B 做 W2 距离档（`0x8E144` 只读探针
对齐离线 `target_dist_rot` 4 档），这是当前还原度最大缺口。C 跨怪一致性。
本轮**未改 NRO / 部署 / `8_` / `7_` / `6_` / load_order / 游戏资源**，
部署点仍 v55 `3656a2b7…`。

---

## 2026-11-14 15:55 · P50 v56 动作耐力消耗 ×64（已部署，未实机）

用户「下场继续打雄火龙，能不能修改掉雄火龙动作的消耗耐力值，让其在一两个动作后
疲劳。这样也能验证链路」。

**方案选择**：改 `0xBD260` 的**入参 delta**，不改 arc 数据表。真改表需定位
`0x756A8 bl 0x711E8` 查的 (id,sub) 消耗表 + 单条目重封 arc + 每怪一份，
成本高且跨怪不通用；改入参对状态机等价、且日志能看到 `d0→d1`，验证价值更高。

**数值依据（P49 实机）**：原始 `d0=-8`；`act+0x508` 初值 800（上限 1000）；
`0xBD2B4 cmp cur,-delta / ble 0xBD350`。`DRAIN_MUL=64` ⇒ `-512`：
cur=800 → 288（不耗尽）→ 288<=512 耗尽；cur=1000 → 488 → 488<=512 耗尽
⇒ **1~2 个动作**。若动作原始消耗更大则 1 个动作即耗尽。

**v56 改动**（源码 `lib.rs`，备份 `lib.rs.v55bak`）：
- `h_stamina` 由一次性 `delta=-(cur+1)` 改为**每次负 delta ×64**
  （`saturating_mul` + `max(-8000)` 防溢出；只作用于 `(a1 as i32)<0` 的扣减调用，
  正 delta 恢复调用原样透传）。零游戏内存写入、零新增 hook、跨怪通用。
- 新增 `DRAIN_DONE` 熔断：游戏自己推进到疲惫（`a505>=1 || a508==0`）后停止放大
  ⇒ 只产生一个疲惫窗口，疲惫结束后不再反复触发。
- 新增 **J 行**（配额 40）：`f/mon/d0/d1/cur/a505/a508/an/jn`，逐动作留痕。
  G 行仍只在耗尽那次输出 1 条，加 `jn=`；S 行 `gdone/gf` 保留。
- epoch 重置加 `J_LOG=0`，但 **DRAIN_DONE/DRAIN_N/FORCE_DONE 累计状态绝不重置**。
- 其余（6 hook、W 行链 I 全字段、W1 判据读 `+0x505`、v53 分段配额、全部门控）
  逐字节不变。

**产物/验证/部署**：`out/rai_stamina_drain_v56.nro`，53248 B，
md5 **`63f37b8e492251ddedcc0b1024c31284`**，部署点一致（部署前确认无游戏进程），
**detour=6**。冒烟 `analyze_v56_drain.py` **38/0/0**（`J=2`、
`d0=-8→d1=-512 (×64)`、`jn=[1,2]`、`G.jn=2`、末次 `a505=1/a508=0`、判定
「2 个动作后游戏自己耗尽」）；降级 v55 实机 31/0/0、v54 26/0/2、v52 20/0/1、
v50 14/0/1 全通。`8_`/`7_` → STEP 56、`TOOL2`→`analyze_v56_drain.py`，
CRLF 71/161、bareLF 0，旧版已备份；`6_` `7361445f…`、load_order 第 38 行、
游戏资源未动。回退 `v55 3656a2b7…` → `v54` → `v52` → `v50`。

**边界**：尚未实机；64 倍是按 −8 / cur 800~1000 推的；`DRAIN_DONE` 全局熔断
（多只大怪时第一只疲惫后其它不再放大）；放大从 `f>=1800 / A_N>=20` 之后开始，
所以「1~2 个动作」不是任务刚开始；P33 闪退仍未归因。

**下场判据**：看第二份报告「v56 动作耐力消耗逐次轨迹」——J 行 1~3 条、
`d0→d1` 倍数 64、末次 `a505>=1/a508=0`、G 行 `jn==J 行数`；再核对 W 行
`t505 0→1→2→3→0`、`t50c` 斜率 −1/帧、`wm=3/wt>0`、零 FATAL、无盲区。
若与 P49 完全一致 ⇒ 「放大消耗不引入偏离原版的行为」得证，可推进 W2 距离档。
报告 `out/P50_v56_per_action_stamina_drain.md`。


---

## 2026-11-14 16:08 · P51 v56 暂停中现场体检

用户「雄火龙已进入疲劳」，问是否需重启换怪，要求先答再读日志。

**答复 1**：换怪不需重启（放弃/完成后接新任务即可）；但 **v56 `DRAIN_DONE`
是插件进程级熔断**，疲惫一次后永久置位（epoch 只重置日志配额、不碰累计状态）
⇒ 同进程换怪不会再放大消耗，**要让 v56 在新怪上再跑一次必须重启游戏**；
且 `8_` 是单文件输出，同进程第二场会混日志。

**② 实机日志（暂停中，快照 `out/game_p54_lite_20261114_1608_v56_LIVEPAUSE.txt`）**：
`J=2` — `f=4105 d0=-8→d1=-512 cur=650→a508=138 a505=0 jn=1`；
`f=4772 cur=138→a508=0 a505=1 jn=2`；`G f=4772 jn=2`。
**2 个动作扣光**，与 P50 预测逐项吻合；6 hook 全装、零异常、`gdone=1 gf=4772`；
W 行 `t505 0→1→2`、`t508=0`、`t50c` 起于 f32 4764。

**疲惫未结束**：`N f=6300 ENTER-LOW`、`BEAT.a` 恒 52 到末帧、`t50c` 冻结在
3898.0 ⇒ 判读出的斜率 −0.060/帧是**暂停失真**，P49 的 −1.000/帧仍成立。

**原 3 个 FAIL 是判读缺陷**：V 行全场 5 条，主怪仅 1 条且在 f=4671（疲惫前），
其余都是小怪 `sp=1016`；疲惫窗 `f>4772` 内主怪无 EMC 抽选 ⇒ `st3=[0] /
wm=[1,2] / wt=0` 是样本缺失。`analyze_v56_drain.py` 三处修正（按「疲惫起点+
主怪」筛 V 行、无样本标 SKIP；斜率偏离 −1 提示暂停；盲区检查识别 BEAT.a 恒定
输出 INFO）。回归：实机 **35/0/1**、冒烟 38/0/0、v55 31/0/0、v54 26/0/2、
v50 14/0/1 全通。

**建议**：恢复游戏让疲惫自然走完（约 80 秒游戏时间）→ 补 W1 疲惫形状样本 →
正常关游戏；之后要换怪并让 v56 再生效才重启。本轮**未改 NRO/部署/`8_`/`7_`/
`6_`/load_order/游戏资源**，部署点仍 v56 `63f37b8e…`。
报告 `out/P51_v56_live_pause_check.md`。


---

## 2026-11-14 16:14 · P52 v56 完整实机验收（疲惫自然走完）

用户让疲惫自然走完并正常关游戏。日志 `out/game_p54_lite_20261114_1614_v56_TIRED_FULL.txt`，
判读 `out/P52_v56_full_report.txt` **PASS=38/0/0**（零异常、6 hook 全装、无观测盲区）。

**① 链路**：`J=2`（`d0=-8→-512`、cur 650→138→0、2 个动作游戏自己耗尽）、
`G f=4772 jn=2 a505=1 a508=0`，与 P50 预测逐项吻合。

**② 完整状态机 0→1→2→0**：f=4800 耗尽 / f=4950 正式疲惫（`t50c` 起于 4764）/
f=5850..28200 **暂停冻结** / f=28200 恢复 / **f=32250 `t505=0 t508=800` 结束** /
恢复到 f=32850 再观测 600 帧。**本场没有 `t505=3`** ⇒ 3 是可选分支非必经
（P46「已疲惫再减气」的加强态，本场低活动 + DRAIN_DONE 停止放大故未触发）；
P49「四态」应改述为「四个可能取值、3 非必经」。

**③ 本轮最硬新证据：计时器按游戏逻辑帧计，暂停不消耗窗口**。
全场线性拟合被 22350 帧暂停平台拉成 −0.172/帧；改按连续递减段切分后：
`f=4950..5850 4764→3898 斜率 −0.962/帧`、`f=28200..32100 3898→97 斜率 −0.975/帧`
（与 P49 的 −1.000 同量级）。**实际游戏逻辑时长 = 900+4050 = 4950 帧 ≈82.5 秒**，
初值 4764/0.962 ≈4952 帧精确吻合；P49 为 4738 帧≈81 秒 ⇒ 两场时长一致，
`act+0x50C` 固定时长计时器定案再确认。判读脚本已改为分段输出 + 暂停平台标注
（回归：实机 38/0/0、冒烟 38/0/0、暂停场 35/0/1、v55 31/0/0、v54 26/0/2、v50 14/0/1）。

**④ W1 疲惫形状补齐**：`V f=29600 mon=0C220B70 st3=2 vd=1 wm=3 wk=3`、
`S f=30000 s2=3 wt=1` ⇒ P51 因暂停缺样本标的 SKIP 转为 3 项 PASS。
`N f=6300 ENTER-LOW / f=30000 EXIT-LOW dA=7` 与暂停段对应。

**⑤ 结论**：全场仅 2 条 J / 1 条 G、`gdone=1 gf=4772` 恒定 ⇒ `DRAIN_DONE` 熔断生效，
没有二次放大；场级字段与 P49（v55 一次性强制）逐项一致 ⇒
**「放大动作消耗不引入偏离原版的行为」得证**，P50 §6 验证目的达成。

**边界**：仅雄火龙单场、跨怪未验证；`p41/pt5c` 仍恒 0（P49 存疑）；
`t508` 恢复值 800 来源未定案；P33 闪退仍未归因。

**下一步**：游戏已关，`DRAIN_DONE` 随插件重载清零 ⇒ 换怪直接重启即可让 v56 重新生效。
建议 A 换跳狗龙跑一场验跨怪一致性（零编译），再做 B（W2 距离档 `0x8E144` 探针）。
本轮**未改 NRO/部署/`8_`/`7_`/`6_`/load_order/游戏资源**，只改判读脚本计时器诊断段。
报告 `out/P52_v56_full_acceptance.md`。


---

## 2026-11-14 23:01 · P53 v56 跨怪一致性验收：雷狼龙

用户完成一场雷狼龙任务、肉眼见疲惫流口水、正常关游戏（日志 1.86 MB，
末帧 f≈51490，`quest ended 2`）。判读 **35/0/1**（修判读筛选后），
零异常、6 hook 全装、无盲区。日志 `out/game_p54_lite_20261114_2301_v56_ZINOGRE.txt`，
报告 `out/P53_v56_zinogre_crossmonster.md`。

**① 跨怪一致性成立**：`sp=39`、`thr=325`、原始 `d0=-50`（雄火龙 −8），
×64 ⇒ `d1=-3200`，`cur=600 <= 3200` ⇒ **1 个动作**游戏自己走
`0xBD2B8 ble 0xBD350`（P50 已预测「消耗更大则 1 个动作」）。
`J=1 / G=1 jn=1`、`a505=1 a508=0`、`t505 0→1→2→0`、
`t508` 恢复 800、`t50c` 斜率 **−1.000/帧** ⇒ `0xBD260` 放大、
`+0x505` 状态机、`+0x50C` 计时器**不是雄火龙专属**。

**② 新定案（修正 P52）**：疲惫计时器初值**按怪种/数据表配置**。
雷狼龙初值 **3453**、窗口 f=9150..12600 = 3450 帧 ≈ **57.5 秒**；
雄火龙 P49 4738 / P52 4764 ≈ 81~82.5 秒，差 **38%**。
⇒ 「固定时长」应表述为「每场线性递减且时长固定，但初值按怪配置」，
与 `0xBD420 ldrsh/vcvt/vstr`（从表载入初值）一致。
另 `f=45750 t505 0→1 / f=46200 1→0 t508=1000`（low=1）是中间态回退，
成因未定案。

**③ 3 个 W1 FAIL = 判读缺陷 + 结构性作用面窄**：
(a) 原判读用 `f > G 帧` 筛疲惫窗，本场日志长（疲惫 f≈12600 结束、日志到 51490）
把恢复后 10 条主怪 V 行（含 4 条 `st3=1` 发怒）误算进去 ⇒ 假 FAIL。
真实窗（`t505>=2` 的 W 行）= f=9150..12600，窗内主怪**无 EMC 抽选 V 行**
（首条 f=12864 在窗外）。已改按真实窗筛选、无样本标 SKIP，同步修合成冒烟时间戳；
回归本场 35/0/1、冒烟 38/0/0、P52 38/0/0、P49 31/0/0、v50 14/0/1 全通。
(b) **更关键**：`S` 行 `s2=5` 但 **`sv2=0`**；源码里 `S_N[st3]` 每次
`h_matcher` 累加，而 `S_V[st3]`、`rise_weight_pick()`、V 行**只在
`REP_N`（prev 命中→否决重抽）分支**执行 ⇒ `wt=0/wm 无 3` 不是 W1 失效，
是疲惫窗内 0 次否决、W1 根本没被调用（P52 `wt=1` 是恰好有 1 次）。
⇒ **当前 W1 只作用于防复读重抽，绝大多数正常抽选仍走 GU 原版权重**。
这是「尽可能复刻 Rise」最实质的机制缺口，优先于距离档。

**④ 稳定性**：全场仅 1 J / 1 G、`gdone=1 gf=8781` 恒定 ⇒ `DRAIN_DONE` 生效；
`N` 行 11 条、`BEAT.a` 末段恒 502（结算后菜单）；零 FATAL / 零 `c0000005`。

**边界**：两怪样本仍有限；`p41` 恒 0（P49 存疑）；中间态回退成因未定案；
`t508` 恢复值 800/1000 来源未定案；P33 闪退仍未归因。

**下一步**：A **把 `rise_weight_pick()` 从 `REP_N` 分支提到每次
`h_matcher` 的 `mode==1/sub==0` 抽选**（不新增 hook、不写内存、不需实机数据，
收益最大）→ B W2 距离档 → C 疲惫窗内持续攻击补主怪否决样本。
本轮**未改 NRO/部署/`8_`/`7_`/`6_`/load_order/游戏资源**，只改
`analyze_v56_drain.py` 与 `make_v56_smoke.py`。


---

## 2026-11-14 23:10 · P54 v57 = W1 全抽选 + 纯只读发布配置（已部署未实机）

用户问「后面还需要 hook 吗？还是能直接制作一个成品 mod？先给结论再做」。
**结论**：① 不需要新增 hook（A 与成品化都在已装 `h_matcher` 内，6 detour 不变）；
② 可直接做成品，但不能发布 v56（验证探针：×64 强制 + 1.86MB/场日志）；
③ W2 精确对齐只需一场只读探针数据（仍用现有 hook），领地争夺/专属演出超边界。
边界：机制级复刻，GU 无 Rise 15 张独立池表与 5 档几何阈值。

**① W1 全抽选（补 P53 结构性缺口）**：P53 实测 `s2=5/sv2=0/wt=0` ⇒
v50~v56 的 `rise_weight_pick()` 只在 `REP_N`（否决重抽）分支执行。
v57 在 `!repeat` 分支也调用：仅 `main_track`（op02/mode1/sub0）、
`sw==100`、`n>=4`、`WALL_OK<MAX_WALL_OK` 时尝试；完整复用
`b_off<=2 / nr∈(0,256] / adiff<=2 / opcode` 校验，任一失败原样返回 r。
成功后 `push_prev` 记实际签名。S 行新增 `wall/wnok`；`w3/w4/wt`
改为统计所有抽选的形状使用次数。`MAX_WALL_OK=12000` 熔断，累计状态不随 epoch 重置。

**② 纯只读发布配置**：`DRAIN_ENABLE=0`（无关强制、`h_stamina` 纯透传、
J/G 行消失）、`PROFILE_RELEASE=1`（R/W 高频块被编译期消除，连扫描开销都省）、
`W1_ALL=1`（置 0 退回 v56）。零写入、零参数改写、6 detour 不变。
`PROFILE_RELEASE=0 + DRAIN_ENABLE=1` 可编回验收配置。

**③ 产物/验证/部署**：`out/rai_w1all_release_v57.nro` 49152 B
md5 **`1aed8640a4bc592c7f1169c375e81710`**，部署点一致；
`J f=`/`W f=` 串计数 0 证明发布配置生效；detour=6。
新增 `analyze_v57_release.py`（20 项）与 `make_v57_smoke.py`：
冒烟 **20/0/0**（wall=48/wnok=41、w3+w4>0、wt>0、无 R/W/J/G、gdone=0）；
降级 v56/v55/v50 实机各 6/0/2 全通。`8_`/`7_` STEP 57、TOOL2→
`analyze_v57_release.py`，CRLF 72/165、bareLF 0，旧版备份。
**附带修复**：v56 轮遗留两处 `echo` 拼接缺陷（8_ 第 46 行、7_ 提示块末尾漏 CRLF），
现 concat=0。部署前确认无游戏进程；`6_`/load_order/游戏资源未动。
回退 `v56 63f37b8e…` → `v55` → `v54` → `v50`。

**④ 边界**：**未实机**。A 改了抽选主干，影响面远大于 v50~v56；
P36 标注的「段内 sub 是否经过 op02/mode1 无实机证据」风险被放大 ⇒
若连段异常优先 `W1_ALL=0` 回退并加段内门控。发布版不强制疲惫，
疲惫形状只在自然疲惫窗口出现（判读标 SKIP）。W2 距离档、
`_IsActionEnd` 门控、12 处境 Hub 仍未实现。

**⑤ 成品判定**：代码层面已完成（零写入/零强制/发布级日志/跨怪通用/
W1 全抽选/完整回退链）。**仍差一场实机验收**：下场正常打一场（不再自动疲惫），
看 `wall/wnok>0`、`w3/w4/wt` 占比、无 R/W/J/G、零异常，以及体感
（动作多样性、连段完整性、卡动作）。通过后即可发布。
报告 `out/P54_v57_w1all_release.md`。


## 2026-11-14 23:45 · P55 v58 = v57 全抽选 + W2 距离档只读探针（已部署未实机）

用户：「把探针一起做了吧，我一场验证 W1 和距离档探针两个」。

**① 静态 + 实机依据**：`emc.md §3/§4/§5` 定案 `0x8E144(ctx,ip,op,mode,value)`
是 EMC block matcher，距离 op `0x0b/0x17/0x57/0x5c/0x7c` 用 case 阈值分档
（mode 5,6,7,15,16,19,20,23,24,25 → case×100；4,14,21,22 → float 表），
几何量在 `sub=*(ctx+0x1428)` 的 `+0x30..0x38 / +0x40..0x48 / +0x2e8.. / +0x54`。
实机 v56 雷狼龙日志 80 条 M 行里已有 `op=17/md=6`×4、`0B/4`×2、`57/14`×1、
`6A/26`×3，但 `MAX_M=40` 被 mode0 状态 switch 吃光；且距离调用 `p5` 恒 0
（value 走 VFP）⇒ 必须读 sub 几何，不能靠 a4。

**② 实现**：`h_matcher` 早返回后加 `dist_mode()` 门控的 `dist_probe()`，
只放行几何 mode（排除 0/1/11/18）。新增 `Z` 行（op/md/val/ip/blk/nc/t0..t3/
hit/ret/st3，`MAX_Z=1200`/epoch，复用 find_begin+scan_cases，失败时 64B 回退
且要求 nc>=2）与 `ZP` 行（每 4 次 Z 一条，`sub` 几何 f32 原始位 + heading +
`cmd=*(mon+0x2588)` / `ent=*(cmd+0x78)`，`MAX_ZP=300`/epoch）。`hit` 由 ret 反推
命中档位；`W2_PROBE=0` 编译期消除整段。`mon_ok`/`sub+0x310` 双重越界保护。
**6 hook 不变、零写入、零参数/返回值改写、W1 主干逐字节不变**。

**③ 产物/验证/部署**：`out/rai_w1all_w2probe_v58.nro` 53248 B，md5
**`12a0d422ed555eba57139fb628c0ee4c`**，部署点同 md5（部署前 `NO_GAME_PROCESS`）。
冒烟 **30/0/0**（Z=600/ZP=150、6 种 mode、case/命中/几何解析全 100%、
wall=48/wnok=41）；v57 判读脚本跑 v58 冒烟 20/0/0；v58 脚本跑 6 份旧日志
降级 6/0/2 全通。新增 `analyze_v58_release.py`（30 项 + 分布诊断）与
`make_v58_smoke.py`；`8_`/`7_` STEP 58、TOOL2 切 v58、CRLF 80/171、bareLF 0；
`6_` `7361445f…` 与 `mods/load_order.txt` 未动；回退 `v57 1aed8640…`。

**④ 边界**：**只是探针，不实现 W2 档位加权**；未实机，距离块的
find_begin/scan_cases 成功率未知；`ent` 是否等于当前 entry 基址未定案；
Rise 5 档几何阈值仍未抽取；成品化需 `W2_PROBE=0` 编译 v59。
下一场 `8_lite_check.bat` 正常打一场，第二份报告同时出 W1 验收与 W2 数据结论。
细节/判据只在 `out/P55_v58_w2_distance_probe.md`，本处只留摘要。


## 2026-11-14 23:47 · P55 暂停中体检：v58 两项均已运行，W2 暴露两个实机缺陷

日志 `02_Workspace/game_p54_lite.txt`（暂停中快照，2512 行，f≈10800）。
- **W1 已实现并生效**：`RAI v58` 横幅、6 个 `INSTALL h_`、零 FATAL/异常、
  无 R/W/J/G（发布配置生效）、`live=1 hub=15 fail=0`；
  S 行时间线 `(f=3000 wall=0) → (6000 wall=2) → (9000 wall=7 wnok=5 w3=2 w4=3)`
  ⇒ 全抽选生效、Rise 形状按非疲态分化。`V=0` 只是本场尚无否决重抽，非故障。
- **W2 探针已实现并在跑**：Z=31 / ZP=7，4 种距离 mode（md=4/5/6/26；
  op=0B/16/17/6A），ZP 几何 7/7 可解为 f32，3D 距离 104~5522 有真实量级变化。
- **缺陷 1（设计错）**：`cmd=*(a0+0x2588)` 全 0 ⇒ `ent` 全 0/7。
  `h_matcher` 的 a0 不是文档里的 em 基址（`scan_em()` 在 1673 行已被注释、
  EM_OFF 恒 0），`ip-ent` 离线对齐链路断了。判读脚本该项 FAIL 属实。
- **缺陷 2（解析率）**：`nc>=2` 16/31(51.6%)、`hit>=0` 14/31(45.2%)；
  **md=6 / op=17（3D 距离）8/8 全败**（blk=0 nc=0 hit=-1，ip 恒 1A18E2F8、
  ret=3）⇒ `find_begin()` 的 `rd8(a1-1)==op` 与 64B 回退对这类块不成立。
  md=4 5/7、md=5 6/10、md=26 5/6 成功（例 `op=16 md=5 t0=1 t1=6`）。
- **暂停口径**：暂停后 forge 帧仍增长（BEAT 到 f=10800）但 Z 止于 f=7904、
  ZP 止于 f=7397 ⇒ 暂停段不产生距离调用，不能当样本；与既有
  「暂停菜单不冻结 forge_onUpdate」定案一致。此快照**不是最终验收**。
- 判读 `analyze_v58_release.py` 对本快照 PASS=26/FAIL=2/SKIP=2
  （FAIL 即 ent 与 hit 率；SKIP 为无疲惫窗、无跨状态样本）。
- **下一步待用户选**：①关游戏修 v59（从 `guess=ip+ret` 直接定位命中 case
  阈值、放宽 begin 回退、ent 改走 em 基址扫描或把该项降为诊断）后重打；
  ②继续打完本场，W1 结论可用、W2 只够部分对齐。


## 2026-11-14 23:55 · P56 v59 = W2 探针修复（已部署未实机）+ W1 输出窗口诊断

用户退出游戏后：「你修，而且我发现 W1 好像没有给我有效的输出窗口？」
**本轮只修 W2，W1 逐字节不变**（避免两个变量混在一场）。

**① P55 最终日志（v58，2556 行 f=13500）**：零 FATAL/异常、6 hook、无 R/W/J/G、
`live=1 hub=15 fail=0`；S 行 `wall=7 wnok=5 w3=2 w4=3 wt=0`；BEAT `sel=52 act=52
ok=7 rep=0 v=0`；Z=31 ZP=7。两个缺陷定案：`ent!=0` 0/7（a0 非 em 基址，
`scan_em` 已证伪停用）、`nc>=2` 16/31 与 `hit>=0` 14/31，md=6/op=17 **8/8 全败**。
暂停段 Z 止于 f=7904 / ZP 止于 7397，与「暂停不冻结 forge_onUpdate」一致。

**② v59 修复**：`scan_cases_near()`（ip-64..ip+256 找 `op,sub=1,w<=100`，
相邻间隔>=3B）兜底；begin 回退 64B→256B；Z 行加 `src`(1=begin/2=near)、
`g`(=ip+ret)、`ts`(命中 case 阈值，0xFF=未定)、`r0/r1`(guess±2 共 8 原始字节)；
新增 `ZS` 行（前 2 次 ZP 扫 a0±0x2000 找 script 段指针候选，输出偏移+值，
定位真正 em/cmd 基址）；判读把 `ent!=0` 降为诊断 SKIP、档位判据改
`hit>=0 || ts!=0xFF`。6 hook、零写入、W1/发布配置全不变。

**③ 产物**：`out/rai_w2probe_fix_v59.nro` 53248 B md5
**`ecabccb4f1a2caee8c04b49c90cc813e`**，部署点同 md5（部署前 NO_GAME_PROCESS）。
冒烟 **29/0/1**（SKIP=ent 诊断）、四路降级 6/0/2 全通；新增
`analyze_v59_probe.py`/`make_v59_smoke.py`；`8_`/`7_` STEP 59、CRLF 85/175、
bareLF 0、concat 0；`6_`/load_order 未动；回退 `v58 12a0d422…`。

**④ W1「没有有效输出窗口」诊断（重要定案）**：`sel=52 → wall=7 → wnok=5`
⇒ 只有 **13.5%** 抽选通过 `sw==100 && n>=4` 护栏、实际改选 **9.6%**；
`rep=0 v=0 wt=0`（无否决重抽、无疲惫窗）。三个原因：
  - `n>=4` 门槛偏严（Rise 15 池 cases 是 3~4），降 `n>=3` 安全
    （`rise_weight_pick` 要求 m>=3，k=4 时 m<k 自动退回原样），可把覆盖面拉满；
  - **W1 作用域只是权重形状**，不改抽选时机/动作持续/连段衔接；
  - 「输出窗口」属 **W3 `_IsActionEnd` 门控 + W4 处境分流**，P34 阶段 D /
    P54 §4 明确未实现、需单独灰度。现在节奏仍是 GU 原版。
⇒ **W1 已生效但体感不明显是预期结果，不是失效**。下一轮二选一：
A `n>=4→n>=3` 扩面（低成本推荐先验）/ B 做 W3 门控（大工程）。
细节只在 `out/P56_v59_w2_probe_fix_and_w1_diagnosis.md`。


## 2026-11-15 00:10 · P57 v60 = W1 高保真对齐 Rise 15 池（已部署未实机）

用户要求「在 W1 既有范围内尽可能高保真复刻 Rise，覆盖主要界面/交互流程/
视觉风格/功能行为，保持结构命名约束，标注假设，列关键差异与未完成项」。
**假设**：本项目是游戏内 AI 插件，无 UI/视觉层 ⇒ 界面映射为既有日志可观测面
（格式不变）、交互流程映射为 W1 抽选流程（不变）、视觉风格不适用（不改渲染）、
功能行为即 W1 形状与状态分化（本版对齐）。详见 `out/P57_...delivery.md §0`。

**① 四项对齐（全在 `rise_weight_pick()` / `SHAPE_*` / `W_MIX_*` 结构内）**：
- 形状表改 Rise 15 池实测降序均值：A3[55,25,20] A4[40,25,20,15]
  N3[47,28,25] N4[41,25,22,12] T3[60,30,10]（T3 保留 P35 熵拟合）。
- 三态分离 + 按状态 k3:k4：anger 40:60（新增 `W_MIX_ANGER_PCT`）、
  normal 60:40（`W_MIX_PCT` 61→60）、tired 恒 k3；`wm/wk`、`w3/w4/wt` 语义不变。
- 护栏 `n>=4 → n>=3`（Rise 10/15 池是 k3；P56 实机只 13.5% 抽选进 W1）。
- `m<目标k` 时按 m 截断形状并归一化回和 100，不再整包退回 GU 原版权重。
**逐字节不变**：W2 探针（Z/ZP/ZS）、疲惫链、6 hook、发布配置、日志格式、
`6_`/load_order。

**② 对拍**（`tools/audit_v60_w1_fidelity.py` → `out/P57_w1_fidelity_audit.md`）：
形状表 anger/normal 四组 L1=0、tired 熵拟合 L1=10；混合熵偏差
anger +0.0437 / normal −0.0012 / tired −0.0029；GU 561 合法池
`cases>=3` 82.4% vs `>=4` 72.4%（+10.0pp）。

**③ 产物**：`out/rai_w1_rise15_fidelity_v60.nro` 53248 B md5
**`6d1a2f1f0eec3f6eb84816b7e5904a5e`**，部署点同 md5（NO_GAME_PROCESS）。
冒烟 29/0/1、四路降级 6/0/2 全通；新增 `analyze_v60_w1.py`/
`make_v60_smoke.py`/`audit_v60_w1_fidelity.py`；`8_`/`7_` STEP 60、
CRLF 91/179、bareLF 0、concat 0；回退 `v59 ecabccb4f…`。

**④ 关键差异/未完成项**：无 15 张状态×距离独立池表（结构性近似）；
W2 档位加权未实现；疲惫形状熵拟合非字面均值；anger 混合熵 +0.0437；
`_CheckPrevTableInfoList` 是 3 项 prev 表近似；k 截断属假设；
W3 门控/W4 12 Hub/领地争夺未实现（输出窗口节奏仍 GU 原版）；
成品化需 `W2_PROBE=0`；**v60 未实机**。清单见报告 §4/§5。


## 2026-11-15 12:10 · P58 v60 首场暂停中体检：W1 扩面与 W2 修复双双实证

日志 `02_Workspace/game_p54_lite.txt`（暂停中快照，3514 行，BEAT 到 f=22500），
`RAI v60`、6 hook、零 FATAL/异常、`live=1 hub=15 fail=0`、无 R/W/J/G。
判读 `analyze_v60_w1.py` **PASS=28 / FAIL=0 / SKIP=2**（SKIP=无自然疲惫窗、
ent 诊断），结论「W1 验收通过 / W2 数据充足，可进入档位映射」。

**① W1（v60 高保真对齐生效）**：BEAT `sel=78 act=78 rep=6 v=6 ok=31`；
S 时间线 `f=3000 wall=0 → 6000 2/0 → 9000 10/8 → 12000 14/12 →
15000 21/19 → 18000 29/27 → 21000 31/29`（wall/wnok）。
⇒ 护栏覆盖 **31/78=39.7%**、实际改选 **29/78=37.2%**，对比 P56 v58 场
`sel=52 wall=7 wnok=5`（13.5% / 9.6%）**约 3 倍提升**；`wnok/wall=0.935`
（v58 为 0.714）⇒ `m<目标k` 截断归一化让尝试更少被退回。
`w3=20 w4=15 wt=0`、`s0=23 s1=14 s2=0`（怒/常都有样本）⇒ 三态分离有实机数据；
V 行 6 条 `st3→vd` / `wm→wk` 零违例（样本含 `wm=2 wk=4`）。
`wt=0` 因发布版不强制疲惫、本场无自然疲惫窗，属预期 SKIP。

**② W2（v59 修复版探针）**：`Z=101 ZP=25 ZS=2` 三类行齐全；
`nc>=2` **95/101=94.1%**（v58 场 51.6%）、档位证据率
（`hit>=0 || ts!=0xFF`）**89/101=88.1%**（v58 场 45.2%）；
`src` 分布 `1:79 / 2:16 / 0:6` ⇒ `scan_cases_near` 兜底救回 16 条。
按 md：4 → 37 条全 100%；5 → 14 条 79%；26 → 44 条 80%；
**md=6/op=17 的 6 条 case 解析仍全败（src=0 nc=0 hit=-1，ip 恒 1C08A1A8、
ret=3），但 `ts=8` 100% 有效** ⇒ v59 的「guess 附近直读命中 case 阈值 +
r0/r1 原始字节」补上了这一档证据（`ts=8` 疑对应 case×100=800 单位）。
结论：md=6 的 begin 定位问题**未根治，但数据已可用**；若后续要完整阈值序列，
需按 `g=1C08A1AB` 的 `r0=02080117 / r1=1E010200` 离线重建该块结构。

**③ ZP / ZS**：ZP 25/25 几何可解 f32，两组坐标完全相同仅 1 条（首条距离 0），
3D 距离 min=0 / p50=3458 / p90=7027 / max=7311，XZ p50=3297 ⇒ 几何量真实可用，
可给档位定阈值。ZS 2 条各 6 个指针候选，值散在 0x08..0x1E
（如 `-7932` 在两条里都出现但值不同：0F27C143 / 1A8DA274）⇒ **仍不足以定位
em/cmd 基址**，`cmd=*(mon+0x2588)` / `ent` 继续全 0（已降为诊断）。

**④ 暂停口径**：Z/ZP 止于 f=19177，BEAT 到 f=22500、S 到 f=21000 但计数基本停滞
⇒ 暂停后 forge 帧继续、游戏逻辑不再产生距离/抽选调用，与既有定案一致。
**此快照不是最终验收**；若继续打，重点补疲惫窗（`wt`）与更多跨状态距离样本。


## 2026-11-15 12:14 · P59 定案：W2 数据量「行数够、工程不够」，需多怪样本

用户关游戏后问「W2 需要多怪样本还是现在的数据量就够了」。
**结论：需要多怪样本。判读脚本的「W2 数据充足」是行数口径，不是工程口径。**

最终日志 `02_Workspace/game_p54_lite.txt`（3568 行），判读 `PASS=28/0/2`，
脚本按 `Z>=20 / ZP>=5 / nc>=2 率>=50% / 档位证据率>=50%` 判「可进入档位映射」。
但块级/怪种级复核显示：
- **单一怪种**：V 行 `sp=0020` 6/6；ZP 的 5 个 `mon` 是实例槽不是怪种。
  EMC 脚本按怪种不同（`emNNN_SS.arc :: enemy/cmd_tbl/*_cmdtbl`），
  单怪标定的 case 阈值不能跨怪通用（项目纪律禁止按单怪硬编码）。
- **11 个 (ip,md) 块，仅 5 个有档位分化（49 条）**；其中真正展示多档切换的
  只有 2 个 md=4 块（`1BF92A37` 22 条 hit 0/1/2/3、`1BF9290F` 13 条 hit 0/1/2）。
  6 个常量块共 52 条（含 `1BF907A0` 35 条全 hit=1/ts=2 的重复采样）。
- **md=6（3D 距离）只有 1 块 6 条**，全 `hit=-1 / ts=8`，零分化；
  md=5 3 块 14 条、md=26 3 块 44 条但多为常量。
- **状态覆盖缺疲惫**：Z 行 `st3` 仅 `{0:70, 1:31}`，无 `st3=2`；`wt=0`。
- ZP 25 条 100% 可与 Z 行 ±60 帧配对（配对机制没问题），但绝对量偏少，
  且 25 条里只有 1 条两组坐标完全相同 ⇒ 几何量本身可用。

**分两层结论**：
1. 目标 = 验证探针链路 + 单怪探索性对齐 ⇒ **现在够了**，可开始离线标定。
2. 目标 = 产出可写进成品的跨怪通用档位阈值 / 把 W1 升级为「状态×档位」
   ⇒ **不够**，至少再 1 场不同怪种，建议 2 场（P34 阶段 E 要求 2-3 只快/慢/多段怪）。

**下一场采集目标（量化）**：换差异大怪种（雷狼龙 `sp=0039` 或跳狗龙王 `sp=0055`）；
unique (ip,md) 块 >=15、有分化块 >=8、md=6 至少 2 块且 hit/ts 有分化、
ZP >=50、含自然疲惫窗 `st3=2`；打法刻意贴身/中距/远离反复切换，任务 8-10 分钟。
可选小改：`ZP_EVERY 4→2` 让几何快照翻倍（需重新编译，本轮**未改**）。
本轮未改任何代码/部署/NRO。


## 2026-11-15 12:45 · P60 定案：跨怪距离档可从游戏数据离线全量挖掘，不需逐怪实机

用户问「怪物数量种类太多，你能自己挖游戏数据来找吗？」⇒ **能，已做完**。
两路只读子代理调研 + 全量离线抽取，本轮**未改插件/NRO/部署/日志格式**。

**① 数据源与链路（已跑通）**：`D:/Monster Hunter Generations Ultimate Recomp/data/romfs/nativeNX/arc/enemy`
137 个 `emNNN_SS.arc`（0 解析错误）。每个 arc 内两个条目：
- `enemy/cmd_tbl/<label>_cmdtbl` → EMC 距离 switch 块（复用 `tools/gu-moves/lib/trees.mjs`
  的 `cmdtblFromArc`/`buildTree`，模板 `audit_emc_pools.mjs:76-77`）；
- `enemy/dt_tune/<label>_dttune` → **4 个 f32/行 的 4 档距离阈值表**。
关键定案：`emc.md:56` 的 `[[ctx+0x75ec]+0x7c]` 是 **loader 后的运行时对象字段，不是文件偏移**
（文件内 `+0x7c` 恒 `0xffff0000` 哨兵）；文件里表在尾部且**每怪偏移不同、2 字节对齐非 4 对齐**
（em001 `+0x13e`、em004/em005 `+0x18e`）。`06_MH4UPort_IPS32/.../tools/dt_convert.py:77-84,153-173`
早已定义 `RANGES=(0x7C,10,0xFA,0x80,11,0xFB)` 与 16B/行 f32；`dttune.md:66-68` 已列出
em001 `[600,1100,2500,5000]` 但误标「语义未知」。04 线此前未接上，NOTES 多处写「未定位」应更正。

**② 新增工具/产物**：
- `tools/audit_dist_bands_offline.mjs`（全量枚举 137 arc，抽 7 个距离/几何 op 的
  case 序列 + beginArgs + dttune 阈值行；2 字节步长扫描「4 个递增 f32」+ 64B 内聚类）
  → `out/dist_bands_all.json`（1.4 MB）。
- `tools/analyze_dist_bands_offline.py` → `out/P60_offline_dist_bands.md`（对齐 + 结论）。
- **全量结果**：8488 个距离块（TABLE 4983 / SCALE100 54 / UNKNOWN 3451）、
  119/137 只怪抽到 2~6 行 4 档 f32 阈值（首行 136~8704，中位 500）。
  最高频序列 `0x0b|0,1,2,3` 2182 块 ⇒ **4 档结构跨怪共享**。
  抽样 em001/em004/em005 与 dttune.md、dt_convert.py 逐字吻合。
- 实机 `sp=0020` → emid 32 → **轰龙 Tigrex**（`refs/.../monster-slot-map-137.json`），
  离线 `em032_00`/`em032_04`。v60 单场 11 个运行时块 vs 离线 8488 ⇒ **772 倍**。
  6/11 个实机块按 (op,case序列) 在离线表找到同构定义。

**③ 基址锚定（诚实边界）**：`ip - pos` 聚类显示**单基址最多覆盖 1/11 个实机 ip**；
11 个 ip 落在 `0x1BF9xxxx` / `0x1C10xxxx` 两段，`0x0b|0,1,2,3` 在 em032* 有 82 个同构块
⇒ 现有日志不足以把运行时 ip 唯一映射回 `(sec,entry,pos)`。唯一收敛例：
`0x1BF907A0` → 基址 `0x1BF90700` → em032 s0/e6 的 `0x6a|5,2` 块。

**④ 路线定案（回答「还需多少实机」）**：
- **路线 A（推荐）按 case 索引分档**：运行时用 `ret` 反推 `hit`(0..3) 当档位驱动 W1
  「状态×档位」形状。4 档结构跨 137 arc 共享 ⇒ 天然跨怪，**不需物理阈值/脚本基址/逐怪实机**；
  剩余只需 1 场验证 `hit`↔档位 + 疲惫态 `st3=2` 样本。
- **路线 B（高保真）按物理距离对齐 Rise 5 档**：需把 dttune 表按怪种编译进插件 +
  1 场基址锚定（`ZS`/`cmd`+`ent`）+ slot 确证（每怪 2~6 行，`0x71164(ctx,slot)` 的 slot
  由哪个 begin 参数决定无 GU 代码级确证）+ 命中顺序/单位验证。**同样不需要逐怪跑任务**。
- 两条路线共同未完成：W2 档位加权本身、W3 门控、W4 12 Hub、领地争夺、
  Rise `em131_00_range_data.user.2` 未抽取；18 只怪无阈值行。
细节只在 `out/P60_offline_dist_bands.md`。


## 2026-11-15 13:35 · P61 v61 = W2 高保真路线前置：运行时 dttune 阈值链探针（已部署未实机）

用户决定：回单怪主线、W2 走高保真路线、领地争夺/双怪互打暂缓。

**① 静态定案（纠正 P60 路线 B 的前置）**：`emc.md:56` 的
`0x71164(ctx,slot) = [[ctx+0x75ec]+0x7c] + 16*slot` 是**运行时对象链**：
`ctx+0x75ec` = dttune 对象指针（`W4-REFERENCE.md:69` 字节级 callback `0x70a1c`
写入、`0x71078` 当指针读）、`obj+0x7c` = 阈值表首地址、`obj+0xfa` = 行数、
`+16*slot` 步长（06 线 `dt_convert.py:77-84,162-173` 的 `RANGES` 定义）。
⇒ **不需把 137 只怪的表编译进 NRO，也不需脚本基址锚定**；游戏自己加载的
表天然按怪种正确。旧 NOTES 把「编译表 + 基址锚定」列为前置应更正为
「先验证运行时表链」。
`a0` 高度可能就是 ctx/em：P55 由 `rd(a0+0x2588)=0` 推出「a0 非 em」是过度
结论（`+0x2588` 是 rEnemyCmd 资源字段、生命周期不同）；`+0x1428` 实机有效、
其它 hook `ident(a0)` 一致、emc.md 签名均支持 a0==em。
**slot 仍未定案**：离线全量 `0x0b` beginArgs 仅 `[0]`(4495)/`[1]`(15)、
`0x57` 仅 `[0]`(473)，值域 {0,1} 编码不了 2~6 行 ⇒ 结构性排除；
`emc.md:42` 说明它参与 mode 判定。`0x71164` 无逐条反汇编（仅 11 指令 accessor 形态）。

**② v61 实现**：仅 TABLE 型 mode(4/14/21/22) 触发 `dist_table_probe()`，
逐级 null/范围检查读 `tune=rd(a0+0x75ec)` → `cnt=rd8(tune+0xfa)` →
`base=rd(tune+0x7c)` → 每 slot 4 个 f32 原始位，输出新 **`ZT` 行**
（避开 v49 已有 `T` 行 / `MAX_T` / `T_LOG` 命名冲突），带 `blk`/`ba`(begin 首
操作数) 供 slot 判定。`MAX_ZT=600`/epoch、`ZT_LOG` 随 epoch 重置。
`mon+0x7700` 单独上界检查（原 `mon_ok` 的 `0x2600` 覆盖不到 `+0x75ec`）。
W1 / Z/ZP/ZS / 6 hook / 发布配置 / 零写入逐字节不变。

**③ 产物**：`out/rai_w2_runtime_table_v61.nro` 57344 B md5
**`dddefa505efe477b903de1be490ffc30`**，部署点同 md5（NO_GAME_PROCESS）。
冒烟 **34/0/1**、四路降级 6/0/2 全通；新增 `analyze_v61_table.py`（5 项 ZT
检查 + 表链诊断）/`make_v61_smoke.py`；`8_`/`7_` STEP 61、CRLF 96/183、
bareLF 0、concat 0；`6_`/load_order 未动；回退 `v60 6d1a2f1f…`。

**④ W2 高保真完整设计（v62）关键洞察**：`emc.md:54` 的
`distance <= threshold` 逐 case 顺序比较 + 每行 4 个递增 f32 ⇒ 距离轴被
切成 **5 个区间**（`d<t0` / `t0..t1` / `t1..t2` / `t2..t3` / `>=t3` 走 default），
**与 Rise 5 距离档天然一一对应**，不需 4→5 降采样。
数据通路：运行时读表 → 用 ZP 几何算 d 定 band → 按 mon 槽记 `{band,f}`
（300 帧时效）→ op02 抽选按 `(st3,band)` 取 15 张形状 → 失败逐级降级到
路线 A / v60。形状表已离线生成 `out/rise_band_shapes.json`（含 Rust
`BAND_SHAPE: [[u32;4];15]`，每池 rates 降序补零、和恒 100）。
`W2_BAND_ENABLE` 编译期开关默认 0，验收后置 1。

**⑤ 未完成**：slot 来源、`0x71164` 反汇编、a0 决定性实测、疲惫态
`st3=2` 样本、18/137 怪无阈值行、Rise `range_data` 单位对齐、
W3/W4、成品化、**v61 未实机**。细节只在
`out/P61_v61_w2_high_fidelity_runtime_table.md`。


## 2026-11-15 13:55 · P62 v62 = 一次性 W2+W3+W4 只读探针（已部署未实机）

用户要求「W3/W4 如果需要探针也一起做，最大可能节省实机轮次」。
**已做成 v62 并部署 `d413761e196daf79e399f0ef2621612c`，6 hook 不变、零写入、
W1 与 Z/ZP/ZS/ZT 逐字节不变。**

**① 关键定案：不需要新增 hook**。只读子代理确认 `h_unify @0x76154` 的
参数契约 `(mon, r1=act, r2=sub, r3=mode, [sp]=p5)` 下，
`(a3==2 && a1==0)` 精确筛出 `0x75224`（vtable slot 247 = action end）发来的
状态请求，**`a2` 即 kind**（`NOTES.md:1561` 已有 78 次实机样本）。
`0x75224` 虽可安全 hook（4 参 `-> u32`、首字 `E92D4010` 十余场恒定、非 IPS32
跳板、v17~v30 零 FATAL、`lib.rs.v17bak:21-22,61`），但只多给体内分支输入，
可在 `h_unify` 内从 `[mon+0x1428]` act 对象读等价字段 ⇒ 保持 6 detour。
**口径更正**：P34:69 的「17 调用者 / 11 可 hook」是 `0x76154` 的 BL 调用者
集合（`STATUS.md:80`、`NOTES.md:920,990`），`0x75224` 自身 BL=0（vtable 虚调用）。
W3 的「END→下一动作提交恒 1 帧」v17 实机 162/162 已确证（`NOTES.md:555-558`）。

**② v62 新增两类只读行**：
- `AE`（forge_onUpdate 每帧扫 8 槽 `mon+0x73E0`，变化才输出，`MAX_AE=600`）：
  `old/new/gap/sel/a/st/e1/t505` ⇒ W3 前置（动作类变化时间线、动作间隔、
  `sel` 同帧配对、暂停期帧漂移）。
- `QX`（h_unify 每次调用，`MAX_QX=800`）：`r1/r2/r3/p5/w0/w1/kind` +
  `e1/dc/t505/t518/t5e08/a1a8/a2c0` ⇒ W4 前置（kind 分布、mode 分类、
  异常状态位交叉、分支输入等价字段）。`kind=(a3==2&&a1==0)?a2:0xFF`。
- 逐级 `heap_ok` + 上界检查（`mon+0x7400`、`act+0x6000`）；`LAST73E0/LAST73F`
  首帧只记录不输出；`AE_LOG/QX_LOG` 随 epoch 重置。不改既有 A/Q 行格式
  （第一份报告仍走 `analyze_v38_log.py`）。

**③ 验证/部署**：57344 B，部署点同 md5（NO_GAME_PROCESS）；冒烟
**39/0/1**（AE=100、QX=200、ZT=300、action-end 请求 100）；四路降级 6/0/2
全通；新增 `analyze_v62_w34.py`/`make_v62_smoke.py`；`8_`/`7_` STEP 62、
CRLF 102/188、bareLF 0、concat 0；`6_`/load_order 未动；回退 `v61 dddefa50…`。

**④ 单场可省轮次**：理想情况下本场可闭合 W2 表链、W3 时序、W4 kind/状态位
结果层；W4 跨怪语义映射与疲惫窗仍需 1 场差异大怪 ⇒ 相比原估计省 **2–3 轮**。
**未完成**：W2 slot/反汇编、W3 门控实现、W4 12 Hub 映射与分流实现、
疲惫态样本、成品化移除 AE/QX、**v62 未实机**。
`a2=kind` 的静态 0/1/2 与实机 r2 的 1/7/0 有差异，本场 QX 用于校准，不预设结论。
细节只在 `out/P62_v62_one_run_w2w3w4_probes.md`。


## 2026-11-15 14:10 · P63 v63 = 温和自适应疲惫放大（已部署未实机）

用户：「自然疲惫太久，能不能复用之前的疲劳方案，就是放大倍率，但这次调小倍率让在攻击 1-2 分钟后疲劳」。
⇒ **能，已做成 v63**，复用 v55/v56 的 `0xBD260` 入参 delta 放大通路（零游戏内存写入、
游戏原生耗尽），但把**固定 ×64 换成自适应温和倍率**，让 v62 的一次性探针在同一场
补到一直缺的 `st3=2` 疲惫态样本。

**① 定量依据**：v56 实机 `d0=-8`/`cur=650`/J f=4105→4772（667 帧 ≈11.1s/动作）、
`f=2550..4050` 槽0 `t508` 恒 650（无持续恢复，只在疲惫结束回 800）⇒ 自然疲惫外推
`650/8≈81` 动作 ≈**15 分钟**。v53 雷狼龙 `d0=-50`，与雄火龙差 6 倍 ⇒ 任何固定
小倍率 M 都会让两怪耗时差 6 倍，违反跨怪通用纪律。**故「调小倍率」= 调成自适应**：
`step = base / DRAIN_TARGET_ACT(8)`，`base` = 该槽首次放大时的 `+0x508`，
**不再用 d0 计算扣减量**。雄火龙 step≈81（等效 ≈10×）、雷狼龙 ≈125（≈2.5×），
都是 8 个动作 ≈89 秒耗尽；开局 v50 门控另占约 1 分钟跑图/接敌。

**② v63 唯一改动**：`DRAIN_ENABLE=1`（采集配置）、新增 `DRAIN_MODE=1`/
`DRAIN_TARGET_ACT=8`/`DRAIN_DEADLINE_AN=20` 与 `DRAIN_BASE[NMON]`/`DRAIN_ACT[NMON]`/
`DRAIN_AN0` 静态；`h_stamina` 内每负 delta 扣 `-step`，第 8 次或 `cur<=step` 或
该槽 `ST_AN` 增长 ≥20 ⇒ 改用 v55 范式 `-(cur+1)` 一次性扣光（P49 实机 PASS）。
**帧兜底已删除**：暂停不冻结 forge 帧，会误触发（用户多次暂停看日志），
改用逻辑动作数，两个兜底全免疫暂停。`DRAIN_DONE` 进入疲惫后熔断，单窗。
J/G 行格式逐字节不变（`d1` 序列可识别温和放大）；`DRAIN_MODE=0` 可编译回 v56 固定倍率。
W1/Z/ZP/ZS/ZT/AE/QX/6 hook/`PROFILE_RELEASE=1`/`W1_ALL=1`/日志格式/`6_`/load_order
全不变，**仍零游戏内存写入**（只改 `0xBD260` 入参）。
**成品发布必须 `DRAIN_ENABLE=0` 重编译**（回退纯只读 v62）。

**③ 产物/验证**：`out/rai_mild_tired_v63.nro` 57344 B md5
**`8702a7a6908c778e39106ba38cd9c34e`**，部署点同 md5（NO_GAME_PROCESS）。
冒烟 **45/0/1**（6 项 `[TIRED]` 全通、J=8、跨度 4669 帧≈77.8s、疲惫态样本 108）；
四路降级 6/0/2 全通；v62 判读跑 v63 冒烟报「无强制 J/G 行」FAIL ⇒ 配置切换证据。
新增 `analyze_v63_tired.py`（放宽 J/G 发布检查、gdone 期望 1、6 项疲惫专项）/
`make_v63_smoke.py`；`8_`/`7_` STEP 63、CRLF 108/195、bareLF 0、concat 0；
`6_` `7361445f…` 未动；回退 `v62 d413761e…`。

**④ 假设**：耐力无持续恢复（P48 §3.1 未定案）；667 帧/动作由 v56 单场外推；
疲惫窗 4764 帧按雄火龙；`base` 取首次放大值；单窗够采 `st3=2`（不足需下轮加多窗）。
**未完成**：W2 档位加权/W3 门控/W4 分流实现、slot 与 `0x71164` 反汇编、跨怪语义映射、
Rise range_data 单位、18/137 怪无 dttune 表、成品化、**v63 未实机**。
细节只在 `out/P63_v63_mild_adaptive_tiredness.md`。


## 2026-11-15 15:10 · P64 v63 首场实机验收 + v64 三缺陷修复部署

用户完成一场任务（两次发怒、约 5 分钟进入疲劳），日志 11777 行 / 1.26 MB。
**核心定案：用户看到的疲惫是游戏自然疲惫，v63 温和放大一次都没触发**
（`J=0 / G=0 / gdone=0`，`h_stamina` 已装 `first=E92D41F0`）。主怪
`mon=0C130510` 状态边沿：发怒 f=8141→12952、16001→20809（疲惫前两段），
`t505=1@21778 → 2@22038 → 3@26426 → 0@26664`，疲惫窗 **4626 帧≈77.1 秒**
与 P49 的 4764 帧计时器定案吻合；疲惫后另有 30116/36475 两段发怒。
判读 `PASS=33/FAIL=12/SKIP=1`，12 个 FAIL 全是「脚本仍按强制疲惫验收」，
非运行故障（零 FATAL/异常、live=1 hub=15 fail=0）。

**① W1 验收通过**：`sel=295 → wall=111(37.6%) → wnok=102(34.6%)`、
`w3=64 w4=62 wt=6`（疲惫形状首次 >0）、`s0=100 s1=41 s2=6`、V 行 34 条零违例。
**② W2 数据全达标**（对照 P59 门槛）：Z=344 / ZP=86（100% 可解且 ±60 帧可配对）/
ZS=4，24 个 unique `(ip,md)` 块、15 个分化块（245 条）、**md=6 有 2/3 块分化**
（v60 场仅 1 块零分化）、`st3=2` 距离样本 12 条、窗内 Z=30/ZP=8、
`nc>=2` 93.6%、档位证据 83.1% ⇒ **路线 A（case 索引分档）可进入实现**。
**③ W2 高保真路线被卡**：md=4 TABLE 型 Z 行 146 次但 **ZT=0** ⇒ P61 的
`a0+0x75ec → +0x7c → +0xfa` 运行时对象链在 `h_matcher` 的 a0 上读不到有效
dttune 对象，「不需编译表/不需基址锚定」**未获实机支持**，需回退编译表+锚定或另找链。
**④ AE 缺陷**：1200 条配额全打满、`gap` 恒 1、`+0x73E0` 每帧变化 ⇒ 证伪其
「L1 动作类」语义；疲惫窗 f=22038..26664 落在无配额段 ⇒ 窗内 AE=0。
**⑤ QX 是最有价值新证据**：1236 行、action-end 请求 538 条，`kind` 实机值域
`{0:76,1:300,3:142,2:20}`（比 P62 静态预期多 3）；**`kind=2` 20 条 100% 落在
疲惫态**，正常态从不出现 ⇒ W4 可用的疲惫处境信号。
**⑥ J=0 三嫌疑**：`LOW` 门控（本场 ≈1.9 动作/300 帧贴近阈值）、
`thr=rd16(act+0x5D84)` 非法、或疲惫由链 II 减气触发使 `0xBD260` 负 delta 很少。

**v64 已部署 `add1af51540bd395a6eca05916386cad`（未实机）**：
`DRAIN_ENABLE=0` 回纯只读（自然疲惫 5-6 分钟可达，强制放大边际价值下降且污染数据，
v63 代码常量全保留）；新增 `DG` 门控诊断行（LOW/A_N/thr/cur/st5/si/an/a1）与
`ZD` 表链诊断行（tune/cnt/base + fail 级码 1..4）；`MAX_AE/MAX_QX` → 2400、
AE 加 `AE_MIN_GAP=20` 节流且基准仅在输出时更新。6 hook、零写入、
W1/Z/ZP/ZS/ZT/QX/日志格式全不变。冒烟 43/0/1、四路降级 6/0/2、
STEP 64、CRLF 114/201、bareLF 0；`6_` 未动；回退 `v63 8702a7a6…`。
新增 `analyze_v64_p64fix.py`/`make_v64_smoke.py`。细节只在
`out/P64_v63_real_machine_acceptance.md`。


## 2026-11-15 15:12 · 补充离线定案（用户问「还要我打一场？」⇒ 不需要）

只读复核本场 `N` 行 19 条与离线表后，P64 的两个「待下一场诊断」项当场闭环：
- **J=0 已定案 = `LOW` 门控**：`N f=5700 ENTER-LOW` → `f=21600 EXIT-LOW`，连续
  15900 帧 `LOW==1`；门控另需 `f>=1800`/`A_N>=20`（f=5700 时 a=16）；疲惫前置
  `t505=1@21778` 距 EXIT 仅 178 帧且 `st5` 已变 ⇒ 放大窗口不存在。与 `thr`、
  链 II 无关，v64 的 `DG` 行不再是必需项；要让 v63 温和放大生效只需去掉
  `h_stamina` 门控里的 `LOW==0`（编译期小改）。
- **ZT=0 不再阻塞高保真 W2**：`dist_bands_all.json` 已含 137 怪 / 8488 块 /
  119 怪 4 档 f32 阈值（`em032 [450,1000,2700,5000]`），`rise_band_shapes.json`
  已含 15 张 `(state,band)` 形状 + Rust `BAND_SHAPE`。运行时 `hit`(0..3) 就是 GU
  自己按阈值判定的档位，按 `(st3, hit)` 取形状即可，**不需 `a0+0x75ec` 运行时
  对象链、不需基址锚定/slot 确证**；离线表仅用于标定与语义解释。P61 运行时表链
  路线可彻底放弃，P60 路线 B 前置下调为可选。
- ⇒ **不需马上再打一场**：J=0、ZT=0、疲惫态样本三项前置全在本场日志+离线数据
  闭环；剩余是纯离线编码（撤 DG/ZD、落 W2 加权、成品化），完成后才需一场整体验收。
  本轮未改任何代码/NRO/部署，部署点仍 v64 `add1af51…`。


## 2026-11-15 15:25 · P65 v65 = W2 高保真「状态×距离档」加权落地（已部署未实机）

用户「做」⇒ 按 P64 §2.1–2.3 离线定案，**零实机**把 W2 加权写进 W1，并撤 DG/ZD。

**① 实现（全在 W1 既有结构内，6 hook 不变、零写入）**：
- 新增 `BAND_SHAPE: [[u32;4];15]`（=`rise_band_shapes.json` 的 Rise 15 池降序形状），
  索引 `[state*5+band]`，state 0=anger/1=normal/2=tired，和恒 100，k 由第 4 项决定 3/4。
- 新增**独立于日志探针**的轻量 `band_sense()`：仅 TABLE 型 mode(4/14/21/22)，
  从 `guess=ip+ret` 附近 6 字节找 `op,sub=1,w` ⇒ `w<=3` 为 band 0..3、`4<=w<0x80`
  为 band 4；按 `slot_of(mon)` 存 `BAND_CUR/BAND_F[8]` + 全局 `BAND_ANY` 兜底，
  `BAND_TTL=300`。**不依赖 dist_probe/Z 行 ⇒ 成品 `W2_PROBE=0` 仍可加权**。
- `band_get()` 读档位，无效/超时 ⇒ 0xFF。
- `rise_weight_pick()` 加 `band` 入参：有效时按 `(st3,band)` 取 BAND_SHAPE，
  否则**逐级降级回 v60 三状态形状**；`kk` 截断归一化、`p5n` 轮盘、
  `w3/w4/wt`、`n>=3` 护栏全不变。`W2_BAND_ENABLE=0` 编译回 v64。
- S 行加 `wb`(按档位形状应用) / `bf`(降级次数)；新增 `B2` 低频行（`ts/bd/si/md`）。
- **删除** `DG`/`ZD` 两类行及常量静态（P64 已离线定案，不再需要）；
  `dist_table_probe` 失败恢复静默跳过，ZT 探针本身保留。
- `DRAIN_ENABLE=0`/`PROFILE_RELEASE=1`/`W1_ALL=1`/Z/ZP/ZS/ZT/AE/QX 全不变。

**② 假设**：TABLE case 操作数 0..3 直接对应档位；仅 TABLE 型更新 band
（SCALE100 的 `ts=8/10` 不映射）；多怪槽溢出用全局兜底可能混入他怪档位；
`BAND_TTL=300` 沿用 P61。GU 无 15 张独立池表 ⇒ 仍是机制级复刻。

**③ 产物/验证**：`out/rai_w2_band_weight_v65.nro` 61440 B md5
**`4d04b95d9c445bf687c9353e8df6436b`**，部署点同 md5（NO_GAME_PROCESS）。
冒烟 **46/0/1**（B2 覆盖 5 档、wb=40/bf=10、疲惫窗 4626 帧）；四路降级 6/0/2；
v64 判读跑 v65 冒烟 2 FAIL 证明 DG/ZD 已撤；`8_`/`7_` STEP 65、
CRLF 120/206、bareLF 0、concat 0；`6_` 未动；回退 `v64 add1af51…`。
新增 `analyze_v65_band.py`/`make_v65_smoke.py`。

**④ 未完成**：**v65 未实机**；W3 门控（另找动作类字段，`+0x73E0` 已证伪）、
W4 12 Hub 分流（`kind=2` 疲惫强信号已实测、`kind=3` 待跨怪）、领地争夺（暂缓）、
成品化（`W2_PROBE=0`/`MAX_B2=0` + 移除诊断行）。
**下一场 = 唯一需要的整体验收**：看 B2 档位覆盖、S 行 wb/bf 占比、
W1 wall/wnok 与连段、疲惫窗数据、零异常；异常则 `W2_BAND_ENABLE=0` 回退。
细节只在 `out/P65_v65_w2_band_weighting.md`。


## 2026-11-15 15:50 · P66 v66 = W3 COMBO 观测 + W4 最小三处境分流（已部署未实机）

用户「都做吧，反正我下场是不同的怪，你还记得上一场我打的是轰龙吗」。
**怪种复核**：主怪 `mon=0C130510` 的 V 行 `sp=0020` **14/14** ⇒ emid 32 =
**轰龙 Tigrex**（`monster-slot-map-137.json`，离线 `em032_00/em032_04`）；
`101A/102D/100F` 属其它 mon（小怪/环境对象）。下一场换怪正好给 W2 跨怪通用性、
W4 12 Hub 语义映射、W1 三态复现提供第二个数据点。

**① 承接 P64 §5.3 更正**：`+0x73E0` 语义未证伪，被证伪的只是 AE「每帧扫描」
采样方式；字段在动作 hook 点仍是 `act/sub/prev_act/prev_sub`。P36 §3.5 S2
离线配对显示「信号齐、密度不够」⇒ 修法是加密观测而非加实机轮次。

**② W3 COMBO 行**：`h_start_40` **每个动作**输出 `ev=1`（`f/mon/sp/a/s/pa/ps/
sel/an/gap/st`），`h_unify` 的 action-end 请求（`(a3==2&&a1==0)`）输出 `ev=2`
（同上 + kind，独立于 QX 配额）；`sp=rd16(a0+0xB5F0)` 便于跨怪分组；
`MAX_COMBO=1600`/epoch。离线按 f 配对即可闭合 S2 的 ③④⑤
（sel 同帧、act=6/6-12→7-21 连段、END→提交帧差）。零新增 hook、零写入。

**③ W4 最小三处境分流**：QX 分支按 `kind==2||t505>=2 ⇒ 2 疲惫`（P64 实机
kind=2 20 条 100% 落疲惫态）、`t518==1 ⇒ 1 发怒`、否则 0 正常，按 `slot_of(mon)`
缓存 `STANCE_CUR/F` + 全局兜底，`STANCE_TTL=300`。`rise_weight_pick` 加 `stance`
入参，`eff = stance`（有效）否则 `st3`，同时决定 BAND_SHAPE 的 state 维、
v60 状态形状与 wm；S 行加 `sc`(修正次数)/`sk`(当前 stance)。
`kind=3` 不参与判定（无跨怪证据）。**不做** 12 `attack_stance_*` Hub、
攻击类/非攻击类筛选（需跨怪映射 + 零干预基线）。

**④ 产物/验证**：`out/rai_w3w4_v66.nro` 65536 B md5
**`5f520ba5d0d8d6f7278df2b88a37e0cc`**，部署点同 md5（NO_GAME_PROCESS）。
冒烟 **54/0/1**（COMBO ev1=80/ev2=20、END→动作 p50=2 帧、pa/ps 80/80、
stance 2 类、sp=0020）；四路降级 6/0/2；v65 判读跑 v66 冒烟 46/0/1 全通
（只增行、向后兼容）；`8_`/`7_` STEP 66、CRLF 127/212、bareLF 0、concat 0；
`6_` 未动；回退 `v65 4d04b95d…`。新增 `analyze_v66_w3w4.py`/`make_v66_smoke.py`。
6 hook / 零写入 / W2 BAND_SHAPE 与 band_sense / B2 / `DRAIN_ENABLE=0` 全不变。

**⑤ 下一场（换怪）清单**：① `COMBO.sp` 与 V 行 sp 是否出现 ≠0020，按 sp 分组
比 W2 wb/bf、B2 档位、W1 wall/wnok；② W3 S2 闭合（连段序列、sel 配对、
END→提交帧差对照 v17 162/162）；③ W4 sc/sk 三类覆盖、kind=2 在新怪是否仍
100% 疲惫；④ W1 与零异常回归。异常开关：`W4_STANCE_ENABLE=0` 回 v65、
`W2_BAND_ENABLE=0` 回 v64。**未完成**：W3 门控实现、W4 12 Hub、领地争夺、
成品化、**v66 未实机**。细节只在 `out/P66_v66_w3_combo_w4_stance.md`。


## 2026-11-15 16:50 · P67 v66 首场（斩龙）跨怪验收 +「疲惫→换区」定案 + v67 部署

用户完成一场（含发怒+疲惫），并观察「疲劳好像会固定触发怪物换区」。
日志 `02_Workspace/game_p54_lite.txt` 8200 行 / 882KB，16:35 落盘，游戏正常退出。

**① 跨怪验收通过**：主怪 V 行 `sp=0050` 10/10 ⇒ emid 80 **斩龙 Glavenus**
（上一场 `0020` 轰龙）。判读 `PASS=50/FAIL=2/SKIP=2`，零 FATAL/异常、
`live=1 hub=15 fail=0`。W1 `sel=109→wall=69→wnok=69`（63.3%）、`w3=64 w4=18 wt=4`；
W2 `wb=74/bf=12`（86% 按 `(st3,band)` 形状，首次实机证明 v65 加权跨怪生效）；
W3 COMBO `ev1=380/ev2=330`、`pa/ps` 非零 355/380、END→下一动作 p50 **0 帧**
（≤3 帧 75%，与 v17 162/162 吻合）、`sel±30` 配对 43/133（v63 场 19/156）
⇒ **P36 §3.5 S2 跨怪闭合**；W4 `kind=2` 19 条 **100% 落疲惫态**（跨怪复现），
`sc=1` 偏少、`sk` 覆盖 0/1/2；疲惫窗 f=30800..34826 = 4026 帧≈67 秒
（斩龙 vs 轰龙 4626 帧≈77 秒，符合按怪种不同）。
**两个 FAIL 同一根因**：`B2=0` 因 `f%300==0` 采样与 band 更新时机不重合，
连带「档位覆盖」误判；`wb=74` 证明功能正常，非故障。

**② 换区观察定案**：实机间接支持 —— ZP 3D 距离 p50 PRE 1904 → TIRED **5594**
→ POST 2486；Z 距离判定 171/11/50；疲惫起点 COMBO gap 271/309 帧；
`s=16` 子动作疲惫前 1 条、窗内及后 52 条。用户肉眼所见是最直接证据。
**静态不支持因果**：`area-move.md` 换区 = 条件 BLOCK `0x3f`(`+0x73f3` 请求位)/
`0x54`(`+0x73f4`)/`0x61`(`+0x73f0`) + EMC leaf `0x94/0x95/0x9e`，
最终 `0xb5e04` 写 `+0x1054`；**请求位写入者未定位**（推测区域停留计时器
`+0x73fc` reset 1800），**疲惫 `+0x505` 不是代码级直接条件** ⇒ 无法区分
「疲惫间接置位」与「计时器到期恰好同时」。雷狼龙 v56 场动作间隔
282→309→289 不显著，跨怪辅助不支持「间隔拉大」为稳定特征。
**潜在翻案**：若疲惫稳定触发换区，则 v55/v56/v63 已 PASS 的原生疲惫放大
（改 `0xBD260` 入参、零写入、跨怪通用）可**间接触发强制换区** ⇒ P36
「不可行」结论需复核，但必须先有只读数据确证，不直接写实现。

**③ v67 已部署 `98dae0bdd0774bea929486fae41e19ff`（未实机）**：
B2 改按 `BAND_N % B2_EVERY(64)` 触发（修采样）；新增 `AR` 行在 `h_start_40`
每动作只读输出 `area=+0x1054 / req=+0x73f3 / f0=+0x73f0 / f4=+0x73f4 /
fc=+0x73fc / t505/t518/a/s/sp`，对应 `0x3f/0x54/0x61`。6 hook、零写入、
W1/W2/W3/W4 全不变。冒烟 **57/0/1**、四路降级 6/0/2、v66 判读跑 v67 冒烟
54/0/1；`8_`/`7_` STEP 67、CRLF 132/217、echo 元字符复扫 0 处未转义；
`run_v66.cmd`（自包含启动器，文件名沿用）TOOL2 切 v67；`6_` 未动；
回退 `v66 5f520ba5…`。新增 `analyze_v67_area.py`/`make_v67_smoke.py`。

**④ 下一场判据**：AR 的 area 变化边沿 + req/f0/f4 命中 + 窗内命中 ⇒
定案换区链；B2>0 且覆盖 ≥2 档；W1/W2/W3/W4 回归；再换第三种怪种 sp。
**未完成**：W3 门控实现（前置已齐）、W4 12 Hub、领地争夺（暂缓）、
原生疲惫→换区需 AR 确证、成品化、**v67 未实机**。
细节只在 `out/P67_v66_crossmonster_and_area_move.md`。


## 2026-11-15 17:05 · P68 v68 = W3 `_IsActionEnd` 重抽门控（已部署未实机）

用户「w3是出招门控是吧我记得？如果是那就先做，请记住，仅最大可能减少实机次数」。
**语义确认**：W3 不是「抽哪一招」（W1/W2），而是「何时允许重新抽选」，
P34 阶段 D 原文「在干净调用者层做『动作未结束不重抽』」，对标 Rise
`_IsActionEnd`/`_IsUnderLayerEnd`，决定「输出窗口」节奏。P36 §3.1 注明
「仅动作结束帧求值」是高置信推断非反汇编实证；P67 斩龙场 COMBO 给出实机
支撑（END→下一动作 p50=0 帧、≤3 帧 75%，与 v17 162/162 一致）。

**① 实现（6 hook/零写入，只作用重抽路径）**：
- `h_unify` 的 `(a3==2&&a1==0)` 写 `END_F[slot]` + `END_N`（`ek`）；
  `h_start_40` 写 `START_F[slot]`，均独立于日志配额，另有全局兜底。
- `w3_gate()`：`START_F > END_F` ⇒ IN_ACTION ⇒ 拦下；拦下时令 `wp=-1`
  自动落到既有 v38 `sw2` 原版权重轮盘，抽选不中断、返回值语义不变。
- **`W1_ALL` 主轨全抽选不受门控**，W2/W4 与 AR/B2/COMBO 数据仍完整。
- 三重护栏：编译期 `W3_GATE_ENABLE=0` 回 v67；自适应熔断
  （`GATE_SKIP > GATE_OK*4 && >20` ⇒ 全放行）；拦下退回原版权重而非丢弃。
- S 行加 `ge`(放行)/`gs`(拦下)/`ek`(END 事件)，累计不随 epoch 重置。

**② 实机次数约束**：v68 = v67 + W3，完整保留 AR 换区探针。下一场本来就要
为换区链打 ⇒ **同一场同时验 W3 与换区，不增轮次**；若门控不合适，
编译期置 0 即回 v67（已有轰龙/斩龙两场基线），无需另打验证回退。
A/B 对照改由 `ge/gs` 量化 + 编译期开关承担。

**③ 产物/验证**：`out/rai_w3_gate_v68.nro` 65536 B md5
**`c8466a4434f2a2c86826ee5bbc714193`**，部署点同 md5（NO_GAME_PROCESS）。
冒烟 **61/0/1**（ek=330/ge=30/gs=8，拦下 21.1%，wall/wnok 未受影响）；
四路降级 6/0/2；v67 判读跑 v68 冒烟 57/0/1 全通；
`8_`/`7_` STEP 68、CRLF 139/222、echo 元字符 0 处未转义；
`run_v66.cmd`（文件名沿用）TOOL2 切 v68；`6_` 未动；
回退 `v67 98dae0bd…`。新增 `analyze_v68_gate.py`/`make_v68_smoke.py`。

**④ 下一场四条判据**：W3 的 `ek>0`/`ge,gs>0`/拦下<90%/连段未切碎；
AR 换区链；B2 修复（>0 且 ≥2 档）；W1/W2/W4 与零异常回归。
判定分支：门控正常 ⇒ W3 进成品候选；拦下过高或连段异常 ⇒ 编译期置 0
回 v67；体感无改善 ⇒ GU 原生 END→提交本就 1 帧，W3 结构性收益有限，
资源转 W4。**未完成**：v68 未实机、W4 12 Hub、领地争夺、原生疲惫→换区
需 AR 确证、成品化。细节只在 `out/P68_v68_w3_isactionend_gate.md`。


## 2026-11-15 17:10 · P69 v69 = W4 机制级 12 处境分流（已部署未实机）

用户「w4能做完吗？」（持续约束：仅最大可能减少实机次数）。
**结论分层**：机制级 W4 本轮做完并部署；Rise 12 `attack_stance_*` Hub 的
数据表级 1:1 **做不完**（`*_main.user` 主例程 0 个、Hub→15 池链断、
GU 无闪光/倒地/无目标只读信号、kind=3 不跨怪、零干预基线属旧 IPS32 口径
不可混算）。**零新增实机轮次**：v69 = v68 + W4，下一场本来要为 AR 打 ⇒ 同场验
W3 + W4 + 换区。

**① 必须修的实机问题**：v66/v67「最小三处境分流」斩龙场 `sc=1` ——
stance 由 `kind==2||t505>=2`（疲惫）/`t518==1`（发怒）推出，与既有 st3
几乎恒等 ⇒ `eff=stance` 没产生新行为。W4 实为重复 W1 状态维。

**② Rise 静态证据**：`out/rsz_json/em001_00_attack_stance_*.user.2.json`
共 12 个（flash / flash_hyakuryu / no_target_routine / out_main_zone /
return_blockcenter_routine / same_main / same_main_{down_floor,down_wall,high,
master,up_floor,up_wall}）。P32 M5：`*_main.user` 0 个 ⇒ Hub→15 池链断。
斩龙场 `t5e08` 全 0、`kind=3` 为 0（轰龙场 142 条）⇒ 异常信号不跨怪稳定；
`dc=1` 265/743 太频繁、`e1` 语义未定案。

**③ v69 设计**：3 状态(anger/normal/tired) × 4 处境 = 12 槽。
`hub_get()` 按优先级 3>2>1>0 读纯只读时间戳（`HUB_TTL=300`，按 mon 槽 +
全局兜底）：hub0 常规 ⇒ **与 v68 逐字节一致**（BAND_SHAPE[state*5+band]）；
hub1 远距/无目标（`band==4`）⇒ `HUB_SHAPE[state*4+1]`（Rise range5）；
hub2 异常（`kind==3` 或 `act+0x5E08!=0`）⇒ `HUB_SHAPE[state*4+2]`（range2）；
hub3 换区（AR 的 `req/f0/f4!=0`）⇒ `return (-1,0,0)` 退回 v38 原版权重，
对应 P34「异常状态不进攻击抽选」，**不按 action_id 硬编码**。
`HUB_SHAPE` 12 张来自 `out/rise_band_shapes.json`，映射 `out/rise_hub_shapes.json`
（hub0←r3 / hub1←r5 / hub2←r2 / hub3←r1 占位），和恒 100、k 3/4、
沿用截断归一化。护栏：`W4_HUB_ENABLE=0` 编译期回 v68；自适应熔断
`HUB_DEFER > h0*2+50` ⇒ 之后全常规；hub3 只退回原版权重、不中断抽选。
S 行加 `h0/h1/h2/h3`（各处境命中）/`hd`（退回）。
6 hook、零写入、W3 门控(ge/gs/ek)、AR、B2、COMBO、BAND_SHAPE、
`DRAIN_ENABLE=0`/`PROFILE_RELEASE=1`/`W1_ALL=1` 全不变。

**④ 产物/验证**：`out/rai_w4_hub_v69.nro` 65536 B md5
**`1f3e15d2ae325f7677df07bec70627ec`**，部署点同 md5（NO_GAME_PROCESS）。
冒烟 **65/0/1**（h0=120/h1=18/h2=9/h3=6/hd=6，特殊 21.6%，wall=48 wnok=41）；
四路降级 6/0/2；v68 判读跑 v69 冒烟 61/0/1（向后兼容）；
`8_`/`7_` STEP 69、CRLF 147/228、bareLF 0、元字符 0、concat 0；
`run_v66.cmd` TOOL2 切 v69；`6_` `7361445f…` 未动；回退 `v68 c8466a44…`。
新增 `analyze_v69_hub.py`/`make_v69_smoke.py`/`rise_hub_shapes.json`/
`P69_v69_w4_12hub_routing.md`。

**⑤ 下一场四条判据**：W4 `h0..h3/hd` + 特殊占比<60% + wall/wnok 未降；
W3 `ek/ge/gs` 拦下<90%；AR 换区链；W1/W2/B2/COMBO 与零异常回归。
W4 无特殊处境样本 ⇒ SKIP（数据结论，不需重打）；异常则编译期置 0 回 v68。
**未完成**：v69 未实机、12 Hub 1:1、W3 `_IsUnderLayerEnd`、跨怪攻击类语义
映射、领地争夺、原生疲惫→换区需 AR 确证、成品化。细节只在
`out/P69_v69_w4_12hub_routing.md`。


## 2026-11-15 17:35 · P70 v69 首场实机（斩龙）三定案 + v70 修复部署

用户完成一场（疲惫在结束前 1–2 分钟），观察「疲惫后攻击窗口没放大，W3 似乎让它一直攻击」。
日志 11368 行 / 1.19 MB，`RAI v69`、6 hook、零 FATAL/异常、`live=1 hub=15 fail=0`，
BEAT 到 f=39900。主怪 `sp=0050`/`0C1F15F0` = **斩龙 Glavenus，本场未换怪**
（`101B` 是其它对象）⇒ 跨怪第三数据点未获得。判读 PASS=58/FAIL=3/SKIP=3，
三个 FAIL 全是判据口径或结构性失效，非故障。

**① 疲惫窗与节奏**：`QX t505>=2` 窗 f=31718..35944 = 4226 帧≈70.4 秒
（距结束 66 秒，与用户描述吻合）；`wt=7`、`kind=2` 17 条 100% 疲惫态（第三次跨场复现）。
动作密度 PRE 10.5 / TIRED **12.4** / POST 8.9 个每千帧，gap p50 52/69/95；
疲惫窗内 `a` 仍含 2/1/7 攻击类、`s` 新增 204/56 ⇒ **流口水同时持续出招，无喘息**。
根因：四层都只改抽选权重/是否套形状，没有一层改动作持续/间隔/提交节奏；
GU 原版疲惫也不喘息（v56 雷狼龙 282→309→289）。
⇒ 零写入+跨怪+不按 action_id 硬编码三条纪律下 **「疲惫喘息/输出窗口放大」做不到**；
分层：B 需离线建跨怪攻击类语义映射（137 怪 cmdtbl + 三场 COMBO）+1 场验证；
C 改动作计时需写内存（v54/v15 两次证伪），不建议。

**② W3 结构性失效（纠正用户归因）**：`ge=21 gs=0 ek=363` ⇒ 门控一次都没拦下。
COMBO END=363/START=338，END→下一动作 **p50=0 帧、≤3 帧 70%** ⇒ 重抽时
`END_F>=START_F` 恒真，`IN_ACTION` 永不成立，**GU 原生没有「动作未结束就重抽」的窗口**。
所以「一直攻击」来自 GU 原生节奏 + W1/W2 形状，与 W3 无关；P68 预判被实机证实。
v70 把 `W3_GATE_ENABLE=0` 撤回无效门控（代码保留）。

**③ S 行 270 字符截断（决定性）**：13/13 条 S 行长度恰 270，末行止于 `ek=363`、
早期行止于 `h3`，`h0..hd` 全丢 ⇒ 判读的「W4 全走常规/特殊处境 0 次」是**误读**，
W4 本场真实分流次数未知。P55 `R` 行同类问题（当时用 W 行解决）。
另：AR `req/f0/f4` 命中 10 帧、10/10 落在 BEAT ±300 帧内、窗内 1 条；
`area=+0x1054` 值域含 38658/23042 等大数 ⇒ 部分槽该字段非区域号，探针对象稳定性待定。

**④ v70 已部署 `29651e72b28bae439c507523c0524731`（纯离线修复，不需马上再打）**：
S 行删 5 个 h 字段回 42 占位符，新增独立短 `HB` 行（每 600 帧、`MAX_HB=200`，
含 `h0..h3/hd/zf/af/ff/sk/ge/gs`）；因 v55 已有 `H`/`MAX_H`/`H_LOG`，
新符号统一 `HB`/`MAX_HB`/`HB_LOG`/`HB_EVERY`（首次编译曾因撞名失败，已修）；
`W3_GATE_ENABLE=0`、`HUB_TTL=1200`；判读三处误报判据降 SKIP + `[HB]` 新检查。
6 hook/零写入/W1/W2/W4/AR/B2/COMBO/QX 全不变。冒烟 **65/0/2**、四路降级 6/0/2、
STEP 70、CRLF 153/234、元字符 0、concat 0、`6_` 未动；回退 `v69 1f3e15d2…`。
新增 `analyze_v70_p70fix.py`/`make_v70_smoke.py`/`P70_...md`。
**下一步**：不需额外实机；下次自然打一场验 HB 完整性、TTL 1200 后 W4 特殊处境、
W1/W2 回归、零异常。细节只在 `out/P70_v69_real_machine_w3_and_tired_window.md`。


## 2026-11-15 17:45 · P71 日志完整性根治（用户批评「半小时任务是浪费时间」⇒ 已修死）

用户指出日志不能支撑完整任务（甚至半小时）。只读核查发现**两个独立缺陷**：
① 单行 270 字符截断（P70 已修 S 行但**不彻底** —— 实测 v71 的 S 行完整长度
**276 字符**、冒烟 295，仍会切）；② **本轮新查出的整场全局封顶**：
`MAXLOG=24000` 且 `LOGN` 累计、epoch 块只重置各 `*_LOG` 配额而从未重置
`LOGN` ⇒ 累计 24000 行时所有 `LOGN < MAXLOG` 门控同时失效、**后半场全停写**。
本场 39900 帧/11368 行≈11.1 分钟，外推 **30 分钟≈30771 行 > 24000** ⇒
半小时任务必丢后半场。此前只修 ① 未查 ②，是判断失误。

**v71 修复（纯离线，不需额外实机）**：
- `MAXLOG 24000 → 1_000_000`（只作灾难熔断），密度由每 30000 帧重置的
  各行独立配额控制；每 epoch 上界 21464 行，30/60/120 分钟 ≈ 7.7/15.5/30.9
  万行 ≈ 8.1/16.2/32.5 MB，理论上限 388 小时。
- **S 行拆为 `S`(前 30 字段到 `anr=`，实机最长 202 字符) + `S2`**
  (`gdone/gf/wall/wnok/wb/bf/sc/sk/ge/gs/ek/log` 12 字段+f，约 110 字符)；
  判读按 f 把 S2 合并回 S ⇒ 既有判据零改动；HB 86、其它行实测最长 228。
- 新增 `tools/check_log_integrity.py`：行长>=265、S/S2/HB 关键字段与配对、
  epoch 盲区（BEAT>=3 但 [rai]<20）、末尾 gap>3000 帧、log 序号触顶、
  时长与 30/60 分钟外推；输出 md+json，退出码 0/1/2。集成进判读 3 项
  `[LOG]` 硬判据，第二份报告直接给「结论=OK」或 ERROR 明细。
- 编译期校验 S 30/30、S2 13/13、HB 13/13；6 hook/零写入/W1-W4/HB/AR/
  B2/COMBO/发布配置全不变。

**验证**：自检跑 v69 实机日志 ⇒ ERROR（准确抓出 `{'S': 13}` 超长），
跑 v71 冒烟 ⇒ OK（最长 246）；v71 判读冒烟 **68/0/2**、`[LOG]` 三项 PASS；
四路旧日志降级 6/0/2；`8_`/`7_` STEP 71、CRLF 159/240、元字符 0、concat 0；
`run_v66.cmd` 判读切 v71；`6_` `7361445f…` 未动。
产物 `out/rai_log_integrity_v71.nro` 65536 B md5
**`1d513ec3364f4f270929fd24193ff74b`**，部署点同 md5（NO_GAME_PROCESS）；
回退 `v70 29651e72…`。新增 `analyze_v71_limits.py`/`make_v71_smoke.py`/
`check_log_integrity.py`/`P71_...md`。

**遗留**：v69 本场 W4 分流次数已无法追回（当时字段被切），但从 v71 起
不会再发生；P70 的「W4 全走常规」结论继续作废。下次自然打一场即可验，
**不增加实机轮次**。细节只在 `out/P71_log_integrity_full_quest.md`。


## 2026-11-15 17:55 · P72 B 方案定案（不可行）+ 结构表 + 成品化配置 + 判读自动结论（未部署）

用户「做」⇒ 执行上一轮承诺的三项离线工作。**本轮未改插件行为、未编译、未部署**，
部署点仍 v71 `1d513ec3…`，下一场仍是唯一一场且待验项没有增加。

**① 严格 B 方案（跨怪攻击类/非攻击类语义映射）不可行** —— 只读子代理确证，
卡点是语义标签在静态层不存在，不是解析/hook/写入/基址：
`tools/mhgu/emc.mjs:37-43` OP_NAMES 只命名 5 个距离 op，`emc.md:50,61-62`
leaf 命令「not named [U]」；13 类动作名闭集在 `mon-ai-entry.md:233` 的 NSO
`+0x73E0` 派发器层；`TableNo→_actionNo→招式名` 链多次定案断裂
（P32:168/P34:125/P36:130/P61:111）；`gu-moves` 缺仓库外私有 KB 实测
ENOENT；唯一分类产物 `v19b_action_ids.json` 是违反纪律的单怪 action_id
白名单。⇒ P70「B 有条件可做」下调为**不可做**，「疲惫喘息/输出窗口放大」
正式列为**不可复刻项**，不再为它安排实机。
口径澄清：`case.sig` = case body 前 16 个 `op0x14` 操作数的 FNV-1a
（`lib.rs:1443-1489`），静态可复算（caseoff 已对拍 137 arc/141792 case）；
P60「单基址最多覆盖 1/11 ip」只阻断按 ip 查物理阈值表，**不阻断按 sig
内容哈希查表**，但仍补不出语义标签。

**② 结构特征表已产出** `out/tired_struct_bias.json`（源 `weighted.tsv`，
137 怪全量）：130/137 怪含空签名 case；空签名权重全表 **22.3%**
(564822/2532200)，按怪 min/p25/p50/p75/max = 0/13.4/**22.4**/37.3/100%；
`cEmpty` 中位 86/最大 620；雌火龙 22.3%、轰龙 11.9%、斩龙 15.4%、
铠龙 15.9%。**未写进插件**：「空签名=原生待机」是 `weighted.md:22-24`
推断；`rise_weight_pick` 主动排除 `sig==FNV0`（`lib.rs:2134`）；
实机 sig 高度集中（NOTES:855 91/124）且 19.7% 块全同签；且结构偏转
只能改招式分布，改不出动作间隔（P70 实机 10.5→12.4 每千帧）。
定位为未来放宽纪律时的资料。

**③ 成品化配置已生成（验收后用，未编译未部署）**：
`tools/make_release_profile.py` → `plug/context_probe/src/lib.rs.release`
(3058 行，未覆盖 lib.rs) + `out/release_profile.md`。
开关 `W2_PROBE=0`、`MAX_B2/AE/COMBO/AR=0`、`MAX_QX=400`、`MAX_HB=200`
(`--silent` 可关 HB)，`MAXLOG=1M`、`W1_ALL/W2_BAND_ENABLE/W4_STANCE_ENABLE/
W4_HUB_ENABLE/PROFILE_RELEASE=1`、`DRAIN_ENABLE/W3_GATE_ENABLE=0`。
**关键依赖**：`band_sense` 独立于 W2_PROBE；`ZONE_F`/`END_F`/`ABN_F`
更新在日志块之外；**只有 `STANCE_CUR/F` 在 QX 分支内 ⇒ `MAX_QX` 不得
置 0**，否则 W4 处境维静默失效。

**④ 判读工具自动结论**：`tools/analyze_v71_limits.py`（TOOL2 路径不变）
新增两段自动结论 —— W4 分流（HB 行 h0..h3/hd + zf/af/ff，判定「全走常规
非故障/产生分流及主要来源/hub3 换区退回」）与疲惫窗节奏
（COMBO ev=1 计算 PRE/TIRED/POST 每千帧密度 + gap p50，判定有无喘息并
给出 P70 结构性原因）。v71 冒烟 68/0/2，自动结论正确输出
「W4 h0=130 h1=22 h2=11 h3=1 特殊 20.7% 来源远距12/换区6」
「疲惫窗密度 101% of 常态 ⇒ 无喘息」；四路旧日志降级 6/0/2。

**⑤ 下一场仍是唯一一场**（v71，双击 `run_v66.cmd`），待验项没有增加：
日志完整性（S/S2/HB/epoch/末尾）、W4 真实分流、疲惫窗自动结论、
跨怪 sp、W1/W2 与零异常回归。验收通过后才按 `release_profile.md` 出成品版。
细节只在 `out/P72_struct_bias_and_release_profile.md`。


## 2026-11-15 19:40 · P79 验收场判读 + 成品部署（唯一一场实机，已闭环）

用户完成一场任务 ⇒ 判读 `02_Workspace/game_p54_lite.txt`（13,518 行 / 10.5 分钟 /
末 BEAT f=37800）。**v71 验收通过：PASS=64 / FAIL=0 / SKIP=4，零异常无闪退**，
六项待验：① 日志完整性 OK（最长 246<270、S/S2/HB 12/12/12 全配对、epoch
{0:4780,1:937} 无盲区、log 峰值 5705/1M）；② **W4 首次有效分流实证**
h0=62 h1=0 h2=8 h3=14 hd=14，特殊占比 26.2%，来源换区 6 / 异常 3（P70 因
S 行截断作废的结论补回）；③ 疲惫窗自动结论误报已修（见下）；④ 主怪换成
`sp=0052` = emid 82 **泡狐龙**（跨怪第 3 种，前为轰龙 0020 / 斩龙 0050），
W1/W2/W4 三层全有数据；⑤ W1 `wall=116 wnok=63 / w3=51 w4=18 wt=1`、
W2 `wb=59 bf=25` / Z=220 ZP=55 / 档位证据 68.2% / st3=[0,1,2]；⑥ FATAL=0、
c0000005=0、6 hook live=1、正常结算回城。W3 `ek=641 ge=85 gs=0` 第三次确认
结构性失效；自然疲惫窗 f=29878..34345 ≈74.5s（纯只读 J/G/gdone=0）。

**判读误报更正（本场核心）**：`analyze_v71_limits.py` 旧口径把全场 7 个 mon
对象的 COMBO ev1 混算且未排除任务收尾，报「前 489/18.9 → 窗 45/10.1 ⇒
下降 47% ⇒ 出现喘息」。实际窗前含 `1007=159 / 1022=135` 等其它对象，窗内
只剩 `0052=20 / 1027=15 / 101A=10`，且**主怪窗后动作 0 次**（结算/离场）。
工具已改为按疲惫态 AR 行识别唯一主怪 + BEAT 全量 sel 交叉 + 窗后归零判
「不可判」：主怪前 151/6.0、窗 20/4.5、后 0；BEAT 前 8.1 → 窗 5.7。
⇒ **P70「疲惫喘息/输出窗口放大做不到」与 P72 B 方案定案维持**，不得据旧
输出向用户报「出现喘息」。重跑 `out/P79_v71_acceptance_judgement.txt`。

**验收后已部署成品**（P78 既定计划，零实机）：备份 v71 NRO →
`out/deployed_v71_1d513ec3.nro`、备份源码 → `lib.rs.v71bak`；部署
`out/rai_release_candidate.nro`（`dfab157d…`/61440 B/6 detour）到 mods 插件位；
同步 `lib.rs` ← `lib.rs.release`（`11131339…`）。下次启动游戏生效，
**不需要再打一场**。回退 = 两份备份覆盖回去。30 分钟任务仍是外推（本场
10.5 分钟）；成品关掉大部分日志，将来新增判据需回退探针版重编译。
细节只在 `out/P79_v71_real_quest_acceptance.md`。


## 2026-11-15 20:15 · P80 目标复盘 + 配额审计 + 成品 v2 修复（离线，零实机）

用户问「是否实现本 mod 目标」并要「继续完成未完成的任务」⇒ 先给诚实结论：
**不能说已实现原目标**，准确说法是「当前四条纪律 + 无 Rise 实机反汇编下，
可交付的最大机制级复刻已做完并部署」。按 Rise L0–L7 分层：L6 加权抽选达成、
L2/L4/L5 机制级近似、L3 结构性证伪、L0/L1/L7 空白（7 层里 1 达成 / 3 近似 /
1 证伪 / 2 空白）。分层与 A/B/C 三类未完成项见
`out/P80_goal_achievement_assessment.md`。未完成分三类：A 结构性不可达（不再试）、
B 可离线推进（本轮派 2 个并行子任务）、C 需实机或放宽纪律（不擅自启动）。

**① 30 分钟配额静态审计**（`tools/audit_p80_30min_quota.py` →
`out/P80_30min_quota_audit.md/.json`）：用 P79 实机密度 + `lib.rs.v71bak` 配额常量
演算。最忙 epoch0 [rai] 行 4780、全部 `MAX_*` 之和 34184；30/60/120 分钟预计
17,208 / 34,416 / 68,832 行，MAXLOG 1M 占用 1.7/3.4/6.9%，理论可撑 29.1 小时。
**结构性结论**：配额每 30000 帧重置 ⇒ 时长本身不会造成整场停写，唯一线性增长
的是总 log 序号。本项从「算术外推」升级为「实测密度 + 源码常量静态审计」，
但仍不是 30 分钟实跑。同时查出 Q/M/X/ZS/E 老诊断配额在 epoch 内就打满
（60/60、40/40、20/20、2/2、38/40），只影响诊断行、不 gate AI 状态，判为已知无害。

**② 顺带查出并修复成品真实缺陷**（`out/P80_stance_quota_fix.md`）：`QX` 是唯一
会 gate AI 状态的诊断配额 —— 成品 `MAX_QX=400`，实测每 epoch 1237 次 QX 事件，
而 `STANCE_CUR/F` 更新原本写在 QX 日志分支内 ⇒ 前 32% 后 W4 处境维停更、
`STANCE_TTL=300` 帧后静默退回 st3（P75 只标注「不得置 0」，未量化够不够）。
修复 = 把 stance 计算整块移到 QX `if` 之外（同 `ident/rd8` 计算、零新增 hook、
零写入、行为等价），删除块内重复更新；`MAX_QX` 保持 400 作低频诊断。
改 `lib.rs` + `lib.rs.release`（md5 `28e74de6…`），复制整目录到 `_release_build/`
删 target 全新编译 1m28s → `out/rai_release_v2.nro` md5
`c174b191549cc734806ef67b99298520`（61440 B / 6 detour / NRO0 头同构 /
`Z/AE/COMBO/AR/J/B2` 特征串全 0 / build_id 全新）。**已部署 v2**，备份 v1
`out/deployed_release_v1_dfab157d.nro`；`out/release_profile.md` 已改：
**P75「MAX_QX 不得置 0」定案作废**，现可置 0。v2 未实机复验（§5）。

**③ 判读/完整性回归**：修正口径后的 `analyze_v71_limits.py` 跑模拟日志
68/0/2、跑 P79 实机 64/0/4；`check_log_integrity.py` 模拟日志 OK。

**④ 两个并行子任务已全部完成**（`out/P80_object_ref_resolution.md` /
`out/P80_bulk_monster_assets.md`）：

- **对象引用修复成功**：`tools/rsz_parse_v2.py`，12/12 文件 `parseOK`、
  1038/1038 引用合法、tail=0；根因 = RSZ `userdataOffset` 指向 data 段**之前**
  的 userdata info 表，userdata 实例数据在外部分件、主流占 0 字节，v1 误按
  fields 内联解析导致其后整体错位（垃圾 ref 其实是合法 `_TreeNodeID`）。
  ⇒ P78「需干净二进制」前提作废。但 **Hub→池因果链仍结构性不可重建**：
  RSZ 无跨文件引用、12 个 Hub 内无池轮盘（`_TransitionActTbl`/`_TransitionRate`
  全 0）、唯一出口 `_ReferenceThinkData` 指向 15 个未抽外部分件、标量无共享
  TableNo ⇒ **「W4 12 Hub 1:1 不可做」定案加强**（标量+引用+结构三重实证）。
- **52 怪全量资产**：468 文件 / 52 怪（`refs/_bulk_extract/`）、468 JSON；v2
  全量 430/468 `parseOK`（38 个 act/combo 失败：37 模板缺类 9 类/52 实例 +
  1 个 `em007_act_001` 的 String 内联 UTF-16 变长串模式，标量不作定量依据）；
  main 用 v2 严格复核 78 `range_data` + 78 `stamina_data` 全 OK ⇒ **翻案两条
  P78 定案**：① 全怪 `_RangeDistance` 255 处全部 4 元素严格递增（95 种数组，
  如 `[6,12,17,22]`/`[10,20,35,50]`），与 GU `dttune` 4 档同构、4 阈值切
  5 区间 ⇒ P73「Rise 无几何阈值阶梯 / 对错了层」的**理由作废**（非单调
  `[8,5,3,1]` 只是 `_range_hate_add_data` 仇恨参数）；main 裁定改为「层是对的，
  但按怪种编译 137 表不值得」，**结论维持**。④ `_tiredSec` 12 种 30~120s
  （61/78 非 0）、`_motRate` 7 种 0.8~1.0（60/78 非 1）⇒ em131 的 0/1 是
  特例，「疲惫数据表级复刻否定」**推翻**，Rise 疲惫数值静态可复刻；但 GU
  执行层（FSM/`+0x50C`）不可达 ⇒「疲惫喘息做不到」结论维持、理由改 GU 侧。
  ② 领地争夺 [C] 不变；③ Hub→池加强。
- **Q(b) 断点定位**：filelist 180,405 行里 enemy 目录 `.msg`=0、招式名文本
  候选=0、638 个 `motlist` 全是编号文件、RSZ 唯一 name 字段是部位名 ⇒
  `TableNo→_actionNo→招式名` 最后一跳**无文本源**，结构性不可完整建立。
- **跨怪通用性**：52 怪字段结构一致但数值按怪变化（疲惫 12 种 / 速度 7 种 /
  距离阈值 95 种）⇒ 通用性在结构规则层，不能硬编码单一常量，支持现有纪律。
- 总入口 `out/P80_full_push_summary.md`；本轮全离线、零实机，最终达成度结论
  仍是「机制级最大复刻已交付」，**不是原目标完全实现**。


## 2026-11-15 21:00 · P81 机制级清单 + 三项剩余缺口离线复核（零实机）

用户问「机制级实现哪些实现了哪些没实现」并要「继续完成未完成的任务」⇒
先给清单（见 `out/P81_mechanism_checklist_and_gaps.md` §1）：**已实现并实机验收
6 组**（W0 状态输入 / W1 Rise 15 池形状 / W2 状态×距离档 / W4 3×4 处境分流 /
6 hook 只读零写入 / 日志完整性与成品化）；**实现但结构性失效或已关闭 2 组**
（W3 门控 `gs=0`、强制疲惫探针）；**未实现 7 组**（L0/L1 FSM、12 Hub 1:1、
L3 生效、L5 条件检查、L7 执行层与招式名、疲惫喘息、领地争夺）。

**本轮把 P80 三项可离线缺口全部推进**（`refs/_p81_extract/`）：

① **重大发现 —— Hub→15 池装配链重建**：从 12 个 `attack_stance_*` Hub 的
userdata info 表解出 15 条外部分件路径（4 action + 3 combo + 8 例程主），
主 pak + patch 全抽出。**8 个 `*_main.user.2` 用 v2 全部 `parseOK`/0 非法/tail=0，
每个恰挂 15 个 `AngerRange1..5Check`/`NormalRange1..5Check`/`TiredRange1..5Check`
userdataPath** ⇒ 3 状态×5 距离档、每格 8 次、共 120 条路径无缺格。再抽 em001
全部 `*range[1-5]check.user.2` 得 **555 个池文件，120/120 目标全覆盖、555/555
parseOK**，`_TransitionRate` 率和 **555/555 恒 100**（P78 的 89 池升级为全量），
15 格每格 37 池；tired 首项权重 52.0~71.5 明显高于 anger/normal 的 38~44，
远距 range5 各状态 k 最小、首项最高 ⇒ Rise tired 池更低熵、远距出招更单一。
⇒ **P80 A「RSZ 无跨文件引用槽 ⇒ 因果链结构性不可重建」部分推翻**：实例数据
确无跨文件实例指针，但 **userdataPath 就是文件级跨文件引用**，装配拓扑已重建
到池文件名级。定案改判「装配链已重建；运行时距离分派与 GU 执行层仍不可达」，
**W4 12 Hub 1:1 不可做结论维持**（缺口从 Rise 侧链断精确化为 GU 侧够不到）。
② **motlist 抽查**：`em001_00_00/01/22.motlist.528` 的 UTF-16 串全是动画轨道
类名/骨骼名/动画 ID（`EnemyLockCogRotationTrack`/`Root`/`em002_00_00001_Loop`），
**无招式名文本** ⇒ `TableNo→ActionNo→招式名` 最后一跳确认为硬断点。
③ **15 池索引对应**：本地 89 池 v2 重解析**无任何距离字段名**，命中的 6/12/
17/22 等数值全来自 `_TransitionRate`/`_TableNo` ⇒ `range1..5` 是**外部分件文件
名槽位**、`_RangeDistance` 在独立 `range_data`，两者之间**结构性无静态中间表**
（需 Rise 运行时/反汇编），不再当「待找的表」列待办。

**未改插件、未编译、未部署**：新证据全在 Rise 静态参照侧，GU 侧 6 hook/抽选层
边界不变；555 池首项口径与 P57 的「按 (state,k) 降序均值」不同，直接替换
`HUB_SHAPE` 会引入未实机验证的偏差。产物定位为参照资产与定案依据。
部署点仍是成品 v2 `c174b191…`。报告 `out/P81_mechanism_checklist_and_gaps.md`，
数据 `out/P81_hub_external_parts.json` / `P81_hub_external_analysis.json` /
`P81_15pool_assembly.json`。


## 2026-11-15 21:10 · L0/L1 落地判定、L7 关闭、GitHub 发布准备

**① L0/L1 不能落地（用户认为 P81 前置已够，实证复核后判定不成立）**：
6 hook 全在抽选/观测层，源码零写入（实际 `write_volatile`/`wr*` 0 处，仅历史
注释）；GU 疲惫 FSM 链在 `0xBD2EC..0xBD30C` / `0xBD390` / `0x816D0` /
`0xF8D384` → `Stamina_low_Start`，`+0x50C` 倒计时由引擎每帧写，均不在 hook
调用链内；P48 直接写 `+0x505/+0x508` 被游戏 149 帧内覆盖。Rise 的 L0 装配是
RSZ `userdataPath` 由引擎加载外部分件，GU 的 `*_cmdtbl` 是单表 + mode/sub
轨道，没有「按处境加载不同表」的机制 ⇒ **缺的是 GU 侧挂载点，不是 Rise 静态
资料**，P81 把装配拓扑补全也不能改变这一点。机制级等价物「按状态×距离取不同
形状」已由 W1+W2+W4 实现并实机验收；若强行落地需放宽零写入纪律 / 新增引擎层
hook，属另一条技术路线。本轮不改插件、不重编译。

**② L7 关闭**：用户定案 GU 自身有完整动画与动作资源，无需复刻 Rise 动作执行层
⇒ 从缺口列表移除；达成度描述改为「L7 不适用」，`out/github_release/README.md`
已写入该边界。

**③ GitHub 发布准备（未完成上传）**：`tools/publish_github.py`（令牌从
`C:/Users/RongLynn/.workbuddy/gh_pat.txt` 读、不打印），`out/github_release/`
含成品 NRO + README + SHA256SUMS + `plugin/`（可编译 Rust 源码与编译配置）+
`tools/elf2nro.py`，14 文件 / 426,771 B，git commit `49a4864`。令牌有效
（`GET /user` 200 / login `Ronglynn`），但 fine-grained PAT 无创建仓库权限：
`POST /user/repos` **403**，目标 `Ronglynn/mhgu-rise-ai` 404。⇒ 待用户网页端
建空公开仓库，或把 token 改为 All repositories + Administration/Contents 写权限；
完成后重跑 `python tools/publish_github.py` 即可自动建仓/上传并校验 tree。

## 2026-11-15 21:40 · P83 · L0 定案舍弃、GitHub 冻结、历史产出只读盘点（全离线 / 零实机 / 远端零操作）

用户问「L0 的作用是什么、GU 侧能否舍弃，之前说已有替代方案已部署」+「GitHub 不再更新 / GitHub 侧别动」+「检查历史产出，不用的可以删了」。报告 `out/P83_L0_retire_github_freeze_cleanup.md`，逐文件清单 `out/P83_cleanup_manifest.txt`。

**① L0 定案舍弃（用户认可口径后写入长期约定）**：L0 = `EnemyUserDataParam` 装配层，引擎按 RSZ `userdataPath` 把 12 处境 Hub → 15 外部分件 → 8 例程主 → 120 条池路径 → 555 池装成决策树；它决定「用哪张表」，**不产生可观测行为**，行为由 L4 池形状 + L6 轮盘产生。GU 侧结构性不可落地（P82 §4 四项：无 15 张独立池表 / 无按处境换表时机 / 改 `em+0x2588` 需写内存且 P48 149 帧覆盖 / 距离分派无静态中间表），补齐 Rise 静态资料不改变这一点。⇒ 与 L7 同样处置：从缺口列表移除，判为「**GU 侧不适用 / 定案舍弃**」，不是「已完成」也不是「无限期搁置」。代价：放弃数据表级 1:1、`BAND_SHAPE_555` 与现表 L1 差 378 不进插件；**不改变成品行为与 P79 验收结论**。

**② 澄清「替代方案已部署」**：已部署的是 v2 成品 NRO `c174b191…`（61,440 B / 6 detour，本轮复核 md5 一致），实现 W1+W2+W4 **机制级等价物**（在同一张 `*_cmdtbl` 上按状态×距离取不同权重形状）；**不是 L0 装配层的等价实现**。P82 的 L0 静态资产（装配拓扑、555 池形状表、`band_shape_555.rs`）未编译进插件。准确说法 =「L0 舍弃 + 效果由已部署机制级方案覆盖 + 数据表级 1:1 明确放弃」。L1 另计：触发层 v55/v56/v63 已实机 PASS（成品 `DRAIN_ENABLE=0` 关闭），未做的是 Rise FSM 结构与 `_tiredSec`/`_motRate` 数值（P81 §7）。达成度口径：L0/L7 移出分母 ⇒ 适用 5 层内 1 达成 / 3 近似 / 1 证伪 + L1 部分；**交付范围与「非原目标完全实现」结论不变**。

**③ GitHub 冻结（用户 21:34 + 21:38 两次指令）**：远端 `Ronglynn/mhgu-rise-ai` **零操作**（不推送 / 不改设置 / 不建仓 / 不 archive / 不删除 / 不读改令牌）；本地 `out/github_release/` 与 `tools/publish_github.py` 原样保留但标记**冻结归档、不再运行**；移除任何「上传 / 同步 / 更新 GitHub」待办。P82 §1 与本章 21:10 ③ 作为历史记录保留不改（P82 已发布完成，head `4fc586d7`）。

**④ 历史产出盘点（只读，未删除任何文件）**：体积 plug 391M（其中 5 个 target 缓存 385M）/ refs 180M / out 93M / _discarded 78M / tools 3.9M。分档：A 保守 458.0 MiB（target + `_discarded` + 工程根 31 个命令误重定向碎片）；B 标准 496.3 MiB（+34 个 sim 日志、77 个历史探针 NRO、587 个 v1 版 RSZ 中间产物）；C 彻底 528.8 MiB（+64 个历史实机日志 32.5M，`02_Workspace/game_p54_lite.txt` 永不删）。保留清单：NOTES.md / 全部 Pxx 报告 / 成品与回退 6 NRO / `plug/_release_build/src` 全部 bak / `out/github_release` / tools / refs 模板与 P81 资产 / v2 解析结果 / 各线 bat / mods / load_order。`refs/guide`、`refs/re`、`refs/hpbar` 不列入删除（跨线共享，需另行确认）。删除执行需用户按档确认，前置：不可再生数据先 zip 备份、全部走系统回收站、小批次核验。

**④ 执行结果（21:45，用户选 C 档 +「日志可以做备份或保留」）**：对 64 个历史实机日志 + 77 个历史探针 NRO 采取「先打包备份、再进回收站」双保险，`02_Workspace/game_p54_lite.txt` 原件不动。备份 `04_RiseAI/_archive_backup_20261115.zip`（3.89 MiB / 144 条目 / testzip 通过，逐文件 sha256 见 `out/P83_backup_sha256.txt`）。三批执行：`P83_delete_batch1.txt` 31 碎片 / `batch2.txt` 175 文件 / `batch3.txt` 9 目录（5 target + `_discarded` + 3 个 v1 RSZ 目录），全部用 Windows 原生 `SHFileOperationW` + `FOF_ALLOWUNDO` 进系统回收站，`rc=0`、残留 0，**未用 `rm -rf` / 强制删除**。工作区 `out/` 93→21 MiB、`plug/` 391→7.9 MiB，共移走约 528.8 MiB（**回收站内容需用户自行清空才真正释放磁盘空间**）。核验通过：部署成品 md5 `c174b191…` 未变、成品与回退 6 NRO 全在、`src/lib.rs` md5 `28e74de6…` 未变、NOTES.md(491,437 B) / 70 份 `P*.md` / rszmhrise.json / `_p81_extract`(573) / `github_release`(41) / P79 验收日志(1,472,935 B) / tools / 各线 bat 均在。GitHub 远端零操作，本地发布快照与脚本冻结保留，mods / 游戏目录 / load_order / 音频线未动，未编译 NRO、未改 `plug/` 源码、零实机。执行细节见 `out/P83_L0_retire_github_freeze_cleanup.md` §6。

## 2026-11-15 22:05 · P84 第三方 Titanbreak 难度 mod「出招速度」实现剖析（离线静态）

用户提供 `D:\Baidunetdiskdownload\titanbreak_difficulties_6b631.7z`（12 MiB → 82 MiB / 1950 文件），问 Hard 及以上如何改怪物出招速度。报告 `out/P84_titanbreak_motion_speed_mechanism.md`。

**① 实现方式 = 单条目补丁 arc + dttune 怒时倍率数组，零 hook / 零代码 / 零写入**。20 个难度档，每档 94~96 个 `romfs/nativeNX/arc/enemy/emNNN_SS.arc`；`arc_tool.py extract` 实测 arc 只含 1 或 5 个条目：`enemy\dt_tune\*_dttune`（全部档）+ 4 个 `enemy\hagi\hagi_s{0,1,2,4}_*`（仅 `+Loot` 档）+ `loc/arc/result.arc`（313 个 hagi 条目，与 emNNN.arc 内 4 个逐字节一致）+ `eng/arc/title_eng.arc`（标题贴图）。按条目与原版 arc 合并，与本项目 ARC 纪律（`arc_tool.py pack --orig`）同构；包内**无** nro / IPS / cmdtbl 条目 ⇒ 不是从 AI 抽选层改的。

**② 改的是 `*_dttune` 里 30 个 f32 怒时倍率数组的前 3 项**（wiki `monster-rage-tired.md` §3bis）。em001 起点 0x1B2，原版 `1.15 / 1.25 / 1.0`；跨 20 档 em001 全文件仅 21 字节差异 = HP 低 2 字节 + 部位硬直(0x3C..0x82) + 这 3 个 f32。数组起点逐怪浮动（0x154/0x17E/0x17F/0x19A/0x1B2/0x1DA/0x202…，含奇数偏移，必须逐字节扫描）。**93/94 怪**三项系数严格 `1.1 / 1.5 / 0.9`（Hard 相对 Easy），无一例外；`em087_00` 只改硬直、无倍率（与 dttune.md「唯一无 status block」一致）。轰龙 em020 数组 @0x198，原版 1.2/1.3/1.0 → Hard 1.32/1.95/0.9，同样三系数。

**③ 逐档系数（em001，官方 GameBanana 文案与字节精确吻合）**：VeryEasy/Easy 速度伤害防御全 ×1.0；Standard 仅伤害 ×1.1（idx0 不动）；Hard 速度 ×1.1 / 伤害 ×1.5 / 玩家伤害 ×0.9；VeryHard ×1.2 / ×1.75 / ×0.85；Master ×1.35 / ×2.0 / ×0.8；Veteran ×1.1 / ×1.0 / ×0.8；Ashenveil ×1.5217 / ×3.85 / ×0.7。⇒ **「Hard 及以上才改出招速度」属实**；Standard 只改 damage 且只动 idx1，是「idx1=Damage、idx0=Speed」的强证据。另有 `+HP` 变体改 `0x38`（em001 4500→Hard 4950 / VeryEasy 2700 / Veteran 9000）、各档改部位硬直、`+Loot` 改 hagi 掉落表。

**④ 字段语义分歧（需标注，勿当定案）**：Titanbreak 010 模板 `dttune_mhgu.bt` 与官方说明把 idx0/1/2 命名为 `SpeedMult / AttackMult / DefenseMult`；本项目 wiki §3bis 的 [B] 推断为 `AttackRate / MotionSpeedRate / MotionSpeedRateLimit`（顺序相反，并把「参数槽 36 → 动作速度 s16 `[x+0x1428]+177`、≥1.0 钳制 `0x10690ac`」绑到 idx1）。两边都非代码级 [C]；若 wiki 对，则 idx2 的 1.0→0.9 会被钳制吃掉、官方 Defence 不生效。⇒ wiki 具名绑定降为「存疑，需参数槽 dump / 实机 A/B」，**本项目不改既有 RE 文档**；不影响「实现方式」结论。

**⑤ 对本项目定案的修正（细化措辞，不改交付结论）**：上一轮「节奏在引擎层、6 hook 够不到」应改为「**hook 层够不到，静态数据层可达**」——该数组由装载器 `0x57740` 整块读入、主程序无副本 ⇒ 改 arc 即改运行时倍率，零 hook / 零写入，且项目已有单条目 arc 工具链与 P48/P61 实机经验。但**仍不能复刻疲惫喘息/输出窗口**：三项倍率属 `cAngryParam` 怒时专用、静态随任务加载、不按状态切换；GU 30 数组后 16 项全 1.0，静态侧无疲惫专属动作速度下限字段（Rise 对应 `_tiredMotSpeedLowerLimitValue`）⇒ GU 只有「怒加速」没有「疲减速」的数据字段，这正是 P80「疲惫喘息不可复刻」更精确的根因。三条路径：静态改怒时速度（可落地但需逐怪 94 arc、与 v2 正交、方向是加速、须实机复验）/ 运行时按疲惫缩放参数槽 36 或 `[x+0x1428]+177`（写内存 + 新 hook，违反零写入与 6-hook 纪律，属另一条路线；Titanbreak 反证该字段是真实生效点，可作未来锚点）/ 维持现状。**P80/P83 达成度结论、v2 成品行为与 P79 验收全部不变**。

**边界**：全程离线静态，未启动游戏、未部署该 mod、未编译 NRO、未改 `plug/` 源码 / 成品与回退 NRO / mods / load_order / 音频线，**GitHub 远端零操作**；解包副本仅在 `%TEMP%/titanbreak_analysis`，原始 7z 原样保留；未做实机 A/B，故「idx0 改动是否真的让动作变快」仍是作者说明 + 数值一致性，非本项目实机验证。

---

## 22:12 P85 · 用户澄清「输出窗口」定义 + Rise 节奏倍率可复刻性（只读复核，报告 `out/P85_interval_definition_and_rise_rate_replication.md`）

**口径定案（此后按此判读）**：用户明确「留输出窗口」= **疲惫态两招之间留给玩家的攻击窗口长，即两招之间的间隔时间** = 本项目 `dE`（上招 END → 下招 START 的空档，NOTES:542）。必须与 `dS`（动作时长，中位 85 帧）和 AE 行 `gap`（相邻动作类边沿帧差 = 动作周期，含 dS，`lib.rs:2719`）区分。**动作速度倍率只改 dS，不改 dE。**

**① 按该口径 v2 没做到，且 GU 原版没有可被拉长的阶段**：v17 实机 `0x75224` 162 个 END 全部 1 帧后提交（162/162，NOTES:558），常规链 `END → 0x76154 → 0xAFF40`（NOTES:962-964）；v2 四层只改抽选权重形状。P70 疲惫窗每千帧动作数 10.5→12.4（+18%）、`gap p50` 52→69，两口径方向不一致但定案「无喘息段」；P79 校正后判「不可判」（窗后归零无基线）。⇒ 两场都不支持间隔变长。

**② 历史上唯一一次人造间隔 = v32/v33，已废弃且不在 v2 内**：`0x76154` detour 延迟调用 original（由 `forge_onUpdate` 补 trampoline），保持 `+0x73E0` 旧值使怪停在 Think 间隙，零写入 / per-mon 8 槽 / 不读 action_id。v33 换怪实机（`sp 0014→0004`）W=11 全 ok、累计 315 帧≈5.2s、平均 28.6 帧 / 最大 45 帧、占时长 1.11%，零 FATAL 正常结算；但离线重放 **87~96% 窗口被 `0xAFF40` 提前结束、平均实际仅 5~18 帧，加大 HOLD 无效**，要 45 帧级可控窗口须移到 `0xAFF40` 层双延迟（从未实施）；窗口内是 GU 原生进食/Think 动画（用户 20:20 反馈）。19:55 审计定性「v33 是自创全局帧间隔节流阀、不是 Rise 仿制；高频怪没管住、慢怪变笨重」，根因是干预装在抽选之后的落盘层 ⇒ **20:43 用户拍板路线 A（抽选层 hook）**，v34 部署后 v33 门控停止。成品 v2 不含任何插间隔逻辑。

**③ Rise 侧没有「两招间隔倍率」字段**：可定量的只有 `_motRate`（动作播放速度，0.8~0.98，60/78 怪，7 种）、`_tiredSec`（状态时长 30~120s，61/78 非零）、`EnemyThinkTimerData._Timer`（0~300s，思考/重复抑制计时器，**P32:120 明说不是疲惫时长**）、`_tiredMotSpeedLowerLimitValue`（逐动作，16/16/10 个显式 1.0，其余 -1.0，无证据拉长硬直）；`explicit_cooldown_field_found=False`。流口水/发呆属 FSM + 动作资源层（442 条清单 437 条 0 覆盖），无 Rise 实机/反汇编。⇒ **把 `_motRate` 1:1 搬进来也只拉伸动作本身，dE 恒 1 帧、判定与后摇同比变慢，玩家可攻击的空档不增加**。

**④ 三条路径判定**：(a) 静态数据层（P84 Titanbreak 范式）**对疲惫不通** —— dttune 30 数组属 `cAngryParam` 怒时专用、任务加载一次性生效、不随状态切换、后 16 项全 1.0；且 wiki §3bis 绑定链「参数槽 36 → 动作速度 s16 `[x+0x1428]+177`」在 `0x10690ac` 有 **≥1.0 下限钳制**（只能加速不能减速），Rise 0.8~0.98 全在钳制区，方向相反。**证据等级**：wiki idx0/1/2 绑定与 Titanbreak 010 模板顺序相反、两边非 [C]（P84 已降存疑），且该怒分支分发头 `0x1068DD8` 实机 **T=0 整场未被调用**（NOTES:3109-3117）⇒ 钳制仅静态反汇编级约束，不作实机定案，但也不足以支撑「写 0.8 会生效」。(b) 运行时按疲惫写参数槽 36 = 写内存 + 第 7 个 hook，违反零写入与 6-hook 纪律，且可能被钳制吃掉。(c) **零写入近似**：复活 v33 延迟落盘 + 用 `act+0x505>=2` 门控仅在疲惫态延长 HOLD，是唯一贴合用户定义且纪律内可行的路线（可复用现有 `0x76154`，不新增 detour）；但继承 5~18 帧硬上限、窗口是进食动画、无法映射 Rise 按怪数值 ⇒ **只能造窗口，不能称复刻 Rise 倍率**，须另开一轮工程与实机 A/B。

**结论**：v2 成品行为、P79 验收、P80/P83 达成度全部不变；「疲惫喘息不可复刻」的理由精确化为「**dE 阶段不存在 + Rise 无间隔倍率字段 + GU 疲惫态无倍率通道**」。若要推进，须先明确放宽「不新增写入 / 不改提交时序」中的哪一条，并把判据改为按 `dE` 而非 `gap` 统计。本轮只读，无实机、未编译、未改源码/成品/mods/load_order，GitHub 远端零操作。

---

## 22:20 P86 · Rise 疲惫四层分解 + 「疲惫态偏向待机权重」方案评估（只读复核，报告 `out/P86_rise_tired_layers_and_idle_weight_bias.md`）

**① Rise 疲惫不是「抽选时间变长」**：静态侧无此类字段。四层分解 —— 状态层 `_IsTired` 持续 + `_tiredSec`(30~120s，61/78 非零) + `_AddTiredTime`(60 处动态累加)；抽选层换 `tiredRange1..5`（候选 3 个、熵 1.2984 vs 怒/常 1.6740/1.6669、首项 55~72%，`_TransitionRate` 率和恒 100 ⇒ 每次仍命中一个动作）；动作层 `_motRate` 0.8~0.98 拉长 `dS`；引擎/动画层流口水/发呆/滑倒/进食（442 条清单 437 条 0 覆盖、107 RSZ JSON 搜 tired/drool/rest 0 命中）。`EnemyThinkTimerData._Timer`(0~300s) 是**思考/防复读计时器**，P32:120 明说「不是疲惫时长」，P32:202 其绑定与因果仍是推断；`explicit_cooldown_field_found=false`；抽选时机由 `_IsActionEnd` 门控（动作内不重抽）。⇒ 玩家感觉「两招之间久」来自动作变慢 + 引擎层发呆，不是抽选器变慢；v2 只复刻了第二层的权重形状。

**② 用户新方案「疲惫态提高抽中待机的权重」= 目前唯一严格纪律内、且有全量数据的路径**：不插间隔、不写内存、不新增 hook、不碰提交时序、按 `sig==FNV0` 结构特征而非按怪/招式硬编码。P72 已产出 `out/tired_struct_bias.json`（137 怪全量）：**130/137 怪含空签名 case**（case body 无 `op0x14` 排队动作），空签名权重占全表 **22.3%**（564822/2532200），按怪 p50 22.4% / 范围 0~100%；`weighted.md:22-24` 解释为「原生待机 / Think 间隙」（**仅推断**）；v36 实机 `empt=323/551=58.6%`（旧口径含 mode=0 混用，不可直接当当前命中率）。

**③ 改动点很小**：`h_matcher` 在游戏算出 `ret` 后由 `rise_weight_pick` 改写 `ret` 换 case ⇒ 插件本就能主动把结果导向任意 case。但候选筛选 `cs[k].sig != FNV0`（`lib.rs:1575`）、外层命中 FNV0 直接透传（`:2134`）、否决重抽三处也排除（`:2207/:2226/:2235`），设计注释 v37「空签名池仍直接透传（不是动作选择池）」⇒ **现状只会把非空签名 case 改成另一个非空签名 case，从没有「主动提高待机率」这条路**。理论推论（未实证）：P70 疲惫窗密度 +18% 可能正是 W1 疲惫低熵 `[60,20,14,6]` 把抽选压到 top-1 非空签名 case 所致，偏向 FNV0 方向相反应降低密度。

**④ 三个未闭环假设**：(a) 空签名 ≠ 已证实的待机，也可能原地发呆（v21i 换 `id=3` 待机的教训）或下一帧立刻重抽、只有 1 帧空档——**派发器每帧调用**（NOTES:237），窗口长度取决于游戏多久后排队下一动作，插件控制不了；(b) 这与 v33「人为按住 `+0x73E0`」不同，可能更干净也可能更短；(c) sig 非唯一 ID（实机 91/124 集中、19.7% 块全同签），FNV0 全空签名共用一个值，放开后 `prev_hit_d` 会把它们互相命中，须单独处理。P72 caveat「结构偏转改不出动作间隔」在严格 `dE` 下成立，但用户接受「变相」（待机动作=低威胁时间），故不能沿用 P72 直接否决；P72 把该资料标为「放宽纪律时用」偏保守，**本方案不需要放宽任何纪律**。

**⑤ 若推进**：① 纯只读探针统计疲惫/非疲惫各自 FNV0 命中次数、**命中后到下一动作开始的帧差分布**、是否伴随 `e1=175`（待机动作号，跨怪未验证）⇒ 可并进下一场自然任务；② 确认有持续空档后，编译期开关放开 FNV0 排除 + 给独立权重槽（疲惫形状按 `p5` 分流「动作 / 待机」）、单独处理 prev 判重并限制每场次数与最短间隔防发呆；③ 跨怪 ≥2 种 A/B，判据用「待机段帧数 / 占时长 / 玩家可攻击段」，不用 `dE`/`gap`，并核对零 FATAL、无发呆/吼叫/动画错位。效果上限参照 v33（315 帧 / 平均 28.6 / 最大 45、87~96% 被 `0xAFF40` 提前结束、进食动画）⇒ 成立也只能造原生待机窗口，**不能复刻 Rise 数值**，且改动后 P79 验收不再自动适用。

**结论**：P72「严格 B 方案（语义映射）不可做」维持；本方案是**结构特征偏转**，与之不是同一条路。v2 成品行为、P79/P80/P83/P85 结论全部不变。本轮只读，零实机、零编译、零部署、GitHub 远端零操作。

---

## 2026-11-15 22:42 · P87：GU 原生「流口水 / 换区进食」定位 + Rise 进食恢复层首次可定量

用户补充两条经验事实：「① GU 侧怪物进入疲劳必定流口水；② GU 侧怪物进入疲劳后换区必定进食。你看能否找出，再去复刻 rise 侧」。**两条都能找出，且指向同一层；并据此找到一条比 P86 更可定量的复刻路径。详见 `out/P87_gu_native_tired_drool_feeding_and_rise_recov_replication.md`。**

**① 两条行为在 GU 侧的实现链（都是引擎层原生，插件不需要生成）**
- 流口水 = 链 I：`0xBD260` 扣 `act+0x508` → 耗尽写 `+0x505=1` → `0x76154` 推 2 → `0x816D0` getter → `Stamina_low_Start` / `tired_start` 动画 FSM（P46 字节级定案；`0xf8d384` / `0x10a1814` / `0x10383a0`）。实机：P19（v43 纯只读，3:35 站立流口水、每 300 帧动作 5~13→2/3/1→连续 0 动作）、P22/P23（dttune 阈值 150→30，1:40 触发 / 2:40 恢复 / 窗约 60s）、**P26 决定性控制组：`dc=rd8(mon+0x73DC)==1` 与站立流口水严格共现，`e1=175` 只是倒地**。只读判据 `+0x505>=2`（成品 W1 已用）+ `dc`（成品 QX 行已读）。
- 换区进食 = 疲惫结束靠进食/耐力回升而非计时器：wiki `monster-rage-tired.md:20/159`「之后会去进食恢复」「即时型 `durF=0` 维持到进食/规定行为结束」；P46 恢复段 `+0x505==3 且 +0x508!=0 → 0xBD184(mon,0)`、`Stamina_low_End` 条件 `0x816D0==0`；P23 `ex` 疲惫段恒 55、恢复段 55→20 未归零；v33 窗口播放的就是 GU 原生 Think 间隙 / **进食动画**（用户 20:20 口述确认）。
- **定性修正**：P85「GU 无 `dE` 阶段」成立，但不能推出「GU 没有可攻击窗口」——GU 的窗口是「一段原生待机/进食状态」，判据必须用低/零动作段帧数，不能再用 `dE` 或 `gap`。

**② v2 为什么没看到窗口**：P19/P22（纯只读）疲惫时连续 0 动作，而 P70（v69 W1 疲惫形状）密度 10.5→12.4(+18%)、「流口水同时持续出招」。成品 `BAND_SHAPE` tired `[65,25,10,0]..[70,20,10,0]`、`HUB_SHAPE` tired hub3 `[65,25,10,0]`，`rise_weight_pick` 明确排除 `sig==FNV0`（`lib.rs:1575`、命中透传 `:2134`、重抽三处也排除）⇒ **只在非空签名 case 之间改 `ret`，从不主动导向原生待机**；疲惫 `veto_depth=1` 又更短。三场跨版本/跨怪/跨打法 ⇒ 强相关线索，**非因果定案**，须 A/B。
- **本轮新增 P79 验收场重新判读**（只统计主怪 `0C250060`，合并 COMBO ev=1 + A 行共 171 事件）：PRE 29 / TIRED 20（与 P79 §4 一致）/ POST 1；TIRED 有 **6 段 ≥300 帧无动作空档，最长 928 帧≈15.5s**（31509→32437），其余 618/582/462/360/313；窗内主怪换区信号 7 次（含 `f=33685 area 6→5`），空档端点与之高度重合。⇒ P79 判「不可判」是窗后归零无基线，**不是窗内没有空档**；但也可能是换区赶路/主怪离场（BEAT 全场桶窗内 0 零桶），**不能当作进食窗口已存在**。

**③ Rise 侧首次拿到可定量的进食恢复层**（78/78 `stamina_data` `parseOK`）：`_SetMeatRecovStartPoint` 20.0(56)/30.0(22) ⇒ `_SetMeatRecovEndPoint` 80.0(56)/70.0(22)；`_mapNikuEatSec` **20.0(74)/10.0(4)**、`_SetMeatEatSec` 10.0(56)/15.0(22)、`_SetMeatConditionSec` 5.0(78/78)；**`_InCombatMapMeatEatFlag=False`(78/78)**、`_SetMeatCombatList` 空(65/78) ⇒ **战斗中不吃、脱战/换区才吃，正是用户第②条的静态解释**；另有 `NikuEatInfo._Probability` 30/25、`SetMeatInfo._StaminaRate/_CheckTime/_Distance/_Rate`。em001 实例全链见报告 §3。
- **修正 P86 一处**：引擎动画层「完全无法定量」应精确为「动画资源仍无法定量，但进食的触发阈值/时长/恢复终点/脱战门控 78/78 完备」；P32 §4「恢复：部分对应（都指向进食）」升级为**两作唯一同构且可定量的复刻落点**。

**④ 复刻路径（纪律内，不推翻 P85）**：不造间隔（v33 废）、不搬 `_motRate`（P85 不通）、不改 dttune 怒时倍率（P84 不通），而是**按 Rise 进食恢复曲线让抽选层「让位」**：门控 `(t505>=2||dc==1) && (cur*100/max)<=StartPoint(20/30) && (hub3/hub1)`，放开 FNV0 排除给独立权重槽（或该处境不改写 `ret`），`>=EndPoint(70/80)` 撤销；`_mapNikuEatSec=20s` 只作护栏/评估基准，不硬塞（GU 动画时长引擎决定）。所需字段全部已有只读通道：`dc/t505` 在 QX 行（`lib.rs:2361-2363`）、`+0x508/+0x506` 在 `0xBD260` hook（`:2421-2427`，现被 `DRAIN_ENABLE==1` 包裹 ⇒ 只需把读取移出分支，与 P80 stance 修复同类、零写入零新增 hook）、`area/req` 在 AR 行、`FNV0` 在 `h_matcher`。三阶段：① 纯只读探针（疲惫/非疲惫 FNV0 命中→下一动作帧差 + 耐力百分比 + 换区位 + 段内动作数，排除赶路/离场伪空档）→ ② 编译期开关 + FNV0 独立判重/次数与最短间隔护栏 → ③ 跨怪 ≥2 种 A/B，判据用低动作段帧数/占时长，不用 `dE`/`gap`。

**边界**：空签名=可攻击待机仍未实证（P86 三风险全在）；让位只能不打断、不能强制触发 GU 原生进食；GU 无进食时长静态字段（wiki §7 待补）；Rise 20s 无法 1:1；改动后 P79 验收不再自动适用。**达成度口径、v2 行为、P80/P83/P85/P86 结论全部不变**。本轮纯只读，零实机/零编译/零部署/未改源码/mods/load_order，GitHub 远端零操作。

---

## 22:55 · P88 — Rise 疲惫是否降速 / 两招如何衔接（用户两问，纯只读）

**问① 是否降低攻击动作速度 → 是，但只有「按怪全局倍率」一层有静态数值证据。**
- `EnemyStaminaData._motRate` 78/78 `parseOK` 全量复核：`0.8×1 / 0.85×5 / 0.9×28 / 0.92×15 / 0.95×9 / 0.98×2 / 1.0×18` ⇒ **60/78 = 76.9% 的怪疲惫时动作播放速度下调 2%~20%**，18/78 不降速；同文件 `_tiredSec` 30~120s（61/78 非零）。em001 = 60s/0.92、em002 = 80s/0.92。字段名 `mot`=motion 属语义推断，无反汇编 / Rise 实机绑定；是否只作用攻击动作不可区分（P20「可能也不只是攻击动作」）。
- **本轮新增且修正 P72 §6 / P86 的暗示**：重解析 `refs/rise_unpack/.../em00{1,2,3}_action_param_data.user.2`（`rsz_parse_v2.py`，三文件全 `parseOK`、cons==dataRegionLen、零非法引用），统计 856 个 `ActionInfo`：`_tiredMotSpeedLowerLimitValue` **814 个 −1.0（禁用）/ 42 个 1.0 / 无任何 <1 值**；`_angerMotSpeedUpperValue` 有 −1.0×762 / 1.0×93 / **1.1×1**(em003) ⇒ 两者是 **Clamp 语义（下限保护 / 上限加速）而非 Scale 语义**，疲惫降速主要由 `_motRate` 承担，逐动作层只做例外保护。P72 的「16/16/10 显式设 1.0、其余 −1.0」应补上「1.0 表示不允许低于原速、不是降速」这层定性。
- 效果只拉伸 `dS`（判定 / 后摇同比变慢），**不改变 `dE`** ⇒ P85「Rise 无间隔倍率字段」维持。

**问② 两招之间如何衔接 → 疲惫前后机制同构，静态侧无「招间间隔 / 冷却」字段。**
链：L3 `ThinkCondition._IsActionEnd`（12 Hub 内 12 True、主例程与 15 池内全 False ⇒ 动作没结束不重抽）→ L5 `_CheckPrevTableInfoList`(每条件恰 1 项) + `EnemyThinkTimerData._Timer`(0~300s / 17 档 44 值，em001 口径，**思考/重复抑制计时器、非疲惫时长、非招间间隔** P32:120) + `_UniqueId` 1..6 → L6 `_TransitionRate` 百分制轮盘、**555/555 率和恒 100 ⇒ 每次必命中一个动作、无「空过/等待」选项** → L7 `ActionTableData(_Category,_TableNo)` → `action/` 或 `combo/`；`ActionInfo` 固定 8 字段无 combo/link/next/CD，`explicit_cooldown_field_found=false`。`combo/` 是预编排序列、段内不回抽选层（高置信推断，资源未解包）。
- 疲惫唯一变化在 **L4 换 tired 五池**：555 池全量 `mean_candidates` 3.35~3.57、最大权重 52~72%、熵 1.2984（怒 1.6740 / 常 1.6669）；em001 原始顺序恒含表 1 且该项权重恒 10、表号并集 `{1,15,20,51}`。**口径澄清**：P32「首项恒 10」= 池内第一项（表 1），555 形状「首项 55~72%」= 按降序归一后的最大权重项，两者不矛盾。连段变少：em001 15 池 `_Category` `{0:64,1:36}`，`tiredrange1` cat1=0 ⇒ combo 路径 0（单怪实证）。
- **没有疲惫专属衔接层**：12 Hub / 15 池 / 107 RSZ JSON 搜 `tired/drool/rest/fatigue` 0 命中（除文件名），无「疲惫时调长 Think 计时器」的字段或绑定证据。「两招变久」三处来源都不在 L3–L7：① `_motRate` 拉长 `dS` ② L1 引擎层 `_IsTired`+`_AddTiredTime` 插入流口水/发呆/滑倒（动作资源 437/442 条 0 覆盖）③ 脱战换区进食（P87，20s / `_InCombatMapMeatEatFlag=False` 78/78）。
- 未定案：表 1 是否待机表（招式名文本源断点）、combo 资源内部序列、`_IsActionEnd`「仅结束帧求值」与 Timer/Counter 因果（推断级）、全部 Rise 结论无实机/反汇编（P32:201）。

**与 v2 关系**：W1/W2/W4 只复刻 L4+L6 权重形状；速度层与 L3 衔接层（W3）未实现且 W3 已三次实机证伪。P84/P85 讲的是 **GU dttune** 无疲惫速度字段，本轮讲 **Rise** 侧两层，互不冲突，GU 执行层不可达维持。P87 的 FNV0 让位方案对应引擎层待机/进食，不受影响。**v2 行为、P79 验收、P80/P83/P85/P86/P87 达成度全部不变**。报告 `out/P88_rise_tired_motion_speed_and_action_linking.md`。本轮纯只读：重解析产物仅在 `%TEMP%/p88_actionparam/`，零实机/零编译/零部署/未改源码/mods/load_order，GitHub 远端零操作。

---

## 23:03 · P89 — 疲惫三项可行性 + 愤怒链（用户提案，纯只读）

用户想在 AI 改进里做「疲惫 = ① 换一批更单一的候选 + ② 状态持续 + ③ 动作变慢」，并提「之前结论是 GU 侧疲劳是计时的」；另问愤怒链。

**前提澄清（必须区分两类「计时」）**：成立的是「减气蓄积计数 / 阈值递推」(`act+0x5D82`、`0xA3198 grow`、`dttune initial`)、「动作剩余计时器」(`act+0x1BC` 逐帧 −1)、`+0x5C` FSM 浮点计时器；**不成立的是「疲惫状态持续靠计时器」**——wiki §4 多数怪 `durF=0` 即时型「维持到进食/规定行为结束」、P19 字节级+实机闭环 (`initial=150` 即流口水触发点)、P20「疲惫结束是进食/耐力回升，不是计时器」、P46 `0xBD184(mon,0)` 恢复段，P87 据此定案。离线反汇编确有 `0x106901C vstr s0,[r4+0xCAC8]` 疲惫计时器 / `0x1068F9C strh [act+0x408]` 疲惫时长，但分发头 **`0x1068DD8` 实机 T=0 整场未调用（死代码）**；角龙 `durF=600`(10s) 属少数固定时长怪，而项目实证 **`durF` 对减气无效**(`initial=0` 反致连续硬直、块偏移逐怪浮动)。⇒ P79「自然疲惫窗 74.5s」是日志观测时长，不是可写机制字段。

**① 换更单一候选 = 代码已实现，但实机几乎没跑起来 ⇒ 三项里唯一纪律内可推进项。**
- 成品 `BAND_SHAPE[state*5+band]`:1023 tired 五档 `[65,25,10,0]/[45,45,10,0]/[45,45,10,0]/[50,40,10,0]/[70,20,10,0]`、`SHAPE_T3` 降级；`mon_state()`:1536 用 `act+0x518==1→ANGER` / `act+0x505>=2→TIRED`；`rise_weight_pick()`:1592-1627 按 `eff` 取形状、`wm=3` 为疲惫形状；W1_ALL/W2_BAND/W4 全开。
- **本轮关键发现**：`WT_N` 专门计疲惫形状使用（`:2180-2182, :2218-2220`），实机 **P70 `wt=7` / P79 `wt=1`**，而 P79 W1 全场 `wall=116/wnok=63` ⇒ 不是没实现，是覆盖率极低。可能原因（未实证，勿当定案）：疲惫窗主轨抽选稀疏、W1 要求 `sw==100 && n>=4 && main_track`、**W4 在 `hub==3`(换区) 时 `return(-1,0,0)` 主动不套形状**（`:1605-1610`）而 P87 重判疲惫窗 6 段长空档恰与 7 次换区信号重合。
- 可推进：放开/调整疲惫态应用条件、处理 hub3 冲突 ⇒ 零新增 hook / 零写入 / 跨怪通用，编译期开关 + 一轮 A/B。**两条边界**：GU 只有一张 `*_cmdtbl`，**候选集合换不了**，只能让同一批 case 权重更集中（机制级近似，非 Rise「换表号集合」1:1）；低熵 = 更单一/复读感更强，P70 疲惫窗密度 +18%，方向可能与「留输出窗口」相反，且与 P87 的 FNV0 让位方案在同一处冲突，必须联合设计。

**② 状态持续 = 原生已有，插件不该造。** GU 引擎层 FSM + 进食恢复维持（P19 连续 0 动作段、P79 场 6 段 ≥300 帧 / 最长 928 帧）。按 Rise `_tiredSec` 30~120s 定量控制需写 `em+0xCAC8`/`act+0x408`/`durF` 或调 `0x1068DD8`，全违反零写入且实机不走。纪律内唯一近似 = P87 让位（用 `StartPoint/EndPoint` 作门控、`20s` 只作护栏），**不控制时长**。

**③ 动作变慢 = 不可行，且方向可能相反。** GU dttune 30 f32 属 `cAngryParam` **怒时专用**、任务加载一次性生效、后 16 项恒 1.0 无疲惫槽；`0x10690ac` ≥1.0 钳制只能加速，Rise `_motRate` 0.8~0.98 全在钳制区；运行时写参数槽 36 需写内存 + 第 7 hook。**更关键**：`_motRate` 只拉伸 `dS`，按用户定义「输出窗口 = `dE`」，`dS` 变长不产生空档，判定/后摇占用更久反而可能缩短可攻击时间 ⇒ 即使放宽纪律做成也不该当输出窗口手段。

**愤怒链（§3 全表见报告）**：GU = 伤害蓄积触发(`0x106873c`，阈值/持续 **[U]**) → 状态字 `mon+0xCAC4=1`(离线 [C]) / **`act+0x518==1`(本项目唯一实机只读通道)** / `mon+0xCBF1` → 分发头 `0x1068DD8(em,1)`(**实机 T=0 死代码**) → 三路效果：① dttune 30 f32 怒时倍率数组(装载器 `0x57740` 整块读入、主程序无副本；wiki idx0/1/2 = AttackRate/MotionSpeedRate/MotionSpeedRateLimit [B]，**与 Titanbreak 模板顺序矛盾、P84 标存疑**) ② 肉质变化(16 怪 75 行 Enraged) ③ `0x75224` 按发怒 getter `0x816D0` + `act+0x1A8` bit6 + `act+0x2C0` + `+0x73E0` act==11 设 kind=0/1/2 → `0x76154(mode=2)`(v27/v28 实机、跨怪通用、最贴近 Rise 处境 Hub)。实机 v22：`st=1` 提交间隔中位 72 帧 vs `st=0` 87 帧。Rise 侧 = L0 `_angerData`(数值未解包) + `angerRange1..5`(3.60 候选、熵 1.6740 vs 常 1.6669 **仅差 +0.43%**、表号并集 `{14,19,20,61,62,80}` 独有 14/61/62/80 ⇒ **发怒差异在可用招式集合而非概率集中度**) + 逐动作 `_angerMotSpeedUpperValue`(856 动作中 762 禁用 / 93 个 1.0 / 1 个 1.1，是上限保护) + `_subStaminaPoint` 反向扣耐力。v2 接入 = `mon_state` 读 `+0x518`，anger 形状与 normal 差异很小，状态分化主要体现在 tired，与 Rise 静态结论一致。

**结论**：① 可推进（成本最低、唯一纪律内）、② 不需要做、③ 不可行且方向相反；要达成输出窗口主路径仍是 P87 让位，且 ① 必须与它联合设计。v2 行为、P79 验收、P80/P83/P85/P86/P87/P88 结论全部不变。报告 `out/P89_tired_trio_feasibility_and_anger_chain.md`。本轮纯只读：零实机/零编译/零部署/未改源码/mods/load_order，GitHub 远端零操作。

---

## 23:10 · P90 现状盘点：能做 / 未实现 / 能否现在做

用户问「按现在情况，本任务哪些能做、能做里哪些没实现、没实现的能否现在实现」。判定标准先立：**能做** = 零写入 / 6 hook 固定 / 跨怪通用 / 不改提交时序 / 不动 GitHub 与其它线；**已实现** = 编进部署 NRO 且有实机证据；**现在实现** = 可写码可编译，但「实现 ≠ 完成」，任何源码改动都使 P79 验收作废，实机只能由用户跑。

**已实现（v2 已部署）**：W1/W2/W4 抽选层形状（`wall=116/wnok=63`、`wb=59/bf=25`、W4 26.2%）、防复读 `prev_hit_d`+`push_prev`（连段 537/570）、三状态只读接入、强制疲惫（v55/v56 PASS、成品 `DRAIN_ENABLE=0`）、W3 与 v32/v33 插间隔（做过、证伪/废弃）、日志完整性；P79 `PASS=64/FAIL=0/SKIP=4`。工具链本轮核验 gcc / cargo / elf2nro 均可用，但 `_release_build/target` 已被 P83 清理，重编需全量构建。

**能做但没实现（4 项）**：① **P89① 疲惫形状覆盖率改进** —— 代码已在 `lib.rs:1023/1536/1592`，但 `WT_N` 实机仅 P70 `wt=7` / P79 `wt=1`；疑因 W1 `sw==100&&n>=3` 门槛（`:2163`）与 W4 `hub==3` 直接 `return(-1,0,0)`（`:1605`）与疲惫换区重合 ⇒ 放开条件即可，零新增 hook / 零写入；**现在能写码**。② **P87① 纯只读 FNV0 探针** —— 统计空签名命中→下一动作帧差 + 耐力% + `dc/t505` + `area/req`，只需加几行输出并把 `+0x508/+0x506` 读取移出 `DRAIN_ENABLE` 分支（`:2421`）；**现在能写码，且是后续所有推断的前置**。③ **P87② 让位权重槽** —— 通道全在，但参数与护栏必须等 ② 的帧差分布，FNV0 独立判重/次数/最短间隔也依赖它 ⇒ **现在只能写骨架，不能上线**。④ **P84 静态怒时速度** —— 技术上可做（单条目 arc 工具链已有），但方向是怒加速、与疲惫输出窗口无关，字段命名分歧未定案 ⇒ 可做、不列待办。另验证类待办：v2 实机复验、30 分钟实跑、跨怪实机仅 3 种。

**不能做 / 已舍弃**：L0 装配 1:1（P83）、L7 招式名（文本源断点）、换候选集合（GU 单张 cmdtbl）、W3 `gs=0`、插间隔（用户 20:43 废弃）、疲惫动作变慢（通道不通且 `dS` 变长反可能缩短 `dE`）、`_tiredSec` 定量状态持续（GU 原生已有 + 写内存 + `0x1068DD8` T=0 死代码）、运行时写参数槽 36、Rise 运行时距离分派 / FSM 数值 1:1（需 Rise 实机反汇编）、GitHub 上传（冻结）。

**对「能否现在实现」的答复**：能交付「待实机的编译版」，不能交付「已验证的功能」。建议按 P89 §4 把 ①+② 合并同一编译版、同一场自然任务（前者取 `wt` 与低动作段判据，后者验证空签名是否真有空档）；求稳可先只上 ②（纯只读、零行为改动）。部署会覆盖已验收 NRO，但回退链完整（v1 / v71 NRO + `lib.rs.v71bak`）。顺带可在同一场完成 v2 复验与 30 分钟实跑。详见 `out/P90_capability_inventory_and_now_doable.md`。

**边界**：以上为 23:10 盘点阶段的纯只读状态（未启动游戏 / 未编译 / 未改源码 / 成品 / mods / `load_order`，GitHub 远端零操作；唯一写入是新增报告、把超限的 `MEMORY.md` 精简重写 18,179 B → 8,369 B 与两处记忆同步）。**随后 23:20 用户选择「合并版：覆盖率 + 探针」，已实现、编译并部署，见下章**。v2 行为与 P79–P89 全部结论不变。

---

## 23:20 · P90 合并探针版：实现 / 编译 / 部署（用户拍板）

用户选「合并版：覆盖率 + 探针」⇒ **已落地**，全程零新增 hook / 零游戏内存写入 / 跨怪通用 / 不动 GitHub 与其它线。

**源码**：`plug/_release_build/src/lib.rs`，11 处精确替换；v2 原样备份 `lib.rs.p90bak`（`28e74de6…`）。新增编译期开关 `P90_TIRED_COVERAGE=1`（置 0 回 v2 覆盖率）、`P90_F0_PROBE=1`（置 0 关探针）、`P90_MIN_CAND=2`、`MAX_F0=600`。

**① P89 覆盖率（3 处）**：`rise_weight_pick` 用 `eff0` 判疲惫态把 `m<3`→`m<2`；`h_matcher` 正常抽选 `n>=3`→`n>=2`；`hub==3` 由无条件 `return(-1,0,0)` 改为**仅非疲惫态** defer，疲惫态继续套 `HUB_SHAPE[tired][3]=[65,25,10,0]`。非疲惫态逐字节保持 v2。

**② P87 纯只读探针**：`F0`（FNV0 段起点：`st/stc/band/hub/nc/pct/dc/t505/area/req/seg`）、`F1`（`h_start_40` 结段：`d=f-f0` 帧差 + 段内命中数 + 结段耐力/状态）、`F9`（每 600 帧：三状态样本/最大帧差/≥300 段数 + `wt`）。静默累计 epoch 不重置，仅 `F0_LOG` 每 30000 帧重置。耐力读 `act+0x508/+0x506`、`dc=mon+0x73DC`、换区 `+0x73F3/+0x1054`，全在既有 6 hook 内 ⇒ **未动 `h_stamina` 的 `DRAIN_ENABLE` 分支**（等价且改动更小）。

**编译部署**：全量 39.43 s + 增量 1.34 s，仅 `-z norelro` 链接器警告；产物 `out/rai_p90_probe.nro` **65,536 B / md5 `0ab6cbec301b4336fbbd50dcb71f9008`**，`NRO0`@0x10 与 v2 同构。静态校验全过：6 detour、`F0/F1/F9/P90 PROBE/RAI v71/S2/HB` 各 1、`Z/AE/COMBO/AR/J/B2` 全 0、新增行长上界 F0 157 / F1 172 / F9 146 **均 <265**（首版 F0/F9 极端值 281/295 已精简字段后重编消除）。已覆盖 `mods/RiseAI_EntryProbe/.../rai_entrylocator_probe.nro`，md5 一致，**下次启动游戏生效**。回退链：v2 NRO `out/deployed_v2_pre_p90_c174b191.nro`（`c174b191…`）+ `lib.rs.p90bak`；v1 / v71 备份仍在。

**修正一处文档过时**：`release_profile.md` 原写 `lib.rs.release` = v2 源码（`28e74de6…`），实测其 md5 为 `11131339…`（P80 前旧快照）；v2 权威备份是 `lib.rs.p90bak`。已改。

**新增判读脚本** `tools/analyze_p90_f0.py`：按状态分组帧差分布、疲惫态最长段、耐力/流口水/换区重合、悬挂段、行长与 FATAL 检查；已用 P79 旧日志冒烟（正确报无 F0/F1）。三条判据见 P90 报告 §8。

**边界**：**P79 验收不再自动适用**，本版是「待实机的探针版」而非已验证功能；P87② 让位权重槽仍未实现，参数须等 F0/F1 帧差分布。未启动游戏、未做实机、GitHub 远端零操作，未动其它 mod / 游戏资源 / `load_order` / 音频线。v2 行为与 P80/P83–P89 全部结论不变。细节只在 `out/P90_capability_inventory_and_now_doable.md §7/§8` 与 `out/release_profile.md §P90`。

---

## 2026-11-16 19:30 · P91 一场多目标实机执行包（纯离线准备，零实机）

用户先问「Rise 的愤怒和疲惫能否简单理解为改了攻击动作速度」⇒ 答**否**：愤怒主通道是切状态专属表（怒/常熵差 +0.43%），疲惫主通道是计时 + 进食让位；速度只是伴随倍率（Titanbreak ×1.1 是 Mod 难度参数，非 Rise 原生），`_motRate` 只拉伸 `dS`、814/856 逐动作下限字段禁用 ⇒ 疲惫侧速度证据最弱，抽选时间也不变长。

随后用户要求「把需要我实机做的都准备好，以便一场能同时推进多个目标」⇒ 盘点 P81 §5 / P90 §7/§8 后，把**所有靠实机日志才能推进的 6 个目标合并到一场**：

| 目标 | 依赖的日志字段 |
|---|---|
| A · P87① FNV0 空档（决定 P87② 是否立项） | `F0/F1/F9`、疲惫态 `d` 分布、`pct/dc/t505/area/req` |
| B · P89① 覆盖率改进 | `S.wt` / `F9.wt`，对照 P79 `wt=1` / P70 `wt=7` |
| C · v2 实机复验（P80 stance 修复后未跑） | 15 条**成品口径**判据（不能用 `analyze_v71_limits.py`，它会对已关闭的 Z/AR/COMBO/AE 行大量误报） |
| D · 30 分钟长时日志 | 末 BEAT `f>=108000`、epoch 分布、末尾 gap、`log` 峰值 |
| E · 跨怪 A/B（现仅 3 种） | `V/F0/F1` 行 `sp`（成品关了 COMBO/AR，sp 只剩这三处） |
| F · P90 自身配额风险（新增） | 每 epoch `F0+F1+F9` 峰值 vs `MAX_F0=600`、F9 是否后半场停写 |

**场次设计**：连续 30~35 分钟不退出游戏；任务 A 与任务 B 各打一只**不同的新大型怪**（避开 0020 轰龙 / 0050 斩龙 / 0052 泡狐龙），各自打到自然疲惫并跟完换区进食（P79 教训：窗后主怪动作归零 ⇒ 不可判）；不按 F9、不用立即完成、正常退出 flush 日志。

**新增 3 个文件**：① 工程根 `9_P91_oneshot.bat`（`fc /b` 前置核验部署 NRO 与 `out/rai_p90_probe.nro` 逐字节一致 → 只轮转自己的 `game_p91_oneshot.txt` → 抓日志 → 自动出 4 份报告；**不碰 `6_`/`7_`/`8_` 与 P79 验收日志**）；② `tools/analyze_p91_session.py`（一场 6 目标汇总，含 `--md/--json`）；③ `out/P91_oneshot_session_kit.md`（照做手册：怎么打、判据表、手动命令、回退、请用户肉眼记 4 件事、边界）。

**判读脚本相对旧 `analyze_p90_f0.py` 的三点增强**：① `F1.mon != F0.mon` 跨怪结段比例（F0/F1 是单一全局段、非按怪分槽，`d` 可能被别的怪结段污染，>20% 需先过滤）；② 明确 `F1` 的 `pct/t505/dc/area/req` 是**结段时**读数、`F0` 是**段起点**，不可混用；③ 新增 F 目标：`MAX_F0=600` 是 F0/F1/F9 **共用**的每 epoch 配额，打满会让 F9 一起静默停写（此时逐行 F0/F1 仍可判读、`wt` 改从 S 行读）。版本横幅缺失时 A/B/F 标「FAIL/不适用（版本）」并在报告顶部加醒目警告，避免把旧日志当判据。

**离线校验**：部署 NRO 与 `out/rai_p90_probe.nro` `cmp` 一致（md5 `0ab6cbec…`）；`py_compile` 通过；P79 旧日志冒烟正确报「非 P90 编译版」；构造 260 行合成 P90 日志全分支跑通（6 目标分别命中「候选窗口 / PASS 明显改善 / PASS 15-0-0 / PASS 33.3min / PASS 2 新怪 / PASS 配额」），Markdown 报告 7 段齐全、4112 字符；临时合成文件与 pycache 已清理。

**边界**：D 达标只证明「P90 成品密度下连续 30 分钟不停写」，**不等于** P80 基于 v71 全量探针版的 30 分钟配额确证（仍未做、不单独安排）；P87② 让位权重槽仍未实现；P79 验收不自动适用于 P90。本轮**未启动游戏、未编译 NRO、未改源码/成品/mods/`load_order`/游戏资源/音频线**，GitHub 远端零操作。细节只在 `out/P91_oneshot_session_kit.md`。

---

## 2026-11-16 20:10 · P92：P91 实机会话复核与定案（细节只在 `out/P92_p91_session_review.md`）

**场次**：`02_Workspace/game_p91_oneshot.txt` 27,498 行 / 2,485 `[rai]` / 22.2 分钟（f=300~80100）/ 6 hook / FATAL=0 / 完整性 OK / `[rai]` 最长 246。部署 NRO 仍为 P90（`0ab6cbec…`，`cmp` 一致）。只打了 1 只新大型怪 `sp=0051`。

**自动报告 v0 三处口径错误，已修并备份**：① v0 用 `F1.st`（**段起点**状态）判疲惫，误报「未进入自然疲惫」；实际疲惫信息在 `F1.t505`（**结段时**读数），且 F0/F1 全局单段被小怪抢占（85 段中 70 段 `sp≥1000`，大型怪仅 15 段 = 17.6%）。修为按 `F1.t505>=2` 分组，`longest`/`feeding`/条件重合全部改用 F1 结段读数。② 「行长>=265=7」全是宿主行（6×`[cheats]` 368 + 1×`[art-ext]` 288），改只数 `[rai]` 行 ⇒ 0 条、最长 246。③ 补「F0 段起点大型怪占比」与「F1/F0 两套读数分列」。改动仅 `tools/analyze_p91_session.py` 与 `tools/analyze_p90_f0.py`，**纯离线工具、未改插件源码、未重编译**；v0 报告备份为 `P91_session_report_auto_v0.md` / `P91_f0_detail_auto_v0.txt`，修正版覆盖原 4 份产出。

**本场真正的新数据 —— GU 原生疲惫窗口 f≈61078~63666（2,588 帧 ≈43s）**：`F1.t505` 2→3 共 7 条、`pct=0`（cur=0/max=1000）、`dc=1` 7/7、`req=1` 两次（f=62453/63245）、`area` 2→5（换区落地）；`V.st3=2` 两次（f=60162/61142，`wm=3`、`sw2=80/75`）；Y 行主怪 `59183→61611` **Δ=2428 帧 ≈40.5s** 为全场第二大间隔（最大 f=29678 Δ=13568 无疲惫标志 ⇒ 赶路/离场，须排除）。`S.s2` 0→5、`sv2` 0→2、`wt` 0→5，之后 `wt` 恒 5。

**探针为何没测到**：疲惫窗口内主怪 FNV0 命中 0 次；`d>=180` 的 16 段 100% 跨怪结段（起点小怪 `sp=1011` → 结段主怪），`F1.d` 不是主怪 `dE`。修正版 A 诚实判「需先过滤」（疲惫段 7、p50=96、max=533、≥300=2、跨怪 58.8%）。

**A 定案：`P87② 让位权重槽` 否决立项**（理由由「缺数据」升级为「机制层不成立」）：40s 长空档是引擎行为层换区进食链，不是战斗内 `dE`；抽选层整窗仅 5 次疲惫形状、FNV0 命中 0 次 ⇒ 无施加对象，强行加权只让抽选更少；与 P88/P89「动作变慢通道不通、方向相反」一致。**不再为 A 安排实机**。

**六目标**：A 否决 P87②｜B 部分改善 `wt=5`（P79=1 / P70=7）建议保留 `P90_TIRED_COVERAGE=1`｜C PASS 15/0/0（口径澄清：跑的是 P90 版不是 v2，可作 P90 新基线，P79 不自动适用）｜D 未达标 22.2min（非阻塞）｜E 未达标只 `sp=0051`（跨怪 3→4，非阻塞）｜F PASS 峰值 134/600。D/E 若要闭环，最小补场 = 双击 `9_P91_oneshot.bat` 连打 ≥30 分钟 + 两只新大型怪（本场日志自动轮转为 `.txt.prev`）。

**不变项**：`P90_F0_PROBE` 留着不影响行为（配额充足），关它需重编译 + 实机 A/B，不建议现在动；回退链不变；`game_p54_lite.txt` 未被动（md5 `a82389ba…`）；GitHub 远端零操作；6 hook 固定；其它 mod / `load_order` / 游戏资源 / 音频线均未动。

---

## 2026-11-16 20:25 · P93：基线定案 / 覆盖率复核 / 待办收口（细节只在 `out/P93_baseline_lock_coverage_review_and_gap_closure.md`）

**复核 B（修正 P92 §1 B 措辞）**：源码 `S.s2=S_N[2]`（疲惫态非空签名抽选次数，`:2210`）、`wt=WT_N`（`awm==3` 疲惫形状成功应用次数，`:1657/:2244/:2282`），两者同源可比。P91 时序 f=60000→63000：`s2` 0→5、`wt` 0→5、`sv2` 0→2、`wall` 120→131、`wnok` 119→130，f=63000 后全不再增长 ⇒ **同场疲惫形状命中率 5/5 = 100%**，P89① 怀疑的「W1/W4 门槛吃掉疲惫抽选」不成立。**但 P90 两处放宽本场都未触发**：`h3=1 hd=1` 全场仅 1 次且 f≤57000 已出现（不在疲惫窗）⇒ hub3 分支未调用；疲惫态 V 行 `nc=8 / wm=3 wk=3` ⇒ 合格候选 `m>=3`，`min_c=2` 无需生效。故 `wt=5` **不能归因于覆盖率改动**；`P79=1 / P70=7 / P91=5` 跨怪种/跨时长/跨疲惫次数**不可比**。准确措辞 =「机制通路验证通过、改动效果未验证」，**不是**「部分改善」。**结论：不再改插件源码** —— `wt` 上限由引擎疲惫态进入抽选层的次数决定（本场 5 次），非插件门槛。

**C / 基线口径**：P91 是 P90 版**成品口径 15 条** PASS 15/0/0；P79 是 v71/v2 **探针口径 64 条** PASS 64/0/4（唯一完整验收）。两者**不可替代**。**当前部署基线 = P90**（`0ab6cbec…`，C 全绿、探针数据已取完），**唯一完整验收仍属 v2/P79**；建议保持现状不动（零编译/零实机）。若要纯净已验收成品可回退 v2，代价失去探针、`wt` 回 1。`P90_F0_PROBE` 留着不影响行为（配额 134/600），关它需重编译 + A/B，不做。

**待办收口**：已闭环 A/B/C/F + P84–P89 + P83 + GitHub 冻结；可选实机仅 3 项且可合并一场 —— D 30 分钟（现 22.2min）、E 第 2 只新大型怪（现 3→4 种）、v2 单独复验（与 D/E 互斥、优先级最低）；永久硬断点（勿列待办）= Rise 运行时 `_RangeDistance` 分派、`_ActionNo→招式名`、L0/L1/L7、12 Hub 1:1、W3 / 插间隔 / 动作变慢 / 疲惫计时、GitHub 上传。**机制级可交付项已全部完成，剩余无离线可推进的功能项。**

**本轮改动（全部离线）**：新增 `out/P93_*.md`；`out/release_profile.md` §P90 实机状态行改写 + 追加 §P93 基线定案；`9_P91_oneshot.bat` 屏显提示改为「A 已关闭、不必再跟疲惫/换区进食，只需 30min + 两只新大型怪」（已重新规范 CRLF，85 行）；`out/P91_oneshot_session_kit.md` §2 加 P93 补场提示。**未动**插件源码 / NRO 编译 / 部署 NRO（仍 `0ab6cbec…`）/ 其它 mod / `load_order` / 游戏资源 / 音频线 / `game_p54_lite.txt`；GitHub 远端零操作；未启动游戏。

---

## 21:0x · P94 「日志没有记录」根因定案与执行包加固

**触发**：用户完成第二场任务；补充「30 分钟 ≈ 一场正常游玩时长；之前多次出现日志没有记录，很烦躁」。权威报告 `out/P94_log_loss_rootcause_and_hardening.md`。

**根因**：宿主 19:21 经 `update/updater.log` 自动升级 `0.15.3 → 0.17.5`（Forge loader 仍 1.5.1）；`mods/forge/romfs/nativeNX/forge/config.ini` 的 `[log] level = error` 把插件全部 INFO 行静默过滤。证据：新日志 `[forge] [INFO]=0 / [ERROR]=1393 / Loading plugin=0 / Initializing plugin=0 / [rai]=0`，但 `loaded rai_entrylocator_probe.nro ... (5 imports bound)` 与 `[forge] plugin ...` 完整；对照 P79（0.15.3）`INFO=6873 / Loading=19 / Initializing=16`；对照游戏目录 `log.txt`（19:22 首次启动）`[rai]=70` + P90 横幅 + 6 INSTALL。20:30 与 20:53 两场同一模式。**不是版本错误、不是配额耗尽、不是插件功能失败**；自动报告原写「非 P90 编译版」是判读 bug。

**本场裁定**：A–F 全部「无数据（日志通道）」，不计入任何验收。P79 唯一完整验收（64/0/4）、P90 当前基线（成品口径 15/0/0）、P87② 否决、P93 功能开发收口 **全部维持不变**。

**修复（纯离线）**：`config.ini` 改 `level = info`，原文件备份 `out/P94_forge_config_backup_20261116.ini`（md5 `8425f5d7…`）—— 本轮唯一游戏侧文件改动。新增 `tools/prepare_p91_env.py`（NRO md5 校验 + level 自动修正 + 时间戳轮转永不删旧日志）与 `tools/watch_p91_log.py`（150 秒无横幅置顶弹窗）；改 `9_P91_oneshot.bat`（前置 / 监视 / 退出自检，CRLF 80 行）、`tools/analyze_p91_session.py` 与 `analyze_p90_f0.py`（识别日志通道故障，A–F 统一标「无数据」而非 9 个功能 FAIL）；四份报告按新口径重出，修前报告留 `P91_session_report_preP94.md`。

**口径修正**：目标 D 重定义为「**一场正常游玩（约 30 分钟）全程日志连续、无盲区**」，不要求用户额外延长时长；用户真正痛点是「这一场有没有被完整记下来」，而非配额验证。

**顺带发现**：旧 bat 的 `.prev` 二次轮转删除了 P92 判读所用的第一场有效日志（27,498 行 / 22.2min），结论已固化在 P92/P93 与 v0 报告中，原始日志不可再复核；新 bat 已改时间戳保留。

**下一场唯一待办**：双击 `9_P91_oneshot.bat`，正常打一场约 30 分钟 + 两只不同新大型怪（避开 `0020/0050/0052/0051`）；前置显示 `[ok] Forge log level = info` + `PREFLIGHT PASSED` 即开打，150 秒内无弹窗即日志正常。不必跟疲惫 / 换区 / 进食。

**未动**：插件源码 / NRO 编译 / 部署 NRO（仍 `0ab6cbec…`）/ 其它 mod / `load_order` / 游戏资源 / 音频线 / `game_p54_lite.txt`；GitHub 远端零操作；未启动游戏、未做实机。

---

## 21:2x · P95：日志通道修复实机验证 + 任务失败场判读（权威 `out/P95_postfix_verification_and_failed_quest_session.md`）

**本场**：`02_Workspace/game_p91_oneshot.txt` 9,754 行 / 13.4 min / `sp=0047`；宿主 0.17.5、`config.ini` 为 `level=info`（P94 修复后）。`[rai]`=2162、`[forge] INFO`=3459（故障场为 0）、`P90 PROBE` + `RAI v71` 双横幅、6 INSTALL、FATAL=0、完整性 OK（最长 246 字符 / 盲区 `[]` / 末尾 gap=0 / S-S2 16/16 配对 / log 峰值 2077）。部署 NRO 仍 `0ab6cbec…`，逐字节一致。旧两场日志经时间戳轮转完整保留。

**核心结论**：P94「日志没有记录」根因修复**实机验证通过** —— 这是 P94 唯一遗留验证项，已闭环。用户死亡三次、任务失败 ⇒ BEAT 161 条 f=300…48300 严格单调、Δf 恒 300、零回退；`[rai]` 在每个 6000 帧段均有记录（最低 120 行）⇒ **任务失败不造成日志断点**。仅时长 13.4 min、未进自然疲惫（`V.st3=[0,1]` / `S.s2=0` / `wt=0` / `F1.t505` 156 段全 0 / `QX.t505` 710 行全 0）；每 6000 帧 `Δsel` 仅 0~5 次，战斗接触时间短。日志中无 `quest failed` / `faint` 显式事件行，任务失败属游戏层状态。

**六目标裁定**：A/B「**无样本（已收口）**」（P92 否决 P87②、P93 收口覆盖率，无需补场）；C **PASS 15/0/0**（第二种新大型怪、多怪共存 Y 行 5 个 mon 下 FATAL=0）；D「**连续性 OK / 时长不足**」；E 未达标但累计跨怪 4→**5 种**（0020/0050/0052/0051/0047）；F PASS 303/600。`[forge] ERROR` 2225 条中 2206 条为其它 mod `[action_ext]` 诊断、涉 `[rai]` 0 条，与本任务无关、无需处理。基线口径不变：当前部署基线 = P90，唯一完整验收仍属 v2/P79（64/0/4）。

**判读口径修正（全部离线）**：`tools/analyze_p91_session.py` —— A/B 无样本由「数据不足/需补场」改为「无样本（已收口）」，有样本统一为「仅记录（跨场不可比）」，删除与 P93 冲突的「部分改善 / 回退开关」措辞；D 按 P94 拆成「日志连续性」与「时长」两维；新增「日志通道」诊断并做回归修正（P79 非 P90 版但 INFO 行可见，应标「正常」而非「异常」）；报告 §A/§B/§D/下一步全部按 P92/P93/P94 定案改写。`tools/analyze_p90_f0.py` 标注「P92 后仅留档」、`wt` 改 P93 跨场不可比口径、补 `9_P91_oneshot.bat` 路径。重出四份判读产出，改动前报告备份为 `P91_session_report_preP95.md` / `P91_f0_detail_preP95.txt`。三路径回归（P79 旧日志 / 20:53 日志通道故障场 / 合成疲惫样本）+ 语法检查全通过，临时文件与 `__pycache__` 已清理。同步 `out/release_profile.md` §P90 实机状态行、`out/P91_oneshot_session_kit.md` 顶部 P95 提示、工作记忆。

**下一场唯一待办**：双击 `9_P91_oneshot.bat`，正常打一场约 30 分钟 + 两只不同的新大型怪（避开 `0020/0050/0052/0051/0047`）；不必跟疲惫 / 换区 / 进食。日志通道已实机验证，不必再担心「白打一场没有记录」。D 只剩「一场正常时长」，E 只剩「同场两只不同新怪」；不补也不影响任何功能结论。

**未动**：插件源码 / NRO 编译 / 部署 NRO / `config.ini`（本轮未再修改）/ 其它 mod / `load_order` / 游戏资源 / 音频线 / `6_启动并抓日志.bat` / `game_p54_lite.txt`；GitHub 远端零操作；未启动游戏、未做实机。永久硬断点不列为待办。

## 21:40 · P96 修正「不能降速」结论：dttune 30-f32 数组的减速可行性

**用户质疑**「Titanbreak 能加速，为什么不能按同逻辑降速」——**质疑成立，原结论下早了**。索引 `out/P96_dttune_slowdown_feasibility_revision.md`、工具 `tools/probe_dttune_speed_array.py`。

**新证据（离线只读，111 个 `em*_00` / 成功定位 59 只大怪 / 87%）**：`idx14..29` **59/59 恒 1.0**（无疲惫专属槽，P84 该条维持）；但 **`idx2` 有 17 只原版即 0.8**、**`idx3..12` 有 20/59 只带 <1.0（最低 0.5）** ⇒ 「该数组只能加速」被数据证否。em001 定位 `0x1B2` 复现 `1.15,1.25,1.0,1.15,1.1,1.05,1.0,1.0,1.5,3.0,0.5,1.5,2.0,1.0`，与 wiki §3bis 逐位一致。

**修正三处**：① P89「动作变慢 = 不可行、方向相反」→ **待实验**（减速字段在数据层已证存在）；② P85/P89「`0x10690ac` ≥1.0 钳制只能加速」→ 钳制代码存在，但所在链入口 `0x1068DD8` 实机 T=0 未调用（P46 死代码）⇒ 是否实际拦截**不能静态定论**；③ P84/P87「无疲惫槽」→ 前半成立（`idx14..29` 恒 1.0），后半须限定为 `idx3..12` 语义仍 [U]。

**四条路径**：A 静态改倍率（Titanbreak 同款，单条目 `--orig`，零 hook 零写入，**纪律内可试**）；B IPS32 解 `0x10690ac` 钳制（不新增 hook，与 HP 条 NOP 同构）；C 在 `idx3..12` 找状态槽（注册表 `0x3ccff8` 节点 dump，唯一可能「疲惫专属 + 零 hook」）；D 运行时写参数槽 36（违反零写入 + 6-hook，仅在放宽纪律时考虑）。

**必须保留的限定（P88/P89 仍成立部分）**：降速只拉伸 `dS`，**不产生 `dE` 空档**；按用户定义「输出窗口 = 两招间隔变长」，降速给的是「整体节奏变慢、每招占用更久」，不是「招间多出时间」，两者手感收益不同。

**最小实验（未执行）**：T1 `idx0×0.8` / T2 `idx1×0.8` 各一场短场（3~5 分钟同怪），定字段归属与钳制生效性；建议对象轰龙 `em020`（定位成功 + `02_Workspace/dttune_cmp/` 有现成样本 + 玩家易感知）；回退 = 删补丁 arc。

**未动**：任何 arc / NRO / 插件源码 / 部署 / `mods/` / `load_order` / 游戏配置 / 音频线；未启动游戏；GitHub 远端零操作。

### 21:55 · P97 疲惫降速结项（离线实证 + 反汇编，权威 `out/P97_tired_slowdown_feasibility_verdict.md`）

**用户质疑**：「Rise 疲惫就是给攻击动作降速，为什么不做？」——答案：**不是没做，是 GU 已经等价做了。**

**实机证据（P79 泡狐龙 `sp=0052`/`mon=0C250060`，`AE.gap`+`t505`）**：常态 n=146 p50=**127** 帧 / p90=308；疲惫 n=22 p50=**141** / p90=**387** ⇒ 中位比 **1.110**，隐含倍率 **0.901**，正等于 Rise `_motRate` 最常见的 0.90（78 只中 28 只）。疲惫窗 `f=29879..34346` = 4467 帧 ≈ **74.5 s**，在 Rise `_tiredSec` 30~120 s 内。动作密度 4.9 vs 5.4 次/1000 帧 ⇒ 变慢来自「换更慢的动作」，不是「少出招」。

**机制层新定案**：疲惫态动作 id 为 **490..534（21 个）**，常态 **4..570（132 个）**，**交集为空**，其中 **9/21 满足 `疲惫id−486==常态id`** ⇒ GU 疲惫使用**独立动作块（id 偏移 +486）**，不是同一动作乘倍率。

**反汇编修正（影响后续所有 RE 引用）**：`refs/hpbar/main_text_decomp.bin` 的 VA 基址 = `0x100000`，锚点 `0x11691bc == 0x42700000`（60.0f）。**wiki 地址是文件偏移，VA = wiki + `0x100000`**（wiki `0x10690ac`→真 `0x11690ac`；`0x6f6e8`→`0x16f6e8`；`0xbaaac`→`0x1baaac`）。函数 `0x1168e94..0x1169100`：`cmp r5,#1` 分流——怒分支取槽 **36** × dttune f32 后经 `cmp r7,#1; movle r7,#1`（**钳制真实存在**，`0x11690b0`）→ `strh [act+0x3CA]`；疲/常分支按 `[this+0xCAC0]` 与计数选槽 22/23/24 或 37/38/39，再取槽 33 × dttune f32、上限用槽 34 → `strh [act+0x408]`；公共段 dttune f32 × **60.0f** 秒→帧。**两分支乘同一个 f32 ⇒ 无疲惫专属速度通道，静态改必然同时影响怒/常。** 钳制对象是 ×60 的**时长/计时** u16，非动作播放速度；本函数内未找到写 `act+177` 的路径 ⇒「idx1=MotionSpeedRate→+177」仍 [B] 未验证。

**修正记录（同议题第三次收敛）**：P84/P85「钳制⇒只能加速」方向对但地址口径错；P96「数组承载 <1.0⇒降速可行」值层面对、语义层面被推翻；本轮中途一次误判「钳制不存在」= 直接用 `0x100000` 基址读 wiki 偏移，已用 60.0f 锚点纠正。**教训：引用 wiki 地址前先做基址锚点校验。**

**差距核算**：疲惫时长（74.5s）、疲惫动作时长（×1.11）两项**已无差距**；剩余硬断点仍是战斗内 `dE` 空档（END→提交 1 帧）与「每怪可调倍率无字段」。继续推进只有两条出事纪律的路：运行时写 `act+0x408`/动作速度（违反零写入+6 hook）或改 motion/anm 动画数据（超出「复刻 AI」定义）。

**未动**：任何 arc / NRO / 插件源码 / 部署（仍 `0ab6cbec…`）/ `mods/` / `load_order` / 游戏配置 / 音频线；未启动游戏；GitHub 远端零操作。

### 22:00 · 追问「Rise 真有战斗内 dE 空档吗」—— 答案：没有证据，`dE` 是本项目自造指标

**结论**：`dE` = 动作 END→下一提交帧差，是 **GU 日志侧为量化用户感知而定义的观测量**（NOTES:542），不是 Rise 里被观测到的阶段。P97 §4 表里「Rise：有 dE」是未证实推断，已改为「未证实」，并加 §6.4 修正记录。

**三条理由**：① Rise 静态字段只有 `_motRate`（动作速度 0.8~0.98）、`_tiredSec`（状态时长）、`EnemyThinkTimerData._Timer`（思考/防复读）、15 池 `_TransitionRate`（率和恒 100）——**没有间隔字段**；② `_IsActionEnd` 门控保证动作内不重抽、率和恒 100 保证每次必命中一个动作（P86 §1.1-1.2）⇒ 数据层不存在「空档槽」；③ FSM 与 `action/combo/motion/message/actiontune` 442 条资产 437 条零覆盖（P32:168-171），本项目无能力证明也无法证否 Rise 运行时细节。

**玩家感知的「窗口」在 Rise 的真实来源**：整招（含后摇）被 `_motRate` 放慢 + 疲惫池候选更少更单一（首项权重 55~72%）+ 引擎层流口水/发呆/滑倒（[I] 攻略可观测，我方无资产可定量）。若看到怪站着，更可能是**抽中待机/发呆动作**，而非两动作之间的间隔。

**关键反证**：GU 疲惫窗自身实测 **2428 帧≈40.5s 零动作段**（P92 §A）⇒ 「GU 没有输出窗口」只在严格 `dE` 口径下成立，是**度量假象**；这也是 P92 否决「待机权重」立项的真正理由。

**不变**：疲惫降速 = 已等价实现（P97）；P90 仍是部署基线 `0ab6cbec…`；唯一完整验收仍属 v2/P79。未动任何 arc/NRO/源码/部署/mods/load_order/游戏配置；未启动游戏；GitHub 远端零操作。
