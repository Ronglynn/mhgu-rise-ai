# -*- coding: utf-8 -*-
"""把 7_ / 8_ 的 STEP 48 提示更新为 STEP 49（v49 三状态权重层）。

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
    "title RiseAI - LITE CHECK (v48 exhaust trigger chain)",
    "title RiseAI - LITE CHECK (v49 three-state weight layer)", "8 title")
s8 = replace_once(s8,
    'set "TOOL2=D:\\MHGU mod maker\\04_RiseAI\\tools\\analyze_v48_trigger.py"',
    'set "TOOL2=D:\\MHGU mod maker\\04_RiseAI\\tools\\analyze_v49_states.py"',
    "8 TOOL2")

lines8 = s8.split("\r\n")
i0 = next(i for i, l in enumerate(lines8)
          if l.startswith("echo === RiseAI LITE CHECK"))
i1 = next(i for i in range(i0, len(lines8)) if lines8[i].strip() == "pause")
block8 = [
    "echo === RiseAI LITE CHECK (v49 THREE-STATE WEIGHT LAYER) ===",
    "echo.",
    "echo P30 CLOSED the exhaust/tired trigger chain. Back on the AI main line.",
    "echo   Rise uses 3 states x 5 distance ranges = 15 weighted pools",
    "echo   (anger 6 tables / entropy 1.67, tired 4 tables / entropy 1.30).",
    "echo   GU has no such table => v49 does a STRUCTURAL approximation:",
    "echo   state controls how strict the prev-table veto is in the EMC",
    "echo   weighted pick. No weight table edit, no action id, no monster id.",
    "echo.",
    "echo THREE STATES (all read-only, works on every monster):",
    "echo   ANGER  *(u8*)(act+0x518)==1            prev depth 3  (more varied)",
    "echo   NORMAL everything else                  prev depth 2  (v38 baseline)",
    "echo   TIRED  EXH add(0xA30E4) ret=1 OR proc(act+0x5D8C) increment",
    "echo          -> window timed by that monster's OWN action count,",
    "echo             NOT forge frames (pause menu does NOT drain it)",
    "echo          prev depth 1 + 50 pct chance to keep the original pick",
    "echo.",
    "echo v48 ONE-SHOT FORCE (amount=thr+16) IS REMOVED. This build is",
    "echo   read-only: no memory write, no parameter change, original! always",
    "echo   called with unchanged arguments. T lines record state transitions,",
    "echo   V lines carry st3/vd, S lines carry per-state counters.",
    "echo.",
    "echo   1. Start ANY quest (Great Maccao is the proven short hunt).",
    "echo   2. Play normally through a few rage phases and one natural",
    "echo      tired/drooling phase (Great Maccao: roughly 3 quest minutes).",
    "echo   3. CLOSE THE GAME NORMALLY afterwards. Do NOT idle in the pause",
    "echo      menu: game logic freezes while the frame callback keeps running.",
    "echo   4. Do NOT press F9. Do NOT use the instant-complete cheat.",
    "echo.",
    "echo SAFETY: read-only. If crash / freeze / animation desync: quit and",
    "echo   tell me. Read-only rollback:",
    "echo   copy 04_RiseAI\\out\\rai_exhaust_chain_v48.nro over the plugin nro.",
    "echo Separate log: %OUT%. game_p54.txt and game_p15.txt are NOT touched.",
    "echo.",
    "echo PLEASE REPORT: which monster, roughly when it raged / drooled,",
    "echo   and whether the fight felt different in each phase.",
]
lines8[i0:i1] = block8
s8 = "\r\n".join(lines8)
# 结尾那两行 PLEASE REPORT 已在上面块里重写，这里改掉旧的收尾提示
s8 = replace_once(s8,
    "echo Please also tell me roughly WHEN the monster looked tired, and\r\n"
    "echo whether it was EARLY (forced) - no need to play a full 15 minutes.",
    "echo Report 2 is the v49 three-state verdict (PASS/FAIL per check).\r\n"
    "echo No forced tired this round: play until a natural drool appears.",
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
    "echo === RiseAI STEP 48: v48 EXHAUST TRIGGER CHAIN (one-shot force) ===",
    "echo === RiseAI STEP 49: THREE-STATE WEIGHT LAYER (read-only) ===", "7 title")

lines7 = s7.split("\r\n")
j0 = next(i for i, l in enumerate(lines7) if l.startswith("echo v48 DOES"))
j1 = next(i for i in range(j0, len(lines7))
          if lines7[i].startswith("echo      stay pure read-only")) + 1
block7 = [
    "echo v49 DOES (v38 rule on NORMAL state unchanged, all read-only):",
    "echo   1. ANGER (act+0x518==1) -> prev veto depth 3: more varied picks.",
    "echo   2. NORMAL               -> prev veto depth 2: v38 behaviour.",
    "echo   3. TIRED  (EXH add ret=1 OR proc increment) -> depth 1 plus",
    "echo      50 pct chance to keep the original weighted pick.",
    "echo      Window uses that monster's OWN action count, so the pause",
    "echo      menu cannot drain it (P19/P22/P28/P30 proven trap).",
    "echo   4. v48 one-shot force amount=thr+16 REMOVED. h_exh is now a",
    "echo      pure read-only trigger observer: same args, read ret only.",
    "echo      T lines = state events, V lines add st3/vd, S = per-state.",
    "echo   5. Runtime first word must be E92Dxxxx push, else SKIP h_exh",
    "echo      and fall back to proc polling (no functional loss).",
]
lines7[j0:j1] = block7
s7 = "\r\n".join(lines7)
s7 = replace_once(s7,
    "echo ROLLBACK: copy 04_RiseAI\\out\\rai_tired_snapshot_v47.nro over plugin nro.",
    "echo ROLLBACK: copy 04_RiseAI\\out\\rai_exhaust_chain_v48.nro over plugin nro.",
    "7 rollback")
s7 = replace_once(s7,
    "echo Play a NORMAL quest (no need to stand still). Tired state usually\r\n"
    "echo shows up after ~15 minutes of quest time, so a normal hunt is best.",
    "echo Play a NORMAL quest. Great Maccao naturally drools at about\r\n"
    "echo 3 quest minutes - one short hunt covers anger AND tired.",
    "7 timing")
s7 = replace_once(s7,
    "echo   look tired (quest minute is best). That pins the c0/t4 segment.",
    "echo   raged / looked tired (quest minute is best). That pins T/S lines.",
    "7 report")
save(P7, s7)

print("[ok] 8_lite_check.bat / 7_P54_启动并抓日志.bat -> STEP 49, CRLF + exec logic intact")
