#!/usr/bin/env python3
"""Rise 对标缺口审计：用两场不同怪的 v32/v33 实机事件流，量化
「高频怪复读未被约束」与「低频怪被无谓插窗口」两个体感问题。

用法：python tools/audit_rise_gap.py [v33_events.json] [v32_events.json]
只读、零风险、可复现。
"""
import json
import sys
from collections import Counter
from pathlib import Path

DEF_V33 = "04_RiseAI/out/v33_crossmonster_events.json"
DEF_V32 = "04_RiseAI/out/v32_framegap_P5_events.json"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def analyse(tag, d):
    A = sorted(d.get("A", []), key=lambda x: x.get("f", 0))
    Q = d.get("Q", [])
    W = d.get("W", [])
    fr = [x["f"] for x in A]
    print(f"\n=== {tag} ===")
    print(f"A={len(A)}  Q={len(Q)}  W={len(W)}  末帧={fr[-1] if fr else 0}")

    # 1. 连续同 action_id 段（Rise prev 表要防的对象）
    runs = []
    i = 0
    while i < len(A):
        j = i
        while j + 1 < len(A) and A[j + 1].get("id") == A[i].get("id"):
            j += 1
        if j - i + 1 >= 2:
            runs.append((A[i].get("id"), j - i + 1, A[i]["f"], A[j]["f"],
                         [A[k]["f"] - A[k - 1]["f"] for k in range(i + 1, j + 1)]))
        i = j + 1
    long_runs = [r for r in runs if r[1] >= 3]
    print(f"连续同 id 段：{len(runs)} 段，其中 >=3 连：{len(long_runs)} 段")
    for id_, n, f0, f1, gaps in long_runs[:6]:
        near = sum(1 for w in W if f0 - 90 <= w.get("f", 0) <= f1 + 90)
        print(f"  id={id_} n={n} f={f0}..{f1} 间隔={gaps} 邻近窗口={near}"
              f"  ⇒ {'门控未触及' if near == 0 else '门控触及'}")

    pairs = [(A[k]["f"] - A[k - 1]["f"], A[k].get("id"))
             for k in range(1, len(A)) if A[k].get("id") == A[k - 1].get("id")]
    if pairs:
        gs = sorted(g for g, _ in pairs)
        print(f"连续同 id 对：{len(pairs)}/{len(A)-1} = {100*len(pairs)/(len(A)-1):.1f}%  "
              f"间隔中位={gs[len(gs)//2]}  <=90帧={sum(1 for g in gs if g<=90)}  "
              f">90帧(门控够不着)={sum(1 for g in gs if g>90)}")

    # 2. 窗口落点：局部 A 间隔，判断是否插在本来正常衔接处
    if W:
        loc = []
        for w in W:
            f = w.get("from", 0)
            prev = max([x for x in fr if x < f], default=0)
            nxt = min([x for x in fr if x >= f], default=0)
            if prev and nxt:
                loc.append((nxt - prev, w.get("win", 0)))
        short = sum(1 for g, _ in loc if g <= 60)
        print(f"窗口落点局部间隔：{sorted(g for g,_ in loc)}")
        print(f"  落在 <=60 帧短间隔处：{short}/{len(loc)} "
              f"（把本已正常的衔接再拉长 ⇒ 慢怪显笨重）")
        print(f"  零长窗口 win=0：{sum(1 for _, win in loc if win == 0)}/{len(loc)}")

    # 3. 状态字段是否被用作规则输入（v33 只读不用）
    q0 = [x for x in Q if x.get("r3") == 0]
    print(f"Q 中 st(怒/疲劳) 分布：{Counter(x.get('st') for x in q0).most_common()}  "
          f"⇒ 规则未使用；Rise 是 3 状态 × 5 距离档加权池")
    same = sum(1 for k in range(1, len(q0))
               if (q0[k].get("r1"), q0[k].get("r2")) ==
                  (q0[k - 1].get("r1"), q0[k - 1].get("r2")))
    print(f"Q 中相邻重复 (act,sub) 提交：{same}/{len(q0)} "
          f"（v32 曾观察到逐帧抽选循环）")


def rise_checklist():
    print("\n" + "=" * 76)
    print("Rise 机制实证清单（本机 RSZ 解析，非推测） vs v33 实现")
    print("=" * 76)
    rows = [
        ("12 个 attack_stance 处境 Hub", "倒地/闪光/无目标/区域外独立文件；攻击池只在 same_main*", "无", "硬直/倒地仍与攻击共用路径"),
        ("ThinkCondition._IsActionEnd", "12 True / 32 False，按分支门控状态转移", "无", "动作进行中仍可重抽；窗口被 A 提前结束 36%"),
        ("3 状态 × 5 距离档加权池", "15 池，_TransitionRate 和恒 100，_TableNo 随档变；tired·档5=[10,20,70]→[1,20,51]", "无", "不读 +0x518、不读距离；快慢怪同一待遇"),
        ("ConditionInfo._CheckPrevTableInfoList", "50 个实例，每个指向本池 1 个 ActionTableData；抽选时按动作表否决/重抽", "无", "连续 4 次 id=524 完全未受约束"),
        ("显式 CoolDown 字段", "explicit_cooldown_field_found=false；Timer 因果未证实", "自创全局 CD", "GAP/HOLD/COOL 是 Rise 没有的机制"),
    ]
    for name, rise, gu, effect in rows:
        print(f"  {name}\n    Rise: {rise}\n    v33 : {gu}\n    后果: {effect}")


def main():
    p33 = sys.argv[1] if len(sys.argv) > 1 else DEF_V33
    p32 = sys.argv[2] if len(sys.argv) > 2 else DEF_V32
    analyse("v33 / sp=0004（用户所述水龙场，连续同招）", load(p33))
    analyse("v32 / sp=0014（将军镰蟹，快节奏基线）", load(p32))
    rise_checklist()
    print("\n结论：v33 不是 Rise AI 仿制，而是统一的帧间隔节流阀；"
          "Rise 的 5 项核心机制实现了 0 项。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
