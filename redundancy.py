"""The total-star counter is implied by the row constraints, and load-bearing anyway.

Eleven rows carrying two stars each already force a total of 22, so the eight-bit
counter adds nothing to the predicate on any input the row logic accepts. It is
still wired into the verdict: flip any one of its flops part-way through the
accepted run and `success` never rises.

This is the precise sense of "redundant" -- redundant as a constraint, not as a
gate. Corrupting the netlist is not something the chip can do to itself; it is a
way of asking which flops the verdict actually depends on.
"""
from sim import Design, BitBackend
from recovered import TOTAL_COUNTER, N

AT = (60, 90, 118)


def accepts(d, be, order, bits, flip=None, at=None):
    st = d.new_state(be)
    for _ in range(2):
        d.cycle(be, st, {"rst_n": be.zero, "enable": be.zero, "I": be.zero})
    for c in range(len(bits) + 3):
        if flip is not None and c == at:
            st[order[flip]] ^= be.one
        lane = be.one if (c < len(bits) and bits[c]) else be.zero
        v = d.eval_at(be, st, {"rst_n": be.one, "enable": be.one,
                               "I": lane, "clk": be.zero})
        if v["net:success"] & 1:
            return True
        d.cycle(be, st, {"rst_n": be.one, "enable": be.one, "I": lane})
    return False


def main():
    d = Design("puzzle_net.json")
    be = BitBackend(1)
    order = [f[1] for f in d.flops]
    bits = [int(c) for c in open("solution_bits.txt").read().strip()]

    print("two stars in each of %d rows forces a total of %d" % (N, 2 * N))
    print("untouched run is accepted: %s" % accepts(d, be, order, bits))
    print()
    print("flipping one counter flop part-way through the accepted run:")
    killed = 0
    for f, w in TOTAL_COUNTER:
        got = [accepts(d, be, order, bits, flip=f, at=c) for c in AT]
        killed += sum(1 for g in got if not g)
        print("  flop %2d (weight %3d) at cycles %s -> accepted %s"
              % (f, w, "/".join(map(str, AT)), got))
    print()
    print("%d of %d corruptions stopped the chip accepting its own solution"
          % (killed, len(TOTAL_COUNTER) * len(AT)))


if __name__ == "__main__":
    main()
