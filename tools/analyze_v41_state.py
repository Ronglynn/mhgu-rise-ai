#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""analyze_v41_state.py — v41 纯只读状态扫描判读（疲劳字段定案）

用法：python 04_RiseAI/tools/analyze_v41_state.py 02_Workspace/game_p54_lite.txt

v41 规则与 v38 逐字节相同，ZERO writes。相对 v40 的三处修正：
  1. 撤销「写 act+0x5D82 强制疲劳」（P11 证实无效，用户要求不再追）。
  2. C 行改为 8 个 mon 槽每帧扫描；P11 只盯 LAST_MON 且盯错怪。
  3. C 行触发改为「离散状态指纹」fp = c0&0xFF | cf<<8 | st<<16 |
     (t4!=0)<<24；c4/c8/ex/t4 数值只输出不触发。P11 的 c4 是每帧变化的
     浮点，400 条配额 816 帧被打光 -> 疲劳段完全没被采到。

候选字段（全部只读）：
  c0 = *(u32*)(mon+0xCAC0)  状态枚举候选：0x106873C 初始化 1；疲惫分支
                             0x1068EA4 `ldr r2,[r4,#0xCAC0]; cmp #2/#3`
  c4 = *(u32*)(mon+0xCAC4)  P11 证伪：413 / 浮点位模式（0xCEFEB8 写 413）
  c8 = *(u32*)(mon+0xCAC8)  与 c4 同族
  cf = *(u8*)(mon+0xCBF1)   怒标志写入点（0x1068E1C / 0x1068E8C）
  e1/dc/h1                   旧候选（动作 sub / 长周期 / Hub）
  st = *(u8*)(act+0x518)    已确证：1=怒；P10/P11 从未出现 2
  t4 = *(u16*)(act+0x408)   疲惫分支 0x1068F18/0x1068F9C 写入的 s16
  ex = *(u16*)(act+0x5D82)  减气蓄积（只读观察）

判读策略：BEAT 的 `a` 是**全量**动作开始计数。疲惫时怪物流口水/喘气/倒地，
几乎不出招 -> 连续 >=3 个 300 帧窗口 Δa=0 是天然的时间锚点（P11 实测
f=69600..70500 = 任务内 15.3~15.5 分钟，与用户截图/描述吻合）。
脚本自动找这些锚点，并检查锚点段内 C 行哪个字段形成持续状态段。

非 v41 日志自动降级为冒烟模式（不把缺失字段判 FAIL）。
"""
import sys, re, collections

HEX = {"mon", "sp", "w73", "ip", "w0", "w1", "first", "blk", "pick", "sig",
       "psig", "act", "fp"}
INT = {"f", "n", "op", "md", "mode", "sub", "p5", "ret", "nc", "d", "delta", "nr",
       "live", "log", "k", "why", "id", "a", "s", "pa", "ps", "st", "r1", "r2", "r3",
       "m", "m1", "m0c", "m0e", "x", "q", "sel", "beg", "begf", "ki", "sw",
       "rep", "v", "noalt", "fail", "ok", "peak", "hub", "depth", "rd", "b1", "sw2",
       "ph", "p2", "a2", "last", "e1", "e0", "r1n", "r0", "n1", "n0", "v1", "v0",
       "c0", "c4", "c8", "cf", "e1", "dc", "h1", "t4", "ex", "i",
       "ex0", "ex1", "forced"}

FIELDS = ["c0", "c4", "c8", "cf", "e1", "dc", "h1", "st", "t4", "ex"]


def parse(s):
    d = {}
    for k, v in re.findall(r"(\w+)=(\S+)", s):
        # A 行 c4 用 {:08X}（历史格式），C 行 c4 用十进制；统一成 int。
        if k == "c4" and re.fullmatch(r"[0-9A-Fa-f]{8}", v):
            d[k] = int(v, 16); continue
        if k in HEX:
            try: d[k] = int(v, 16)
            except ValueError: d[k] = v
        elif k in INT:
            try: d[k] = int(v, 0)
            except ValueError: d[k] = v
        else:
            d[k] = v
    return d


def main(path):
    lines = open(path, "rb").read().decode("utf-8", "replace").splitlines()
    rows = collections.defaultdict(list)
    for ln in lines:
        m = re.search(r"\[rai\] (A|V|BEAT|S|K|E|C|F) (.*)$", ln)
        if m:
            rows[m.group(1)].append(parse(m.group(2)))
    A, C, B, V = rows["A"], rows["C"], rows["BEAT"], rows["V"]
    is_v41 = any("RAI v41" in l for l in lines)
    fatal = sum(1 for l in lines if "FATAL" in l)
    ok, bad = [], []

    def add(name, cond, detail):
        (ok if cond else bad).append((name, detail))

    print("=== v41 只读状态扫描判读：%s ===" % path)
    print("  版本=%s  FATAL=%d  A=%d  C=%d  V=%d  BEAT=%d" %
          ("v41" if is_v41 else "旧日志(冒烟)", fatal, len(A), len(C), len(V), len(B)))
    if not is_v41:
        print("  非 v41 日志 -> 冒烟完成，不做状态判读。")
        return 0
    add("零 FATAL", fatal == 0, "FATAL=%d" % fatal)
    add("有 A 行与 C 行", len(A) > 0 and len(C) > 0, "A=%d C=%d" % (len(A), len(C)))
    add("A 行含新字段 c0/t4", all(("c0" in x and "t4" in x) for x in A[:5]),
        "首行键=%s" % sorted(A[0].keys()) if A else "无 A 行")

    # --- 任务开始锚点（HUD layout 行）---
    qstart = None
    for ln in lines:
        m = re.search(r"\[KatSmithy\] f=(\d+) layout \+ GUI\\01_quest\\hud\\hud0", ln)
        if m:
            qstart = int(m.group(1)); break
    if qstart is None and B:
        qstart = B[0]["f"]
    print("\n=== 任务时间锚点 ===")
    print("  任务开始 f≈%s   结算/末帧 f=%s" %
          (qstart, B[-1]["f"] if B else "?"))
    if qstart and B:
        print("  按 60fps 全场时长≈%.1f 分钟（P11 已用 29 分钟口径校验）" %
              ((B[-1]["f"] - qstart) / 3600.0))

    # --- BEAT 全量计数 -> 零动作段（疲劳时间锚点）---
    steps = [(B[i]["f"], B[i]["a"] - B[i - 1]["a"]) for i in range(1, len(B))
             if isinstance(B[i].get("a"), int) and isinstance(B[i - 1].get("a"), int)]
    runs, cur = [], []
    for f, da in steps:
        if da == 0:
            cur.append(f)
        else:
            if len(cur) >= 3: runs.append((cur[0] - 300, cur[-1], len(cur)))
            cur = []
    if len(cur) >= 3: runs.append((cur[0] - 300, cur[-1], len(cur)))
    # 排除开场加载段（任务开始之前）和结算后段
    if qstart:
        runs = [r for r in runs if r[0] >= qstart]
    print("\n=== 零动作段（连续 >=3 个 300 帧窗口无动作开始，疲惫候选锚点）===")
    for f0, f1, n in runs:
        mins = ((f0 - qstart) / 3600.0, (f1 - qstart) / 3600.0) if qstart else (0, 0)
        print("  f=%6d..%-6d  窗口=%d  任务内≈%5.1f..%5.1f 分钟" %
              (f0, f1, n, mins[0], mins[1]))
    if not runs:
        print("  本场无零动作段（可能没进疲劳，或观察时长不足）")
    add("存在零动作锚点段", len(runs) > 0, "段数=%d" % len(runs))

    # --- C 行覆盖度 ---
    slots = collections.Counter(x.get("i") for x in C)
    mons = collections.Counter(x.get("mon") for x in C)
    cf0, cf1 = (C[0]["f"], C[-1]["f"]) if C else (0, 0)
    last_f = B[-1]["f"] if B else 0
    cover = (cf1 / last_f) if last_f else 0
    print("\n=== C 行覆盖（P11 失败点：f=15380 后全场无状态记录）===")
    print("  C=%d  f=%d..%d  覆盖到末帧的 %.1f%%" % (len(C), cf0, cf1, cover * 100))
    print("  扫描槽 i 分布=%s" % sorted(slots.items(), key=lambda z: str(z[0])))
    print("  mon 数=%d  top=%s" % (len(mons), mons.most_common(6)))
    add("C 行覆盖全场 >80%", cover > 0.8, "覆盖=%.1f%% (末 f=%d)" % (cover * 100, last_f))
    add("C 行多槽扫描", len(mons) >= 1, "不同 mon=%d" % len(mons))
    add("C 行配额未打满即断", len(C) < 790 or cover > 0.95,
        "C=%d (上限 800)" % len(C))

    # --- 按 mon 的 C 行状态段 ---
    print("\n=== C 行状态段（按 mon / fp 连续段）===")
    per = collections.defaultdict(list)
    for x in C: per[x.get("mon")].append(x)
    all_segs = []
    for mon, xs in per.items():
        segs = []
        for x in xs:
            key = x.get("fp")
            if segs and segs[-1][0] == key:
                segs[-1][2] = x["f"]
            else:
                segs.append([key, x["f"], x["f"], x])
        all_segs.extend((mon,) + tuple(z) for z in segs)
    for mon, key, f0, f1, x in sorted(all_segs, key=lambda z: z[3] - z[2], reverse=True)[:14]:
        print("  mon=%-10s fp=%-10s f=%6d..%-6d 持续=%5d  c0=%-5s cf=%-4s st=%-3s t4=%-6s c4=%s" %
              (mon, key, f0, f1, f1 - f0, x.get("c0"), x.get("cf"),
               x.get("st"), x.get("t4"), x.get("c4")))
    add("存在 >=300 帧的持续状态段",
        any((z[3] - z[2]) >= 300 for z in all_segs),
        "最长=%d 帧" % max((z[3] - z[2] for z in all_segs), default=0))

    # --- 锚点段内 C 行事件：哪个字段形成状态段 ---
    print("\n=== 锚点段内 / 前后 600 帧的 C 行（定案关键）===")
    hits = []
    for f0, f1, n in runs:
        near = [x for x in C if f0 - 600 <= x["f"] <= f1 + 600]
        print("  锚点 f=%d..%d → C 行 %d 条" % (f0, f1, len(near)))
        for x in near[:12]:
            print("    f=%-7d i=%-2s mon=%-10s fp=%-10s c0=%-5s c4=%-11s c8=%-11s cf=%-4s st=%-3s t4=%-6s ex=%s" %
                  (x["f"], x.get("i"), x.get("mon"), x.get("fp"), x.get("c0"),
                   x.get("c4"), x.get("c8"), x.get("cf"), x.get("st"),
                   x.get("t4"), x.get("ex")))
        hits.extend(near)
    add("锚点段附近捕获到状态事件", len(hits) > 0, "C 行数=%d" % len(hits))

    # --- 候选字段值域概览 ---
    print("\n=== A 行候选字段值域（唯一值数 / top5）===")
    for k in FIELDS:
        c = collections.Counter(x.get(k) for x in A if k in x)
        print("  %-3s 唯一=%-4d top=%s" % (k, len(c), c.most_common(5)))

    # --- 定案判据：锚点段内哪个字段出现「非基线且持续」的值 ---
    print("\n=== 判读结论 ===")
    if hits:
        for k in ["c0", "cf", "st", "t4", "c4", "c8", "dc", "h1", "ex"]:
            vals = collections.Counter(x.get(k) for x in hits if k in x)
            if not vals: continue
            base = collections.Counter(x.get(k) for x in A if k in x).most_common(1)
            basev = base[0][0] if base else None
            special = [(v, n) for v, n in vals.most_common() if v != basev]
            print("  %-3s 锚点内取值=%s  基线=%s  非基线=%s" %
                  (k, vals.most_common(5), basev, special[:4]))
        c0s = set(x.get("c0") for x in hits if isinstance(x.get("c0"), int))
        sts = set(x.get("st") for x in hits if isinstance(x.get("st"), int))
        t4s = set(x.get("t4") for x in hits if isinstance(x.get("t4"), int))
        print("  c0 集合=%s  st 集合=%s  t4 集合=%s" %
              (sorted(c0s)[:12], sorted(sts)[:12], sorted(t4s)[:12]))
        if any(v in (2, 3) for v in c0s):
            print("  -> **`mon+0xCAC0` 在疲惫锚点出现 2/3**：与离线反汇编"
                  "（初始化 1、疲惫分支 cmp #2/#3）一致，可作为 3 状态权重层的状态输入。")
        elif any(v != 0 for v in t4s):
            print("  -> `act+0x408` 在锚点非零：疲惫分支写入的 s16 被捕获，"
                  "可作疲惫时长/阈值输入；仍需与 c0/cf 对照定案状态字。")
        else:
            print("  -> 锚点内未见清晰状态枚举；需对照用户口述时刻，"
                  "或扩大候选（+0xCAC0..+0xCBF4 状态区逐字节扫描）。")
    else:
        print("  锚点附近无 C 行事件 -> 本轮未能定案；检查 C 行是否覆盖主怪槽。")

    print("\n=== 冒烟判据 ===")
    for name, detail in ok: print("  PASS  %s : %s" % (name, detail))
    for name, detail in bad: print("  FAIL  %s : %s" % (name, detail))
    print("  结论：PASS=%d FAIL=%d -> %s" %
          (len(ok), len(bad), "判读链路可用" if not bad else "需排查上述项"))
    print("  提示：请把『怪物进入疲劳』的大致任务内时刻与上面的锚点段对照。")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "02_Workspace/game_p54_lite.txt"))
