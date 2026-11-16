"""v28 状态 Hub 因果确证日志分析。

用法: python tools/analyze_v28_log.py <log>
输出: out/v28_hubcause_events.json + 终端摘要

判据：
  1. H.w0 -> H.w1 变化率（action-end 内部是否重写 +0x73E0）
  2. A.hW1 == A 行反推的 +0x73E0（w1 是否就是随后动作开始时读到的字段）
  3. J 行 a0/vt/sp 分布（skip 的调用者是其它怪还是非怪对象 → 跨怪通用）
  4. Hub 输入字段与 st / hp / id 的对齐
"""
import json
import os
import re
import sys
import collections

LOG = sys.argv[1] if len(sys.argv) > 1 else "02_Workspace/game_p54.txt"
lines = open(LOG, "rb").read().decode("utf-8", "replace").splitlines()

HEXKEYS = {"w0", "w1", "w73", "hW1", "s1A8", "s2C0", "vt", "a0"}
H, A, T, J, BEAT, MON, SITE, meta = [], [], [], [], [], [], [], {}
for ln in lines:
    m = re.search(r"\[rai\] (.*)$", ln)
    if not m:
        continue
    s = m.group(1)
    if s.startswith(("H ", "A ", "T ", "J ")):
        d = dict(re.findall(r"(\w+)=(\S+)", s))
        for k, v in list(d.items()):
            if k in HEXKEYS or re.fullmatch(r"[0-9A-Fa-f]{8}", v):
                try:
                    d[k] = int(v, 16)
                except ValueError:
                    pass
            elif v.lstrip("-").isdigit():
                d[k] = int(v)
        tag = s[0]
        (H if tag == "H" else A if tag == "A" else T if tag == "T" else J).append(d)
    elif s.startswith("BEAT "):
        BEAT.append(dict((k, int(v)) for k, v in re.findall(r"(\w+)=(\d+)", s)))
    elif s.startswith("MON "):
        MON.append(s)
    elif s.startswith("SITE "):
        SITE.append(s)
        for off, word in re.findall(r"\+([0-9A-F]{6})=([0-9A-F]{8})", s):
            meta.setdefault("site_" + off, word)
    elif s.startswith(("INSTALL ", "SKIP ", "=====", "0x76154")):
        meta.setdefault(s.split()[0], s)

print(f"=== v28 日志概览 ({os.path.basename(LOG)}) ===")
print(f"  H(状态Hub)={len(H)}  A(动作开始)={len(A)}  J(其它调用者)={len(J)}  "
      f"T(状态切换)={len(T)}  BEAT={len(BEAT)}  FATAL={sum('FATAL' in l for l in lines)}")

print("\n=== 1 · SITE 与安装 ===")
for s in SITE:
    print("  " + s)
for k in ("INSTALL", "SKIP", "====="):
    if k in meta:
        print("  " + meta[k])

print("\n=== 2 · 因果判据 ①：H.w0 -> H.w1 ===")
if H:
    have = [x for x in H if x.get("w1") is not None]
    if not have:
        print("  本日志无 w1 字段（v27 及更早），跳过该判据")
    else:
        chg = sum(1 for x in have if x.get("w0") != x.get("w1"))
        print(f"  w0 != w1: {chg}/{len(have)}  ({chg/len(have)*100:.0f}%)")
        for key in ("w0", "w1"):
            top = [(f"{k:08X}", v) for k, v in
                   collections.Counter(x.get(key) for x in have if x.get(key) is not None).most_common(5)]
            print(f"  {key} top: {top}")

print("\n=== 3 · 因果判据 ②：prev 链（H.w0 低16位 -> A 高16位）===")
if A:
    hit = hit_w1 = 0
    for x in A:
        wa = (x.get('a', 0) | (x.get('s', 0) << 8) |
              (x.get('pa', 0) << 16) | (x.get('ps', 0) << 24)) & 0xFFFFFFFF
        if x.get('hW1') == wa:
            hit_w1 += 1
        if (x.get('hW1', 0) >> 16) == (wa >> 16):
            hit += 1
    print(f"  hW1 全等 A 字段: {hit_w1}/{len(A)}  (w1 是 decision-in-progress 中间态，不全等属预期)")
    print(f"  hW1 高16位 == A 的 prev: {hit}/{len(A)}  -> action-end 内已完成 prev 移位")
    amap_h = {x['f']: x for x in H}
    chain = tot = 0
    for x in A:
        h = amap_h.get(x['f'])
        if not h:
            continue
        tot += 1
        wa = (x.get('a', 0) | (x.get('s', 0) << 8) |
              (x.get('pa', 0) << 16) | (x.get('ps', 0) << 24)) & 0xFFFFFFFF
        if (h.get('w0', 0) & 0xFFFF) == (wa >> 16):
            chain += 1
    print(f"  H.w0 低16位 == A 的 prev: {chain}/{tot}  -> GU 自带 prev 表在 action-end 更新")
    dh = collections.Counter(x.get("dH") for x in A)
    print("  dH 分布:", dh.most_common(8))
    print("  hEq 分布:", collections.Counter(x.get("hEq") for x in A).most_common())

print("\n=== 4 · 因果判据 ③：J 行（skip 的调用者身份）===")
if J:
    for key, fmt in (("a0", "08X"), ("vt", "08X"), ("sp", "04X")):
        top = [(format(k, fmt) if isinstance(k, int) else str(k), v) for k, v in
               collections.Counter(x.get(key) for x in J if x.get(key) is not None).most_common(12)]
        print(f"  {key} 唯一值: {top}")
    inrange = sum(1 for x in J if 0x0C000000 <= x.get('a0', 0) < 0x0C400000)
    print(f"  a0 在堆区 {inrange}/{len(J)}；vt 落在 0x01900000..0x02000000 的 "
          f"{sum(1 for x in J if 0x01900000 <= x.get('vt', 0) < 0x02000000)} 个")
    print("  -> vt 落在 vtable 区且 sp 合理 = 其它怪；vt=0/异常 = 非怪对象或指针无效")
else:
    print("  无 J 行（本场无 peek 失败调用）")

print("\n=== 5 · Hub 输入字段 ===")
if H:
    print("  eq=1:", sum(1 for x in H if x.get('eq') == 1), "/", len(H))
    for key in ("st", "s1A1", "s1A8", "s2C0"):
        vals = [x.get(key) for x in H if key in x]
        if vals:
            top = collections.Counter(vals).most_common(8)
            if key in ("s1A8", "s2C0"):
                top = [(f"{k:08X}", v) for k, v in top if k is not None]
            print(f"  {key}: {top}")
    hf = [x["f"] for x in H]
    g = sorted(hf[i] - hf[i - 1] for i in range(1, len(hf)))
    if g:
        print(f"  H 间隔: min={g[0]} 中位={g[len(g)//2]} p90={g[9*len(g)//10]} max={g[-1]}")

print("\n=== 6 · BEAT 尾部 ===")
for x in BEAT[-5:]:
    print("  " + str(x))

out = os.path.join(os.path.dirname(LOG), "v28_hubcause_events.json")
json.dump({"H": H, "A": A, "J": J, "T": T, "BEAT": BEAT, "MON": MON,
           "SITE": SITE, "meta": meta}, open(out, "w"), indent=1, ensure_ascii=False)
print(f"\n→ {out}")
