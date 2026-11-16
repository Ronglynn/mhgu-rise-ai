# -*- coding: utf-8 -*-
"""v60 W1 高保真对拍：Rise 15 池实测数据 vs 插件内 W1 形状表。

输出 out/P57_w1_fidelity_audit.md，量化：
  1. 形状表是否与 Rise (state,k) 降序均值一致
  2. 按状态混合后的熵与 Rise 池平均熵的偏差
  3. GU 离线池里 n>=3 / n>=4 的覆盖率（护栏放宽的收益）
  4. k 截断归一化后的形状与 Rise k3 均值的偏差

用法: python audit_v60_w1_fidelity.py
"""
import collections
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "out"
RISE = ROOT / "rise_routine_rates.json"
GU = [ROOT / "emc_offline" / ("pools_em%s_00.json" % x)
      for x in ("004", "010", "020")]
OUT = ROOT / "P57_w1_fidelity_audit.md"

# 与 plug/context_probe/src/lib.rs 的 v60 常量逐字对应
SHAPES = {
    ("anger", 3): [55, 25, 20],
    ("anger", 4): [40, 25, 20, 15],
    ("normal", 3): [47, 28, 25],
    ("normal", 4): [41, 25, 22, 12],
    ("tired", 3): [60, 30, 10],          # P35 熵拟合，非 Rise 字面均值
}
MIX = {"anger": 40, "normal": 60, "tired": 100}   # k3 占比（百分比）


def H(v):
    return -sum((x / 100.0) * math.log2(x / 100.0) for x in v if x > 0)


def mean_shape(rows):
    k = max(len(r) for r in rows)
    m = [round(sum(r[i] for r in rows) / len(rows)) for i in range(k)]
    m[0] += 100 - sum(m)
    return m


def l1(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) + abs(len(a) - len(b)) * 0


def main():
    rise = json.loads(RISE.read_text(encoding="utf-8"))
    groups = collections.defaultdict(list)
    pools_by_state = collections.defaultdict(list)
    for e in rise:
        srt = sorted(e["rates"], reverse=True)
        groups[(e["state"], len(srt))].append(srt)
        pools_by_state[e["state"]].append(srt)

    lines = ["# P57 · v60 W1 高保真对拍（Rise 15 池实测 vs 插件形状表）", "",
             "数据源 `out/rise_routine_rates.json`（15 池 = 3 状态 × 5 距离档）",
             "与 `out/emc_offline/pools_em{004,010,020}_00.json`（GU 561 池）。", "",
             "## 1 · 形状表一致性", "",
             "| state | k | Rise 池数 | Rise 降序均值 | v60 常量 | L1 偏差 | H(Rise均值) | H(v60) |",
             "|---|---|---|---|---|---|---|---|"]
    ok = True
    for key in sorted(SHAPES, key=lambda x: (x[0], x[1])):
        st, k = key
        rows = groups.get(key, [])
        if not rows:
            lines.append("| %s | %d | 0 | — | %s | — | — | %.4f |" %
                         (st, k, str(SHAPES[key]), H(SHAPES[key])))
            continue
        ms = mean_shape(rows)
        v = SHAPES[key]
        d = l1(ms, v)
        if st != "tired" and d > 0:
            ok = False
        lines.append("| %s | %d | %d | %s | %s | %d | %.4f | %.4f |" %
                     (st, k, len(rows), str(ms), str(v), d, H(ms), H(v)))
    lines += ["",
              "疲惫行 L1=10 是**有意的熵拟合取舍**：Rise 疲惫 5 池降序均值 "
              "`[55,35,10]` 熵 1.3367，高于 Rise 疲惫池平均熵 1.2984"
              "（形状均值 != 熵均值）；沿用 P35 定案 `[60,30,10]` 使熵落到 1.2955。",
              ""]

    lines += ["## 2 · 按状态混合后的熵偏差", "",
              "| state | Rise 池平均熵 | v60 混合熵 | 偏差 | k3:k4 (v60) | Rise k3:k4 |",
              "|---|---|---|---|---|---|"]
    for st in ("anger", "normal", "tired"):
        rise_h = sum(H(r) for r in pools_by_state[st]) / len(pools_by_state[st])
        p3 = MIX[st] / 100.0
        s3 = SHAPES.get((st, 3))
        s4 = SHAPES.get((st, 4))
        mix_h = p3 * H(s3) + ((1 - p3) * H(s4) if s4 else 0.0)
        cnt = collections.Counter(len(r) for r in pools_by_state[st])
        lines.append("| %s | %.4f | %.4f | %+.4f | %d:%d | %d:%d |" %
                     (st, rise_h, mix_h, mix_h - rise_h,
                      MIX[st], 100 - MIX[st], cnt[3], cnt[4]))
    lines.append("")

    lines += ["## 3 · GU 池覆盖率（护栏 n>=4 → n>=3）", "",
              "| 怪 | 池数 | sum=100 且 cases>=3 | 占比 | sum=100 且 cases>=4 | 占比 |",
              "|---|---|---|---|---|---|"]
    tot = [0, 0, 0]
    for p in GU:
        d = json.loads(p.read_text(encoding="utf-8"))
        pools = d.get("allPools", [])
        valid = [x for x in pools if x.get("sum") == 100]
        c3 = sum(1 for x in valid if x.get("cases", 0) >= 3)
        c4 = sum(1 for x in valid if x.get("cases", 0) >= 4)
        tot[0] += len(valid); tot[1] += c3; tot[2] += c4
        lines.append("| %s | %d | %d | %.1f%% | %d | %.1f%% |" %
                     (d.get("label"), len(pools), c3, 100.0 * c3 / len(valid),
                      c4, 100.0 * c4 / len(valid)))
    lines.append("| **合计** | — | **%d** | **%.1f%%** | **%d** | **%.1f%%** |" %
                 (tot[1], 100.0 * tot[1] / tot[0], tot[2], 100.0 * tot[2] / tot[0]))
    lines += ["",
              "⇒ 护栏从 `n>=4` 放宽到 `n>=3`，W1 可介入的合法 GU 池从 %.1f%% 提升到 %.1f%%。" %
              (100.0 * tot[2] / tot[0], 100.0 * tot[1] / tot[0]),
              "P56 实机场 `sel=52 → wall=7`（13.5%）与离线量级一致；v60 预期 `wall` 显著上升。",
              ""]

    # k 截断归一化：目标 k4 但合格候选只有 3 个
    lines += ["## 4 · k 截断归一化（假设验证）", ""]
    for st in ("anger", "normal"):
        s4 = SHAPES[(st, 4)]
        s = sum(s4[:3])
        trunc = [x * 100 // s for x in s4[:2]]
        trunc.append(100 - sum(trunc))
        r3 = SHAPES[(st, 3)]
        lines.append("- %s k4 `%s` 在 m=3 时截断前 3 项并归一化 ⇒ `%s`（和 %d），"
                     "与 Rise %s k3 均值 `%s` 的 L1=%d，H=%.4f" %
                     (st, str(s4), str(trunc), sum(trunc), st, str(r3),
                      l1(trunc, r3), H(trunc)))
    lines += ["",
              "**假设**：Rise 池的 k 由池内 case 数决定（15 池里 10 个 k3、5 个 k4，"
              "tired 5 池全 k3）。v60 在 GU 合格候选 `m<目标k` 时按 m 截断并归一化，"
              "不再整包退回 GU 原版权重；此假设无 Rise 运行时证据，仅由池结构推断。",
              ""]

    lines += ["## 5 · 结论", "",
              "- 形状表（除疲惫熵拟合行）与 Rise 实测降序均值 **%s**。" %
              ("完全一致（L1=0）" if ok else "存在偏差，见上表"),
              "- 三状态分离 + 按状态 k 混合 + `n>=3` + k 截断，均在 W1 既有"
              " `rise_weight_pick()` / `SHAPE_*` / `W_MIX_*` 结构内完成。",
              "- 未改：W2 探针、疲惫链、6 个 hook、日志格式、零写入约束。",
              ""]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("wrote", OUT.name)
    print("shape_table_exact =", ok)
    print("GU pools: valid=%d cases>=3=%d (%.1f%%) cases>=4=%d (%.1f%%)" %
          (tot[0], tot[1], 100.0 * tot[1] / tot[0], tot[2], 100.0 * tot[2] / tot[0]))


if __name__ == "__main__":
    main()
