#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""rollback_maccao_probe.py — 撤销「跳狗龙王减气阈值」临时参数 mod

用法：python 04_RiseAI/tools/rollback_maccao_probe.py

做三件事（全部可逆，不删除任何文件）：
  1. 把 mods/Maccao_StaminaProbe 移动到 04_RiseAI/out/_retired_Maccao_StaminaProbe；
  2. 从 out/load_order_backup_20261111_2125.txt 恢复 load_order.txt（不改其它行）；
  3. 确认 RiseAI_EntryProbe 插件仍是 v47 纯只读（md5 0fd173bd…）。
运行前请先关闭游戏。
"""
import hashlib
import shutil
from pathlib import Path

GAME = Path(r"D:\Monster Hunter Generations Ultimate Recomp")
AI = Path(r"D:\MHGU mod maker\04_RiseAI")
MOD = GAME / "mods" / "Maccao_StaminaProbe"
LO = GAME / "mods" / "load_order.txt"
BACKUP = AI / "out" / "load_order_backup_20261111_2125.txt"
PLUGIN = (GAME / "mods" / "RiseAI_EntryProbe" / "romfs" / "nativeNX"
          / "plugins" / "rai_entrylocator_probe.nro")
V47 = AI / "out" / "rai_tired_snapshot_v47.nro"

md5 = lambda p: hashlib.md5(p.read_bytes()).hexdigest()

# 1) 把 mod 移出游戏加载列表（不删除）
if MOD.exists():
    dest = AI / "out" / "_retired_Maccao_StaminaProbe"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.move(str(MOD), str(dest))
    print("[ok] mod retired ->", dest)
else:
    print("[ok] mod already absent")

# 2) 恢复 load_order
if BACKUP.exists():
    shutil.copy2(BACKUP, LO)
    print("[ok] load_order restored from", BACKUP.name)
else:
    s = LO.read_text(encoding="utf-8")
    s = "\n".join(l for l in s.splitlines()
                  if l.strip() != "Maccao_StaminaProbe") + "\n"
    LO.write_bytes(s.encode("utf-8"))
    print("[ok] load_order line removed")

# 3) 确认插件仍是 v47 纯只读（该探针不写内存，一般不改动）
if PLUGIN.exists() and V47.exists() and md5(PLUGIN) != md5(V47):
    shutil.copy2(V47, PLUGIN)
    print("[ok] plugin restored to v47 read-only")
else:
    print("[ok] plugin already v47 read-only:",
          md5(PLUGIN)[:8] if PLUGIN.exists() else "missing")

print("[done] 临时参数已撤销；游戏资源与原有 load_order 行未改动。")
