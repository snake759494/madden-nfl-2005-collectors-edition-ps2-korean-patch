"""번역 작업 나누기/검사/합치기
  python jobs.py split            src/*.txt -> jobs/<묶음>_NN.in.tsv  (번호\t바이트한도\t영문)
  python jobs.py check FILE...    jobs/*.out.tsv 검사 (번호\t한글)
  python jobs.py merge            jobs/*.out.tsv -> translation/db_50_*.tsv, story_50_*.tsv
"""
import os, sys, re, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
W = os.path.join(HERE, '..'); SRC = os.path.join(W, 'src'); J = os.path.join(W, 'jobs'); TR = os.path.join(W, 'translation')
GROUPS = [('names', ['name_first', 'name_last', 'name_misc']), ('teamplay', ['team', 'play']), ('trivia', ['trivia']),
          ('scout', ['scout']), ('text', ['text']), ('cptn', ['story_cptn']), ('hdln', ['story_hdln']),
          ('emal', ['story_emal']), ('stext', ['story_text'])]
MAXC = 95000
TOK = re.compile(r'%[A-Za-z_]+-[a-z0-9]+%|%%|%[0-9]|%[A-Z]{2,}[0-9]*|%[-+#0]*[0-9]*(?:\.[0-9]+)?[hlL]*[diouxXcsfeEgGp]|\r|\n|\t|^<[^>]*>')

def src_lines(g):
    out = []
    for f in dict(GROUPS)[g]:
        for line in open(os.path.join(SRC, f + '.txt'), encoding='utf-8'):
            cap, en = line.rstrip('\n').split('\t', 1); out.append((f, int(cap), en))
    return out

def split():
    for g, _ in GROUPS:
        L = src_lines(g); chunks = [[]]; n = 0
        for i, x in enumerate(L):
            if n > MAXC: chunks.append([]); n = 0
            chunks[-1].append((i, x)); n += len(x[2])
        for k, c in enumerate(chunks):
            with open(os.path.join(J, '%s_%02d.in.tsv' % (g, k)), 'w', encoding='utf-8', newline='\n') as w:
                for i, (f, cap, en) in c: w.write('%d\t%d\t%s\n' % (i, cap, en))
            print(g, k, len(c), sum(len(x[1][2]) for x in c))

def blen(t): return sum(2 if '가' <= c <= '힣' else 1 for c in re.sub(r'\[rnt]', 'x', t))
def toks(t): return collections.Counter(TOK.findall(t))

def check(fn):
    inn = {}
    for line in open(fn.replace('.out.', '.in.'), encoding='utf-8'):
        i, cap, en = line.rstrip('\n').split('\t', 2); inn[i] = (int(cap), en)
    errs = []; got = {}
    if os.path.exists(fn):
        for ln, line in enumerate(open(fn, encoding='utf-8'), 1):
            line = line.rstrip('\n')
            if not line: continue
            if '\t' not in line: errs.append('line %d: no tab' % ln); continue
            i, ko = line.split('\t', 1); got[i] = ko
    for i, (cap, en) in inn.items():
        if i not in got: errs.append('%s: missing' % i); continue
        ko = got[i]
        bad = [c for c in ko if not (32 <= ord(c) < 127 or '가' <= c <= '힣')]
        if bad: errs.append('%s: bad chars %r (use ASCII or Hangul syllables only)' % (i, ''.join(sorted(set(bad)))))
        if toks(en) != toks(ko): errs.append('%s: tokens differ: en %s / ko %s' % (i, sorted(toks(en).elements()), sorted(toks(ko).elements())))
        if blen(ko) > cap: errs.append('%s: too long %d > %d bytes (Hangul = 2 bytes)' % (i, blen(ko), cap))
    for i in got:
        if i not in inn: errs.append('%s: unknown id' % i)
    return errs, got

def merge():
    for g, files in GROUPS:
        L = src_lines(g); res = {}
        for fn in glob.glob(os.path.join(J, g + '_*.out.tsv')):
            errs, got = check(fn); bad = {e.split(':')[0] for e in errs}
            for i, ko in got.items():
                if i not in bad: res[int(i)] = ko
        per = collections.defaultdict(list)
        for i, ko in sorted(res.items()):
            f, cap, en = L[i]
            if not re.search(r'[가-힣]', ko) or en.startswith('ÿþ') or chr(0) in en: continue
            ko = ko.replace('% ok', '%').replace('(57% of fans)', '(57%)')
            per[f].append('%s\t%s' % (en, ko))
        for f, lines in per.items():
            pre = 'story_50_' if f.startswith('story') else 'db_50_'
            open(os.path.join(TR, pre + f + '.tsv'), 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
            print(f, len(lines))

if __name__ == '__main__':
    if sys.argv[1] == 'split': split()
    elif sys.argv[1] == 'merge': merge()
    else:
        for fn in sys.argv[2:]:
            errs, got = check(fn)
            print('%s: %d translated, %d errors' % (os.path.basename(fn), len(got), len(errs)))
            for e in errs[:60]: print('  ' + e)
            base = set(open(os.path.join(J, 'base_syllables.txt'), encoding='utf-8').read())
            new = collections.Counter(c for v in got.values() for c in v if '가' <= c <= '힣' and c not in base)
            print('  syllables outside base_syllables.txt: %d -> %s' % (len(new), ' '.join('%s%d' % kv for kv in new.most_common())))
