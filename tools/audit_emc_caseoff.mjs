#!/usr/bin/env node
/**
 * audit_emc_caseoff.mjs — v35「运行时 case 扫描 + body 签名」算法的离线对拍（只读）
 *
 * 目的（DESIGN_v35.md §5.2 要求）：插件 hook 内不解析整张表，只从当前指令
 * （a1 指向 sub、a1-1 指向 opcode）起按 LEN 规则逐条 decode，收集同一个 op
 * 的 case 指令，比较各 case body 的字节签名，选出与上次不同的分支。
 * 本脚本在 137 个 arc / 102 张表上用同一套 LEN 与同一套签名算法预演，
 * 回答三个问题：
 *   1. 相邻 case 的字节距离是否落在 P6 实机 ret 值域（0..43）；
 *   2. 有多少 op02 块能找到「body 签名不同」的下一个 case（可替换率）；
 *   3. 全部 case 签名相同的块（必然同招池）占比 —— 这部分 v35 会安全透传。
 *
 * 用法：node tools/audit_emc_caseoff.mjs
 * 产物：out/emc_offline/caseoff.tsv / caseoff.md
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const OUT = path.join(ROOT, 'out', 'emc_offline');
const ARC_DIR = 'D:/Monster Hunter Generations Ultimate Recomp/data/romfs/nativeNX/arc/enemy';
const SLOT_MAP = 'D:/MHGU mod maker/00_Tools/92_MHGU-master/MHGU-master/docs/data/json/monster-slot-map-137.json';
const { cmdtblFromArc } = await import(pathToFileURL(path.join(HERE, 'gu-moves', 'lib', 'trees.mjs')).href);
const { LEN_TABLE } = await import(pathToFileURL(path.join(HERE, 'mhgu', 'emc.mjs')).href);

const nameOf = (label) => {
  try {
    const map = JSON.parse(fs.readFileSync(SLOT_MAP, 'utf-8'));
    const m = /^em(\d+)_(\d+)/.exec(label);
    const hit = m && map.find(x => x.emid === Number(m[1]));
    return hit ? hit.cn : '';
  } catch { return ''; }
};

// 与插件 v35 完全一致：签名 = case body 内所有 op14(排队动作) 的 entry 字节序列
// op14 是 leaf，LEN=1，故 entry = 指令后第一个 operand 字节。
// 这正是 Rise `_CheckPrevTableInfoList` 里「按动作表项否决」的 GU 等价物，
// 而不是按分支编号/任意字节判重。
function fnv(bytes) {
  let h = 0x811c9dc5;
  for (let i = 0; i < Math.min(bytes.length, 16); i++) {
    h ^= bytes[i];
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}
function sigEntries(ins, from, to) {
  const bytes = [];
  for (let j = from; j < to && bytes.length < 16; j++) {
    if (ins[j].op === 0x14) bytes.push(ins[j].args[0] ?? 0);
  }
  return fnv(bytes);
}

// 模拟插件 hook：从某个 op02 块起，按 ins 顺序收集同 op 的 case，直到 endblock
function scanBlock(ins, start, op) {
  const cases = [];
  let depth = 0;
  // start 本身就是当前块的 begin，从下一条指令开始扫（depth=0）
  for (let i = start + 1; i < ins.length; i++) {
    const x = ins[i];
    if (x.kind === 'end') break;
    if (x.op !== op) continue;               // 其它 op 的指令（含嵌套块）不影响
    if (x.sub === 0) { depth++; continue; }  // 同 op 嵌套 begin
    if (x.sub === 0xff) { if (depth === 0) break; depth--; continue; }
    if (x.sub === 1 && depth === 0) cases.push(i);
  }
  // 每个 case 的 body = 该 case 指令之后到下一条同 op case/endblock 之前的字节
  return cases.map((idx, k) => {
    const end = k + 1 < cases.length ? cases[k + 1] : (() => {
      let d = 0;
      for (let j = idx + 1; j < ins.length; j++) {
        if (ins[j].kind === 'end') return j;
        if (ins[j].op === op && ins[j].sub === 0) d++;
        if (ins[j].op === op && ins[j].sub === 0xff) { if (d === 0) return j; d--; }
      }
      return ins.length;
    })();
    return { index: idx, pos: ins[idx].pos, val: ins[idx].args[0] ?? 0, sig: sigEntries(ins, idx + 1, end) };
  });
}

const arcs = fs.readdirSync(ARC_DIR).filter(f => /\.arc$/i.test(f)).sort();
fs.mkdirSync(OUT, { recursive: true });
const rows = [];
const globalGap = new Map();

for (const file of arcs) {
  const label = file.replace(/\.arc$/i, '');
  try {
    const buf = fs.readFileSync(path.join(ARC_DIR, file));
    const { doc } = cmdtblFromArc(buf, `enemy\\cmd_tbl\\${label}_cmdtbl`, label);
    let blocks = 0, cases = 0, multi = 0, switchable = 0, forced = 0;
    const gaps = [];
    for (const s of doc.sections) for (const e of s.entries) {
      const ins = e.ins;
      for (let i = 0; i < ins.length; i++) {
        const x = ins[i];
        if (x.op !== 0x02 || x.sub !== 0) continue;   // op02 begin
        const cs = scanBlock(ins, i, 0x02);
        if (!cs.length) continue;
        blocks++; cases += cs.length;
        if (cs.length >= 2) multi++;
        const uniq = new Set(cs.map(c => c.sig));
        if (uniq.size > 1) switchable++; else forced++;
        for (let k = 1; k < cs.length; k++) {
          const g = cs[k].pos - cs[k - 1].pos;
          gaps.push(g);
          globalGap.set(g, (globalGap.get(g) ?? 0) + 1);
        }
      }
    }
    const gs = gaps.slice().sort((a, b) => a - b);
    rows.push({ label, name: nameOf(label), blocks, cases, multi, switchable, forced,
      switchPct: blocks ? +(100 * switchable / blocks).toFixed(1) : 0,
      gapMed: gs.length ? gs[gs.length >> 1] : 0, gapMax: gs.length ? gs[gs.length - 1] : 0,
      gapLe43: gaps.length ? +(100 * gaps.filter(g => g <= 43).length / gaps.length).toFixed(1) : 0 });
  } catch (err) { console.error(`  FAIL ${label}: ${err.message}`); }
}

const cols = ['label', 'name', 'blocks', 'cases', 'multi', 'switchable', 'forced', 'switchPct', 'gapMed', 'gapMax', 'gapLe43'];
fs.writeFileSync(path.join(OUT, 'caseoff.tsv'),
  [cols.join('\t'), ...rows.map(r => cols.map(c => r[c] ?? '').join('\t'))].join('\n') + '\n');

const sum = (k) => rows.reduce((a, r) => a + r[k], 0);
const active = rows.filter(r => r.blocks > 0);
const gapTotal = [...globalGap.values()].reduce((a, b) => a + b, 0);
const gapSorted = [...globalGap.entries()].sort((a, b) => b[1] - a[1]);
const L = [];
L.push('# v35 运行时 case 扫描算法 · 离线对拍报告\n');
L.push(`数据源：\`${ARC_DIR}\` 的 ${arcs.length} 个 arc / ${active.length} 张含 op02 块的表；只读解析，零游戏改动。`);
L.push('算法与插件 v35 完全一致：`a1-1` 对齐 opcode → 按 `LEN_TABLE` 逐条 decode → 收集同 op 且 `sub=1` 的 case → **每个 case 的 body 中所有 `op14`(排队动作) 的 entry 字节序列做 FNV-1a** 作为「动作表项」签名（Rise `_CheckPrevTableInfoList` 的等价物），不是按分支编号或任意字节判重。\n');
L.push('## 汇总\n');
L.push(`- op02 块总数 **${sum('blocks')}**，case 总数 ${sum('cases')}；含 ≥2 case 的块 ${sum('multi')}。`);
L.push(`- **可替换块**（存在 body 签名不同的 case）：${sum('switchable')} / ${sum('blocks')} = **${(100 * sum('switchable') / sum('blocks')).toFixed(1)}%**。`);
L.push(`- **必然同招块**（所有 case 签名相同，v35 会安全透传）：${sum('forced')} = ${(100 * sum('forced') / sum('blocks')).toFixed(1)}%。`);
L.push(`- 相邻 case 字节距离：≤43 占比 **${(100 * [...globalGap.entries()].filter(([g]) => g <= 43).reduce((a, [, n]) => a + n, 0) / gapTotal).toFixed(1)}%**（P6 实机 ret 值域 0..43），中位 ${gapSorted.length ? gapSorted[0][0] : '-'}，最大 ${Math.max(...globalGap.keys())}。`);
L.push(`- 距离 TOP 10：${gapSorted.slice(0, 10).map(([g, n]) => `${g}B×${n}`).join(', ')}\n`);
L.push('## 三只重点怪\n');
for (const lb of ['em010_00', 'em020_00', 'em004_00']) {
  const r = rows.find(x => x.label === lb);
  if (r) L.push(`- **${lb} ${r.name}**：块 ${r.blocks} / case ${r.cases} / 可替换 ${r.switchable}（${r.switchPct}%）/ 必然同招 ${r.forced} / 相邻距离中位 ${r.gapMed}B、≤43B ${r.gapLe43}%。`);
}
L.push('\n## 对标 Rise 与硬约束\n');
L.push('- Rise `_CheckPrevTableInfoList` 按「动作表项」否决并重抽；v35 的 body 签名 = 该 case 实际排队的动作字节，故按签名判重等价于按动作表项判重，**不是按分支编号**。');
L.push('- 规则只读运行时脚本字节与 per-mon prev，不读 `action_id`、不判断怪种、不针对具体招式；对全部 op02 块一视同仁。');
L.push('- 必然同招块找不到不同签名 ⇒ 透传原 `ret`，不会把游戏改得更糟；该部分需后续路线 B（离线改表）解决。');
L.push('- **边界**：`op02` 的 case 值是否等同 Rise `_TransitionRate` 权重仍未运行时闭环，本报告只做结构对拍，不宣称实现加权池。\n');
fs.writeFileSync(path.join(OUT, 'caseoff.md'), L.join('\n'));
console.log(L.slice(0, 12).join('\n'));
console.log(`\n[written] ${OUT}/caseoff.tsv / caseoff.md  (${rows.length} rows)`);
