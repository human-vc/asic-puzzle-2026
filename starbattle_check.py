"""Independent check: solve 2-star Star Battle on the recovered regions with SAT,
and compare against the grid the chip accepts."""
from pysat.card import CardEnc, EncType
from pysat.formula import IDPool
from pysat.solvers import Cadical153

from recovered import N, REGION_CELLS as REGIONS


def contiguous(cells):
    cells = set(cells)
    seen = {next(iter(cells))}
    front = list(seen)
    while front:
        r, c = front.pop()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (r + dr, c + dc)
            if n in cells and n not in seen:
                seen.add(n)
                front.append(n)
    return len(seen) == len(cells)


def main():
    grid = [REGIONS[r * N:(r + 1) * N] for r in range(N)]
    regions = {}
    for r in range(N):
        for c in range(N):
            regions.setdefault(grid[r][c], []).append((r, c))

    print("regions: %d  contiguous(4-conn): %s" % (
        len(regions), all(contiguous(v) for v in regions.values())))
    for k in sorted(regions):
        if not contiguous(regions[k]):
            print("   region %s is NOT contiguous" % k)

    pool = IDPool()
    def v(r, c):
        return pool.id(("s", r, c))

    cnf = []
    groups = ([[(r, c) for c in range(N)] for r in range(N)] +
              [[(r, c) for r in range(N)] for c in range(N)] +
              list(regions.values()))
    for g in groups:
        lits = [v(r, c) for r, c in g]
        cnf += CardEnc.equals(lits=lits, bound=2, vpool=pool, encoding=EncType.seqcounter).clauses

    for r in range(N):
        for c in range(N):
            for dr, dc in ((0, 1), (1, -1), (1, 0), (1, 1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < N and 0 <= cc < N:
                    cnf.append([-v(r, c), -v(rr, cc)])

    s = Cadical153(bootstrap_with=cnf)
    sols = []
    while s.solve() and len(sols) < 5:
        model = set(l for l in s.get_model() if l > 0)
        cells = [(r, c) for r in range(N) for c in range(N) if v(r, c) in model]
        sols.append(cells)
        s.add_clause([-v(r, c) for r, c in cells])
    print("star-battle solutions found (cap 5): %d" % len(sols))

    chip = [int(x) for x in open("solution_bits.txt").read().strip()]
    chip_cells = sorted((k // N, k % N) for k in range(N * N) if chip[k])
    print("matches the grid the chip accepts:", sorted(sols[0]) == chip_cells if sols else False)

    for r in range(N):
        print("   " + " ".join("%s%s" % (grid[r][c], "*" if chip[r * N + c] else " ")
                               for c in range(N)))


if __name__ == "__main__":
    main()
