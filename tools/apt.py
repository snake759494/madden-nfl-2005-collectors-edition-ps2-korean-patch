"""Apt(플래시) 블롭 문자열 교체: 'Apt Data' / 'Apt constant file'.

문자열은 4바이트 정렬, NUL 종료이며 같은 블롭 안의 정렬된 32비트 오프셋으로 참조된다.
새 문자열이 원래보다 길면 끝에 붙이고, 그 문자열을 가리키는 모든 오프셋을 고친다.
"""
import struct
MAGICS = (b'Apt Data\x1a', b'Apt constant file\x1a')
def is_apt(b): return b.startswith(MAGICS)
def _ptrs(b):
    """정렬된 워드 값 -> 그 워드 위치 목록"""
    m = {}
    for p in range(0, len(b) - 3, 4):
        v = struct.unpack_from('<I', b, p)[0]
        if 0x10 <= v < len(b) and v % 4 == 0: m.setdefault(v, []).append(p)
    return m
def strings(b):
    """(오프셋, 바이트열, 참조 위치 목록) - 참조되는 정렬 문자열만"""
    m = _ptrs(b)
    for v in sorted(m):
        if v and b[v - 1] != 0: continue
        e = b.find(b'\0', v)
        if e <= v: continue
        s = b[v:e]
        if all(c in (9, 10, 13) or 32 <= c < 127 or c >= 0xa0 for c in s):
            yield v, s, m[v]
def replace(b, tr):
    out = bytearray(b); changed = False
    for v, s, refs in list(strings(b)):
        n = tr(s)
        if n is None or n == s: continue
        changed = True
        if len(n) <= len(s):
            out[v:v + len(s)] = n + bytes(len(s) - len(n))
        else:
            while len(out) % 4: out.append(0)
            p = len(out); out += n + b'\0'
            for r in refs: struct.pack_into('<I', out, r, p)
    if not changed: return None
    while len(out) % 4: out.append(0)
    return bytes(out)
