"""PCSX2 16:9 와이드 패치(pnach) 생성: 3D 투영의 4:3 비율 상수(0x3FAAAAAB)를 16:9(0x3FE38E39)로 바꾼다.
파일 이름의 CRC = 실행파일 전체를 32비트 단어로 XOR한 값"""
import struct
# 4:3·16:9 값이 짝으로 놓인 .data 상수 표의 4:3 자리 (가상 주소)
ADDRS = [0x75c9b8, 0x75c9bc, 0x75e91c, 0x75e924, 0x75e930, 0x75fb48]
R43, R169 = 0x3FAAAAAB, 0x3FE38E39
VBASE = 0x100000 - 0x1000      # 첫 LOAD 세그먼트: 파일 0x1000 -> 0x100000

def crc(elf):
    c = 0
    for (w,) in struct.iter_unpack('<I', elf[:len(elf) // 4 * 4]): c ^= w
    return c

def pnach(elf, title):
    for a in ADDRS:
        assert struct.unpack_from('<I', elf, a - VBASE)[0] == R43, hex(a)
    lines = ['gametitle=%s' % title, '', '[Widescreen 16:9]', 'gsaspectratio=16:9', 'author=snake759494',
             'description=3D 화면 비율 4:3 -> 16:9 (투영 비율 상수 교체)', '']
    lines += ['patch=1,EE,2%07x,extended,%08X //%08X' % (a, R169, R43) for a in ADDRS]
    return '%08X' % crc(elf), '\n'.join(lines) + '\n'

def write(orig_elf, ko_elf, outdir):
    out = []
    for elf, t in ((ko_elf, 'Madden NFL 2005 [Special Collectors Edition] (SLUS-21025) 한글패치판'),
                   (orig_elf, 'Madden NFL 2005 [Special Collectors Edition] (SLUS-21025)')):
        c, txt = pnach(elf, t)
        fn = '%s/SLUS-21025_%s.pnach' % (outdir, c)
        open(fn, 'w', encoding='utf-8', newline='\n').write(txt); out.append(fn)
    print('widescreen', out)
    return out
