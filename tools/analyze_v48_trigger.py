# -*- coding: utf-8 -*-
"""v48 判读：减气（Exhaust）触发链一次定案。

关键链路（P29 离线反汇编，字节级）：
  getter 0x71078 = *(em+0x75EC)+0x64 ; [getter+0x44] = res+0xA8 = Exhaust 块
  act = *(em+0x1428)
    +0x5D82 counter (日志 ex)
    +0x5D84 thr     当前阈值
    +0x5D88 衰减计时器 float (d5 是低 16 位)
    +0x5D8C proc    已触发次数
    +0x4D8  amt     本次动作减气点数
    +0x5E08 flg     状态位（毒/眠/麻/气绝…；减气为瞬时判定）
  0x9A470 -> 0xA30E4 add(em, amount): counter += amount ;
             若 counter >= thr 且 [vt+0x39C]()!=1 返回 1（触发）
  0xA3198 grow: counter=0, proc+1, thr=min(initial+increase*proc, max)
  -> 0xA4130 -> 虚表 +0x1CC 通知 Stamina_low_Start / tired_start

用法: python analyze_v48_trigger.py <log>
"""
import re
import sys
import collections
from pathlib import Path

INT = {"f", "i", "log", "a", "an", "dA", "lowhits", "a1", "cnt", "thr",
       "proc", "amt", "force", "forced", "ret", "st", "t4", "ex", "d5",
       "h1", "e1", "dc", "s3f", "f5c", "p3ca", "p3be", "low", "flg",
       "t5c", "live", "hub"}
ROW = re.compile(r"\[rai\] ([A-Z]+) (.*)$")


def parse(tail):
    d = {}
    for k, v in re.findall(r"(\w+)=(\S+)", tail):
        if k in INT:
            try:
                d[k] = int(v, 0) if v.startswith("0x") else int(v)
            except ValueError:
                d[k] = v
        else:
            d[k] = v
    return d


def main(path):
    lines = Path(path).read_bytes().decode("utf-8", "replace").splitlines()
    rows = collections.defaultdict(list)
    for ln in lines:
        m = ROW.search(ln)
        if m:
            rows[m.group(1)].append(parse(m.group(2)))
    U, R, A, C, N = rows["U"], rows["R"], rows["A"], rows["C"], rows["N"]
    U.sort(key=lambda x: x.get("f", 0) if isinstance(x.get("f"), int) else 0)
    R.sort(key=lambda x: x.get("f", 0) if isinstance(x.get("f"), int) else 0)
    is_v48 = any("RAI v48" in l for l in lines)
    fatal = sum(1 for l in lines if "FATAL" in l)
    install = any("INSTALL h_exh" in l for l in lines)
    skip = any("SKIP h_exh" in l for l in lines)
    site = [l.strip() for l in lines if "SITE +" in l and "A30E4" in l]
    banner = next((l.strip() for l in lines if "RAI v48" in l), "(旧日志)")

    print("=== v48 减气触发链判读 ===")
    print("日志: %s" % path)
    print("banner: %s" % banner[:110])
    print("版本=%s  U=%d R=%d A=%d C=%d N=%d  FATAL=%d" %
          ("v48" if is_v48 else "旧日志(冒烟)", len(U), len(R), len(A),
           len(C), len(N), fatal))
    for l in site[:2]:
        print("  " + l[:130])
    print("  INSTALL h_exh=%s  SKIP h_exh=%s" % (install, skip))

    checks = []

    def add(name, ok, detail):
        checks.append((name, bool(ok), detail))
        print("  [%s] %-38s %s" % ("PASS" if ok else "FAIL", name, detail))

    add("U 行存在（EXH add 被 hook 调用）", len(U) > 0, "U=%d" % len(U))
    add("INSTALL h_exh 成功", install, "SKIP=%s" % skip)
    forced = [x for x in U if x.get("force") == 1]
    add("一次性强制恰好 1 次", len(forced) == 1, "force=1 共 %d" % len(forced))
    if forced:
        fo = forced[0]
        print("  >>> FORCE: f=%s em=%s a1=%s cnt=%s thr=%s amt=%s forced=%s" %
              (fo.get("f"), fo.get("em"), fo.get("a1"), fo.get("cnt"),
               fo.get("thr"), fo.get("amt"), fo.get("forced")))
        add("强制 amount = thr+16",
            isinstance(fo.get("amt"), int) and isinstance(fo.get("thr"), int)
            and fo["amt"] == fo["thr"] + 16,
            "thr=%s amt=%s" % (fo.get("thr"), fo.get("amt")))
        post = [x for x in U if x.get("ret") is not None and
                isinstance(x.get("f"), int) and x["f"] >= fo.get("f", 0)]
        if post:
            p = post[0]
            print("  >>> POST : ret=%s cnt=%s thr=%s proc=%s flg=%s t5c=%s" %
                  (p.get("ret"), p.get("cnt"), p.get("thr"), p.get("proc"),
                   p.get("flg"), p.get("t5c")))
            add("add 返回 1（判定成立）", p.get("ret") == 1,
                "ret=%s" % p.get("ret"))
            # P30 实机：POST 打印紧跟 original! 返回，此时 grow（0xA3198）
            # 尚未执行（它由状态机在后续帧经 0x75F0C 调用）。故 POST 时
            # cnt 被钳到 thr、proc 仍为旧值是**正常时序**，不是失败。
            # grow 是否执行改由下方「proc 出现变化 / thr 有效值」判据验证。
            add("POST 时序正常（cnt 钳到 thr 或归零）",
                p.get("cnt") == fo.get("thr") or p.get("cnt") == 0,
                "cnt=%s thr=%s proc=%s（grow 在后续帧）" %
                (p.get("cnt"), fo.get("thr"), p.get("proc")))
    add("R 行覆盖全场（无条件快照）", len(R) >= 20,
        "R=%d 末帧=%s" % (len(R), max((x.get("f") for x in R
                                     if isinstance(x.get("f"), int)), default=0)))
    thr = [x.get("thr") for x in R if isinstance(x.get("thr"), int)]
    add("thr 有有效值（链路字段生效）", any(0 < v < 0x8000 for v in thr),
        "thr 值域=%s" % (sorted(set(thr))[:8] if thr else []))
    proc = [x.get("proc") for x in R if isinstance(x.get("proc"), int)]
    add("proc 出现变化（grow 递推）", len(set(proc)) >= 2,
        "proc 集合=%s" % sorted(set(proc))[:8])
    add("零 FATAL", fatal == 0, "FATAL=%d" % fatal)
    live = [x.get("live") for x in rows["BEAT"] if isinstance(x.get("live"), int)]
    add("live=1（自保护未熔断）", not live or live[-1] == 1,
        "BEAT.live 末值=%s" % (live[-1] if live else "?"))

    # 触发前后字段差分
    print("\n=== 触发前后 R 行字段差分 ===")
    if forced and R:
        f0 = forced[0].get("f", 0)
        before = [x for x in R if isinstance(x.get("f"), int) and x["f"] < f0]
        after = [x for x in R if isinstance(x.get("f"), int) and x["f"] >= f0]
        keys = ("ex", "thr", "proc", "amt", "flg", "t5c", "st", "t4",
                "d5", "h1", "e1", "dc", "s3f", "f5c", "p3ca", "p3be")
        for k in keys:
            b = {x.get(k) for x in before if k in x}
            a = {x.get(k) for x in after if k in x}
            if a - b:
                print("  %-5s 窗口内新值: %s （窗口前: %s）" %
                      (k, sorted(a - b)[:8], sorted(b)[:8]))
        print("  (窗口内出现新值的字段即为状态切换候选)")
    else:
        print("  无 FORCE 行或无 R 行，跳过差分")

    print("\n=== 结论 ===")
    npass = sum(1 for _, ok, _ in checks if ok)
    print("  PASS=%d / FAIL=%d" % (npass, len(checks) - npass))
    if not is_v48:
        print("  -> 旧日志（v47 及以前）：无 U 行属预期，用于验证降级不崩溃。")
    elif not install and skip:
        print("  -> EXH add 运行时首字不是 push（解释器跳板/版本差异）⇒ 插件已"
              "安全 SKIP，本轮纯只读，无强制触发；R 行仍可用于链路观测。")
    elif forced and any(x.get("ret") == 1 for x in U):
        print("  -> **触发链实机闭环**：EXH add 判定成立、grow 递推 thr、"
              "游戏自己进入疲惫状态。对照用户体感即可定案，随后进 3 状态权重层。")
    elif forced:
        print("  -> 强制已执行但 add 未返回 1（可能 [vt+0x39C] 抑制）。"
              "看 U 行 ret / R 行 thr-proc 轨迹再定，不要重复写状态字。")
    else:
        print("  -> hook 已安装但从未满足条件（看 U 行 a1 / thr / A_N）。"
              "插件保持只读观测。")
    print("  回退：copy 04_RiseAI\\out\\rai_tired_snapshot_v47.nro 覆盖插件 nro")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "04_RiseAI/out/sim_v48_smoke.txt")
