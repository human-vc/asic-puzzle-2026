"""Block diagram of the recovered machine, with every count read back from the
recovered structure rather than typed into the drawing.

The shape is the argument: one bit enters on the left, and by the time it has
crossed the page it has been folded into a handful of counters and a twelve-deep
window. Nothing on this page is wide enough to hold a grid.
"""
import collections
import json

import recovered as rec

INK = "#12151a"
DIM = "#767f90"
TEXT = "#12151a"
LINE = "#ccd2dd"
SURF = "#fbfcfd"
ACCENT = "#2a78d6"
FILL = "#eef4fc"
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

ADV = {FONT: 0.55, MONO: 0.60}


def fits(text, size, width, font=FONT):
    """guard against a label outgrowing its box, which is invisible until rendered"""
    need = len(text) * size * ADV[font]
    if need > width:
        raise SystemExit("label %r needs %.0fpx at %gpt but has %.0fpx"
                         % (text, need, size, width))
    return text

W, H = 740, 320
BOXH, STEP = 30, 38
C2, C2W = 148, 200
C3, C3W = 392, 300
IBUS, PBUS, VBUS = 132, 364, 716


def counts():
    blocks = json.load(open("blocks.json"))
    return collections.Counter(c["block"] for c in blocks["cells"])


def box(x, y, w, h, title, sub=None, note=None, accent=False, mono=False):
    pad = 11
    inner = w - 2 * pad
    face = MONO if mono else FONT
    lines = note if isinstance(note, (list, tuple)) else [note] if note else []
    need = 48 + 13 * (len(lines) - 1) + 6 if lines else (40 if sub else 22)
    if h < need:
        raise SystemExit("box %r is %gpx tall but needs %gpx for %d note line(s)"
                         % (title, h, need, len(lines)))
    ty = y + 19 if sub or lines else y + h / 2 + 4
    out = ['<rect x="%g" y="%g" width="%g" height="%g" rx="4" fill="%s" stroke="%s"/>'
           % (x, y, w, h, FILL if accent else "#ffffff", ACCENT if accent else LINE),
           '<text x="%g" y="%g" font-size="11.5" fill="%s"%s>%s</text>'
           % (x + pad, ty, INK, ' font-family="%s"' % MONO if mono else "",
              fits(title, 11.5, inner, face)),
           ]
    if sub:
        out.append('<text x="%g" y="%g" font-size="10" fill="%s">%s</text>'
                   % (x + pad, y + 34, TEXT, fits(sub, 10, inner)))
    for i, ln in enumerate(lines):
        out.append('<text x="%g" y="%g" font-size="9.5" fill="%s"%s>%s</text>'
                   % (x + pad, y + 48 + i * 13, TEXT,
                      ' font-family="%s"' % MONO if mono else "",
                      fits(ln, 9.5, inner, face)))
    return out


def line(x1, y1, x2, y2, head=False):
    return ['<path d="M%g %g L%g %g" stroke="%s" stroke-width="1.2" fill="none"%s/>'
            % (x1, y1, x2, y2, DIM, ' marker-end="url(#a)"' if head else "")]


def label(x, y, text, size=9.5, font=None):
    face = ' font-family="%s"' % font if font else ""
    return ['<text x="%g" y="%g" font-size="%g" fill="%s"%s>%s</text>'
            % (x, y, size, TEXT, face, text)]


def main(out="figures/datapath.svg"):
    n = counts()
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
         'viewBox="0 0 %d %d" font-family="%s">' % (W, H, W, H, FONT),
         '<rect width="%d" height="%d" fill="%s"/>' % (W, H, SURF),
         '<defs><marker id="a" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" '
         'markerHeight="6" orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="%s"/></marker>'
         '</defs>' % DIM,
         '<text x="24" y="28" font-size="12.5" fill="%s">'
         '121 bits into 92 flip-flops</text>' % INK]

    s += box(24, 52, 92, BOXH, "I", accent=True, mono=True)
    s += label(24, 100, "clk, enable, rst_n", 9, font=MONO)

    c2 = ["input delay line", "cell counter (mod 11)", "row counter", "run / done flag"]
    for i, name in enumerate(c2):
        s += box(C2, 52 + i * STEP, C2W, BOXH, name, accent=(i == 0))

    rules = ["adjacency check", "row accumulator", "column accumulators",
             "region accumulators", "total-star counter"]
    s += label(C3, 42, "five rules settled as they arrive", 10)
    for i, name in enumerate(rules):
        s += box(C3, 52 + i * STEP, C3W, BOXH, name)

    BOT = 52 + 5 * STEP + 24
    s += box(C3, BOT, C3W, BOXH, "success latch", accent=True)
    s += box(24, BOT, C3W, BOXH, "output generator")

    def cy(i):
        return 52 + i * STEP + BOXH / 2

    POSY = 52 + 4 * STEP + 14
    s += line(116, cy(0), IBUS, cy(0))
    s += line(IBUS, cy(0), IBUS, POSY)
    for i in range(3):
        s += line(IBUS, cy(i), C2, cy(i), head=True)
    s += line(IBUS, POSY, PBUS, POSY)
    s += line(PBUS, cy(1), PBUS, POSY)
    s.append('<circle cx="%g" cy="%g" r="3" fill="%s"/>' % (PBUS, POSY, DIM))
    s += label(IBUS + 10, POSY - 6, "the bit and its position", 9)
    for i in (1, 2):
        s += line(C2 + C2W, cy(i), PBUS, cy(i))
    for i in range(1, 5):
        s += line(PBUS, cy(i), C3, cy(i), head=True)
    s += line(C2 + C2W, cy(0), C3, cy(0), head=True)
    s += label(C2 + C2W + 6, cy(0) - 6, "taps", 9)

    for i in range(5):
        s += line(C3 + C3W, cy(i), VBUS, cy(i))
    s += line(VBUS, cy(0), VBUS, BOT + BOXH / 2)
    s += line(VBUS, BOT + BOXH / 2, C3 + C3W, BOT + BOXH / 2, head=True)
    s += line(C3, BOT + BOXH / 2, 24 + C3W, BOT + BOXH / 2, head=True)
    s += label(340, BOT + BOXH / 2 - 6, "start", 9)

    s.append('</svg>')
    open(out, "w").write("\n".join(s))
    print("wrote %s: %.1f KB" % (out, len(open(out).read()) / 1024))


if __name__ == "__main__":
    main()
