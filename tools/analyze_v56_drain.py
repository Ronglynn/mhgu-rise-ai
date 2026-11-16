# -*- coding: utf-8 -*-
"""v56 判读：动作耐力消耗 ×64（1~2 个动作自然耗尽）+ v55~v50 全兼容。

用户 2026-11-14 15:55 要求「修改雄火龙动作的消耗耐力值，让其在一两个动作后疲劳」。
v56 在已装的 h_stamina @0xBD260 里把每次负 delta 放大 DRAIN_MUL=64 倍
（实测原始 -8 → -512），让游戏自己连续扣当前耐力 act+0x508，
由 0xBD2B4 cmp cur,-delta / ble 0xBD350 自然判定耗尽。
新增 J 行记录每次放大（d0/d1/cur/a505/a508/jn），G 行仍只在耗尽时输出 1 条。

--- v55 原文（历史判据）---
v55 判读：游戏原生强制疲惫（0xBD260 delta 放大）+ W 行链 I 字段 + 全版本兼容。

P48 证伪 v54 直接写状态字：a505=2/a508=0 被游戏状态更新覆盖（t505→0, t508→800）。
v55 改为 hook 0xBD260 一次性把 delta 放大为 -(cur+1)，让游戏自己走耗尽分支：
  +0x508=0 → +0x505=1 → 同一 0x76154 内 0x762C8 门控 1→2 → 0x816D0 → 0xF8D384
另修 R 行 270 字符截断：链 I 全字段移到独立 W 行；W1 疲惫判据切到 act+0x505。

--- v54 原文（历史判据，保留供对照）---
v54 判读：完整疲惫链路只读快照 + 一次性强制疲惫 + v53/v52/v51/v50 全兼容。

v54 新增（P46 链 I 定案）：
  R 行 t505(疲惫状态字) / t506(上限) / t508(当前耐力) / t50c / p41(Stamina_low FSM)
      / pt5c(二级解引用计时器) / t1a8 / t362 / t5df3
  G 行 = 一次性强制事件前后快照（b505/b508/bp41 → a505/a508/ap41）
  S 行 gdone/gf = 强制熔断标志与触发帧
  强制只写 act+0x508=0 与 act+0x505=2，共 3 字节，一次性、LOW==0 门控。

--- v52 原文 ---
v52 判读：每动作 stamina（减气点）观测 + 候选当前耐力扫描 + v51/v50 全兼容。

v52 新增（零新增 hook / 零写入）：
  Y 行 = 每 2 个动作 1 条快照，am=act+0x4D8（每动作 amount 瞬时值）、d2=+0x4D2（气绝对照）
  S 行 amx/anf/anr = 每帧扫 8 槽 amount 的峰值 / 非零帧数 / 上升沿次数
  R 行 q40..q60 = p=*(mon+0xCAC0) 子对象 +0x40..+0x60 的候选当前耐力字段
离线字节级依据（main_text_decomp.bin 文件偏移 base=0）：
  0x9DBE4 movw r1,#0x4D8 / ldrh / add r1,r1,r3 / strh  ← 每动作累加减气点
  0x9A454 movw r0,#0x4D8 / ldrh / bl 0xA30E4            ← 消费该 amount
  ⇒ GU 无独立「当前耐力值」，模型是「每动作 amount → counter(5D82) vs thr(5D84)」。

--- v51 原文 ---
v51 判读：上游减气 amount 观测探针 + v50 W1 权重层 / W0 门控。

v51 新增（零新增 hook、零写入）：
  H 行 = 0xA30E4 add 调用等距样本（a1 即 amount，含 ret/cnt/thr/proc/d5）
  R 行 ac/asum/amax/anz = 每槽调用数 / amount 累计 / 峰值 / 非零次数
  S 行 gac/gsum/gmax/gnz = 全局口径
根因判据（P41 更正，2026-11-12 22:23）：
  X h_exh 未 INSTALL       -> IPS32 跳板，gac=0 不可解读
  N gac==0                 -> **正常静默态，不能定案任何根因**
      实证：v48 P30 场在插件强制触发前已有 28 次动作，add=0 / ex=0；
      40 条 U 行全部出现在 f=5193 强制之后（疲惫状态机连锁）。
      0xA30E4 是「减气蓄积 counter 的累加入口」，不是「每动作扣 stamina」的通道。
      只有在观察到疲惫/流口水后 gac 仍为 0，才构成异常。
  B gac>0 且 gsum==0      -> 通道在跑但 amount 恒 0（数据层）
  C gac>0 且 gsum>0 且 ex 恒 0 -> 累加被别处吞掉（新根因）
  D 其余                   -> 减气链在跑，本场未达阈值
  （原 A「跨怪路径差异」已撤回：与打不打怪、与怪种均无关）

--- v50 原文 ---
v50 判读：W1 Rise 池权重层 + W0 疲惫触发门控。

W1：对合格 case 按原权重降序取 top-k，按 Rise 排序形状重分配（和恒 100）后轮盘赌。
  形状 N3[45,32,23] / N4[40,27,20,13] / T3[60,30,10]，非疲 61:39 混合。
  离线对拍：非疲 1.6701 (Rise 1.6705)、疲惫 1.2955 (Rise 1.2984)。
W0：proc<=30 且 0<thr<0x4000；h_exh 已装时只信 ret==1；小怪槽 thr=65535 排除。

用法: python analyze_v56_drain.py <log>
"""
import re
import sys
import collections
from pathlib import Path

INT = {"f", "i", "log", "a", "an", "an0", "dA", "lowhits", "a1", "cnt",
       "thr", "proc", "amt", "force", "forced", "ret", "st", "st3", "vd",
       "wm", "wk", "tir", "bad", "kind", "reason", "t4", "ex", "d5",
       "h1", "e1", "dc", "s3f", "f5c", "p3ca", "p3be", "low", "flg",
       "t5c", "live", "hub", "s0", "s1", "s2", "sv0", "sv1", "sv2",
       "w3", "w4", "wt", "d3", "skip", "n", "nc", "d", "ki", "rd",
       "b1", "ph", "sw", "sw2", "nr", "p5", "sel", "act", "beg", "begf",
       "rep", "v", "noalt", "fail", "ok", "peak", "m", "m1", "m0c",
       "m0e", "x", "q", "ac", "asum", "amax", "anz",
       "gac", "gsum", "gmax", "gnz", "s", "am", "d2", "amx", "anf", "anr",
       "q40", "q44", "q48", "q4c", "q50", "q54", "q58", "q60",
       "t505", "t506", "t508", "t50c", "p41", "pt5c", "t1a8", "t362", "t5df3",
       "b505", "b508", "b506", "bp41", "a505", "a508", "ap41", "force",
       "gdone", "gf", "an", "thr", "d0", "d1", "cur", "jn"}
ROW = re.compile(r"\[rai\] ([A-Z]+) (.*)$")


def parse(tail):
    d = {}
    for k, v in re.findall(r"(\w+)=(\S+)", tail):
        if k in INT:
            try:
                d[k] = int(v, 0) if v.startswith("0x") else int(v)
            except ValueError:
                d[k] = v
        else:
            d[k] = v
    return d


def ival(rows, key):
    return [r[key] for r in rows if isinstance(r.get(key), int)]


def main(path):
    lines = Path(path).read_bytes().decode("utf-8", "replace").splitlines()
    rows = collections.defaultdict(list)
    for ln in lines:
        m = ROW.search(ln)
        if m:
            rows[m.group(1)].append(parse(m.group(2)))
    V, T, U, S, R, N = rows["V"], rows["T"], rows["U"], rows["S"], rows["R"], rows["N"]
    H = rows["H"]
    Y = rows["Y"]
    G = rows["G"]
    W = rows["W"]
    J = rows["J"]
    QKEYS = ("q40", "q44", "q48", "q4c", "q50", "q54", "q58", "q60")
    TKEYS = ("t505", "t506", "t508", "t50c", "p41", "pt5c", "t1a8", "t362", "t5df3")
    BEAT = rows["BEAT"]
    is_v56 = any("RAI v56" in l for l in lines)
    is_v55 = is_v56 or any("RAI v55" in l for l in lines)
    is_v54 = is_v55 or any("RAI v54" in l for l in lines)
    is_v53 = is_v54 or any("RAI v53" in l for l in lines)
    is_v52 = is_v53 or any("RAI v52" in l for l in lines)
    is_v51 = is_v52 or any("RAI v51" in l for l in lines)
    is_v50 = is_v51 or any("RAI v50" in l for l in lines)
    fatal = sum(1 for l in lines if "FATAL" in l)
    # 实机行带 "[forge] [INFO]" 前缀，不能用 startswith("[rai]")
    installs = [l.strip() for l in lines if "[rai] INSTALL h_" in l]
    banner = next((l.strip() for l in lines if "RAI v56" in l),
                  next((l.strip() for l in lines if "RAI v55" in l),
                  next((l.strip() for l in lines if "RAI v54" in l),
                  next((l.strip() for l in lines if "RAI v52" in l),
                  next((l.strip() for l in lines if "RAI v51" in l),
                  next((l.strip() for l in lines if "RAI v50" in l), "(旧日志)"))))))
    crash = [l.strip() for l in lines
             if "c0000005" in l or "*** exception" in l or "host backtrace" in l]

    print("=== v56 动作耐力消耗 x64 + J 行逐动作 + v55~v50 判读 ===")
    print("日志: %s" % path)
    print("banner: %s" % banner[:120])
    ver = ("v56" if is_v56 else ("v55" if is_v55 else ("v54" if is_v54 else
           ("v53" if is_v53 else ("v52" if is_v52 else
           ("v51" if is_v51 else ("v50" if is_v50 else "旧日志(降级)")))))))
    print("版本=%s  V=%d T=%d U=%d S=%d R=%d W=%d J=%d N=%d H=%d Y=%d G=%d BEAT=%d  FATAL=%d" %
          (ver, len(V), len(T), len(U), len(S), len(R), len(W), len(J), len(N),
           len(H), len(Y), len(G), len(BEAT), fatal))
    for l in installs[:6]:
        print("  " + l[:120])

    checks = []
    skips = []
    # 一场没有自然疲惫的任务里，疲惫态判据是「样本缺失」而非「规则违例」。
    # P37：v50 雄火龙场 U=0/T=0/st2=0 曾被误报为 6 个 FAIL，现区分 SKIP。
    # v54：疲惫可由链 I（+0x505）触发，与链 II 的 U/T/st3 无关。
    # 但 W1 的疲惫形状判据仍基于链 II，故强制疲惫场 wm=3 / wt 可能全 0。
    # ⇒ 区分「有疲惫事件」（用于诊断输出）与「W1 疲惫形状样本」（用于规则检查）。
    has_tired = (len(U) > 0 or len(T) > 0
                 or any(x.get("st3") == 2 for x in V))
    has_chain1_tired = (len(G) > 0
                        or any(isinstance(r.get("t505"), int) and r["t505"] >= 2
                               for r in R))
    w1_tired_sample = any(x.get("st3") == 2 for x in V) or any(
        x.get("wm") == 3 for x in V)

    def add(name, ok, detail):
        checks.append((name, bool(ok), detail))
        print("  [%s] %-42s %s" % ("PASS" if ok else "FAIL", name, detail))

    def skip(name, detail):
        skips.append((name, detail))
        print("  [SKIP] %-42s %s" % (name, detail))

    # --- 版本 / 安全性 ---
    add("RAI v50 版本横幅", is_v50, banner[:60])
    if is_v54 and not is_v55:
        add("RAI v54 横幅（疲惫链路快照 + 强制）", True, "v54 observer")
        if R and all(isinstance(R[0].get(k), int) for k in TKEYS):
            add("R 行 P46 链 I 字段齐全", True,
                "R=%d 首行 t505=%s t508=%s p41=%s" %
                (len(R), R[0].get("t505"), R[0].get("t508"), R[0].get("p41")))
        else:
            skip("R 行 P46 链 I 字段齐全",
                 "v54 已知 270 字符截断（P48 实证）；v55 已改由 W 行承载")
        add("G 行强制事件恰好 1 条", len(G) == 1, "G=%d" % len(G))
        if G:
            g = G[0]
            add("强制前状态为未疲惫（b505=0）", g.get("b505") == 0,
                "b505=%s b508=%s b506=%s bp41=%s" %
                (g.get("b505"), g.get("b508"), g.get("b506"), g.get("bp41")))
            add("强制写入回读正确（a505=2 / a508=0）",
                g.get("a505") == 2 and g.get("a508") == 0,
                "a505=%s a508=%s ap41=%s" %
                (g.get("a505"), g.get("a508"), g.get("ap41")))
            add("p+0x41 未被插件写入（交给游戏 FSM）",
                g.get("bp41") == g.get("ap41"),
                "bp41=%s ap41=%s" % (g.get("bp41"), g.get("ap41")))
        if S:
            add("S 行强制熔断已置位（gdone=1）", S[-1].get("gdone") == 1,
                "gdone=%s gf=%s" % (S[-1].get("gdone"), S[-1].get("gf")))
    if is_v56:
        add("RAI v56 横幅（动作消耗 x64）", True, "v56 drain x64")
        add("J 行逐动作放大记录存在", len(J) >= 1, "J=%d" % len(J))
        add("1~3 个动作内耗尽（J 行数）", 1 <= len(J) <= 3, "J=%d" % len(J))
        if J:
            j0, jl = J[0], J[-1]
            add("每次放大 d0 != d1",
                all(isinstance(x.get("d0"), int) and isinstance(x.get("d1"), int)
                    and x["d0"] != x["d1"] for x in J),
                "首 d0=%s d1=%s / 末 d0=%s d1=%s" %
                (j0.get("d0"), j0.get("d1"), jl.get("d0"), jl.get("d1")))
            add("最后一次 J 触发游戏耗尽（a505>=1 或 a508=0）",
                (isinstance(jl.get("a505"), int) and jl["a505"] >= 1)
                or jl.get("a508") == 0,
                "a505=%s a508=%s" % (jl.get("a505"), jl.get("a508")))
            add("jn 递增且与 J 行数一致",
                [x.get("jn") for x in J] == list(range(1, len(J) + 1)),
                "jn=%s" % [x.get("jn") for x in J])
        if G:
            add("G 行 jn 与放大次数一致",
                G[0].get("jn") == len(J), "G.jn=%s J=%d" % (G[0].get("jn"), len(J)))
    if is_v55:
        add("RAI v55 横幅（原生强制疲惫）", True, "v55 native force")
        add("h_stamina @0xBD260 已安装（运行时首字核对）",
            any("INSTALL h_stamina" in l for l in lines),
            "INSTALL=%d SKIP=%d" %
            (sum(1 for l in lines if "INSTALL h_stamina" in l),
             sum(1 for l in lines if "SKIP h_stamina" in l)))
        add("W 行链 I 字段齐全（修 R 行 270 截断）",
            bool(W) and all(isinstance(W[0].get(k), int) for k in TKEYS),
            "W=%d 首行 t505=%s t508=%s p41=%s" %
            (len(W), W[0].get("t505") if W else "?", W[0].get("t508") if W else "?",
             W[0].get("p41") if W else "?"))
        add("G 行强制事件恰好 1 条", len(G) == 1, "G=%d" % len(G))
        if G:
            g = G[0]
            add("delta 已放大（d0 != d1）",
                isinstance(g.get("d0"), int) and isinstance(g.get("d1"), int)
                and g["d0"] != g["d1"],
                "d0=%s d1=%s (d1 = -(cur+1) 补码)" % (g.get("d0"), g.get("d1")))
            add("游戏原生耗尽（a508=0 / a505>=1）",
                g.get("a508") == 0 and isinstance(g.get("a505"), int)
                and g["a505"] >= 1,
                "a505=%s a508=%s ap41=%s" %
                (g.get("a505"), g.get("a508"), g.get("ap41")))
            add("p+0x41 未被插件写入（交给游戏 FSM）",
                g.get("bp41") == g.get("ap41"),
                "bp41=%s ap41=%s" % (g.get("bp41"), g.get("ap41")))
        if S:
            add("S 行强制熔断已置位（gdone=1）", S[-1].get("gdone") == 1,
                "gdone=%s gf=%s" % (S[-1].get("gdone"), S[-1].get("gf")))
    if is_v52:
        add("RAI v52 每动作 stamina 横幅（只读，无新增 hook）", True, "v52 observer")
        add("S 行 amx/anf/anr 字段齐全",
            bool(S) and all(isinstance(S[-1].get(k), int) for k in ("amx", "anf", "anr")),
            "S=%d 末行 amx=%s anf=%s anr=%s" %
            (len(S), S[-1].get("amx") if S else "?", S[-1].get("anf") if S else "?",
             S[-1].get("anr") if S else "?"))
        qsrc = W if is_v55 else R
        add("q40..q60 候选字段齐全（v55 在 W 行）",
            bool(qsrc) and all(isinstance(qsrc[0].get(k), int) for k in QKEYS),
            "%s=%d 首行 q40=%s" %
            ("W" if is_v55 else "R", len(qsrc), qsrc[0].get("q40") if qsrc else "?"))
        if Y:
            add("Y 行每动作快照存在", True, "Y=%d" % len(Y))
        else:
            skip("Y 行每动作快照", "本场无动作开始事件（或全被配额截断）")
    if is_v51:
        add("RAI v51 探针横幅（只读，无新增 hook）", True, "v51 observer")
        add("S 行上游统计字段齐全（gac/gsum/gmax/gnz）",
            bool(S) and all(isinstance(S[-1].get(k), int) for k in
                            ("gac", "gsum", "gmax", "gnz")),
            "S=%d 末行 gac=%s gsum=%s gmax=%s gnz=%s" %
            (len(S), S[-1].get("gac") if S else "?",
             S[-1].get("gsum") if S else "?", S[-1].get("gmax") if S else "?",
             S[-1].get("gnz") if S else "?"))
    add("零 FATAL（guest 侧）", fatal == 0, "FATAL=%d" % fatal)
    add("零 host 异常（c0000005）", not crash,
        "异常行=%d %s" % (len(crash), crash[0][:50] if crash else ""))
    n_inst = sum(1 for l in installs if any(h in l for h in
                 ("h_matcher", "h_emc", "h_unify", "h_start_40", "h_exh")))
    add("5 个 hook 全部 INSTALL", n_inst >= 5, "INSTALL=%d" % n_inst)
    add("U 行无 v48 amount 强制（v54 的 G 行 force=1 属本版设计）",
        not any(x.get("force") == 1 for x in U), "U force=1 计数=%d" %
        sum(1 for x in U if x.get("force") == 1))
    live = ival(BEAT, "live")
    add("live=1（自保护未熔断）", not live or live[-1] == 1,
        "BEAT.live 末值=%s" % (live[-1] if live else "?"))
    hub = ival(BEAT, "hub")
    add("hub=15", not hub or 15 in hub, "hub=%s" % sorted(set(hub))[:4])

    # --- W1 权重层 ---
    bad_wm = [x for x in V if isinstance(x.get("wm"), int)
              and isinstance(x.get("wk"), int)
              and x["wk"] != {0: 0, 1: 3, 2: 4, 3: 3}.get(x["wm"], -1)]
    add("V 行 wm->wk 映射正确 (0/1/2/3 -> 0/3/4/3)",
        len(V) > 0 and len(bad_wm) == 0, "V=%d 违例=%d" % (len(V), len(bad_wm)))
    bad_vd = [x for x in V if isinstance(x.get("st3"), int)
              and isinstance(x.get("vd"), int)
              and x["vd"] != (1 if x["st3"] == 2 else 2)]
    add("V 行 st3->vd 收敛两档 (非疲2/疲1)",
        len(V) > 0 and len(bad_vd) == 0, "违例=%d" % len(bad_vd))
    st_set = set(ival(V, "st3"))
    wm_set = set(ival(V, "wm"))
    if S:
        s = S[-1]
        w34 = [s.get(k) for k in ("w3", "w4")]
        wsum = sum(v for v in w34 if isinstance(v, int))
        # P41：本场 13 条 V 行里 12 条因池内合格 case<4 退回 v38，
        # 只有 1 条走 k3。要求 w3>0 且 w4>0 会把「样本不足」误报成违例。
        if wsum > 0:
            add("W1 非疲形状生效（w3+w4>0）", True,
                "w3/w4=%s（k4 需 >=4 个合格 case，样本少时不触发属正常）" % w34)
        else:
            skip("W1 非疲形状生效",
                 "本场抽选事件过少 / 候选不足，无 Rise 形状样本（非规则违例）")
        add("d3/skip 恒 0（v49 旋钮已移除）",
            s.get("d3") == 0 and s.get("skip") == 0,
            "d3=%s skip=%s" % (s.get("d3"), s.get("skip")))
    else:
        skip("W1 非疲形状生效", "S=0（无汇总行）")
        add("d3/skip 恒 0（v49 旋钮已移除）", False, "S=0")

    if is_v55 and (has_chain1_tired or w1_tired_sample):
        # v55：W1 疲惫判据已切到链 I，链 II 的 U/T 事件在原生强制场本就不出现。
        # P51：疲惫窗口内若主怪没有任何 EMC 抽选事件（常见于用户暂停、
        # 或疲惫期低活动），st3/wm/wt 全 0 是「样本缺失」而非规则违例。
        # 必须按「疲惫起点 + 主怪」筛选 V 行，否则会把小怪抽选算进来。
        gf = G[0].get("f") if G else None
        gmon = G[0].get("mon") if G else None
        # P53：必须用「t505>=2 的真实疲惫窗口」筛选 V 行，不能用 f>G 帧。
        # 长任务里疲惫结束后还有几万帧，f>G 会把恢复后的发怒样本
        # （st3=1）误算进疲惫窗，造成 wm/wt 缺失的假 FAIL。
        tw = [x for x in W if isinstance(x.get("t505"), int)
              and x["t505"] >= 2 and isinstance(x.get("f"), int)
              and (gmon is None or x.get("mon") == gmon)]
        t0 = min((x["f"] for x in tw), default=None)
        t1 = max((x["f"] for x in tw), default=None)
        if t0 is None and isinstance(gf, int):
            t0, t1 = gf, gf + 6000   # 无 W 行时退化为 G 后 6000 帧
        tired_v = [x for x in V if isinstance(x.get("f"), int)
                   and isinstance(t0, int) and isinstance(t1, int)
                   and t0 <= x["f"] <= t1
                   and (gmon is None or x.get("mon") == gmon)]
        if not tired_v:
            skip("W1 疲惫形状（st3/wm/wt）",
                 "真实疲惫窗 f=%s..%s 内主怪 %s 无 EMC 抽选 V 行（低活动/结算后菜单），"
                 "样本缺失非规则违例" % (t0, t1, gmon))
        else:
            add("W1 疲惫判据切链 I（V 行 st3=2 出现）",
                any(x.get("st3") == 2 for x in tired_v),
                "疲惫窗内主怪 V=%d st3=%s" %
                (len(tired_v), sorted(set(ival(tired_v, "st3")))))
            add("疲惫 Rise 形状被使用（wm=3）",
                any(x.get("wm") == 3 for x in tired_v),
                "wm=%s" % sorted(set(ival(tired_v, "wm"))))
            if S:
                add("疲惫形状计数 wt>0",
                    isinstance(S[-1].get("wt"), int) and S[-1]["wt"] > 0,
                    "wt=%s" % S[-1].get("wt"))
    elif has_tired and w1_tired_sample:
        add("三态均有 V 行样本", {0, 1, 2}.issubset(st_set),
            "st3=%s" % sorted(st_set))
        add("三种 Rise 形状均被使用", {1, 2, 3}.issubset(wm_set),
            "wm=%s" % sorted(wm_set))
        if S:
            add("疲惫形状计数 wt>0",
                isinstance(S[-1].get("wt"), int) and S[-1]["wt"] > 0,
                "wt=%s" % S[-1].get("wt"))
        add("U 行 EXH 触发全部合法（bad=0）",
            all(x.get("bad") == 0 for x in U),
            "U=%d bad!=0=%d" % (len(U), sum(1 for x in U if x.get("bad") != 0)))
        enter = [x for x in T if x.get("kind") == 1]
        exit_ = [x for x in T if x.get("kind") == 2]
        add("T 行疲惫 ENTER/EXIT 齐备", len(enter) > 0 and len(exit_) > 0,
            "ENTER=%d EXIT=%d" % (len(enter), len(exit_)))
        add("疲惫退出用动作数窗口（免疫暂停）",
            any(x.get("reason") == 3 and isinstance(x.get("an"), int)
                and x["an"] >= 40 for x in exit_),
            "reason=3 & an>=40 = %d" %
            sum(1 for x in exit_ if x.get("reason") == 3
                and isinstance(x.get("an"), int) and x["an"] >= 40))
    elif is_v54 and has_chain1_tired and not w1_tired_sample:
        # v54 强制疲惫走链 I（+0x505），而 W1 疲惫形状判据基于链 II
        # （EXH ret==1 / proc 递增）。两者解耦 ⇒ 这里不是规则违例，
        # 而是 v55 待修项：把疲惫判据切到 t505>=2 / p41>=5。
        skip("W1 三态 / 三形状 / wt / U / T",
             "链 I 强制疲惫已发生（G=%d, t505>=2），但 W1 疲惫判据基于链 II，"
             "本场 st3/wm=3/wt 全 0 属预期；判据切换留待 v55" % len(G))
    else:
        skip("三态 / 三形状 / wt / U / T 疲惫态判据",
             "本场无疲惫样本（U=0 T=0 st2=0），非规则违例")

    # --- W0 门控（无论有无疲惫样本都适用）---
    bad_proc = [x for x in T if isinstance(x.get("proc"), int) and x["proc"] > 30]
    add("T 行无 proc>30 误判（P33 修复）", len(bad_proc) == 0,
        "越界=%d %s" % (len(bad_proc), [x.get("proc") for x in bad_proc][:5]))

    # --- 观测完整性 ---
    add("R 行无条件定时快照保留", len(R) >= 20, "R=%d" % len(R))
    add("N 行低活动锚点保留", len(N) > 0, "N=%d" % len(N))

    print("\n=== 上游减气输入诊断 (v51 / P38 §5) ===")
    if not is_v51:
        print("  旧日志无 H / ac / gac 字段，跳过（验证降级不崩溃）。")
    else:
        gac = S[-1].get("gac", 0) if S else 0
        gsum = S[-1].get("gsum", 0) if S else 0
        gmax = S[-1].get("gmax", 0) if S else 0
        gnz = S[-1].get("gnz", 0) if S else 0
        print("  S 末行: gac=%s gsum=%s gmax=%s gnz=%s" %
              (gac, gsum, gmax, gnz))
        a1s = ival(H, "a1")
        print("  H 样本=%d  a1 值域=%s  a1>0 计数=%d" %
              (len(H), sorted(set(a1s))[:12], sum(1 for v in a1s if v > 0)))
        per = collections.defaultdict(list)
        for x in R:
            if isinstance(x.get("ac"), int):
                per[x.get("mon")].append(x)
        for mon, rs in sorted(per.items(), key=lambda kv: -len(kv[1]))[:5]:
            last = rs[-1]
            print("  mon=%s R=%d thr=%s ex=%s d5=%s | ac=%s asum=%s amax=%s anz=%s" %
                  (mon, len(rs), last.get("thr"), last.get("ex"),
                   last.get("d5"), last.get("ac"), last.get("asum"),
                   last.get("amax"), last.get("anz")))
        exs = ival(R, "ex")
        exh_installed = any("INSTALL h_exh" in l for l in lines)
        print("  h_exh INSTALL = %s" % exh_installed)
        if not exh_installed:
            verdict = "X: h_exh 未 INSTALL（IPS32 跳板）=> gac=0 不可解读，先核对 SITE +0A30E4"
        elif not isinstance(gac, int) or gac == 0:
            # P41 更正：v48 P30 场强制前 28 次动作也是 add=0/ex=0，
            # 40 条 U 行全部在 f=5193 插件强制之后。故 gac=0 是自然静默态，
            # 与打不打怪、与怪种无关，不能判「跨怪路径差异」。
            verdict = ("N: 正常静默态，不能定案根因（v48 强制前 28 次动作亦 add=0/ex=0；"
                       "0xA30E4 是减气蓄积通道，不是每动作 stamina 扣减）")
        elif isinstance(gsum, int) and gsum == 0:
            verdict = "B: 通道在跑但 amount 恒 0 => 数据层（动作参数不带减气点）"
        elif isinstance(gsum, int) and gsum > 0 and exs and max(exs) == 0:
            verdict = "C: 有有效 amount 但 ex 恒 0 => 累加被别处吞掉（新根因）"
        else:
            verdict = "D: amount 与 ex 均正常 => 减气链在跑，本场未达阈值"
        print("  根因判据: %s" % verdict)
        if isinstance(gac, int) and gac == 0 and exh_installed:
            print("  提示: 想观测「每动作扣 stamina」应改探 0x9DB54/0x9A470 上游，")
            print("        或找被轮询的当前耐力值；本探针不覆盖该层（P41 §4）。")

    print("\n=== v52 每动作 stamina / 候选当前耐力 ===")
    if not is_v52:
        print("  旧日志无 Y / q* / amx 字段，跳过（验证降级不崩溃）。")
    else:
        ams = ival(Y, "am")
        print("  Y 行=%d  am(act+0x4D8) 值域=%s  am>0 计数=%d  峰值=%s" %
              (len(Y), sorted(set(ams))[:12], sum(1 for v in ams if v > 0),
               max(ams) if ams else "-"))
        d2s = ival(Y, "d2")
        print("  d2(act+0x4D2 气绝对照) 值域=%s" % sorted(set(d2s))[:8])
        if S:
            sl = S[-1]
            print("  S 末行 amount 每帧统计: amx=%s anf=%s anr=%s" %
                  (sl.get("amx"), sl.get("anf"), sl.get("anr")))
        # P43：全量 uniq 会把「不同怪槽的常量差」误当成「随时间变化」。
        # 必须按主怪（thr 合法且 R 行最多）单独统计，才能判断是不是运行时量。
        by_mon = collections.defaultdict(list)
        for r in R:
            by_mon[r.get("mon")].append(r)
        valid = {m: rs for m, rs in by_mon.items()
                 if any(isinstance(r.get("thr"), int) and 0 < r["thr"] < 0x4000
                        for r in rs)}
        main_rows = max(valid.values(), key=len) if valid else []
        main_mon = next((m for m, rs in valid.items() if rs is main_rows), "?")
        print("  R 行候选字段取值数（主怪=%s R=%d）:" % (main_mon, len(main_rows)))
        for k in QKEYS + ("s3f", "f5c"):
            vals = ival(R, k)
            mv = ival(main_rows, k)
            print("    %-4s 全量 uniq=%-3d 主怪 uniq=%-3d 主怪值=%s" %
                  (k, len(set(vals)), len(set(mv)), sorted(set(mv))[:6]))
        consts = [k for k in QKEYS if main_rows and len(set(ival(main_rows, k))) == 1]
        if len(consts) == len(QKEYS):
            print("    => 全部 q* 在主怪上恒定，属参数/常量区，不是当前耐力值")
        else:
            print("    => 主怪上变化的候选: %s" %
                  [k for k in QKEYS if k not in consts])
        amx = S[-1].get("amx", 0) if S else 0
        if ams and max(ams) > 0:
            sv = "已捕获每动作减气 amount（Y.am>0），可统计动作→减气点分布"
        elif isinstance(amx, int) and amx > 0:
            sv = "Y 行未抓到瞬时值，但每帧统计 amx>0 ⇒ amount 真实存在（同帧被消费清零）"
        else:
            # P43 严谨化：Y 行是动作开始时的离散采样，forge_onUpdate 是宿主帧回调，
            # 两者都可能错过 0x9DBE4「写入 -> 0x9A470 消费 -> 清零」的短窗口。
            # 全 0 只能说明「没采到」，不能定案「路径未走」。
            sv = ("离散采样未捕获非零 amount：无法区分「0x9DBE4 路径未走」与"
                  "「写入-清零窗口短于采样间隔」。定案需 hook 0x9DB54/0x9DBE4 "
                  "直接抓 r3（须核对 IPS32 首字）")
        print("  判定: %s" % sv)

    print("\n=== v55/v54 疲惫链路时间线 (P46 链 I) ===")
    if not (is_v54 or is_v55):
        print("  旧日志无 t505/t508/p41/G 字段，跳过。")
    else:
        # 主怪 = thr 合法且 R 行最多
        by_mon = collections.defaultdict(list)
        for r in R:
            by_mon[r.get("mon")].append(r)
        valid = {m: rs for m, rs in by_mon.items()
                 if any(isinstance(r.get("thr"), int) and 0 < r["thr"] < 0x4000
                        for r in rs)}
        main_rows = max(valid.values(), key=len) if valid else []
        if is_v55 and W:
            wmap = {(w.get("f"), w.get("mon")): w for w in W}
            for r in main_rows:
                w = wmap.get((r.get("f"), r.get("mon")))
                if w:
                    for k in TKEYS:
                        if k in w: r[k] = w[k]
        print("  主怪 R=%d  t505 值域=%s  t508 值域=%s  p41 值域=%s" %
              (len(main_rows), sorted(set(ival(main_rows, "t505")))[:8],
               sorted(set(ival(main_rows, "t508")))[:8],
               sorted(set(ival(main_rows, "p41")))[:8]))
        gf = G[0].get("f") if G else None
        if isinstance(gf, int):
            win = [r for r in main_rows
                   if isinstance(r.get("f"), int) and gf - 300 <= r["f"] <= gf + 900]
            print("  G 事件 f=%d，窗口 ±300/+900 内 %d 条 R 行：" % (gf, len(win)))
            for r in win[::max(1, len(win) // 12)][:14]:
                print("    f=%-7s t505=%-3s t508=%-6s p41=%-3s pt5c=%-12s st=%-2s ex=%s" %
                      (r.get("f"), r.get("t505"), r.get("t508"), r.get("p41"),
                       r.get("pt5c"), r.get("st"), r.get("ex")))
            after = [r for r in win if isinstance(r.get("f"), int) and r["f"] > gf]
            t505_after = [r.get("t505") for r in after if isinstance(r.get("t505"), int)]
            p41_after = [r.get("p41") for r in after if isinstance(r.get("p41"), int)]
            if any(v >= 2 for v in t505_after):
                print("  => 游戏保持疲惫态（t505>=2），强制生效")
            else:
                print("  => 强制后 t505 未保持 >=2：需查游戏是否复位 / G 后是否有 R 行")
            if any(isinstance(v, int) and v >= 5 for v in p41_after):
                print("  => p+0x41 出现 >=5，Stamina_low_Start FSM 已推进")
            else:
                # P49 实机：用户肉眼可见疲惫且 t505 完整走 0→1→2→3→0，
                # 但 p+0x41 恒 0 ⇒ P46 对该偏移的推断存疑（可能对象不同，
                # 或 0xF8F384 的 FSM 状态字不在此处）。不能据此否定疲惫。
                print("  => p+0x41 恒 0：P46 对该偏移/对象的推断存疑（P49 实证）；")
                print("     不要据此否定疲惫，以 t505 状态机 + t50c 计时器为准")

        # --- P49：act+0x50C 疲惫帧倒计时（f32，每帧 -1，归零结束）---
        import struct
        def _f32(v):
            try:
                return struct.unpack("<f", struct.pack("<I", v & 0xFFFFFFFF))[0]
            except Exception:
                return 0.0
        c50 = [(x.get("f"), x.get("t50c"), x.get("t505")) for x in W
               if isinstance(x.get("f"), int) and isinstance(x.get("t50c"), int)
               and x.get("t50c") and x.get("mon") in valid]
        if c50:
            vals = [_f32(c) for _, c, _ in c50]
            print("  P49 计时器 act+0x50C: n=%d  f32 %.1f .. %.1f  f=%s..%s" %
                  (len(c50), min(vals), max(vals), c50[0][0], c50[-1][0]))
            # P52：按「连续递减」切段。暂停期间 forge 帧继续涨但计时器冻结，
            # 会形成平台；全场线性拟合会被拉平（实测 -0.172），必须分段算。
            pts = [(f, _f32(c)) for f, c, _ in c50]
            segs, cur = [], [pts[0]]
            for p in pts[1:]:
                if p[1] < cur[-1][1] - 0.5:
                    cur.append(p)
                else:
                    if len(cur) >= 2:
                        segs.append(cur)
                    cur = [p]
            if len(cur) >= 2:
                segs.append(cur)
            for sg in segs:
                f0, v0 = sg[0]
                f1, v1 = sg[-1]
                if f1 > f0 and v0 > v1:
                    sl = (v1 - v0) / (f1 - f0)
                    tag = "正常游戏逻辑帧倒计时" if abs(sl + 1.0) < 0.15 else "偏离 -1"
                    print("     递减段 f=%s..%s  f32 %.1f→%.1f  斜率 %+.3f/帧 (%s)" %
                          (f0, f1, v0, v1, sl, tag))
            if len(segs) > 1:
                print("     => 多段递减 + 段间平台 = 暂停冻结：计时器按游戏逻辑帧计，"
                      "暂停不消耗疲惫窗口")
            print("     => 疲惫是固定时长计时器，计时器归零后 t505→0 / t508 恢复")
        print("  注：v55 已把 W1 疲惫判据切到链 I（act+0x505>=2），"
              "本场 wm=3 / wt>0 应出现；链 II 的 U/T 事件不再作为疲惫必要条件。")

    print("\n=== v56 动作耐力消耗逐次轨迹 ===")
    if not is_v56:
        print("  旧日志无 J 行，跳过。")
    else:
        for x in J[:12]:
            print("  J f=%-7s d0=%-12s d1=%-12s cur=%-5s -> a505=%-2s a508=%-5s an=%-3s jn=%s" %
                  (x.get("f"), x.get("d0"), x.get("d1"), x.get("cur"),
                   x.get("a505"), x.get("a508"), x.get("an"), x.get("jn")))
        if J:
            def signed(v):
                return v - (1 << 32) if isinstance(v, int) and v >= (1 << 31) else v
            print("  原始消耗 d0=%s，放大后 d1=%s（倍数 %s）" %
                  (signed(J[0].get("d0")), signed(J[0].get("d1")),
                   ("%.1f" % (signed(J[0].get("d1")) / signed(J[0].get("d0"))))
                   if signed(J[0].get("d0")) else "?"))
            print("  => %d 个动作后游戏自己判定耗尽" % len(J))

    print("\n=== 观测配额盲区检查 (P45) ===")
    last_beat = max(ival(BEAT, "f")) if BEAT else 0
    last_r = max(ival(R, "f")) if R else 0
    last_y = max(ival(Y, "f")) if Y else 0
    gap_r, gap_y = last_beat - last_r, last_beat - last_y
    print("  BEAT 末帧=%-7d R 末帧=%-7d (差 %-6d)  Y 末帧=%-7d (差 %-6d)" %
          (last_beat, last_r, gap_r, last_y, gap_y))
    tail_a = [b.get("a") for b in BEAT[-4:] if isinstance(b.get("a"), int)]
    paused = len(tail_a) >= 3 and len(set(tail_a)) == 1
    if paused and gap_r <= 3000:
        print("  [INFO] BEAT.a 末段恒 %s ⇒ 游戏暂停中：Y 行不再增长、t50c 计时器"
              "冻结属预期；R/W 仍覆盖末帧，无状态盲区。" % tail_a[-1])
    elif gap_r > 3000 or gap_y > 3000:
        print("  [WARN] 末段无状态快照：v52 的 MAX_R=1800 / MAX_Y=200 在长任务中")
        print("         会提前耗尽（P45: f=59730 / f=47593），疲惫瞬间落在盲区。")
        print("         => 该窗口内的字段全 0 不能解读为「路径未走」。")
        print("         v53 已按 30000 帧分段重置配额（需关游戏后部署）。")
    else:
        print("  [OK] R/Y 行覆盖到日志末段，无观测盲区。")

    print("\n=== 权重形状分布 ===")
    for wm, name in ((0, "退回v38"), (1, "非疲k3"), (2, "非疲k4"), (3, "疲惫k3")):
        vv = [x for x in V if x.get("wm") == wm]
        print("  %-8s wm=%d  V=%-4d  wk=%s  st3=%s" %
              (name, wm, len(vv), sorted(set(ival(vv, "wk"))),
               sorted(set(ival(vv, "st3")))))
    if T:
        print("  T 事件（最多 8 条）:")
        for x in T[:8]:
            print("    f=%-7s kind=%-2s reason=%-2s proc=%-3s an=%s" %
                  (x.get("f"), x.get("kind"), x.get("reason"),
                   x.get("proc"), x.get("an")))

    print("\n=== 结论 ===")
    npass = sum(1 for _, ok, _ in checks if ok)
    nfail = len(checks) - npass
    print("  PASS=%d / FAIL=%d / SKIP=%d" % (npass, nfail, len(skips)))
    if crash:
        print("  [CRASH] 日志含 host 异常，本场为中断场；三态样本不完整属预期。")
    if skips:
        print("  -> 本场没有自然疲惫触发（U=0 / T=0 / st2=0）；疲惫态判据")
        print("     已标为 SKIP，不代表插件出错。需在出现流口水的场次复验。")
    if not is_v50:
        print("  -> 旧日志（v49 及以前）：W1 字段缺失属预期，用于验证降级不崩溃。")
    elif nfail == 0:
        print("  -> 规则层全通：5 hook / 零 FATAL / live=1 / W1 形状映射零违例 /")
        print("     W0 proc 门控无误判。W1 已在非疲态生效。")
    else:
        print("  -> 存在 FAIL，按上方条目定位，不要据此推进实机。")
    if is_v51:
        print("  -> v51 上游探针按「根因判据」N/B/C/D 解读；gac=0 是自然静默态（P41）。")
    if is_v52:
        print("  -> v52 看「判定」行：am/amx 是否 >0 决定要不要上 0x9DB54 hook。")
    if is_v54 and not is_v55:
        print("  -> v54 看「G 事件」与「疲惫链路时间线」（该版直接写状态字已被 P48 证伪）。")
    if is_v56:
        print("  -> v56 看「J 行逐次轨迹」：几个动作扣光、d0→d1 倍数、")
        print("     最后一次 a505>=1 / a508=0；再核对 W 行 t505 四态与 t50c 计时器。")
    if is_v55:
        print("  -> v55 看「G 事件」d0!=d1 / a508=0 / a505>=1，以及 W 行时间线：")
        print("     游戏是否把 t505 推进到 >=2 并保持、p41 是否到 5（Stamina_low_Start）。")
        print("  -> W1 疲惫形状 wm=3 / wt>0 由链 I 判据触发，本版应能出现。")
    print("  回退：copy 04_RiseAI\\out\\rai_native_tired_v55.nro 覆盖插件 nro")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "04_RiseAI/out/sim_v56_smoke.txt")
