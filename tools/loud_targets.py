"""원본 해설 조각별 활성 RMS(dB)를 측정해 speech/loud.json 으로 저장: python tools/loud_targets.py <원본 ISO>"""
import os, sys, json, subprocess, tempfile, wave, numpy as np
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import loud, isofs
W = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SP = os.path.join(W, 'speech'); VGM = os.path.abspath(os.path.join(W, 'ext', 'vgm', 'vgmstream-cli.exe'))
man = {e['id']: e for e in json.load(open(os.path.join(SP, 'manifest.json')))}
ids = sorted(f[:-4] for f in os.listdir(os.path.join(SP, 'ko')) if f.endswith('.pcm'))
iso = sys.argv[1]; base = 880466 * 2048
tmp = tempfile.mkdtemp()
def one(i):
    e = man[i]
    with open(iso, 'rb') as f: f.seek(base + e['off']); b = f.read(e['len'])
    a = os.path.join(tmp, i + '.asf'); w = a + '.wav'; open(a, 'wb').write(b)
    subprocess.run([VGM, '-o', w, a], capture_output=True)
    with wave.open(w) as h: x = np.frombuffer(h.readframes(h.getnframes()), '<i2') / 32768
    os.remove(a); os.remove(w)
    return i, round(float(loud.active_rms(x)), 2)
with ThreadPoolExecutor(6) as ex: res = dict(ex.map(one, ids))
os.rmdir(tmp)
json.dump(res, open(os.path.join(SP, 'loud.json'), 'w'))
print(len(res), np.median(list(res.values())))
