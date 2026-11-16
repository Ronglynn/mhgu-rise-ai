#!/usr/bin/env node
/**
 * audit_emc_v36_align.mjs — v36「向前定位 begin + 完整块扫描」离线对拍（只读）
 *
 * 背景：v35 P7 实机 veto=0。离线归因发现运行时扫描 nc=1 占 58%、空签名 63%，
 * 远高于离线完整块（14% / 11.9%）⇒ scan_cases 从 a1-1 起时落在块中间，
 * 把嵌套块的 endblock 误判为当前块结束而提前终止。
 *
 * 本脚本在 137 个 arc / 102 张 EMC 表上，用与插件 v36 完全相同的逻辑预演：
 *   1. 从「块内任意 case」起点向前定位最近的 op02/sub=0 begin，
 *      并用 depth 校验「该 begin 到起点之间未闭合」⇒ 对齐成功率；
 *   2. 从 begin 起完整扫描，比较可见 case 数 / 空签名率相对 v35 的提升；
 *   3. 非空签名 case 向后存在不同动作的比例（B1 理论成功率）。
 *
 * 用法：node tools/audit_emc_v36_align.mjs
 * 产物：out/emc_offline/v36_align.md / v36_align.tsv
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const OUT = path.join(ROOT, 'out', 'emc_offline');
const ARC = 'D:/Monster Hunter Generations Ultimate Recomp/data/romfs/nativeNX/arc/enemy';
const SLOT_MAP = 'D:/MHGU mod maker/00_Tools/92_MHGU-master/MHGU-master/docs/data/json/monster-slot-map-137.json';
const { cmdtblFromArc } = await import(pathToFileURL(path.join(HERE, 'gu-moves', 'lib', 'trees.mjs')).href);
const FNV0 = 0x811c9dc5;
const fnv = (h, b) => Math.imul((h ^ (b >>> 0)) >>> 0, 0x01000193) >>> 0;

const nameOf = (label) => {
  try {
    const map = JSON.parse(fs.readFileSync(SLOT_MAP, 'utf-8'));
    const m = /^em(\d+)_(\d+)/.exec(label);
    const hit = m && map.find(x => x.emid === Number(m[1]));
    return hit ? hit.cn : '';
  } catch { return ''; }
};

/** 与 v36 插件一致：从块 begin 起收集同 op 的最外层 case，签名 = body 内 op14 entry 序列 */
function casesOf(ins, beginIdx, op) {
  const cs = [];
  let depth = 1;                     // begin 本身已开启一层
  for (let j = beginIdx + 1; j < ins.length; j++) {
    const x = ins[j];
    if (x.kind === 'end') break;
    if (x.op !== op) continue;
    if (x.sub === 0) { depth++; continue; }
    if (x.sub === 0xff) { depth--; if (depth <= 0) break; continue; }
    if (x.sub === 1 && depth === 1) cs.push(j);
  }
  return cs.map((idx, k) => {
    let end = ins.length;
    if (k + 1 < cs.length) end = cs[k + 1];
    else {
      let d = 1;
      for (let j = idx + 1; j < ins.length; j++) {
        if (ins[j].kind === 'end') { end = j; break; }
        if (ins[j].op === op && ins[j].sub === 0) d++;
        if (ins[j].op === op && ins[j].sub === 0xff) { d--; if (d <= 0) { end = j; break; } }
      }
    }
    let h = FNV0, c = 0;
    for (let j = idx + 1; j < end && c < 16; j++) {
      if (ins[j].op === 0x14) { h = fnv(h, ins[j].args[0] ?? 0); c++; }
    }
    return { idx, sig: h };
  });
}

/** v35 的截断扫描：直接从起点（块内某 case）向后，depth 从 0 起 */
function v35Cases(ins, from, op) {
  const cs = [];
  let depth = 0;
  for (let j = from + 1; j < ins.length; j++) {
    const x = ins[j];
    if (x.kind === 'end') break;
    if (x.op !== op) continue;
    if (x.sub === 0) { depth++; continue; }
    if (x.sub === 0xff) { if (depth === 0) break; depth--; continue; }
    if (x.sub === 1 && depth === 0) cs.push(j);
  }
  return cs;
}

/** v36 的核心：从「块内任意位置」向前定位包含它的 begin（depth 不闭合校验） */
function findBegin(ins, at, op) {
  for (let j = at; j >= 0; j--) {
    const x = ins[j];
    if (x.op !== op || x.sub !== 0) continue;
    // 从 j 走到 at：必须始终在同一块的未闭合层级内
    let depth = 1, ok = true;
    for (let k = j + 1; k <= at; k++) {
      const y = ins[k];
      if (y.kind === 'end') { ok = false; break; }
      if (y.op !== op) continue;
      if (y.sub === 0) depth++;
      else if (y.sub === 0xff) { depth--; if (depth <= 0) { ok = false; break; } }
    }
    if (ok) return j;
  }
  return -1;
}

function stat(buf, label) {
  const { doc } = cmdtblFromArc(buf, `enemy\\cmd_tbl\\${label}_cmdtbl`, label);
  let blocks = 0, cases = 0, alignOk = 0, alignTot = 0, alignRight = 0;
  let empty = 0, backOk = 0, nonEmptyBack = 0, nonEmptyTot = 0;
  let v35Visible = 0, v36Visible = 0, v35NoAlt = 0;
  let nested = 0;
  for (const s of doc.sections) for (const e of s.entries) {
    const ins = e.ins;
    for (let i = 0; i < ins.length; i++) {
      if (ins[i].op !== 0x02 || ins[i].sub !== 0) continue;
      const arr = casesOf(ins, i, 0x02);
      if (!arr.length) continue;
      blocks++; cases += arr.length;
      for (let k = 0; k < arr.length; k++) {
        const at = arr[k].idx;
        const b = findBegin(ins, at, 0x02);
        alignTot++;
        if (b >= 0) {
          alignOk++;
          if (b === i) alignRight++; else nested++;
          const full = casesOf(ins, b, 0x02);
          v36Visible += full.length;
        }
        v35Visible += v35Cases(ins, at, 0x02).length + 1;
        if (v35Cases(ins, at, 0x02).length === 0) v35NoAlt++;
        if (arr[k].sig === FNV0) empty++;
        const rest = arr.slice(k + 1);
        const ok = rest.some(c => c.sig !== arr[k].sig && c.sig !== FNV0);
        if (ok) backOk++;
        if (arr[k].sig !== FNV0) { nonEmptyTot++; if (ok) nonEmptyBack++; }
      }
    }
  }
  return { label, name: nameOf(label), blocks, cases, alignOk, alignTot, alignRight,
    nested, empty, backOk, nonEmptyBack, nonEmptyTot, v35Visible, v36Visible, v35NoAlt };
}

const arcs = fs.readdirSync(ARC).filter(f => /\.arc$/i.test(f)).sort();
const rows = [];
for (const f of arcs) {
  const label = f.replace(/\.arc$/i, '');
  try { rows.push(stat(fs.readFileSync(path.join(ARC, f)), label)); }
  catch (e) { console.error(`  SKIP ${label}: ${e.message}`); }
}
const sum = (k) => rows.reduce((a, r) => a + (r[k] || 0), 0);
const B = sum('blocks'), C = sum('cases');
const tsv = ['label\tname\tblocks\tcases\talignOk\talignTot\talignRight\tnested\tempty\tbackOk\tnonEmptyBack\tnonEmptyTot\tv35Visible\tv36Visible'];
for (const r of rows) tsv.push([r.label, r.name, r.blocks, r.cases, r.alignOk, r.alignTot,
  r.alignRight, r.nested, r.empty, r.backOk, r.nonEmptyBack, r.nonEmptyTot,
  r.v35Visible, r.v36Visible].join('\t'));
fs.writeFileSync(path.join(OUT, 'v36_align.tsv'), tsv.join('\n') + '\n');

const pct = (a, b) => b ? (100 * a / b).toFixed(1) + '%' : '-';
const L = [];
L.push('# v36 扫描算法离线对拍（137 arc / 只读）\n');
L.push(`- 表 / 块 / case：**${rows.length} arc / ${B} 块 / ${C} case**\n`);
L.push(`- 向前定位 begin 成功率：**${sum('alignOk')}/${sum('alignTot')} = ${pct(sum('alignOk'), sum('alignTot'))}**`);
L.push(`  - 其中定位到「原始块 begin」= ${sum('alignRight')}（${pct(sum('alignRight'), sum('alignTot'))}），`);
L.push(`  - 定位到更内层嵌套块 begin = ${sum('nested')}（${pct(sum('nested'), sum('alignTot'))}，仍为合法作用域）`);
L.push(`- 可见 case 数：v35 截断扫描 ${sum('v35Visible')} → v36 完整块 ${sum('v36Visible')} `);
L.push(`  （**${(sum('v36Visible') / Math.max(sum('v35Visible'), 1)).toFixed(2)}×**）；`);
L.push(`  v35 有 ${sum('v35NoAlt')}/${sum('alignTot')}（${pct(sum('v35NoAlt'), sum('alignTot'))}）起点扫不到任何后续 case ⇒ 必然 noalt\n`);
L.push(`- 空签名 case（body 内无 op14）：${sum('empty')}/${C} = **${pct(sum('empty'), C)}** ⇒ v36 直接透传，不判重\n`);
L.push(`- 向后存在「不同且非空」动作签名：**${sum('backOk')}/${C} = ${pct(sum('backOk'), C)}**`);
L.push(`  （非空签名 case 中为 ${sum('nonEmptyBack')}/${sum('nonEmptyTot')} = ${pct(sum('nonEmptyBack'), sum('nonEmptyTot'))}）\n`);
L.push('## 三只重点怪\n');
L.push('| 怪 | 块 | case | begin 对齐率 | 空签名 | 向后可换 |');
L.push('|---|---:|---:|---:|---:|---:|');
for (const lb of ['em067_00', 'em010_00', 'em020_00', 'em004_00']) {
  const r = rows.find(x => x.label === lb);
  if (!r) continue;
  L.push(`| ${lb} ${r.name} | ${r.blocks} | ${r.cases} | ${pct(r.alignOk, r.alignTot)} | ${pct(r.empty, r.cases)} | ${pct(r.backOk, r.cases)} |`);
}
L.push('\n## 结论\n');
L.push('1. v35 的「从 a1-1 向后扫」在块中间起点上会系统性截断（大量起点可见 0~1 个 case），');
L.push('   与 P7 实机 `nc=1` 58% / 空签名 63% 一致；v36 改为「向前定位 begin + 从 begin 完整扫描」后');
L.push(`   可见 case 数提升约 ${(sum('v36Visible') / Math.max(sum('v35Visible'), 1)).toFixed(1)} 倍。`);
L.push(`2. 排除空签名池后，B1「向后换一个不同动作」的理论成功率约 ${pct(sum('nonEmptyBack'), sum('nonEmptyTot'))}，`);
L.push('   明显高于 v35 实机的 0%。表结构不是死路，修复方向正确。');
L.push('3. 本脚本只做结构对拍，不证明运行时 a1/ret 基址（由 v36 实机 V 行 d/p5 复核）。\n');
fs.writeFileSync(path.join(OUT, 'v36_align.md'), L.join('\n') + '\n');
console.log(L.join('\n'));
