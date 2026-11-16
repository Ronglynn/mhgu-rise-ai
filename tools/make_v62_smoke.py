# -*- coding: utf-8 -*-
"""从 v61 冒烟日志变换出 v62（W2+W3+W4 一次性探针）冒烟日志。"""
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent / "out"
SRC, OUT = ROOT / "sim_v61_smoke.txt", ROOT / "sim_v62_smoke.txt"
P = "[forge] [INFO] "
lines = SRC.read_text(encoding="utf-8").splitlines()
out = []
for idx, l in enumerate(lines):
    if idx == 0:
        out.append(P + "[rai] ===== RAI v62 ONE-RUN W2+W3+W4 PROBES (AE action-class edges / QX hub kind) =====")
    elif idx == 1:
        out.append(P + "[rai] Rule: AE +0x73E0 edges + QX kind/state bits / ZT runtime table / W1 + Z/ZP/ZS UNCHANGED / 6 hooks / ZERO writes / ROLLBACK v61.nro")
    else:
        out.append(l)
    if "[rai] BEAT " in l:
        f = l.split("f=", 1)[1].split(" ", 1)[0]
        ff = int(f) if f.isdigit() else 6000
        out.append(P + ("[rai] AE f=%d mon=0C1044F0 old=00000006 new=00000002 gap=43 sel=31 a=29 "
                        "st=1 e1=7 t505=0 log=9100") % ff)
        out.append(P + ("[rai] QX f=%d mon=0C1044F0 r1=0 r2=1 r3=2 p5=0 w0=00000002 w1=00000002 "
                        "kind=1 e1=7 dc=1 t505=0 t518=1 t5e08=0 a1a8=00000040 a2c0=00000000 log=9101") % ff)
        out.append(P + ("[rai] QX f=%d mon=0C1044F0 r1=2 r2=7 r3=0 p5=0 w0=00000002 w1=00000702 "
                        "kind=255 e1=7 dc=1 t505=0 t518=1 t5e08=0 a1a8=00000040 a2c0=00000000 log=9102") % (ff+1))
OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print("wrote", OUT.name, len(out), "lines")
