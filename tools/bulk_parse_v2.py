# -*- coding: utf-8 -*-
"""用 parser-ref 的 rsz_parse_v2.parse() 重解析 52 怪全部 468 个 .user.2。

只读 + 新增文件：不改 tools/rsz_parse.py / tools/rsz_parse_v2.py，
不覆盖 out/rsz_main_json/。CLI --all 硬编码 em131 目录且 468 路径会超
Windows 命令行长度，所以直接 import parse() 并 rglob _bulk_extract。

产出：
  out/rsz_bulk_json_v2/*.user.2.json     每个文件的 v2 结构化解析
  out/rsz_bulk_json_v2/_diag_summary.json  parseOK / fieldsComplete / 引用合法率统计
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from rsz_parse_v2 import parse  # noqa: E402

SRC = ROOT / "refs" / "_bulk_extract"
OUT = ROOT / "out" / "rsz_bulk_json_v2"
OUT.mkdir(parents=True, exist_ok=True)


def cls_of(name: str) -> str:
    if name.endswith("_range_data.user.2"):
        return "range_data"
    if name.endswith("_stamina_data.user.2"):
        return "stamina_data"
    if name.endswith("_combat_main.user.2"):
        return "combat_main"
    if name.endswith("_main.user.2"):
        return "main"
    if "_combo_" in name:
        return "combo"
    if "_act_" in name:
        return "act"
    return "other"


def main() -> int:
    files = sorted(SRC.rglob("*.user.2"))
    if not files:
        print("NO FILES in", SRC)
        return 1

    summary = {
        "parser": "rsz_parse_v2",
        "source": "refs/_bulk_extract",
        "output": "out/rsz_bulk_json_v2",
        "files_total": len(files),
        "parseOK_count": 0,
        "parseOK_by_class": {},
        "not_parseOK": [],
        "fieldsComplete_false": [],
        "files_with_invalid_refs": [],
        "objectRefs_total": 0,
        "objectRefs_valid": 0,
        "objectRefs_invalid": 0,
        "arrayCounts_total": 0,
        "arrayCounts_implausible": 0,
        "alignmentSearch_triggered": [],
        "parse_failures": [],
        "per_file": [],
    }
    by_class = {}

    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        cl = cls_of(p.name)
        try:
            r = parse(str(p))
        except Exception as exc:  # noqa: BLE001
            summary["parse_failures"].append({"file": rel, "error": "%s: %s" % (type(exc).__name__, exc)})
            print("FAIL", p.name, exc)
            continue
        (OUT / (p.name + ".json")).write_text(
            json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        dg = r["diagnostics"]
        inv = len(dg["objectRefs"]["invalid"])
        rec = {
            "file": rel, "class": cl,
            "instanceCount": r["instanceCount"], "userdataCount": r["userdataCount"],
            "root": r.get("root"),
            "parseOK": dg["parseOK"], "fieldsComplete": dg["fieldsComplete"],
            "tail": dg["tail"], "bytesConsumed": dg["bytesConsumed"],
            "dataRegionLen": dg["dataRegionLen"],
            "objectRefs": {"total": dg["objectRefs"]["total"],
                            "valid": dg["objectRefs"]["valid"], "invalid": inv},
            "arrayCounts": {"total": dg["arrayCounts"]["total"],
                            "implausible": len(dg["arrayCounts"]["implausible"])},
            "alignmentSearchTriggered": dg["alignmentSearch"]["triggered"],
        }
        summary["per_file"].append(rec)
        bc = by_class.setdefault(cl, [0, 0])
        bc[0] += 1
        if dg["parseOK"]:
            summary["parseOK_count"] += 1
            bc[1] += 1
        else:
            summary["not_parseOK"].append(rel)
        if not dg["fieldsComplete"]:
            summary["fieldsComplete_false"].append(rel)
        if inv:
            summary["files_with_invalid_refs"].append({"file": rel, "invalid": inv})
        summary["objectRefs_total"] += dg["objectRefs"]["total"]
        summary["objectRefs_valid"] += dg["objectRefs"]["valid"]
        summary["objectRefs_invalid"] += inv
        summary["arrayCounts_total"] += dg["arrayCounts"]["total"]
        summary["arrayCounts_implausible"] += len(dg["arrayCounts"]["implausible"])
        if dg["alignmentSearch"]["triggered"]:
            summary["alignmentSearch_triggered"].append(rel)

    summary["parseOK_by_class"] = {k: {"total": v[0], "parseOK": v[1]} for k, v in sorted(by_class.items())}
    (OUT / "_diag_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n=== v2 批量重解析汇总 ===")
    print("files            :", summary["files_total"], " parse_failures:", len(summary["parse_failures"]))
    print("parseOK          :", summary["parseOK_count"], "/", summary["files_total"])
    print("by class         :", summary["parseOK_by_class"])
    print("fieldsComplete=false (不作定量依据):", len(summary["fieldsComplete_false"]))
    print("not parseOK      :", len(summary["not_parseOK"]))
    print("files w/ invalid refs:", len(summary["files_with_invalid_refs"]))
    print("objectRefs       : total=%d valid=%d invalid=%d" % (
        summary["objectRefs_total"], summary["objectRefs_valid"], summary["objectRefs_invalid"]))
    print("arrayCounts      : total=%d implausible=%d" % (
        summary["arrayCounts_total"], summary["arrayCounts_implausible"]))
    print("alignSearch trig :", len(summary["alignmentSearch_triggered"]))
    print("wrote", OUT / "_diag_summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
