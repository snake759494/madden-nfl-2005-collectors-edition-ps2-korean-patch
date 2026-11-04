"""tr/out_*.tsv -> ko.tsv (군집1=아나운서 목소리는 R로 통일)"""
import glob
inp={};o=[]
for f in sorted(glob.glob('tr/in_*.tsv')):
  for l in open(f,encoding='utf-8'): r=l.rstrip('\n').split('\t');inp[r[0]]=r
for f in sorted(glob.glob('tr/out_*.tsv')):
  for l in open(f,encoding='utf-8'):
    r=l.rstrip('\n').split('\t')
    if len(r)!=3: continue
    i,s,t=r
    if inp.get(i,[0]*4)[3]=='1': s='R'
    if s not in 'PCRS' or not s: s='P'
    o.append('\t'.join([i,s,t.strip()]))
open('ko.tsv','w',encoding='utf-8').write('\n'.join(o)+'\n');print(len(o),sum(1 for x in o if x.endswith('\t-')))
