# -*- coding: utf-8 -*-
"""解析定向抽出的 Rise .user.2，输出 JSON 与关键字段汇总。

绕开 rsz_parse.py 的 CLI bug（它把 --json-out 的值也当成输入文件），
直接 import 其 parse()。只读抽取结果，不改任何游戏文件。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from rsz_parse import parse  # noqa: E402

SRC = ROOT / "refs/_main_extract"
OUT_JSON = ROOT / "out/rsz_main_json"
OUT_FACTS = ROOT / "out/rise_extracted_facts.json"

KEY = re.compile(
    r"range|dist|tired|stamina|mot|nextstate|tableno|actionno|rate|sec|value|threshold|"
    r"category|condition|stateno|stateid|weight", re.I)


def scalar(v):
    return isinstance(v, (int, float, bool)) and not isinstance(v, bool) or isinstance(v, bool)


def main() -> int:
    files = sorted(SRC.rglob("*.user.2"))
    if not files:
        print("NO FILES in", SRC)
        return 1
    OUT_JSON.mkdir(parents=True, exist_ok=True)
    facts = {"source": str(SRC), "files": [], "by_file": {}, "caveats": [
        "P32:36 警告：files_partial=60/107，_ConditionList/_ActionList/_TransitionActTbl 等对象引用会失步；标量才可信",
        "本脚本只做字段级摘录，未做语义判定；对象引用类字段不可作定论",
    ]}
    for p in files:
        r = parse(str(p))
        (OUT_JSON / (p.name + ".json")).write_text(
            json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        rows = []
        for it in r.get("instances", []):
            vals = it.get("values") or {}
            if not isinstance(vals, dict):
                continue
            hit = {k: v for k, v in vals.items()
                   if KEY.search(k) and (isinstance(v, (int, float, bool)) or isinstance(v, str))}
            if hit:
                rows.append({"index": it.get("index"), "class": it.get("class"),
                             "class_found": it.get("class_found"), "fields": hit})
        ok = sum(1 for i in r.get("instances", []) if i.get("class_found"))
        info = {"file": str(p.relative_to(ROOT)), "bytes": p.stat().st_size,
                "root": r.get("root"), "instanceCount": r.get("instanceCount"),
                "class_ok": ok, "bytesConsumed": r.get("bytesConsumed"),
                "fileSize": r.get("fileSize"), "key_fields": rows}
        facts["files"].append(info)
        facts["by_file"][p.name] = rows
        print("%-46s inst=%-4d class_ok=%-4d consumed=%d/%d key_rows=%d" %
              (p.name, r.get("instanceCount", 0), ok,
               r.get("bytesConsumed", 0), r.get("fileSize", 0), len(rows)))
        for x in rows[:4]:
            print("    ", x["class"], str(x["fields"])[:180])
    OUT_FACTS.write_text(json.dumps(facts, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    print("\nwrote", OUT_FACTS)
    print("wrote JSON:", len(files), "->", OUT_JSON)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
