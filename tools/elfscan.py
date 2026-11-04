"""ELF 데이터 영역에서 번역 사전에 없는 문장형 문자열을 elf_need.txt 로 뽑는다"""
import sys, os, glob, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import isofs, ktext
f = open(glob.glob(os.path.join(HERE, '..', '..', '*Edition).iso'))[0], 'rb'); E = {e[0]: e for e in isofs.walk(f)}
_, l, s, _ = E['SLUS_210.25']; f.seek(l * 2048); b = f.read(s)
tr = ktext.Translator()
out = []; seen = set()
for lo, hi in tr.ELF_RANGES:
    for m in re.finditer(rb'(?<=\x00)[\x20-\x7e\t\r\n\xa0-\xff]{3,}(?=\x00)', b[lo:hi]):
        t = m.group().decode('latin1')
        if t in seen or tr.elf_lookup(t) is not None: continue
        seen.add(t)
        if not re.search(r'[a-z]{2,}', t) or ' ' not in t.strip(): continue
        if re.search(r'[_{}\\/<>=]|\.(c|cpp|h|dat|tdb|qkl)\b|%[0-9]*[sd].*:.*%|^[a-z]+[A-Z]', t): continue
        out.append(t)
open(os.path.join(HERE, '..', 'elf_need.txt'), 'w', encoding='utf-8', newline='\n').write(''.join(ktext.esc(t) + '\n' for t in out))
print(len(out))
