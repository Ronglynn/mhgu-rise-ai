# -*- coding: utf-8 -*-
"""从 v60 冒烟日志变换出 v61（运行时 dttune 阈值链探针）冒烟日志。"""
import struct
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent / "out"
SRC, OUT = ROOT / "sim_v60_smoke.txt", ROOT / "sim_v61_smoke.txt"
P = "[forge] [INFO] "
def hx(v):
    return "%08X" % struct.unpack("<I", struct.pack("<f", v))[0]
lines = SRC.read_text(encoding="utf-8").splitlines()
out = []
for idx, l in enumerate(lines):
    if idx == 0:
        out.append(P + "[rai] ===== RAI v61 W2 HIGH-FIDELITY: RUNTIME DTTUNE THRESHOLD CHAIN PROBE =====")
    elif idx == 1:
        out.append(P + "[rai] Rule: ZT line reads a0+0x75ec / +0x7c / +0xfa / 16*slot f32 / W1 + Z/ZP/ZS UNCHANGED / ZERO writes / NO new hook / ROLLBACK v60.nro")
    else:
        out.append(l)
    if "[rai] ZP " in l:
        f = l.split("f=", 1)[1].split(" ", 1)[0]
        rows = [(600.0, 1100.0, 2500.0, 5000.0), (800.0, 1400.0, 3000.0, 5000.0)]
        for slot, r in enumerate(rows):
            out.append(P + ("[rai] ZT f=%s mon=0C1044F0 md=4 ip=1BF92A37 blk=1BF92A36 ba=0 "
                            "tune=0C220000 cnt=2 base=0C230000 slot=%d t0=%s t1=%s t2=%s t3=%s log=9000") %
                       (f, slot, *[hx(x) for x in r]))
OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print("wrote", OUT.name, len(out), "lines")
