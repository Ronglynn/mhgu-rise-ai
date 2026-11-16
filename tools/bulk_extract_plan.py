# -*- coding: utf-8 -*-
"""离线规划：为 52 个非 em131 怪生成批量抽取目标清单与 -f 正则。

只读 filelist，产出到 out/（新增文件），不改任何已有资产。
- 核心 4 类：think/emNNN_NN_main、hub/emNNN_NN_combat_main、
            user_data/emNNN_NN_range_data、emNNN_NN_stamina_data（全 variant 全量）
- act/combo：每怪最多 3 个样本（优先 action 编号最小 2 个 + combo 编号最小 1 个，
            不足则用另一类补足，仍不足则取全部）
- 正则：核心用「枚举 52 id 的共享组 + 通配结构」紧凑覆盖（天然排除 em131）；
        act/combo 用「精确 basename alternation」精确控制样本，避免抽多。
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # 04_RiseAI
BASE = ROOT.parent                                     # MHGU mod maker
LIST = BASE / "00_Tools" / "06_REEngine_Pak" / "assets" / "filelist" / "MHR_STM_Release.list"
OUT = ROOT / "out"
OUT.mkdir(parents=True, exist_ok=True)

EXCLUDE = {"em131"}
ENEMY_RE = re.compile(r"^natives/stm/enemy/(em\d{3})/")
CORE_RE = re.compile(
    r"^natives/stm/enemy/(em\d{3})/(\d{2})/"
    r"(?:ai_fsm_user_data/(?:think|hub)/|user_data/)"
    r"em\d{3}_\d{2}_(?:main|combat_main|range_data|stamina_data)\.user\.2$")
ACT_RE = re.compile(r"act_tbl_user_data/action/(em\d{3}_act_\d{3})\.user\.2$")
COMBO_RE = re.compile(r"act_tbl_user_data/combo/(em\d{3}_combo_\d{3})\.user\.2$")


def main() -> int:
    lines = [l.strip() for l in LIST.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]

    all_ids = sorted({m.group(1) for l in lines if (m := ENEMY_RE.match(l))})
    target_ids = [i for i in all_ids if i not in EXCLUDE]

    core_paths: list[str] = []
    acts: dict[str, list[str]] = defaultdict(list)      # id -> basenames (action)
    combos: dict[str, list[str]] = defaultdict(list)    # id -> basenames (combo)
    motlist_enemy = 0
    name_enemy = 0

    for l in lines:
        m = ENEMY_RE.match(l)
        if not m:
            continue
        em = m.group(1)
        if em in EXCLUDE:
            continue
        if "motlist" in l:
            motlist_enemy += 1
        if re.search(r"\.msg\.|mmsg|actionname|movename|attackname|action_name|"
                     r"mot_name|skillname|name", l, re.I):
            name_enemy += 1
        if CORE_RE.match(l):
            core_paths.append(l)
        if a := ACT_RE.search(l):
            acts[em].append(a.group(1))
        if c := COMBO_RE.search(l):
            combos[em].append(c.group(1))

    # ---- 每怪最多 3 个 act/combo 样本 ----
    def key_num(b: str) -> int:
        m = re.search(r"_(\d+)$", b)
        return int(m.group(1)) if m else 0

    sample_basenames: list[str] = []
    sample_paths: list[str] = []
    per_id_sample: dict[str, list[str]] = {}
    for em in target_ids:
        a = sorted(set(acts[em]), key=key_num)
        c = sorted(set(combos[em]), key=key_num)
        chosen: list[str] = []
        # 优先 action 2 个 + combo 1 个
        chosen += a[:2]
        chosen += c[:1]
        # 补足到 3
        if len(chosen) < 3:
            chosen += [x for x in a[2:] if x not in chosen][: 3 - len(chosen)]
        if len(chosen) < 3:
            chosen += [x for x in c[1:] if x not in chosen][: 3 - len(chosen)]
        chosen = chosen[:3]
        per_id_sample[em] = chosen
        sample_basenames += [b + ".user.2" for b in chosen]
        # 反查完整路径（用于清单）
        wanted = set(chosen)
        for l in lines:
            if em not in l:
                continue
            mm = re.search(r"/(em\d{3}_(?:act|combo)_\d{3})\.user\.2$", l)
            if mm and mm.group(1) in wanted:
                sample_paths.append(l)

    sample_paths = sorted(set(sample_paths))
    all_paths = sorted(core_paths) + sample_paths

    # ---- basename 唯一性校验 ----
    core_bn = [l.rsplit("/", 1)[-1] for l in core_paths]
    all_bn = core_bn + [b + ".user.2" for b in
                        [x for v in per_id_sample.values() for x in v]]
    dup = [b for b, n in defaultdict(int, {b: all_bn.count(b) for b in set(all_bn)}).items() if n > 1]

    # ---- 正则（稳健版）----
    # 工具 -f 里 " | " 的语义未知：可能是「单个 regex 的 alternation」，也可能是
    # 「多个 pattern 的分隔符」。这里让每个 | 分支内部绝不含 | ，则两种实现下
    # 都等价于「匹配任一分支」，无需赌语义。核心按 52 个 id × 4 类拆成独立段
    # （精确排除 em131），act/combo 用精确 basename 段。
    esc = lambda s: s.replace(".", r"\.")
    segments: list[str] = []
    for i in target_ids:                       # i 形如 em001
        segments += [
            rf"enemy/{i}/\d{{2}}/ai_fsm_user_data/think/{i}_\d{{2}}_main\.user\.2",
            rf"enemy/{i}/\d{{2}}/ai_fsm_user_data/hub/{i}_\d{{2}}_combat_main\.user\.2",
            rf"enemy/{i}/\d{{2}}/user_data/{i}_\d{{2}}_range_data\.user\.2",
            rf"enemy/{i}/\d{{2}}/user_data/{i}_\d{{2}}_stamina_data\.user\.2",
        ]
    segments += [esc(b) for b in sorted(set(sample_basenames))]
    assert all("|" not in s for s in segments), "每个分支内部不得含 |"
    assert not any(s.startswith("(") for s in segments), "分支不得依赖分组"
    full_regex = "|".join(segments)

    # ---- 落盘 ----
    (OUT / "bulk_target_paths.txt").write_text("\n".join(all_paths) + "\n", encoding="utf-8")
    (OUT / "bulk_filter_regex.txt").write_text(full_regex, encoding="utf-8")
    stats = {
        "list": str(LIST),
        "all_em_ids": all_ids,
        "all_em_id_count": len(all_ids),
        "excluded": sorted(EXCLUDE),
        "target_id_count": len(target_ids),
        "target_ids": target_ids,
        "core_file_count": len(core_paths),
        "core_by_class": {
            "main": sum(1 for l in core_paths if "/think/" in l and l.endswith("_main.user.2")),
            "combat_main": sum(1 for l in core_paths if l.endswith("_combat_main.user.2")),
            "range_data": sum(1 for l in core_paths if l.endswith("_range_data.user.2")),
            "stamina_data": sum(1 for l in core_paths if l.endswith("_stamina_data.user.2")),
        },
        "act_total_all_targets": sum(len(v) for v in acts.values()),
        "combo_total_all_targets": sum(len(v) for v in combos.values()),
        "sample_file_count": len(sample_paths),
        "sample_per_id": per_id_sample,
        "total_target_files": len(all_paths),
        "regex_char_len": len(full_regex),
        "duplicate_basenames": dup,
        "motlist_enemy_files": motlist_enemy,
        "enemy_name_text_candidates": name_enemy,
    }
    (OUT / "bulk_plan_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1),
                                              encoding="utf-8")

    print("all em ids      :", len(all_ids), "(excluded em131 ->", len(target_ids), "targets)")
    print("core files      :", len(core_paths), stats["core_by_class"])
    print("act/combo total :", stats["act_total_all_targets"], "/", stats["combo_total_all_targets"])
    print("sample files    :", len(sample_paths), "(<=3 per monster)")
    print("TOTAL targets   :", len(all_paths), "(<=600 required)")
    print("regex length    :", len(full_regex), "chars")
    print("dup basenames   :", dup if dup else "NONE (basenames globally unique)")
    print("motlist(enemy)  :", motlist_enemy, " enemy name-text candidates:", name_enemy)
    print("sample per id (first 6):")
    for em in target_ids[:6]:
        print("   ", em, per_id_sample[em])
    print("\nwrote out/bulk_target_paths.txt / out/bulk_filter_regex.txt / out/bulk_plan_stats.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
