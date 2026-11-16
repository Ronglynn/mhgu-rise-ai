# -*- coding: utf-8 -*-
"""从 v67 冒烟日志变换出 v68（W3 _IsActionEnd 重抽门控）冒烟日志。"""
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent / "out"
SRC, OUT = ROOT / "sim_v67_smoke.txt", ROOT / "sim_v68_smoke.txt"
P = "[forge] [INFO] "
B0 = P + "[rai] ===== RAI v68 W3 IsActionEnd REDRAW GATE + v67 AREA PROBE ====="
R0 = P + "[rai] Rule: gate on veto-redraw only (IN_ACTION => v38 original weights) / W1_ALL unchanged / auto-fuse + W3_GATE_ENABLE=0 fallback / AR+B2+COMBO kept / 6 hooks / ZERO writes / ROLLBACK v67.nro"
lines = SRC.read_text(encoding="utf-8").splitlines()
out = []
for idx, l in enumerate(lines):
    if idx == 0:
        out += [B0, R0, l]
    elif "[rai] S " in l:
        out.append(l + " ge=30 gs=8 ek=330")
    else:
        out.append(l)
OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print("wrote", OUT.name, len(out), "lines")
