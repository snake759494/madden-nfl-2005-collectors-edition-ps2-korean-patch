"""Apt 블롭에서 화면 표시용으로 보이는 문자열 중 번역 사전에 없는 것을 apt_need.txt 로 뽑는다"""
import sys, os, glob, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import isofs, terf, lzh, apt, ktext
ROOT = os.path.join(HERE, '..', '..')
f = open(glob.glob(os.path.join(ROOT, '*Edition).iso'))[0], 'rb'); E = {e[0]: e for e in isofs.walk(f)}
def rd(n): _, l, s, _ = E[n]; f.seek(l * 2048); return f.read(s)
L = lzh.LZH(rd('SLUS_210.25'))
S = {}
def walk(d, n):
    for o, s, c, u in terf.entries(d):
        b = d[o:o + s]
        if c == 5: b = L.decode(b, u)[0]
        elif c != 0: continue
        if b[:4] == b'TERF': walk(b, n)
        elif apt.is_apt(b):
            for v, s, r in apt.strings(b): S.setdefault(s.decode('latin1'), set()).add(n[5:-4])
APT_FILES = [n for n in E if n.startswith('DATA/') and E[n][2] < 20_000_000]
for n in APT_FILES:
    d = rd(n)
    if d[:4] == b'TERF': walk(d, n)
BAD = re.compile(r'undefined|ASSERT|Assert|^<.*>$|unloaded|library ID|####|\*\*\*|Biig|DEPRECATED|->|^[A-Z][A-Z0-9_]+$|^[A-Z][a-z]+[A-Z]\w*$|[_{}();=\\/]|\.\w+\(|^[a-z]+[A-Z]')
def disp(t):
    if BAD.search(t): return False
    if ' ' in t.strip() and re.search('[a-z]', t): return True
    return bool(re.fullmatch(r"[A-Z][a-z]+[.!?]?|[A-Z][A-Z ]+[A-Z]|\|.*", t))
tr = ktext.Translator()
need = [k for k in sorted(S) if disp(k) and k not in tr.ui and k not in tr.elf]
open(os.path.join(HERE, '..', 'apt_need.txt'), 'w', encoding='utf-8', newline='\n').write(
    ''.join(ktext.esc(k) + '\n' for k in need))
print(len(S), len(need))
