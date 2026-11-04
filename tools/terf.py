import struct
def parse(d):
    """TERF -> dict(entries=[(off,size,ctype,usize)], chunks)"""
    assert d[:4]==b'TERF'
    p=struct.unpack_from('<I',d,4)[0];ch={}
    order=[]
    while p+8<=len(d):
        tag=d[p:p+4].decode('latin1');ln=struct.unpack_from('<I',d,p+4)[0]
        if not tag.isalnum() or ln==0: break
        ch[tag]=(p,ln);order.append(tag)
        if tag=='DATA': break
        p+=ln
    return ch,order
def entries(d):
    ch,_=parse(d)
    p,ln=ch['DIR1'];w=struct.unpack_from('<%dI'%((ln-8)//4),d,p+8)
    base=ch['DATA'][0]
    E=[[base+w[i],w[i+1],0,w[i+1]] for i in range(0,len(w)-1,2)]
    if 'COMP' in ch:
        p,ln=ch['COMP'];c=struct.unpack_from('<%dI'%((ln-8)//4),d,p+8)
        for i,e in enumerate(E): e[2],e[3]=c[2*i],c[2*i+1]
    return E

def rebuild(d, repl):
    """repl: {index: (bytes, ctype)} -> 새 TERF. 헤더/청크 순서 유지, 데이터는 정렬 규칙대로 다시 배치"""
    ch, _ = parse(d)
    align = struct.unpack_from('<H', d, 12)[0] or 1
    dp, _ = ch['DATA']
    E = entries(d)
    out = bytearray(d[:dp + 8])
    first = E[0][0] - dp if E else 8
    while len(out) < dp + first: out.append(0)
    newE = []
    for i, (o, s, c, u) in enumerate(E):
        if i in repl:
            b, c2 = repl[i][:2]; u2 = repl[i][2] if len(repl[i]) > 2 else len(b)
        else:
            b, c2, u2 = d[o:o + s], c, u
        while (len(out) - dp) % align: out.append(0)
        newE.append((len(out) - dp, len(b), c2, u2)); out += b
    tail_pad = (len(d) - (E[-1][0] + E[-1][1])) if E else 0
    while (len(out) - dp) % align: out.append(0)
    struct.pack_into('<I', out, dp + 4, len(out) - dp)
    p, ln = ch['DIR1']
    for i, (o, s, c, u) in enumerate(newE): struct.pack_into('<II', out, p + 8 + 8 * i, o, s)
    if 'COMP' in ch:
        p, ln = ch['COMP']
        for i, (o, s, c, u) in enumerate(newE): struct.pack_into('<II', out, p + 8 + 8 * i, c, u)
    return bytes(out)
