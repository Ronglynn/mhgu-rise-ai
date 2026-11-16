# -*- coding: utf-8 -*-
"""生成 v49 三状态权重层的合成冒烟日志（离线判读回归用）。

不依赖实机：按 v49 真实日志格式伪造一轮典型短场，含
  - 5 个 hook INSTALL / SITE 首字校验
  - 三态 V 行（st3=0/1/2 -> vd=2/3/1）
  - U 行 EXH 触发（ret=1 force=0）
  - T 行疲惫窗口进出（含动作数时钟退出 reason=3 an>=40）
  - R 行冻结段全同（模拟暂停菜单，验证窗口不被 forge 帧消耗）
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "out" / "sim_v49_smoke.txt"
L = []


def w(s):
    L.append(s)


w("[rai] ===== RAI v49 THREE-STATE WEIGHT LAYER (anger/normal/tired -> veto depth 3/2/1) =====")
w("[rai] Rule: v38 base UNCHANGED on normal state / anger st==1 depth3 / tired EXH-ret1|proc window depth1+keep50 / READONLY / ROLLBACK v48.nro")
w("[rai] ===== RAI v48 EXHAUST-TRIGGER CHAIN (force REMOVED in v49; read-only trigger observer) =====")
w("[rai] SITE +08E144=E92D4FF0 +082F80=E92D4FF0 +076154=E92D4FF0 +0AFF40=E92D4FF0")
w("[rai] SITE +0A30E4=E92D41F0 (EXH add, expect E92Dxxxx push else SKIP)")
w("[rai] INSTALL h_matcher +0008E144 first=E92D4FF0")
w("[rai] INSTALL h_emc +00082F80 first=E92D4FF0")
w("[rai] INSTALL h_unify +00076154 first=E92D4FF0")
w("[rai] INSTALL h_start_40 +000AFF40 / hubMask=15 hooks=4 / ROLLBACK v31.nro")
w("[rai] INSTALL h_exh +000A30E4 first=E92D41F0 (v49 read-only trigger observer)")

MON = "0C250060"
MON2 = "0C440060"

# ---- BEAT / R 行：f=300..30000 ----
for f in range(300, 30001, 300):
    w("[rai] BEAT f=%d m=%d m1=%d m0c=0 m0e=0 x=0 q=2 a=%d sel=%d act=%d "
      "beg=%d begf=0 rep=%d v=%d noalt=0 fail=0 ok=%d live=1 peak=8 hub=15 "
      "log=%d mon=%s" %
      (f, f // 3, f // 3, f // 12, f // 12, f // 12, f // 12,
       f // 24, f // 24, f // 12, f // 3, MON))

# R 行：150 帧周期；14250..20400 是「暂停菜单冻结」段（9 字段全同）
for f in range(600, 30001, 150):
    frozen = 14250 <= f <= 20400
    st = 1 if 8400 <= f <= 12150 and not frozen else 0
    proc = 0 if f < 5193 else (1 if f < 8400 else (2 if f < 11700 else 3))
    if frozen:
        proc, st, ex, thr = 3, 0, 0, 285
    else:
        ex = min(140, max(0, (f // 60) % 150))
        thr = 142 if f < 5250 else (190 if f < 8400 else (237 if f < 11700 else 285))
    w("[rai] R f=%d i=0 mon=%s act=0C2601A0 st=%d t4=0 ex=%d thr=%d proc=%d "
      "amt=10 flg=0 t5c=0 d5=0 h1=0 e1=2 dc=%d s3f=0 f5c=0 p3ca=71 p3be=73 "
      "low=%d log=%d" %
      (f, MON, st, ex, thr, proc, 1 if f >= 12000 else 0,
       1 if 14250 <= f <= 20400 else 0, f // 150))

# ---- 低活动锚点 ----
w("[rai] N f=14700 kind=ENTER-LOW dA=1 lowhits=2 a=241 log=900")
w("[rai] N f=20700 kind=EXIT-LOW dA=9 lowhits=0 a=262 log=901")

# ---- U 行：EXH add 返回 1（游戏自己判定成立），无强制 ----
for f, proc, thr in ((5193, 1, 142), (8400, 2, 190), (11700, 3, 237)):
    w("[rai] U f=%d em=%s act=0C2601A0 ret=1 cnt=%d thr=%d proc=%d flg=0 "
      "force=0 log=%d" % (f, MON, thr, thr, proc, 1000 + f))

# ---- T 行：疲惫窗口进出 ----
w("[rai] T f=5193 kind=1 reason=1 i=0 mon=%s tir=1 proc=1 an=22 an0=22 low=0 log=1100" % MON)
w("[rai] T f=8400 kind=1 reason=2 i=1 mon=%s tir=1 proc=2 an=61 an0=61 low=0 log=1101" % MON2)
w("[rai] T f=9600 kind=2 reason=3 i=0 mon=%s tir=0 proc=1 an=40 an0=22 low=0 log=1102" % MON)
w("[rai] T f=14100 kind=2 reason=3 i=1 mon=%s tir=0 proc=2 an=41 an0=61 low=1 log=1103" % MON2)

# ---- V 行：三态样本 ----
vlog = 2000
vn = 0
for st3, vd, count in ((0, 2, 30), (1, 3, 12), (2, 1, 18)):
    for k in range(count):
        vn += 1
        f = 1200 + vn * 480
        w("[rai] V f=%d n=%d mon=%s sp=0055 md=1 p5=%d blk=0812A400 nc=6 ret=17 "
          "d=0 sel=0812A4C0 sig=3A7C11E2 pick=0812A4D8 psig=91BB02F4 ki=%d "
          "rd=1 b1=0 ph=1 sw=100 sw2=72 nr=%d st3=%d vd=%d live=1 log=%d" %
          (f, vn, MON, f % 100, k % 6, 24 + k % 6, st3, vd, vlog))
        vlog += 1

# ---- S 行：三态统计（d3 == s1，skip>0）----
w("[rai] S f=3000 e1=3 e0=0 r1=20 r0=0 n1=0 n0=0 v1=18 v0=0 rd=18 b1=0 p2=6 "
  "s0=30 s1=12 s2=18 sv0=18 sv1=12 sv2=9 d3=12 skip=5 log=3000")
w("[rai] S f=30000 e1=14 e0=0 r1=88 r0=0 n1=1 n0=0 v1=60 v0=0 rd=60 b1=0 p2=25 "
  "s0=120 s1=48 s2=64 sv0=70 sv1=46 sv2=31 d3=48 skip=22 log=3001")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
print("[ok] %s  lines=%d" % (OUT, len(L)))
