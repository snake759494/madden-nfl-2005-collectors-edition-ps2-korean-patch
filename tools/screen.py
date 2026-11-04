"""UI 화면(UIS) 블롭의 문자열 표: 헤더 +8 개수, +12 표 오프셋, 레코드 (타입, 길이, 오프셋)"""
import struct
def strings(b):
    cnt, off = struct.unpack_from('<II', b, 8)
    return [struct.unpack_from('<III', b, off + 12 * i) for i in range(cnt)]
def is_screen(b):
    if len(b) < 48 or b[:4] == b'TERF': return False
    cnt, off = struct.unpack_from('<II', b, 8)
    if off + cnt * 12 > len(b) or cnt == 0: return False
    return all(t == 1 and o + l <= len(b) for t, l, o in strings(b))
def replace(b, tr):
    """tr(bytes)->bytes|None. 새 문자열은 끝에 붙이고 레코드만 고친다(같거나 짧으면 제자리)"""
    out = bytearray(b); cnt, off = struct.unpack_from('<II', b, 8)
    cache = {}
    for i, (t, l, o) in enumerate(strings(b)):
        s = b[o:o + l]; n = tr(s)
        if n is None or n == s: continue
        if len(n) <= l:
            out[o:o + l] = n + bytes(l - len(n))   # 끝 NUL 채움
            struct.pack_into('<I', out, off + 12 * i + 4, len(n))
        else:
            if n not in cache:
                while len(out) % 4: out.append(0)
                cache[n] = len(out); out += n + b'\0'
            struct.pack_into('<II', out, off + 12 * i + 4, len(n), cache[n])
    while len(out) % 4: out.append(0)
    return bytes(out)
