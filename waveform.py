"""Text waveform of the 12-deep history window sliding past an adjacency violation.

The window is 12 bits wide, so it cannot be drawn as a one-bit waveform: each
tap gets its own row, cycles run left to right, and a star travelling down the
line appears as a diagonal. The adjacency check fires on the cycle where the
incoming bit and tap 11 (the cell directly above) are both set.
"""
import sys

from sim import Design, BitBackend
from recovered import DELAY_LINE, ADJACENCY, CELL_COUNTER, ROW_COUNTER, N


def run(d, be, stars, cycles):
    order = [f[1] for f in d.flops]
    st = d.new_state(be)
    for _ in range(2):
        d.cycle(be, st, {"rst_n": be.zero, "enable": be.zero, "I": be.zero})
    rows = []
    for c in range(cycles):
        bit = 1 if c in stars else 0
        rows.append({
            "cyc": c,
            "I": bit,
            "taps": [st[order[f]] & 1 for f in DELAY_LINE],
            "adj": st[order[ADJACENCY[0]]] & 1,
        })
        d.cycle(be, st, {"rst_n": be.one, "enable": be.one,
                         "I": (be.one if bit else be.zero)})
    return rows


def render(rows, lo, hi, stars):
    sel = [r for r in rows if lo <= r["cyc"] <= hi]
    label = 14

    def line(name, vals):
        return name.ljust(label) + " ".join(vals)

    out = []
    out.append(line("cycle", ["%2d" % (r["cyc"] % 100) for r in sel]))
    out.append(line("row", ["%2d" % (r["cyc"] // N) for r in sel]))
    out.append(line("col", ["%2d" % (r["cyc"] % N) for r in sel]))
    out.append(" " * label + "-" * (3 * len(sel) - 1))
    out.append(line("I", [" 1" if r["I"] else " ." for r in sel]))
    for t in range(12):
        out.append(line("  tap %2d" % (t + 1),
                        [" 1" if r["taps"][t] else " ." for r in sel]))
    out.append(" " * label + "-" * (3 * len(sel) - 1))
    out.append(line("adjacency", [" 1" if r["adj"] else " ." for r in sel]))
    return "\n".join(out)


def main():
    a = int(sys.argv[1]) if len(sys.argv) > 1 else 64
    b = int(sys.argv[2]) if len(sys.argv) > 2 else 75
    d = Design("puzzle_net.json")
    be = BitBackend(1)
    stars = {a, b}
    rows = run(d, be, stars, b + 4)
    lo, hi = a - 1, b + 2
    print("stars at cell %d (r%dc%d) and cell %d (r%dc%d)"
          % (a, a // N, a % N, b, b // N, b % N))
    print()
    print(render(rows, lo, hi, stars))


if __name__ == "__main__":
    main()
