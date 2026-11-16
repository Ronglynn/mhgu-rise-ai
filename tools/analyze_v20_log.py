#!/usr/bin/env python3
"""v20 日志分析：HP-Bar getter 链 / act 状态字段 / 否决策略模拟。

用法：python tools/analyze_v20_log.py [日志路径]
默认读 02_Workspace/game_p54.txt。输出 out/v20_probe_events.json 供后续复用。
"""
import re, os, sys, json, collections, statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = sys.argv[1] if len(sys.argv) > 1 else r"D:/MHGU mod maker/02_Workspace/game_p54.txt"
if not os.path.isabs(LOG):
    LOG = os.path.join(ROOT, LOG)

raw = open(LOG, 'rb').read().decode('utf-8', 'replace').splitlines()
R = {k: [] for k in 'CEAKRVXBG'}
meta, beat, site, fatal = [], [], [], []
for ln in raw:
    if re.search(r'FATAL|plugin disabled|panic', ln, re.I):
        fatal.append(ln[:160])
    m = re.search(r"\[rai\] (.*)$", ln)
    if not m:
        continue
    s = m.group(1)
    tag = s.split()[0] if s.split() else ''
    if tag in R:
        d = {}
        for k, v in re.findall(r"(\w+)=(\S+)", s):
            d[k] = v
        R[tag].append(d)
    elif s.startswith('BEAT '):
        beat.append(dict(re.findall(r"(\w+)=(\S+)", s)))
    elif s.startswith('SITE '):
        site.append(s)
    else:
        meta.append(s)

def num(d, k, default=0):
    v = d.get(k, default)
    try:
        return int(v, 16) if isinstance(v, str) and re.fullmatch(r'[0-9A-Fa-f]{8}', v) else int(v)
    except (ValueError, TypeError):
        return default

def stats(name, xs):
    xs = sorted(xs)
    if not xs:
        print(f"  {name}: (空)")
        return
    print(f"  {name}: n={len(xs)} min={xs[0]} p25={xs[len(xs)//4]} 中位={xs[len(xs)//2]} "
          f"p75={xs[3*len(xs)//4]} max={xs[-1]} 均值={statistics.mean(xs):.1f}")

C, E, A, K, Rr, V, X = R['C'], R['E'], R['A'], R['K'], R['R'], R['V'], R['X']
print(f"=== v20 日志概览 ({os.path.basename(LOG)}) ===")
print(f"  C={len(C)} K={len(K)} E={len(E)} R={len(Rr)} A={len(A)} V={len(V)} X={len(X)} "
      f"BEAT={len(beat)} FATAL={len(fatal)}")
for x in fatal[:3]:
    print("  !", x)
for x in meta[:4]:
    print("  |", x[:150])

# ---- 1. HP Bar getter 链 ----
print("\n=== 1 · C: HP-Bar getter 链（确认怪） ===")
if C:
    eq = sum(1 for x in C if x.get('mon', '').upper() == x.get('obj', '').upper())
    print(f"  mon == END-hook obj : {eq}/{len(C)}")
    print("  mon 取值:", collections.Counter(x.get('mon') for x in C).most_common(5))
    print("  obj 取值:", collections.Counter(x.get('obj') for x in C).most_common(5))
    print("  slot 取值:", collections.Counter(x.get('slot') for x in C).most_common(5))
    print("  lock 取值:", collections.Counter(x.get('lock') for x in C).most_common(5))
    print("  g0 (mon getter 首字):", collections.Counter(x.get('g0') for x in C).most_common(3))
    print("  样例:", C[:2])
else:
    print("  (无 C 行：mgr 无效或未到 300 帧)")

print("\n=== 2 · K: mon 与 OBJ 的字段对比（判定是否同一层对象） ===")
if K:
    print("  p1428 (mon 侧):", collections.Counter(x.get('p1428') for x in K).most_common(5))
    print("  o1428 (OBJ 侧):", collections.Counter(x.get('o1428') for x in K).most_common(5))
    print("  p2588 (mon 侧):", collections.Counter(x.get('p2588') for x in K).most_common(5))
    print("  o2588 (OBJ 侧):", collections.Counter(x.get('o2588') for x in K).most_common(5))
    hp = [num(x, 'hp') for x in K if num(x, 'hp') > 0]
    mx = [num(x, 'max') for x in K if num(x, 'max') > 0]
    stats("  hp>0", hp); stats("  max>0", mx)
    print("  species:", collections.Counter(x.get('sp') for x in K).most_common(4))
    print("  样例:", K[:2])
else:
    print("  (无 K 行)")

# ---- 3. E / R 状态 ----
print("\n=== 3 · E/R: 动作结束与状态快照 ===")
if E:
    stats("  E.dE 动作周期", [num(x, 'dE') for x in E if num(x, 'dE') < 5000])
    print("  E 的 (a,s) 分布:", collections.Counter((num(x, 'a'), num(x, 's')) for x in E).most_common(10))
if Rr:
    for k in ('s1A0', 's1A4', 's1A8', 'emc0', 'hp', 'max'):
        c = collections.Counter(x.get(k) for x in Rr)
        print(f"  R.{k} 取值 {len(c)} 种: {c.most_common(5)}")
    # 相邻 R 变化率：接近 100% 才可能是动作边界信号
    print("  相邻 R 字段变化率 (n-1 次):")
    for k in ('s1A0', 's1A4', 's1A8', 'emc0'):
        seq = [x.get(k) for x in Rr]
        ch = sum(1 for i in range(1, len(seq)) if seq[i] != seq[i-1])
        print(f"    {k}: {ch}/{max(1,len(seq)-1)}")
    # 与 act 类别的关联（找怒/硬直/倒地位）
    em = {num(x, 'f'): x for x in E}
    cross = collections.Counter((num(em[f], 'a'), Rr[i].get('s1A0'), Rr[i].get('s1A8'))
                                for i, f in enumerate(sorted(em)) if i < len(Rr))
    print("  (a, s1A0, s1A8) 前 8:", cross.most_common(8))

# ---- 4. A 动作 id ----
print("\n=== 4 · A: 动作开始 / 新动作提交 ===")
if A:
    MA = [x for x in A if x.get('this') == (C[0].get('obj') if C else None)] or A
    print(f"  A 总数 {len(A)}；主对象 {len(MA)}")
    print("  sub=1 (新动作提交):", sum(1 for x in A if num(x, 'sub') == 1))
    print("  id 分布:", collections.Counter(num(x, 'id') for x in A).most_common(18))
    print("  a (act 类) 分布:", collections.Counter(num(x, 'a') for x in A).most_common())
    sub = [x for x in A if num(x, 'sub') == 1]
    print("  提交行 id ↔ (a,s) 映射:")
    m = collections.defaultdict(collections.Counter)
    for x in sub:
        m[num(x, 'id')][(num(x, 'a'), num(x, 's'))] += 1
    one = sum(1 for v in m.values() if len(v) == 1)
    print(f"    id 共 {len(m)}，唯一 (a,s) {one} 个")
    for k, v in sorted(m.items(), key=lambda kv: -sum(kv[1].values()))[:16]:
        print(f"      id={k:4d} n={sum(v.values()):3d} -> {v.most_common(3)}")
    print("  攻击类 (a=2/7) 提交:", sum(1 for x in sub if num(x, 'a') in (2, 7)), "/", len(sub))

# ---- 5. V 否决模拟 ----
print("\n=== 5 · V: 输出窗口否决模拟（INTERVENE=0，零写入） ===")
if V:
    print(f"  模拟拦截 {len(V)} 次；applied 取值: {collections.Counter(x.get('applied') for x in V)}")
    print("  被拦 id0:", collections.Counter(num(x, 'id0') for x in V).most_common(12))
    stats("  win_left (距窗口结束)", [num(x, 'win_left') for x in V])
    vf = sorted(num(x, 'f') for x in V)
    stats("  相邻拦截帧差", [vf[i]-vf[i-1] for i in range(1, len(vf))])
    if E:
        ef = sorted(num(x, 'f') for x in E)
        print(f"  END 总数 {len(ef)}，拦掉 {len(vf)} ({len(vf)/max(1,len(ef)):.1%})")
else:
    print("  (无 V 行：窗口未命中，检查 E/A 同帧顺序与 sub 判据)")

# ---- 6. X 字段差分 ----
print("\n=== 6 · X: act/EMC 字段变化与 END 对齐 ===")
if X:
    print("  变化字段 top:", collections.Counter((x.get('w'), x.get('off')) for x in X).most_common(12))
    if E:
        ef = set(num(x, 'f') for x in E)
        al = sum(1 for x in X if any(abs(num(x, 'f') - f) <= 2 for f in ef))
        print(f"  X 落在 END ±2 帧: {al}/{len(X)}")
    print("  样例:", X[:4])
else:
    print("  (无 X 行：act 指针仍无效，见 K 行)")

print("\n=== 7 · BEAT 尾部 ===")
for x in beat[-4:]:
    print(" ", x)

out = os.path.join(ROOT, 'out', 'v20_probe_events.json')
json.dump({k: R[k] for k in R} | {'BEAT': beat, 'SITE': site, 'meta': meta, 'fatal': fatal},
          open(out, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(f"\n→ {out}")
