"""Recover the hard-wired region map by probing each cell with a one-hot input.

Cell k (row-major) is the only star; whichever region accumulator moves off zero
identifies that cell's region.
"""
import collections

from sim import Design, BitBackend

from recovered import REGION_ACCUM as REGION_GROUPS, COLUMN_ACCUM as COLUMN_GROUPS

N = 121


def probe():
    d = Design("puzzle_net.json")
    be = BitBackend(N)
    st = d.new_state(be)
    order = [f[1] for f in d.flops]

    for _ in range(2):
        d.cycle(be, st, {"rst_n": be.zero, "enable": be.zero, "I": be.zero})
    for k in range(N):
        d.cycle(be, st, {"rst_n": be.one, "enable": be.one, "I": 1 << k})
    return d, be, st, order


def assign(st, order, groups):
    """for each of the 121 lanes, which group index is non-zero"""
    res = [set() for _ in range(N)]
    for gi, g in enumerate(groups):
        acc = 0
        for f in g:
            acc |= st[order[f]]
        for k in range(N):
            if (acc >> k) & 1:
                res[k].add(gi)
    return res


def main():
    d, be, st, order = probe()
    reg = assign(st, order, REGION_GROUPS)
    col = assign(st, order, COLUMN_GROUPS)

    bad = [k for k in range(N) if len(reg[k]) != 1]
    print("cells with a unique region hit: %d/121  (anomalies: %s)" % (N - len(bad), bad[:5]))

    colmap = [sorted(col[k])[0] if len(col[k]) == 1 else None for k in range(N)]
    ok = all(colmap[k] is not None for k in range(N))
    print("column groups behave as columns:",
          ok and all(len({colmap[r * 11 + c] for r in range(11)}) == 1 for c in range(11)))

    letters = "ABCDEFGHIJK"
    grid = [[letters[sorted(reg[r * 11 + c])[0]] if reg[r * 11 + c] else "?"
             for c in range(11)] for r in range(11)]
    print("\nregion map:")
    for row in grid:
        print("   " + " ".join(row))

    sizes = collections.Counter(ch for row in grid for ch in row)
    print("\nregion sizes:", dict(sorted(sizes.items())))

    bits = [int(x) for x in open("solution_bits.txt").read().strip()]
    print("\nsolution overlaid on regions:")
    for r in range(11):
        print("   " + " ".join(("%s*" % grid[r][c]) if bits[r * 11 + c] else ("%s " % grid[r][c])
                               for c in range(11)))
    per_region = collections.Counter(grid[r][c] for r in range(11) for c in range(11)
                                     if bits[r * 11 + c])
    print("\nstars per region:", dict(sorted(per_region.items())))
    print("stars per row:   ", [sum(bits[r * 11:(r + 1) * 11]) for r in range(11)])
    print("stars per column:", [sum(bits[r * 11 + c] for r in range(11)) for c in range(11)])
    adj = [(r, c) for r in range(11) for c in range(11) if bits[r * 11 + c]
           for dr in (-1, 0, 1) for dc in (-1, 0, 1)
           if (dr or dc) and 0 <= r + dr < 11 and 0 <= c + dc < 11
           and bits[(r + dr) * 11 + c + dc]]
    print("adjacent star pairs (8-neighbourhood):", len(adj))


if __name__ == "__main__":
    main()
