"""v25 抽选层只读探针日志分析。

用法: python tools/analyze_v25_log.py <log>
输出: out/v25_selectlayer_events.json + 终端摘要

判据（对应 STATUS.md S5 第 1 步）：
  1. INSTALL sel=1 且 G 有数据 —— 0x752EC 在目标怪上确实被调用；
  2. A.dG ≈ 0 —— G 发生在 A 同帧之前（提交点早于动作开始）；
  3. G.w1 低字节 == G.act、次字节 == G.sub —— 落盘字段与传入参数一致；
  4. A.gAct/gSub == A.a/s —— 抽选结果一路传到动作开始，无中途改写。
"""
import re, json, os, sys, collections

LOG = sys.argv[1] if len(sys.argv) > 1 else r"02_Workspace/game_p54.txt"
if not os.path.isabs(LOG) and not os.path.exists(LOG):
    LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), LOG)
lines = open(LOG, "rb").read().decode("utf-8", "replace").splitlines()

G, A, T, MON, BEAT, meta = [], [], [], [], [], {}
for ln in lines:
    m = re.search(r"\[rai\] (.*)$", ln)
    if not m:
        continue
    s = m.group(1)
    if s.startswith(("G ", "A ", "T ", "MON ", "BEAT ")):
        d = dict(re.findall(r"(\w+)=(\S+)", s))
        for k, v in list(d.items()):
            if k in ("w0", "w1", "mon", "act"):
                try: d[k + "_hex"] = v
                except Exception: pass
            if v.lstrip("-").isdigit():
                d[k] = int(v)
        (G if s.startswith("G ") else A if s.startswith("A ") else
         T if s.startswith("T ") else MON if s.startswith("MON ") else BEAT).append(d)
    elif s.startswith(("INSTALL ", "SKIP ", "=====")):
        meta.setdefault(s.split()[0], s)

def num(x, k, default=0):
    v = x.get(k, default)
    return v if isinstance(v, int) else default

print(f"=== v25 日志概览 ({os.path.basename(LOG)}) ===")
print(f"  G(提交)={len(G)}  A(动作开始)={len(A)}  T(状态切换)={len(T)}  "
      f"MON={len(MON)}  BEAT={len(BEAT)}  FATAL={sum('FATAL' in l for l in lines)}")
for k, v in meta.items():
    print(f"  {k}: {v[:130]}")

if MON:
    print("\n=== 1 · 目标怪识别 ===")
    for x in MON[:3]:
        print(f"  f={num(x,'f')} mon={x.get('mon')} act={x.get('act')} "
              f"hp={x.get('hp')} max={x.get('max')} sp={x.get('sp')} st={x.get('st')}")

if G:
    print("\n=== 2 · G 提交参数分布 ===")
    print("  act:", collections.Counter(num(x, "act") for x in G).most_common(12))
    print("  sub:", collections.Counter(num(x, "sub") for x in G).most_common(12))
    print("  st :", collections.Counter(num(x, "st") for x in G).most_common())

    print("\n=== 3 · 落盘一致性：G.w1 低 8 位==act、次 8 位==sub ===")
    hit_a = hit_s = 0
    for x in G:
        w1 = x.get("w1")
        if isinstance(w1, str):
            try: w1 = int(w1, 16)
            except ValueError: w1 = None
        if w1 is None: continue
        hit_a += ((w1 & 0xFF) == num(x, "act"))
        hit_s += (((w1 >> 8) & 0xFF) == num(x, "sub"))
    print(f"  act 吻合 {hit_a}/{len(G)}   sub 吻合 {hit_s}/{len(G)}")
    chg = sum(1 for x in G if str(x.get("w0")) != str(x.get("w1")))
    print(f"  w0 != w1（字段确实被改写）: {chg}/{len(G)}")

if A:
    print("\n=== 4 · 时序：A.dG（距最近 G 的帧差） ===")
    dgs = [num(x, "dG") for x in A]
    real = [v for v in dgs if v != 0x7FFFFFFF]
    print("  分布:", collections.Counter(min(v, 20) for v in real).most_common(12))
    print(f"  有 G 记录: {len(real)}/{len(A)}；dG==0: {sum(1 for v in real if v==0)}；"
          f"dG<=2: {sum(1 for v in real if v<=2)}")
    print("\n=== 5 · 抽选结果是否一路传到动作开始 ===")
    ok = sum(1 for x in A if num(x, "gAct") == num(x, "a") and num(x, "gSub") == num(x, "s"))
    print(f"  A.gAct/gSub == A.a/s : {ok}/{len(A)}")
    print("  A.a/s top:", collections.Counter((num(x,'a'), num(x,'s')) for x in A).most_common(10))
    print("  A.id top :", collections.Counter(num(x,'id') for x in A).most_common(10))

if T:
    print("\n=== 6 · 发怒 / 状态切换 ===")
    for x in T[:12]:
        print(f"  f={num(x,'f')} n={num(x,'n')} st={x.get('st')}")

if BEAT:
    print("\n=== 7 · BEAT 尾部 ===")
    for x in BEAT[-5:]:
        print(f"  f={num(x,'f')} g={num(x,'g')} a={num(x,'a')} state={num(x,'state')} "
              f"log={num(x,'log')} mon={x.get('mon')} sel={num(x,'sel')} lastG={num(x,'lastG')}")

out = os.path.join(os.path.dirname(LOG), "v25_selectlayer_events.json")
json.dump({"G": G, "A": A, "T": T, "MON": MON, "BEAT": BEAT, "meta": meta},
          open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(f"\n→ {out}")
