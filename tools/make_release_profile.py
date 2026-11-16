# -*- coding: utf-8 -*-
"""从当前 lib.rs 生成成品版源码（只写文件，不编译、不部署）。

成品目标：关掉高频只读探针日志，但保留 W1/W2/W4 的全部行为逻辑。
验收场（v71）跑完并通过后再使用；生成结果需自行编译 + elf2nro + 覆盖部署。

用法：
  python tools/make_release_profile.py              # lite：保留 S/S2/HB/BEAT/V/QX
  python tools/make_release_profile.py --silent     # 连 HB 也关（W4 统计不可见，行为仍在）
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "plug/context_probe/src/lib.rs"
DST = ROOT / "plug/context_probe/src/lib.rs.release"
DOC = ROOT / "out/release_profile.md"

# 必须由「行为逻辑」保留，不能置 0 的开关
KEEP_ON = {
    "W1_ALL": 1, "W2_BAND_ENABLE": 1, "W4_STANCE_ENABLE": 1,
    "W4_HUB_ENABLE": 1, "PROFILE_RELEASE": 1,
}
KEEP_OFF = {"DRAIN_ENABLE": 0, "W3_GATE_ENABLE": 0}
# 可关的高频诊断行（W2_PROBE=0 会编译期消除 Z/ZP/ZS/ZT/dist_probe）
LITE = {
    "W2_PROBE": 0,
    "MAX_B2": 0,
    "MAX_AE": 0,
    "MAX_COMBO": 0,
    "MAX_AR": 0,
    # MAX_QX 必须保留 >=1：QX 分支内更新 STANCE_CUR/F，W4 处境分流依赖它
    "MAX_QX": 400,
    "MAX_HB": 200,
}
SILENT_EXTRA = {"MAX_HB": 0}


def set_const(src: str, name: str, value: int) -> str:
    pat = re.compile(r"^(const\s+%s\s*:\s*u32\s*=\s*)[\d_]+(;.*)$" % re.escape(name), re.M)
    m = pat.search(src)
    if not m:
        raise KeyError("找不到常量 %s" % name)
    return src[:m.start()] + m.group(1) + str(value) + m.group(2) + src[m.end():]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--silent", action="store_true")
    a = ap.parse_args(argv)
    s = SRC.read_text(encoding="utf-8")
    changes = dict(LITE)
    if a.silent:
        changes.update(SILENT_EXTRA)
    changes.update(KEEP_ON)
    changes.update(KEEP_OFF)
    for k, v in changes.items():
        s = set_const(s, k, v)
    # 安全阀：成品也必须保留全局日志上限与完整性行
    s = set_const(s, "MAXLOG", 1_000_000)
    DST.write_text(s, encoding="utf-8", newline="")
    print("wrote", DST, len(s.splitlines()), "lines")

    lines = [
        "# 成品版编译配置（验收通过后使用，本轮未部署）", "",
        "生成物：`04_RiseAI/plug/context_probe/src/lib.rs.release`（**未覆盖** `lib.rs`，**未编译**，**未部署**）。", "",
        "## 开关清单", "",
        "| 常量 | 成品值 | 作用 |", "|---|---|---|",
    ]
    for k, v in sorted(changes.items()):
        note = {
            "W2_PROBE": "关 Z/ZP/ZS/ZT 探针；`band_sense` 独立，W2 加权仍生效",
            "MAX_B2": "关 B2 诊断行",
            "MAX_AE": "关 AE 动作类边沿行",
            "MAX_COMBO": "关 COMBO 连段观测行",
            "MAX_AR": "关 AR 换区状态行；`ZONE_F` 状态更新在 AR 块之外，W4 hub3 仍生效",
            "MAX_QX": "**必须 >=1**：QX 分支内更新 `STANCE_CUR/F`，W4 处境分流依赖它",
            "MAX_HB": "HB 行（W4 分流统计）；`--silent` 时置 0",
            "MAXLOG": "全局灾难熔断，保留 100 万",
            "W1_ALL": "主轨全抽选，保持开启",
            "W2_BAND_ENABLE": "W2 状态×档位加权，保持开启",
            "W4_STANCE_ENABLE": "W4 处境状态维，保持开启",
            "W4_HUB_ENABLE": "W4 12 处境分流，保持开启",
            "PROFILE_RELEASE": "发布配置，保持开启",
            "DRAIN_ENABLE": "强制疲惫放大，必须关闭",
            "W3_GATE_ENABLE": "P70 实机证明 GU 无可拦窗口，保持关闭",
        }.get(k, "")
        lines.append("| `%s` | %s | %s |" % (k, v, note))
    lines += [
        "", "## 依赖说明（重要）", "",
        "- `band_sense()` 独立于 `W2_PROBE`，所以关掉 Z 系日志后 W2 加权仍工作。",
        "- `ZONE_F`（换区 hub3）状态更新在 AR 日志块**之外**，关 `MAX_AR` 不影响 W4。",
        "- `END_F` / `ABN_F`（W3/W4 异常）更新在 `h_unify` 独立块，不依赖 QX 日志。",
        "- **只有 `STANCE_CUR/F` 在 QX 分支内** ⇒ `MAX_QX` 不得置 0；若将来要彻底关 QX，",
        "  必须先把 stance 状态更新移到 QX 分支之外（等价改造，零新增 hook）。",
        "", "## 编译与部署（验收通过后执行）", "",
        "```",
        "cp 04_RiseAI/plug/context_probe/src/lib.rs 04_RiseAI/plug/context_probe/src/lib.rs.v71bak",
        "cp 04_RiseAI/plug/context_probe/src/lib.rs.release 04_RiseAI/plug/context_probe/src/lib.rs",
        "cd 04_RiseAI/plug/context_probe",
        "cargo build --release -Zjson-target-spec -Zbuild-std=core,alloc --target armv7a-none-eabi.json",
        "cd ../../.. && python bin/elf2nro.py <so> 04_RiseAI/out/rai_release.nro",
        "cp 04_RiseAI/out/rai_release.nro \"<游戏>/mods/RiseAI_EntryProbe/romfs/nativeNX/plugins/rai_entrylocator_probe.nro\"",
        "```",
        "", "回退：把 `lib.rs.v71bak` 复制回 `lib.rs`，重新编译 v71 NRO。", "",
        "## 本轮状态", "",
        "**未部署任何 NRO**，当前部署点仍是 v71 `1d513ec3…`；下一场验收仍用 v71 全量探针日志。",
        "成品版必须等验收场判读通过（W4 分流、日志完整性、零异常、连段正常）之后再编译。", "",
    ]
    DOC.write_text("\n".join(lines), encoding="utf-8", newline="")
    print("wrote", DOC)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
