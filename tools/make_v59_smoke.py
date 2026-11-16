# -*- coding: utf-8 -*-
"""从 v58 冒烟日志变换出 v59（W2 探针修复版）冒烟日志，离线判读回归用。"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "out"
SRC = ROOT / "sim_v58_smoke.txt"
OUT = ROOT / "sim_v59_smoke.txt"
P = "[forge] [INFO] "

lines = SRC.read_text(encoding="utf-8").splitlines()
out = []
zs_added = 0
for idx, l in enumerate(lines):
    if idx == 0:
        out.append(P + "[rai] ===== RAI v59 W2 PROBE FIX (near-case scan + raw bytes + script ptr scan) =====")
        continue
    if idx == 1:
        out.append(P + "[rai] Rule: v59 W2 Z line adds src/g/ts/r0/r1 + ZS script-pointer scan / ent is DIAGNOSTIC only / W1 UNCHANGED / ZERO writes / NO new hook / ROLLBACK v58.nro")
        continue
    if "[rai] Z " in l:
        d = {k: v for k, v in re.findall(r"(\w+)=(\S+)", l.split("[rai] Z ", 1)[1])}
        md = int(d.get("md", 0))
        hit = int(d.get("hit", -1))
        ret = int(d.get("ret", 0))
        ip = int(d.get("ip", "0"), 16)
        # 模拟 v59：md=6 由 near 扫描兜底(src=2)，其余走 begin(src=1)
        src = 2 if md == 6 else 1
        ts = int(d.get("t%d" % hit, 255)) if hit >= 0 else (8 if md == 6 else 255)
        g = (ip + ret) & 0xFFFFFFFF
        l = l.replace(" log=", " src=%d ts=%d g=%08X r0=%08X r1=%08X log=" %
                      (src, ts, g, 0x01061708, 0x0206170A))
    out.append(l)
    if "[rai] ZP " in l and zs_added < 2:
        zs_added += 1
        out.append(
            P + ("[rai] ZS f=%s mon=0C1044F0 n=3 o0=6016 v0=1A77D000 "
                 "o1=6020 v1=1A77E000 o2=6096 v2=1C063000 "
                 "o3=0 v3=00000000 o4=0 v4=00000000 o5=0 v5=00000000 log=%d")
            % (re.search(r"f=(\d+)", l).group(1), 6000 + zs_added))
OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print("wrote", OUT.name, len(out), "lines, ZS=%d" % zs_added)
