# -*- coding: utf-8 -*-
"""生成 v54 疲惫链路快照 + 一次性强制疲惫合成冒烟日志（离线回归用）。

按 v50 真实日志格式伪造一轮短场，含：5 hook INSTALL / U(bad=0) /
T(ENTER+EXIT, proc<=30) / V(wm,wk,st3,vd) / S(w3,w4,wt,d3=0,skip=0) /
R 冻结段全同 / BEAT hub=15 live=1。
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "out" / "sim_v54_smoke.txt"
L = []


def w(s):
    L.append(s)


P = "[forge] [INFO] "
w(P + "[rai] ===== RAI v54 TIRED-CHAIN SNAPSHOT + ONE-SHOT BOUNDED FORCE =======")
w(P + "[rai] Rule: P46 chain I fields t505-t508-p41 / wr16(act+0x508,0)+wr8(act+0x505,2) ONCE / LOW==0 gate / G line before-after / ROLLBACK v53.nro")
w(P + "[rai] ===== RAI v53 LONG-QUEST QUOTA RESET (READONLY, no new hook) =====")
w(P + "[rai] ===== RAI v52 PER-ACTION STAMINA OBSERVER (READONLY, no new hook) =====")
w(P + "[rai] Rule: UNCHANGED v51/v50 / Y line am=act+0x4D8 per action / S line amx-anf-anr per-frame / R line q40..q60 candidates / ROLLBACK v51.nro")
w(P + "[rai] ===== RAI v51 UPSTREAM EXHAUST-AMOUNT OBSERVER (READONLY, no new hook) =====")
w(P + "[rai] Rule: UNCHANGED v50 W1 / H line sampled EXH add(a1) / R line ac-asum-amax-anz / S line gac-gsum-gmax-gnz / ROLLBACK v50.nro")
w(P + "[rai] ===== RAI v50 W1 RISE-POOL WEIGHT LAYER (top-k + sorted shape, READONLY) =====")
w(P + "[rai] Rule: W1 shapes N3[45,32,23] N4[40,27,20,13] T3[60,30,10] mix61 / veto depth 2|1 / W0 proc<=30 + 0<thr<0x4000 gate / ROLLBACK v49.nro")
w(P + "[rai] ===== RAI v49 THREE-STATE WEIGHT LAYER (v50: anger depth3 & tired keep50 REMOVED) =====")
w(P + "[rai] SITE +08E144=E92D4FF0 +082F80=E92D4FF0 +076154=E92D4FF0 +0AFF40=E3A02000")
w(P + "[rai] SITE +0A30E4=E92D41F0 (EXH add, expect E92Dxxxx push else SKIP)")
w(P + "[rai] INSTALL h_matcher +0008E144 first=E92D4FF0")
w(P + "[rai] INSTALL h_emc +00082F80 first=E92D4FF0")
w(P + "[rai] INSTALL h_unify +00076154 first=E92D4FF0")
w(P + "[rai] INSTALL h_exh +000A30E4 first=E92D41F0 (v49 read-only trigger observer)")
w(P + "[rai] INSTALL h_start_40 +000AFF40 / hubMask=15 hooks=4 / ROLLBACK v31.nro")

MON = "0C250060"
MON2 = "0C440060"

for f in range(300, 30001, 300):
    w(P + "[rai] BEAT f=%d m=%d m1=%d m0c=0 m0e=0 x=0 q=2 a=%d sel=%d act=%d "
      "beg=%d begf=0 rep=%d v=%d noalt=0 fail=0 ok=%d live=1 peak=8 hub=15 "
      "log=%d mon=%s" %
      (f, f // 3, f // 3, f // 12, f // 12, f // 12, f // 12,
       f // 24, f // 24, f // 12, f // 3, MON))

for f in range(600, 30001, 150):
    frozen = 14250 <= f <= 20400
    st = 1 if 8400 <= f <= 12150 and not frozen else 0
    proc = 0 if f < 5193 else (1 if f < 8400 else (2 if f < 11700 else 3))
    if frozen:
        proc, st, ex, thr = 3, 0, 0, 285
    else:
        ex = min(140, max(0, (f // 60) % 150))
        thr = 142 if f < 5250 else (190 if f < 8400 else (237 if f < 11700 else 285))
    w(P + "[rai] R f=%d i=0 mon=%s act=0C2601A0 st=%d t4=0 ex=%d thr=%d proc=%d "
      "amt=10 flg=0 t5c=0 d5=0 h1=0 e1=2 dc=%d s3f=0 f5c=0 p3ca=71 p3be=73 "
      "q40=%d q44=%d q48=%d q4c=%d q50=%d q54=%d q58=%d q60=%d "
      "t505=%d t506=1000 t508=%d t50c=0 p41=%d pt5c=%d t1a8=1 t362=0 t5df3=0 "
      "ac=%d asum=%d amax=10 anz=%d low=%d log=%d" %
      (f, MON, st, ex, thr, proc, 1 if f >= 12000 else 0,
       100 - min(99, f // 300), 0, 0, 0, 0, 0, 0, 0,
       0 if f < 15000 else 2, 1000 if f < 15000 else 0,
       0 if f < 15000 else 5, 0 if f < 15000 else 30,
       f // 150, f // 150 * 10, f // 150, 1 if frozen else 0, f // 150))

w(P + "[rai] N f=14700 kind=ENTER-LOW dA=1 lowhits=2 a=241 log=900")
w(P + "[rai] N f=20700 kind=EXIT-LOW dA=9 lowhits=0 a=262 log=901")

# U：W0 门控通过（bad=0），proc 1/2/3、thr 合法
for f, proc, thr in ((5193, 1, 142), (8400, 2, 190), (11700, 3, 237)):
    w(P + "[rai] U f=%d em=%s act=0C2601A0 ret=1 cnt=%d thr=%d proc=%d "
      "flg=0 bad=0 force=0 log=%d" % (f, MON, thr, thr, proc, 1000 + f))

# T：proc 全部 <=30，EXIT 走动作数窗口
w(P + "[rai] T f=5193 kind=1 reason=1 i=0 mon=%s tir=1 proc=1 an=22 an0=22 low=0 log=1100" % MON)
w(P + "[rai] T f=8400 kind=1 reason=1 i=1 mon=%s tir=1 proc=2 an=61 an0=61 low=0 log=1101" % MON2)
w(P + "[rai] T f=9600 kind=2 reason=3 i=0 mon=%s tir=0 proc=1 an=40 an0=22 low=0 log=1102" % MON)
w(P + "[rai] T f=14100 kind=2 reason=3 i=1 mon=%s tir=0 proc=2 an=41 an0=61 low=1 log=1103" % MON2)

# V：三态齐全；wm/wk 与 st3/vd 映射严格一致
vlog = 2000
vn = 0
for st3, vd, wm, wk, count in ((0, 2, 1, 3, 16), (0, 2, 2, 4, 12),
                               (1, 2, 1, 3, 8), (1, 2, 2, 4, 6),
                               (2, 1, 3, 3, 18)):
    for k in range(count):
        vn += 1
        f = 1200 + vn * 460
        w(P + "[rai] V f=%d n=%d mon=%s sp=0055 md=1 p5=%d blk=0812A400 nc=6 ret=17 "
          "d=0 sel=0812A4C0 sig=3A7C11E2 pick=0812A4D8 psig=91BB02F4 ki=%d "
          "rd=1 b1=0 ph=1 sw=100 sw2=72 nr=%d st3=%d vd=%d wm=%d wk=%d live=1 log=%d" %
          (f, vn, MON, f % 100, k % 6, 24 + k % 6, st3, vd, wm, wk, vlog))
        vlog += 1

w(P + "[rai] S f=3000 e1=3 e0=0 r1=20 r0=0 n1=0 n0=0 v1=18 v0=0 rd=18 b1=0 p2=6 "
  "s0=30 s1=12 s2=18 sv0=18 sv1=12 sv2=9 w3=16 w4=10 wt=8 d3=0 skip=0 "
  "gac=20 gsum=200 gmax=10 gnz=20 amx=15 anf=42 anr=20 gdone=0 gf=0 log=3000")
w(P + "[rai] S f=30000 e1=14 e0=0 r1=88 r0=0 n1=1 n0=0 v1=60 v0=0 rd=60 b1=0 p2=25 "
  "s0=120 s1=48 s2=64 sv0=70 sv1=46 sv2=31 w3=48 w4=30 wt=36 d3=0 skip=0 "
  "gac=200 gsum=2000 gmax=10 gnz=200 amx=15 anf=430 anr=198 gdone=1 gf=15000 log=3001")

# G：v54 一次性强制疲惫事件（前后快照）
w(P + "[rai] G f=15000 mon=%s act=0C2601A0 b505=0 b508=1000 b506=1000 bp41=0 "
  "a505=2 a508=0 ap41=0 thr=285 an=48 force=1 log=6000" % MON)

# Y：v52 每动作减气 amount 快照（am 非零，模拟 0x9DBE4 已累加）
for k, f in enumerate(range(1200, 30001, 1200), start=1):
    am = (10 if k % 3 else 15)
    w(P + "[rai] Y f=%d mon=%s a=%d s=%d am=%d d2=0 ex=%d thr=%d proc=%d "
      "d5=0 st=0 amx=15 log=%d" %
      (f, MON, 6 + k % 5, 10 + k % 4, am, min(140, k * 5),
       142 if k < 8 else 190, 0 if k < 8 else 1, 5000 + k))

# H：v51 上游 add 调用等距样本（amount 非零，通道在跑）
for k, f in enumerate(range(1500, 15001, 1500), start=1):
    w(P + "[rai] H f=%d em=%s a1=10 ret=0 cnt=%d thr=142 proc=0 d5=0 "
      "ac=%d low=0 log=%d" % (f, MON, min(140, k * 10), k * 10, 4000 + k))

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
print("[ok] %s  lines=%d" % (OUT, len(L)))
