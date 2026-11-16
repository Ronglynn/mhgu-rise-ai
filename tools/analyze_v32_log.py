#!/usr/bin/env python3
"""v32 帧间隔门控（延迟落盘）实机日志判据。

用法：python tools/analyze_v32_log.py <log.txt>
输出：判定清单 + G/D/F/A 对齐统计 + 输出窗口前后对比。
"""
import re
import sys
import json
import collections
from pathlib import Path

FIELDS_INT = ("f", "n", "gap", "hold", "due", "life", "ok", "r1", "r2",
              "r3", "p5", "st", "s1A1", "hp", "id", "a", "s", "pa", "ps",
              "q", "u", "state", "skip", "hub", "g", "d", "fuse", "live",
              "log", "commit", "eq", "mon", "a0", "sp", "vt", "max")
FIELDS_HEX = ("w0", "w1", "s2C0", "a0", "mon", "vt", "sp")


def parse_line(s):
    d = dict(re.findall(r"(\w+)=(\S+)", s))
    out = {}
    for k, v in d.items():
        if k in FIELDS_HEX or v.lower().startswith("0x"):
            try:
                out[k] = int(v, 16) if not v.lower().startswith("0x") else int(v, 16)
            except ValueError:
                try:
                    out[k] = int(v, 16)
                except ValueError:
                    out[k] = v
        elif re.fullmatch(r"-?\d+", v):
            out[k] = int(v)
        elif "/" in v and all(re.fullmatch(r"\d+", x) for x in v.split("/")):
            out[k] = v
        else:
            out[k] = v
    return out


def main():
    if len(sys.argv) < 2:
        print("usage: analyze_v32_log.py <log.txt>")
        return 2
    path = Path(sys.argv[1])
    text = path.read_bytes().decode("utf-8", "replace")
    lines = text.splitlines()

    rows = collections.defaultdict(list)
    for ln in lines:
        m = re.search(r"\[rai\] (.*)$", ln)
        if not m:
            continue
        s = m.group(1)
        for tag in ("G", "D", "F", "Q", "U", "A", "T", "J", "BEAT", "MON", "INSTALL", "SITE", "SKIP"):
            if s.startswith(tag + " ") or s.startswith(tag + "="):
                d = parse_line(s)
                d["_raw"] = s
                if "f" in d or tag in ("INSTALL", "SITE", "SKIP", "MON"):
                    rows[tag].append(d)
                break

    fatal = sum(1 for l in lines if "FATAL" in l)
    G, D, F, Q, A, BEAT = (rows[k] for k in ("G", "D", "F", "Q", "A", "BEAT"))
    q0 = [x for x in Q if x.get("r3") == 0]
    qd = [x for x in Q if x.get("d") == 1]
    installs = [str(x.get("_raw", x)) for x in rows["INSTALL"]]

    print("=" * 72)
    print("v32 FRAME-GAP GATE 判据  ——", path.name)
    print("=" * 72)
    print(f"FATAL={fatal}  Q={len(Q)} (mode0={len(q0)}, d=1 {len(qd)})  "
          f"U={len(rows['U'])}  A={len(A)}  G={len(G)}  D={len(D)}  F={len(F)}  BEAT={len(BEAT)}")
    for x in installs[:4]:
        print("  INSTALL:", x[:150])

    checks = []

    is_v32 = any("RAI v32" in l for l in lines)

    def add(name, ok, detail=""):
        checks.append((name, ok, detail))

    def gate(ok):
        # 非 v32 日志（只读回退版）只做冒烟，干预相关判据记 N/A
        return ok if is_v32 else None

    add("零 FATAL", fatal == 0, f"count={fatal}")
    add("h_unify 已安装", any("h_unify" in x and "SKIP" not in x for x in installs),
        "; ".join(installs)[:120])
    add("hubMask=3", any("hubMask=3" in x for x in installs), "")
    add("SITE +076154=E92D4FF0", any("E92D4FF0" in str(x) for x in rows["SITE"]), "")
    add("Q 非空（hook 活跃）", len(Q) > 0, f"Q={len(Q)}")
    add("G 非空（门控触发）", gate(len(G) > 0), f"G={len(G)}")
    add("D 非空（补落盘执行）", gate(len(D) > 0), f"D={len(D)}")
    ok_d = [x for x in D if x.get("ok") == 1]
    add("补落盘全部成功", gate(len(ok_d) == len(D) if D else None),
        f"ok={len(ok_d)}/{len(D)}")
    add("G ≈ D（无丢失）", gate(abs(len(G) - len(D)) <= max(2, len(G) // 5) if G else None),
        f"G={len(G)} D={len(D)} （pending 覆盖会合并，D<=G 属正常）")
    add("**F=0（A 未早于落盘）**", gate(len(F) == 0 if G else None),
        f"F={len(F)} -> {'顺序兼容，方案成立' if len(F) == 0 else '顺序不兼容，需改方案'}")
    live = [x.get("live") for x in BEAT if "live" in x]
    add("门控未熔断", gate(all(v == 1 for v in live) if live else None),
        f"live 序列={live[-5:] if live else 'n/a'}")
    add("Q.d=1 时 w1==w0（未落盘）",
        gate(all(x.get("w1") == x.get("w0") for x in qd) if qd else None),
        f"d=1 行={len(qd)}")

    # D 后同帧 A 的 (a,s) 是否等于补落盘的 (r1,r2)
    amap = {}
    for x in A:
        amap.setdefault(x.get("f"), x)
    hit = 0
    for x in D:
        y = amap.get(x.get("f"))
        if y and x.get("r1") == y.get("a") and x.get("r2") == y.get("s"):
            hit += 1
    add("D 与 A 同帧 (act,sub) 对齐", hit > 0 if D else None,
        f"{hit}/{len(D)}（D 在 onUpdate、A 在动作脚本，可能差 1 帧）")

    # 输出窗口：A 帧间隔
    fr = sorted(x["f"] for x in A if isinstance(x.get("f"), int))
    if len(fr) > 2:
        gaps = [fr[i] - fr[i - 1] for i in range(1, len(fr))]
        sg = sorted(gaps)
        short = sum(1 for g in gaps if g <= 30)
        print(f"\nA 帧间隔：n={len(gaps)} min={sg[0]} 中位={sg[len(sg)//2]} "
              f"p90={sg[9*len(sg)//10]} max={sg[-1]}")
        print(f"  ≤30 帧：{short}/{len(gaps)} = {100*short/len(gaps):.1f}%  "
              f"（v31 基线 25.3%，中位 79）")
    else:
        print("\nA 帧间隔：样本不足")

    # per-mon 覆盖
    mons = collections.Counter(x.get("mon") for x in G)
    print(f"\nG 按 mon：{[(hex(k) if isinstance(k,int) else k, v) for k,v in mons.most_common(6)]}")

    print("\n" + "-" * 72)
    for name, ok, detail in checks:
        mark = "PASS" if ok is True else ("FAIL" if ok is False else "N/A ")
        print(f"  [{mark}] {name}  {detail}")
    nf = sum(1 for _, ok, _ in checks if ok is False)
    print("-" * 72)
    if not is_v32:
        verdict = "非 v32 日志（只读版）冒烟完成：基础判据已核对，干预判据 N/A"
    elif nf == 0 and fatal == 0:
        verdict = "全部通过 -> 延迟门控成立，可进入规则细化（怒/疲劳权重、距离档）"
    else:
        verdict = "存在失败项 -> 回退 v31 只读并按 F 行结论重新设计"
    print(f"结论：FAIL={nf}  is_v32={is_v32}  {verdict}")

    # 结构化输出，便于离线仿真复用
    out = Path(__file__).resolve().parent.parent / "out" / "v32_framegap_events.json"
    try:
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps({k: rows[k] for k in
                                   ("G", "D", "F", "Q", "U", "A", "BEAT")},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"events → {out}")
    except OSError as e:
        print(f"events write skipped: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
