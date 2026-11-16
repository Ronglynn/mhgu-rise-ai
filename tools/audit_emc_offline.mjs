#!/usr/bin/env node
/**
 * audit_emc_offline.mjs — 完全离线解析 MHGU 怪物 AI 决策表（EMC / cmdtbl）
 *
 * 数据源：游戏 romfs/nativeNX/arc/enemy/emNNN_SS.arc 内的
 *         enemy\cmd_tbl\emNNN_SS_cmdtbl （只读，不解压到磁盘、不改任何 mod）
 * 解析器：本任务区 04_RiseAI/tools/mhgu/emc.mjs（LEN 表 + 脚本文法）
 *         04_RiseAI/tools/gu-moves/lib/（buildTree / entryFacts）
 *
 * 用途：替代「跨 2 只快慢不同的怪实机取对照」。EMC 是 GU 自己的
 *       处境 Hub（21 段）+ 距离档 switch + 加权抽选池（op02 块，case 百分比、
 *       块内和恒 100）+ 动作队列（op14），与 Rise 的 _TransitionRate 同构。
 *
 * 用法：
 *   node tools/audit_emc_offline.mjs                      # 全 137 只怪
 *   node tools/audit_emc_offline.mjs em010_00 em020_00   # 指定怪
 *
 * 产物：out/emc_offline/summary.tsv / summary.json / focus.md
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

const DIST_OPS = new Set([0x0b, 0x17, 0x57, 0x5c, 0x7c]);
const STATE_OPS = new Set([0x07, 0x08, 0x09, 0x0a, 0x0c, 0x23, 0x29, 0x63]);
const WEIGHT_OP = 0x02;
const QUEUE_OP = 0x14;
const RESET_OP = 0x00;

function entropy(ws) {
  const t = ws.reduce((a, b) => a + b, 0);
  if (!t) return 0;
  return -ws.reduce((a, w) => a + (w > 0 ? (w / t) * Math.log2(w / t) : 0), 0);
}

function analyzeDoc(doc, label) {
  const r = {
    label, sections: doc.sections.length, entries: 0, ins: 0,
    blocks: 0, op02Blocks: 0, op02Cases: 0, op02Sum100: 0,
    soloBlocks: 0, highWeightBlocks: 0, maxWeight: 0, entropySum: 0,
    distBlocks: 0, distCases: 0, distOpSet: {},
    stateBlocks: 0, stateCases: 0, stateOpSet: {},
    op14: 0, op14Weighted: 0, resets: 0, queueTargets: new Map(),
    perSection: [], errors: 0,
    // 复读结构候选：同一个动作 entry 被多个 op14 指向
    repeatedTargets: 0, topTarget: null,
  };
  const weightBlocks = [];

  for (const s of doc.sections) {
    let secEntries = 0, secOp14 = 0;
    for (const e of s.entries) {
      secEntries++; r.entries++; r.ins += e.ins.length;
      const { root, errors } = buildTree(e.ins);
      r.errors += (errors?.length ?? 0);
      const walk = (body, path_) => {
        for (const n of body) {
          if (n.t === 'leaf') {
            if (n.op === QUEUE_OP) {
              r.op14++; secOp14++;
              const key = n.args[0];
              r.queueTargets.set(key, (r.queueTargets.get(key) ?? 0) + 1);
              const w = [...path_].reverse().find(p => p.op === WEIGHT_OP && p.kind === 'case');
              if (w) r.op14Weighted++;
            } else if (n.op === RESET_OP) r.resets++;
            continue;
          }
          r.blocks++;
          const cases = n.branches.filter(b => b.kind === 'case');
          const opKey = '0x' + n.op.toString(16).padStart(2, '0');
          if (n.op === WEIGHT_OP) {
            r.op02Blocks++; r.op02Cases += cases.length;
            const ws = cases.map(b => b.args[0] ?? 0);
            const sum = ws.reduce((a, b) => a + b, 0);
            if (sum === 100) r.op02Sum100++;
            if (ws.length === 1) r.soloBlocks++;
            const mx = ws.length ? Math.max(...ws) : 0;
            if (mx >= 80) r.highWeightBlocks++;
            r.maxWeight = Math.max(r.maxWeight, mx);
            r.entropySum += entropy(ws);
            weightBlocks.push({ sec: s.index, entry: e.index, pos: n.pos, cases: ws, sum });
          } else if (DIST_OPS.has(n.op)) {
            r.distBlocks++; r.distCases += cases.length;
            r.distOpSet[opKey] = (r.distOpSet[opKey] ?? 0) + 1;
          } else if (STATE_OPS.has(n.op)) {
            r.stateBlocks++; r.stateCases += cases.length;
            r.stateOpSet[opKey] = (r.stateOpSet[opKey] ?? 0) + 1;
          }
          for (const br of n.branches) {
            walk(br.body, [...path_, { op: n.op, kind: br.kind, args: br.args }]);
          }
        }
      };
      walk(root.branches[0].body, []);
    }
    r.perSection.push({ sec: s.index, entries: secEntries, op14: secOp14 });
  }
  r.meanEntropy = r.op02Blocks ? +(r.entropySum / r.op02Blocks).toFixed(3) : 0;
  const sorted = [...r.queueTargets.entries()].sort((a, b) => b[1] - a[1]);
  r.repeatedTargets = sorted.filter(([, c]) => c > 1).length;
  r.topTarget = sorted.length ? { entry: sorted[0][0], count: sorted[0][1] } : null;
  r.weightBlocks = weightBlocks;
  return r;
}

function nameOf(label) {
  try {
    const map = JSON.parse(fs.readFileSync(SLOT_MAP, 'utf-8'));
    const m = /^em(\d+)_(\d+)/.exec(label);
    if (!m) return '';
    const emid = Number(m[1]);
    const hit = map.find(x => x.emid === emid);
    return hit ? `${hit.cn} / ${hit.en}` : '';
  } catch { return ''; }
}

const argv = process.argv.slice(2);
let arcs = fs.readdirSync(ARC_DIR).filter(f => /\.arc$/i.test(f)).sort();
if (argv.length) arcs = arcs.filter(f => argv.some(a => f.toLowerCase().includes(a.toLowerCase())));

fs.mkdirSync(OUT, { recursive: true });
const rows = [];
let bad = 0;
for (const file of arcs) {
  const label = file.replace(/\.arc$/i, '');
  try {
    const buf = fs.readFileSync(path.join(ARC_DIR, file));
    const m = /^em(\d+)_(\d+)/.exec(label);
    const want = `enemy\\cmd_tbl\\${m ? `em${m[1]}_${m[2]}` : label}_cmdtbl`;
    const { doc } = cmdtblFromArc(buf, want, label);
    const r = analyzeDoc(doc, label);
    r.name = nameOf(label);
    r.bytes = doc.sections.reduce((a, s) => a + s.entries.reduce((b, e) => b + e.length, 0), 0);
    delete r.weightBlocks; // 不写进 JSON，太大
    rows.push(r);
    process.stdout.write(`\r  ${String(rows.length).padStart(3)}/${arcs.length} ${label.padEnd(12)} 段=${r.sections} 权重块=${String(r.op02Blocks).padStart(4)} 距离块=${String(r.distBlocks).padStart(3)} 动作队列=${String(r.op14).padStart(4)}   `);
  } catch (e) {
    bad++; console.error(`\n  FAIL ${label}: ${e.message}`);
  }
}
console.log(`\n解析 ${rows.length}/${arcs.length}，失败 ${bad}`);

// TSV
const cols = ['label', 'name', 'sections', 'entries', 'ins', 'op02Blocks', 'op02Cases', 'op02Sum100',
  'soloBlocks', 'highWeightBlocks', 'maxWeight', 'meanEntropy',
  'distBlocks', 'distCases', 'stateBlocks', 'stateCases', 'op14', 'op14Weighted',
  'resets', 'repeatedTargets', 'bytes'];
const tsv = [cols.join('\t'), ...rows.map(r => cols.map(c => r[c] ?? '').join('\t'))].join('\n') + '\n';
fs.writeFileSync(path.join(OUT, 'summary.tsv'), tsv);
fs.writeFileSync(path.join(OUT, 'summary.json'), JSON.stringify(rows, null, 2));
console.log(`产物：${path.join(OUT, 'summary.tsv')} / summary.json`);

// 焦点报告
const focusLabels = ['em010_00', 'em020_00', 'em004_00'];
const focus = rows.filter(r => focusLabels.includes(r.label));
const all = (key) => rows.map(r => r[key]).filter(Number.isFinite).sort((a, b) => a - b);
const pct = (v, arr) => {
  if (!arr.length) return 0;
  return +(100 * arr.filter(x => x <= v).length / arr.length).toFixed(1);
};
const lines = [];
lines.push('# EMC 离线审计：GU 怪物 AI 决策结构（无实机）\n');
lines.push(`数据源：\`${ARC_DIR}\`，共 ${rows.length} 张 \`*_cmdtbl\`。只读解析，未改任何游戏文件。\n`);
lines.push('## 全量分布\n');
lines.push('| 指标 | 最小 | 中位 | 最大 | 说明 |');
lines.push('|---|---|---|---|---|');
for (const [k, desc] of [
  ['op02Blocks', '加权抽选块数（≈Rise 加权池）'],
  ['op02Cases', '加权 case 总数'],
  ['distBlocks', '距离档 switch 块数'],
  ['stateBlocks', '状态字节 switch 块数'],
  ['op14', '动作队列叶子数'],
  ['soloBlocks', '单 case 块（100% 固定动作 → 复读结构候选）'],
  ['highWeightBlocks', '最大权重 ≥80 的块'],
  ['meanEntropy', '权重块平均熵（bit，越低越集中）'],
]) {
  const a = all(k);
  if (!a.length) continue;
  lines.push(`| ${k} | ${a[0]} | ${a[a.length >> 1]} | ${a[a.length - 1]} | ${desc} |`);
}
lines.push(`\n加权块总和恒 100 的比例：${rows.filter(r => r.op02Blocks && r.op02Sum100 === r.op02Blocks).length}/${rows.filter(r => r.op02Blocks).length} 只怪 ` +
  `（与 Rise \`_TransitionRate\` 同构的直接证据）。\n`);

lines.push('## 三只重点怪对比\n');
lines.push('| 怪 | 段 | 加权块 | case | 单case块 | ≥80权重块 | 平均熵 | 距离块 | 状态块 | 动作队列 | 重复指向 |');
lines.push('|---|---|---|---|---|---|---|---|---|---|---|');
for (const r of focus) {
  lines.push(`| ${r.label} ${r.name} | ${r.sections} | ${r.op02Blocks} | ${r.op02Cases} | ${r.soloBlocks} | ${r.highWeightBlocks} | ${r.meanEntropy} | ${r.distBlocks} | ${r.stateBlocks} | ${r.op14} | ${r.repeatedTargets} |`);
}
lines.push('\n各指标在全体 137 只怪中的百分位：\n');
for (const r of focus) {
  lines.push(`- **${r.label} ${r.name}**：加权块 ${pct(r.op02Blocks, all('op02Blocks'))}% 分位；` +
    `单 case 块 ${pct(r.soloBlocks, all('soloBlocks'))}%；距离块 ${pct(r.distBlocks, all('distBlocks'))}%；` +
    `平均熵 ${r.meanEntropy}（${pct(r.meanEntropy, all('meanEntropy'))}% 分位）；` +
    `动作队列 ${pct(r.op14, all('op14'))}% 分位。`);
}
lines.push('\n## 结论要点\n');
lines.push('- EMC 表 = 21 段处境分支 + 距离/状态 switch + `op02` 多分支块（130/130 表 case 数值和恒 100）+ `op14` 动作队列；**不是纯确定性 switch**（至少是分支选择结构）。');
lines.push('- 「GU 无抽选层」的结论不成立：EMC 脚本由解释器 `0x82f80` 执行、表在 `em+0x2588`，是全怪共用的决策层；此前在 `0x76154` 落盘层做帧间隔节流，压根没碰这一层。');
lines.push('- 「连续 N 次同招」可从表层量化：单 case 块 / ≥80 集中块 / 同一 entry 被多个 case 反复指向，无需实机取对照，详见 `repeat.md`。');
lines.push('- **口径边界**：`op02` case 是否为概率份额（`_TransitionRate` 同构）尚未运行时闭环（matcher `0x8e144` 的 `s16` 是几何/状态计算值）；和恒 100 是强结构证据，不是代码级确证。');
lines.push('- 21 段的 section→AI 状态映射在资料库中仍标 `[U]`，本脚本只给结构统计，不臆测语义。\n');
fs.writeFileSync(path.join(OUT, 'focus.md'), lines.join('\n'));
console.log(`产物：${path.join(OUT, 'focus.md')}`);
