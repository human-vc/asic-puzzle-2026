"""Unroll the puzzle into CNF and search for inputs asserting success.

The verdict lands one cycle after the last cell, so the unroll has to run one
cycle past the grid: at 121 cycles `success` is still low and the solver
correctly reports UNSAT. The extra cycle's input bit is free and not part of the
grid, so only the first 121 are read back.
"""
import time

from pysat.solvers import Cadical153

from cnf import CnfBackend
from sim import Design

GRID_BITS = 121
CYCLES = GRID_BITS + 1


def build(path=("puzzle_net.json"), cycles=CYCLES):
    d = Design(path)
    be = CnfBackend()

    reset = {}
    for kind, q, _d, _c, _ctrl, _n in d.flops:
        reset[q] = be.one if kind == "dfstp" else be.zero

    state = dict(reset)
    ivars = []
    for c in range(cycles):
        i = be.new()
        ivars.append(i)
        inputs = {"rst_n": be.one, "enable": be.one, "I": i, "clk": be.zero}
        state, _v = d.step(be, state, inputs)

    succ = state["net:success"]
    return d, be, ivars, state, succ


def main():
    t0 = time.time()
    d, be, ivars, state, succ = build()
    print("unrolled %d cycles: vars=%d clauses=%d  (%.1fs)" % (
        CYCLES, be.nvars, len(be.clauses), time.time() - t0))

    s = Cadical153(bootstrap_with=be.clauses)
    s.add_clause([succ])
    t0 = time.time()
    sat = s.solve()
    print("solve: %s (%.1fs)" % (sat, time.time() - t0))
    if not sat:
        return
    gvars = ivars[:GRID_BITS]
    model = set(l for l in s.get_model() if l > 0)
    bits = [1 if v in model else 0 for v in gvars]
    print("input bits (%d):" % GRID_BITS, "".join(map(str, bits)))

    grid = ["".join(map(str, bits[r * 11:(r + 1) * 11])) for r in range(11)]
    print("\n11x11 grid (row-major, first bit first):")
    for row in grid:
        print("   " + " ".join("#" if ch == "1" else "." for ch in row))

    with open("solution_bits.txt", "w") as f:
        f.write("".join(map(str, bits)) + "\n")

    n = 1
    while n < 5:
        s.add_clause([-v if b else v for v, b in zip(gvars, bits)])
        if not s.solve():
            break
        model = set(l for l in s.get_model() if l > 0)
        bits = [1 if v in model else 0 for v in gvars]
        n += 1
    print("\ndistinct solutions found (cap 5): %d" % n)


if __name__ == "__main__":
    main()
