#!/usr/bin/env python3
"""ELF32(ARM) -> NRO 转换器，行为对齐 cargo-mhgu-forge 的 nro.rs。

用法: python bin/elf2nro.py <input.elf> <output.nro>
"""
import struct
import sys

PT_LOAD = 1
EM_ARM = 40
SHT_NOTE = 7
NT_GNU_BUILD_ID = 3
ELF_HEADER_SIZE = 52
PHDR_SIZE = 32
PAGE = 0x1000
NRO_START_SIZE = 0x10
NRO_HEADER_SIZE = 0x70


def align_up(v, align):
    return (v + align - 1) & ~(align - 1)


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def read_build_id(elf):
    build_id = bytearray(0x20)
    try:
        e_shoff = u32(elf, 32)
        e_shnum = u16(elf, 48)
        e_shentsize = u16(elf, 46) or 40
    except struct.error:
        return bytes(build_id)
    for k in range(e_shnum):
        sh = e_shoff + k * e_shentsize
        if sh + 20 > len(elf):
            break
        if u32(elf, sh + 4) != SHT_NOTE:
            continue
        note_off = u32(elf, sh + 16)
        try:
            n_namesz = u32(elf, note_off)
            n_descsz = u32(elf, note_off + 4)
            n_type = u32(elf, note_off + 8)
        except struct.error:
            continue
        name_off = note_off + 12
        desc_off = name_off + n_namesz
        if n_type == NT_GNU_BUILD_ID and n_namesz == 4 and elf[name_off:name_off + 4] == b"GNU\0":
            n = min(n_descsz, 0x20)
            build_id[:n] = elf[desc_off:desc_off + n]
    return bytes(build_id)


def elf_to_nro(elf):
    if elf[:4] != b"\x7fELF":
        raise SystemExit("不是 ELF 文件")
    if elf[4] != 1:
        raise SystemExit("需要 32 位 ELF")
    if elf[5] != 1:
        raise SystemExit("需要小端 ELF")
    if u16(elf, 18) != EM_ARM:
        raise SystemExit("不是 ARM ELF")

    e_phoff = u32(elf, 28)
    e_phnum = u16(elf, 44)
    loads = []
    for k in range(e_phnum):
        b = e_phoff + k * PHDR_SIZE
        if u32(elf, b) == PT_LOAD:
            loads.append({
                "offset": u32(elf, b + 4),
                "vaddr": u32(elf, b + 8),
                "filesz": u32(elf, b + 16),
                "memsz": u32(elf, b + 20),
            })
    if len(loads) < 3:
        raise SystemExit(f"PT_LOAD 段不足 3 个（实际 {len(loads)}）")

    seg_off, seg_size = [0, 0, 0], [0, 0, 0]
    total = 0
    for i in range(3):
        size = align_up(loads[i]["filesz"], PAGE)
        seg_off[i] = loads[i]["vaddr"]
        seg_size[i] = size
        total = align_up(total + size, PAGE)

    data = loads[2]
    dfs = align_up(data["filesz"], PAGE)
    bss = align_up(data["memsz"] - dfs, PAGE) if data["memsz"] > dfs else 0

    image = bytearray(total)
    for i in range(3):
        src = loads[i]["offset"]
        n = loads[i]["filesz"]
        dst = seg_off[i]
        image[dst:dst + n] = elf[src:src + n]

    hdr = bytearray(NRO_HEADER_SIZE)
    hdr[0:4] = b"NRO0"
    struct.pack_into("<I", hdr, 0x08, total)
    for i in range(3):
        struct.pack_into("<I", hdr, 0x10 + i * 8, seg_off[i])
        struct.pack_into("<I", hdr, 0x14 + i * 8, seg_size[i])
    struct.pack_into("<I", hdr, 0x28, bss)
    hdr[0x30:0x50] = read_build_id(elf)[:0x20]

    image[NRO_START_SIZE:NRO_START_SIZE + NRO_HEADER_SIZE] = hdr
    return bytes(image)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("用法: python bin/elf2nro.py <in.elf> <out.nro>")
    src, dst = sys.argv[1], sys.argv[2]
    nro = elf_to_nro(open(src, "rb").read())
    open(dst, "wb").write(nro)
    print(f"[ok] {dst}  {len(nro)} B")


if __name__ == "__main__":
    main()
