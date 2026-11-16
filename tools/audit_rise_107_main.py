# -*- coding: utf-8 -*-
"""对拍已解包的 107 个 Rise JSON：12 Hub 与 15 池的标量能否建立因果链。

只读，不做语义推断。输出 out/rise_107_hub_pool_main.json。
"""
from __future__ import annotations

import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "out/rsz_json"
OUT = ROOT / "out/rise_107_hub_pool_main.json"


def vals(d):
    for it in d.get("instances", []):
        c = it.get("class") or ""
        v = it.get("values")
        if isinstance(v, dict):
            yield c, v


def main() -> int:
    files = sorted(SRC.glob("*.json"))
    hubs, pools, other = [], [], []
    hub_tc, hub_next, hub_true = [], [], 0
    pool_rates, pool_tables, pool_values = [], [], []
    for p in files:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        name = p.name
        tc = []
        rates, tables, tv = [], [], []
        for c, v in vals(d):
            if c.endswith("ThinkCondition") or "ThinkCondition" in c:
                tc.append({k: v.get(k) for k in
                           ("_IsActionEnd", "_IsUnderLayerEnd", "_NextStateID")})
            for k in v:
                if k == "_TransitionRate" and isinstance(v[k], (int, float)):
                    rates.append(v[k])
                if k == "_TableNo" and isinstance(v[k], int) and v[k] != 65535:
                    tables.append(v[k])
                if k == "_TransitionValue" and isinstance(v[k], (int, float)):
                    tv.append(v[k])
        rec = {"file": name, "thinkConditions": tc, "rates": rates,
               "tables": tables, "transitionValues": tv}
        if "attack_stance" in name:
            hubs.append(rec)
            hub_tc += tc
            hub_next += [x.get("_NextStateID") for x in tc if x.get("_NextStateID") is not None]
            hub_true += sum(1 for x in tc if x.get("_IsActionEnd") is True)
        elif "range" in name and "check" in name:
            pools.append(rec)
            pool_rates += rates
            pool_tables += tables
            pool_values += tv
        else:
            other.append(rec)
    hub_tables = [t for h in hubs for t in h["tables"]]
    shared = sorted(set(hub_tables) & set(pool_tables))
    out = {
        "files": len(files), "hub_files": len(hubs), "pool_files": len(pools),
        "other_files": len(other),
        "hub_thinkConditions": len(hub_tc),
        "hub_IsActionEnd_true": hub_true,
        "hub_NextStateID_values": dict(collections.Counter(str(x) for x in hub_next)),
        "pool_rates_sum_per_file": {x["file"]: sum(x["rates"]) for x in pools},
        "pool_rates_all_sum_const_100": all(
            abs(sum(x["rates"]) - 100) < 1e-6 for x in pools if x["rates"]),
        "pool_TableNo_set": sorted(set(pool_tables)),
        "hub_TableNo_set": sorted(set(hub_tables)),
        "shared_TableNo": shared,
        "transitionValue_range": [min(pool_values), max(pool_values)] if pool_values else [],
        "verdict": ("Hub 与 15 池共享 TableNo=%s，可作为弱关联；但 Hub 的 _NextStateID 是状态 ID，"
                    "不等于池索引，且对象引用失步 ⇒ 因果链仍不能定案" % shared if shared else
                    "Hub 与 15 池无共享 TableNo ⇒ 标量无法建立因果链"),
        "caveat": "P32:36 对象引用失步；本对拍只用标量，不作语义结论",
        "pool_file_details": [{"file": x["file"], "rates": x["rates"],
                               "tables": sorted(set(x["tables"]))} for x in pools],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("files=%d hub=%d pool=%d other=%d" % (len(files), len(hubs), len(pools), len(other)))
    print("Hub ThinkCondition=%d  _IsActionEnd True=%d  _NextStateID=%s" %
          (len(hub_tc), hub_true, out["hub_NextStateID_values"]))
    print("池率和恒100 =", out["pool_rates_all_sum_const_100"])
    print("Hub TableNo =", out["hub_TableNo_set"])
    print("池  TableNo =", out["pool_TableNo_set"])
    print("共享 TableNo =", shared)
    print("结论:", out["verdict"])
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
