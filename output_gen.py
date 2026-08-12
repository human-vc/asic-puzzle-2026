"""The output generator, decoded and then tested.

The message is not stored anywhere in the layout. What the gates hold is a mask
table; the plaintext only exists once the LFSR has been clocked from its reset
seed through the whole run:

    O = permute(LFSR) xor mask(index)

This script recovers the mask table by running the chip and subtracting the
permuted LFSR from the emitted byte, then tries to break the reading three ways:
by flipping single LFSR bits (the relation must be XOR-linear at every index),
by randomising the LFSR, and by randomising the index. The last two must destroy
the message; if either leaves it intact, the decode is a coincidence.
"""
import random

from sim import Design, BitBackend
from recovered import OUT_INDEX, OUT_LFSR, LFSR_TO_OUT_BIT, MESSAGE

EMIT = len(MESSAGE) + 4        # cycles of emission to watch, past the message


def permute(lfsr_bits):
    """each LFSR flop drives exactly one output bit"""
    o = 0
    for f, out_bit in LFSR_TO_OUT_BIT.items():
        o |= lfsr_bits[f] << out_bit
    return o


class Run:
    def __init__(self, path="puzzle_net.json"):
        self.d = Design(path)
        self.be = BitBackend(1)
        self.order = [f[1] for f in self.d.flops]
        self.bits = [int(c) for c in open("solution_bits.txt").read().strip()]

    def stream(self, force=None):
        """run the solution; `force(state, order, cycle)` may corrupt flops"""
        d, be, order = self.d, self.be, self.order
        st = d.new_state(be)
        for _ in range(2):
            d.cycle(be, st, {"rst_n": be.zero, "enable": be.zero, "I": be.zero})
        out = []
        for c in range(len(self.bits) + EMIT):
            lane = be.one if (c < len(self.bits) and self.bits[c]) else be.zero
            if force is not None:
                force(st, order, c)
            v = d.eval_at(be, st, {"rst_n": be.one, "enable": be.one,
                                   "I": lane, "clk": be.zero})
            if v["net:success"] & 1:
                out.append({
                    "cycle": c,
                    "O": sum(((v["net:O[%d]" % k] & 1) << k) for k in range(8)),
                    "index": sum(((st[order[f]] & 1) << i)
                                 for i, f in enumerate(OUT_INDEX)),
                    "lfsr": {f: st[order[f]] & 1 for f in OUT_LFSR},
                })
            d.cycle(be, st, {"rst_n": be.one, "enable": be.one, "I": lane})
        return out

    def text(self, frames):
        return "".join(chr(f["O"]) for f in frames if f["O"])


def main():
    r = Run()
    frames = r.stream()

    table = {}
    for f in frames:
        m = f["O"] ^ permute(f["lfsr"])
        if table.setdefault(f["index"], m) != m:
            raise RuntimeError("index %d wants two different masks" % f["index"])

    msg = r.text(frames)
    print("emitted: %r" % msg)
    print("matches the recovered message: %s" % (msg == MESSAGE))
    print()
    print("mask table, one entry per index (the gates hold these, not the text):")
    emitted = {f["index"]: f["O"] for f in frames}
    for i in sorted(table):
        print("  index %2d  mask %02x   -> %r" % (i, table[i], chr(emitted[i])))
    print("  the index counter saturates at 15, where the output parks at 00")
    print()

    print("is O linear in the LFSR? flip one LFSR bit as each byte is emitted:")
    trials, bad = 0, 0
    for f_idx in OUT_LFSR:
        for target in range(len(MESSAGE)):
            at = frames[target]["cycle"]

            def force(st, order, c, f_idx=f_idx, at=at):
                if c == at:
                    st[order[f_idx]] ^= r.be.one
            got = r.stream(force)
            trials += 1
            delta = got[target]["O"] ^ frames[target]["O"]
            if delta != (1 << LFSR_TO_OUT_BIT[f_idx]):
                bad += 1
    print("  %d of %d flips moved exactly the one predicted output bit"
          % (trials - bad, trials))

    first = frames[0]["cycle"]
    rng = random.Random(0)

    def scramble_lfsr(st, order, c):
        if c == first:
            for f in OUT_LFSR:
                st[order[f]] = r.be.one if rng.random() < 0.5 else r.be.zero

    def scramble_index(st, order, c):
        if c == first:
            for f in OUT_INDEX:
                st[order[f]] = r.be.one if rng.random() < 0.5 else r.be.zero

    print()
    print("negative controls (both must destroy the message):")
    print("  randomised LFSR  -> %r" % r.text(r.stream(scramble_lfsr)))
    print("  randomised index -> %r" % r.text(r.stream(scramble_index)))


if __name__ == "__main__":
    main()
