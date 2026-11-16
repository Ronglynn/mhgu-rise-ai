# -*- coding: utf-8 -*-
"""从 v56 合成冒烟日志变换出 v57 发布配置合成冒烟日志（离线判读回归用）。"""
import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "out" / "sim_v56_smoke.txt"
OUT = Path(__file__).resolve().parent.parent / "out" / "sim_v57_smoke.txt"
P = "[forge] [INFO] "

lines = SRC.read_text(encoding="utf-8").splitlines()
out = [
    P + "[rai] ===== RAI v57 W1-ALL-PICKS + READONLY RELEASE PROFILE =====",
    P + "[rai] Rule: Rise shape on EVERY main-track draw / DRAIN_ENABLE=0 / PROFILE_RELEASE=1 / ZERO writes / W1_ALL=1 / ROLLBACK v56.nro",
]
wall = 0
for l in lines:
    # 发布配置：R/W/J/G 高频与强制行全部不存在
    if any(("[rai] %s " % t) in l for t in ("R", "W", "J", "G")):
        continue
    if "[rai] S " in l:
        wall += 24
        l = re.sub(r" gdone=\d+", " gdone=0", l)
        l = re.sub(r" gf=\d+", " gf=0", l)
        l = re.sub(r" log=\d+", " wall=%d wnok=%d log=%d" %
                   (wall, int(wall * 0.86), 3000 + wall // 24), l)
    out.append(l)
OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print("wrote", OUT.name, len(out), "lines")
