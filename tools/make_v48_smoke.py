# -*- coding: utf-8 -*-
"""生成 v48 合成日志，无需游戏即可验证判读链路。"""
from pathlib import Path

OUT = Path(r"D:\MHGU mod maker\04_RiseAI\out\sim_v48_smoke.txt")
L = []
qstart = 3247
L.append("[forge] [INFO] [rai] ===== RAI v48 EXHAUST-TRIGGER CHAIN "
         "(rule = v38, one-shot bounded force) =====")
L.append("[forge] [INFO] [rai] SITE +0A30E4=E92D41F0 "
         "(EXH add, expect E92Dxxxx push else SKIP)")
L.append("[forge] [INFO] [rai] INSTALL h_exh +000A30E4 first=E92D41F0 "
         "(force amount once)")
L.append("[KatSmithy] f=%d layout + GUI\\01_quest\\hud\\hud0" % qstart)

# R 行：常规 150f 一条；触发点附近加密为 30f
MAIN = "0C1F1930"
ACT = "0C1F2D70"
force_f = 9000
f = 600
an = 0
while f <= 15000:
    step = 30 if 8700 <= f <= 10200 else 150
    if f % step == 0 or f == force_f:
        if f < force_f:
            ex, thr, proc, amt, flg = (f // 150) % 60, 150, 0, 5, 0
            st = 0
        elif f < force_f + 600:
            ex, thr, proc, amt, flg = 0, 200, 1, 0, 0
            st = 0
        else:
            ex, thr, proc, amt, flg = 10, 200, 1, 5, 0
            st = 0
        L.append("[forge] [INFO] [rai] R f=%d i=0 mon=%s act=%s st=%d t4=0 "
                 "ex=%d thr=%d proc=%d amt=%d flg=%d t5c=0 d5=%d h1=1 e1=%d "
                 "dc=0 s3f=0 f5c=0 p3ca=50 p3be=50 low=%d log=%d" %
                 (f, MAIN, ACT, st, ex, thr, proc, amt, flg,
                  (f * 7) % 65536, (f // 30) % 120,
                  1 if 8400 <= f <= 10800 else 0, len(L)))
    f += 30 if 8700 <= f <= 10200 else 150

# A 行（动作开始抽样）
for i, af in enumerate(range(1200, 15000, 360)):
    an += 1
    L.append("[forge] [INFO] [rai] A f=%d mon=%s id=%d a=7 s=%d pa=3 ps=1 "
             "st=0 c0=0 c4=0 c8=0 cf=0 e1=%d dc=0 h1=1 t4=0 ex=%d log=%d" %
             (af, MAIN, 500 + i, i % 100, i % 100, min(150, i * 5), len(L)))

L.append("[forge] [INFO] [rai] N f=8400 kind=ENTER-LOW dA=1 lowhits=2 "
         "a=30 log=%d" % len(L))
L.append("[forge] [INFO] [rai] N f=10800 kind=EXIT-LOW dA=6 a=42 log=%d" % len(L))

# U 行：EXH add 调用轨迹（force 前后 + POST）
for uf in (7200, 8100, 8700, force_f):
    a1 = 5 if uf < force_f else 5
    cnt, thr = 55, 150
    amt = thr + 16 if uf == force_f else a1
    L.append("[forge] [INFO] [rai] U f=%d em=%s act=%s a1=%d cnt=%d thr=%d "
             "proc=0 amt=%d force=%d forced=0 log=%d" %
             (uf, MAIN, ACT, a1, cnt, thr, amt,
              1 if uf == force_f else 0, len(L)))
L.append("[forge] [INFO] [rai] U f=%d em=%s act=%s POST ret=1 cnt=0 thr=200 "
         "proc=1 flg=0 t5c=0 log=%d" % (force_f, MAIN, ACT, len(L)))
for uf in (9600, 10500, 12000):
    L.append("[forge] [INFO] [rai] U f=%d em=%s act=%s a1=5 cnt=10 thr=200 "
             "proc=1 amt=5 force=0 forced=1 log=%d" % (uf, MAIN, ACT, len(L)))

# BEAT
a = 0
for bf in range(300, 15300, 300):
    a += 0 if 8400 <= bf <= 10800 else 5
    L.append("[forge] [INFO] [rai] BEAT f=%d m=100 a=%d sel=1 act=1 v=15 "
             "noalt=0 fail=0 ok=10 live=1 peak=8 hub=15 log=%d mon=%s" %
             (bf, a, len(L), MAIN))

OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
print("wrote", OUT, "lines", len(L))
