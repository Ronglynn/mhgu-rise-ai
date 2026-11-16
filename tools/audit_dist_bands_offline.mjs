#!/usr/bin/env node
/**
 * audit_dist_bands_offline.mjs — 全量离线抽取「怪物距离档」表（只读，零实机）
 *
 * 数据源：enemy/*.arc 内两个条目
 *   1) enemy\cmd_tbl\<label>_cmdtbl  → EMC 距离 switch 块（op 0x0b/0x17/0x57/0x5c/0x7c）
 *      case 操作数序列 + block begin 参数（slot 候选）
 *   2) enemy\dt_tune\<label>_dttune  → 4 x f32 / 行 的距离阈值表（mode 4/14/21/22 用）
 *
 * 依据：
 *   docs/reference/formats/emc.md §4/§5（mode→阈值构造）、
 *   06_MH4UPort_IPS32/.../tools/dt_convert.py:77-84,153-173（ranges 定义），
 *   docs/reference/formats/dttune.md:66-68（em001 实测数值，曾被标「语义未知」）。
 *
 * 用法：node tools/audit_dist_bands_offline.mjs [labelSubstr ...]
 * 产物：out/dist_bands_all.json
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const OUT_JSON = path.join(ROOT, 'out', 'dist_bands_all.json');
const ARC_DIR = 'D:/Monster Hunter Generations Ultimate Recomp/data/romfs/nativeNX/arc/enemy';

const { cmdtblFromArc, buildTree } = await import(
  pathToFileURL(path.join(HERE, 'gu-moves', 'lib', 'trees.mjs')).href);
const { readArc, inflateEntry } = await import(
  pathToFileURL(path.join(HERE, 'mhgu', 'arc.mjs')).href);

// op -> [语义名, 默认 mode, 阈值类型]
// mode 来自 emc.md §4/§5 与 mhgu/emc.mjs OP_NAMES；0x0b 的 mode 4 有
// 「begin operand == 0」前提（emc.md:42），此处按默认记录并标注假设。
const DIST = {
  0x0b: ['target_dist_rot', 4, 'TABLE'],
  0x17: ['dist_3d', 6, 'SCALE100'],
  0x57: ['target_dist_rot2', 14, 'TABLE'],
  0x5c: ['dist_xz', 16, 'SCALE100'],
  0x7c: ['min_dist6', 24, 'SCALE100'],
  // v60 实机 Z 行额外观察到的两个几何 switch（emc.md 未列 mode，阈值构造未知）
  0x16: ['other_geo_mode5', 5, 'UNKNOWN'],
  0x6a: ['other_geo_mode26', 26, 'UNKNOWN'],
};

function f32(buf, off) {
  if (off < 0 || off + 4 > buf.length) return NaN;
  return buf.readFloatLE(off);
}

/** 判定一行是否为「4 个递增的有限 f32 距离阈值」。
 *  下界 50 排除非正规浮点与倍率区（1.0~2.0）；上界 1e5 排除噪声。 */
function isRangeRow(v) {
  if (!v.every(Number.isFinite)) return false;
  if (!(v[0] >= 50 && v[0] < v[1] && v[1] < v[2] && v[2] < v[3])) return false;
  if (!(v[3] <= 1e5)) return false;
  return v[3] / v[0] >= 1.5 && v[3] / v[0] < 100;
}

/**
 * 扫 dttune 找 range 行。
 * 实测（em001 +0x13e / em004 +0x18e / em005 +0x18e）表起点是 **2 字节对齐
 * 而非 4 字节对齐**，且每怪偏移不同、行间隔也非固定 16B（常夹 12B/16B
 * 的 offset 数据）⇒ 逐 2 字节扫描所有命中行，再按「相邻起点 <=64B」聚类。
 * emc.md 的 [[ctx+0x75ec]+0x7c] 是 loader 后的运行时对象字段，
 * 不是文件偏移，不能按 +0x7c seek。
 */
function scanRanges(buf) {
  const hits = [];
  for (let off = 0; off + 16 <= buf.length; off += 2) {
    const v = [0, 1, 2, 3].map(k => f32(buf, off + 4 * k));
    if (isRangeRow(v)) hits.push({ off, v });
  }
  const groups = [];
  for (const h of hits) {
    const g = groups.find(x => h.off - x.last <= 64);
    if (g) { g.rows.push(h); g.last = h.off; }
    else groups.push({ first: h.off, last: h.off, rows: [h] });
  }
  groups.sort((a, b) => b.rows.length - a.rows.length || b.first - a.first);
  const cands = groups.slice(0, 4).map(g => ({
    offset: '0x' + g.first.toString(16),
    offsets: g.rows.map(r => '0x' + r.off.toString(16)),
    rows: g.rows.map(r => r.v),
  }));
  return { best: cands[0] ?? null, candidateCount: groups.length, candidates: cands };
}

function distBlocksOf(doc) {
  const out = [];
  for (const s of doc.sections) {
    for (const e of s.entries) {
      const { root } = buildTree(e.ins);
      const walk = (body) => {
        for (const n of body) {
          if (n.t === 'leaf') continue;
          const meta = DIST[n.op];
          if (meta) {
            const cases = n.branches.filter(b => b.kind === 'case')
              .map(b => (b.args && b.args.length ? b.args[0] : null));
            const [opName, mode, kind] = meta;
            out.push({
              sec: s.index, entry: e.index, pos: n.pos,
              op: '0x' + n.op.toString(16).padStart(2, '0'),
              opName, mode, thresholdType: kind,
              beginArgs: n.args ?? [],
              cases,
              scale100: kind === 'SCALE100' ? cases.map(c => (c == null ? null : c * 100)) : null,
            });
          }
          for (const br of n.branches) walk(br.body);
        }
      };
      if (root.branches && root.branches[0]) walk(root.branches[0].body);
    }
  }
  return out;
}

const filter = process.argv.slice(2);
const labels = fs.readdirSync(ARC_DIR)
  .filter(f => /\.arc$/i.test(f))
  .map(f => f.replace(/\.arc$/i, ''))
  .filter(l => !filter.length || filter.some(q => l.includes(q)))
  .sort();

const monsters = [];
let errCount = 0;
for (const label of labels) {
  const rec = { label, distBlocks: [], range: null, errors: [] };
  try {
    const buf = fs.readFileSync(path.join(ARC_DIR, label + '.arc'));
    // --- cmdtbl ---
    try {
      const { doc } = cmdtblFromArc(buf, `enemy\\cmd_tbl\\${label}_cmdtbl`, label);
      rec.distBlocks = distBlocksOf(doc);
    } catch (e) { rec.errors.push('cmdtbl: ' + e.message); }
    // --- dttune ---
    try {
      const arc = readArc(buf, label);
      const ent = arc.entries.find(x => /_dttune$/i.test(x.name));
      if (!ent) rec.errors.push('dttune: entry missing');
      else {
        const d = inflateEntry(buf, ent, label);
        rec.range = scanRanges(d);
        rec.dttuneBytes = d.length;
      }
    } catch (e) { rec.errors.push('dttune: ' + e.message); }
  } catch (e) { rec.errors.push('arc: ' + e.message); }
  if (rec.errors.length) errCount++;
  monsters.push(rec);
  process.stdout.write(`\r[${monsters.length}/${labels.length}] ${label} blocks=${rec.distBlocks.length} rows=${rec.range?.best?.rows.length ?? 0}   `);
}
process.stdout.write('\n');

const byOp = {};
const seqCount = {};
let totalBlocks = 0, tableBlocks = 0, scaleBlocks = 0, unknownBlocks = 0, withRanges = 0;
for (const m of monsters) {
  for (const b of m.distBlocks) {
    totalBlocks++;
    byOp[b.op] = (byOp[b.op] ?? 0) + 1;
    if (b.thresholdType === 'TABLE') tableBlocks++;
    else if (b.thresholdType === 'SCALE100') scaleBlocks++;
    else unknownBlocks++;
    const key = b.op + '|' + b.cases.join(',');
    seqCount[key] = (seqCount[key] ?? 0) + 1;
  }
  if (m.range?.best?.rows.length) withRanges++;
}

const res = {
  generated: new Date().toISOString(),
  arcDir: ARC_DIR,
  arcCount: labels.length,
  monsters,
  summary: {
    monsters: monsters.length, errMonsters: errCount,
    totalDistBlocks: totalBlocks, tableBlocks, scaleBlocks, unknownBlocks,
    monstersWithRangeRows: withRanges,
    byOp,
    topCaseSequences: Object.entries(seqCount)
      .sort((a, b) => b[1] - a[1]).slice(0, 30).map(([k, v]) => ({ seq: k, count: v })),
  },
};
fs.writeFileSync(OUT_JSON, JSON.stringify(res, null, 1));
console.log('wrote', path.relative(ROOT, OUT_JSON));
console.log(JSON.stringify(res.summary, null, 1).slice(0, 1400));
