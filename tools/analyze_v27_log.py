"""v27 状态 Hub 层只读探针日志分析。

用法: python tools/analyze_v27_log.py <log>
输出: out/v27_hublayer_events.json + 终端摘要
"""
import json
import os
import re
import sys
import collections

LOG = sys.argv[1] if len(sys.argv) > 1 else "02_Workspace/game_p54.txt"
lines = open(LOG, "rb").read().decode("utf-8", "replace").splitlines()

H, A, T, BEAT, MON, SITE, meta = [], [], [], [], [], [], {}
for ln in lines:
    m = re.search(r"\[rai\] (.*)$", ln)
    if not m:
        continue
    s = m.group(1)
    if s.startswith(("H ", "A ", "T ")):
        d = dict(re.findall(r"(\w+)=(\S+)", s))
        for k, v in list(d.items()):
            if v.lstrip("-").isdigit():
                d[k] = int(v)
        (H if s.startswith("H ") else A if s.startswith("A ") else T).append(d)
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

print(f"=== v27 日志概览 ({os.path.basename(LOG)}) ===")
print(f"  H(状态Hub)={len(H)}  A(动作开始)={len(A)}  T(状态切换)={len(T)}  "
      f"MON={len(MON)}  BEAT={len(BEAT)}  FATAL={sum('FATAL' in l for l in lines)}")

print("\n=== 1 · SITE：12 个候选入口运行时首字 ===")
for s in SITE:
    print("  " + s)
std = sum(1 for k, v in meta.items() if k.startswith("site_") and v.startswith(("E92D", "E3A0")))
jump = sum(1 for k, v in meta.items() if k.startswith("site_") and v.startswith("E28FF"))
print(f"  标准 prologue ≈ {std} 个 / IPS32 跳板(add pc,pc) = {jump} 个")
print("  (被切成解释器的入口不可安全 hook：跳板是 PC 相对的)")

print("\n=== 2 · 安装状态 ===")
for k in ("INSTALL", "SKIP", "=====", "0x76154"):
    if k in meta:
        print("  " + meta[k])

if H:
    print("\n=== 3 · H 层（action-end 状态 Hub） ===")
    print(f"  a0 唯一值 {len(set(x.get('a0', 0) for x in H))} 个；"
          f"eq=1 (a0 == mon) {sum(1 for x in H if x.get('eq') == 1)}/{len(H)}")
    for key in ("st", "s1A1", "s1A8", "s2C0", "a1", "a2", "a3"):
        vals = [x.get(key) for x in H if key in x]
        if vals:
            print(f"  {key}: {collections.Counter(vals).most_common(8)}")
    hf = [x["f"] for x in H]
    gaps = [hf[i] - hf[i - 1] for i in range(1, len(hf))]
    gaps.sort()
    if gaps:
        print(f"  H 帧间隔: min={gaps[0]} 中位={gaps[len(gaps)//2]} p90={gaps[9*len(gaps)//10]} max={gaps[-1]}")

if A:
    print("\n=== 4 · A 层与 H 的时序 ===")
    dh = [x.get("dH", 0x7FFFFFFF) for x in A]
    print("  dH 分布:", collections.Counter(dh).most_common(8))
    print("  hEq 分布:", collections.Counter(x.get("hEq") for x in A).most_common())
    valid = [v for v in dh if v < 100000]
    if valid:
        valid.sort()
        print(f"  dH(有效) 中位={valid[len(valid)//2]}  ≤2帧={sum(1 for v in valid if v <= 2)}/{len(valid)}")
    print("  A (a,s) top:", collections.Counter((x.get("a"), x.get("s")) for x in A).most_common(8))
    print("  st 分布:", collections.Counter(x.get("st") for x in A).most_common())
    hps = [x.get("hp") for x in A]
    if hps:
        print(f"  HP {hps[0]} -> {hps[-1]}，变化 {sum(1 for i in range(1, len(hps)) if hps[i] != hps[i-1])} 次")

print("\n=== 5 · BEAT 尾部 ===")
for x in BEAT[-5:]:
    print("  " + str(x))

out = os.path.join(os.path.dirname(LOG), "v27_hublayer_events.json")
json.dump({"H": H, "A": A, "T": T, "BEAT": BEAT, "MON": MON, "SITE": SITE, "meta": meta},
          open(out, "w"), indent=1, ensure_ascii=False)
print(f"\n→ {out}")
