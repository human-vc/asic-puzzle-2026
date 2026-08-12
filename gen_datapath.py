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
LINE = "#ccd2dd"
SURF = "#fbfcfd"
ACCENT = "#2a78d6"
FILL = "#eef4fc"
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

W, H = 780, 486
C2, C2W = 148, 200
C3, C3W = 392, 300
IBUS, PBUS, VBUS = 132, 364, 716


def counts():
    blocks = json.load(open("blocks.json"))
    return collections.Counter(c["block"] for c in blocks["cells"])


def box(x, y, w, h, title, sub, note=None, accent=False):
    out = ['<rect x="%g" y="%g" width="%g" height="%g" rx="4" fill="%s" stroke="%s"/>'
           % (x, y, w, h, FILL if accent else "#ffffff", ACCENT if accent else LINE),
           '<text x="%g" y="%g" font-size="11.5" fill="%s">%s</text>'
           % (x + 11, y + 19, INK, title),
           '<text x="%g" y="%g" font-size="10" fill="%s">%s</text>'
           % (x + 11, y + 34, DIM, sub)]
    if note:
        out.append('<text x="%g" y="%g" font-size="9.5" fill="%s">%s</text>'
                   % (x + 11, y + 48, DIM, note))
    return out


def line(x1, y1, x2, y2, head=False):
    return ['<path d="M%g %g L%g %g" stroke="%s" stroke-width="1.2" fill="none"%s/>'
            % (x1, y1, x2, y2, DIM, ' marker-end="url(#a)"' if head else "")]


def label(x, y, text, size=9.5):
    return ['<text x="%g" y="%g" font-size="%g" fill="%s">%s</text>' % (x, y, size, DIM, text)]


def main(out="figures/datapath.svg"):
    n = counts()
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
         'viewBox="0 0 %d %d" font-family="%s">' % (W, H, W, H, FONT),
         '<rect width="%d" height="%d" fill="%s"/>' % (W, H, SURF),
         '<defs><marker id="a" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" '
         'markerHeight="6" orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="%s"/></marker>'
         '</defs>' % DIM,
         '<text x="24" y="28" font-size="12.5" fill="%s">121 bits in, one per clock. '
         '92 flip-flops in total, and nowhere to keep a grid.</text>' % INK]

    s += box(24, 52, 92, 54, "I", "1 bit", "per clock", accent=True)
    s += label(24, 126, "clk, enable, rst_n", 9)

    mid2 = [79, 139, 199]
    s += box(C2, 52, C2W, 54, "input delay line",
             "%d cells, %d flops" % (n["input delay line"], len(rec.DELAY_LINE)),
             "the previous twelve bits", accent=True)
    s += box(C2, 112, C2W, 54, "cell counter (mod 11)",
             "%d cells, %d flops" % (n["cell counter (mod 11)"], len(rec.CELL_COUNTER)),
             "column of the arriving bit")
    s += box(C2, 172, C2W, 54, "row counter",
             "%d cells, %d flops" % (n["row counter"], len(rec.ROW_COUNTER)),
             "row of the arriving bit")
    s += box(C2, 232, C2W, 48, "run / done flag",
             "%d cells, %d flops" % (n["run/done flag"], len(rec.RUN_FLAG) + len(rec.TOGGLE)),
             "end of the stream")

    rules = [
        (52, "adjacency check", n["adjacency check"], len(rec.ADJACENCY),
         "taps 1 and 10-12, masked at row edges"),
        (112, "row accumulator", n["row accumulator"], len(rec.ROW_ACCUM),
         "one-hot, cleared at every row boundary"),
        (172, "column accumulators", n["column accumulators"],
         sum(len(x) for x in rec.COLUMN_ACCUM), "11 tallies, 2 bits saturating at 3"),
        (232, "region accumulators", n["region accumulators"],
         sum(len(x) for x in rec.REGION_ACCUM), "11 tallies, against the hard-wired map"),
        (292, "total-star counter", n["total-star counter"], len(rec.TOTAL_COUNTER),
         "redundant, and still load-bearing"),
    ]
    s += label(C3, 42, "the five rules, settled as the stream runs", 11)
    for y, title, cells, flops, note in rules:
        s += box(C3, y, C3W, 54, title, "%d cells, %d flops" % (cells, flops), note)

    s += box(C3, 376, C3W, 54, "success latch",
             "%d cells, %d flops" % (n["success latch"], len(rec.SUCCESS)),
             "one cycle after the last bit", accent=True)
    s += box(24, 376, C3W, 54, "output generator",
             "%d cells, %d flops (%d LFSR, %d index)"
             % (n["output generator"], len(rec.OUT_LFSR) + len(rec.OUT_INDEX),
                len(rec.OUT_LFSR), len(rec.OUT_INDEX)),
             "O = permute(LFSR) xor mask(index), gated by success")

    s += line(116, 79, IBUS, 79)
    s += line(IBUS, 79, IBUS, 346)
    for y in mid2:
        s += line(IBUS, y, C2, y, head=True)
    s += line(IBUS, 346, PBUS, 346)
    s += line(PBUS, 139, PBUS, 346)
    s.append('<circle cx="%g" cy="346" r="3" fill="%s"/>' % (PBUS, DIM))
    s += label(IBUS + 10, 340, "the bit and its position")
    for y in (139, 199):
        s += line(C2 + C2W, y, PBUS, y)
    for y, *_ in rules[1:]:
        s += line(PBUS, y + 27, C3, y + 27, head=True)
    s += line(C2 + C2W, 79, C3, 79, head=True)
    s += label(C2 + C2W + 6, 72, "taps")

    for y, *_ in rules:
        s += line(C3 + C3W, y + 27, VBUS, y + 27)
    s += line(VBUS, 79, VBUS, 403)
    s += line(VBUS, 403, C3 + C3W, 403, head=True)
    s += line(C3, 403, 24 + C3W, 403, head=True)
    s += label(340, 396, "start")
    s += label(24, 462, "the %d payload bytes exist nowhere on the die; "
                        "they appear only as the LFSR walks away from its seed"
               % len(rec.MESSAGE))

    s.append('</svg>')
    open(out, "w").write("\n".join(s))
    print("wrote %s: %.1f KB" % (out, len(open(out).read()) / 1024))


if __name__ == "__main__":
    main()
