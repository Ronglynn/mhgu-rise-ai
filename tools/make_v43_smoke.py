#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""make_v43_smoke.py — 生成 v43 判读链路的合成日志（不需要游戏）

场景：两个 mon 槽都扫到同一个 em 偏移 delta=-288；D 行在任务内
~15.7 分钟出现 c0=2 / c4=2 / t4=180 的疲惫段。用于验证
analyze_v43_base.py 的判据链路，不代表实机结论。
"""
import sys
from pathlib import Path

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"D:\MHGU mod maker\04_RiseAI\out\sim_v43_smoke.txt")
L = []


def p(s):
    L.append(s)


p("[rai] ===== RAI v43 EM-BASE SELF-CONSISTENCY SCAN (rule = v38, ZERO writes) =====")
p("[rai] Rule: UNCHANGED v38 / read-only em base scan / P line delta / D line real state fields")
p("[rai] ===== RAI v41 STATE SCAN (fields retained: 8 mon slots + discrete fingerprint) =====")
p("[rai] ===== RAI v38 PREV-TABLE VETO + NORMALIZED REDRAW (main track only) =====")
p("[rai] SITE +08E144=E92D4FF0 +082F80=E92D4FF0 +076154=E92D4FF0 +0AFF40=E3A02000")
p("[rai] INSTALL h_matcher +0008E144 first=E92D4FF0")
p("[rai] INSTALL h_emc +00082F80 first=E92D4FF0")
p("[rai] INSTALL h_unify +00076154 first=E92D4FF0")
p("[rai] INSTALL h_start_40 +000AFF40 / hubMask=15 hooks=4")
p("[KatSmithy] f=13278 layout + GUI\\01_quest\\hud\\hud0 rGUI=0x19bdfa10")

QSTART, LAST = 13278, 120000
MON = ("0C1C2D40", "0C410060")
DELTA = -288

# P 行：每槽 1 个自洽命中 + 1 条汇总
for i, mon in enumerate(MON):
    em = int(mon, 16) + DELTA
    p("[rai] P f=%d i=%d mon=%s em=%08X delta=%d c0=1 c4=0 cf=0 "
      "act=0C1C3A10 strict=1 loose=3 log=%d" % (14000 + i * 60, i, mon, em, DELTA, 10 + i))
    p("[rai] P f=%d i=%d mon=%s SUMMARY strict=1 loose=3 best_delta=%d log=%d" %
      (14000 + i * 60, i, mon, DELTA, 12 + i))

a = 0
for f in range(300, LAST + 1, 300):
    if 70000 <= f <= 70900:
        da = 0
    else:
        da = 3 if f % 900 else 5
        a += da
    p("[rai] BEAT f=%d m=900 m1=60 m0c=40 m0e=30 x=100 q=200 a=%d sel=%d act=%d "
      "beg=60 begf=0 rep=8 v=10 noalt=0 fail=0 ok=60 live=1 peak=20 hub=15 "
      "log=%d mon=0C1C2D40" % (f, a, a, a, 30 + f // 300))
    if f % 3000 == 0:
        p("[rai] S f=%d e1=2 e0=1 r1=4 r0=0 n1=0 n0=0 v1=10 v0=0 "
          "rd=10 b1=0 p2=3 log=%d" % (f, 40 + f // 3000))

for j in range(200):
    f = 13400 + j * 480
    p("[rai] A f=%d mon=%s id=%d a=7 s=0 pa=0 ps=0 st=0 c0=0 c4=413 "
      "c8=413 cf=0 e1=0 dc=0 h1=1 t4=65535 ex=0 log=%d" %
      (f, MON[j % 2], 1 + j % 8, 200 + j))

for f in range(13400, LAST, 2000):
    tired = 70000 <= f <= 72000
    c0, c4, cf, st, t4 = (2, 2, 0, 0, 180) if tired else (1, 0, 0, 0, 65535)
    for i, mon in enumerate(MON):
        em = int(mon, 16) + DELTA
        p("[rai] D f=%d i=%d mon=%s em=%08X delta=%d c0=%d c4=%d cf=%d "
          "st=%d t4=%d fp=%08X log=%d" %
          (f, i, mon, em, DELTA, c0, c4, cf, st, t4,
           c0 | (c4 << 8) | (cf << 16) | (st << 24), 500 + f // 1000))
        p("[rai] C f=%d i=%d mon=%s c0=0 c4=413 c8=413 cf=0 e1=0 dc=0 st=0 "
          "t4=65535 ex=0 fp=00000000 log=%d" % (f, i, mon, 700 + f // 1000))

out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(L) + "\n", encoding="utf-8")
print("wrote %s lines=%d bytes=%d" % (out, len(L), out.stat().st_size))
