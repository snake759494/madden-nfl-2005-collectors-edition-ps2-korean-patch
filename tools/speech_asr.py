"""해설 조각 받아쓰기(영어 원문 확보용). 짧은 조각을 무음으로 이어 붙여 한 번에 처리하고 단어 시각으로 다시 나눈다.
이어하기 지원. 출력: speech/asr.tsv  id<TAB>sec<TAB>text"""
import os, sys, wave, json
import numpy as np
from faster_whisper import WhisperModel
ROOT = sys.argv[1]; MODEL = sys.argv[2] if len(sys.argv) > 2 else 'base.en'
out = os.path.join(ROOT, 'asr.tsv')
done = set()
if os.path.exists(out):
    for l in open(out, encoding='utf-8'): done.add(l.split('\t')[0])
man = json.load(open(os.path.join(ROOT, 'manifest.json')))
ids = [e['id'] for e in man if e['dat'] == 'SPCHDATA' and 11 <= int(e['path'].split('/')[1]) < 4500 and e['id'] not in done]
m = WhisperModel(MODEL, device='cpu', compute_type='int8', cpu_threads=4)
GAP = 1.0; SR = 16000

def load(i):
    with wave.open(os.path.join(ROOT, 'SPCHDATA', i + '.asf.wav')) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
    return np.interp(np.arange(0, len(x), 36000 / SR), np.arange(len(x)), x).astype(np.float32), len(x) / 36000

o = open(out, 'a', encoding='utf-8')
k = 0
while k < len(ids):
    buf = []; spans = []; t = 0.0
    while k < len(ids):
        a, sec = load(ids[k])
        if sec > 25: a = a[:25 * SR]
        if buf and t + len(a) / SR > 27: break
        spans.append((ids[k], t, t + len(a) / SR, sec)); buf += [a, np.zeros(int(GAP * SR), np.float32)]
        t += len(a) / SR + GAP; k += 1
    seg, _ = m.transcribe(np.concatenate(buf), beam_size=1, language='en', word_timestamps=True,
                          condition_on_previous_text=False, vad_filter=False)
    words = [w for s in seg for w in (s.words or [])]
    for i, a0, a1, sec in spans:
        txt = ''.join(w.word for w in words if a0 - 0.3 <= (w.start + w.end) / 2 <= a1 + 0.3).strip()
        o.write('%s\t%.3f\t%s\n' % (i, sec, txt))
    o.flush()
