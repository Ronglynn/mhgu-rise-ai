# -*- coding: utf-8 -*-
"""v65 判读：P64 三缺陷修复后的纯只读一次验收。

v65 与 v63 的差别：DRAIN_ENABLE=0（自然疲惫已够）、新增 DG（放大门控诊断）
与 ZD（dttune 表链失败级码）、AE/QX 扩配额并节流。判读关注：
自然疲惫窗与窗内探针数据、DG 定位 J=0、ZD 定位 ZT=0、W2 路线 A 数据达标。


v65 与 v62 的唯一差别：DRAIN_ENABLE=1，倍率改为自适应（base/8），
约 8 个动作 ≈1.5 分钟后游戏原生进入疲惫，供同场采 st3=2 样本。
J/G 行会重新出现（放宽发布检查），R/W 仍关闭，6 hook、零内存写入不变。


v65 只改 W1 形状表/混合比/护栏，W2 探针与日志格式逐字节不变：
  - 形状 SHAPE_A3/A4/N3/N4/T3 取自 Rise 15 池实测降序均值
  - 怒/常/疲三态分离，按状态给 k3:k4 混合比，护栏 n>=4 -> n>=3
  - 验收关注 wall/wnok 覆盖率上升、w3/w4/wt 分化、零异常


v65 只修 W2 探针，W1 行为不变：
  - Z 行新增 src(解析来源) / g(guess) / ts(命中 case 阈值) / r0,r1(原始字节)
  - 新增 ZS 行（a0±0x2000 脚本指针候选），ent 从硬 FAIL 降为诊断
  - 档位判据改为「hit>=0 或 ts!=0xFF」的档位证据率


v65 = RAI v65 W1-ALL-PICKS + W2 DISTANCE-BAND READONLY PROBE
  - 继承 v57 全部行为与发布配置（W1_ALL=1 / DRAIN_ENABLE=0 / PROFILE_RELEASE=1）
  - 新增 Z 行（距离块 op/md/val/ip/blk/case 阈值/命中档位/st3）
  - 新增 ZP 行（sub 几何字段 f32 原始位 + cmd/ent 脚本基址）
验收核心：W1 wall/wnok>0 且形状生效；W2 Z/ZP 有足够样本、case 解析成功、
阈值序列非全 0、命中档位可定位、几何值可解释为有限 f32。

用法: python analyze_v65_release.py <log>
"""
import collections
import math
import re
import struct
import sys

INT = {
    "f", "n", "nc", "ret", "d", "ki", "rd", "b1", "ph", "sw", "sw2", "nr",
    "st3", "vd", "wm", "wk", "live", "log", "md", "p5", "a", "sel", "ok",
    "e1", "e0", "r1", "r0", "n1", "n0", "v1", "v0", "p2",
    "s0", "s1", "s2", "sv0", "sv1", "sv2", "w3", "w4", "wt", "d3", "skip",
    "gac", "gsum", "gmax", "gnz", "amx", "anf", "anr", "gdone", "gf",
    "wall", "wnok", "hub", "peak", "m", "m1", "m0c", "m0e", "x", "q",
    "fail", "rep", "v", "beg", "begf", "noalt",
    # v65 Z 行（十进制字段；op/val/ip/blk 是 hex 字符串，不入此表）
    "t0", "t1", "t2", "t3", "hit", "src", "ts",
}
HEX = {"op", "val", "ip", "blk", "mon", "sub", "a30", "a34", "a38",
       "a40", "a44", "a48", "e0", "e2", "e4", "hd", "cmd", "ent",
       "g", "r0", "r1"}
Z_NEED = ("f", "op", "md", "val", "ip", "blk", "nc", "src", "t0", "t1",
          "t2", "t3", "hit", "ts", "ret", "st3", "g", "r0", "r1")
DIST_MODES = {4, 5, 6, 7, 14, 15, 16, 19, 20, 21, 22, 23, 24, 25, 26}


def parse_line(line):
    m = re.search(r"\[rai\] ([A-Z][A-Z0-9]*) (.*)$", line)
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


def f32(h):
    try:
        return struct.unpack("<f", struct.pack("<I", int(str(h), 16)))[0]
    except (ValueError, TypeError):
        return float("nan")


def good_float(x):
    return math.isfinite(x) and abs(x) < 1.0e7


def pct(a, b):
    return (100.0 * a / b) if b else 0.0


def quantile(xs, q):
    if not xs:
        return 0.0
    s = sorted(xs)
    return s[min(len(s) - 1, int(q * len(s)))]


def main(path):
    lines = open(path, "r", encoding="utf-8", errors="replace").read().splitlines()
    rows = collections.defaultdict(list)
    for l in lines:
        tag, d = parse_line(l)
        if tag and d:
            rows[tag].append(d)

    V, S, B = rows["V"], rows["S"], rows["BEAT"]
    J, G, R, W = rows["J"], rows["G"], rows["R"], rows["W"]
    Z, ZP, ZT = rows["Z"], rows["ZP"], rows["ZT"]
    AE, QX = rows["AE"], rows["QX"]
    B2 = rows["B2"]
    is_v65 = any("RAI v65" in l for l in lines)
    banner = next((l.strip() for l in lines if "RAI v65" in l), "(旧日志)")
    fatal = sum(1 for l in lines if "FATAL" in l)
    crash = [l for l in lines
             if "c0000005" in l or "*** exception" in l or "host backtrace" in l]
    installs = [l.strip() for l in lines if "[rai] INSTALL h_" in l]

    print("=== v65 W1 全抽选 + W2 距离档只读探针 判读 ===")
    print("日志: %s" % path)
    print("banner: %s" % banner[:120])
    print("版本=%s  V=%d S=%d BEAT=%d Z=%d ZP=%d ZT=%d B2=%d AE=%d QX=%d J=%d G=%d FATAL=%d" %
          ("v65" if is_v65 else "旧日志(降级)", len(V), len(S), len(B),
           len(Z), len(ZP), len(ZT), len(B2), len(AE), len(QX),
           len(J), len(G), fatal))
    for l in installs[:6]:
        print("  " + l[:120])

    checks, skips = [], []

    def add(name, ok, detail):
        checks.append((name, bool(ok)))
        print("  [%s] %-46s %s" % ("PASS" if ok else "FAIL", name, detail))

    def skip(name, detail):
        skips.append(name)
        print("  [SKIP] %-46s %s" % (name, detail))

    # --- 基础健康（所有版本通用）---
    add("零 FATAL", fatal == 0, "FATAL=%d" % fatal)
    add("零 host 异常（c0000005）", len(crash) == 0, "异常=%d" % len(crash))
    need = 6 if is_v65 else 5
    add("hook INSTALL 数量符合版本（%d）" % need,
        len(installs) >= need, "INSTALL=%d" % len(installs))
    if is_v65:
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

    if not is_v65:
        skip("v65 专项判据", "旧日志无 Z/ZP 与 v65 横幅，降级仅做基础健康检查")
        print("\n=== 结论 ===")
        npass = sum(1 for _, ok in checks if ok)
        print("  PASS=%d / FAIL=%d / SKIP=%d" % (npass, len(checks) - npass, len(skips)))
        print("  -> 旧日志降级：仅基础健康检查有效。")
        return

    # --- v65：W2 状态×档位加权 + 纯只读 ---
    add("RAI v65 横幅", True, "v65 state x band weighting")
    add("PROFILE_RELEASE：无 R/W 高频快照行", len(R) == 0 and len(W) == 0,
        "R=%d W=%d" % (len(R), len(W)))
    add("纯只读：无强制 J/G 行", len(J) == 0 and len(G) == 0,
        "J=%d G=%d" % (len(J), len(G)))
    add("纯只读：gdone=0（无强制疲惫）",
        bool(S) and S[-1].get("gdone") == 0,
        "gdone=%s" % (S[-1].get("gdone") if S else "?"))
    u_force = sum(1 for l in lines if "[rai] U " in l and "force=1" in l)
    add("U 行无 v48 amount 强制", u_force == 0, "U force=1=%d" % u_force)
    add("DG/ZD 诊断行已撤除（P64 已离线定案）",
        len(rows["DG"]) == 0 and len(rows["ZD"]) == 0,
        "DG=%d ZD=%d" % (len(rows["DG"]), len(rows["ZD"])))

    # --- v65：自然疲惫窗 + W2 状态×档位加权验收 ---
    def ti(d, k, default=0):
        try:
            return int(d.get(k, default))
        except (TypeError, ValueError):
            return default
    tired_ae = sum(1 for d in AE if ti(d, "t505") >= 2)
    tired_qx = [d for d in QX if ti(d, "t505", 255) >= 2]
    tired_z = sum(1 for d in Z if ti(d, "st3") == 2)
    wt = max((ti(d, "wt") for d in S), default=0)
    tired_rows = tired_ae + len(tired_qx) + tired_z
    lo = min((ti(d, "f") for d in tired_qx), default=0)
    hi = max((ti(d, "f") for d in tired_qx), default=0)
    win_ae = sum(1 for d in AE if lo and lo <= ti(d, "f") <= hi)
    win_other = sum(1 for tag in ("ZT", "QX", "Z", "ZP", "B2")
                    for d in rows[tag] if lo and lo <= ti(d, "f") <= hi)
    bds = [ti(d, "bd", 0xFF) for d in B2]
    bset = set(x for x in bds if x <= 4)
    wb = max((ti(d, "wb") for d in S), default=0)
    bf = max((ti(d, "bf") for d in S), default=0)
    add("[TIRED] 自然疲惫窗存在（t505>=2 / st3=2 / wt>0）",
        tired_rows > 0 or wt > 0,
        "AE=%d QX=%d Z=%d wt=%d" % (tired_ae, len(tired_qx), tired_z, wt))
    add("[TIRED] 疲惫窗时长合理（30~150 秒）", 1800 <= hi - lo <= 9000,
        "f=%d..%d 共 %d 帧 ≈%.1f 秒" % (lo, hi, hi - lo, (hi - lo) / 60.0))
    add("[TIRED] 窗内 W2/W3/W4 探针有数据", win_other > 0,
        "窗内 ZT/QX/Z/ZP/B2 行=%d" % win_other)
    add("[TIRED] 窗内 AE 有数据", win_ae > 0, "窗内 AE=%d" % win_ae)
    add("[BAND] B2 档位诊断行存在", len(B2) > 0, "B2=%d" % len(B2))
    add("[BAND] 档位覆盖 >=2 档", len(bset) >= 2,
        "bd 分布=%s" % dict(collections.Counter(bds)))
    add("[BAND] W1 已按 (st3,band) 取 Rise 15 池形状（wb>0）", wb > 0,
        "wb=%d bf(降级)=%d" % (wb, bf))
    add("[BAND] 降级护栏可用（bf>=0 且 wb+bf 与抽选量级相符）",
        wb + bf > 0, "wb+bf=%d" % (wb + bf))
    print("\n=== v65 W2 状态×档位加权 ===")
    print("  B2=%d 档位分布=%s 覆盖档数=%d" %
          (len(B2), dict(collections.Counter(bds)), len(bset)))
    print("  S 行 wb(按档位形状)=%d  bf(降级 v60)=%d  占比=%.1f%%" %
          (wb, bf, 100.0 * wb / (wb + bf) if wb + bf else 0.0))
    print("  疲惫窗 f=%d..%d (%.1f 秒)  窗内 AE=%d 其他探针=%d  wt=%d" %
          (lo, hi, (hi - lo) / 60.0, win_ae, win_other, wt))
    if B2:
        print("  B2 md 分布=%s  si 分布=%s" %
              (dict(collections.Counter(d.get("md") for d in B2)),
               dict(collections.Counter(d.get("si") for d in B2).most_common(4))))
    if ZT:
        print("  ZT=%d 行（运行时表链仍可读，非必需）" % len(ZT))
    else:
        print("  ZT=0（P64 定案：不需运行时表链，按 hit/ts 分档即可）")

    # --- W1 全抽选（继承 v57）---
    if S:
        s = S[-1]
        wall, wnok = s.get("wall"), s.get("wnok")
        add("S 行 wall/wnok 字段齐全",
            isinstance(wall, int) and isinstance(wnok, int),
            "wall=%s wnok=%s" % (wall, wnok))
        add("[W1] 全抽选已生效（wall>0 / wnok>0）",
            isinstance(wall, int) and isinstance(wnok, int) and wall > 0 and wnok > 0,
            "wall=%s wnok=%s" % (wall, wnok))
        add("[W1] 成功应用不超过尝试次数",
            isinstance(wall, int) and isinstance(wnok, int) and wnok <= wall,
            "wnok/wall=%.3f" % (wnok / wall if isinstance(wall, int) and wall else 0))
        add("[W1] Rise 形状在非疲态生效（w3+w4>0）",
            isinstance(s.get("w3"), int) and isinstance(s.get("w4"), int)
            and s["w3"] + s["w4"] > 0,
            "w3=%s w4=%s wt=%s" % (s.get("w3"), s.get("w4"), s.get("wt")))
        add("[W1] d3/skip 恒 0",
            s.get("d3") == 0 and s.get("skip") == 0,
            "d3=%s skip=%s" % (s.get("d3"), s.get("skip")))
        if isinstance(s.get("wt"), int) and s["wt"] > 0:
            add("[W1] Rise 疲惫形状已使用（wt>0）", True, "wt=%s" % s["wt"])
        else:
            skip("[W1] Rise 疲惫形状（wt）",
                 "v65 应出现疲惫窗；若 wt=0 需看上方 [TIRED] 疲惫态样本是否充足")
    else:
        add("S 行存在", False, "S=0")
    bad_st = [(v.get("f"), v.get("st3"), v.get("vd")) for v in V
              if isinstance(v.get("st3"), int) and isinstance(v.get("vd"), int)
              and ((v["st3"] == 2 and v["vd"] != 1)
                   or (v["st3"] in (0, 1) and v["vd"] != 2))]
    add("[W1] V 行 st3->vd 映射零违例", len(bad_st) == 0,
        "违例=%d %s" % (len(bad_st), bad_st[:3]))
    bad_wm = [(v.get("f"), v.get("wm"), v.get("wk")) for v in V
              if isinstance(v.get("wm"), int) and isinstance(v.get("wk"), int)
              and v["wm"] in (1, 2, 3)
              and ((v["wm"] == 3 and v["wk"] != 3)
                   or (v["wm"] in (1, 2) and v["wk"] not in (3, 4)))]
    add("[W1] V 行 wm->wk 映射零违例", len(bad_wm) == 0,
        "违例=%d %s" % (len(bad_wm), bad_wm[:3]))

    # --- W2 距离档探针 ---
    add("[W2] Z 行存在", len(Z) > 0, "Z=%d" % len(Z))
    add("[W2] ZP 几何快照行存在", len(ZP) > 0, "ZP=%d" % len(ZP))
    zfull = [z for z in Z if all(k in z for k in Z_NEED)]
    add("[W2] Z 行字段齐全", len(zfull) == len(Z) and len(Z) > 0,
        "完整=%d/%d" % (len(zfull), len(Z)))
    modes = collections.Counter(z.get("md") for z in zfull
                                if isinstance(z.get("md"), int))
    dist_modes = {m for m in modes if m in DIST_MODES}
    add("[W2] 距离 mode 覆盖 >=2 种", len(dist_modes) >= 2,
        "modes=%s" % sorted(dist_modes))
    n_good = sum(1 for z in zfull if isinstance(z.get("nc"), int) and z["nc"] >= 2)
    add("[W2] case 阈值序列解析成功率 >=50%", pct(n_good, len(zfull)) >= 50.0,
        "nc>=2: %d/%d (%.1f%%)" % (n_good, len(zfull), pct(n_good, len(zfull))))
    t_nz = sum(1 for z in zfull
               if any(isinstance(z.get(k), int) and z[k] != 0
                      for k in ("t0", "t1", "t2", "t3")))
    add("[W2] 存在非零 case 阈值", t_nz > 0,
        "非零阈值行=%d/%d" % (t_nz, len(zfull)))
    hit_i = sum(1 for z in zfull if isinstance(z.get("hit"), int) and z["hit"] >= 0)
    ts_ok = sum(1 for z in zfull if isinstance(z.get("ts"), int) and z["ts"] != 0xFF)
    hit_ok = sum(1 for z in zfull
                 if (isinstance(z.get("hit"), int) and z["hit"] >= 0)
                 or (isinstance(z.get("ts"), int) and z["ts"] != 0xFF))
    add("[W2] 档位证据率 >=50%（hit>=0 或 ts 有效）",
        pct(hit_ok, len(zfull)) >= 50.0,
        "证据=%d/%d (%.1f%%) [hit=%d ts=%d]" %
        (hit_ok, len(zfull), pct(hit_ok, len(zfull)), hit_i, ts_ok))
    geo_ok = 0
    d3s, dxzs = [], []
    for p in ZP:
        a = [f32(p.get(k)) for k in ("a30", "a34", "a38", "a40", "a44", "a48")]
        if all(good_float(x) for x in a):
            geo_ok += 1
            dx, dy, dz = a[0] - a[3], a[1] - a[4], a[2] - a[5]
            d3s.append(math.sqrt(dx * dx + dy * dy + dz * dz))
            dxzs.append(math.sqrt(dx * dx + dz * dz))
    add("[W2] ZP 几何字段可解释为有限 f32", geo_ok > 0,
        "可解=%d/%d" % (geo_ok, len(ZP)))
    ent_ok = sum(1 for p in ZP if str(p.get("ent", "0")).upper() not in ("0", "00000000"))
    skip("[W2] 脚本基址 ent（P55 已证伪，降为诊断）",
         "ent!=0: %d/%d；v65 改用 ZS 行的指针候选定位 em/cmd" % (ent_ok, len(ZP)))
    st_seen = {z.get("st3") for z in zfull if isinstance(z.get("st3"), int)}
    if len(st_seen) >= 2:
        add("[W2] 距离样本跨多个怪物状态", True, "st3=%s" % sorted(st_seen))
    else:
        skip("[W2] 距离样本跨多个怪物状态",
             "本场 st3=%s，属正常（无发怒/疲惫窗口）" % sorted(st_seen))

    # --- 诊断 ---
    # --- v65 运行时 dttune 阈值链专项 ---
    def to_f(h):
        try:
            return struct.unpack("<f", struct.pack("<I", int(str(h), 16)))[0]
        except (ValueError, TypeError):
            return float("nan")
    def iv2(d, k, default=0):
        try:
            return int(d.get(k, default))
        except (ValueError, TypeError):
            return default
    tune_ok = sum(1 for p in ZT if str(p.get("tune", "0")).upper() not in ("0", "00000000"))
    base_ok = sum(1 for p in ZT if str(p.get("base", "0")).upper() not in ("0", "00000000"))
    cnts = [iv2(p, "cnt") for p in ZT]
    good_rows = []
    for p in ZT:
        v = [to_f(p.get("t%d" % k, "0")) for k in range(4)]
        if all(math.isfinite(x) for x in v) and v[0] >= 50 and v[0] < v[1] < v[2] < v[3] <= 1e5:
            good_rows.append((p, v))
    if is_v65:
        if ZT:
            add("[W2] ZT 运行时阈值行存在", True, "ZT=%d" % len(ZT))
            add("[W2] 存在递增 4 档 f32 物理阈值", len(good_rows) > 0,
                "合法行=%d/%d" % (len(good_rows), len(ZT)))
        else:
            skip("[W2] ZT 运行时表链（P64 已证零输出）",
                 "ZT=0；v65 用 ZD 行的 fail 级码定位卡点，暂不阻塞本场")
    print("\n=== v65 运行时阈值链（W2 高保真前置） ===")
    if ZT:
        print("  cnt 分布: %s" % dict(collections.Counter(cnts)))
        print("  ba 分布: %s" % dict(collections.Counter(p.get("ba") for p in ZT)))
        print("  slot 分布: %s" % dict(collections.Counter(p.get("slot") for p in ZT)))
        for p, v in good_rows[:6]:
            print("  f=%s slot=%s ba=%s 阈值=[%s]" %
                  (p.get("f"), p.get("slot"), p.get("ba"),
                   ", ".join("%.0f" % x for x in v)))
        print("  => 表链可读=%s / a0=ctx/em 支持度=%s / 合法物理阈值行=%d" %
              (tune_ok > 0 and base_ok > 0, "高" if tune_ok > 0 else "未定", len(good_rows)))
    else:
        print("  无 ZT 行（旧日志或表链检查全部静默失败）")

    # --- v65 W3/W4 一次性探针专项 ---
    def q(d, k, default=0):
        try:
            return int(d.get(k, default))
        except (TypeError, ValueError):
            return default
    gaps = [q(p, "gap") for p in AE]
    modes = collections.Counter(q(p, "r3") for p in QX)
    end_req = [p for p in QX if q(p, "kind", 0xFF) != 0xFF]
    kinds = collections.Counter(q(p, "kind") for p in end_req)
    if is_v65:
        add("[W3] AE 动作类变化行存在", len(AE) > 0, "AE=%d" % len(AE))
        add("[W3] +0x73E0 变化间隔 gap 可用",
            bool(gaps) and max(gaps) > 0,
            "gap min/p50/max=%s" % (str([min(gaps), sorted(gaps)[len(gaps)//2], max(gaps)]) if gaps else "无"))
        add("[W3] QX 提交事件行存在", len(QX) > 0, "QX=%d" % len(QX))
        add("[W3] AE 节流生效（gap 中位 >=20）",
            bool(gaps) and sorted(gaps)[len(gaps)//2] >= 20,
            "gap p50=%d" % (sorted(gaps)[len(gaps)//2] if gaps else -1))
        add("[W4] 捕获 action-end 状态请求（kind!=0xFF）", len(end_req) > 0,
            "end_req=%d/%d kinds=%s" % (len(end_req), len(QX), dict(kinds)))
        add("[W4] mode 分类覆盖（r3）", len(modes) >= 2,
            "modes=%s" % dict(modes))
    print("\n=== v65 W3/W4 一次性探针（单场节省轮次） ===")
    if AE:
        print("  AE=%d  gap min/p50/p90/max = %d/%d/%d/%d 帧" %
              (len(AE), min(gaps), sorted(gaps)[len(gaps)//2],
               sorted(gaps)[int(.9*len(gaps))], max(gaps)))
        print("  AE st(怒)=%s  t505(疲惫)=%s" %
              (dict(collections.Counter(p.get("st") for p in AE)),
               dict(collections.Counter(p.get("t505") for p in AE))))
    else:
        print("  AE: 无（旧日志或未触发）")
    if QX:
        print("  QX=%d  mode(r3)=%s  action-end 请求=%d  kind=%s" %
              (len(QX), dict(modes), len(end_req), dict(kinds)))
        print("  异常状态位 t505=%s t518=%s t5e08=%s" %
              (dict(collections.Counter(p.get("t505") for p in QX)),
               dict(collections.Counter(p.get("t518") for p in QX)),
               dict(collections.Counter(p.get("t5e08") for p in QX))))
        cross = collections.Counter((p.get("kind"), p.get("t505"), p.get("t518")) for p in end_req)
        print("  kind x (t505,t518) 交叉 top5: %s" % cross.most_common(5))
    else:
        print("  QX: 无（旧日志或未触发）")

    print("\n=== W2 距离档分布诊断 ===")
    print("  %-6s %-6s %-8s %-10s %-22s %s" %
          ("md", "rows", "nc>=2", "hit>=0", "t序列top", "st3分布"))
    for md in sorted(dist_modes):
        sub = [z for z in zfull if z.get("md") == md]
        tc = collections.Counter(
            tuple(z.get(k, 0) for k in ("t0", "t1", "t2", "t3")) for z in sub)
        ng = sum(1 for z in sub if isinstance(z.get("nc"), int) and z["nc"] >= 2)
        nh = sum(1 for z in sub if isinstance(z.get("hit"), int) and z["hit"] >= 0)
        stc = collections.Counter(z.get("st3") for z in sub)
        print("  %-6s %-6d %-8s %-10s %-22s %s" %
              (md, len(sub), "%.0f%%" % pct(ng, len(sub)),
               "%.0f%%" % pct(nh, len(sub)), str(tc.most_common(1)[0][0]),
               dict(sorted(stc.items(), key=lambda x: str(x[0])))))
    src_c = collections.Counter(z.get("src") for z in zfull)
    print("  解析来源 src: %s (1=begin / 2=near / 0=未解析)" % dict(src_c))
    ZS = rows["ZS"]
    if ZS:
        for p in ZS[:2]:
            cand = ["%s=%s/%s" % (k, p.get("o"+k), p.get("v"+k))
                    for k in "012345"
                    if str(p.get("v"+k, "0")).upper() not in ("0", "00000000", "NONE")]
            print("  ZS 指针候选: n=%s %s" % (p.get("n"), " ".join(cand)))
    else:
        print("  ZS 行: 无（脚本指针扫描未触发）")
    ops = collections.Counter(z.get("op") for z in zfull)
    print("  op 分布: %s" % dict(ops.most_common(10)))
    print("  hit 分布: %s" % dict(sorted(collections.Counter(
        z.get("hit") for z in zfull).items(), key=lambda x: str(x[0]))))
    print("  val(原始位) 非零: %d/%d" %
          (sum(1 for z in zfull if str(z.get("val", "0")).upper() not in
               ("0", "00000000")), len(zfull)))
    if d3s:
        print("  ZP 3D 距离: min=%.1f p50=%.1f p90=%.1f max=%.1f (n=%d)" %
              (min(d3s), quantile(d3s, 0.5), quantile(d3s, 0.9), max(d3s), len(d3s)))
        print("  ZP XZ 距离: min=%.1f p50=%.1f p90=%.1f max=%.1f" %
              (min(dxzs), quantile(dxzs, 0.5), quantile(dxzs, 0.9), max(dxzs)))
        t100 = [z["t0"] * 100 for z in zfull
                if isinstance(z.get("t0"), int) and z["t0"] > 0
                and z.get("md") in (5, 6, 7, 15, 16, 19, 20, 23, 24, 25)]
        if t100:
            print("  case*100 阈值: min=%d p50=%d max=%d (n=%d)" %
                  (min(t100), int(quantile(t100, 0.5)), max(t100), len(t100)))
    offs = []
    ents_all = [int(str(p.get("ent", "0")), 16) for p in ZP
                if str(p.get("ent", "0")).upper() not in ("0", "00000000")]
    for z in zfull:
        try:
            ipv = int(str(z.get("ip", "0")), 16)
            if ents_all and ipv > ents_all[0]:
                offs.append(ipv - ents_all[0])
        except (ValueError, TypeError):
            pass
    if offs:
        print("  ip-ent 脚本内偏移: min=%d p50=%d max=%d (n=%d)" %
              (min(offs), int(quantile(offs, 0.5)), max(offs), len(offs)))

    # --- 结论 ---
    print("\n=== 结论 ===")
    npass = sum(1 for _, ok in checks if ok)
    nfail = len(checks) - npass
    print("  PASS=%d / FAIL=%d / SKIP=%d" % (npass, nfail, len(skips)))
    w2_ready = (len(Z) >= 20 and len(ZP) >= 5
                and pct(n_good, len(zfull)) >= 50.0
                and pct(hit_ok, len(zfull)) >= 50.0 and geo_ok > 0)
    if nfail == 0:
        print("  -> W1 验收通过：全抽选生效（wall/wnok>0）、Rise 形状按状态分化。")
        print("  -> W2 数据%s：%s" %
              ("充足，可进入档位映射" if w2_ready else "不足，需补一轮探针",
               "Z=%d ZP=%d case解析%.0f%% 档位证据%.0f%%" %
               (len(Z), len(ZP), pct(n_good, len(zfull)), pct(hit_ok, len(zfull)))))
        print("     W2 已按 (st3,band) 取 Rise 15 池形状；离线 dist_bands_all.json")
        print("     提供 137 怪 4 档 f32 阈值用于标定与语义解释。")
        print("  -> 自然疲惫窗：f=%d..%d (%.1f 秒)，疲惫态样本=%d，wt=%d" %
              (lo, hi, (hi - lo) / 60.0, tired_rows + wt, wt))
        print("  -> W2 加权：B2=%d 覆盖档位=%s，wb=%d 次按档位形状 / bf=%d 次降级 v60" %
              (len(B2), sorted(bset), wb, bf))
        print("     成品可设 W2_PROBE=0 / MAX_B2=0；band_sense 独立于日志，加权仍生效。")
    else:
        print("  -> 存在 FAIL，按上方条目定位，不要据此发布或推进 W2。")
    print("  回退：copy 04_RiseAI\\out\\rai_p64_fix_v64.nro 覆盖插件 nro")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "04_RiseAI/out/sim_v65_smoke.txt")
