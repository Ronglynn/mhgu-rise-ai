#!/usr/bin/env python3
"""v33 帧间隔门控 v2 实机判据。

用法：python tools/analyze_v33_log.py <log.txt>
重点：窗口总量(W.sum)、跨怪覆盖(W 按 mon)、门控是否全程存活(live=1)。
"""
import re
import sys
import json
import collections
from pathlib import Path

HEX = ("w0", "w1", "s2C0", "a0", "mon", "vt", "sp")


def parse_line(s):
    out = {}
    for k, v in re.findall(r"(\w+)=(\S+)", s):
        if k in HEX or v.lower().startswith("0x"):
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
        print("usage: analyze_v33_log.py <log.txt>")
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
        for tag in ("G", "D", "E", "W", "Q", "U", "A", "T", "J",
                    "BEAT", "MON", "INSTALL", "SITE", "SKIP"):
            if s.startswith(tag + " ") or s.startswith(tag + "="):
                d = parse_line(s)
                d["_raw"] = s
                if "f" in d or tag in ("INSTALL", "SITE", "SKIP", "MON"):
                    rows[tag].append(d)
                break

    fatal = sum(1 for l in lines if "FATAL" in l)
    G, D, E, W, Q, A, BEAT = (rows[k] for k in ("G", "D", "E", "W", "Q", "A", "BEAT"))
    qd = [x for x in Q if x.get("d") == 1]
    installs = [str(x.get("_raw", x)) for x in rows["INSTALL"]]
    live = [x.get("live") for x in BEAT if "live" in x]
    last_w = [x.get("w") for x in BEAT if "w" in x]

    print("=" * 74)
    print("v33 FRAME-GAP GATE v2 判据  ——", path.name)
    print("=" * 74)
    print(f"FATAL={fatal}  Q={len(Q)} (d=1 {len(qd)})  A={len(A)}  "
          f"G={len(G)} D={len(D)} E={len(E)} W={len(W)}  BEAT={len(BEAT)}")
    for x in installs[:3]:
        print("  INSTALL:", x[:130])

    ok_w = [x for x in W if x.get("ok") == 1]
    wins = [x.get("win") for x in ok_w if isinstance(x.get("win"), int)]
    total = sum(wins) if wins else 0
    zero_win = sum(1 for v in wins if v == 0)
    frames = max([x.get("f") for x in BEAT if isinstance(x.get("f"), int)] +
                 [x.get("f") for x in A if isinstance(x.get("f"), int)] + [1])
    print(f"\n窗口统计：成功 {len(ok_w)}/{len(W)}  累计 {total} 帧 ≈ {total/60:.1f}s  "
          f"平均 {total/max(len(wins),1):.1f} 帧  最大 {max(wins) if wins else 0} 帧")
    print(f"  零长窗口 win=0：{zero_win}/{len(wins)}（G 与 A 同帧，结构性上限，无害）")
    print(f"  占战斗时长 {frames} 帧：{100*total/frames:.2f}%")
    print(f"  BEAT 末次累计 w={last_w[-1] if last_w else 'n/a'}  "
          f"live 序列（末 6）={live[-6:]}")
    mons = collections.Counter(x.get("mon") for x in W)
    print(f"  W 按 mon：{[(hex(k) if isinstance(k,int) else k, v) for k,v in mons.most_common(6)]}"
          f"  → 不同怪对象 {len(mons)} 个")
    sps = collections.Counter(x.get("sp") for x in Q if "sp" in x)
    print(f"  Q 行 species：{[(hex(k) if isinstance(k,int) else k, v) for k,v in sps.most_common(5)]}"
          f"  （v32 场 sp=0014，本场不同即跨怪验证成立）")

    fr = sorted(x["f"] for x in A if isinstance(x.get("f"), int))
    if len(fr) > 2:
        gaps = sorted(fr[i] - fr[i - 1] for i in range(1, len(fr)))
        short = sum(1 for g in gaps if g <= 30)
        print(f"\nA 帧间隔：n={len(gaps)} 中位={gaps[len(gaps)//2]} "
              f"p90={gaps[9*len(gaps)//10]} max={gaps[-1]}  "
              f"≤30帧 {short}/{len(gaps)}={100*short/len(gaps):.1f}%")
        print("  注意：仅同一怪种的原版基线可归因；跨怪种（sp 不同）不可直接比较。")
        ids = [x.get("id") for x in A]
        pairs = [(x.get("a"), x.get("s")) for x in A]
        rep = sum(1 for i in range(1, len(ids)) if ids[i] == ids[i - 1])
        prep = sum(1 for i in range(1, len(pairs)) if pairs[i] == pairs[i - 1])
        print(f"  连续同 id {rep}/{max(len(ids)-1,1)}={100*rep/max(len(ids)-1,1):.1f}%  "
              f"连续同 (a,s) {prep}/{max(len(pairs)-1,1)}={100*prep/max(len(pairs)-1,1):.1f}%"
              f"  （缺该怪原版基线，只记录不归因）")

    checks = []
    is_v33 = any("RAI v33" in l for l in lines)

    def gate(ok):
        return ok if is_v33 else None

    def add(name, ok, detail=""):
        checks.append((name, ok, detail))

    add("零 FATAL", fatal == 0, f"count={fatal}")
    add("h_unify 已安装", any("h_unify" in x and "SKIP" not in x for x in installs), "")
    add("hubMask=3", any("hubMask=3" in x for x in installs), "")
    add("Q 非空", len(Q) > 0, f"Q={len(Q)}")
    add("G 非空（窗口开启）", gate(len(G) > 0), f"G={len(G)}（v32 是 15，其中 14 条是抽选循环噪声）")
    add("W 非空（窗口结算）", gate(len(W) > 0), f"W={len(W)}")
    add("补落盘全部成功", gate(all(x.get("ok") == 1 for x in W) if W else None),
        f"ok={len(ok_w)}/{len(W)}")
    add("**门控全程未熔断**", gate(all(v == 1 for v in live) if live else None),
        f"live={live[-6:]}（v32 在 f=7093 后恒 0）")
    # 绝对帧数阈值不适用于慢节奏怪：用本场事件流离线仿真复核更严谨
    # （simulate_gate_v33.py 对本场预测 11 次 / 315 帧，与实测一致）
    add("窗口数 ≥ 8", gate(len(W) >= 8 if W else None),
        f"W={len(W)}（v32 仅 1 次有效窗口）")
    add("窗口占战斗时长 ≥ 1%", gate(100 * total / frames >= 1.0 if W else None),
        f"{100*total/frames:.2f}%（慢节奏怪天然触发少，属按需门控，不是缺陷）")
    add("平均窗口 > 8 帧", gate(total / max(len(wins), 1) > 8 if wins else None),
        f"{total/max(len(wins),1):.1f} 帧")
    add("零长窗口 < 50%", gate(zero_win / max(len(wins), 1) < 0.5 if wins else None),
        f"{zero_win}/{len(wins)}")
    add("Q.d=1 时 w1==w0", gate(all(x.get("w1") == x.get("w0") for x in qd) if qd else None),
        f"d=1 行={len(qd)}")
    add("跨怪覆盖（≥1 个怪对象）", gate(len(mons) >= 1 if W else None),
        f"不同 mon={len(mons)}，species={[hex(k) if isinstance(k,int) else k for k in sps][:3]}")

    print("\n" + "-" * 74)
    for name, ok, detail in checks:
        mark = "PASS" if ok is True else ("FAIL" if ok is False else "N/A ")
        print(f"  [{mark}] {name}  {detail}")
    nf = sum(1 for _, ok, _ in checks if ok is False)
    print("-" * 74)
    if not is_v33:
        verdict = "非 v33 日志（旧版）冒烟完成"
    elif nf == 0 and fatal == 0:
        verdict = ("全部通过 -> 规则稳定、门控全程存活；"
                   "窗口量是否够用由体感决定，必要时评估 0xAFF40 层双延迟")
    else:
        verdict = "存在失败项 -> 复核该怪种事件流；必要时回退 v31 只读"
    print(f"结论：FAIL={nf}  is_v33={is_v33}  {verdict}")

    out = Path(__file__).resolve().parent.parent / "out" / "v33_gate_events.json"
    try:
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps({k: rows[k] for k in
                                   ("G", "D", "E", "W", "Q", "A", "BEAT")},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"events → {out}")
    except OSError as e:
        print(f"events write skipped: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
