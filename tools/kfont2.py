"""FNTS 폰트에 한글 글리프 추가 (글리프마다 잉크 영역만 잘라 배치)

글리프 레코드 <HBBHHbbbB>: 코드, 폭, 높이, u, v, 진행폭, x오프셋, y오프셋(줄 위 기준), 0
텍스처 4bpp(0~15 농도). 원본 그림은 그대로 두고 아래쪽에 한글을 채운다.
"""
import struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import sfn as sfnmod

def code_of(idx):
    return ((0xE0 + idx // 128) << 8) | (0x80 + idx % 128)

def metrics(f):
    G = {g[0]: g for g in f.glyphs}
    caps = [G[c] for c in b'HEIMNT' if c in G]
    top = min(g[7] for g in caps); bot = max(g[7] + g[2] for g in caps)
    return top, bot   # 대문자 윗선/기준선(줄 위 기준)

def render(font, ch, size_px):
    W = size_px * 3
    im = Image.new('L', (W, W), 0)
    ImageDraw.Draw(im).text((size_px, size_px * 2), ch, font=font, fill=255, anchor='ls')
    a = np.array(im)
    ys = np.where(a.max(1) > 20)[0]; xs = np.where(a.max(0) > 20)[0]
    if len(xs) == 0: return None
    g = a[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1]
    return np.clip((g.astype(np.int32) * 15 + 127) // 255, 0, 15).astype(np.uint8), xs[0] - size_px, ys[0] - size_px * 2

def build(raw, chars, ttf, scale=1.12, maxh=None, spacing=1, gamma=None, layered=True):
    """chars: [(idx, ch)]. 한글 높이 = 대문자 높이*scale (maxh 로 제한)"""
    f = sfnmod.SFN(raw)
    top, base = metrics(f)
    cap = base - top
    target = cap * scale
    if maxh: target = min(target, maxh)
    font = ImageFont.truetype(ttf, 64)
    # '한' 잉크 높이로 px 결정
    r = render(font, '한', 64); px = max(6, int(round(64 * target / r[0].shape[0])))
    font = ImageFont.truetype(ttf, px)
    # 기준선: 한글 잉크 가운데가 대문자 가운데에 오도록
    mid = (top + base) / 2
    ref = render(font, '한', px); refmid = ref[2] + ref[0].shape[0] / 2   # 기준선 대비 위치(음수)
    baseline_line = mid - refmid
    rend = []
    for idx, ch in chars:
        r = render(font, ch, px)
        if r is None: continue
        g, xo, yo = r
        if gamma: g = np.clip(np.round(15 * (g / 15.0) ** gamma), 0, 15).astype(np.uint8)
        rend.append((code_of(idx), g, max(0, xo), int(round(baseline_line + yo))))
    # 레이어: 한글은 2비트로 줄여 두 벌로 나눠 같은 자리에 겹친다(하위 2비트=1, 상위 2비트=2). fontlayer.py 참고
    sets = [rend[0::2], rend[1::2]] if layered else [rend]
    def shelf(W):
        """선반 배치: 원래 그림 오른쪽 띠(x>=tw, y<th)를 먼저 채우고 그 아래는 전체 폭으로"""
        place = []; H = 0
        for li, s in enumerate(sets):
            x0 = f.tw + 1 if W > f.tw + 1 else 0
            x = x0; y = 0 if x0 else f.th + 1; rowh = 0
            for code, g, xo, yo in s:
                h, w = g.shape
                if x + w + 1 > W:
                    x = x0; y += rowh + 1; rowh = 0
                if x0 and y + h + 1 > f.th:          # 띠가 찼으면 원래 그림 아래로
                    x0 = 0; x = 0; y = f.th + 1; rowh = 0
                place.append((code, x, y, g, xo, yo, li + 1 if layered else 0)); x += w + 1; rowh = max(rowh, h)
            H = max(H, y + rowh + 1, f.th)
        return place, (H + 7) & ~7
    # VRAM 은 2의 거듭제곱 폭 x 높이로 잡히는 것으로 보인다(실측). 그 크기가 가장 작은 폭을 고른다
    best = None
    for W in (128, 256, 512, 1024):
        if W < f.tw: continue
        place, H = shelf(W)
        if H > 1024: continue
        key = (W * H, W)
        if best is None or key < best[0]: best = (key, W, H, place)
    _, W, H, place = best
    img = np.zeros((H, W), np.uint8); img[:f.th, :f.tw] = f.img
    glyphs = [list(g) for g in f.glyphs]
    adv_extra = spacing
    for code, gx, gy, g, xo, yo, layer in place:
        h, w = g.shape
        if layer:
            q = ((g.astype(np.int32) * 3 + 7) // 15).astype(np.uint8)   # 0..15 -> 0..3
            img[gy:gy + h, gx:gx + w] |= q << (2 * (layer - 1))
        else:
            img[gy:gy + h, gx:gx + w] = g
        glyphs.append([code, w, h, gx, gy, min(127, w + xo + adv_extra), xo, yo, layer])
    glyphs.sort(key=lambda g: g[0])
    return pack(f, glyphs, img), img

def pack(f, glyphs, img):
    H, W = img.shape
    gt = b''.join(struct.pack('<HBBHHbbbB', *g) for g in glyphs)
    name = f.extra
    toff = 0x20 + len(gt) + len(name)
    if toff % 16: name = name + bytes(16 - toff % 16); toff = 0x20 + len(gt) + len(name)
    flat = img.reshape(-1)
    px = (flat[0::2] | (flat[1::2] << 4)).astype(np.uint8).tobytes()
    tex = struct.pack('<IHH', f.ttype, W, H) + f.thdr[8:16] + px
    body = bytearray(f.hdr[:0x20]) + gt + name + tex + f.tail
    tex_end = len(body)
    koff = 0
    if f.kern:
        while len(body) % 16: body.append(0)
        koff = len(body); body += f.kern
    struct.pack_into('<H', body, 0xa, len(glyphs))
    struct.pack_into('<III', body, 0x14, 0x20, koff, toff)
    struct.pack_into('<I', body, 4, tex_end - 0x14)
    return bytes(body)
