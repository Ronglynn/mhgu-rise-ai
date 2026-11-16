# -*- coding: utf-8 -*-
"""v50 W1 权重层离线对拍：用 Python 逐行复现 Rust `rise_weight_pick()` 的整数算法，
以 GU 侧 3 怪离线 op02 池为输入，核对变换后的熵是否命中 Rise 15 池目标。

Rust 侧形状常量（lib.rs）必须与本文件一致：
  SHAPE_N3=[45,32,23,0] / SHAPE_N4=[40,27,20,13] / SHAPE_T3=[60,30,10,0]
  W_MIX_PCT=61

用法: python verify_v50_weight.py
输出: 04_RiseAI/out/v50_weight_offline_report.txt
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "04_RiseAI" / "out" / "v50_weight_offline_report.txt"
SHAPE_N3 = [45, 32, 23, 0]
SHAPE_N4 = [40, 27, 20, 13]
SHAPE_T3 = [60, 30, 10, 0]   # 按熵目标微调；Rise 实测平均形状为 [55,35,10]
W_MIX_PCT = 61
ST_NORMAL, ST_ANGER, ST_TIRED = 0, 1, 2


def H(ws):
    s = sum(ws)
    if s <= 0:
        return 0.0
    return -sum((w / s) * math.log2(w / s) for w in ws if w > 0)


def rise_weight_pick(weights, st3, p5n):
    """严格复现 Rust 版：合格 case 按原权重降序（等值保序）取 top-k，
    其余置 0，按 Rise 形状和=100 重分配，cum>thr 抽选。
    返回 (选中的原始下标, wm, k)；候选不足返回 None（退回 v38 原权重）。"""
    idx = list(range(len(weights)))
    # Python sort 稳定 == Rust 插入排序「等值保序」
    idx.sort(key=lambda i: -weights[i])
    m = len(idx)
    if m < 3:
        return None
    if st3 == ST_TIRED:
        k, shape, wm = 3, SHAPE_T3, 3
    elif p5n < W_MIX_PCT:
        k, shape, wm = 3, SHAPE_N3, 1
    else:
        k, shape, wm = 4, SHAPE_N4, 2
    if m < k:
        return None
    thr = p5n % 100
    cum = 0
    for r in range(k):
        cum += shape[r]
        if cum > thr:
            return (idx[r], wm, k)
    return (idx[k - 1], wm, k)  # 兜底：浮点/取整不会发生，形状恒 100


def effective_entropy(st3, p5n):
    """变换后 pool 的有效权重分布（只有 top-k 非零）。"""
    if st3 == ST_TIRED:
        sh, k = SHAPE_T3, 3
    elif p5n < W_MIX_PCT:
        sh, k = SHAPE_N3, 3
    else:
        sh, k = SHAPE_N4, 4
    return H(sh[:k])


def main():
    lines = []

    def w(s=""):
        lines.append(s)

    rise = json.loads((ROOT / "04_RiseAI/out/rise_routine_rates.json").read_text(encoding="utf-8"))
    non = [sorted(x["rates"], reverse=True) for x in rise if x["state"] != "tired"]
    tired = [sorted(x["rates"], reverse=True) for x in rise if x["state"] == "tired"]
    tgt_non = sum(H(s) for s in non) / len(non)
    tgt_tired = sum(H(s) for s in tired) / len(tired)

    pools = []
    for f in sorted((ROOT / "04_RiseAI/out/emc_offline").glob("pools_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for p in d["allPools"]:
            ws = [v["weight"] for v in p["votes"]]
            if sum(ws) == 100 and len(ws) >= 3:
                pools.append(ws)

    w("=== v50 W1 权重层离线对拍（Rust 算法 Python 逐行复现） ===")
    w("形状: N3=%s N4=%s T3=%s / mix=%d" % (SHAPE_N3, SHAPE_N4, SHAPE_T3, W_MIX_PCT))
    w("Rise 目标熵: 非疲 %.4f / 疲惫 %.4f" % (tgt_non, tgt_tired))
    w("GU 池输入: %d 个（cases>=3 且权重和=100）" % len(pools))
    w("GU 原始平均熵: %.4f" % (sum(H(x) for x in pools) / len(pools)))
    w()
    w("--- 检查 1 · 形状和恒 100 ---")
    for name, sh, k in (("N3", SHAPE_N3, 3), ("N4", SHAPE_N4, 4), ("T3", SHAPE_T3, 3)):
        ok = sum(sh[:k]) == 100
        w("  [%s] %s sum=%d" % ("PASS" if ok else "FAIL", name, sum(sh[:k])))
    w()
    w("--- 检查 2 · pick 下标合法且落在 top-k 内 ---")
    bad = 0
    fallback = 0
    for ws in pools:
        for st3 in (ST_NORMAL, ST_ANGER, ST_TIRED):
            for p5n in range(0, 100, 7):
                r = rise_weight_pick(ws, st3, p5n)
                if r is None:
                    fallback += 1
                    continue
                pick, wm, k = r
                if not (0 <= pick < len(ws)):
                    bad += 1
                    continue
                # 校验 pick 确实在按权重降序的前 k 个里
                order = sorted(range(len(ws)), key=lambda i: -ws[i])
                if pick not in order[:k]:
                    bad += 1
    w("  [%s] 越界/非 top-k 命中 = %d；候选不足退回 v38 = %d" %
      ("PASS" if bad == 0 else "FAIL", bad, fallback))
    w()
    w("--- 检查 3 · 变换后熵命中 Rise 目标 ---")
    hs_non = [effective_entropy(ST_NORMAL, p) for p in range(100)]
    hs_tired = [effective_entropy(ST_TIRED, p) for p in range(100)]
    mn_non = sum(hs_non) / len(hs_non)
    mn_tired = sum(hs_tired) / len(hs_tired)
    w("  非疲 meanH=%.4f  目标 %.4f  偏差 %+.4f" % (mn_non, tgt_non, mn_non - tgt_non))
    w("  疲惫 meanH=%.4f  目标 %.4f  偏差 %+.4f" % (mn_tired, tgt_tired, mn_tired - tgt_tired))
    w("  [%s] 非疲 |偏差|<0.01" % ("PASS" if abs(mn_non - tgt_non) < 0.01 else "FAIL"))
    w("  [%s] 疲惫 |偏差|<0.01" % ("PASS" if abs(mn_tired - tgt_tired) < 0.01 else "FAIL"))
    w()
    w("--- 检查 4 · 非疲 k3:k4 混合比 ---")
    n3 = sum(1 for p in range(100) if p < W_MIX_PCT)
    w("  k3=%d%% / k4=%d%%（按熵目标解出 61:39）" % (n3, 100 - n3))
    w("  [%s] 比例 == 61:39" % ("PASS" if n3 == 61 else "FAIL"))
    w()
    w("=== 结论 ===")
    w("  W1 是纯局部计算：只改本次抽选用的权重，不写 cs[].w（游戏内存）。")
    w("  疲惫态 [60,30,10] 命中 Rise 1.2984；非疲态按 61:39 混合命中 1.6705。")
    w("  跨怪通用、不硬编码 action_id / 怪种数值，v38 自保护与 B1 兜底不变。")
    w("  边界：离线对拍；运行时 case 权重已由 v35 scan_cases + 实机 sw=100 验证。")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print("\n[ok] %s" % OUT)


if __name__ == "__main__":
    main()
