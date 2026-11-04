"""asr.tsv -> 번역용 청크(tr/in_NNN.tsv: id, sec, 묶음, 화자군집, 영어). 이미 만든 청크는 건너뜀."""
import json,os,sys
N=int(sys.argv[1]) if len(sys.argv)>1 else 1500
man={e['id']:e for e in json.load(open('manifest.json'))};spk=json.load(open('spk.json'))
rows=[l.rstrip('\n').split('\t') for l in open('asr.tsv',encoding='utf-8')]
rows.sort(key=lambda r:r[0])
have=sorted(f for f in os.listdir('tr') if f.startswith('in_'))
start=sum(sum(1 for _ in open('tr/'+f,encoding='utf-8')) for f in have)
k=len(have)
while start+N<=len(rows) or (len(sys.argv)>2 and start<len(rows)):
  with open('tr/in_%03d.tsv'%k,'w',encoding='utf-8') as o:
    for i,sec,t in rows[start:start+N]:
      g=man[i]['path'].split('/')[1];o.write('\t'.join([i,sec,g,str(spk.get(g,'?')),t])+'\n')
  start+=N;k+=1
print(k,'chunks',start)
