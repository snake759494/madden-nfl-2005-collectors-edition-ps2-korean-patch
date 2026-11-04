"""번역문 -> edge-tts 한국어 음성 -> 36kHz mono s16, 원본 길이 이내로 맞춤.
사용: python dub_tts.py speech  (speech/ko.tsv: id<TAB>voice<TAB>한국어)  -> speech/ko/<id>.pcm"""
import os, sys, asyncio, subprocess, wave, json
import edge_tts, imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = sys.argv[1]; OUT = os.path.join(ROOT, 'ko'); os.makedirs(OUT, exist_ok=True)
VOICE = {'P': ('ko-KR-InJoonNeural', '+0Hz'), 'C': ('ko-KR-HyunsuMultilingualNeural', '-4Hz'),
         'R': ('ko-KR-InJoonNeural', '-12Hz'), 'S': ('ko-KR-SunHiNeural', '+0Hz')}

def dur(i):
    with wave.open(os.path.join(ROOT, 'SPCHDATA', i + '.asf.wav')) as w: return w.getnframes() / 36000

def to_pcm(mp3, target, dst):
    def conv(tempo):
        af = 'silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse'
        if tempo > 1.001: af += ',atempo=%.4f' % tempo
        return subprocess.run([FF, '-v', 'error', '-i', mp3, '-af', af, '-ac', '1', '-ar', '36000', '-f', 's16le', '-'],
                              capture_output=True, check=True).stdout
    pcm = conv(1.0); L = len(pcm) / 72000
    lim = target * 0.98
    if L > lim: pcm = conv(min(L / lim, 2.0))
    pcm = pcm[:int(lim * 36000) * 2]  # 그래도 길면 잘라냄(atempo 2.0 초과 시)
    open(dst, 'wb').write(pcm)

async def one(sem, i, v, text):
    dst = os.path.join(OUT, i + '.pcm')
    if os.path.exists(dst): return
    async with sem:
        mp3 = dst + '.mp3'; voice, pitch = VOICE[v]
        for t in range(5):
            try:
                await edge_tts.Communicate(text, voice, pitch=pitch, rate='+8%').save(mp3); break
            except Exception as e:
                await asyncio.sleep(3 + 5 * t)
        else:
            print('FAIL', i, file=sys.stderr); return
        await asyncio.to_thread(to_pcm, mp3, dur(i), dst); os.remove(mp3)

async def main():
    rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'ko.tsv'), encoding='utf-8') if l.strip()]
    sem = asyncio.Semaphore(8)
    await asyncio.gather(*(one(sem, i, v, t) for i, v, t in rows if t and t != '-'))
asyncio.run(main())
