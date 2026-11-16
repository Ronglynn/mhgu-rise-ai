# -*- coding: utf-8 -*-
"""P82：从 555 个 Rise 15 池文件生成 3 状态 × 5 距离档的精确权重形状表。

只做静态资产汇总，不编译进插件（改变权重需实机复验）。
产物：out/rise_15pool_shapes_555.json、out/band_shape_555.rs
"""
from __future__ import annotations

import collections
import glob
import json
import pathlib
import re
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from rsz_parse_v2 import parse as v2  # noqa: E402

STATES = ("anger", "normal", "tired")


def current_band_shape() -> list[list[int]]:
    src = (ROOT / "plug/context_probe/src/lib.rs").read_text(encoding="utf-8")
    m = re.search(r"const BAND_SHAPE:\s*\[\[u32;\s*4\];\s*15\]\s*=\s*\[(.*?)\];", src, re.S)
    if not m:
        return []
    return [[int(x.strip()) for x in row.split(",") if x.strip()]
            for row in re.findall(r"\[([0-9,\s]+)\]", m.group(1))]


def main() -> int:
    files = sorted(glob.glob(str(ROOT / "refs/_p81_extract/**/*range[1-5]check.user.2"), recursive=True))
    groups: dict[tuple[str, int], list[list[float]]] = collections.defaultdict(list)
    parse_ok = 0
    rate_sums: collections.Counter = collections.Counter()
    for p in files:
        r = v2(p)
        if not r["diagnostics"]["parseOK"]:
            continue
        parse_ok += 1
        rates = []
        for it in r["instances"]:
            for k, v in (it.get("values") or {}).items():
                if k == "_TransitionRate" and isinstance(v, (int, float)) and not isinstance(v, bool):
                    rates.append(float(v))
        rates.sort(reverse=True)
        if rates:
            rate_sums[round(sum(rates))] += 1
        name = pathlib.Path(p).name
        m = re.search(r"(anger|normal|tired)range([1-5])check", name, re.I)
        if m:
            groups[(m.group(1).lower(), int(m.group(2)))].append(rates)

    shapes: dict[str, list[int]] = {}
    detail: dict[str, dict] = {}
    for st in STATES:
        for band in range(1, 6):
            key = (st, band)
            arrs = groups.get(key, [])
            padded = [(a + [0.0] * 4)[:4] for a in arrs]
            mean = [statistics.mean(x[i] for x in padded) for i in range(4)] if padded else [0.0] * 4
            total = sum(mean)
            shape = [int(round(x / total * 100)) if total else 0 for x in mean]
            shape[3] += 100 - sum(shape)
            tag = "%s_range%d" % (st, band)
            shapes[tag] = shape
            detail[tag] = {
                "pools": len(arrs),
                "mean_candidates": round(statistics.mean(len(a) for a in arrs), 2) if arrs else 0,
                "mean_top_weight": round(statistics.mean(a[0] for a in arrs if a), 1) if arrs else 0,
                "raw_mean": [round(x, 2) for x in mean],
            }

    cur = current_band_shape()
    l1: dict[str, int] = {}
    if len(cur) == 15:
        for i, st in enumerate(STATES):
            for band in range(1, 6):
                tag = "%s_range%d" % (st, band)
                l1[tag] = sum(abs(a - b) for a, b in zip(shapes[tag], cur[i * 5 + band - 1]))

    out = {
        "source": "refs/_p81_extract (555 Rise 15-pool files)",
        "pool_files": len(files),
        "parseOK": parse_ok,
        "transition_rate_sum_distribution": dict(rate_sums),
        "shape_definition": "每组取各池 _TransitionRate 降序前 4 项均值，归一化到和 100",
        "shapes": shapes,
        "per_cell_detail": detail,
        "current_BAND_SHAPE": cur,
        "L1_vs_current": l1,
        "note": "静态参照资产；未编译进插件（改变权重需实机复验）",
    }
    (ROOT / "out/rise_15pool_shapes_555.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = [
        "// P82：Rise 15 池全量形状表（555 个 *RangeNCheck 池文件，v2 解析）",
        "// 生成：tools/make_555_shapes.py；静态参照资产，未编译进插件。",
        "// 顺序：[anger1..5, normal1..5, tired1..5]，每行 4 项、和恒 100。",
        "const BAND_SHAPE_555: [[u32; 4]; 15] = [",
    ]
    for st in STATES:
        for band in range(1, 6):
            tag = "%s_range%d" % (st, band)
            lines.append("    [%s],  // %-14s pools=%d" % (
                ", ".join(str(x) for x in shapes[tag]), tag, detail[tag]["pools"]))
    lines.append("];")
    (ROOT / "out/band_shape_555.rs").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("pool files", len(files), "parseOK", parse_ok)
    print("rate sum distribution", dict(rate_sums))
    for st in STATES:
        print(" ", st, [shapes["%s_range%d" % (st, b)] for b in range(1, 6)])
    if l1:
        print("L1 vs current BAND_SHAPE:", l1, "total", sum(l1.values()))
    print("wrote out/rise_15pool_shapes_555.json, out/band_shape_555.rs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
