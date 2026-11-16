#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""make_v45_smoke.py — 由 v44 合成日志生成 v45「hook 改参」场景（无需游戏）

场景：h_tired hook 捕获游戏自己的 0x1068DD8 调用（T 行），
首次 r1=1 改成 2，original! 之后 em+0xCAC4=2 / act+0x408=180（F 行），
W 行回读确认。用于验证 analyze_v43_base.py 的 v45 判据链路。
"""
import re
import sys
from pathlib import Path

src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"D:\MHGU mod maker\04_RiseAI\out\sim_v44_smoke.txt")
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(
    r"D:\MHGU mod maker\04_RiseAI\out\sim_v45_smoke.txt")

L = []
for ln in src.read_text(encoding="utf-8").splitlines():
    if "RAI v44 FORCE-TIRED VIA GAME STATE MACHINE" in ln:
        L.append("[rai] ===== RAI v45 FORCE-TIRED VIA HOOK (rule = v38, one-shot r1 1->2) =====")
        L.append("[rai] INSTALL h_tired +001068DD8 first=E92D4FF0 (r1 1->2 one shot)")
        continue
    if ln.startswith("[rai] F "):
        continue  # 换成 v45 格式
    L.append(ln)

L.append("[rai] T f=15000 em=0C1C2C20 r1=1 r2=0 forced=0 change=1 log=900")
L.append("[rai] T f=15100 em=0C1C2C20 r1=3 r2=1 forced=1 change=0 log=901")
L.append("[rai] F f=15000 em=0C1C2C20 src=hook r1b=1 r1a=2 "
         "c4b=0 c4a=2 t4b=65535 t4a=180 log=902")

out.write_text("\n".join(L) + "\n", encoding="utf-8")
print("wrote %s lines=%d bytes=%d" % (out, len(L), out.stat().st_size))
