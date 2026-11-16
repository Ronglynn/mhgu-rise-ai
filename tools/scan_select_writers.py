"""离线扫描 GU main.text：定位谁写入 +0x73E0 / +0x73E1（L1 动作号 / 次级状态）。

零风险、不需要实机。数据源 refs/hpbar/main_text_decomp.bin（NSO0 text LZ4 解压）。

思路：
  0x73E0 > 4095，ARM 不能用立即数偏移，必须用 movw rN,#0x73e0 + 寄存器偏移访存。
  1) 找所有 movw rN,#0x73e0 / #0x73e1；
  2) 向后追踪 16 条内 str/strb/strh [rBase,rN]（或 add rT,rBase,rN 后间接写）→ 写入点；
     同理 ldr/ldrb → 读取点（派发器）作对照；
  3) 向前找最近 push {...,lr} 作函数起点；
  4) 全量 BL 调用图，统计每个函数的调用者；
  5) 输出：写入者清单、调用者、是否与 0xAFF40 提交点同函数/相邻。

输出 out/gu_select_writers.json + 终端摘要。
"""
import json, struct, collections, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "refs", "hpbar", "main_text_decomp.bin")
OUT = os.path.join(ROOT, "out", "gu_select_writers.json")

b = open(BIN, "rb").read()
W = list(struct.unpack("<%dI" % (len(b) // 4), b))
N = len(W)
del b


def movw(w):
    """返回 (rd, imm16) 若为 movw，否则 None"""
    if (w & 0xFFF00000) == 0xE3000000:
        return (w >> 12) & 0xF, (((w >> 16) & 0xF) << 12) | (w & 0xFFF)
    return None


def regmem(w):
    """解码 [rn, rm] 寄存器偏移型访存，返回 (kind, rn, rd, rm)。
    kind: str / strb / strh / ldr / ldrb / ldrh / None
    """
    top = w & 0xFFF00000
    rn, rd, rm = (w >> 16) & 0xF, (w >> 12) & 0xF, w & 0xF
    if top == 0xE7800000: return "str", rn, rd, rm
    if top == 0xE7C00000: return "strb", rn, rd, rm
    if top == 0xE7900000: return "ldr", rn, rd, rm
    if top == 0xE7D00000: return "ldrb", rn, rd, rm
    # strh/ldrh 寄存器偏移：低 12 位 = 0xB0 | rm，需额外清位
    if (w & 0xFFF00FF0) == 0xE18000B0: return "strh", rn, rd, rm
    if (w & 0xFFF00FF0) == 0xE19000B0: return "ldrh", rn, rd, rm
    return None


def is_add_reg(w):
    return (w & 0xFFF00000) == 0xE0800000   # add rd, rn, rm (寄存器)


def imm_mem(w):
    """[rn, #imm12] 立即数偏移型访存，返回 (kind, rn, rd, imm)"""
    if (w & 0xFFB00000) == 0xE5800000:  # str
        return "str", (w >> 16) & 0xF, (w >> 12) & 0xF, w & 0xFFF
    if (w & 0xFFB00000) == 0xE5C00000:  # strb
        return "strb", (w >> 16) & 0xF, (w >> 12) & 0xF, w & 0xFFF
    if (w & 0xFFB00000) == 0xE5900000:  # ldr
        return "ldr", (w >> 16) & 0xF, (w >> 12) & 0xF, w & 0xFFF
    if (w & 0xFFB00000) == 0xE5D00000:  # ldrb
        return "ldrb", (w >> 16) & 0xF, (w >> 12) & 0xF, w & 0xFFF
    return None


def writes_rd(w):
    """返回该指令写入的目标寄存器（用于判断 rN 是否被覆盖）"""
    m = movw(w)
    if m: return m[0]
    if (w & 0xFFE00000) == 0xE3A00000: return (w >> 12) & 0xF  # mov rd,#imm
    if (w & 0xFFF00000) in (0xE2800000, 0xE0800000, 0xE0000000, 0xE1A00000):
        return (w >> 12) & 0xF  # add / and / mov reg
    r = regmem(w)
    if r and r[0].startswith("ldr"): return r[2]
    im = imm_mem(w)
    if im and im[0].startswith("ldr"): return im[2]
    if (w & 0xFFF00000) == 0xE5900000: return (w >> 12) & 0xF
    return None


TARGETS = (0x73E0, 0x73E1, 0x73E4, 0x73E8, 0x73EC)
sites = []   # (off, imm, rd, kind)  kind=write/read/indirect
for i in range(N - 1):
    m = movw(W[i])
    if not m or m[1] not in TARGETS:
        continue
    rd_n, imm = m
    alias = {rd_n}
    for j in range(i + 1, min(i + 18, N)):
        wj = W[j]
        wr = writes_rd(wj)
        r = regmem(wj)
        if r and r[3] in alias:
            kind = "write" if r[0].startswith("str") else "read"
            sites.append((j * 4, imm, r[0], r[1], r[2], r[3], kind))
        # add rT, rBase, rN → 间接基址；再看后 6 条是否有 [rT,#0] 写
        if is_add_reg(wj) and (wj & 0xF) in alias:
            rt = (wj >> 12) & 0xF
            alias.add(rt)
            for k in range(j + 1, min(j + 8, N)):
                im = imm_mem(W[k])
                if im and im[1] == rt:
                    kind = "write" if im[0].startswith("str") else "read"
                    sites.append((k * 4, imm, im[0] + "(ind)", im[1], im[2], im[3], kind))
        if wr in alias and wr != rd_n:
            pass  # 保守：不移除，避免漏掉 str rd,[rn,rm] 中 rd==rm 的情形
        if wr == rd_n and j > i + 1:
            break

# 函数起点：向前找最近 push {..., lr}（0xE92D4000 位14）
def func_start(off):
    i = off // 4
    for j in range(i, max(i - 400, 0), -1):
        w = W[j]
        if (w & 0xFFF00000) == 0xE9200000 and (w & 0x4000):
            return j * 4
    return None

# BL 调用图（一次性扫全 text）
bl_targets = collections.defaultdict(list)
for i in range(N):
    w = W[i]
    if (w & 0xFF000000) == 0xEB000000:
        imm24 = w & 0xFFFFFF
        if imm24 & 0x800000: imm24 -= 0x1000000
        tgt = i * 4 + 8 + imm24 * 4
        if 0 <= tgt < N * 4:
            bl_targets[tgt].append(i * 4)

# 汇总按函数
funcs = collections.defaultdict(lambda: {"writes": [], "reads": []})
for (off, imm, kind, rn, rd, rm, rw) in sites:
    fs = func_start(off)
    key = fs if fs is not None else off
    funcs[key][rw + "s"].append({"off": off, "imm": imm, "op": kind,
                                 "rn": rn, "rd": rd, "rm": rm})

rows = []
for fs, d in funcs.items():
    callers = bl_targets.get(fs, [])
    # 该函数内部是否调用 0xAFF40
    body_bl = []
    for j in range(fs // 4, min(fs // 4 + 600, N)):
        w = W[j]
        if (w & 0xFF000000) == 0xEB000000:
            imm24 = w & 0xFFFFFF
            if imm24 & 0x800000: imm24 -= 0x1000000
            t = j * 4 + 8 + imm24 * 4
            if t == 0xAFF40: body_bl.append(j * 4)
    rows.append({"func": fs, "n_write": len(d["writes"]), "n_read": len(d["reads"]),
                 "callers": len(callers), "caller_sample": callers[:6],
                 "calls_0xAFF40": body_bl[:6],
                 "writes": d["writes"][:8], "reads": d["reads"][:4]})

rows.sort(key=lambda r: (-r["n_write"], -r["n_read"]))
writers = [r for r in rows if r["n_write"] > 0]
readers = [r for r in rows if r["n_read"] > 0 and r["n_write"] == 0]

print(f"=== GU main.text 扫描（{N*4:#x} 字节）===")
print(f"  movw #0x73E0/73E1/73E4/73E8/73EC 后的访存点: {len(sites)}")
print(f"  含写入的函数: {len(writers)}   仅读取的函数: {len(readers)}（派发器为主体）")
print(f"  BL 目标地址总数: {len(bl_targets)}")
print(f"  BL 指向 0xAFF40 的调用点数: {len(bl_targets.get(0xAFF40, []))}")

print("\n=== 写入 +0x73Ex 的函数（按写入点数排序，前 30）===")
print("  func      wr rd  callers  BL→0xAFF40  写入点(op/imm)")
for r in writers[:30]:
    ws = ",".join(f"{x['op']}@{x['off']:X}/{x['imm']:X}" for x in r["writes"][:3])
    print(f"  {r['func']:08X}  {r['n_write']:2d} {r['n_read']:2d}  {r['callers']:4d}    "
          f"{str(r['calls_0xAFF40'][:2]):<18} {ws}")

print("\n=== 同时调用 0xAFF40 的写入者（抽选/提交层首要候选）===")
both = [r for r in writers if r["calls_0xAFF40"]]
for r in both[:25]:
    print(f"  {r['func']:08X}  wr={r['n_write']} callers={r['callers']}  BL→0xAFF40@{r['calls_0xAFF40'][:3]}")
print("  计数:", len(both))

print("\n=== 写入点按偏移分布 ===")
c = collections.Counter((s[1], s[6], s[2]) for s in sites)
for (imm, rw, op), n in c.most_common(25):
    print(f"  +{imm:04X} {rw:5s} {op:12s}: {n}")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump({"source": BIN, "sites": len(sites), "writers": writers,
           "readers_only_count": len(readers), "both_aff40": both,
           "bl_to_aff40_count": len(bl_targets.get(0xAFF40, []))},
          open(OUT, "w", encoding="utf-8"), indent=1)
print(f"\n→ {OUT}")
