# -*- coding: utf-8 -*-
"""从 v68 冒烟日志变换出 v69（W4 12 处境分流）冒烟日志。"""
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent / "out"
SRC, OUT = ROOT / "sim_v68_smoke.txt", ROOT / "sim_v69_smoke.txt"
P = "[forge] [INFO] "
B0 = P + "[rai] ===== RAI v69 W4 MECHANISM-LEVEL 12-HUB ROUTING (3 states x 4 stances) ====="
R0 = P + "[rai] Rule: HUB_SHAPE[state*4+hub] / hub3 defer to v38 weights / hub0 identical to v68 / W3 gate + AR + B2 + COMBO kept / 6 hooks / ZERO writes / ROLLBACK v68.nro"
lines = SRC.read_text(encoding="utf-8").splitlines()
out = []
for idx, l in enumerate(lines):
    if idx == 0:
        out += [B0, R0, l]
    elif "[rai] S " in l:
        out.append(l + " h0=120 h1=18 h2=9 h3=6 hd=6")
    else:
        out.append(l)
OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print("wrote", OUT.name, len(out), "lines")
