# -*- coding: utf-8 -*-
"""从 v54 合成冒烟日志变换出 v55 合成冒烟日志（离线判读回归用）。"""
import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "out" / "sim_v54_smoke.txt"
OUT = Path(__file__).resolve().parent.parent / "out" / "sim_v55_smoke.txt"
P = "[forge] [INFO] "
MON = "0C250060"

lines = SRC.read_text(encoding="utf-8").splitlines()
head = []
body = []
for l in lines:
    body.append(l)

# 1) 头部插入 v55 横幅与 h_stamina 安装行
head.append(P + "[rai] ===== RAI v55 NATIVE TIREDNESS FORCE (delta amplification @0xBD260) ======")
head.append(P + "[rai] Rule: W line chain-I fields / h_stamina amplifies delta=-(cur+1) ONCE / ZERO memory writes / W1 tired verdict reads act+0x505 / ROLLBACK v54.nro")
out = head[:2]
for l in body:
    out.append(l)
    if "[rai] SITE +0A30E4=" in l:
        out.append(P + "[rai] SITE +0BD260=E92D41F0 (v55 stamina delta hook, expect E92Dxxxx)")
        out.append(P + "[rai] INSTALL h_stamina +000BD260 first=E92D41F0 (v55 native tiredness force)")

# 2) R 行瘦身 + 派生 W 行；G 行改 v55 语义；V 行制造疲惫样本
DROP = {"q40","q44","q48","q4c","q50","q54","q58","q60",
        "t50c","p41","pt5c","t1a8","t362","t5df3"}
final = []
for l in out:
    if "[rai] R " in l:
        m = re.search(r"\[rai\] R (.*)$", l)
        kv = m.group(1).split()
        d = dict(x.split("=", 1) for x in kv if "=" in x)
        # v55 W 行（从 v54 全字段构造）
        w = ("[rai] W f=%s i=%s mon=%s act=%s t505=%s t506=%s t508=%s "
             "t50c=0 p41=%s pt5c=%s t1a8=1 t362=0 t5df3=0 "
             "q40=%s q44=%s q48=%s q4c=%s q50=%s q54=%s q58=%s q60=%s "
             "low=%s log=%s" %
             (d.get("f","0"), d.get("i","0"), d.get("mon",MON), d.get("act","0C2601A0"),
              d.get("t505","0"), d.get("t506","1000"), d.get("t508","1000"),
              "5" if d.get("t505","0") != "0" else "0",
              "30" if d.get("t505","0") != "0" else "0",
              d.get("q40","0"), d.get("q44","0"), d.get("q48","0"), d.get("q4c","0"),
              d.get("q50","0"), d.get("q54","0"), d.get("q58","0"), d.get("q60","0"),
              d.get("low","0"), d.get("log","0")))
        keep = [x for x in kv if x.split("=",1)[0] not in DROP]
        final.append(P + "[rai] R " + " ".join(keep))
        final.append(P + w)
        continue
    if "[rai] G " in l:
        final.append(P + "[rai] G f=15000 mon=%s act=0C2601A0 b505=0 b508=1000 b506=1000 "
                     "d0=4294967286 d1=4294966295 bp41=0 a505=1 a508=0 ap41=0 "
                     "thr=285 an=48 force=1 log=6000" % MON)
        continue
    if "[rai] V " in l and "f=2120" in l:
        l = re.sub(r" st3=\d+", " st3=2", l)
        l = re.sub(r" vd=\d+", " vd=1", l)
        l = re.sub(r" wm=\d+", " wm=3", l)
    final.append(l)

OUT.write_text("\n".join(final) + "\n", encoding="utf-8", newline="\n")
print("wrote", OUT.name, len(final), "lines")
