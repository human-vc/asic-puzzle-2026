"""Cycle-accurate trace of every flop, for structural discovery."""
import sys

from sim import Design, BitBackend


def run(path, bits, cycles=None, enable=1, show=None, hold_reset=2):
    d = Design(path)
    be = BitBackend(1)
    st = d.new_state(be)
    fname = {f[1]: "F%02d" % i for i, f in enumerate(d.flops)}
    order = [f[1] for f in d.flops]

    def snap(v):
        return "".join(str(v.get(q, 0) & 1) for q in order)

    rows = []
    for _ in range(hold_reset):
        d.cycle(be, st, {"rst_n": 0, "enable": 0, "I": 0})
    n = cycles if cycles is not None else len(bits)
    for c in range(n):
        i = bits[c] if c < len(bits) else 0
        v = d.eval_at(be, st, {"rst_n": 1, "enable": enable, "I": i, "clk": 0})
        rows.append((c, i, snap(st), v.get("net:success", 0) & 1,
                     sum(((v.get("net:O[%d]" % k, 0) & 1) << k) for k in range(8))))
        d.cycle(be, st, {"rst_n": 1, "enable": enable, "I": i})
    return d, fname, order, rows


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "puzzle_net.json"
    N = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    d, fname, order, rows = run(path, [0] * N, cycles=N)
    print("cyc I  " + " ".join("F%02d" % i for i in range(len(order))) + "   S  O")
    for c, i, s, succ, o in rows:
        print("%3d %d  %s   %d  %02x" % (c, i, "   ".join(s), succ, o))
