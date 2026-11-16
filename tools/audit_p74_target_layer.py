#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P74 只读离线统计：距离档目标点归属的间接证据量化。

只读日志文件，不写任何文件、不改任何游戏数据。输出全部到 stdout。
用法: python audit_p74_target_layer.py [主日志路径] [归档glob目录]
依赖: 仅标准库。
"""
import glob
import math
import os
import re
import struct
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # 04_RiseAI
PROJ = os.path.dirname(ROOT)                       # 工程根
MAIN_LOG = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PROJ, "02_Workspace", "game_p54_lite.txt")
OUT_DIR = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "out")

RAI = re.compile(r"\[rai\]\s+(\w+)\s+f=(\d+)\s+(.*)$")
KV = re.compile(r"(\w+)=([0-9A-Fa-f]+)")


def f32(hexstr):
    """把 8 位十六进制原始位解成 float。"""
    try:
        return struct.unpack("<f", struct.pack("<I", int(hexstr, 16)))[0]
    except (ValueError, struct.error):
        return float("nan")


def finite(v):
    return not (math.isnan(v) or math.isinf(v))


def parse_lines(path):
    """逐行解析 [rai] 行，返回 (类型, 帧, 字段dict)。"""
    out = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = RAI.search(line)
            if not m:
                continue
            typ, fr, body = m.group(1), int(m.group(2)), m.group(3)
            d = {k: v for k, v in KV.findall(body)}
            out.append((typ, fr, d))
    return out


def quantiles(vals, ps=(0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0)):
    if not vals:
        return {}
    s = sorted(vals)
    n = len(s)
    res = {}
    for p in ps:
        idx = min(n - 1, max(0, int(round(p * (n - 1)))))
        res["p%d" % int(p * 100)] = round(s[idx], 2)
    return res


def clus_split(vals):
    """一维值排序后按最大相邻间隙切两段，给出双簇候选统计。"""
    s = sorted(vals)
    if len(s) < 4:
        return None
    gaps = [(s[i + 1] - s[i], i) for i in range(len(s) - 1)]
    gmax, gi = max(gaps)
    lo, hi = s[: gi + 1], s[gi + 1 :]
    return {
        "max_gap": round(gmax, 2),
        "gap_at": gi,
        "lo_n": len(lo), "lo_min": round(lo[0], 2), "lo_max": round(lo[-1], 2),
        "hi_n": len(hi), "hi_min": round(hi[0], 2), "hi_max": round(hi[-1], 2),
        "gap_ratio": round(gmax / max(1e-6, s[-1] - s[0]), 3),
    }


def main():
    print("=" * 78)
    print("P74 离线统计（只读） 主日志:", MAIN_LOG)
    print("=" * 78)

    # ---------- 1) 归档概览 ----------
    logs = [MAIN_LOG] + sorted(glob.glob(os.path.join(OUT_DIR, "game_p54_lite_*.txt")))
    print("\n[1] 归档日志：Z/ZP 探针覆盖情况（ZP 自 v58 才加入）")
    for p in logs:
        if not os.path.isfile(p):
            continue
        rows = parse_lines(p)
        c = Counter(t for t, _, _ in rows)
        vsp = sorted({d.get("sp", "?") for t, _, d in rows if t == "V"})
        print("  %-58s Z=%-4d ZP=%-4d AR=%-4d COMBO=%-4d V=%-4d Vsp=%s"
              % (os.path.basename(p), c["Z"], c["ZP"], c["AR"], c["COMBO"], c["V"], ",".join(vsp)))

    rows = parse_lines(MAIN_LOG)
    allc = Counter(t for t, _, _ in rows)
    print("\n[2] 主日志 [rai] 行类型计数:", dict(sorted(allc.items())))

    # ---------- 3) sp / mon 值域（判断大怪数） ----------
    print("\n[3] 实体口径：sp 值域（sp = rd16(mon+0xB5F0)，是'动作所属实体自身'的怪种/类型字，不是目标）")
    for t in ("V", "COMBO", "AR", "QX", "ZP"):
        sp = Counter(d.get("sp", "?") for tt, _, d in rows if tt == t)
        mon = {d.get("mon", "?") for tt, _, d in rows if tt == t}
        print("  %-6s sp值域=%-46s 不同mon数=%d" % (t, ",".join(sorted(sp.keys())), len(mon)))
    # 低位 sp（<0x1000）视为工程惯例里的大怪 emid
    low = sorted({d.get("sp") for t, _, d in rows if t in ("V", "COMBO", "AR")
                  and d.get("sp") and int(d["sp"], 16) < 0x1000})
    print("  ==> 低位(<0x1000)大怪怪种 sp 值域 =", low, "（跨全体 V/COMBO/AR 行）")

    # ---------- 4) ZP 几何解析 ----------
    zp = [(fr, d) for t, fr, d in rows if t == "ZP"]
    print("\n[4] ZP 几何快照：共 %d 条" % len(zp))
    recs = []
    for fr, d in zp:
        p1 = tuple(f32(d.get(k, "0")) for k in ("a30", "a34", "a38"))   # sub+0x30..0x38
        p2 = tuple(f32(d.get(k, "0")) for k in ("a40", "a44", "a48"))   # sub+0x40..0x48
        if not all(finite(x) for x in p1 + p2):
            continue
        dist = math.dist(p1, p2)
        recs.append({"f": fr, "mon": d.get("mon"), "sub": d.get("sub"),
                     "p1": p1, "p2": p2, "d": dist,
                     "e0": f32(d.get("e0", "0")), "hd": d.get("hd")})
    print("  可解为有限 f32 的条数 =", len(recs))

    bymon = defaultdict(list)
    for r in recs:
        bymon[r["mon"]].append(r)
    print("  不同 mon 数 =", len(bymon))
    for mon, rs in sorted(bymon.items(), key=lambda kv: -len(kv[1])):
        p1u = {tuple(round(v, 3) for v in r["p1"]) for r in rs}
        p2u = {tuple(round(v, 3) for v in r["p2"]) for r in rs}
        ds = [r["d"] for r in rs]
        print("   mon=%s ZP=%2d | a30组唯一值=%2d a40组唯一值=%2d | d %s"
              % (mon, len(rs), len(p1u), len(p2u), quantiles(ds, (0, 0.5, 1.0))))

    # ---------- 5) 两组坐标的时间稳定性 ----------
    print("\n[5] 两组坐标谁恒定/谁变化（同一 mon 内）")
    for mon, rs in sorted(bymon.items(), key=lambda kv: -len(kv[1])):
        p1u = {tuple(r["p1"]) for r in rs}
        p2u = {tuple(r["p2"]) for r in rs}
        print("   mon=%s : sub+0x30组 raw唯一值=%d , sub+0x40组 raw唯一值=%d"
              % (mon, len(p1u), len(p2u)))
    p1_all = {tuple(r["p1"]) for r in recs}
    p2_all = {tuple(r["p2"]) for r in recs}
    print("   全体: sub+0x30组 raw唯一值=%d , sub+0x40组 raw唯一值=%d" % (len(p1_all), len(p2_all)))

    # ---------- 5b) a30 固定值明细 ----------
    print("\n[5b] sub+0x30..0x38 固定值明细（解码 f32 -> 出现的 mon）")
    tri_mons = defaultdict(set)
    for r in recs:
        tri_mons[tuple(round(v, 1) for v in r["p1"])].add(r["mon"])
    for tri, mons in sorted(tri_mons.items(), key=lambda kv: -len(kv[1])):
        print("   f32=(%.1f, %.1f, %.1f)  出现 mon = %s" % (tri[0], tri[1], tri[2], sorted(mons)))

    # ---------- 5c) a40 相邻帧位移 ----------
    print("\n[5c] sub+0x40..0x48 相邻帧位移（同一 mon 按帧排序）")
    all_steps = []
    for mon, rs in sorted(bymon.items(), key=lambda kv: -len(kv[1])):
        rs2 = sorted(rs, key=lambda r: r["f"])
        steps = [math.dist(rs2[i]["p2"], rs2[i + 1]["p2"]) for i in range(len(rs2) - 1)]
        all_steps += steps
        if steps:
            print("   mon=%s n=%d 相邻位移 %s" % (mon, len(rs2), quantiles(steps, (0, 0.5, 1.0))))
    print("   全体相邻位移 %s" % quantiles(all_steps, (0, 0.5, 1.0)))

    # ---------- 5d) a40 各轴值域 ----------
    print("\n[5d] sub+0x40..0x48 各轴值域")
    for ax, name in enumerate("xyz"):
        vals = [r["p2"][ax] for r in recs]
        print("   %s: min=%.1f max=%.1f 跨度=%.1f" % (name, min(vals), max(vals), max(vals) - min(vals)))

    # ---------- 6) 3D 距离分布与双簇检测 ----------
    ds = [r["d"] for r in recs]
    print("\n[6] ZP 3D 距离 |a40-a30| 分布")
    print("   n=%d  min=%.1f max=%.1f mean=%.1f" % (len(ds), min(ds), max(ds), sum(ds) / len(ds)))
    print("   分位:", quantiles(ds))
    cs = clus_split(ds)
    if cs:
        print("   最大间隙切分(双簇候选):", cs)
        print("   判读: gap_ratio=%.3f %s" % (cs["gap_ratio"],
              ">0.35 且两段各>=3 → 疑似两簇" if cs["gap_ratio"] > 0.35 and cs["lo_n"] >= 3 and cs["hi_n"] >= 3
              else "→ 未见明显两簇"))
    # 简单直方图
    if ds:
        lo, hi = min(ds), max(ds)
        nb = 12
        w = (hi - lo) / nb if hi > lo else 1
        hist = [0] * nb
        for v in ds:
            hist[min(nb - 1, int((v - lo) / w))] += 1
        print("   直方图(12桶): " + " ".join("[%.0f-%.0f]:%d" % (lo + i * w, lo + (i + 1) * w, hist[i])
                                          for i in range(nb) if hist[i]))

    # ---------- 7) 跨 mon 对应：目标点是否指向另一实体 ----------
    print("\n[7] 跨 mon 坐标对应（判定'目标点是否指向另一只实体'的关键离线检验）")
    TOL = 1.0
    pairs = 0
    p1_self = defaultdict(set); p2_self = defaultdict(set)
    for r in recs:
        p1_self[r["mon"]].add(tuple(round(v, 2) for v in r["p1"]))
        p2_self[r["mon"]].add(tuple(round(v, 2) for v in r["p2"]))
    mons = sorted(p1_self.keys())
    for i, ma in enumerate(mons):
        for mb in mons[i + 1:]:
            for lbl, sa, sb in (("a40(A)~a30(B)", p2_self[ma], p1_self[mb]),
                                ("a30(A)~a40(B)", p1_self[ma], p2_self[mb]),
                                ("a40(A)~a40(B)", p2_self[ma], p2_self[mb]),
                                ("a30(A)~a30(B)", p1_self[ma], p1_self[mb])):
                hit = sum(1 for x in sa for y in sb if math.dist(x, y) < TOL)
                if hit:
                    pairs += 1
                    print("   %s vs %s : %s 命中 %d 对 (tol=%.1f)" % (ma, mb, lbl, hit, TOL))
    print("   跨 mon 近似坐标命中总数 =", pairs,
          "（若为 0 → 无任何'某实体目标点等于另一实体自身点'的证据）")

    # ---------- 8) Z 与 ZP 配对 ----------
    zs = [(fr, d) for t, fr, d in rows if t == "Z"]
    print("\n[8] Z 行 (op/md/val) 与 ZP 行配对抽样")
    print("   Z=%d 条, 距离 mode 分布=%s" % (len(zs), dict(Counter(d.get("md") for _, d in zs))))
    near = 0
    for fr, d in zp[:5]:
        cand = [z for zf, z in zs if abs(zf - fr) <= 2]
        print("   ZP f=%d d=%.1f | 同帧±2 Z: %s"
              % (fr, math.dist(tuple(f32(d.get(k, "0")) for k in ("a30", "a34", "a38")),
                              tuple(f32(d.get(k, "0")) for k in ("a40", "a44", "a48"))),
                 [(c.get("md"), c.get("val")) for c in cand[:3]]))
        if cand:
            near += 1
    print("   说明: Z 行 val 是 case 阈值/计算值原始位，不含'目标实体身份'字段；ZP 不含猎人坐标。")

    # ---------- 9) 结论性缺口清单 ----------
    print("\n[9] 现有日志对'目标点身份'的可判定性（字段盘点）")
    print("   已有: 两组几何坐标(sub+0x30..0x38 / sub+0x40..0x48)、heading、mon、sp、area、act/sub、Z case 阈值")
    print("   缺失: 猎人/玩家坐标真值、target_type/target_id/target_selID 运行时值、")
    print("         mon→怪种映射表、两只大怪同区同时间窗样本、任意'目标实体指针'字段")
    print("   ==> 无法把任一坐标组绑定到'猎人'或'另一只大怪'；只能给出间接/否定性证据。")
    print("=" * 78)


if __name__ == "__main__":
    main()
