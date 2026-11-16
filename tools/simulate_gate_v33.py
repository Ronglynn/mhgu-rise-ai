#!/usr/bin/env python3
"""用 v32 实机事件流离线仿真 v33 门控参数（零实机、零风险）。

事件流：Q(mode==0) 提交 + A 动作开始，同帧 Q 在 A 之前。
规则：mode0 提交时，若该 mon 已有真实动作、冷却已过、且距上次 A <= GAP_MIN
      ⇒ 开一个 pending 窗口；窗口在「下一次 A」或「f+HOLD」较早者结束；
      结束设 COOLDOWN。统计窗口次数 / 累计帧 / 全场占比。
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

GAP_LIST = (30, 45, 60, 90)
HOLD_LIST = (30, 45, 60)
COOL_LIST = (60, 90, 120, 180)


def load(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    ev = []
    for x in d.get("Q", []):
        if x.get("r3") == 0 and isinstance(x.get("f"), int):
            # 同帧 Q 先于 A；用 seq 保证稳定顺序
            ev.append((x["f"], 0, "Q", x.get("a0", x.get("mon", 0))))
    for x in d.get("A", []):
        if isinstance(x.get("f"), int):
            ev.append((x["f"], 1, "A", 0))
    ev.sort()
    return ev, d


def simulate(ev, gap_min, hold, cooldown):
    # 单 mon 模型：本场只有一只主怪，且目的只是校准参数量级。
    # A 行没有 mon 字段，用单一状态与 v33 的 h_start_40 行为对齐。
    last_a = 0
    cool = 0
    pending = None  # (from, due)
    wins = []
    for f, _, kind, _mon in ev:
        if pending is not None:
            pfrom, pdue = pending
            if kind == "A" or f >= pdue:
                end = f
                # 到期优先判 D：A 与 due 同帧到达时，实际是 onUpdate 先结算
                how = "D" if f >= pdue else "A"
                wins.append((pfrom, end, end - pfrom, how))
                cool = end + cooldown
                last_a = end
                pending = None
                continue  # 该 A 已用于结束窗口，不再刷新基准
            continue  # pending 期间的 Q 只覆盖参数，不重开窗口
        if kind == "A":
            last_a = f  # h_start_40 每次动作开始刷新 S_ACTA
            continue
        # Q(mode0)
        if last_a == 0:
            last_a = f  # 首个动作：建立基准，不开窗口
            continue
        if f < cool or f - last_a > gap_min:
            continue
        pending = (f, f + hold)
    if pending is not None:
        pfrom, pdue = pending
        wins.append((pfrom, pdue, pdue - pfrom, "D"))
    return wins


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else \
        "04_RiseAI/out/v32_framegap_P5_events.json"
    ev, d = load(path)
    frames = max(f for f, _, _, _ in ev)
    print(f"事件流：Q(mode0)={sum(1 for e in ev if e[2]=='Q')}  "
          f"A={sum(1 for e in ev if e[2]=='A')}  末帧={frames} ≈ {frames/60:.0f}s")
    print("\nGAP HOLD COOL | 窗口数 累计帧 约秒数 占比 平均窗口帧  A提前结束占比")
    print("-" * 84)
    rows = []
    for gap in GAP_LIST:
        for hold in HOLD_LIST:
            for cool in COOL_LIST:
                w = simulate(ev, gap, hold, cool)
                n = len(w)
                total = sum(x[2] for x in w)
                early = sum(1 for x in w if x[3] == "A")
                rows.append((gap, hold, cool, n, total, early, w))
    for gap, hold, cool, n, total, early, w in rows:
        if (gap, hold) in ((60, 45), (60, 60), (45, 45), (90, 45), (30, 45)) and cool in (60, 90, 120):
            print(f"{gap:>3} {hold:>4} {cool:>4} | {n:>5} {total:>6} {total/60:>6.1f}s "
                  f"{100*total/frames:>5.1f}% {total/max(n,1):>11.1f} "
                  f"{100*early/max(n,1):>10.0f}%")
    print("-" * 84)
    print("推荐区间：累计 900~1800 帧（15~30 秒）、占比 6~12%、平均窗口 25~45 帧。")
    best = [r for r in rows if 900 <= r[4] <= 1800 and 6 <= 100*r[4]/frames <= 12]
    best.sort(key=lambda r: abs(r[4] - 1350))
    for gap, hold, cool, n, total, early, w in best[:5]:
        print(f"  候选 GAP={gap} HOLD={hold} COOL={cool} → {n} 次 / {total} 帧 / {total/60:.1f}s")
    if not best:
        print("  无候选落在该区间，取最接近者：")
        rows.sort(key=lambda r: abs(r[4] - 1350))
        for gap, hold, cool, n, total, early, w in rows[:5]:
            print(f"  GAP={gap} HOLD={hold} COOL={cool} → {n} 次 / {total} 帧 / {total/60:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
