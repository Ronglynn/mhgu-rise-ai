# -*- coding: utf-8 -*-
"""基于 out/rsz_bulk_json_v2/（parser-ref 的 v2 解析器）重新汇总三问。

只读 + 新增/更新 out/ 文件；不改任何工具源码、不覆盖 out/rsz_main_json/。
按 diagnostics.parseOK 过滤：定量结论只取 parseOK=True 的文件；
fieldsComplete=false / not-parseOK 的文件只用于结构/字段名统计，不作定量依据。

产出（覆盖为最终 v2 版）：
  out/rise_bulk_facts.json
"""
from __future__ import annotations

import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V2 = ROOT / "out" / "rsz_bulk_json_v2"
DIAG = json.loads((V2 / "_diag_summary.json").read_text(encoding="utf-8"))
TARGETS = ROOT / "out" / "bulk_target_paths.txt"
PLAN = json.loads((ROOT / "out" / "bulk_plan_stats.json").read_text(encoding="utf-8"))
EM131_JSON = ROOT / "out" / "rsz_main_json"          # 只读对照
LIST = ROOT.parent / "00_Tools" / "06_REEngine_Pak" / "assets" / "filelist" / "MHR_STM_Release.list"
OUT = ROOT / "out" / "rise_bulk_facts.json"

TIRED_KEY = re.compile(r"tired|fatigue|rest", re.I)


def basename_of(json_name: str) -> str:
    return json_name[:-5] if json_name.endswith(".json") else json_name


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


def em_of(name: str) -> str | None:
    m = re.match(r"(em\d{3})_", name)
    return m.group(1) if m else None


def numeric_array(v):
    """严格数值数组：元素全为 int/float（bool / 结构化 ref dict / 字符串均排除）。"""
    if not isinstance(v, list) or not v:
        return None
    nums = []
    for e in v:
        if isinstance(e, bool) or not isinstance(e, (int, float)):
            return None
        nums.append(e)
    return nums


def monotonic(nums):
    if len(nums) < 2:
        return False, False
    return (all(nums[i] <= nums[i + 1] for i in range(len(nums) - 1)),
            all(nums[i] < nums[i + 1] for i in range(len(nums) - 1)))


def main() -> int:
    jsons = sorted(V2.glob("*.user.2.json"))
    targets = set(x.strip() for x in TARGETS.read_text(encoding="utf-8").splitlines() if x.strip())

    # 定量容器（只收 parseOK 文件）
    arrays_by_field = collections.defaultdict(list)   # field -> [{file,class,len,values,nondec,strict}]
    len5_mono = []
    numeric_len_dist = collections.Counter()
    range_per_file = collections.defaultdict(list)
    tired_hits = []
    tiredsec_values = collections.Counter()
    motrate_values = collections.Counter()
    tiredsec_by_file = {}
    motrate_by_file = {}
    ta = collections.defaultdict(lambda: {"TableNo": [], "ActionNo": [], "Category": [],
                                          "classes": set(), "ref_fields": collections.Counter()})
    name_like_fields = collections.Counter()

    by_monster = collections.defaultdict(lambda: collections.Counter())
    by_class = collections.Counter()
    parseOK_files = []
    not_parseOK_files = []
    fields_false_files = []

    for jp in jsons:
        r = json.loads(jp.read_text(encoding="utf-8"))
        bn = basename_of(jp.name)
        cl = cls_of(bn)
        em = em_of(bn)
        rel = "refs/_bulk_extract/natives/stm/enemy/%s/.../%s" % (em or "?", bn)
        dg = r.get("diagnostics", {})
        ok = bool(dg.get("parseOK"))
        fc = bool(dg.get("fieldsComplete"))
        by_class[cl] += 1
        if em:
            by_monster[em]["total"] += 1
            if ok:
                by_monster[em]["parseOK"] += 1
        if ok:
            parseOK_files.append(rel)
        else:
            not_parseOK_files.append(rel)
        if not fc:
            fields_false_files.append(rel)

        for it in r.get("instances", []):
            vals = it.get("values") or {}
            if not isinstance(vals, dict):
                continue
            icls = it.get("class") or "?"
            for k, v in vals.items():
                # 结构/字段名统计：所有文件都可看
                if TIRED_KEY.search(k):
                    tired_hits.append({"file": rel, "class": icls, "field": k,
                                       "value": v if isinstance(v, (int, float, bool, str)) else str(v)[:60],
                                       "parseOK": ok})
                if re.search(r"name|title|label|text|string", k, re.I) and isinstance(v, str):
                    name_like_fields[k] += 1
                # 定量统计：仅 parseOK 文件
                if not ok:
                    continue
                na = numeric_array(v)
                if na is not None:
                    nondec, strict = monotonic(na)
                    numeric_len_dist[len(na)] += 1
                    rec = {"file": rel, "class": icls, "field": k, "len": len(na),
                           "values": na, "nondec": nondec, "strict": strict}
                    arrays_by_field[k].append(rec)
                    if len(na) == 5 and (nondec or strict):
                        len5_mono.append(rec)
                    if cl == "range_data":
                        range_per_file[rel].append({"field": k, "len": len(na),
                                                    "values": na, "nondec": nondec, "strict": strict})
                if k == "_tiredSec" and isinstance(v, (int, float)) and not isinstance(v, bool):
                    tiredsec_values[float(v)] += 1
                    tiredsec_by_file[rel] = float(v)
                if k == "_motRate" and isinstance(v, (int, float)) and not isinstance(v, bool):
                    motrate_values[float(v)] += 1
                    motrate_by_file[rel] = float(v)
                if k in ("_TableNo", "_ActionNo", "_Category") and isinstance(v, (int, float)) and not isinstance(v, bool):
                    ta[rel][k.lstrip("_")].append(v)
                    ta[rel]["classes"].add(icls)
                # 统计结构化 ref 字段（v2 特征）
                if isinstance(v, dict) and "ref" in v:
                    ta[rel]["ref_fields"][k] += 1
                elif isinstance(v, list) and v and isinstance(v[0], dict) and "ref" in v[0]:
                    ta[rel]["ref_fields"][k] += len(v)

    # ---- (a) 几何阈值 vs 仇恨参数 ----
    def summarize(field):
        arrs = arrays_by_field.get(field, [])
        lens = collections.Counter(a["len"] for a in arrs)
        return {
            "count": len(arrs),
            "len_distribution": {str(k): v for k, v in sorted(lens.items())},
            "strictly_increasing": sum(1 for a in arrs if a["strict"]),
            "nondecreasing": sum(1 for a in arrs if a["nondec"]),
            "non_monotonic": sum(1 for a in arrs if not a["nondec"]),
            "sample_values": [a["values"] for a in arrs[:6]],
            "interpretation": "",
        }

    rd = summarize("_RangeDistance")
    rd["interpretation"] = ("几何距离阈值：4 个严格递增阈值切出 5 个距离区间（range1..5）；"
                            "即 Rise 确有几何阈值阶梯")
    hb = summarize("_range_hate_add_data")
    hb["interpretation"] = "仇恨/气息增量参数（非单调、可递减/含负数），不是几何距离阈值"
    kh = summarize("_RangeKehaiAdd")
    kh["interpretation"] = "气息（Kehai）增量参数（非单调），不是几何距离阈值"

    # ---- (b) TableNo / ActionNo（基于 parseOK 的 act/combo）----
    tableno_match = 0
    actcombo_with_table = 0
    actcombo_with_action = 0
    actionno_values = []
    ref_field_counter = collections.Counter()
    for f, d in ta.items():
        m = re.search(r"_(?:act|combo)_(\d+)\.user\.2", f)
        if not m:
            continue
        fno = int(m.group(1))
        if d["TableNo"]:
            actcombo_with_table += 1
            if any(int(x) == fno for x in d["TableNo"]):
                tableno_match += 1
        if d["ActionNo"]:
            actcombo_with_action += 1
            actionno_values.extend(d["ActionNo"])
        for k, n in d["ref_fields"].items():
            ref_field_counter[k] += n

    # ---- (b) filelist 文本层证据 ----
    lines = [x.strip() for x in LIST.read_text(encoding="utf-8", errors="replace").splitlines() if x.strip()]
    motlist_all = sum("motlist" in l for l in lines)
    message_all = sum("message" in l for l in lines)
    enemy_motlist = sum(bool(re.search(r"enemy/em\d{3}/.*motlist", l)) for l in lines)
    enemy_name_text = sum(bool(re.search(
        r"enemy/em\d{3}/.*(\.msg\.|mmsg|actionname|movename|attackname|action_name|"
        r"mot_name|skillname|name)", l, re.I)) for l in lines)
    enemy_msg = sum(bool(re.search(r"enemy/em\d{3}/.*\.msg\.", l)) for l in lines)

    # ---- (c) em131 只读对照 ----
    em131_ref = {}
    if EM131_JSON.is_dir():
        for p in sorted(EM131_JSON.glob("*.json")):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            for it in d.get("instances", []):
                v = it.get("values") or {}
                if not isinstance(v, dict):
                    continue
                for k in ("_tiredSec", "_motRate", "_hyakuryuTiredSec"):
                    if k in v:
                        em131_ref.setdefault(k, []).append({"file": p.name, "value": v[k]})

    facts = {
        "generated_by": "tools/bulk_facts_v2.py",
        "parser": "rsz_parse_v2 (parser-ref)",
        "source_json": "out/rsz_bulk_json_v2",
        "source_assets": "refs/_bulk_extract",
        "note": "本文件为 v2 定稿版（覆盖 v1 版）。定量结论只取 diagnostics.parseOK=True 的文件；"
                "fieldsComplete=false 文件只用于结构/字段名统计，不作定量依据。",
        "quantitative_basis": {
            "files_total": DIAG["files_total"],
            "parseOK_count": DIAG["parseOK_count"],
            "parseOK_by_class": DIAG["parseOK_by_class"],
            "not_parseOK_count": len(not_parseOK_files),
            "not_parseOK_files": not_parseOK_files,
            "fieldsComplete_false_count": len(fields_false_files),
            "fieldsComplete_false_files": fields_false_files,
            "objectRefs": {"total": DIAG["objectRefs_total"], "valid": DIAG["objectRefs_valid"],
                            "invalid": DIAG["objectRefs_invalid"]},
            "v1_reference": {"parser": "rsz_parse.py (v1)", "partial_files": 191,
                             "files_with_out_of_range_refs": 252,
                             "invalid_refs": 1899, "ref_total": 24371,
                             "note": "v1 失步由 userdata 实例占位 0 字节被误内联解析导致，见 P80_object_ref_resolution.md §1"},
            "main_v2_crosscheck": "out/P80_v2_crosscheck_52monsters.json：156/156 (range+stamina) parseOK、tail=0",
            "parser_ref_full_endorsement": ("parser-ref out/_v2_full_468.py 内存全量重跑 468："
                                            "430/468 parseOK、438/468 tail=0；"
                                            "range/stamina/main/combat_main 78/78 全 OK、0 非法引用；"
                                            "range/stamina 的 v1↔v2 ref 序列逐项一致"),
            "not_parseOK_root_causes": {
                "template_missing_class": 37,
                "string_utf16_inline_mode": 1,
                "string_mode_file": "em007_act_001.user.2",
                "missing_typeIds": {"0df87250": 25, "077a9e93": 7, "026f597b": 6,
                                    "0a84b65f": 4, "07e5ee43": 3, "04db4de2": 3,
                                    "02da62cf": 2, "041c55aa": 1, "0a59bcb6": 1},
                "note": ("9 个未收录 typeId、52 个缺类实例/37 文件；String 内联 UTF-16 变长串"
                         "被当作 4 字节 ref（见 parser-ref P80_object_ref_resolution.md §8.6）"),
                "v1_caveat": ("em007_act_001 / em072_act_002 的 v1 非法 ref=0 但 partial 提前 break 丢字段"
                              " ⇒ 不能把『非法 ref=0』当完整判据，须按 diagnostics.parseOK 过滤"),
                "remediation": ("parser-ref §8.7 / out/_probe_unknown_skip.py：未知类统一占 S 字节实验"
                                "仅 11/37(29.7%) 达 parseOK+tail=0，26 个仍修不好 ⇒ 本轮不补"
                                " rszmhrise.json（二进制推不出字段名/类型、会改 66MB 共享基线、收益为零）、"
                                "不扩展 v2 缺类容错（产物与工具版本不一致、不改变定案），保持 parseOK=false 排除。"
                                "未来线索：最佳 S=28 在 10 文件重复出现，暗示 0df87250 类数据长约 28B"),
            },
        },
        "coverage": {
            "target_files": len(targets),
            "extracted_files": len(jsons),
            "monster_count": len(by_monster),
            "by_class": dict(by_class),
            "by_monster": {k: dict(v) for k, v in sorted(by_monster.items())},
        },
        "questions": {
            "a": {
                "question": "全怪 range_data 里是否存在 5 元素递增数值阈值数组；_RangeDistance 是不是几何阈值",
                "based_on": "v2 parseOK 文件（range_data 78/78 parseOK）",
                "_RangeDistance": rd,
                "_range_hate_add_data": hb,
                "_RangeKehaiAdd": kh,
                "geometric_threshold_verdict": ("_RangeDistance 为 4 个严格递增的几何距离阈值，"
                                                "4 阈值切 5 区间（range1..5）⇒ Rise 确有几何阈值阶梯；"
                                                "P73「Rise 无几何阈值阶梯」作废"),
                "numeric_len_distribution_all_parseOK_files": {str(k): v for k, v in sorted(numeric_len_dist.items())},
                "numeric_len_by_field": {"%s|len=%d" % (k, n): c
                                         for k, arrs in arrays_by_field.items()
                                         for n, c in collections.Counter(a["len"] for a in arrs).items()},
                "len5_monotonic_numeric_arrays": len5_mono,
                "len5_monotonic_count": len(len5_mono),
                "range_data_files_count": len(range_per_file),
                "range_data_per_file": {k: v for k, v in sorted(range_per_file.items())},
            },
            "b": {
                "question": "_TableNo -> _actionNo -> 招式名 中间映射能否建立",
                "based_on": "v2 parseOK 的 act/combo 文件（act 79/105、combo 39/51 parseOK；38 个 not-parseOK 排除定量）",
                "act_combo_files_with_TableNo": actcombo_with_table,
                "act_combo_files_with_ActionNo": actcombo_with_action,
                "TableNo_equals_own_file_no_count": tableno_match,
                "ActionNo_value_min": min(actionno_values) if actionno_values else None,
                "ActionNo_value_max": max(actionno_values) if actionno_values else None,
                "ActionNo_distinct_sample": sorted(set(int(x) for x in actionno_values))[:40],
                "structured_ref_field_counts": dict(ref_field_counter),
                "name_like_string_fields": dict(name_like_fields),
                "filelist_evidence": {
                    "filelist_lines": len(lines),
                    "motlist_all": motlist_all,
                    "message_all": message_all,
                    "enemy_motlist": enemy_motlist,
                    "enemy_msg_files": enemy_msg,
                    "enemy_action_name_text_candidates": enemy_name_text,
                    "plan_enemy_name_text_candidates": PLAN.get("enemy_name_text_candidates"),
                },
                "verdict": ("TableNo=文件编号这一跳可建；_TableNo 与 _ActionNo 分属不同类/实例、"
                            "无标量外键逐行对应（v2 结构化 ref 仍是文件内 instance index，无跨文件引用槽）；"
                            "且 enemy 目录招式名文本表 0 命中 ⇒ 完整映射不能建立"),
                "sample_TableNo_ActionNo": [
                    {"file": f, "TableNo": d["TableNo"], "ActionNo": d["ActionNo"], "Category": d["Category"]}
                    for f, d in list(sorted(ta.items()))[:8]],
            },
            "c": {
                "question": "_tiredSec/_motRate 是否跨怪恒为 0.0/1.0；全怪 tired/fatigue/rest 字段",
                "based_on": "v2 parseOK 文件（stamina_data 78/78 parseOK）",
                "_tiredSec_values": {str(k): v for k, v in sorted(tiredsec_values.items())},
                "_motRate_values": {str(k): v for k, v in sorted(motrate_values.items())},
                "_tiredSec_is_always_0": set(tiredsec_values) == {0.0} and bool(tiredsec_values),
                "_motRate_is_always_1": set(motrate_values) == {1.0} and bool(motrate_values),
                "_tiredSec_by_file": tiredsec_by_file,
                "_motRate_by_file": motrate_by_file,
                "tired_fatigue_rest_field_hits": tired_hits,
                "tired_fatigue_rest_hit_count": len(tired_hits),
                "tired_field_names": dict(collections.Counter(h["field"] for h in tired_hits)),
                "em131_readonly_reference": em131_ref,
                "verdict": ("em131 的 _tiredSec=0/_motRate=1 是 17/78 的默认值特例；跨 52 怪这两个字段"
                            "是按怪配置的数据表参数（30~120 秒、0.8~1.0）⇒ P78「疲惫数据表级复刻否定」作废"),
            },
        },
        "verdicts": {
            "P73_rise_no_geometric_threshold_ladder": "作废（_RangeDistance 4 阈值切 5 区间=几何阈值阶梯）",
            "P78_1_W2_route_B_wrong_layer": "作废/改判（Rise 几何阈值阶梯存在，路线 B 对齐的层没错；原判基于 em131 单怪 + 误把仇恨参数当阈值）",
            "P78_4_tired_datatable_replication_negation": "作废（Rise 疲惫表跨怪真实存在且可变；GU 侧结构性限制另论）",
            "cross_monster_generality": "结构/字段跨怪通用（支持通用规则），数值按怪配置（须参数化，不可硬编码单一常量）",
        },
        "caveats": [
            "v2 仍有 38 个 not-parseOK / 37 个 fieldsComplete=false（集中 act/combo）：根因 37 个模板缺类 + 1 个 String 变长串模式(em007_act_001)，不作定量依据",
            "motlist/message 只查 filelist 文件名层，未抽 .motlist.528/.msg 二进制内容",
            "全部静态资产复核，无 Rise 实机/反汇编（沿用 P32:201 证据等级）",
        ],
    }
    OUT.write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")

    print("=== v2 facts 汇总 ===")
    print("parseOK %d/%d ; not_parseOK=%d fieldsComplete_false=%d" % (
        DIAG["parseOK_count"], DIAG["files_total"], len(not_parseOK_files), len(fields_false_files)))
    print("Q(a) _RangeDistance count=%d strict=%d/%d lens=%s" % (
        rd["count"], rd["strictly_increasing"], rd["count"], rd["len_distribution"]))
    print("     _range_hate_add_data count=%d non_monotonic=%d ; len5_mono=%d" % (
        hb["count"], hb["non_monotonic"], len(len5_mono)))
    print("Q(b) TableNo==fileNo %d/%d ; ActionNo files=%d range=%s..%s" % (
        tableno_match, actcombo_with_table, actcombo_with_action,
        facts["questions"]["b"]["ActionNo_value_min"], facts["questions"]["b"]["ActionNo_value_max"]))
    print("Q(c) _tiredSec=%s ; _motRate=%s" % (dict(tiredsec_values), dict(motrate_values)))
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
