# -*- coding: utf-8 -*-
"""日志完整性自检（v71 起，任何一场任务日志都可离线运行）。

根治两类会让人白打一场的缺陷：
  1. 单行 270 字符截断（宿主日志缓冲固定长度）⇒ 关键字段被切掉；
  2. 全局 MAXLOG 封顶 / 配额耗尽 ⇒ 后半场所有日志停写（epoch 盲区）。

用法：
  python tools/check_log_integrity.py <日志路径> [--source <lib.rs>] [--json <输出>]
退出码 0 = 完整；1 = 有 ERROR；2 = 有 WARN（可继续判读但需留意）。
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

LINE_LIMIT = 270          # 宿主日志单行硬上限（实测）
WARN_LEN = 250            # 接近上限即提醒
EPOCH_F = 30000           # 与插件 QUOTA_EPOCH_F 一致
TAG_RE = re.compile(r"\[rai\] ([A-Z][A-Z0-9]*) ")
F_RE = re.compile(r"\bf=(\d+)")
LOG_RE = re.compile(r"\blog=(\d+)")


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def audit(path: Path, source: Path | None = None) -> dict:
    lines = read_lines(path)
    rai = [l for l in lines if "[rai]" in l]
    tagged = [(l, (TAG_RE.search(l).group(1) if TAG_RE.search(l) else "?")) for l in rai]

    # --- 1. 单行截断 ---
    long_by_type = collections.Counter(
        t for l, t in tagged if len(l) >= LINE_LIMIT - 5
    )
    max_len = max((len(l) for l in rai), default=0)
    longest = sorted(((len(l), t, l) for l, t in tagged), reverse=True)[:3]

    # --- 2. 关键行字段完整性 ---
    s_lines = [l for l, t in tagged if t == "S"]
    s2_lines = [l for l, t in tagged if t == "S2"]
    hb_lines = [l for l, t in tagged if t == "HB"]
    # v71：S 只到第 30 字段 anr=，后半在独立 S2 行
    s_bad = [l for l in s_lines if "anr=" not in l]
    s2_bad = [l for l in s2_lines if "ek=" not in l or "log=" not in l]
    hb_bad = [l for l in hb_lines if "hd=" not in l or "log=" not in l]
    s_f = [F_RE.search(l).group(1) for l in s_lines if F_RE.search(l)]
    s2_f = [F_RE.search(l).group(1) for l in s2_lines if F_RE.search(l)]
    pair_bad = len(s_f) - len(set(s_f) & set(s2_f))

    # --- 3. epoch 盲区（全局封顶 / 配额耗尽的直接证据）---
    frames = [int(m.group(1)) for l in rai for m in [F_RE.search(l)] if m]
    epoch_rows = collections.Counter(f // EPOCH_F for f in frames)
    beat_rows = collections.Counter(
        int(m.group(1)) // EPOCH_F
        for l, t in tagged if t == "BEAT"
        for m in [F_RE.search(l)] if m
    )
    # 只把「该 epoch 已有 >=3 条 BEAT 但 [rai] 行 <20」判为盲区，
    # 避免 epoch 刚开头只有 1 条 BEAT 的边界误报
    blind = [(e, n, beat_rows.get(e, 0)) for e, n in sorted(epoch_rows.items())
             if beat_rows.get(e, 0) >= 3 and n < 20]
    # 有 BEAT 但完全无 [rai] 行的 epoch
    missing = [e for e in sorted(set(beat_rows) | set(epoch_rows))
               if beat_rows.get(e, 0) > 0 and epoch_rows.get(e, 0) == 0]

    # --- 4. 时长覆盖 ---
    beat_fs = [int(m.group(1)) for l, t in tagged if t == "BEAT"
               for m in [F_RE.search(l)] if m]
    f0 = min(frames) if frames else 0
    f_last_rai = max(frames) if frames else 0
    f_last_beat = max(beat_fs) if beat_fs else 0
    tail_gap = f_last_beat - f_last_rai
    minutes = f_last_beat / 3600.0 if f_last_beat else 0.0
    density = len(rai) / max(1, f_last_beat - f0)
    est_30m = int(density * 30 * 3600)
    est_60m = int(density * 60 * 3600)

    # --- 5. log 序号是否触顶 ---
    logs = [int(m.group(1)) for l in rai for m in [LOG_RE.search(l)] if m]
    log_max = max(logs) if logs else 0
    maxlog = 1_000_000
    if source and source.exists():
        m = re.search(r"^const MAXLOG:\s*u32\s*=\s*([\d_]+)", source.read_text(encoding="utf-8"), re.M)
        if m:
            maxlog = int(m.group(1).replace("_", ""))
    log_near = log_max >= int(maxlog * 0.9)

    # --- 6. 源码静态提示：格式串静态文本 + 占位符估算 ---
    src_warn = []
    if source and source.exists():
        txt = source.read_text(encoding="utf-8")
        for m in re.finditer(r'info!\("([^"]+)"', txt):
            fmt = m.group(1)
            # 占位符按典型展开 4 字符估算（{:08X} 按 8）
            n_plain = fmt.count("{}")
            n_hex8 = fmt.count("{:08X}")
            n_hex4 = fmt.count("{:04X}")
            n_hex2 = fmt.count("{:02X}")
            est = len(fmt) + n_plain * 4 + n_hex8 * 8 + n_hex4 * 4 + n_hex2 * 2
            if est >= WARN_LEN:
                src_warn.append((est, fmt[:70]))

    errors, warns = [], []
    if long_by_type:
        errors.append("单行 >=%d 字符（被截断）: %s" % (LINE_LIMIT - 5, dict(long_by_type)))
    if s_bad:
        errors.append("S 行字段被切 %d/%d（缺 anr=）" % (len(s_bad), len(s_lines)))
    if s2_bad:
        errors.append("S2 行字段被切 %d/%d（缺 ek= 或 log=）" % (len(s2_bad), len(s2_lines)))
    if s2_lines and pair_bad:
        errors.append("S / S2 未按 f 配对 %d 条" % pair_bad)
    if hb_bad and hb_lines:
        errors.append("HB 行字段被切 %d/%d（缺 hd= 或 log=）" % (len(hb_bad), len(hb_lines)))
    if blind:
        errors.append("epoch 盲区（BEAT 有但 [rai] 行 <20）: %s" % blind)
    if missing:
        errors.append("epoch 完全无 [rai] 行: %s" % missing)
    if tail_gap > 3000:
        errors.append("日志末尾比 BEAT 早 %d 帧（%.1f 秒）⇒ 后半场停写" %
                      (tail_gap, tail_gap / 60.0))
    if log_near:
        errors.append("log 序号 %d 已接近 MAXLOG %d" % (log_max, maxlog))
    if max_len >= WARN_LEN and not long_by_type:
        warns.append("最长行 %d 字符，接近 %d 上限" % (max_len, LINE_LIMIT))
    # 源码静态估算只是粗估（按每占位符 4 字符），不作为 WARN 阻塞判读；
    # 真实截断一律以实测日志行长为判据
    if not hb_lines:
        warns.append("无 HB 行（v69 及更早日志，或本场未到 600 帧采样点）")

    return {
        "path": str(path), "lines": len(lines), "rai_lines": len(rai),
        "max_len": max_len, "long_by_type": dict(long_by_type),
        "longest": [(n, t, l[-90:]) for n, t, l in longest],
        "s_lines": len(s_lines), "s_bad": len(s_bad),
        "s2_lines": len(s2_lines), "s2_bad": len(s2_bad), "pair_bad": pair_bad,
        "hb_lines": len(hb_lines), "hb_bad": len(hb_bad),
        "epoch_rows": {str(k): v for k, v in sorted(epoch_rows.items())},
        "beat_rows": {str(k): v for k, v in sorted(beat_rows.items())},
        "blind": blind, "missing": missing,
        "f0": f0, "f_last_rai": f_last_rai, "f_last_beat": f_last_beat,
        "tail_gap": tail_gap, "minutes": round(minutes, 1),
        "density_per_frame": round(density, 4),
        "est_30min_lines": est_30m, "est_60min_lines": est_60m,
        "log_max": log_max, "maxlog": maxlog,
        "source_long_formats": src_warn[:8],
        "errors": errors, "warns": warns,
        "verdict": "ERROR" if errors else ("WARN" if warns else "OK"),
    }


def render(r: dict) -> str:
    L = ["# 日志完整性自检（v71）", "",
         "日志: `%s`" % r["path"], "",
         "**结论：%s**" % r["verdict"], "",
         "| 指标 | 值 |", "|---|---|",
         "| 总行数 / [rai] 行 | %d / %d |" % (r["lines"], r["rai_lines"]),
         "| 最长行 | %d 字符（上限 %d） |" % (r["max_len"], LINE_LIMIT),
         "| 任务时长（末 BEAT） | %.1f 分钟 (f=%d) |" % (r["minutes"], r["f_last_beat"]),
         "| 日志覆盖到 | f=%d（差 %d 帧） |" % (r["f_last_rai"], r["tail_gap"]),
         "| 30 / 60 分钟外推行数 | %d / %d |" % (r["est_30min_lines"], r["est_60min_lines"]),
         "| MAXLOG / log 序号峰值 | %d / %d |" % (r["maxlog"], r["log_max"]),
         "| epoch 行数分布 | %s |" % r["epoch_rows"],
         "| BEAT 行数分布 | %s |" % r["beat_rows"],
         "| S 行 / 被切 | %d / %d |" % (r["s_lines"], r["s_bad"]),
         "| S2 行 / 被切 / 未配对 | %d / %d / %d |" %
         (r["s2_lines"], r["s2_bad"], r["pair_bad"]),
         "| HB 行 / 被切 | %d / %d |" % (r["hb_lines"], r["hb_bad"]),
         "", ]
    if r["errors"]:
        L += ["## ERROR（必须修，否则这场数据不可用）", ""] + ["- " + x for x in r["errors"]] + [""]
    if r["warns"]:
        L += ["## WARN", ""] + ["- " + x for x in r["warns"]] + [""]
    L += ["## 最长 3 行", ""] + ["- %d 字符 `%s` … `%s`" % (n, t, tail)
                               for n, t, tail in r["longest"]] + [""]
    L += ["## 说明", "",
          "- 宿主日志单行固定 %d 字符，超过即被静默切断；插件侧只能拆成多个短行。" % LINE_LIMIT,
          "- v71 起 `MAXLOG=1_000_000` 只作灾难熔断，密度由每 %d 帧重置的行配额控制。" % EPOCH_F,
          "- epoch 盲区 / 末尾 gap >3000 帧 = 全局封顶或配额耗尽，属严重缺陷。", "",
          "## 源码静态提示（粗估，不阻塞）", "",
          "- %d 条 info! 格式串按每占位符 4 字符估算 >=%d 字符；实测行长才是判据。" %
          (len(r["source_long_formats"]), WARN_LEN), ""]
    for est, head in r["source_long_formats"]:
        L.append("- 估算 %d: `%s`" % (est, head))
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("log", nargs="?", default="02_Workspace/game_p54_lite.txt")
    ap.add_argument("--source", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--md", default=None)
    a = ap.parse_args(argv)
    path = Path(a.log)
    if not path.exists():
        print("MISSING", path)
        return 1
    src = Path(a.source) if a.source else None
    r = audit(path, src)
    print(render(r))
    if a.json:
        Path(a.json).write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8", newline="")
    if a.md:
        Path(a.md).write_text(render(r), encoding="utf-8", newline="")
    return 0 if r["verdict"] == "OK" else (1 if r["verdict"] == "ERROR" else 2)


if __name__ == "__main__":
    sys.exit(main())
