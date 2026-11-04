"""필요한 MIPS 명령만 인코딩하는 작은 어셈블러"""
R = {n: i for i, n in enumerate('zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra'.split())}
def _i(op, rs, rt, imm): return (op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xffff)
def _r(rs, rt, rd, sh, fn): return (R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | (sh << 6) | fn
def lw(rt, off, base): return _i(0x23, base, rt, off)
def lbu(rt, off, base): return _i(0x24, base, rt, off)
def sltiu(rt, rs, imm): return _i(0x0b, rs, rt, imm)
def ori(rt, rs, imm): return _i(0x0d, rs, rt, imm)
def addiu(rt, rs, imm): return _i(0x09, rs, rt, imm)
def addu(rd, rs, rt): return _r(rs, rt, rd, 0, 0x21)
def or_(rd, rs, rt): return _r(rs, rt, rd, 0, 0x25)
def move(rd, rs): return or_(rd, rs, 'zero')
def sll(rd, rt, sh): return _r('zero', rt, rd, sh, 0)
def nop(): return 0
def j(t): return (2 << 26) | ((t >> 2) & 0x3ffffff)
def jal(t): return (3 << 26) | ((t >> 2) & 0x3ffffff)
def bne(rs, rt, pc, target): return _i(5, rs, rt, (target - pc - 4) >> 2)
class Block:
    """라벨을 쓰는 코드 조각. 항목: 정수(명령) 또는 ('bne', rs, rt, label) / ('label', name)"""
    def __init__(s, base): s.base = base; s.items = []
    def __call__(s, *ins): s.items += ins; return s
    def assemble(s):
        lab = {}; pc = s.base
        for it in s.items:
            if isinstance(it, tuple) and it[0] == 'label': lab[it[1]] = pc
            else: pc += 4
        out = []; pc = s.base
        for it in s.items:
            if isinstance(it, tuple):
                if it[0] == 'label': continue
                if it[0] == 'bne': out.append(bne(it[1], it[2], pc, lab[it[3]]))
            else: out.append(it)
            pc += 4
        return out
