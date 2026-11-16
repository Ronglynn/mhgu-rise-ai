# -*- coding: utf-8 -*-
"""从 v69 冒烟日志变换出 v70（P70 修复：HB 行 / W3 关闭 / TTL 1200）冒烟日志。"""
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent / "out"
SRC, OUT = ROOT / "sim_v69_smoke.txt", ROOT / "sim_v70_smoke.txt"
P = "[forge] [INFO] "
B0 = P + "[rai] ===== RAI v70 P70 FIX: HB line (S truncation) / W3 gate OFF / HUB_TTL 1200 ====="
R0 = P + "[rai] Rule: HB line carries h0..h3/hd + stance timestamps / W3 gate disabled (GU has no IN_ACTION window) / W1-W2-W4 + AR + B2 + COMBO kept / 6 hooks / ZERO writes / ROLLBACK v69.nro"
lines = SRC.read_text(encoding="utf-8").splitlines()
out = []
for idx, l in enumerate(lines):
    if idx == 0:
        out += [B0, R0, l]
    elif "[rai] S " in l:
        out.append(l.replace(" h0=120 h1=18 h2=9 h3=6 hd=6", "").replace(" gs=8 ", " gs=0 "))
    else:
        out.append(l)
for k in range(12):
    f = 6000 + 600 * k
    out.append(P + ("[rai] HB f=%d h0=%d h1=%d h2=%d h3=%d hd=%d zf=%d af=%d ff=%d "
                    "sk=%d ge=30 gs=0 log=%d") %
               (f, 20 + 10 * k, 2 * k, k, 1 if k >= 6 else 0, 1 if k >= 6 else 0,
                22385 if k >= 6 else 0, 0, 21000 + 200 * k, k % 3, 9700 + k))
OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print("wrote", OUT.name, len(out), "lines")
