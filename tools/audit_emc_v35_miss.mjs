#!/usr/bin/env node
/**
 * audit_emc_v35_miss.mjs — 诊断 v35 P7「veto=0」的离线归因（只读）
 *
 * P7 实机：act=84 / rep=57 / noalt=57 / veto=0 / fail=0（解析全部成功），
 * K 行 why 全是 4（找不到签名不同的 case）。本脚本用与插件完全相同的
 * LEN 文法与 op14-entry FNV 签名，在离线表上量化三件事：
 *   1. 有多少 case 是「空签名」（body 内无 op14 ⇒ 该池不是动作选择池）；
 *   2. 每个 case「向后存在不同签名」的比例（B1 的理论成功率）；
 *   3. 运行时扫描起点在块中间时，可见 case 数会缩短多少。
 *
 * 用法：node tools/audit_emc_v35_miss.mjs
 * 产物：out/emc_offline/v35_miss.md
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
const fnv = (h, b) => Math.imul((h ^ b) >>> 0, 0x01000193) >>> 0;

const nameOf = (label) => {
  try {
    const map = JSON.parse(fs.readFileSync(SLOT_MAP, 'utf-8'));
    const m = /^em(\d+)_(\d+)/.exec(label);
    const hit = m && map.find(x => x.emid === Number(m[1]));
    return hit ? hit.cn : '';
  } catch { return ''; }
};

// 与插件 scan_cases 一致：从块 begin 起收集同 op case，签名 = body 内 op14 entry 序列
function casesOf(ins, i, op) {
  const cs = [];
  let depth = 0;
  for (let j = i + 1; j < ins.length; j++) {
    const x = ins[j];
    if (x.kind === 'end') break;
    if (x.op !== op) continue;
    if (x.sub === 0) { depth++; continue; }
    if (x.sub === 0xff) { if (depth === 0) break; depth--; continue; }
    if (x.sub === 1 && depth === 0) cs.push(j);
  }
  return cs.map((idx, k) => {
    let end = ins.length;
    if (k + 1 < cs.length) end = cs[k + 1];
    else {
      let d = 0;
      for (let j = idx + 1; j < ins.length; j++) {
        if (ins[j].kind === 'end') { end = j; break; }
        if (ins[j].op === op && ins[j].sub === 0) d++;
        if (ins[j].op === op && ins[j].sub === 0xff) { if (d === 0) { end = j; break; } d--; }
      }
    }
    let h = FNV0, c = 0;
    for (let j = idx + 1; j < end && c < 16; j++) {
      if (ins[j].op === 0x14) { h = fnv(h, ins[j].args[0] ?? 0); c++; }
    }
    return { sig: h };
  });
}

function stat(buf, label) {
  const { doc } = cmdtblFromArc(buf, `enemy\\cmd_tbl\\${label}_cmdtbl`, label);
  let blocks = 0, cs = 0, empty = 0, backOk = 0, nonEmptyBack = 0, nonEmptyTot = 0;
  let midVisible = 0;            // 模拟从随机中间 case 起扫描，可见 case 数总和
  const ncDist = new Map();
  for (const s of doc.sections) for (const e of s.entries) {
    const ins = e.ins;
    for (let i = 0; i < ins.length; i++) {
      const x = ins[i];
      if (x.op !== 0x02 || x.sub !== 0) continue;
      const arr = casesOf(ins, i, 0x02);
      if (!arr.length) continue;
      blocks++; cs += arr.length;
      ncDist.set(arr.length, (ncDist.get(arr.length) ?? 0) + 1);
      for (let k = 0; k < arr.length; k++) {
        if (arr[k].sig === FNV0) empty++;
        const ok = arr.slice(k + 1).some(c => c.sig !== arr[k].sig);
        if (ok) backOk++;
        if (arr[k].sig !== FNV0) { nonEmptyTot++; if (ok) nonEmptyBack++; }
        midVisible += arr.length - k;   // 从第 k 个 case 起扫描，只看得到后半段
      }
    }
  }
  return { label, name: nameOf(label), blocks, cs, empty, backOk, nonEmptyBack, nonEmptyTot,
    midVisible, ncDist: [...ncDist.entries()].sort((a, b) => a[0] - b[0]) };
}

const arcs = fs.readdirSync(ARC).filter(f => /\.arc$/i.test(f)).sort();
const rows = [];
for (const f of arcs) {
  const label = f.replace(/\.arc$/i, '');
  try { rows.push(stat(fs.readFileSync(path.join(ARC, f)), label)); }
  catch (e) { console.error(`  FAIL ${label}: ${e.message}`); }
}
const active = rows.filter(r => r.blocks > 0);
const sum = k => active.reduce((a, r) => a + r[k], 0);
const pick = lb => rows.find(r => r.label === lb);
const L = [];
L.push('# v35 P7「veto=0」离线归因报告\n');
L.push(`数据源：\`${ARC}\` ${arcs.length} 个 arc / ${active.length} 张含 op02 块的表；只读解析。`);
L.push('算法与插件 `scan_cases` 一致（LEN 文法 + case body 内 `op14` entry 序列 FNV-1a 签名）。\n');
L.push('## P7 实机对照\n');
L.push('```');
L.push('act=84  rep=57  noalt=57  veto=0  fail=0  ok=27  live=1  FATAL=0');
L.push('K 行 why 全为 4（找不到签名不同的 case）；nc 分布 1:33 / 2:8 / 3:6 / 4:5 / 5:3 / 6:2');
L.push('K 行 sig==FNV0 36/57 = 63%；d 分布 7:27 / 3:21 / 4:9（均 ≤8，基址推导正确）');
L.push('```');
L.push('⇒ **解析本身 100% 成功**（fail=0、d≤8），但一次否决都没发生。本脚本判定原因是下面两条，而不是表结构无解。\n');
L.push('## 全量\n');
L.push(`- op02 块 ${sum('blocks')} / case ${sum('cs')}；空签名 case ${sum('empty')} = ${(100 * sum('empty') / sum('cs')).toFixed(1)}%。`);
L.push(`- 每个 case「向后存在不同签名」= ${sum('backOk')}/${sum('cs')} = **${(100 * sum('backOk') / sum('cs')).toFixed(1)}%**（B1 的理论成功率）。`);
L.push(`- 非空签名 case 中向后有替代 = ${sum('nonEmptyBack')}/${sum('nonEmptyTot')} = **${(100 * sum('nonEmptyBack') / sum('nonEmptyTot')).toFixed(1)}%**。`);
L.push(`- 从块中间第 k 个 case 起扫描，平均只可见 ${(sum('midVisible') / sum('cs')).toFixed(2)} 个 case（完整块平均 ${(sum('cs') / sum('blocks')).toFixed(2)} 个）⇒ 起点在块中间会损失约 ${(100*(1-sum('midVisible')/sum('cs')/(sum('cs')/sum('blocks')))).toFixed(0)}% 的可见候选。\n`);
L.push('## P7 的「nc × 空签名」交叉证据（决定性）\n');
L.push('| 运行时扫描到的 case 数 nc | 行数 | 其中空签名 |');
L.push('|---|---|---|');
L.push('| 1 | 33 | 26 (79%) |');
L.push('| 2 | 8 | 7 (88%) |');
L.push('| 3 | 6 | 3 (50%) |');
L.push('| ≥4 | 10 | **0 (0%)** |');
L.push('\n**扫描越短，签名越容易为空**；而离线完整块的空签名只占 11.9%（变形冰鲨 14%）、`nc=1` 只占 14%。');
L.push('⇒ 首要归因不是表结构，而是 **运行时 `scan_cases` 提前终止**：case body 未扫完 ⇒ `op14` 漏计 ⇒ 签名退化为 FNV0、可见候选只剩 1 个 ⇒ 必然 noalt。');
L.push('最可能的机制：扫描从 `a1-1` 起时若落在**嵌套 op02 块内部**，depth 从 0 开始会把该嵌套块的 `endblock` 误判为当前块结束而立即 break。需 v36 实机验证。\n');
L.push('## 三只重点怪\n');
L.push('| 怪 | 池 | case | 空签名 | 向后有替代(全部) | 向后有替代(非空签名) | case 数分布(前 8) |');
L.push('|---|---|---|---|---|---|---|');
for (const lb of ['em067_00', 'em010_00', 'em020_00']) {
  const r = pick(lb);
  if (!r) continue;
  L.push(`| ${r.label} ${r.name} | ${r.blocks} | ${r.cs} | ${r.empty} (${(100*r.empty/r.cs).toFixed(1)}%) | ${(100*r.backOk/r.cs).toFixed(1)}% | ${(100*r.nonEmptyBack/Math.max(r.nonEmptyTot,1)).toFixed(1)}% | ${r.ncDist.slice(0,8).map(([n,c])=>`${n}:${c}`).join(' ')} |`);
}
L.push('\n## 结论与修复方向\n');
L.push('1. **修复扫描终止（首要）**：从 `a1-1` 向前定位最近的 `op==0x02 && sub==0` begin，用 LEN decode 校验能对齐回 `a1-1`，再从 begin 起扫描并正确维护 depth。这样 case body 完整、`op14` 不漏计、`nc` 恢复到离线水平（平均 5.6）。`delta` 仍为正 ⇒ `nr>0`，不引入往回跳的风险。');
L.push('2. **跳过空签名池**：body 内确实没有 `op14` 的池（离线 11.9%，与 `repeat.mjs` 的 `emptyVote` 对应）不是动作选择池，v35 把 FNV0 当成「同一动作」判重必然 noalt ⇒ 应不判重、不计入 noalt、直接透传。');
L.push('3. 修完后 B1 理论成功率约 **76.8%**（非空签名池 85.0%），可做 v36；`op14` 之外的动作排队 op 仍需另行确认，本脚本不臆测。');
L.push('4. **P7 两个体感与 v35 无关**：`veto=0` ⇒ 插件未改写任何返回值，游戏行为等同原版只读探针。发呆/三连喷吐需同怪原版对照或下一版加长时间分层采样才能归因。\n');
fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(path.join(OUT, 'v35_miss.md'), L.join('\n'));
console.log(L.slice(0, 16).join('\n'));
console.log(`\n[written] ${OUT}/v35_miss.md  (${active.length} tables)`);
