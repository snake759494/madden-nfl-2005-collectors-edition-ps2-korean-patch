"""번역 원문 목록 만들기: work/src/*.txt  (바이트 한도\t영문). 한글 1음절 = 2바이트"""
import os, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import isofs, terf, lzh, content
from ktext import esc
ROOT = os.path.join(HERE, '..', '..')
OUT = os.path.join(HERE, '..', 'src')
f = open(glob.glob(os.path.join(ROOT, '*Edition).iso'))[0], 'rb'); E = {e[0]: e for e in isofs.walk(f)}
def get(n):
    _, l, s, _ = E[n]; f.seek(l * 2048); return f.read(s)
L = lzh.LZH(get('SLUS_210.25'))
ex = content.extract(get, L)
GROUPS = {
    'name_first': [('PLAY', 'ANFP'), ('SPNM', 'ANFP'), ('PICO', 'ANFP'), ('PLGA', 'ANFP'), ('AWPL', 'ANFP')],
    'name_last': [('PLAY', 'ANLP'), ('DRYR', 'ANLP'), ('PICO', 'ANLP'), ('PLGA', 'ANLP'), ('AWPL', 'ANLP')],
    'name_misc': [('COCH', 'ANLC'), ('OCRI', 'ANLC'), ('PLAB', 'MANB'), ('MCCM', 'mNCM'), ('SMRC', 'NHRM'), ('SMRC', 'NORM'),
                  ('SDHS', 'MNSH'), ('STHS', 'MNSH'), ('TD1P', 'ANPT'), ('TD2P', 'ANPT'), ('T1HS', 'ANPT'), ('T2HS', 'ANPT'),
                  ('OSSI', 'ENSS')],
    'trivia': [('TRTX', k) for k in ('XTQT', '1WAT', '2WAT', '3WAT', '4WAT', '5WAT', '6WAT', '7WAT', '8WAT', '9WAT', 'IRAT')],
    'team': [('TEAM', 'ANDT'), ('TEAM', 'ANLT'), ('TEAM', 'CNMT'), ('CITY', 'MNYC'), ('CITY', 'TSYC'), ('CTSS', 'TSYC'),
             ('COLL', 'ANOC'), ('STAD', 'ANMT'), ('STAD', 'MANS'), ('CTLC', 'ANDT'), ('CTLG', 'NDTC'), ('OCTT', 'ANDT'),
             ('OCTT', 'ANLT'), ('DIVI', 'MAND'), ('EXDI', 'MAND'), ('CONF', 'MANC'), ('LEAG', 'MANL'), ('OWST', 'ANMT'),
             ('OWST', 'MANS'), ('OTRI', 'ANDT'), ('OTRI', 'ANLT'), ('OTRI', 'NDOT'), ('OTRI', 'NLOT'), ('OTRL', 'ANDT'),
             ('OTRL', 'ANLT'), ('TMDP', 'ANDT'), ('TMDP', 'MNMT'), ('FNTP', 'NTPF')],
    'scout': [('SNOT', 'ETNS')],
    'play': [('FORM', 'eman'), ('PBFM', 'eman'), ('PBPL', 'eman'), ('PBST', 'eman'), ('PLYL', 'eman'), ('SETL', 'eman'),
             ('SPKF', 'eman'), ('SGF ', 'eman')],
}
os.makedirs(OUT, exist_ok=True)
used = set(); allcap = {}
for k, v in ex.items():
    for en, cap in v.items(): allcap[en] = min(cap, allcap.get(en, 999))
def dump(name, items):
    with open(os.path.join(OUT, name + '.txt'), 'w', encoding='utf-8', newline='\n') as w:
        for en in sorted(items): w.write('%d\t%s\n' % (allcap[en], esc(en)))
    print(name, len(items), sum(len(x) for x in items))
for g, keys in GROUPS.items():
    items = set()
    for k in keys:
        if k in ex: items |= set(ex[k]); used.add(k)
    dump(g, items)
rest = set()
for k, v in ex.items():
    if k not in used: rest |= set(v); print('  text', k, len(v))
dump('text', rest)
# 신문 기사
for n in content.STORY_FILES:
    d = get(n); items = set()
    for o, s, c, u in terf.entries(d):
        if c == 0 and s: items.add(d[o:o + s].decode('latin1'))
    for en in items: allcap[en] = 9999
    dump('story_' + n[9:13].lower(), items)
