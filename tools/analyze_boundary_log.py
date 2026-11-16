#!/usr/bin/env python3
"""分析 v16 动作边界探针日志：重建 217 个字段变化点，找「动作结束/提交」信号。"""
import re, json, collections, sys, os

LOG = sys.argv[1] if len(sys.argv) > 1 else r"D:/MHGU mod maker/04_RiseAI/out/game_p54_20261108_1305_v16_boundary.txt"
OFFS = [0x73D0, 0x73D4, 0x73D8, 0x73DC, 0x73E0, 0x73E4, 0x73E8, 0x73EC, 0x0110, 0x011C]

lines = open(LOG, "rb").read().decode("utf-8", "replace").splitlines()
recs, sites, ptrs, meta = [], [], [], {}
cur = None
for ln in lines:
    m = re.search(r"\[rai\] (.*)$", ln)
    if not m: continue
    s = m.group(1)
    if s.startswith("SITE "):
        sites.append(s); continue
    if s.startswith("VT ") or s.startswith("OBJ "):
        meta.setdefault(s.split()[0], s); continue
    if s.startswith("F "):
        d = dict(re.findall(r"(\w+)=(\S+)", s))
        cur = {"f": int(d["f"]), "h": int(d["h"]), "a": int(d["a"]), "s": int(d["s"]),
               "pa": int(d["pa"]), "ps": int(d["ps"]), "mask": int(d["mask"], 16), "w": []}
        recs.append(cur); continue
    if s.startswith("W ") and cur is not None:
        cur["w"] += [int(x, 16) for x in s.split()[1:]]; continue
    if s.startswith("P "):
        p = s.split()
        ptrs.append({"f": int(p[1].split("=")[1]), "v": [int(x, 16) for x in p[2:6]]}); continue

print(f"记录 {len(recs)} 条, 完整(10字) {sum(1 for r in recs if len(r['w'])==10)} 条, SITE {len(sites)}, P {len(ptrs)}")
print("=== 锚点函数字节 ===")
for s in sites: print("  " + s)
print("=== 实例 ===")
for k, v in meta.items(): print("  " + v)

# mask 位频次
mc = collections.Counter()
for r in recs:
    for i in range(10):
        if r["mask"] >> i & 1: mc[OFFS[i]] += 1
print("\n=== 各字段变化次数 (共 %d 个变化点) ===" % len(recs))
for o in OFFS: print(f"  +{o:04X}: {mc[o]:4d}  ({mc[o]*100//len(recs)}%)")

# 每字段取值分布
print("\n=== 各字段取值分布 (top 8) ===")
for i, o in enumerate(OFFS):
    c = collections.Counter(r["w"][i] for r in recs if len(r["w"]) == 10)
    print(f"  +{o:04X} uniq={len(c):4d}: " + ", ".join(f"{v:08X}x{n}" for v, n in c.most_common(8)))

# mask 组合分布
comb = collections.Counter(r["mask"] for r in recs)
print("\n=== 变化组合 mask top 15 ===")
for m, n in comb.most_common(15):
    fields = "+".join(f"{OFFS[i]:04X}" for i in range(10) if m >> i & 1)
    print(f"  {m:03X} x{n:3d}  {fields}")

# 帧间隔
gaps = [recs[i]["f"] - recs[i-1]["f"] for i in range(1, len(recs))]
print("\n=== 相邻变化点帧间隔 ===")
print(f"  min={min(gaps)} 中位={sorted(gaps)[len(gaps)//2]} max={max(gaps)}  <=3帧={sum(1 for g in gaps if g<=3)}  <=10帧={sum(1 for g in gaps if g<=10)}")
print("  分布: " + ", ".join(f"{k}帧x{v}" for k, v in collections.Counter(gaps).most_common(12)))

# 按帧聚类：<=3 帧视为同一次「动作提交」簇
clusters, cl = [], [recs[0]]
for r in recs[1:]:
    if r["f"] - cl[-1]["f"] <= 3: cl.append(r)
    else: clusters.append(cl); cl = [r]
clusters.append(cl)
print(f"\n=== 按 <=3 帧聚类: {len(clusters)} 个事件簇 ===")
print("  簇大小分布: " + ", ".join(f"{k}x{v}" for k, v in collections.Counter(len(c) for c in clusters).most_common()))

print("\n=== 前 45 个事件簇 (帧 / 动作序列 / 变化字段 / 关键字段值) ===")
for c in clusters[:45]:
    r0, rl = c[0], c[-1]
    a_seq = "+".join(f"{r['a']}/{r['s']}" for r in c)
    m = 0
    for r in c: m |= r["mask"]
    fields = ",".join(f"{OFFS[i]:04X}" for i in range(10) if m >> i & 1)
    w = rl["w"] if len(rl["w"]) == 10 else [0]*10
    print(f"  f={r0['f']:6d} n={len(c)} len={rl['f']-r0['f']:3d} a/s={a_seq:<24} mask=[{fields}] 110={w[8]:08X} 11C={w[9]:08X} 73E4={w[5]:08X} 73E8={w[6]:08X} 73EC={w[7]:08X}")

# 状态字段 0110 / 011C 与 act 关联
print("\n=== +0110 / +011C 与 act ===")
for idx, name in ((8, "0110"), (9, "011C")):
    c = collections.Counter((r["w"][idx], r["a"]) for r in recs if len(r["w"]) == 10)
    print(f"  -- {name} --")
    for (v, a), n in c.most_common(14): print(f"    {v:08X} act={a:2d}: {n}")

# P 指针稳定性
print("\n=== P 指针取值分布 ===")
for i, name in enumerate(("1428", "2588", "75F0", "75EC")):
    c = collections.Counter(p["v"][i] for p in ptrs)
    print(f"  +{name} uniq={len(c)}: " + ", ".join(f"{v:08X}x{n}" for v, n in c.most_common(6)))

out = os.path.join(os.path.dirname(LOG), "v16_boundary_events.json")
json.dump({"sites": sites, "meta": meta, "records": recs, "pointers": ptrs}, open(out, "w"), indent=1)
print(f"\n→ {out}")
