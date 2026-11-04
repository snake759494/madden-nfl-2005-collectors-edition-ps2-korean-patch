"""SPCHDATA/SPCHFEDT 의 모든 SCHl 음성 스트림을 위치(DAT 내 절대 오프셋)·슬롯 크기와 함께 추출.
슬롯 = 다음 스트림(또는 잎 끝)까지의 바이트. 재삽입은 슬롯 안에서 제자리 덮어쓰기."""
import sys, os, struct, json
sys.path.insert(0, os.path.dirname(__file__))
import terf
ISO = sys.argv[1]; OUT = sys.argv[2]
DATS = {'SPCHDATA': (880466, 837017600), 'SPCHFEDT': (720936, 245590016)}

def walk(d, base, path, out):
    if d[:4] == b'TERF':
        ch, _ = terf.parse(d)
        if 'DIR1' in ch:
            for i, (o, s, c, u) in enumerate(terf.entries(d)):
                if not c: walk(d[o:o + s], base + o, path + '/%d' % i, out)
            return
    if d[:4] != b'SCHl': return
    offs = []; i = 0
    while i >= 0:
        offs.append(i); i = d.find(b'SCHl', i + 1)
        # SCHl 이 블록 데이터 안에 우연히 나올 수 있으므로 앞 스트림의 SCEl 이후만 인정
    good = []; end = 0
    for o in offs:
        if o < end: continue
        j = d.find(b'SCEl', o)
        if j < 0: break
        good.append(o); end = j + struct.unpack_from('<I', d, j + 4)[0]
    for k, o in enumerate(good):
        slot = (good[k + 1] if k + 1 < len(good) else len(d)) - o
        out.append(dict(path=path, k=k, off=base + o, slot=slot))

man = []
f = open(ISO, 'rb')
for nm, (lba, sz) in DATS.items():
    f.seek(lba * 2048); d = f.read(sz); out = []; walk(d, 0, '', out)
    os.makedirs(os.path.join(OUT, nm), exist_ok=True)
    for n, e in enumerate(out):
        e['dat'] = nm; e['id'] = '%s_%05d' % (nm, n)
        o = e['off']; j = d.find(b'SCEl', o); e['len'] = j + struct.unpack_from('<I', d, j + 4)[0] - o
        open(os.path.join(OUT, nm, e['id'] + '.asf'), 'wb').write(d[o:o + e['len']])
    man += out; print(nm, len(out))
json.dump(man, open(os.path.join(OUT, 'manifest.json'), 'w'))
