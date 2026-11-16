#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P90 合并探针版实机日志判读（只读）。

用法:
    python tools/analyze_p90_f0.py [日志文件路径]

默认读 02_Workspace/game_p54.txt。输出 FNV0 空签名段 -> 下一动作开始的
帧差分布、按状态分组、疲惫/换区/耐力重合、日志完整性。判据口径见
out/P90_capability_inventory_and_now_doable.md §8 与 out/P87_*.md §4.2。
"""
import sys
import os
import re
import statistics
import collections

DEFAULT = r"D:\MHGU mod maker\02_Workspace\game_p54.txt"
TAG = {"F0": "[rai] F0 ", "F1": "[rai] F1 ", "F9": "[rai] F9 "}


def kv(line):
    return {k: v for k, v in re.findall(r"(\w+)=(\S+)", line)}


def num(d, key, default=0):
    try:
        return int(d.get(key, default))
    except ValueError:
        return default


def pct(vals, q):
    if not vals:
        return 0
    s = sorted(vals)
    return s[min(len(s) - 1, int(len(s) * q))]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    if not os.path.isfile(path):
        print("日志文件不存在:", path)
        return 1
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()

    f0 = [kv(l) for l in lines if TAG["F0"] in l]
    f1 = [kv(l) for l in lines if TAG["F1"] in l]
    f9 = [kv(l) for l in lines if TAG["F9"] in l]
    # 修正(P92)：宿主自身行（[cheats] 加载列表、[forge] [ERROR] [art-ext] 诊断）
    # 不受插件控制，且可长达 368 字符；P71 硬判据只约束插件输出的 [rai] 行。
    rai_lines = [l for l in lines if "[rai]" in l]
    long_lines = sum(1 for l in rai_lines if len(l) >= 265)
    rai_max = max((len(l) for l in rai_lines), default=0)
    fatal = sum(1 for l in lines if "FATAL" in l)

    print("P90 FNV0 空签名段判读 ·", path)
    print("总行数=%d  [rai]行=%d  F0=%d  F1=%d  F9=%d  [rai]行长>=265=%d (最长%d)  FATAL=%d"
          % (len(lines), len(rai_lines), len(f0), len(f1), len(f9),
             long_lines, rai_max, fatal))
    if not f0 and not f1:
        info_n = sum(1 for l in lines if "[forge] [INFO]" in l)
        err_n = sum(1 for l in lines if "[forge] [ERROR]" in l)
        loaded = any("loaded rai_entrylocator_probe.nro" in l for l in lines)
        if loaded and info_n == 0 and err_n > 0:
            print("✖ 日志通道故障（非版本问题）：插件已加载，但 [forge] [INFO]=0、"
                  "[forge] [ERROR]=%d ⇒ Forge config.ini 的 [log] level=error "
                  "过滤了全部 [rai] INFO 行。" % err_n)
            print("  修复：level 改为 info（9_P91_oneshot.bat 前置自动修正）后重打；"
                  "本场无判据数据。")
        else:
            print("未发现 F0/F1 行：确认已加载 P90 NRO (md5 0ab6cbec…) "
                  "且日志来自 9_P91_oneshot.bat / 7_P54 抓日志脚本。")
        return 0

    # ---- 帧差按【段起点】状态分组（仅作分布参考，不能当疲惫判据）----
    print("\n=== F1 帧差 d = FNV0 段起点 -> 下一动作开始 ===")
    print("  st 为【段起点】mon_state；疲惫判据请看下方按 F1.t505 的分组")
    print("%-14s %6s %8s %8s %8s %8s %8s %8s"
          % ("分组", "n", "mean", "p50", "p90", "max", ">=300", ">=180"))
    byst = collections.defaultdict(list)
    for r in f1:
        byst[num(r, "st", 9)].append(num(r, "d"))
    for st in sorted(byst):
        v = byst[st]
        label = {0: "normal", 1: "anger", 2: "tired"}.get(st, "unknown") + "(起点)"
        print("%-14s %6d %8.1f %8.0f %8d %8d %8d %8d"
              % (label, len(v), sum(v) / len(v), statistics.median(v), pct(v, 0.9),
                 max(v), sum(1 for x in v if x >= 300), sum(1 for x in v if x >= 180)))
    # 修正(P92)：F1 的 t505/pct/dc/area/req 是【结段时】读数；疲惫段必须按此筛。
    tired_rows = [r for r in f1 if num(r, "t505") >= 2]
    tv = [num(r, "d") for r in tired_rows]
    if tv:
        print("%-14s %6d %8.1f %8.0f %8d %8d %8d %8d"
              % ("tired(结段)", len(tv), sum(tv) / len(tv), statistics.median(tv),
                 pct(tv, 0.9), max(tv), sum(1 for x in tv if x >= 300),
                 sum(1 for x in tv if x >= 180)))
    else:
        print("%-14s %6d  (需交叉 V.st3 / S.s2 / wt / Y 间隔确认是否进过自然疲惫)"
              % ("tired(结段)", 0))

    # ---- 疲惫段明细（最长 10，按结段 t505>=2）----
    tired = sorted(((num(r, "d"), r) for r in tired_rows), reverse=True)
    if tired:
        print("\n=== 疲惫态最长 10 段（F1 结段 t505>=2）===")
        print("%8s %8s %7s %6s %6s %6s %6s %6s %10s"
              % ("d", "f", "f0", "pct", "t505", "dc", "area", "req", "mon"))
        for d, r in tired[:10]:
            print("%8d %8d %7d %6d %6d %6d %6d %6d %10s"
                  % (d, num(r, "f"), num(r, "f0"), num(r, "pct"),
                     num(r, "t505"), num(r, "dc"), num(r, "area"), num(r, "req"),
                     r.get("mon", "?")))

    # ---- 段起点 / 结段两套读数分列 ----
    print("\n=== 条件重合（F0=段起点 / F1=结段时，不可混用）===")
    f0_low = sum(1 for r in f0 if num(r, "pct", 0xFFFF) <= 30)
    f0_drool = sum(1 for r in f0 if num(r, "dc") == 1)
    f0_t505 = sum(1 for r in f0 if num(r, "t505") >= 2)
    f0_zone = sum(1 for r in f0 if num(r, "req") != 0 or num(r, "hub") == 3)
    f0_st2 = sum(1 for r in f0 if num(r, "st") == 2)
    print("  F0 段数=%d  起点 st=2=%d  起点耐力<=30%%=%d  起点 dc=1=%d  起点 t505>=2=%d  起点换区/脱战=%d"
          % (len(f0), f0_st2, f0_low, f0_drool, f0_t505, f0_zone))
    f1_low = sum(1 for r in f1 if num(r, "pct", 0xFFFF) <= 30)
    f1_drool = sum(1 for r in f1 if num(r, "dc") == 1)
    f1_zone = sum(1 for r in f1 if num(r, "req") != 0)
    combo = sum(1 for r in f1 if num(r, "pct", 0xFFFF) <= 30
                and num(r, "t505") >= 2 and num(r, "req") != 0)
    print("  F1 结段数=%d  结段 t505>=2=%d  结段耐力<=30%%=%d  结段 dc=1=%d  结段 req!=0=%d  【三者同时】=%d"
          % (len(f1), len(tired_rows), f1_low, f1_drool, f1_zone, combo))
    print("  段起点只看一次；段内命中次数在 F1.segn，累计在 F9.f0n。")
    big_f0 = sum(1 for r in f0 if re.fullmatch(r"[0-9A-Fa-f]{4}", r.get("sp", ""))
                 and int(r.get("sp"), 16) < 0x1000)
    print("  F0 段起点大型怪(sp<0x1000)占比=%d/%d；全局单段被小怪抢占时 d 不代表主怪空档。"
          % (big_f0, len(f0)))

    # ---- 悬挂段与最终汇总 ----
    print("\n=== 完整性与汇总 ===")
    print("  悬挂段（F0 段数 - F1 结段数）=%d（>0 表示任务结束前未出现下一动作）"
          % (len(f0) - len(f1)))
    if f9:
        z = f9[-1]
        print("  末条 F9: f=%s f0n=%s seg=%s f1n=%s n2=%s x2=%s g2=%s wt=%s"
              % (z.get("f"), z.get("f0n"), z.get("seg"), z.get("f1n"),
                 z.get("n2"), z.get("x2"), z.get("g2"), z.get("wt")))
        print("  wt = 疲惫形状应用次数（P93 已收口，仅作记录：P79=1 / P70=7 / P91=5 跨场不可比）。")
    print("  [rai] 行 >=265 必须为 0（P71 硬判据）；FATAL 必须为 0。")
    print("\n判读要点（P92 后本节仅留档，A/B 均已收口）：")
    print("  1. 若疲惫态 d 的 p50 仅 1~5 帧 ⇒ 空签名不是可攻击待机，P86 风险①成立，放弃让位方案。")
    print("  2. 若存在 d>=300 帧段且与 pct<=30 / dc=1 / req!=0 重合 ⇒ 可能是 GU 原生进食/换区窗口，")
    print("     仍需排除换区赶路/主怪离场（用 mon 是否连续出现 + BEAT/Y 全量交叉）。")
    print("  3. **P92 已否决 P87② 立项**：实测 f≈61078~63666 长空档属引擎行为层换区进食链")
    print("     （主怪零动作 2428 帧≈40.5s），抽选层无施加对象；无自然疲惫样本无需补场。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
