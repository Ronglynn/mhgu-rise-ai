# -*- coding: utf-8 -*-
"""从 v62 冒烟日志变换出 v63（温和自适应疲惫采集）冒烟日志。"""
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent / "out"
SRC, OUT = ROOT / "sim_v62_smoke.txt", ROOT / "sim_v63_smoke.txt"
P = "[forge] [INFO] "
B0 = P + "[rai] ===== RAI v63 MILD ADAPTIVE STAMINA DRAIN (target ~8 actions / 1-2 min to tired) ====="
R0 = P + "[rai] Rule: adaptive step = base/DRAIN_TARGET_ACT / 2 action-count fallbacks (pause-immune) / DRAIN_ENABLE=1 COLLECTION ONLY / ZERO memory writes / 6 hooks / W1+ZT+AE+QX UNCHANGED / set DRAIN_ENABLE=0 for release / ROLLBACK v62.nro"
lines = SRC.read_text(encoding="utf-8").splitlines()
out = []
for idx, l in enumerate(lines):
    if idx == 0:
        out += [B0, R0, l]
    elif idx == 1:
        out.append(l)
    else:
        out.append(l.replace("gdone=0", "gdone=1").replace("gf=0", "gf=8774"))
# 8 次温和放大，间隔 667 帧（v56 实机口径），最后一次一次性扣光
FS = [4105 + 667 * k for k in range(8)]
for k, f in enumerate(FS):
    cur = max(0, 650 - 81 * k)
    d1 = -(cur + 1) if k == 7 else -81
    a505 = 1 if k == 7 else 0
    a508 = 0 if k == 7 else max(0, cur - 81)
    out.append(P + ("[rai] J f=%d mon=0C220B70 d0=-8 d1=%d cur=%d a505=%d a508=%d "
                    "an=%d jn=%d log=%d") % (f, d1, cur, a505, a508, 5 + k, k + 1, 9100 + k))
GF = FS[-1]
out.append(P + ("[rai] G f=%d mon=0C220B70 act=0C221FB0 b505=0 b508=2 b506=1000 "
                "d0=-8 d1=-3 bp41=0 a505=1 a508=0 ap41=0 thr=233 an=12 jn=8 force=1 log=9110") % GF)
# 疲惫窗内的 W2/W3/W4 探针样本（t505=2 / st3=2）
for k in range(6):
    f = GF + 300 + 150 * k
    out.append(P + ("[rai] AE f=%d mon=0C220B70 old=00000006 new=00000002 gap=150 "
                    "sel=40 a=38 st=0 e1=7 t505=2 log=%d") % (f, 9120 + k))
    out.append(P + ("[rai] QX f=%d mon=0C220B70 r1=0 r2=1 r3=2 p5=0 w0=00000002 w1=00000002 "
                    "kind=1 e1=7 dc=1 t505=2 t518=0 t5e08=0 a1a8=00000040 a2c0=00000000 log=%d")
               % (f, 9130 + k))
    out.append(P + ("[rai] Z f=%d op=0B md=4 val=00000000 ip=1BF92A37 blk=1BF92A36 nc=4 "
                    "src=1 t0=0 t1=1 t2=2 t3=3 hit=2 ts=2 ret=7 st3=2 g=1BF92A3E "
                    "r0=02080117 r1=1E010200 log=%d") % (f, 9140 + k))
OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print("wrote", OUT.name, len(out), "lines")
