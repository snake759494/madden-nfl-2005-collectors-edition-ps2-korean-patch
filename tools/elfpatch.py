"""ELF 패치: 글자 출력/폭 측정/줄바꿈 루프가 2바이트 한글(선행 0xE0~0xFE)을 한 글자로 읽게 한다.

새 코드는 쓰이지 않는 HUFF 압축(인코더) 함수 자리에 넣는다.
"""
import struct
from asm import *
CAVE = 0x68ce08   # HUFF 인코더(모드 0, 게임에서 호출 안 함) 자리
LEAD = 0xE0

def two_byte(b, ch, idx, load_next):
    """ch 가 선행 바이트면 다음 바이트와 합치고 idx 를 1 증가. load_next: 다음 바이트를 v1 에 싣는 명령들"""
    b(sltiu('v0', ch, LEAD), ('bne', 'v0', 'zero', 'end' + ch), nop())
    b(*load_next)
    b(sll(ch, ch, 8), or_(ch, ch, 'v1'), addiu(idx, idx, 1), ('label', 'end' + ch))

def build():
    b = Block(CAVE)
    entries = {}
    # A: 출력 레이아웃 0x5c4738 (글자 s4, 인덱스 s6, 문자열 4($sp))
    entries['A'] = CAVE
    b(lw('a0', 0, 'sp'))
    two_byte(b, 's4', 's6', [lw('v1', 4, 'sp'), addu('v1', 'v1', 's6'), lbu('v1', 1, 'v1')])
    b(j(0x5c4740), nop())
    # B: 폭 측정 0x5c49a0 (글자 s1, 인덱스 s3, 문자열 s7)
    entries['B'] = CAVE + 4 * len(b.assemble())
    b(move('a0', 'fp'))
    b(sltiu('v0', 's1', LEAD), ('bne', 'v0', 'zero', 'Bend'), nop(),
      addu('v1', 's7', 's3'), lbu('v1', 1, 'v1'), sll('s1', 's1', 8), or_('s1', 's1', 'v1'), addiu('s3', 's3', 1),
      ('label', 'Bend'), jal(0x5c3e18), move('a1', 's1'), j(0x5c49ac), nop())
    # C: 줄바꿈 0x5c4bc8 (글자 s1, 인덱스 s6, 현재 위치 s3)
    entries['C'] = CAVE + 4 * len(b.assemble())
    b(move('a0', 'fp'))
    b(sltiu('v0', 's1', LEAD), ('bne', 'v0', 'zero', 'Cend'), nop(),
      lbu('v1', 1, 's3'), sll('s1', 's1', 8), or_('s1', 's1', 'v1'), addiu('s6', 's6', 1),
      ('label', 'Cend'), j(0x5c4bd0), nop())
    # D: 한 글자 폭 0x5c4a60 (a1 = 1바이트 글자). 선행 바이트면 첫 한글 글리프(0xE080)의 폭을 쓴다
    entries['D'] = CAVE + 4 * len(b.assemble())
    b(sltiu('v0', 'a1', LEAD), ('bne', 'v0', 'zero', 'Dend'), nop(),
      ori('a1', 'zero', (LEAD << 8) | 0x80),
      ('label', 'Dend'), j(0x5c3e18), nop())
    code = b.assemble()
    hooks = {0x5c4738: [j(entries['A'])],
             0x5c49a0: [j(entries['B']), nop()],
             0x5c4bc8: [j(entries['C'])],
             0x5c4a70: [jal(entries['D'])]}
    return struct.pack('<%dI' % len(code), *code), hooks

def patch(elf):
    d = bytearray(elf)
    code, hooks = build()
    phoff = struct.unpack_from('<I', d, 0x1c)[0]; phn = struct.unpack_from('<H', d, 0x2c)[0]
    t, off, va, pa, fs, ms = struct.unpack_from('<6I', d, phoff)
    def fo(a): return a - va + off
    expect = {0x5c4738: [0x8fa40000], 0x5c49a0: [0x03c0202d, 0x0c170f86], 0x5c4bc8: [0x03c0202d],
              0x5c4a70: [0x0c170f86]}
    for a, ws in hooks.items():
        cur = list(struct.unpack_from('<%dI' % len(ws), d, fo(a)))
        assert cur == expect[a], (hex(a), [hex(x) for x in cur])
        struct.pack_into('<%dI' % len(ws), d, fo(a), *ws)
    assert len(code) <= 0x68d018 - CAVE
    d[fo(CAVE):fo(CAVE) + len(code)] = code
    # 글꼴 레이어(2비트 두 겹) 패치: HUFF 인코더 나머지 + LZM1 인코더 자리
    import fontlayer
    c1 = (CAVE + len(code) + 15) & ~15
    blobs, lhooks, lexp = fontlayer.build(c1, 0x68ec58)
    for a, ws in lhooks.items():
        cur = list(struct.unpack_from('<%dI' % len(lexp[a]), d, fo(a)))
        assert cur == lexp[a], (hex(a), [hex(x) for x in cur])
        struct.pack_into('<%dI' % len(ws), d, fo(a), *ws)
    for a, blob in blobs:
        assert a + len(blob) <= (0x68d0e8 if a < 0x68e000 else 0x68efd8), hex(a)
        d[fo(a):fo(a) + len(blob)] = blob
    return bytes(d)

if __name__ == '__main__':
    code, hooks = build()
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32 | capstone.CS_MODE_LITTLE_ENDIAN)
    for i in md.disasm(code, CAVE): print(hex(i.address), i.mnemonic, i.op_str)
    for a, ws in hooks.items():
        for i in md.disasm(struct.pack('<%dI' % len(ws), *ws), a): print(hex(i.address), i.mnemonic, i.op_str)
