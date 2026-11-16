# -*- coding: utf-8 -*-
"""把 7_ / 8_ 的 STEP 49 提示更新为 STEP 50（v50 W1 权重层）。

纪律：只改 echo 提示文字 / title / TOOL2 指向；
执行逻辑、输出路径、日志轮转、Python 绝对路径、CRLF 全部保持不变。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P7 = ROOT / "7_P54_启动并抓日志.bat"
P8 = ROOT / "8_lite_check.bat"


def load(p):
    b = p.read_bytes()
    assert b"\r\n" in b, "%s 不是 CRLF" % p
    return b.decode("gbk")


def save(p, s):
    p.write_bytes(s.encode("gbk"))


def replace_once(s, old, new, tag):
    assert s.count(old) == 1, "%s: 匹配 %d 次（应为 1）" % (tag, s.count(old))
    return s.replace(old, new, 1)


# ---------------- 8_lite_check.bat ----------------
s8 = load(P8)
s8 = replace_once(s8,
    "title RiseAI - LITE CHECK (v49 three-state weight layer)",
    "title RiseAI - LITE CHECK (v50 W1 rise-pool weight layer)", "8 title")
s8 = replace_once(s8,
    'set "TOOL2=D:\\MHGU mod maker\\04_RiseAI\\tools\\analyze_v49_states.py"',
    'set "TOOL2=D:\\MHGU mod maker\\04_RiseAI\\tools\\analyze_v50_weight.py"',
    "8 TOOL2")

lines8 = s8.split("\r\n")
i0 = next(i for i, l in enumerate(lines8) if l.startswith("echo === RiseAI LITE CHECK"))
i1 = next(i for i in range(i0, len(lines8)) if lines8[i].strip() == "pause")
block8 = [
    "echo === RiseAI LITE CHECK (v50 W1 RISE-POOL WEIGHT LAYER) ===",
    "echo.",
    "echo P32/P34 audit: v49 only changed how OFTEN a move is vetoed,",
    "echo   it never touched the REAL Rise carrier: the weighted action pool.",
    "echo   Rise 15 pools = 3 states x 5 distance ranges, entropy",
    "echo   non-tired 1.6705 / tired 1.2984. GU op02 is the same kind of",
    "echo   rand%%100 weighted lottery (case weight sum = 100).",
    "echo.",
    "echo W1 (this build): for eligible cases sort by weight, take top-k,",
    "echo   zero the rest, re-assign to a Rise-shaped 100-sum distribution,",
    "echo   then run the normalized lottery. Shapes:",
    "echo     NON-TIRED k=3 [45,32,23] or k=4 [40,27,20,13]  mix 61:39",
    "echo     TIRED     k=3 [60,30,10]",
    "echo   Offline check: non-tired H=1.6701, tired H=1.2955 vs Rise targets.",
    "echo   Local calculation ONLY - case weights in game memory are NOT written.",
    "echo.",
    "echo W0 fix (P33): tired trigger now needs proc<=30 AND 0<thr<0x4000;",
    "echo   when h_exh is installed only ret==1 counts. This kills the fake",
    "echo   tired window from the v49 field (proc=211, U=0).",
    "echo   veto depth is now 2 (non-tired) / 1 (tired); anger depth3 and",
    "echo   the tired 50%% keep were REMOVED (P32: anger/normal entropy equal).",
    "echo.",
    "echo   1. Start ANY quest (Great Maccao is the proven short hunt).",
    "echo   2. Play normally through rage phases and one natural drool",
    "echo      (Great Maccao: roughly 3 quest minutes).",
    "echo   3. CLOSE THE GAME NORMALLY. Do NOT idle in the pause menu:",
    "echo      game logic freezes while the frame callback keeps running.",
    "echo   4. Do NOT press F9. Do NOT use the instant-complete cheat.",
    "echo.",
    "echo SAFETY: read-only, 5 hooks unchanged, original! args unchanged.",
    "echo   Crash / freeze / desync: quit and tell me. Read-only rollback:",
    "echo   copy 04_RiseAI\\out\\rai_tristate_v49.nro over the plugin nro.",
    "echo Separate log: %OUT%. game_p54.txt and game_p15.txt are NOT touched.",
    "echo.",
    "echo PLEASE REPORT: monster, roughly when it raged / drooled, and",
    "echo   whether the action mix feels different in each phase.",
]
lines8[i0:i1] = block8
s8 = "\r\n".join(lines8)
s8 = replace_once(s8,
    "echo === THREE-STATE WEIGHT LAYER (v49) ===",
    "echo === W1 RISE-POOL WEIGHT (v50) ===", "8 header2")
s8 = replace_once(s8,
    "echo Report 2 is the v49 three-state verdict (PASS/FAIL per check).\r\n"
    "echo No forced tired this round: play until a natural drool appears.",
    "echo Report 2 is the v50 W1 verdict (PASS/FAIL per check).\r\n"
    "echo V lines carry wm/wk (Rise shape), S lines carry w3/w4/wt counts.",
    "8 footer")

for guard in ('set "OUT=D:\\MHGU mod maker\\02_Workspace\\game_p54_lite.txt"',
              'set "PY=C:\\Users\\RongLynn\\.workbuddy\\binaries\\python\\versions\\3.13.12\\python.exe"',
              'mhgurecomp.exe > "%OUT%" 2>&1',
              '"%PY%" "%TOOL%" "%OUT%" > "%REP%" 2>&1',
              '"%PY%" "%TOOL2%" "%OUT%" > "%REP2%" 2>&1'):
    assert guard in s8, "8 执行逻辑被破坏: %s" % guard
save(P8, s8)

# ---------------- 7_P54_启动并抓日志.bat ----------------
s7 = load(P7)
s7 = replace_once(s7,
    "echo === RiseAI STEP 49: THREE-STATE WEIGHT LAYER (read-only) ===",
    "echo === RiseAI STEP 50: W1 RISE-POOL WEIGHT LAYER (read-only) ===", "7 title")
lines7 = s7.split("\r\n")
j0 = next(i for i, l in enumerate(lines7) if l.startswith("echo v49 DOES"))
j1 = next(i for i in range(j0, len(lines7))
          if lines7[i].startswith("echo      and fall back to proc polling")) + 1
block7 = [
    "echo v50 DOES (W1 weight layer + W0 gate, all read-only):",
    "echo   1. Rise 15 pools use _TransitionRate weights. v49 only tuned",
    "echo      veto frequency; v50 re-shapes the actual case weights.",
    "echo   2. Eligible cases sorted by weight -> top-k -> Rise-shaped",
    "echo      100-sum distribution -> normalized rand%%100 lottery.",
    "echo      NON-TIRED k3[45,32,23] / k4[40,27,20,13] mix 61:39",
    "echo      TIRED k3[60,30,10]. Offline H: 1.6701 / 1.2955.",
    "echo      Case weights in game memory are NEVER written.",
    "echo   3. veto depth 2 (non-tired) / 1 (tired). Anger depth3 and",
    "echo      tired 50%% keep REMOVED: P32 proved anger/normal entropy",
    "echo      is nearly identical (1.6740 vs 1.6669).",
    "echo   4. W0 gate: proc<=30 AND 0<thr<0x4000; with h_exh installed",
    "echo      only EXH add ret==1 counts. Kills the v49 fake tired event.",
    "echo   5. Tired window still uses that monster's OWN action count,",
    "echo      so the pause menu cannot drain it (P19/P22/P28/P30).",
    "echo   6. V lines add wm/wk; S lines add w3/w4/wt; U lines add bad.",
]
lines7[j0:j1] = block7
s7 = "\r\n".join(lines7)
s7 = replace_once(s7,
    "echo ROLLBACK: copy 04_RiseAI\\out\\rai_exhaust_chain_v48.nro over plugin nro.",
    "echo ROLLBACK: copy 04_RiseAI\\out\\rai_tristate_v49.nro over plugin nro.",
    "7 rollback")
s7 = replace_once(s7,
    "echo   raged / looked tired (quest minute is best). That pins T/S lines.",
    "echo   raged / looked tired (quest minute is best). That pins V/S/T lines.",
    "7 report")
save(P7, s7)

print("[ok] 8_lite_check.bat / 7_P54_启动并抓日志.bat -> STEP 50, CRLF + exec logic intact")
