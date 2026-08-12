"""Replay a candidate 121-bit input on the gate-level model and read O[7:0]."""
import sys

from sim import Design, BitBackend

TAIL = int(sys.argv[2]) if len(sys.argv) > 2 else 64


def main():
    bits = [int(c) for c in open(sys.argv[1]).read().strip()]
    d = Design("puzzle_net.json")
    be = BitBackend(1)
    st = d.new_state(be)
    for _ in range(2):
        d.cycle(be, st, {"rst_n": be.zero, "enable": be.zero, "I": be.zero})

    for b in bits:
        d.cycle(be, st, {"rst_n": be.one, "enable": be.one, "I": (be.one if b else be.zero)})
    v = d.eval_at(be, st, {"rst_n": be.one, "enable": be.one, "I": be.zero, "clk": be.zero})
    print("success right after last bit: %d" % (v["net:success"] & 1))

    d.cycle(be, st, {"rst_n": be.one, "enable": be.one, "I": be.zero})
    v = d.eval_at(be, st, {"rst_n": be.one, "enable": be.one, "I": be.zero, "clk": be.zero})
    print("success one cycle later:      %d" % (v["net:success"] & 1))

    print("\nO[7:0] for the next %d cycles:" % TAIL)
    out = []
    for k in range(TAIL):
        v = d.eval_at(be, st, {"rst_n": be.one, "enable": be.one, "I": be.zero, "clk": be.zero})
        o = sum(((v["net:O[%d]" % i] & 1) << i) for i in range(8))
        out.append(o)
        d.cycle(be, st, {"rst_n": be.one, "enable": be.one, "I": be.zero})
    print("hex:", " ".join("%02x" % o for o in out))
    print("asc:", "".join(chr(o) if 32 <= o < 127 else "." for o in out))


if __name__ == "__main__":
    main()
