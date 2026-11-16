#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""analyze_v42_force.py — v42「减气蓄积写入 + 状态扫描」判读

用法：python 04_RiseAI/tools/analyze_v42_force.py 02_Workspace/game_p54_lite.txt

v42 = v41 全部只读改进（8 槽多怪 / 离散状态指纹 / c0,t4 / 配额 800+400）
      + 恢复 `act+0x5D82 = 1000` 的**有界写入**：
  F 行  一次性写入事件（含真实回读 ex1、槽号 i、动作计数 an）
  W 行  写入后 +1/2/4/8/16/32/64/96/120/180/300/600 帧的只读轨迹
        （记录「补写前」的 ex，故能看出游戏是否把蓄积清零/衰减）
  G 行  维持窗口早停：c0==2/3 或 t4!=0 时认为状态机已消费

判读目标（一轮定案，缺一不可）：
  1. 写入是否落地        F.ex1 非 0、W.ex 出现非 0
  2. 对象是否统一        F.mon == W.mon，且该 mon 出现在 C 行扫描槽
  3. 是否驱动状态机      G 行 / C 行 c0∈{2,3} / W 行 c0∈{2,3} 或 t4!=0
  4. 是否提前疲惫        BEAT 全量零动作锚点相对任务开始 < 15 分钟
                        （P11 自然疲劳锚点是 15.3~15.5 分钟）

非 v42 日志自动降级为冒烟模式，不把缺失字段判 FAIL。
"""
import sys, re, collections

HEX = {"mon", "act", "sp", "ip", "w0", "w1", "first", "blk", "pick", "sig",
       "psig", "fp"}
INT = {"f", "n", "op", "md", "mode", "sub", "p5", "ret", "nc", "d", "nr",
       "live", "log", "id", "a", "s", "pa", "ps", "st", "r1", "r2", "r3",
       "m", "m1", "m0c", "m0e", "x", "q", "sel", "beg", "begf", "ki", "sw",
       "rep", "v", "noalt", "fail", "ok", "peak", "hub", "depth", "rd", "b1",
       "sw2", "ph", "p2", "c0", "c4", "c8", "cf", "e1", "dc", "h1", "t4",
       "ex", "ex0", "ex1", "i", "an", "forced", "fw", "dt", "step", "done"}


def parse(s):
    d = {}
    for k, v in re.findall(r"(\w+)=(\S+)", s):
        if k == "c4" and re.fullmatch(r"[0-9A-Fa-f]{8}", v):
            d[k] = int(v, 16); continue
        if k in HEX:
            try: d[k] = int(v, 16)
            except ValueError: d[k] = v
        elif k in INT:
            try: d[k] = int(v, 0)
            except ValueError: d[k] = v
        else:
            d[k] = v
    return d


def hx(v):
    return ("%08X" % v) if isinstance(v, int) else str(v)


def main(path):
    lines = open(path, "rb").read().decode("utf-8", "replace").splitlines()
    rows = collections.defaultdict(list)
    for ln in lines:
        m = re.search(r"\[rai\] (A|V|BEAT|S|K|E|C|F|W|G) (.*)$", ln)
        if m:
            rows[m.group(1)].append(parse(m.group(2)))
    A, C, B, F, W, G = (rows[k] for k in ("A", "C", "BEAT", "F", "W", "G"))
    is_v42 = any("RAI v42" in l for l in lines)
    fatal = sum(1 for l in lines if "FATAL" in l)
    ok, bad = [], []

    def add(name, cond, detail):
        (ok if cond else bad).append((name, detail))

    print("=== v42 减气蓄积写入 / 状态扫描判读：%s ===" % path)
    print("  版本=%s  FATAL=%d  F=%d W=%d G=%d A=%d C=%d BEAT=%d" %
          ("v42" if is_v42 else "旧日志(冒烟)", fatal,
           len(F), len(W), len(G), len(A), len(C), len(B)))
    if not is_v42:
        print("  非 v42 日志 -> 冒烟完成，不做写入判读。")
        return 0

    add("零 FATAL", fatal == 0, "FATAL=%d" % fatal)
    add("F 行恰好 1 条（一次触发）", len(F) == 1, "F=%d" % len(F))

    # --- 任务开始锚点 ---
    qstart = None
    for ln in lines:
        m = re.search(r"\[KatSmithy\] f=(\d+) layout \+ GUI\\01_quest\\hud\\hud0", ln)
        if m:
            qstart = int(m.group(1)); break
    if qstart is None and B:
        qstart = B[0]["f"]
    last_f = B[-1]["f"] if B else 0
    print("\n=== 任务时间锚点 ===")
    print("  任务开始 f≈%s   末帧 f=%s   60fps 全场≈%.1f 分钟" %
          (qstart, last_f,
           ((last_f - qstart) / 3600.0) if (qstart and last_f) else 0.0))

    # --- F 行：写入是否落地、时机、对象 ---
    print("\n=== F 行（写入事件）===")
    f0 = F[0] if F else {}
    for x in F:
        print("  f=%-7s i=%-3s an=%-5s mon=%-10s act=%-10s ex0=%-5s ex1=%-5s st=%-3s c0=%-4s t4=%s" %
              (x.get("f"), x.get("i"), x.get("an"), hx(x.get("mon")), hx(x.get("act")),
               x.get("ex0"), x.get("ex1"), x.get("st"), x.get("c0"), x.get("t4")))
    ex1 = f0.get("ex1")
    add("写入真实回读落地 (ex1!=0)", isinstance(ex1, int) and ex1 != 0,
        "ex0=%s ex1=%s（v40 打印的是常量，未验证）" % (f0.get("ex0"), ex1))
    an = f0.get("an")
    add("写入避开加载期 (an>=30)", isinstance(an, int) and an >= 30,
        "A_N=%s（v40 在 f=14563 / 任务 HUD 前一帧写入）" % an)
    if qstart and isinstance(f0.get("f"), int):
        add("写入发生在任务开始之后", f0["f"] > qstart,
            "F.f=%d  qstart=%d" % (f0["f"], qstart))

    # --- W 行：写入后轨迹 ---
    print("\n=== W 行（写入后只读轨迹；ex 是补写前的值）===")
    for x in W:
        print("  f=%-7s dt=%-5s step=%-5s ex=%-6s c0=%-4s cf=%-4s st=%-3s t4=%-6s fw=%-4s done=%s" %
              (x.get("f"), x.get("dt"), x.get("step"), x.get("ex"), x.get("c0"),
               x.get("cf"), x.get("st"), x.get("t4"), x.get("fw"), x.get("done")))
    wex = [x.get("ex") for x in W if isinstance(x.get("ex"), int)]
    wdt = [x.get("dt") for x in W if isinstance(x.get("dt"), int)]
    print("  W.ex 值域=%s  最小/最大 dt=%s/%s" %
          (sorted(set(wex))[:12], min(wdt) if wdt else 0, max(wdt) if wdt else 0))
    add("W 行轨迹完整 (>=8 条且覆盖 >=300 帧)", len(W) >= 8 and (max(wdt) if wdt else 0) >= 300,
        "W=%d 最大 dt=%s" % (len(W), max(wdt) if wdt else 0))
    add("W 行 ex 出现非 0（未被逐帧清零）", any(v != 0 for v in wex),
        "ex 集合=%s" % sorted(set(wex))[:10])
    if F and W:
        fmon, wmon = f0.get("mon"), W[0].get("mon")
        add("写入对象与监控对象同源", fmon == wmon,
            "F.mon=%s  W.mon=%s（v40 写入 0C181390 / 监控 0C220060）" % (hx(fmon), hx(wmon)))
        cmon = set(x.get("mon") for x in C)
        add("写入对象在 C 行扫描槽内", fmon in cmon,
            "C 行 mon 数=%d" % len(cmon))

    # --- G 行 / 状态字段 ---
    print("\n=== G 行 / 状态字段（是否驱动状态机）===")
    for x in G:
        print("  f=%-7s dt=%-5s mon=%-10s c0=%-4s t4=%-6s fw=%s" %
              (x.get("f"), x.get("dt"), hx(x.get("mon")), x.get("c0"),
               x.get("t4"), x.get("fw")))
    c0_w = set(x.get("c0") for x in W if isinstance(x.get("c0"), int))
    c0_c = set(x.get("c0") for x in C if isinstance(x.get("c0"), int))
    t4_w = set(x.get("t4") for x in W if isinstance(x.get("t4"), int))
    t4_c = set(x.get("t4") for x in C if isinstance(x.get("t4"), int))
    # 0xFFFF(65535) 是 act+0x408 的未初始化哨兵，不能当「疲惫时长非零」。
    # v42 暂停场实测 t4 恒 65535 -> G 行在 +1 帧假早停，窗口只写了 1 次。
    def t4_valid(v):
        return isinstance(v, int) and 0 < v < 65535
    c0_state = any(v in (2, 3) for v in c0_w | c0_c)
    t4_state = any(t4_valid(v) for v in t4_w | t4_c)
    g_valid = any(isinstance(x.get("c0"), int) and x.get("c0") in (2, 3)
                  or t4_valid(x.get("t4")) for x in G)
    state = c0_state or t4_state or g_valid
    print("  W.c0=%s  C.c0=%s  W.t4=%s  C.t4=%s" %
          (sorted(c0_w)[:10], sorted(c0_c)[:10], sorted(t4_w)[:10], sorted(t4_c)[:10]))
    add("状态机消费写入 (c0=2,3 / 0<t4<65535)", state,
        "G=%d(有效=%s)  c0∩{2,3}=%s  有效t4=%s  65535=哨兵已排除" %
        (len(G), g_valid, sorted((c0_w | c0_c) & {2, 3}),
         sorted(v for v in (t4_w | t4_c) if t4_valid(v))[:8]))

    # --- BEAT 零动作锚点：是否提前疲惫 ---
    steps = [(B[i]["f"], B[i]["a"] - B[i - 1]["a"]) for i in range(1, len(B))
             if isinstance(B[i].get("a"), int) and isinstance(B[i - 1].get("a"), int)]
    runs, cur = [], []
    for fr, da in steps:
        if da == 0:
            cur.append(fr)
        else:
            if len(cur) >= 3: runs.append((cur[0] - 300, cur[-1], len(cur)))
            cur = []
    if len(cur) >= 3: runs.append((cur[0] - 300, cur[-1], len(cur)))
    if qstart:
        runs = [r for r in runs if r[0] >= qstart]
    print("\n=== BEAT 零动作锚点（疲惫候选；P11 自然疲劳 = 任务内 15.3 分钟）===")
    for fr0, fr1, n in runs:
        mins = ((fr0 - qstart) / 3600.0, (fr1 - qstart) / 3600.0) if qstart else (0, 0)
        print("  f=%6d..%-6d  窗口=%d  任务内≈%5.1f..%5.1f 分钟" % (fr0, fr1, n, mins[0], mins[1]))
    if not runs:
        print("  本场无零动作段")
    quest_len = (last_f - qstart) if (qstart and last_f) else 0
    short = quest_len < 15 * 3600
    early = bool(qstart and any((fr0 - qstart) < 15 * 3600 for fr0, _, _ in runs))
    print("  存在 <15 分钟的零动作段：%s；全场任务时长≈%.1f 分钟%s" %
          (early, quest_len / 3600.0,
           "（不足 15 分钟：短样本，『提前』不构成证据）" if short else ""))

    # --- C 行覆盖 ---
    cf1 = C[-1]["f"] if C else 0
    cover = (cf1 / last_f) if last_f else 0
    print("\n=== C 行覆盖（v41 离散指纹扫描）===")
    print("  C=%d  f=%s..%s  覆盖到末帧 %.1f%%  不同 mon=%d" %
          (len(C), C[0]["f"] if C else 0, cf1, cover * 100,
           len(set(x.get("mon") for x in C))))
    gap = last_f - cf1
    add("C 行覆盖全场 >80% 或末段无状态变化", cover > 0.8 or gap < 12000,
        "覆盖=%.1f%%  末段间隔=%d 帧（离散指纹无变化不出 C 行，暂停时属正常）" %
        (cover * 100, gap))

    # --- 自保护 ---
    live = B[-1].get("live") if B else None
    add("live=1 全场", live == 1, "末 BEAT live=%s" % live)
    add("无 hook SKIP", not any("SKIP h_" in l for l in lines),
        "SKIP 行数=%d" % sum(1 for l in lines if "SKIP h_" in l))

    # --- 结论 ---
    print("\n=== 判读结论 ===")
    if not wex or all(v == 0 for v in wex):
        print("  -> 写入未落地：`act+0x5D82` 被游戏逐帧清零或字段/对象推断有误。"
              "回退 v41 纯只读，停止追减气蓄积。")
    elif wex and len(set(wex)) == 1 and wex[0] > 0 and not state:
        print("  -> **写入落地但游戏完全未消费**：W 行 ex 恒为 %s 且状态字段无响应。"
              "该地址不是活的减气蓄积字段（或对象/基址推断有误）；"
              "`act+0x5D82` 路径证伪，停止追写入。" % wex[0])
    elif state and early and not short:
        print("  -> **写入落地并驱动疲惫**：状态字段被捕获且零动作段早于自然疲劳"
              "（15.3 分钟）。可定案状态字，进入 3 状态权重层。")
    elif state and short:
        print("  -> 状态字段有响应，但本场不足 15 分钟，无法区分强制/自然疲惫；"
              "样本不足，需打满一场。")
    elif state:
        print("  -> 写入落地且状态字段有响应，但未见提前零动作段："
              "状态字可用，强制疲惫的体感证据需与用户口述对照。")
    else:
        print("  -> 写入落地但状态未响应：蓄积被消费却没进疲惫，"
              "或 c0/t4 不是状态字；对照 W 轨迹与用户体感再定。")

    print("\n=== 判据 ===")
    for name, detail in ok: print("  PASS  %s : %s" % (name, detail))
    for name, detail in bad: print("  FAIL  %s : %s" % (name, detail))
    print("  结论：PASS=%d FAIL=%d -> %s" %
          (len(ok), len(bad), "判读链路可用" if not bad else "需排查上述项"))
    print("  提示：请告知『怪物变疲劳』的大致任务内时刻，以及有无反复疲惫/动画错位。")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1
                  else "02_Workspace/game_p54_lite.txt"))
