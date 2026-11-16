"""v13-a 只读探针日志离线分析（04_RiseAI 专用，不触碰音频线）。

输入: out/game_p54_20261108_1220_v13a_context.txt (Recomp log.txt 备份)
输出: out/v13a_decisions.json + 控制台摘要

目的:
  1. 量化「原版基线」的攻击密度 / 状态切换 / 输出窗口（用户 12:20 体感）。
  2. 从 CTX 的 24 个字里找出随决策变化的字段：动作计时器、前动作记录、状态字节。
  3. 找「一个完整动作何时结束」的可用信号，供下一阶段在真正的动作提交点做否决式干预。
"""
import re
import json
import collections
import statistics
import os

ROOT = r"D:\MHGU mod maker\04_RiseAI"
LOG = os.path.join(ROOT, "out", "game_p54_20261108_1220_v13a_context.txt")
OUT = os.path.join(ROOT, "out", "v13a_decisions.json")

RE_DEC = re.compile(r"\[rai\] DEC n=(\d+) obj=([0-9A-Fa-f]+) act=(\d+) sub=(\d+) hit=(\d+)")
RE_CTX = re.compile(r"\[rai\] CTX n=(\d+) g=(\d+) \+([0-9A-Fa-f]{3,4})\s+((?:[0-9A-Fa-f]{8}\s*){8})")
RE_BEAT = re.compile(r"\[rai\] BEAT f=(\d+) hit=(\d+) dec=(\d+)")

BASE = {1: 0x40, 2: 0x100, 3: 0x73D0}

decisions = {}
beats = []
with open(LOG, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        m = RE_DEC.search(line)
        if m:
            n = int(m.group(1))
            decisions[n] = {
                "n": n, "obj": m.group(2), "act": int(m.group(3)),
                "sub": int(m.group(4)), "hit": int(m.group(5)), "words": {},
            }
            continue
        m = RE_CTX.search(line)
        if m:
            n, g = int(m.group(1)), int(m.group(2))
            words = m.group(4).split()
            d = decisions.get(n)
            if d is None or len(words) != 8:
                continue
            base = int(m.group(3), 16)
            assert base == BASE[g], (g, hex(base))
            for i, w in enumerate(words):
                d["words"][base + 4 * i] = int(w, 16)
            continue
        m = RE_BEAT.search(line)
        if m:
            beats.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))

dec = [decisions[k] for k in sorted(decisions)]
print(f"decisions={len(dec)} beats={len(beats)}")

# ---- 1. 时间轴：用 BEAT(f, hit) 线性插值把 hit 换算成近似帧 ----
def hit_to_frame(hit):
    if not beats:
        return hit
    prev = beats[0]
    for b in beats:
        if b[1] >= hit:
            if b[1] == prev[1]:
                return b[0]
            return prev[0] + (hit - prev[1]) * (b[0] - prev[0]) / (b[1] - prev[1])
        prev = b
    return beats[-1][0]

for d in dec:
    d["frame"] = round(hit_to_frame(d["hit"]))

# ---- 2. 决策序列：act / sub / 转移 / 间隔 ----
acts = collections.Counter(d["act"] for d in dec)
subs = collections.Counter(d["sub"] for d in dec)
print("\n[act 分布]", dict(sorted(acts.items())))
print("[sub 分布 top12]", subs.most_common(12), f"共 {len(subs)} 种")

gaps = [dec[i]["hit"] - dec[i - 1]["hit"] for i in range(1, len(dec))]
fgaps = [dec[i]["frame"] - dec[i - 1]["frame"] for i in range(1, len(dec))]
def pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(len(v) * p))] if v else 0
print(f"[决策间隔 hit] min={min(gaps)} p25={pct(gaps,.25)} med={statistics.median(gaps)} p75={pct(gaps,.75)} max={max(gaps)}")
print(f"[决策间隔 帧] min={min(fgaps)} p25={pct(fgaps,.25)} med={statistics.median(fgaps)} p75={pct(fgaps,.75)} max={max(fgaps)}")
print(f"[间隔 <=30 帧] {sum(1 for x in fgaps if x <= 30)}/{len(fgaps)} = {sum(1 for x in fgaps if x <= 30)/len(fgaps):.1%}")
print(f"[间隔 <=60 帧] {sum(1 for x in fgaps if x <= 60)}/{len(fgaps)} = {sum(1 for x in fgaps if x <= 60)/len(fgaps):.1%}")

trans = collections.Counter((dec[i - 1]["act"], dec[i]["act"]) for i in range(1, len(dec)))
print("\n[act 转移 top15]", trans.most_common(15))

# 非攻击类 act 之后紧接攻击类 act 的间隔（用户说的「硬直/倒地被覆盖」候选）
NONATK = {0, 6, 10}
ov = [(dec[i - 1]["act"], dec[i]["act"], fgaps[i - 1]) for i in range(1, len(dec))
      if dec[i - 1]["act"] in NONATK and dec[i]["act"] not in NONATK]
print(f"[非攻击类->攻击类 次数] {len(ov)} / 非攻击类出现 {sum(1 for i in range(1,len(dec)) if dec[i-1]['act'] in NONATK)}")
if ov:
    g = [x[2] for x in ov]
    print(f"  间隔帧 min={min(g)} med={statistics.median(g)} <=60帧={sum(1 for x in g if x<=60)}/{len(g)}")

# (act,sub) 复现
seq = [(d["act"], d["sub"]) for d in dec]
for w in (3, 5, 8):
    rep = sum(1 for i, s in enumerate(seq) if s in seq[max(0, i - w):i])
    print(f"[窗口{w} 同招复现] {rep}/{len(seq)} = {rep/len(seq):.4f}")

# ---- 3. 字段差分：哪个偏移在变 ----
offs = sorted({o for d in dec for o in d["words"]})
print(f"\n[字段偏移] 共 {len(offs)} 个: {[hex(o) for o in offs]}")
rows = []
for o in offs:
    vals = [d["words"].get(o) for d in dec]
    uniq = len(set(vals))
    chg = sum(1 for i in range(1, len(vals)) if vals[i] != vals[i - 1])
    top = collections.Counter(vals).most_common(3)
    rows.append((o, uniq, chg, top))
print("\n[按变化次数排序] off | uniq | chg | top3")
for o, uniq, chg, top in sorted(rows, key=lambda x: -x[2]):
    print(f"  +{o:04X} | {uniq:4d} | {chg:4d} | {[(hex(v), c) for v, c in top]}")

# ---- 4. 字节级：找 act/sub/prev/计时器 ----
print("\n[字节级变化次数 top30] (off+idx | chg | uniq)")
brows = []
for o in offs:
    for j in range(4):
        vals = []
        for d in dec:
            w = d["words"].get(o)
            vals.append(None if w is None else (w >> (8 * j)) & 0xFF)
        uniq = len(set(vals))
        chg = sum(1 for i in range(1, len(vals)) if vals[i] != vals[i - 1])
        brows.append((o + j, chg, uniq, vals))
for off, chg, uniq, vals in sorted(brows, key=lambda x: -x[1])[:30]:
    print(f"  +{off:04X} | {chg:4d} | {uniq:3d} | 首8={vals[:8]}")

json.dump({"decisions": dec, "beats": beats}, open(OUT, "w"), indent=1)
print(f"\n[写出] {OUT}")
