# -*- coding: utf-8 -*-
"""从 v55 合成冒烟日志变换出 v56 合成冒烟日志（离线判读回归用）。"""
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "out" / "sim_v55_smoke.txt"
OUT = Path(__file__).resolve().parent.parent / "out" / "sim_v56_smoke.txt"
P = "[forge] [INFO] "
MON = "0C250060"

lines = SRC.read_text(encoding="utf-8").splitlines()
out = [
    P + "[rai] ===== RAI v56 PER-ACTION STAMINA DRAIN x64 (1-2 actions -> tired) ======",
    P + "[rai] Rule: amplify every negative delta @0xBD260 / J line per action / G line once on drain / DRAIN_DONE fuse / ZERO writes / ROLLBACK v55.nro",
]
j_added = False
for l in lines:
    # 合成数据里疲惫 V 行原本在 f=2120（G 帧之前），移到真实疲惫窗口内
    if "[rai] V " in l and "f=2120" in l:
        l = l.replace("f=2120", "f=16000")
    if "[rai] G " in l:
        # 2 个 J 行：第 1 次扣半不耗尽，第 2 次游戏判定耗尽
        out.append(P + "[rai] J f=14400 mon=%s d0=4294967288 d1=4294966784 cur=800 "
                   "a505=0 a508=288 an=20 jn=1 log=6001" % MON)
        out.append(P + "[rai] J f=14700 mon=%s d0=4294967288 d1=4294966784 cur=288 "
                   "a505=1 a508=0 an=21 jn=2 log=6002" % MON)
        out.append(P + "[rai] G f=15000 mon=%s act=0C2601A0 b505=0 b508=288 b506=1000 "
                   "d0=4294967288 d1=4294966784 bp41=0 a505=1 a508=0 ap41=0 "
                   "thr=285 an=21 jn=2 force=1 log=6000" % MON)
        j_added = True
        continue
    out.append(l)
assert j_added, "no G line in source"
OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print("wrote", OUT.name, len(out), "lines")
