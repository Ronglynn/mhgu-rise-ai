#!/usr/bin/env node
/**
 * audit_emc_pools.mjs — 单怪 EMC 加权池明细（离线，只读）
 *
 * 回答三件事：
 *  1. 每个 op02 权重块里，各 case 的百分比分别把票投给哪个动作 entry（op14）；
 *  2. 是否有「同一块内同一 entry 被多次投票」「单 case 100%」等复读结构；
 *  3. 距离/状态 switch 的 case 分布，以及状态 op 清单（找 GU 有无 prev 表检查线索）。
 *
 * 用法：node tools/audit_emc_pools.mjs em010_00 [em020_00 ...]
 * 产物：out/emc_offline/pools_<label>.json
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const OUT = path.join(ROOT, 'out', 'emc_offline');
const ARC_DIR = 'D:/Monster Hunter Generations Ultimate Recomp/data/romfs/nativeNX/arc/enemy';
const { cmdtblFromArc, buildTree } = await import(pathToFileURL(path.join(HERE, 'gu-moves', 'lib', 'trees.mjs')).href);

const DIST = { 0x0b: 'target_dist_rot', 0x17: 'dist_3d', 0x57: 'target_dist_rot2', 0x5c: 'dist_xz', 0x7c: 'min_dist6' };
const STATE = { 0x07: '[sub+0x5cdc]', 0x08: '[sub+0x5cdd]', 0x09: '[sub+0x2c0]',
  0x0a: '[sub+0x2c0]', 0x0c: '[sub+0x1ba]', 0x23: '[sub+0x5cb7]', 0x29: '[sub+0x5cb6]', 0x63: '[sub+0x5cba]' };

const labels = process.argv.slice(2);
if (!labels.length) { console.error('usage: node tools/audit_emc_pools.mjs <label> [...]'); process.exit(2); }
fs.mkdirSync(OUT, { recursive: true });

for (const label of labels) {
  const file = label + '.arc';
  const buf = fs.readFileSync(path.join(ARC_DIR, file));
  // emsNNN 等命名不一致的 arc 由 cmdtblFromArc 的 *_cmdtbl 回退匹配处理
  const { doc } = cmdtblFromArc(buf, `enemy\\cmd_tbl\\${label}_cmdtbl`, label);

  const pools = [], distCases = [], stateCases = [];
  const opHist = {};
  let sectionsWithPools = 0;

  for (const s of doc.sections) {
    let hasPool = false;
    for (const e of s.entries) {
      const { root } = buildTree(e.ins);
      const walk = (body, path_) => {
        for (const n of body) {
          if (n.t === 'leaf') {
            opHist['0x' + n.op.toString(16).padStart(2, '0')] = (opHist['0x' + n.op.toString(16).padStart(2, '0')] ?? 0) + 1;
            continue;
          }
          const opk = '0x' + n.op.toString(16).padStart(2, '0');
          opHist[opk + '.block'] = (opHist[opk + '.block'] ?? 0) + 1;
          const cases = n.branches.filter(b => b.kind === 'case');
          if (n.op === 0x02) {
            hasPool = true;
            const votes = [];
            for (const br of cases) {
              const w = br.args[0] ?? 0;
              const targets = [];
              const collect = (bb) => {
                for (const x of bb) {
                  if (x.t === 'leaf' && x.op === 0x14) targets.push(x.args[0]);
                  else if (x.t === 'block') for (const b2 of x.branches) collect(b2.body);
                }
              };
              collect(br.body);
              votes.push({ weight: w, targets });
            }
            const allT = votes.flatMap(v => v.targets);
            const dup = allT.length - new Set(allT).size;
            pools.push({ sec: s.index, entry: e.index, pos: n.pos, cases: votes.length,
              sum: votes.reduce((a, v) => a + v.weight, 0),
              maxWeight: votes.length ? Math.max(...votes.map(v => v.weight)) : 0,
              votes, duplicateTargetsInPool: dup,
              path: path_.map(p => 'op' + p.op.toString(16) + '.' + p.kind + '(' + p.args.join(',') + ')').join(' > ') });
          } else if (DIST[n.op]) {
            distCases.push({ sec: s.index, entry: e.index, op: DIST[n.op], cases: cases.map(b => b.args.join(',')) });
          } else if (STATE[n.op]) {
            stateCases.push({ sec: s.index, entry: e.index, op: STATE[n.op], read: Object.keys(STATE).find(k => +k === n.op), cases: cases.map(b => b.args.join(',')) });
          }
          for (const br of n.branches) walk(br.body, [...path_, { op: n.op, kind: br.kind, args: br.args }]);
        }
      };
      walk(root.branches[0].body, []);
    }
    if (hasPool) sectionsWithPools++;
  }

  const solo = pools.filter(p => p.cases === 1);
  const high = pools.filter(p => p.maxWeight >= 80);
  const dupPools = pools.filter(p => p.duplicateTargetsInPool > 0);
  const stateOpCount = {};
  for (const x of stateCases) stateOpCount[x.op] = (stateOpCount[x.op] ?? 0) + 1;

  const res = { label, pools: pools.length, sectionsWithPools, soloPools: solo.length,
    highWeightPools: high.length, duplicateTargetPools: dupPools.length,
    distBlocks: distCases.length, stateBlocks: stateCases.length, stateOps: stateOpCount,
    opHist, solo, high, duplicatePools: dupPools, distCases, stateCases,
    allPools: pools };
  fs.writeFileSync(path.join(OUT, `pools_${label}.json`), JSON.stringify(res, null, 1));

  console.log(`=== ${label} ===`);
  console.log(`  加权池 ${pools.length} 个，分布在 ${sectionsWithPools}/21 段；单case池 ${solo.length}，最高权重>=80 池 ${high.length}，池内重复指向 ${dupPools.length}`);
  console.log(`  距离 switch ${distCases.length} 块；状态 switch ${stateCases.length} 块，读取点：${JSON.stringify(stateOpCount)}`);
  console.log('  最高权重池 TOP6：');
  for (const p of [...pools].sort((a, b) => b.maxWeight - a.maxWeight).slice(0, 6)) {
    console.log(`    s${p.sec}.e${p.entry} case=${p.cases} sum=${p.sum} max=${p.maxWeight} votes=${JSON.stringify(p.votes.map(v => [v.weight, v.targets]))}`);
  }
  console.log('  池内重复指向样例：');
  for (const p of dupPools.slice(0, 4)) console.log(`    s${p.sec}.e${p.entry} dup=${p.duplicateTargetsInPool} votes=${JSON.stringify(p.votes.map(v => [v.weight, v.targets]))}`);
}
