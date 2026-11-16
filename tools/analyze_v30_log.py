"""v30 带 (act,sub) 提交入口多 Hub 只读观测日志分析。

用法: python tools/analyze_v30_log.py <log>
输出: <log 同目录>/v30_submithub_events.json + 终端摘要

本轮核心判据（比 v29 更进一步）：
  1. 5 个 Hub 是否全装（hubMask=31）、零 FATAL
  2. U 行按 site 分组：哪些「带 (act,sub) 提交入口」真的活跃
  3. **U.w1 低16位 == a1 | (a2<<8)** —— 直接确证 a1/a2 就是落盘的 (act,sub)
  4. **U.a1/a2 与同帧 A 行的 (a,s) 对齐率** —— 判定该入口是否是
     「抽选结果落盘前最后一跳」，即合规的通用干预层
  5. U 行对 A 行的覆盖率（同帧或 ±1 帧）
  6. H-A prev 链、J 行跨对象身份（v28/v29 口径）
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
        {"H": H, "U": U, "A": A, "T": T, "J": J}[s[0]].append(d)
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

SITES = {
    0x075224: ("action-end 状态 Hub（对照）", "vtable 槽，BL=0；传 r1=0,r2=kind,r3=2"),
    0x076AFC: ("(act,sub) 提交 S1", "51 共享区调用者；r1=act,r2=sub,r3=5"),
    0x076984: ("(act,sub) 提交 S2", "354 每怪区调用者；含 +0x73E0==11 与 +0x7420 门控"),
    0x076AB0: ("(act,sub) 提交 S3", "42 每怪区调用者；r3=1"),
    0x075574: ("(act,sub,mode) 直通 S4", "4 共享区调用者；a1/a2/a3 原样透传 0x76154"),
}

print(f"=== v30 日志概览 ({os.path.basename(LOG)}) ===")
print(f"  H(0x75224)={len(H)}  U(4 个提交入口)={len(U)}  A(动作开始)={len(A)}  "
      f"J(peek失败)={len(J)}  T(状态切换)={len(T)}  BEAT={len(BEAT)}  "
      f"FATAL={sum('FATAL' in l for l in lines)}")

print("\n=== 1 · SITE 与安装 ===")
for s in SITE:
    print("  " + s)
for k in ("INSTALL", "SKIP", "====="):
    for s in meta.get(k, [])[:10]:
        print("  " + s)
if BEAT:
    print(f"  BEAT hubMask: {collections.Counter(x.get('hub') for x in BEAT).most_common()}")
    print("  -> hubMask=31 表示 5 个 Hub 全部安装成功；低位置 0 的位对应 SKIP")

print("\n=== 2 · U 行按 site 分组（本轮核心）===")
if not U:
    print("  无 U 行：4 个提交入口本场均未被调用（或日志被 MAXLOG 截断）")
    print("  -> 结合 BEAT.log 判断：若 log 远小于 2000，则确实没调用，")
    print("     说明常规链只有 0x75224 → 0x76154 → 0xAFF40，应转路线 2（inline hook）")
else:
    amap = {x["f"]: x for x in A}
    bysite = collections.defaultdict(list)
    for x in U:
        bysite[x.get("site", 0)].append(x)
    for site, rows in sorted(bysite.items()):
        name, desc = SITES.get(site, ("未知 site", "?"))
        print(f"\n  -- site={site:06X}  {name} --")
        print(f"     n={len(rows)}  eq=1: {sum(1 for x in rows if x.get('eq') == 1)}/{len(rows)}"
              f"  w0!=w1: {sum(1 for x in rows if x.get('w0') != x.get('w1'))}/{len(rows)}")
        print(f"     {desc}")
        # ★ 判据 3：w1 低 16 位是否就是 a1 | (a2<<8)
        hit_w = tot_w = 0
        for x in rows:
            if x.get("w1") is None or x.get("a1") is None or x.get("a2") is None:
                continue
            tot_w += 1
            if (x["w1"] & 0xFFFF) == ((x["a1"] & 0xFF) | ((x["a2"] & 0xFF) << 8)):
                hit_w += 1
        print(f"     ★ w1低16位 == a1|(a2<<8): {hit_w}/{tot_w}"
              f"  -> 命中即确证 a1/a2 就是落盘的 (act,sub)")
        # ★ 判据 4：a1/a2 与同帧 A 行 (a,s) 对齐
        strict = near = 0
        for x in rows:
            a = amap.get(x.get("f"))
            if a and x.get("a1") == a.get("a") and x.get("a2") == a.get("s"):
                strict += 1
            else:
                for d in (-1, 1):
                    a2 = amap.get(x.get("f", 0) + d)
                    if a2 and x.get("a1") == a2.get("a") and x.get("a2") == a2.get("s"):
                        near += 1
                        break
        print(f"     ★ a1/a2 == 同帧 A 的 (a,s): {strict}/{len(rows)}"
              f"  ±1帧额外命中 {near}  -> 高命中率 = 抽选结果落盘前最后一跳")
        for key in ("a1", "a2", "a3", "st", "s2C0", "sp", "vt"):
            vals = [x.get(key) for x in rows if key in x]
            if vals:
                top = collections.Counter(vals).most_common(8)
                if key in ("s2C0", "vt"):
                    top = [(f"{k:08X}", v) for k, v in top if isinstance(k, int)]
                elif key == "sp":
                    top = [(f"{k:04X}", v) if isinstance(k, int) else (str(k), v) for k, v in top]
                print(f"     {key}: {top}")
        fr = sorted(x["f"] for x in rows if "f" in x)
        if len(fr) > 1:
            gaps = sorted(fr[i] - fr[i - 1] for i in range(1, len(fr)))
            print(f"     帧范围 {fr[0]}..{fr[-1]}  间隔中位={gaps[len(gaps)//2]} max={gaps[-1]}")
    # 判据 5：U 对 A 的覆盖率
    covered = 0
    for x in A:
        if any(u["f"] in (x["f"] - 1, x["f"], x["f"] + 1) for u in U):
            covered += 1
    print(f"\n  ★ U 覆盖 A（同帧或 ±1 帧）: {covered}/{len(A)}")

print("\n=== 3 · H 行（v28/v29 对照：prev 链 / Hub 输入）===")
if H:
    print(f"  eq=1: {sum(1 for x in H if x.get('eq') == 1)}/{len(H)}"
          f"  w0!=w1: {sum(1 for x in H if x.get('w0') != x.get('w1'))}/{len(H)}")
    print("  s2C0 低字节:", collections.Counter((x.get("s2C0", 0) & 0xFF) for x in H).most_common())
    print("  st:", collections.Counter(x.get("st") for x in H).most_common())
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
    print(f"  H.w0 低16位 == A 的 prev: {chain}/{tot}")
    print("  A.dH 分布:", collections.Counter(x.get("dH") for x in A).most_common(8))
else:
    print("  无 H 行")

print("\n=== 4 · J 行（peek 失败调用者 / 哪些 site 有非主怪调用）===")
if J:
    print("  site 分布:", [(f"{k:06X}" if isinstance(k, int) else str(k), v) for k, v in
                          collections.Counter(x.get("site") for x in J).most_common()])
    for key in ("a0", "vt", "sp"):
        top = collections.Counter(x.get(key) for x in J if key in x).most_common(8)
        fmt = "08X" if key in ("a0", "vt") else "04X"
        print(f"  {key}: {[(format(k, fmt) if isinstance(k, int) else str(k), v) for k, v in top]}")
else:
    print("  无 J 行")

print("\n=== 5 · BEAT 尾部 ===")
for x in BEAT[-5:]:
    print("  " + str(x))

out = os.path.join(os.path.dirname(LOG), "v30_submithub_events.json")
json.dump({"H": H, "U": U, "A": A, "J": J, "T": T, "BEAT": BEAT,
           "MON": MON, "SITE": SITE, "meta": meta},
          open(out, "w"), indent=1, ensure_ascii=False)
print(f"\n→ {out}")
