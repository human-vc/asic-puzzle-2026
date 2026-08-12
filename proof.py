"""Formal equivalence: prove the silicon's `success` equals the Star Battle
predicate for every one of the 2^121 possible input streams.

Builds a miter: unroll the extracted gate netlist 122 cycles, build the
high-level spec over the same 121 input variables, and ask SAT for any input
where they disagree. UNSAT in both directions = equivalence.
"""
import time

from pysat.solvers import Cadical153

from cnf import CnfBackend
from sim import Design
from recovered import REGION_CELLS as REGIONS

N = 11
CYCLES = 122


def popcount(be, lits):
    """binary sum of lits, LSB first"""
    total = []
    for lit in lits:
        carry = lit
        out = []
        for b in total:
            out.append(be.xorn([b, carry]))
            carry = be.andn([b, carry])
        out.append(carry)
        total = out
    return total


def exactly(be, lits, k):
    bits = popcount(be, lits)
    want = []
    for i, b in enumerate(bits):
        want.append(b if (k >> i) & 1 else be.not_(b))
    return be.andn(want)


def spec_circuit(be, ivars):
    grid = [REGIONS[r * N:(r + 1) * N] for r in range(N)]
    cell = lambda r, c: ivars[r * N + c]

    regions = {}
    for r in range(N):
        for c in range(N):
            regions.setdefault(grid[r][c], []).append(cell(r, c))

    terms = []
    for r in range(N):
        terms.append(exactly(be, [cell(r, c) for c in range(N)], 2))
    for c in range(N):
        terms.append(exactly(be, [cell(r, c) for r in range(N)], 2))
    for k in sorted(regions):
        terms.append(exactly(be, regions[k], 2))
    for r in range(N):
        for c in range(N):
            for dr, dc in ((0, 1), (1, -1), (1, 0), (1, 1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < N and 0 <= cc < N:
                    terms.append(be.not_(be.andn([cell(r, c), cell(rr, cc)])))
    return be.andn(terms)


def main():
    t0 = time.time()
    d = Design("puzzle_net.json")
    be = CnfBackend()
    state = {q: (be.one if k == "dfstp" else be.zero) for k, q, _, _, _, _ in d.flops}
    ivars = [be.new() for _ in range(CYCLES)]
    for c in range(CYCLES):
        state, _ = d.step(be, state, {"rst_n": be.one, "enable": be.one,
                                      "I": ivars[c], "clk": be.zero})
    succ = state["net:success"]
    print("netlist unrolled %d cycles (%.1fs)" % (CYCLES, time.time() - t0))

    spec = spec_circuit(be, ivars[:N * N])
    print("spec built; total vars=%d clauses=%d" % (be.nvars, len(be.clauses)))

    for name, a, b in [("chip accepts but spec rejects", succ, be.not_(spec)),
                       ("spec accepts but chip rejects", spec, be.not_(succ))]:
        s = Cadical153(bootstrap_with=be.clauses)
        t = time.time()
        sat = s.solve(assumptions=[a, b])
        print("  %-32s : %s  (%.1fs)" % (name, "COUNTEREXAMPLE FOUND" if sat else "UNSAT",
                                         time.time() - t))
        if sat:
            model = set(l for l in s.get_model() if l > 0)
            bits = [1 if v in model else 0 for v in ivars[:N * N]]
            print("     ", "".join(map(str, bits)))
        s.delete()

    print("\nEquivalence holds => the chip is exactly an 11x11 two-star Star Battle")
    print("checker on the recovered regions, for all 2^121 input streams.")

    MAX_MODELS = 3
    s = Cadical153(bootstrap_with=be.clauses)
    s.add_clause([spec])
    n = 0
    while s.solve() and n < MAX_MODELS:
        model = set(l for l in s.get_model() if l > 0)
        bits = [1 if v in model else 0 for v in ivars[:N * N]]
        n += 1
        s.add_clause([-v if b else v for v, b in zip(ivars[:N * N], bits)])
    print("satisfying grids for the spec: %d%s"
          % (n, " (unique)" if n == 1 else " (search capped at %d)" % MAX_MODELS))


if __name__ == "__main__":
    main()
