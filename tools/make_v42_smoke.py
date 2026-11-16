#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""make_v42_smoke.py — 生成 v42 判读链路的合成日志（不需要游戏）

用法：python 04_RiseAI/tools/make_v42_smoke.py [输出路径]
默认写 04_RiseAI/out/sim_v42_smoke.txt。

场景：写入在任务内第 30 个动作开始后落地（ex1=1000），
      维持窗口内 ex 逐渐衰减，dt=32 时 c0=2 / t4=180 ⇒ G 行早停；
      BEAT 在任务内约 4.3 分钟出现零动作段（早于自然疲劳 15.3 分钟）。
用于验证 analyze_v42_force.py 的判据链路，不代表实机结论。
"""
import sys
from pathlib import Path

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"D:\MHGU mod maker\04_RiseAI\out\sim_v42_smoke.txt")
L = []


def p(s):
    L.append(s)


p("[rai] ===== RAI v42 FORCE-TIRED + STATE SCAN (rule = v38, bounded exhaust write) =====")
p("[rai] Rule: UNCHANGED v38 / act+0x5D82=1000 after 30 action starts / 120f maintain window")
p("[rai] ===== RAI v41 STATE SCAN (fields retained: 8 mon slots + discrete fingerprint) =====")
p("[rai] ===== RAI v39 STATE PROBE (rule = v38, read-only fields) =====")
p("[rai] ===== RAI v38 PREV-TABLE VETO + NORMALIZED REDRAW (main track only) =====")
p("[rai] SITE +08E144=E92D4FF0 +082F80=E92D4FF0 +076154=E92D4FF0 +0AFF40=E92D4FF0")
p("[rai] INSTALL h_matcher +0008E144 first=E92D4FF0")
p("[rai] INSTALL h_emc +00082F80 first=E92D4FF0")
p("[rai] INSTALL h_unify +00076154 first=E92D4FF0")
p("[rai] INSTALL h_start_40 +000AFF40 / hubMask=15 hooks=4")
p("[KatSmithy] f=14566 layout + GUI\\01_quest\\hud\\hud0")

QSTART = 14566
F_FRAME = 15000
LAST = 120000

# --- BEAT：全量动作计数；f=30000..30900 三个 300 帧窗口零动作 ---
a = 0
for f in range(300, LAST + 1, 300):
    if 30000 <= f <= 30900:
        da = 0
    else:
        da = 3 if f % 900 else 5
        a += da
    p("[rai] BEAT f=%d m=12 m1=12 m0c=8 m0e=4 x=2 q=1 a=%d sel=%d act=%d "
      "beg=40 begf=0 rep=8 v=10 noalt=0 fail=0 ok=40 live=1 peak=2 hub=15 "
      "log=%d mon=0C181390" % (f, a, a, a, 20 + f // 300))
    if f % 3000 == 0:
        p("[rai] S f=%d e1=2 e0=1 r1=4 r0=0 n1=0 n0=0 v1=10 v0=0 "
          "rd=10 b1=0 p2=3 log=%d" % (f, 30 + f // 3000))

# --- V 行（机制层，供旧脚本兼容）---
for f in range(15200, LAST, 4000):
    p("[rai] V f=%d mon=0C181390 sig=000C5540 pick=000C5540 rd=1 b1=0 "
      "ph=1 sw2=60 nr=12 log=%d" % (f, 100 + f // 4000))

# --- A 行：全场等距采样，含 v42 的 forced/fw ---
for j in range(300):
    f = 14600 + j * 320
    ex = 850 if f < 32000 else (180 if f < 60000 else 0)
    p("[rai] A f=%d mon=0C181390 id=%d a=7 s=0 pa=0 ps=0 st=0 c0=1 c4=413 "
      "c8=413 cf=0 e1=0 dc=0 h1=3 t4=0 ex=%d forced=1 fw=12 log=%d" %
      (f, 1 + j % 8, ex, 200 + j))

# --- C 行：多槽、离散指纹，覆盖到末帧 ---
for f in range(14600, LAST, 2000):
    for i, mon in ((0, "0C181390"), (1, "0C220060")):
        c0 = 2 if (i == 0 and 30000 <= f <= 33000) else 1
        t4 = 180 if c0 == 2 else 0
        p("[rai] C f=%d i=%d mon=%s c0=%d c4=413 c8=413 cf=0 e1=0 dc=0 "
          "st=0 t4=%d ex=0 fp=%08X log=%d" %
          (f, i, mon, c0, t4, c0 | (0x01000000 if t4 else 0), 600 + f // 1000))

# --- F / W / G ---
p("[rai] F f=%d i=0 an=30 mon=0C181390 act=0C1827D0 ex0=0 ex1=1000 "
  "st=0 c0=1 t4=0 forced=1 log=900" % F_FRAME)
STEPS = [1, 2, 4, 8, 16, 32, 64, 96, 120, 180, 300, 600]
exvals = [1000, 980, 960, 930, 900, 850, 700, 520, 380, 200, 60, 0]
for k, (dt, ex) in enumerate(zip(STEPS, exvals)):
    reached = dt >= 32
    c0, t4 = (2, 180) if reached else (1, 0)
    fw = min(dt + 1, 12)
    p("[rai] W f=%d dt=%d step=%d mon=0C181390 act=0C1827D0 ex=%d "
      "c0=%d cf=0 st=0 t4=%d fw=%d done=%d log=%d" %
      (F_FRAME + dt, dt, dt, ex, c0, t4, fw, 1 if reached else 0, 910 + k))
p("[rai] G f=%d dt=32 mon=0C181390 c0=2 t4=180 fw=8 "
  "STATE-REACHED stop-window log=930" % (F_FRAME + 32))

out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(L) + "\n", encoding="utf-8")
print("wrote %s lines=%d bytes=%d" % (out, len(L), out.stat().st_size))
