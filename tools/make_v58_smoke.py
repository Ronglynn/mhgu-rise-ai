# -*- coding: utf-8 -*-
"""从 v57 合成冒烟日志变换出 v58（W1 全抽选 + W2 距离档只读探针）冒烟日志。

只用于离线判读回归，不代表实机数据（实机 value 走 VFP，val 多为 0；
阈值序列与几何原始位由实机决定，此处按 emc.md §4/§5 造合法形状）。
"""
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "out"
SRC = ROOT / "sim_v57_smoke.txt"
OUT = ROOT / "sim_v58_smoke.txt"
P = "[forge] [INFO] "

# (op, md, 阈值序列) —— 对应 emc.md 距离/几何 mode
BANDS = [
    ("17", 6, (8, 10, 15, 0)),     # 3D 距离，case*100 => 800/1000/1500
    ("0B", 4, (0, 1, 2, 3)),       # target point，float 表索引
    ("57", 14, (1, 2, 3, 0)),      # 另一目标槽，float 表索引
    ("5C", 16, (8, 12, 20, 0)),    # XZ 距离，case*100
    ("6A", 26, (3, 0, 0, 0)),      # 实机已见的其它几何 mode
    ("17", 7, (5, 9, 14, 0)),
]


def f32hex(v):
    return "%08X" % struct.unpack("<I", struct.pack("<f", v))[0]


def main():
    lines = SRC.read_text(encoding="utf-8").splitlines()
    out = [
        P + "[rai] ===== RAI v58 W1-ALL-PICKS + W2 DISTANCE-BAND READONLY PROBE =====",
        P + "[rai] Rule: W2 Z line (op/md/val/ip/blk/thresholds/hit/ret/st3) + ZP line (sub geometry raw bits) / ZERO writes / NO new hook / W2_PROBE=1 / ROLLBACK v57.nro",
    ]
    z_n = 0
    beats = 0
    for l in lines:
        out.append(l)
        # 在 BEAT 行之后插入一段 Z/ZP 采样，模拟一场任务的距离分支调用
        if "[rai] BEAT " not in l:
            continue
        fm = re.search(r"f=(\d+)", l)
        f = int(fm.group(1)) if fm else 300
        for i in range(6):
            op, md, thr = BANDS[(beats + i) % len(BANDS)]
            z_n += 1
            ff = f - 290 + i * 7
            ip = 0x1A77E300 + (z_n * 17) % 0x400
            blk = ip - 6
            hit = z_n % 3
            st3 = 2 if z_n % 11 == 0 else (1 if z_n % 4 == 0 else 0)
            val = 0 if z_n % 5 else 0x44FA0000
            out.append(
                P + ("[rai] Z f=%d op=%s md=%d val=%08X ip=%08X blk=%08X "
                     "nc=%d t0=%d t1=%d t2=%d t3=%d hit=%d ret=%d st3=%d log=%d")
                % (ff, op, md, val, ip, blk, 3, thr[0], thr[1], thr[2],
                   thr[3], hit, 3 + hit * 5, st3, 4000 + z_n))
            if z_n % 4 == 0:
                d = 300.0 + (z_n % 9) * 250.0
                out.append(
                    P + ("[rai] ZP f=%d mon=0C1044F0 sub=0C220B70 "
                         "a30=%s a34=%s a38=%s a40=%s a44=%s a48=%s "
                         "e0=%s e2=%s e4=%s hd=%04X cmd=0C104800 ent=%08X log=%d")
                    % (ff, f32hex(d), f32hex(0.0), f32hex(d * 0.5),
                       f32hex(0.0), f32hex(0.0), f32hex(0.0),
                       f32hex(d), f32hex(d * 0.8), f32hex(d * 0.6),
                       (z_n * 977) & 0xFFFF, 0x1A77D000, 5000 + z_n))
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print("wrote", OUT.name, len(out), "lines, Z=%d" % z_n)


if __name__ == "__main__":
    main()
