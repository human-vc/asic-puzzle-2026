"""Animated trace of the accepted grid streaming through the recovered chip.

Every frame is read out of the gate-level model in sim.py, not drawn from a
script: the twelve window cells are the twelve delay-line flops, the star count
is the total counter, and the verdict is the `success` net. The grid and the tap
strip show the same twelve bits in the two shapes the design gives them.
"""
import os

from PIL import Image, ImageDraw, ImageFont

from recovered import DELAY_LINE, TOTAL_COUNTER, N, region_grid
from sim import Design, BitBackend

INK = (18, 21, 26)
DIM = INK
LINE = (204, 210, 221)
SURF = (251, 252, 253)
ACCENT = (42, 120, 214)
STAR = (235, 104, 52)
WINDOW = (232, 241, 251)
COMPARE = (203, 224, 248)
WHITE = (255, 255, 255)

W, H = 680, 424
CELL = 26
GX, GY = 28, 52
PANEL = 356
TAPY = 366

SANS = ["/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf"]
FONTS = ["/System/Library/Fonts/Menlo.ttc",
         "/System/Library/Fonts/SFNSMono.ttf",
         "/Library/Fonts/Menlo.ttc"]


def font(size, paths=None):
    for path in (paths or FONTS):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


SCALE = 2

F11 = font(11 * SCALE, SANS)
F12 = font(12 * SCALE, SANS)
F13 = font(13 * SCALE, SANS)
F12M = font(12 * SCALE)


class Scaled:
    """ImageDraw proxy that multiplies coordinates and stroke widths by SCALE"""

    def __init__(self, g, s):
        self.g, self.s = g, s

    def _xy(self, xy):
        if isinstance(xy[0], (tuple, list)):
            return [(x * self.s, y * self.s) for x, y in xy]
        return [v * self.s for v in xy]

    def _kw(self, kw):
        if "width" in kw:
            kw = dict(kw, width=kw["width"] * self.s)
        return kw

    def rectangle(self, xy, **kw):
        self.g.rectangle(self._xy(xy), **self._kw(kw))

    def line(self, xy, **kw):
        self.g.line(self._xy(xy), **self._kw(kw))

    def polygon(self, xy, **kw):
        self.g.polygon(self._xy(xy), **kw)

    def text(self, xy, *a, **kw):
        self.g.text(self._xy(xy), *a, **kw)


def star_points(cx, cy, r):
    import math
    pts = []
    for k in range(10):
        rad = r if k % 2 == 0 else r * 0.42
        a = -math.pi / 2 + k * math.pi / 5
        pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    return pts


def neighbours(idx):
    r, c = divmod(idx, N)
    out = []
    for dr, dc in ((0, -1), (-1, -1), (-1, 0), (-1, 1)):
        rr, cc = r + dr, c + dc
        if 0 <= rr < N and 0 <= cc < N:
            out.append(rr * N + cc)
    return out


def run(bits, tail):
    d = Design("puzzle_net.json")
    be = BitBackend(1)
    order = [f[1] for f in d.flops]
    st = d.new_state(be)
    for _ in range(2):
        d.cycle(be, st, {"rst_n": be.zero, "enable": be.zero, "I": be.zero})

    frames = []
    for c in range(len(bits) + tail):
        bit = bits[c] if c < len(bits) else 0
        inp = {"rst_n": be.one, "enable": be.one,
               "I": (be.one if bit else be.zero), "clk": be.zero}
        v = d.eval_at(be, st, inp)
        frames.append({
            "cyc": c,
            "bit": bit,
            "live": c < len(bits),
            "taps": [st[order[f]] & 1 for f in DELAY_LINE],
            "stars": sum(w for f, w in TOTAL_COUNTER if st[order[f]] & 1),
            "success": v["net:success"] & 1,
        })
        d.cycle(be, st, {"rst_n": be.one, "enable": be.one,
                         "I": (be.one if bit else be.zero)})
    return frames


def draw(fr, bits, regions):
    img = Image.new("RGB", (W * SCALE, H * SCALE), SURF)
    g = Scaled(ImageDraw.Draw(img), SCALE)

    cyc, live = fr["cyc"], fr["live"]
    cur = cyc if live else None
    window = [] if cur is None else [cur - k - 1 for k in range(12) if cur - k - 1 >= 0]
    comp = [] if cur is None else [n for n in neighbours(cur) if n in window]

    g.text((GX, 20), "121 cells in, one at a time", font=F13, fill=INK)

    for i in range(N * N):
        r, c = divmod(i, N)
        x, y = GX + c * CELL, GY + r * CELL
        fill = WHITE
        if i in comp:
            fill = COMPARE
        elif i in window:
            fill = WINDOW
        g.rectangle([x, y, x + CELL, y + CELL], fill=fill, outline=LINE)
        if i < cyc and bits[i]:
            g.polygon(star_points(x + CELL / 2, y + CELL / 2, 8), fill=STAR)

    for r in range(N):
        for c in range(N):
            x, y = GX + c * CELL, GY + r * CELL
            if c + 1 < N and regions[r][c] != regions[r][c + 1]:
                g.line([x + CELL, y, x + CELL, y + CELL], fill=INK, width=2)
            if r + 1 < N and regions[r][c] != regions[r + 1][c]:
                g.line([x, y + CELL, x + CELL, y + CELL], fill=INK, width=2)
    g.rectangle([GX, GY, GX + N * CELL, GY + N * CELL], outline=INK, width=2)

    if cur is not None:
        r, c = divmod(cur, N)
        x, y = GX + c * CELL, GY + r * CELL
        g.rectangle([x, y, x + CELL, y + CELL], outline=ACCENT, width=3)

    px, py = PANEL, GY + 4
    rows = [("cycle", "%d" % cyc)]
    if live:
        rows.append(("row, col", "%d, %d" % divmod(cyc, N)))
        rows.append(("bit in", "1" if fr["bit"] else "."))
    else:
        rows.append(("row, col", "stream done"))
        rows.append(("bit in", "."))
    rows.append(("stars so far", "%d" % fr["stars"]))
    rows.append(("success", "%d" % fr["success"]))
    for k, (a, b) in enumerate(rows):
        y = py + k * 22
        g.text((px, y), a, font=F12, fill=DIM)
        colour = ACCENT if (a == "success" and fr["success"]) else INK
        g.text((px + 108, y), b, font=F12M, fill=colour)

    ly = py + len(rows) * 22 + 18
    legend = [(COMPARE, "the four earlier neighbours"),
              (WINDOW, "the rest of the 12-cell window"),
              (WHITE, "not yet read")]
    for k, (col, label) in enumerate(legend):
        y = ly + k * 20
        g.rectangle([px, y, px + 13, y + 13], fill=col, outline=LINE)
        g.text((px + 21, y + 1), label, font=F11, fill=DIM)
    y = ly + len(legend) * 20
    g.rectangle([px, y, px + 13, y + 13], fill=WHITE, outline=ACCENT, width=2)
    g.text((px + 21, y + 1), "arriving cell", font=F11, fill=DIM)

    g.text((GX, TAPY - 18), "delay line", font=F11, fill=DIM)
    for t in range(12):
        x = GX + t * 24
        held = fr["taps"][t]
        pos = None if cur is None else cur - t - 1
        fill = WHITE
        if held:
            fill = STAR
        elif pos is not None and pos in comp:
            fill = COMPARE
        elif pos is not None and pos >= 0:
            fill = WINDOW
        outline = ACCENT if (pos is not None and pos in comp) else LINE
        g.rectangle([x, TAPY, x + 18, TAPY + 18], fill=fill, outline=outline)
    g.text((GX + 12 * 24 + 12, TAPY + 3), "tap 1 is to the left, taps 10-12 the row above",
           font=F11, fill=DIM)

    return img


def main():
    bits = [int(c) for c in open("solution_bits.txt").read().strip()]
    regions = region_grid()
    frames = run(bits, tail=6)

    imgs, durs = [], []
    for fr in frames:
        imgs.append(draw(fr, bits, regions))
        durs.append(700 if not fr["live"] else 70)
    durs[-1] = 1600

    os.makedirs("figures", exist_ok=True)
    out = "figures/streaming.gif"
    pal = [im.convert("P", palette=Image.ADAPTIVE, colors=64) for im in imgs]
    pal[0].save(out, save_all=True, append_images=pal[1:],
                duration=durs, loop=0, optimize=True)
    print("wrote %s: %d frames, %.1f s, %d KB"
          % (out, len(pal), sum(durs) / 1000.0, os.path.getsize(out) // 1024))


if __name__ == "__main__":
    main()
