# -*- coding: utf-8 -*-
"""从 v66 冒烟日志变换出 v67（B2 修复 + AR 换区探针）冒烟日志。"""
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent / "out"
SRC, OUT = ROOT / "sim_v66_smoke.txt", ROOT / "sim_v67_smoke.txt"
P = "[forge] [INFO] "
B0 = P + "[rai] ===== RAI v67 B2 SAMPLE FIX + AR AREA-MOVE READONLY PROBE ====="
R0 = P + "[rai] Rule: AR reads area(+0x1054) / req(+0x73f3) / f0,f4,fc / B2 by band-update counter / W1-W4 unchanged / 6 hooks / ZERO writes / ROLLBACK v66.nro"
lines = SRC.read_text(encoding="utf-8").splitlines()
out = []
for idx, l in enumerate(lines):
    if idx == 0:
        out += [B0, R0, l]
    else:
        out.append(l)
# AR 换区状态：疲惫窗内出现请求位与区域号变化
for k in range(12):
    f = 9000 + 300 * k
    area = 3 if k < 6 else 7
    req = 1 if k in (5, 6) else 0
    f0 = 1 if k == 6 else 0
    f4 = 1 if k == 5 else 0
    t505 = 2 if 3 <= k <= 8 else 0
    out.append(P + ("[rai] AR f=%d mon=0C1A0060 sp=0050 area=%d req=%d f0=%d f4=%d "
                    "fc=%d t505=%d t518=0 a=2 s=16 log=%d") %
               (f, area, req, f0, f4, 1800 - 100 * k, t505, 9900 + k))
OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print("wrote", OUT.name, len(out), "lines")
