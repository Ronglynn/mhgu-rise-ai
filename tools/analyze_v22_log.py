#!/usr/bin/env python3
"""v22/v23 动作 id 分类 / 状态字段 / 选招点日志分析。

用法: python tools/analyze_v22_log.py <log>
输出: out/v22_idstate_events.json + 终端摘要
v23 额外支持 P 行（0xEB66BC 选招点）、S.dP、act+0x1A1 与连招指纹。
"""
import re, sys, os, json, collections

LOG = sys.argv[1] if len(sys.argv) > 1 else r"out/game_p54_20261108_1630_v21i_intervene.txt"
lines = open(LOG, 'rb').read().decode('utf-8', 'replace').splitlines()

S, T, P, MON, BEAT, HALT, meta = [], [], [], [], [], [], {}
for ln in lines:
    m = re.search(r"\[rai\] (.*)$", ln)
    if not m:
        continue
    s = m.group(1)
    if s.startswith(("S ", "T ", "P ")):
        d = dict(re.findall(r"(\w+)=(\S+)", s))
        for k, v in list(d.items()):
            if v.lstrip('-').isdigit():
                d[k] = int(v)
        if s.startswith("T ") and isinstance(d.get('st'), str) and '->' in d['st']:
            a, b = d['st'].split('->', 1)
            d['st0'], d['st1'] = int(a), int(b)
            del d['st']
        (S if s.startswith("S ") else T if s.startswith("T ") else P).append(d)
    elif s.startswith("MON "):
        MON.append(dict(re.findall(r"(\w+)=(\S+)", s)))
    elif s.startswith("BEAT "):
        BEAT.append(dict((k, int(v)) for k, v in re.findall(r"(\w+)=(\d+)", s)))
    elif s.startswith("HALT "):
        HALT.append(s)
    elif s.startswith(("=====", "SITE ", "INSTALL ", "single ", "NO ", "NO ")):
        meta.setdefault(s.split()[0], s)

print(f"=== v22/v23 日志概览 ({os.path.basename(LOG)}) ===")
print(f"  S(新动作提交)={len(S)}  P(选招点)={len(P)}  T(状态变化)={len(T)}  MON={len(MON)}  BEAT={len(BEAT)}  HALT={len(HALT)}  FATAL={sum('FATAL' in l for l in lines)}")
for k, v in meta.items():
    print(f"  | {v[:110]}")
for x in MON:
    print(f"  MON f={x.get('f')} mon={x.get('mon')} act={x.get('act')} hp={x.get('hp')}/{x.get('max')} sp={x.get('sp')} st={x.get('st')} sz={x.get('sz')}")

def stats(name, xs):
    if not xs:
        print(f"  {name}: (空)")
        return
    g = sorted(xs)
    n = len(g)
    print(f"  {name}: n={n} min={g[0]} p25={g[n//4]} 中位={g[n//2]} p75={g[3*n//4]} max={g[-1]}")

if S:
    print("\n=== 1 · 动作 id 分布（无干预基线，用于取代 act=2/7 粗判） ===")
    c = collections.Counter(x.get('id', -1) for x in S)
    print(f"  不同 id {len(c)} 个；top20: {c.most_common(20)}")
    print("  act 分布:", collections.Counter(x.get('a') for x in S).most_common())
    print("\n  id → (act,sub) 映射（唯一映射数 = 可安全分类的动作）:")
    mp = collections.defaultdict(collections.Counter)
    for x in S:
        mp[x.get('id', -1)][(x.get('a'), x.get('s'))] += 1
    uniq = sum(1 for v in mp.values() if len(v) == 1)
    print(f"    {uniq}/{len(mp)} 个 id 有唯一 (act,sub)")
    for i, v in sorted(mp.items(), key=lambda kv: -sum(kv[1].values()))[:25]:
        print(f"    id={i:4d} n={sum(v.values()):3d} -> {v.most_common(3)}")
    print("\n  提交间隔:")
    stats("  S 帧间隔", [S[i]['f'] - S[i-1]['f'] for i in range(1, len(S))])

    # 对照 v21i 干预场：干预后占比异常升高的 id（疑似吼叫 / 异常动作）
    other = r"out/game_p54_20261108_1630_v21i_intervene.txt"
    if os.path.exists(other) and os.path.abspath(other) != os.path.abspath(LOG):
        old = []
        for l in open(other, 'rb').read().decode('utf-8', 'replace').splitlines():
            m = re.search(r"\[rai\] A (.*)$", l)
            if m:
                d = dict(re.findall(r"(\w+)=(\S+)", m.group(1)))
                if d.get('sub') == '1':
                    old.append(int(d['id']))
        co = collections.Counter(old)
        print("\n=== 2 · 对照 v21i 干预场：占比变化最大的 id ===")
        n1, n2 = len(S), len(old)
        delta = []
        for i in set(list(c) + list(co)):
            p1, p2 = c.get(i, 0) / max(n1, 1), co.get(i, 0) / max(n2, 1)
            delta.append((p2 - p1, i, c.get(i, 0), co.get(i, 0)))
        for d, i, a, b in sorted(delta, reverse=True)[:10]:
            print(f"    id={i:4d}  基线 {a:3d}/{n1} ({a/max(n1,1)*100:4.1f}%)  干预 {b:3d}/{n2} ({b/max(n2,1)*100:4.1f}%)  Δ={d*100:+5.1f}pp")
        print("    注：525/526/527 在干预场占比升高且 `s1A0` 取特殊值，是「吼叫/特殊动作」首要嫌疑。")

if T:
    print("\n=== 3 · act+0x518 状态枚举变化（发怒 / 疲劳权重输入） ===")
    print("  取值分布:", collections.Counter(x.get('st1') for x in T).most_common())
    for x in T[:20]:
        print(f"    f={x.get('f'):6d} n={x.get('n'):2d} st={x.get('st0')}->{x.get('st1')} hp={x.get('hp')} id={x.get('id')}")
    print("  判据：若 st 只在少数值间切换且与 HP 阈值/时长相关 -> 可作发怒、疲劳权重输入。")
else:
    print("\n=== 3 · 状态枚举：本场 T 行 0 条（字段未变化，或本日志非 v22） ===")

print("\n=== 4 · 选招点 0xEB66BC / 连招指纹（v23） ===")
if P:
    print(f"  P 行数 {len(P)}；k1/k2 分布 {collections.Counter((x.get('k1'), x.get('k2')) for x in P).most_common(6)}")
    print(f"  P 帧间隔: ", end="")
    stats("", [P[i]['f'] - P[i-1]['f'] for i in range(1, len(P))])
    dp = [x['dP'] for x in S if isinstance(x.get('dP'), int)]
    if dp:
        print("  S.dP（提交距最近选招帧差）: ", end="")
        stats("", dp)
        print(f"    dP=0 占比 {sum(1 for v in dp if v == 0)}/{len(dp)}；dP≤3 占比 {sum(1 for v in dp if v <= 3)}/{len(dp)}")
        print("    判据：dP≈0 且 P 在 S 之前出现 -> 0xEB66BC 可作否决式重抽点。")
    a1s = collections.Counter(x.get('s1A1') for x in S)
    print(f"  S.s1A1（act+0x1A1 动作分派状态）分布: {a1s.most_common()}")
else:
    print("  本日志无 P 行（非 v23 或选招 hook 被 SKIP）")

if S:
    # 「后退→前撞」连招指纹：19(6/12)→4(6/7)→19(6/12)，段间隔 10~13 帧
    fp = 0; runs = []
    i = 1
    while i < len(S) - 1:
        a, b, c = S[i-1], S[i], S[i+1]
        if (a.get('id'), b.get('id'), c.get('id')) == (19, 4, 19) and b['f'] - a['f'] <= 40 and c['f'] - b['f'] <= 40:
            fp += 1
            runs.append((a['f'], c['f']))
            i += 2
        else:
            i += 1
    print(f"  连招指纹 19→4→19 命中 {fp} 次，帧段 {runs[:8]}")
    print("  其它高频对:", collections.Counter((S[i-1].get('id'), S[i].get('id')) for i in range(1, len(S))).most_common(6))

print("\n=== 5 · BEAT 尾部 ===")
for x in BEAT[-4:]:
    print("   ", x)
for h in HALT[:3]:
    print("   HALT:", h)

out = os.path.join(os.path.dirname(LOG), "v22_idstate_events.json")
json.dump({"S": S, "T": T, "P": P, "MON": MON, "BEAT": BEAT, "HALT": HALT, "meta": meta}, open(out, "w"), indent=1)
print(f"\n→ {out}")
