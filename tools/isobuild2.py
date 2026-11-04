"""DVD9(2층) ISO 빌드: 레이어 0 끝에 수정 파일을 덧붙이고 레이어 1을 그만큼 뒤로 민다.

원본: 레이어 0 볼륨 = [0, L0) (PVD 크기), 마지막 섹터 L0-1 은 UDF 앵커.
레이어 1 기준 섹터 = L0-16 (레이어 1 PVD 는 L0 위치). 레이어 1 내부 LBA 는 상대값이라 그대로.
PCSX2 는 이미지 가운데부터 16섹터 단위로 레이어 1 PVD 를 찾으므로 N 은 16의 배수로 한다.
제자리에 들어가는 파일은 원래 위치에 덮어쓴다.
"""
import os, struct, shutil
import isofs, udf
SEC = 2048
CHUNK = 64 << 20

def build(src, dst, files, log=print):
    fs = open(src, 'rb')
    ents = {e[0]: e for e in isofs.walk(fs)}
    fs.seek(16 * SEC); pvd = bytearray(fs.read(SEC))
    L0 = struct.unpack_from('<I', pvd, 80)[0]
    total = os.path.getsize(src) // SEC
    # 배치
    newdata = bytearray(); place = {}
    for name, data in files.items():
        _, lba, size, roff = ents[name]
        if (len(data) + SEC - 1) // SEC <= (size + SEC - 1) // SEC:
            place[name] = lba
        else:
            place[name] = L0 + len(newdata) // SEC
            newdata += data + bytes(-len(data) % SEC)
    need = len(newdata) // SEC + 1          # + 새 앵커
    N = (need + 15) // 16 * 16
    newL0 = L0 + N
    fd = open(dst, 'wb')
    # 1) 레이어 0 원본 [0, L0-1)
    copy(fs, fd, 0, L0 - 1)
    fd.write(bytes(SEC))                      # 옛 앵커 자리
    fd.write(newdata); fd.write(bytes((N - 1) * SEC - len(newdata)))
    fs.seek((L0 - 1) * SEC); fd.write(fs.read(SEC))   # 앵커(내용은 아래에서 다시 씀)
    # 2) 레이어 1 [L0, total)
    copy(fs, fd, L0, total)
    fd.close(); fs.close()
    # 3) 파일 기록 + 디렉터리/UDF 갱신
    f = open(dst, 'r+b')
    u = udf.UDF(f)
    for name, data in files.items():
        _, lba, size, roff = ents[name]; pos = place[name]
        f.seek(pos * SEC); f.write(data + bytes(-len(data) % SEC))
        f.seek(roff); rec = bytearray(f.read(34))
        struct.pack_into('<I', rec, 2, pos); struct.pack_into('>I', rec, 6, pos)
        struct.pack_into('<I', rec, 10, len(data)); struct.pack_into('>I', rec, 14, len(data))
        f.seek(roff); f.write(rec)
        u.set_file('/' + name, pos, len(data))
        log(f'  {name}: {size} -> {len(data)} @ {pos}{" (moved)" if pos != lba else ""}')
    struct.pack_into('<I', pvd, 80, newL0); struct.pack_into('>I', pvd, 84, newL0)
    f.seek(16 * SEC); f.write(pvd)
    u.grow(newL0)          # 파티션 길이 + 앵커(newL0-1)
    f.close()
    return N

def copy(fs, fd, a, b):
    fs.seek(a * SEC); n = (b - a) * SEC
    while n > 0:
        c = fs.read(min(CHUNK, n)); fd.write(c); n -= len(c)
