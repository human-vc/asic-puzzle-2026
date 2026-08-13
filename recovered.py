"""Everything recovered from puzzle.gds, in one place.

Every other script imports from here rather than keeping its own copy, so a
correction cannot leave a stale duplicate behind. Flop numbers are indices into
`sim.Design.flops`, which is ordered by the extracted netlist.

Run this file directly to check the structure against itself.
"""

N = 11
CELLS = N * N

MESSAGE = "(* TWO STARS *)"

REGION_MAP = """
A A A A A C C G J J I
A A D A A C G G J J I
A A D C C C C G G J I
A A D C B B B I G G I
D A D C B I I I I I I
D D D C B B B I K K K
C C C C C C B I K H H
C F F F B B B I K H H
C F F E I I I I K H H
C C F E E I I I K K K
C F F E I I I I I I I
"""

CELL_COUNTER = [38, 84, 45, 73]
ROW_COUNTER = [14, 9, 64, 58]
RUN_FLAG = [7]
TOGGLE = [61]
DELAY_LINE = [13, 20, 71, 46, 29, 52, 15, 50, 8, 65, 74, 62]
ADJACENCY = [28]
ROW_ACCUM = [68, 88, 81]

COLUMN_ACCUM = [[11, 24], [18, 30], [27, 80], [31, 72], [33, 76], [36, 42],
                [37, 59], [39, 67], [40, 57], [43, 78], [79, 85]]
REGION_ACCUM = [[6, 55], [10, 25], [17, 47], [19, 82], [23, 87], [26, 70],
                [32, 63], [41, 66], [48, 53], [49, 75], [56, 69]]

TOTAL_COUNTER = [(16, 1), (12, 2), (83, 4), (86, 8), (89, 16), (51, 32),
                 (34, 64), (54, 128)]

SUCCESS = [35, 60]

OUT_INDEX = [0, 1, 2, 91]
OUT_LFSR = [3, 4, 5, 21, 22, 44, 77, 90]

LFSR_TO_OUT_BIT = {3: 0, 4: 5, 5: 2, 21: 4, 22: 6, 44: 3, 77: 1, 90: 7}

TOTAL_FLOPS = 92


REGION_CELLS = REGION_MAP.split()


def region_grid():
    """the region letter of each cell, as 11 rows of 11"""
    rows = [r.split() for r in REGION_MAP.strip().splitlines()]
    assert len(rows) == N and all(len(r) == N for r in rows)
    return rows


def region_letters():
    grid = region_grid()
    return sorted({ch for row in grid for ch in row})


def regions():
    """letter -> the cell indices it covers, row-major"""
    grid = region_grid()
    out = {}
    for k in range(CELLS):
        out.setdefault(grid[k // N][k % N], []).append(k)
    return out


def forward_neighbours(k):
    """The neighbours of cell k that come later in row-major order.

    Checking only these visits each adjacent pair exactly once, which is what
    the chip does with its 12-deep history.
    """
    r, c = divmod(k, N)
    out = []
    for dr, dc in ((0, 1), (1, -1), (1, 0), (1, 1)):
        rr, cc = r + dr, c + dc
        if 0 <= rr < N and 0 <= cc < N:
            out.append(rr * N + cc)
    return out


def all_flop_groups():
    return {
        "cell counter": CELL_COUNTER,
        "row counter": ROW_COUNTER,
        "run/done flag": RUN_FLAG,
        "toggle": TOGGLE,
        "input delay line": DELAY_LINE,
        "adjacency check": ADJACENCY,
        "row accumulator": ROW_ACCUM,
        "column accumulators": [f for pair in COLUMN_ACCUM for f in pair],
        "region accumulators": [f for pair in REGION_ACCUM for f in pair],
        "total-star counter": [f for f, _w in TOTAL_COUNTER],
        "success latch": SUCCESS,
        "output index": OUT_INDEX,
        "output LFSR": OUT_LFSR,
    }


def check():
    """The invariant that would have caught mislabelling: the groups must
    partition all 92 flip-flops, with none missing and none claimed twice."""
    groups = all_flop_groups()
    seen, dupes = set(), []
    for name, idxs in groups.items():
        for i in idxs:
            if i in seen:
                dupes.append((name, i))
            seen.add(i)
    missing = sorted(set(range(TOTAL_FLOPS)) - seen)
    grid = region_grid()
    sizes = {k: len(v) for k, v in regions().items()}
    print("flop groups: %d, covering %d of %d flops" % (len(groups), len(seen), TOTAL_FLOPS))
    print("  duplicates: %s" % (dupes or "none"))
    print("  unaccounted: %s" % (missing or "none"))
    print("regions: %d, sizes summing to %d" % (len(sizes), sum(sizes.values())))
    print("message: %r (%d bytes)" % (MESSAGE, len(MESSAGE)))
    assert not dupes and not missing, "flop groups do not partition the flops"
    assert sum(sizes.values()) == CELLS
    assert len(grid) == N
    print("OK")


if __name__ == "__main__":
    check()
