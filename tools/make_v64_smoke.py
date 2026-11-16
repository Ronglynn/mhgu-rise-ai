# -*- coding: utf-8 -*-
"""从 v63 冒烟日志变换出 v64（P64 三缺陷修复 / 纯只读）冒烟日志。"""
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent / "out"
SRC, OUT = ROOT / "sim_v63_smoke.txt", ROOT / "sim_v64_smoke.txt"
P = "[forge] [INFO] "
B0 = P + "[rai] ===== RAI v64 P64 FIX: DG gate diag / ZD table-chain diag / AE-QX quota + throttle / READONLY ====="
R0 = P + "[rai] Rule: DRAIN_ENABLE=0 (natural tiredness in ~5min, P64) / DG diagnoses why v63 J/G=0 / ZD diagnoses why ZT=0 / 6 hooks / ZERO writes / ROLLBACK v63.nro"
lines = SRC.read_text(encoding="utf-8").splitlines()
out = []
for idx, l in enumerate(lines):
    if idx == 0:
        out += [B0, R0, l]
    elif "[rai] J " in l or "[rai] G " in l:
        continue
    else:
        out.append(l.replace("gdone=1", "gdone=0").replace("gf=8774", "gf=0"))
# DG 门控诊断（模拟 LOW=1 卡点）
for k in range(6):
    f = 3600 + 600 * k
    out.append(P + ("[rai] DG f=%d mon=0C130510 a1=-8 en=0 done=0 site=1 gate=1 low=1 "
                    "A=%d thr=233 cur=650 st5=0 si=0 an=12 hn=%d log=%d") %
               (f, 40 + 10 * k, 64 * (k + 1), 9500 + k))
# ZD 表链诊断（模拟 tune 无效，fail=2）
for k in range(6):
    out.append(P + ("[rai] ZD f=%d mon=0C130510 md=4 ip=1C010D4E ba=0 tune=00000000 "
                    "cnt=0 base=00000000 fail=2 log=%d") % (4200 + 600 * k, 9600 + k))
# 把疲惫窗拉到 P64 实测的 ~4626 帧，供时长判据校验
for k, off in enumerate((1800, 3600, 4626)):
    out.append(P + ("[rai] QX f=%d mon=0C220B70 r1=0 r2=1 r3=2 p5=0 w0=00000002 w1=00000002 "
                    "kind=2 e1=7 dc=1 t505=2 t518=0 t5e08=0 a1a8=00000040 a2c0=00000000 log=%d") %
               (9074 + off, 9800 + k))
OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print("wrote", OUT.name, len(out), "lines")
