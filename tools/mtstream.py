"""PCM(36kHz mono s16) -> EA SCHl MicroTalk Rev3 스트림. 원본 스트림의 SCHl 헤더를 재사용(샘플 수만 교체)."""
import struct, subprocess, os, tempfile
ENC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ext', 'utk', 'mtenc.exe'))
PACK = ENC.replace('mtenc.exe', 'mtpack.exe')

def encode_frames(pcm, rate=36000, bitrate=56000):
    """pcm: bytes(s16le). -> [(nbits, bytes)] 프레임별"""
    fd, wav = tempfile.mkstemp(suffix='.wav'); os.close(fd)
    out = wav + '.mt'
    with open(wav, 'wb') as f:
        f.write(b'RIFF' + struct.pack('<I', 36 + len(pcm)) + b'WAVEfmt ' +
                struct.pack('<IHHIIHH', 16, 1, 1, rate, rate * 2, 2, 16) + b'data' + struct.pack('<I', len(pcm)) + pcm)
    subprocess.run([ENC, '-f', '-q', '-b', str(bitrate), wav, out], check=True)
    subprocess.run([PACK, out, out + 'p'], check=True)
    d = open(out + 'p', 'rb').read(); os.remove(wav); os.remove(out); os.remove(out + 'p')
    fr = []; p = 0
    while p < len(d):
        nb = d[p] | d[p + 1] << 8
        fr.append((nb, d[p + 2:p + 2 + nb])); p += 2 + nb
    return fr

def parse_header(orig):
    """원본 스트림에서 SCHl 청크, 블록 엔디안, 블록당 프레임 수"""
    hl = struct.unpack_from('<I', orig, 4)[0]; sch = bytearray(orig[:hl])
    be = sch[8:12] == b'GSTR'
    p = hl + struct.unpack_from('<I', orig, hl + 4)[0]  # first SCDl
    ns = struct.unpack_from('>I' if be else '<I', orig, p + 8)[0]
    return sch, be, max(1, ns // 432)

def set_samples(sch, n):
    s = len(sch)
    while True:  # 뒤에서부터 0xfd 서브헤더 후보를 찾아 0x85(샘플 수)를 포함하는 것을 쓴다
        s = sch.rfind(b'\xfd', 0, s)
        if s < 0: raise ValueError('no 0x85')
        i = s; ok = None
        while i + 2 < len(sch):
            i += 1; k = sch[i]
            if k == 0xff: break
            L = sch[i + 1]
            if L > 4: break
            if k == 0x85: ok = (i, L); break
            i += 1 + L
        if ok:
            i, L = ok; assert n < 1 << (8 * L)
            sch[i + 2:i + 2 + L] = n.to_bytes(L, 'big'); return

def build(orig, pcm):
    sch, be, fpb = parse_header(orig)
    nsamp = len(pcm) // 2
    set_samples(sch, nsamp)
    fr = encode_frames(pcm)
    E = '>I' if be else '<I'
    blocks = []
    for b in range(0, len(fr), fpb):
        grp = fr[b:b + fpb]
        ns = min(432 * len(grp), nsamp - 432 * b)
        s = bytearray([0x00])  # 첫 프레임 플래그(PCM 없음)
        for n, by in grp: s += by  # 프레임 데이터 + 다음 플래그
        body = struct.pack(E, ns) + b'\0\0\0\0' + bytes([1 if b == 0 else 0]) + s
        while (len(body) + 8) % 4: body += b'\0'
        blocks.append(b'SCDl' + struct.pack('<I', len(body) + 8) + body)
    out = bytes(sch) + b'SCCl' + struct.pack('<I', 12) + struct.pack(E, len(blocks)) + b''.join(blocks) + b'SCEl\x08\0\0\0'
    return out
