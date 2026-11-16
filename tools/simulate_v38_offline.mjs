#!/usr/bin/env node
/**
 * simulate_v38_offline.mjs — 无需实机的 EMC 抽选规则蒙特卡洛对拍
 *
 * 目的：用户无需再跑一轮游戏，即可定量比较「原版 / v37 / v38」三种
 *       抽选规则在全量游戏表结构上的行为差异。
 *
 * 数据来源：游戏 romfs 内 137 个 emNNN_SS.arc 的 enemy\cmd_tbl\*_cmdtbl，
 *           复用 audit_emc_weighted.mjs 的 casesOf()（已与 v36 P8 实机对拍
 *           begin 对齐 100%、case 值 = 权重、块内权重和恒 100）。
 *
 * 三种规则（严格按插件源码语义）：
 *   vanilla : 按 case 值 w 累积 > rand%100 轮盘赌，直接执行选中 case。
 *   v37     : 1 项 prev 表；命中后 B1「向后找第一个不同且非空签名 case」，
 *             B1 失败才按完整池权重重抽（v37 的 88% 走 B1）。
 *   v38     : 2 项 prev 表；命中后排除空签名与 prev 命中项，对剩余 w
 *             归一化（sw2）后按新阈值重抽；B1 仅作兜底。
 *   共同    : 选中 case 的 sig==FNV0（body 内无 op14）⇒ 直接透传，
 *             不判重、不更新 prev（与插件 E1_N 分支一致）。
 *
 * 统计口径：过滤掉 FNV0 后的「实际有动作执行序列」上计算
 *   相邻同 sig / 连续 3 次同 sig / 连续 4 次 / ABAB(i==i-2 且 !=i-1)，
 *   另报空签名透传率、改写率、B1 率、重抽率、兜底率、池内落点 top3 占比。
 *
 * 边界（必须随结论一起声明）：
 *   1. 假设每个池被调用频率相同；实机并非如此，故这是**结构层面**对拍，
 *      不是某一场战斗的预测。
 *   2. 插件里重抽阈值 p5n=(p5+f*7+veto*13+37)%100 依赖帧号，仿真用
 *      独立可复现 RNG 生成 0..99 新阈值；两者结构等价但分布不同。
 *   3. 仿真完全不能验证「改 ret 后游戏是否真执行该 case」——
 *      动画/状态兼容性、发呆、体感、结算必须靠实机。
 *
 * 用法：node tools/simulate_v38_offline.mjs
 * 产物：out/emc_offline/sim_v38.md / sim_v38.tsv
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
const T = 120;                       // 每个池连续抽选次数
const RULES = ['vanilla', 'v37', 'v38'];
const nameOf = (label) => {
  try {
    const map = JSON.parse(fs.readFileSync(SLOT_MAP, 'utf-8'));
    const m = /^em(\d+)_(\d+)/.exec(label);
    const hit = m && map.find(x => x.emid === Number(m[1]));
    return hit ? hit.cn : '';
  } catch { return ''; }
};

// 与 audit_emc_weighted.mjs 完全一致：取最外层 case 及其权重/动作签名
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
    return { sig: h, w: (ins[idx].args[0] ?? 0) & 0xff };
  });
}

function poolsOf(buf, label) {
  const { doc } = cmdtblFromArc(buf, `enemy\\cmd_tbl\\${label}_cmdtbl`, label);
  const pools = [];
  for (const s of doc.sections) for (const e of s.entries) {
    const ins = e.ins;
    for (let i = 0; i < ins.length; i++) {
      if (ins[i].op !== 0x02 || ins[i].sub !== 0) continue;
      const arr = casesOf(ins, i, 0x02);
      if (!arr.length) continue;
      let sw = 0; for (const c of arr) sw += c.w;
      if (sw <= 0) continue;               // 实机 sw 恒 100，异常池跳过
      pools.push(arr);
    }
  }
  return pools;
}

function makeRng(seed) {
  let x = (seed | 0) || 1;
  return () => { x ^= x << 13; x ^= x >>> 17; x ^= x << 5; return x >>> 0; };
}

function weightedPick(cs, p5) {
  let cum = 0;
  for (let k = 0; k < cs.length; k++) { cum += cs[k].w; if (cum > p5) return k; }
  return cs.length - 1;
}

function simulate(cs, rule, rands) {
  const K = rule === 'v38' ? 2 : rule === 'v37' ? 1 : 0;
  let prev = [];
  const seq = [];                        // 实际执行序列（含 FNV0，后处理过滤）
  let veto = 0, redraw = 0, b1 = 0, fallback = 0, empty = 0;
  const picks = new Map();               // 改写落点签名 -> 次数
  for (let t = 0; t < rands.length; t++) {
    const { p5, p5n } = rands[t];
    const k = weightedPick(cs, p5);
    const sig = cs[k].sig;
    if (sig === FNV0) { empty++; seq.push(sig); continue; }   // 插件 E1_N 透传
    let execSig = sig;
    const hit = K > 0 && prev.slice(0, K).includes(sig);
    if (hit) {
      veto++;
      let pk = -1;
      if (rule === 'v37') {
        for (let j = k + 1; j < cs.length; j++)
          if (cs[j].sig !== sig && cs[j].sig !== FNV0) { pk = j; break; }
        if (pk >= 0) b1++;
        else {
          let sw = 0; for (const c of cs) sw += c.w;
          const thr = Math.floor(p5n * sw / 100);
          let cum = 0, k0 = cs.length - 1;
          for (let j = 0; j < cs.length; j++) { cum += cs[j].w; if (cum > thr) { k0 = j; break; } }
          for (let d = 0; d < cs.length; d++) {
            const j = (k0 + d) % cs.length;
            if (cs[j].sig !== sig && cs[j].sig !== FNV0) { pk = j; break; }
          }
          redraw++;
        }
      } else if (rule === 'v38') {
        const elig = j => cs[j].sig !== FNV0 && !prev.slice(0, K).includes(cs[j].sig);
        let sw2 = 0;
        for (let j = 0; j < cs.length; j++) if (elig(j)) sw2 += cs[j].w;
        if (sw2 > 0) {
          const thr = Math.floor(p5n * sw2 / 100);
          let cum = 0;
          for (let j = 0; j < cs.length; j++) {
            if (!elig(j)) continue;
            cum += cs[j].w;
            if (cum > thr) { pk = j; break; }
          }
          if (pk >= 0) redraw++;
        }
        if (pk < 0) {
          for (let j = 0; j < cs.length; j++)
            if (cs[j].sig !== sig && cs[j].sig !== FNV0) { pk = j; break; }
          if (pk >= 0) fallback++;
        }
      }
      if (pk >= 0) {
        execSig = cs[pk].sig;
        picks.set(execSig, (picks.get(execSig) || 0) + 1);
      }
    }
    if (K > 0) prev = [execSig, ...prev].slice(0, K);
    seq.push(execSig);
  }

  const act = seq.filter(s => s !== FNV0);
  let adj = 0, r3 = 0, r4 = 0, abab = 0;
  for (let i = 1; i < act.length; i++) {
    if (act[i] === act[i - 1]) { adj++; if (i >= 2 && act[i] === act[i - 2]) r3++;
      if (i >= 3 && act[i] === act[i - 3]) r4++; }
    if (i >= 2 && act[i] === act[i - 2] && act[i] !== act[i - 1]) abab++;
  }
  const top3 = [...picks.values()].sort((a, b) => b - a).slice(0, 3).reduce((a, b) => a + b, 0);
  return {
    n: rands.length, act: act.length, adj, r3, r4, abab,
    uniq: new Set(act).size, empty, veto, redraw, b1, fallback,
    top3: veto ? top3 / veto : 0, top3n: top3, hasTop3: veto > 0,
    single: new Set(cs.filter(c => c.sig !== FNV0).map(c => c.sig)).size <= 1,
  };
}

// ---- 主流程 ----
const arcs = fs.readdirSync(ARC).filter(f => /\.arc$/i.test(f)).sort();
const acc = {}; for (const r of RULES) acc[r] = [];
const perArc = [];
let nPools = 0, nSingle = 0, nCases = 0;
console.log(`[sim] ${arcs.length} arc, T=${T} 次/池, 规则=${RULES.join('/')}`);

for (const f of arcs) {
  const label = f.replace(/\.arc$/i, '');
  let pools;
  try { pools = poolsOf(fs.readFileSync(path.join(ARC, f)), label); }
  catch (e) { console.error(`  SKIP ${label}: ${e.message}`); continue; }
  if (!pools.length) continue;
  const byRule = {}; for (const r of RULES) byRule[r] = { pools: 0, n: 0, act: 0, adj: 0, r3: 0, r4: 0, abab: 0, uniq: 0, empty: 0, veto: 0, redraw: 0, b1: 0, fallback: 0, top3n: 0, top3w: 0, hasTop3: 0 };
  for (let pi = 0; pi < pools.length; pi++) {
    const cs = pools[pi];
    nPools++; nCases += cs.length;
    if (new Set(cs.filter(c => c.sig !== FNV0).map(c => c.sig)).size <= 1) nSingle++;
    // 同一 (池, t) 随机序列供三规则共用 ⇒ paired comparison，降低方差
    const rng = makeRng(0x9e3779b9 ^ (nPools * 2654435761));
    const rands = Array.from({ length: T }, () => ({ p5: rng() % 100, p5n: rng() % 100 }));
    for (const rule of RULES) {
      const z = simulate(cs, rule, rands);
      const a = byRule[rule];
      a.pools++; a.n += z.n; a.act += z.act; a.adj += z.adj; a.r3 += z.r3; a.r4 += z.r4;
      a.abab += z.abab; a.uniq += z.uniq; a.empty += z.empty; a.veto += z.veto;
      a.redraw += z.redraw; a.b1 += z.b1; a.fallback += z.fallback;
      a.top3n += z.top3n; if (z.hasTop3) { a.top3w += z.top3; a.hasTop3++; }
      acc[rule].push(z);
    }
  }
  perArc.push({ label, name: nameOf(label), byRule });
}
console.log(`[sim] ${nPools} 池 / ${nCases} case / 单动作池 ${nSingle}`);

const pct = (a, b) => b ? (100 * a / b).toFixed(2) + '%' : '-';
const fmt = (r) => ({
  adj: pct(r.adj, r.act), r3: pct(r.r3, r.act), r4: pct(r.r4, r.act),
  abab: pct(r.abab, r.act), empty: pct(r.empty, r.n), veto: pct(r.veto, r.n),
  b1: pct(r.b1, r.veto || 1), redraw: pct(r.redraw, r.veto || 1), fallback: pct(r.fallback, r.veto || 1),
  uniq: (r.uniq / r.pools).toFixed(2), top3: pct(r.top3n, r.veto || 1),
});

const rows = RULES.map(rule => {
  const r = {};
  for (const a of perArc) for (const [k, v] of Object.entries(a.byRule[rule])) r[k] = (r[k] || 0) + v;
  return { rule, r, f: fmt(r) };
});

// 排除「必然同招池」后的可干预子集：这些池才是规则真正能起作用的地方
const multiRows = RULES.map(rule => {
  const zs = acc[rule].filter(z => !z.single);
  const r = { pools: zs.length, n: 0, act: 0, adj: 0, r3: 0, r4: 0, abab: 0,
    uniq: 0, empty: 0, veto: 0, redraw: 0, b1: 0, fallback: 0, top3n: 0, top3w: 0, hasTop3: 0 };
  for (const z of zs) for (const k of Object.keys(r))
    if (k !== 'pools' && typeof z[k] === 'number') r[k] += z[k];
  return { rule, r, f: fmt(r) };
});

const L = [];
L.push('# EMC 抽选规则离线蒙特卡洛对拍（无需实机）\n');
L.push(`- 数据：**${arcs.length} arc / ${nPools} 个加权池 / ${nCases} 个 case**，每池连续抽选 **${T}** 次，共 ${(nPools * T * RULES.length / 1e6).toFixed(2)}M 次规则执行。`);
L.push(`- 只有一个非空动作签名的「必然同招池」：**${nSingle} / ${nPools} = ${pct(nSingle, nPools)}** —— 任何抽选规则都无法改变这部分。`);
L.push('- 配对设计：同一池、同一步的三个规则使用**完全相同**的随机序列。\n');
L.push('| 规则 | 相邻同招 | 连续 3 次 | 连续 4 次 | ABAB 二循环 | 改写率 | B1 率 | 归一化重抽率 | 兜底率 | 池内落点 top3 | 空签名透传 | 每池唯一动作 |');
L.push('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|');
for (const { rule, f } of rows)
  L.push(`| ${rule} | ${f.adj} | ${f.r3} | ${f.r4} | ${f.abab} | ${f.veto} | ${f.b1} | ${f.redraw} | ${f.fallback} | ${f.top3} | ${f.empty} | ${f.uniq} |`);
L.push('\n## 剔除「必然同招池」后（可干预子集，规则真正的战场）\n');
L.push('| 规则 | 相邻同招 | 连续 3 次 | 连续 4 次 | ABAB 二循环 | 改写率 | B1 率 | 归一化重抽率 | 兜底率 | 池内落点 top3 |');
L.push('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|');
for (const { rule, f } of multiRows)
  L.push(`| ${rule} | ${f.adj} | ${f.r3} | ${f.r4} | ${f.abab} | ${f.veto} | ${f.b1} | ${f.redraw} | ${f.fallback} | ${f.top3} |`);
L.push('\n## 读法\n');
L.push('1. **连续 3 次**是用户反馈的核心症状（「连续 3 次喷吐」）；**ABAB** 是 v37 被 P9 日志证实的机械二循环。');
L.push('2. 「空签名透传」是插件对 `sig==FNV0` 分支的原样放行（原生 Think 间隙 / 待机），三规则应一致；若不一致说明仿真实现有偏差。');
L.push('3. 「池内落点 top3」越低，替代动作越分散；v37 P9 实机为 99/124 = 79.8%。');
L.push('\n## 边界（不可替代实机的部分）\n');
L.push('1. 假设每个池调用频率相同；实机并非如此 ⇒ 这是**表结构层面**对拍，不是某场战斗的预测。');
L.push('2. 插件重抽阈值含帧号盐，仿真用独立可复现 RNG 生成 0..99 新阈值，结构等价、分布不同。');
L.push('3. **无法验证改 `ret` 后游戏是否真执行该 case**：动画/状态兼容性、发呆、体感、正常结算仍需实机。');
L.push('4. 本仿真不产生也不修改任何游戏文件，纯只读。\n');
fs.writeFileSync(path.join(OUT, 'sim_v38.md'), L.join('\n') + '\n');

const tsv = ['label\tname\trule\tpools\tdraws\tact\tr2\tr3\tr4\tabab\tempty\tveto\tb1\tredraw\tfallback\ttop3\tuniq'];
for (const a of perArc) for (const rule of RULES) {
  const r = a.byRule[rule];
  tsv.push([a.label, a.name, rule, r.pools, r.n, r.act, r.adj, r.r3, r.r4, r.abab,
    r.empty, r.veto, r.b1, r.redraw, r.fallback, r.top3n, r.uniq].join('\t'));
}
fs.writeFileSync(path.join(OUT, 'sim_v38.tsv'), tsv.join('\n') + '\n');
console.log(L.join('\n'));
