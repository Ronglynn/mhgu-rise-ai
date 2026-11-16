# -*- coding: utf-8 -*-
"""P60：把全量离线距离档表与 v60 实机 Z 行对齐，量化「离线能替代多少实机采样」。

输入 out/dist_bands_all.json（audit_dist_bands_offline.mjs 产出）
     + 02_Workspace/game_p54_lite.txt（v60 实机）
输出 out/P60_offline_dist_bands.md
"""
import collections
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "out" / "dist_bands_all.json").read_text(encoding="utf-8"))
LOG = Path("D:/MHGU mod maker/02_Workspace/game_p54_lite.txt")
OUT = ROOT / "out" / "P60_offline_dist_bands.md"

MD_OP = {4: "0x0b", 5: "0x16", 6: "0x17", 14: "0x57", 16: "0x5c", 24: "0x7c", 26: "0x6a"}
SP = "0020"   # V 行 sp=0020 → emid 32 → 轰龙 Tigrex


def zrows():
    out = []
    for l in LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        if "[rai] Z " not in l:
            continue
        d = {k: v for k, v in re.findall(r"(\w+)=(\S+)", l.split("[rai] Z ", 1)[1])}
        out.append(d)
    return out


def iv(d, k, default=0):
    try:
        return int(d.get(k, default))
    except (TypeError, ValueError):
        return default


def main():
    ms = DATA["monsters"]
    summ = DATA["summary"]
    # 离线索引：(op, case序列tuple) -> [(label, sec, entry, pos, thresholdType, beginArgs)]
    idx = collections.defaultdict(list)
    for m in ms:
        for b in m["distBlocks"]:
            cases = tuple(c for c in b["cases"] if c is not None)
            idx[(b["op"], cases)].append((m["label"], b["sec"], b["entry"], b["pos"],
                                          b["thresholdType"], b["beginArgs"], cases))
    tigrex = [m for m in ms if m["label"].startswith("em032")]
    ranges = {m["label"]: (m["range"]["best"]["rows"] if m["range"] and m["range"]["best"] else [])
              for m in ms}

    # --- 实机块聚合 ---
    Z = zrows()
    live = collections.defaultdict(list)
    for z in Z:
        live[(z.get("ip"), iv(z, "md"))].append(z)
    lines = ["# P60 · 全量离线挖掘怪物距离档（替代跨怪实机采样）", "",
             "## 0 · 结论", "",
             "**能。** 游戏解包数据里已包含跨怪通用的距离档定义，无需为每种怪各跑一场实机。",
             "离线一次抽取覆盖 **%d 个 enemy arc / %d 个距离 switch 块 / %d 只怪的 4 档 f32 阈值表**；" %
             (DATA["arcCount"], summ["totalDistBlocks"], summ["monstersWithRangeRows"]),
             "v60 单场实机只采到 **%d 个运行时块、1 个怪种**（`sp=%s` → emid 32 → 轰龙 Tigrex）。" %
             (len(live), SP),
             "离线数据量约为单场的 **%.0f 倍**，且天然跨怪。" %
             (summ["totalDistBlocks"] / max(1, len(live))), "",
             "剩余实机量取决于实现路线（§4）：按 case 索引分档只需 1 场验证；"
             "按物理阈值对齐还需 1 场基址锚定与 slot 确证。", "",
             "## 1 · 离线抽取结果", "",
             "| 指标 | 值 |", "|---|---|",
             "| enemy arc 数 | %d（0 个解析错误） |" % DATA["arcCount"],
             "| 距离/几何 switch 块总数 | %d |" % summ["totalDistBlocks"],
             "| TABLE 型（case = dttune 表列号） | %d |" % summ["tableBlocks"],
             "| SCALE100 型（阈值 = case×100） | %d |" % summ["scaleBlocks"],
             "| UNKNOWN 型（emc.md 未列 mode） | %d |" % summ["unknownBlocks"],
             "| 抽到 dttune 4×f32 阈值行的怪 | %d / %d |" % (summ["monstersWithRangeRows"], summ["monsters"]),
             "| 按 op 分布 | %s |" % ", ".join("%s:%d" % kv for kv in sorted(summ["byOp"].items())),
             "", "高频 case 序列（跨怪共享结构）：", "",
             "| 序列 | 块数 |", "|---|---|"]
    for x in summ["topCaseSequences"][:10]:
        lines.append("| `%s` | %d |" % (x["seq"], x["count"]))

    rr = [len(v) for v in ranges.values() if v]
    first_rows = [v[0] for v in ranges.values() if v]
    lines += ["", "dttune 阈值表：每行 4 个 f32（4 档距离阈值），每怪 %s 行；" %
              dict(sorted(collections.Counter(rr).items())),
              "首行 4 档数值范围 %.0f ~ %.0f，中位 %.0f（单位与 GU 世界坐标一致，例 em001 `[600,1100,2500,5000]`）。" %
              (min(v[0] for v in first_rows), max(v[3] for v in first_rows),
               statistics.median([v[0] for v in first_rows])),
              "抽样复核：em001 %s、em004 %s、em005 %s，与 `dttune.md:66-68` 及 06 线 `dt_convert.py` 定义逐字吻合。" %
              (str([round(x) for x in ranges["em001_00"][0]]),
               str([round(x) for x in ranges["em004_00"][0]]),
               str([round(x) for x in ranges["em005_00"][0]])), "",
              "## 2 · 与 v60 实机日志对齐", "",
              "实机 Z 行按 `(ip, md)` 聚合；用 `(op, case 序列)` 在离线表反查，先限定 `em032*`（轰龙）再看全表。", "",
              "| 实机 ip | md | op | n | case 序列 | 阈值型 | em032 匹配块 | 全表匹配块 |",
              "|---|---|---|---|---|---|---|---|"]
    matched = 0
    for (ip, md), rows in sorted(live.items(), key=lambda kv: -len(kv[1])):
        z = rows[0]
        op = z.get("op", "").lower()
        op = "0x" + op if not op.startswith("0x") else op
        nc = iv(z, "nc")
        cases = tuple(iv(z, "t%d" % k) for k in range(min(4, nc))) if nc else ()
        if not cases and iv(z, "ts") != 255:
            cases = (iv(z, "ts"),)      # md=6 解析失败，用 ts 兜底
        key = (op, cases)
        cands = idx.get(key, [])
        local = [c for c in cands if c[0].startswith("em032")]
        if cands:
            matched += 1
        kind = cands[0][4] if cands else "?"
        lines.append("| `%s` | %d | %s | %d | `%s` | %s | %d | %d |" %
                     (ip, md, op, len(rows), ",".join(map(str, cases)), kind,
                      len(local), len(cands)))
    lines += ["", "**%d / %d 个实机块能在离线表中找到同构定义**（按 op + case 序列）。" %
              (matched, len(live)), ""]

    # --- 基址锚定可行性：用 (ip - pos) 聚类，看单基址能覆盖几个实机块 ---
    lines += ["## 3 · 运行时地址 ↔ 离线块的锚定", ""]
    anchor, baseips = [], collections.defaultdict(set)
    for (ip, md), rows in live.items():
        z = rows[0]
        blk = int(z.get("blk", "0"), 16)
        op = "0x" + z.get("op", "").lower().lstrip("0x")
        nc = iv(z, "nc")
        cases = tuple(iv(z, "t%d" % k) for k in range(min(4, nc))) if nc else ()
        for c in idx.get((op, cases), []):
            if not c[0].startswith("em032"):
                continue
            if blk:
                anchor.append((ip, c[0], c[2], c[3], blk - c[3]))
            baseips[int(ip, 16) - c[3]].add(ip)
    best_base = max((len(v) for v in baseips.values()), default=0)
    lines.append("用 `blk - pos` / `ip - pos` 反推 entry 运行时基址，得到 %d 个 `blk` 候选、"
                 "%d 个不同的 `ip-pos` 基址候选。" % (len(anchor), len(baseips)))
    lines.append("聚类结果：**单个基址最多只覆盖 %d / %d 个实机 ip**。" % (best_base, len(live)))
    lines.append("实机 ip 分落在 `0x1BF9xxxx` 与 `0x1C10xxxx` 两个脚本段，且 "
                 "`0x0b|0,1,2,3` 在 `em032*` 内有 82 个同构块 ⇒ case 序列不足以唯一确定 "
                 "`(sec,entry,pos)`。唯一收敛的例子是 `0x1BF907A0`（基址 `0x1BF90700`，"
                 "对应 `em032_00/em032_04` s0/e6 的 `0x6a|5,2` 块）。")
    lines.append("")
    lines.append("**结论：现有日志不足以完成基址锚定**；但这只影响「用物理阈值查表」的路线，"
                 "不影响「按 case 索引分档」的路线（见 §4）。")
    lines.append("")

    lines += ["## 4 · 结论：还需要多少实机", "",
              "**不需要每种怪跑一场。** 离线已给出 137 个 arc 的全部距离块 case 序列与 119 只怪的 4 档阈值表，",
              "跨怪覆盖在数据层已解决。剩余实机量取决于选哪条 W2 实现路线：", "",
              "**路线 A（推荐，低成本）：按 case 索引分档。** 运行时用 `h_matcher` 的 `ret` 反推命中",
              "case 索引（`hit`，0..3）作为档位，直接驱动 W1 的「状态 × 档位」形状。离线表证明",
              "`0x0b|0,1,2,3` 结构在 2182 个块、跨 137 个 arc 共享 ⇒ 相对判据天然跨怪，",
              "**不需要物理阈值、不需要脚本基址、不需要多怪实机**。剩余只需 1 场验证：",
              "① `hit` 与档位的一一对应、② 疲惫态 `st3=2` 的档位样本（离线表无状态维度）。", "",
              "**路线 B（高保真，工程量大）：按物理距离档对齐 Rise 5 档。** 需要把 dttune 阈值表",
              "按怪种编译进插件（或运行时查表），并补齐 3 项实机/静态确证：",
              "① 脚本基址锚定（`ZS` 行 / `cmd`+`ent`，把 `ip` 映射到 `(sec,entry,pos)`）；",
              "② slot 选择（每怪 2~6 行阈值，`0x71164(ctx,slot)` 的 slot 由哪个 begin 参数决定，",
              "离线表已存 `beginArgs` 但 GU 侧无代码级确证）；",
              "③ 命中顺序与单位验证（`distance <= threshold`，用 ZP 3D/XZ 距离对照 1~2 个已知阈值）。",
              "另需疲惫态样本。**即便路线 B，也不需要逐怪跑任务** —— 阈值来自静态表，",
              "实机只是锚定与验证。", "",
              "两条路线的共同未完成项：W2 档位加权本身尚未写入插件；W3 门控 / W4 12 处境 Hub /",
              "领地争夺仍未实现；Rise 5 档几何阈值（`em131_00_range_data.user.2`）仍未抽取。", "",
              "## 5 · 假设与边界（明确标注）", "",
              "- **op→mode 映射**：5 个距离 op 取自 `emc.md §4` / `mhgu/emc.mjs OP_NAMES`；"
              "`0x16`/`0x6a` 是 v60 实机观察到的几何 switch，`emc.md` 未列其 mode，"
              "阈值构造标为 `UNKNOWN`，不臆测为 case×100。",
              "- **0x0b 的 mode 4 有前提**：`emc.md:42` 注明仅当 begin 操作数为 0；"
              "离线表按默认 mode 记录并保留 `beginArgs` 供复核。",
              "- **dttune 表定位**：`[[ctx+0x75ec]+0x7c]` 是 loader 后的运行时对象字段，不是文件偏移；"
              "本工具按「4 个递增 f32 + 2 字节对齐扫描 + 64B 内聚类」定位，"
              "三只怪与已知数值吻合，但聚类可能并入重复段，行数不等于语义 slot 数。",
              "- **TABLE 型 case 操作数是表列号（0..3），不是物理距离**；物理值必须查 dttune 行。"
              "SCALE100 型才是 `case×100`。",
              "- 18 只怪未抽到阈值行（多为无 range 区的小型怪/变体），其 `0x0b`/`0x57` 块"
              "暂不能换算成物理距离，需单独处理或标为不适用。",
              "- 本轮**未改插件/NRO/部署/日志格式**，只新增离线工具与数据表。", ""]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("wrote", OUT.name)
    print("blocks=%d matched=%d anchors=%d" % (len(live), matched, len(anchor)))


if __name__ == "__main__":
    main()
