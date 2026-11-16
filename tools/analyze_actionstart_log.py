#!/usr/bin/env python3
"""分析 v19 入口定位探针日志：BL 调用图判入口、A/E 配对、action_id / duration 白名单。

用法：python tools/analyze_actionstart_log.py [日志路径]
默认读 02_Workspace/game_p54.txt；输出 JSON 写到日志同目录。
"""
import re, json, collections, sys, os, struct

LOG = sys.argv[1] if len(sys.argv) > 1 else r"D:/MHGU mod maker/02_Workspace/game_p54.txt"
lines = open(LOG, "rb").read().decode("utf-8", "replace").splitlines()
E, A, D, X, H, G, M, BEAT, SITE, CALL, meta = [], [], [], [], [], [], [], [], [], [], {}
for ln in lines:
    m = re.search(r"\[rai\] (.*)$", ln)
    if not m: continue
    s = m.group(1)
    if s.startswith(("E ", "A ", "D ")):
        d = dict(re.findall(r"(\w+)=(\S+)", s))
        rec = {}
        for k, v in d.items():
            rec[k] = int(v, 16) if k in ("this", "dur", "x") else (int(v) if v.lstrip("-").isdigit() else v)
        (E if s.startswith("E") else A if s.startswith("A") else D).append(rec)
    elif s.startswith("X "):
        mm = re.match(r"X f=(\d+) w=(\w+) \+([0-9A-Fa-f]+) ([0-9A-Fa-f]+)->([0-9A-Fa-f]+)", s)
        if mm:
            X.append(dict(f=int(mm.group(1)), w=mm.group(2), off=int(mm.group(3), 16),
                          old=int(mm.group(4), 16), new=int(mm.group(5), 16)))
    elif s.startswith(("H ", "G ", "M ")):
        (H if s.startswith("H") else G if s.startswith("G") else M).append(s)
    elif s.startswith("BEAT "):
        BEAT.append(dict((k, int(v)) for k, v in re.findall(r"([A-Za-z0-9_/]+)=(\d+)", s)))
    elif s.startswith("SITE "):
        SITE.append(s)
    elif s.startswith("CALL "):
        CALL.append(s)
    elif s.startswith(("INSTALL ", "SKIP ", "FALLBACK ", "=====")):
        meta.setdefault(s.split()[0], s)

print(f"E(结束)={len(E)}  A(开始)={len(A)}  D(dispatch)={len(D)}  X(字段差分)={len(X)}  H={len(H)} G={len(G)} M={len(M)}  BEAT={len(BEAT)}")
for k, v in meta.items(): print("  " + v)
print("\n=== 锚点 / 函数边界字节 ===")
for s in SITE: print("  " + s)
print("\n=== BL 调用图（入口判定，最关键） ===")
for s in CALL: print("  " + s)
if BEAT:
    print("\n=== BEAT 尾部 ===")
    for b in BEAT[-4:]: print("  " + str(b))

def stats(name, xs):
    xs = sorted(xs)
    if not xs: return
    print(f"  {name}: n={len(xs)} min={xs[0]} p25={xs[len(xs)//4]} 中位={xs[len(xs)//2]} "
          f"p75={xs[3*len(xs)//4]} max={xs[-1]} 均值={sum(xs)/len(xs):.1f}")

print("\n=== A.dE (END -> START 帧差) ===")
stats("A.dE", [r["dE"] for r in A if r.get("dE", 0) < 10000])
print("  分布: " + ", ".join(f"{k}帧x{v}" for k, v in collections.Counter(r["dE"] for r in A).most_common(10)))
print(f"  dE<=2: {sum(1 for r in A if r.get('dE',9999)<=2)}/{len(A)}")

print("\n=== action_id 分布 (A 行) ===")
c = collections.Counter(r.get("id", -1) for r in A)
print(f"  uniq={len(c)}  " + ", ".join(f"id={k}x{v}" for k, v in c.most_common(25)))

print("\n=== duration 位模式 -> float ===")
cd = collections.Counter(r.get("dur", 0) for r in A)
for bits, n in cd.most_common(12):
    f = struct.unpack("<f", struct.pack("<I", bits))[0]
    print(f"  {bits:08X} ({f:8.3f}) x{n}")

print("\n=== id × (act,sub) 交叉 (前 25) ===")
cx = collections.Counter((r.get("id", -1), r.get("a"), r.get("s")) for r in A)
for (i, a, s), n in cx.most_common(25): print(f"  id={i:5d} act={a}/{s}: {n}")

print("\n=== 按 id 分组的 dur / dE ===")
for i, n in c.most_common(10):
    sub = [r for r in A if r.get("id") == i]
    print(f"  id={i:5d} n={n:3d} dur={collections.Counter(r.get('dur') for r in sub).most_common(3)} dE={collections.Counter(r.get('dE') for r in sub).most_common(3)}")

if D:
    print("\n=== D(dispatch fallback) k 分布 / dE ===")
    print("  k: " + ", ".join(f"{k}x{v}" for k, v in collections.Counter(r.get("k") for r in D).most_common(15)))
    stats("D.dE", [r["dE"] for r in D if r.get("dE", 0) < 10000])

print("\n=== E 动作周期 ===")
stats("E.dE", [r["dE"] for r in E if r.get("dE", 0) < 10000])

print("\n=== X 字段差分：act(+0x180..0x1C0) / EMC(+0x00..0x40) ===")
cx = collections.Counter((r["w"], r["off"]) for r in X)
print(f"  变化字段 {len(cx)} 个；top 25:")
for (w, off), n in cx.most_common(25): print(f"    {w}+{off:03X}: {n} 次")
ef = sorted(r["f"] for r in E)
def near_end(f):
    # 二分找 [f-2, f+2] 内是否有 END
    import bisect
    i = bisect.bisect_left(ef, f - 2)
    return i < len(ef) and ef[i] <= f + 2
print("\n  与 END 帧 ±2 对齐的字段（字段层 act 信号候选）:")
rows = []
for (w, off), n in cx.items():
    sub = [r for r in X if r["w"] == w and r["off"] == off]
    k = sum(1 for r in sub if near_end(r["f"]))
    if k: rows.append((k, k / len(sub), n, w, off))
for k, ratio, n, w, off in sorted(rows, reverse=True)[:20]:
    flag = " <== 候选" if k >= 3 and ratio >= 0.5 else ""
    print(f"    {w}+{off:03X}: 对齐 {k}/{n} ({ratio:.0%}){flag}")

print("\n=== H 快照（act 对象 / HP Bar 链） ===")
for s in H[:6]: print("  " + s)
if len(H) > 6: print(f"  ... 共 {len(H)} 条，末条: {H[-1]}")
print("\n=== G 全局 / M 管理器→怪指针 ===")
for s in G[:2]: print("  " + s)
if len(G) > 2: print(f"  ... 末条: {G[-1]}")
mo = collections.Counter(re.search(r"mgr\+([0-9A-F]+)", s).group(1) for s in M if re.search(r"mgr\+([0-9A-F]+)", s))
print(f"  M 命中 {len(M)} 条，偏移分布: {dict(mo.most_common(10))}")

out = os.path.join(os.path.dirname(LOG), "v19b_entry_act_events.json")
json.dump({"E": E, "A": A, "D": D, "X": X, "H": H, "G": G, "M": M,
           "BEAT": BEAT, "SITE": SITE, "CALL": CALL, "meta": meta}, open(out, "w"), indent=1)
print(f"\n→ {out}")
