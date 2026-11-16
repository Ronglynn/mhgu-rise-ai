#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P96 · dttune 30-f32 倍率数组批量侦察（纯离线只读）。

目的：回答「疲惫态动作速度能否用纯静态数据层降速」的两个前置问题
  1. 数组后 16 项（idx14..29）是否在全部怪上恒为 1.0 —— 若是，则不存在"疲惫专属倍率槽"。
  2. idx3..12（wiki 标 [U] 未绑定）在各怪上的取值分布 —— 若有怪带 <1.0 值，说明该区确实
     存在"非怒状态倍率"用途，疲惫槽可能藏在这里。

定位规则（不依赖固定偏移，逐怪浮动）：
  在 0x100..0x340 逐字节试起点，取满足下列条件的窗口
    - 30 个 f32 全部落在 [0.3, 5.2]
    - 恰好 1.0 的项数 >= 14
    - idx0/idx1 均 > 0.9（怒时倍率恒 >= 1.0 的已知性质）
  多个候选时取 ones 最多、偏移最小者。

用法：
  python tools/probe_dttune_speed_array.py [原版 arc 目录] [--json 输出]
"""

import glob
import json
import os
import struct
import sys
import zlib

DEF_DIR = r"D:\MHGU mod maker\01_Original_romfs\romfs\nativeNX\arc\enemy"
LO, HI = 0.3, 5.2
ONE_TOL = 1e-5


def read_entries(data):
    _ver, cnt = struct.unpack("<HH", data[4:8])
    for i in range(cnt):
        off = 0x0C + i * 0x50
        name = data[off:off + 0x40].split(b"\x00")[0].decode("latin1")
        h, csize, usize_flag, ds = struct.unpack("<IIII", data[off + 0x40:off + 0x50])
        yield name, csize, usize_flag, ds


def load_dttune(arc_path):
    data = open(arc_path, "rb").read()
    for name, csize, usize_flag, ds in read_entries(data):
        if "dttune" not in name:
            continue
        raw = data[ds:ds + csize]
        ulen = usize_flag & 0x0FFFFFFF
        if (usize_flag >> 28) == 4:
            body = zlib.decompressobj().decompress(raw)[:ulen]
        else:
            body = raw[:ulen]
        return name, body
    return None, None


def locate(body):
    best = None
    for off in range(0x100, 0x340):
        if off + 120 > len(body):
            break
        f = struct.unpack_from("<30f", body, off)
        if not all(LO <= x <= HI for x in f):
            continue
        if f[0] <= 0.9 or f[1] <= 0.9:
            continue
        ones = sum(1 for x in f if abs(x - 1.0) < ONE_TOL)
        if ones < 14:
            continue
        key = (-ones, off)
        if best is None or key < best[0]:
            best = (key, off, f)
    if best is None:
        return None, None
    return best[1], best[2]


def main():
    arc_dir = DEF_DIR
    json_out = None
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--json" and i + 1 < len(args):
            json_out = args[i + 1]
        elif not a.startswith("--"):
            arc_dir = a

    files = sorted(glob.glob(os.path.join(arc_dir, "em*_00.arc")))
    rows = []
    for p in files:
        emid = os.path.basename(p).split("_")[0]
        name, body = load_dttune(p)
        if body is None:
            continue
        off, f = locate(body)
        if off is None:
            rows.append(dict(emid=emid, off=None, arr=None))
            continue
        rows.append(dict(emid=emid, off=off, arr=[round(x, 6) for x in f]))

    ok = [r for r in rows if r["arr"]]
    print("扫描 arc=%d  定位成功=%d  失败=%d" % (len(files), len(ok), len(files) - len(ok)))

    # ---- 1. 后 16 项是否恒 1.0 ----
    tail_all_one = [r for r in ok if all(abs(x - 1.0) < ONE_TOL for x in r["arr"][14:])]
    print("\n=== idx14..29 恒为 1.0 的怪：%d/%d ===" % (len(tail_all_one), len(ok)))
    bad = [r for r in ok if r not in tail_all_one]
    for r in bad[:12]:
        print("  %s  tail=%s" % (r["emid"], r["arr"][14:]))

    # ---- 2. 每列取值分布 ----
    print("\n=== 各列非 1.0 的怪数量 / 取值范围 ===")
    print("%-5s %6s %10s %10s  %s" % ("idx", "非1.0", "min", "max", "说明"))
    note = {0: "AttackRate 或 SpeedMult（分歧）", 1: "MotionSpeedRate 或 AttackMult（分歧）",
            2: "MotionSpeedRateLimit 或 DefenseMult（分歧）"}
    for idx in range(30):
        vals = [r["arr"][idx] for r in ok]
        nz = [v for v in vals if abs(v - 1.0) >= ONE_TOL]
        tag = note.get(idx, "")
        if idx >= 3 and idx <= 12:
            tag = "[U] 未绑定区"
        print("%-5d %6d %10.4f %10.4f  %s"
              % (idx, len(nz), min(vals), max(vals), tag))

    # ---- 3. idx3..12 是否有 <1.0 ----
    print("\n=== idx3..12 出现 <1.0 的怪（疲惫槽候选线索）===")
    cnt = 0
    for r in ok:
        hit = [(i, r["arr"][i]) for i in range(3, 13) if r["arr"][i] < 1.0 - ONE_TOL]
        if hit:
            cnt += 1
            if cnt <= 15:
                print("  %s  %s" % (r["emid"], hit))
    print("  合计 %d/%d 只怪在 idx3..12 带 <1.0 值" % (cnt, len(ok)))

    if json_out:
        with open(json_out, "w", encoding="utf-8") as fh:
            json.dump(dict(scanned=len(files), located=len(ok), rows=rows), fh, ensure_ascii=False, indent=1)
        print("\nJSON -> %s" % json_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
