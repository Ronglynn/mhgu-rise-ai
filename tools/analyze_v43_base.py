#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""analyze_v43_base.py — v43「em 基址自洽扫描」判读

用法：python 04_RiseAI/tools/analyze_v43_base.py 02_Workspace/game_p54_lite.txt

v43 纯只读（ZERO writes），目标：定位疲惫管线真正用的 em 对象。
  P 行  a0±64KB 结构自洽扫描命中（em 地址、delta = em - a0、c0/c4/cf/act）
  D 行  按 delta 每帧读 em+0xCAC0 / +0xCAC4 / +0xCBF1 + act+0x518 / +0x408，
        只在离散状态指纹变化时记录

判据：找到 delta（strict>0）→ D 行覆盖全场 → 状态字段出现 2/3（疲惫）
      → 对照 BEAT 零动作锚点（自然疲劳约任务内 15.3 分钟）。
非 v43 日志自动降级冒烟，不把缺失字段判 FAIL。
"""
import sys, re, collections

HEX = {"mon", "em", "act", "sp", "ip", "w0", "w1", "first", "blk", "pick",
       "sig", "psig", "fp"}
INT = {"f", "i", "delta", "best_delta", "strict", "loose", "c0", "c4", "c8",
       "cf", "e1", "dc", "h1", "st", "t4", "ex", "log", "a", "live", "hub",
       "c0b", "c4b", "t4b", "c0a", "c4a", "t4a", "dt", "step", "site", "first",
       "r1", "r1b", "r1a", "r2", "change", "forced", "n", "stb", "sta",
       "m", "m1", "v", "rep", "noalt", "fail", "ok", "peak", "sel", "beg",
       "begf", "x", "q", "rd", "b1", "p2"}


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


def main(path):
    lines = open(path, "rb").read().decode("utf-8", "replace").splitlines()
    rows = collections.defaultdict(list)
    for ln in lines:
        m = re.search(r"\[rai\] (A|V|BEAT|S|K|E|C|P|D|F|W|G|T|Y) (.*)$", ln)
        if m:
            d = parse(m.group(2))
            if " SUMMARY " in ln: d["summary"] = 1
            rows[m.group(1)].append(d)
    A, C, B, P, D = (rows[k] for k in ("A", "C", "BEAT", "P", "D"))
    hits = [x for x in P if "em" in x]
    summary = [x for x in P if x.get("summary")]
    is_v46 = any("RAI v46" in l for l in lines)
    is_v45 = is_v46 or any("RAI v45" in l for l in lines)
    is_v44 = is_v45 or any("RAI v44" in l for l in lines)
    is_v43 = is_v44 or any("RAI v43" in l for l in lines)
    fatal = sum(1 for l in lines if "FATAL" in l)
    ok, bad = [], []

    def add(name, cond, detail):
        (ok if cond else bad).append((name, detail))

    print("=== v43 em 基址扫描判读：%s ===" % path)
    print("  版本=%s  FATAL=%d  P命中=%d P汇总=%d D=%d A=%d C=%d BEAT=%d" %
          ("v46" if is_v46 else ("v45" if is_v45 else ("v44" if is_v44 else ("v43" if is_v43 else "旧日志(冒烟)"))), fatal,
           len(hits), len(summary), len(D), len(A), len(C), len(B)))
    if not is_v43:
        print("  非 v43 日志 -> 冒烟完成，不做基址判读。")
        return 0

    add("零 FATAL", fatal == 0, "FATAL=%d" % fatal)
    Fh = [x for x in rows["F"] if "em" in x]
    W = rows["W"]
    if is_v46:
        Yh = [x for x in rows["Y"] if x.get("kind") == "TRIG"]
        Yhold = [x for x in rows["Y"] if x.get("kind") == "HOLD"]
        add("Y 行 TRIG 恰好 1 条（一次触发）", len(Yh) == 1, "TRIG=%d" % len(Yh))
        add("写后回读 st=2", any(x.get("sta") == 2 for x in Yh),
            "sta=%s" % [x.get("sta") for x in Yh])
        add("HOLD 行 >=5 且 st 保持 2",
            len(Yhold) >= 5 and all(x.get("sta") == 2 for x in Yhold),
            "HOLD=%d sta集合=%s" % (len(Yhold), sorted({x.get("sta") for x in Yhold})))
        add("A 行出现 st=2", any(x.get("st") == 2 for x in A),
            "A.st=%s" % sorted({x.get("st") for x in A})[:8])
    elif is_v44:
        skipped = any("[rai] F " in l and "SKIP" in l for l in lines)
        if is_v45:
            add("T 行存在（h_tired 被调用）", len(rows["T"]) > 0,
                "T=%d" % len(rows["T"]))
            add("INSTALL h_tired 成功", any("INSTALL h_tired" in l for l in lines),
                "INSTALL 行=%d" % sum(1 for l in lines if "INSTALL h_tired" in l))
        add("F 行恰好 1 条（一次触发）", len(Fh) == 1, "F=%d SKIP=%s" % (len(Fh), skipped))
        add("调用后 em+0xCAC4=2", any(x.get("c4a") == 2 for x in Fh),
            "c4a=%s" % [x.get("c4a") for x in Fh])
        add("W 行回读 >=5 且疲惫状态保持",
            len(W) >= 5 and any(x.get("c4") == 2 for x in W),
            "W=%d c4集合=%s" % (len(W), sorted({x.get("c4") for x in W if isinstance(x.get("c4"), int)})))
        add("疲惫时长脱离 0xFFFF",
            any(isinstance(x.get("t4"), int) and 0 < x.get("t4") < 65535 for x in W),
            "t4集合=%s" % sorted({x.get("t4") for x in W if isinstance(x.get("t4"), int)})[:8])
    else:
        add("零游戏侧写入 (无 F/W/G 行)",
            not (rows["F"] or rows["W"] or rows["G"]),
            "F=%d W=%d G=%d" % (len(rows["F"]), len(rows["W"]), len(rows["G"])))

    # --- P 行：em 基址 ---
    print("\n=== P 行（em 候选：结构自洽命中）===")
    for x in hits[:20]:
        print("  f=%-7s i=%-2s mon=%-10s em=%-10s delta=%-8s c0=%-4s c4=%-4s cf=%-3s act=%-10s strict=%s loose=%s" %
              (x.get("f"), x.get("i"), x.get("mon"), x.get("em"),
               x.get("delta"), x.get("c0"), x.get("c4"), x.get("cf"),
               x.get("act"), x.get("strict"), x.get("loose")))
    for x in summary[:10]:
        print("  SUMMARY f=%-7s i=%-2s mon=%-10s strict=%-4s loose=%-4s best_delta=%s" %
              (x.get("f"), x.get("i"), x.get("mon"), x.get("strict"),
               x.get("loose"), x.get("best_delta")))
    deltas = collections.Counter(x.get("delta") for x in hits if isinstance(x.get("delta"), int))
    strict_total = sum(x.get("strict", 0) for x in summary if isinstance(x.get("strict"), int))
    print("  delta 分布=%s  strict 合计=%s" % (deltas.most_common(8), strict_total))
    if not is_v46:
        add("找到 em 基址 (strict>0 且有 delta)", strict_total > 0 and len(deltas) > 0,
            "strict=%s delta种类=%d" % (strict_total, len(deltas)))
        add("delta 跨槽一致（固定偏移）", len(deltas) == 1,
            "delta 集合=%s" % sorted(deltas)[:8])
    else:
        print("  （v46 不依赖 em 扫描；P/D 行仅作对照）")

    # --- 任务时间锚点 ---
    qstart = None
    for ln in lines:
        m = re.search(r"\[KatSmithy\] f=(\d+) layout \+ GUI\\01_quest\\hud\\hud0", ln)
        if m:
            qstart = int(m.group(1)); break
    if qstart is None and B:
        qstart = B[0]["f"]
    last_f = B[-1]["f"] if B else 0
    print("\n=== 任务时间 ===")
    print("  qstart=%s  末帧=%s  60fps 全场≈%.1f 分钟" %
          (qstart, last_f, ((last_f - qstart) / 3600.0) if (qstart and last_f) else 0.0))

    # --- D 行：真实状态字段 ---
    print("\n=== D 行（em 真实状态字段；按 fp 连续段）===")
    for x in D[:14]:
        print("  f=%-7s i=%-2s mon=%-10s em=%-10s delta=%-8s c0=%-4s c4=%-4s cf=%-3s st=%-3s t4=%-6s fp=%s" %
              (x.get("f"), x.get("i"), x.get("mon"), x.get("em"),
               x.get("delta"), x.get("c0"), x.get("c4"), x.get("cf"),
               x.get("st"), x.get("t4"), x.get("fp")))
    df1 = D[-1]["f"] if D else 0
    gap = last_f - df1
    cover = (df1 / last_f) if last_f else 0
    print("  D=%d  f=%s..%s  覆盖=%.1f%%  末段间隔=%d 帧" %
          (len(D), D[0]["f"] if D else 0, df1, cover * 100, gap))
    add("D 行覆盖全场 >80% 或末段无状态变化", cover > 0.8 or gap < 12000,
        "覆盖=%.1f%% gap=%d" % (cover * 100, gap))
    add("D 行存在", len(D) > 0, "D=%d" % len(D))

    c0s = collections.Counter(x.get("c0") for x in D if isinstance(x.get("c0"), int))
    c4s = collections.Counter(x.get("c4") for x in D if isinstance(x.get("c4"), int))
    t4s = collections.Counter(x.get("t4") for x in D if isinstance(x.get("t4"), int))
    print("  D.c0=%s  D.c4=%s  D.t4=%s" %
          (c0s.most_common(6), c4s.most_common(6), t4s.most_common(6)))
    tired_seen = any(v in (2, 3) for v in c0s) or any(v == 2 for v in c4s)
    print("  疲惫状态出现 (c0=2/3 或 c4=2)：%s" % tired_seen)

    # --- BEAT 零动作锚点 ---
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
    print("\n=== BEAT 零动作锚点（自然疲劳≈任务内 15.3 分钟）===")
    for fr0, fr1, n in runs:
        mins = ((fr0 - qstart) / 3600.0, (fr1 - qstart) / 3600.0) if qstart else (0, 0)
        near = [x for x in D if fr0 - 600 <= x["f"] <= fr1 + 600]
        print("  f=%6d..%-6d 窗口=%d 任务内≈%5.1f..%5.1f 分钟 附近 D 行=%d" %
              (fr0, fr1, n, mins[0], mins[1], len(near)))
        for x in near[:6]:
            print("    f=%-7d c0=%-4s c4=%-4s cf=%-3s st=%-3s t4=%s" %
                  (x["f"], x.get("c0"), x.get("c4"), x.get("cf"),
                   x.get("st"), x.get("t4")))
    if not runs:
        print("  本场无零动作段")

    # --- 自保护 ---
    live = B[-1].get("live") if B else None
    add("live=1 全场", live == 1, "末 BEAT live=%s" % live)
    add("无 hook SKIP", not any("SKIP h_" in l for l in lines),
        "SKIP=%d" % sum(1 for l in lines if "SKIP h_" in l))

    # --- v44 F/W 摘要 ---
    if is_v44:
        print("\n=== F / W / T / Y 行（强制疲惫触发与回读）===")
        for x in rows["Y"][:14]:
            print("  Y f=%-7s dt=%-5s kind=%-5s act=%-10s stb=%-3s sta=%-3s t4=%-6s n=%s" %
                  (x.get("f"), x.get("dt"), x.get("kind"), x.get("act"),
                   x.get("stb"), x.get("sta"), x.get("t4"), x.get("n")))
        for x in rows["T"][:6]:
            print("  T f=%-7s em=%-10s r1=%-3s r2=%-3s forced=%-3s change=%s" %
                  (x.get("f"), x.get("em"), x.get("r1"), x.get("r2"),
                   x.get("forced"), x.get("change")))
        for x in Fh:
            print("  f=%-7s i=%-2s mon=%-10s em=%-10s delta=%-8s c0b=%-4s c4b=%-4s t4b=%-6s c0a=%-4s c4a=%-4s t4a=%s" %
                  (x.get("f"), x.get("i"), x.get("mon"), x.get("em"), x.get("delta"),
                   x.get("c0b"), x.get("c4b"), x.get("t4b"), x.get("c0a"),
                   x.get("c4a"), x.get("t4a")))
        for x in W[:12]:
            print("  W f=%-7s dt=%-5s c0=%-4s c4=%-4s t4=%s" %
                  (x.get("f"), x.get("dt"), x.get("c0"), x.get("c4"), x.get("t4")))

    # --- 结论 ---
    print("\n=== 判读结论 ===")
    if is_v46:
        Yh = [x for x in rows["Y"] if x.get("kind") == "TRIG"]
        if Yh and any(x.get("sta") == 2 for x in Yh):
            print("  -> **字段层写入已落地**：act+0x518 被写成 2，Y 行 HOLD 回读保持。"
                  "下一步看用户体感：若怪物仍无疲劳动画，则 st=2 只是判定标志，"
                  "需另找疲惫动画字段；若出现流口水/喘气，则可定案。")
        else:
            print("  -> 未触发或写入未落地（看 Y 行 TRIG / A 行 st）；"
                  "插件保持只读回退。")
    elif is_v45:
        if Fh and any(x.get("c4a") == 2 for x in Fh):
            print("  -> **强制疲惫生效（hook 改参）**：h_tired 把首次 r1=1 改成 2，"
                  "游戏自己走完疲惫分支，em+0xCAC4=2、act+0x408 脱离 0xFFFF。"
                  "可定案状态字并进 3 状态权重层。")
        elif not rows["T"]:
            print("  -> h_tired 从未被调用（0x1068DD8 没有走这条路）；"
                  "需改 hook 上游 0x1069D8C / 0x873C 或换触发点。")
        else:
            print("  -> hook 被调用但 r1 从未为 1 或 c4a 未变 2；对照 T 行 r1 值再定。")
    elif is_v44:
        if Fh and any(x.get("c4a") == 2 for x in Fh):
            print("  -> **强制疲惫生效**：游戏自己的 0x1068DD8(em,2,0) 把 "
                  "em+0xCAC4 置 2 并写 act+0x408；W/D 行显示状态被保持。"
                  "可据此定案状态字并进 3 状态权重层。")
        elif any("[rai] F " in l and "SKIP" in l for l in lines):
            print("  -> 疲惫入口运行时首字不符（解释器跳板/版本差异）⇒ 插件已安全 SKIP，"
                  "未调用；回退 v43 纯只读，需另找调用点。")
        else:
            print("  -> 未找到合法 em 或未满足触发条件（看 P 行 strict / TIRED SITE）；"
                  "本轮未强制，插件保持只读。")
    elif strict_total == 0 or not deltas:
        print("  -> 未找到自洽 em 基址：需放宽判据（去掉 cf/c4 约束）或扩大扫描范围。")
    elif tired_seen:
        print("  -> **状态字定案**：em = mon + %s（delta=%s），`em+0xCAC0` / "
              "`em+0xCAC4` 随疲惫变化。可进入 3 状态权重层。" %
              (sorted(deltas)[0], sorted(deltas)))
    elif qstart and last_f and (last_f - qstart) < 15 * 3600:
        print("  -> em 基址已定案（delta=%s），但本场不足 15 分钟、未见疲惫；"
              "需打满一场取自然疲劳段的值域。" % sorted(deltas))
    else:
        print("  -> em 基址已定案（delta=%s），但 D 行未见 2/3；"
              "对照用户口述疲劳时刻与锚点段再判。" % sorted(deltas))

    print("\n=== 判据 ===")
    for name, detail in ok: print("  PASS  %s : %s" % (name, detail))
    for name, detail in bad: print("  FAIL  %s : %s" % (name, detail))
    print("  结论：PASS=%d FAIL=%d -> %s" %
          (len(ok), len(bad), "判读链路可用" if not bad else "需排查上述项"))
    print("  提示：请告知『怪物变疲劳』的大致任务内时刻，用于对照 D 行状态段。")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1
                  else "02_Workspace/game_p54_lite.txt"))
