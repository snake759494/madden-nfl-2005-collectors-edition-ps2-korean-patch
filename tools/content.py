"""DB(TDB) 문자열 필드와 신문 기사(STRY*) 추출/패치

번역 파일: translation/db_*.tsv  (영문\t한글) - 같은 영문은 모든 표/필드에서 같은 한글로 바뀐다.
          translation/db_99_fit.tsv (표.필드|영문\t한글) - 특정 필드에 길이가 안 맞을 때 쓰는 짧은 번역
          translation/story_*.tsv (영문\t한글) - STRY* 항목 전체 문자열
"""
import os, re, struct, glob
import terf, tdb
from ktext import esc, unesc

HERE = os.path.dirname(os.path.abspath(__file__))
TR = os.path.join(HERE, '..', 'translation')
DB_FILES = ['DATA/STDATANV.DB', 'DATA/DBTMPANV.DAT', 'DATA/DBTEMANV.DAT', 'DATA/GAMEDATA.DAT']
STORY_FILES = ['DATA/STRYTEXT.DAT', 'DATA/STRYEMAL.DAT', 'DATA/STRYCPTN.DAT', 'DATA/STRYHDLN.DAT']
# 번역하지 않는 표/필드: 크레딧, 디버그용 편집기, 노래/음반사, 웹 주소, 약칭 코드
SKIP = {('TCcl', 'edRC'), ('ASDF', 'MNDP'), ('ASDF', 'SDDP'), ('PATY', 'NODP'), ('PATY', 'NPDP'), ('PATY', 'DPDP'),
        ('PATY', 'MEDP'), ('MUSO', 'NOSM'), ('MUSO', 'NRAM'), ('MUSO', 'NLAM'), ('MUST', 'NTSM'), ('CITY', 'PNYC'),
        ('TEAM', 'ANST'), ('OCTT', 'ANST'), ('MCCO', 'OCCM'), ('NIRA', 'ORPD'), ('TEGP', 'YEKg'), ('TGPA', 'YEKg'),
        ('UINF', 'nuSP'), ('UINF', 'WPSP')}

def is_text(v):
    return re.search(rb'[A-Za-z]{2}', v) and all(32 <= c < 127 or c in (0xb0, 0xa9, 0xae, 9, 10, 13) for c in v)

def db_blobs(get, L):
    """(이름, 바이트, 되돌려 넣는 함수) - TERF 안 항목은 압축 여부를 기억해 다시 넣는다"""
    for n in DB_FILES:
        d = get(n)
        if d[:4] != b'TERF':
            yield n, d, None; continue
        for i, (o, s, c, u) in enumerate(terf.entries(d)):
            if not s: continue
            b = d[o:o + s]
            if c == 5: b = L.decode(b, u)[0]
            elif c != 0: continue
            if b[:4] == b'DB\x00\x08': yield '%s/%d' % (n, i), b, c

def extract(get, L):
    """{(표, 필드): {영문: 바이트 한도}}"""
    out = {}
    for name, b, _ in db_blobs(get, L):
        db = tdb.TDB(b)
        for tn, t in db.tables.items():
            for f in t.strfields():
                if (tn, f) in SKIP: continue
                n = t.fields[f][2] // 8
                for i in range(t.nrec):
                    v = t.get_str(db, i, f)
                    if is_text(v): out.setdefault((tn, f), {})[v.decode('latin1')] = n - 1
    return out

def load(pattern):
    d = {}
    for fn in sorted(glob.glob(os.path.join(TR, pattern))):
        for line in open(fn, encoding='utf-8'):
            line = line.rstrip('\n')
            if not line or line.startswith('#') or '\t' not in line: continue
            en, ko = line.split('\t', 1)
            d[unesc(en)] = unesc(ko)
    return d

class Patcher:
    def __init__(s, tr):
        s.tr = tr                      # ktext.Translator (enc, 음절표)
        s.db = tr.db; s.story = tr.story
        s.long = []; s.n = 0
    def db_value(s, tn, f, en, cap):
        ko = s.db.get('%s.%s|%s' % (tn, f, en)) or s.db.get(en)
        if ko is None: return None
        e = s.tr.enc(ko)
        if len(e) > cap:
            s.long.append('%s.%s|%s\t%s\t%d>%d' % (tn, f, esc(en), esc(ko), len(e), cap)); return None
        return e
    def patch_db(s, b):
        db = tdb.TDB(b); changed = False
        for tn, t in db.tables.items():
            for f in t.strfields():
                if (tn, f) in SKIP: continue
                cap = t.fields[f][2] // 8 - 1
                for i in range(t.nrec):
                    v = t.get_str(db, i, f)
                    if not is_text(v): continue
                    e = s.db_value(tn, f, v.decode('latin1'), cap)
                    if e is None: continue
                    t.set_str(db, i, f, e); changed = True; s.n += 1
        return db.bytes() if changed else None
    def patch_files(s, get, L, out):
        """out 에 바뀐 파일을 넣는다"""
        only = os.environ.get('DBONLY')
        for n in DB_FILES:
            if only is not None and only not in n: continue
            d = out.get(n) or get(n)
            if d[:4] != b'TERF':
                nb = s.patch_db(d)
                if nb: out[n] = nb
                continue
            rep = {}; nd = bytearray(d)
            for i, (o, sz, c, u) in enumerate(terf.entries(d)):
                if not sz or c not in (0, 5): continue
                b = d[o:o + sz]
                if c == 5: b = L.decode(b, u)[0]
                if b[:4] != b'DB\x00\x08': continue
                nb = s.patch_db(b)
                if nb is None: continue
                assert len(nb) == len(b)
                if c == 0: nd[o:o + sz] = nb; out[n] = bytes(nd)        # 같은 크기: 제자리
                else: rep[i] = (L.encode(nb)[0], 5, len(nb))
            if rep: out[n] = terf.rebuild(bytes(nd), rep)
        for n in STORY_FILES:
            d = get(n); rep = {}
            for i, (o, sz, c, u) in enumerate(terf.entries(d)):
                if c != 0 or not sz: continue
                en = d[o:o + sz].decode('latin1')
                ko = s.story.get(en)
                if ko is None: continue
                rep[i] = (s.tr.enc(ko), 0); s.n += 1
            if rep: out[n] = terf.rebuild(d, rep)
        print('DB/story strings patched', s.n, 'too long', len(s.long))
