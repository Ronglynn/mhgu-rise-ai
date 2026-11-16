# -*- coding: utf-8 -*-
"""从 v59 冒烟日志变换出 v60（W1 高保真对齐）冒烟日志，离线判读回归用。"""
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent / "out"
SRC = ROOT / "sim_v59_smoke.txt"
OUT = ROOT / "sim_v60_smoke.txt"
P = "[forge] [INFO] "
lines = SRC.read_text(encoding="utf-8").splitlines()
out = []
for idx, l in enumerate(lines):
    if idx == 0:
        out.append(P + "[rai] ===== RAI v60 W1 RISE-15-POOL FIDELITY (3-state shapes / n>=3 / k-truncation) =====")
    elif idx == 1:
        out.append(P + "[rai] Rule: W1 shapes from Rise 15 pools (A3/A4/N3/N4/T3) / state-specific k3:k4 mix / n>=3 gate / W2 + hooks + log format UNCHANGED / ZERO writes / ROLLBACK v59.nro")
    else:
        out.append(l)
OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print("wrote", OUT.name, len(out), "lines")
