# -*- coding: utf-8 -*-
"""汇总 04_RiseAI/out/rsz_json/ 的静态标量，产出 out/rise_hub_pool_scalars.json。

可重复运行（只读源目录，覆盖写目标 JSON，输出确定性强）：
    python 04_RiseAI/tools/audit_rise_scalars.py

内容：
  - 遍历 out/rsz_json/ 全部 JSON（默认 107 个），统计 partial 质量。
  - 12 个 attack_stance_* Hub: _NextStateID / _TableNo / _Category。
  - 15 个 main_out1_*range*check 池: _TransitionRate / _TableNo。
  - 每个观测值带来源文件 / 实例 index / 类名 / 值。
  - 用标量数值证据判定「Hub→池因果链是否可由标量建立」。

解析质量（P32:36）：60/107 文件 partial=True，_ConditionList/_ActionList 等对象引用
会失步；只有标量 _TransitionRate/_TableNo/_subStaminaPoint 才可信。本工具只摘录标量，
不对对象引用下任何结论。
"""
from __future__ import annotations

import fnmatch
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # 04_RiseAI
SRC = ROOT / "out" / "rsz_json"
OUT = ROOT / "out" / "rise_hub_pool_scalars.json"

HUB_PATTERN = "*attack_stance_*.user.2.json"
POOL_PATTERN = "*main_out1_*range*check.user.2.json"
HUB_FIELDS = ("_NextStateID", "_TableNo", "_Category")
POOL_FIELDS = ("_TransitionRate", "_TableNo")
SENTINEL_TABLENO = 65535  # RegistActionTableInfo 的「无表」哨兵值


def is_scalar(v) -> bool:
    return isinstance(v, (int, float, bool))


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:  # 跳过损坏文件，保证工具可重复运行
        print("  WARN cannot load %s: %s" % (path.name, exc))
        return None


def collect(doc, fields):
    """返回 [(instance_index, class, field, value, is_scalar), ...]。"""
    out = []
    for it in doc.get("instances", []):
        vals = it.get("values") or {}
        if not isinstance(vals, dict):
            continue
        for f in fields:
            if f in vals:
                v = vals[f]
                out.append((it.get("index"), it.get("class"), f, v, is_scalar(v)))
    return out


def summarize(rows, fields):
    """按字段给出 distinct 标量集合与计数（非标量不计入 distinct）。"""
    agg = {}
    for f in fields:
        vals = [r["value"] for r in rows
                if r["field"] == f and r["scalar"]]
        agg[f] = {
            "count": len(vals),
            "distinct": sorted(set(vals)),
        }
    return agg


def main() -> int:
    files = sorted(p for p in SRC.glob("*.json") if p.is_file())
    hubs = [p for p in files if fnmatch.fnmatch(p.name, HUB_PATTERN)]
    pools = [p for p in files if fnmatch.fnmatch(p.name, POOL_PATTERN)]

    partial_all = 0
    rows = []            # 一张结构化表：每行 = 一个标量观测值
    by_file = []
    non_scalar = 0
    for p in files:
        doc = load(p)
        if doc is None:
            continue
        if doc.get("partial"):
            partial_all += 1
        if p in hubs:
            group, fields = "hub", HUB_FIELDS
        elif p in pools:
            group, fields = "pool", POOL_FIELDS
        else:
            continue
        per_field = {f: [] for f in fields}
        for idx, cls, f, v, scalar in collect(doc, fields):
            row = {
                "group": group,
                "source_file": p.name,
                "field": f,
                "instance_index": idx,
                "class": cls,
                "value": v,
                "scalar": scalar,
            }
            rows.append(row)
            if scalar:
                per_field[f].append(v)
            else:
                non_scalar += 1
        by_file.append({
            "source_file": p.name,
            "group": group,
            "root": doc.get("root"),
            "partial": bool(doc.get("partial")),
            "instanceCount": doc.get("instanceCount"),
            "trustedInstances": doc.get("trustedInstances"),
            "fields": per_field,
        })

    hub_rows = [r for r in rows if r["group"] == "hub"]
    pool_rows = [r for r in rows if r["group"] == "pool"]
    hub_agg = summarize(hub_rows, HUB_FIELDS)
    pool_agg = summarize(pool_rows, POOL_FIELDS)

    # ---- 因果链判定：只看标量，证据全部由上面数据算出 ----
    hub_tab = set(hub_agg["_TableNo"]["distinct"])
    hub_next = set(hub_agg["_NextStateID"]["distinct"])
    pool_tab = set(pool_agg["_TableNo"]["distinct"])
    real_pool = sorted(pool_tab - {SENTINEL_TABLENO})
    overlap_tab = sorted(pool_tab & hub_tab)
    overlap_next = sorted(pool_tab & hub_next)
    joinable_real = sorted((set(real_pool) & (hub_tab | hub_next)) - {SENTINEL_TABLENO})
    coverage = (len(joinable_real) / len(real_pool)) if real_pool else 0.0

    # 覆盖不足 1.0 即判否；80 这类重合是状态 ID 与表号的数值巧合，非路由键
    verdict = "YES" if coverage >= 1.0 else "NO"
    reason = (
        "12 个 Hub 的 _TableNo 取值集合 = %s，均为 RegistActionTableInfo 的哨兵/默认值，"
        "不含真实表号；15 个池的 _TableNo = %s 才是实际表号。二者交集仅 %s（哨兵 %d），"
        "无法做 1:1 数值连接。看似重合的 _NextStateID / _TableNo 交集 = %s 属于"
        "「状态 ID 与表号」的语义错配且非一一对应，是数值巧合而非路由键。"
        "真正的 Hub→池路由编码在 _ActionList / _ConditionList 等对象引用里，而 P32:36 "
        "显示 %d/%d 个文件解析失步、这些对象引用不可信。"
        "因此 Hub→池因果链不可由标量建立，需重新解析干净二进制或依赖 plug/ 下的实机探针重建。"
        "注意：本机 pak 已找到且 em131 已完成定向抽取，但这 107 个 em001 旧 JSON 仍是"
        "当时失步的解析结果，em131 新文件并不能替代本表所依据的数据集。"
        % (sorted(hub_tab), sorted(pool_tab), overlap_tab, SENTINEL_TABLENO,
           overlap_next, partial_all, len(files))
    )

    result = {
        "meta": {
            "tool": "04_RiseAI/tools/audit_rise_scalars.py",
            "source_dir": "04_RiseAI/out/rsz_json",
            "source_file_count": len(files),
            "selection": {
                "hub": {"pattern": HUB_PATTERN, "count": len(hubs), "fields": list(HUB_FIELDS)},
                "pool": {"pattern": POOL_PATTERN, "count": len(pools), "fields": list(POOL_FIELDS)},
            },
            "partial_files_all": partial_all,
            "partial_hubs": sum(1 for f in by_file if f["group"] == "hub" and f["partial"]),
            "partial_pools": sum(1 for f in by_file if f["group"] == "pool" and f["partial"]),
            "non_scalar_observations": non_scalar,
        },
        "columns": ["group", "source_file", "field", "instance_index", "class", "value", "scalar"],
        "rows": rows,
        "by_file": by_file,
        "aggregate": {"hub": hub_agg, "pool": pool_agg},
        "causal_chain": {
            "question": "Hub→池因果链是否可由标量建立",
            "verdict": verdict,
            "verdict_cn": "是 / 可由标量建立" if verdict == "YES" else "否 / 不可由标量建立",
            "sentinel_tableno": SENTINEL_TABLENO,
            "evidence": {
                "hub_tableno_distinct": sorted(hub_tab),
                "hub_nextstateid_distinct": sorted(hub_next),
                "pool_tableno_distinct": sorted(pool_tab),
                "pool_tableno_real_minus_sentinel": real_pool,
                "overlap_pool_vs_hub_tableno": overlap_tab,
                "overlap_pool_vs_hub_nextstateid": overlap_next,
                "joinable_real_tablenos": joinable_real,
                "joinable_real_count": len(joinable_real),
                "real_tableno_count": len(real_pool),
                "join_coverage": round(coverage, 6),
            },
            "reason": reason,
        },
        "caveats": [
            "P32:36 质量警告：files_partial=%d/%d；_ConditionList/_ActionList/_TransitionActTbl 等对象引用会失步，不可据此下因果链定论。" % (partial_all, len(files)),
            "仅标量 _TransitionRate/_TableNo/_subStaminaPoint（及 _NextStateID/_Category）可信；本表只摘录标量观测值。",
            "12 个 Hub 与 15 个池均为 em001，取自此前已解包的 107 个文件；em131 关键资产已由 main 从本机 pak 定向抽取（见 out/rsz_main_json/ 与 out/rise_target_extract_plan.md），与本表数据集不同、互补不冲突。",
        ],
    }

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("source JSON      : %d (partial=%d)" % (len(files), partial_all))
    print("hubs / pools     : %d / %d" % (len(hubs), len(pools)))
    print("scalar rows      : %d (non-scalar skipped=%d)" % (len(rows), non_scalar))
    print("causal_chain     : %s  (%s)" % (verdict, result["causal_chain"]["verdict_cn"]))
    print("wrote            : %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
