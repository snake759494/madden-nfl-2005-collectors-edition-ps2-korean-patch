"""번역 사전 로드, 한글 -> 2바이트 코드 변환"""
import os, json, re, glob
HERE = os.path.dirname(os.path.abspath(__file__))
TR = os.path.join(HERE, '..', 'translation')

class Translator:
    def __init__(s):
        s.ui = {}; s.elf = {}; s.apt = {}; s.db = {}; s.story = {}
        for pat, dic in (('ui_*.tsv', s.ui), ('elf_*.tsv', s.elf), ('apt_*.tsv', s.apt), ('db_*.tsv', s.db), ('story_*.tsv', s.story)):
            for fn in sorted(glob.glob(os.path.join(TR, pat))):
                for line in open(fn, encoding='utf-8'):
                    line = line.rstrip('\n')
                    if not line or line.startswith('#') or '\t' not in line: continue
                    en, ko = line.split('\t', 1)
                    dic[unesc(en)] = unesc(ko)
        # 이름 약식 "%c.%s"(이름 첫 바이트 + 성)는 한글 이름의 첫 바이트만 잘라내므로 성만 찍는 "%.*s" 로 바꾼다
        for k in s.elf: s.elf[k] = s.elf[k].replace('%c.%s', '%.*s')
        s.used = set(); s.missing = set(); s.texts = []
        s._chars = None
    def all_ko(s):
        return list(s.ui.values()) + list(s.elf.values()) + list(s.apt.values()) + list(s.db.values()) + list(s.story.values())
    def charset(s):
        if s._chars is None:
            cs = set()
            for t in s.all_ko(): cs.update(c for c in t if '\uac00' <= c <= '\ud7a3')
            extra = int(os.environ.get('EXTRA', 0))   # 시험용: KS X 1001 음절을 더 넣는다
            for c in ks_syllables():
                if extra <= 0: break
                if c not in cs: cs.add(c); extra -= 1
            s._chars = sorted(cs)
            s.idx = {c: i for i, c in enumerate(s._chars)}
        return list(enumerate(s._chars))
    def enc(s, t):
        s.charset()
        out = bytearray()
        for c in t:
            if c in s.idx:
                i = s.idx[c]; out += bytes([0xE0 + i // 128, 0x80 + i % 128])
            else:
                out += c.encode('latin1')
        return bytes(out)
    def screen_string(s, raw):
        pad = len(raw) - len(raw.rstrip(b'\0'))
        key = raw.rstrip(b'\0').decode('latin1')
        if key not in s.ui:
            s.missing.add(key); return None
        if sig(key) != sig(s.ui[key]):
            s.missing.add('FMT ' + key); return None
        s.used.add(key)
        n = s.enc(s.ui[key])
        if pad:   # 고정 길이 버퍼: 같은 길이 유지
            if len(n) >= len(raw): return None
            return n + bytes(len(raw) - len(n))
        return n
    # ELF 데이터 영역(파일 오프셋 범위): .rodata x2, .data, .rodata, .sdata
    ELF_RANGES = [(0x1000, 0x34cc), (0x3500, 0x5fca0), (0x5b7c00, 0x604528), (0x604800, 0x65d879), (0x660e00, 0x66b780)]
    def elf_lookup(s, key):
        if key in s.elf: return s.elf[key]
        if ' ' in key.strip() and len(key) >= 8 and key in s.ui: return s.ui[key]
        return None
    def patch_elf(s, elf, ranges=None):
        b = bytearray(elf); n_ok = n_long = n_fmt = 0
        s.elf_long = []
        ok = lambda c: c in (9, 10, 13) or 32 <= c < 127 or 0xa0 <= c
        for lo, hi in ranges or s.ELF_RANGES:
            i = lo
            while i < hi:
                if b[i] == 0 or (i > lo and b[i - 1] != 0): i += 1; continue
                j = i
                while j < hi and b[j] != 0 and ok(b[j]): j += 1
                if j >= hi or b[j] != 0 or j - i < 3: i = j + 1; continue
                key = bytes(elf[i:j]).decode('latin1')
                ko = s.elf_lookup(key)
                if ko is not None:
                    if sig(key) != sig(ko):
                        n_fmt += 1; s.elf_long.append('FMT\t' + esc(key))
                    else:
                        k = j
                        while k < hi and b[k] == 0: k += 1
                        cap = k - i - 1          # 다음 항목 직전까지 (NUL 1바이트 남김)
                        enc = s.enc(ko)
                        if len(enc) <= cap:
                            b[i:k] = enc + bytes(k - i - len(enc)); n_ok += 1; s.used.add(key)
                        else:
                            n_long += 1; s.elf_long.append('%d>%d\t%s\t%s' % (len(enc), cap, esc(key), esc(ko)))
                i = j + 1
        print('ELF strings patched', n_ok, 'too long', n_long, 'fmt mismatch', n_fmt)
        return bytes(b)
    def apt_string(s, raw):
        """Apt 문자열: 한 단어는 스크립트 식별자일 수 있으므로 apt 사전에 명시한 것만, 나머지는 띄어쓰기 있는 UI 문장도 허용"""
        key = raw.decode('latin1')
        ko = s.apt.get(key)
        if ko is None and ' ' in key.strip() and key in s.ui: ko = s.ui[key]
        if ko is None or sig(key) != sig(ko): return None
        s.used.add(key)
        return s.enc(ko)
    def report(s, fn):
        open(fn, 'w', encoding='utf-8').write('\n'.join(sorted(esc(x) for x in s.missing)))

def ks_syllables():
    return [bytes([a, b]).decode('cp949') for a in range(0xb0, 0xc9) for b in range(0xa1, 0xff)]

def sig(t):
    return FMT.findall(t.replace('%.*s', '%c%s'))

FMT = re.compile(r'%[-+ #0]*[0-9]*(?:\.[0-9]+)?[hlL]*[diouxXcsfeEgGp%]')
BS = chr(92)
def esc(t): return t.replace(BS, BS + BS).replace('\n', BS + 'n').replace('\r', BS + 'r').replace('\t', BS + 't')
def unesc(t):
    m = {'n': '\n', 'r': '\r', 't': '\t', BS: BS}
    out = []; i = 0
    while i < len(t):
        if t[i] == BS and i + 1 < len(t) and t[i + 1] in m: out.append(m[t[i + 1]]); i += 2
        else: out.append(t[i]); i += 1
    return ''.join(out)
