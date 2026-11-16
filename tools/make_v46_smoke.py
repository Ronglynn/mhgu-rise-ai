#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""make_v46_smoke.py — 由 v45 合成日志生成 v46「字段层强制疲劳」场景

场景：Y 行 TRIG 把 act+0x518 写成 2，之后 600 帧 HOLD 回读恒为 2，
A 行 st 出现 2。用于验证 analyze_v43_base.py 的 v46 判据链路。
"""
import re
import sys
from pathlib import Path

src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"D:\MHGU mod maker\04_RiseAI\out\sim_v45_smoke.txt")
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(
    r"D:\MHGU mod maker\04_RiseAI\out\sim_v46_smoke.txt")

L = []
for ln in src.read_text(encoding="utf-8").splitlines():
    if "RAI v45 FORCE-TIRED VIA HOOK" in ln:
        L.append("[rai] ===== RAI v46 FIELD-LEVEL FORCE-TIRED (act+0x518=2, 600f hold) =====")
        continue
    if ln.startswith("[rai] A "):
        ln = re.sub(r"st=\d+", "st=2", ln)
    L.append(ln)

F = 15000
L.append("[rai] Y f=%d dt=0 kind=TRIG act=0C1C3A10 stb=1 sta=2 t4=65535 n=1 log=950" % F)
for k, dt in enumerate([1, 2, 4, 8, 16, 32, 64, 120, 300, 600]):
    L.append("[rai] Y f=%d dt=%d kind=HOLD act=0C1C3A10 stb=0 sta=2 "
             "t4=%d n=%d log=%d" % (F + dt, dt, 180 if dt >= 32 else 65535, 1 + k, 951 + k))

out.write_text("\n".join(L) + "\n", encoding="utf-8")
print("wrote %s lines=%d bytes=%d" % (out, len(L), out.stat().st_size))
