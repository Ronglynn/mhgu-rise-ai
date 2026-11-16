#!/usr/bin/env node
/**
 * audit_emc_weighted.mjs — 解释 v36 P8 实机 `empt=323/551=58.6%`、`noalt=38/40` 的离线核验
 *
 * 假设：离线按「case 数」统计空签名只有 11.9%，但 GU 是 rand%100 按 case 值（权重）
 * 抽选 ⇒ 应按权重加权统计。若「空签名 case 的权重和」≈59%，则实机的 empt 高不是 bug，
 * 而是表结构本身：高权重分支常常不排队动作（原生待机/Think 间隙）。
 * 同理，「向后存在不同动作」按权重加权后应显著低于按 case 计的 82.8%，解释 noalt。
 *
 * 用法：node tools/audit_emc_weighted.mjs
 * 产物：out/emc_offline/weighted.md / weighted.tsv
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

function casesOf(ins, beginIdx, op) {
  const cs = [];
  let depth = 1;
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
    // case 值 = args[0]（1 字节，块内和恒 100 的那个数）
    return { sig: h, w: (ins[idx].args[0] ?? 0) & 0xff };
  });
}

function stat(buf, label) {
  const { doc } = cmdtblFromArc(buf, `enemy\\cmd_tbl\\${label}_cmdtbl`, label);
  let blocks = 0, cases = 0;
  let wTotal = 0, wEmpty = 0;         // 空签名 case 的权重和
  let wBackOk = 0, wRep = 0;          // 向后有不同动作的权重 / 非空签名权重
  let cEmpty = 0, cBackOk = 0;
  for (const s of doc.sections) for (const e of s.entries) {
    const ins = e.ins;
    for (let i = 0; i < ins.length; i++) {
      if (ins[i].op !== 0x02 || ins[i].sub !== 0) continue;
      const arr = casesOf(ins, i, 0x02);
      if (!arr.length) continue;
      blocks++; cases += arr.length;
      for (let k = 0; k < arr.length; k++) {
        const w = arr[k].w;
        wTotal += w;
        const empty = arr[k].sig === FNV0;
        if (empty) { wEmpty += w; cEmpty++; }
        const back = arr.slice(k + 1).some(c => c.sig !== arr[k].sig && c.sig !== FNV0);
        if (back) cBackOk++;
        if (!empty) { wRep += w; if (back) wBackOk += w; }
      }
    }
  }
  return { label, name: nameOf(label), blocks, cases, wTotal, wEmpty, wRep, wBackOk, cEmpty, cBackOk };
}

const arcs = fs.readdirSync(ARC).filter(f => /\.arc$/i.test(f)).sort();
const rows = [];
for (const f of arcs) {
  const label = f.replace(/\.arc$/i, '');
  try { rows.push(stat(fs.readFileSync(path.join(ARC, f)), label)); }
  catch (e) { console.error(`  SKIP ${label}: ${e.message}`); }
}
const sum = (k) => rows.reduce((a, r) => a + (r[k] || 0), 0);
const tsv = ['label\tname\tblocks\tcases\twTotal\twEmpty\twRep\twBackOk\tcEmpty\tcBackOk'];
for (const r of rows) tsv.push([r.label, r.name, r.blocks, r.cases, r.wTotal, r.wEmpty,
  r.wRep, r.wBackOk, r.cEmpty, r.cBackOk].join('\t'));
fs.writeFileSync(path.join(OUT, 'weighted.tsv'), tsv.join('\n') + '\n');

const pct = (a, b) => b ? (100 * a / b).toFixed(1) + '%' : '-';
const L = [];
L.push('# EMC 加权口径核验（解释 v36 P8 的 empt / noalt）\n');
L.push(`- 表 / 块 / case：**${rows.length} arc / ${sum('blocks')} 块 / ${sum('cases')} case**\n`);
L.push('| 口径 | 空签名（选中后应透传） | 向后有不同动作（B1 可替换） |');
L.push('|---|---:|---:|');
L.push(`| 按 case 数（旧口径） | ${pct(sum('cEmpty'), sum('cases'))} | ${pct(sum('cBackOk'), sum('cases'))} |`);
L.push(`| **按 case 值加权**（rand%100 的真实口径） | **${pct(sum('wEmpty'), sum('wTotal'))}** | **${pct(sum('wBackOk'), sum('wTotal'))}**（非空签名权重中 ${pct(sum('wBackOk'), sum('wRep'))}） |`);
L.push(`| **v36 P8 实机** | **empt=323/551=58.6%** | **noalt=38/40=95%**（即成功率 5%） |\n`);
L.push('## 三只重点怪（按权重）\n');
L.push('| 怪 | 块 | case | 空签名权重占比 | 向后可换权重占比 |');
L.push('|---|---:|---:|---:|---:|');
for (const lb of ['em067_00', 'em010_00', 'em020_00', 'em004_00']) {
  const r = rows.find(x => x.label === lb);
  if (!r) continue;
  L.push(`| ${lb} ${r.name} | ${r.blocks} | ${r.cases} | ${pct(r.wEmpty, r.wTotal)} | ${pct(r.wBackOk, r.wTotal)} |`);
}
L.push('\n## 结论\n');
L.push('1. 若「空签名权重占比」接近实机 58.6%，则 `empt` 高**不是运行时扫描 bug**，');
L.push('   而是 GU 表结构：高权重分支常常不排队动作（原生待机 / Think 间隙）。');
L.push('   v36 把它们排除是对的，但也意味着规则作用面被结构性地砍掉一大半。');
L.push('2. 若「向后可换权重占比」很低，则 `noalt` 高是 **B1「只向后找」的结构性限制**：');
L.push('   rand%100 的累积阈值常落在靠后的 case，后面已没有不同动作 ⇒ 否决失败。');
L.push('   ⇒ v37 应改为「否决后重抽」（换随机阈值让 matcher 重新抽一次），');
L.push('   而不是只在当前 ret 之后找一个 case —— 这也更贴 Rise 的「否决后重抽」。');
L.push('3. 本脚本只做离线结构统计；运行时 p5 分布由 v36 P8 的 V 行（46 / 89）与后续实机复核。\n');
fs.writeFileSync(path.join(OUT, 'weighted.md'), L.join('\n') + '\n');
console.log(L.join('\n'));
