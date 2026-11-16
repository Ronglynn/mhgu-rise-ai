#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""analyze_v36_log.py — v36 实机判据（EMC 抽选层 prev 否决 v2）

用法：python 04_RiseAI/tools/analyze_v36_log.py 02_Workspace/game_p54.txt

判据分三层：
  安全：零 FATAL / hub=15 无 SKIP / live=1 全程 / 正常结算
  机制：m1>0（GU 加权抽选活跃）/ sel>0 / act>0 / beg>0 / p5 落在 0..99
  效果：v>0（真的改写了 ret）/ V.nr==ret+delta / 0<nr<256 / 跨 mon 覆盖
非 v36 日志（v34/v35 旧日志）自动降级为冒烟模式，不把缺失字段判 FAIL。
"""
import sys, re, json, collections, os

HEX = {"mon", "sp", "w73", "ip", "w0", "w1", "first", "blk", "pick", "sig", "psig"}
INT = {"f", "n", "op", "md", "mode", "sub", "p5", "ret", "nc", "d", "delta", "nr",
       "live", "log", "k", "why", "id", "a", "s", "pa", "ps", "st", "r1", "r2", "r3",
       "m", "m1", "m0c", "m0e", "x", "q", "sel", "act", "beg", "begf",
       "empt", "rep", "v", "v1", "v0", "noalt", "fail", "ok", "peak", "hub", "depth",
       "a2", "last"}


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
        for tag in ("BEAT", "V", "K", "M", "X", "Q", "A", "SITE", "INSTALL", "SKIP", "MON"):
            if s.startswith(tag + " ") or s == tag:
                d = parse(s)
                if tag in ("V", "K", "M", "X", "Q", "A", "BEAT") and "f" not in d:
                    break
                rows[tag].append(d)
                break

    is_v36 = any("RAI v36" in l for l in lines)
    fatal = sum(1 for l in lines if "FATAL" in l)
    checks = []

    def add(name, ok, detail=""):
        checks.append((name, None if not is_v36 else bool(ok), detail))

    print(f"=== v36 判据：{os.path.basename(path)} ===")
    print(f"  版本={'v36' if is_v36 else '旧日志 → 冒烟模式（判据显示为 SKIP）'}  "
          f"FATAL={fatal}  行数={len(lines)}")
    B, V, K, M, A = rows["BEAT"], rows["V"], rows["K"], rows["M"], rows["A"]
    last = B[-1] if B else {}
    print(f"  BEAT={len(B)}  V={len(V)}  K={len(K)}  M={len(M)}  A={len(A)}")
    print()

    add("零 FATAL", fatal == 0, f"FATAL={fatal}")
    site_lines = [l for l in lines if "[rai] SITE" in l]
    site_ok = bool(site_lines) and "E92D4FF0" in site_lines[0]
    add("SITE matcher 首字 E92D4FF0", site_ok,
        site_lines[0].strip()[:150] if site_lines else "none")
    hub_ok = ("hubMask=15" in raw) or (last.get("hub") == 15)
    add("4 hook 全装（hub=15）", hub_ok,
        f"hubMask=15 出现={'hubMask=15' in raw}  BEAT.hub={last.get('hub')}")
    add("无 SKIP", len(rows["SKIP"]) == 0, f"SKIP={len(rows['SKIP'])}")
    live = [x.get("live") for x in B if "live" in x]
    add("live=1 全程", all(v == 1 for v in live) if live else False,
        f"live 序列末 6={live[-6:] if live else 'n/a'}")

    m1 = last.get("m1", 0); m0c = last.get("m0c", 0); m0e = last.get("m0e", 0)
    sel = last.get("sel", 0); act = last.get("act", 0)
    beg = last.get("beg", 0); begf = last.get("begf", 0)
    empt = last.get("empt", 0); rep = last.get("rep", 0)
    v = last.get("v", 0); v1 = last.get("v1", 0); v0 = last.get("v0", 0)
    noalt = last.get("noalt", 0); fail = last.get("fail", 0); ok = last.get("ok", 0)
    add("m1>0（加权抽选 begin 活跃）", m1 > 0, f"m1={m1}")
    add("m0c>0（case 遍历轨活跃）", m0c > 0, f"m0c={m0c} m0e(endblock)={m0e}")
    add("sel>0 / act>0（作用面有效）", sel > 0 and act > 0, f"sel={sel} act={act}")
    add("beg>0（向前定位 begin 成功）", beg > 0 and begf <= max(2, beg // 10),
        f"beg={beg} begf={begf}")
    add("ok>0（case 解析成功）", ok > 0, f"ok={ok} fail={fail}")

    # 核心：真的改写了
    add("**v>0（veto 真的发生）**", v > 0, f"v={v}  v1(mode1加权轨)={v1}  v0(mode0轨)={v0}")
    add("V 行非空", len(V) > 0, f"V={len(V)}（配额 {min(len(V), 200)}）")
    bad_nr = [x for x in V if not (isinstance(x.get("nr"), int) and 0 < x["nr"] < 256)]
    add("V.nr ∈ (0,256)", len(bad_nr) == 0 if V else False, f"异常 {len(bad_nr)}/{len(V)}")
    bad_delta = [x for x in V if isinstance(x.get("ret"), int) and isinstance(x.get("delta"), int)
                  and isinstance(x.get("nr"), int) and x["nr"] != x["ret"] + x["delta"]]
    add("V.nr == ret+delta", len(bad_delta) == 0 if V else False,
        f"异常 {len(bad_delta)}/{len(V)}")
    ds = [x.get("d") for x in V if isinstance(x.get("d"), int)]
    add("d 中位数 ≤ 8（基址对齐）",
        (sorted(ds)[len(ds) // 2] <= 8) if ds else False,
        f"d 分布={collections.Counter(ds).most_common(8)}")

    # mode=1 的 p5 必须是 0..99 随机数 -> 加权语义闭环
    p5s = [x.get("p5") for x in V if x.get("md") == 1 and isinstance(x.get("p5"), int)]
    add("mode1 的 p5 落在 0..99（rand%100）",
        all(0 <= p < 100 for p in p5s) if p5s else False,
        f"p5 样例={p5s[:12]} n={len(p5s)}")
    why = collections.Counter(x.get("why") for x in K)
    print(f"\nK 行 why 分布：{why.most_common(10)}   K 总数={len(K)}")
    ncs = collections.Counter(x.get("nc") for x in K)
    print(f"K 行 nc 分布：{ncs.most_common(10)}")
    print(f"  空签名透传 empt={empt}  判重复 rep={rep}  无替代 noalt={noalt}")
    print(f"  -> 完整块扫描后 nc 应显著高于 v35 的 nc=1(58%)")
    mons = collections.Counter(x.get("mon") for x in V)
    print(f"\nV 按 mon：{[(hex(k) if isinstance(k, int) else k, n) for k, n in mons.most_common(6)]}"
          f"  → 不同怪对象 {len(mons)} 个")
    add("跨怪覆盖（≥1 个 mon）", len(mons) >= 1 if V else False, f"mon 数={len(mons)}")

    # A 行时间分层：帧范围与末 BEAT 对比
    afs = [x["f"] for x in A if isinstance(x.get("f"), int)]
    last_f = last.get("f", 0)
    if afs:
        print(f"\nA 行采样：n={len(A)}  f={min(afs)}..{max(afs)}  末 BEAT f={last_f}  "
              f"覆盖率={100 * max(afs) / max(last_f, 1):.1f}%")
        seg = collections.Counter(x["f"] // 3000 for x in A)
        print(f"  按 3000 帧段分布：{sorted(seg.items())[:14]}")
        add("A 采样覆盖后半场", max(afs) >= last_f * 0.6 if last_f else True,
            f"末 A={max(afs)} / 末 BEAT={last_f}")
    if A:
        ids = [x.get("id") for x in A]
        repa = sum(1 for i in range(1, len(ids)) if ids[i] == ids[i - 1])
        print(f"  A 连续同 id：{repa}/{max(len(ids) - 1, 1)} = "
              f"{100 * repa / max(len(ids) - 1, 1):.1f}%（体感复读参考，跨怪不可直接对比）")

    print("\n=== 判据明细 ===")
    npass = nfail = nskip = 0
    for name, ok, detail in checks:
        if ok is None: tag, nskip = "SKIP", nskip + 1
        elif ok: tag, npass = "PASS", npass + 1
        else: tag, nfail = "FAIL", nfail + 1
        print(f"  [{tag}] {name}  —  {detail}")
    print(f"\n结论：PASS={npass} FAIL={nfail} SKIP={nskip}  " +
          ("全部通过 -> 抽选层否决生效，进入体感评估（连续同招 / 发呆 / 结算）"
           if nfail == 0 and fatal == 0 and is_v36 else
           "冒烟完成（旧日志）" if not is_v36 else
           "存在失败项 -> 看 K 行 why / d 分布，必要时回退 v31 只读"))

    out = {"rows": {k: rows[k] for k in rows},
           "verdict": {"pass": npass, "fail": nfail, "skip": nskip, "fatal": fatal,
                       "is_v36": is_v36, "last": last}}
    op = os.path.join(os.path.dirname(os.path.abspath(path)), "v36_preveto_events.json")
    try:
        with open(op, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print(f"  events -> {op}")
    except Exception as e:
        print(f"  events 写入跳过：{e}")
    return 0 if (nfail == 0 or not is_v36) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "02_Workspace/game_p54.txt"))
