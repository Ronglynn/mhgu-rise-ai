# -*- coding: utf-8 -*-
"""从 v65 冒烟日志变换出 v66（W3 COMBO + W4 三处境）冒烟日志。"""
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent / "out"
SRC, OUT = ROOT / "sim_v65_smoke.txt", ROOT / "sim_v66_smoke.txt"
P = "[forge] [INFO] "
B0 = P + "[rai] ===== RAI v66 W3 COMBO TRACE + W4 3-STANCE ROUTING (sp-tagged for cross-monster) ====="
R0 = P + "[rai] Rule: COMBO ev=1 action-start / ev=2 action-end (P36 S2) / stance from kind=2|t505 + t518 / W2 band unchanged / 6 hooks / ZERO writes / ROLLBACK v65.nro"
lines = SRC.read_text(encoding="utf-8").splitlines()
out = []
sk_i = 0
for idx, l in enumerate(lines):
    if idx == 0:
        out += [B0, R0, l]
    elif "[rai] S " in l:
        out.append(l + " sc=8 sk=%d" % (sk_i % 3))
        sk_i += 1
    else:
        out.append(l)
# 动作开始序列（含 6/12 -> 7/21 连段，帧差 10）
seq = [(3, 1), (2, 4), (7, 21), (1, 3), (6, 12), (7, 21), (3, 0), (2, 7), (1, 1), (3, 4)] * 8
for k, (a, s) in enumerate(seq):
    f = 3500 + 233 * k
    out.append(P + ("[rai] COMBO f=%d mon=0C130510 sp=0020 a=%d s=%d pa=%d ps=%d "
                    "sel=%d an=%d gap=233 st=%d ev=1 kind=255 log=%d") %
               (f, a, s, a, s, 40 + k, 10 + k, 1 if k % 3 == 0 else 0, 9800 + k))
# END 请求（ev=2），故意落在动作开始前 1-3 帧
for k in range(20):
    f = 3498 + 233 * k
    out.append(P + ("[rai] COMBO f=%d mon=0C130510 sp=0020 a=3 s=1 pa=2 ps=4 "
                    "sel=%d an=0 gap=1 st=0 ev=2 kind=%d log=%d") %
               (f, 40 + k, k % 4, 9900 + k))
OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print("wrote", OUT.name, len(out), "lines")
