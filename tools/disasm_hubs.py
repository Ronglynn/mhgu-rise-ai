"""离线反汇编 GU 状态 Hub 调用者：找出每个 bl 0x76154 的 kind 与函数入口首字。

零风险、不需要实机。数据源 refs/hpbar/main_text_decomp.bin（GU NSO0 text，
文件偏移 == hook offset == main+0x...）。

注意：main.text 里混有字面量池/数据，不能从 0x75000 连续反汇编（capstone 会中断），
必须按每个 `push {..., lr}` 函数入口分段反汇编。

输出：0x75000..0x77000 区间内所有 bl 0x76154 的调用点、所属函数入口、
入口首字（判断 IPS32 跳板）、调用点前 r2(kind)/r1(act)/r3 的装载值。
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

TARGET = 0x76154
LO, HI = 0x75000, 0x77000

# push {..., lr}: E92D 4?? 且 bit14(lr)=1 → 0xE92D4xxx
entries = [a for a in range(LO, HI, 4)
           if (W[a // 4] & 0xFFFF4000) == 0xE92D4000]
print(f"=== 0x75000..0x77000 内 push-lr 函数入口 {len(entries)} 个 ===\n")


def disasm_range(start, end):
    return list(md.disasm(b[start:end], start))


def last_mov(insns, idx, regname, back=24):
    """找 idx 之前最近一条 mov rN,#imm，返回 imm 或 None。"""
    for i in reversed(insns[max(0, idx - back):idx]):
        if i.mnemonic in ("mov", "movw", "movs") and len(i.operands) >= 2 \
                and i.op_str.startswith(regname + ", #"):
            try:
                return int(i.op_str.split("#")[1].split(",")[0], 0)
            except ValueError:
                return None
    return None


rows = []
for n, e in enumerate(entries):
    nxt = entries[n + 1] if n + 1 < len(entries) else e + 0x100
    insns = disasm_range(e, min(nxt, e + 0x180))
    for k, i in enumerate(insns):
        if i.mnemonic == "bl" and f"#{TARGET:x}" in i.op_str.replace("0x", ""):
            kind = last_mov(insns, k, "r2")
            act = last_mov(insns, k, "r1")
            r3 = last_mov(insns, k, "r3")
            rows.append((e, W[e // 4], i.address, kind, act, r3))

print(f"=== bl 0x76154 调用点 {len(rows)} 处 ===")
for e, first, call, kind, act, r3 in rows:
    print(f"  entry +{e:06X} first={first:08X}  call=+{call:06X}"
          f"  r2(kind)={kind}  r1(act)={act}  r3={r3}")

print("\n=== 12 个候选 Hub 入口首字（静态镜像）===")
sites = [0x76154, 0x75224, 0x752EC, 0x75338, 0x75394, 0x753EC,
         0x75444, 0x754B8, 0x75510, 0x75574, 0x76908, 0x76984]
for s in sites:
    i = next(iter(disasm_range(s, s + 4)), None)
    print(f"  +{s:06X} = {W[s//4]:08X}   {'<' + i.mnemonic + ' ' + i.op_str + '>' if i else ''}")

print("\n=== 三个候选 Hub 入口正文 ===")
for s in (0x75338, 0x75394, 0x76908):
    nxt = min([e for e in entries if e > s] + [s + 0xC0])
    print(f"\n--- +{s:06X} .. +{nxt:06X} ---")
    for i in disasm_range(s, nxt):
        mark = "   <<< bl 0x76154" if i.mnemonic == "bl" and "76154" in i.op_str else ""
        print(f"  {i.address:06X}  {i.mnemonic:<8} {i.op_str}{mark}")
