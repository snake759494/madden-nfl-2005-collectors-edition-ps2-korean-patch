"""EA TDB('DB\\0\\x08') 읽기/문자열 필드 쓰기

헤더: +0x10 표 개수, +0x18 (이름4, 오프셋) 목록, 그 뒤가 표 데이터 기준점.
표: +8 레코드 바이트, +0xc 레코드 비트, +0x14 최대 레코드, +0x16 레코드 수, +0x1c 필드 수,
    +0x28 필드 정의(형식, 비트 위치, 이름4, 비트 길이) x 필드 수, 그 뒤 레코드.
형식 0 = 문자열(고정 길이, 비트 길이/8 바이트).
"""
import struct

class Table:
    def __init__(s, db, name, base):
        b = db.b
        s.name = name; s.base = base
        s.recbytes, s.recbits = struct.unpack_from('<II', b, base + 8)
        s.maxrec, s.nrec = struct.unpack_from('<HH', b, base + 0x14)
        s.nfield = b[base + 0x1c]
        s.fields = {}
        for i in range(s.nfield):
            t, off, nm, bits = struct.unpack_from('<II4sI', b, base + 0x28 + 16 * i)
            s.fields[nm[::-1].decode('latin1')] = (t, off, bits)
        s.data = base + 0x28 + 16 * s.nfield
    def strfields(s):
        return [k for k, (t, o, n) in s.fields.items() if t == 0]
    def rec(s, i): return s.data + i * s.recbytes
    def get_str(s, db, i, f):
        t, off, bits = s.fields[f]
        p = s.rec(i) + off // 8
        raw = bytes(db.b[p:p + bits // 8])
        return raw.split(b'\0')[0]
    def set_str(s, db, i, f, val):
        t, off, bits = s.fields[f]
        n = bits // 8; p = s.rec(i) + off // 8
        if len(val) >= n: raise ValueError('too long %s %d>=%d' % (f, len(val), n))
        db.b[p:p + n] = val + bytes(n - len(val))

class TDB:
    def __init__(s, b):
        s.b = bytearray(b)
        assert s.b[:4] == b'DB\x00\x08'
        n = struct.unpack_from('<I', s.b, 0x10)[0]
        dirs = [(s.b[0x18 + 8 * i:0x1c + 8 * i].decode('latin1'), struct.unpack_from('<I', s.b, 0x1c + 8 * i)[0]) for i in range(n)]
        base = 0x18 + 8 * n
        s.tables = {nm: Table(s, nm, base + off) for nm, off in dirs}
        s.dir = (0x18, base)
    def bytes(s):
        """CRC(CRC-32/MPEG-2) 다시 계산: 헤더, 디렉터리 -> 첫 표 +0, 각 표(+0x28~다음 표) -> 다음 표 +0, 마지막 표 -> 끝 4바이트"""
        b = s.b
        struct.pack_into('<I', b, 0x14, crc(b[0:0x14]))
        tl = sorted(s.tables.values(), key=lambda t: t.base)
        struct.pack_into('<I', b, tl[0].base, crc(b[s.dir[0]:s.dir[1]]))
        ends = [t.base for t in tl[1:]] + [len(b) - 4]
        for t, e in zip(tl, ends):
            struct.pack_into('<I', b, e, crc(b[t.base + 0x28:e]))
        return bytes(b)

def _table():
    T = []
    for i in range(256):
        c = i << 24
        for _ in range(8): c = ((c << 1) ^ 0x04C11DB7) & 0xffffffff if c & 0x80000000 else (c << 1) & 0xffffffff
        T.append(c)
    return T
_T = _table()
def crc(x, c=0xffffffff):
    T = _T
    for v in bytes(x): c = T[((c >> 24) ^ v) & 0xff] ^ ((c << 8) & 0xffffffff)
    return c
