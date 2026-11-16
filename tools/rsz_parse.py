"""离线解析 RE Engine USER/.user.2（RSZ 容器），类型描述来自 RE_RSZ 的 rszmhrise.json。

用法：python rsz_parse.py <file.user.2> [更多文件...] [--json-out DIR]

不依赖 010 Editor、不依赖实机游戏。输出每个实例的类名与字段值（结构化 JSON）。
布局依据 RE_RSZ.bt 的 RSZHEADER / InstanceInfo 定义：
    magic, version, objectCount, instanceCount, userdataCount, reserved (4B x6)
    instanceOffset, dataOffset, userdataOffset (8B x3)   = 48B
    instanceInfo[instanceCount] : {u32 typeId, u32 crc}  (从 RSZHeader+instanceOffset)
    instance data                : 从 RSZHeader+dataOffset 起，按 fields 顺序内联
"""
import json
import pathlib
import struct
import sys

TYPES_PATH = pathlib.Path(__file__).resolve().parent.parent / "refs" / "rszmhrise.json"
_TYPES = None


def types():
    global _TYPES
    if _TYPES is None:
        _TYPES = json.load(open(TYPES_PATH, encoding="utf-8"))
    return _TYPES


def u32(d, o):
    return struct.unpack_from("<I", d, o)[0]


def i32(d, o):
    return struct.unpack_from("<i", d, o)[0]


def align_up(v, a):
    a = a or 1
    return (v + a - 1) // a * a


def scalar(d, o, f):
    """按字段类型解释标量；size 以 JSON 为准。"""
    t = f.get("type", "")
    size = f.get("size", 4)
    raw = d[o:o + size]
    if len(raw) < size:
        return None
    try:
        if t in ("F32", "F64"):
            return round(struct.unpack("<f" if size == 4 else "<d", raw)[0], 6)
        if t in ("S32", "S16", "S8", "S64"):
            return int.from_bytes(raw, "little", signed=True)
        if t in ("U32", "U16", "U8", "U64", "Enum"):
            return int.from_bytes(raw, "little")
        if t == "Bool":
            return bool(raw[0])
        if t in ("Object", "String", "Resource", "UserData", "Action", "RuntimeType"):
            v = int.from_bytes(raw[:4], "little")
            return "ref:0x%08X" % v
        if size == 4:
            v = struct.unpack("<I", raw)[0]
            fv = struct.unpack("<f", raw)[0]
            return {"u32": v, "f32": round(fv, 6)}
        return int.from_bytes(raw, "little")
    except (struct.error, ValueError):
        return None


def parse(path):
    d = pathlib.Path(path).read_bytes()
    if d[:4] != b"USR\x00":
        raise ValueError("not a USER file")
    # 定位内嵌 RSZ 段
    pos = d.find(b"RSZ\x00")
    if pos < 0:
        raise ValueError("RSZ segment not found")
    (magic, version, object_count, instance_count,
     userdata_count, reserved) = struct.unpack_from("<6I", d, pos)
    instance_offset, data_offset, userdata_offset = struct.unpack_from("<3q", d, pos + 24)
    info = pos + instance_offset
    data = pos + data_offset
    root_tid = u32(d, 48)  # USER header 里的根类型 id

    T = types()
    inst = []
    for i in range(instance_count):
        tid = u32(d, info + i * 8)
        crc = u32(d, info + i * 8 + 4)
        key = "%08x" % tid
        cls = T.get(key)
        inst.append({
            "index": i,
            "typeId": key,
            "crc": "0x%08X" % crc,
            "class": cls["name"] if cls else None,
            # JSON 里的 crc 是类型名散列，实例里的 CRC 是实例级校验值，二者不等价；
            # 这里只用「类型能否在 rszmhrise.json 中解析」作为可信度指标。
            "class_found": cls is not None,
            "fields": cls["fields"] if cls else [],
        })

    # 依据 RE_RSZ.bt:2505 / 1360-1372 / 5635：
    #   - 对齐基于「绝对文件偏移」getAlignedOffset(FTell(), align)
    #   - 数组字段的对齐固定为 4；非数组字段用 JSON 的 align
    #   - Count 之后的每个数组元素前，还要再按字段 align 对齐一次
    off = data
    trusted = 0
    partial = False
    for it in inst:
        vals = {}
        if it["class"] is None:
            it["values"] = None
            continue
        flds = it["fields"]
        if flds:
            a0 = 4 if flds[0].get("array") else (flds[0].get("align") or 1)
            off = align_up(off, a0)
        for f in flds:
            is_arr = bool(f.get("array"))
            a = 4 if is_arr else (f.get("align", 4) or 1)
            elem_align = f.get("align", 4) or 1
            size = f.get("size", 4)
            name = f.get("name", "?")
            off = align_up(off, a)
            if is_arr:
                cnt = u32(d, off) if off + 4 <= len(d) else 0
                off += 4
                if cnt > 4096:  # 解析失步保护：停止本文件后续解析，避免产出错误数值
                    vals[name] = "<bad count %d>" % cnt
                    partial = True
                    break
                elems = []
                for _ in range(cnt):
                    off = align_up(off, elem_align)
                    elems.append(scalar(d, off, f))
                    off += size
                vals[name] = elems
            else:
                vals[name] = scalar(d, off, f)
                off += size
        it["values"] = vals
        trusted += 1
        if partial:
            break

    return {
        "file": str(path),
        "root": T.get("%08x" % root_tid, {}).get("name"),
        "version": version,
        "objectCount": object_count,
        "instanceCount": instance_count,
        "trustedInstances": trusted,
        "partial": partial,
        "rszOffset": pos,
        "dataOffset": data,
        "bytesConsumed": off - data,
        "fileSize": len(d),
        "instances": inst,
    }


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = None
    if "--json-out" in sys.argv:
        out = pathlib.Path(sys.argv[sys.argv.index("--json-out") + 1])
        out.mkdir(parents=True, exist_ok=True)
    for p in args:
        r = parse(p)
        ok = sum(1 for i in r["instances"] if i["class_found"])
        print("%s | root=%s inst=%d class_ok=%d consumed=%d/%d" % (
            pathlib.Path(p).name, r["root"], r["instanceCount"], ok,
            r["bytesConsumed"], r["fileSize"]))
        for it in r["instances"][:6]:
            if it["class"]:
                nums = {k: v for k, v in (it["values"] or {}).items()
                        if not isinstance(v, list) and isinstance(v, (int, float, bool))}
                print("   %-2d %-58s %s" % (it["index"], it["class"][:58], str(nums)[:150]))
        if out:
            (out / (pathlib.Path(p).name + ".json")).write_text(
                json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
