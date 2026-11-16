#!/usr/bin/env python3
"""分析 v17 action-end 探针日志：配对 E(动作结束)/S(提交)，量化动作时长与输出窗口。"""
import re, json, collections, sys, os

LOG = sys.argv[1] if len(sys.argv) > 1 else r"D:/MHGU mod maker/02_Workspace/game_p54.txt"
lines = open(LOG, "rb").read().decode("utf-8", "replace").splitlines()
E, S, BEAT, meta = [], [], [], {}
for ln in lines:
    m = re.search(r"\[rai\] (.*)$", ln)
    if not m: continue
    s = m.group(1)
    if s.startswith(("E ", "S ")):
        d = dict(re.findall(r"(\w+)=(\S+)", s))
        st = d.get("st", "").split("/")
        rec = {k: (int(v) if k in ("f","n","dE","dS","a","s","pa","ps") else v)
               for k, v in d.items() if k != "st"}
        rec["st"] = st
        rec["rng"] = int(d.get("rng", "0"), 16)
        (E if s.startswith("E") else S).append(rec)
    elif s.startswith("BEAT "):
        BEAT.append(dict((k, int(v, 0) if v.startswith("0x") else int(v))
                         for k, v in re.findall(r"([A-Za-z0-9_/]+)=(\S+)", s)))
    elif s.startswith("OBJ ") or s.startswith("SITE ") or s.startswith("====="):
        meta.setdefault(s.split()[0], s)

print(f"E(动作结束)={len(E)}  S(提交)={len(S)}  BEAT={len(BEAT)}")
for k, v in meta.items(): print("  " + v)
if BEAT:
    print("\n=== BEAT 尾部 ===")
    for b in BEAT[-4:]: print("  " + str(b))
    # 判定 0x75224 是否每帧调用
    rates = [b["end/600"] for b in BEAT if "end/600" in b]
    if rates:
        print(f"\n  end/600 范围 {min(rates)}..{max(rates)}；"
              f"{'⚠ 接近每帧调用 → 0x75224 不是 action-end' if max(rates) > 300 else '✓ 非每帧调用 → 支持 action-end 语义'}")

def stats(name, xs):
    if not xs: return
    xs = sorted(xs)
    print(f"  {name}: n={len(xs)} min={xs[0]} p25={xs[len(xs)//4]} 中位={xs[len(xs)//2]} "
          f"p75={xs[3*len(xs)//4]} max={xs[-1]} 均值={sum(xs)/len(xs):.1f}")

print("\n=== 帧差 ===")
stats("E.dS 提交→结束 (动作时长)", [r["dS"] for r in E if 0 <= r["dS"] < 10000])
stats("E.dE 结束→结束 (动作周期)", [r["dE"] for r in E if 0 <= r["dE"] < 10000])
stats("S.dS 提交→提交 (决策间隔)", [r["dS"] for r in S if 0 <= r["dS"] < 10000])
stats("S.dE 结束→提交 (输出窗口候选)", [r["dE"] for r in S if 0 <= r["dE"] < 10000])

# 按时间顺序配对：每个 S 找它之前最近的 E
es = sorted((r["f"], r) for r in E)
ss = sorted((r["f"], r) for r in S)
pairs = []
for f, r in ss:
    prev = [x for x in es if x[0] <= f]
    if prev:
        ef, er = prev[-1]
        pairs.append((f - ef, er, r))
print(f"\n=== 配对 (S 之前最近的 E): {len(pairs)} 组 ===")
stats("结束→提交间隔", [p[0] for p in pairs if p[0] < 10000])
short = sum(1 for p in pairs if p[0] <= 30)
print(f"  <=30 帧: {short}/{len(pairs)} ({short*100//max(1,len(pairs))}%)  <=60 帧: {sum(1 for p in pairs if p[0] <= 60)}")
print("\n  前 20 组:")
for gap, er, sr in pairs[:20]:
    print(f"    E f={er['f']:6d} {er['a']}/{er['s']:<3} -> S f={sr['f']:6d} {sr['a']}/{sr['s']:<3}  gap={gap:4d}  actlen(E.dS)={er['dS']:4d}  st={'/'.join(er['st'][:4])}")

print("\n=== act 分布 ===")
for name, xs in (("E", E), ("S", S)):
    c = collections.Counter(r["a"] for r in xs)
    print(f"  {name}: " + ", ".join(f"{k}:{v}" for k, v in c.most_common()))

print("\n=== 状态字取值 (E 行) ===")
for i, nm in enumerate(("73D0","73D4","73D8","73DC","0110","011C")):
    c = collections.Counter(r["st"][i] for r in E if len(r["st"]) > i)
    print(f"  +{nm} uniq={len(c)}: " + ", ".join(f"{k}x{v}" for k, v in c.most_common(6)))

out = os.path.join(os.path.dirname(LOG), "v17_actionend_events.json")
json.dump({"E": E, "S": S, "BEAT": BEAT, "meta": meta}, open(out, "w"), indent=1)
print(f"\n→ {out}")
