"""Differential test: gate-level simulation vs the Star Battle spec.

Independent of the SAT path in proof.py -- this runs the actual gate netlist
bit-parallel over many grids (single/double bit flips of the solution, random
2-per-row grids, uniform random) and checks the chip agrees with the spec.
"""
import itertools
import random

from sim import Design, BitBackend
from recovered import REGION_CELLS as REGIONS, forward_neighbours

N = 11
CELLS = N * N
GRID = [REGIONS[r * N:(r + 1) * N] for r in range(N)]
REGION_OF = [GRID[k // N][k % N] for k in range(CELLS)]
NEIGH = [forward_neighbours(k) for k in range(CELLS)]


def spec(bits):
    for r in range(N):
        if sum(bits[r * N:(r + 1) * N]) != 2:
            return 0
    for c in range(N):
        if sum(bits[r * N + c] for r in range(N)) != 2:
            return 0
    counts = {}
    for k in range(CELLS):
        if bits[k]:
            counts[REGION_OF[k]] = counts.get(REGION_OF[k], 0) + 1
    if sorted(counts.values()) != [2] * N or len(counts) != N:
        return 0
    for k in range(CELLS):
        if bits[k]:
            for j in NEIGH[k]:
                if bits[j]:
                    return 0
    return 1


def chip(d, grids):
    """run len(grids) grids in parallel through the gate netlist"""
    w = len(grids)
    be = BitBackend(w)
    st = d.new_state(be)
    for _ in range(2):
        d.cycle(be, st, {"rst_n": be.zero, "enable": be.zero, "I": be.zero})
    lanes = []
    for k in range(CELLS):
        lanes.append(sum((g[k] << i) for i, g in enumerate(grids)))
    for k in range(CELLS):
        d.cycle(be, st, {"rst_n": be.one, "enable": be.one, "I": lanes[k]})
    d.cycle(be, st, {"rst_n": be.one, "enable": be.one, "I": be.zero})
    v = d.eval_at(be, st, {"rst_n": be.one, "enable": be.one, "I": be.zero, "clk": be.zero})
    s = v["net:success"]
    return [(s >> i) & 1 for i in range(w)]


def batches(grids, size=512):
    for i in range(0, len(grids), size):
        yield grids[i:i + size]


def main():
    random.seed(0)
    sol = [int(c) for c in open("solution_bits.txt").read().strip()]
    d = Design("puzzle_net.json")

    pool = []
    pool.append(("solution", [list(sol)]))

    flips1 = []
    for k in range(CELLS):
        g = list(sol)
        g[k] ^= 1
        flips1.append(g)
    pool.append(("1-bit flips", flips1))

    flips2 = []
    for a, b in itertools.combinations(range(CELLS), 2):
        g = list(sol)
        g[a] ^= 1
        g[b] ^= 1
        flips2.append(g)
    pool.append(("2-bit flips", flips2))

    two_per_row = []
    for _ in range(20000):
        g = [0] * CELLS
        for r in range(N):
            for c in random.sample(range(N), 2):
                g[r * N + c] = 1
        two_per_row.append(g)
    pool.append(("random 2-per-row", two_per_row))

    rnd = [[random.randint(0, 1) for _ in range(CELLS)] for _ in range(5000)]
    pool.append(("uniform random", rnd))

    sparse = []
    for _ in range(5000):
        g = [0] * CELLS
        for k in random.sample(range(CELLS), 22):
            g[k] = 1
        sparse.append(g)
    pool.append(("random 22 stars", sparse))

    total = disagree = accepted = 0
    for name, grids in pool:
        n = bad = acc = 0
        for chunk in batches(grids):
            got = chip(d, chunk)
            for g, s in zip(chunk, got):
                e = spec(g)
                n += 1
                acc += s
                if s != e:
                    bad += 1
                    if disagree + bad <= 3:
                        print("  MISMATCH chip=%d spec=%d grid=%s"
                              % (s, e, "".join(map(str, g))))
        total += n
        disagree += bad
        accepted += acc
        print("  %-18s n=%-7d disagreements=%-4d accepted-by-chip=%d" % (name, n, bad, acc))

    print("\ntotal grids tested: %d   disagreements: %d   accepted by chip: %d"
          % (total, disagree, accepted))


if __name__ == "__main__":
    main()
