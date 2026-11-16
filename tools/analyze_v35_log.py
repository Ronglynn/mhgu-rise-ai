#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""analyze_v35_log.py — v35「EMC 抽选层通用 prev 否决」实机判据。

用法：python tools/analyze_v35_log.py <log>
产物：与日志同目录的 v35_preveto_events.json（若日志在 02_Workspace 下亦写一份）

核心判据（体感优先，日志辅助）：
  零 FATAL / hub=15 四 hook 全装 / 无 SKIP / live=1 全程未熔断
  sel>0 / ok>0（case 解析成功） / veto>0（真的改了 ret）
  V 行 nr == ret+delta 且 0<nr<256 / K 行 why 分布 / 跨 mon 覆盖
"""
import re
import sys
import json
import collections
from pathlib import Path

HEX = {"mon", "sp", "sig", "psig", "sel", "pick", "blk", "ip",
       "w0", "w1", "w73", "first", "vt"}
TAGS = ("V", "K", "M", "X", "Q", "A", "BEAT", "SITE", "INSTALL", "SKIP", "MON")


def parse_line(s):
    d = {}
    for k, v in re.findall(r"(\w+)=(\S+)", s):
        v = v.rstrip(",;)")
        try:
            d[k] = int(v, 16) if k in HEX else int(v, 0)
        except ValueError:
            d[k] = v
    return d


def main():
    if len(sys.argv) < 2:
        print("usage: analyze_v35_log.py <log>")
        return 2
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"[ERR] no such log: {p}")
        return 2
    text = p.read_bytes().decode("utf-8", "replace")
    lines = text.splitlines()
    is_v35 = "RAI v35" in text
    rows = collections.defaultdict(list)
    rai = []
    for ln in lines:
        m = re.search(r"\[rai\] (.*)$", ln)
        if not m:
            continue
        s = m.group(1).strip()
        rai.append(s)
        for tag in TAGS:
            if s.startswith(tag + " "):
                d = parse_line(s)
                rows[tag].append(d)
                break
        if s.startswith("INSTALL") or s.startswith("SKIP"):
            pass
    install_lines = [s for s in rai if s.startswith("INSTALL")]
    skip_lines = [s for s in rai if s.startswith("SKIP")]
    fatal = sum(1 for l in lines if "FATAL" in l)

    V, K, B = rows["V"], rows["K"], rows["BEAT"]
    A, M, X, Q = rows["A"], rows["M"], rows["X"], rows["Q"]
    checks = []

    def gate(ok):
        # 非 v35 日志（只读回退版）只做冒烟，不把缺失的干预数据判成 FAIL
        return None if not is_v35 else bool(ok)

    def add(name, ok, detail=""):
        checks.append((name, gate(ok), detail))

    def has(tag, key):
        return any(key in d for d in tag)

    print(f"=== {p.name} ===  v35={'YES' if is_v35 else 'NO(smoke only)'}  lines={len(lines)}")
    print(f"banner: {next((s for s in rai if s.startswith('=====')), 'n/a')}")
    print(f"install: {install_lines[:5]}")
    print(f"skip   : {skip_lines[:5] if skip_lines else 'none'}")
    print(f"FATAL={fatal}  V={len(V)} K={len(K)} BEAT={len(B)} M={len(M)} X={len(X)} Q={len(Q)} A={len(A)}")

    add("零 FATAL", fatal == 0, f"FATAL={fatal}")
    hub = [d.get("hub") for d in B if "hub" in d]
    add("hub=15（4 hook 全装）", bool(hub) and all(h == 15 for h in hub),
        f"hub 序列={hub[:3]}..{hub[-3:] if hub else []}")
    add("无 SKIP", len(skip_lines) == 0, f"SKIP={len(skip_lines)}")
    # SITE 行形如 `+08E144=E92D4FF0 ...`，key 带 + 号无法被 parse_line 提取，直接查原文
    site_ok = bool(re.search(r"\+08E144=E92D4FF0", text))
    add("SITE matcher 首字 E92D4FF0", site_ok,
        next((s[:100] for s in rai if s.startswith("SITE ")), "n/a"))

    live = [d.get("live") for d in B if "live" in d]
    add("live=1 全程未熔断", bool(live) and all(v == 1 for v in live),
        f"live 序列（末 6）={live[-6:]}")
    last = B[-1] if B else {}
    sel, act, ok, veto = (last.get("sel", 0), last.get("act", 0),
                          last.get("ok", 0), last.get("veto", 0))
    rep, noalt, fail = last.get("rep", 0), last.get("noalt", 0), last.get("fail", 0)
    add("sel>0（op02 抽选块活跃）", sel > 0, f"sel={sel}")
    add("act>0（ret>0 的真实选 case）", act > 0, f"act={act}")
    add("ok>0（case 解析成功）", ok > 0, f"ok={ok}")
    add("veto>0（实际改写了 ret）", veto > 0, f"veto={veto} rep={rep}")
    add("解析失败率 < 50%", (fail / max(fail + ok, 1)) < 0.5,
        f"fail={fail} ok={ok} 比例={fail/max(fail+ok,1):.1%}")
    add("noalt 未完全主导", noalt <= max(veto * 3, 10),
        f"noalt={noalt} veto={veto}（必然同招块会透传，属预期）")

    good_v = 0
    for d in V:
        ret, delta, nr = d.get("ret"), d.get("delta"), d.get("nr")
        if isinstance(ret, int) and isinstance(delta, int) and isinstance(nr, int):
            if nr == ret + delta and 0 < nr < 256:
                good_v += 1
    add("V 行 nr==ret+delta 且 0<nr<256", good_v == len(V) if V else None,
        f"{good_v}/{len(V)}")
    mons = collections.Counter(d.get("mon") for d in V)
    add("跨怪覆盖 ≥1 个 mon 对象", len(mons) >= 1 if V else None,
        f"不同 mon={len(mons)}  {[(hex(k) if isinstance(k,int) else k,v) for k,v in mons.most_common(6)]}")

    kw = collections.Counter(d.get("why") for d in K)
    print(f"\nK 行 why 分布：{kw.most_common()}")
    ds = collections.Counter(d.get("d") for d in V if isinstance(d.get("d"), int))
    kd = collections.Counter(d.get("d") for d in K if isinstance(d.get("d"), int))
    print(f"V 行 d（ret↔case 偏差）分布：{ds.most_common(12)}")
    print(f"  d>8 占比={sum(n for d, n in ds.items() if d > 8)}/{sum(ds.values())}"
          f" -> {'基址可能有系统偏差，需按本轮数据校准' if any(d > 8 for d in ds) else '与静态推导一致（偏差 ≤8）'}")
    print(f"K 行 d 分布：{kd.most_common(8)}")
    knc = collections.Counter(d.get("nc") for d in K if isinstance(d.get("nc"), int))
    f0 = sum(1 for d in K if d.get("sig") == 0x811C9DC5)
    print(f"K 行 nc（扫描到的 case 数）分布：{knc.most_common()}")
    print(f"K 行 sig==FNV0(空签名/该池无 op14)：{f0}/{len(K)} = {f0/max(len(K),1):.1%}"
          f"  -> 这类池不是动作选择池，规则不适用，应整体跳过")
    # 采样配额与后段停滞窗口（诊断「进入动作后不动」）
    if A and B:
        afr = [d.get("f") for d in A if isinstance(d.get("f"), int)]
        print(f"\n采样覆盖：A={len(A)} 条（上限 80） f={min(afr)}..{max(afr)}，"
              f"末 BEAT f={B[-1].get('f')} -> "
              f"{'已截断，后段动作时间线不可见' if len(A) >= 80 else '未截断'}")
        stalls = []
        for i in range(1, len(B)):
            p, c = B[i - 1], B[i]
            dm = c.get("m", 0) - p.get("m", 0)
            dq = c.get("q", 0) - p.get("q", 0)
            da = c.get("a", 0) - p.get("a", 0)
            ds = c.get("sel", 0) - p.get("sel", 0)
            if da == 0 and (dm > 0 or dq > 0 or ds > 0):
                stalls.append(c.get("f"))
        print(f"后段停滞窗口（300 帧内 a 不增但 m/q/sel 仍增）：{len(stalls)} 个，"
              f"样例 f={stalls[:8]}  -> 仅说明脚本在跑，不能区分换区/原生长动作/发呆")
        print("  BEAT 的 a 是全局累计（不受采样配额限制），末值 =", B[-1].get("a"))
    if V:
        print("\nV 行（前 12 条否决明细）：")
        for d in V[:12]:
            print("  f=%-6s mon=%s sp=%s nc=%-3s ret=%-4s d=%-3s sel=%08X sig=%08X pick=%08X delta=%-4s nr=%-4s" % (
                d.get("f"), d.get("mon"), d.get("sp"), d.get("nc"), d.get("ret"),
                d.get("d"), d.get("sel", 0), d.get("sig", 0), d.get("pick", 0),
                d.get("delta"), d.get("nr")))
    if B:
        print("\nBEAT 首 / 末：")
        for d in (B[0], B[-1]):
            print("  f=%-6s sel=%-5s act=%-5s rep=%-5s veto=%-5s noalt=%-5s fail=%-5s ok=%-5s live=%s peak=%s hub=%s" % (
                d.get("f"), d.get("sel"), d.get("act"), d.get("rep"), d.get("veto"),
                d.get("noalt"), d.get("fail"), d.get("ok"), d.get("live"), d.get("peak"), d.get("hub")))
    # 复读量化（仅记录；怪种不同不可与历史场直接比较）
    if A:
        ids = [d.get("id") for d in A]
        pairs = [(d.get("a"), d.get("s")) for d in A]
        rep_id = sum(1 for i in range(1, len(ids)) if ids[i] == ids[i - 1])
        rep_pair = sum(1 for i in range(1, len(pairs)) if pairs[i] == pairs[i - 1])
        print(f"\n复读量化（本场 A={len(A)}，采样上限 80，仅作参考）："
              f"连续同 id {rep_id}/{max(len(ids)-1,1)}={rep_id/max(len(ids)-1,1):.1%}，"
              f"连续同 (a,s) {rep_pair}/{max(len(pairs)-1,1)}={rep_pair/max(len(pairs)-1,1):.1%}")

    print("\n=== 判据 ===")
    npass = nfail = nskip = 0
    for name, ok, detail in checks:
        mark = "PASS" if ok is True else ("FAIL" if ok is False else "SKIP")
        if ok is True: npass += 1
        elif ok is False: nfail += 1
        else: nskip += 1
        print(f"  [{mark}] {name}  {detail}")
    print(f"\n结论：PASS={npass} FAIL={nfail} SKIP={nskip}  " +
          ("全部通过 -> 按体感决定是否进入加权池 / 状态自适应" if nfail == 0 and fatal == 0 and is_v35
           else "存在失败项或为冒烟 -> 检查 K 行原因；必要时回退 v31 纯只读" if is_v35
           else "非 v35 日志，仅冒烟（不判 FAIL）"))

    out = {"log": str(p), "is_v35": is_v35,
           "rows": {k: v for k, v in rows.items()},
           "summary": {"fatal": fatal, "V": len(V), "K": len(K), "BEAT": len(B),
                       "A": len(A), "sel": sel, "ok": ok, "veto": veto, "rep": rep,
                       "noalt": noalt, "fail": fail}}
    for cand in (p.parent / "v35_preveto_events.json",
                 Path("D:/MHGU mod maker/04_RiseAI/out/v35_preveto_events.json")):
        try:
            cand.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        except OSError:
            pass
    return 0 if nfail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
