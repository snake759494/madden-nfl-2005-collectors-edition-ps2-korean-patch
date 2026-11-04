"""SFN(FNTS) 폰트에 한글 글리프 추가

글리프 표는 16비트 코드 오름차순(엔진이 이진 탐색), 원래 0x20~ 글자는 앞쪽 그대로 둔다.
텍스처는 4bpp(값 0~15 = 농도), 원본 그림은 좌상단에 그대로 두고 아래쪽(필요하면 오른쪽)에 한글을 채운다.
"""
import struct, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import sfn as sfnmod

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def code_of(idx):
    """한글 글자 번호 -> 2바이트 코드 (선행 0x81~0x9F, 후행 0x80~0xBF)"""
    assert idx < 31 * 64
    return ((0x81 + idx // 64) << 8) | (0x80 + idx % 64)


def render_glyph(font, ch, cell_h, base, thr=0):
    """ch 를 그려 (농도 배열 0~15, x 시작, 폭)"""
    W = cell_h * 3
    im = Image.new('L', (W, cell_h + 8), 0)
    d = ImageDraw.Draw(im)
    d.text((cell_h // 2, base + 4), ch, font=font, fill=255, anchor='ls')
    a = np.array(im)
    a = a[4:4 + cell_h]
    cols = np.where(a.max(0) > thr)[0]
    if len(cols) == 0:
        return np.zeros((cell_h, 1), np.uint8), 0
    x0, x1 = cols[0], cols[-1] + 1
    g = a[:, x0:x1]
    g = np.clip((g.astype(np.int32) * 15 + 127) // 255, 0, 15).astype(np.uint8)
    return g, x0 - cell_h // 2


def stylize(g, style):
    if style == 'bin':
        return np.where(g >= 7, 15, 0).astype(np.uint8)
    if style == 'comic':
        b = g >= 7
        h, w = g.shape
        o = np.zeros((h, w + 1), np.uint8)
        sh = np.zeros_like(o); sh[1:, 1:] = b[:-1, :]
        o[sh] = 1
        o[:, :w][b] = 9
        return o
    return g


def build(raw, chars, ttf, px, cell_top, cell_h, base, spacing=1, tex_w=None, xshift=0, style=None):
    """raw: 원본 SFN, chars: 한글 문자 목록(코드 순서 = 목록 순서 인덱스는 code_map 사용)
    cell_top: 글리프 상단의 yo, cell_h: 셀 높이, base: 셀 안 기준선 위치"""
    f = sfnmod.SFN(raw)
    font = ImageFont.truetype(ttf, px)
    rend = []
    for idx, ch in chars:
        g, xo = render_glyph(font, ch, cell_h, base)
        g = stylize(g, style)
        rend.append((code_of(idx), g, xo))
    W = tex_w or f.tw
    if W < f.tw: W = f.tw
    if tex_w is None:   # 높이 1024 이하가 되도록 폭 자동 확장
        area = sum((g.shape[1] + 1) * (cell_h + 1) for _, g, _ in rend)
        while W < 512 and f.th + area * 1.15 / W > 1000: W *= 2
    # 배치: 원본 아래에 줄 단위로
    x = 0; y = f.th + 1; rowh = cell_h + 1
    place = []
    for code, g, xo in rend:
        w = g.shape[1]
        if x + w + 1 > W:
            x = 0; y += rowh
        place.append((code, x, y, g, xo)); x += w + 1
    H = y + rowh
    H = (H + 3) & ~3
    img = np.zeros((H, W), np.uint8)
    img[:f.th, :f.tw] = f.img
    glyphs = [list(g) for g in f.glyphs]
    for code, gx, gy, g, xo in place:
        h, w = g.shape
        img[gy:gy + h, gx:gx + w] = g
        adv = w + spacing + max(0, xo) + xshift
        glyphs.append([code, w, h, gx, gy, adv, max(0, xo) + xshift, cell_top, 0])
    glyphs.sort(key=lambda g: g[0])
    return pack(f, glyphs, img), img


def pack(f, glyphs, img):
    H, W = img.shape
    n = len(glyphs)
    out = bytearray(f.hdr)
    gt = bytearray()
    for c, w, h, u, v, adv, xo, yo, pad in glyphs:
        gt += struct.pack('<HBBHHbbbB', c, w, h, u, v, adv, xo, yo, pad)
    name = f.extra
    toff = 0x20 + len(gt) + len(name)
    if toff % 16:
        name = name + bytes(16 - toff % 16); toff = 0x20 + len(gt) + len(name)
    flat = img.reshape(-1)
    px = (flat[0::2] | (flat[1::2] << 4)).astype(np.uint8).tobytes()
    tex = struct.pack('<IHH', 1, W, H) + f.thdr[8:16] + px
    body = bytes(out[:0x20]) + gt + name + tex + f.tail
    koff = 0
    if f.kern:
        koff = len(body)
        body += f.kern
    body = bytearray(body)
    struct.pack_into('<H', body, 0xa, n)
    struct.pack_into('<III', body, 0x14, 0x20, koff, toff)
    tex_end = toff + len(tex)
    struct.pack_into('<I', body, 4, tex_end - len(name))
    return bytes(body)
