"""v29 多 Hub 只读观测日志分析。

用法: python tools/analyze_v29_log.py <log>
输出: <log 同目录>/v29_multihub_events.json + 终端摘要

判据：
  1. 4 个 Hub 是否都装上（INSTALL / hubMask=15）、零 FATAL、SITE 首字
  2. U 行按 site 分组：各 Hub 活跃度 / kind 分布 / w0->w1 / 跨对象 sp-vt
  3. 0x76908（act/sub 请求入口）的 a1/a2 是否就是 (act,sub)
  4. H 行 prev 链（v28 口径：H.w0 低16位 == A 的 prev、A.hW1 高16位 == A 的 prev）
  5. J 行：0C43xxxx 盲区是否已补上（vt/sp 非零）
"""
import collections
import json
import os
import re
import sys

LOG = sys.argv[1] if len(sys.argv) > 1 else "02_Workspace/game_p54.txt"
lines = open(LOG, "rb").read().decode("utf-8", "replace").splitlines()

HEXKEYS = {"w0", "w1", "w73", "hW1", "s1A8", "s2C0", "vt", "a0", "site"}
H, U, A, T, J, BEAT, MON, SITE, meta = [], [], [], [], [], [], [], [], {}
for ln in lines:
    m = re.search(r"\[rai\] (.*)$", ln)
    if not m:
        continue
    s = m.group(1)
    if s.startswith(("H ", "U ", "A ", "T ", "J ")):
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
        {"H": H, "U": U, "A": A, "T": T, "J": J}[tag].append(d)
    elif s.startswith("BEAT "):
        BEAT.append(dict((k, int(v, 16) if k == "mon" else int(v))
                         for k, v in re.findall(r"(\w+)=([0-9A-Fa-f]+)", s)))
    elif s.startswith("MON "):
        MON.append(s)
    elif s.startswith("SITE "):
        SITE.append(s)
        for off, word in re.findall(r"\+([0-9A-F]{6})=([0-9A-F]{8})", s):
            meta.setdefault("site_" + off, word)
    elif s.startswith(("INSTALL ", "SKIP ", "=====")):
        meta.setdefault(s.split()[0], []).append(s)

# 静态 kind 对照（`tools/disasm_hubs.py` 定案：0x76154 的 r2=kind/sub, r3=mode）
KIND = {
    0x075224: ("action-end / 状态 Hub", "r2=0/1/2 (按怒/2C0/act==11 分支), r3=2"),
    0x075338: ("状态 Hub K3", "r1=0, r2=3, r3=2"),
    0x075394: ("状态 Hub K6", "r1=0, r2=6, r3=2"),
    0x076908: ("act/sub 请求入口", "r1=a1(act), r2=a2(sub), r3=5；7420==0 时暂存 73E6/73E7"),
}

print(f"=== v29 日志概览 ({os.path.basename(LOG)}) ===")
print(f"  H(0x75224)={len(H)}  U(3 个额外 Hub)={len(U)}  A(动作开始)={len(A)}  "
      f"J(peek失败)={len(J)}  T(状态切换)={len(T)}  BEAT={len(BEAT)}  "
      f"FATAL={sum('FATAL' in l for l in lines)}")

print("\n=== 1 · SITE 与安装 ===")
for s in SITE:
    print("  " + s)
for k in ("INSTALL", "SKIP", "====="):
    for s in meta.get(k, [])[:8]:
        print("  " + s)
if BEAT:
    print(f"  BEAT hubMask: {collections.Counter(x.get('hub') for x in BEAT).most_common()}")
    print("  -> hubMask=15 表示 4 个 Hub 全部安装成功；低位置 0 的位对应 SKIP")

print("\n=== 2 · U 行按 site 分组（本轮核心）===")
if not U:
    print("  无 U 行：3 个额外 Hub 本场均未被调用（或日志被 MAXLOG 截断）")
    print("  -> 若 H 正常而 U=0，说明常规链只走 0x75224；下轮换 0x75510/0x75574 等入口")
else:
    bysite = collections.defaultdict(list)
    for x in U:
        bysite[x.get("site", 0)].append(x)
    for site, rows in sorted(bysite.items()):
        name, kind = KIND.get(site, ("未知 site", "?"))
        print(f"\n  -- site={site:06X}  {name} --")
        print(f"     n={len(rows)}  eq=1: {sum(1 for x in rows if x.get('eq') == 1)}/{len(rows)}"
              f"  w0!=w1: {sum(1 for x in rows if x.get('w0') != x.get('w1'))}/{len(rows)}")
        print(f"     静态: {kind}")
        for key in ("a0", "a1", "a2", "a3", "st", "s1A1", "s2C0", "sp", "vt"):
            vals = [x.get(key) for x in rows if key in x]
            if not vals:
                continue
            top = collections.Counter(vals).most_common(8)
            fmt = "08X" if key in ("a0", "s2C0", "vt") else "04X" if key == "sp" else None
            if fmt:
                top = [(format(k, fmt) if isinstance(k, int) else str(k), v) for k, v in top]
            print(f"     {key}: {top}")
        fr = sorted(x["f"] for x in rows if "f" in x)
        if len(fr) > 1:
            gaps = sorted(fr[i] - fr[i - 1] for i in range(1, len(fr)))
            print(f"     帧范围 {fr[0]}..{fr[-1]}  间隔中位={gaps[len(gaps)//2]} max={gaps[-1]}")

print("\n=== 3 · H 行（v28 对照：prev 链 / Hub 输入）===")
if H:
    print(f"  eq=1: {sum(1 for x in H if x.get('eq') == 1)}/{len(H)}"
          f"  w0!=w1: {sum(1 for x in H if x.get('w0') != x.get('w1'))}/{len(H)}")
    for key in ("st", "s1A1", "s1A8", "s2C0", "sp", "vt"):
        vals = [x.get(key) for x in H if key in x]
        if vals:
            top = collections.Counter(vals).most_common(6)
            if key in ("s1A8", "s2C0", "vt"):
                top = [(f"{k:08X}", v) for k, v in top if isinstance(k, int)]
            elif key == "sp":
                top = [(f"{k:04X}", v) for k, v in top if isinstance(k, int)]
            print(f"  {key}: {top}")
else:
    print("  无 H 行")

print("\n=== 4 · A 行 / prev 链 ===")
if A:
    hit_w1 = hit_hi = 0
    for x in A:
        wa = (x.get("a", 0) | (x.get("s", 0) << 8) |
              (x.get("pa", 0) << 16) | (x.get("ps", 0) << 24)) & 0xFFFFFFFF
        if x.get("hW1") == wa:
            hit_w1 += 1
        if (x.get("hW1", 0) >> 16) == (wa >> 16):
            hit_hi += 1
    print(f"  hW1 全等 A 字段: {hit_w1}/{len(A)}（中间态，不全等属预期）")
    print(f"  hW1 高16位 == A 的 prev: {hit_hi}/{len(A)}")
    hmap = {x["f"]: x for x in H}
    chain = tot = 0
    for x in A:
        h = hmap.get(x.get("f"))
        if not h:
            continue
        tot += 1
        wa = (x.get("a", 0) | (x.get("s", 0) << 8) |
              (x.get("pa", 0) << 16) | (x.get("ps", 0) << 24)) & 0xFFFFFFFF
        if (h.get("w0", 0) & 0xFFFF) == (wa >> 16):
            chain += 1
    print(f"  H.w0 低16位 == A 的 prev: {chain}/{tot}  -> GU 自带 prev 表在 action-end 更新")
    print("  dH 分布:", collections.Counter(x.get("dH") for x in A).most_common(8))
    print("  id top:", collections.Counter(x.get("id") for x in A).most_common(10))
else:
    print("  无 A 行")

print("\n=== 5 · J 行（盲区是否补上 / 跨对象身份）===")
if J:
    print("  site 分布:", [(f"{k:06X}" if isinstance(k, int) else str(k), v) for k, v in
                          collections.Counter(x.get("site") for x in J).most_common()])
    for key in ("a0", "vt", "sp"):
        top = collections.Counter(x.get(key) for x in J if key in x).most_common(12)
        fmt = "08X" if key in ("a0", "vt") else "04X"
        print(f"  {key}: {[(format(k, fmt) if isinstance(k, int) else str(k), v) for k, v in top]}")
    wide = [x for x in J if 0x0C400000 <= x.get("a0", 0) < 0x0C500000]
    print(f"  a0 落在 0C400000..0C500000（v28 盲区）: {len(wide)} 条；"
          f"其中 vt!=0: {sum(1 for x in wide if x.get('vt'))}, "
          f"sp!=0: {sum(1 for x in wide if x.get('sp'))}")
    print("  -> 若 vt/sp 非零且合理，说明放宽 HEAP_HI 后盲区已补，可判定是否另一只怪")
else:
    print("  无 J 行（本场无 peek 失败调用）")

print("\n=== 6 · BEAT 尾部 ===")
for x in BEAT[-5:]:
    print("  " + str(x))

out = os.path.join(os.path.dirname(LOG), "v29_multihub_events.json")
json.dump({"H": H, "U": U, "A": A, "J": J, "T": T, "BEAT": BEAT,
           "MON": MON, "SITE": SITE, "meta": meta},
          open(out, "w"), indent=1, ensure_ascii=False)
print(f"\n→ {out}")
