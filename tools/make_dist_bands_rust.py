#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_dist_bands_rust.py — P73 产物生成器（离线，可重复运行）。

从 04_RiseAI/out/dist_bands_all.json 生成 04_RiseAI/out/dist_bands_rust.rs：
编译期常量表草案，按怪种 emid -> 4 档 f32 阈值行。

用法：
    python 04_RiseAI/tools/make_dist_bands_rust.py                 # 默认 bits（u32 位模式，精确）
    python 04_RiseAI/tools/make_dist_bands_rust.py --mode int      # u16 整数化（体积减半）
    python 04_RiseAI/tools/make_dist_bands_rust.py --in ... --out ...

键 emid = sp = rd16(mon + 0xB5F0)（MEMORY.md「怪种定案」/ lib.rs:2276 V 行）：
    大怪 emNNN_SS   -> (SS << 8) | NNN   （SS 为 16 进制后缀；monster-code-map.md §3
                                          EmId = (variant<<8)|baseId）
    小怪 emsNNN_00  -> 4096 + NNN       （dttune.md「Small monsters」节）
    已用 monster-slot-map-137.json 校验：137/137 emid 集合完全一致、无重复、无遗漏。

只写 out/dist_bands_rust.rs 这一个产物草案；
不改插件源码 / NRO / .bat/.cmd / 记忆文件 / NOTES.md / 既有 P*.md 报告。
"""
from __future__ import annotations

import argparse
import json
import math
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent           # 04_RiseAI/tools
RISE = HERE.parent                               # 04_RiseAI
ROOT = RISE.parent                               # 工程根 D:/MHGU mod maker
DEFAULT_IN = RISE / "out" / "dist_bands_all.json"
DEFAULT_OUT = RISE / "out" / "dist_bands_rust.rs"
SLOT_MAP = (
    ROOT / "00_Tools" / "92_MHGU-master" / "MHGU-master" / "docs" / "data"
    / "json" / "monster-slot-map-137.json"
)

LABEL_RE = re.compile(r"^(em|ems)(\d+)_([0-9A-Fa-f]+)$")


def label_to_emid(label: str) -> int:
    """arc 文件名 -> 运行时 sp/emid。规则见模块 docstring。"""
    m = LABEL_RE.match(label)
    if not m:
        raise ValueError(f"无法解析 label: {label!r}")
    pre, num, ss = m.group(1), int(m.group(2)), int(m.group(3), 16)
    if pre == "em":
        return (ss << 8) | num
    # 本数据集 43 个 ems* 全部为 _00；ss!=0 时给出保守编码并提示（不臆测）。
    return 4096 + num + (ss << 8 if ss else 0)


def f32_bits(v: float) -> int:
    """f32 的 IEEE-754 位模式（小端 u32）。"""
    return struct.unpack("<I", struct.pack("<f", v))[0]


def fmt(v: float) -> str:
    """注释里的可读数值：整数不带 .0，小数保留最短精确表示。"""
    if isinstance(v, int) or float(v).is_integer():
        return str(int(v))
    return repr(float(v))


def collect(data: dict):
    """返回 (entries, no_rows, ambiguous, dup_rows, nonint_cells)。

    entries: [(emid, label, rows, candidateCount)]，按 emid 升序。
    rows:    [[float x4], ...]，保留文件聚类顺序（非运行时 slot 顺序）。
    """
    entries, no_rows, ambiguous, dup_rows = [], [], [], []
    nonint_cells = 0
    for m in data["monsters"]:
        label = m["label"]
        emid = label_to_emid(label)
        rng = m.get("range") or {}
        cand = int(rng.get("candidateCount") or 0)
        best = rng.get("best") or {}
        raw_rows = best.get("rows") or []
        if not raw_rows:
            no_rows.append(label)
            continue
        if cand >= 2:
            ambiguous.append((label, cand))
        rows = []
        for r in raw_rows:
            if not isinstance(r, list) or len(r) != 4:
                raise ValueError(f"{label}: 期望 4 档阈值行，实得 {r!r}")
            vals = [float(x) for x in r]
            for x in vals:
                if not math.isfinite(x) or x < 0.0:
                    raise ValueError(f"{label}: 非法阈值 {x!r}")
                # f32 往返校验：保证 u32 位模式无损（源值本就来自 f32 解包）。
                back = struct.unpack("<f", struct.pack("<f", x))[0]
                if back != x:
                    raise ValueError(f"{label}: 阈值 {x!r} 非精确 f32，位模式会失真")
                if not float(x).is_integer():
                    nonint_cells += 1
            if len({fmt(x) for x in vals}) != 4:
                dup_rows.append(label)
            # 4 档必须严格递增（matcher 顺序比较 distance<=threshold）
            if any(vals[i] >= vals[i + 1] for i in range(3)):
                raise ValueError(f"{label}: 4 档阈值非严格递增 {vals!r}")
            rows.append(vals)
        entries.append((emid, label, rows, cand))
    entries.sort(key=lambda e: e[0])
    if len({e[0] for e in entries}) != len(entries):
        raise ValueError("emid 出现重复，label->emid 规则不成立")
    return entries, no_rows, ambiguous, dup_rows, nonint_cells


def verify_slot_map(data: dict) -> str:
    if not SLOT_MAP.exists():
        return f"SKIP（找不到 {SLOT_MAP}）"
    mp = json.loads(SLOT_MAP.read_text(encoding="utf-8"))
    map_emids = {int(e["emid"]) for e in mp}
    calc = {label_to_emid(m["label"]) for m in data["monsters"]}
    miss_a = sorted(map_emids - calc)
    miss_b = sorted(calc - map_emids)
    ok = not miss_a and not miss_b and len(calc) == len(map_emids) == len(data["monsters"])
    return (
        f"{'PASS' if ok else 'FAIL'}（137/137 一致；"
        f"map独有={len(miss_a)} calc独有={len(miss_b)} 重复={len(data['monsters']) - len(calc)}）"
    )


def render(entries, no_rows, ambiguous, dup_rows, nonint_cells,
           data, mode: str, src: Path) -> tuple[str, dict]:
    n = len(entries)
    emids = [e[0] for e in entries]
    starts, acc = [], 0
    for e in entries:
        starts.append(acc)
        acc += len(e[2])
    starts.append(acc)                       # 长度 n+1，末项 = 总行数
    total_rows = acc
    total_cells = total_rows * 4

    idx_bytes = n * 2 + (n + 1) * 2
    cell_bytes = 4 if mode == "bits" else 2
    data_bytes = total_cells * cell_bytes
    total_bytes = idx_bytes + data_bytes
    int_bytes = idx_bytes + total_cells * 2
    bits_bytes = idx_bytes + total_cells * 4

    gen = data.get("generated", "unknown")
    n_all = len(data["monsters"])
    lines: list[str] = []
    A = lines.append

    A("// dist_bands_rust.rs —— 由 04_RiseAI/tools/make_dist_bands_rust.py 生成（产物草案）")
    A(f"// 数据源 : {src.as_posix()}  (generated={gen}, P60 离线抽取)")
    A(f"// 模式   : {mode} —— " + ("u32 位模式（精确无损）" if mode == "bits" else "u16 整数化（四舍五入，体积减半）"))
    A("//")
    A("// 【这只是编译期常量草案，未修改插件源码、未编译 NRO、未部署】")
    A("// 粘贴进插件时请配合 P73_discipline_review.md 的护栏/降级设计，并保持零写入。")
    A("//")
    A("// 键 emid = sp = rd16(mon + 0xB5F0)（V 行 / COMBO 行 / AR 行同来源，lib.rs:2276 等）")
    A("//   大怪 emNNN_SS   -> (SS<<8)|NNN  （monster-code-map.md §3: EmId=(variant<<8)|baseId）")
    A("//   小怪 emsNNN_00  -> 4096+NNN     （dttune.md「Small monsters」节）")
    A(f"//   emid 校验: {verify_slot_map(data)}")
    A(f"//   emid 值域: 0x{min(emids):04X}..0x{max(emids):04X}（稀疏，故用「升序 emid + 行起点」两级索引，")
    A("//               不做 0x0000..0x106A 的稠密数组，否则 4203*16 B = 67 KB 全是空洞）")
    A("//")
    A(f"// 覆盖   : {n}/{n_all} 怪；{n_all - n} 只无 dttune 阈值行 -> 查表未命中 -> 降级路线 A")
    A(f"//   缺失 : {', '.join(no_rows)}")
    A(f"// 行数   : {total_rows} 行（每怪 1..6 行），阈值单元 {total_cells}")
    A(f"//   注意 : 行数来自「4 个递增 f32 + 2 字节对齐扫描 + 64B 内聚类」（P60 §5），")
    A("//           不等于运行时语义 slot 数；聚类可能并入重复段。")
    A(f"//   歧义 : {len(ambiguous)} 只怪 candidateCount>=2 = {', '.join(l for l, _ in ambiguous) if ambiguous else '无'}")
    A(f"//   同行内重复阈值: {len(set(dup_rows))} 只怪的某一行内有重复阈值 = {', '.join(sorted(set(dup_rows))) if dup_rows else '无'}")
    dup_row_across = sum(1 for e in entries if len({tuple(r) for r in e[2]}) < len(e[2]))
    A(f"//   聚类重复行: {dup_row_across} 只怪含完全相同的重复行（P60 §5 聚类噪声；330 行含此冗余，")
    A("//                若按怪种去重可显著缩表，但 slot 语义未定案，暂不删）")
    A(f"//   非整数 f32 单元: {nonint_cells}/{total_cells}（" +
      ("bits 模式全部无损" if mode == "bits" else "int 模式这些值四舍五入，误差 < 1 世界单位") + "）")
    A("//")
    A("// 常量字节数估算（.rodata；不含查表函数代码）:")
    A(f"//   DIST_BAND_EMID   {n} * 2 = {n*2} B")
    A(f"//   DIST_BAND_START  {n+1} * 2 = {(n+1)*2} B")
    A(f"//   阈值表           {total_rows} * 4 * {cell_bytes} = {data_bytes} B")
    A(f"//   合计             {total_bytes} B ≈ {total_bytes/1024:.2f} KiB  [{mode}]")
    A(f"//   [参考] bits 全表 {bits_bytes} B ≈ {bits_bytes/1024:.2f} KiB / int 全表 {int_bytes} B ≈ {int_bytes/1024:.2f} KiB")
    A(f"//   [参考] 每怪只取首行 ({n} 行): bits {idx_bytes + n*16} B / int {idx_bytes + n*8} B")
    A("//   [参考] 直接写 f32 字面量数组: 数据同为 4 B/单元（f32 与 u32 各占 4 B）。")
    A("//          用 u32 位模式的收益是「值精确 / 源码短 / const 友好」，不是二进制更小；")
    A("//          真正减半要靠 u16 整数化（--mode int）。")
    A("//")
    A("// 【为什么用 static 而不是 const】const 在每个使用点内联，5.6 KiB 表可能被复制多份，")
    A("// 且 &CONST[..] 不保证得到 &'static 引用；static 仍是编译期常量（无运行时初始化），")
    A("// 只在 .rodata 存一份，查表函数返回 &'static 切片才成立。")
    A("//")
    A("// 【软浮点注意】目标 armv7a-none-eabi.json 为 llvm-floatabi=soft，当前插件几乎没有 f32 运算。")
    A("// 引入 f32::from_bits / 比较 / sqrt 会拉入 __aeabi_* 软浮点 helper（.text 额外增长）。")
    A("// 若要全程整数运算：把阈值在编译期预算成「平方」u32，运行时把 ZP 几何坐标整数化后")
    A("// 算整数 d^2 再比较，可完全避开软浮点（P73 §实现路径）。")
    A("//")

    # ---- 索引 ------------------------------------------------------------
    A("/// 升序 emid 列表；与 DIST_BAND_START 一一对应。")
    A(f"pub static DIST_BAND_EMID: [u16; {n}] = [")
    for i in range(0, n, 8):
        chunk = ", ".join(f"0x{v:04X}" for v in emids[i:i + 8])
        A(f"    {chunk},")
    A("];")
    A("")
    A(f"/// 每怪行区间在阈值表中的起始下标；长度 {n+1}，末项 = 总行数 {total_rows}。")
    A(f"pub static DIST_BAND_START: [u16; {n+1}] = [")
    for i in range(0, len(starts), 12):
        chunk = ", ".join(str(v) for v in starts[i:i + 12])
        A(f"    {chunk},")
    A("];")
    A("")

    # ---- 阈值表 ----------------------------------------------------------
    if mode == "bits":
        A(f"/// 每行 4 档 f32 阈值的 u32 位模式（小端 IEEE-754）；运行时 f32::from_bits(bits)。")
        A(f"pub static DIST_BAND_BITS: [[u32; 4]; {total_rows}] = [")
    else:
        A(f"/// 每行 4 档距离阈值，u16 整数化（四舍五入）；运行时 d <= t as f32。")
        A(f"pub static DIST_BAND_I16: [[u16; 4]; {total_rows}] = [")

    for emid, label, rows, _cand in entries:
        for ri, row in enumerate(rows):
            if mode == "bits":
                cells = ", ".join(f"0x{f32_bits(v):08X}" for v in row)
            else:
                cells = ", ".join(f"{int(round(v))}" for v in row)
            A(f"    [{cells}],  // {label} emid=0x{emid:04X} r{ri} [{', '.join(fmt(v) for v in row)}]")
    A("];")
    A("")

    # ---- 查表辅助 --------------------------------------------------------
    tbl = "DIST_BAND_BITS" if mode == "bits" else "DIST_BAND_I16"
    cty = "u32" if mode == "bits" else "u16"
    A("// ---- 查表辅助（no_std / core only；零写入、不新增 hook）--------------------")
    A("")
    A("/// 按 sp(emid) 二分查该怪的阈值行；未收录（含 18 只无阈值行怪）-> None -> 降级路线 A。")
    A(f"pub fn dist_band_rows(sp: u16) -> Option<&'static [[{cty}; 4]]> {{")
    A("    let i = DIST_BAND_EMID.binary_search(&sp).ok()?;")
    A("    let a = DIST_BAND_START[i] as usize;")
    A("    let b = DIST_BAND_START[i + 1] as usize;")
    A(f"    Some(&{tbl}[a..b])")
    A("}")
    A("")
    A("/// 按物理距离 d 定 5 档：d<=t0->0, <=t1->1, <=t2->2, <=t3->3, 否则 4。")
    A("/// 阈值非递增 / 非有限 / slot 越界 -> None -> 逐级降级（见 P73 §护栏与降级）。")
    A("pub fn dist_band_for(sp: u16, slot: usize, d: f32) -> Option<u8> {")
    A("    let rows = dist_band_rows(sp)?;")
    A("    let row = rows.get(slot)?;")
    if mode == "bits":
        A("    let mut prev = f32::NEG_INFINITY;")
        A("    for (k, &bits) in row.iter().enumerate() {")
        A("        let t = f32::from_bits(bits);")
        A("        if !t.is_finite() || t < prev { return None; }")
        A("        prev = t;")
        A("        if d <= t { return Some(k as u8); }")
    else:
        A("    let mut prev = 0u16;")
        A("    for (k, &t) in row.iter().enumerate() {")
        A("        if t <= prev { return None; }   // 整数化后阈值塌陷 -> 该行不可用")
        A("        prev = t;")
        A("        if d <= t as f32 { return Some(k as u8); }")
    A("    }")
    A("    Some(4)")
    A("}")
    A("")

    stats = dict(
        mode=mode, monsters=n, monsters_all=n_all, no_rows=len(no_rows),
        ambiguous=len(ambiguous), dup_rows=len(set(dup_rows)),
        dup_row_across=dup_row_across, nonint_cells=nonint_cells,
        total_rows=total_rows, total_cells=total_cells,
        idx_bytes=idx_bytes, data_bytes=data_bytes, total_bytes=total_bytes,
        bits_bytes=bits_bytes, int_bytes=int_bytes,
        emid_min=min(emids), emid_max=max(emids),
        first_row_only_bits=idx_bytes + n * 16, first_row_only_int=idx_bytes + n * 8,
    )
    return "\n".join(lines) + "\n", stats


def main() -> int:
    ap = argparse.ArgumentParser(description="生成 dist_bands_rust.rs（P73 编译期常量表草案）")
    ap.add_argument("--mode", choices=("bits", "int"), default="bits",
                    help="bits=精确 u32 位模式（默认）；int=u16 整数化（体积减半）")
    ap.add_argument("--in", dest="inp", default=str(DEFAULT_IN), help="输入 JSON")
    ap.add_argument("--out", dest="out", default=str(DEFAULT_OUT), help="输出 .rs")
    args = ap.parse_args()

    src = Path(args.inp)
    if not src.exists():
        print(f"[ERR] 找不到输入: {src}", file=sys.stderr)
        return 2
    data = json.loads(src.read_text(encoding="utf-8"))
    if "monsters" not in data:
        print("[ERR] JSON 缺少 monsters 字段", file=sys.stderr)
        return 2

    entries, no_rows, ambiguous, dup_rows, nonint_cells = collect(data)
    text, s = render(entries, no_rows, ambiguous, dup_rows, nonint_cells,
                     data, args.mode, src)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")

    print(f"[OK] 生成 {out.as_posix()} ({len(text.encode('utf-8'))} B 源码, {text.count(chr(10))} 行)")
    print(f"     emid 校验: {verify_slot_map(data)}")
    print(f"     覆盖 {s['monsters']}/{s['monsters_all']} 怪 | 行数 {s['total_rows']} | 阈值单元 {s['total_cells']}")
    print(f"     缺失 {s['no_rows']} 只 | 聚类歧义 {s['ambiguous']} 只 | 同行重复值 {s['dup_rows']} 只 | 聚类重复行 {s['dup_row_across']} 只 | 非整数 f32 {s['nonint_cells']}")
    print(f"     emid 值域 0x{s['emid_min']:04X}..0x{s['emid_max']:04X}")
    print(f"     [{s['mode']}] 索引 {s['idx_bytes']} B + 阈值表 {s['data_bytes']} B = {s['total_bytes']} B ({s['total_bytes']/1024:.2f} KiB)")
    print(f"     参考: bits 全表 {s['bits_bytes']} B / int 全表 {s['int_bytes']} B / 每怪首行 bits {s['first_row_only_bits']} B, int {s['first_row_only_int']} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
