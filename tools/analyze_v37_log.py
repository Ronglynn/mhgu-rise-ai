#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""analyze_v37_log.py — v37 实机判据（加权抽选层「否决后重抽」）

用法：python 04_RiseAI/tools/analyze_v37_log.py 02_Workspace/game_p54.txt

判据三层：
  安全：零 FATAL / hub=15 / live=1 全程 / 正常结算
  机制：m1>0 / sel>0 / beg>0 / ok>0 / p5∈[0,99]（rand%100）
  效果：v 显著高于 v36 的 2 / rd>0（重抽生效）/ V.nr∈(0,256) /
        n1 相对 rep 下降 / A 等距采样覆盖全场 / 分轨 S 行一致
非 v37 日志自动降级为冒烟模式（不把缺失字段判 FAIL）。
"""
import sys, re, json, collections, os

HEX = {"mon", "sp", "w73", "ip", "w0", "w1", "first", "blk", "pick", "sig", "psig"}
A_EVERY = 4

INT = {"f", "n", "op", "md", "mode", "sub", "p5", "ret", "nc", "d", "delta", "nr",
       "live", "log", "k", "why", "id", "a", "s", "pa", "ps", "st", "r1", "r2", "r3",
       "m", "m1", "m0c", "m0e", "x", "q", "sel", "act", "beg", "begf", "ki", "sw",
       "rep", "v", "noalt", "fail", "ok", "peak", "hub", "depth", "rd",
       "e1", "e0", "r1n", "r0", "n1", "n0", "v1", "v0", "a2", "last"}


def parse(s):
    d = {}
    for k, v in re.findall(r"(\w+)=(\S+)", s):
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
    raw = open(path, "rb").read().decode("utf-8", "replace")
    lines = raw.splitlines()
    rows = collections.defaultdict(list)
    for ln in lines:
        m = re.search(r"\[rai\] (.*)$", ln)
        if not m: continue
        s = m.group(1).strip()
        for tag in ("BEAT", "S", "V", "K", "E", "M", "X", "Q", "A", "SITE", "INSTALL", "SKIP", "MON"):
            if s.startswith(tag + " ") or s == tag:
                d = parse(s)
                if tag in ("V", "K", "E", "S", "M", "X", "Q", "A", "BEAT") and "f" not in d:
                    break
                rows[tag].append(d)
                break

    is_v37 = any("RAI v37" in l for l in lines)
    fatal = sum(1 for l in lines if "FATAL" in l)
    checks = []

    def add(name, ok, detail=""):
        checks.append((name, None if not is_v37 else bool(ok), detail))

    print(f"=== v37 判据：{os.path.basename(path)} ===")
    print(f"  版本={'v37' if is_v37 else '旧日志 → 冒烟模式'}  FATAL={fatal}  行数={len(lines)}")
    B, S, V, K, E, A = rows["BEAT"], rows["S"], rows["V"], rows["K"], rows["E"], rows["A"]
    last = B[-1] if B else {}
    slast = S[-1] if S else {}
    print(f"  BEAT={len(B)} S={len(S)} V={len(V)} K={len(K)} E={len(E)} A={len(A)}")
    print()

    add("零 FATAL", fatal == 0, f"FATAL={fatal}")
    site_lines = [l for l in lines if "[rai] SITE" in l]
    add("SITE matcher 首字 E92D4FF0",
        bool(site_lines) and "E92D4FF0" in site_lines[0],
        site_lines[0].strip()[:140] if site_lines else "none")
    add("4 hook 全装（hub=15）", ("hubMask=15" in raw) or (last.get("hub") == 15),
        f"hubMask={'hubMask=15' in raw} BEAT.hub={last.get('hub')}")
    add("无 SKIP", len(rows["SKIP"]) == 0, f"SKIP={len(rows['SKIP'])}")
    live = [x.get("live") for x in B if "live" in x]
    add("live=1 全程", all(v == 1 for v in live) if live else False,
        f"末 6={live[-6:] if live else 'n/a'}")

    m1 = last.get("m1", 0); m0c = last.get("m0c", 0)
    sel = last.get("sel", 0); act = last.get("act", 0)
    beg = last.get("beg", 0); begf = last.get("begf", 0)
    ok = last.get("ok", 0); fail = last.get("fail", 0)
    rep = last.get("rep", 0); v = last.get("v", 0); noalt = last.get("noalt", 0)
    add("m1>0（加权抽选活跃）", m1 > 0, f"m1={m1}  m0c(副轨仅统计)={m0c}")
    add("sel / act / beg 有效", sel > 0 and act > 0 and beg > 0 and begf <= max(2, beg // 10),
        f"sel={sel} act={act} beg={beg} begf={begf}")
    add("ok>0（解析成功）", ok > 0, f"ok={ok} fail={fail}")

    # 核心：规则是否真的生效
    add("**v>2（高于 v36 的 2 次）**", v > 2,
        f"v={v}  改写率={100 * v / max(sel, 1):.1f}%（v36 P8 为 2/551=0.36%）")
    add("rd>0（否决后重抽生效）", slast.get("rd", 0) > 0 if S else False,
        f"S.rd={slast.get('rd', 0)}  S.v1={slast.get('v1', 0)}  S.n1={slast.get('n1', 0)}")
    add("noalt 相对 v36(95%) 下降",
        (noalt / max(rep, 1) < 0.8) if rep else False,
        f"noalt={noalt}/rep={rep} = {100 * noalt / max(rep, 1):.1f}%（v36 P8: 38/40=95%）")

    bad_nr = [x for x in V if not (isinstance(x.get("nr"), int) and 0 < x["nr"] < 256)]
    add("V.nr ∈ (0,256)", len(bad_nr) == 0 if V else False, f"异常 {len(bad_nr)}/{len(V)}")
    p5s = [x.get("p5") for x in V if isinstance(x.get("p5"), int)]
    add("mode1 的 p5 ∈ [0,99]", all(0 <= p < 100 for p in p5s) if p5s else False,
        f"样例={p5s[:10]}")
    rds = [x for x in V if x.get("rd") == 1]
    print(f"\nV 行：总数 {len(V)}，其中重抽路径 rd=1 的 {len(rds)} 条")
    if rds:
        print(f"  rd=1 的 nr 分布={collections.Counter(x.get('nr') for x in rds).most_common(8)}")
        print(f"  rd=1 的 sw 分布={collections.Counter(x.get('sw') for x in rds).most_common(8)}")
    kd = collections.Counter(x.get("d") for x in V)
    print(f"V.d 分布：{kd.most_common(8)}")
    kw = collections.Counter(x.get("why") for x in K)
    print(f"K.why 分布：{kw.most_common(8)}   K.nc 分布：{collections.Counter(x.get('nc') for x in K).most_common(8)}")
    if E:
        print(f"E 行（空签名池结构）：nc={collections.Counter(x.get('nc') for x in E).most_common(6)}  "
              f"sw={collections.Counter(x.get('sw') for x in E).most_common(6)}")
    print(f"S 末行：{slast}")

    mons = collections.Counter(x.get("mon") for x in V)
    add("跨怪覆盖", len(mons) >= 1 if V else False,
        f"mon 数={len(mons)}  {[(hex(k) if isinstance(k, int) else k, n) for k, n in mons.most_common(5)]}")

    # A 等距采样：覆盖全场 + 各段均匀
    afs = [x["f"] for x in A if isinstance(x.get("f"), int)]
    last_f = last.get("f", 0)
    if afs:
        segs = collections.Counter(x // 3000 for x in afs)
        occ = [s for s in range(0, (last_f // 3000) + 1)]
        miss = [s for s in occ if segs.get(s, 0) == 0 and s >= 1]
        print(f"\nA 等距采样：n={len(A)} f={min(afs)}..{max(afs)} 末BEAT={last_f} "
              f"覆盖={100 * max(afs) / max(last_f, 1):.1f}%")
        print(f"  按 3000 帧段：{sorted(segs.items())}  后半场空段={miss}")
        add("A 采样覆盖后 1/4 场", max(afs) >= last_f * 0.75 if last_f else True,
            f"末A={max(afs)} / 末BEAT={last_f}")
        # A 是「每 4 个 0xAFF40 事件记 1 条」的**事件等距**抽样，不是时间等距。
        # 因此空段本身不是缺陷：只有当该段 BEAT.a 仍有 >=4 次动作开始时才算漏采。
        seg_da = collections.defaultdict(int)
        for i in range(1, len(B)):
            # BEAT 的 Δa 是「过去 300 帧」的增量，须归属上一 BEAT 所在段，
            # 否则段边界会错位一个窗口（P9 段 5 因此被误判）。
            seg_da[B[i - 1]["f"] // 3000] += B[i]["a"] - B[i - 1]["a"]
        bad_segs = [g for g in miss if seg_da.get(g, 0) >= 4]
        add("A 事件等距（空段确实无动作开始）", len(bad_segs) == 0,
            f"空段={miss}  其中仍有动作的段={bad_segs}")
        add("A 总行数 ≈ a_N/4", abs(len(A) - last.get("a", 0) // A_EVERY) <= 1,
            f"A={len(A)}  a_N/4={last.get('a',0)//A_EVERY}")
    if A:
        ids = [x.get("id") for x in A]
        repa = sum(1 for i in range(1, len(ids)) if ids[i] == ids[i - 1])
        print(f"  A 连续同 id：{repa}/{max(len(ids)-1,1)} = {100*repa/max(len(ids)-1,1):.1f}%"
              f"（等距抽样下仅供体感参考）")

    print("\n=== 判据明细 ===")
    npass = nfail = nskip = 0
    for name, ok_, detail in checks:
        if ok_ is None: tag, nskip = "SKIP", nskip + 1
        elif ok_: tag, npass = "PASS", npass + 1
        else: tag, nfail = "FAIL", nfail + 1
        print(f"  [{tag}] {name}  —  {detail}")
    print(f"\n结论：PASS={npass} FAIL={nfail} SKIP={nskip}  " +
          ("全部通过 -> 否决后重抽生效，进入体感评估（连续同招 / 发呆 / 结算）"
           if nfail == 0 and fatal == 0 and is_v37 else
           "冒烟完成（旧日志）" if not is_v37 else
           "存在失败项 -> 看 S/V/K 行，必要时回退 v36 或 v31 只读"))

    out = {"rows": {k: rows[k] for k in rows},
           "verdict": {"pass": npass, "fail": nfail, "skip": nskip, "fatal": fatal,
                       "is_v37": is_v37, "last": last, "slast": slast}}
    op = os.path.join(os.path.dirname(os.path.abspath(path)), "v37_redraw_events.json")
    try:
        with open(op, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print(f"  events -> {op}")
    except Exception as e:
        print(f"  events 写入跳过：{e}")
    return 0 if (nfail == 0 or not is_v37) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "02_Workspace/game_p54.txt"))
