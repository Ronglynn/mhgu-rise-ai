#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v47 判读：疲惫窗口定时快照 (R 行) + 低动作锚点 (N 行)。

用法: python analyze_v47_tired.py <log>
输出: 锚点段、R 行覆盖、窗口内字段值域差分、候选状态字段、自保护判据。
纯读文件，不修改任何东西。
"""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

INT = {"f", "i", "a", "st", "t4", "ex", "d5", "h1", "e1", "dc", "p3ca",
       "p3be", "low", "log", "dA", "lowhits", "live", "hub", "peak",
       "c0", "c4", "c8", "cf", "fp", "id", "s", "pa", "ps", "v", "ok",
       "m", "m1", "m0c", "m0e", "x", "q", "sel", "act", "beg", "begf",
       "rep", "noalt", "fail"}
FIELDS = ("st", "t4", "ex", "d5", "h1", "e1", "dc", "p3ca", "p3be")


def parse(tail):
    d = {}
    for k, v in re.findall(r"(\w+)=([^\s]+)", tail):
        if k in INT:
            try:
                d[k] = int(v, 0) if v.lower().startswith("0x") else int(v)
            except ValueError:
                d[k] = v
        else:
            d[k] = v
    return d


def main(path):
    p = Path(path)
    lines = p.read_bytes().decode("utf-8", "replace").splitlines()
    rows = defaultdict(list)
    for ln in lines:
        m = re.search(r"\[rai\] (A|BEAT|C|R|N|S|V) (.*)$", ln)
        if m:
            rows[m.group(1)].append(parse(m.group(2)))

    is_v47 = any("RAI v47" in l for l in lines)
    fatal = sum(1 for l in lines if "FATAL" in l)
    live = [x.get("live") for x in rows["BEAT"] if x.get("live") is not None]
    live_ok = bool(live) and all(v == 1 for v in live)
    hub = [x.get("hub") for x in rows["BEAT"] if x.get("hub") is not None]
    hub_ok = set(hub) == {15} if hub else False

    R = [x for x in rows["R"] if isinstance(x.get("f"), int)]
    N = [x for x in rows["N"] if isinstance(x.get("f"), int)]
    A = [x for x in rows["A"] if isinstance(x.get("f"), int)]
    C = [x for x in rows["C"] if isinstance(x.get("f"), int)]
    B = [x for x in rows["BEAT"] if isinstance(x.get("f"), int)
         and isinstance(x.get("a"), int)]
    B.sort(key=lambda z: z["f"])

    qstart = None
    for l in lines:
        m = re.search(r"\[KatSmithy\] f=(\d+) layout \+ GUI\\01_quest\\hud\\hud0", l)
        if m:
            qstart = int(m.group(1))
            break

    print("=== v47 疲惫窗口判读: %s ===" % p.name)
    print("  版本=%s  A=%d C=%d R=%d N=%d BEAT=%d  FATAL=%d  live=%s  hub=%s"
          % ("v47" if is_v47 else "旧日志(回溯)", len(A), len(C), len(R),
             len(N), len(B), fatal, live_ok, sorted(set(hub))[:4]))

    # --- BEAT 低动作段（行为锚点） ---
    wins = [(B[i]["f"], B[i]["a"] - B[i - 1]["a"]) for i in range(1, len(B))]
    lows = [(f, d) for f, d in wins if d <= 1]
    zeros = [(f, d) for f, d in wins if d == 0]
    runs = []
    cur = []
    for f, d in lows:
        if cur and f - cur[-1][0] > 300:
            runs.append(cur)
            cur = []
        cur.append((f, d))
    if cur:
        runs.append(cur)
    print("\n=== 行为锚点 (BEAT 300f 动作增量) ===")
    print("  低活动窗口(<=1)=%d  零动作窗口=%d  连续段=%d" %
          (len(lows), len(zeros), len(runs)))
    for r in runs[:6]:
        f0, f1 = r[0][0] - 300, r[-1][0]
        mins = ((f0 - qstart) / 3600.0) if qstart else None
        print("    f=%d..%d  时长=%.1fs  窗口数=%d  dA=%s%s" %
              (f0, f1, (f1 - f0) / 60.0, len(r), [d for _, d in r][:12],
               ("  任务内≈%.2f 分钟" % mins) if mins is not None else ""))
    # 排除加载期（qstart 前/刚进任务）与过短段，只保留真正的疲惫窗口
    anchors = [(r[0][0] - 300, r[-1][0]) for r in runs if len(r) >= 2]
    if qstart:
        filt = [(a, b) for a, b in anchors
                if a >= qstart + 300 and (b - a) >= 600]
        if filt:
            anchors = filt
    if not anchors and zeros:
        anchors = [(zeros[0][0] - 300, zeros[-1][0])]

    # --- N 行锚点 ---
    print("\n=== N 行自动锚点 ===")
    if N:
        for x in N[:10]:
            print("  f=%-7s kind=%-10s dA=%-3s lowhits=%-3s a=%s" %
                  (x.get("f"), x.get("kind"), x.get("dA"),
                   x.get("lowhits"), x.get("a")))
    else:
        print("  (无 N 行：旧日志或本场未出现连续低活动)")

    # --- 暂停冻结检测（P22）：连续 >=8 条 R 行所有字段完全相同 ---
    freeze = None
    freeze_end = None
    run = 1
    R.sort(key=lambda z: z["f"])
    for i in range(1, len(R)):
        if all(R[i].get(k) == R[i - 1].get(k) for k in FIELDS):
            run += 1
            if run >= 8 and freeze is None:
                freeze = R[i - run + 1]["f"]
        else:
            if freeze is not None and freeze_end is None:
                freeze_end = R[i - 1]["f"]
            run = 1

    # --- R 行覆盖 ---
    print("\n=== R 行定时快照覆盖 ===")
    if freeze:
        nfr = sum(1 for x in R if x["f"] >= freeze
                  and (freeze_end is None or x["f"] <= freeze_end))
        print("  [!] 暂停冻结段 f=%d..%s：%d 条 R 行 9 个字段全部相同"
              "（forge_onUpdate 不冻结、游戏逻辑冻结）⇒ 该段不能当疲惫状态样本"
              % (freeze, freeze_end if freeze_end else "末", nfr))
    if R:
        rf = [x["f"] for x in R]
        print("  R=%d  f=%d..%d  主怪槽分布=%s" %
              (len(R), min(rf), max(rf),
               Counter(x.get("mon") for x in R).most_common(5)))
        covered = 0
        for a, b in anchors:
            n = sum(1 for f in rf if a <= f <= b)
            covered += n
            print("  锚点 f=%d..%d 内 R 行=%d 条%s" %
                  (a, b, n, "  <-- 覆盖成功" if n >= 3 else "  <-- 覆盖不足"))
    else:
        print("  R=0（本版未启用定时快照）")

    # --- 窗口内字段值域差分 ---
    print("\n=== 窗口内字段值域差分（候选状态字段） ===")
    if R and anchors:
        if freeze:
            # 暂停冻结：以「冻结前最后一个 R 行字段突变点」为状态切换锚点，
            # inside = 突变点..冻结前，outside = 突变点之前（冻结段整体排除）。
            changes, multi = [], []
            for i in range(1, len(R)):
                if R[i]["f"] >= freeze:
                    break
                ndiff = sum(1 for k in FIELDS if R[i].get(k) != R[i - 1].get(k))
                if ndiff:
                    changes.append(R[i]["f"])
                    if ndiff >= 3:
                        multi.append(R[i]["f"])
            # 优先取「多字段同时突变」点（状态切换），避免把噪声计时器的
            # 单点变化当成锚点。
            cut = multi[-1] if multi else (changes[-1] if changes else min(anchors)[0])
            print("  [anchor] 用 R 行突变点 f=%d 作状态切换锚点（冻结段已排除）" % cut)
            inside = [x for x in R if cut <= x["f"] < freeze]
            outside = [x for x in R if x["f"] < cut]
        else:
            win = set()
            for a, b in anchors:
                win |= {x["f"] for x in R if a <= x["f"] <= b}
            inside = [x for x in R if x["f"] in win]
            # 基线 = 锚点前 + 锚点结束后 900 帧（避开状态恢复的过渡样本）
            a0, b0 = min(win), max(win)
            outside = [x for x in R if x["f"] < a0 or x["f"] > b0 + 900]
            if not outside:
                outside = [x for x in R if x["f"] < a0]
        outvals = {k: {x.get(k) for x in outside if x.get(k) is not None}
                   for k in FIELDS}
        invals = {k: {x.get(k) for x in inside if x.get(k) is not None}
                  for k in FIELDS}
        cand = []
        for k in FIELDS:
            new = invals[k] - outvals[k]
            print("  %-5s 窗口外=%-24s 窗口内=%-24s 新增值=%s" %
                  (k, str(sorted(outvals[k], key=str)[:8]),
                   str(sorted(invals[k], key=str)[:8]),
                   sorted(new, key=str)[:8] if new else "-"))
            if new:
                cand.append((k, sorted(new, key=str)[:8]))
        print("  候选状态字段(窗口内出现新值): %s" %
              (", ".join("%s=%s" % (k, v) for k, v in cand) if cand else "无"))
    else:
        print("  (无 R 行或无可信锚点，无法差分)")
        cand = []

    # --- 判据 ---
    P = []
    def add(name, ok, note=""):
        P.append(ok)
        print("  [%s] %s %s" % ("PASS" if ok else "FAIL", name, note))

    print("\n=== 判据 ===")
    add("v47 banner", is_v47, "banner=%s" % is_v47)
    add("零 FATAL", fatal == 0, "FATAL=%d" % fatal)
    add("live=1 / hub=15", live_ok and hub_ok, "live=%s hub=%s" % (live_ok, sorted(set(hub))[:4]))
    add("存在低动作/零动作锚点段", len(anchors) > 0, "锚点段=%d" % len(anchors))
    add("R 行覆盖锚点段 (>=3 条/段)",
        bool(R) and all(sum(1 for x in R if a <= x["f"] <= b) >= 3
                        for a, b in anchors) if anchors else False,
        "R=%d 覆盖=%d" % (len(R), covered if R else 0))
    main_anchor = max(anchors, key=lambda z: z[1] - z[0])[0] if anchors else 0
    add("C 行配额未被早期噪声吃光",
        is_v47 or (not C) or (max(x["f"] for x in C) >= main_anchor),
        "C=%d 末帧=%s 主锚点=%s" %
        (len(C), max((x["f"] for x in C), default=0), main_anchor))
    add("窗口内出现候选状态字段", len(cand) > 0,
        "候选=%s" % [k for k, _ in cand])
    print("\n  结论：PASS=%d FAIL=%d" % (sum(P), len(P) - sum(P)))

    if not anchors:
        print("  -> 本场没有出现低动作/零动作段，无法定位疲惫窗口。")
    elif not R:
        print("  -> 零动作段存在但没有任何状态快照（旧版 C/A 行依赖动作事件，"
              "配额耗尽后为空）。这正是 v47 要修复的失败模式。")
    elif cand:
        print("  -> **已捕获疲惫窗口字段变化**：候选字段如上。"
              "对照用户口述流口水时刻后即可定案状态字，随后进 3 状态权重层。")
    else:
        print("  -> R 行覆盖到了锚点段，但所有候选字段值域都没有新增值："
              "疲惫状态字不在本版观测的偏移集合内，需扩大扫描范围。")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: analyze_v47_tired.py <log>")
        sys.exit(2)
    main(sys.argv[1])
