import capstone,struct
import os
D=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','x','SLUS_210.25'),'rb').read()
def rd(va,n): return D[va-0x100000+0x1000:va-0x100000+0x1000+n]
md=capstone.Cs(capstone.CS_ARCH_MIPS,capstone.CS_MODE_MIPS64|capstone.CS_MODE_LITTLE_ENDIAN)
def dis(va,n):
    for i in md.disasm(rd(va,n*4),va): print(hex(i.address),i.mnemonic,i.op_str)
def words():
    for o in range(0x1000,0x1000+0x66a780,4):
        yield o-0x1000+0x100000,struct.unpack_from('<I',D,o)[0]
def ins_at(va):
    r=list(md.disasm(rd(va,4),va))
    return r[0] if r else None
def scan(a,b):
    out=[]
    for va in range(a,b,4):
        i=ins_at(va)
        if i: out.append(i)
    return out
