# -*- coding: utf-8 -*-
"""v49 判读：三状态权重层（怒 / 普通 / 疲惫 -> prev 否决严格度）。

三态输入（全部只读、跨怪通用、零写入）：
  怒   *(u8*)(act+0x518)==1                     P14/P25/P30 实机闭环
  疲   EXH add(0xA30E4) 返回 1 或 proc(act+0x5D8C) 递增 -> 疲惫窗口
       窗口按「该怪自己的动作数」计时（免疫暂停菜单冻结 forge 帧）
  常   其余
权重映射：怒 depth=3 / 常 depth=2（v38 基线）/ 疲 depth=1 + 50% 放弃否决
  => Rise 15 池「怒熵 1.67 高、疲熵 1.30 低」的结构性近似，不是等价实现。

用法: python analyze_v49_states.py <log>
"""
import re
import sys
import collections
from pathlib import Path

INT = {"f", "i", "log", "a", "an", "an0", "dA", "lowhits", "a1", "cnt",
       "thr", "proc", "amt", "force", "forced", "ret", "st", "st3", "vd",
       "kind", "reason", "tir", "t4", "ex", "d5", "h1", "e1", "dc", "s3f",
       "f5c", "p3ca", "p3be", "low", "flg", "t5c", "live", "hub",
       "s0", "s1", "s2", "sv0", "sv1", "sv2", "d3", "skip",
       "n", "nc", "d", "ki", "rd", "b1", "ph", "sw", "sw2", "nr", "p5",
       "sel", "act", "beg", "begf", "rep", "v", "noalt", "fail", "ok",
       "peak", "m", "m1", "m0c", "m0e", "x", "q"}
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
    is_v49 = any("RAI v49" in l for l in lines)
    fatal = sum(1 for l in lines if "FATAL" in l)
    # 实机日志行带宿主前缀 "[forge] [INFO] [rai] INSTALL ..."，
    # 不能用 startswith("[rai]")（P33：曾导致 INSTALL=0 的假 FAIL）。
    installs = [l.strip() for l in lines if "[rai] INSTALL h_" in l]
    banner = next((l.strip() for l in lines if "RAI v49" in l), "(旧日志)")
    crash_lines = [l.strip() for l in lines
                   if "c0000005" in l or "*** exception" in l
                   or "host backtrace" in l]

    print("=== v49 三状态权重层判读 ===")
    print("日志: %s" % path)
    print("banner: %s" % banner[:120])
    print("版本=%s  V=%d T=%d U=%d S=%d R=%d N=%d BEAT=%d  FATAL=%d" %
          ("v49" if is_v49 else "旧日志(冒烟/降级)", len(V), len(T), len(U),
           len(S), len(R), len(N), len(BEAT), fatal))
    for l in installs[:6]:
        print("  " + l[:120])
    site = [l.strip() for l in lines if "SITE +" in l and "A30E4" in l]
    for l in site[:1]:
        print("  " + l[:120])

    checks = []

    def add(name, ok, detail):
        checks.append((name, bool(ok), detail))
        print("  [%s] %-40s %s" % ("PASS" if ok else "FAIL", name, detail))

    # --- 版本 / 安全性 ---
    add("RAI v49 版本横幅", is_v49, banner[:60])
    add("零 FATAL（guest 侧）", fatal == 0, "FATAL=%d" % fatal)
    add("零 host 异常（c0000005）", not crash_lines,
        "异常行=%d %s" % (len(crash_lines), crash_lines[0][:60] if crash_lines else ""))
    n_inst = sum(1 for l in installs if any(h in l for h in
                 ("h_matcher", "h_emc", "h_unify", "h_start_40", "h_exh")))
    add("5 个 hook 全部 INSTALL", n_inst >= 5, "INSTALL=%d" % n_inst)
    add("EXH hook 为 v49 只读观测",
        any("v49 read-only trigger observer" in l for l in installs),
        "INSTALL h_exh 文案")
    add("v48 强制放大已移除（无 force=1）",
        not any(x.get("force") == 1 for x in U),
        "U 行 force=1 计数=%d" % sum(1 for x in U if x.get("force") == 1))
    live = ival(BEAT, "live")
    add("live=1（自保护未熔断）", not live or live[-1] == 1,
        "BEAT.live 末值=%s" % (live[-1] if live else "?"))
    hub = ival(BEAT, "hub")
    add("hub=15（hook 掩码兼容）", not hub or 15 in hub,
        "hub 集合=%s" % sorted(set(hub))[:4])

    # --- 疲惫窗口 ---
    enter = [x for x in T if x.get("kind") == 1]
    exit_ = [x for x in T if x.get("kind") == 2]
    add("T 行 TIRED-ENTER 事件", len(enter) > 0, "ENTER=%d" % len(enter))
    add("T 行 TIRED-EXIT 事件", len(exit_) > 0, "EXIT=%d" % len(exit_))
    reasons = sorted(set(ival(T, "reason")))
    add("疲惫触发含 EXH ret=1 / proc 递增",
        any(r in reasons for r in (1, 2)), "reason 集合=%s" % reasons)
    add("疲惫退出用动作数窗口（免疫暂停）",
        any(x.get("reason") == 3 and isinstance(x.get("an"), int)
            and x["an"] >= 40 for x in exit_),
        "EXIT reason=3 且 an>=40 计数=%d" %
        sum(1 for x in exit_ if x.get("reason") == 3
            and isinstance(x.get("an"), int) and x["an"] >= 40))
    add("U 行 EXH 触发轨迹（ret=1 force=0）",
        any(x.get("ret") == 1 and x.get("force") == 0 for x in U),
        "U=%d" % len(U))

    # --- 三态 -> 否决深度映射 ---
    bad_map = [x for x in V if isinstance(x.get("st3"), int)
               and isinstance(x.get("vd"), int)
               and x["vd"] != {0: 2, 1: 3, 2: 1}.get(x["st3"], -1)]
    add("V 行 st3 -> vd 映射正确 (0/1/2 -> 2/3/1)",
        len(V) > 0 and len(bad_map) == 0,
        "V=%d 违例=%d" % (len(V), len(bad_map)))
    st_set = set(ival(V, "st3"))
    add("三态均有 V 行样本", {0, 1, 2}.issubset(st_set),
        "st3 集合=%s" % sorted(st_set))
    d3_v = sum(1 for x in V if x.get("st3") == 1)
    add("怒态 depth=3 生效", d3_v > 0, "V(st3=1)=%d" % d3_v)

    # --- S 行统计 ---
    if S:
        s = S[-1]
        s_n = [s.get(k) for k in ("s0", "s1", "s2")]
        add("S 行三态抽选计数非空", all(isinstance(v, int) and v > 0 for v in s_n),
            "s0/s1/s2=%s" % s_n)
        add("S 行 d3 与怒态抽选一致",
            isinstance(s.get("d3"), int) and s["d3"] == s.get("s1"),
            "d3=%s s1=%s" % (s.get("d3"), s.get("s1")))
        add("疲惫态放弃否决生效（skip>0）",
            isinstance(s.get("skip"), int) and s["skip"] > 0,
            "skip=%s" % s.get("skip"))
    else:
        add("S 行三态抽选计数非空", False, "S=0")
        add("S 行 d3 与怒态抽选一致", False, "S=0")
        add("疲惫态放弃否决生效（skip>0）", False, "S=0")

    # --- 观测完整性 ---
    add("R 行无条件定时快照保留", len(R) >= 20, "R=%d" % len(R))
    add("N 行低活动锚点保留", len(N) > 0, "N=%d" % len(N))

    print("\n=== 三态分布 ===")
    for st, name in ((0, "普通"), (1, "发怒"), (2, "疲惫")):
        vv = [x for x in V if x.get("st3") == st]
        print("  %-4s st3=%d  V=%-4d  vd=%s" %
              (name, st, len(vv), sorted(set(ival(vv, "vd")))))
    if T:
        print("  T 事件（最多 8 条）:")
        for x in T[:8]:
            print("    f=%-7s kind=%-2s reason=%-2s mon=%-10s proc=%-3s an=%s" %
                  (x.get("f"), x.get("kind"), x.get("reason"),
                   x.get("mon"), x.get("proc"), x.get("an")))

    # P33：proc 是 u8 且 grow 上限 ~30，>30 基本可判为「非主怪槽误读」。
    bad_proc = [x for x in T if isinstance(x.get("proc"), int) and x["proc"] > 30]
    if bad_proc:
        print("\n  [WARN] T 行 proc>30 共 %d 条（值=%s）=> 疑似把非目标槽字节当 proc，"
              "会制造假疲惫窗口；需在插件侧加 proc<=30 与 thr 合法性门控。" %
              (len(bad_proc), [x.get("proc") for x in bad_proc][:6]))

    print("\n=== 结论 ===")
    npass = sum(1 for _, ok, _ in checks if ok)
    nfail = len(checks) - npass
    print("  PASS=%d / FAIL=%d" % (npass, nfail))
    if crash_lines:
        print("  [CRASH] 日志含 host 异常：%s" % crash_lines[0][:100])
        print("  -> 本场为闪退中断，三态样本不完整属预期；先按 P33 做 A/B 归因，"
              "不要在未定因前改动插件参数。")
    if not is_v49:
        print("  -> 旧日志（v48 及以前）：三态字段缺失属预期，用于验证降级不崩溃。")
    elif nfail == 0:
        print("  -> 三状态权重层离线闭环：怒/常/疲三态均可判定，否决严格度按态分化，")
        print("     疲惫窗口由该怪动作数计时（暂停不消耗），v48 强制已移除、全程只读。")
        print("  -> 下一步：实机短场（跳狗龙王自然疲惫约 3 分钟），对比体感与 S 行分布。")
    else:
        print("  -> 存在 FAIL，按上方条目定位；不要据此推进实机。")
    print("  回退：copy 04_RiseAI\\out\\rai_exhaust_chain_v48.nro 覆盖插件 nro")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "04_RiseAI/out/sim_v49_smoke.txt")
