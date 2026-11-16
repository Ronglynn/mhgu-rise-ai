#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""analyze_v39_state.py — v39 只读状态探针判读（方案 B）

用法：python 04_RiseAI/tools/analyze_v39_state.py 02_Workspace/game_p54_lite.txt

v39 规则与 v38 逐字节相同，只在 `0xAFF40` 的 A 行追加只读字段：
  c4  = *(u32*)(mon+0xCAC4)   离线反汇编确证：1=怒 / 2=疲（0x1068E08 / 0x1068E2C）
  cf  = *(u8*)(mon+0xCBF1)    怒标志（0x1068E1C 写 1）
  e1  = *(u8*)(mon+0x73E1)    动作/状态号
  dc  = *(u8*)(mon+0x73DC)    长周期状态候选
  h1  = *(u8*)(act+0x1A1)     Hub 状态候选
  st  = *(u8*)(act+0x518)     旧字段（1=怒、2=「疑似疲劳」，P10 未出现 2）

判读目标：一轮实机内定案**哪个字段真能观测到疲劳**，供后续 3 状态权重层使用。
非 v39 日志自动降级为冒烟模式。
"""
import sys, re, json, collections

HEX = {"mon", "sp", "w73", "ip", "w0", "w1", "first", "blk", "pick", "sig", "psig", "c4", "act"}
INT = {"f", "n", "op", "md", "mode", "sub", "p5", "ret", "nc", "d", "delta", "nr",
       "live", "log", "k", "why", "id", "a", "s", "pa", "ps", "st", "r1", "r2", "r3",
       "m", "m1", "m0c", "m0e", "x", "q", "sel", "act", "beg", "begf", "ki", "sw",
       "rep", "v", "noalt", "fail", "ok", "peak", "hub", "depth", "rd", "b1", "sw2",
       "ph", "p2", "cf", "e1", "dc", "h1", "a2", "last",
       "e1", "e0", "r1n", "r0", "n1", "n0", "v1", "v0",
       "ex", "forced", "ex0", "ex1"}


def parse(s):
    d = {}
    for k, v in re.findall(r"(\w+)=(\S+)", s):
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
    raw = open(path, "rb").read().decode("utf-8", "replace")
    lines = raw.splitlines()
    rows = collections.defaultdict(list)
    for ln in lines:
        m = re.search(r"\[rai\] (A|V|BEAT|S|K|E|C|F) (.*)$", ln)
        if m:
            rows[m.group(1)].append(parse(m.group(2)))
    is_v39 = any(("RAI v39" in l or "RAI v40" in l) for l in lines)
    is_v40 = any("RAI v40" in l for l in lines)
    C, F = rows["C"], rows["F"]
    fatal = sum(1 for l in lines if "FATAL" in l)
    A, V, B = rows["A"], rows["V"], rows["BEAT"]
    print("=== v39/v40 状态探针判读：%s ===" % path)
    print("  版本=%s  FATAL=%d  A=%d  V=%d  BEAT=%d" %
          ("v40" if is_v40 else "v39" if is_v39 else "旧日志(冒烟)",
           fatal, len(A), len(V), len(B)))
    if not is_v39:
        print("  非 v39 日志 -> 冒烟完成，不做状态判读。")
        return 0
    if not A:
        print("  无 A 行 -> 无法判读。")
        return 1

    if is_v40:
        print("\n=== F 行（一次性写入事件，用户授权的观测写入）===")
        if F:
            for x in F:
                print("  f=%-7d mon=%s act=%s  ex %s -> %s  c4=%s" %
                      (x.get("f"), x.get("mon"), x.get("act"),
                       x.get("ex0"), x.get("ex1"), x.get("c4")))
        else:
            print("  无 F 行：写入未触发（可能整场都在愤怒，或没有动作开始事件）")
        print("\n=== C 行（每帧状态变化即时捕获，不受 A 采样限制）===")
        csegs = []
        for x in C:
            v = x.get("c4")
            if csegs and csegs[-1][0] == v:
                csegs[-1][2] = x["f"]; csegs[-1][3] += 1
            else:
                csegs.append([v, x["f"], x["f"], 1])
        print("  共 %d 条 C 行 / %d 段：" % (len(C), len(csegs)))
        for v, f0, f1, n in csegs[:30]:
            print("    c4=%-10s f=%7d..%-7d  跨度=%5d 帧  记录=%d" %
                  (v, f0, f1, f1 - f0, n))
        if len(csegs) > 30: print("    ... 共 %d 段" % len(csegs))
        c2 = [s for s in csegs if s[0] == 2]
        print("  ** c4==2（疲惫）段数=%d 最长=%d 帧 **" %
              (len(c2), max((s[2] - s[1] for s in c2), default=0)))
        print("  A 行 ex 分布（写入后实际蓄积值）: %s" %
              collections.Counter(x.get("ex") for x in A).most_common(10))

    FIELDS = ["st", "c4", "cf", "e1", "dc", "h1"]
    print("\n=== A 行候选字段分布 ===")
    for k in FIELDS:
        c = collections.Counter(x.get(k) for x in A)
        print("  %-3s : %s" % (k, c.most_common(10)))

    print("\n=== st(旧) × c4(新) 交叉表 ===")
    cross = collections.Counter((x.get("st"), x.get("c4")) for x in A)
    for (st, c4), n in sorted(cross.items(), key=lambda z: (str(z[0][0]), str(z[0][1]))):
        print("  st=%-4s c4=%-10s : %d" % (st, c4, n))

    # 连续状态段（按 A 行抽样顺序）
    print("\n=== c4 状态段（A 抽样，1=怒 / 2=疲）===")
    segs = []
    for x in A:
        v = x.get("c4")
        if segs and segs[-1][0] == v:
            segs[-1][2] = x["f"]
            segs[-1][3] += 1
        else:
            segs.append([v, x["f"], x["f"], 1])
    for v, f0, f1, n in segs[:40]:
        print("  c4=%-10s f=%6d..%-6d  A行数=%d" % (v, f0, f1, n))
    if len(segs) > 40: print("  ... 共 %d 段" % len(segs))

    # V 行按最近 A 行状态分组
    ast = [(x["f"], x.get("c4"), x.get("st")) for x in A]
    def state_at(f):
        """返回 (最近 A 行的 c4, st)；注意第一个元素是帧号，不能误当状态。"""
        c = [z for z in ast if z[0] <= f]
        return (c[-1][1], c[-1][2]) if c else (None, None)
    print("\n=== V 行按 c4 状态分组 ===")
    g = collections.defaultdict(list)
    for x in V:
        g[state_at(x["f"])[0]].append(x)
    for c4, xs in sorted(g.items(), key=lambda z: str(z[0])):
        if not xs: continue
        print("  c4=%-10s V=%3d  ph2=%3d  rd1=%3d  b1=%2d  落点前3=%s" % (
            c4, len(xs), sum(1 for z in xs if z.get("ph") == 2),
            sum(1 for z in xs if z.get("rd") == 1), sum(1 for z in xs if z.get("b1") == 1),
            collections.Counter(z.get("pick") for z in xs).most_common(3)))

    # 结论：哪个字段出现「2」且能形成持续段；v40 优先用 C 行（每帧，权威）
    print("\n=== 判读结论 ===")
    has2 = {k: sum(1 for x in A if x.get(k) == 2) for k in FIELDS}
    print("  出现值 2 的 A 行数：%s" % has2)
    c4segs = [s for s in segs if s[0] == 2]
    c2segs = [s for s in (csegs if is_v40 else []) if s[0] == 2]
    print("  c4==2 段：A 行 %d 段 / C 行 %d 段（C 行每帧，权威）" %
          (len(c4segs), len(c2segs)))
    if is_v40 and F:
        print("  一次性写入已发生：ex %s -> %s；若 C 行随后出现 c4==2 段 -> "
              "**`act+0x5D82` 蓄积 → 游戏自然判定疲惫 → `mon+0xCAC4=2` 全链路确证**。" %
              (F[0].get("ex0"), F[0].get("ex1")))
    if c2segs or c4segs:
        print("  -> **mon+0xCAC4 观测到疲惫状态**，可作为 3 状态权重层的状态输入。")
    elif any(has2[k] for k in FIELDS):
        print("  -> c4 未形成 2 段，但其它候选出现 2；需对照用户观察到的疲劳时段复核。")
    else:
        print("  -> 本场所有候选均未稳定出现 2：需检查 F 行是否写入、")
        print("     `act+0x5D82` 是否为真正的 Exhaust 蓄积字段，")
        print("     或疲惫发生在 C 行上限之后（C 行最多 400 条）。")
    print("  提示：把本场『怪物进入疲劳』的大致时刻（任务结束前多久）与上面的"
          " c4 状态段时间对照，即可定案。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "02_Workspace/game_p54_lite.txt"))
