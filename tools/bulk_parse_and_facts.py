# -*- coding: utf-8 -*-
"""批量解析 refs/_bulk_extract/ 的 .user.2 -> out/rsz_bulk_json/，并汇总三问。

只读抽取结果与 filelist / 已有 em131 JSON（只读），新增文件到 out/。
不覆盖 out/rsz_main_json/、refs/_main_extract/。
绕开 rsz_parse.py 的 CLI bug，直接 import parse()。

产出：
  out/rsz_bulk_json/*.user.2.json   每个文件的结构化解析
  out/rise_bulk_facts.json          覆盖数 / 按怪统计 / 解析成功率 / 三问数据
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from rsz_parse import parse  # noqa: E402

SRC = ROOT / "refs" / "_bulk_extract"
OUT_JSON = ROOT / "out" / "rsz_bulk_json"
OUT_FACTS = ROOT / "out" / "rise_bulk_facts.json"
TARGETS = ROOT / "out" / "bulk_target_paths.txt"
PLAN = ROOT / "out" / "bulk_plan_stats.json"
EM131_JSON = ROOT / "out" / "rsz_main_json"          # 只读对照
LIST = ROOT.parent / "00_Tools" / "06_REEngine_Pak" / "assets" / "filelist" / "MHR_STM_Release.list"

KEY = re.compile(
    r"range|dist|tired|fatigue|rest|stamina|mot|tableno|actionno|category|"
    r"rate|sec|value|threshold|point|weight|state|id", re.I)
TIRED_KEY = re.compile(r"tired|fatigue|rest", re.I)


def em_of(path: Path) -> str | None:
    m = re.search(r"/(em\d{3})/", path.as_posix())
    return m.group(1) if m else None


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


def numeric_array(v):
    """严格数值数组：元素必须全是 int/float（bool 与 dict/ref 字符串都排除）。
    返回 (numbers, kind)；非数值数组返回 None。"""
    if not isinstance(v, list):
        return None
    if not v:
        return [], "empty"
    nums = []
    for e in v:
        if isinstance(e, bool):
            return None
        if isinstance(e, (int, float)):
            nums.append(e)
        else:
            return None
    return nums, "numeric"


def monotonic(nums):
    if len(nums) < 2:
        return False, False
    nondec = all(nums[i] <= nums[i + 1] for i in range(len(nums) - 1))
    strict = all(nums[i] < nums[i + 1] for i in range(len(nums) - 1))
    return nondec, strict


def main() -> int:
    files = sorted(SRC.rglob("*.user.2"))
    if not files:
        print("NO FILES in", SRC)
        return 1
    OUT_JSON.mkdir(parents=True, exist_ok=True)
    targets = set(x.strip() for x in TARGETS.read_text(encoding="utf-8").splitlines() if x.strip())
    plan = json.loads(PLAN.read_text(encoding="utf-8"))

    # 相对 ROOT 的 posix 路径（与 bulk_target_paths.txt 对齐）
    extracted = set()
    per_file = []
    parse_failures = []
    partial_files = []
    by_monster = collections.defaultdict(lambda: collections.Counter())
    by_class = collections.Counter()
    class_found_total = 0
    instance_total = 0

    # 三问数据容器
    arr_len_global = collections.Counter()          # 数值数组长度分布（全文件）
    arr_len_by_field = collections.Counter()        # (字段名, len)
    arr_len5_mono = []                              # len==5 且单调的数值数组（全文件）
    range_per_file = {}                             # 每个 range_data 文件 -> 数值数组清单
    tired_hits = []                                 # tired/fatigue/rest 命名字段
    tiredsec_values = collections.Counter()
    motrate_values = collections.Counter()
    tiredsec_by_file = {}
    motrate_by_file = {}
    table_action = collections.defaultdict(lambda: {"TableNo": [], "ActionNo": [],
                                                     "Category": [], "classes": set()})
    name_like_fields = collections.Counter()

    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        extracted.add(rel.split("_bulk_extract/", 1)[-1])
        em = em_of(p)
        cl = cls_of(p.name)
        if em:
            by_monster[em]["total"] += 1
            by_monster[em][cl] += 1
        by_class[cl] += 1
        try:
            r = parse(str(p))
        except Exception as exc:                     # noqa: BLE001
            parse_failures.append({"file": rel, "error": "%s: %s" % (type(exc).__name__, exc)})
            (OUT_JSON / (p.name + ".json")).write_text(
                json.dumps({"file": str(p), "parse_error": str(exc)}, ensure_ascii=False, indent=1),
                encoding="utf-8")
            continue
        (OUT_JSON / (p.name + ".json")).write_text(
            json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        if em:
            by_monster[em]["parsed_ok"] += 1
        if r.get("partial"):
            partial_files.append(rel)
        insts = r.get("instances", [])
        cok = sum(1 for i in insts if i.get("class_found"))
        class_found_total += cok
        instance_total += r.get("instanceCount", 0)
        rows = []
        for it in insts:
            vals = it.get("values") or {}
            if not isinstance(vals, dict):
                continue
            icls = it.get("class") or "?"
            # 关键字段摘录
            hit = {k: v for k, v in vals.items()
                   if KEY.search(k) and isinstance(v, (int, float, bool, str))}
            if hit:
                rows.append({"index": it.get("index"), "class": icls,
                             "class_found": it.get("class_found"), "fields": hit})
            for k, v in vals.items():
                # (a) 数值数组长度分布
                na = numeric_array(v)
                if na is not None:
                    nums, kind = na
                    if kind == "numeric":
                        arr_len_global[len(nums)] += 1
                        arr_len_by_field[(k, len(nums))] += 1
                        nondec, strict = monotonic(nums)
                        if len(nums) == 5 and (nondec or strict):
                            arr_len5_mono.append({
                                "file": rel, "class": icls, "field": k,
                                "values": nums, "nondecreasing": nondec,
                                "strictly_increasing": strict})
                        if cl == "range_data":
                            range_per_file.setdefault(rel, []).append(
                                {"field": k, "len": len(nums), "values": nums,
                                 "nondec": nondec, "strict": strict})
                # (c) tired/fatigue/rest 命名字段 + _tiredSec/_motRate 值
                if TIRED_KEY.search(k):
                    tired_hits.append({"file": rel, "class": icls, "field": k,
                                       "value": v if isinstance(v, (int, float, bool, str)) else str(v)[:60]})
                if k == "_tiredSec" and isinstance(v, (int, float)) and not isinstance(v, bool):
                    tiredsec_values[float(v)] += 1
                    tiredsec_by_file[rel] = float(v)
                if k == "_motRate" and isinstance(v, (int, float)) and not isinstance(v, bool):
                    motrate_values[float(v)] += 1
                    motrate_by_file[rel] = float(v)
                # (b) act/combo 里的 _ActionNo/_TableNo/_Category + 名字类字段
                if k in ("_TableNo", "_ActionNo", "_Category") and isinstance(v, (int, float)):
                    table_action[rel][k.lstrip("_")].append(v)
                    table_action[rel]["classes"].add(icls)
                if re.search(r"name|title|label|text|string", k, re.I) and isinstance(v, str):
                    name_like_fields[k] += 1
        per_file.append({"file": rel, "em": em, "class": cl, "root": r.get("root"),
                         "instanceCount": r.get("instanceCount"), "class_ok": cok,
                         "trustedInstances": r.get("trustedInstances"),
                         "partial": r.get("partial"),
                         "bytesConsumed": r.get("bytesConsumed"), "fileSize": r.get("fileSize"),
                         "key_fields": rows})

    # ---- (b) _TableNo 是否等于 act/combo 文件自身编号 ----
    tableno_match = 0
    actcombo_with_table = 0
    actcombo_with_action = 0
    actionno_values = []
    for f, d in table_action.items():
        m = re.search(r"_(?:act|combo)_(\d+)\.user\.2$", f)
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

    # ---- (b) filelist 里 motlist/message/mot/招式名文本证据 ----
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

    # ---- 覆盖率 ----
    missing = sorted(targets - extracted)
    extra = sorted(extracted - targets)

    facts = {
        "generated_by": "tools/bulk_parse_and_facts.py",
        "source": "refs/_bulk_extract",
        "caveats": [
            "对象引用类字段是 4 字节原始值，_ActionTableInfo/_ConditionList 等会失步（另一 agent 处理）；标量才可信",
            "数值数组判定为严格 int/float 元素，bool / ref 字符串 / {u32,f32} 字典均未计入",
            "em131 仅作只读对照，不并入 52 怪统计",
        ],
        "coverage": {
            "target_files": len(targets),
            "extracted_files": len(extracted),
            "missing_vs_targets": missing,
            "extra_vs_targets": extra,
            "monster_count": len(by_monster),
            "by_class": dict(by_class),
            "by_monster": {k: dict(v) for k, v in sorted(by_monster.items())},
        },
        "parse": {
            "files_total": len(files),
            "parsed_ok": len(files) - len(parse_failures),
            "parse_failures": parse_failures,
            "partial_files": partial_files,
            "instance_total": instance_total,
            "class_found_total": class_found_total,
            "class_found_ratio": round(class_found_total / instance_total, 4) if instance_total else None,
        },
        "questions": {
            "a": {
                "question": "全怪 range_data 里是否存在 5 元素递增数值阈值数组",
                "numeric_array_len_distribution_all_files": {str(k): v for k, v in sorted(arr_len_global.items())},
                "numeric_array_len_by_field": {"%s|len=%d" % (k, n): c
                                              for (k, n), c in sorted(arr_len_by_field.items())},
                "range_data_files_count": len(range_per_file),
                "range_data_per_file": range_per_file,
                "len5_monotonic_numeric_arrays": arr_len5_mono,
                "len5_monotonic_count": len(arr_len5_mono),
            },
            "b": {
                "question": "_TableNo -> _actionNo -> 招式名 中间映射能否建立",
                "act_combo_files_with_TableNo": actcombo_with_table,
                "act_combo_files_with_ActionNo": actcombo_with_action,
                "TableNo_equals_own_file_no_count": tableno_match,
                "ActionNo_value_min": min(actionno_values) if actionno_values else None,
                "ActionNo_value_max": max(actionno_values) if actionno_values else None,
                "ActionNo_distinct_sample": sorted(set(int(x) for x in actionno_values))[:40],
                "name_like_string_fields": dict(name_like_fields),
                "filelist_evidence": {
                    "filelist_lines": len(lines),
                    "motlist_all": motlist_all,
                    "message_all": message_all,
                    "enemy_motlist": enemy_motlist,
                    "enemy_msg_files": enemy_msg,
                    "enemy_action_name_text_candidates": enemy_name_text,
                    "plan_enemy_name_text_candidates": plan.get("enemy_name_text_candidates"),
                },
                "sample_TableNo_ActionNo": [
                    {"file": f, "TableNo": d["TableNo"], "ActionNo": d["ActionNo"],
                     "Category": d["Category"]}
                    for f, d in list(sorted(table_action.items()))[:8]],
            },
            "c": {
                "question": "_tiredSec/_motRate 是否跨怪恒为 0.0/1.0；全怪 tired/fatigue/rest 字段",
                "_tiredSec_values": {str(k): v for k, v in sorted(tiredsec_values.items())},
                "_motRate_values": {str(k): v for k, v in sorted(motrate_values.items())},
                "_tiredSec_by_file": tiredsec_by_file,
                "_motRate_by_file": motrate_by_file,
                "_tiredSec_is_always_0": set(tiredsec_values) == {0.0} and bool(tiredsec_values),
                "_motRate_is_always_1": set(motrate_values) == {1.0} and bool(motrate_values),
                "tired_fatigue_rest_field_hits": tired_hits,
                "tired_fatigue_rest_hit_count": len(tired_hits),
                "em131_readonly_reference": em131_ref,
            },
        },
        "per_file": per_file,
    }
    OUT_FACTS.write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
    print("parsed %d files -> %s" % (len(files), OUT_JSON))
    print("coverage: extracted=%d / targets=%d  missing=%d extra=%d monsters=%d" %
          (len(extracted), len(targets), len(missing), len(extra), len(by_monster)))
    print("parse failures=%d partial=%d class_found=%d/%d" %
          (len(parse_failures), len(partial_files), class_found_total, instance_total))
    print("Q(a) len5 monotonic numeric arrays =", len(arr_len5_mono),
          " numeric len dist =", dict(sorted(arr_len_global.items())))
    print("Q(b) TableNo==fileNo %d/%d  ActionNo files=%d  enemy name-text=%d" %
          (tableno_match, actcombo_with_table, actcombo_with_action, enemy_name_text))
    print("Q(c) _tiredSec=%s _motRate=%s tired-hits=%d" %
          (dict(tiredsec_values), dict(motrate_values), len(tired_hits)))
    print("wrote", OUT_FACTS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
