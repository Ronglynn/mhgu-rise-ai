#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""locate_tired_base.py — 重新定位疲惫/发怒分发函数的 r4/r7 基址（纯离线）

背景（P12 实机）：把 `mon+0xCAC0/+0xCAC4/+0xCAC8`、`act+0x408`、
`act+0x5D82` 当状态字/减气蓄积全部失败。推测 `0x1068dd8` 系列函数里的
`r4`/`r7` **不是 mon**，而是某个 manager / 子对象；以前把相对 r4 的偏移
直接套到 `0xAFF40` 的 a0(=mon) 上，导致候选全错。

数据源 refs/hpbar/main_text_decomp.bin（GU NSO0 text，文件偏移 == main+0x...）。
输出：函数入口、r4/r7 赋值来源、疲惫分支全部指令、所有 BL 调用者及参数。
"""
import os
import struct
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_LITTLE_ENDIAN

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "refs", "hpbar", "main_text_decomp.bin")
b = open(BIN, "rb").read()
W = list(struct.unpack("<%dI" % (len(b) // 4), b))
md = Cs(CS_ARCH_ARM, CS_MODE_ARM | CS_MODE_LITTLE_ENDIAN)
md.detail = True


def is_push_lr(w):
    return (w & 0xFFFF4000) == 0xE92D4000


def entry_before(addr, back=0x3000):
    for a in range(addr & ~3, max(0, addr - back), -4):
        if is_push_lr(W[a // 4]):
            return a
    return None


def next_entry(addr, fwd=0x2000):
    for a in range((addr & ~3) + 4, min(len(b), addr + fwd), 4):
        if is_push_lr(W[a // 4]):
            return a
    return addr + fwd


def dis(a0, a1):
    return list(md.disasm(b[a0:a1], a0))


def fmt(insns, lo=None, hi=None):
    out = []
    for i in insns:
        if (lo is not None and i.address < lo) or (hi is not None and i.address > hi):
            continue
        out.append("  %08X  %-9s %s" % (i.address, i.mnemonic, i.op_str))
    return "\n".join(out)


def bl_callers(target):
    """扫描全 text 段，找 BL 到 target 的调用点。"""
    res = []
    for a in range(0, len(b) - 4, 4):
        w = W[a // 4]
        if (w & 0x0F000000) != 0x0B000000:
            continue
        imm = w & 0x00FFFFFF
        if imm & 0x00800000:
            imm -= 0x01000000
        if a + 8 + imm * 4 == target:
            res.append(a)
    return res


def reg_source(insns, reg, upto=None):
    """列出 insns 中写 reg 的指令（找基址来源）。"""
    hits = []
    for i in insns:
        if upto is not None and i.address > upto:
            break
        ops = i.op_str.split(",")
        if ops and ops[0].strip() == reg and i.mnemonic not in ("cmp", "tst", "teq"):
            hits.append("    %08X  %-9s %s" % (i.address, i.mnemonic, i.op_str))
    return "\n".join(hits[-12:])


def main():
    print("=== 1) 0x1068dd8 所在函数 ===")
    e = entry_before(0x1068DD8)
    n = next_entry(e) if e else 0x1069200
    print("entry=+%08X first=%08X  next_entry=+%08X" %
          (e or 0, W[(e or 0) // 4], n))
    insns = dis(e, min(n, e + 0xC00))
    print("\n--- 入口后 40 条（看 r4/r7 来源）---")
    print(fmt(insns[:40]))
    for r in ("r0", "r1", "r4", "r5", "r7", "r8"):
        src = reg_source(insns[:80], r)
        if src:
            print("\n--- %s 写入点 ---\n%s" % (r, src))

    print("\n=== 2) 疲惫分发 0x1068DD8..0x1068FA0 全部指令 ===")
    print(fmt(dis(0x1068DD8, 0x1068FA4)))

    print("\n=== 3) 0x106873C 附近（旧「初始化 1」推断处）===")
    print(fmt(dis(0x10686F0, 0x10687B0)))

    print("\n=== 4) BL 调用者 ===")
    for t in (0x1068DD8, 0x1069D8C, 0x106AEF0, 0x106B04C):
        cs = bl_callers(t)
        print("\n  target +%08X : %d 个调用点 %s" %
              (t, len(cs), ["+%X" % x for x in cs[:12]]))
        for c in cs[:6]:
            ce = entry_before(c)
            print("    call=+%08X entry=+%08X" % (c, ce or 0))
            if ce:
                seg = dis(ce, c + 8)
                print("      入口后 12 条:\n" + fmt(seg[:12]))
                print("      call 前 16 条:\n" + fmt(seg[-18:-2]))

    print("\n=== 5) 0x106AFDC 附近（HP 比值 rage 管线）===")
    print(fmt(dis(0x106AF90, 0x106B020)))


if __name__ == "__main__":
    main()
