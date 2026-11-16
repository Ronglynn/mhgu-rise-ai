#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""make_v44_smoke.py — 由 v43 合成日志生成 v44 强制疲劳场景（不需要游戏）

场景：P 行找到 em（delta=-288）；F 行一次性调用 0x1068DD8(em,2,0)，
调用后 em+0xCAC4=2、act+0x408=180；9 条 W 行回读确认状态被保持；
D 行全程显示疲惫状态。用于验证 analyze_v43_base.py 的 v44 判据链路。
"""
import re
import sys
from pathlib import Path

src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"D:\MHGU mod maker\04_RiseAI\out\sim_v43_smoke.txt")
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(
    r"D:\MHGU mod maker\04_RiseAI\out\sim_v44_smoke.txt")

L = []
for ln in src.read_text(encoding="utf-8").splitlines():
    if "RAI v43 EM-BASE SELF-CONSISTENCY SCAN" in ln:
        L.append(ln.replace(
            "RAI v43 EM-BASE SELF-CONSISTENCY SCAN (rule = v38, ZERO writes)",
            "RAI v44 FORCE-TIRED VIA GAME STATE MACHINE (rule = v38, one-shot call)"))
        L.append("[rai] TIRED SITE +1068DD8=E92D4FF0 (expect E92D4FF0 else SKIP)")
        continue
    if ln.startswith("[rai] D "):
        ln = re.sub(r"c0=\d+", "c0=2", ln)
        ln = re.sub(r"c4=\d+", "c4=2", ln)
        ln = re.sub(r"t4=\d+", "t4=180", ln)
    L.append(ln)

F_FRAME = 15000
F = ("[rai] F f=%d i=0 mon=0C1C2D40 em=0C1C2C20 delta=-288 site=10106DD8 "
     "c0b=1 c4b=0 t4b=65535 c0a=2 c4a=2 t4a=180 log=901" % F_FRAME)
L.append(F)
for k, dt in enumerate([1, 2, 4, 8, 16, 32, 64, 120, 300]):
    L.append("[rai] W f=%d dt=%d step=%d i=0 em=0C1C2C20 c0=2 c4=2 cf=0 "
             "t4=180 log=%d" % (F_FRAME + dt, dt, dt, 902 + k))

out.write_text("\n".join(L) + "\n", encoding="utf-8")
print("wrote %s lines=%d bytes=%d" % (out, len(L), out.stat().st_size))
