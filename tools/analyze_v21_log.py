#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v21 日志分析：Rise 式输出窗口模拟 / 闪退 A/B 归因。

用法: python tools/analyze_v21_log.py [日志路径]
默认读 02_Workspace/game_p54.txt（7_ 脚本输出）。
"""
import re, sys, os, json, collections

LOG = sys.argv[1] if len(sys.argv) > 1 else r"D:/MHGU mod maker/02_Workspace/game_p54.txt"
lines = open(LOG, 'rb').read().decode('utf-8', 'replace').splitlines()

MON, A, V, HALT, BEAT, SITE, FATAL, meta = [], [], [], [], [], [], [], {}
for ln in lines:
    m = re.search(r"\[rai\] (.*)$", ln)
    if m:
        s = m.group(1)
        d = dict(re.findall(r"(\w+)=(\S+)", s))
        def num(k, base=10):
            v = d.get(k)
            if v is None: return 0
            try: return int(v, base) if base == 16 else int(v)
            except ValueError: return v
        if s.startswith("MON "):
            MON.append(dict(f=num('f'), mon=d.get('mon',''), act=d.get('act',''),
                            hp=num('hp'), max=num('max'), sp=d.get('sp',''),
                            intervene=num('intervene')))
        elif s.startswith("A "):
            A.append(dict(f=num('f'), n=num('n'), id=num('id'), a=num('a'), s=num('s'),
                          pa=num('pa'), ps=num('ps'), sub=num('sub'),
                          t=d.get('t',''), z=d.get('z',''), hp=num('hp')))
        elif s.startswith("V "):
            V.append(dict(f=num('f'), n=num('n'), id0=num('id0'), id1=num('id1'),
                          a=num('act'), s=num('s'), win_left=num('win_left'),
                          applied=num('applied')))
        elif s.startswith("HALT "):
            HALT.append(dict(f=num('f'), reason=num('reason'), mon=d.get('mon',''),
                             bad=num('bad'), hp=num('hp'), max=num('max')))
        elif s.startswith("BEAT "):
            BEAT.append(dict(f=num('f'), a=num('a'), passn=num('pass'), veto=num('veto'),
                             log=num('log'), mon=d.get('mon',''), halt=d.get('halt',''),
                             win=num('win')))
        elif s.startswith("SITE "):
            SITE.append(s)
        elif s.startswith(("=====", "INSTALL ")):
            meta[s.split()[0]] = s
    if re.search(r"FATAL|no function at 0", ln):
        FATAL.append(ln.strip()[:160])

print(f"=== v21 日志概览 ({os.path.basename(LOG)}) ===")
print(f"  MON={len(MON)} A={len(A)} V={len(V)} HALT={len(HALT)} BEAT={len(BEAT)} FATAL={len(FATAL)}")
for v in FATAL[:3]: print("  !!", v)
for k, v in meta.items(): print(f"  | {v[:150]}")

if MON:
    print("\n=== 1 · 目标怪自识别（a0 == HP-Bar 的 mon） ===")
    for m in MON[:5]:
        print(f"  f={m['f']} mon={m['mon']} act={m['act']} hp={m['hp']}/{m['max']} sp={m['sp']} intervene={m['intervene']}")
    print(f"  MON 次数 {len(MON)}（>1 说明换了对象或重新识别）")

if A:
    print("\n=== 2 · 新动作提交与攻击占比 ===")
    sub = [x for x in A if x['sub'] == 1]
    atk = [x for x in sub if x['a'] in (2, 7)]
    print(f"  A 总 {len(A)} / submit {len(sub)} / 攻击类 {len(atk)} ({len(atk)*100//max(1,len(sub))}%)")
    fs = [x['f'] for x in sub]
    if len(fs) > 1:
        g = sorted(fs[i]-fs[i-1] for i in range(1, len(fs)))
        n = len(g)
        print(f"  submit 间隔: min={g[0]} p25={g[n//4]} 中位={g[n//2]} p75={g[3*n//4]} max={g[-1]}")
        print(f"  <=60 帧: {sum(1 for x in g if x<=60)}/{n}  <=90 帧: {sum(1 for x in g if x<=90)}/{n}")
    print("  act 分布:", collections.Counter(x['a'] for x in A).most_common())
    print("  id top:", collections.Counter(x['id'] for x in sub).most_common(12))
    hp = [x['hp'] for x in A if x['hp'] > 0]
    if hp: print(f"  HP 轨迹 {hp[0]} -> {hp[-1]}（下降=战斗真实进行）")

if V:
    print("\n=== 3 · 输出窗口命中（V） ===")
    print(f"  命中 {len(V)} 次；applied 分布 {dict(collections.Counter(x['applied'] for x in V))}")
    print("  被拦 id0:", collections.Counter(x['id0'] for x in V).most_common(12))
    wl = [x['win_left'] for x in V]
    print(f"  win_left: min={min(wl)} 中位={sorted(wl)[len(wl)//2]} max={max(wl)}")
    g = sorted(V[i]['f']-V[i-1]['f'] for i in range(1, len(V)))
    if g: print(f"  相邻拦截帧差 中位={g[len(g)//2]}（应≈窗口 60 帧，过大说明窗口未连续生效）")
    print("  注：applied=0 -> 纯只读模拟；applied=1 -> 已把 action_id 换成 IDLE_ID=3")

if HALT:
    print("\n=== 4 · 阵亡/结算熔断 ===")
    for h in HALT[:6]: print("  ", h)
else:
    print("\n=== 4 · 阵亡/结算熔断：未触发（本场可能没阵亡，或对象未失效） ===")

if BEAT:
    print("\n=== 5 · BEAT 尾部（闪退归因关键） ===")
    for b in BEAT[-6:]:
        print(f"  f={b['f']} a={b['a']} pass={b['passn']} veto={b['veto']} log={b['log']} "
              f"mon={b['mon']} halt={b['halt']} win={b['win']}")
    print(f"  最后心跳帧 {BEAT[-1]['f']}；若 FATAL 紧随其后且无 HALT -> 崩溃与探针状态无关")

out = os.path.join(os.path.dirname(LOG) if os.path.dirname(LOG) else ".", "v21_risewindow_events.json")
json.dump(dict(MON=MON, A=A, V=V, HALT=HALT, BEAT=BEAT, SITE=SITE,
               FATAL=FATAL, meta=meta, source=LOG), open(out, "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)
print(f"\n→ {out}")
