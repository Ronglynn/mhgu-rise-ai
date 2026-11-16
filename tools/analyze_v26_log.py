"""v26 统一落盘点只读探针日志分析。

用法: python tools/analyze_v26_log.py <log>
输出: out/v26_unified_events.json + 终端摘要

判据：
  1. INSTALL h_unify / uni=1 且 Q 有数据 —— 0x76154 覆盖目标怪提交；
  2. A.dQ ≈ 0 —— 统一落盘发生在动作开始同帧之前；
  3. Q.w1 低字节==act、次字节==sub —— 落盘字段与传入参数一致；
  4. Q.kind 分布 —— 17 个状态 Hub 分支哪些在本场活跃。
"""
import re, json, os, sys, collections

LOG = sys.argv[1] if len(sys.argv) > 1 else r"02_Workspace/game_p54.txt"
if not os.path.isabs(LOG) and not os.path.exists(LOG):
    LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), LOG)
lines = open(LOG, "rb").read().decode("utf-8", "replace").splitlines()

Q, A, T, MON, BEAT, meta = [], [], [], [], [], {}
for ln in lines:
    m = re.search(r"\[rai\] (.*)$", ln)
    if not m:
        continue
    s = m.group(1)
    if s.startswith(("Q ", "A ", "T ", "MON ", "BEAT ")):
        d = dict(re.findall(r"(\w+)=(\S+)", s))
        for k, v in list(d.items()):
            if v.lstrip("-").isdigit():
                d[k] = int(v)
        (Q if s.startswith("Q ") else A if s.startswith("A ") else
         T if s.startswith("T ") else MON if s.startswith("MON ") else BEAT).append(d)
    elif s.startswith(("INSTALL ", "SKIP ", "=====")):
        meta.setdefault(s.split()[0], s)

def num(x, k, default=0):
    v = x.get(k, default)
    return v if isinstance(v, int) else default

is26 = any("RAI v26" in l for l in lines)
print(f"=== v26 日志概览 ({os.path.basename(LOG)}) ===")
print(f"  Q(统一落盘)={len(Q)}  A(动作开始)={len(A)}  T(状态切换)={len(T)}  "
      f"MON={len(MON)}  BEAT={len(BEAT)}  FATAL={sum('FATAL' in l for l in lines)}")
if not is26:
    print("  [warn] 该日志不是 v26 版本：以下分布仅作兼容性检查，不能作为判据")
for k, v in meta.items():
    print(f"  {k}: {v[:130]}")
if MON:
    print(f"  MON: f={num(MON[0],'f')} mon={MON[0].get('mon')} act={MON[0].get('act')} "
          f"hp={MON[0].get('hp')} max={MON[0].get('max')} sp={MON[0].get('sp')} st={MON[0].get('st')}")

if Q:
    print("\n=== 1 · Q 参数分布 ===")
    print("  act :", collections.Counter(num(x, "act") for x in Q).most_common(14))
    print("  sub :", collections.Counter(num(x, "sub") for x in Q).most_common(14))
    print("  kind:", collections.Counter(num(x, "kind") for x in Q).most_common())
    print("  p5  :", collections.Counter(num(x, "p5") for x in Q).most_common())
    print("  st  :", collections.Counter(num(x, "st") for x in Q).most_common())
    print("\n=== 2 · 落盘一致性：Q.w1 低8==act、次8==sub ===")
    hit_a = hit_s = 0
    for x in Q:
        w1 = x.get("w1")
        if isinstance(w1, str):
            try: w1 = int(w1, 16)
            except ValueError: w1 = None
        if w1 is None: continue
        hit_a += ((w1 & 0xFF) == num(x, "act"))
        hit_s += (((w1 >> 8) & 0xFF) == num(x, "sub"))
    print(f"  act 吻合 {hit_a}/{len(Q)}   sub 吻合 {hit_s}/{len(Q)}")
    print(f"  w0 != w1（字段确实改写）: {sum(1 for x in Q if str(x.get('w0')) != str(x.get('w1')))}/{len(Q)}")

if A:
    print("\n=== 3 · 时序：A.dQ（距最近 Q 的帧差） ===")
    real = [num(x, "dQ") for x in A if num(x, "dQ") != 0x7FFFFFFF]
    print("  分布:", collections.Counter(min(v, 20) for v in real).most_common(12))
    print(f"  有 Q 记录: {len(real)}/{len(A)}；dQ==0: {sum(1 for v in real if v==0)}；"
          f"dQ<=2: {sum(1 for v in real if v<=2)}")
    print("\n=== 4 · 抽选结果是否一路传到动作开始 ===")
    ok = sum(1 for x in A if num(x, "qAct") == num(x, "a") and num(x, "qSub") == num(x, "s"))
    print(f"  A.qAct/qSub == A.a/s : {ok}/{len(A)}")
    print("  A.a/s top:", collections.Counter((num(x,'a'), num(x,'s')) for x in A).most_common(10))
    print("  A.id top :", collections.Counter(num(x,'id') for x in A).most_common(10))

if T:
    print("\n=== 5 · 发怒 / 状态切换 ===")
    for x in T[:12]:
        print(f"  f={num(x,'f')} n={num(x,'n')} st={x.get('st')}")

if BEAT:
    print("\n=== 6 · BEAT 尾部 ===")
    for x in BEAT[-5:]:
        print(f"  f={num(x,'f')} q={num(x,'q')} a={num(x,'a')} state={num(x,'state')} "
              f"log={num(x,'log')} mon={x.get('mon')} uni={num(x,'uni')} lastQ={num(x,'lastQ')}")

out = os.path.join(os.path.dirname(LOG), "v26_unified_events.json")
json.dump({"Q": Q, "A": A, "T": T, "MON": MON, "BEAT": BEAT, "meta": meta},
          open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(f"\n→ {out}")
