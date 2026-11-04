"""LZH1(type 5) 해제: 게임 ELF 의 디코더를 unicorn 으로 실행"""
import struct, os
from unicorn import *
from unicorn.mips_const import *
ELF = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'x', 'SLUS_210.25')
GP = 0x764970
HEAP = 0x1000000
STUB = 0x1fff000
class LZH:
    def __init__(s, elf=None):
        D = elf or open(ELF, 'rb').read()
        img = bytearray(D[0x1000:0x1000 + 0x66a780])
        for o in range(0, len(img), 4):   # R5900 sq/lq -> sd/ld
            w = struct.unpack_from('<I', img, o)[0]; op = w >> 26
            if op == 0x1f: struct.pack_into('<I', img, o, (w & 0x3ffffff) | (0x3f << 26))
            elif op == 0x1e: struct.pack_into('<I', img, o, (w & 0x3ffffff) | (0x37 << 26))
        u = s.u = Uc(UC_ARCH_MIPS, UC_MODE_MIPS64 | UC_MODE_LITTLE_ENDIAN)
        u.mem_map(0, 0x2000000)
        u.mem_write(0x100000, bytes(img))
        s.heap = HEAP
        s.stubs = {0x5ced00: s.malloc, 0x5ced20: s.nop, 0x5e7cb8: s.nop, 0x5e7d48: s.nop, 0x5e75f8: s.nop, 0x695dc8: s.adler}
        for a in s.stubs: u.hook_add(UC_HOOK_CODE, s.hook, begin=a, end=a)
        s.vt = struct.unpack_from('<10I', D, 0x701a08 - 0x100000 + 0x1000)
    def hook(s, u, addr, size, ud):
        f = s.stubs.get(addr)
        if f:
            u.reg_write(UC_MIPS_REG_V0, f())
            u.reg_write(UC_MIPS_REG_PC, u.reg_read(UC_MIPS_REG_RA))
    def nop(s): return 0
    def adler(s):
        u = s.u; a0 = u.reg_read(UC_MIPS_REG_A0) & 0xffffffff
        a1 = u.reg_read(UC_MIPS_REG_A1) & 0xffffffff; n = u.reg_read(UC_MIPS_REG_A2) & 0xffffffff
        v = struct.unpack('<I', u.mem_read(a0, 4))[0]; a, b = v & 0xffff, v >> 16
        for c in bytes(u.mem_read(a1, n)) if n else b'':
            a = (a + c) % 65521; b = (b + a) % 65521
        u.mem_write(a0, struct.pack('<I', (b << 16) | a)); return (b << 16) | a
    def malloc(s):
        n = s.u.reg_read(UC_MIPS_REG_A1) & 0xffffffff
        p = s.heap; s.heap = (s.heap + n + 63) & ~63
        s.u.mem_write(p, bytes(n)); return p
    def call(s, fn, *args):
        u = s.u
        for r, a in zip([UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_A2, UC_MIPS_REG_A3], args): u.reg_write(r, a)
        u.reg_write(UC_MIPS_REG_GP, GP); u.reg_write(UC_MIPS_REG_SP, 0xff0000); u.reg_write(UC_MIPS_REG_RA, STUB)
        u.emu_start(fn, STUB)
        return u.reg_read(UC_MIPS_REG_V0) & 0xffffffff
    def decode(s, src, usize):
        u = s.u; s.heap = HEAP
        SRC = 0x1400000; DST = 0x1800000; IN = 0x13ff000; OUT = 0x13ff100
        u.mem_write(SRC, src); u.mem_write(DST, bytes(usize + 64))
        u.mem_write(IN, struct.pack('<III', SRC, len(src), 0) + bytes(0x20)); u.mem_write(IN + 0x18, b'\1')
        u.mem_write(OUT, struct.pack('<III', DST, usize, 0) + bytes(0x20)); u.mem_write(OUT + 0x18, b'\1')
        r = s.call(s.vt[5], IN, OUT)
        r = s.call(s.vt[6], IN, OUT, r)
        n = struct.unpack('<I', u.mem_read(OUT + 8, 4))[0]
        return bytes(u.mem_read(DST, usize)), n, r
if __name__ == '__main__':
    import terf, sys
    d = open(sys.argv[1], 'rb').read(); L = LZH()
    for o, sz, c, us in terf.entries(d):
        if c == 5:
            out, n, r = L.decode(d[o:o+sz], us); print(sz, us, n, hex(r), out[:64])

def _encode(s, data):
    u = s.u; s.heap = HEAP
    SRC = 0x1400000; DST = 0x1800000; IN = 0x13ff000; OUT = 0x13ff100
    cap = len(data) * 2 + 0x10000
    u.mem_write(SRC, data); u.mem_write(DST, bytes(cap))
    u.mem_write(IN, struct.pack('<III', SRC, len(data), 0) + bytes(0x20)); u.mem_write(IN + 0x18, b'\1')
    u.mem_write(OUT, struct.pack('<III', DST, cap, 0) + bytes(0x20)); u.mem_write(OUT + 0x18, b'\1')
    r = s.call(s.vt[2], IN, OUT)
    r2 = s.call(s.vt[3], IN, OUT, r)
    s.call(s.vt[4], IN, OUT, r)
    n = struct.unpack('<I', u.mem_read(OUT + 8, 4))[0]
    return bytes(u.mem_read(DST, n)), r, r2
LZH.encode = _encode
