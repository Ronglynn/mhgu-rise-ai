# -*- coding: utf-8 -*-
"""v50 判读：W1 Rise 池权重层 + W0 疲惫触发门控。

W1：对合格 case 按原权重降序取 top-k，按 Rise 排序形状重分配（和恒 100）后轮盘赌。
  形状 N3[45,32,23] / N4[40,27,20,13] / T3[60,30,10]，非疲 61:39 混合。
  离线对拍：非疲 1.6701 (Rise 1.6705)、疲惫 1.2955 (Rise 1.2984)。
W0：proc<=30 且 0<thr<0x4000；h_exh 已装时只信 ret==1；小怪槽 thr=65535 排除。

用法: python analyze_v50_weight.py <log>
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
       "m0e", "x", "q"}
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
    BEAT = rows["BEAT"]
    is_v50 = any("RAI v50" in l for l in lines)
    fatal = sum(1 for l in lines if "FATAL" in l)
    # 实机行带 "[forge] [INFO]" 前缀，不能用 startswith("[rai]")
    installs = [l.strip() for l in lines if "[rai] INSTALL h_" in l]
    banner = next((l.strip() for l in lines if "RAI v50" in l), "(旧日志)")
    crash = [l.strip() for l in lines
             if "c0000005" in l or "*** exception" in l or "host backtrace" in l]

    print("=== v50 W1 权重层判读 ===")
    print("日志: %s" % path)
    print("banner: %s" % banner[:120])
    print("版本=%s  V=%d T=%d U=%d S=%d R=%d N=%d BEAT=%d  FATAL=%d" %
          ("v50" if is_v50 else "旧日志(降级)", len(V), len(T), len(U),
           len(S), len(R), len(N), len(BEAT), fatal))
    for l in installs[:6]:
        print("  " + l[:120])

    checks = []
    skips = []
    # 一场没有自然疲惫的任务里，疲惫态判据是「样本缺失」而非「规则违例」。
    # P37：v50 雄火龙场 U=0/T=0/st2=0 曾被误报为 6 个 FAIL，现区分 SKIP。
    has_tired = (len(U) > 0 or len(T) > 0
                 or any(x.get("st3") == 2 for x in V))

    def add(name, ok, detail):
        checks.append((name, bool(ok), detail))
        print("  [%s] %-42s %s" % ("PASS" if ok else "FAIL", name, detail))

    def skip(name, detail):
        skips.append((name, detail))
        print("  [SKIP] %-42s %s" % (name, detail))

    # --- 版本 / 安全性 ---
    add("RAI v50 版本横幅", is_v50, banner[:60])
    add("零 FATAL（guest 侧）", fatal == 0, "FATAL=%d" % fatal)
    add("零 host 异常（c0000005）", not crash,
        "异常行=%d %s" % (len(crash), crash[0][:50] if crash else ""))
    n_inst = sum(1 for l in installs if any(h in l for h in
                 ("h_matcher", "h_emc", "h_unify", "h_start_40", "h_exh")))
    add("5 个 hook 全部 INSTALL", n_inst >= 5, "INSTALL=%d" % n_inst)
    add("v48 强制已移除（无 force=1）",
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
        add("W1 非疲形状生效（w3,w4>0）",
            all(isinstance(v, int) and v > 0 for v in w34), "w3/w4=%s" % w34)
        add("d3/skip 恒 0（v49 旋钮已移除）",
            s.get("d3") == 0 and s.get("skip") == 0,
            "d3=%s skip=%s" % (s.get("d3"), s.get("skip")))
    else:
        add("W1 非疲形状生效（w3,w4>0）", False, "S=0")
        add("d3/skip 恒 0（v49 旋钮已移除）", False, "S=0")

    if has_tired:
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
    print("  回退：copy 04_RiseAI\\out\\rai_tristate_v49.nro 覆盖插件 nro")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "04_RiseAI/out/sim_v50_smoke.txt")
