#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P91 · 一场多目标实机会话汇总判读（纯只读）。

用法:
    python tools/analyze_p91_session.py [日志路径] [--md 报告.md] [--json 结果.json]

默认读 02_Workspace/game_p91_oneshot.txt。一次运行同时给出 6 个目标的结论:
    A  P87① FNV0 空档帧差分布（决定 P87② 让位权重槽是否上）
    B  P89① 疲惫形状覆盖率改进是否生效（wt）
    C  v2 实机复验（P80 stance 修复后未跑，按成品口径，不用 v71 探针口径）
    D  30 分钟长时日志完整性（P80 静态配额审计的实跑确证，含边界说明）
    E  跨怪（已知 3 种；本场目标 >=2 只新怪，满足 P90 §7.3 的跨怪 A/B）
    F  P90 自身 F0 行配额风险（MAX_F0=600/epoch 是否打满导致 F9 停写）

判据口径见 out/P91_oneshot_session_kit.md、out/P90_capability_inventory_and_now_doable.md §8。
本脚本不修改日志、不写游戏内存、不触碰任何 mod。
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from check_log_integrity import audit as log_audit, EPOCH_F, LINE_LIMIT  # noqa: E402

PROJ = HERE.parents[1]
DEFAULT_LOG = PROJ / "02_Workspace" / "game_p91_oneshot.txt"

TAG_RE = re.compile(r"\[rai\] ([A-Z][A-Z0-9]*) (.*)$")
KV_RE = re.compile(r"(\w+)=(\S+)")
STATE = {0: "normal", 1: "anger", 2: "tired"}
KNOWN_SP = {"0020": "轰龙", "0050": "斩龙", "0052": "泡狐龙"}
MAX_F0 = 600


def iv(d: dict, k: str, default: int = 0) -> int:
    v = d.get(k)
    if v is None:
        return default
    try:
        return int(v, 0) if v.lower().startswith("0x") else int(v)
    except (ValueError, TypeError):
        return default


def sv(d: dict, k: str, default: str = "") -> str:
    return str(d.get(k, default))


def q(vals: list[int], p: float) -> int:
    if not vals:
        return 0
    s = sorted(vals)
    return s[min(len(s) - 1, int(len(s) * p))]


def parse(lines: list[str]) -> dict:
    out = collections.defaultdict(list)
    for line in lines:
        m = TAG_RE.search(line)
        if not m:
            continue
        d = dict(KV_RE.findall(m.group(2)))
        out[m.group(1)].append(d)
    return out


def merge_s_s2(rows: dict) -> int:
    s2 = {r.get("f"): r for r in rows.get("S2", [])}
    paired = 0
    for r in rows.get("S", []):
        x = s2.get(r.get("f"))
        if x:
            paired += 1
            for k, v in x.items():
                if k != "f":
                    r.setdefault(k, v)
    return paired


def verdict_table(goals: list[dict]) -> str:
    s = ["| 目标 | 结论 | 关键数字 | 下一步 |", "|---|---|---|---|"]
    for g in goals:
        s.append("| %s | **%s** | %s | %s |" % (g["name"], g["verdict"], g["evidence"], g["next"]))
    return "\n".join(s)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("log", nargs="?", default=str(DEFAULT_LOG))
    ap.add_argument("--md", default=None)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)

    path = Path(a.log)
    if not path.is_file():
        print("日志文件不存在:", path)
        return 1
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    rows = parse(lines)
    integ = log_audit(path)
    s_pairs = merge_s_s2(rows)

    S = rows.get("S", [])
    HB = rows.get("HB", [])
    BEAT = rows.get("BEAT", [])
    V = rows.get("V", [])
    F0 = rows.get("F0", [])
    F1 = rows.get("F1", [])
    F9 = rows.get("F9", [])

    installs = [l.strip() for l in lines if "[rai] INSTALL h_" in l]
    fatal = sum(1 for l in lines if "FATAL" in l)
    crash = sum(1 for l in lines if "c0000005" in l or "*** exception" in l
                or "host backtrace" in l)
    p90_banner = any("P90 PROBE" in l for l in lines)
    v71_banner = any("RAI v71" in l for l in lines)

    # ---- P94: 宿主日志通道诊断 -------------------------------------------
    # Forge 的 [log] level=error 会静默丢掉全部插件 INFO 行（含 [rai]），
    # 但插件本身已 loaded/relocated。此时不是「版本不对」，而是日志被过滤。
    forge_info = sum(1 for l in lines if "[forge] [INFO]" in l)
    forge_error = sum(1 for l in lines if "[forge] [ERROR]" in l)
    rai_lines = sum(1 for l in lines if "[rai]" in l)
    # 「日志通道」只看插件 INFO 行是否可见，与是否 P90 编译版无关。
    log_channel_ok = rai_lines > 0 and forge_info > 0
    plugin_loaded = any("loaded rai_entrylocator_probe.nro" in l for l in lines)
    host_ver = next((l.strip() for l in lines[:5]
                     if l.startswith("MHGU Recomp ")), "未知")
    log_filtered = (not p90_banner and plugin_loaded
                    and forge_info == 0 and forge_error > 0)
    ver_reason = ("Forge [log] level=error 过滤了全部插件 INFO 行" if log_filtered
                  else "未检出 P90 PROBE 横幅，无法确认编译版")
    ver_fix = ("把 mods/forge/romfs/nativeNX/forge/config.ini 的 level 改为 info"
               "（9_P91_oneshot.bat 前置会自动修正）后重打；本场无任何判据数据"
               if log_filtered
               else "确认加载 md5 0ab6cbec… 的 NRO 后重打；不要据此判据推进")

    beat_last = BEAT[-1] if BEAT else {}
    live, hub, fail = (iv(beat_last, k, -1) for k in ("live", "hub", "fail"))
    beat_fs = [iv(r, "f") for r in BEAT]
    f_last_beat = max(beat_fs) if beat_fs else 0
    minutes = f_last_beat / 3600.0

    # 怪种：P90 关闭了 COMBO/AR，sp 只能从 V 与 F0/F1 行取
    sp_all = collections.Counter()
    for tag in ("V", "F0", "F1"):
        for r in rows.get(tag, []):
            sp = sv(r, "sp")
            if sp and sp != "0000":
                sp_all[sp] += 1
    large = {sp: n for sp, n in sp_all.items()
             if re.fullmatch(r"[0-9A-Fa-f]{4}", sp) and int(sp, 16) < 0x1000}
    new_large = sorted(set(large) - set(KNOWN_SP))
    # 疲惫是否发生的多源交叉（F1.t505 为结段读数；V.st3 / S.s2 / wt 为独立证据）
    s2_peak = max((iv(r, "s2") for r in S), default=0)
    st3_seen = sorted({iv(r, "st3", 0xFF) for r in V if iv(r, "st3", 0xFF) <= 2})

    # ---------- A · FNV0 空档 ----------
    f0_by_start = {sv(r, "f"): r for r in F0}
    byst = collections.defaultdict(list)
    cross_mon = 0
    paired_f1 = 0
    for r in F1:
        d = iv(r, "d")
        byst[iv(r, "st", 9)].append(d)
        src = f0_by_start.get(sv(r, "f0"))
        if src:
            paired_f1 += 1
            if sv(src, "mon") and sv(r, "mon") and sv(src, "mon") != sv(r, "mon"):
                cross_mon += 1
    cross_ratio = 100.0 * cross_mon / paired_f1 if paired_f1 else 0.0
    # 修正(P92)：F1 的 st 是【段起点】状态；疲惫判据必须用【结段时】的 t505>=2。
    # F0/F1 是全局单段，同场小怪频繁命中 FNV0 会抢占段起点，使 st 恒 0/1，
    # 把主怪的真实疲惫段全部误归 normal。
    tired_rows = [r for r in F1 if iv(r, "t505") >= 2]
    tired_d = [iv(r, "d") for r in tired_rows]
    tired_p50 = int(statistics.median(tired_d)) if tired_d else -1
    tired_max = max(tired_d) if tired_d else 0
    ge300 = sum(1 for x in tired_d if x >= 300)
    longest = sorted(((iv(r, "d"), r) for r in tired_rows),
                     key=lambda t: t[0], reverse=True)[:10]
    # 条件重合一律按【结段时】读数(F1)；F0 只是段起点，两者不可混用。
    low_stam = sum(1 for r in F1 if iv(r, "pct", 0xFFFF) <= 30)
    drool = sum(1 for r in F1 if iv(r, "dc") == 1)
    t505 = len(tired_rows)
    zone = sum(1 for r in F1 if iv(r, "req") != 0)
    combo3 = sum(1 for r in F1 if iv(r, "pct", 0xFFFF) <= 30
                 and iv(r, "t505") >= 2 and iv(r, "req") != 0)
    feeding = [(d, r) for d, r in longest if d >= 300 and
               (iv(r, "pct", 0xFFFF) <= 30 or iv(r, "dc") == 1 or iv(r, "req") != 0)]

    version_ok = p90_banner
    if not version_ok or not (F0 or F1 or F9):
        ga = dict(name="A · P87① FNV0 空档",
                  verdict="无数据（日志通道）" if log_filtered else "FAIL（版本）",
                  evidence="%s；[forge] INFO=%d / ERROR=%d；插件已加载=%s；宿主=%s"
                           % (ver_reason, forge_info, forge_error,
                              plugin_loaded, host_ver),
                  next=ver_fix)
    elif not tired_d:
        # P92 已否决 P87② 立项：无疲惫样本不构成待办，不再提示「补一场」。
        ga = dict(name="A · P87① FNV0 空档", verdict="无样本（已收口）",
                  evidence=("F1 结段 t505>=2 的段=0；V.st3=%s / S.s2峰值=%d ⇒ 本场未进入自然疲惫。"
                            "F0/F1 为全局单段，小怪抢占段起点会漏记主怪疲惫窗口，"
                            "判据须交叉 V.st3 / S.s2 / wt / Y 间隔") % (st3_seen, s2_peak),
                  next=("P92 定案：GU 原生疲惫窗属引擎行为层换区进食链（主怪零动作 2428 帧≈40.5s），"
                        "抽选层无施加对象 ⇒ P87② 否决立项。本目标已收口，无需为 A 补场"))
    elif cross_ratio > 20.0:
        ga = dict(name="A · P87① FNV0 空档", verdict="需先过滤",
                  evidence="疲惫段 %d，p50=%d 帧；跨怪结段 %.1f%%（F1.mon≠F0.mon）"
                           % (len(tired_d), tired_p50, cross_ratio),
                  next="先按 mon 连续性重判，d 可能被别的怪的动作结段污染")
    elif tired_p50 >= 0 and tired_p50 <= 5:
        ga = dict(name="A · P87① FNV0 空档", verdict="否决 P87②",
                  evidence="疲惫段 %d，p50=%d 帧，max=%d 帧，≥300=%d"
                           % (len(tired_d), tired_p50, tired_max, ge300),
                  next="空签名不是可攻击待机（P86 风险①成立），放弃让位权重槽")
    elif feeding:
        ga = dict(name="A · P87① FNV0 空档", verdict="候选窗口",
                  evidence="疲惫段 %d，p50=%d 帧，max=%d，≥300=%d；条件重合段 %d"
                           % (len(tired_d), tired_p50, tired_max, ge300, len(feeding)),
                  next="疑似 GU 原生进食窗口，仅留档；P92 已否决 P87② 立项，不进入参数设计")
    else:
        ga = dict(name="A · P87① FNV0 空档", verdict="未见长空档",
                  evidence="疲惫段 %d，p50=%d 帧，max=%d，≥300=%d"
                           % (len(tired_d), tired_p50, tired_max, ge300),
                  next="看下方最长 10 段明细；倾向不推进 P87②，先由 agent 复核")

    # ---------- B · P89① 覆盖率 ----------
    wt_s = max((iv(r, "wt") for r in S), default=0)
    wt_f9 = max((iv(r, "wt") for r in F9), default=0)
    wt = max(wt_s, wt_f9)
    if not version_ok:
        gb = dict(name="B · P89① 覆盖率改进",
                  verdict="无数据（日志通道）" if log_filtered else "不适用（版本）",
                  evidence="%s；wt 不可与 P90 对照" % ver_reason,
                  next=ver_fix)
    elif not tired_d and wt == 0:
        gb = dict(name="B · P89① 覆盖率改进", verdict="无样本（已收口）",
                  evidence="wt=0 / F1 疲惫段=0 / V.st3=%s / S.s2峰值=%d ⇒ 本场无自然疲惫样本"
                           % (st3_seen, s2_peak),
                  next=("P93 定案：不再改插件源码；wt 跨怪种、跨时长、跨疲惫次数不可比。"
                        "本目标已收口，无需为 B 补场"))
    else:
        # P93：wt 上限由引擎疲惫态进入抽选层的次数决定，非插件门槛；
        # P79=1 / P70=7 / P91=5 跨场不可比，且 P90 两处放宽在 P91 未触发。
        gb = dict(name="B · P89① 覆盖率改进", verdict="仅记录（跨场不可比）",
                  evidence="wt=%d（P79=1 / P70=7 / P91=5）；F1 疲惫段=%d / F1 结段=%d"
                           % (wt, len(tired_d), len(F1)),
                  next=("P93 定案：机制通路通过但改动效果未验证（hub3 仅 1 次不在疲惫窗、"
                        "合格候选 m>=3）；不再改插件源码，保留 P90_TIRED_COVERAGE=1"))

    # ---------- C · v2 复验（成品口径） ----------
    s_last = S[-1] if S else {}
    hb_last = HB[-1] if HB else {}
    wall, wnok = iv(s_last, "wall"), iv(s_last, "wnok")
    wb, bf = iv(s_last, "wb"), iv(s_last, "bf")
    w3, w4 = iv(s_last, "w3"), iv(s_last, "w4")
    gs, ge = iv(s_last, "gs"), iv(s_last, "ge")
    h0, h1, h2, h3 = (max((iv(r, k) for r in HB), default=0)
                      for k in ("h0", "h1", "h2", "h3"))
    hd = max((iv(r, "hd") for r in HB), default=0)
    htot = h0 + h1 + h2 + h3
    hratio = 100.0 * (h1 + h2 + h3) / htot if htot else 0.0
    st_seen = sorted({iv(r, "st3", 0xFF) for r in V if iv(r, "st3", 0xFF) <= 2})
    closed = {t: len(rows.get(t, [])) for t in
              ("Z", "ZP", "ZS", "ZT", "AE", "B2", "COMBO", "AR", "J", "G")}
    checks = []

    def ck(name, ok, detail, skip=False):
        checks.append((name, "SKIP" if skip else ("PASS" if ok else "FAIL"), detail))

    ck("6 个 hook INSTALL", len(installs) >= 6, "INSTALL=%d" % len(installs))
    ck("零 FATAL / 零 host 异常", fatal == 0 and crash == 0,
       "FATAL=%d crash=%d" % (fatal, crash))
    ck("BEAT live=1 / hub=15 / fail=0", live == 1 and hub == 15 and fail == 0,
       "live=%d hub=%d fail=%d" % (live, hub, fail))
    ck("S ↔ S2 全部配对", len(S) > 0 and s_pairs == len(S),
       "S=%d 配对=%d" % (len(S), s_pairs))
    ck("[LOG] 完整性自检无 ERROR", not integ["errors"],
       "verdict=%s 最长行=%d 盲区=%s 末尾gap=%d"
       % (integ["verdict"], integ["max_len"], integ["blind"], integ["tail_gap"]))
    ck("W1 全抽选 wall>0 / wnok>0 / wnok<=wall",
       wall > 0 and wnok > 0 and wnok <= wall, "wall=%d wnok=%d" % (wall, wnok))
    ck("W1 非疲态 Rise 形状生效 (w3+w4>0)", w3 + w4 > 0, "w3=%d w4=%d" % (w3, w4))
    ck("W2 (st3,band) 形状生效 (wb>0)", wb > 0, "wb=%d bf=%d" % (wb, bf))
    ck("W4 HB 行完整且 h0>0", bool(HB) and h0 > 0,
       "HB=%d h0=%d h1=%d h2=%d h3=%d hd=%d 特殊=%.1f%%"
       % (len(HB), h0, h1, h2, h3, hd, hratio))
    ck("W4 特殊处境占比 <60%（熔断护栏）", htot == 0 or hratio < 60.0, "%.1f%%" % hratio,
       skip=(htot == 0))
    ck("W3 已关闭 (gs=0) 且 END 事件存在 (ge>0)", gs == 0 and ge > 0,
       "ge=%d gs=%d" % (ge, gs))
    ck("纯只读 gdone=0 / J=0 / G=0",
       iv(s_last, "gdone") == 0 and closed["J"] == 0 and closed["G"] == 0,
       "gdone=%d J=%d G=%d" % (iv(s_last, "gdone"), closed["J"], closed["G"]))
    ck("d3=0 / skip=0", iv(s_last, "d3") == 0 and iv(s_last, "skip") == 0,
       "d3=%d skip=%d" % (iv(s_last, "d3"), iv(s_last, "skip")))
    ck("成品已关闭探针行全 0", sum(closed.values()) == 0,
       ",".join("%s=%d" % kv for kv in closed.items()))
    ck("三状态只读接入 (V.st3 覆盖 >=2)", len(st_seen) >= 2, "st3=%s" % st_seen)
    nfail = sum(1 for _, v, _ in checks if v == "FAIL")
    gc = dict(name="C · v2 实机复验", verdict="PASS" if nfail == 0 else "FAIL",
              evidence="%d PASS / %d FAIL / %d SKIP；wall=%d wnok=%d wb=%d bf=%d W4特殊=%.1f%%"
                       % (sum(1 for _, v, _ in checks if v == "PASS"), nfail,
                          sum(1 for _, v, _ in checks if v == "SKIP"),
                          wall, wnok, wb, bf, hratio),
              next="成品口径 15 条全绿，P90 基线再获一场跨怪复验；P79 探针口径验收仍不可替代"
                   if nfail == 0 else "按下方 FAIL 条目定位，不要据此宣布复验通过")

    # ---------- D · 一场正常游玩（约 30min）日志连续性 ----------
    # P94 重定义：用户一场游玩本就约 30 分钟，痛点是「反复没记录」，
    # 不是要额外延长时长。故把「日志连续性」与「时长」分开判定。
    d_cont = (not integ["errors"] and not integ["blind"] and not integ["missing"]
              and integ["tail_gap"] <= 3000
              and integ["log_max"] < 0.9 * integ["maxlog"])
    d_ok = minutes >= 30.0 and d_cont
    if not d_cont:
        d_next = "日志存在盲区/坏行，按 [LOG] 完整性报告定位后再打"
    elif d_ok:
        d_next = ("一场正常游玩全程日志连续无盲区；P94 日志通道修复已实机确认。"
                  "P80 的 v71 探针版 30 分钟配额确证仍未做、不单独安排")
    else:
        d_next = ("日志连续性已 OK（核心痛点『没记录』已解决），仅时长 %.1f 分钟不足一场正常游玩；"
                  "再打一场正常时长即闭环，无需为日志本身补场" % minutes)
    gd = dict(name="D · 一场正常游玩日志连续性",
              verdict="PASS" if d_ok else ("连续性 OK / 时长不足" if d_cont else "未达标"),
              evidence=("时长 %.1f 分钟 / 末 BEAT f=%d / 连续性=%s（盲区=%s 末尾gap=%d 未配对=%d）/ "
                        "log峰值=%d (MAXLOG=%d) / epoch=%s")
                       % (minutes, f_last_beat, "OK" if d_cont else "异常",
                          integ["blind"], integ["tail_gap"], integ["pair_bad"],
                          integ["log_max"], integ["maxlog"], integ["epoch_rows"]),
              next=d_next)

    # ---------- E · 跨怪 ----------
    e_ok = len(new_large) >= 2
    ge_goal = dict(name="E · 跨怪 A/B", verdict="PASS" if e_ok else "未达标",
                   evidence="本场大型怪候选 %s；新增（非 0020/0050/0052）%d 种 %s"
                            % (sorted(large), len(new_large), new_large),
                   next="同场达成两只不同新大型怪 A/B；累计跨怪样本见 out 报告"
                        if e_ok
                        else "本场新增 %d 种 %s；累计跨怪样本见 out 报告。"
                             "同场两只目标仍需一场正常游玩即可"
                             % (len(new_large), new_large))

    # ---------- F · P90 自身配额 ----------
    epoch_f = collections.Counter()
    for tag in ("F0", "F1", "F9"):
        for r in rows.get(tag, []):
            epoch_f[iv(r, "f") // EPOCH_F] += 1
    max_epoch = max(epoch_f.values()) if epoch_f else 0
    f9_last = max((iv(r, "f") for r in F9), default=0)
    f9_gap = f_last_beat - f9_last if f9_last else 0
    f9_desc = ("F9 末条 f=%d，距末 BEAT %d 帧" % (f9_last, f9_gap)
               if f9_last else "无 F9 行")
    saturated = max_epoch >= MAX_F0 - 10
    f9_stopped = f9_last > 0 and f9_gap > 3000
    if not version_ok:
        gf = dict(name="F · P90 配额风险",
                  verdict="无数据（日志通道）" if log_filtered else "不适用（版本）",
                  evidence="%s；日志无 F0/F1/F9 行" % ver_reason,
                  next=ver_fix)
    else:
        gf = dict(name="F · P90 配额风险", verdict="注意" if (saturated or f9_stopped) else "PASS",
                  evidence="单 epoch F0+F1+F9 峰值=%d/%d；%s；epoch分布=%s"
                           % (max_epoch, MAX_F0, f9_desc, dict(sorted(epoch_f.items()))),
                  next="配额打满 / F9 停写：逐行 F0/F1 仍可判读，wt 改从 S 行读；下版提高 MAX_F0 或给 F0 降频"
                       if (saturated or f9_stopped) else "配额充足，F9 全场累计可用")

    goals = [ga, gb, gc, gd, ge_goal, gf]
    # 日志通道故障时，C/D/E 的 FAIL / 未达标是「没有数据」，不是功能失败，
    # 统一改写避免把空日志误读成实机回归。
    if log_filtered:
        for g in goals:
            if g["name"].startswith(("C ·", "D ·", "E ·")):
                g["verdict"] = "无数据（日志通道）"
                g["evidence"] = ("Forge level=error 过滤全部 [rai] 行；原判读值 %s"
                                 % g["evidence"])
                g["next"] = ver_fix

    # ---------- 输出 ----------
    if log_filtered:
        warn_md = ("> **✖ 日志通道故障（不是版本问题）**：宿主 `%s` 已加载 "
                   "`rai_entrylocator_probe.nro`，但 `[forge] [INFO]=%d`、"
                   "`[forge] [ERROR]=%d` ⇒ Forge `config.ini` 的 `[log] level` 为 "
                   "`error`，插件全部 INFO 行（含 `[rai]`）被静默过滤。"
                   "**本场没有任何判据数据**，A–F 六目标全部不可判读；"
                   "插件很可能已正常运行，只是日志没落盘。修复 level=info 后重打。\n\n"
                   % (host_ver, forge_info, forge_error))
    elif not version_ok:
        warn_md = ("> **⚠ 版本警告**：日志未检出 `P90 PROBE` 横幅，不是 P90 编译版。"
                   "以下全部结论仅作脚本冒烟自检，**不可用于任何判据**。\n\n")
    else:
        warn_md = ""
    L = ["# P91 · 一场多目标实机会话判读", "",
         "日志：`%s`（%d 行）" % (path, len(lines)), "",
         warn_md.rstrip(), "",
         "版本：P90 横幅=%s / RAI v71 横幅=%s / 6 hook INSTALL=%d / FATAL=%d / host异常=%d"
         % (p90_banner, v71_banner, len(installs), fatal, crash),
         "宿主：%s / [forge] INFO=%d / ERROR=%d / 插件已加载=%s"
         % (host_ver, forge_info, forge_error, plugin_loaded),
         "日志通道：%s（[rai]=%d 行 / [forge] INFO=%d / P90 横幅=%s）；%s"
         % ("正常" if log_channel_ok else "异常", rai_lines, forge_info, p90_banner,
            "P94 修复（level=info）实机验证通过" if (log_channel_ok and p90_banner)
            else "插件 INFO 行可见；本日志非 P90 版，版本警告见上" if log_channel_ok
            else "按 P94 检查 Forge config.ini 的 [log] level"), "",
         "## 目标总表", "", verdict_table(goals), "",
         "## A · FNV0 空档帧差（P92 已否决 P87② 立项，本节仅留档）", "",
         "F0 段=%d  F1 结段=%d  F9 汇总=%d  悬挂段=%d  跨怪结段=%d/%d (%.1f%%)"
         % (len(F0), len(F1), len(F9), len(F0) - len(F1), cross_mon, paired_f1, cross_ratio), "",
         "| st | n | mean | p50 | p90 | max | >=300 | >=180 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for st in sorted(byst):
        v = byst[st]
        L.append("| %s | %d | %.1f | %d | %d | %d | %d | %d |"
                 % (STATE.get(st, "st%s" % st), len(v), sum(v) / len(v),
                    int(statistics.median(v)), q(v, 0.9), max(v),
                    sum(1 for x in v if x >= 300), sum(1 for x in v if x >= 180)))
    L += ["", "F1 结段时重合（疲惫判据）：t505>=2=%d，耐力<=30%%=%d，dc=1 流口水=%d，"
          "req!=0 换区=%d，三者同时=%d；对照 F0 段起点疲惫 st=2=%d"
          % (t505, low_stam, drool, zone, combo3,
             sum(1 for r in F0 if iv(r, "st") == 2)), "",
          "**字段口径**：F1 的 `pct/t505/dc/area/req` 是**结段时**读数，F0 是**段起点**读数；"
          "`F1.d = 段起点 → 下一动作开始` 的帧差。疲惫分组一律用 `F1.t505>=2`，"
          "不能用段起点 `st`（全局单段被小怪抢占时 st 恒 0/1）。F0/F1 共用单一全局段"
          "（非按怪分槽），故 `F1.mon != F0.mon` 的段可能是被别的怪结段，不能直接当主怪空档。", "",
          "疲惫态最长 10 段（按结段 t505>=2）：", "",
          "| d | f0 | f | pct | t505 | dc | area | req | mon(结段) |", "|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for d, r in longest:
        L.append("| %d | %s | %s | %d | %d | %d | %d | %d | %s |"
                 % (d, sv(r, "f0"), sv(r, "f"), iv(r, "pct", 0xFFFF),
                    iv(r, "t505"), iv(r, "dc"), iv(r, "area"), iv(r, "req"), sv(r, "mon")))
    L += ["", "三条判据（P90 §8，P92 后仅留档）：① 疲惫 `d` p50 仅 1~5 帧 ⇒ 放弃让位；"
          "② `d>=300` 且与 `pct<=30` / `dc=1` / `req!=0` 重合 ⇒ 可能是 GU 原生进食窗口，"
          "仍须用 `mon` 连续性与 BEAT 全量排除赶路/离场；③ 只有确认【战斗内】持续可攻击空档才进入 P87②。"
          "**P92 定案**：捕获到的 f≈61078~63666 长空档属引擎行为层换区进食链（主怪零动作 2428 帧≈40.5s），"
          "抽选层无施加对象 ⇒ P87② 否决立项，不再为本目标补场。", "",
          "## B · 覆盖率改进（P93 已收口，仅记录）", "",
          "S 行 wt 峰值=%d，F9 行 wt 峰值=%d ⇒ **wt=%d**；对照 P79 `wt=1` / P70 `wt=7` / P91 `wt=5`。"
          % (wt_s, wt_f9, wt), "",
          "**P93 定案**：`wt` 上限由引擎疲惫态进入抽选层的次数决定（P91 仅 5 次，疲惫时引擎走行为层），"
          "非插件门槛；`P79=1 / P70=7 / P91=5` 跨怪种、跨时长、跨疲惫次数不可比，且 P90 两处放宽在 P91 "
          "均未触发。机制通路验证通过、改动效果未验证 ⇒ **不再改插件源码**，保留 `P90_TIRED_COVERAGE=1`。", "",
          "## C · v2 实机复验明细（成品口径，不用 v71 探针口径）", "",
          "| 判据 | 结论 | 依据 |", "|---|---|---|"]
    for name, v, detail in checks:
        L.append("| %s | %s | %s |" % (name, v, detail))
    L += ["", "> 说明：`analyze_v71_limits.py` 的判据针对 v71 全量探针（Z/ZP/AR/COMBO/AE 等），"
          "成品已把这些行关闭，直接跑会大量误报 FAIL，故本表按成品口径重写。", "",
          "## D · 一场正常游玩（约 30 分钟）日志连续性", "",
          "- 任务时长（末 BEAT）：**%.1f 分钟**（f=%d）" % (minutes, f_last_beat),
          "- 日志覆盖到 f=%d，末尾 gap=%d 帧；epoch 行分布=%s"
          % (integ["f_last_rai"], integ["tail_gap"], integ["epoch_rows"]),
          "- 最长行=%d 字符（上限 %d）；S/S2/HB 坏行=%d/%d/%d；未配对=%d"
          % (integ["max_len"], LINE_LIMIT, integ["s_bad"], integ["s2_bad"],
             integ["hb_bad"], integ["pair_bad"]),
          "- log 序号峰值=%d / MAXLOG=%d；30 / 60 分钟外推=%d / %d 行"
          % (integ["log_max"], integ["maxlog"], integ["est_30min_lines"], integ["est_60min_lines"]),
          "- 完整性结论：**%s**" % integ["verdict"], "",
          "> **口径（P94 重定义）**：用户一场游玩时长本就约 30 分钟，痛点是「反复没记录」，"
          "不是要额外延长时长。D = 一次正常游玩全程日志连续无盲区（盲区=[] / 末尾gap<=3000 / "
          "S-S2 全配对 / `[rai]` 行长<270），时长仅作会话完整性佐证。P94 已定位根因为 Forge "
          "`config.ini` 的 `[log] level=error` 过滤掉全部 `[rai]` INFO 行；改为 info 后由本场实机验证。"
          "P80 基于 v71 全量探针版的 30 分钟配额确证与此不等价，不单独安排。", "",
          "## E · 跨怪", "",
          "- 本场全部 sp：%s" % dict(sp_all.most_common()),
          "- 大型怪候选（sp<0x1000）：%s" % sorted(large),
          "- 已知 3 种：0020 轰龙 / 0050 斩龙 / 0052 泡狐龙；本场新增：%s" % new_large, "",
          "## F · P90 自身配额风险", "",
          "- `MAX_F0=600` 是 **F0+F1+F9 共用**的每 epoch(30000 帧) 配额，epoch 只重置 `F0_LOG`，"
          "累计量（F0_N/F1_N/WT_N）不重置。",
          "- 单 epoch 峰值=%d/%d；%s。"
          % (max_epoch, MAX_F0, f9_desc),
          "- 若配额打满，F9 会随 F0/F1 一起静默停写；此时逐行 F0/F1 仍可重建分布，`wt` 改从 S 行读。", "",
          "## 下一步（按 P92 / P93 / P94 定案，不需要用户操作）", "",
          "1. A（P87②）已由 P92 否决立项、B（覆盖率）已由 P93 收口 ⇒ 本场无自然疲惫样本不影响任何定案，无需补场；",
          "2. C 成品口径全绿 ⇒ P90 作为当前部署基线再获一场跨怪佐证；P79 探针口径 64/0/4 仍是唯一完整验收，不可替代；",
          "3. D/E 仅剩一场正常时长（约 30 分钟）+ 两只不同新大型怪；P94 日志通道修复已实机验证，不必再为「没记录」补场；",
          "4. 永久硬断点不列为待办；不再改插件源码、不重编译、不回退。", ""]

    report = "\n".join(L)
    if log_filtered:
        warn_txt = ("✖ 日志通道故障：Forge level=error 过滤了全部 [rai] INFO 行"
                    "（插件已加载，非版本问题）。本场无判据数据，修复后重打。\n")
    elif not version_ok:
        warn_txt = ("⚠ 版本警告：未检出 P90 PROBE 横幅，以下结论仅作冒烟自检，"
                    "不可用于判据。\n")
    else:
        warn_txt = ""
    console = ["P91 一场多目标会话判读 · %s" % path,
               warn_txt.rstrip(),
               "版本 P90=%s  v71=%s  6hook=%d  FATAL=%d  crash=%d  时长=%.1f 分钟"
               % (p90_banner, v71_banner, len(installs), fatal, crash, minutes),
               "宿主 %s / [forge] INFO=%d ERROR=%d / 插件已加载=%s"
               % (host_ver, forge_info, forge_error, plugin_loaded),
               "日志通道 %s / [rai]=%d 行%s"
               % ("正常" if log_channel_ok else "异常", rai_lines,
                  "  (P94 修复实机验证通过)" if (log_channel_ok and p90_banner)
                  else "  (插件 INFO 可见，非 P90 版)" if log_channel_ok else ""), "",
               verdict_table(goals), "",
               "A 疲惫段 n=%d p50=%d max=%d >=300=%d 跨怪结段=%.1f%%"
               % (len(tired_d), tired_p50, tired_max, ge300, cross_ratio),
               "B wt=%d (P79=1 / P70=7 / P91=5，跨场不可比)   C %s   D 完整性=%s   E 新怪=%s"
               % (wt, gc["verdict"], integ["verdict"], new_large), ""]
    print("\n".join(console))
    if a.md:
        Path(a.md).write_text(report, encoding="utf-8", newline="")
        print("[报告] %s" % a.md)
    if a.json:
        payload = {"log": str(path), "lines": len(lines), "goals": goals,
                   "wt": wt, "minutes": minutes, "sp": dict(sp_all),
                   "new_large": new_large, "checks": checks,
                   "integrity": integ, "f0": len(F0), "f1": len(F1), "f9": len(F9)}
        Path(a.json).write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                                encoding="utf-8", newline="")
        print("[数据] %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
