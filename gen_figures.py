"""Static figures for a README or a writeup.

Only the three claims that cannot be checked by reading: where each recovered
block physically sits, what the puzzle actually is, and the Morse row beneath
the die. Plain SVG so they stay crisp and diff-able.
"""
import collections
import json
import math
import os

import klayout.db as db

from recovered import MESSAGE, region_grid

INK = "#12151a"
DIM = "#12151a"
LINE = "#ccd2dd"
SURF = "#fbfcfd"
ACCENT = "#2a78d6"
STAR = "#eb6834"
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

ORDER = ["cell counter (mod 11)", "row counter", "input delay line", "adjacency check",
         "row accumulator", "column accumulators", "region accumulators",
         "total-star counter", "success latch", "output generator"]


def floorplan(out="figures/floorplan.svg", cols=5, pw=104, gap=16):
    bl = json.load(open("blocks.json"))
    die = bl["die"]
    by_block = collections.defaultdict(list)
    for c in bl["cells"]:
        by_block[c["block"]].append(c)
    allc = bl["cells"]

    scale = pw / die["w"]
    ph = die["h"] * scale
    rows = (len(ORDER) + cols - 1) // cols
    lab = 34
    W = cols * pw + (cols + 1) * gap
    H = rows * (ph + lab) + (rows + 1) * gap + 26

    def sub(c):
        """one cell as path data, which is far more compact than a <rect>"""
        x = (c["x"] - die["x"]) * scale
        y = ph - (c["y"] - die["y"] + c["h"]) * scale
        return "M%.1f %.1fh%.1fv%.1fh%.1fz" % (
            x, y, max(c["w"] * scale, 0.6), max(c["h"] * scale, 0.6),
            -max(c["w"] * scale, 0.6))

    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
         'viewBox="0 0 %d %d" font-family="%s">' % (W, H, W, H, FONT)]
    s.append('<rect width="%d" height="%d" fill="%s"/>' % (W, H, SURF))
    s.append('<defs><path id="ctx" fill="%s" d="%s"/></defs>'
             % (LINE, "".join(sub(c) for c in allc)))
    s.append('<text x="%d" y="18" font-size="11" fill="%s">every gate placed by probing '
             'the net at its output pin &#183; die 200 &#215; 353 &#181;m</text>' % (gap, DIM))
    for i, name in enumerate(ORDER):
        r, c = divmod(i, cols)
        ox = gap + c * (pw + gap)
        oy = 26 + gap + r * (ph + lab + gap)
        s.append('<g transform="translate(%.1f,%.1f)">' % (ox, oy))
        s.append('<rect x="-1" y="-1" width="%.1f" height="%.1f" fill="none" stroke="%s"/>'
                 % (pw + 2, ph + 2, LINE))
        s.append('<use href="#ctx"/>')
        s.append('<path fill="%s" d="%s"/>'
                 % (ACCENT, "".join(sub(c) for c in by_block.get(name, []))))
        short = name.replace(" (mod 11)", "")
        s.append('<text x="0" y="%.1f" font-size="9" fill="%s">%s</text>'
                 % (ph + 13, INK, short))
        s.append('<text x="0" y="%.1f" font-size="8" fill="%s">%d cells</text>'
                 % (ph + 24, DIM, len(by_block.get(name, []))))
        s.append('</g>')
    s.append('</svg>')
    write(out, "\n".join(s))


def puzzle(out="figures/puzzle.svg", S=30):
    grid = region_grid()
    bits = [int(c) for c in open("solution_bits.txt").read().strip()]
    P, N = 14, 11
    W = H = N * S + 2 * P
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
         'viewBox="0 0 %d %d" font-family="%s">' % (W, H, W, H, FONT)]
    s.append('<rect width="%d" height="%d" fill="%s"/>' % (W, H, SURF))
    for r in range(N):
        for c in range(N):
            s.append('<rect x="%d" y="%d" width="%d" height="%d" fill="%s" stroke="%s" '
                     'stroke-width="0.5"/>' % (P + c * S, P + r * S, S, S, SURF, LINE))
    for r in range(N):
        for c in range(N):
            if bits[r * N + c]:
                cx, cy = P + c * S + S / 2, P + r * S + S / 2
                pts = []
                for i in range(10):
                    a = -math.pi / 2 + i * math.pi / 5
                    rad = S * 0.30 if i % 2 == 0 else S * 0.125
                    pts.append("%.2f,%.2f" % (cx + rad * math.cos(a), cy + rad * math.sin(a)))
                s.append('<polygon points="%s" fill="%s"/>' % (" ".join(pts), STAR))
    for r in range(N + 1):
        for c in range(N + 1):
            if c < N and (r == 0 or r == N or grid[r - 1][c] != grid[r][c]):
                s.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="2.2"/>'
                         % (P + c * S, P + r * S, P + (c + 1) * S, P + r * S, INK))
            if r < N and (c == 0 or c == N or grid[r][c - 1] != grid[r][c]):
                s.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="2.2"/>'
                         % (P + c * S, P + r * S, P + c * S, P + (r + 1) * S, INK))
    s.append('</svg>')
    write(out, "\n".join(s))


def morse(out="figures/morse.svg", scale=6.0, h=26):
    ly = db.Layout()
    ly.read("puzzle.gds")
    top = ly.top_cell()
    marks = sorted((i.bbox().left * ly.dbu, i.bbox().width() * ly.dbu)
                   for i in top.each_inst() if i.bbox().top * ly.dbu < 0.01)
    P = 14
    W = int(200 * scale) + 2 * P
    H = h + 62
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
         'viewBox="0 0 %d %d" font-family="%s">' % (W, H, W, H, FONT)]
    s.append('<rect width="%d" height="%d" fill="%s"/>' % (W, H, SURF))
    s.append('<text x="%d" y="16" font-size="11" fill="%s">36 placeholder cells in one row '
             'beneath the cell array, in two widths</text>' % (P, DIM))
    for x, w in marks:
        s.append('<rect x="%.2f" y="26" width="%.2f" height="%d" fill="%s"/>'
                 % (P + x * scale, w * scale, h, INK))
    s.append('<text x="%d" y="%d" font-size="15" fill="%s" letter-spacing="2" '
             'font-family="%s">PER ARENAM AD ASTRA</text>' % (P, h + 52, STAR, MONO))
    s.append('</svg>')
    write(out, "\n".join(s))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(text)
    print("  %-28s %5.1f KB" % (path, len(text) / 1024))


if __name__ == "__main__":
    print("message: %r" % MESSAGE)
    floorplan()
    puzzle()
    morse()
