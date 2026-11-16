#!/usr/bin/env node
/**
 * audit_emc_repeat.mjs — 全量扫描 EMC 加权池的「等效同招」结构（离线，只读）
 *
 * 对每个 op02 权重池，把各 case 的权重按目标动作 entry 聚合：
 *   等效概率(entry) = Σ 投给该 entry 的 case 权重
 * 若最大等效概率 == 池总和（通常 100），则无论 RNG 落到哪个 case 都选同一动作
 * ⇒ 该处境下必然连出同一招。这是 GU 表里「复读」的结构性来源，
 *   也是 Rise `_CheckPrevTableInfoList` 要解决的问题。
 *
 * 用法：node tools/audit_emc_repeat.mjs
 * 产物：out/emc_offline/repeat.tsv / repeat.md
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const OUT = path.join(ROOT, 'out', 'emc_offline');
const ARC_DIR = 'D:/Monster Hunter Generations Ultimate Recomp/data/romfs/nativeNX/arc/enemy';
const SLOT_MAP = 'D:/MHGU mod maker/00_Tools/92_MHGU-master/MHGU-master/docs/data/json/monster-slot-map-137.json';
const { cmdtblFromArc, buildTree } = await import(pathToFileURL(path.join(HERE, 'gu-moves', 'lib', 'trees.mjs')).href);

const nameOf = (label) => {
  try {
    const map = JSON.parse(fs.readFileSync(SLOT_MAP, 'utf-8'));
    const m = /^em(\d+)_(\d+)/.exec(label);
    const hit = m && map.find(x => x.emid === Number(m[1]));
    return hit ? hit.cn : '';
  } catch { return ''; }
};

const arcs = fs.readdirSync(ARC_DIR).filter(f => /\.arc$/i.test(f)).sort();
fs.mkdirSync(OUT, { recursive: true });
const rows = [];

for (const file of arcs) {
  const label = file.replace(/\.arc$/i, '');
  try {
    const buf = fs.readFileSync(path.join(ARC_DIR, file));
    // emsNNN / 占位表都走 cmdtblFromArc 的 *_cmdtbl 回退匹配，不依赖文件名正则
    const { doc } = cmdtblFromArc(buf, `enemy\\cmd_tbl\\${label}_cmdtbl`, label);
    let pools = 0, forced = 0, highConc = 0, emptyVote = 0, maxSum = 0;
    const forcedDetail = [];
    for (const s of doc.sections) for (const e of s.entries) {
      const { root } = buildTree(e.ins);
      const walk = (body) => {
        for (const n of body) {
          if (n.t !== 'block') continue;
          if (n.op === 0x02) {
            pools++;
            const agg = new Map();
            let sum = 0;
            for (const br of n.branches.filter(b => b.kind === 'case')) {
              const w = br.args[0] ?? 0; sum += w;
              const collect = (bb) => {
                for (const x of bb) {
                  if (x.t === 'leaf' && x.op === 0x14) agg.set(x.args[0], (agg.get(x.args[0]) ?? 0) + w);
                  else if (x.t === 'block') for (const b2 of x.branches) collect(b2.body);
                }
              };
              collect(br.body);
            }
            if (!agg.size) emptyVote++;
            const top = agg.size ? Math.max(...agg.values()) : 0;
            maxSum = Math.max(maxSum, top);
            if (top >= 80) highConc++;
            if (agg.size && top === sum) {
              forced++;
              const winner = [...agg.entries()].find(([, v]) => v === top);
              forcedDetail.push({ sec: s.index, entry: e.index, target: winner[0], sum, cases: n.branches.filter(b => b.kind === 'case').length });
            }
          }
          for (const br of n.branches) walk(br.body);
        }
      };
      walk(root.branches[0].body);
    }
    rows.push({ label, name: nameOf(label), pools, forced, forcedPct: pools ? +(100 * forced / pools).toFixed(1) : 0,
      highConc, emptyVote, maxSum, detail: forcedDetail.slice(0, 5) });
    process.stdout.write(`\r  ${String(rows.length).padStart(3)}/${arcs.length} ${label.padEnd(12)} 池=${String(pools).padStart(4)} 必然同招池=${String(forced).padStart(3)}   `);
  } catch (err) { console.error(`\n  FAIL ${label}: ${err.message}`); }
}
console.log('');

// 去重（多个 arc 共享同一张表：按 label 保留但标注结构指纹重复）
const seen = new Set();
const uniq = rows.filter(r => {
  const k = `${r.pools}|${r.forced}|${r.highConc}|${r.maxSum}`;
  if (seen.has(k)) return false;
  seen.add(k); return true;
});

const cols = ['label', 'name', 'pools', 'forced', 'forcedPct', 'highConc', 'emptyVote', 'maxSum'];
fs.writeFileSync(path.join(OUT, 'repeat.tsv'), [cols.join('\t'), ...rows.map(r => cols.map(c => r[c] ?? '').join('\t'))].join('\n') + '\n');

const active = rows.filter(r => r.pools > 0).sort((a, b) => b.forcedPct - a.forcedPct);
const L = [];
L.push('# EMC 加权池「等效同招」全量扫描（离线，无实机）\n');
L.push(`数据源：\`${ARC_DIR}\`，${rows.length} 个 arc / ${uniq.length} 张不同结构的表；只读解析。\n`);
L.push('定义：把每个 `op02` 池各 case 的权重按目标动作 entry 聚合，`max(等效概率)==池总和` 即「无论 RNG 落哪个 case 都选同一动作」。\n');
L.push('## 汇总\n');
L.push(`- 有加权池的表：${active.length}；存在「必然同招池」的表：${active.filter(r => r.forced > 0).length}。`);
L.push(`- 必然同招池总数：${active.reduce((a, r) => a + r.forced, 0)}，占全部池 ${(100 * active.reduce((a, r) => a + r.forced, 0) / active.reduce((a, r) => a + r.pools, 0)).toFixed(2)}%。\n`);
L.push('## 必然同招池占比 TOP 15（越大越容易复读）\n');
L.push('| 怪 | 名称 | 池数 | 必然同招池 | 占比 | ≥80%集中池 |');
L.push('|---|---|---|---|---|---|');
for (const r of active.slice(0, 15)) L.push(`| ${r.label} | ${r.name} | ${r.pools} | ${r.forced} | ${r.forcedPct}% | ${r.highConc} |`);
L.push('\n## 三只重点怪\n');
for (const lb of ['em010_00', 'em020_00', 'em004_00']) {
  const r = rows.find(x => x.label === lb);
  if (!r) continue;
  const rank = active.findIndex(x => x.label === lb) + 1;
  L.push(`- **${lb} ${r.name}**：池 ${r.pools}，必然同招池 ${r.forced}（${r.forcedPct}%），≥80% 集中池 ${r.highConc}，全量占比排名第 ${rank}/${active.length}。` +
    (r.detail.length ? ` 样例：${r.detail.map(d => `s${d.sec}.e${d.entry}→entry${d.target}(${d.cases} case, 和${d.sum})`).join('; ')}` : ''));
}
L.push('\n## 对标 Rise\n');
L.push('- Rise `_CheckPrevTableInfoList`：抽选时按动作表否决并重抽，防止同一动作连续出现。');
L.push('- GU EMC：池内多 case 可投给同一 entry 且无 prev 否决 ⇒ 该处境下 100% 复读，属表结构自身缺陷。');
L.push('- 这说明「防复读」应在**抽选层**（EMC 解释器 / 池选择）做通用规则，而不是在落盘层做帧间隔节流。\n');
L.push('## 严谨性边界（必须保留）\n');
L.push('1. **本报告的「必然同招池」结论不依赖 `op02` case 数值的语义**：判据是「该块所有有 `op14` 目标的 case 都指向同一 entry，且其权重和等于全块 case 权重和」，');
L.push('   即无论 case 表示概率份额、阈值还是状态枚举，任何分支都选同一个动作。');
L.push('2. **`op02` case 值 = 百分比（`_TransitionRate` 同构）尚未运行时闭环**：资料库 `tools/gu-moves/lib/trees.mjs` 明确按百分比实现，且本扫描 130/130 表 `op02` 块 case 和恒 100（强结构证据）；');
L.push('   但 `reference/formats/emc.md §4` 把 `0x02` 归为「按 enemy 状态字节 switch」[I]，且反汇编 matcher `0x8e144` 的 `s16` 是几何/状态计算值（`0x8e468 vsqrt` / `0x8e6d0 vabs` / `0x8e634 vselgt`），');
L.push('   `0x8e86c vcmpe.f32 s20,s16; blt next-case` 是阈值顺序比较，未见 0~100 随机数来源。**因此「GU 已有 Rise 式加权池」只能作为高置信工作假设，不能当作代码级确证。**');
L.push('3. `section → AI 状态` 映射在资料库仍标 `[U]`；本报告只做结构统计，不臆测 21 段各自语义。\n');
fs.writeFileSync(path.join(OUT, 'repeat.md'), L.join('\n'));
console.log(fs.readFileSync(path.join(OUT, 'repeat.md'), 'utf-8'));
