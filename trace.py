"""Three ways of watching the recovered checker run.

    trace.py flops [netlist] [n]   every flip-flop, cycle by cycle
    trace.py window [a] [b]        the 12-deep history window as a text waveform
    trace.py verify <bits> [n]     replay a candidate grid and read O[7:0]
"""
import sys

from sim import Design, BitBackend
from recovered import DELAY_LINE, ADJACENCY, N


def flops(path="puzzle_net.json", cycles=40):
    d = Design(path)
    be = BitBackend(1)
    st = d.new_state(be)
    order = [f[1] for f in d.flops]
    for _ in range(2):
        d.cycle(be, st, {"rst_n": be.zero, "enable": be.zero, "I": be.zero})

    print("cyc I  " + " ".join("F%02d" % i for i in range(len(order))) + "   S  O")
    for c in range(cycles):
        v = d.eval_at(be, st, {"rst_n": be.one, "enable": be.one,
                               "I": be.zero, "clk": be.zero})
        snap = "".join(str(st.get(q, 0) & 1) for q in order)
        o = sum(((v.get("net:O[%d]" % k, 0) & 1) << k) for k in range(8))
        print("%3d %d  %s   %d  %02x"
              % (c, 0, "   ".join(snap), v.get("net:success", 0) & 1, o))
        d.cycle(be, st, {"rst_n": be.one, "enable": be.one, "I": be.zero})


def stream(d, be, stars, cycles):
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


def render(rows, lo, hi):
    sel = [r for r in rows if lo <= r["cyc"] <= hi]
    label = 14

    def line(name, vals):
        return name.ljust(label) + " ".join(vals)

    out = [line("cycle", ["%2d" % (r["cyc"] % 100) for r in sel]),
           line("row", ["%2d" % (r["cyc"] // N) for r in sel]),
           line("col", ["%2d" % (r["cyc"] % N) for r in sel]),
           " " * label + "-" * (3 * len(sel) - 1),
           line("I", [" 1" if r["I"] else " ." for r in sel])]
    for t in range(12):
        out.append(line("  tap %2d" % (t + 1),
                        [" 1" if r["taps"][t] else " ." for r in sel]))
    out.append(" " * label + "-" * (3 * len(sel) - 1))
    out.append(line("adjacency", [" 1" if r["adj"] else " ." for r in sel]))
    return "\n".join(out)


def window(a=64, b=75):
    d = Design("puzzle_net.json")
    be = BitBackend(1)
    rows = stream(d, be, {a, b}, b + 4)
    print("stars at cell %d (r%dc%d) and cell %d (r%dc%d)"
          % (a, a // N, a % N, b, b // N, b % N))
    print()
    print(render(rows, a - 1, b + 2))


def verify(path, tail=64):
    bits = [int(c) for c in open(path).read().strip()]
    d = Design("puzzle_net.json")
    be = BitBackend(1)
    st = d.new_state(be)
    for _ in range(2):
        d.cycle(be, st, {"rst_n": be.zero, "enable": be.zero, "I": be.zero})

    for b in bits:
        d.cycle(be, st, {"rst_n": be.one, "enable": be.one,
                         "I": (be.one if b else be.zero)})
    v = d.eval_at(be, st, {"rst_n": be.one, "enable": be.one,
                           "I": be.zero, "clk": be.zero})
    print("success right after last bit: %d" % (v["net:success"] & 1))

    d.cycle(be, st, {"rst_n": be.one, "enable": be.one, "I": be.zero})
    v = d.eval_at(be, st, {"rst_n": be.one, "enable": be.one,
                           "I": be.zero, "clk": be.zero})
    print("success one cycle later:      %d" % (v["net:success"] & 1))

    print("\nO[7:0] for the next %d cycles:" % tail)
    out = []
    for _k in range(tail):
        v = d.eval_at(be, st, {"rst_n": be.one, "enable": be.one,
                               "I": be.zero, "clk": be.zero})
        out.append(sum(((v["net:O[%d]" % i] & 1) << i) for i in range(8)))
        d.cycle(be, st, {"rst_n": be.one, "enable": be.one, "I": be.zero})
    print("hex:", " ".join("%02x" % o for o in out))
    print("asc:", "".join(chr(o) if 32 <= o < 127 else "." for o in out))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "flops"
    a = sys.argv[2:]
    if mode == "flops":
        flops(a[0] if a else "puzzle_net.json", int(a[1]) if len(a) > 1 else 40)
    elif mode == "window":
        window(int(a[0]) if a else 64, int(a[1]) if len(a) > 1 else 75)
    elif mode == "verify":
        verify(a[0], int(a[1]) if len(a) > 1 else 64)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
