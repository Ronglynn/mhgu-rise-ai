"""v31 —— 0x76154 统一落盘入口只读 hook 日志分析（变体口径）。

用法: python tools/analyze_v31_log.py <log>
输出: <log 同目录>/v31_unifyentry_events.json + 终端摘要

核心判据：
  1. P4：INSTALL h_unify 成功 / hubMask=3 / SITE +076154=E92D4FF0 / 零 FATAL
  2. Q 行活跃度（0x76154 是否真的被调用）
  3. Q.r1/r2 是否就是落盘的 (act,sub)：w1 低16位 == r1|(r2<<8)
  4. Q.r1/r2 == 同帧 A 行的 (a,s)；Q 覆盖 A 的比例
  5. Q 与 U（0x75574 上游最后一跳）同帧参数一致性
  6. 状态输入 / prev 链分布（为通用干预规则提供基线）
"""
import collections
import json
import os
import re
import sys

LOG = sys.argv[1] if len(sys.argv) > 1 else "02_Workspace/game_p54.txt"
lines = open(LOG, "rb").read().decode("utf-8", "replace").splitlines()

HEXKEYS = {"w0", "w1", "w73", "s2C0", "vt", "a0", "site"}
Q, U, A, T, J, BEAT, MON, SITE, meta = [], [], [], [], [], [], [], [], {}
for ln in lines:
    m = re.search(r"\[rai\] (.*)$", ln)
    if not m:
        continue
    s = m.group(1)
    if s.startswith(("Q ", "U ", "A ", "T ", "J ")):
        d = dict(re.findall(r"(\w+)=(\S+)", s))
        # 过滤以 "Q " 开头的说明性 banner（如 "Q = unified landing ..."）
        if "f" not in d:
            continue
        for k, v in list(d.items()):
            if k in HEXKEYS or re.fullmatch(r"[0-9A-Fa-f]{8}", v):
                try:
                    d[k] = int(v, 16)
                except ValueError:
                    pass
            elif v.lstrip("-").isdigit():
                d[k] = int(v)
        {"Q": Q, "U": U, "A": A, "T": T, "J": J}[s[0]].append(d)
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

print(f"=== v31 日志概览 ({os.path.basename(LOG)}) ===")
print(f"  Q(0x76154)={len(Q)}  U(0x75574)={len(U)}  A(动作开始)={len(A)}  "
      f"J(peek失败)={len(J)}  T={len(T)}  BEAT={len(BEAT)}  "
      f"FATAL={sum('FATAL' in l for l in lines)}")

print("\n=== 1 · P4 启动判据 ===")
for s in SITE:
    print("  " + s)
for k in ("INSTALL", "SKIP", "====="):
    for s in meta.get(k, [])[:8]:
        print("  " + s)
w = meta.get("site_076154", "-")
print(f"  SITE +076154 = {w}  "
      f"{'PASS native' if w == 'E92D4FF0' else 'CHECK (expected E92D4FF0)'}")
if BEAT:
    print("  BEAT hubMask:", collections.Counter(x.get("hub") for x in BEAT).most_common(),
          " (3 = 两个 Hub 全装)")
print(f"  FATAL = {sum('FATAL' in l for l in lines)}")

print("\n=== 2 · Q 活跃度与落盘语义 ===")
if not Q:
    print("  Q=0 -> 0x76154 入口 hook 未命中（检查 INSTALL / SKIP / 是否 FATAL）；")
    print("  若日志被 MAXLOG 截断，BEAT.log 会接近 2000。")
else:
    print(f"  eq=1: {sum(1 for x in Q if x.get('eq') == 1)}/{len(Q)}"
          f"  w0!=w1: {sum(1 for x in Q if x.get('w0') != x.get('w1'))}/{len(Q)}")
    hit_w = sum(1 for x in Q if x.get("w1") is not None and x.get("r1") is not None
                and (x["w1"] & 0xFFFF) == ((x["r1"] & 0xFF) | ((x.get("r2", 0) & 0xFF) << 8)))
    print(f"  ★ w1低16位 == r1|(r2<<8): {hit_w}/{len(Q)}"
          f"  -> 命中即确证 r1/r2 就是写进 +0x73E0 的 (act,sub)")
    amap = {x["f"]: x for x in A}
    strict = near = 0
    for x in Q:
        a = amap.get(x.get("f"))
        if a and x.get("r1") == a.get("a") and x.get("r2") == a.get("s"):
            strict += 1
        else:
            for d in (-1, 1):
                a2 = amap.get(x.get("f", 0) + d)
                if a2 and x.get("r1") == a2.get("a") and x.get("r2") == a2.get("s"):
                    near += 1
                    break
    print(f"  ★ r1/r2 == 同帧 A 的 (a,s): {strict}/{len(Q)}   ±1帧额外 {near}")
    covered = sum(1 for x in A
                  if any(q.get("f") in (x["f"] - 1, x["f"], x["f"] + 1) for q in Q))
    print(f"  ★ Q 覆盖 A（同帧或 ±1 帧）: {covered}/{len(A)}"
          f"  （v30 的 0x75574 是 63/72 = 87.5%）")
    for key in ("r1", "r2", "r3", "p5", "st", "s1A1", "s2C0", "sp", "vt"):
        vals = [x.get(key) for x in Q if key in x]
        if vals:
            top = collections.Counter(vals).most_common(10)
            if key in ("s2C0", "vt"):
                top = [(f"{k:08X}", v) for k, v in top if isinstance(k, int)]
            elif key == "sp":
                top = [(f"{k:04X}", v) if isinstance(k, int) else (str(k), v) for k, v in top]
            print(f"  {key}: {top}")
    # prev 链
    qmap = {x["f"]: x for x in Q}
    chain = tot = 0
    for x in A:
        q = qmap.get(x.get("f"))
        if not q:
            continue
        tot += 1
        wa = (x.get("a", 0) | (x.get("s", 0) << 8) |
              (x.get("pa", 0) << 16) | (x.get("ps", 0) << 24)) & 0xFFFFFFFF
        if (q.get("w0", 0) & 0xFFFF) == (wa >> 16):
            chain += 1
    print(f"  Q.w0 低16位 == A 的 prev: {chain}/{tot}")

print("\n=== 3 · Q 与 U 的参数链（0x75574 → 0x76154）===")
if Q and U:
    umap = {}
    for x in U:
        umap.setdefault(x["f"], []).append(x)
    same = tot = 0
    for q in Q:
        us = umap.get(q.get("f"), [])
        if not us:
            continue
        tot += 1
        if any(u.get("a1") == q.get("r1") and u.get("a2") == q.get("r2")
               and u.get("a3") == q.get("r3") for u in us):
            same += 1
    print(f"  同帧 U.a1/a2/a3 == Q.r1/r2/r3: {same}/{tot}"
          f"  -> 高命中率说明 0x75574 就是 0x76154 的直接上游")
    print(f"  U 行数 {len(U)} / Q 行数 {len(Q)}"
          f"  -> 差值 = 不经 0x75574 的其它 wrapper 调用")
else:
    print("  Q 或 U 为空，跳过")

print("\n=== 4 · A 行与 J 行 ===")
if A:
    print("  A.id top:", collections.Counter(x.get("id") for x in A).most_common(10))
    print("  A.st:", collections.Counter(x.get("st") for x in A).most_common())
if J:
    print("  J.site:", [(f"{k:08X}" if isinstance(k, int) else str(k), v) for k, v in
                        collections.Counter(x.get("site") for x in J).most_common()])
    print("  J.vt:", [(f"{k:08X}", v) for k, v in
                      collections.Counter(x.get("vt") for x in J if "vt" in x).most_common(6)
                      if isinstance(k, int)])

print("\n=== 5 · BEAT 尾部 ===")
for x in BEAT[-5:]:
    print("  " + str(x))

out = os.path.join(os.path.dirname(LOG), "v31_unifyentry_events.json")
json.dump({"Q": Q, "U": U, "A": A, "J": J, "T": T, "BEAT": BEAT,
           "MON": MON, "SITE": SITE, "meta": meta},
          open(out, "w"), indent=1, ensure_ascii=False)
print(f"\n→ {out}")
