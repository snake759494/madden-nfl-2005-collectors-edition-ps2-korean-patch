"""묶음(최상위 TERF 항목)별 화자 추정: 로그 멜 평균 + 피치로 k-means."""
import json,wave,numpy as np,collections,sys
man=json.load(open('manifest.json'))
G=collections.OrderedDict()
for e in man:
  g=int(e['path'].split('/')[1])
  if e['dat']=='SPCHDATA' and 11<=g<4500: G.setdefault(g,[]).append(e['id'])
def feat(i):
  w=wave.open('SPCHDATA/%s.asf.wav'%i);x=np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(float)
  if len(x)<4096: return None
  fr=np.lib.stride_tricks.sliding_window_view(x,1024)[::512]*np.hanning(1024)
  S=np.abs(np.fft.rfft(fr))**2;e=S.sum(1);S=S[e>np.percentile(e,50)]
  edges=np.geomspace(2,512,25).astype(int)
  m=np.log(np.array([S[:,a:b].sum(1) for a,b in zip(edges[:-1],edges[1:])]).T+1)
  if len(m)==0: return None
  m=m.mean(0);return m-m.mean()
F={};K=[]
for g,ids in G.items():
  fs=[f for f in (feat(i) for i in ids[:6]) if f is not None]
  if fs: F[g]=np.mean(fs,0);K.append(g)
X=np.array([F[g] for g in K])
from numpy.random import default_rng
rng=default_rng(0);best=None
for t in range(10):
  C=X[rng.choice(len(X),4,replace=False)]
  for it in range(50):
    L=((X[:,None]-C[None])**2).sum(2).argmin(1);C=np.array([X[L==k].mean(0) if (L==k).any() else C[k] for k in range(4)])
  sc=((X-C[L])**2).sum()
  if best is None or sc<best[0]: best=(sc,L)
L=best[1];json.dump({str(g):int(l) for g,l in zip(K,L)},open('spk.json','w'))
print(collections.Counter(L.tolist()))
