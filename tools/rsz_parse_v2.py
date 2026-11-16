"""离线解析 RE Engine USER/.user.2（RSZ 容器）—— v2：修复对象引用失步。

相对 v1 (tools/rsz_parse.py) 的改进，见 out/P80_object_ref_resolution.md：

1. **识别 userdata 实例**. RSZ header 第 3 个 uint64 (userdataOffset) 指向
   userdata info 表，条目 {u32 instanceId, u32 typeId, u32 pathOffset, u32 zero}（16B）。
   userdataCount 个实例的数据存放在 **外部分件**（pathOffset 指向的 UTF-16 路径），
   在主 data 流里 **占 0 字节**。v1 把它们也按 fields 内联解析（典型吃掉 8B），
   导致其后所有实例整体错位 —— 这就是 `ThinkState._ActionList` 出现
   `ref:0x4BCCF5F2` 垃圾值、bytesConsumed 与文件长对不上的根因。

2. **Object/UserData 引用按 instance index 解析**（0 = null，1..instanceCount-1），
   输出 {ref, targetClass, valid}，并校验落在 [0, instanceCount]。

3. **判据驱动的对齐搜索**：默认策略 (skip=0, alignUserdata=False) 若不能同时满足
   「全部引用合法 / 数组 count 合理 / 类定义齐全」，则在候选策略空间
   (skip ∈ {0,1,2,4,8,16} × align ∈ {False,True}) 内搜索，记录每个候选的评分与选择理由。

4. 只读 + 新增文件；不修改 tools/rsz_parse.py、不改动 out/rsz_main_json/ 既有 JSON。

用法：
    python rsz_parse_v2.py <file.user.2> [更多...] --json-out DIR [--summary FILE.json]
    python rsz_parse_v2.py --all --json-out DIR [--summary FILE.json]
"""
import json
import pathlib
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TYPES_PATH = ROOT / "refs" / "rszmhrise.json"
EXTRACT_DIR = ROOT / "refs" / "_main_extract"

_T = None


def types():
    global _T
    if _T is None:
        with open(TYPES_PATH, encoding="utf-8") as fh:
            _T = json.load(fh)
    return _T


# 这些类型在 RSZ 里存的是 instance index（4B），不是内存地址/句柄。
REF_TYPES = {"Object", "String", "Resource", "UserData", "Action", "RuntimeType"}
# 统计用：需要列出「指向哪个实例 + 目标关键字段」的关键表字段。
KEY_FIELDS = ("_ActionList", "_ConditionList", "_TransitionActTbl", "_StateList",
              "_ActionTableInfo", "_CheckPrevTableInfoList", "_ReferenceThinkData")
# 目标实例的关键标量字段（用于报告因果链）。
KEY_SCALARS = ("_TableNo", "_Category", "_Regist", "_NextStateID", "_IsActionEnd",
               "_IsUnderLayerEnd", "_TransitionRate", "_CheckType", "_ID", "set_type")


def u32(d, o):
    return struct.unpack_from("<I", d, o)[0] if o + 4 <= len(d) else None


def align_up(v, a):
    a = a or 1
    return (v + a - 1) // a * a


def read_wstr(d, off):
    """从 off 读 UTF-16LE 字符串，遇 0x0000 结束。"""
    if off is None or off < 0 or off + 2 > len(d):
        return None
    out = []
    p = off
    while p + 2 <= len(d):
        c = struct.unpack_from("<H", d, p)[0]
        if c == 0:
            break
        out.append(chr(c))
        p += 2
    return "".join(out)


def scalar_value(d, off, f):
    """按字段类型解释标量。返回 (value, is_ref)。size 以 rszmhrise.json 为准。"""
    t = f.get("type", "")
    size = f.get("size", 4)
    raw = d[off:off + size]
    if len(raw) < size:
        return None, False
    try:
        if t in ("F32", "F64"):
            return round(struct.unpack("<f" if size == 4 else "<d", raw)[0], 6), False
        if t in ("S32", "S16", "S8", "S64"):
            return int.from_bytes(raw, "little", signed=True), False
        if t in ("U32", "U16", "U8", "U64", "Enum"):
            return int.from_bytes(raw, "little"), False
        if t == "Bool":
            return bool(raw[0]), False
        if t in REF_TYPES:
            return int.from_bytes(raw[:4], "little"), True
        if t == "Guid":
            return "0x" + raw.hex(), False
        if size == 4:
            v = struct.unpack("<I", raw)[0]
            fv = struct.unpack("<f", raw)[0]
            return {"u32": v, "f32": round(fv, 6)}, False
        return "0x" + raw.hex(), False
    except (struct.error, ValueError):
        return None, False


def read_header(d):
    """返回 USER + RSZ header 的绝对偏移与字段。"""
    if d[:4] != b"USR\x00":
        raise ValueError("not a USER file (missing USR\\0)")
    # USER header @32 = 指向 RSZ 段的绝对偏移；用 find 作回退/交叉校验。
    user_data_offset = struct.unpack_from("<q", d, 32)[0]
    pos = d.find(b"RSZ\x00")
    if user_data_offset != pos:
        pos = user_data_offset if 0 < user_data_offset < len(d) and d[user_data_offset:user_data_offset + 4] == b"RSZ\x00" else pos
    if pos < 0 or d[pos:pos + 4] != b"RSZ\x00":
        raise ValueError("RSZ segment not found")
    magic, version, object_count, instance_count, userdata_count, reserved = struct.unpack_from("<6I", d, pos)
    instance_offset, data_offset, userdata_offset = struct.unpack_from("<3q", d, pos + 24)
    root_tid = u32(d, 48)
    return {
        "pos": pos, "version": version, "objectCount": object_count,
        "instanceCount": instance_count, "userdataCount": userdata_count,
        "instanceOffset": instance_offset, "dataOffset": data_offset,
        "userdataOffset": userdata_offset, "rootTid": root_tid,
        "infoAbs": pos + instance_offset, "dataAbs": pos + data_offset,
        "utblAbs": pos + userdata_offset,
        "userHeaderDataOffset": user_data_offset,
    }


def read_tables(d, h):
    """object table / instance info / userdata info。"""
    T = types()
    obj_table = [u32(d, h["pos"] + 48 + 4 * k) for k in range(h["objectCount"])]
    infos = []
    for i in range(h["instanceCount"]):
        tid = u32(d, h["infoAbs"] + 8 * i)
        crc = u32(d, h["infoAbs"] + 8 * i + 4)
        cls = T.get("%08x" % tid)
        infos.append({
            "index": i, "typeId": "%08x" % tid, "crc": "0x%08X" % (crc or 0),
            "class": cls["name"] if cls else None,
            "classFound": cls is not None,
            "fields": cls["fields"] if cls else [],
        })
    ud = []
    for j in range(h["userdataCount"]):
        base = h["utblAbs"] + 16 * j
        iid = u32(d, base)
        tid = u32(d, base + 4)
        poff = u32(d, base + 8)
        zero = u32(d, base + 12)
        # pathOffset 是相对 RSZ 段起点的偏移
        path = read_wstr(d, h["pos"] + poff) if poff is not None else None
        ud.append({"instanceId": iid, "typeId": "%08x" % (tid or 0),
                   "pathOffset": poff, "reserved": zero, "path": path})
    return obj_table, infos, ud


def resolve_ref(v, h, infos):
    if v is None:
        return {"ref": None, "targetClass": None, "valid": False, "reason": "out of file"}
    target = infos[v]["class"] if 0 <= v < len(infos) else None
    return {"ref": v, "targetClass": target, "valid": 0 <= v <= h["instanceCount"]}


def parse_data(d, h, infos, ud, skip_bytes, align_userdata):
    """按给定策略解析 data 流。返回 (instances_out, diagnostics)。"""
    udset = {u["instanceId"] for u in ud}
    udpath = {u["instanceId"]: u["path"] for u in ud}
    off = h["dataAbs"]
    invalid_refs = []
    implausible_counts = []
    ref_total = 0
    cnt_total = 0
    out = []

    for it in infos:
        rec = {
            "index": it["index"], "typeId": it["typeId"], "crc": it["crc"],
            "class": it["class"], "classFound": it["classFound"],
            "isNull": it["index"] == 0, "isUserdata": it["index"] in udset,
            "values": None,
        }
        if it["index"] in udset:
            rec["userdataPath"] = udpath.get(it["index"])
            if align_userdata:
                off = align_up(off, 4)
            off += skip_bytes
            out.append(rec)
            continue
        if not it["classFound"]:
            out.append(rec)
            continue

        flds = it["fields"]
        if flds:
            a0 = 4 if flds[0].get("array") else (flds[0].get("align") or 1)
            off = align_up(off, a0)
        vals = {}
        for f in flds:
            is_arr = bool(f.get("array"))
            a = 4 if is_arr else (f.get("align", 4) or 1)
            elem_align = f.get("align", 4) or 1
            size = f.get("size", 4)
            name = f.get("name", "?")
            off = align_up(off, a)
            if is_arr:
                cnt = u32(d, off)
                off += 4
                cnt_total += 1
                if cnt is None or cnt > 4096 or cnt * size > (len(d) - off):
                    implausible_counts.append({"index": it["index"], "field": name, "count": cnt})
                    vals[name] = "<bad count %s>" % cnt
                    break
                elems = []
                for _ in range(cnt):
                    off = align_up(off, elem_align)
                    v, is_ref = scalar_value(d, off, f)
                    if is_ref:
                        ref_total += 1
                        rv = resolve_ref(v, h, infos)
                        if not rv["valid"]:
                            invalid_refs.append({"index": it["index"], "field": name, "value": v})
                        elems.append(rv)
                    else:
                        elems.append(v)
                    off += size
                vals[name] = elems
            else:
                v, is_ref = scalar_value(d, off, f)
                if is_ref:
                    ref_total += 1
                    rv = resolve_ref(v, h, infos)
                    if not rv["valid"]:
                        invalid_refs.append({"index": it["index"], "field": name, "value": v})
                    vals[name] = rv
                else:
                    vals[name] = v
                off += size
        rec["values"] = vals
        out.append(rec)

    consumed = off - h["dataAbs"]
    data_region_len = len(d) - h["dataAbs"]
    fields_complete = all(x["classFound"] for x in infos if x["index"] != 0)
    diag = {
        "strategy": {"userdataSkipBytes": skip_bytes, "alignUserdata": align_userdata},
        "objectRefs": {"total": ref_total, "valid": ref_total - len(invalid_refs),
                       "invalid": invalid_refs},
        "arrayCounts": {"total": cnt_total, "plausible": cnt_total - len(implausible_counts),
                        "implausible": implausible_counts},
        "bytesConsumed": consumed,
        "dataRegionLen": data_region_len,
        "tail": len(d) - off,
        "fieldsComplete": fields_complete,
        "parseOK": (len(invalid_refs) == 0 and len(implausible_counts) == 0 and fields_complete),
    }
    return out, diag


def score(diag):
    """候选策略评分：先满足合法性，再让 tail 最小、skip 最小、不对齐优先。"""
    return (1 if diag["parseOK"] else 0,
            -abs(diag["tail"]),
            -len(diag["objectRefs"]["invalid"]),
            -len(diag["arrayCounts"]["implausible"]),
            -diag["strategy"]["userdataSkipBytes"],
            -int(diag["strategy"]["alignUserdata"]))


def parse(path):
    d = pathlib.Path(path).read_bytes()
    h = read_header(d)
    obj_table, infos, ud = read_tables(d, h)
    T = types()

    # 默认策略：userdata 实例占 0 字节、不做额外对齐。
    default = (0, False)
    instances, diag = parse_data(d, h, infos, ud, *default)

    search = {"triggered": False, "reason": "", "candidates": [], "chosen": None}
    if not diag["parseOK"]:
        search["triggered"] = True
        search["reason"] = ("默认策略 (skip=0, align=False) 未通过判据："
                            "invalid_refs=%d implausible_counts=%d fieldsComplete=%s tail=%d" % (
                                len(diag["objectRefs"]["invalid"]),
                                len(diag["arrayCounts"]["implausible"]),
                                diag["fieldsComplete"], diag["tail"]))
        best_instances, best_diag = instances, diag
        best_S, best_A = default
        cand = []
        for S in (0, 1, 2, 4, 8, 16):
            for A in (False, True):
                ins, dg = parse_data(d, h, infos, ud, S, A)
                cand.append({
                    "userdataSkipBytes": S, "alignUserdata": A,
                    "parseOK": dg["parseOK"], "tail": dg["tail"],
                    "invalidRefs": len(dg["objectRefs"]["invalid"]),
                    "implausibleCounts": len(dg["arrayCounts"]["implausible"]),
                    "score": list(score(dg)),
                })
                if score(dg) > score(best_diag):
                    best_instances, best_diag = ins, dg
                    best_S, best_A = S, A
        search["candidates"] = cand
        search["chosen"] = {"userdataSkipBytes": best_S, "alignUserdata": best_A}
        instances, diag = best_instances, best_diag
    diag["alignmentSearch"] = search

    root = T.get("%08x" % h["rootTid"], {}).get("name")
    return {
        "file": str(path),
        "parser": "rsz_parse_v2",
        "root": root,
        "version": h["version"],
        "objectCount": h["objectCount"],
        "instanceCount": h["instanceCount"],
        "userdataCount": h["userdataCount"],
        "rszOffset": h["pos"],
        "instanceInfoOffset": h["instanceOffset"],
        "dataOffset": h["dataOffset"],
        "userdataInfoOffset": h["userdataOffset"],
        "userHeaderDataOffset": h["userHeaderDataOffset"],
        "objectTable": obj_table,
        "userdataInfo": ud,
        "instances": instances,
        "diagnostics": diag,
    }


def key_tables(result):
    """汇总关键表字段指向的实例类名与目标实例关键标量。"""
    insts = result["instances"]
    by_idx = {i["index"]: i for i in insts}
    rows = []
    for it in insts:
        vals = it.get("values") or {}
        for fld in KEY_FIELDS:
            if fld not in vals:
                continue
            v = vals[fld]
            refs = v if isinstance(v, list) else [v]
            for r in refs:
                if not isinstance(r, dict) or "ref" not in r:
                    continue
                tgt = by_idx.get(r["ref"])
                scalars = {}
                if tgt and tgt.get("values"):
                    for k in KEY_SCALARS:
                        if k in tgt["values"] and not isinstance(tgt["values"][k], (list, dict)):
                            scalars[k] = tgt["values"][k]
                rows.append({
                    "file": pathlib.Path(result["file"]).name,
                    "fromIndex": it["index"], "fromClass": it["class"],
                    "field": fld,
                    "ref": r["ref"], "valid": r["valid"],
                    "targetClass": r["targetClass"],
                    "targetUserdata": (tgt or {}).get("isUserdata", False),
                    "targetPath": (tgt or {}).get("userdataPath"),
                    "targetKeyScalars": scalars,
                })
    return rows


def main():
    argv = sys.argv[1:]
    out = None
    summary = None
    files = []
    if "--json-out" in argv:
        out = pathlib.Path(argv[argv.index("--json-out") + 1])
        out.mkdir(parents=True, exist_ok=True)
    if "--summary" in argv:
        summary = pathlib.Path(argv[argv.index("--summary") + 1])
    if "--all" in argv:
        files = sorted(EXTRACT_DIR.rglob("*.user.2"))
    else:
        files = [pathlib.Path(a) for a in argv
                 if not a.startswith("--") and a not in _option_values(argv)]
    if not files:
        print(__doc__)
        return

    all_rows = []
    print("%-34s %4s %4s %6s %6s %5s %5s %5s %6s  %s" % (
        "file", "inst", "ud", "cons", "data", "refs", "badR", "cnt", "badC", "OK"))
    for p in files:
        r = parse(p)
        dg = r["diagnostics"]
        print("%-34s %4d %4d %6d %6d %5d %5d %5d %6d  %s" % (
            pathlib.Path(p).name, r["instanceCount"], r["userdataCount"],
            dg["bytesConsumed"], dg["dataRegionLen"],
            dg["objectRefs"]["total"], len(dg["objectRefs"]["invalid"]),
            dg["arrayCounts"]["total"], len(dg["arrayCounts"]["implausible"]),
            "YES" if dg["parseOK"] else "NO"))
        if out:
            (out / (pathlib.Path(p).name + ".json")).write_text(
                json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        all_rows.extend(key_tables(r))

    if summary:
        summary.parent.mkdir(parents=True, exist_ok=True)
        summary.write_text(json.dumps({
            "files": [pathlib.Path(p).name for p in files],
            "keyTables": all_rows,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        print("summary -> %s (%d key-table rows)" % (summary, len(all_rows)))


def _option_values(argv):
    vals = []
    for opt in ("--json-out", "--summary"):
        if opt in argv:
            i = argv.index(opt)
            if i + 1 < len(argv):
                vals.append(argv[i + 1])
    return vals


if __name__ == "__main__":
    main()
