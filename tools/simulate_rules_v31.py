"""v31 离线规则仿真 —— 用只读实机数据校准「通用 AI 干预」的触发率与阈值。

用法: python tools/simulate_rules_v31.py <v31_unifyentry_events.json>
零风险、不需要实机、不写游戏内存。输入是 analyze_v31_log.py 产出的 JSON。

只基于**跨怪通用**的输入：mode(r3)、prev 表(+0x73E0 低16位)、st(+0x518)、
act 类(r1)、帧间隔。**不读任何 action_id 作为规则目标**。
"""
import collections
import json
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "02_Workspace/v31_unifyentry_events.json"
d = json.load(open(PATH))
Q, A = d["Q"], d["A"]

# 只有 mode==0 才是「实际动作提交」；mode==2 是 action-end 状态请求（不产生 A 行）
SUB = sorted([x for x in Q if x.get("r3") == 0 and x.get("eq") == 1], key=lambda x: x["f"])
REQ = [x for x in Q if x.get("r3") == 2]
amap = {x["f"]: x for x in A}

print(f"=== v31 离线规则仿真 ({PATH.split('/')[-1]}) ===")
print(f"  Q 总数 {len(Q)}  |  实际动作提交(mode=0,eq=1) {len(SUB)}  |  "
      f"状态请求(mode=2) {len(REQ)}  |  A 行 {len(A)}")

# 逐次提交重建
rows = []
for i, x in enumerate(SUB):
    prev = x.get("w0", 0) & 0xFFFF          # 即将成为 prev 的上一个 (act,sub)
    pa, ps = prev & 0xFF, (prev >> 8) & 0xFF
    gap = x["f"] - SUB[i - 1]["f"] if i else None
    a = amap.get(x["f"])
    rows.append(dict(f=x["f"], r1=x.get("r1"), r2=x.get("r2"), st=x.get("st"),
                     s1a1=x.get("s1A1"), pa=pa, ps=ps, gap=gap,
                     id=a.get("id") if a else None))

print("\n=== 1 · 基线（与 v16 对照，确认变体口径下行为未变）===")
gaps = sorted(r["gap"] for r in rows if r["gap"] is not None)
print(f"  相邻提交帧差: n={len(gaps)} min={gaps[0]} 中位={gaps[len(gaps)//2]} "
      f"p90={gaps[9*len(gaps)//10]} max={gaps[-1]}")
print(f"  <=30 帧: {sum(1 for g in gaps if g <= 30)}/{len(gaps)}"
      f"  ({sum(1 for g in gaps if g <= 30)/len(gaps)*100:.1f}%)   "
      f"<=60 帧: {sum(1 for g in gaps if g <= 60)}/{len(gaps)}")
print(f"  st 分布: {collections.Counter(r['st'] for r in rows).most_common()}")
print(f"  act 类(r1) 分布: {collections.Counter(r['r1'] for r in rows).most_common()}")
print(f"  s1A1 分布: {collections.Counter(r['s1a1'] for r in rows).most_common()}")

print("\n=== 2 · 通用 prev 表检查（等价 Rise _CheckPrevTableInfoList）===")
same_full = sum(1 for r in rows if r["r1"] == r["pa"] and r["r2"] == r["ps"])
same_act = sum(1 for r in rows if r["r1"] == r["pa"])
print(f"  (r1,r2) == 上一个 (act,sub)  [完全复读]: {same_full}/{len(rows)}")
print(f"  r1 == 上一个 act 类         [同类连发]: {same_act}/{len(rows)}")

print("\n=== 3 · 候选通用规则触发率（不针对任何具体招式/action_id）===")
ATTACK = {2, 7}          # L1 粗粒度攻击类，仅作统计口径，不写死规则目标
rules = {
    "R1 prev完全复读": lambda r: r["r1"] == r["pa"] and r["r2"] == r["ps"],
    "R2 间隔<=30帧": lambda r: r["gap"] is not None and r["gap"] <= 30,
    "R3 间隔<=45帧": lambda r: r["gap"] is not None and r["gap"] <= 45,
    "R4 间隔<=60帧": lambda r: r["gap"] is not None and r["gap"] <= 60,
    "R5 短间隔且攻击类": lambda r: r["gap"] is not None and r["gap"] <= 30 and r["r1"] in ATTACK,
    "R6 短间隔且同类连发": lambda r: r["gap"] is not None and r["gap"] <= 30 and r["r1"] == r["pa"],
    "R7 怒时短间隔": lambda r: r["gap"] is not None and r["gap"] <= 30 and r["st"] == 1,
}
for name, fn in rules.items():
    hit = [r for r in rows if fn(r)]
    print(f"  {name:<20} {len(hit):3}/{len(rows)}  ({len(hit)/len(rows)*100:.1f}%)"
          f"   act类={collections.Counter(r['r1'] for r in hit).most_common(4)}")

print("\n=== 4 · 若按规则插入缓冲，预期窗口增量（纯估算）===")
for BUF in (30, 45, 60):
    for name, fn in (("R2 间隔<=30帧", rules["R2 间隔<=30帧"]),
                     ("R5 短间隔且攻击类", rules["R5 短间隔且攻击类"]),
                     ("R6 短间隔且同类连发", rules["R6 短间隔且同类连发"])):
        hit = sum(1 for r in rows if fn(r))
        total_frames = sum(r["gap"] for r in rows if r["gap"] is not None)
        print(f"  缓冲 {BUF:2} 帧 × {name:<20} 触发 {hit:3} 次"
              f"  ⇒ 全场新增 {hit*BUF} 帧 ≈ {hit*BUF/60:.1f} 秒"
              f"  (原战斗 {total_frames} 帧 ≈ {total_frames/60:.1f} 秒)")
    print()

print("=== 5 · 结论提示 ===")
print("  - mode==2 的 78 次是状态 Hub 请求(r1 恒 0)，**不产生动作**，干预时须排除；")
print("  - 只有 mode==0 的提交可施加通用规则；这本身就是跨怪通用条件，非招式特例；")
print("  - act 类(2/7) 是粗粒度 L1 类，仅作统计；任何规则不得把具体 id 或单怪分布写死；")
print("  - 疲劳 st=2 本场仍未出现，3 状态权重暂用 怒/普通 两态；")
print("  - 距离字段未定位，5 距离档暂缓，先用 prev 表 + 间隔门控 + 状态分支。")
