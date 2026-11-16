# -*- coding: utf-8 -*-
"""从 v70 冒烟日志变换出 v71（S 拆为 S+S2 / MAXLOG 1M）冒烟日志。"""
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent / "out"
SRC, OUT = ROOT / "sim_v70_smoke.txt", ROOT / "sim_v71_smoke.txt"
P = "[forge] [INFO] "
B0 = P + "[rai] ===== RAI v71 LOG INTEGRITY: MAXLOG 1M + per-epoch quotas + offline self-check ====="
R0 = P + "[rai] Rule: no global log cut for 30-60 min quests / run check_log_integrity.py after any quest / W1-W4 + HB + AR unchanged / 6 hooks / ZERO writes / ROLLBACK v70.nro"
lines = SRC.read_text(encoding="utf-8").splitlines()
out = []
for idx, l in enumerate(lines):
    if idx == 0:
        out += [B0, R0, l]
    elif "[rai] S " in l:
        body = l.split("[rai] S ", 1)[1]
        d = dict(re.findall(r"(\w+)=(\S+)", body))
        keys = ["e1","e0","r1","r0","n1","n0","v1","v0","rd","b1","p2",
                "s0","s1","s2","sv0","sv1","sv2","w3","w4","wt","d3","skip",
                "gac","gsum","gmax","gnz","amx","anf","anr"]
        keys2 = ["gdone","gf","wall","wnok","wb","bf","sc","sk","ge","gs","ek","log"]
        s1 = P + "[rai] S " + " ".join("f=%s" % d.get("f","0") if k == "f" else "%s=%s" % (k, d.get(k,"0")) for k in [] ) if False else None
        out.append(P + "[rai] S f=%s " % d.get("f","0") + " ".join("%s=%s" % (k, d.get(k,"0")) for k in keys))
        out.append(P + "[rai] S2 f=%s " % d.get("f","0") + " ".join("%s=%s" % (k, d.get(k,"0")) for k in keys2))
    else:
        out.append(l)
OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print("wrote", OUT.name, len(out), "lines")
