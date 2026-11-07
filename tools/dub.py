"""한국어 해설 음성을 SPCHDATA.DAT 에 제자리(슬롯 안) 삽입."""
import os, json
from concurrent.futures import ThreadPoolExecutor
import mtstream, loud

def patch(d, speech_dir, log=print):
    man = {e['id']: e for e in json.load(open(os.path.join(speech_dir, 'manifest.json')))}
    kodir = os.path.join(speech_dir, 'ko')
    if not os.path.isdir(kodir): return None
    ids = sorted(f[:-4] for f in os.listdir(kodir) if f.endswith('.pcm'))
    lj = os.path.join(speech_dir, 'loud.json')
    tgt = json.load(open(lj)) if os.path.exists(lj) else {}
    cache = os.path.join(speech_dir, 'enc'); os.makedirs(cache, exist_ok=True)
    def enc(i):
        e = man[i]; src = os.path.join(kodir, i + '.pcm'); c = os.path.join(cache, i + '.asf')
        if os.path.exists(c) and os.path.getmtime(c) >= os.path.getmtime(src): return i, open(c, 'rb').read()
        pcm = open(src, 'rb').read()
        if i in tgt: pcm = loud.match(pcm, min(-11.0, max(-22.0, tgt[i])))  # 원본 영어 해설과 같은 음량
        s = mtstream.build(d[e['off']:e['off'] + e['len']], pcm)
        open(c, 'wb').write(s); return i, s
    with ThreadPoolExecutor(4) as ex: res = list(ex.map(enc, ids))
    b = bytearray(d); n = over = 0
    for i, s in res:
        e = man[i]
        if len(s) > e['slot']: over += 1; continue
        b[e['off']:e['off'] + e['slot']] = s + bytes(e['slot'] - len(s)); n += 1
    log('dub: %d clips, %d skipped (too long)' % (n, over))
    return bytes(b)
