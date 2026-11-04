"""글꼴 겹치기 패치: 4bpp 텍스처 한 칸에 2비트 글리프 두 벌(하위 2비트=레이어 1, 상위 2비트=레이어 2)을 겹쳐 담는다.

- 글리프 레코드 11번 바이트 = 레이어(0: 원래 4비트 글리프, 1, 2)
- 레이아웃(0x5c4780): 현재 패스의 레이어가 아닌 글리프는 사각형을 만들지 않고 펜만 전진
- 문자열 그리기(0x5c5590): 패스 0 을 그린 뒤 쓰인 레이어마다 TEX0 의 CLUT 를 레이어용으로 바꿔 다시 그린다
- CLUT 생성(0x5c5a30): Main/Outline/Inline CLUT 의 레이어용 6벌을 더 만든다
코드는 쓰이지 않는 압축 인코더(HUFF/LZM1 f0·f1, 코덱 표에서 디스패치되지 않음) 자리에 넣는다.
"""
import struct
R = {n: i for i, n in enumerate('zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra'.split())}
def I(op, rs, rt, imm): return (op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xffff)
def Rr(rs, rt, rd, sh, fn): return (R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | (sh << 6) | fn
addiu = lambda rt, rs, i: I(9, rs, rt, i)
andi = lambda rt, rs, i: I(0xc, rs, rt, i)
ori = lambda rt, rs, i: I(0xd, rs, rt, i)
slti = lambda rt, rs, i: I(0xa, rs, rt, i)
lui = lambda rt, i: I(0xf, 'zero', rt, i)
lb = lambda rt, o, b: I(0x20, b, rt, o)
lbu = lambda rt, o, b: I(0x24, b, rt, o)
lw = lambda rt, o, b: I(0x23, b, rt, o)
sb = lambda rt, o, b: I(0x28, b, rt, o)
sw = lambda rt, o, b: I(0x2b, b, rt, o)
ld = lambda rt, o, b: I(0x37, b, rt, o)
sd = lambda rt, o, b: I(0x3f, b, rt, o)
sq = lambda rt, o, b: I(0x1f, b, rt, o)
addu = lambda rd, rs, rt: Rr(rs, rt, rd, 0, 0x21)
or_ = lambda rd, rs, rt: Rr(rs, rt, rd, 0, 0x25)
move = lambda rd, rs: Rr(rs, 'zero', rd, 0, 0x2d)      # daddu (64비트 복사)
sll = lambda rd, rt, s: Rr('zero', rt, rd, s, 0)
sllv = lambda rd, rt, rs: Rr(rs, rt, rd, 0, 4)
srlv = lambda rd, rt, rs: Rr(rs, rt, rd, 0, 6)
jr = lambda rs: Rr(rs, 'zero', 'zero', 0, 8)
NOP = 0
def j(t): return (2 << 26) | ((t >> 2) & 0x3ffffff)
def jal(t): return (3 << 26) | ((t >> 2) & 0x3ffffff)
def hi(a): return ((a + 0x8000) >> 16) & 0xffff
def lo(a): return a & 0xffff

class Asm:
    def __init__(s, base): s.base = base; s.it = []
    def __call__(s, *xs): s.it += xs; return s
    def L(s, name): s.it.append(('L', name)); return s
    def addr(s, name):
        pc = s.base
        for x in s.it:
            if isinstance(x, tuple) and x[0] == 'L':
                if x[1] == name: return pc
            elif isinstance(x, tuple) and x[0] == 'D': pc += len(x[1])
            else: pc += 4
        raise KeyError(name)
    def bytes(s):
        out = bytearray(); pc = s.base
        for x in s.it:
            if isinstance(x, tuple):
                if x[0] == 'L': continue
                if x[0] == 'D': out += x[1]; pc += len(x[1]); continue
                op, a, b, lab = x            # ('beq'|'bne', rs, rt, label)
                off = (s.addr(lab) - pc - 4) >> 2
                out += struct.pack('<I', I(4 if op == 'beq' else 5, a, b, off))
            else:
                out += struct.pack('<I', x)
            pc += 4
        return bytes(out)
    def size(s): return len(s.bytes())

TEX = (0x28, 0x30, 0x38)      # 글꼴 그리기 객체의 TEX0: Main, Outline, Inline CLUT
CLUT_MAKE, CLUT_REG, CLUT_LOCK, MEM_FREE, TEX0_OF = 0x5fd7f8, 0x5fc4d8, 0x5fc518, 0x5ced20, 0x5c4d18
# 2비트 값(0..3 -> 4비트 0,5,10,15)에 원래 CLUT 공식을 적용한 알파
ATAB = bytes([0, 42, 85, 128,  0, 91, 128, 128,  0, 0, 36, 128])

def build(cave1, cave2):
    """cave1: 데이터+레이아웃/초기화 훅, cave2: 그리기 훅. -> [(주소, 바이트)], {훅주소: [명령]}"""
    a = Asm(cave1)
    D = cave1
    # 데이터: +0 PASS, +1 MASK, +4 H[6], +0x1c NTAB[6](시프트, ATAB 오프셋), +0x28 ATAB[12]
    ntab = bytes(sum(([sh, k * 4] for sh in (0, 2) for k in range(3)), []))
    a(('D', bytes(4) + bytes(24) + ntab + ATAB))
    PASS, MASK, H, NTAB, AT = 0, 1, 4, 0x1c, 0x28
    # --- 레이아웃 훅 (0x5c4780 자리, 지연 슬롯에서 s3 += 0x14 가 이미 실행됨)
    a.L('layout')
    a(lbu('v1', 0xb, 's0'), lui('a0', hi(D)), addiu('a0', 'a0', lo(D)),
      lbu('v0', MASK, 'a0'), addiu('a2', 'zero', 1), sllv('a2', 'a2', 'v1'), or_('v0', 'v0', 'a2'), sb('v0', MASK, 'a0'),
      lbu('v0', PASS, 'a0'), ('bne', 'v0', 'v1', 'lskip'), NOP,
      lb('v1', 9, 's0'), j(0x5c4788), NOP)
    a.L('lskip')
    a(addiu('s3', 's3', -0x14), j(0x5c47c0), NOP)
    # --- 초기화 훅 (0x5c5a30 의 jal 0x5ced20 대신. a0 = s0 = 64바이트 CLUT 버퍼, s2 = 0x770000, 호출자 sp 에 기술자)
    a.L('init')
    a(addiu('sp', 'sp', -0x40), sd('ra', 0, 'sp'), sd('s1', 8, 'sp'), sd('s3', 0x10, 'sp'),
      lui('s1', hi(D)), addiu('s1', 's1', lo(D)), move('s3', 'zero'))
    a.L('in')
    a(sll('t0', 's3', 1), addu('t0', 't0', 's1'), lbu('t1', NTAB, 't0'), lbu('t2', NTAB + 1, 't0'),
      addu('t2', 't2', 's1'), move('t3', 'zero'))
    a.L('ii')
    a(srlv('t4', 't3', 't1'), andi('t4', 't4', 3), addu('t4', 't4', 't2'), lbu('t4', AT, 't4'),
      sll('t5', 't3', 2), addu('t5', 't5', 's0'), sb('t4', 3, 't5'),
      addiu('t3', 't3', 1), slti('t6', 't3', 16), ('bne', 't6', 'zero', 'ii'), NOP)
    a(move('a0', 'zero'), addiu('a1', 'sp', 0x40), addiu('a2', 's2', -0x68c0),
      lui('a3', hi(0x751ff8)), addiu('a3', 'a3', lo(0x751ff8)),
      jal(CLUT_MAKE), NOP,                                   # 반환값이 CLUT 핸들(원래 코드도 이것을 저장)
      sll('t0', 's3', 2), addu('t0', 't0', 's1'), sw('v0', H, 't0'),
      jal(CLUT_REG), move('a0', 'v0'),
      sll('t0', 's3', 2), addu('t0', 't0', 's1'), lw('a0', H, 't0'),
      jal(CLUT_LOCK), NOP,
      addiu('s3', 's3', 1), slti('v0', 's3', 6), ('bne', 'v0', 'zero', 'in'), NOP)
    a(ld('ra', 0, 'sp'), ld('s1', 8, 'sp'), ld('s3', 0x10, 'sp'), addiu('sp', 'sp', 0x40),
      j(MEM_FREE), move('a0', 's0'))
    # --- 그리기 훅 (0x5c5590 진입)
    w = Asm(cave2)
    w.L('inner')
    w(addiu('sp', 'sp', -0x60), sq('s0', 0x50, 'sp'), j(0x5c5598), NOP)
    w.L('draw')
    w(addiu('sp', 'sp', -0x60), sd('ra', 0, 'sp'), sd('s0', 8, 'sp'), sd('s1', 0x10, 'sp'),
      sd('a0', 0x18, 'sp'), sd('a1', 0x20, 'sp'), sd('a2', 0x28, 'sp'), sd('a3', 0x30, 'sp'),
      move('s0', 'a0'), lui('s1', hi(D)), addiu('s1', 's1', lo(D)),
      sb('zero', PASS, 's1'), sb('zero', MASK, 's1'))
    for k, o in enumerate(TEX): w(ld('v0', o, 's0'), sd('v0', 0x38 + 8 * k, 'sp'))
    w(jal(w.base), NOP, sw('v0', 0x50, 'sp'))          # inner = cave2 시작
    for L in (1, 2):
        w(lbu('v0', MASK, 's1'), andi('v0', 'v0', 1 << L), ('beq', 'v0', 'zero', 'skip%d' % L), NOP,
          addiu('v0', 'zero', L), sb('v0', PASS, 's1'))
        for k, o in enumerate(TEX):
            w(lw('a0', 0x18, 's0'), lw('a1', H + 4 * (3 * (L - 1) + k), 's1'), jal(TEX0_OF), NOP, sd('v0', o, 's0'))
        w(ld('a0', 0x18, 'sp'), ld('a1', 0x20, 'sp'), ld('a2', 0x28, 'sp'), ld('a3', 0x30, 'sp'), jal(w.base), NOP)
        w.L('skip%d' % L)
    for k, o in enumerate(TEX): w(ld('v0', 0x38 + 8 * k, 'sp'), sd('v0', o, 's0'))
    w(sb('zero', PASS, 's1'), lw('v0', 0x50, 'sp'), ld('ra', 0, 'sp'), ld('s0', 8, 'sp'), ld('s1', 0x10, 'sp'),
      jr('ra'), addiu('sp', 'sp', 0x60))
    hooks = {0x5c4780: [j(a.addr('layout'))],                 # 다음 명령(addiu s3,s3,0x14)이 지연 슬롯
             0x5c5590: [j(w.addr('draw')), NOP],
             0x5c5a30: [jal(a.addr('init'))]}
    expect = {0x5c4780: [0x82030009], 0x5c5590: [0x27bdffa0, 0x7fb00050], 0x5c5a30: [0x0c173b48]}
    return [(cave1, a.bytes()), (cave2, w.bytes())], hooks, expect
