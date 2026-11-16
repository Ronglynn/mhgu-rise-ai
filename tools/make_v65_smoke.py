# -*- coding: utf-8 -*-
"""从 v64 冒烟日志变换出 v65（W2 状态×档位加权）冒烟日志。"""
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent / "out"
SRC, OUT = ROOT / "sim_v64_smoke.txt", ROOT / "sim_v65_smoke.txt"
P = "[forge] [INFO] "
B0 = P + "[rai] ===== RAI v65 W2 HIGH-FIDELITY: (STATE x BAND) RISE 15-POOL WEIGHTING ====="
R0 = P + "[rai] Rule: BAND_SHAPE[st3*5+band] from Rise 15 pools / band_sense independent of W2_PROBE / fallback to v60 state shapes / 6 hooks / ZERO writes / ROLLBACK v64.nro"
lines = SRC.read_text(encoding="utf-8").splitlines()
out = []
for idx, l in enumerate(lines):
    if idx == 0:
        out += [B0, R0, l]
    elif "[rai] DG " in l or "[rai] ZD " in l:
        continue
    elif "[rai] S " in l:
        out.append(l + " wb=40 bf=10")
    else:
        out.append(l)
# B2 档位诊断，覆盖 0..4 五个档位
for k in range(10):
    out.append(P + ("[rai] B2 f=%d mon=0C130510 md=4 op=0B ts=%d bd=%d si=0 log=%d") %
               (3000 + 300 * k, k % 5, k % 5, 9700 + k))
OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print("wrote", OUT.name, len(out), "lines")
