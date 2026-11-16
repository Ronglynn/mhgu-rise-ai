# -*- coding: utf-8 -*-
"""v57 判读：W1 全抽选 + 纯只读发布配置（v56~v50 日志可降级）。

v57 = RAI v57 W1-ALL-PICKS + READONLY RELEASE PROFILE
  - rise_weight_pick() 从「仅否决重抽」扩展到每次主轨抽选
  - DRAIN_ENABLE=0 / PROFILE_RELEASE=1 ⇒ 零强制、零写入、无 R/W/J/G 高频行
  - S 行新增 wall(全抽选尝试) / wnok(成功应用)
验收核心：wall>0 / wnok>0 / wnok<=wall / w3+w4>0 / 发布版无 J·G·R·W 行。

用法: python analyze_v57_release.py <log>
"""
import re
import sys
import collections

INT = {
    "f", "n", "nc", "ret", "d", "ki", "rd", "b1", "ph", "sw", "sw2", "nr",
    "st3", "vd", "wm", "wk", "live", "log", "md", "p5", "a", "sel", "ok",
    "e1", "e0", "r1", "r0", "n1", "n0", "v1", "v0", "p2",
    "s0", "s1", "s2", "sv0", "sv1", "sv2", "w3", "w4", "wt", "d3", "skip",
    "gac", "gsum", "gmax", "gnz", "amx", "anf", "anr", "gdone", "gf",
    "wall", "wnok", "hub", "peak", "m", "m1", "m0c", "m0e", "x", "q",
    "fail", "rep", "v", "beg", "begf", "noalt",
}


def parse_line(line):
    m = re.search(r"\[rai\] ([A-Z]+) (.*)$", line)
    if not m:
        return None, None
    tag, body = m.group(1), m.group(2)
    d = {}
    for k, v in re.findall(r"(\w+)=(\S+)", body):
        if k in INT:
            try:
                d[k] = int(v, 0) if v.startswith("0x") else int(v)
            except ValueError:
                d[k] = v
        else:
            d[k] = v
    return tag, d


def main(path):
    lines = open(path, "r", encoding="utf-8", errors="replace").read().splitlines()
    rows = collections.defaultdict(list)
    for l in lines:
        tag, d = parse_line(l)
        if tag and d:
            rows[tag].append(d)

    V, S, B = rows["V"], rows["S"], rows["BEAT"]
    J, G, R, W = rows["J"], rows["G"], rows["R"], rows["W"]
    is_v57 = any("RAI v57" in l for l in lines)
    banner = next((l.strip() for l in lines if "RAI v57" in l), "(旧日志)")
    fatal = sum(1 for l in lines if "FATAL" in l)
    crash = [l for l in lines
             if "c0000005" in l or "*** exception" in l or "host backtrace" in l]
    installs = [l.strip() for l in lines if "[rai] INSTALL h_" in l]

    print("=== v57 W1 全抽选 / 纯只读发布配置 判读 ===")
    print("日志: %s" % path)
    print("banner: %s" % banner[:120])
    print("版本=%s  V=%d S=%d BEAT=%d J=%d G=%d R=%d W=%d  FATAL=%d" %
          ("v57" if is_v57 else "旧日志(降级)", len(V), len(S), len(B),
           len(J), len(G), len(R), len(W), fatal))
    for l in installs[:6]:
        print("  " + l[:120])

    checks, skips = [], []

    def add(name, ok, detail):
        checks.append((name, bool(ok), detail))
        print("  [%s] %-44s %s" % ("PASS" if ok else "FAIL", name, detail))

    def skip(name, detail):
        skips.append((name, detail))
        print("  [SKIP] %-44s %s" % (name, detail))

    # --- 基础健康（所有版本通用）---
    add("零 FATAL", fatal == 0, "FATAL=%d" % fatal)
    add("零 host 异常（c0000005）", len(crash) == 0, "异常=%d" % len(crash))
    # v50 时代只有 5 个 hook（h_stamina 自 v55 起才有），降级时按版本要求。
    need = 6 if is_v57 else 5
    add("hook INSTALL 数量符合版本（%d）" % need,
        len(installs) >= need, "INSTALL=%d" % len(installs))
    if is_v57:
        add("h_stamina @0xBD260 已安装",
            any("INSTALL h_stamina" in l for l in lines), "首字核对见 INSTALL 行")
    else:
        skip("h_stamina（v55+ 才有）", "旧版本无此 hook，降级不检查")
    if B:
        add("live=1（自检未熔断）", B[-1].get("live") == 1,
            "live=%s" % B[-1].get("live"))
        add("hub=15", B[-1].get("hub") == 15, "hub=%s" % B[-1].get("hub"))
        add("零抽选解析失败", B[-1].get("fail") == 0,
            "fail=%s" % B[-1].get("fail"))
    else:
        add("BEAT 行存在", False, "BEAT=0")

    if not is_v57:
        skip("v57 发布版专项判据", "旧日志无 wall/wnok 字段，降级仅做基础健康检查")
    else:
        add("RAI v57 横幅", True, "v57 release")
        # 发布配置特征
        add("发布配置：无 R/W 高频快照行", len(R) == 0 and len(W) == 0,
            "R=%d W=%d" % (len(R), len(W)))
        add("发布配置：无强制 J/G 行", len(J) == 0 and len(G) == 0,
            "J=%d G=%d" % (len(J), len(G)))
        add("发布配置：gdone=0（无强制疲惫）",
            bool(S) and S[-1].get("gdone") == 0,
            "gdone=%s" % (S[-1].get("gdone") if S else "?"))
        # gac 是 0xA30E4 的全局调用计数（游戏自己也会调），与「强制」无关；
        # 真正的强制标志是 U 行 force=1 / J / G 行。
        u_force = sum(1 for l in lines if "[rai] U " in l and "force=1" in l)
        add("发布配置：U 行无 v48 amount 强制", u_force == 0,
            "U force=1 计数=%d" % u_force)
        # A：全抽选
        if S:
            s = S[-1]
            wall, wnok = s.get("wall"), s.get("wnok")
            add("S 行 wall/wnok 字段齐全",
                isinstance(wall, int) and isinstance(wnok, int),
                "wall=%s wnok=%s" % (wall, wnok))
            add("W1 全抽选已生效（wall>0 / wnok>0）",
                isinstance(wall, int) and isinstance(wnok, int)
                and wall > 0 and wnok > 0,
                "wall=%s wnok=%s" % (wall, wnok))
            add("成功应用不超过尝试次数（wnok<=wall）",
                isinstance(wall, int) and isinstance(wnok, int) and wnok <= wall,
                "wnok/wall=%.3f" % (wnok / wall if isinstance(wall, int)
                                    and wall else 0))
            add("Rise 形状在非疲态生效（w3+w4>0）",
                isinstance(s.get("w3"), int) and isinstance(s.get("w4"), int)
                and s["w3"] + s["w4"] > 0,
                "w3=%s w4=%s wt=%s" % (s.get("w3"), s.get("w4"), s.get("wt")))
            add("d3/skip 恒 0（v49 旋钮已移除）",
                s.get("d3") == 0 and s.get("skip") == 0,
                "d3=%s skip=%s" % (s.get("d3"), s.get("skip")))
            if isinstance(s.get("wt"), int) and s["wt"] > 0:
                add("Rise 疲惫形状已使用（wt>0）", True, "wt=%s" % s["wt"])
            else:
                skip("Rise 疲惫形状（wt）",
                     "本场无自然疲惫窗口；发布版不强制疲惫，属预期")
        else:
            add("S 行存在", False, "S=0")
        # V 行映射
        bad_st = [(v.get("f"), v.get("st3"), v.get("vd")) for v in V
                  if isinstance(v.get("st3"), int) and isinstance(v.get("vd"), int)
                  and ((v["st3"] == 2 and v["vd"] != 1)
                       or (v["st3"] in (0, 1) and v["vd"] != 2))]
        add("V 行 st3->vd 映射零违例", len(bad_st) == 0,
            "违例=%d %s" % (len(bad_st), bad_st[:3]))
        bad_wm = [(v.get("f"), v.get("wm"), v.get("wk")) for v in V
                  if isinstance(v.get("wm"), int) and isinstance(v.get("wk"), int)
                  and v["wm"] in (1, 2, 3)
                  and ((v["wm"] == 3 and v["wk"] != 3)
                       or (v["wm"] in (1, 2) and v["wk"] not in (3, 4)))]
        add("V 行 wm->wk 映射零违例", len(bad_wm) == 0,
            "违例=%d %s" % (len(bad_wm), bad_wm[:3]))

    # --- 全抽选形状分布诊断（纯输出）---
    print("\n=== W1 全抽选形状分布 ===")
    if S and is_v57:
        for s in S[::max(1, len(S) // 8)][:9]:
            print("  S f=%-7s s0=%-4s s1=%-3s s2=%-3s wall=%-6s wnok=%-6s "
                  "w3=%-4s w4=%-4s wt=%-3s" %
                  (s.get("f"), s.get("s0"), s.get("s1"), s.get("s2"),
                   s.get("wall"), s.get("wnok"), s.get("w3"), s.get("w4"),
                   s.get("wt")))
        s = S[-1]
        w3, w4, wt = s.get("w3", 0), s.get("w4", 0), s.get("wt", 0)
        tot = (w3 or 0) + (w4 or 0) + (wt or 0)
        if tot:
            print("  形状占比: 非疲 k3=%.1f%% / k4=%.1f%% / 疲惫=%.1f%%" %
                  (100.0 * (w3 or 0) / tot, 100.0 * (w4 or 0) / tot,
                   100.0 * (wt or 0) / tot))
    else:
        print("  旧日志无 wall/wnok，跳过。")

    print("\n=== 结论 ===")
    npass = sum(1 for _, ok, _ in checks if ok)
    nfail = len(checks) - npass
    print("  PASS=%d / FAIL=%d / SKIP=%d" % (npass, nfail, len(skips)))
    if is_v57:
        if nfail == 0:
            print("  -> v57 发布配置全通：零写入、零强制、R/W/J/G 高频行已消除；")
            print("     W1 已覆盖全部主轨抽选（wall/wnok>0），Rise 形状生效。")
            print("  -> 仍建议一场实机确认动作分布与连段无异常（A 改动了抽选主干）。")
        else:
            print("  -> 存在 FAIL，按上方条目定位，不要据此发布。")
    else:
        print("  -> 旧日志降级：仅基础健康检查有效。")
    print("  回退：copy 04_RiseAI\\out\\rai_stamina_drain_v56.nro 覆盖插件 nro")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "04_RiseAI/out/sim_v57_smoke.txt")
