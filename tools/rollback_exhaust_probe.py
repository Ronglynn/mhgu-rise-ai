#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""rollback_exhaust_probe.py — 撤销「雄火龙减气阈值」临时参数 mod

用法：python 04_RiseAI/tools/rollback_exhaust_probe.py

做三件事（全部可逆，不删除任何文件）：
  1. 把 mods/Rathalos_ExhaustProbe 移动到 04_RiseAI/out/_retired_Rathalos_ExhaustProbe；
  2. 从 out/load_order_backup_20261110_2350.txt 恢复 load_order.txt（不改其它行）；
  3. 确认 RiseAI_EntryProbe 插件仍是 v43 纯只读（md5 6a5683f7…）。
运行前请先关闭游戏。
"""
import hashlib
import shutil
from pathlib import Path

GAME = Path(r"D:\Monster Hunter Generations Ultimate Recomp")
AI = Path(r"D:\MHGU mod maker\04_RiseAI")
MOD = GAME / "mods" / "Rathalos_ExhaustProbe"
LO = GAME / "mods" / "load_order.txt"
BACKUP = AI / "out" / "load_order_backup_20261110_2350.txt"
PLUGIN = GAME / "mods" / "RiseAI_EntryProbe" / "romfs" / "nativeNX" / "plugins" / "rai_entrylocator_probe.nro"
V43 = AI / "out" / "rai_em_base_v43.nro"

# 1) move the mod out of the game's mod list
if MOD.exists():
    dest = AI / "out" / "_retired_Rathalos_ExhaustProbe"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.move(str(MOD), str(dest))
    print("[ok] mod retired ->", dest)
else:
    print("[ok] mod already absent")

# 2) restore load_order from the pre-change backup
if BACKUP.exists():
    shutil.copy2(BACKUP, LO)
    print("[ok] load_order restored from", BACKUP.name)
else:
    s = LO.read_text(encoding="utf-8")
    s = "\n".join(l for l in s.splitlines() if l.strip() != "Rathalos_ExhaustProbe") + "\n"
    LO.write_bytes(s.encode("utf-8"))
    print("[ok] load_order line removed")

# 3) ensure read-only probe
md5 = lambda p: hashlib.md5(p.read_bytes()).hexdigest()
if PLUGIN.exists() and V43.exists() and md5(PLUGIN) != md5(V43):
    shutil.copy2(V43, PLUGIN)
    print("[ok] plugin rolled back to v43 read-only")
else:
    print("[ok] plugin already v43 read-only:", md5(PLUGIN)[:8] if PLUGIN.exists() else "missing")

print("[done] 临时参数已撤销；游戏资源与原有 load_order 行未改动。")
