# -*- coding: utf-8 -*-
"""P80：用 v71 实机日志的实测密度 + 插件源码配额常量，静态审计
「30/60/120 分钟任务会不会停写」。

v71 的结构：每 QUOTA_EPOCH_F 帧重置各行独立配额，MAXLOG 只作全局熔断。
⇒ 只要「单 epoch 每类行用量 < 该类配额」，任务时长本身不会造成停写；
   唯一随任务时长线性增长的是总 log 序号，需与 MAXLOG 比较。
本脚本不实机、不改插件、不造日志，只用实测数据演算。
"""
from __future__ import annotations

import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT.parent / "02_Workspace" / "game_p54_lite.txt"
SRC = ROOT / "plug" / "context_probe" / "src" / "lib.rs.v71bak"
OUT_MD = ROOT / "out" / "P80_30min_quota_audit.md"
OUT_JSON = ROOT / "out" / "P80_30min_quota_audit.json"

TAG_RE = re.compile(r"\[rai\] ([A-Z][A-Z0-9]*) ")
F_RE = re.compile(r"\bf=(\d+)")
CONST_RE = re.compile(r"^const (MAX_[A-Z0-9_]+)\s*:\s*u32\s*=\s*([\d_]+)", re.M)
EPOCH_RE = re.compile(r"^const QUOTA_EPOCH_F\s*:\s*u32\s*=\s*([\d_]+)", re.M)
MAXLOG_RE = re.compile(r"^const MAXLOG\s*:\s*u32\s*=\s*([\d_]+)", re.M)

# 日志 tag -> 插件里对应的每 epoch 配额常量；None = 固定节奏行，不占动态配额
TAG_QUOTA = {
    "V": "MAX_V", "K": "MAX_K", "E": "MAX_E", "M": "MAX_M", "X": "MAX_X",
    "Q": "MAX_Q", "A": "MAX_A", "C": "MAX_C", "R": "MAX_R", "N": "MAX_N",
    "U": "MAX_U", "H": "MAX_H", "Y": "MAX_Y", "G": "MAX_G", "W": "MAX_W",
    "Z": "MAX_Z", "ZP": "MAX_ZP", "ZS": "MAX_ZS", "ZT": "MAX_ZT",
    "AE": "MAX_AE", "QX": "MAX_QX", "B2": "MAX_B2", "COMBO": "MAX_COMBO",
    "AR": "MAX_AR", "HB": "MAX_HB", "J": "MAX_J", "T": "MAX_T",
    "P": "MAX_P", "D": "MAX_D",
    "S": None, "S2": None, "BEAT": None, "INSTALL": None, "SITE": None,
    "FIX": None, "ZERO": None, "Rule": None,
}
FPS = 60


def int_lit(s: str) -> int:
    return int(s.replace("_", ""))


def main() -> int:
    src = SRC.read_text(encoding="utf-8", errors="replace")
    consts = {m.group(1): int_lit(m.group(2)) for m in CONST_RE.finditer(src)}
    epoch_f = int_lit(EPOCH_RE.search(src).group(1))
    maxlog = int_lit(MAXLOG_RE.search(src).group(1))

    by_epoch = collections.defaultdict(collections.Counter)
    total_rai = 0
    for line in LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        if "[rai]" not in line:
            continue
        total_rai += 1
        fm = F_RE.search(line)
        if not fm:
            continue
        tm = TAG_RE.search(line)
        if not tm:
            continue
        by_epoch[int(fm.group(1)) // epoch_f][tm.group(1)] += 1

    # 取「带 f 的行数最多」的 epoch 作保守单 epoch 上界
    busy = max(by_epoch, key=lambda e: sum(by_epoch[e].values()))
    busy_rows = by_epoch[busy]
    busy_total = sum(busy_rows.values())
    quota_total = sum(v for k, v in consts.items() if k.startswith("MAX_"))

    rows = []
    for tag, cnt in sorted(busy_rows.items(), key=lambda x: -x[1]):
        qname = TAG_QUOTA.get(tag, "?")
        if qname is None:
            quota = None
            ratio = None
        elif qname in consts:
            quota = consts[qname]
            ratio = round(cnt / quota, 4) if quota else None
        else:
            quota = None
            ratio = None
        rows.append({"tag": tag, "epoch_rows": cnt, "quota_const": qname,
                     "quota": quota, "usage_ratio": ratio})
    tight = [r for r in rows if r["usage_ratio"] is not None]
    tight.sort(key=lambda r: -(r["usage_ratio"] or 0))

    projections = {}
    for minutes in (10.5, 30, 60, 120):
        frames = int(minutes * 60 * FPS)
        epochs = frames / epoch_f
        proj_rows = busy_total * epochs
        projections["%gmin" % minutes] = {
            "frames": frames, "epochs": round(epochs, 2),
            "projected_rai_rows": round(proj_rows),
            "maxlog": maxlog,
            "maxlog_usage_pct": round(100.0 * proj_rows / maxlog, 4),
            "would_hit_maxlog": proj_rows >= maxlog,
        }
    maxlog_ceiling_hours = maxlog / (busy_total * FPS * 3600 / epoch_f)

    # 保守放大 2x 抗密度波动：单 epoch 每类行是否仍低于配额
    overflow = [r for r in tight if r["quota"] and r["epoch_rows"] * 2 >= r["quota"]]
    ok = not overflow
    result = {
        "source_log": str(LOG), "source_code": str(SRC),
        "epoch_frames": epoch_f, "maxlog": maxlog,
        "total_rai_lines": total_rai,
        "epoch_row_counts": {str(k): sum(v.values()) for k, v in sorted(by_epoch.items())},
        "busy_epoch": busy, "busy_epoch_rows": busy_total,
        "sum_of_all_quota_constants": quota_total,
        "per_tag": rows,
        "tightest": tight[:8],
        "projections": projections,
        "maxlog_theoretical_hours": round(maxlog_ceiling_hours, 1),
        "overflow_at_2x": overflow,
        "verdict": "OK" if ok else "AT_RISK",
    }
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = [
        "# P80 · 30 分钟任务日志配额静态审计（零实机）",
        "",
        "依据：v71 实机日志 `%s`（[rai] 行 %d）+ 插件源码 `%s`。",
        "",
        "## 结构性结论",
        "",
        "v71 的 **每 %d 帧重置各行独立配额** + `MAXLOG=%d` 只作全局熔断 ⇒",
        "**任务时长本身不会造成停写**：只要单 epoch 每类行用量 < 该类配额，",
        "30 / 60 / 120 分钟甚至更长都只是把同一个 epoch 循环重复；唯一随任务时长",
        "线性增长的是总 log 序号，需与 MAXLOG 比较。",
        "",
        "最忙 epoch = %d（f=%d..%d），[rai] 行 %d；全部配额常量之和 = %d。",
        "**2 倍密度压力测试下越限的类：%s** ⇒ 结论 **%s**。",
        "",
        "## 时长外推（按最忙 epoch 密度，60 fps）",
        "",
        "| 时长 | 帧数 | epoch 数 | 预计 [rai] 行 | MAXLOG 占用 | 是否触顶 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    lines[2] = lines[2] % (LOG.name, total_rai, SRC.name)
    lines[6] = lines[6] % (epoch_f, maxlog)
    lines[11] = lines[11] % (busy, busy * epoch_f, (busy + 1) * epoch_f - 1, busy_total, quota_total)
    lines[12] = lines[12] % (", ".join("%s(%.2f)" % (r["tag"], r["usage_ratio"] or 0)
                                      for r in overflow) or "无", result["verdict"])
    for k, v in projections.items():
        lines.append("| %s | %d | %.2f | %d | %.4f%% | %s |" %
                     (k, v["frames"], v["epochs"], v["projected_rai_rows"],
                      v["maxlog_usage_pct"], "是" if v["would_hit_maxlog"] else "否"))
    lines += [
        "",
        "MAXLOG 理论可撑 **%.1f 小时**（按最忙 epoch 密度）。",
        "",
        "## 最紧的 8 类行（单 epoch 用量 / 配额）",
        "",
        "| tag | 本 epoch 行数 | 配额常量 | 配额 | 占用 |",
        "|---|---:|---|---:|---:|",
    ]
    lines[-6] = lines[-6] % maxlog_ceiling_hours
    for r in tight[:8]:
        lines.append("| %s | %d | %s | %d | %.1f%% |" %
                     (r["tag"], r["epoch_rows"], r["quota_const"], r["quota"],
                      100 * (r["usage_ratio"] or 0)))
    lines += [
        "",
        "## 边界（不夸大）",
        "",
        "- 这是**静态配额演算**，不是 30 分钟实机日志；实机还会受游戏实际动作密度、",
        "  epoch 边界帧是否恰好命中 `f % 30000 == 0`、宿主日志缓冲影响。",
        "- P79 实机场只有 10.5 分钟，已实测「无 270 截断、无 epoch 盲区、末尾不停写」。",
        "- 成品版把 `MAX_AE/AR/B2/COMBO` 置 0、`MAX_QX` 降到 400，日志密度**只减不增**，",
        "  本审计对成品版同样成立（且更宽松）。",
        "- 真要 100% 确证，仍需回退 v71 探针版打一场 30 分钟任务；用户已明确表示",
        "  这类实机浪费时间，故本轮不安排。",
        "",
        "产物：`out/P80_30min_quota_audit.json`，工具 `tools/audit_p80_30min_quota.py`。",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("verdict=%s busy_epoch=%d rows=%d maxlog_hours=%.1f" %
          (result["verdict"], busy, busy_total, maxlog_ceiling_hours))
    for r in tight[:6]:
        print("  %-6s %5d / %5d  %.1f%%" %
              (r["tag"], r["epoch_rows"], r["quota"], 100 * (r["usage_ratio"] or 0)))
    print("wrote", OUT_MD.name, OUT_JSON.name)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
