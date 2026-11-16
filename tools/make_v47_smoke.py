#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 v47 合成日志（无需游戏），用于验证 analyze_v47_tired.py 判读链路。"""
from pathlib import Path

OUT = Path(r"D:\MHGU mod maker\04_RiseAI\out\sim_v47_smoke.txt")
L = []
n = 0


def emit(s):
    global n
    n += 1
    L.append("[forge] [INFO] [rai] " + s.replace("log=X", "log=%d" % n))


L.append("[forge] [INFO] [rai] ===== RAI v47 TIRED-WINDOW TIMED SNAPSHOT (rule = v38, ZERO writes) =====")
L.append("[forge] [INFO] [rai] ===== RAI v43 EM-BASE SELF-CONSISTENCY SCAN (compat) =====")
L.append("[KatSmithy] f=3247 layout + GUI\\01_quest\\hud\\hud0")

MON = "0C190060"
ACT = "0C1914A0"
a_total = 0
ex = 0
# 每 300 帧的动作增量：正常 -> 下降 -> 零动作 -> 恢复
dA = [8] * 40 + [5, 2, 1, 0, 0, 0, 0, 0, 0, 0, 9, 11, 8]
qstart = 3247

for i, d in enumerate(dA):
    f = 300 * (i + 1)
    a_total += d
    # BEAT
    emit("BEAT f=%d m=%d m1=1 m0c=1 m0e=1 x=1 q=1 a=%d sel=1 act=1 beg=1 "
         "begf=0 rep=1 v=1 noalt=0 fail=0 ok=1 live=1 peak=25 hub=15 log=X mon=%s"
         % (f, a_total, a_total, MON))
    # A 行：减气蓄积累积，低动作段没有出招
    if d > 0:
        ex = min(150, ex + 5)
        emit("A f=%d mon=%s id=520 a=7 s=4 pa=2 ps=16 st=%d c0=0 c4=0 c8=0 "
             "cf=0 e1=4 dc=0 h1=0 t4=0 ex=%d log=X"
             % (f - 100, MON, 1 if 10000 < f < 14200 else 0, ex))
    # N 行锚点
    if f == 12600:
        emit("N f=%d kind=ENTER-LOW dA=2 lowhits=2 a=%d log=X" % (f, a_total))
    if f == 16200:
        emit("N f=%d kind=EXIT-LOW dA=9 lowhits=0 a=%d log=X" % (f, a_total))
    # R 行定时快照：常规 150f，低动作段 30f
    low = 12600 <= f <= 15900
    period = 30 if low else 150
    for k in range(300 // period):
        rf = f - 300 + k * period
        if rf < 600:
            continue
        tired = 12600 <= rf <= 15000
        emit("R f=%d i=0 mon=%s act=%s st=%d t4=%d ex=%d d5=%d h1=%d e1=4 "
             "dc=0 p3ca=%d p3be=%d low=%d log=X"
             % (rf, MON, ACT,
                2 if tired else 0,          # st: 疲惫窗口 0 -> 2
                600 if tired else 0,        # t4: 疲惫窗口 0 -> 600
                ex, 0, 0,
                120 if tired else 0,        # p3ca: 疲惫窗口 0 -> 120
                0, 1 if low else 0))
    # 少量 C 行（v47 指纹不含噪声，不会吃光配额）
    if f % 1200 == 0:
        emit("C f=%d i=0 mon=%s c0=0 c4=0 c8=0 cf=0 e1=4 dc=0 st=0 t4=0 "
             "ex=%d fp=00000000 log=X" % (f, MON, ex))

OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
print("wrote", OUT, "lines", len(L))
