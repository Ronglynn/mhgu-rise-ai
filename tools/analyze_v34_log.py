#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_v34_log.py — v34「EMC 抽选层只读探针」实机判据

用法：python tools/analyze_v34_log.py 02_Workspace/game_p54.txt

回答四个工程问题：
  1. 0x8e144 / 0x82f80 能否安全安装 5 参 / 3 参 hook（首字 E92D4FF0）；
  2. 调用频率、单帧峰值、重入深度 —— 该层能否常驻 hook；
  3. op==0x02 && mode==0 的抽选块是否活跃（这是通用 prev 否决的作用面）；
  4. matcher 的 ip 脚本字节 / ret 分支偏移 / 与主怪 +0x73E0 落盘的关联。

判据是「可行性」而非「效果」：本版零写入，游戏行为应为原版。
"""
import re
import sys
import json
import collections
from pathlib import Path

TAGS = ("M", "X", "Q", "A", "BEAT", "INSTALL", "SKIP", "SITE", "MON", "FATAL")


INT_HEX = {"mon", "sp", "w73", "ip", "w0", "w1", "op", "first"}
INT_DEC = {"f", "n", "mode", "p5", "ret", "depth", "sel", "log", "a", "s",
           "pa", "ps", "st", "id", "r1", "r2", "r3", "m", "x", "q", "peak",
           "hub", "op02", "mode0", "dist", "state", "other", "ret0", "retneg",
           "a2", "hooks", "sum"}


def parse_line(s):
    d = {}
    for k, v in re.findall(r"(\w+)=(\S+)", s):
        try:
            if k in INT_HEX:
                d[k] = int(v, 16)
            elif k in INT_DEC:
                d[k] = int(v, 0)
            else:
                d[k] = v          # b / last / 说明性等保持字符串
        except ValueError:
            d[k] = v
    return d


def main(path):
    p = Path(path)
    if not p.exists():
        print(f"ERROR: {path} not found")
        return 1
    lines = p.read_bytes().decode("utf-8", "replace").splitlines()
    rows = {t: [] for t in TAGS}
    banner = []
    for ln in lines:
        if "[rai] =====" in ln:
            banner.append(ln.strip())
        m = re.search(r"\[rai\] (.*)$", ln)
        if not m:
            continue
        s = m.group(1)
        for t in TAGS:
            if s.startswith(t + " "):
                d = parse_line(s)
                if t in ("INSTALL", "SKIP", "SITE", "MON", "FATAL") or "f" in d:
                    rows[t].append(d)
                break
        if "FATAL" in ln and "[rai]" not in ln:
            rows["FATAL"].append({"raw": ln[:180]})
    fatal = len(rows["FATAL"]) + sum(1 for ln in lines if "FATAL" in ln and "[rai]" not in ln)

    M, X, Q, A, BEAT = rows["M"], rows["X"], rows["Q"], rows["A"], rows["BEAT"]
    is_v34 = any("RAI v34" in b for b in banner)

    print("=" * 78)
    print("v34 EMC 抽选层只读探针 —— 实机判据")
    print("=" * 78)
    print(f"日志：{p}  行数={len(lines)}  banner={banner[:1]}")
    print(f"M={len(M)} X={len(X)} Q={len(Q)} A={len(A)} BEAT={len(BEAT)}  FATAL={fatal}")
    for d in rows["INSTALL"]:
        print("  INSTALL", d)
    for d in rows["SKIP"]:
        print("  SKIP   ", d)
    print()

    checks = []

    def add(name, ok, detail=""):
        checks.append((name, None if not is_v34 else ok, detail))

    last = BEAT[-1] if BEAT else {}
    hub = last.get("hub", 0)
    m_tot = last.get("m", 0)
    x_tot = last.get("x", 0)
    q_tot = last.get("q", 0)
    a_tot = last.get("a", 0)
    sel = last.get("sel", 0)
    dist = last.get("dist", 0)
    state = last.get("state", 0)
    other = last.get("other", 0)
    peak = last.get("peak", 0)
    depth = last.get("depth", 0)
    frames = last.get("f", 0)

    add("零 FATAL", fatal == 0, f"FATAL={fatal}")
    add("4 hook 全装（hub=15）", hub == 15, f"hub={hub}（1=matcher 2=interp 4=landing 8=start）")
    add("matcher 有调用", m_tot > 0, f"m={m_tot}")
    add("解释器入口有调用", x_tot > 0, f"x={x_tot}")
    add("落盘 / 动作开始基准非空", q_tot > 0 and a_tot > 0, f"q={q_tot} a={a_tot}")
    add("**op02 && mode0 抽选块活跃**", sel > 0,
        f"sel={sel}（占 matcher {100*sel/max(m_tot,1):.1f}%）-> 通用 prev 否决的作用面")
    add("无 SKIP（4 hook 首字全为标准 prologue）", len(rows["SKIP"]) == 0,
        f"SKIP={len(rows['SKIP'])} 行；SITE 行={len(rows['SITE'])}")
    add("5 参栈参数未破坏（p5 有非 0 且无异常）",
        any(d.get("p5", 0) != 0 for d in M) if M else None,
        f"p5 分布={collections.Counter(d.get('p5') for d in M).most_common(6)}")
    add("重入深度 <= 1（无嵌套）", depth <= 1 if depth else None, f"depth_max={depth}")
    # 工程经验阈值：单帧 matcher 峰值过高则此层不适合常驻 hook
    add("单帧 matcher 峰值可接受（<=200）", 0 < peak <= 200 if peak else None,
        f"peak={peak}/帧，m/帧={m_tot/max(frames,1):.2f}（经验阈值，需体感校准）")

    print("-" * 78)
    print("判据：")
    for name, ok, detail in checks:
        mark = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
        print(f"  [{mark:4}] {name:<42} {detail}")
    nf = sum(1 for _, ok, _ in checks if ok is False)
    print()

    # --- 分布 ---
    print("-" * 78)
    print("BEAT 累计（末次）：")
    print(f"  m={m_tot} x={x_tot} q={q_tot} a={a_tot} frames={frames}")
    print(f"  op 分类：sel(op02&mode0)={sel}  dist={dist}  state={state}  other={other}")
    print(f"  op02 总数={last.get('op02', 0)}  mode0 总数={last.get('mode0', 0)}  "
          f"ret0={last.get('ret0', 0)}  retneg={last.get('retneg', 0)}")
    print(f"  单帧 matcher 峰值={peak}  重入峰值={depth}  平均 m/帧={m_tot/max(frames,1):.2f}")
    print()

    if M:
        ops = collections.Counter(d.get("op") for d in M)
        modes = collections.Counter(d.get("mode") for d in M)
        rets = collections.Counter(d.get("ret") for d in M)
        p5s = collections.Counter(d.get("p5") for d in M)
        print("M 行采样分布：")
        print(f"  op    top={[(hex(k) if isinstance(k, int) else k, v) for k, v in ops.most_common(10)]}")
        print(f"  mode  top={modes.most_common(10)}")
        print(f"  ret   top={rets.most_common(10)}")
        print(f"  p5    top={p5s.most_common(8)}")
        selrows = [d for d in M if d.get("sel") == 1]
        print(f"  sel 行={len(selrows)}，样例：")
        for d in selrows[:5]:
            print(f"    f={d.get('f')} mon={d.get('mon'):08X} sp={d.get('sp'):04X} "
                  f"op={d.get('op'):02X} mode={d.get('mode')} b={d.get('b')} ret={d.get('ret')} w73={d.get('w73'):08X}")
        # 实机定案：matcher 的 a1 指向的是 block 指令流里的 **sub 字节**，
        # 不是 opcode（op 由 a2 传入）。所以判据是 sub 必须符合 EMC 文法
        # {00 begin, 01 case, 02 default, FF endblock}。
        good = sum(1 for d in M if str(d.get("b", ""))[:2] in ("00", "01", "02", "FF"))
        print(f"  b[0]=sub 文法自洽（00/01/02/FF）：{good}/{len(M)}")
        subs = collections.Counter(str(d.get("b", ""))[:2] for d in M)
        print(f"  sub 分布：{subs.most_common()}")
        # op02 块的 case 值（b[1]）形似权重百分比，是「op02=加权池」的实机旁证
        cases = []
        for d in M:
            b = str(d.get("b", ""))
            if len(b) >= 4 and b[:2] == "01" and d.get("op") == 0x02:
                try:
                    cases.append(int(b[2:4], 16))
                except ValueError:
                    pass
        if cases:
            print(f"  op02 case 值（b[1]）top={collections.Counter(cases).most_common(12)}")
            print("    （离线 EMC 表 130/130 的 op02 块 case 和恒 100；此处是运行时旁证，"
                  "matcher s16 为几何值 -> 加权语义仍未 100% 闭环）")
        print()

    if Q and A:
        qm = [d for d in Q if d.get("r3") == 0]
        # v34 实机修正旧口径：r3==0 并不等于「动作提交」，大量是 r1=0 且 w0==w1 的空请求
        empt = [d for d in qm if d.get("r1") == 0 and d.get("w0") == d.get("w1")]
        real = [d for d in qm if d not in empt]
        print("落盘 / 动作基准：")
        print(f"  Q(r3=0)={len(qm)} / Q 采样={len(Q)}；A 采样={len(A)}")
        print(f"  **空请求(r1=0 且 w0==w1)={len(empt)}/{len(qm)}，真实提交={len(real)}**")
        print(f"    -> 修正 v31/v33 旧口径：动作提交应加 `r1!=0`/`w0!=w1` 过滤，"
              f"不能只按 mode==0")
        print(f"  Q r1 分布={collections.Counter(d.get('r1') for d in qm).most_common(8)}")
        print(f"  A id 分布={collections.Counter(d.get('id') for d in A).most_common(8)}")
        amap = {d.get("f"): d for d in A}
        hit = sum(1 for d in real if d.get("f") in amap
                  and d.get("r1") == amap[d["f"]].get("a")
                  and d.get("r2") == amap[d["f"]].get("s"))
        print(f"  同帧 真实提交(r1,r2)==A(a,s)：{hit}/{len(real)}")
        qf = [int(d["f"]) for d in Q]
        af = [int(d["f"]) for d in A]
        print(f"  采样窗口：Q={min(qf)}..{max(qf)}  A={min(af)}..{max(af)}"
              f"  -> 配额错位，同帧命中率低属采样原因，不作机制判据")
        print()

    print("-" * 78)
    if not is_v34:
        verdict = "非 v34 日志（冒烟）：仅做解析健壮性检查，未判 FAIL"
    elif nf == 0 and fatal == 0:
        verdict = ("可行性通过 -> 抽选层可挂钩、op02 抽选块活跃；"
                   "下一步才设计通用 prev 否决（本版仍为纯只读）")
    else:
        verdict = "存在 FAIL -> 回退 v31 纯只读，或改走路线 B（离线改表）"
    print(f"结论：FAIL={nf}  {verdict}")

    out = p.parent / "v34_emcselect_events.json"
    try:
        out.write_text(json.dumps({k: v for k, v in rows.items()}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"事件快照：{out}")
    except Exception as e:
        print(f"快照写入失败：{e}")
    return 0 if nf == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "02_Workspace/game_p54.txt"))
