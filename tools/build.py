"""매든 NFL 2005 한글 패치 빌드: python tools/build.py"""
import os, sys, struct, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import isofs, isobuild2, terf, lzh, screen, apt, kfont2, elfpatch, ktext, content, widescreen, dub
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
WORK = os.path.join(ROOT, 'work')
SRC = os.path.join(ROOT, "Madden NFL 2005 (USA) (Collector's Edition).iso")
DST = os.path.join(ROOT, "Madden NFL 2005 (USA) (Collector's Edition) (Korean).iso")
DST = os.environ.get("OUT", DST)
FONT_DIR = ROOT
FONT_MAIN = os.path.join(FONT_DIR, 'NanumSquareNeo-cBd.ttf')
FONT_HEAVY = os.path.join(FONT_DIR, 'NanumSquareNeo-dEb.ttf')
FONT_SMALL = os.path.join(WORK, 'fonts', 'Galmuri11-Bold.ttf')

def read(f, ents, name):
    _, lba, size, _ = ents[name]; f.seek(lba * 2048); return f.read(size)

def main():
    t0 = time.time()
    tr = ktext.Translator()
    f = open(SRC, 'rb'); ents = {e[0]: e for e in isofs.walk(f)}
    out = {}
    L = lzh.LZH(read(f, ents, 'SLUS_210.25'))
    # 1) UI 화면
    def proc(d):
        rep = {}
        for i, (o, s, c, u) in enumerate(terf.entries(d)):
            b = d[o:o + s]
            if c == 5: b = L.decode(b, u)[0]
            elif c != 0: continue
            if b[:4] == b'TERF':
                nb = proc(b)
            elif apt.is_apt(b):
                nb = apt.replace(b, tr.apt_string)
            elif screen.is_screen(b) and (os.environ.get('NOTOSS') is None or b'won the toss' not in b):
                nb = screen.replace(b, tr.screen_string)
            else: continue
            if nb is None or nb == b: continue
            rep[i] = (L.encode(nb)[0], 5, len(nb)) if c == 5 else (nb, 0)
        return terf.rebuild(d, rep) if rep else None
    uis = ['DATA/' + n + '.DAT' for n in ('UIS_ALL', 'UIS_POPS', 'UIS_PAUS', 'UIS_PAUC', 'UIS_MDRC', 'UIS_MEMC',
                                          'UIS_PRPS', 'UIS_SETT', 'UIS_SFPC', 'UIS_BANR', 'SONTOURN',
                                          # 온라인 메뉴(Apt 플래시)
                                          'SONLOGIN', 'SONGENRL', 'SONSETTG', 'FONLINE', 'SONLOBBY', 'LGENERAL',
                                          'SGENERAL', 'SONSTAT', 'SONMENU', 'SONEAMSG', 'SONPREGM')]
    for name in uis:
        d = read(f, ents, name)
        if d[:4] != b'TERF': continue
        nd = proc(d)
        if nd: out[name] = nd; print(name, len(d), '->', len(nd))
    print('used', len(tr.used), 'missing', len(tr.missing))
    # 1-2) QKL 캐시: 항목 표(DTLS)를 비워 게임이 원래 파일에서 읽게 한다
    for name in ('DATA/FE.QKL', 'DATA/GAME.QKL'):
        q = bytearray(read(f, ents, name)); p = q.find(b'DTLS')
        struct.pack_into('<I', q, p + 8, 0)
        out[name] = bytes(q)
    # 2) ELF
    out['SLUS_210.25'] = elfpatch.patch(tr.patch_elf(read(f, ents, 'SLUS_210.25')))
    # 2-2) 온라인 모듈(ONLINE.DAT 0번 항목 = 재배치 ELF): .data/.rodata 문자열 제자리 교체
    d = read(f, ents, 'DATA/ONLINE.DAT'); o, s, c, u = list(terf.entries(d))[0]
    ov = tr.patch_elf(d[o:o + s], [(0x83940, 0x1237e0), (0x1237e0, 0x13ce30)])
    out['DATA/ONLINE.DAT'] = d[:o] + ov + d[o + s:]
    # 2-3) DB(선수 이름, 작전명, 퀴즈, 문구) / 신문 기사
    cp = content.Patcher(tr)
    cp.patch_files(lambda n: read(f, ents, n), L, out)
    if cp.long: open(os.path.join(WORK, 'db_long.txt'), 'w', encoding='utf-8').write(chr(10).join(cp.long))
    # 3) 폰트
    chars = tr.charset()
    print('syllables', len(chars))
    for name in ('DATA/UIS_FONT.DAT', 'DATA/FONTS.DAT'):
        d = read(f, ents, name); rep = {}; pages = 0
        for i, (o, s, c, u) in enumerate(terf.entries(d)):
            b = d[o:o + s]
            if b[:4] != b'FNTS': continue
            nb, img = make_font(b, chars)
            pages += img.shape[0] * img.shape[1] // 2
            rep[i] = (nb, 0)
        out[name] = terf.rebuild(d, rep)
        print(name, len(d), '->', len(out[name]), 'texbytes', pages)
    # 4) 한국어 해설 더빙
    nd = dub.patch(read(f, ents, 'DATA/SPCHDATA.DAT'), os.environ.get('SPEECH', os.path.join(WORK, 'speech')))
    if nd: out['DATA/SPCHDATA.DAT'] = nd
    f.close()
    tr.report(os.path.join(WORK, 'missing.txt'))
    only = os.environ.get('ONLY')
    if only: out = {k: v for k, v in out.items() if any(x in k for x in only.split(','))}
    isobuild2.build(SRC, DST, out)
    # 4) 와이드 패치: 한글판·원본용 pnach를 ISO 옆에 쓴다
    f = open(SRC, 'rb'); widescreen.write(read(f, ents, 'SLUS_210.25'), out['SLUS_210.25'], ROOT); f.close()
    print('done %.1fs' % (time.time() - t0))

def make_font(b, chars):
    import sfn
    f = sfn.SFN(b)
    top, base = kfont2.metrics(f)
    cap = base - top
    ttf = FONT_SMALL if cap <= 11 else FONT_MAIN
    return kfont2.build(b, chars, ttf, scale=1.05, maxh=int(os.environ.get('MAXH', 11)))

if __name__ == '__main__':
    main()
