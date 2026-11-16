# MHGU 项目长期约定（2026-11-15 23:10 精简重写 · 只做路由）
**细节一律查** `D:\MHGU mod maker\04_RiseAI\NOTES.md` 与 `04_RiseAI\out\Pxx_*.md`（76 份）。本文件只留路由、口径、结论。

## 现状
- **当前部署 = P90 合并探针版（23:20）**：插件位 = `out/rai_p90_probe.nro`，md5 `0ab6cbec…`（65,536 B / 6 detour）；源码 `plug/_release_build/src/lib.rs`（P90 版）。新增开关 `P90_TIRED_COVERAGE=1` / `P90_F0_PROBE=1` / `P90_MIN_CAND=2` / `MAX_F0=600`（前两者置 0 即编回 v2 行为 + 关探针）。**P92（11-16 20:10）已有一场 22.2min 实机、成品口径 PASS 15/0/0 ⇒ P90 可作新基线；v2 单独复验仍未做、P79 验收不自动适用**；判读 `tools/analyze_p90_f0.py` 与 `tools/analyze_p91_session.py`（均已按 P92 修正口径），细节 `out/P92_p91_session_review.md` / `out/P90_capability_inventory_and_now_doable.md §7/§8` / `out/release_profile.md §P90`。
- **v2 成品已回退为备份**：`out/rai_release_v2.nro` / `out/deployed_v2_pre_p90_c174b191.nro`，md5 `c174b191…`（61,440 B / 6 detour）；v2 源码 `plug/_release_build/src/lib.rs.p90bak`（`28e74de6…`）。回退 = 该 NRO 覆盖插件位 + `lib.rs.p90bak` 覆盖 `lib.rs` + 重启。**修正**：`lib.rs.release` md5 `11131339…` 是 P80 前旧快照、非 v2 源码。开关表 `out/release_profile.md`。
- **验收**：唯一场 `02_Workspace/game_p54_lite.txt`（10.5 min / 13,518 行 / 泡狐龙 `sp=0052`）`PASS=64/FAIL=0/SKIP=4`、FATAL=0；W4 分流 26.2%、W1 `wall=116/wnok=63`、W2 `wb=59/bf=25`、W3 `gs=0` 三度失效；自然疲惫窗 74.5s。`out/P79_v71_real_quest_acceptance.md`。**P80 修 stance 配额后重编译部署、未实机复验**。
- 回退链：v1 `out/deployed_release_v1_dfab157d.nro`、v71 `out/deployed_v71_1d513ec3.nro` + `lib.rs.v71bak`（覆盖+重启）。
- **达成度**：L6 达成、L2/L4/L5 机制级近似、L3 证伪、L1 部分、L0/L7 舍弃移出分母 ⇒ 适用 5 层内 1/3/1。准确说法「现有纪律 + 无 Rise 实机反汇编下可交付的最大机制级复刻已做完并部署」。`out/P80_goal_achievement_assessment.md`。
- **两作关系**：v2 = W1/W2/W4 在同一张 `*_cmdtbl` 上按状态×距离×处境改权重形状 + 防复读；**不是** L0 装配层等价物（P82 静态资产未编译进插件）。L0 舍弃、数据表级 1:1 放弃。
- **GitHub 冻结**：远端 `Ronglynn/mhgu-rise-ai` 零操作；本地 `out/github_release/`、`tools/publish_github.py` 保留但冻结不再运行；head `4fc586d7` 不变。不列上传/同步待办。
- **P83 清理已执行**：64 实机日志 + 77 探针 NRO 先备份 `04_RiseAI/_archive_backup_20261115.zip`（144 条目 / sha256 在 `out/P83_backup_sha256.txt`）再进回收站，三批 `rc=0` 残留 0，释放 528.8 MiB。**回收站需用户自行清空**。清单 `out/P83_cleanup_manifest.txt`；后续清理按「按档确认→备份→回收站→逐批核验」。

## 路径与工程
- 工程根 `D:\MHGU mod maker`（非会话 cwd）；游戏 `D:\Monster Hunter Generations Ultimate Recomp`；逆向库 `00_Tools\92_MHGU-master\MHGU-master\docs`。插件 `02_Workspace/plug/` → `03_Output/*.nro` → `mods/<Mod>/romfs/nativeNX/plugins/`。
- 每任务独立目录 + 唯一 NOTES.md，daily log 只写一行指向章节；04/05/06/07/08 各线隔离；mods 下只留 `RiseAI_EntryProbe`。**04 全部细节只在 `04_RiseAI/NOTES.md` 与 `out/Pxx_*.md`**。
- 编译命令见 `out/release_profile.md`（cargo → `bin/elf2nro.py`）；gcc / cargo / elf2nro 均可用；`_release_build/target` 已被 P83 清理，重编需全量构建。

## 全局纪律
- 回复简洁干练，直给结论/数据/下一步。
- 不动 `6_启动并抓日志.bat`（音频线）、游戏资源、`load_order` 既有行；各线脚本/日志互不覆盖。
- ARC：禁止整包重封共享大 arc；一律单条目 `arc_tool.py pack ... --orig`，打包前查冲突 + md5 校验。
- Hook：IPS32 解释器首字 `E28FFxxx` 不可 hook；静态 prologue ≠ 运行时首字；**6 hook 固定** `0x8E144/0x82F80/0x76154/0xAFF40/0xA30E4/0xBD260`，成品不新增。
- AI 改进必须跨怪通用：禁止按 action_id 硬编码，只走抽选层/权重结构性对标；不得绑定 `Show HP Bar`。判据看 BEAT 全量而非 A 采样；怪种看 V 行 `sp`。
- 日志：宿主单行 270 字符；v71 起 `MAXLOG=1M` + 每 30000 帧重置配额；`tools/check_log_integrity.py` 自检。成品关掉大部分日志，新增判据须回探针版重编译。

## 核心定案（详见对应报告）
- GU 决策层 = EMC `0x82F80`（表 `em+0x2588`），`op02` case 值 = 权重（`rand%100`，同构 Rise `_TransitionRate`）；`0x76154` 的 `r3==0` ≠ 提交。
- 疲惫链 I：`+0x508` 耐力 / `+0x505` 状态 / `+0x50C` 倒计时；`0xBD260` 每动作扣耐力、`0xBD184` 门控、`0x816D0` getter、`Stamina_low_Start`。**禁止直接写 `+0x505/+0x508`**（P48 覆盖）。发怒唯一实机只读 `act+0x518==1`；疲惫 `act+0x505>=2`。强制疲惫 = 改 `0xBD260` 入参 delta（v55/v56 PASS），成品 `DRAIN_ENABLE=0`。
- W1 15 池形状 / W2 `(st3,band)` / W4 3 状态×4 处境 12 槽；W3 `_IsActionEnd` 三次实机 `gs=0` 结构性失效，关闭。12 Hub 1:1 不可做。
- **P80**：78 怪 `_tiredSec` 30~120s、`_motRate` 0.8~1.0 静态可复刻，GU 执行层不可达；P81 对象引用修复后 555/555 池解析、率和恒 100。
- **P84 Titanbreak**：改 `dttune` 30 f32 怒时倍率（单条目补丁 arc）⇒「hook 层够不到、**静态数据层可达**」；但怒时专用、无疲槽、`0x10690ac` ≥1.0 钳制 ⇒ 疲惫窗口仍不可复刻。字段命名有分歧，勿当定案。
- **P85/86 输出窗口**：用户定义 = 疲惫两招间空档 `dE`（≠ `gap` 周期、≠ `dS` 时长）。v17 实机 END→提交恒 1 帧 ⇒ GU 无 `dE`；Rise 静态无间隔倍率字段。v32/v33 插间隔造窗口 PASS 但 87~96% 被 `0xAFF40` 提前结束，20:43 拍板废弃、v2 不含。**唯一纪律内路径 = 疲惫态提高待机权重**（结构特征 `sig==FNV0`，130/137 怪含空签名、权重 22.3%；成品 `rise_weight_pick` 现排除 `lib.rs:1575`）。须先纯只读探针验证 FNV0 空档。
- **P87**：GU 疲惫必定流口水 + 换区进食 = 引擎层原生链 I（`dc=mon+0x73DC==1` 站立流口水；`durF=0` 即时型维持到进食结束）⇒ 判据改「低/零动作段帧数」。P79 重判 6 段 ≥300 帧 / 最长 928 帧，但可能是赶路。Rise 78/78 `stamina_data` 进食参数完备（StartPoint 20/30→EndPoint 80/70、`_mapNikuEatSec` 20s、`_InCombatMapMeatEatFlag=False` 78/78）⇒ 两作唯一同构且可定量落点。**方案**：按 Rise 曲线让抽选层让位（放开 FNV0 + 独立权重槽 + StartPoint/EndPoint 门控），零新增 hook/零写入；P86 三风险全在，须先探针。
- **P88**：疲惫降速只有按怪 `_motRate` 有数值证据（60/78 为 0.8~0.98），只拉伸 `dS`；逐动作 `_tiredMotSpeedLowerLimitValue` 856 个动作 814 禁用/42 个 1.0 ⇒ Clamp 下限保护非降速倍率。衔接疲惫前后同构：L3 `_IsActionEnd` → L5 prev + Think Timer(防复读非间隔) → L6 轮盘 555/555 率和恒 100 必命中动作 → L7；无 cooldown 字段。
- **P89**：疲惫三项里 ①「换更单一候选」代码已实现但**实机几乎没生效**（P70 `wt=7` / P79 `wt=1`），疑因 W1 `sw==100&&n>=3` 门槛与 W4 `hub==3` 直接 `return(-1,0,0)`（`:1605`）与疲惫换区重合 ⇒ **唯一纪律内可推进项**；② 状态持续 GU 原生已有不需做；③ 动作变慢：**P97 结项为「GU 原生已等价实现」** —— 实机（P79 泡狐龙）疲惫换**独立动作块**（id **+486**，490..534 与常态 4..570 **零交集**），中位时长 141 vs 127 帧 = ×1.111 ⇒ 隐含倍率 **0.901**，正等于 Rise `_motRate` 最常见的 0.90；疲惫窗 74.5s 亦在 Rise 30~120s 内。反汇编（**wiki 地址=文件偏移，VA 需 +0x100000**，锚点 `0x11691bc`=60.0f）确认怒/疲两分支乘**同一个** dttune f32 ⇒ 无疲惫专属速度通道；`cmp r7,#1;movle r7,#1`（`0x11690ac`）真实但钳的是 ×60 的**时长/计时** u16，非播放速度。「GU 疲劳是计时的」仅对减气计数/动作计时器成立，状态持续不是计时器（`0x1068DD8` 实机 T=0 死代码）。愤怒链与 Rise 怒/常熵仅差 0.43% ⇒ 差异在招式集合非概率集中度。
- **Rise 资产**：pak `D:\Steam\steamapps\common\MonsterHunterRise\re_chunk_000.pak`；`rsz_parse_v2.py` + `refs/rszmhrise.json`；标量按 `diagnostics.parseOK` 过滤；`TableNo→招式名` 无文本源。怪种 `sp`：`0020` 轰龙 / `0050` 斩龙 / `0052` 泡狐龙。

## 已证伪 / 勿重试
`0x1068DD8/0x1069D8C/0x873C` 实机 T=0 死代码；写 `act+0x518=2`、写 `act+0x5D82`、改 dttune `initial=0`、`durF` 对减气均无效；`e1=175`/`ex=55` 是疲惫标志非倒地动作。

## 待办（权威 `out/P81_mechanism_checklist_and_gaps.md` §5 + `out/P90_*.md`）
30 分钟实跑（P91 22.2min / P95 13.4min 未达标，但 P95 日志连续性 OK）；v2 单独复验（P91/P95 跑的都是 P90 版）；跨怪 3→5（`0051`/`0047`），同场两只目标仍未达。**永久硬断点（勿列待办）**：Rise `_RangeDistance` 分派（需实机反汇编、P81 已定性无静态中间表）、`_ActionNo→招式名`（文本层 0 命中）、L0/L1/L7、12 Hub 1:1、W3 / 插间隔 / 动作变慢 / 疲惫计时、GitHub 上传。**P92（20:10，`out/P92_p91_session_review.md`）**：GU 原生疲惫窗 f≈61078~63666（`t505` 2→3 / `pct=0` / `dc=1` / `req=1` 换区 / 主怪零动作 2428 帧≈40.5s）⇒ **P87② 否决立项**（引擎行为层、抽选层无施加对象，不再为 A 跑实机）；C 成品口径 PASS 15/0/0 ⇒ P90 为当前部署基线；F PASS 134/600。两判读脚本已修正：疲惫分组用 `F1.t505>=2`（F1=结段、F0=段起点；全局单段 70/85 被小怪抢占，`d` 非主怪 `dE`）、行长只数 `[rai]`。**P93（20:25，`out/P93_*.md`）**：B 措辞修正 —— `s2=5/wt=5` 命中率 100%，但 `hub3` 全场仅 1 次且不在疲惫窗、合格候选 `m>=3` ⇒ **P90 两处放宽本场未触发**，`wt=5` 与 P79=1/P70=7 跨场不可比、不能归因于改动；**不再改插件源码**（`wt` 上限由引擎疲惫态抽选次数决定）。C 口径：P90=当前部署基线，**唯一完整验收仍属 v2/P79（64/0/4）**，与 15 条成品判据不可替代。功能开发收口；剩余 3 验证项可合并一场（30min + 两只新怪；v2 复验互斥且优先级最低）。**部署仍 P90** `0ab6cbec…`，`P90_F0_PROBE` 不建议关；回退见 `out/release_profile.md`。任何源码改动使 P79 验收作废。补场提示已更新（`9_P91_oneshot.bat`）：不必再跟疲惫/进食。**P94（21:0x，`out/P94_log_loss_rootcause_and_hardening.md`）**：20:30/20:53 两场 `[rai]=0` 根因 = Forge `mods/forge/romfs/nativeNX/forge/config.ini` `[log] level=error`（宿主 19:21 自动升 0.15.3→0.17.5），插件已加载、非版本/配额/功能失败；两场 A–F 全部无数据、**不计验收**，P79/P90/P92/P93 定案不变。已改 `level=info`（备份 `out/P94_forge_config_backup_20261116.ini`，唯一游戏侧改动）；新增 `tools/prepare_p91_env.py` / `tools/watch_p91_log.py`，改 `9_P91_oneshot.bat`（时间戳轮转不删旧日志、前置自动修 level、150s 无横幅置顶弹窗、退出自检）与两判读脚本（识别「日志通道故障」，不再误报非 P90 版或 9 个功能 FAIL）。**D 口径重定义 = 一场正常游玩约 30min 全程日志连续无盲区，不要求额外延长时长**（用户补充：一场游玩就约 30min，痛点是反复「没记录」）。旧 bat 二次轮转删了 P92 第一场原始 27,498 行日志（结论已固化在报告，不可再复核）。**P95（21:2x，`out/P95_*.md`）**：P94 修复后首场有效日志（`[rai]`=2162 / INFO 3459 / 双横幅 / 6hook / FATAL=0 / 完整性 OK）⇒ 日志通道修复**实机验证通过**。用户死亡三次任务失败，但 BEAT f=300..48300 严格单调、每 300 帧、零盲区 ⇒ 失败不造成日志断点；仅 13.4min 且无自然疲惫（`V.st3=[0,1]`/`s2=0`/`wt=0`/`F1.t505` 全 0）⇒ A/B 无样本但已收口不阻塞。C 在 `sp=0047` 再次 15/0/0；ERROR 2225 中 2206 为其它 mod `[action_ext]` diag、涉 `[rai]`=0。两判读脚本按 P92/P93/P94 定案改口径：A/B「无样本（已收口）」不再提示补场、有样本「仅记录（跨场不可比）」、D 拆「连续性/时长」、新增日志通道诊断并修正 P79 回归误标；重出四份报告、三路径回归通过。下一场仍双击 bat 正常打一场约 30min + 两只不同新大型怪（避开 0020/0050/0052/0051/0047）即可。

## 各线一行
音频：居合 `swo_fx2`→`swo_fx2_success`，v3 实机通过。HP 条：`0x4EEC bne 0x50c4` → NOP。IPS32：删 `0x76254` 记录使 `0x76154` 回 native，变体 `4e778eef…` 长期启用（回滚 = AI mod 失效），此后数据均为变体口径。07 随从猫 22:45 已回滚移除，任务区与产出不在。
